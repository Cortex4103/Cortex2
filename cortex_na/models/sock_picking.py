# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from werkzeug.urls import url_encode
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ['stock.picking','portal.mixin']

    sales_count = fields.Integer(compute='_compute_sale_count', string='Sale Order')
    purchase_count = fields.Integer(compute='_compute_purchase_count', string='Purchase Order')
    external_tracking_reference = fields.Char(string='External Tracking Reference')
    shipping_charge = fields.Monetary(string='Shipping Charge')
    currency_id = fields.Many2one('res.currency')

    def write(self, vals):
        res=super(StockPicking, self).write(vals)
        if vals.get('scheduled_date') and self.picking_type_code == 'outgoing':
            delivery_id = self.search([('origin','=',self.origin)])
            max_id = max(delivery_id)
            sale_order = self.env['sale.order'].search([('name','=',max_id.origin)])
            if sale_order:
                sale_order.commitment_date = max_id.scheduled_date
        if vals.get('shipping_charge') and self.picking_type_code == 'outgoing':
            sale_order = self.env['sale.order'].search([('name', '=',self.origin)])
            if sale_order:
                self.currency_id =sale_order.currency_id.id

        return res

    def copy(self, default=None):
        if self.picking_type_id.code in ['outgoing','incoming'] and (not self._context.get('allowed_copy')):
            raise UserError(_('Cannot duplicate delivery and receipts!'))
        else:
            res = super(StockPicking, self).copy(default)
            return res

    @api.model
    def create(self, vals):
        res = super(StockPicking, self).create(vals)
        if res.scheduled_date and res.picking_type_code == 'outgoing':
            sale_order = self.env['sale.order'].search([('name', '=', res.origin)])
            if sale_order:
                sale_order.commitment_date = res.scheduled_date
        return res

    def unlink(self):
        if not self._context.get('allow_unlink'):
            raise UserError(_('You cannot delete Delivery / Receipt.'))
        return super(StockPicking, self).unlink()

    def action_view_sale_order(self):
        action = self.env.ref('sale.action_orders').read()[0]
        action['domain'] = [('id', '=', self.group_id.sale_id.id)]
        action['views'] = [(False, 'form')]
        action['res_id'] = self.group_id.sale_id.id
        return action

    @api.depends('group_id', 'group_id.sale_id')
    def _compute_sale_count(self):
        for order in self:
            sale_order = self.env['sale.order'].search([('id', '=', order.group_id.sale_id.id)])
            order.sales_count = len(sale_order)


    def action_view_purchase_order(self):
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        action['domain'] = [('id', '=', self.purchase_id.id)]
        action['views'] = [(False, 'form')]
        action['res_id'] = self.purchase_id.id
        return action

    @api.depends('purchase_id')
    def _compute_purchase_count(self):
        for order in self:
            purchase_order = self.env['purchase.order'].search([('id', '=', order.purchase_id.id)])
            order.purchase_count = len(purchase_order)


    def action_add_to_order(self):
        list_order_details = []
        if self.shipping_charge:
            is_product_id = self.env['ir.config_parameter'].sudo().get_param('cortex_na.product_id')
            if is_product_id:
                shipping_charge_total = 0
                if self.shipping_charge > 15:
                    shipping_charge_total = self.shipping_charge * 1.15
                else:
                    shipping_charge_total = 15

                list_order_details.append([0, 0, {'product_id': int(is_product_id),
                                                 'product_uom_qty': 1,
                                                  'price_unit':shipping_charge_total,

                                                      }])

                sale_order = self.env['sale.order'].search([('name', '=', self.origin)])
                sale_order.write({'order_line': list_order_details})
            else:
                raise UserError(_('Please set DO Service Product.'))
        return True

    def action_add_sawmill(self):
        return {
            'name': _('Add Sawmill'),
            'type': 'ir.actions.act_window',
            'res_model': 'add.sawmill',
            'view_mode': 'form',
            'view_id': self.env.ref('cortex_na.add_sawmill_form_view').id,
            'context': {'default_stock_picking_id': self.id},
            'target': 'new'
        }

    def set_from_qty_in_stock_move_lines(self):
        for data in self.move_line_ids:
            source_quant = self.env['stock.quant'].search(
                [('location_id', '=', data.location_id.id), ('product_id', '=', data.product_id.id),
                 ('lot_id', '=', data.lot_id.id)], order='id desc', limit=1)
            dest_quant = data.env['stock.quant'].search(
                [('location_id', '=', data.location_dest_id.id), ('product_id', '=', data.product_id.id),
                 ('lot_id', '=', data.lot_id.id)], order='id desc', limit=1)
            data.qty_from = source_quant.quantity
            data.qty_to = dest_quant.quantity
            data.quantity_set = True
            data.quantity_set_dest = True

    def action_done(self):
        res = super(StockPicking,self).action_done()
        self.set_from_qty_in_stock_move_lines()
        return res

    def send_confirmation_email_method(self):
        ''' Opens a wizard to compose an email, with relevant mail template loaded by default '''
        self.ensure_one()
        if self.env.context.get('email_configuration'):
            ir_model_data = self.env['ir.model.data']
            delivery_template_id = self.company_id.stock_mail_confirmation_template_id.id
            lang = self.env.context.get('lang')
            template = self.env['mail.template'].browse(delivery_template_id)
            try:
                compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False
            if template.lang:
                lang = template._render_template(template.lang, 'stock.picking', self.ids[0])
            ctx = {
                'default_model': 'stock.picking',
                'active_model': 'stock.picking',
                'active_id': self.ids[0],
                'default_res_id': self.ids[0],
                'default_use_template': bool(delivery_template_id),
                'default_template_id': delivery_template_id,
                'default_composition_mode': 'comment',
                'custom_layout': "mail.mail_notification_paynow",
                'force_email': True,
                'model_description': self.with_context(lang=lang),
            }
            return {
                'name': _('Compose Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form_id, 'form')],
                'view_id': compose_form_id,
                'target': 'new',
                'context': ctx,                
            }
            
    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        installed_parts_list = []
        if self.move_line_ids_without_package:
            for line in self.move_line_ids_without_package:
                if line.product_id.id not in line.install_part_id.installed_part_detail_id.mapped('product_id').ids:
                    line.install_part_id.write({'installed_part_detail_id':[[0, 0, {'product_id':line.product_id.id,
                                                        'installed_knife':line.installed_part
                                                          }]]})

        return res

    def action_generate_backorder_wizard(self):
        wiz = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, p.id) for p in self]})
        wiz.process()
        return {}

    def _create_backorder(self):
        backorders = super(StockPicking, self)._create_backorder()
        if backorders:
            backorders.do_unreserve()
        return backorders