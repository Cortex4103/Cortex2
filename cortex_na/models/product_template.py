# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
import logging
import base64

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, RedirectWarning, UserError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"


    mrp_product_qty = fields.Float('Manufactured',digits='New Cortex Precision',
                                   compute='_compute_mrp_product_qty', compute_sudo=False)
    drawing_no = fields.Char('Drawing #', track_visibility='onchange')
    default_code = fields.Char(
        'Part Number', compute='_compute_default_code',
        inverse='_set_default_code', store=True)
    drawing_version = fields.Selection([('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D'), ('e', 'E'), ('f', 'F'), ('g', 'G'), ('h', 'H')], string='Drawing Version')
    drawing_pdf = fields.Binary(string='Drawing pdf')
    file_name = fields.Char(string='FileName')
    sales_count = fields.Float(compute='_compute_sales_count', string='Sold', digits='New Cortex Precision')
    purchased_product_qty = fields.Float(compute='_compute_purchased_product_qty', string='Purchased',digits='New Cortex Precision')
    length = fields.Float(string="Length",compute='_compute_length', inverse='_set_length',store=True)
    running_avg_cost = fields.Float(string="Running AVG. cost",compute='_compute_running_avg_cost',digits='New Cortex Precision')
    machine_parts_count = fields.Integer(string='Machine Part', compute='_compute_installed_parts_ids')
    installed_parts_count = fields.Integer(string='Installed Part', compute='_compute_installed_parts_ids')
    vendor_product_code_store = fields.Char(string="Store Vendor Code",compute="compute_store_vendor_code",store=True)
    drawing_number = fields.Char(string='Drawing #', compute='_compute_drawing_number', store=True)
    service_products = fields.Many2many('product.product', string='Service Products')
    cornomics_detail_ids = fields.One2many('cornomics.company.detail', 'product_tmpl_id',
                                           string='Cornomics Detail Line')
    active = fields.Boolean('Active', default=True, tracking=True,
                            help="If unchecked, it will allow you to hide the product without removing it.")
    installed_quantity = fields.Float(string="Installed Quantity",compute="_compute_installed_parts_ids",digits='New Cortex Precision' )
    minimum_stock = fields.Integer('Minimum Stock',default=50)
    unit_or_per = fields.Selection([('per','%'),('unit','Unit')],default='per')
    product_with_vendor_ids = fields.One2many('product.with.vendor','product_template_id', string="Manufacturing Order")    
    list_of_attachment = fields.One2many('drawing.files','template_id',string="List of Attachment")

    @api.onchange('drawing_no', 'drawing_version')
    def onchange_drawing_no(self):
        # If the drawing no is not exist then no need for drawing version so removed value of it
        if not self.drawing_no and self.drawing_version:
            self.drawing_version = ''

    @api.depends('drawing_no', 'drawing_version')
    def _compute_drawing_number(self):
        for record in self:
            drawing_number = record.drawing_no
            if record.drawing_version and drawing_number:
                drawing_number = drawing_number + ' - ' + (record.drawing_version).upper()
            record.drawing_number = drawing_number

    @api.depends('seller_ids.product_code')
    def compute_store_vendor_code(self):
        for record in self:
            total_product_code =''
            for line in record.seller_ids:
                if line.product_code:
                    if total_product_code:
                        total_product_code += ',' +  line.product_code
                    else:
                        total_product_code = line.product_code
            record.vendor_product_code_store = total_product_code

    @api.depends('product_variant_id')
    def _compute_installed_parts_ids(self):
        for product in self:
            machine_parts = self.env['installed.part'].search([('installed_part_detail_id.product_id', 'in', product.product_variant_id.ids)])
            installed_parts = self.env['installed.part.detail'].search(
                [('product_id', 'in',  product.product_variant_id.ids)])

            total=0
            for record in installed_parts:
                total += record.installed_knife

            product.installed_quantity = total
            product.machine_parts_count = len(machine_parts)
            product.installed_parts_count = len(installed_parts)


    def action_view_machine_parts(self):
        return {
            'name': _('Machine Center'),
            'res_model': 'installed.part',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('installed_part_detail_id.product_id', 'in', self.product_variant_id.ids)],
            'context': {'default_partner_id':self.id}
        }

    def action_view_installed_parts(self):
        return {
            'name': _('Installed Part'),
            'res_model': 'installed.part.detail',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('product_id', 'in', self.product_variant_id.ids)],
            'context': {'search_default_filter_frequency': 1}
        }

    def _compute_running_avg_cost(self):
        stock_valuation = self.env['stock.valuation.layer']
        fields = ['product_id', 'quantity', 'value']
        groupby = ['product_id']
        for records in self:
            domain = [('product_id.product_tmpl_id','=',records.id)]
            inventory_value = stock_valuation.read_group(domain, fields, groupby)
            if inventory_value:
                if inventory_value[0].get('quantity') > 0:
                    records.running_avg_cost = inventory_value[0].get('value') / inventory_value[0].get('quantity')
                else:
                    records.running_avg_cost = 0.0
            else:
                records.running_avg_cost = 0.0

    @api.depends('product_variant_ids', 'product_variant_ids.length')
    def _compute_length(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.length = template.product_variant_ids.length
        for template in (self - unique_variants):
            template.length = 0.0

    def _set_length(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.length = template.length

    # Send  mail when installed part stock gone below half of minimum  stock
    def cron_alert_installed_part(self):
        product_data = self.search_read([], ['default_code', 'name', 'installed_quantity', 'qty_available','minimum_stock','unit_or_per','product_variant_id'])
        IrConfigParameter = self.env['ir.config_parameter'].sudo().get_param('cortex_na.product_related_hq_location', 'False')
        location = int(IrConfigParameter)
        fields = ['product_id', 'quantity']
        groupby = ['product_id']
        domain = [('location_id','=',location),('quantity','>',0)]
        inventory_value = self.env['stock.quant'].read_group(domain, fields, groupby)
        product_dict = {}
        for obj in inventory_value:
            product_dict.update({obj.get('product_id')[0]:obj.get('quantity')})

        product_list = []
        for record in product_data:
            installed_quantity = record.get('installed_quantity')
            mnimum_stock = record.get('minimum_stock')
            unit_or_per = record.get('unit_or_per')
            if unit_or_per == 'per':
                ratio = (installed_quantity * mnimum_stock) / 100
            else:
                ratio = mnimum_stock

            on_hand = record.get('qty_available') or 0
            if on_hand < ratio:
                record['hq'] = product_dict.get(record.get('product_variant_id')[0]) or 0
                record['other_location'] = record.get('qty_available') - record.get('hq')
                product_list.append(record)
        


        template_id = self.env.ref('cortex_na.email_template_alert_installed_part')
        user_ids = self.env.user
        if product_list:
            attachmnet_id = self.action_generate_attachment(product_list)
            if attachmnet_id:
                template_id.attachment_ids = [(6, 0, attachmnet_id.ids)]
                msg = "Please find an attachment for parts which is below the minimum stock level."
            else:
                template_id.attachment_ids = None
                msg = "No any Parts which is below the minimum stock level."
        else:
            template_id.attachment_ids = None
            msg = "No any Parts which is below the minimum stock level."
        template_id.with_context(msg=msg).send_mail(user_ids.id, force_send=True)
        _logger.info("Successfully send mail for Installed Part Stock Report.")

    def action_generate_attachment(self, product_list):
        """ this method called from button action in view xml """
        # generate pdf from report, use report's id as reference
        pdf = self.env.ref('cortex_na.alert_installed_part_report').with_context(data=product_list).render_qweb_pdf()
        # pdf result is a list
        b64_pdf = base64.b64encode(pdf[0])
        # save pdf as attachment
        attachment_name = "Installed Part Stock Report"
        if b64_pdf:
            return self.env['ir.attachment'].create({
                'name': attachment_name,
                'type': 'binary',
                'datas': b64_pdf,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })
        else:
            return False

    def duplicate_with_bom(self):
        self.ensure_one()
        new_product = self.copy()

        current_attributes_vals = {}
        for tmpl_attr in self.valid_product_template_attribute_line_ids._without_no_variant_attributes().product_template_value_ids._only_active():
            current_attributes_vals[tmpl_attr.id] = (tmpl_attr.attribute_id.id, tmpl_attr.name)
        new_attributes_vals_r = {}
        for tmpl_attr in new_product.valid_product_template_attribute_line_ids._without_no_variant_attributes().product_template_value_ids._only_active():
            new_attributes_vals_r[(tmpl_attr.attribute_id.id, tmpl_attr.name)] = tmpl_attr.id

        new_variants_attrs_r = {}
        for product in new_product.product_variant_ids:
            new_variants_attrs_r[tuple(product.product_template_attribute_value_ids.ids)] = product.id

        existing_bom = self.env['mrp.bom'].search([('product_tmpl_id', '=', self.id)])
        if existing_bom:
            for e_bom in existing_bom:
                new_bom_data = {
                    'product_tmpl_id': new_product.id
                }
                new_bom_p_id = None
                if e_bom.product_id:
                    e_product_attrs_ids = e_bom.product_id.product_template_attribute_value_ids.ids
                    if e_product_attrs_ids:
                        n_product_attrs_ids = []
                        for attr_id in e_product_attrs_ids:
                            attr_val = current_attributes_vals[attr_id]
                            if new_attributes_vals_r.get(attr_val):
                                n_product_attrs_ids.append(new_attributes_vals_r[attr_val])
                        if new_variants_attrs_r.get(tuple(n_product_attrs_ids)):
                            new_bom_p_id = new_variants_attrs_r[tuple(n_product_attrs_ids)]
                    else:
                        new_bom_p_id = new_product.product_variant_id.id
                if new_bom_p_id:
                    new_bom_data['product_id'] = new_bom_p_id

                bom_vals = e_bom.with_context(active_test=False).copy_data(new_bom_data)[0]
                for bom_line in bom_vals.get('bom_line_ids') or []:
                    if len(bom_line) == 3:
                        line_data = bom_line[2]
                        if line_data.get('bom_product_template_attribute_value_ids'):
                            line_attr = line_data['bom_product_template_attribute_value_ids']
                            if len(line_attr[0]) == 3 and line_attr[0][2]:
                                new_attr_ids = []
                                for line_attr_id in line_attr[0][2]:
                                    line_attr_val = current_attributes_vals[line_attr_id]
                                    if new_attributes_vals_r.get(line_attr_val):
                                        new_attr_ids.append(new_attributes_vals_r[line_attr_val])
                                line_attr_list_data = list(line_attr[0])
                                line_attr_list_data[2] = new_attr_ids
                                line_attr[0] = tuple(line_attr_list_data)
                e_bom.copy(bom_vals)
        if new_product:
            action = {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current',
                'res_id': new_product.id,
                'context': dict(self._context),
            }
        else:
            raise UserError(_('Something went wrong.'))
        return action


class ProductWithVendor(models.Model):
    _name = "product.with.vendor"
        
    product_template_id = fields.Many2one('product.template', string="Product")
    bom_id = fields.Many2one('mrp.bom',string='Bill of Material', domain = "[('product_tmpl_id','=',parent.id),('type', '=', 'normal')]", required="True")
    partner_id = fields.Many2one('res.partner',string='Vendor', required="True")
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company, index=True, required=True)
