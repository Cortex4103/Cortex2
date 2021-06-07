# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class AddSawmill(models.TransientModel):
    _name = 'add.sawmill'
    _description = 'Add Sawmill'

    apply_on = fields.Selection([('all','All order line'), ('empty', 'Emplty Sawmill')], default='empty', string='Apply on')
    partner_id = fields.Many2one('res.partner', string='Sawmill')
    # sale_id = fields.Many2one('sale.order', string='Sale Order')
    stock_picking_id = fields.Many2one('stock.picking',string='Transfer')

    def action_add_sawmill(self):
        if self.stock_picking_id and self.stock_picking_id.move_line_ids_without_package:
            if self.apply_on == 'all':
                self.stock_picking_id.move_line_ids_without_package.write({'partner_id': self.partner_id.id})
            else:
                order_obj = self.stock_picking_id.move_line_ids_without_package.filtered(lambda r: not r.partner_id)
                order_obj.write({'partner_id': self.partner_id.id})
