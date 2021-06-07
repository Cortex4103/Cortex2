# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

class PurchaseReportGst(models.Model):
    _name = 'purchase.report.gst'
    _description = "CGST Report"
    _auto = False
    _order = 'date_order desc'
    _rec_name = 'order_id'

    state_id = fields.Many2one('res.country.state', 'State')
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Vendor', readonly=True)
    order_id = fields.Many2one('purchase.order', 'Order', readonly=True)
    date_order = fields.Datetime('Order Date', readonly=True, help="Date on which this document has been created")
    state = fields.Selection([
        ('draft', 'Draft RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], 'Order Status', readonly=True)
    untaxed_total = fields.Float('Sub Total', readonly=True)


    def init(self):
        gst_product_id = self.env['ir.config_parameter'].sudo().get_param('cortex_na.canadian_gst_product_id')
        tools.drop_view_if_exists(self.env.cr, self._table)
        if gst_product_id:
            self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
                %s
                FROM ( %s ) WHERE l.product_id IS NOT NULL AND l.product_id = %s
                %s
                )""" % (self._table, self._select(), self._from(),gst_product_id ,self._group_by()))
        # else:
        #     self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
        #         %s
        #         FROM ( %s ) WHERE l.product_id IS NOT NULL
        #         %s
        #         )""" % (self._table, self._select(), self._from(),self._group_by()))


    def _select(self):
        select_str = """
            WITH currency_rate as (%s)
                SELECT
                    po.id as order_id,
                    min(l.id) as id,
                    po.date_order as date_order,
                    po.state,
                    po.partner_id as partner_id,
                    l.product_id as product_id,
                    sum(l.price_subtotal / COALESCE(po.currency_rate, 1.0))::decimal(16,2) as untaxed_total,
                    partner.state_id as state_id
                    
        """ % self.env['res.currency']._select_companies_rates()
        return select_str

    def _from(self):
        from_str = """
            purchase_order_line l
                join purchase_order po on (l.order_id=po.id)
                join res_partner partner on po.partner_id = partner.id
                join canadian_gst cgst on cgst.state_id = partner.state_id
                    left join product_product p on (l.product_id=p.id)
               
                
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                l.product_id,
                po.partner_id,
                l.date_planned,
                po.date_order,
                po.state,
                po.id,
                partner.state_id
        """
        return group_by_str
