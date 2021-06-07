# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
import logging
import io
import xlsxwriter
from ast import literal_eval
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, RedirectWarning, UserError

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = "product.product"


    mrp_product_qty = fields.Float('Manufactured', digits='New Cortex Precision',
                                   compute='_compute_mrp_product_qty', compute_sudo=False)

    default_code = fields.Char('Part Number', index=True)
    sales_count = fields.Float(compute='_compute_sales_count', string='Sold', digits='New Cortex Precision')
    purchased_product_qty = fields.Float(compute='_compute_purchased_product_qty', string='Purchased', digits='New Cortex Precision')
    length = fields.Float(string="Length")
    active = fields.Boolean('Active', default=True, tracking=True,
        help="If unchecked, it will allow you to hide the product without removing it.")

    @api.model
    def remove_no_update(self):
        try:
            ids = [self.env.ref('product.decimal_product_uom').id, self.env.ref('product.decimal_price').id]
            ir_model_data = self.env['ir.model.data'].search([('res_id', 'in', ids), ('model', '=', 'decimal.precision')])
            for record in ir_model_data:
                record.write({'noupdate': False})
        except:
            pass

    def _compute_average_price(self, qty_invoiced, qty_to_invoice, stock_moves):
        try:
            return super(ProductProduct, self)._compute_average_price(qty_invoiced, qty_to_invoice, stock_moves)
        except Exception as e:
            _logger.warning(_("Invoice qty is zero which product comes from Sale order: %s" % e))
            return 0

    def cron_can_not_sold_product(self):
        product_obj = self.search([ ('sale_ok', '=', True), '|', ('default_code', 'like', '-C3'), ('default_code', 'like','-NOTGRINDED')])
        if product_obj:
            product_obj.write({'sale_ok': False})
        _logger.info(_("Set Sold is False to Product Successfully."))

    def get_product_available_data(self, value):
        product_data = self.with_context(value)._product_available()
        product_data = product_data.get(self.id)
        value['location'] = None
        value['lot_id'] = None
        total_available = self.with_context(value)._product_available()
        total_available_qty = 0
        if total_available.get(self.id):
            total_available_qty = total_available.get(self.id).get('qty_available')
        if product_data:
            product_data['total_available_qty'] = total_available_qty
        return product_data

    def export_product(self):
        name = self.search([])
        # print('name----------------',name)
        url = '/custom_download_file/get_file?model={}&record_id={}&token={}&data={}&context={}'.format(
            "export.xlsx.product.item", '', '', name.ids ,'')
        # print('url----------------', url)

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'nodestroy': True,
            'target': '_blank',
        }

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if self._context.get('input_product'):
            bom_ids = self.env['mrp.bom.line'].search([('product_id', '=', self._context.get('input_product'))]).mapped('bom_id')
            args += [('id', 'in', bom_ids.mapped('product_tmpl_id').mapped('product_variant_id').ids)]
        return super(ProductProduct, self).name_search(name=name, args=args, operator=operator, limit=limit)


