# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from collections import defaultdict
from itertools import groupby
from datetime import datetime as dt
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools import date_utils, float_round, float_is_zero
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class MrpProduction(models.Model):
    """ Manufacturing Orders """
    _inherit = 'mrp.production'

    product_qty = fields.Float(
        'Quantity To Produce',
        default=1.0, digits='New Cortex Precision',
        readonly=True, required=True, tracking=True,
        states={'draft': [('readonly', False)]})
    service_charge_ids = fields.One2many('service.charge', 'production_id', 'Service Charges', copy=True)
    service_charge_total = fields.Float(string='Service Charges Total', compute='compute_charge_total')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company.currency_id)
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True, states={'draft': [('readonly', False)]})
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', copy=False)
    product_uom_qty = fields.Float(string='Total Quantity', compute='_compute_product_uom_qty', store=True, digits='Product Unit of Measure')
    batch_production_id = fields.Many2one('batch.production', string='Batch Production', copy=False)
    code = fields.Selection([('incoming', 'Receipt'), ('outgoing', 'Delivery'), ('internal', 'Internal Transfer')], 'Type of Operation', related='picking_type_id.code', store=True,)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', ondelete='cascade',check_company=True, related='picking_type_id.warehouse_id', store=True,)
    sale_order_ids = fields.Many2many('sale.order', string='Sale Orders')
    sale_order_count = fields.Integer(compute='_compute_sale_order_count', string='Sale Order')

    @api.onchange('product_id','partner_id')
    def _onchange_product_and_vendor_id(self):
        if self.product_id and self.partner_id:
            product_vendor_obj = self.env['product.with.vendor'].search([('product_template_id','=',self.product_id.product_tmpl_id.id),('partner_id','=',self.partner_id.id)],limit=1)
            if product_vendor_obj:
                self.bom_id = product_vendor_obj.bom_id.id
            else: 
                self.bom_id = False


    @api.onchange('product_id', 'picking_type_id', 'company_id')
    def onchange_product_id(self):
        """ Finds UoM of changed product. """
        if not self.product_id:
            self.bom_id = False
        elif self.product_id and self.partner_id:
            product_vendor_obj = self.env['product.with.vendor'].search([('product_template_id','=',self.product_id.product_tmpl_id.id),('partner_id','=',self.partner_id.id)],limit=1)
            if product_vendor_obj:
                self.bom_id = product_vendor_obj.bom_id.id            
        else:
            bom = self.env['mrp.bom']._bom_find(product=self.product_id, picking_type=self.picking_type_id, company_id=self.company_id.id, bom_type='normal')
            if bom:
                self.bom_id = bom.id
                self.product_qty = self.bom_id.product_qty
                self.product_uom_id = self.bom_id.product_uom_id.id
            else:
                self.bom_id = False
                self.product_uom_id = self.product_id.uom_id.id
            return {'domain': {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}}           


    @api.depends('service_charge_ids','service_charge_ids.subtotal')
    def compute_charge_total(self):
        for record in self:
            total = 0
            for line in record.service_charge_ids:
                total += line.subtotal
            record.service_charge_total = total

    def action_open_sale_orders(self):
        sale_obj = self.env['sale.order'].search([('id', '=',self.sale_order_ids.ids)])
        sale_ids = []
        view_id = self.env.ref('sale.view_order_form').id
        for each in sale_obj:
            sale_ids.append(each.id)
        if len(sale_ids) <= 1:
            return {
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': view_id,
                'name': _('Sale Orders'),
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'domain': [('id', '=', self.sale_order_ids.ids)],
                'res_id': sale_ids and sale_ids[0]
            }
        else:
            return {
                'name': _('Sale Orders'),
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'domain': [('id', '=', self.sale_order_ids.ids)],
            }

    def _compute_sale_order_count(self):
            sale_order = self.env['sale.order'].search([('id', '=', self.sale_order_ids.ids)])
            self.sale_order_count = len(sale_order)

    @api.onchange('bom_id')
    def _onchange_bom(self):
        charge_list = [(2, move.id) for move in self.service_charge_ids.filtered(lambda m: m.bom_line_id)]
        if self.bom_id:
            for record in self.bom_id.service_charge_ids:
                charge_list.append([0, 0, {'product_id': record.product_id.id,
                                           'quantity': record.quantity,
                                           'price_unit': record.price_unit,
                                           'subtotal': record.quantity * record.price_unit,
                                           'product_uom_id': record.product_uom_id.id,
                                           'bom_line_id': self.bom_id.id,
                                           'bom_charge_id': record.id,
                                           'production_id': self.id,
                                           'batch_production_id': self.batch_production_id.id
                                        }])
        self.service_charge_ids = charge_list

    @api.onchange('product_qty', 'product_uom_id')
    def _onchange_service_charges(self):
        if self.bom_id and self.product_qty > 0:
            for move in self.service_charge_ids.filtered(lambda m: m.bom_line_id):
                factor = 1
                if move.product_uom_id.id != self.product_uom_id.id:
                    factor = self.product_uom_id._compute_quantity(self.product_qty,
                                                                         self.bom_id.product_uom_id) / (self.bom_id.product_qty or 1)
                quantity = factor
                if move.bom_charge_id:
                    if factor > 1:
                        factor = factor / (self.product_qty or 1)
                    quantity = (self.product_qty * move.bom_charge_id.quantity) * factor
                move.quantity = quantity
                move.onchange_price_quantity()
        else:
            self.service_charge_ids = [(2, move.id) for move in self.service_charge_ids.filtered(lambda m: m.bom_line_id)]

    def _cal_price(self, consumed_moves):
        """Set a price unit on the finished move according to `consumed_moves`.
        """
        self.ensure_one()
        work_center_cost = 0
        if self.currency_id and self.currency_id.id != self.company_id.currency_id.id:
            service_charge_cost = self.service_charge_total * self.company_id.currency_id.rate / (self.currency_id.rate if self.currency_id.rate else 1)
        else:
            service_charge_cost = self.service_charge_total
        bom_id = self.bom_id
        product_dict = {}
        if bom_id:
            product_id = bom_id.product_tmpl_id.product_variant_id.id
            product_dict[product_id] = bom_id.charges_per
            for byproduct in bom_id.byproduct_ids:
                product_dict[byproduct.product_id.id] = byproduct.charges_per
        finished_move = self.move_finished_ids.filtered(lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity_done > 0)
        if finished_move:
            finished_move.ensure_one()
            for work_order in self.workorder_ids:
                time_lines = work_order.time_ids.filtered(lambda x: x.date_end and not x.cost_already_recorded)
                duration = sum(time_lines.mapped('duration'))
                time_lines.write({'cost_already_recorded': True})
                work_center_cost += (duration / 60.0) * work_order.workcenter_id.costs_hour
            if finished_move.product_id.cost_method in ('fifo', 'average'):
                qty_done = finished_move.product_uom._compute_quantity(finished_move.quantity_done, finished_move.product_id.uom_id)
                extra_cost = self.extra_cost * qty_done
                price_unit = (sum([-m.stock_valuation_layer_ids.value for m in consumed_moves]) + work_center_cost + extra_cost + service_charge_cost) / qty_done
                finished_move.price_unit = price_unit * product_dict.get(self.product_id.id) / 100
                finished_move.charges_per = product_dict.get(self.product_id.id)

        byproduct_move = self.move_finished_ids.filtered(
            lambda x: x.product_id != self.product_id and x.state not in ('done', 'cancel') and x.quantity_done > 0)
        for move in byproduct_move:
            if move.product_id.cost_method in ('fifo', 'average'):
                if product_dict.get(move.product_id.id):
                    qty_done = move.product_uom._compute_quantity(move.quantity_done,
                                                                move.product_id.uom_id)
                    price_unit = (sum([-m.stock_valuation_layer_ids.value for m in
                                       consumed_moves]) + work_center_cost + service_charge_cost) / qty_done
                    move.price_unit = price_unit * product_dict.get(move.product_id.id) / 100
                    move.charges_per = product_dict.get(move.product_id.id)
                else:
                    move.price_unit = 0
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                
        return True

    def create_purchase_order(self):
        vendor_obj = self.partner_id
        if vendor_obj:
            order_list = []
            for line in self.service_charge_ids:
                product = line.product_id
                product_lang = product.with_context(
                    lang=vendor_obj.lang,
                    partner_id=vendor_obj.id,
                )
                name = product_lang.display_name
                if product_lang.description_purchase:
                    name += '\n' + product_lang.description_purchase
                order_list.append([0,0, {'product_id': product.id,
                                         'name': name,
                                         'product_qty': line.quantity,
                                         'product_uom': line.product_uom_id.id,
                                         'date_planned': dt.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                         'price_unit': line.price_unit,
                                         'currency_id': line.currency_id.id}])

            po_dict = {
                'partner_id': vendor_obj.id,
                # 'date_order': fields.Datetime.now,
                'order_line': order_list,
                'currency_id': self.currency_id.id
            }
            self.purchase_order_id = self.env['purchase.order'].with_context({'create_po':1}).create(po_dict).id
        else:
            raise UserError(_('Please select Vendor'))

    # @api.onchange('purchase_order_id')
    # def onchange_purchase_order(self):
    #     if self.purchase_order_id:
    #         item_list = [[5,0]]
    #         for line in self.purchase_order_id.order_line:
    #             if line.product_id.id in self.product_id.service_products.ids:
    #                 item_list.append([0, 0, {'product_id': line.product_id.id,
    #                                     'quantity': line.product_qty,
    #                                     'product_uom_id': line.product_uom.id,
    #                                     'price_unit': line.price_unit,
    #                                     'subtotal': line.product_qty * line.price_unit,
    #                                     'currency_id': line.currency_id.id,
    #                                     'production_id': self.id,
    #                                     'batch_production_id': self.batch_production_id.id}])
    #         self.update({'service_charge_ids': item_list, 'partner_id': self.purchase_order_id.partner_id.id,
    #                      'currency_id': self.purchase_order_id.currency_id.id})
    
    @api.onchange('partner_id')
    def oncahnge_partner_id(self):
        if self.partner_id and self.purchase_order_id:
            if self.partner_id != self.purchase_order_id.partner_id:
                self.purchase_order_id = None

    def button_mark_done(self):
        res = super(MrpProduction, self).button_mark_done()
        message_obj = self.env['mail.message']
        if self.purchase_order_id:
            for line in self.purchase_order_id.order_line:
                total_quantity = 0.00
                for service in self.service_charge_ids:
                    if line.product_id.id == service.product_id.id:
                        total_quantity = line.qty_received + service.quantity
                        line.update({'qty_received':total_quantity})
                        msg_values = {
                            'record_name': self.purchase_order_id.name,
                            'model': 'purchase.order',
                            'res_id': self.purchase_order_id.id,
                            'message_type': 'comment',
                            'body': 'Manufacturing Order ' + self.name + ' has received quantity ' + str(service.quantity) + ' for product ' + line.product_id.name
                        }
                        message_obj.create(msg_values)


class MrpUnbuild(models.Model):
    _inherit = "mrp.unbuild"

    product_qty = fields.Float(
        'Quantity', default=1.0,digits='New Cortex Precision',
        required=True, states={'done': [('readonly', True)]})


