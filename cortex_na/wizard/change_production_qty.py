# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ChangeProductionQty(models.TransientModel):
    _inherit = 'change.production.qty'

    def change_prod_qty(self):
        prod_dict = {}
        for wizard in self:
            production = wizard.mo_id
            prod_dict[production.id] = production.state
        res = super(ChangeProductionQty, self).change_prod_qty()
        for wizard in self:
            production = wizard.mo_id
            if prod_dict.get(production.id) == 'to_close':
                for move in production.service_charge_ids.filtered(lambda m: m.bom_line_id):
                    factor = 1
                    if move.product_uom_id.id != production.product_uom_id.id:
                        factor = production.product_uom_id._compute_quantity(production.product_qty,
                                                                       production.bom_id.product_uom_id) / (
                                 production.bom_id.product_qty or 1)
                    quantity = factor
                    if move.bom_charge_id:
                        if factor > 1:
                            factor = factor / (production.product_qty or 1)
                        quantity = (wizard.product_qty * move.bom_charge_id.quantity) * factor
                    move.quantity = quantity + move.quantity
                    move.onchange_price_quantity()
            else:
                for move in production.service_charge_ids.filtered(lambda m: m.bom_line_id):
                    factor = 1
                    if move.product_uom_id.id != production.product_uom_id.id:
                        factor = production.product_uom_id._compute_quantity(production.product_qty,
                                                                             production.bom_id.product_uom_id) / (
                            production.bom_id.product_qty or 1)
                    quantity = factor
                    if move.bom_charge_id:
                        if factor > 1:
                            factor = factor / (production.product_qty or 1)
                        quantity = (wizard.product_qty * move.bom_charge_id.quantity) * factor
                    move.quantity = quantity
                    move.onchange_price_quantity()
        return res
