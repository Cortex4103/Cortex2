# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
import io
import xlsxwriter
from ast import literal_eval


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    service_charge_ids = fields.One2many('service.charge', 'bom_id', 'Service Charges', copy=True)
    charges_per = fields.Float(string='Charges %', default=100)
    charges_per_change = fields.Float(string='Charges %')
    service_charge_total = fields.Float(string='Service Charges Total', compute='compute_charge_total')
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True, store=True)
    product_qty = fields.Float(
        'Quantity', default=1.0,
        digits='Product Unit of Measure', required=True)
    partner_ids = fields.Many2many('res.partner', string="Customers")

    @api.depends('service_charge_ids', 'service_charge_ids.subtotal')
    def compute_charge_total(self):
        for record in self:
            total = 0
            for line in record.service_charge_ids:
                total += line.subtotal
            record.service_charge_total = total

    @api.onchange('byproduct_ids', 'byproduct_ids.charges_per')
    def onchange_byproduct_charges(self):
        per = 100
        if self.byproduct_ids:
            for product in self.byproduct_ids:
                per -= product.charges_per
        self.charges_per = per if per >= 0 and per <= 100 else 0

    @api.onchange('charges_per', 'byproduct_ids', 'byproduct_ids.charges_per')
    def onchange_charges_per(self):
        per = self.charges_per
        byproduct_per = 100
        for product in self.byproduct_ids:
            per += product.charges_per
            byproduct_per -= product.charges_per
        if self.charges_per > 100:
            self.charges_per = byproduct_per if byproduct_per >= 0 and byproduct_per <= 100 else 0
        self.charges_per_change = per

    @api.model
    def create(self, vals):
        res = super(MrpBom, self).create(vals)
        if res.charges_per_change != 100:
            raise ValidationError(_("Please Set Charges Percentage Total 100."))
        return res
    
    def write(self, vals):
        res = super(MrpBom, self).write(vals)
        if self.charges_per_change != 100:
            raise ValidationError(_("Please Set Charges Percentage Total 100."))
        return res

    def export_bom_pricing(self):
        part = self.product_tmpl_id.default_code
        part_no = part.replace('"',"'")
        product = self.product_tmpl_id.name
        product_name = product.replace('"', "'")
        product_name = product_name.replace(',', "")
        full_name = part_no + "-" + product_name
        # full_name = "ASM-6KN-24CD-CA-RH-6 Knife 24' Diameter RIGHT head assembly"
        # print(k)
        url = '/custom_download_file/get_file?model={}&record_id={}&token={}&data={}&context={}'.format(
            "export.xlsx.bom.line.item", '', '',self.id,full_name)


        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'nodestroy': True,
            'target': '_blank',
        }


class MrpByProduct(models.Model):
    _inherit = 'mrp.bom.byproduct'

    charges_per = fields.Float(string='Charges %')

    @api.onchange('charges_per')
    def onchange_charges_per(self):
        if self.charges_per > 100:
            raise ValidationError('Charges Percentage should be a maximum of 100')


class ServiceCharges(models.Model):
    _name = 'service.charge'

    product_id = fields.Many2one('product.product', string='Service Charge')
    quantity = fields.Float(string='Quantity', default=1, digits='New Cortex Precision')
    price_unit = fields.Float(string='Unit Price', digits='New Cortex Product Precision')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', default=lambda self: self.env.ref('uom.product_uom_unit'))
    bom_id = fields.Many2one('mrp.bom', string='Bill of Material', ondelete='cascade')
    bom_line_id = fields.Many2one('mrp.bom', string='Bill of Material')
    bom_charge_id = fields.Many2one('service.charge', string='Bom Service')
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', ondelete='cascade')
    subtotal = fields.Float(string='Subtotal',digits='New Cortex Product Precision')
    currency_id = fields.Many2one(related="production_id.currency_id", string="Currency", readonly=True, store=True)
    batch_production_id = fields.Many2one('batch.production', string='Batch Production', ondelete='cascade')

    @api.onchange('price_unit', 'quantity')
    def onchange_price_quantity(self):
        self.subtotal = self.quantity * self.price_unit

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
            self.price_unit = self.product_id.standard_price

    @api.onchange('production_id')
    def onchange_production_id(self):
        self.production_id.write({'purchase_order_id': self.batch_production_id.purchase_order_id})




