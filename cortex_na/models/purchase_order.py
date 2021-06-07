# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError
import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons import decimal_precision as dp

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    qty_received_total = fields.Float(compute='_compute_qty_remaining_received_total', string='Product to be Received',
                                          store=True,digits='New Cortex Precision')
    qty_billed_total = fields.Float(compute='_compute_qty_remaining_billed_total', string='Unbilled',
                                        store=True,digits='New Cortex Precision')
    payment_ids = fields.One2many('account.payment', 'purchase_order_id', string='Account Payment')
    payment_count = fields.Integer(compute='_compute_account_payment_count', string='Purchase Order')
    advance_payment = fields.Float(string='Advance Payment', compute='_compute_advance_payment', store=True)
    remaining_amount = fields.Float(string='Unpaid Balance', compute='_compute_remaining_amount', store=True)
    # delivery_date = fields.Date(string='Estimated Delivery Date', track_visibility='onchange')
    select_sale_order_ids = fields.Many2many('sale.order', string='Sale Orders')
    expected_date = fields.Date(string='Expected Date',default=fields.Date.today ,track_visibility='onchange')
    show_in_cash_flow = fields.Boolean(string='Show in Cash FLow')

    @api.onchange('payment_term_id')
    def onchange_payment_term_id(self):
        today = datetime.date.today().strftime('%Y-%m-%d')
        exp_date = self.expected_date.strftime('%Y-%m-%d')
        inv_date =  today
        inv_date = datetime.datetime.strptime(inv_date, "%Y-%m-%d")
        if self.payment_term_id:
            payment_obj = self.env['account.payment.term.line'].search([('payment_id','=',self.payment_term_id.id)])
            total_days = 0
            for record in payment_obj:
                total_days += record.days
            self.expected_date = (inv_date + datetime.timedelta(total_days)).strftime("%Y-%m-%d")
        else:
            self.expected_date = (inv_date + datetime.timedelta(0)).strftime("%Y-%m-%d")



    @api.depends('advance_payment', 'amount_total', 'invoice_status')
    def _compute_remaining_amount(self):
        for record in self:
            record.remaining_amount = record.amount_total - record.advance_payment if record.invoice_status != 'invoiced' else 0

    @api.depends('payment_ids','payment_ids.amount')
    def _compute_advance_payment(self):
        for record in self:
            total_amount = 0
            if record.payment_ids:
                for line in record.payment_ids:
                    total_amount += line.amount
            record.advance_payment = total_amount

    @api.depends('payment_ids')
    def _compute_account_payment_count(self):
        for order in self:
            order.payment_count = len(order.payment_ids)

    def action_view_advance_payment(self):
        action = self.env.ref('account.action_account_payments_payable').read()[0]
        advance_payment = self.mapped('payment_ids')
        if len(advance_payment) > 1:
            action['domain'] = [('id', 'in', advance_payment.ids)]
        elif advance_payment:
            form_view = [(self.env.ref('account.view_account_payment_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = advance_payment.id
        return action

    @api.depends('order_line.qty_rem_received')
    def _compute_qty_remaining_received_total(self):
        for record in self:
            qty_received_total = 0
            if record.order_line:
                for line in record.order_line:
                    qty_received_total += line.qty_rem_received
            record.qty_received_total = qty_received_total

    @api.depends('order_line.qty_rem_billed')
    def _compute_qty_remaining_billed_total(self):
        for record in self:
            qty_billed_total = 0
            if record.order_line:
                for line in record.order_line:
                    qty_billed_total += line.qty_rem_billed
            record.qty_billed_total = qty_billed_total

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if self._context.get('partner_id'):
            args += [('partner_id', '=', self._context.get('partner_id'))]
        return super(PurchaseOrder, self).name_search(name=name, args=args, operator=operator, limit=limit)

    def action_advance_payment(self):
        ctx = dict(
            default_partner_id=self.partner_id.id,
            default_purchase_order_id=self.id,
            default_payment_type='outbound',
            default_partner_type='supplier',
            default_communication=self.name,
            default_currency_id = self.currency_id.id
        )
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment',
            'view_mode': 'form',
            'view_id': self.env.ref('cortex_na.view_account_payment_invoice_form_custom').id,
            'context': ctx,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    @api.model
    def create(self,vals):
        res = super(PurchaseOrder, self).create(vals)
        ord_line = self.add_gst_in_purchase_order('create',res)
        return res

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        ord_line = self.add_gst_in_purchase_order('write')
        return res
    
    def add_gst_in_purchase_order(self,gst_type,order = {}):
        po_values = {}
        gst_product_id = self.env['ir.config_parameter'].sudo().get_param('cortex_na.canadian_gst_product_id')
        product =  self.env['product.product'].search([('id', '=',int(gst_product_id))])
        if product:
            total,line_total = 0,0
            if gst_type == 'write':
                gst = self.env['canadian.gst'].search([('state_id','=',self.partner_id.state_id.id)])
                if gst.purchase_gst:
                    for line in self.order_line:
                        if line.product_id.id != product.id:
                            line_total +=line.price_subtotal

                    total = ((line_total * gst.purchase_gst)/100)
                    po_values = {
                        'product_id': product.id,
                        'name':product.name,
                        'price_unit': total,
                        'product_qty':1,
                        'product_uom_qty':1,
                        'order_id': self.id,
                        'product_uom': product.uom_id.id
                    }
                    if product.id in self.order_line.product_id.ids:
                        po_line = self.env['purchase.order.line'].search([('order_id','=',self.id),('product_id','=',product.id)])
                        po_line.write(po_values)
                        return po_line
                    else:
                        po_values['date_planned'] = datetime.datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        po_line = self.env['purchase.order.line'].create(po_values)
                        return po_line
                else:
                    po_line = self.env['purchase.order.line'].search([('order_id','=',self.id),('product_id','=',product.id)])
                    po_line.unlink()
            elif gst_type == 'create':
                gst_create = self.env['canadian.gst'].search([('state_id','=',order.partner_id.state_id.id)])
                if gst_create.purchase_gst:
                    po_values = {
                        'product_id': product.id,
                        'name':product.name,
                        'price_unit': ((order.amount_total * gst_create.purchase_gst)/100),
                        'product_qty':1,
                        'product_uom_qty':1,
                        'order_id': order.id,
                        'product_uom': product.uom_id.id,
                        'date_planned': datetime.datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    }
                    po_line = self.env['purchase.order.line'].create(po_values)
                    return po_line
        else:
            raise UserError(_('Please set Canadian GST Product in settings.'))


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    price_unit = fields.Float(string='Unit Price', required=True, digits='New Cortex Product Precision', default=0.0)
    qty_received = fields.Float("Received Qty", compute='_compute_qty_received', inverse='_inverse_qty_received',
                                compute_sudo=True, store=True, digits='New Cortex Precision')
    qty_invoiced = fields.Float(compute='_compute_qty_invoiced', string="Billed Qty", digits='New Cortex Precision',
                                store=True)
    product_qty = fields.Float(string='Quantity', digits='New Cortex Precision', required=True)
    qty_rem_received = fields.Float(compute='_compute_qty_remaining_received', string='Product to be Received',digits='New Cortex Precision', store=True)
    qty_rem_billed = fields.Float(compute='_compute_qty_remaining_billed', string='Unbilled', store=True,digits='New Cortex Precision')
    drawing_no = fields.Char('Drawing #')

    @api.depends('product_qty', 'qty_received', 'price_unit', 'product_id')
    def _compute_qty_remaining_received(self):
        for line in self:
             line.qty_rem_received = ((line.product_qty - line.qty_received) * line.price_unit)

    @api.depends('product_qty', 'qty_invoiced', 'price_unit')
    def _compute_qty_remaining_billed(self):
        for line in self:
            line.qty_rem_billed = ((line.product_qty - line.qty_invoiced) * line.price_unit)

    @api.onchange('product_id')
    def _onchange_products(self):
        if self.product_id.drawing_version:
            self.drawing_no = (self.product_id.drawing_no or '') + ' - ' + self.product_id.drawing_version.upper()
        else:
            self.drawing_no = self.product_id.drawing_no

    def _create_or_update_picking(self):
        for line in self:
            if line.product_id and line.product_id.type in ('product', 'consu'):
                # Prevent decreasing below received quantity
                if float_compare(line.product_qty, line.qty_received, line.product_uom.rounding) < 0:
                    raise UserError(_('You cannot decrease the ordered quantity below the received quantity.\n'
                                      'Create a return first.'))

                if float_compare(line.product_qty, line.qty_invoiced, line.product_uom.rounding) == -1:
                    # If the quantity is now below the invoiced quantity, create an activity on the vendor bill
                    # inviting the user to create a refund.
                    activity = self.env['mail.activity'].sudo().create({
                        'activity_type_id': self.env.ref('mail.mail_activity_data_warning').id,
                        'note': _(
                            'The quantities on your purchase order indicate less than billed. You should ask for a refund. '),
                        'res_id': line.invoice_lines[0].move_id.id,
                        'res_model_id': self.env.ref('account.model_account_move').id,
                    })
                    activity._onchange_activity_type_id()

                # If the user increased quantity of existing line or created a new line
                pickings = line.order_id.picking_ids.filtered(
                    lambda x: x.state not in ('done', 'cancel') and x.location_dest_id.usage in ('internal', 'transit'))
                picking = pickings and pickings[0] or False
                if not picking:
                    res = line.order_id._prepare_picking()
                    picking = self.env['stock.picking'].create(res)
                move_vals = line._prepare_stock_moves(picking)
                for move_val in move_vals:
                    self.env['stock.move'] \
                        .create(move_val) \
                        ._action_confirm() \
                        ._action_assign()


