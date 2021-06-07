# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class SaleReportCustom(models.Model):
        _name = "sale.report.custom"
        _description = "Sales Analysis Report"
        _auto = False
        _order = 'date desc'
        _rec_name = 'order_id'

        @api.model
        def _get_done_states(self):
            return ['sale', 'done', 'paid']

        name = fields.Char('Order Reference', readonly=True)
        date = fields.Datetime('Order Date', readonly=True)
        product_id = fields.Many2one('product.product', 'Product Variant', readonly=True)
        product_uom = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True)
        product_uom_qty = fields.Float('Knife Inches Ordered', readonly=True, digits='New Knife Precision')
        qty_delivered = fields.Float('Knife Inches Delivered', readonly=True, digits='New Knife Precision')
        qty_to_invoice = fields.Float('Qty To Invoice', readonly=True, digits='New Cortex Precision')
        qty_invoiced = fields.Float('Knife Inches Invoiced', readonly=True, digits='New Knife Precision')
        partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
        company_id = fields.Many2one('res.company', 'Company', readonly=True)
        user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
        price_total = fields.Float('Total', readonly=True)
        price_subtotal = fields.Float('Untaxed Total', readonly=True)
        untaxed_amount_to_invoice = fields.Float('Untaxed Amount To Invoice', readonly=True)
        untaxed_amount_invoiced = fields.Float('Untaxed Amount Invoiced', readonly=True)
        product_tmpl_id = fields.Many2one('product.template', 'Product', readonly=True)
        categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)
        type = fields.Selection([
            ('consu', 'Consumable'),
            ('service', 'Service'),
            ('product', 'Storable Product')], string='Product Type', readonly=True)
        # nbr = fields.Integer('# of Lines', readonly=True)
        pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
        analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
        # team_id = fields.Many2one('crm.team', 'Sales Team', readonly=True)
        country_id = fields.Many2one('res.country', 'Customer Country', readonly=True)
        currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
        # industry_id = fields.Many2one('res.partner.industry', 'Customer Industry', readonly=True)
        # commercial_partner_id = fields.Many2one('res.partner', 'Customer Entity', readonly=True)
        state = fields.Selection([
            ('draft', 'Draft Quotation'),
            ('sent', 'Quotation Sent'),
            ('sale', 'Sales Order'),
            ('done', 'Sales Done'),
            ('cancel', 'Cancelled'),
            ], string='Status', readonly=True)
        # weight = fields.Float('Gross Weight', readonly=True)
        # volume = fields.Float('Volume', readonly=True)

        discount = fields.Float('Discount %', readonly=True)
        discount_amount = fields.Float('Discount Amount', readonly=True)
        # campaign_id = fields.Many2one('utm.campaign', 'Campaign')
        # medium_id = fields.Many2one('utm.medium', 'Medium')
        # source_id = fields.Many2one('utm.source', 'Source')
        line_partner_id = fields.Many2one('res.partner', string='Sawmill')
        order_id = fields.Many2one('sale.order', 'Order #', readonly=True)


        product_qty = fields.Float('Knife Inches Manufactured',digits='New Knife Precision')

        def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
            with_ = ("WITH %s" % with_clause) if with_clause else ""

            select_ = """
                min(l.id) as id,
                l.product_id as product_id,
                l.partner_id as line_partner_id,
                t.uom_id as product_uom,
                sum((l.product_uom_qty / u.factor * u2.factor) * p.length) as product_uom_qty,
                sum((l.qty_delivered / u.factor * u2.factor) * p.length) as qty_delivered,
                sum((l.qty_invoiced / u.factor * u2.factor) * p.length) as qty_invoiced,
                sum((l.qty_to_invoice / u.factor * u2.factor) * p.length) as qty_to_invoice,
                sum(l.price_total / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as price_total,
                sum(l.price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as price_subtotal,
                sum(l.untaxed_amount_to_invoice / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as untaxed_amount_to_invoice,
                sum(l.untaxed_amount_invoiced / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as untaxed_amount_invoiced,
                s.name as name,
                s.date_order as date,
                s.state as state,
                s.partner_id as partner_id,
                s.user_id as user_id,
                s.company_id as company_id,
                l.currency_id as currency_id,
                extract(epoch from avg(date_trunc('day',s.date_order)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
                t.categ_id as categ_id,
                t.type as type,
                categ.category_display_in_report as category_display_in_report,
                s.pricelist_id as pricelist_id,
                s.analytic_account_id as analytic_account_id,
                p.product_tmpl_id,
                partner.country_id as country_id,
                l.discount as discount,
                sum((l.price_unit * l.discount / 100.0 / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END)) as discount_amount,
                s.id as order_id,
                CAST (NULL AS DOUBLE PRECISION) as product_qty
            """

            for field in fields.values():
                select_ += field

            from_ = """
                    sale_order_line l
                          join sale_order s on (l.order_id=s.id)
                          join res_partner partner on s.partner_id = partner.id
                            left join product_product p on (l.product_id=p.id)
                                left join product_template t on (p.product_tmpl_id=t.id)
                                    left join product_category categ on (t.categ_id = categ.id)
                        left join uom_uom u on (u.id=l.product_uom)
                        left join uom_uom u2 on (u2.id=t.uom_id)
                        left join product_pricelist pp on (s.pricelist_id = pp.id)
                       
                        
                    %s
            """ % from_clause

            groupby_ = """
                l.product_id,
                l.partner_id,
                l.order_id,
                t.uom_id,
                t.categ_id,
                t.type,
                categ.category_display_in_report,
                s.name,
                s.date_order,
                s.partner_id,
                s.user_id,
                s.state,
                s.company_id,
                l.currency_id,
                s.pricelist_id,
                s.analytic_account_id,
                p.product_tmpl_id,
                partner.country_id,
                l.discount,
                s.id
                 %s
            """ % (groupby)

            return """%s (SELECT %s FROM %s WHERE l.product_id IS NOT NULL AND t.type IN ('product','consu') AND categ.category_display_in_report = TRUE GROUP BY %s)""" % (with_, select_, from_, groupby_)

        def _query_manufactur(self, with_clause='', fields={}, groupby='', from_clause=''):
            with_ = ("WITH %s" % with_clause) if with_clause else ""

            select_ = """
                   min(mp.id) + 1 as id,
                   mp.product_id as product_id,
                   CAST(NULL AS int4) line_partner_id,
                   mt.uom_id as product_uom,
                   CAST (NULL AS DOUBLE PRECISION) product_uom_qty,
                   CAST (NULL AS DOUBLE PRECISION) qty_delivered,
                   CAST (NULL AS DOUBLE PRECISION) qty_invoiced,
                   CAST (NULL AS DOUBLE PRECISION) qty_to_invoice,
                   CAST (NULL AS DOUBLE PRECISION) price_total,
                   CAST (NULL AS DOUBLE PRECISION) price_subtotal,
                   CAST (NULL AS DOUBLE PRECISION) untaxed_amount_to_invoice,
                   CAST (NULL AS DOUBLE PRECISION) untaxed_amount_invoiced,
                   mp.name as name,
                   mp.date_finished as date,
                   CAST(NULL AS CHAR) state,
                   CAST(NULL AS int4) partner_id,
                   CAST(NULL AS int4) user_id,
                   CAST(NULL AS int4) company_id,
                   CAST(NULL AS int4) currency_id,
                   NULL as delay,
                   mt.categ_id as categ_id,
                   mt.type as type,
                   mcateg.category_display_in_report as category_display_in_report,
                   CAST(NULL AS int4) pricelist_id,
                   CAST(NULL AS int4) analytic_account_id,
                   mpp.product_tmpl_id,
                    CAST(NULL AS int4) country_id,
                   CAST (NULL AS DOUBLE PRECISION) discount,
                   CAST (NULL AS DOUBLE PRECISION) discount_amount,
                   CAST(NULL AS int4) order_id,
                   sum((mp.product_qty / mu.factor * mu2.factor) * mpp.length) as product_qty
               """

            for field in fields.values():
                select_ += field

            from_ = """
                       mrp_production mp
                                join product_product mpp on (mp.product_id=mpp.id)
                                join product_template mt on (mpp.product_tmpl_id=mt.id)
                                join product_category mcateg on (mt.categ_id = mcateg.id)
                           left join uom_uom mu on (mu.id=mp.product_uom_id)
                           left join uom_uom mu2 on (mu2.id=mt.uom_id)
                          
    
                       %s
               """ % from_clause

            groupby_ = """
                   mp.product_id,
                   mt.uom_id,
                   mt.categ_id,
                   mt.type,
                   mcateg.category_display_in_report,
                   mpp.product_tmpl_id,
                    mp.product_qty,
                    mp.date_finished,
                    mp.name
              
                    %s
               """ % (groupby)

            return """%s (SELECT %s FROM %s WHERE mp.state ='done' AND mcateg.category_display_in_report = TRUE GROUP BY %s)""" % (
            with_, select_, from_, groupby_)

        def _combine_consumption(self):
            from_str = """(%s UNION ALL %s)""" % (self._query(), self._query_manufactur())
            return from_str

        # @api.model
        # def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        #     # if 'order_id' in groupby:
        #     #     domain =(domain or []) + [('order_id','!=',False)]
        #     #     if 'product_qty:sum' in fields:
        #     #         fields.remove('product_qty:sum')
        #
        #     result = super(SaleReportCustom, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
        #                                                     orderby=orderby, lazy=lazy)
        #
        #     return result



        def init(self):
            # self._table = sale_report
            tools.drop_view_if_exists(self.env.cr, self._table)
            self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._combine_consumption()))