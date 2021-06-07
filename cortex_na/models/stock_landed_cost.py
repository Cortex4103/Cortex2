# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class AdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'
    _description = 'Valuation Adjustment Lines'

    length = fields.Float(
        'Length', default=1.0)

class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    mrp_production_ids = fields.Many2many(
        'mrp.production', string='Manufacturing Orders',
        copy=False, states={'done': [('readonly', True)]})
    landed_cost_selection = fields.Selection([('transfers', 'Transfers'), ('mo_orders', 'Manufacturing Orders')], string='Landed Cost on', default='transfers')
    batch_production_id = fields.Many2one('batch.production',  string='Batch Production')

    @api.onchange('batch_production_id')
    def onchange_batch_production(self):
        if self.batch_production_id:
            mrp_obj = self.env['mrp.production'].search([('batch_production_id', '=', self.batch_production_id.id)])
            not_done_mrp = [mrp.name for mrp in mrp_obj if not mrp.state == 'done']
            if not_done_mrp:
                raise UserError(_("Please first done Manufaturing Orders are: %s" % (','.join([str(not_done) for not_done in not_done_mrp]))))
            self.mrp_production_ids = [(6, 0, mrp_obj.ids)]
        else:
            self.mrp_production_ids = None

    def get_valuation_lines(self):
        lines = []
        if self.landed_cost_selection == 'transfers':
            for move in self.mapped('picking_ids').mapped('move_lines'):
                # it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
                if move.product_id.valuation != 'real_time' or move.product_id.cost_method not in ('fifo', 'average') or move.state == 'cancel':
                    continue
                vals = {
                    'product_id': move.product_id.id,
                    'move_id': move.id,
                    'quantity': move.product_qty,
                    'former_cost': sum(move.stock_valuation_layer_ids.mapped('value')),
                    'weight': move.product_id.weight * move.product_qty,
                    'volume': move.product_id.volume * move.product_qty,
                    'length': move.product_id.length * move.product_qty
                }
                lines.append(vals)
            if not lines and self.mapped('picking_ids'):
                raise UserError(_(
                    "You cannot apply landed costs on the chosen transfer(s). Landed costs can only be applied for products with automated inventory valuation and FIFO or average costing method."))
        else:
            for move in self.mapped('mrp_production_ids').mapped('move_finished_ids'):
                if move.product_id.valuation != 'real_time' or move.product_id.cost_method not in ('fifo', 'average') or move.state == 'cancel':
                    continue
                vals = {
                    'product_id': move.product_id.id,
                    'move_id': move.id,
                    'quantity': move.product_qty,
                    'former_cost': sum(move.stock_valuation_layer_ids.mapped('value')),
                    'weight': move.product_id.weight * move.product_qty,
                    'volume': move.product_id.volume * move.product_qty,
                    'length': move.product_id.length * move.product_qty
                }
                lines.append(vals)

            if not lines and self.mapped('mrp_production_ids'):
                raise UserError(_("You cannot apply landed costs on the chosen Menufecturing Order(s). Landed costs can only be applied for products with automated inventory valuation and FIFO or average costing method."))

        return lines

    def button_validate(self):
        if any(cost.state != 'draft' for cost in self):
            raise UserError(_('Only draft landed costs can be validated'))
        if self.landed_cost_selection == 'transfers':
            if not all(cost.picking_ids for cost in self):
                raise UserError(_('Please define the transfers on which those additional costs should apply.'))
        else:
            if not all(cost.mrp_production_ids for cost in self):
                raise UserError(_('Please define the manufacturing orders on which those additional costs should apply.'))
        cost_without_adjusment_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))
        for cost in self:
            move = self.env['account.move']
            move_vals = {
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'line_ids': [],
                'type': 'entry',
            }
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                remaining_qty = sum(line.move_id.stock_valuation_layer_ids.mapped('remaining_qty'))
                if remaining_qty:
                    linked_layer = line.move_id.stock_valuation_layer_ids[0]


                # Prorate the value at what's still in stock
                cost_to_add = (remaining_qty / line.move_id.product_qty) * line.additional_landed_cost
                if not cost.company_id.currency_id.is_zero(cost_to_add):
                    valuation_layer = self.env['stock.valuation.layer'].create({
                        'value': cost_to_add,
                        'unit_cost': 0,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'stock_valuation_layer_id': linked_layer.id,
                        'description': cost.name,
                        'stock_move_id': line.move_id.id,
                        'product_id': line.move_id.product_id.id,
                        'stock_landed_cost_id': cost.id,
                        'company_id': cost.company_id.id,
                    })
                    move_vals['stock_valuation_layer_ids'] = [(6, None, [valuation_layer.id])]
                    linked_layer.remaining_value += cost_to_add
                # Update the AVCO
                product = line.move_id.product_id
                if product.cost_method == 'average' and not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                    product.with_context(force_company=self.company_id.id).sudo().standard_price += cost_to_add / product.quantity_svl
                # `remaining_qty` is negative if the move is out and delivered proudcts that were not
                # in stock.
                qty_out = 0
                if line.move_id._is_in():
                    qty_out = line.move_id.product_qty - remaining_qty
                elif line.move_id._is_out():
                    qty_out = line.move_id.product_qty
                move_vals['line_ids'] += line._create_accounting_entries(move, qty_out)

            move = move.create(move_vals)
            cost.write({'state': 'done', 'account_move_id': move.id})
            move.post()

            if cost.vendor_bill_id and cost.vendor_bill_id.state == 'posted' and cost.company_id.anglo_saxon_accounting:
                all_amls = cost.vendor_bill_id.line_ids | cost.account_move_id.line_ids
                for product in cost.cost_lines.product_id:
                    accounts = product.product_tmpl_id.get_product_accounts()
                    input_account = accounts['stock_input']
                    all_amls.filtered(lambda aml: aml.account_id == input_account and not aml.reconciled).reconcile()
        return True

    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()
        digits = self.env['decimal.precision'].precision_get('Product Price')
        towrite_dict = {}
        if self.landed_cost_selection == 'transfers':
            for cost in self.filtered(lambda cost: cost.picking_ids):
                method_list = [line.split_method for line in cost.cost_lines]
                if 'by_per' in method_list:
                    raise UserError(_('"By Percentage" spliting method in "Additional Costs" can be used in only Manufacturing Orders.'))
                production_qty = {}
                production_weight = {}
                production_volume = {}
                production_cost = {}
                production_inches = {}
                production_move_line = {}
                production_moves = {move.id: move.picking_id.id for move in
                                    self.mapped('picking_ids').mapped('move_lines')}
                all_val_line_values = cost.get_valuation_lines()
                production_list = []
                for val_line_values in all_val_line_values:
                    for cost_line in cost.cost_lines:
                        val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id})
                        self.env['stock.valuation.adjustment.lines'].create(val_line_values)
                    move_id = val_line_values.get('move_id')
                    production_id = production_moves.get(move_id)

                    former_cost = val_line_values.get('former_cost', 0.0)
                    former_cost = tools.float_round(former_cost, precision_digits=digits) if digits else former_cost
                    if production_id in production_list:
                        production_qty[production_id] += val_line_values.get('quantity', 0.0)
                        production_weight[production_id] += val_line_values.get('weight', 0.0)
                        production_volume[production_id] += val_line_values.get('volume', 0.0)
                        production_inches[production_id] += val_line_values.get('length', 0.0)
                        production_cost[production_id] += former_cost
                        production_move_line[production_id] += 1
                    else:
                        production_qty[production_id] = val_line_values.get('quantity', 0.0)
                        production_weight[production_id] = val_line_values.get('weight', 0.0)
                        production_volume[production_id] = val_line_values.get('volume', 0.0)
                        production_inches[production_id] = val_line_values.get('length', 0.0)
                        production_cost[production_id] = former_cost
                        production_move_line[production_id] = 1
                        production_list.append(production_id)

                for line in cost.cost_lines:
                    value_split = 0.0
                    for valuation in cost.valuation_adjustment_lines:
                        value = 0.0
                        picking_id = valuation.move_id.picking_id.id
                        if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                            if line.split_method == 'by_quantity':
                                if production_qty.get(picking_id):
                                    per_unit = (line.price_unit / len(cost.picking_ids.ids))
                                    value = valuation.quantity * per_unit / production_qty.get(picking_id)
                                else:
                                    raise UserError(_('Please Set quantity of product "%s" of Transfers "%s" is greater than zero.' % (
                                    valuation.move_id.product_id.name, valuation.move_id.picking_id.name)))
                            elif line.split_method == 'by_weight':
                                if production_weight.get(picking_id):
                                    per_unit = (line.price_unit / len(cost.picking_ids.ids))
                                    value = valuation.weight * per_unit / production_weight.get(picking_id)
                                else:
                                    raise UserError(_('Please Set weight of product "%s" of Transfers "%s" is greater than zero.' % (
                                    valuation.move_id.product_id.name, valuation.move_id.picking_id.name)))
                            elif line.split_method == 'by_volume':
                                if production_volume.get(picking_id):
                                    per_unit = (line.price_unit / len(cost.picking_ids.ids))
                                    value = valuation.volume * per_unit / production_volume.get(picking_id)
                                else:
                                    raise UserError(_('Please Set volume of product "%s" of Transfers "%s" is greater than zero.' % (
                                    valuation.move_id.product_id.name, valuation.move_id.picking_id.name)))
                            elif line.split_method == 'equal':
                                value = (line.price_unit / (production_move_line.get(picking_id) * len(cost.picking_ids.ids)))
                            elif line.split_method == 'by_current_cost_price':
                                if production_cost.get(picking_id):
                                    per_unit = (line.price_unit / len(cost.picking_ids.ids))
                                    value = valuation.former_cost * per_unit / production_cost.get(picking_id)
                                else:
                                    raise UserError(_('Please Set cost price of product "%s" of Transfers "%s" is greater than zero.' % (
                                    valuation.move_id.product_id.name, valuation.move_id.picking_id.name)))
                            elif line.split_method == 'by_inches':
                                if production_inches.get(picking_id):
                                    per_unit = (line.price_unit / len(cost.picking_ids.ids))
                                    value = valuation.length * per_unit / production_inches.get(picking_id)
                                else:
                                    raise UserError(_('Please Set length of product "%s" of Transfers "%s" is greater than zero.' % (
                                    valuation.move_id.product_id.name, valuation.move_id.picking_id.name)))
                            else:
                                value = (line.price_unit / (
                                production_move_line.get(picking_id) * len(cost.picking_ids.ids)))

                            if digits:
                                value = tools.float_round(value, precision_digits=digits, rounding_method='UP')
                                fnc = min if line.price_unit > 0 else max
                                value = fnc(value, line.price_unit - value_split)
                                value_split += value

                            if valuation.id not in towrite_dict:
                                towrite_dict[valuation.id] = value
                            else:
                                towrite_dict[valuation.id] += value
            for key, value in towrite_dict.items():
                AdjustementLines.browse(key).write({'additional_landed_cost': value})
        else:
            AdjustementLines = self.env['stock.valuation.adjustment.lines']
            AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()
            digits = self.env['decimal.precision'].precision_get('Product Price')
            towrite_dict = {}
            for cost in self.filtered(lambda cost: cost.mrp_production_ids):
                production_qty = {}
                production_weight = {}
                production_volume = {}
                production_cost = {}
                production_inches = {}
                production_move_line = {}
                production_moves = {move.id: move.production_id.id for move in
                                    self.mapped('mrp_production_ids').mapped('move_finished_ids')}
                production_list = []
                all_val_line_values = cost.get_valuation_lines()
                for val_line_values in all_val_line_values:
                    for cost_line in cost.cost_lines:
                        val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id})
                        self.env['stock.valuation.adjustment.lines'].create(val_line_values)
                    move_id = val_line_values.get('move_id')
                    production_id = production_moves.get(move_id)

                    former_cost = val_line_values.get('former_cost', 0.0)
                    former_cost = tools.float_round(former_cost, precision_digits=digits) if digits else former_cost

                    if production_id in production_list:
                        production_qty[production_id] += val_line_values.get('quantity', 0.0)
                        production_weight[production_id] += val_line_values.get('weight', 0.0)
                        production_volume[production_id] += val_line_values.get('volume', 0.0)
                        production_inches[production_id] += val_line_values.get('length', 0.0)
                        production_cost[production_id] += former_cost
                        production_move_line[production_id] += 1
                    else:
                        production_qty[production_id] = val_line_values.get('quantity', 0.0)
                        production_weight[production_id] = val_line_values.get('weight', 0.0)
                        production_volume[production_id] = val_line_values.get('volume', 0.0)
                        production_inches[production_id] = val_line_values.get('length', 0.0)
                        production_cost[production_id] = former_cost
                        production_move_line[production_id] = 1
                        production_list.append(production_id)

                for line in cost.cost_lines:
                    value_split = 0.0
                    for valuation in cost.valuation_adjustment_lines:
                        value = 0.0
                        production_id = valuation.move_id.production_id.id
                        if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                            if line.split_method == 'by_quantity':
                                if production_qty.get(production_id):
                                    per_unit = (line.price_unit / len(cost.mrp_production_ids.ids))
                                    value = valuation.quantity * per_unit / production_qty.get(production_id)
                                else:
                                    raise UserError(_('Please Set quantity of product "%s" of Manufacturing order "%s" is greater than zero.' % (valuation.move_id.product_id.name, valuation.move_id.production_id.name)))
                            elif line.split_method == 'by_weight':
                                if production_weight.get(production_id):
                                    per_unit = (line.price_unit / len(cost.mrp_production_ids.ids))
                                    value = valuation.weight * per_unit / production_weight.get(production_id)
                                else:
                                    raise UserError(_('Please Set weight of product "%s" of Manufacturing order "%s" is greater than zero.' % (valuation.move_id.product_id.name, valuation.move_id.production_id.name)))
                            elif line.split_method == 'by_volume':
                                if production_volume.get(production_id):
                                    per_unit = (line.price_unit / len(cost.mrp_production_ids.ids))
                                    value = valuation.volume * per_unit / production_volume.get(production_id)
                                else:
                                    raise UserError(_('Please Set volume of product "%s" of Manufacturing order "%s" is greater than zero.' % (valuation.move_id.product_id.name, valuation.move_id.production_id.name)))
                            elif line.split_method == 'equal':
                                value = (line.price_unit / (production_move_line.get(production_id) * len(cost.mrp_production_ids.ids)))
                            elif line.split_method == 'by_current_cost_price':
                                if production_cost.get(production_id):
                                    per_unit = (line.price_unit / len(cost.mrp_production_ids.ids))
                                    value = valuation.former_cost * per_unit / production_cost.get(production_id)
                                else:
                                    raise UserError(_('Please Set cost price of product "%s" of Manufacturing order "%s" is greater than zero.' % (valuation.move_id.product_id.name, valuation.move_id.production_id.name)))
                            elif line.split_method == 'by_per':
                                value = line.price_unit * valuation.move_id.charges_per / (100 * len(cost.mrp_production_ids.ids))
                            elif line.split_method == 'by_inches':
                                if production_inches.get(production_id):
                                    per_unit = (line.price_unit /len(cost.mrp_production_ids.ids))
                                    value = valuation.length * per_unit / production_inches.get(production_id)
                                else:
                                    raise UserError(_('Please Set length of product "%s" of Manufacturing order "%s" is greater than zero.' % (valuation.move_id.product_id.name, valuation.move_id.production_id.name)))
                            else:
                                value = (line.price_unit / (production_move_line.get(production_id) * len(cost.mrp_production_ids.ids)))

                            if digits:
                                value = tools.float_round(value, precision_digits=digits, rounding_method='UP')
                                fnc = min if line.price_unit > 0 else max
                                value = fnc(value, line.price_unit - value_split)
                                value_split += value

                            if valuation.id not in towrite_dict:
                                towrite_dict[valuation.id] = value
                            else:
                                towrite_dict[valuation.id] += value
            for key, value in towrite_dict.items():
                AdjustementLines.browse(key).write({'additional_landed_cost': value})
        return True


class StockLandedCostLines(models.Model):
    _inherit = 'stock.landed.cost.lines'

    split_method = fields.Selection(selection_add=[('by_per', 'By Percentage'),
    ('by_inches', 'By Inches')], string='Split Method', required=True)

    @api.onchange('product_id')
    def onchange_product_id(self):
        super(StockLandedCostLines, self).onchange_product_id()
        self.split_method = 'by_weight'
