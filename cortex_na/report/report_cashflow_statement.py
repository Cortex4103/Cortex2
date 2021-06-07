import datetime
import io
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta
import datetime, calendar
import ast
from dateutil.relativedelta import relativedelta


class ReportDataForCashFlow(models.TransientModel):
    _inherit = 'download.file.base.model'
    _name = 'report_cashflow_cortex_na_template'

    so = fields.Char()
    po = fields.Char()
    rfq = fields.Char()
    ar = fields.Char()
    ap = fields.Char()
    quote = fields.Char()

    def find_general_data(self):
        receivable_move = self.env['account.move'].search(
            [("invoice_payment_state", "!=", "paid"), ("state", "=", "posted"), ("type", "=", "out_invoice")],order='invoice_date_due asc')
        payable_move = self.env['account.move'].search(
            [("invoice_payment_state", "!=", "paid"), ("state", "=", "posted"), ("type", "=", "in_invoice")],order='invoice_date asc')
        sale_order = self.env['sale.order'].search([("pending_amount", ">", 0),
                                                    ("invoice_status", "!=", "invoiced"),("state","not in",['draft','cancel'])])
        purchase_order = self.env['purchase.order'].search(
            [("remaining_amount", ">", 0), ("qty_received_total", ">", 0),("state","not in",['draft','cancel'])])

        quotations = self.env['sale.order'].search([("show_in_cash_flow", "=", True),
            ("invoice_status", "!=", "invoiced"),("state","in",['draft','sent'])])
        rfqs = self.env['purchase.order'].search(
                    [("show_in_cash_flow", "=", True),
                    ("remaining_amount", ">", 0),("state", "in", ['draft'])])
        date_duration = datetime.datetime.strptime(str(self.date_duration), "%Y-%m-%d")
        date_duration = datetime.datetime.strftime(date_duration, "%Y-%m-%d")
        data_dict = {
                "account_receivable": receivable_move.ids,
                "account_payable": payable_move.ids,
                "sale_order": sale_order.ids,
                "purchase_order": purchase_order.ids,
                "period_days": int(self.period_days),
                "date_duration": date_duration,
                "quotations":quotations.ids,
                "rfqs":rfqs.ids
            }
        return data_dict

    def print_report(self,report_type):
        report_name = 'cortex_na.report_data_cash_flow_base'
        return self.env['ir.actions.report'].search(
            [('report_name', '=', report_name),
             ('report_type', '=', report_type)], limit=1).report_action(self)

    def get_period_days(self):
        period_days_lst = []
        for vals in range(1, 16):
            period_days_lst.append((vals, vals))
        return period_days_lst

    def default_duration_date(self):
        today = date.today()
        add_five_months = today + relativedelta(months=+5)
        find_last_day = add_five_months + relativedelta(day=31)
        return find_last_day

    def print_html_report(self):
        return self.get_html(given_context=None)

    def _get_html(self):
        result = {}
        rcontext = {}
        context = dict(self.env.context)
        try:
            report = self.browse(context.get('active_id'))
            # for check object is exist in db or not if not then except part will execute
            duration_date = report.date_duration
        except:
            report = self.search([], order='id desc', limit=1)
        if report:
            rcontext['o'] = report
            result['html'] = self.env.ref(
                'cortex_na.report_cashflow_cortex_na_template').render(
                    rcontext)
        return result

    @api.model
    def get_html(self, given_context=None):
        return self._get_html()

    def set_dates_in_reports(self,data):
        list_of_dates = []
        start_date = date.today().replace(day=1) + relativedelta(months=1)
        # list_of_dates.append(date.today())
        list_of_dates.append(start_date)
        end_date = datetime.datetime.strptime(data.get('date_duration'), "%Y-%m-%d").date()
        while start_date <= end_date:
            period_days = data.get('period_days')
            if period_days == 15:
                month_count = calendar.monthrange(start_date.year, start_date.month)
                s_date = start_date.replace(year=start_date.year, month=start_date.month, day=15)
                e_date = start_date.replace(year=start_date.year, month=start_date.month, day=month_count[1])
                list_of_dates.append(s_date)
                list_of_dates.append(e_date)
                start_date += timedelta(days=month_count[1])
            elif period_days == 10:
                month_count = calendar.monthrange(start_date.year, start_date.month)
                s_date = start_date.replace(year=start_date.year, month=start_date.month, day=10)
                m_date = start_date.replace(year=start_date.year, month=start_date.month, day=20)
                e_date = start_date.replace(year=start_date.year, month=start_date.month, day=month_count[1])
                list_of_dates.append(s_date)
                list_of_dates.append(m_date)
                list_of_dates.append(e_date)
                start_date += timedelta(days=month_count[1])
            else:
                list_of_dates.append(start_date)
                start_date += timedelta(days=period_days)
        return list_of_dates

    def closest_date(self,closest_date):
        if closest_date:
            return min(closest_date)

    def return_today(self):
        return date.today()

    # def export_excel_file(self):
    #     # return self.cf_id.action_print_cash_flow_report()

    def prepare_report_aged_partner_balance(self):
        vals = {'period_days':15,
                'date_duration':self.default_duration_date(),
                # 'cf_id':self.id,
        }
        action = self.env.ref(
                    'cortex_na.report_cashflow_cortex_na_template_custom')
        vals2 = {}
        vals2 = action.read()[0]
        vals2.pop('context')
        model = self.env['report_cashflow_cortex_na_template']
        report = model.create(vals)
        vals2['context'] = {'active_id':report.id,
                            'active_ids':report.ids}
        return vals2

    period_days = fields.Selection(get_period_days, string='Period days', default=15, required=True)
    date_duration = fields.Date(string='Duration', default=default_duration_date, required=True)
    # cf_id = fields.Many2one('cash.flow.report')
    rec_click = fields.Boolean("")
    acc_pay_click = fields.Boolean("")
    sale_order_click = fields.Boolean("")
    purhcase_order_click = fields.Boolean("")


    #excel_part_of_report
    def get_filename(self):
        return 'Cortex Cash Flow Statement' + datetime.datetime.today().strftime('%Y/%m/%d') + '.xlsx'

    def generate_excel_report(self):
        data_dict = self.find_general_data()
        url = '/custom_download_file/get_file?model={}&record_id={}&token={}&data={}&context={}'.format(
            "report_cashflow_cortex_na_template", '', '', data_dict, self._context)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'nodestroy': True,
            'target': 'self',
        }

    def colToExcel(self, col):  # col is 1 based
        excelCol = str()
        div = col
        while div:
            (div, mod) = divmod(div - 1, 26)  # will return (x, 0 .. 25)
            excelCol = chr(mod + 65) + excelCol
        return excelCol

    # def write(self,vals):
    #     res = super(ReportDataForCashFlow,self).write(vals)
    #     print("valslslslsl \n",vals)
    #     self._cr.commit()
    #     return res

    @api.model
    def get_content(self, data):
        if data:
            data = ast.literal_eval(data)
            output = io.BytesIO()
            wb = xlsxwriter.Workbook(output)
            if data:
                self.ExportFinalCashFlowXlsx(data, wb)
                self.ExportAccountReceibaleXlsx(data, wb)
                self.ExportQuotationXlsx(data, wb)
                self.ExportSaleOrderXlsx(data, wb)
                self.ExportAccountPayableXlsx(data, wb)
                self.ExportRFQSrXlsx(data,wb)
                self.ExportPurchaseOrderXlsx(data, wb)
            wb.close()
            output.seek(0)
            return output.read()


    @api.model
    def excel_elems(self):
        excel_elems = dict(self._context)
        if excel_elems.get('so'):
            self.so = excel_elems.get('so')
        if excel_elems.get('po'):
            self.po = excel_elems.get('po')
        if excel_elems.get('rfq'):
            self.rfq = excel_elems.get('rfq')
        if excel_elems.get('quote'):
            self.quote = excel_elems.get('quote')
        if excel_elems.get('ar'):
            self.ar = excel_elems.get('ar')
        if excel_elems.get('ap'):
            self.ap = excel_elems.get('ap')
        # print("\n\n 222222", self.ar)



    def ExportAccountReceibaleXlsx(self, data, wb):
        # if data.get('account_receivable'):
        sheet = wb.add_worksheet(_('Accounts Receivable'))
        title_style_none = wb.add_format(
            {'align': 'center', 'font_size': 12, 'bold': True, 'bottom': 1, 'bg_color': '#EBF1DE'})
        title_style = wb.add_format(
            {'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bottom': 1, 'bg_color': '#EBF1DE'})
        # title_style1 = wb.add_format({'font_name': 'Arial', 'bold': True, 'align': 'right', 'bottom': 1})
        title_style2 = wb.add_format(
            {'font_size': 13, 'font_name': 'Arial', 'bold': True, 'align': 'center', 'bottom': 1,
             'bg_color': '#EBF1DE'})
        # line_style = wb.add_format({'font_name': 'Arial', 'align': 'right', 'valign': 'vcenter'})
        line_style1 = wb.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#EBF1DE', 'font_size': 11})
        date_format = wb.add_format(
            {'num_format': 'YYYY-mm-dd', 'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#EBF1DE',
             'font_size': 11})
        date_format_title = wb.add_format(
            {'num_format': 'dd/mm/YYYY', 'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bg_color': '#EBF1DE',
             'bottom': 1})
        row = 0
        col = 0
        sheet.write(row + 1, col, 'Number', title_style)
        sheet.write(row + 1, col + 1, 'Invoice Partner Icon', title_style)
        sheet.write(row + 1, col + 2, 'Invoice Partner Display Name', title_style)
        sheet.write(row + 1, col + 3, 'Invoice/Bill Date', title_style)
        sheet.write(row + 1, col + 4, 'Origin', title_style)
        sheet.write(row + 1, col + 5, 'Expected Payment Date', title_style)
        sheet.write(row + 1, col + 6, 'Due Date', title_style)
        sheet.write(row + 1, col + 7, 'Reference', title_style)
        sheet.write(row + 1, col + 8, 'Total Signed', title_style)
        sheet.write(row + 1, col + 9, 'Amount Due', title_style)
        sheet.write(row + 1, col + 10, 'Status', title_style)
        sheet.merge_range('A1:F1', 'Open Accounts Receivable', title_style2)
        sheet.merge_range('G1:H1', 'Open Invoices', title_style2)
        start_date = date.today().replace(day=1) + relativedelta(months=1)
        sheet.write(row + 1, col + 11, date.today(), date_format_title)
        sheet.write(row + 1, col + 12, start_date, date_format_title)
        end_date = datetime.datetime.strptime(data.get('date_duration'), "%Y-%m-%d").date()
        alphabet_lst = []
        alphabet_lst.append(self.colToExcel(12))
        date_col_count = 13
        col_cnt = 0
        while start_date <= end_date:
            period_days = data.get('period_days')
            if period_days == 15:
                alphabet_lst.append(self.colToExcel(date_col_count))
                month_count = calendar.monthrange(start_date.year, start_date.month)
                s_date = start_date.replace(year=start_date.year, month=start_date.month, day=15)
                e_date = start_date.replace(year=start_date.year, month=start_date.month, day=month_count[1])
                sheet.write(row + 1, date_col_count, s_date, date_format_title)
                date_col_count += 1
                alphabet_lst.append(self.colToExcel(date_col_count))
                sheet.write(row + 1, date_col_count, e_date, date_format_title)
                date_col_count += 1
                start_date += timedelta(days=month_count[1])
            else:
                if col_cnt > 0:
                    alphabet_lst.append(self.colToExcel(date_col_count))
                    sheet.write(row + 1, date_col_count, start_date, date_format_title)
                    date_col_count += 1
                start_date += timedelta(days=period_days)
                col_cnt +=1
        alphabet_lst.append(self.colToExcel(date_col_count))
        col_count = 12
        for vals in range(1, len(alphabet_lst)):
            total_amount_formula = '=SUBTOTAL(9,' + alphabet_lst[vals] + str(3) + ':' + alphabet_lst[vals] + str(1000)
            sheet.write_formula(0, col_count, '{' + total_amount_formula + '}', title_style)
            col_count += 1
        sheet.write('I1', '-', title_style_none)
        sheet.write_formula('J1', '{=SUBTOTAL(9,J3:J1000)}', title_style)
        sheet.write('K1', '-', title_style_none)
        sheet.write_formula('L1', '{=SUBTOTAL(9,L3:L1000)}', title_style)
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:C', 25)
        sheet.set_column(3, date_col_count, 12)
        row = 2
        account_move = self.env['account.move'].browse(data.get('account_receivable'))
        for move in account_move:
            sheet.write(row, col, move.name, line_style1)
            sheet.write(row, col + 1, '', line_style1)
            sheet.write(row, col + 2, move.partner_id.name, line_style1)
            sheet.write(row, col + 3, move.invoice_date if move.invoice_date else None, date_format)
            sheet.write(row, col + 4, move.invoice_origin if move.invoice_origin else None, line_style1)
            sheet.write(row, col + 5, move.expected_date if move.expected_date else None, date_format)
            sheet.write(row, col + 6, move.invoice_date_due if move.invoice_date_due else None, date_format)
            sheet.write(row, col + 7, move.ref if move.ref else None, line_style1)
            sheet.write(row, col + 8, move.amount_total_signed, line_style1)
            sheet.write(row, col + 9, move.amount_residual_signed, line_style1)
            sheet.write(row, col + 10, dict(move._fields['state'].selection).get(move.state), line_style1)
            # F = Expected Payment Date , G = Due Date
            first_date_col_formula = self.first_date_data_acc_rec_acc_pay(row,move.invoice_date_due,move.expected_date)
            # first_date_col_formula = '{=IF($F' + str(row + 1) + '<=L$2,$I' + str(row + 1) + ',0)}'
            if first_date_col_formula:
                sheet.write_formula(row, col + 11, first_date_col_formula, line_style1)
            elif not first_date_col_formula:
                sheet.write(row, col + 11, 0, line_style1)
            alphabet_col = 0
            for cols in range(12, date_col_count):
                find_max = 'MAX($F' + str(row+1) + ',$G' + str(row+1)
                all_date_formula = '{=IF(AND(' + find_max + ')' + '>' + str(
                    alphabet_lst[alphabet_col]) + '$2,' + find_max + ')'+'<=' + alphabet_lst[
                                       alphabet_col + 1] + '$2' + ',MIN(' + str(
                    alphabet_lst[alphabet_col]) + '$2,' + str(
                    alphabet_lst[alphabet_col + 1]) + '$2)=' + str(
                    alphabet_lst[alphabet_col]) + '$2)' + ',$J' + str(row + 1) + ',0)' + '}'
                # all_date_formula = '{=IF(AND($F' + str(row + 1) + '>' + str(
                #     alphabet_lst[alphabet_col]) + '$2,$F' + str(row + 1) + '<=' + alphabet_lst[
                #                        alphabet_col + 1] + '$2'+',MIN('+ str(alphabet_lst[alphabet_col]) + '$2,' + str(
                #     alphabet_lst[alphabet_col + 1]) + '$2)='+ str(
                #     alphabet_lst[alphabet_col]) + '$2)' +',$I' + str(row + 1) + ',0)' +'}'
                sheet.write_formula(row, cols, all_date_formula, line_style1)
                alphabet_col += 1
            row += 1

    def ExportAccountPayableXlsx(self,data, wb):
        # if data.get('account_payable'):
        sheet = wb.add_worksheet(_('Accounts Payables'))
        title_style_none = wb.add_format(
            {'align': 'center', 'font_size': 12, 'bold': True, 'bottom': 1, 'bg_color': '#E6E0EC'})
        title_style = wb.add_format(
            {'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bottom': 1, 'bg_color': '#E6E0EC'})
        # title_style1 = wb.add_format({'font_name': 'Arial', 'bold': True, 'align': 'right', 'bottom': 1})
        title_style2 = wb.add_format(
            {'font_size': 13, 'font_name': 'Arial', 'bold': True, 'align': 'center', 'bottom': 1,
             'bg_color': '#E6E0EC'})
        # line_style = wb.add_format({'font_name': 'Arial', 'align': 'right', 'valign': 'vcenter'})
        line_style1 = wb.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#E6E0EC', 'font_size': 11})
        date_format = wb.add_format(
            {'num_format': 'YYYY-mm-dd', 'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#E6E0EC',
             'font_size': 11})
        date_format_title = wb.add_format(
            {'num_format': 'dd/mm/YYYY', 'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bg_color': '#E6E0EC',
             'bottom': 1})
        row = 0
        col = 0

        sheet.write(row + 1, col, 'Number', title_style)
        sheet.write(row + 1, col + 1, 'Invoice Partner Icon', title_style)
        sheet.write(row + 1, col + 2, 'Invoice Partner Display Name', title_style)
        sheet.write(row + 1, col + 3, 'Invoice/Bill Date', title_style)
        sheet.write(row + 1, col + 4, 'Origin', title_style)
        sheet.write(row + 1, col + 5, 'Planned Payment Date', title_style)
        sheet.write(row + 1, col + 6, 'Due Date', title_style)
        sheet.write(row + 1, col + 7, 'Reference', title_style)
        sheet.write(row + 1, col + 8, 'Total Due', title_style)
        sheet.write(row + 1, col + 9, 'Remaining Due', title_style)
        sheet.write(row + 1, col + 10, 'Status', title_style)
        sheet.merge_range('A1:F1', 'Bills', title_style2)
        sheet.merge_range('G1:H1', 'Open Account Payables', title_style2)
        start_date = date.today().replace(day=1) + relativedelta(months=1)
        sheet.write(row + 1, col + 11, date.today(), date_format_title)
        sheet.write(row + 1, col + 12, start_date, date_format_title)
        end_date = datetime.datetime.strptime(data.get('date_duration'), "%Y-%m-%d").date()
        alphabet_lst = []
        alphabet_lst.append(self.colToExcel(12))
        date_col_count = 13
        col_cnt = 0
        while start_date <= end_date:
            period_days = data.get('period_days')
            if period_days == 15:
                alphabet_lst.append(self.colToExcel(date_col_count))
                month_count = calendar.monthrange(start_date.year, start_date.month)
                s_date = start_date.replace(year=start_date.year, month=start_date.month, day=15)
                e_date = start_date.replace(year=start_date.year, month=start_date.month, day=month_count[1])
                sheet.write(row + 1, date_col_count, s_date, date_format_title)
                date_col_count += 1
                alphabet_lst.append(self.colToExcel(date_col_count))
                sheet.write(row + 1, date_col_count, e_date, date_format_title)
                date_col_count += 1
                start_date += timedelta(days=month_count[1])
            else:
                if col_cnt > 0:
                    alphabet_lst.append(self.colToExcel(date_col_count))
                    sheet.write(row + 1, date_col_count, start_date, date_format_title)
                    date_col_count += 1
                start_date += timedelta(days=period_days)
                col_cnt += 1
        alphabet_lst.append(self.colToExcel(date_col_count))
        col_count = 12
        for vals in range(1, len(alphabet_lst)):
            total_amount_formula = '=SUBTOTAL(9,' + alphabet_lst[vals] + str(3) + ':' + alphabet_lst[vals] + str(1000)
            sheet.write_formula(0, col_count, '{' + total_amount_formula + '}', title_style)
            col_count += 1
        sheet.write('I1', '-', title_style_none)
        sheet.write_formula('J1','{=SUBTOTAL(9,J3:J1000)}', title_style)
        sheet.write('K1', '-', title_style_none)
        sheet.write_formula('L1', '{=SUBTOTAL(9,L3:K1000)}', title_style)
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:C', 25)
        sheet.set_column(3, date_col_count, 11)
        row = 2
        account_move = self.env['account.move'].browse(data.get('account_payable'))
        for move in account_move:
            sheet.write(row, col, move.name, line_style1)
            sheet.write(row, col + 1, '', line_style1)
            sheet.write(row, col + 2, move.partner_id.name, line_style1)
            sheet.write(row, col + 3, move.invoice_date if move.invoice_date else None, date_format)
            sheet.write(row, col + 4, move.invoice_origin if move.invoice_origin else None, line_style1)
            sheet.write(row, col + 5, move.expected_date if move.expected_date else None, date_format)
            sheet.write(row, col + 6, move.invoice_date_due if move.invoice_date_due else None, date_format)
            sheet.write(row, col + 7, move.ref if move.ref else None, line_style1)
            sheet.write(row, col + 8, ( - move.amount_total_signed), line_style1)
            sheet.write(row, col + 9, ( - move.amount_residual_signed), line_style1)
            sheet.write(row, col + 10, dict(move._fields['state'].selection).get(move.state), line_style1)
            # first_date_col_formula = '{=IF($F' + str(row + 1) + '<=K$2,$I' + str(row + 1) + ',0)}'
            # sheet.write_formula(row, col + 12, first_date_col_formula, line_style1)
            # F = Expected Payment Date , G = Due Date
            first_date_col_formula = self.first_date_data_acc_rec_acc_pay(row, move.invoice_date_due,
                                                                          move.expected_date)
            # first_date_col_formula = '{=IF($F' + str(row + 1) + '<=L$2,$I' + str(row + 1) + ',0)}'
            if first_date_col_formula:
                sheet.write_formula(row, col + 11, first_date_col_formula, line_style1)
            elif not first_date_col_formula:
                sheet.write(row, col + 11, 0, line_style1)

            alphabet_col = 0
            for cols in range(12, date_col_count):
                find_max = 'MAX($F' + str(row + 1) + ',$G' + str(row + 1)
                all_date_formula = '{=IF(AND(' + find_max + ')' + '>' + str(
                    alphabet_lst[alphabet_col]) + '$2,' + find_max + ')' + '<=' + alphabet_lst[
                                       alphabet_col + 1] + '$2' + ',MIN(' + str(
                    alphabet_lst[alphabet_col]) + '$2,' + str(
                    alphabet_lst[alphabet_col + 1]) + '$2)=' + str(
                    alphabet_lst[alphabet_col]) + '$2)' + ',$J' + str(row + 1) + ',0)' + '}'
                sheet.write_formula(row, cols, all_date_formula, line_style1)
                alphabet_col += 1
            row += 1

    def first_date_data_acc_rec_acc_pay(self,row,invoice_date_due,expected_date):
        # F = Expected Payment Date , G = Due Date
        first_date_col_formula = ''
        if not invoice_date_due:
            if expected_date:
                if expected_date <= self.return_today():
                    first_date_col_formula = '{=IF($F' + str(row + 1) + '<=L$2,$J' + str(row + 1) + ',0)}'
        if not expected_date:
            if invoice_date_due:
                if invoice_date_due <= self.return_today():
                    first_date_col_formula = '{=IF($G' + str(row + 1) + '<=L$2,$J' + str(row + 1) + ',0)}'
        if expected_date and invoice_date_due:
            if invoice_date_due > expected_date and invoice_date_due <= self.return_today():
                first_date_col_formula = '{=IF($G' + str(row + 1) + '<=L$2,$J' + str(row + 1) + ',0)}'
        if expected_date and invoice_date_due:
            if expected_date > invoice_date_due and expected_date <= self.return_today():
                first_date_col_formula = '{=IF($F' + str(row + 1) + '<=L$2,$J' + str(row + 1) + ',0)}'
        if expected_date and invoice_date_due:
            if invoice_date_due == expected_date and invoice_date_due <= self.return_today():
                first_date_col_formula = '{=IF($G' + str(row + 1) + '<=L$2,$J' + str(row + 1) + ',0)}'
        return first_date_col_formula

    def num_to_col_letters(self,num):
        letters = ''
        while num:
            mod = (num - 1) % 26
            letters += chr(mod + 65)
            num = (num - 1) // 26
        return ''.join(reversed(letters))

    def ExportQuotationXlsx(self, data, wb):
        # if data.get('quotations'):
        sheet = wb.add_worksheet(_('Quotations'))
        title_style_none = wb.add_format(
            {'align': 'center', 'font_size': 12, 'bold': True, 'bottom': 1, 'bg_color': '#DBEEF4'})
        title_style = wb.add_format(
            {'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bg_color': '#DBEEF4', 'bottom': 1})
        title_style2 = wb.add_format(
            {'font_size': 13, 'font_name': 'Arial', 'bold': True, 'align': 'center', 'bg_color': '#DBEEF4',
             'bottom': 1})
        line_style1 = wb.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#DBEEF4', 'font_size': 11})
        date_format = wb.add_format(
            {'num_format': 'dd/mm/YYYY hh:mm:ss', 'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#DBEEF4',
             'font_size': 11})
        date_format2 = wb.add_format(
            {'num_format': 'dd/mm/YYYY', 'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#DBEEF4',
             'font_size': 11})
        date_format_title = wb.add_format(
            {'num_format': 'dd/mm/YYYY', 'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bg_color': '#DBEEF4',
             'bottom': 1})
        row = 0
        col = 0
        sheet.write(row + 1, col, 'Order Reference', title_style)
        sheet.write(row + 1, col + 1, 'Order Date', title_style)
        sheet.write(row + 1, col + 2, 'Delivery Date', title_style)
        sheet.write(row + 1, col + 3, 'Expected Date', title_style)
        sheet.write(row + 1, col + 4, 'Customer', title_style)
        sheet.write(row + 1, col + 5, 'Customer Reference', title_style)
        sheet.write(row + 1, col + 6, 'Total', title_style)
        sheet.write(row + 1, col + 7, 'Invoice Status', title_style)
        sheet.merge_range('A1:F1', 'Quotations', title_style2)
        start_date = date.today().replace(day=1) + relativedelta(months=1)
        sheet.write(row + 1, col + 8, date.today(), date_format_title)
        sheet.write(row + 1, col + 9, start_date, date_format_title)
        end_date = datetime.datetime.strptime(data.get('date_duration'), "%Y-%m-%d").date()
        alphabet_lst = []
        date_col_count = 10
        col_cnt = 0
        list_of_dates = []
        list_of_dates.append(start_date)
        while start_date <= end_date:
            period_days = data.get('period_days')
            if period_days == 15:
                alphabet_lst.append(self.colToExcel(date_col_count))
                month_count = calendar.monthrange(start_date.year, start_date.month)
                s_date = start_date.replace(year=start_date.year, month=start_date.month, day=15)
                e_date = start_date.replace(year=start_date.year, month=start_date.month, day=month_count[1])
                sheet.write(row + 1, date_col_count, s_date, date_format_title)
                date_col_count += 1
                alphabet_lst.append(self.colToExcel(date_col_count))
                sheet.write(row + 1, date_col_count, e_date, date_format_title)
                date_col_count += 1
                list_of_dates.append(s_date)
                list_of_dates.append(e_date)
                start_date += timedelta(days=month_count[1])
            else:
                if col_cnt > 0:
                    alphabet_lst.append(self.colToExcel(date_col_count))
                    sheet.write(row + 1, date_col_count, start_date, date_format_title)
                    date_col_count += 1
                list_of_dates.append(start_date)
                start_date += timedelta(days=period_days)
                col_cnt += 1
        alphabet_lst.append(self.colToExcel(date_col_count))
        col_count = 9
        for vals in alphabet_lst:
            total_amount_formula = '=SUBTOTAL(9,' + str(vals) + str(3) + ':' + str(
                vals) + str(1000)
            sheet.write_formula(0, col_count, '{' + total_amount_formula + '}', title_style)
            col_count += 1
        sheet.write_formula('G1', '{=SUBTOTAL(9,G3:G1000)}', title_style)
        # sheet.write_formula('J1', '{=SUBTOTAL(9,J3:J1000)}', title_style)
        sheet.write('H1', '-', title_style_none)
        sheet.write_formula('I1', '{=SUBTOTAL(9,I3:I1000)}', title_style)
        alphabet_lst.append(self.colToExcel(date_col_count + 1))
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 16)
        sheet.set_column('D:D', 10)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 15)
        sheet.set_column(6, date_col_count, 9)
        row = 2
        sale_orders = self.env['sale.order'].browse(data.get('quotations'))
        for order in sale_orders:
            date_order = datetime.datetime.strptime(str(order.date_order),
                                                    "%Y-%m-%d %H:%M:%S") if order.date_order else None
            commitment_date = datetime.datetime.strptime(str(order.commitment_date),
                                                         "%Y-%m-%d %H:%M:%S") if order.commitment_date else None
            sheet.write(row, col, order.name, line_style1)
            sheet.write(row, col + 1, date_order, date_format)
            sheet.write(row, col + 2, commitment_date, date_format)
            sheet.write(row, col + 3, order.new_expected_date, date_format2)
            sheet.write(row, col + 4, order.partner_id.name, line_style1)
            sheet.write(row, col + 5, order.client_order_ref if order.client_order_ref else None, line_style1)
            sheet.write(row, col + 6, order.amount_total, line_style1)
            sheet.write(row, col + 7, dict(order._fields['invoice_status'].selection).get(order.invoice_status),
                        line_style1)
            first_date_col_formula = '{=IF($D' + str(row + 1) + '<=I$2,$G' + str(row + 1) + ',0)}'
            sheet.write_formula(row, col + 8, first_date_col_formula, line_style1)
            alphabet_col = 0
            alphabet_lst.append("I")
            for cols in range(9, date_col_count):
                all_date_formula = '{=IF(AND($D' + str(row + 1) + '>' + \
                                   str(alphabet_lst[alphabet_col-1]) + \
                                   '$2,$D' + str(row + 1) + '<=' + str(alphabet_lst[alphabet_col]) \
                                   + '$2' + ',MIN(' + str(
                    alphabet_lst[alphabet_col - 1]) + '$2,' + str(
                    alphabet_lst[alphabet_col]) + '$2)=' + str(
                    alphabet_lst[alphabet_col - 1]) + '$2),$G' + str(row + 1) + ',0)}'
                sheet.write_formula(row, cols, all_date_formula, line_style1)
                alphabet_col += 1
            row += 1

    def ExportSaleOrderXlsx(self, data, wb):
        # if data.get('sale_order'):
        sheet = wb.add_worksheet(_('Sales Orders'))
        title_style_none = wb.add_format(
            {'align': 'center', 'font_size': 12, 'bold': True, 'bottom': 1, 'bg_color': '#DBEEF4'})
        title_style = wb.add_format(
            {'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bg_color': '#DBEEF4', 'bottom': 1})
        title_style2 = wb.add_format(
            {'font_size': 13, 'font_name': 'Arial', 'bold': True, 'align': 'center', 'bg_color': '#DBEEF4',
             'bottom': 1})
        line_style1 = wb.add_format({'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#DBEEF4', 'font_size': 11})
        date_format = wb.add_format(
            {'num_format': 'dd/mm/YYYY hh:mm:ss', 'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#DBEEF4',
             'font_size': 11})
        date_format2 = wb.add_format(
            {'num_format': 'dd/mm/YYYY', 'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#DBEEF4',
             'font_size': 11})
        date_format_title = wb.add_format(
            {'num_format': 'dd/mm/YYYY', 'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bg_color': '#DBEEF4',
             'bottom': 1})
        row = 0
        col = 0
        sheet.write(row + 1, col, 'Order Reference', title_style)
        sheet.write(row + 1, col + 1, 'Order Date', title_style)
        sheet.write(row + 1, col + 2, 'Delivery Date', title_style)
        sheet.write(row + 1, col + 3, 'Expected Date', title_style)
        sheet.write(row + 1, col + 4, 'Customer', title_style)
        sheet.write(row + 1, col + 5, 'Customer Reference', title_style)
        sheet.write(row + 1, col + 6, 'Total', title_style)
        sheet.write(row + 1, col + 7, 'Delivered Amount', title_style)
        sheet.write(row + 1, col + 8, 'Pending Amount', title_style)
        sheet.write(row + 1, col + 9, 'Remaining Funds To Be Received', title_style)
        sheet.write(row + 1, col + 10, 'Invoice Status', title_style)
        sheet.merge_range('A1:F1', 'Sales Orders', title_style2)
        sheet.merge_range('G1:H1', 'Sales Orders', title_style2)
        start_date = date.today().replace(day=1) + relativedelta(months=1)
        sheet.write(row + 1, col + 11, date.today(), date_format_title)
        sheet.write(row + 1, col + 12, start_date, date_format_title)
        end_date = datetime.datetime.strptime(data.get('date_duration'), "%Y-%m-%d").date()
        alphabet_lst = []
        date_col_count = 13
        col_cnt = 0
        list_of_dates = []
        list_of_dates.append(start_date)
        while start_date <= end_date:
            period_days = data.get('period_days')
            if period_days == 15:
                alphabet_lst.append(self.colToExcel(date_col_count))
                month_count = calendar.monthrange(start_date.year, start_date.month)
                s_date = start_date.replace(year=start_date.year, month=start_date.month, day=15)
                e_date = start_date.replace(year=start_date.year, month=start_date.month, day=month_count[1])
                sheet.write(row + 1, date_col_count, s_date, date_format_title)
                date_col_count += 1
                alphabet_lst.append(self.colToExcel(date_col_count))
                sheet.write(row + 1, date_col_count, e_date, date_format_title)
                date_col_count += 1
                list_of_dates.append(s_date)
                list_of_dates.append(e_date)
                start_date += timedelta(days=month_count[1])
            else:
                if col_cnt > 0:
                    alphabet_lst.append(self.colToExcel(date_col_count))
                    sheet.write(row + 1, date_col_count, start_date, date_format_title)
                    date_col_count += 1
                list_of_dates.append(start_date)
                start_date += timedelta(days=period_days)
                col_cnt += 1
        alphabet_lst.append(self.colToExcel(date_col_count))
        col_count = 12
        for vals in alphabet_lst:
            total_amount_formula = '=SUBTOTAL(9,' + str(vals) + str(3) + ':' + str(
                vals) + str(1000)
            sheet.write_formula(0, col_count, '{' + total_amount_formula + '}', title_style)
            col_count += 1
        sheet.write_formula('I1', '{=SUBTOTAL(9,I3:I1000)}', title_style)
        sheet.write_formula('J1', '{=SUBTOTAL(9,J3:J1000)}', title_style)
        sheet.write('K1', '-', title_style_none)
        sheet.write_formula('L1', '{=SUBTOTAL(9,L3:L1000)}', title_style)
        alphabet_lst.append(self.colToExcel(date_col_count + 1))
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 16)
        sheet.set_column('D:D', 10)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 15)
        sheet.set_column(6, date_col_count, 11)
        row = 2
        sale_orders = self.env['sale.order'].browse(data.get('sale_order'))
        for order in sale_orders:
            date_order = datetime.datetime.strptime(str(order.date_order),
                                                    "%Y-%m-%d %H:%M:%S") if order.date_order else None
            commitment_date = datetime.datetime.strptime(str(order.commitment_date),
                                                         "%Y-%m-%d %H:%M:%S") if order.commitment_date else None
            expected_date = datetime.datetime.strptime(str(order.expected_date),
                                                       "%Y-%m-%d %H:%M:%S").date() if order.expected_date else None
            sheet.write(row, col, order.name, line_style1)
            sheet.write(row, col + 1, date_order, date_format)
            sheet.write(row, col + 2, commitment_date, date_format)
            sheet.write(row, col + 3, order.new_expected_date, date_format2)
            sheet.write(row, col + 4, order.partner_id.name, line_style1)
            sheet.write(row, col + 5, order.client_order_ref if order.client_order_ref else None, line_style1)
            sheet.write(row, col + 6, order.amount_total, line_style1)
            sheet.write(row, col + 7, order.delivered_amount, line_style1)
            sheet.write_number(row, col + 8, order.pending_amount, line_style1)
            sheet.write_number(row, col + 9, order.remaining_funds_to_be_received, line_style1)
            sheet.write(row, col + 10, dict(order._fields['invoice_status'].selection).get(order.invoice_status),
                        line_style1)
            first_date_col_formula = '{=IF($D' + str(row + 1) + '<=L$2,$J' + str(row + 1) + ',0)}'
            sheet.write_formula(row, col + 11, first_date_col_formula, line_style1)
            alphabet_col = 0
            alphabet_lst.append("L")
            for cols in range(12, date_col_count):
                all_date_formula = '{=IF(AND($D' + str(row + 1) + '>' + \
                                   str(alphabet_lst[alphabet_col-1]) + \
                                   '$2,$D' + str(row + 1) + '<=' + str(alphabet_lst[alphabet_col]) \
                                   + '$2' + ',MIN(' + str(
                    alphabet_lst[alphabet_col - 1]) + '$2,' + str(
                    alphabet_lst[alphabet_col]) + '$2)=' + str(
                    alphabet_lst[alphabet_col - 1]) + '$2),$J' + str(row + 1) + ',0)}'
                sheet.write_formula(row, cols, all_date_formula, line_style1)
                alphabet_col += 1
            row += 1

    def ExportRFQSrXlsx(self, data, wb):
        # if data.get('rfqs'):
        sheet = wb.add_worksheet(_('Request For Quotation'))
        title_style = wb.add_format(
            {'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bottom': 1, 'bg_color': '#EBF1DE'})
        title_style_none = wb.add_format(
            {'align': 'center', 'font_size': 12, 'bold': True, 'bottom': 1, 'bg_color': '#EBF1DE'})
        # title_style1 = wb.add_format({'font_name': 'Arial', 'bold': True, 'align': 'right', 'bottom': 1})
        title_style2 = wb.add_format(
            {'font_size': 13, 'font_name': 'Arial', 'bold': True, 'align': 'center', 'bottom': 1,
             'bg_color': '#EBF1DE'})
        title_style3 = wb.add_format(
            {'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bottom': 1, 'bg_color': '#B7DEE8'})
        title_style4 = wb.add_format(
            {'font_size': 13, 'font_name': 'Arial', 'bold': True, 'bottom': 1, 'bg_color': '#B7DEE8'})
        line_style1 = wb.add_format(
            {'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#D7E4BD', 'font_size': 11})
        line_style2 = wb.add_format(
            {'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#B7DEE8', 'font_size': 11})
        date_format = wb.add_format(
            {'num_format': 'YYYY-mm-dd hh:mm:ss', 'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#D7E4BD',
             'font_size': 12})
        date_format_title = wb.add_format(
            {'num_format': 'dd/mm/YYYY', 'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bg_color': '#EBF1DE',
             'bottom': 1})
        row = 0
        col = 0
        sheet.write(row + 1, col, 'Order Reference', title_style)
        sheet.write(row + 1, col + 1, 'Expected Date', title_style)
        sheet.write(row + 1, col + 2, 'Confirmation Date', title_style)
        sheet.write(row + 1, col + 3, 'Vendor', title_style)
        sheet.write(row + 1, col + 4, 'Receipt Date', title_style)
        sheet.write(row + 1, col + 5, 'Purchase Representative', title_style)
        sheet.write(row + 1, col + 6, 'Source Document', title_style)
        sheet.write(row + 1, col + 7, 'Advance Payment', title_style)
        sheet.write(row + 1, col + 8, 'Remaining Amount', title_style)
        sheet.write(row + 1, col + 9, 'Remaining to be Received', title_style)
        sheet.write(row + 1, col + 10, 'Remaining to be Billed', title_style)
        sheet.write(row + 1, col + 11, 'Total', title_style)
        sheet.write(row + 1, col + 12, 'Billing Status', title_style)
        sheet.write(row + 1, col + 13, 'Left to be Paid ', title_style4)
        sheet.merge_range('A1:F1', 'Request For Quotation', title_style2)
        sheet.merge_range('G1:H1', 'Request For Quotation', title_style2)
        # sheet.write_formula(0, col + 14, '{=SUBTOTAL(9,M3:M1000)}', title_style3)
        start_date = date.today().replace(day=1) + relativedelta(months=1)
        sheet.write(row + 1, col + 14, date.today(), date_format_title)
        sheet.write(row + 1, col + 15, start_date, date_format_title)
        end_date = datetime.datetime.strptime(data.get('date_duration'), "%Y-%m-%d").date()
        alphabet_lst = []
        alphabet_lst.append(self.colToExcel(15))
        date_col_count = 16
        col_cnt = 0
        while start_date <= end_date:
            period_days = data.get('period_days')
            if period_days == 15:
                alphabet_lst.append(self.colToExcel(date_col_count))
                month_count = calendar.monthrange(start_date.year, start_date.month)
                s_date = start_date.replace(year=start_date.year, month=start_date.month, day=15)
                e_date = start_date.replace(year=start_date.year, month=start_date.month, day=month_count[1])
                sheet.write(row + 1, date_col_count, s_date, date_format_title)
                date_col_count += 1
                alphabet_lst.append(self.colToExcel(date_col_count))
                sheet.write(row + 1, date_col_count, e_date, date_format_title)
                date_col_count += 1
                start_date += timedelta(days=month_count[1])
            else:
                if col_cnt > 0:
                    alphabet_lst.append(self.colToExcel(date_col_count))
                    sheet.write(row + 1, date_col_count, start_date, date_format_title)
                    date_col_count += 1
                start_date += timedelta(days=period_days)
                col_cnt += 1
        alphabet_lst.append(self.colToExcel(date_col_count))
        col_count = 15
        # for vals in alphabet_lst:
        #     total_amount_formula = '=SUBTOTAL(9,' + str(vals) + str(3) + ':' + str(
        #         vals) + str(1000)
        #     sheet.write_formula(0, col_count, '{' + total_amount_formula + '}', title_style)
        #     col_count += 1
        for vals in range(1, len(alphabet_lst)):
            total_amount_formula = '=SUBTOTAL(9,' + alphabet_lst[vals] + str(3) + ':' + alphabet_lst[vals] + str(1000)
            sheet.write_formula(0, col_count, '{' + total_amount_formula + '}', title_style)
            col_count += 1
        # sheet.write_formula('I1', '{=SUBTOTAL(9,I3:I1000)}', title_style)
        sheet.write('I1', '-', title_style_none)
        sheet.write_formula('J1', '{=SUBTOTAL(9,J3:J1000)}', title_style)
        sheet.write_formula('K1', '{=SUBTOTAL(9,K3:K1000)}', title_style)
        sheet.write_formula('L1', '{=SUBTOTAL(9,L3:L1000)}', title_style)
        sheet.write('M1', '-', title_style_none)
        sheet.write_formula('N1', '{=SUBTOTAL(9,N3:N1000)}', title_style)
        sheet.write_formula('O1', '{=SUBTOTAL(9,O3:O1000)}', title_style)
        # header_total_amount_formula = '{=SUM(' + alphabet_lst[0] + str(1) + ':' + alphabet_lst[-1] + str(1) + ')}'
        # sheet.write_formula(0, date_col_count + 1, header_total_amount_formula)
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column(4, date_col_count, 13)
        row = 2
        purchase_orders = self.env['purchase.order'].browse(data.get('rfqs'))
        for order in purchase_orders:
            sheet.write(row, col, order.name, line_style1)
            sheet.write(row, col + 1, order.expected_date if order.expected_date else None, date_format)
            sheet.write(row, col + 2, order.date_approve if order.date_approve else None, date_format)
            sheet.write(row, col + 3, order.partner_id.name, line_style1)
            sheet.write(row, col + 4, order.date_planned if order.date_planned else None, date_format)
            sheet.write(row, col + 5, order.user_id.name, line_style1)
            sheet.write(row, col + 6, order.origin if order.origin else None, line_style1)
            sheet.write(row, col + 7, order.advance_payment, line_style1)
            sheet.write(row, col + 8, order.remaining_amount, line_style1)
            sheet.write(row, col + 9, order.qty_received_total, line_style1)
            sheet.write(row, col + 10, order.qty_billed_total, line_style1)
            sheet.write(row, col + 11, order.amount_total, line_style1)
            sheet.write(row, col + 12,
                        dict(order._fields['invoice_status'].selection).get(order.invoice_status), line_style1)
            to_be_paid_formula = '=IF(AND(I' + str(row + 1) + '=0,J' + str(row + 1) + '>I' + str(
                row + 1) + '),J' + str(row + 1) + ',I' + str(row + 1) + ')'
            sheet.write_formula(row, col + 13, '{' + to_be_paid_formula + '}', line_style2)

            first_date_col_formula = '{=IF($B' + str(row + 1) + '<=O$2,$N' + str(row + 1) + ',0)}'
            sheet.write_formula(row, col + 14, first_date_col_formula, line_style1)
            alphabet_col = 0
            for cols in range(15, date_col_count):

                all_date_formula = '{=IF(AND($B' + str(row + 1) + '>' + \
                                   str(alphabet_lst[alphabet_col]) + \
                                   '$2,$B' + str(row + 1) + '<=' + str(alphabet_lst[alphabet_col+1]) \
                                   + '$2' + ',MIN(' + str(
                    alphabet_lst[alphabet_col]) + '$2,' + str(
                    alphabet_lst[alphabet_col+1]) + '$2)=' + str(
                    alphabet_lst[alphabet_col ]) + '$2),$N' + str(row + 1) + ',0)}'
                sheet.write_formula(row, cols, all_date_formula, line_style1)

                alphabet_col += 1
            row += 1

    def ExportPurchaseOrderXlsx(self, data, wb):
        # if data.get('purchase_order'):
        sheet = wb.add_worksheet(_('Open Purchase Orders'))
        title_style = wb.add_format(
            {'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bottom': 1, 'bg_color': '#EBF1DE'})
        title_style_none = wb.add_format(
            {'align': 'center', 'font_size': 12, 'bold': True, 'bottom': 1, 'bg_color': '#EBF1DE'})
        # title_style1 = wb.add_format({'font_name': 'Arial', 'bold': True, 'align': 'right', 'bottom': 1})
        title_style2 = wb.add_format(
            {'font_size': 13, 'font_name': 'Arial', 'bold': True, 'align': 'center', 'bottom': 1,
             'bg_color': '#EBF1DE'})
        title_style3 = wb.add_format(
            {'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bottom': 1, 'bg_color': '#B7DEE8'})
        title_style4 = wb.add_format(
            {'font_size': 13, 'font_name': 'Arial', 'bold': True, 'bottom': 1, 'bg_color': '#B7DEE8'})
        line_style1 = wb.add_format(
            {'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#D7E4BD', 'font_size': 11})
        line_style2 = wb.add_format(
            {'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#B7DEE8', 'font_size': 11})
        date_format = wb.add_format(
            {'num_format': 'YYYY-mm-dd hh:mm:ss', 'font_name': 'Arial', 'valign': 'vcenter', 'bg_color': '#D7E4BD',
             'font_size': 12})
        date_format_title = wb.add_format(
            {'num_format': 'dd/mm/YYYY', 'font_size': 12, 'font_name': 'Arial', 'bold': True, 'bg_color': '#EBF1DE',
             'bottom': 1})
        row = 0
        col = 0
        sheet.write(row + 1, col, 'Order Reference', title_style)
        sheet.write(row + 1, col + 1, 'Expected Date', title_style)
        sheet.write(row + 1, col + 2, 'Confirmation Date', title_style)
        sheet.write(row + 1, col + 3, 'Vendor', title_style)
        sheet.write(row + 1, col + 4, 'Receipt Date', title_style)
        sheet.write(row + 1, col + 5, 'Purchase Representative', title_style)
        sheet.write(row + 1, col + 6, 'Source Document', title_style)
        sheet.write(row + 1, col + 7, 'Advance Payment', title_style)
        sheet.write(row + 1, col + 8, 'Remaining Amount', title_style)
        sheet.write(row + 1, col + 9, 'Remaining to be Received', title_style)
        sheet.write(row + 1, col + 10, 'Remaining to be Billed', title_style)
        sheet.write(row + 1, col + 11, 'Total', title_style)
        sheet.write(row + 1, col + 12, 'Billing Status', title_style)
        sheet.write(row + 1, col + 13, 'Left to be Paid ', title_style4)
        sheet.merge_range('A1:F1', 'Purchase Orders', title_style2)
        sheet.merge_range('G1:H1', 'Purchase Orders', title_style2)
        # sheet.write_formula(0, col + 14, '{=SUBTOTAL(9,M3:M1000)}', title_style3)
        start_date = date.today().replace(day=1) + relativedelta(months=1)
        sheet.write(row + 1, col + 14, date.today(), date_format_title)
        sheet.write(row + 1, col + 15, start_date, date_format_title)
        end_date = datetime.datetime.strptime(data.get('date_duration'), "%Y-%m-%d").date()
        alphabet_lst = []
        alphabet_lst.append(self.colToExcel(15))
        date_col_count = 16
        col_cnt = 0
        while start_date <= end_date:
            period_days = data.get('period_days')
            if period_days == 15:
                alphabet_lst.append(self.colToExcel(date_col_count))
                month_count = calendar.monthrange(start_date.year, start_date.month)
                s_date = start_date.replace(year=start_date.year, month=start_date.month, day=15)
                e_date = start_date.replace(year=start_date.year, month=start_date.month, day=month_count[1])
                sheet.write(row + 1, date_col_count, s_date, date_format_title)
                date_col_count += 1
                alphabet_lst.append(self.colToExcel(date_col_count))
                sheet.write(row + 1, date_col_count, e_date, date_format_title)
                date_col_count += 1
                start_date += timedelta(days=month_count[1])
            else:
                if col_cnt > 0:
                    alphabet_lst.append(self.colToExcel(date_col_count))
                    sheet.write(row + 1, date_col_count, start_date, date_format_title)
                    date_col_count += 1
                start_date += timedelta(days=period_days)
                col_cnt += 1
        alphabet_lst.append(self.colToExcel(date_col_count))
        col_count = 15
        # for vals in alphabet_lst:
        #     total_amount_formula = '=SUBTOTAL(9,' + str(vals) + str(3) + ':' + str(
        #         vals) + str(1000)
        #     sheet.write_formula(0, col_count, '{' + total_amount_formula + '}', title_style)
        #     col_count += 1
        for vals in range(1, len(alphabet_lst)):
            total_amount_formula = '=SUBTOTAL(9,' + alphabet_lst[vals] + str(3) + ':' + alphabet_lst[vals] + str(1000)
            sheet.write_formula(0, col_count, '{' + total_amount_formula + '}', title_style)
            col_count += 1
        # sheet.write_formula('I1', '{=SUBTOTAL(9,I3:I1000)}', title_style)
        sheet.write('I1', '-', title_style_none)
        sheet.write_formula('J1', '{=SUBTOTAL(9,J3:J1000)}', title_style)
        sheet.write_formula('K1', '{=SUBTOTAL(9,K3:K1000)}', title_style)
        sheet.write_formula('L1', '{=SUBTOTAL(9,L3:L1000)}', title_style)
        sheet.write('M1', '-', title_style_none)
        sheet.write_formula('N1', '{=SUBTOTAL(9,N3:N1000)}', title_style)
        sheet.write_formula('O1', '{=SUBTOTAL(9,O3:O1000)}', title_style)
        # header_total_amount_formula = '{=SUM(' + alphabet_lst[0] + str(1) + ':' + alphabet_lst[-1] + str(1) + ')}'
        # sheet.write_formula(0, date_col_count + 1, header_total_amount_formula)
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column(4, date_col_count, 13)
        row = 2
        purchase_orders = self.env['purchase.order'].browse(data.get('purchase_order'))
        for order in purchase_orders:
            sheet.write(row, col, order.name, line_style1)
            sheet.write(row, col + 1, order.expected_date if order.expected_date else None, date_format)
            sheet.write(row, col + 2, order.date_approve if order.date_approve else None, date_format)
            sheet.write(row, col + 3, order.partner_id.name, line_style1)
            sheet.write(row, col + 4, order.date_planned if order.date_planned else None, date_format)
            sheet.write(row, col + 5, order.user_id.name, line_style1)
            sheet.write(row, col + 6, order.origin if order.origin else None, line_style1)
            sheet.write(row, col + 7, order.advance_payment, line_style1)
            sheet.write(row, col + 8, order.remaining_amount, line_style1)
            sheet.write(row, col + 9, order.qty_received_total, line_style1)
            sheet.write(row, col + 10, order.qty_billed_total, line_style1)
            sheet.write(row, col + 11, order.amount_total, line_style1)
            sheet.write(row, col + 12,
                        dict(order._fields['invoice_status'].selection).get(order.invoice_status), line_style1)
            to_be_paid_formula = '=IF(AND(I' + str(row + 1) + '=0,J' + str(row + 1) + '>I' + str(
                row + 1) + '),J' + str(row + 1) + ',I' + str(row + 1) + ')'
            sheet.write_formula(row, col + 13, '{' + to_be_paid_formula + '}', line_style2)

            first_date_col_formula = '{=IF($B' + str(row + 1) + '<=O$2,$N' + str(row + 1) + ',0)}'
            sheet.write_formula(row, col + 14, first_date_col_formula, line_style1)
            alphabet_col = 0
            for cols in range(15, date_col_count):

                all_date_formula = '{=IF(AND($B' + str(row + 1) + '>' + \
                                   str(alphabet_lst[alphabet_col]) + \
                                   '$2,$B' + str(row + 1) + '<=' + str(alphabet_lst[alphabet_col+1]) \
                                   + '$2' + ',MIN(' + str(
                    alphabet_lst[alphabet_col]) + '$2,' + str(
                    alphabet_lst[alphabet_col+1]) + '$2)=' + str(
                    alphabet_lst[alphabet_col ]) + '$2),$N' + str(row + 1) + ',0)}'
                sheet.write_formula(row, cols, all_date_formula, line_style1)

                alphabet_col += 1
            row += 1

    def ExportFinalCashFlowXlsx(self, data, wb):
        sheet = wb.add_worksheet(_('Cash Flow 2020'))
        title_style = wb.add_format({'font_size': 15, 'font_name': 'Arial', 'bold': True, 'bottom': 1})
        date_format_title = wb.add_format({'align': 'center','num_format': 'dd/mm/YYYY', 'font_size': 15, 'font_name': 'Arial', 'bold': True, 'bottom': 1})
        line_style1 = wb.add_format({'font_name': 'Arial', 'font_size': 13, 'align': 'right'})
        line_style4 = wb.add_format({'font_name': 'Arial', 'font_size': 13, 'align': 'left'})
        line_style2 = wb.add_format({'font_name': 'Arial', 'font_size': 13, 'bg_color':'#BFBFBF', 'bold': True})
        line_style3 = wb.add_format({'font_name': 'Arial', 'font_size': 14,  'bold': True})

        row = 0
        col = 0
        sheet.merge_range('A1:ZZ1', None)
        sheet.set_default_row(28)
        sheet.write(row + 1, col+1, "Today's Balance", title_style)
        # sheet.write(row + 1, col+2, "Holder Column", title_style)
        sheet.write(row + 2, col, "Accounts Receivable", line_style4)
        sheet.write(row + 3, col, "Quotations", line_style4)
        sheet.write(row + 4, col, "Sales Orders", line_style4)
        sheet.write(row + 5, col, "Total A/R and S/O's", line_style2)
        sheet.write(row + 6, col, "Accounts Payable", line_style4)
        sheet.write(row + 7, col, "Requests For Quotation", line_style4)
        sheet.write(row + 8, col, "Open Purchase Orders", line_style4)
        sheet.write(row + 9, col, "Total Payables & PO's", line_style2)
        sheet.write(row + 10, col, "Net Up or Down", line_style3)
        start_date = date.today().replace(day=1) + relativedelta(months=1)
        sheet.write(row + 1, col + 2, date.today(), date_format_title)
        sheet.write(row + 1, col + 3, start_date, date_format_title)
        end_date = datetime.datetime.strptime(data.get('date_duration'), "%Y-%m-%d").date()
        alphabet_lst = []
        alphabet_lst.append(self.colToExcel(3))
        date_col_count = 4
        col_cnt = 0
        period_days = data.get('period_days')
        while start_date <= end_date:
            if period_days == 15:
                alphabet_lst.append(self.colToExcel(date_col_count))
                month_count = calendar.monthrange(start_date.year, start_date.month)
                s_date = start_date.replace(year=start_date.year, month=start_date.month, day=15)
                e_date = start_date.replace(year=start_date.year, month=start_date.month, day=month_count[1])
                sheet.write(row + 1, date_col_count, s_date, date_format_title)
                date_col_count += 1
                alphabet_lst.append(self.colToExcel(date_col_count))
                sheet.write(row + 1, date_col_count, e_date, date_format_title)
                date_col_count += 1
                start_date += timedelta(days=month_count[1])
            else:
                if col_cnt > 0:
                    alphabet_lst.append(self.colToExcel(date_col_count))
                    sheet.write(row + 1, date_col_count, start_date, date_format_title)
                    date_col_count += 1
                start_date += timedelta(days=period_days)
                col_cnt += 1
        alphabet_lst.append(self.colToExcel(date_col_count))
        order_list = []
        purchase_order_list = []
        quote_list = []
        for k in range(12, len(alphabet_lst)+12):
            order_list.append(self.num_to_col_letters(k))
        for j in range(15, len(alphabet_lst)+15):
            purchase_order_list.append(self.num_to_col_letters(j))
        for quote in range(9,len(alphabet_lst)+9):
            quote_list.append(self.num_to_col_letters(quote))
        if order_list:
            for rec in range(len(order_list)):
                amount_receivable = "{='Accounts Receivable'!%s" % order_list[rec] + str(1) + "}"
                amount_quotations = "{='Quotations'!%s" % quote_list[rec] + str(1) + "}"
                amount_sale_order = "{='Sales Orders'!%s" % order_list[rec] + str(1) + "}"
                amount_payable = "{='Accounts Payables'!%s" % order_list[rec] + str(1) + "}"
                amount_rfqs = "{='Request For Quotation'!%s" % purchase_order_list[rec] + str(1) + "}"
                amount_purchase_order = "{='Open Purchase Orders'!%s" % purchase_order_list[rec] + str(1) + "}"
                amount_receivable_sale_order = "{=SUM(" + alphabet_lst[rec] + str(3) + ":" + alphabet_lst[rec] + str(4) + ":" + alphabet_lst[rec] + str(5) +"}"
                amount_payable_purchase_order = "{=SUM(" + alphabet_lst[rec] + str(7) + ":" + alphabet_lst[rec] + str(8) + ":" + alphabet_lst[rec] + str(9) + "}"
                total_net_amount_formula = '{=' + alphabet_lst[rec] + str(6) + '-' + alphabet_lst[rec] + str(10) + "}"
                sheet.write_formula(2, rec+2, amount_receivable, line_style1)
                sheet.write_formula(3, rec + 2, amount_quotations, line_style1)
                sheet.write_formula(4, rec+2, amount_sale_order, line_style1)
                sheet.write_formula(5, rec+2, amount_receivable_sale_order, line_style2)
                sheet.write_formula(6, rec+2, amount_payable, line_style1)
                sheet.write_formula(7, rec + 2, amount_rfqs, line_style1)
                sheet.write_formula(8, rec+2, amount_purchase_order, line_style1)
                sheet.write_formula(9, rec+2, amount_payable_purchase_order, line_style2)
                sheet.write_formula(10, rec+2, total_net_amount_formula, line_style3)

        sheet.set_column('A:A', 27)
        sheet.set_column('B:B', 16)
        sheet.set_column(2, date_col_count, 15)
        sheet.write_formula('B3', "{='Accounts Receivable'!J1}", line_style1)
        sheet.write_formula('B4', "{='Quotations'!G1}", line_style1)
        sheet.write_formula('B5', "{='Sales Orders'!J1}", line_style1)
        sheet.write_formula('B6', "{=SUM(B3:B4:B5)}", line_style2)
        sheet.write_formula('B7', "{='Accounts Payables'!J1}", line_style1)
        sheet.write_formula('B8', "{='Request For Quotation'!N1}", line_style1)
        sheet.write_formula('B9', "{='Open Purchase Orders'!N1}", line_style1)
        sheet.write_formula('B10', "{=SUM(B7:B8:B9)}", line_style2)
        sheet.write_formula('B11', "{=B6-B10}", line_style1)



