# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockValuationLayer(models.Model):
    """Stock Valuation Layer"""

    _inherit = 'stock.valuation.layer'

    quantity = fields.Float('Quantity', digits='Product Unit of Measure', help='Quantity', readonly=True)

    def update_layer_create_date(self, query):
        if query:
            self.env.cr.execute(query)
        return True