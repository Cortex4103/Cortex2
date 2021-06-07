# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo import tools
from odoo.exceptions import Warning
import logging

_logger = logging.getLogger(__name__)


class ManufacturingProcessReport(models.Model):
    _name = "manufacturing.knife.process.report"
    _description = "Knife Processed by Vendor"
    _auto = False
    name = fields.Char(
        'Order Reference', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    knife_inches = fields.Float(string="knife inches", readonly=True)
    date_planned_start = fields.Datetime('Planned Date')
    product_qty = fields.Float('knives', readonly=True, digits='Product Unit of Measure')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    code = fields.Selection([('incoming', 'Receipt'), ('outgoing', 'Delivery'), ('internal', 'Internal Transfer'), ('mrp_operation', 'Manufacturing')], 'Type of Operation', readonly=True, store=True,)
    location_src_id = fields.Many2one('stock.location', 'Components Location', readonly=True)
    total_inches = fields.Float('Total Inches', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('planned', 'Planned'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='State', readonly=True)


    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            min(l.id) as id,
            s.name as name,
            s.product_id as product_id,
            sum(s.product_qty / u.factor * u2.factor) as product_qty,
            (sum(s.product_qty / u.factor * u2.factor)) *  t.length as knife_inches,
            s.warehouse_id as warehouse_id,
            s.code as code,
            s.location_src_id,
            s.state,
            s.partner_id,
            s.date_planned_start
            
        """

        for field in fields.values():
            select_ += field

        from_ = """
                    stock_move l
                    join mrp_production s on (l.production_id=s.id)
                     join product_product p on (s.product_id=p.id)
                     join product_template t on (p.product_tmpl_id=t.id)
                     join uom_uom u on (u.id=s.product_uom_id)
                     join uom_uom u2 on (u2.id=t.uom_id)
                %s
        """ % from_clause

        groupby_ = """
            s.product_id,
            s.name,
            s.product_qty,
            s.warehouse_id,
            s.code,
            t.length,
            s.location_src_id,
            s.state,
            s.partner_id,
            s.id,
            s.date_planned_start %s
        """ % (groupby)

        return """%s (SELECT %s FROM %s WHERE s.product_id IS NOT NULL GROUP BY %s)""" % (with_, select_, from_, groupby_)

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))