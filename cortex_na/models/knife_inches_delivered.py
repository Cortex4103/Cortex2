# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class KnifeInchesDeliveredCustom(models.Model):
    _name = "knife.inches.delivered.custom"
    _description = "Knife Inches Delivered Report"
    _auto = False
    _order = 'delivery_date desc'
    _rec_name = 'order_id'

    @api.model
    def _get_done_states(self):
        return ['sale', 'done', 'paid']

    name = fields.Char('Order Reference', readonly=True)
    delivery_date = fields.Datetime('Delivery Date', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
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
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)
    line_product_id = fields.Many2one('product.product', 'Sold Product', readonly=True)
    categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product')], string='Product Type', readonly=True)
    country_id = fields.Many2one('res.country', 'Customer Country', readonly=True)    
    location_dest_id = fields.Many2one('stock.location', 'To', readonly=True)
    qty_done = fields.Float('Quantity Done', readonly=True)
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Sales Done'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True)
    discount = fields.Float('Discount %', readonly=True)
    discount_amount = fields.Float('Discount Amount', readonly=True)
    line_partner_id = fields.Many2one('res.partner', string='Sawmill')
    order_id = fields.Many2one('sale.order', 'Order #', readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        picking_type = self.env['stock.picking.type'].search([('code','=','outgoing')])
        dest_location_id = self.env['stock.location'].search([('name','=','Customers')],limit=1)
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            min(l.id) as id,
            sml.product_id as product_id,
            l.product_id as line_product_id,
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
            sml.date as delivery_date,
            sml.location_dest_id as location_dest_id,
            sml.qty_done as qty_done,   
            sm.picking_type_id,          
            s.state as state,
            s.partner_id as partner_id,
            s.user_id as user_id,
            s.company_id as company_id,                        
            t.categ_id as categ_id,
            t.type as type,
            categ.category_display_in_report as category_display_in_report,
            p.product_tmpl_id,
            partner.country_id as country_id,
            l.discount as discount,
            sum((l.price_unit * l.discount / 100.0 / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END)) as discount_amount,
            s.id as order_id
        """

        for field in fields.values():
            select_ += field

        from_ = """
                stock_move_line sml
                    join stock_picking sp on sml.picking_id = sp.id
                    join stock_move sm on sp.id = sm.picking_id                    
                    join procurement_group pg on sp.group_id = pg.id
                    join sale_order s on pg.sale_id = s.id
                    join sale_order_line l on l.order_id = s.id
                    join res_partner partner on s.partner_id = partner.id
                        left join product_product p on (sml.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                                left join product_category categ on (t.categ_id = categ.id)
                    left join uom_uom u on (u.id=l.product_uom)
                    left join uom_uom u2 on (u2.id=t.uom_id)                    
                %s
        """ % from_clause

        groupby_ = """
            sml.product_id,
            l.partner_id,
            l.order_id,
            l.product_id,
            t.uom_id,
            t.categ_id,
            t.type,
            categ.category_display_in_report,
            s.name,
            sml.date,
            sml.location_dest_id,
            sml.qty_done,
            sm.picking_type_id,
            s.partner_id,
            s.user_id,
            s.company_id,            
            p.product_tmpl_id,
            partner.country_id,
            l.discount,
            s.id %s
        """ % (groupby)

        return """%s (SELECT %s FROM %s WHERE sml.product_id IS NOT NULL AND t.type IN ('product','consu') AND sml.state = 'done' AND categ.category_display_in_report = TRUE AND sml.location_dest_id = %s GROUP BY %s)""" % (with_, select_, from_, dest_location_id.id, groupby_)

    def init(self):        
        tools.drop_view_if_exists(self.env.cr, self._table) 
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
