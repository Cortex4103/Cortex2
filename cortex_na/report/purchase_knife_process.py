# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Please note that these reports are not multi-currency !!!
#

from odoo import api, fields, models, tools


class PurchaseKnifeProcessReport(models.Model):
    _name = "purchase.knife.process.report"
    _description = "Knife Process Cost"
    _auto = False
    _order = 'date_order desc, price_total desc'
    _rec_name = 'order_id'

    date_order = fields.Datetime('Order Date', readonly=True, help="Date on which this document has been created")
    state = fields.Selection([
        ('draft', 'Draft RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], 'Order Status', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Vendor', readonly=True)
    date_approve = fields.Datetime('Confirmation Date', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Reference Unit of Measure', required=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    user_id = fields.Many2one('res.users', 'Purchase Representative', readonly=True)
    price_total = fields.Float('Total', readonly=True)
    # price_average = fields.Float('Avg. Cost per Knife', readonly=True, group_operator="avg")
    price_average = fields.Float('Avg. Cost per Knife', readonly=True)
    price_subtotal = fields.Monetary(string='Subtotal', readonly=True)
    category_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    order_id = fields.Many2one('purchase.order', 'Order', readonly=True)
    untaxed_total = fields.Float('Untaxed Total', readonly=True)
    qty_ordered = fields.Float('Qty Ordered', readonly=True, digits='New Cortex Precision')
    qty_received = fields.Float('Qty Received', readonly=True, digits='New Cortex Precision')
    qty_billed = fields.Float('Qty Billed', readonly=True, digits='New Cortex Precision')
    qty_to_be_billed = fields.Float('Qty to be Billed', readonly=True, digits='New Cortex Precision')
    total_inches = fields.Float('Total Inches', readonly=True)
    cost_avg_per_inch = fields.Float('Avg. Cost per Inch', readonly=True)
    length = fields.Float('Length', readonly=True)

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s ) WHERE l.product_id IS NOT NULL AND po.state != 'cancel' AND t.type IN ('service')
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))

    def _select(self):
        select_str = """
            WITH currency_rate as (%s)
                SELECT
                    po.id as order_id,
                    min(l.id) as id,
                    po.date_order as date_order,
                    po.state,
                    po.date_approve,
                    po.dest_address_id,
                    po.partner_id as partner_id,
                    po.user_id as user_id,
                    po.company_id as company_id,
                    l.product_id,
                    p.product_tmpl_id,
                    t.categ_id as category_id,
                    t.length as length,
                    po.currency_id,
                    t.uom_id as product_uom,
                    l.price_subtotal as price_subtotal,
                    CASE COALESCE((l.product_qty * t.length), 0) WHEN 0 THEN Null ELSE (sum(l.product_qty / line_uom.factor * product_uom.factor) * t.length) END as total_inches,
                    CASE COALESCE((l.product_qty * t.length), 0) WHEN 0 THEN Null ELSE (l.price_subtotal / (sum(l.product_qty / line_uom.factor * product_uom.factor) * t.length)) END as cost_avg_per_inch,
                    CASE COALESCE(l.product_qty, 0) WHEN 0 THEN Null ELSE l.price_subtotal / (sum(l.product_qty / line_uom.factor * product_uom.factor)) END as price_average,
                    --(sum(l.product_qty * (l.price_unit / CASE WHEN t.length !=0 THEN t.length END) / COALESCE(po.currency_rate, 1.0))/NULLIF(sum(l.product_qty/line_uom.factor*product_uom.factor),0.0))::decimal(16,2) as cost_avg_per_inch,
                    sum(l.price_total / COALESCE(po.currency_rate, 1.0))::decimal(16,2) as price_total,
                    --(sum(l.product_qty * l.price_unit / COALESCE(po.currency_rate, 1.0))/NULLIF(sum(l.product_qty/line_uom.factor*product_uom.factor),0.0))::decimal(16,2) as price_average,
                    analytic_account.id as account_analytic_id,
                    sum(l.price_subtotal / COALESCE(po.currency_rate, 1.0))::decimal(16,2) as untaxed_total,
                    sum(l.product_qty / line_uom.factor * product_uom.factor) as qty_ordered,
                    sum(l.qty_received / line_uom.factor * product_uom.factor) as qty_received,
                    sum(l.qty_invoiced / line_uom.factor * product_uom.factor) as qty_billed,
                    case when t.purchase_method = 'purchase' 
                         then sum(l.product_qty / line_uom.factor * product_uom.factor) - sum(l.qty_invoiced / line_uom.factor * product_uom.factor)
                         else sum(l.qty_received / line_uom.factor * product_uom.factor) - sum(l.qty_invoiced / line_uom.factor * product_uom.factor)
                    end as qty_to_be_billed
        """ % self.env['res.currency']._select_companies_rates()
        return select_str

    def _from(self):
        from_str = """
            purchase_order_line l
                join purchase_order po on (l.order_id=po.id)
                join res_partner partner on po.partner_id = partner.id
                    left join product_product p on (l.product_id=p.id)
                        left join product_template t on (p.product_tmpl_id=t.id)
                left join uom_uom line_uom on (line_uom.id=l.product_uom)
                left join uom_uom product_uom on (product_uom.id=t.uom_id)
                left join account_analytic_account analytic_account on (l.account_analytic_id = analytic_account.id)
                left join currency_rate cr on (cr.currency_id = po.currency_id and
                    cr.company_id = po.company_id and
                    cr.date_start <= coalesce(po.date_order, now()) and
                    (cr.date_end is null or cr.date_end > coalesce(po.date_order, now())))
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                po.company_id,
                po.user_id,
                po.partner_id,
                line_uom.factor,
                po.currency_id,
                l.price_unit,
                po.date_approve,
                l.date_planned,
                l.product_uom,
                po.dest_address_id,
                l.product_id,
                l.product_qty,
                l.price_subtotal,
                p.product_tmpl_id,
                t.categ_id,
                t.length,
                po.date_order,
                po.state,
                line_uom.uom_type,
                line_uom.category_id,
                t.uom_id,
                t.purchase_method,
                line_uom.id,
                product_uom.factor,
                analytic_account.id,
                po.id
        """
        return group_by_str

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'price_subtotal:sum' not in fields:
            fields += ['price_subtotal']
        result = super(PurchaseKnifeProcessReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                                    orderby=orderby, lazy=lazy)
        for data in result:
            if data.get('product_id'):
                length = data.get('total_inches') / data.get('qty_ordered') if data.get('qty_ordered') else 0
                price_total_knife = data.get('price_subtotal') / data.get('qty_ordered') if data.get(
                    'qty_ordered') else 0
                data['price_average'] = price_total_knife if price_total_knife else 0
                price_total_inch = price_total_knife / length if length else 0
                data['cost_avg_per_inch'] = price_total_inch if price_total_inch else 0
            if data.get('id') or (not data.get('product_id') and not data.get('order_id')):
                data.pop('cost_avg_per_inch')
                data.pop('price_average')
        return result

