# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons import decimal_precision as dp


class SaleOrder(models.Model):
    _inherit = "sale.order"

    project_id = fields.Many2one('project.project', string='Project',readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)],'sale': [('readonly', False)]},tracking=True)