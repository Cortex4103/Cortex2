# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OpenWizard(models.TransientModel):
    _name = 'open.wizard'
    _inherit = 'batch.production'
    _description = 'Open Wizard for destination location'

    company_id = fields.Many2one('res.company', string='Company')
    location_dest_id = fields.Many2one('stock.location', "Destination Location",required=True)
    
    def action_add_transfer_order(self):
        if self.location_dest_id:
            tfm_list = {}
            tfm_data = self.env['batch.production'].browse(self._context.get('active_id'))
            tfm_list['picking_type_id'] = tfm_data.picking_type_id.warehouse_id.int_type_id.id
            tfm_list['location_id'] = tfm_data.picking_type_id.default_location_src_id.id
            tfm_list['location_dest_id'] = self.location_dest_id.id
            tfm_list['move_type'] = "direct"
            tfm_list['is_locked'] = "true"
            tfm_list['immediate_transfer'] = "true"
            tfm_list['batch_id'] = tfm_data.id
            if tfm_data.batch_detail_ids:
                lists = []
                # Get MRP Production obj of current Batch production
                mo_objects = self.env['mrp.production'].search([('batch_production_id', '=', tfm_data.id)])
                for line in tfm_data.batch_detail_ids:
                    product_id = line.product_id
                    if mo_objects and product_id.tracking != 'none':
                        # Get MRP Object of batch product
                        mrp_obj = mo_objects.filtered(lambda m: m.product_id == product_id)
                        if mrp_obj:
                            # Finished move line to get Lot of MRP product
                            for obj in mrp_obj[0].finished_move_line_ids.filtered(lambda l: l.product_id == product_id):
                                lists.append((0, 0, {
                                    'product_id': product_id.id,
                                    'qty_done': obj.qty_done,
                                    'product_uom_id': product_id.uom_id.id,
                                    'location_id': tfm_data.picking_type_id.default_location_src_id.id,
                                    'location_dest_id': self.location_dest_id.id,
                                    'lot_id': obj.lot_id.id
                                }))
                        else:
                            lists.append((0, 0, {
                                'product_id': product_id.id,
                                'qty_done': line.quantity,
                                'product_uom_id': product_id.uom_id.id,
                                'location_id': tfm_data.picking_type_id.default_location_src_id.id,
                                'location_dest_id': self.location_dest_id.id
                            }))
                    else:
                        lists.append((0, 0, {
                            'product_id': product_id.id,
                            'qty_done': line.quantity,
                            'product_uom_id': product_id.uom_id.id,
                            'location_id': tfm_data.picking_type_id.default_location_src_id.id,
                            'location_dest_id': self.location_dest_id.id
                        }))
                tfm_list['move_line_ids_without_package'] = lists
                mo_obj = self.env['stock.picking'].create(tfm_list)
        if mo_obj:
            return {
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id':mo_obj.id,
                'domain': [('batch_id', '=', tfm_data.id)],
            }

class BatchProduction(models.Model):
    _inherit = 'stock.picking'

    batch_id = fields.Char('Batch No')