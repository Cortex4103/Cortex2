from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError, Warning
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import logging
import sys
from datetime import datetime as dt
import base64
import io
import xlsxwriter
from odoo.addons import decimal_precision as dp
from xlrd import open_workbook
import urllib.request as urllib2
import json

_logger = logging.getLogger(__name__)


class ImportBOM(models.TransientModel):
    _name = 'import.bom'
    _rec_name = 'name'

    name = fields.Char('name', default='Import Purchase Order')
    upload_document = fields.Binary(string='Upload XLS')
    upload_file_name = fields.Char('File Name')

    def import_bom_data(self):
        if self.upload_document:
            if self.upload_file_name:
                filename = self.upload_file_name.split('.')
                ext = filename[len(filename) - 1]
                if ext.lower() != 'xlsx' and ext.lower() != 'xls':
                    raise Warning('Only .XLS or .XLSX file is supported. Please upload .XLS or .XLSX file.')
            xls_data = open_workbook(file_contents=base64.b64decode(self.upload_document))

            xlsx_list_data = []
            for s in xls_data.sheets():
                part_number = []
                product = []
                quantity = []
                uom = []
                bom_type = []
                component_part = []
                component = []
                component_qty = []
                component_uom = []
                service_part = []
                service_charges = []
                unit_price = []
                service_qty = []
                service_uom = []
                bom_obj_list = []
                component_data_list = []
                bom_dict = {}
                next_row = 1
                for data in range(s.nrows):
                    if data == 0:
                        for col in range(s.ncols):
                            coloumn_title = s.cell(data, col).value

                            if coloumn_title == "PART NUMBER":
                                part_number.append(col)

                            if coloumn_title == "PRODUCT":
                                product.append(col)

                            if coloumn_title == "QUANTITY":
                                quantity.append(col)

                            if coloumn_title == "UNIT OF MEASURE":
                                uom.append(col)

                            if coloumn_title == "BOM TYPE":
                                bom_type.append(col)

                            if coloumn_title == "COMPONENT PART NUMBER":
                                component_part.append(col)

                            if coloumn_title == "COMPONENT":
                                component.append(col)

                            if coloumn_title == "COMPONENT QTY":
                                component_qty.append(col)

                            if coloumn_title == "COMPONENT UOM":
                                component_uom.append(col)

                            if coloumn_title == "SERVICE PART NUMBER":
                                service_part.append(col)

                            if coloumn_title == "SERVICE CHARGES":
                                service_charges.append(col)

                            if coloumn_title == "UNIT PRICE":
                                unit_price.append(col)

                            if coloumn_title == "SERVICE QTY":
                                service_qty.append(col)

                            if coloumn_title == "SERVICE UOM":
                                service_uom.append(col)
                    if data < next_row:
                        continue
                    if s.ncols > 0:
                        part_numbers, products, quantitys, uoms, bom_types = None, None, None, None, None
                        component_parts, components, component_qtys, component_uoms, unit_pricess, service_parts = None, None, 0, None, 0, None
                        service_chargess,service_qtys,service_uoms = None,0,None
                        service_data_list = []
                        for col in range(s.ncols):
                            cell_value = s.cell_value(data, col)

                            if col in part_number:
                                part_numbers = cell_value.strip()


                            if col in product:
                                products = cell_value.strip()

                            if col in quantity:
                                quantitys = cell_value


                            if col in uom:
                                uoms = cell_value.strip()


                            if col in bom_type:
                                bom_types = cell_value.strip()


                            next_row_component = data

                            if col in component_part:
                                component_parts = cell_value.strip()
                                if component_parts not in (None, ""):
                                     next_row_component,component_data_list=self.get_attribute_component(s,data, component_part,component,component_qty,component_uom,part_number,product)

                            next_row_service = data

                            if col in service_part:
                                service_parts = cell_value.strip()
                                if service_parts not in (None, "") and bom_types == 'Manufacture this product':
                                     next_row_service,service_data_list=self.get_attribute_service_charges(s,data, service_part,service_charges,unit_price,service_qty,service_uom,part_number,product)


                        if part_numbers and products:
                            bom_dict = {}
                            product_obj = self.get_product_tmpl_obj(part_numbers, products)
                            bom_dict['product_tmpl_id'] = product_obj.id
                            bom_dict['product_qty'] = quantitys
                            if uoms:
                                uom_obj = self.get_uom_obj(uoms)
                                bom_dict['product_uom_id'] = uom_obj.id
                            if bom_types == 'Manufacture this product':
                                bom_dict['type'] = 'normal'
                            if bom_types == 'Kit':
                                bom_dict['type'] = 'phantom'
                            if bom_types == 'Subcontracting':
                                bom_dict['type'] = 'subcontract'
                            bom_dict['charges_per'] = 100
                            bom_dict['charges_per_change'] = 100
                            if component_data_list:
                                bom_dict['bom_line_ids'] = component_data_list
                            if service_data_list and bom_dict.get('type') == 'normal':
                                bom_dict['service_charge_ids'] = service_data_list
                            next_row = max(next_row_service,next_row_component)
                            bom = self.env['mrp.bom'].create(bom_dict)
                            bom_obj_list.append(bom.id)
                            # print('------------bom---------------', bom)


                    else:
                        raise Warning('The XLS seems empty. Please upload .XLS with data.')

                _logger.info(_("Successfully Created BOM"))
                ir_model_data = self.env['ir.model.data']
                act_obj = self.env['ir.actions.act_window']
                invoice_id = ir_model_data.get_object_reference('mrp', 'mrp_bom_form_action')
                invoice_action = act_obj.browse(invoice_id[1])
                dict = invoice_action.read([])[0]
                dict['domain'] = [('id', 'in', bom_obj_list)]
                return dict
        else:
            raise Warning('Please upload xls file.')

    def get_attribute_component(self, s,row, component_part,component,component_qty,component_uom,part_numbers,products):
        component_data_list = []
        for r in range(row, s.nrows):
            if r == row or s.cell_value(r, part_numbers[0]) in (None, "", ' '):
                component_parts = str(s.cell_value(r, component_part[0])).strip()
                components = str(s.cell_value(r, component[0])).strip()
                component_qtys = str(s.cell_value(r, component_qty[0])).strip()
                component_uoms = str(s.cell_value(r, component_uom[0])).strip()

                if component_parts not in (None, "", ' ') and components not in (None, "", ' ') and component_qtys not in (None, "", ' ') and component_uoms not in (None, "", ' '):
                    component_obj = self.get_product_obj(component_parts, components)
                    uom_obj = self.get_uom_obj(component_uoms)
                    component_data_list.append(
                        (0, 0, {
                            'product_id': component_obj.id,
                            'product_qty': component_qtys,
                            'product_uom_id':uom_obj.id
                        }))

            else:
                break
        return r, component_data_list

    def get_attribute_service_charges(self, s,row, service_part,service_charges,unit_price,service_qty,service_uom,part_numbers,product):
        service_data_list = []
        for r in range(row, s.nrows):
            if r == row or s.cell_value(r, part_numbers[0]) in (None, "", ' '):
                service_parts = str(s.cell_value(r, service_part[0])).strip()
                service_charge = str(s.cell_value(r, service_charges[0])).strip()
                unit_prices = str(s.cell_value(r, unit_price[0])).strip()
                service_qtys = str(s.cell_value(r, service_qty[0])).strip()
                service_uoms = str(s.cell_value(r, service_uom[0])).strip()

                if service_parts not in (None, "", ' ') and service_charge not in (None, "", ' ') and unit_prices not in (None, "", ' ') and service_qtys not in (None, "", ' ') and service_uoms not in (None, "", ' '):
                    service_obj = self.get_product_obj(service_parts, service_charge)
                    uom_obj = self.get_uom_obj(service_uoms)
                    service_data_list.append(
                        (0, 0, {
                            'product_id': service_obj.id,
                            'quantity': service_qtys,
                            'price_unit':unit_prices,
                            'product_uom_id':uom_obj.id,
                            'subtotal':float(service_qtys) * float(unit_prices)
                        }))

            else:
                break
        return r, service_data_list

    def get_product_tmpl_obj(self, part_numbers, products):
        product_obj = None
        if part_numbers:
            product_obj = self.env['product.template'].search([('default_code', '=', part_numbers),('name', '=', products)], limit=1)
        if not product_obj:
            raise Warning("Product '%s' does not exist." % products)
        return product_obj

    def get_product_obj(self, component_parts, components):
        product_obj = None
        if component_parts and components:
            product_obj = self.env['product.product'].search([('default_code', '=', component_parts),('name', '=', components)], limit=1)
        if not product_obj:
            raise Warning("Product '%s' does not exist." % components)
        return product_obj

    def get_uom_obj(self, uoms):
        uom_obj = None
        if uoms:
            uom_obj = self.env['uom.uom'].search([('name', '=ilike', uoms)], limit=1)
        if not uom_obj:
            raise Warning("Unit of measure '%s' does not exist." % uoms)
        return uom_obj

   


