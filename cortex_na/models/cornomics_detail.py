# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
import logging
import io
import xlsxwriter
from ast import literal_eval
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, RedirectWarning, UserError

_logger = logging.getLogger(__name__)

class CornomicsDetails(models.Model):
    _name = "cornomics.company.detail"
    _rec_name="product_des"

    compititor_company_id = fields.Many2one('cornomics.company', string='Company', required=True)
    product_id = fields.Many2one('product.product', 'Product')
    product_des = fields.Char('Product', required=True)
    estimated_consumption = fields.Float(string='Estimated Consumption')
    estimated_price = fields.Float(string='Estimated Price')
    product_tmpl_id = fields.Many2one('product.template',string='Product template')

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if self._context.get('is_company'):
            domain = [('compititor_company_id', '=', self._context.get('is_company')), ('product_des', '!=', False)]
            return super(CornomicsDetails, self).name_search(name=name, args=domain, operator=operator, limit=limit)
        return super(CornomicsDetails, self).name_search(name=name, args=args, operator=operator, limit=limit)

class CornomicsCompany(models.Model):
    _name = "cornomics.company"

    name = fields.Char(string='Cornomics Company Name')
