# -*- coding: utf-8 -*-

import json

from odoo import api, models, _
from odoo.tools import float_round

class ReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    def _get_bom(self, bom_id=False, product_id=False, line_qty=False, line_id=False, level=False):
        bom = self.env['mrp.bom'].browse(bom_id)
        bom_quantity = line_qty
        if line_id:
            current_line = self.env['mrp.bom.line'].browse(int(line_id))
            bom_quantity = current_line.product_uom_id._compute_quantity(line_qty, bom.product_uom_id)
        # Display bom components for current selected product variant
        if product_id:
            product = self.env['product.product'].browse(int(product_id))
        else:
            product = bom.product_id or bom.product_tmpl_id.product_variant_id
        if product:
            attachments = self.env['mrp.document'].search(['|', '&', ('res_model', '=', 'product.product'),
            ('res_id', '=', product.id), '&', ('res_model', '=', 'product.template'), ('res_id', '=', product.product_tmpl_id.id)])
        else:
            product = bom.product_tmpl_id
            attachments = self.env['mrp.document'].search([('res_model', '=', 'product.template'), ('res_id', '=', product.id)])
        operations = []
        if bom.product_qty > 0:
            operations = self._get_operation_line(bom.routing_id, float_round(bom_quantity / bom.product_qty, precision_rounding=1, rounding_method='UP'), 0)
        company = bom.company_id or self.env.company
        lines = {
            'bom': bom,
            'bom_qty': bom_quantity,
            'bom_prod_name': product.display_name,
            'currency': company.currency_id,
            'product': product,
            'code': bom and bom.display_name or '',
            'price': product.uom_id._compute_price(product.with_context(force_company=company.id).standard_price, bom.product_uom_id) * bom_quantity,
            'total': sum([op['total'] for op in operations]),
            'level': level or 0,
            'operations': operations,
            'operations_cost': sum([op['total'] for op in operations]),
            'attachments': attachments,
            'operations_time': sum([op['duration_expected'] for op in operations])
        }
        component, total = self._get_bom_lines(bom, bom_quantity, product, line_id, level)
        service_charge ,total_service_charge = self._get_service_charges_(bom, bom_quantity, product, line_id, level)
        lines['components'] = component
        lines['service_charges'] = service_charge
        lines['total'] += total
        lines['total'] += total_service_charge
        return lines


    def _get_service_charges_(self, bom, bom_quantity, product, line_id, level):
        service_charges = []
        total = 0
        for line in bom.service_charge_ids:
            line_quantity = bom_quantity
            company = bom.company_id or self.env.company
            if bom.product_qty > 0:
                operations = self._get_operation_line(bom.routing_id,float_round(bom_quantity / bom.product_qty, precision_rounding=1,rounding_method='UP'), 0)
            quantity = line.quantity * line_quantity
            price = line.price_unit * line_quantity
            sub_total = line.subtotal * line_quantity
            sub_total = self.env.company.currency_id.round(sub_total)

            service_charges.append({
                'prod_id': line.product_id.id,
                'prod_name': line.product_id.display_name,
                'prod_qty': quantity,
                'prod_uom': line.product_uom_id.name,
                'prod_cost': price,
                'parent_id': bom.id,
                'line_id': line.id,
                'level': level or 0,
                'total': sub_total,

            })
            total += sub_total
        return service_charges, total



        bom = self.env['mrp.bom'].browse(bom_id)
        product = product_id or bom.product_id or bom.product_tmpl_id.product_variant_id
        data = self._get_bom(bom_id=bom_id, product_id=product.id, line_qty=qty)
        pdf_lines = get_sub_lines(bom, product, qty, False, 1)
        data['components'] = []
        data['service_charges'] = []
        data['lines'] = pdf_lines
        return data


