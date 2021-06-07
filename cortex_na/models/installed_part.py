# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from datetime import datetime


class InstalledPart(models.Model):
    _name = 'installed.part'
    _description = 'Installed Part'
    _rec_name = 'machine_center_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    machine_center_id = fields.Many2one('machine.center', string='Machine Center', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Sawmill (Customer)', tracking=True) 
    knife_provider_id = fields.Many2one('knife.provider',string='Knife Provider', tracking=True)
    machine_center_oem_id = fields.Many2one('machine.center.oem',string='Machine Center OEM')
    knives_per_segment_id = fields.Many2one('knives.per.segment',string='Knives Per Segment')
    pockets_id = fields.Many2one('knives.per.segment',string='# of Pockets')
    length_of_knives_id = fields.Many2one('length.of.knives',string='Length Of Knives')
    length_of_knife_id = fields.Many2one('length.of.knives',string='Length Of knife')
    length_of_short_knife_id = fields.Many2one('length.of.knives',string='Length of Short Knife')
    length_of_long_knife_id = fields.Many2one('length.of.knives',string='Length of Long Knife')
    spline = fields.Boolean(string='Spline')
    short_knives_per_ea_head_id = fields.Many2one('knives.per.segment', string='Short Knives per ea Heads')
    long_knives_ea_head_id = fields.Many2one('numbers',string='Long Knives ea Head')
    knives_per_pocket_id = fields.Many2one('numbers',string='Knives per Pocket')
    segment_per_head= fields.Selection([('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10')],string='# of Segments per Head')
    of_head = fields.Selection([('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10')],string='# Of Heads')
    length_of_pockets = fields.Char(string='Length of Pocket')
    installed_part_detail_id = fields.One2many('installed.part.detail','install_part_id',string='Install Part Detail', required=True)
    is_drumhead = fields.Boolean(string='Drumhead',default='False')
    is_conicals = fields.Boolean(string='Conical',default='False')
    is_chipper = fields.Boolean(string='Chipper',default='False')
    description = fields.Char(string='Description')
    date = fields.Date(string='Date')

    @api.onchange('date')
    def onchange_date(self):
        if self.installed_part_detail_id:
            self.installed_part_detail_id.update({'date': self.date})
            self.installed_part_detail_id._onchange_date()

    @api.onchange('machine_center_id')
    def onchange_machine_center_id(self):
        if self.machine_center_id:
            if self.machine_center_id.id == self.env.ref('cortex_na.machine_center_drumhead').id:
                self.is_drumhead = True
                self.is_conicals = False
                self.is_chipper = False
            elif self.machine_center_id.id == self.env.ref('cortex_na.machine_center_conical').id:
                self.is_conicals = True
                self.is_chipper = False
                self.is_drumhead = False
            elif self.machine_center_id.id == self.env.ref('cortex_na.machine_center_chipper').id:
                self.is_chipper = True
                self.is_conicals = False
                self.is_drumhead = False
            else:
                self.is_drumhead = True
                self.is_chipper = False
                self.is_conicals = False
        else:
            self.is_chipper = False
            self.is_conicas = False
            self.is_drumhead = False

    def name_get(self):
        result = []
        for record in self:
            for line in record:
                if line.description:
                    result.append((line.installed_part_detail_id.install_part_id.id, '[%s] %s' % (line.machine_center_id.name, line.description)))
                else:
                    result.append((line.installed_part_detail_id.install_part_id.id, '[%s]' % (line.machine_center_id.name)))
        return result


class InstalledPartDetail(models.Model):
    _name = 'installed.part.detail'
    _rec_name = 'product_id'

    install_part_id = fields.Many2one('installed.part',string='Installed Part', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='# Part')
    installed_knife = fields.Float(string='# of Installed (Operating) Parts',  digits=(16,0))
    estimated_monthly_consumption = fields.Integer(string='Estimated Monthly Consumption (annual consumption for parts)')
    head_location_id = fields.Many2one('drumhead.location',string='Head Location')
    date = fields.Date(string='Date')
    installed = fields.Boolean(string='Active', readonly=True , default=True)
    categ_id = fields.Many2one('product.category', related='product_id.categ_id', string='Product Category', store=True)
    partner_id = fields.Many2one(related="install_part_id.partner_id", string='Customer', store=True)
    knife_lenth = fields.Float(related="product_id.length", string='Lenth of Knife', store=True)
    monthly_consumption_calculate = fields.Integer(string='Estimated Monthly Consumption', compute="compute_knife_inches", store="True")
    estimated_annual_consumption = fields.Integer(string='Est. Annual Consumption', compute="compute_knife_inches", store="True")
    estimated_monthly_knife_inches = fields.Integer(string='Est Monthly Knife Inches')
    estimated_annual_knife_inches = fields.Integer(string='Est Annual Knife Inches ')
    frequency = fields.Selection([('monthly', 'Monthly'), ('yearly', 'Yearly'), ('2_year', '2 Year')], string='Frequency', default='monthly')
   

    @api.depends('estimated_monthly_consumption','frequency')
    def compute_knife_inches(self):
        for rec in self:
            product_length = rec.product_id.length
            if rec.frequency == 'yearly':
                rec.estimated_annual_consumption = rec.estimated_monthly_consumption
                rec.monthly_consumption_calculate = rec.estimated_monthly_consumption/12
                rec.estimated_monthly_knife_inches = (rec.estimated_monthly_consumption/12) * product_length
                rec.estimated_annual_knife_inches = rec.estimated_monthly_consumption * product_length
            elif rec.frequency == '2_year':
                rec.estimated_annual_consumption = rec.estimated_monthly_consumption/2
                rec.monthly_consumption_calculate = rec.estimated_monthly_consumption/24
                rec.estimated_monthly_knife_inches = (rec.estimated_monthly_consumption/24) * product_length
                rec.estimated_annual_knife_inches = (rec.estimated_monthly_consumption/2) * product_length
            else:
                rec.estimated_annual_consumption = rec.estimated_monthly_consumption * 12 
                rec.monthly_consumption_calculate = rec.estimated_monthly_consumption 
                rec.estimated_monthly_knife_inches = rec.estimated_monthly_consumption * product_length
                rec.estimated_annual_knife_inches = rec.estimated_monthly_consumption * product_length * 12

    @api.onchange('date')
    def _onchange_date(self):
        for line in self:
            if line.date:
                if line.date > datetime.now().date():
                    line.installed = False
                else:
                    line.installed = True

    # Update installed part which have passed date and still not actived
    def update_installed_part_active(self):
        installed_part_obj = self.search([('date', '<=', datetime.now().date()), ('installed', '=', False)])
        if installed_part_obj:
            installed_part_obj.write({'installed': True})
        return True


class stick_land(models.Model):
    _inherit = 'stock.landed.cost'

    allowed_picking_ids = fields.Char("stock")

