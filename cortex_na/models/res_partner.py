# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from werkzeug import urls

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    
    is_distributor = fields.Boolean(string='Is a Distributor')
    machine_parts_count = fields.Integer(string='Machine Parts', compute='_compute_installed_parts_ids')
    installed_parts_count = fields.Integer(string='Installed Parts', compute='_compute_installed_parts_ids')
    related_bom_count = fields.Integer(string='Installed BOM', compute='_compute_installed_bom')
    bom_ids = fields.Many2many('mrp.bom', string='BOM IDS')

    def _compute_installed_bom(self):
        for record in self:
            mrp_boms = self.env['mrp.bom'].search([('id','=', record.bom_ids.ids)])
            record.related_bom_count = len(mrp_boms)


    def _compute_installed_parts_ids(self):
        for partner in self:
            machine_parts = self.env['installed.part'].search([('partner_id', 'in', partner.ids)])
            installed_parts = self.env['installed.part.detail'].search([('install_part_id.partner_id', 'in', partner.ids)])
            partner.machine_parts_count = len(machine_parts)
            partner.installed_parts_count = len(installed_parts)

    @api.model
    def default_get(self, fields):
        res = super(ResPartner, self).default_get(fields)
        res['property_payment_term_id'] = self.env.ref('account.account_payment_term_30days').id
        return res

    @api.depends('street', 'zip', 'city', 'country_id', 'street2', 'state_id')
    def _compute_complete_address(self):
        for record in self:
            record.contact_address_complete = ''
            if record.street:
                record.contact_address_complete += record.street + ','
            if record.street2:
                record.contact_address_complete += record.street2 + ','
            if record.city:
                record.contact_address_complete += record.city + ','
            if record.state_id:
                record.contact_address_complete += record.state_id.code + ' '
            if record.zip:
                record.contact_address_complete += record.zip + ','
            if record.country_id:
                record.contact_address_complete += record.country_id.name

    def action_view_machine_parts(self):
        return {
            'name': _('Machine Center'),
            'res_model': 'installed.part',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id':self.id}
        }

    def action_view_installed_parts(self):
        return {
            'name': _('Installed Part'),
            'res_model': 'installed.part.detail',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('install_part_id.partner_id', '=', self.id)],
            'context': {'search_default_filter_frequency': 1}
        }

    def action_view_installed_bom(self):
        return {
            'name': _('Installed BOM'),
            'res_model': 'mrp.bom',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('id', '=', self.bom_ids.ids)],
        }

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        res.geo_localize()
        return res

    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        if vals.get('street') != None or vals.get('street2') != None or vals.get('city') != None or vals.get('state_id') != None or vals.get('zip') != None or vals.get('country_id') != None:
            self.geo_localize()
        return res

    def _clean_website(self, website):
        # url = urls.url_parse(website)
        # if not url.scheme:
            # if not url.netloc:
                # url = url.replace(netloc=url.path, path='')
            # website = url.replace(scheme='http').to_url()
        return website


