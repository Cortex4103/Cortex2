# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import logging
import itertools
import xlsxwriter
from ast import literal_eval
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, RedirectWarning, UserError

_logger = logging.getLogger(__name__)


"""
CLASS: Cornomics Data
"""
class CornomicsData(models.Model):
    _name = "cornomics.data"
    _description = 'Cornomics Data'
    _rec_name = 'cortex_company_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    compititor_company_id = fields.Many2one('cornomics.company', string='Company')
    company_id = fields.Many2one('res.company', string="Company" , default=lambda self: self.env.company)
    competitor_monthly_op_cost = fields.Float('COMPETITOR MONTHLY OPERATING COSTS',compute='competitor_monthly_cost')
    competitor_annual_op_cost = fields.Float('COMPETITOR ANNUAL OPERATING COSTS',compute='competitor_annual_cost')

    cortex_company_name = fields.Char(string='Cortex Company',default='CORTEX OPERATING COSTS')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.company.currency_id)
    cortex_monthly_op_cost = fields.Float('CORTEX MONTHLY OPERATING COSTS',compute='cortex_monthly_cost')
    cortex_annual_op_cost = fields.Float('CORTEX ANNUAL OPERATING COSTS',compute='cortex_annual_cost')
    cortex_annual_saving = fields.Float('ANNUAL SAVINGS WITH CORTEX',compute='compute_cortex_annual_saving')
    cornomics_data_detail_line_ids = fields.One2many('cornomics.data.detail.line','cornomics_data_id',string='Cornomics Detail Line Ids')
    cortex_total_agerage_savings = fields.Float("CORTEX TOTAL AVERAGE SAVINGS (%)", readonly=True)

    #Competitor ROI Fields
    competitor_annual_knife_cost = fields.Float("ANNUAL KNIFE COST", compute='set_competitor_annual_knife_cost')
    cost_of_new_bases = fields.Float("COST OF NEW BASES")
    base_consumption_year = fields.Integer("BASE CONSUMPTION/YEAR")
    normal_holder_replacement_cost = fields.Float("NORMAL HOLDER REPLACEMENT COST", compute='set_normal_holder_replacement_cost')

    #Cortex ROI
    # assumptions = fields.Integer("ASSUMPTIONS")
    assumption = fields.Text("ASSUMPTIONS")
    investment_cost = fields.Float("INVESTMENT COST")
    less_normal_holder_replacement_cost = fields.Float("LESS-NORMAL HOLDER REPLACEMENT COST", compute='set_less_normal_holder_replacement_cost')
    total_investment = fields.Float("TOTAL INVESTMENT", compute='set_total_investment')
    annual_savings_with_cortex = fields.Float("ANNUAL SAVINGS WITH CORTEX", compute='set_annual_savings_with_cortex')
    indirect_savings_with_cortex = fields.Float("INDIRECT SAVINGS WITH CORTEX", compute='set_indirect_savings_with_cortex')

    #Cortext ROI Benifits
    grinding_labor_savings = fields.Integer("GRINDING LABOR SAVINGS (HOURS PER WEEK)")
    knife_change_labor = fields.Integer("KNIFE CHANGE LABOR (HOURS)")
    hourly_labor_cost = fields.Float("HOURLY LABOR COST")
    weekly_labor_savings = fields.Float("WEEKLY LABOR SAVINGS", compute='set_weekly_labor_savings')
    monthly_labor_savings = fields.Float("MONTHLY LABOR SAVINGS", compute='set_monthly_labor_savings')
    indirect_cortex_roi_benefits_total = fields.Float("TOTAL", compute='set_indirect_cortex_roi_benefits_total')


    @api.depends('cornomics_data_detail_line_ids')
    def competitor_monthly_cost(self):
        for record in self:
            monthly_cost = 0
            for line in record.cornomics_data_detail_line_ids:
                monthly_cost += line.competitor_total_cost
            record.competitor_monthly_op_cost = monthly_cost

    @api.depends('cornomics_data_detail_line_ids')
    def cortex_monthly_cost(self):
        for record in self:
            monthly_cost = 0
            for line in record.cornomics_data_detail_line_ids:
                monthly_cost += line.cortex_total_cost
            record.cortex_monthly_op_cost = monthly_cost

    @api.depends('competitor_monthly_op_cost')
    def competitor_annual_cost(self):
        for record in self:
            record.competitor_annual_op_cost = record.competitor_monthly_op_cost * 12
            record.competitor_annual_knife_cost = record.competitor_annual_op_cost
    
    @api.depends('cortex_monthly_op_cost')
    def cortex_annual_cost(self):
        for record in self:
            record.cortex_annual_op_cost = record.cortex_monthly_op_cost * 12

    @api.depends('cortex_annual_op_cost','competitor_annual_op_cost')
    def compute_cortex_annual_saving(self):
        for record in self:
            record.cortex_annual_saving = record.competitor_annual_op_cost - record.cortex_annual_op_cost
            
            # CORTEX TOTAL AVERAGE SAVINGS (%)
            com_total_cost = 0
            cor_total_cost = 0
            for rec in self.cornomics_data_detail_line_ids:
                com_total_cost = com_total_cost + rec.competitor_total_cost
                cor_total_cost = cor_total_cost + rec.cortex_total_cost
            
            if com_total_cost > cor_total_cost:
                diff = com_total_cost - cor_total_cost
                saving = (diff * 100) / com_total_cost
                record.cortex_total_agerage_savings = round(saving)

    @api.depends('competitor_annual_op_cost')
    def set_competitor_annual_knife_cost(self):
        for record in self:
            record.competitor_annual_knife_cost = record.competitor_annual_op_cost
    
    @api.depends('cost_of_new_bases', 'base_consumption_year')
    def set_normal_holder_replacement_cost(self):
        for record in self:
            record.normal_holder_replacement_cost = (record.cost_of_new_bases * record.base_consumption_year)

    @api.depends('normal_holder_replacement_cost')
    def set_less_normal_holder_replacement_cost(self):
        for record in self:
            record.less_normal_holder_replacement_cost = record.normal_holder_replacement_cost

    @api.depends('less_normal_holder_replacement_cost','investment_cost')
    def set_total_investment(self):
        for record in self:
            record.total_investment = (record.less_normal_holder_replacement_cost - record.investment_cost)
    
    @api.depends('cortex_annual_saving')
    def set_annual_savings_with_cortex(self):
        for record in self:
            record.annual_savings_with_cortex = record.cortex_annual_saving

    @api.depends('indirect_cortex_roi_benefits_total')
    def set_indirect_savings_with_cortex(self):
        for record in self:
            record.indirect_savings_with_cortex = record.indirect_cortex_roi_benefits_total

    @api.depends('grinding_labor_savings','knife_change_labor','hourly_labor_cost')
    def set_weekly_labor_savings(self):
        for record in self:
            record.weekly_labor_savings = (record.grinding_labor_savings + record.knife_change_labor) * record.hourly_labor_cost

    @api.depends('weekly_labor_savings')
    def set_monthly_labor_savings(self):
        for record in self:
            record.monthly_labor_savings = record.weekly_labor_savings * 4

    @api.depends('monthly_labor_savings')
    def set_indirect_cortex_roi_benefits_total(self):
        for record in self:
            record.indirect_cortex_roi_benefits_total = record.monthly_labor_savings * 12



