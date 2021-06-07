# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class distributionService(models.Model):
    _name = 'distribution.service'

    distribution_on = fields.Selection([('quantity', 'Quantity'), ('weight', 'Weight'), ('length', 'Length')], string='Distribution On')
    product_id = fields.Many2one('product.product', string='Service Charge')
    quantity = fields.Float(string='Quantity', digits='New Cortex Precision')
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', default=lambda self: self.env.ref('uom.product_uom_unit'))
    subtotal = fields.Float(string='Subtotal', compute='compute_subtotal',digits='New Cortex Product Precision')
    batch_production_id = fields.Many2one('batch.production', string='Batch Production', ondelete='cascade')

    @api.depends('quantity', 'price_unit')
    def compute_subtotal(self):
        for record in self:
            record.subtotal = record.quantity * record.price_unit
    
    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
            self.price_unit = self.product_id.standard_price
