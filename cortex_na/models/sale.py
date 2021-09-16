# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.exceptions import Warning
import datetime
from datetime import timedelta


class SaleOrder(models.Model):
    _inherit = "sale.order"

    delivered_amount = fields.Float('Delivered Amount', compute='_compute_delivered_amount', store=True)
    pending_amount = fields.Float('Pending Amount', compute='_compute_pending_amount', store=True)
    product_ids = fields.Many2many('product.product', string='Product', compute='_compute_product_categories',
                                   store=True)
    product_categ_ids = fields.Many2many('product.category', string='Product Category',
                                         compute='_compute_product_categories', store=True)
    purchase_count = fields.Integer(compute='_compute_purchase_count', string='Purchase Order')
    remaining_funds_to_be_received = fields.Float("Remaining Funds To Be Received",
                                                  compute='_compute_remaining_funds_to_be_received', store=True)
    new_expected_date = fields.Date(string='Expected Date', default=fields.Date.today, track_visibility='onchange')
    show_in_cash_flow = fields.Boolean(string='Show in Cash FLow')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False,
                                   states={'sale': [('required', True)], 'done': [('required', True)]}, readonly=False,
                                   default=None)
    manufacturing_count = fields.Integer(compute='_compute_manufacture_count', string='Manufacture Order')
    expected_ship_date = fields.Date(string='Expected Ship Date', track_visibility='onchange', copy=False)
    dont_apply_gst = fields.Boolean(string="Don't Apply GST", default=False, track_visibility='onchange', copy=False)

    @api.onchange('date_order')
    def onchange_date_order(self):
        if self.date_order:
            self.expected_ship_date = self.date_order + timedelta(days=60)

    @api.onchange('payment_term_id')
    def onchange_payment_term_id(self):
        today = datetime.date.today().strftime('%Y-%m-%d')
        exp_date = self.new_expected_date.strftime('%Y-%m-%d')
        inv_date = today
        inv_date = datetime.datetime.strptime(inv_date, "%Y-%m-%d")
        if self.payment_term_id:
            payment_obj = self.env['account.payment.term.line'].search([('payment_id', '=', self.payment_term_id.id)])
            total_days = 0
            for record in payment_obj:
                total_days += record.days
            self.new_expected_date = (inv_date + datetime.timedelta(total_days)).strftime("%Y-%m-%d")
        else:
            self.new_expected_date = (inv_date + datetime.timedelta(0)).strftime("%Y-%m-%d")

    def _compute_purchase_count(self):
        purchase_order = self.env['purchase.order'].search([('select_sale_order_ids', 'in', self.id)])
        self.purchase_count = len(purchase_order)

    def _compute_manufacture_count(self):
        manufacture_order = self.env['mrp.production'].search([('sale_order_ids', 'in', self.id)])
        self.manufacturing_count = len(manufacture_order)

    def action_view_purchase_order(self):
        purchase_obj = self.env['purchase.order'].search([('select_sale_order_ids', 'in', self.id)])
        purchase_ids = []
        for each in purchase_obj:
            purchase_ids.append(each.id)
        view_id = self.env.ref('purchase.purchase_order_form').id
        if purchase_ids:
            if len(purchase_ids) <= 1:
                value = {
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'purchase.order',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'name': _('Purchase orders'),
                    'res_id': purchase_ids and purchase_ids[0]
                }
            else:
                value = {
                    'domain': str([('id', 'in', purchase_ids)]),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'purchase.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name': _('Purchase orders'),
                    'res_id': purchase_ids
                }
            return value

    def action_open_mo(self):
        manufacture_obj = self.env['mrp.production'].search([('sale_order_ids', 'in', self.id)])
        manufacture_ids = []
        view_id = self.env.ref('mrp.mrp_production_form_view').id
        for each in manufacture_obj:
            manufacture_ids.append(each.id)
        if len(manufacture_ids) <= 1:
            return {
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': view_id,
                'name': _('Manufacturing Orders'),
                'res_model': 'mrp.production',
                'type': 'ir.actions.act_window',
                'domain': [('sale_order_ids', 'in', self.id)],
                'res_id': manufacture_ids and manufacture_ids[0]
            }
        else:
            return {
                'name': _('Manufacturing Orders'),
                'res_model': 'mrp.production',
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'domain': [('sale_order_ids', 'in', self.id)],
            }

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if self._context.get('ctx_amount_pending_to_deliver'):
            order_list = []
            for record in self.sudo().search([]):
                if record.amount_total > record.delivered_amount:
                    order_list.append(record.id)
            domain += [['id', 'in', order_list]]
            return super(SaleOrder, self.sudo()).search_read(domain=domain, fields=fields, offset=offset, limit=limit,
                                                             order=order)
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.depends('order_line', 'order_line.product_id', 'order_line.product_id.categ_id')
    def _compute_product_categories(self):
        for record in self:
            product_list = []
            product_categ_list = []
            if record.order_line:
                for line in record.order_line:
                    if line.product_id:
                        product_list.append(line.product_id.id)
                    if line.product_id.categ_id:
                        product_categ_list.append(line.product_id.categ_id.id)
            record.product_ids = [(6, 0, product_list)]
            record.product_categ_ids = [(6, 0, product_categ_list)]

    @api.depends('state', 'order_line.product_id', 'order_line.product_uom_qty', 'order_line.qty_delivered',
                 'order_line.net_price')
    def _compute_delivered_amount(self):
        deliverd_amount = 0
        for record in self:
            deliverd_amount = 0
            if record.state not in ('draft', 'sent'):
                for line in record.order_line:
                    deliverd_qty = line.qty_delivered * line.net_price
                    deliverd_amount += deliverd_qty
                record.delivered_amount = deliverd_amount
            else:
                record.delivered_amount = 0.0
            # if line.product_id.type == 'service' and line.is_downpayment == False:
            #     deliverd_qty = line.product_uom_qty *line.net_price
            # elif line.product_id.type =='consu' or line.product_id.type == 'product':
            #     deliverd_qty = line.qty_delivered *line.net_price

    @api.depends('pending_amount', 'order_line', 'state', 'order_line.product_id',
                 'order_line.product_uom_qty', 'order_line.qty_delivered', 'order_line.net_price',
                 'order_line.qty_invoiced')
    def _compute_remaining_funds_to_be_received(self):
        for record in self:
            advance_payment = 0.0
            if record.state not in ('draft', 'sent'):
                if record.pending_amount > 0:
                    for line in record.order_line:
                        if line.is_downpayment == True:
                            net_price = line.price_unit - ((line.price_unit * line.discount) / 100)
                            if line.qty_invoiced > 0 and net_price > 0:
                                if line.net_price:
                                    advance_payment += line.qty_invoiced * line.net_price
                                if not line.net_price:
                                    advance_payment += line.qty_invoiced * net_price
                    record.remaining_funds_to_be_received = record.pending_amount - advance_payment
                elif record.remaining_funds_to_be_received < 0:
                    record.remaining_funds_to_be_received = 0.0
                else:
                    record.remaining_funds_to_be_received = 0.0
            else:
                record.remaining_funds_to_be_received = 0.0

    @api.depends('state', 'order_line.product_id', 'order_line.product_uom_qty', 'order_line.qty_delivered',
                 'order_line.net_price')
    def _compute_pending_amount(self):
        for record in self:
            line_pending_amount = 0
            pending_amounts = 0
            if record.state not in ('draft', 'sent'):
                for line in record.order_line:
                    if line.is_downpayment == True:
                        advance_payment = line.product_uom_qty * line.net_price
                        qty = line.product_uom_qty - line.qty_delivered
                        line_pending_amount = (qty * line.net_price) - advance_payment
                    else:
                        qty = line.product_uom_qty - line.qty_delivered
                        line_pending_amount = qty * line.net_price
                    pending_amounts += line_pending_amount
                record.pending_amount = pending_amounts
            else:
                record.pending_amount = 0.0

    @api.depends('state')
    def _compute_type_name(self):
        for record in self:
            record.type_name = _('Quote Number')

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            warehouse_id = self.warehouse_id

    def action_confirm(self):
        if not self.warehouse_id:
            raise Warning(_('Please select warehouse before confirming order'))
        res = super(SaleOrder, self).action_confirm()
        return res

    # def action_confirm(self):
    #     res = super(SaleOrder, self).action_confirm()
    #     product_dict = {}
    #     installed_parts_obj = self.env['installed.parts']
    #     installed_parts_list = []
    #     if self.order_line:
    #         for line in self.order_line:
    #             if line.partner_id:
    #                 if line.product_id:
    #                     if product_dict.get(line.partner_id.id):
    #                         product_dict[line.partner_id.id].append((4,line.product_id.id))
    #                     else:
    #                         product_dict[line.partner_id.id] = [(4,line.product_id.id)]
    #                 installed_parts = installed_parts_obj.search([('partner_id', '=', line.partner_id.id), ('product_id', '=', line.product_id.id)])
    #                 if not installed_parts:
    #                     installed_parts_list.append({'partner_id': line.partner_id.id, 'product_id': line.product_id.id,
    #                                                  'installed_knife': line.product_uom_qty})
    #     if installed_parts_list:
    #         installed_parts_obj.create(installed_parts_list)
    #     if product_dict:
    #         for line in product_dict:
    #             self.env['res.partner'].browse(line).write({'product_ids':  product_dict.get(line)})
    #     return res

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if not res.dont_apply_gst:
            ord_line = self.add_gst_in_sale_order('create', res)
        return res

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        for record in self:
            if not record.dont_apply_gst:
                ord_line = record.add_gst_in_sale_order('write')
            elif record.state in ['draft', 'sent']:
                record.remove_gst_line()
        return res

    def remove_gst_line(self):
        gst_product_id = self.env['ir.config_parameter'].sudo().get_param('cortex_na.canadian_gst_product_id')
        if gst_product_id:
            so_line = self.env['sale.order.line'].search(
                [('order_id', '=', self.id), ('product_id', '=', int(gst_product_id))])
            if so_line:
                so_line.unlink()

    def add_gst_in_sale_order(self, gst_type, order={}):
        so_values = {}
        gst_product_id = self.env['ir.config_parameter'].sudo().get_param('cortex_na.canadian_gst_product_id')
        product = self.env['product.product'].search([('id', '=', int(gst_product_id))])
        if product:
            total, line_total = 0, 0
            if gst_type == 'write':
                gst = self.env['canadian.gst'].search([('state_id', '=', self.partner_id.state_id.id)])
                if gst.sale_gst:
                    for line in self.order_line:
                        if line.product_id.id != product.id:
                            line_total += line.price_subtotal

                    total = ((line_total * gst.sale_gst) / 100)
                    so_values = {
                        'name': product.name,
                        'price_unit': total,
                        'product_uom_qty': 0,
                        'order_id': self.id,
                        'discount': 0.0,
                        'product_uom': product.uom_id.id,
                        'product_id': product.id,
                        'net_price': total
                    }
                    if product.id in self.order_line.product_id.ids:
                        so_line = self.env['sale.order.line'].search(
                            [('order_id', '=', self.id), ('product_id', '=', product.id)])
                        so_line.write(so_values)
                        return so_line
                    else:
                        so_line = self.env['sale.order.line'].create(so_values)
                        return so_line
                else:
                    so_line = self.env['sale.order.line'].search(
                        [('order_id', '=', self.id), ('product_id', '=', product.id)])
                    so_line.unlink()
            elif gst_type == 'create':
                gst_create = self.env['canadian.gst'].search([('state_id', '=', order.partner_id.state_id.id)])
                if gst_create.sale_gst:
                    total = ((order.amount_total * gst_create.sale_gst) / 100)
                    so_values = {
                        'name': product.name,
                        'price_unit': total,
                        'product_uom_qty': 0,
                        'order_id': order.id,
                        'discount': 0.0,
                        'product_uom': product.uom_id.id,
                        'product_id': product.id,
                        'net_price': total
                    }
                    so_line = self.env['sale.order.line'].create(so_values)
                    return so_line
        else:
            raise UserError(_('Please set Canadian GST Product in settings.'))

    def action_add_sawmill(self):
        return {
            'name': _('Add Sawmill'),
            'type': 'ir.actions.act_window',
            'res_model': 'add.sawmill',
            'view_mode': 'form',
            'view_id': self.env.ref('cortex_na.add_sawmill_form_view').id,
            'context': {'default_sale_id': self.id},
            'target': 'new'
        }

    def cron_action_cancel_sale_order(self, order_number):
        if order_number:
            sale_order = self.env['sale.order'].search([('name', '=', order_number)])
            if sale_order:
                sale_order.write({'state': 'cancel'})

    def cron_change_saleperson(self):
        sale_order = self.env['sale.order'].search([('user_id', '=', 'John McGee')])
        gavin_carpenter = self.env['res.users'].search([('name', '=', 'Trent Carpenter')])
        if sale_order:
            for record in sale_order:
                record.write({'user_id': gavin_carpenter.id})
        customers = self.env['res.partner'].search([('user_id', '=', 'John McGee')])
        if customers:
            for record in customers:
                record.write({'user_id': gavin_carpenter.id})
        leads_obj = self.env['crm.lead'].search([('user_id', '=', 'John McGee')])
        if leads_obj:
            for record in leads_obj:
                record.write({'user_id': gavin_carpenter.id})
        return True

    def update_lines_delivered_qty(self):
        for order in self:
            for line in order.order_line:
                if line.product_id.id in [2258, 2259]:
                    line.qty_delivered_method = 'manual'


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def _default_partner_id(self):
        if self._context.get('ctx_partner_id'):
            partner = self.env['res.partner'].browse(self._context.get('ctx_partner_id'))
            return False if partner.is_distributor else self._context.get('ctx_partner_id')

    price_unit = fields.Float('Unit Price', required=True, digits='New Cortex Product Precision', default=0.0)
    product_uom_qty = fields.Float(string='Quantity', digits='New Cortex Precision', required=True, default=1)
    qty_delivered = fields.Float('Delivered Quantity', copy=False, compute='_compute_qty_delivered',
                                 inverse='_inverse_qty_delivered', compute_sudo=True, store=True,
                                 digits='New Cortex Precision', default=0)
    qty_to_invoice = fields.Float(
        compute='_get_to_invoice_qty', string='To Invoice Quantity', store=True, readonly=True,
        digits='New Cortex Precision')
    qty_invoiced = fields.Float(
        compute='_get_invoice_qty', string='Invoiced Quantity', store=True, readonly=True,
        digits='New Cortex Precision')
    net_price = fields.Float('Discounted Price', digits=dp.get_precision('Discount'))
    partner_id = fields.Many2one('res.partner', string='Sawmill', default=_default_partner_id)
    sale_cost = fields.Float(string='AVG. cost', compute='compute_sale_cost', store=True, digits='New Cortex Precision')

    @api.depends('product_uom_qty', 'qty_delivered')
    def compute_sale_cost(self):
        stock_valuation_obj = self.env['stock.valuation.layer']
        for record in self:
            sale_cost = record.product_id.running_avg_cost
            product_uom_qty = record.product_uom_qty
            qty_delivered = record.qty_delivered
            if product_uom_qty and record.product_uom:
                if record.product_uom.id != record.product_id.uom_id.id:
                    uom_factor = record.product_id.uom_id.factor * record.product_uom.factor
                    product_uom_qty = product_uom_qty / uom_factor
                    stock_valuation = stock_valuation_obj.search([('stock_move_id.sale_line_id', '=', record.id)])
                    if stock_valuation:
                        if len(stock_valuation) == 1:
                            valuation_cost = stock_valuation.unit_cost
                            qty_delivered = -stock_valuation.quantity
                        else:
                            valuation_cost = sum([s.unit_cost for s in stock_valuation]) / len(stock_valuation)
                            qty_delivered = sum([s.unit_cost for s in stock_valuation])
                        sale_cost = ((
                                                 product_uom_qty - qty_delivered) * sale_cost + qty_delivered * valuation_cost) / product_uom_qty
                else:
                    if product_uom_qty == qty_delivered:
                        stock_valuation = stock_valuation_obj.search([('stock_move_id.sale_line_id', '=', record.id)])
                        if stock_valuation:
                            if len(stock_valuation) == 1:
                                sale_cost = stock_valuation.unit_cost
                            else:
                                sale_cost = sum([s.unit_cost for s in stock_valuation]) / len(stock_valuation)
                    elif qty_delivered:
                        stock_valuation = stock_valuation_obj.search([('stock_move_id.sale_line_id', '=', record.id)])
                        if stock_valuation:
                            if len(stock_valuation) == 1:
                                valuation_cost = stock_valuation.unit_cost
                            else:
                                valuation_cost = sum([s.unit_cost for s in stock_valuation]) / len(stock_valuation)
                            sale_cost = ((
                                                     product_uom_qty - qty_delivered) * sale_cost + qty_delivered * valuation_cost) / product_uom_qty
            else:
                sale_cost = 0
            record.sale_cost = sale_cost

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'net_price')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.net_price
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.onchange('discount', 'price_unit')
    def _onchange_discount(self):
        if not self._context.get('is_discount'):
            self.net_price = self.price_unit - ((self.price_unit * self.discount) / 100)

    @api.onchange('net_price')
    def _onchange_net_price(self):
        if self.price_unit:
            self.discount = (self.price_unit - self.net_price) * 100 / self.price_unit

    def _prepare_invoice_line(self):
        data = super(SaleOrderLine, self)._prepare_invoice_line()
        data['discounted_price'] = self.net_price
        return data

    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()
        for order_line in self:
            if order_line.qty_delivered_method == 'stock_move':
                boms = order_line.move_ids.mapped('bom_line_id.bom_id')
                main_bom = boms.filtered(lambda b: b.type == 'phantom' and (b.product_id == order_line.product_id or (
                            b.product_tmpl_id == order_line.product_id.product_tmpl_id and not b.product_id)))
                if not main_bom:
                    domain = ['|', ('product_id', '=', order_line.product_id.id),
                              ('product_tmpl_id', '=', order_line.product_id.product_tmpl_id.id),
                              ('type', '=', 'phantom')]
                    bom_obj = self.env['mrp.bom'].search(domain, limit=1)
                    main_bom = bom_obj

                boms |= main_bom
                relevant_bom = boms.filtered(lambda b: b.type == 'phantom' and
                                                       (b.product_id == order_line.product_id or
                                                        (
                                                                    b.product_tmpl_id == order_line.product_id.product_tmpl_id and not b.product_id)))
                if relevant_bom:
                    # In case of dropship, we use a 'all or nothing' policy since 'bom_line_id' was
                    # not written on a move coming from a PO.
                    # FIXME: if the components of a kit have different suppliers, multiple PO
                    # are generated. If one PO is confirmed and all the others are in draft, receiving
                    # the products for this PO will set the qty_delivered. We might need to check the
                    # state of all PO as well... but sale_mrp doesn't depend on purchase.
                    moves = order_line.move_ids.filtered(lambda m: m.state == 'done' and not m.scrapped)
                    filters = {
                        'incoming_moves': lambda m: m.location_dest_id.usage == 'customer' and (
                                    not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund)),
                        'outgoing_moves': lambda m: m.location_dest_id.usage != 'customer' and m.to_refund
                    }
                    order_qty = order_line.product_uom._compute_quantity(order_line.product_uom_qty,
                                                                         relevant_bom.product_uom_id)
                    order_line.qty_delivered = moves._compute_kit_quantities(order_line.product_id, order_qty,
                                                                             relevant_bom, filters)


class SaleOrderOption(models.Model):
    _inherit = "sale.order.option"

    quantity = fields.Float('Quantity', required=True, digits='New Cortex Precision', default=1)
