# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons import decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    product_id = fields.Many2one('product.product', string='DO service product', help='Add Do service product ')
    canadian_gst_product_id = fields.Many2one('product.product', string='Canadian GST Product', help='Add Canadian GST Product')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        Param = self.env['ir.config_parameter'].sudo()
        Param.set_param('cortex_na.product_id', self.product_id.id)
        Param.set_param('cortex_na.canadian_gst_product_id', self.canadian_gst_product_id.id)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        product_id = int(params.get_param('cortex_na.product_id'))
        res.update(product_id=product_id)
        canadian_gst_product_id = int(params.get_param('cortex_na.canadian_gst_product_id'))
        res.update(canadian_gst_product_id=canadian_gst_product_id)
        return res