class ProductExports(models.TransientModel):
    _inherit = 'download.file.base.model'
    _name = 'export.xlsx.product.item'
    _description = 'Demo data'

    def get_filename(self):
        if self._context.get('payslip_number'):
            return self._context.get('payslip_number') + '.xlsx'
        return 'Product.xlsx'

    def get_content(self, data):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output)
        # product data************************************************

        sheet = wb.add_worksheet(_('ProductData'))
        title_style = wb.add_format({'font_name': 'Arial', 'bold': True})
        title_style1 = wb.add_format({'font_name': 'Arial', 'bold': True, 'align': 'right'})
        row = 0
        col = 0
        sheet.write(row, col, 'DESCRIPTION', title_style)
        sheet.write(row, col + 1, 'COMPANY ', title_style)
        sheet.write(row, col + 2, 'ESTIMATED CONSUMPTION', title_style1)
        sheet.write(row, col + 3, 'ESTIMATED PRICE', title_style1)
        sheet.set_column('A:A', 40)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 20)
        row += 1
        if data:
            product_obj = self.env['product.product'].browse(literal_eval(data))
            if product_obj:
                for lines in product_obj:
                    sheet.write(row, col, lines.name)
                    sheet.write(row, col + 1, lines.company_id.name)
                    sheet.write(row, col + 2, lines.standard_price)
                    sheet.write(row, col + 3, lines.list_price)
                    row += 1

        # cornomics company name ----------------------------------

        sheet = wb.add_worksheet(_('CornomicsCompanyData'))
        title_style = wb.add_format({'font_name': 'Arial', 'bold': True})
        title_style1 = wb.add_format({'font_name': 'Arial', 'bold': True, 'align': 'right'})
        row = 0
        col = 0
        sheet.write(row, col, 'CORNOMICS COMPANY NAME ', title_style)
        sheet.set_column('A:A', 30)
        row += 1

        company_obj = self.env['cornomics.company'].search([])
        if company_obj:
            for lines in company_obj:
                sheet.write(row, col, lines.name)
                row += 1

        # copititor company detail**********************************************

        sheet = wb.add_worksheet(_('CompititorCompanyData'))
        title_style = wb.add_format({'font_name': 'Arial', 'bold': True})
        title_style1 = wb.add_format({'font_name': 'Arial', 'bold': True, 'align': 'right'})
        row = 0
        col = 0
        sheet.write(row, col, 'Product Name ', title_style)
        sheet.write(row, col + 1, 'CORNOMICS COMPANY NAME ', title_style)
        sheet.write(row, col + 2, 'PRODUCT', title_style)
        sheet.write(row, col + 3, 'ESTIMATED CONSUMPTION', title_style)
        sheet.write(row, col + 4, 'ESTIMATED PRICE', title_style)
        sheet.set_column('A:A', 40)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:C', 40)
        sheet.set_column('D:D', 30)
        sheet.set_column('E:E', 30)
        row += 1

        company_obj = self.env['product.product'].browse(literal_eval(data))
        print('company obj ------------------------------',company_obj)
        if company_obj:
            for record in company_obj.cornomics_detail_ids:
                print('record----------------',record)
                sheet.write(row, col, record.product_tmpl_id.name)
                sheet.write(row, col + 1, record.company_id.name)
                sheet.write(row, col + 2, record.product_id.name)
                sheet.write(row, col + 3, record.estimated_consumption)
                sheet.write(row, col + 4, record.estimated_price)
                row += 1

        # selection product data ************************************************

        sheet = wb.add_worksheet(_('SelectionProductdata'))
        # money = wb.add_format({'num_format': '$#,##0'})
        title_style = wb.add_format({'font_name': 'Calibri', 'bold': True,'align': 'right','font_size':14})
        title_style_f56 = wb.add_format({'left':2})
        title_style5 = wb.add_format({'font_name': 'Calibri','bold':True, 'align': 'right','font_size':14,'num_format':'$#,##0.00','right':2})
        title_style6 = wb.add_format({'font_name': 'Calibri','bold':True, 'align': 'right','font_size':14,'num_format':'$#,##0.00','right':2})
        title_style7 = wb.add_format({'font_name': 'Calibri', 'bold': True,'align': 'right','font_size':14,'num_format':'$#,##0.00','left':2,})
        title_style8 = wb.add_format({'font_name': 'Calibri', 'bold': True,'align': 'right','font_size':14,'num_format':'$#,##0.00','right':2})
        company_title = wb.add_format({'font_name': 'Calibri', 'bold': True, 'align': 'center','bg_color':'FFC000','font_size':14})

        cortex_title = wb.add_format({'font_name': 'Calibri', 'bold': True, 'align': 'center','bg_color':'92D050','font_size':14,'right':2,'left':2,'top':2})
        cortex_title8 = wb.add_format({'font_name': 'Calibri', 'bold': True, 'align': 'right','bg_color':'92D050','font_size':14,'left':2})
        cortex_title9 = wb.add_format({'font_name': 'Calibri', 'bold': True, 'align': 'right','bg_color':'92D050','font_size':14,'left':2,'bottom':2})

        # cortex_title1 = wb.add_format({'font_name': 'Calibri', 'bold': True, 'align': 'right','bg_color':'92D050','font_size':14})
        row_title = wb.add_format({'font_name': 'Calibri', 'bold': True, 'align': 'right','bg_color':'D9D9D9','text_wrap': True,'font_size':12})
        row_title_left = wb.add_format({'font_name': 'Calibri', 'bold': True, 'align': 'right','bg_color':'D9D9D9','text_wrap': True,'font_size':12,'left':2})
        row_title_right = wb.add_format({'font_name': 'Calibri', 'bold': True, 'align': 'right','bg_color':'D9D9D9','text_wrap': True,'font_size':12,'right':2})
        row_title_cortex8 = wb.add_format({'font_name': 'Calibri', 'bold': True, 'align': 'right','bg_color':'92D050','text_wrap': True,'font_size':14,'right':2,'num_format':'$#,##0.00'})
        row_title_cortex9 = wb.add_format({'font_name': 'Calibri', 'bold': True, 'align': 'right','bg_color':'92D050','text_wrap': True,'font_size':14,'right':2,'bottom':2,'num_format':'$#,##0.00'})
        cell_title_c = wb.add_format({'font_name': 'Calibri', 'align': 'right','bg_color':'FFFF00','num_format':'$#,##0.00'})
        cell_title_price = wb.add_format({'num_format':'$#,##0.00'})
        cell_title_price_78 = wb.add_format({'font_size':14,'num_format':'$#,##0.00','bold': True})
        cell_title_d = wb.add_format({'font_name': 'Calibri', 'align': 'right','bg_color':'FFFF00'})

        sheet.set_column('A:A', 20)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:C', 18)
        sheet.set_column('D:D', 18)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 10)
        sheet.set_column('G:G', 10)
        sheet.set_column('H:H', 12)
        sheet.set_column('I:I', 20)
        sheet.set_column('J:J', 15)
        sheet.set_row(3,50)
        sheet.set_row(2,20)

        row = 0
        col = 0
        validate_company = sheet.data_validation(2, 0, 2, 0,
                                                 {'validate': 'list', 'source': '=CornomicsCompanyData!$A$2:$A$10'})
        # sheet.Rows(4).RowHeight = 60
        sheet.write('C1','',cell_title_c)
        sheet.write('D1','ENTER OWN NUMBERS IN YELLOW CELLS')
        sheet.merge_range('A3:E3', validate_company , company_title)
        sheet.merge_range('F3:J3', 'CORTEX OPERATING COSTS ', cortex_title)
        sheet.merge_range('A4:B4', 'PART DESCRIPTION / EXISTING SYSTEM - BRAND L ', row_title)
        sheet.write('C4', 'ESTIMATED KNIFE PRICE ', row_title)
        sheet.write('D4', 'ESTIMATED CONSUMPTION PER MONTH ', row_title)
        sheet.write('E4', 'TOTAL COST', row_title)
        sheet.merge_range('F4:G4', 'CORTEX PART DESCRIPTION ', row_title_left)
        sheet.write('H4', 'PRICE ', row_title)
        sheet.write('I4', 'ESTIMATED CONSUMPTION PER MONTH ', row_title)
        sheet.write('J4', 'TOTAL COST', row_title_right)

        validate_product_compititor = sheet.data_validation(4, 0, 5, 0,{'validate': 'list', 'source': '=ProductData!$A$2:$A$900'})

        validate_product_cortex = sheet.data_validation(4, 5, 5, 5,{'validate': 'list', 'source': '=ProductData!$A$2:$A$900'})

        sheet.merge_range('A5:B5',validate_product_compititor)
        sheet.write('C5','',cell_title_c)
        sheet.write('D5','',cell_title_d)
        sheet.write('E5','=C5*D5',cell_title_price)

        sheet.merge_range('A6:B6', validate_product_compititor)
        sheet.write('C6', '',cell_title_c)
        sheet.write('D6', '',cell_title_d)
        sheet.write('E6', '=C6*D6',cell_title_price)

        sheet.merge_range('F5:G5',validate_product_cortex , title_style_f56)
        sheet.write('H5', '=VLOOKUP(F5,ProductData!A:D,4,0)',cell_title_price)
        sheet.write('I5', '=VLOOKUP(F5,ProductData!A:C,3,0)')
        sheet.write('J5', '=H5*I5',title_style5)

        sheet.merge_range('F6:G6', validate_product_cortex , title_style_f56)
        sheet.write('H6', '=VLOOKUP(F6,ProductData!A:D,4,0)',cell_title_price)
        sheet.write('I6', '=VLOOKUP(F6,ProductData!A:C,3,0)')
        sheet.write('J6', '=H6*I6',title_style6)

        sheet.merge_range('C7:D7', 'MONTHLY OPERATING COSTS',title_style)
        sheet.write('E7', '=SUM(E5:E6)',cell_title_price_78)

        sheet.merge_range('C8:D8', 'ANNUAL OPERATING COSTS',title_style)
        sheet.write('E8', '=E7*12',cell_title_price_78)

        sheet.merge_range('F7:I7', 'MONTHLY OPERATING COSTS',title_style7)
        sheet.write('J7', '=SUM(J5:J6)',title_style8)

        sheet.merge_range('F8:I8', 'ANNUAL OPERATING COSTS',cortex_title8)
        sheet.write('J8', '=J7*12',row_title_cortex8)

        sheet.merge_range('F9:I9', 'ANNUAL SAVINGS WITH CORTEX',cortex_title9)
        sheet.write('J9', '=E8-J8',row_title_cortex9)




        wb.close()
        output.seek(0)
        return output.read()

# vlookup
class ProductCategory(models.Model):
    _inherit = "product.category"

    category_display_in_report = fields.Boolean('Category display in Sale report')

