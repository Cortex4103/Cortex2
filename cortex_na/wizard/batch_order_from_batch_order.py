# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning

class BatchOrder(models.TransientModel):
    _name = 'batch.order'
    _description = 'Open Wizard for Create Batch Order from Batch Order'

    partner_id = fields.Many2one('res.partner', string='Vendor', tracking=True)
    mrp_type = fields.Selection([('conversion', 'Conversion')], string='Manufacturing Type', default='conversion', tracking=True)
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type', domain="[('code', '=', 'mrp_operation')]")
    batch_detail_ids = fields.One2many('batch.order.lines', 'batch_id', 'Batch Detail', copy=True)
    
    def action_add_batch_order(self):
        print(self.batch_detail_ids)
        batch_order = []
        for batch_line in self.batch_detail_ids:
            if batch_line.product_id.id == False:
                raise Warning(_("Please Select Product for Batch Details"))
            else:
                batch_order.append([0,0,{
                            'product_id':batch_line.product_id.id,
                            'bom_id':batch_line.bom_id.id,
                            'quantity': batch_line.quantity,
                            'p_length':batch_line.p_length,
                            'input_product_id':batch_line.input_product_id.id
                        }])
        vals={
            'partner_id':self.partner_id.id,
            'mrp_type':self.mrp_type,
            'picking_type_id':self.picking_type_id.id,
            'batch_detail_ids':batch_order
        }
        batch_id = self.env['batch.production'].create(vals)
        if batch_id:
            return {
                'res_model': 'batch.production',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id':batch_id.id
            }

class BatchOrderLine(models.TransientModel):
    _name = 'batch.order.lines'

    product_id = fields.Many2one('product.product', string='Product', required=False)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Material', copy=True , required=False)
    p_length = fields.Float(string='Length', copy=True)
    quantity = fields.Float(string='Quantity')
    batch_id = fields.Many2one('batch.order',ondelete="cascade")
    batch_production_id = fields.Many2one('batch.production', string='Batch Production')
    input_product_id = fields.Many2one('product.product', string='Input Product', store=True, readonly=True )
   
    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.p_length = self.product_id.length
            bom_id = self.env['mrp.bom'].search(['|', ('product_id', '=', self.product_id.id), '&', ('product_id', '=', False),
                                                 ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
                                                 ], limit=1)
            self.bom_id = bom_id.id
        else:
            self.p_length = 0
            self.bom_id = None

    @api.onchange('bom_id','bom_id.bom_line_ids','bom_id.bom_line_ids.product_id')
    def onchange_bom(self):
        for record in self:
            if record.bom_id.bom_line_ids:
                record.input_product_id = record.bom_id.bom_line_ids[0].product_id.id