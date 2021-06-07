# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class AccountPayments(models.Model):
    _inherit = "account.payment"

    check_number = fields.Char(string="Check Number", readonly=False, copy=False,
                               help="The selected journal is configured to print check numbers. If your pre-printed check paper already has numbers "
                                    "or if the current numbering is wrong, you can change it in the journal configuration page.")
    purchase_order_id = fields.Many2one('purchase.order', 'purchase_id', ondelete='cascade', copy=False)


class AccountPaymentRegisters(models.TransientModel):
    _inherit = "account.payment.register"

    check_number = fields.Char(string="Check Number", help="The selected journal is configured to print check numbers. If your pre-printed check paper already has numbers "
                                    "or if the current numbering is wrong, you can change it in the journal configuration page.")

    def _prepare_payment_vals(self, invoice):
        res = super(AccountPaymentRegisters, self)._prepare_payment_vals(invoice)
        res.update({
            'check_number': self.check_number,
        })
        return res
