# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CanadianGST(models.Model):
    _name = 'canadian.gst'
    _description = 'Canadian GST'

    state_id = fields.Many2one('res.country.state', 'State', required=True)
    name = fields.Char(string='Name')
    sale_gst = fields.Float(string='Sale GST %', required=True)
    purchase_gst = fields.Float(string='Purchase GST %', required=True)

    @api.onchange('state_id')
    def onchange_state_id(self):
        if self.state_id:
            self.name = self.state_id.name