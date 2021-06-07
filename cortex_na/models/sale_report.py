# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    line_partner_id = fields.Many2one('res.partner', string='Sawmill')
    product_uom_qty = fields.Float('Qty Ordered', readonly=True, digits='New Cortex Precision')
    qty_delivered = fields.Float('Qty Delivered', readonly=True, digits='New Cortex Precision')
    qty_to_invoice = fields.Float('Qty To Invoice', readonly=True, digits='New Cortex Precision')
    qty_invoiced = fields.Float('Qty Invoiced', readonly=True,digits='New Cortex Precision')
    rem_delivery_qty = fields.Float('Qty to be delivered', readonly=True, digits='New Cortex Precision')
    rem_invoice_amount = fields.Float('Amount to be invoiced', readonly=True)
    delivered_amount = fields.Float('Amount to be delivered', readonly=True)
    net_price = fields.Float('Discounted Price')
    delivery_date = fields.Datetime('Delivery Date', readonly=True)
    type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product')
    ], string='Status')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields[
                'line_partner_id'] = ", l.partner_id as line_partner_id, t.type as type,l.net_price as net_price, CASE WHEN t.type != 'service' AND l.qty_delivered > 0 AND l.qty_invoiced = 0  THEN sum((l.qty_delivered - l.qty_invoiced) * l.net_price) WHEN t.type = 'service' THEN sum((l.product_uom_qty - l.qty_invoiced) * l.net_price) ELSE 0  END as rem_invoice_amount,CASE WHEN t.type != 'service' THEN sum(l.product_uom_qty - l.qty_delivered) ELSE 0 END as rem_delivery_qty, sum((CASE WHEN t.type != 'service' THEN l.product_uom_qty - l.qty_delivered ELSE 0 END) * l.net_price) as delivered_amount"
            # fields['line_partner_id'] = ", l.partner_id as line_partner_id,sum(l.product_uom_qty - l.qty_delivered) as rem_delivery_qty, sum((l.product_uom_qty - l.qty_invoiced) * l.net_price) as rem_invoice_amount"
        groupby += ', l.partner_id,t.type,l.qty_invoiced , l.qty_delivered,l.product_uom_qty,l.net_price'
        res = super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)
        return  res
