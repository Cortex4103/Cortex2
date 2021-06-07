# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools, SUPERUSER_ID, _


class Users(models.Model):
    _inherit = "res.users"

    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    warehouse_id =  fields.Many2one('stock.warehouse', string="Warehouse")

    @api.onchange('first_name', 'last_name')
    def _onchange_name(self):
        self.name = self.first_name + " " + self.last_name if self.last_name else self.first_name

    @api.model
    def set_no_update_val(self):
        term_ids = [self.env.ref('account.account_payment_term_21days').id, self.env.ref('account.account_payment_term_30days').id,
                    self.env.ref('account.account_payment_term_45days').id, self.env.ref('account.account_payment_term_15days').id,]
        self.env['ir.model.data'].search([('res_id','in', term_ids), ('model','=','account.payment.term')]).write({'noupdate': False})