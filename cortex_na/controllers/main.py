# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo
from odoo import fields, http
from odoo.addons.web.controllers.main import serialize_exception,GroupExportXlsxWriter,ExportXlsxWriter,ExcelExport
from odoo.exceptions import AccessError, UserError, AccessDenied
import datetime
import json
from odoo import http, _, fields
from odoo.http import request
from odoo.tools import image_process, topological_sort, html_escape, pycompat, ustr, apply_inheritance_specs, lazy_property

from odoo import http, tools
from odoo.http import content_disposition, dispatch_rpc, request, serialize_exception as _serialize_exception, Response

class GroupExportXlsxWriterInherit(GroupExportXlsxWriter):

    def _write_group_header(self, row, column, label, group, group_depth=0):
        if self.context_data.get('export_all_sale_and_cost'):
            aggregates = group.aggregated_values
            margin_total = round((aggregates.get('credit') - aggregates.get('debit')) / aggregates.get(
                'credit') if aggregates.get('credit') else 0,2)
            margin_per = margin_total * 100
            aggregates['margin'] = str(round(margin_per)) + '%'

            label = '%s%s (%s)' % ('    ' * group_depth, label, group.count)

            self.write(row, column, label, self.header_bold_style)
            for field in self.fields[1:]:  # No aggregates allowed in the first column because of the group title
                column += 1
                aggregated_value = aggregates.get(field['name'])
                self.write(row, column, str(aggregated_value if aggregated_value is not None else ''),
                           self.header_bold_style)
            return row + 1, 0
        else:
            aggregates = group.aggregated_values
            label = '%s%s (%s)' % ('    ' * group_depth, label, group.count)
            self.write(row, column, label, self.header_bold_style)
            for field in self.fields[1:]:  # No aggregates allowed in the first column because of the group title
                column += 1
                aggregated_value = aggregates.get(field['name'])
                self.write(row, column, str(aggregated_value if aggregated_value is not None else ''),
                           self.header_bold_style)
            return row + 1, 0


    def write_cell(self, row, column, cell_value):
        if self.context_data.get('export_all_sale_and_cost'):
            if column == 9:
                cell_value = ''
            cell_style = self.base_style
            if isinstance(cell_value, bytes):
                try:
                    # because xlsx uses raw export, we can get a bytes object
                    # here. xlsxwriter does not support bytes values in Python 3 ->
                    # assume this is base64 and decode to a string, if this
                    # fails note that you can't export
                    cell_value = pycompat.to_text(cell_value)
                except UnicodeDecodeError:
                    raise UserError(_(
                        "Binary fields can not be exported to Excel unless their content is base64-encoded. That does not seem to be the case for %s.") %
                                    self.field_names[column])

            if isinstance(cell_value, str):
                if len(cell_value) > self.worksheet.xls_strmax:
                    cell_value = _(
                        "The content of this cell is too long for an XLSX file (more than %s characters). Please use the CSV format for this export.") % self.worksheet.xls_strmax
                else:
                    cell_value = cell_value.replace("\r", " ")
            elif isinstance(cell_value, datetime.datetime):
                cell_style = self.datetime_style
            elif isinstance(cell_value, datetime.date):
                cell_style = self.date_style
            self.write(row, column, cell_value, cell_style)
        else:
            cell_style = self.base_style
            if isinstance(cell_value, bytes):
                try:
                    # because xlsx uses raw export, we can get a bytes object
                    # here. xlsxwriter does not support bytes values in Python 3 ->
                    # assume this is base64 and decode to a string, if this
                    # fails note that you can't export
                    cell_value = pycompat.to_text(cell_value)
                except UnicodeDecodeError:
                    raise UserError(_(
                        "Binary fields can not be exported to Excel unless their content is base64-encoded. That does not seem to be the case for %s.") %
                                    self.field_names[column])

            if isinstance(cell_value, str):
                if len(cell_value) > self.worksheet.xls_strmax:
                    cell_value = _(
                        "The content of this cell is too long for an XLSX file (more than %s characters). Please use the CSV format for this export.") % self.worksheet.xls_strmax
                else:
                    cell_value = cell_value.replace("\r", " ")
            elif isinstance(cell_value, datetime.datetime):
                cell_style = self.datetime_style
            elif isinstance(cell_value, datetime.date):
                cell_style = self.date_style
            self.write(row, column, cell_value, cell_style)


GroupExportXlsxWriter._write_group_header = GroupExportXlsxWriterInherit._write_group_header
GroupExportXlsxWriter.write_cell = GroupExportXlsxWriterInherit.write_cell


class ExcelExportInherit(ExcelExport):

    def from_group_data(self, fields, groups):
        if self.context_data.get('export_all_sale_and_cost'):
            with GroupExportXlsxWriter(fields, groups.count) as xlsx_writer:
                x, y = 1, 0
                credit =0
                debit = 0
                group=None
                xlsx_writer.context_data = self.context_data
                for group_name, group in groups.children.items():
                    aggrigate = group.aggregated_values
                    x, y = xlsx_writer.write_group(x, y, group_name, group)
                    credit += aggrigate.get('credit')
                    debit += aggrigate.get('debit')

                if group:
                    margin_total = round((credit - debit) / credit if credit else 0, 2)
                    margin_per = margin_total * 100
                    margin = str(round(margin_per)) + '%'
                    x += 1
                    xlsx_writer.write(x, y, 'Total Margin',xlsx_writer.header_bold_style)
                    for field in fields[1:]:  # No aggregates allowed in the first column because of the group title
                        y += 1
                        aggregated_value = ''
                        if field.get('name') == 'debit':
                            aggregated_value = debit
                        elif field.get('name') == 'credit':
                            aggregated_value = credit
                        elif field.get('name') == 'margin':
                            aggregated_value = margin
                        xlsx_writer.write(x, y, str(aggregated_value if aggregated_value is not None else ''),
                                   xlsx_writer.header_bold_style)
            return xlsx_writer.value
        else:
            with GroupExportXlsxWriter(fields, groups.count) as xlsx_writer:
                x, y = 1, 0
                xlsx_writer.context_data = self.context_data
                for group_name, group in groups.children.items():
                    x, y = xlsx_writer.write_group(x, y, group_name, group)
            return xlsx_writer.value

    @http.route('/web/export/xlsx', type='http', auth="user")
    @serialize_exception
    def index(self, data, token):
        self.context_data = json.loads(data).get('context') or {}
        return self.base(data, token)
#
#
ExcelExport.from_group_data = ExcelExportInherit.from_group_data
ExcelExport.index = ExcelExportInherit.index

