# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
import logging

from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    return_count = fields.Integer(string='Sale Order',compute="compute_order_count")
    purchase_count = fields.Integer(string='Purchase Order',compute="compute_purchase_order_count")
    expected_date = fields.Date(string="Expected Payment Date", copy=False)#readonly=True, states={'draft': [('readonly', False)]},
    invoice_date_due = fields.Date(string='Due Date', index=True, copy=False)#readonly=True,states={'draft': [('readonly', False)],'post': [('readonly', False)],}

    

    def _recompute_payment_terms_lines(self):
        ''' Compute the dynamic payment term lines of the journal entry.'''
        self.ensure_one()
        in_draft_mode = self != self._origin
        today = fields.Date.context_today(self)

        def _get_payment_terms_computation_date(self):
            ''' Get the date from invoice that will be used to compute the payment terms.
            :param self:    The current account.move record.
            :return:        A datetime.date object.
            '''
            if self.invoice_payment_term_id:
                return self.invoice_date or today
            else:
                return self.invoice_date_due or self.invoice_date or today

        def _get_payment_terms_account(self, payment_terms_lines):
            ''' Get the account from invoice that will be set as receivable / payable account.
            :param self:                    The current account.move record.
            :param payment_terms_lines:     The current payment terms lines.
            :return:                        An account.account record.
            '''
            if payment_terms_lines:
                # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                return payment_terms_lines[0].account_id
            elif self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    return self.partner_id.property_account_receivable_id
                else:
                    return self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=', 'receivable' if self.type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'),
                ]
                return self.env['account.account'].search(domain, limit=1)

        def _compute_payment_terms(self, date, total_balance, total_amount_currency):
            ''' Compute the payment terms.
            :param self:                    The current account.move record.
            :param date:                    The date computed by '_get_payment_terms_computation_date'.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
            '''

            if not self.env.context.get('manual') :
                if self.invoice_payment_term_id:
                    to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date, currency=self.currency_id)
                    if self.currency_id != self.company_id.currency_id:
                        # Multi-currencies.
                        to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date, currency=self.currency_id)
                        return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
                    else:
                        # Single-currency.
                        return [(b[0], b[1], 0.0) for b in to_compute]

                else:
                    if self.env.context.get('manual'):
                        return [(fields.Date.to_string(self.invoice_date_due), total_balance, total_amount_currency)]
                    else:
                        return [(fields.Date.to_string(date), total_balance, total_amount_currency)]
            else:
                if self.env.context.get('manual'):
                    return [(fields.Date.to_string(self.invoice_date_due), total_balance, total_amount_currency)]
                else:
                    return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

        def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
            ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
            :param self:                    The current account.move record.
            :param existing_terms_lines:    The current payment terms lines.
            :param account:                 The account.account record returned by '_get_payment_terms_account'.
            :param to_compute:              The list returned by '_compute_payment_terms'.
            '''
            # As we try to update existing lines, sort them by due date.
            existing_terms_lines = existing_terms_lines.sorted(lambda line: line.date_maturity or today)
            existing_terms_lines_index = 0

            # Recompute amls: update existing line or create new one for each payment term.
            new_terms_lines = self.env['account.move.line']
            for date_maturity, balance, amount_currency in to_compute:
                if self.journal_id.company_id.currency_id.is_zero(balance) and len(to_compute) > 1:
                    continue

                if existing_terms_lines_index < len(existing_terms_lines):
                    # Update existing line.
                    candidate = existing_terms_lines[existing_terms_lines_index]
                    existing_terms_lines_index += 1
                    candidate.update({
                        'date_maturity': date_maturity,
                        'amount_currency': -amount_currency,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                    })
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                    candidate = create_method({
                        'name': self.invoice_payment_ref or '',
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'quantity': 1.0,
                        'amount_currency': -amount_currency,
                        'date_maturity': date_maturity,
                        'move_id': self.id,
                        'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                        'account_id': account.id,
                        'partner_id': self.commercial_partner_id.id,
                        'exclude_from_invoice_tab': True,
                    })
                new_terms_lines += candidate
                if in_draft_mode:
                    candidate._onchange_amount_currency()
                    candidate._onchange_balance()
            return new_terms_lines

        existing_terms_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        others_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        total_balance = sum(others_lines.mapped('balance'))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        if not others_lines:
            self.line_ids -= existing_terms_lines
            return

        computation_date = _get_payment_terms_computation_date(self)
        account = _get_payment_terms_account(self, existing_terms_lines)
        to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)
        new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)

        # Remove old terms lines that are no longer needed.
        self.line_ids -= existing_terms_lines - new_terms_lines

        if new_terms_lines:
            self.invoice_payment_ref = new_terms_lines[-1].name or ''
            if self.env.context.get('manual'):
                self.invoice_date_due = self.invoice_date_due
            else:
                self.invoice_date_due = new_terms_lines[-1].date_maturity


    @api.onchange('invoice_date_due')
    def hard_reset_invoice_date_due(self):
        self.env.context = dict(self.env.context)
        self.env.context.update({'manual': 'manual'})
        # self._onchange_recompute_dynamic_lines()
        self._recompute_payment_terms_lines()

    @api.onchange('line_ids', 'invoice_payment_term_id', 'invoice_cash_rounding_id',
                  'invoice_vendor_bill_id')
    def _onchange_recompute_dynamic_lines(self):
        self._recompute_dynamic_lines()


    @api.depends('invoice_origin')
    def compute_order_count(self):
        for record in self:
            if record.type == 'out_invoice' or record.type == 'out_refund':
                sale_order = self.env['sale.order'].search([('name', '=', record.invoice_origin)])
                record.return_count = len(sale_order)
            else:
                record.return_count = 0

    @api.depends('invoice_origin')
    def compute_purchase_order_count(self):
        for record in self:
            if record.type == 'in_invoice' or record.type == 'in_refund':
                purchase_order = self.env['purchase.order'].search([('name', '=', record.invoice_origin)])
                record.purchase_count = len(purchase_order)
            else:
                record.purchase_count = 0

    def action_view_purchase_order(self):
        if self.type == 'in_invoice' or self.type == 'in_refund':
            purchase_order = self.env['purchase.order'].search([('name', '=', self.invoice_origin)])
            action = self.env.ref('purchase.purchase_form_action').read([])[0]
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = purchase_order.id
        return action

    def action_view_sale_order(self):
        if self.type == 'out_invoice' or self.type == 'out_refund':
            sale_order = self.env['sale.order'].search([('name', '=', self.invoice_origin)])
            action = self.env.ref('sale.action_orders').read([])[0]
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = sale_order.id
        return action

    def button_create_landed_costs(self):
        self.ensure_one()
        landed_costs_lines = self.line_ids.filtered(lambda line: line.is_landed_costs_line)

        landed_costs = self.env['stock.landed.cost'].create({
            'vendor_bill_id': self.id,
            'cost_lines': [(0, 0, {
                'product_id': l.product_id.id,
                'name': l.product_id.name,
                'account_id': l.product_id.product_tmpl_id.get_product_accounts()['stock_input'].id,
                'price_unit': l.price_subtotal,
                'split_method': 'by_weight',
            }) for l in landed_costs_lines],
        })
        action = self.env.ref('stock_landed_costs.action_stock_landed_cost').read()[0]
        res = dict(action, view_mode='form', res_id=landed_costs.id, views=[(False, 'form')])
        company_currency = self.env.company.currency_id
        if self.currency_id.id != company_currency.id:
            if landed_costs:
                for line in landed_costs.cost_lines:
                    line.price_unit = line.price_unit * company_currency.rate / (self.currency_id.rate or 1)

        return res





class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    price_unit = fields.Float(string='Unit Price', digits='New Cortex Product Precision')
    quantity = fields.Float(string='Quantity',
                            default=1, digits='New Cortex Precision',
                            help="The optional quantity expressed by this line, eg: number of product sold. "
                                 "The quantity is not a legal requirement but is very useful for some reports.")
    discounted_price = fields.Float('Discounted Price', digits=dp.get_precision('Discount'))
    is_generated_entry = fields.Boolean(string="Is Generated Entry?", default=False)
    margin = fields.Float(string='Margin%',digits='New Knife Precision' )
    categ_id = fields.Many2one('product.category', 'Category', compute='_compute_product_categories', store=True)

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}

        # Compute 'price_subtotal'.
        price_unit_wo_discount = self.discounted_price or price_unit * (1 - (discount / 100.0))
        price_decimal = float("{0:.4f}".format(price_unit_wo_discount))
        subtotal = quantity * price_decimal

        # Compute 'price_total'.
        if taxes:
            taxes_res = taxes._origin.compute_all(price_decimal,
                                                  quantity=quantity, currency=currency, product=product,
                                                  partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        return res

    @api.onchange('discount', 'price_unit')
    def _onchange_discount_line(self):
        # self.update({'discounted_price' : self.price_unit - ((self.price_unit * self.discount) / 100)})
        self.discounted_price =  self.price_unit - ((self.price_unit * self.discount) / 100)

    def create(self,values):
        if self._context.get('params') and self._context.get('params').get('model') == 'sale.order':
            pass
        else:
            if isinstance(values, list):
                for line in values:
                    if line.get('price_unit') and line.get('discount'):
                        line['discounted_price'] = line.get('price_unit') - ((line.get('price_unit') * line.get('discount')) / 100)
            elif values.get('price_unit') and values.get('discount'):
                 values['discounted_price'] = values.get('price_unit') - ((values.get('price_unit') * values.get('discount')) / 100)
        return super(AccountMoveLine, self).create(values)

    def write(self, values):
        if values.get('price_unit') or values.get('discount'):
            unit_price = values.get('price_unit') if values.get('price_unit') else self.price_unit
            discount = values.get('discount') if values.get('discount') else self.discount
            values['discounted_price'] = unit_price - ((unit_price * discount)/100)
        return super(AccountMoveLine, self).write(values)

    @api.depends('product_id','product_id.categ_id')
    def _compute_product_categories(self):
            for record in self:
                if record.product_id:
                    record.categ_id=record.product_id.categ_id.id
                    # self.write({'categ_id': self.product_id.categ_id.id})
                else:
                    record.categ_id = False


    @api.onchange('discounted_price')
    def _onchange_net_price(self):
        if self.price_unit:
            self.discount = (self.price_unit - self.discounted_price) * 100 / self.price_unit

    def cron_create_journal_entry(self, inventory_adjustment_id, journal_id, reference=None):
        if inventory_adjustment_id and journal_id:
            received_account = self.env['account.account'].search([('code', '=', '110200'), ('name', '=', 'Stock Interim (Received)')])
            delivered_account = self.env['account.account'].search([('code', '=', '110300'), ('name', '=', 'Stock Interim (Delivered)')])
            if received_account:
                received_account_lines = self.search([('move_id.state', '=', 'posted'), ('account_id', '=', received_account.id), ('is_generated_entry', '=', False), '|', ('name', 'ilike', 'Product Quantity Updated'), ('name', 'ilike', 'INV:Inventory')])
                _logger.info(_("Received Records: %s" % (received_account_lines)))
                for account_line in received_account_lines:
                    name = reference or account_line.move_id.ref
                    account_dict = {'ref': name, 'date': account_line.date, 'journal_id': journal_id}
                    line_list = []
                    if account_line.credit:
                        debit = account_line.credit
                        credit = 0
                    else:
                        credit = account_line.debit
                        debit = 0
                    line_list.append((0, 0, {'account_id': account_line.account_id.id,
                                             'credit': credit,
                                             'debit': debit,
                                             'date': account_line.date,
                                             'name': name,
                                             'quantity': account_line.quantity,
                                             'product_id': account_line.product_id.id,
                                             'is_generated_entry': True}))
                    line_list.append((0, 0, {'account_id': inventory_adjustment_id,
                                             'credit': debit,
                                             'debit': credit,
                                             'date': account_line.date,
                                             'name': name,
                                             'quantity': account_line.quantity,
                                             'product_id': account_line.product_id.id,
                                             'is_generated_entry': True}))
                    account_dict['line_ids'] = line_list
                    account = self.env['account.move'].create(account_dict)
                    account.action_post()
                    account_line.is_generated_entry = True
                    self.env.cr.commit()
                    _logger.info(_("Successfully Created Journal enrtry for (received): %s %s" % (account_line, name)))
            if delivered_account:
                delivered_account_lines = self.search(
                    [('move_id.state', '=', 'posted'), ('account_id', '=', delivered_account.id),
                     ('is_generated_entry', '=', False), '|', ('name', 'ilike', 'Product Quantity Updated'),
                     ('name', 'ilike', 'INV:Inventory')])
                _logger.info(_("Deliverd Records: %s" % (delivered_account_lines)))
                for account_line in delivered_account_lines:
                    name = reference or account_line.move_id.ref
                    account_dict = {'ref': name, 'date': account_line.date, 'journal_id': journal_id}
                    line_list = []
                    if account_line.credit:
                        debit = account_line.credit
                        credit = 0
                    else:
                        credit = account_line.debit
                        debit = 0
                    line_list.append((0, 0, {'account_id': account_line.account_id.id,
                                             'credit': credit,
                                             'debit': debit,
                                             'date': account_line.date,
                                             'name': name,
                                             'quantity': account_line.quantity,
                                             'product_id': account_line.product_id.id,
                                             'is_generated_entry': True}))
                    line_list.append((0, 0, {'account_id': inventory_adjustment_id,
                                             'credit': debit,
                                             'debit': credit,
                                             'date': account_line.date,
                                             'name': name,
                                             'quantity': account_line.quantity,
                                             'product_id': account_line.product_id.id,
                                             'is_generated_entry': True}))
                    account_dict['line_ids'] = line_list
                    account = self.env['account.move'].create(account_dict)
                    account.action_post()
                    account_line.is_generated_entry = True
                    self.env.cr.commit()
                    _logger.info(_("Successfully Created Journal enrtry for (delivered): %s %s" % (account_line, name)))

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(AccountMoveLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                           orderby=orderby, lazy=lazy)
        for data in res:
            if data.get('credit', 0) > 0 :
                data['margin'] = (data.get('credit') - data.get('debit'))/data.get('credit')
            else:
                data['margin'] = 0
        return res

   
