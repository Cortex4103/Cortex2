# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, api, _

class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    quantity = fields.Float(string='Product Quantity', readonly=True ,digits="New Cortex Precision")
