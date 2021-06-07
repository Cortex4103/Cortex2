# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class ReportStockQuantity(models.Model):
    _inherit = 'report.stock.quantity'

    product_qty = fields.Float(string='Quantity', readonly=True, digits='Product Unit of Measure')