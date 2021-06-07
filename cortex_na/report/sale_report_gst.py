# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#access_sale_report_gst,access_sale_report_gst,model_sale_report_gst,base.group_user,1,1,1,1
from odoo import fields, models, tools, api
class SaleReportGstorder(models.Model):
    _name = 'sale.order.report.gst'
    _description = "CGST Report"
    _auto = False

    date = fields.Datetime('Order Date', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    price_subtotal = fields.Float('Sub Total', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Sales Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True)

    order_id = fields.Many2one('sale.order', '', readonly=True)
    state_id = fields.Many2one('res.country.state', 'State')
    type = fields.Selection([
               ('consu', 'Consumable'),
               ('service', 'Service'),
                ('product', 'Storable Product')
        ], string='Status')

class SaleReportGst(models.Model):

    _name = 'sale.report.gst'
    _description = "CGST Report"
    _auto = False
    _order = 'date desc'
    _rec_name = 'order_id'

    date = fields.Datetime('Order Date', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    price_subtotal = fields.Float('Sub Total', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Sales Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True)

    order_id = fields.Many2one('sale.order', '', readonly=True)
    state_id = fields.Many2one('res.country.state', 'State')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        gst_product_id = self.env['ir.config_parameter'].sudo().get_param('cortex_na.canadian_gst_product_id')
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            min(l.id) as id,
            l.product_id as product_id,
            sum(l.price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as price_subtotal,
            s.date_order as date,
            s.state as state,
            s.partner_id as partner_id,
            s.id as order_id,
            partner.state_id as state_id
        """

        from_ = """
                sale_order_line l
                      join sale_order s on (l.order_id=s.id)
                      join res_partner partner on s.partner_id = partner.id
                      join canadian_gst cgst on cgst.state_id = partner.state_id


                %s
        """ % from_clause

        groupby_ = """
                l.product_id,
                l.order_id,
                s.date_order,
                s.partner_id,
                s.state,
                s.id,
                partner.state_id %s
        """ % (groupby)

        # if gst_product_id:
        return '%s (SELECT %s FROM %s WHERE l.product_id IS NOT NULL AND l.product_id = %s GROUP BY %s)' % (
        with_, select_, from_, gst_product_id, groupby_)
        # else:
        #     return '%s (SELECT %s FROM %s WHERE l.product_id IS NOT NULL GROUP BY %s)' % (with_, select_, from_,groupby_)

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
