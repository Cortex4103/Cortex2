# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, SUPERUSER_ID
from odoo.tools.float_utils import float_round
from odoo.addons import decimal_precision as dp

class Lead(models.Model):
    _inherit = "crm.lead"

    planned_revenue = fields.Float(string='Expected Revenue', currency_field='company_currency', tracking=True, default=None, digits=(16, 0))
    probability = fields.Float('Probability', group_operator="avg", default=None, digits=(16, 0))