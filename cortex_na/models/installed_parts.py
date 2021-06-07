# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class InstalledParts(models.Model):
    _name = 'installed.parts'
    _description = 'Installed Parts'
    _rec_name = 'partner_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    partner_id = fields.Many2one('res.partner', string='Sawmill (Customer)', tracking=True)
    machine_center_id = fields.Many2one('machine.center', string='Machine Center')
    brand_id = fields.Many2one('brand.brand', string='Brand')
    product_id = fields.Many2one('product.product', string='Knife/Product', tracking=True)
    installed_knife = fields.Float(string='# of Installed Knife #1', tracking=True)
    qty_knife_per_mnth = fields.Float(string='Qty KN1/Mnth', tracking=True)
    est_conversion_rev = fields.Float(string='Est Conversion Revenue')
    active = fields.Boolean(string='Active', default=True)


class MachineCenter(models.Model):
    _name = 'machine.center'
    _description = 'Machine Center'
    _rec_name = 'name'

    name = fields.Char(string='Machine Center')


class BrandBrand(models.Model):
    _name = 'brand.brand'
    _description = 'Brand'
    _rec_name = 'name'

    name = fields.Char(string='Brand')