class ExportLatestProduct(models.TransientModel):
    _inherit = 'download.file.base.model'
    _name = 'demo.data.xlsx.report'
    _description = 'Demo data'

    def get_filename(self):
        return 'BOM Demo Data.xlsx'

    @api.model
    def get_content(self, data):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output)
        sheet = wb.add_worksheet(_('BOM Demo data'))

        title_style_right = wb.add_format({'font_name': 'Arial', 'bold': True,'align': 'right'})
        title_style_left = wb.add_format({'font_name': 'Arial', 'bold': True})
        row = 0
        col = 0
        sheet.write(row, col, 'PART NUMBER', title_style_left)
        sheet.write(row, col + 1, 'PRODUCT', title_style_left)
        sheet.write(row, col + 2, 'QUANTITY', title_style_right)
        sheet.write(row, col + 3, 'UNIT OF MEASURE',title_style_left)
        sheet.write(row, col + 4, 'BOM TYPE', title_style_left)
        sheet.write(row, col + 5, 'COMPONENT PART NUMBER', title_style_left)
        sheet.write(row, col + 6, 'COMPONENT', title_style_left)
        sheet.write(row, col + 7, 'COMPONENT QTY', title_style_right)
        sheet.write(row, col + 8, 'COMPONENT UOM', title_style_left)
        sheet.write(row, col + 9, 'SERVICE PART NUMBER', title_style_left)
        sheet.write(row, col + 10, 'SERVICE CHARGES', title_style_left)
        sheet.write(row, col + 11, 'UNIT PRICE', title_style_right)
        sheet.write(row, col + 12, 'SERVICE QTY', title_style_right)
        sheet.write(row, col + 13, 'SERVICE UOM', title_style_left)
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 50)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 35)
        sheet.set_column('H:H', 20)
        sheet.set_column('I:I', 50)
        sheet.set_column('J:J', 20)
        sheet.set_column('K:K', 35)
        sheet.set_column('L:L', 20)
        sheet.set_column('M:M', 20)
        sheet.set_column('N:N', 20)
        row += 1
        list_uom = []
        unit_obj = self.env['uom.uom'].search([],order='id')
        for rec in unit_obj:
            list_uom.append(rec.name)
        sheet.write(row, col, 'KT-0262-RT')
        sheet.write(row, col + 1, 'Cortex 2.62" Kit for Conical Head RIGHT Tab. Drawing #100380')
        sheet.write(row, col + 2, 1)
        sheet.write(row,col + 3,list_uom[0])
        sheet.data_validation(1, 3, 100, 3,{'validate': 'list', 'source': list_uom})
        sheet.write(row, col + 4, 'Manufacture this product')
        sheet.data_validation(1, 4, 100, 4,{'validate': 'list', 'source': ['Manufacture this product', 'Kit', 'Subcontracting']})
        sheet.write(row, col + 5, 'CK0262-RT-CTG')
        sheet.write(row, col + 6, 'Cortex 2.62" Counter Knife with a Right Wing Tab only and Wear Coating')
        sheet.write(row, col + 7, 1)
        sheet.write(row, col + 8, list_uom[0])
        sheet.data_validation(1, 8, 100, 8,{'validate': 'list', 'source': list_uom})
        sheet.write(row, col + 9, '0981-Surface Finish of Cortex Knife')
        sheet.write(row, col + 10, 'Surface Finish of Cortex 9.81" length Knife - does not include backgrind')
        sheet.write(row, col + 11, 0.50)
        sheet.write(row, col + 12, 1)
        sheet.write(row, col + 13, list_uom[0])
        sheet.data_validation(1,13, 100, 13,{'validate': 'list', 'source': list_uom})
        row += 1
        sheet.write(row, col + 5,'CL0262')
        sheet.write(row, col + 6,'Cortex 2.62" Clamp. Drawing #100325')
        sheet.write(row, col + 7, 1)
        sheet.write(row, col + 8, list_uom[0])
        sheet.data_validation(1, 8, 100, 8, {'validate': 'list', 'source': list_uom})
        sheet.write(row, col + 9,'0156-CRTX-Surface Finish')
        sheet.write(row, col + 10,'Surface Finish of 1.56" knife')
        sheet.write(row, col + 11, 0.78)
        sheet.write(row, col + 12, 1)
        sheet.write(row, col + 13, list_uom[0])
        sheet.data_validation(1,13, 100, 13, {'validate': 'list', 'source': list_uom})
        row += 1
        sheet.write(row, col + 5,'HEX 5/8x11x2-1/2')
        sheet.write(row, col + 6,'Hex Clamp Bolt - 5/8" Diameter - 2 1/2" Length - 15/16" Head - Grade 8 Coarse Thread')
        sheet.write(row, col + 7, 1)
        sheet.write(row, col + 8, list_uom[0])
        sheet.data_validation(1, 8, 100, 8, {'validate': 'list', 'source': list_uom})
        wb.close()
        output.seek(0)
        return output.read()