class BOMExports(models.TransientModel):
    _inherit = 'download.file.base.model'
    _name = 'export.xlsx.bom.line.item'
    _description = 'Demo data'

    def get_filename(self):
        if self._context.get('payslip_number'):
            return self._context.get('payslip_number')+ '.xlsx'
        return 'BOMData.xlsx'

    def get_line(self,row,col,sheet,child_bom_line,product_qty,space,child_bom_ids,count):
        if child_bom_line:
            for sub_bom1 in child_bom_line:
                qty= sub_bom1.product_qty
                sheet.write(row, col + 1,space+sub_bom1.product_id.display_name)
                sheet.write(row, col + 2, qty)
                sheet.write(row, col + 3, sub_bom1.product_uom_id.name)
                sheet.write(row, col + 4, sub_bom1.product_id.list_price)
                sheet.write(row, col + 5, sub_bom1.product_id.list_price * qty)
                row += 1
                count += 1
                if sub_bom1.child_bom_id and sub_bom1.child_bom_id.id not in child_bom_ids:
                    child_bom_ids.append(sub_bom1.child_bom_id.id)
                    child_bom_line = sub_bom1.child_bom_id.bom_line_ids
                    row,sheet,count = self.get_line(row, col,sheet, child_bom_line,qty,space+"               ",child_bom_ids,count)
        return row,sheet,count

    def get_product_line(self,child_bom_line,product_qty,product_dict):
        if child_bom_line:
            for rec in child_bom_line:
                qty = product_qty * rec.product_qty
                if not rec.child_bom_id:
                    if product_dict.get(rec.product_id):
                        source = product_dict[rec.product_id].get('bom_uom')
                        destination = rec.product_uom_id
                        uom = self.get_qty(qty, source, destination)
                        product_dict[rec.product_id]['qty'] += uom
                    else:
                        product_dict[rec.product_id] = {'qty' :qty, 'bom_uom':rec.product_uom_id}
                else:
                    child_bom_line = rec.child_bom_id.bom_line_ids
                    product_dict = self.get_product_line( child_bom_line,qty,product_dict)
        return product_dict

    def get_qty(self,qty,source,destination):
        if source == destination:
            return qty
        else:
            qty = qty * destination.factor_inv / source.factor_inv if source.factor_inv else 0
            return float("{:.2f}".format(qty))

    def get_content(self, data):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output)

        sheet = wb.add_worksheet(_('BOM Data'))
        title_style = wb.add_format({'font_name': 'Arial', 'bold': True})
        title_style1 = wb.add_format({'font_name': 'Arial', 'bold': True, 'align': 'right'})
        row = 0
        col = 0
        count = 0
        sheet.write(row, col, 'PRODUCT', title_style)
        sheet.write(row, col + 1,'COMPONENT', title_style)
        sheet.write(row, col + 2, 'QUANTITY', title_style1)
        sheet.write(row, col + 3, 'UNIT OF MEASURE',title_style)
        sheet.write(row, col + 4, 'SALE PRICE', title_style1)
        sheet.write(row, col + 5, 'SUBTOTAL', title_style1)

        sheet.set_column('A:A', 50)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        row += 1
        count += 1
        if data:
            bom_obj = self.env['mrp.bom'].browse(literal_eval(data))
            if bom_obj:
                sheet.write(row,col,bom_obj.product_tmpl_id.display_name)
                child_bom_ids=[]
                for lines in bom_obj.bom_line_ids:
                    sheet.write(row, col + 1, lines.product_id.display_name)
                    sheet.write(row, col + 2, lines.product_qty)
                    sheet.write(row, col + 3, lines.product_uom_id.name)
                    sheet.write(row, col + 4, lines.product_id.list_price)
                    sheet.write(row, col + 5, lines.product_id.list_price * lines.product_qty)
                    row += 1
                    count += 1
                    if lines.child_bom_id and  lines.child_bom_id.id not in child_bom_ids:
                        child_bom_ids.append(lines.child_bom_id.id)
                        child_bom_line = lines.child_bom_id.bom_line_ids
                        row,sheet,count = self.get_line(row, col,sheet, child_bom_line ,lines.product_qty,"               ",child_bom_ids,count)

        # sheet.merge_range('A' + str(count + 1) + ':E' + str(count + 1) + '', 'TOTAL', title_style1)
        # total = "{=SUM(F" + str(2) + ": F" + str(count) +"}"
        # sheet.write_formula(row, col + 5,total )


        sheet = wb.add_worksheet(_('Part Data'))
        title_style = wb.add_format({'font_name': 'Arial', 'bold': True})
        title_style1 = wb.add_format({'font_name': 'Arial', 'bold': True, 'align': 'right'})
        product_dict = {}
        bom_obj = self.env['mrp.bom'].browse(literal_eval(data))
        if bom_obj:
            for lines in bom_obj.bom_line_ids:
                qty = lines.product_qty
                if not lines.child_bom_id:
                    if product_dict.get(lines.product_id):
                        source = product_dict[lines.product_id].get('bom_uom')
                        destination = lines.product_uom_id
                        uom = self.get_qty(qty,source,destination)
                        product_dict[lines.product_id]['qty'] +=uom
                    else:
                        product_dict[lines.product_id] = {'qty' :qty, 'bom_uom':lines.product_uom_id}
                else:
                    product_dict = self.get_product_line(lines.child_bom_id.bom_line_ids, qty, product_dict)

        row = 0
        col = 0
        count = 0
        sheet.write(row, col, 'PRODUCT', title_style)
        sheet.write(row, col + 1, 'COMPONENT', title_style)
        sheet.write(row, col + 2, 'QUANTITY', title_style1)
        sheet.write(row, col + 3, 'UNIT OF MEASURE', title_style)
        sheet.write(row, col + 4, 'SALE PRICE', title_style1)
        sheet.write(row, col + 5, 'SUBTOTAL', title_style1)

        sheet.set_column('A:A', 50)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        row += 1
        count += 1
        if data:
            bom_obj = self.env['mrp.bom'].browse(literal_eval(data))
            if bom_obj:
                sheet.write(row, col, bom_obj.product_tmpl_id.display_name)
                for key,value in product_dict.items():
                    uom = value.get('bom_uom')
                    sheet.write(row, col + 1, key.display_name)
                    sheet.write(row, col + 2, value.get('qty'))
                    sheet.write(row, col + 3, uom.name)
                    sheet.write(row, col + 4, key.list_price)
                    sheet.write(row, col + 5, key.list_price * value.get('qty'))
                    row += 1
                    count += 1

        sheet.merge_range('A' + str(count+1) +':E' + str(count+1) +'', 'TOTAL', title_style1)
        total = "{=SUM(F" + str(2) + ": F" + str(count) + "}"
        sheet.write_formula(row, col + 5, total)

        wb.close()
        output.seek(0)
        return output.read()