"""
CLASS: CornomicsDataDetail
"""
class CornomicsDataDetail(models.Model):
    _name = "cornomics.data.detail.line"
    _description = 'Cornomics Data Detail Line'

    cornomics_data_id = fields.Many2one('cornomics.data',string='Cornomics Data Id')
    # competitor_product = fields.Selection([('production', 'Production'), ('conversion', 'Conversion')],string='Product')
    competitor_product_id = fields.Many2one('cornomics.company.detail',string='PART DESCRIPTION')
    estimated_consumption = fields.Float(string='EST CONSUMPTION-MONTH')
    estimated_price = fields.Float(string='PRICE')
    competitor_total_cost = fields.Float('TOTAL', compute='compute_competitor_total_cost')

    product_id = fields.Many2one('product.product', 'DESCRIPTION')
    cortex_estimated_consumption = fields.Float(string='EST CONSUMPTION-MONTH')
    price = fields.Float(string='PRICE')
    cortex_total_cost = fields.Float('TOTAL', compute='compute_cortex_total_cost')

    cornomics_percent_savings = fields.Float("SAVINGS (%)")

    @api.onchange('competitor_product_id')
    def onchange_competitor_product_id(self):
        self.product_id = self.competitor_product_id.product_tmpl_id.product_variant_id.id if self.competitor_product_id else False
        self.estimated_consumption = self.competitor_product_id.estimated_consumption
        self.estimated_price = self.competitor_product_id.estimated_price
        self.cortex_estimated_consumption = self.competitor_product_id.estimated_consumption

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.price = self.product_id.list_price if self.product_id else False

            if self.competitor_total_cost > self.cortex_total_cost:
                diff = self.competitor_total_cost - self.cortex_total_cost
                saving = (diff * 100) / self.competitor_total_cost
                self.cornomics_percent_savings = round(saving)
            else:
                self.cornomics_percent_savings = 0.0

    @api.depends('estimated_consumption', 'estimated_price')
    def compute_competitor_total_cost(self):
        for record in self:
            record.competitor_total_cost = record.estimated_price * record.estimated_consumption

    @api.depends('cortex_estimated_consumption','price')
    def compute_cortex_total_cost(self):
        for record in self:
            record.cortex_total_cost = record.price * record.cortex_estimated_consumption
