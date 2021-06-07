# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, tools, _
from odoo.osv import expression
from odoo.tools.float_utils import float_round


class StockMove(models.Model):
    _inherit = 'stock.move'

    charges_per = fields.Float(string='Charges %',digits='New Cortex Precision')

    def _action_confirm(self, merge=False, merge_into=False):
        """
        This method override for BOM kit calculation works proper in delivery,
        we remove the merge functionality for it.
        """
        return super(StockMove, self)._action_confirm(merge=merge, merge_into=merge_into)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _default_partner_id(self):
        partner_id = self.picking_id.partner_id.id
        return partner_id


    product_qty = fields.Float(
        'Real Reserved Quantity', digits='Product Unit of Measure',
        compute='_compute_product_qty', inverse='_set_product_qty', store=True)
    installed_part = fields.Float(string='Installed Part')
    partner_id = fields.Many2one('res.partner', string='Sawmill',default=_default_partner_id)
    qty_from = fields.Float("From Qty" ,digits='New Cortex Precision')
    qty_to = fields.Float("To Qty",digits='New Cortex Precision')
    quantity_set = fields.Boolean("Source Quantity Updated?")
    quantity_set_dest = fields.Boolean("Destination Quantity Updated?")

    def search_quant_and_move(self):
        move = self.env['stock.move'].search([('state','=','done')])
        quant = self.env['stock.quant'].search([])
        line = self.env['stock.move.line'].search([('state','=','done')])
        vals = {
            'move':move.ids,
            'quant':quant.ids,
            'line':line.ids
        }
        return vals

    def iter_move_lines(self,product_id,from_date,location,lot_id):
        move_qty = 0
        stock_move = self.env['stock.move.line'].browse(self.search_quant_and_move().get('line'))
        for move in stock_move:
            if move.product_id.id == product_id and move.location_id.id == location and move.date <= from_date \
                    and move.lot_id.id == lot_id:
                move_qty += move.qty_done
        return move_qty

    def iter_move_lines_dest(self,product_id,from_date,location,lot_id):
        move_qty = 0
        stock_move = self.env['stock.move.line'].browse(self.search_quant_and_move().get('line'))
        for move in stock_move:
            if move.product_id.id == product_id and move.location_dest_id.id == location and move.date <= from_date \
                    and move.lot_id.id == lot_id:
                move_qty += move.qty_done
        return move_qty

    #cron job to update from qty in stock move line
    def set_stock_move_line_source_loc_qty(self):
        for data in self.search([('state','=','done'),('quantity_set','=',False)]):
            iter_move_lines = data.iter_move_lines(data.product_id.id,data.date,data.location_id.id,data.lot_id.id)
            iter_move_lines_dest = data.iter_move_lines_dest(data.product_id.id,data.date,data.location_id.id,data.lot_id.id)
            data.qty_from = iter_move_lines_dest  - iter_move_lines
            data.quantity_set = True
            data._cr.commit()

    # cron job to update to qty in stock move line
    def set_stock_move_lines_dest_loc_qty(self):
        for data in self.search([('state','=','done'),('quantity_set_dest','=',False)]):
            iter_move_lines = data.iter_move_lines(data.product_id.id, data.date, data.location_dest_id.id, data.lot_id.id)
            iter_move_lines_dest = data.iter_move_lines_dest(data.product_id.id,data.date,data.location_dest_id.id,data.lot_id.id)
            data.qty_to = iter_move_lines_dest - iter_move_lines
            data.quantity_set_dest = True
            data._cr.commit()

    # cron job to mark old technical booleans false
    def fix_wrong_qty_values(self):
        for data in self.search([]):
            data.quantity_set_dest = False
            data.quantity_set = False
            data._cr.commit()

    install_part_id = fields.Many2one('installed.part', string='Machine Center')


    @api.onchange('install_part_id')
    def onchange_install_part_id(self):
        if self.install_part_id:
            part = self.env['installed.part.detail'].search([('product_id','=',self.product_id.id),('install_part_id','=',self.install_part_id.id)])
            if part:
                self.write({'installed_part':part.installed_knife})




