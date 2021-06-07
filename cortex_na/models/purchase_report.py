# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Please note that these reports are not multi-currency !!!
#

from odoo import api, fields, models, tools


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    qty_ordered = fields.Float('Qty Ordered', readonly=True, digits='New Cortex Precision')
    qty_received = fields.Float('Qty Received', readonly=True, digits='New Cortex Precision')
    qty_billed = fields.Float('Qty Billed', readonly=True, digits='New Cortex Precision')
    qty_to_be_billed = fields.Float('Qty to be Billed', readonly=True, digits='New Cortex Precision')
    qty_rem_received = fields.Float(string='Product to be Received', readonly=True, digits='New Cortex Precision')
    qty_rem_billed = fields.Float(string='Unbilled', readonly=True, digits='New Cortex Precision')

    def _select(self):
        return super(PurchaseReport, self)._select() + ", l.qty_rem_received as qty_rem_received, l.qty_rem_billed as qty_rem_billed"

    def _group_by(self):
        return super(PurchaseReport, self)._group_by() + ", l.qty_rem_received, l.qty_rem_billed"
