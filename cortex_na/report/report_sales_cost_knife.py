# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, api, _


class SalesCostKnife(models.Model):
    _name = "sales.cost.knife"
    _description = "Sales and Cost by knife"
    _auto = False

    product_id = fields.Many2one('product.product', 'Product Variant', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True)
    product_uom_qty = fields.Float('Sale Qty', readonly=True, digits='New Cortex Precision')
    order_id = fields.Many2one('sale.order', 'Sale Order', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    sawmill_id = fields.Many2one('res.partner', string="Sawmill")
    sale_cost = fields.Float(string="Sales Cost")
    avg_cost = fields.Float(string="Avg. Cost")
    avg_cost_inch = fields.Float(string="Avg. Cost per inch")
    sale_price = fields.Float(string='Sale Price')
    avg_price = fields.Float(string='Avg. Sale')
    price_average = fields.Float(string='Avg. Sale per Inch', readonly=True)
    sale_inch = fields.Float(string='Sale Inches')
    product_tmpl_id = fields.Many2one('product.template', 'Product', readonly=True)
    categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product')], string='Product Type', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Sales Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True)
    date = fields.Datetime('Order Date', readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            min(l.id) as id,
            l.product_id as product_id,
            t.uom_id as product_uom,
            sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
            CASE COALESCE(l.product_uom_qty, 0) WHEN 0 THEN 0 ELSE (l.sale_cost * sum(l.product_uom_qty / u.factor * u2.factor)) END as sale_cost,
            l.sale_cost as avg_cost,
            CASE COALESCE(t.length, 0) WHEN 0 THEN 0 ELSE (l.sale_cost / t.length) END as avg_cost_inch,
            l.price_subtotal as sale_price,
            CASE COALESCE(l.product_uom_qty, 0) WHEN 0 THEN 0 ELSE (l.price_subtotal / sum(l.product_uom_qty / u.factor * u2.factor)) END as avg_price,
            CASE COALESCE((l.product_uom_qty * t.length), 0) WHEN 0 THEN 0 ELSE l.price_subtotal / (sum(l.product_uom_qty / u.factor * u2.factor) * t.length) END as price_average,
            (sum(l.product_uom_qty / u.factor * u2.factor) * t.length) as sale_inch,
            s.date_order as date,
            s.state as state,
            s.partner_id as partner_id,
            l.partner_id as sawmill_id,
            l.currency_id as currency_id,
            t.categ_id as categ_id,
            p.product_tmpl_id,
            t.type as type,
            s.id as order_id
        """

        for field in fields.values():
            select_ += field

        from_ = """
                sale_order_line l
                      join sale_order s on (l.order_id=s.id)
                      join res_partner partner on s.partner_id = partner.id
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join uom_uom u on (u.id=l.product_uom)
                    left join uom_uom u2 on (u2.id=t.uom_id)
                %s
        """ % from_clause

        groupby_ = """
            l.product_id,
            l.product_uom_qty,
            l.price_subtotal,
            l.sale_cost,
            l.partner_id,
            l.order_id,
            l.currency_id,
            t.uom_id,
            t.length,
            t.categ_id,
            s.date_order,
            s.partner_id,
            s.state,
            p.product_tmpl_id,
            t.type,
            s.id %s
        """ % (groupby)

        return "%s (SELECT %s FROM %s WHERE l.product_id IS NOT NULL AND s.state != 'cancel' GROUP BY %s)" % (with_, select_, from_, groupby_)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'sale_cost:sum' not in fields:
            fields += ['sale_cost']
        if 'sale_price:sum' not in fields:
            fields += ['sale_price']
        if 'sale_inch:sum' not in fields:
            fields += ['sale_inch']
        result = super(SalesCostKnife, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                   orderby=orderby, lazy=lazy)
        for data in result:
            if data.get('product_id') and data.get('__count') > 1:
                sale_qty = data.get('product_uom_qty')
                if sale_qty:
                    data['avg_cost'] = data.get('sale_cost') / sale_qty
                    data['avg_price'] = data.get('sale_price') / sale_qty
                else:
                    data['avg_cost'] = 0
                    data['avg_price'] = 0
                sale_inch = data.get('sale_inch')
                if sale_inch:
                    data['avg_cost_inch'] = data.get('sale_cost') / sale_inch
                    data['price_average'] = data.get('sale_price') / sale_inch
                else:
                    data['avg_cost_inch'] = 0
                    data['price_average'] = 0

            if data.get('id') or (not data.get('product_id') and not data.get('order_id')):
                data.pop('avg_cost')
                data.pop('avg_price')
                data.pop('avg_cost_inch')
                data.pop('price_average')
        return result

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
