# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, tools,_
import collections, functools, operator
import datetime
from dateutil import relativedelta
from collections import defaultdict
from math import copysign
from odoo.addons.web.controllers.main import clean_action


class ConsumptionForecastReport(models.AbstractModel):
    _name = "consumption.forecast.report"
    _description = "General Ledger Report"
    _inherit = "account.report"

    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_all_entries = False
    filter_journals = True
    filter_analytic = True
    filter_unfold_all = False
    order_selected_column = {'default': 0}

    @api.model
    def _get_templates(self):
        templates = super(ConsumptionForecastReport, self)._get_templates()
        templates['main_template'] = 'cortex_na.main_template_consumption_forecast'
        templates['main_table_header_template'] = 'cortex_na.main_table_header_consumption_forecast'
        templates['line_template'] = 'cortex_na.line_template_cortex'
        templates['footnotes_template'] = 'cortex_na.footnotes_template_cortex'
        templates['search_template'] = 'cortex_na.search_template_cortex'
        return templates

    @api.model
    def _get_columns_name(self, options):
        # extend_month is how many months for show consumption forecast from now
        extend_month = 6
        list_header = []
        for i in range(0, extend_month):
            nextmonth = datetime.date.today() + relativedelta.relativedelta(months=i)
            month = datetime.date.strftime(nextmonth, "%b %Y")
            list_header.append({'name': _(month), 'class': 'number'})

        # please make sure that rows and column are same in header and data counting with colspan
        # if not match it will affect on sorting of data
        main_header = [
            {'style': "padding: 0;"},
            {'name': 'Product', 'class': 'sortable'},
            # {'name': _(''), 'class': 'date'},
            # {'name': _(''), 'class': 'number'},
            # {'name': _(''), 'class': 'number'},
            {'name': _('Sales Price'), 'class': 'number'},
            {'name': _('AVG. cost'), 'class': 'number'},
            # {'name': _(''), 'class': 'number'},
            # {'name': _(''), 'class': 'number'},
            {'name': _('Installed Quantity'), 'class': 'number sortable'},
            {'name': _('Monthly Consumption'), 'class': 'number sortable'}
        ]
        header = main_header + list_header
        return header

    @api.model
    def _get_filter_journals(self):
        return self.env['account.journal']

    @api.model
    def _get_filter_journal_groups(self):
        journals = self._get_filter_journals()
        groups = self.env['account.journal.group'].search([], order='sequence')
        ret = self.env['account.journal.group']
        for journal_group in groups:
            # Only display the group if it doesn't exclude every journal
            if journals - journal_group.excluded_journal_ids:
                ret += journal_group
        return ret

    @api.model
    def _init_filter_journals(self, options, previous_options=None):
        if self.filter_journals is None:
            return

        previous_company = False
        if previous_options and previous_options.get('journals'):
            journal_map = dict((opt['id'], opt['selected']) for opt in previous_options['journals'] if
                               opt['id'] != 'divider' and 'selected' in opt)
        else:
            journal_map = {}
        options['journals'] = []

        group_header_displayed = False
        default_group_ids = []
        for group in self._get_filter_journal_groups():
            journal_ids = (self._get_filter_journals() - group.excluded_journal_ids).ids
            if len(journal_ids):
                if not group_header_displayed:
                    group_header_displayed = True
                    options['journals'].append({'id': 'divider', 'name': _('Journal Groups')})
                    default_group_ids = journal_ids
                options['journals'].append({'id': 'group', 'name': group.name, 'ids': journal_ids})
        self._cr.execute("""SELECT categ.name FROM installed_part_detail i LEFT JOIN product_product p ON (p.id=i.product_id)
         LEFT JOIN product_template pt ON (pt.id=p.product_tmpl_id)
         LEFT JOIN product_category categ ON (categ.id=pt.categ_id) ORDER BY categ.name""", )
        result = self._cr.fetchall()
        product_categories = list(set([categ[0] for categ in result]))
        product_categories.sort()
        i = 1
        for j in product_categories:
            options['journals'].append({
                'id': i,
                'name': j,
                'code': j,
                'type' : 'journals',
                'selected': journal_map.get(i, i in default_group_ids),
            })
            i += 1

    @api.model
    def _get_lines(self, options, line_id=None):
        offset = int(options.get('lines_offset', 0))
        remaining = int(options.get('lines_remaining', 0))
        balance_progress = float(options.get('lines_progress', 0))

        if offset > 0:
            # Case a line is expanded using the load more.

            return self._load_more_lines(options, line_id, offset, remaining, balance_progress)
        else:
            self.do_query(options)
            # Case the whole report is loaded or a line is expanded for the first time.
            return self._get_general_ledger_lines(options, line_id)

    @api.model
    def do_query(self, options):
        # extend_month is how many months for show consumption forecast from now
        extend_month = 6
        domain = []
        id_list = []
        for val in options.get('journals'):
            if val.get('selected') == True:
                id_list.append(val.get('name'))
            # elif val.get('selected') == True and val.get('id') == 1:
            #     id_list.append(val.get('name'))
            # elif val.get('selected') == True and val.get('id') == 3:
            #     id_list.append(val.get('name'))
            # elif val.get('selected') == True and val.get('id') == 4:
            #     id_list.append(val.get('name'))
        if id_list:
            if 'Cortex V2 Knives' in id_list:
                id_list[id_list.index('Cortex V2 Knives')] = 'V_2_Cortex Knives'
            if 'Without Bridge Knives' in id_list:
                if 'Bridge Knives' not in id_list:
                    categ_id = self.env['product.category'].search([('name', '=', 'Bridge Knives')])
                    product = self.env['product.product'].search([('categ_id', '!=', categ_id.id)])
                    domain = product.ids
                elif 'Bridge Knives' in id_list:
                    product = self.env['product.product'].search([])
                    domain = product.ids
                else:
                    product = self.env['product.product'].search([])
                    domain = product.ids
            else:
                categ_id = self.env['product.category'].search([('name', 'in', id_list)])
                product = self.env['product.product'].search([('categ_id','in',categ_id.ids)])
                domain = product.ids
            # if 1 in id_list and 2 not in id_list:
            #     categ_id = self.env['product.category'].search([('name','=','Bridge Knives')])
            #     product = self.env['product.product'].search([('categ_id','in',categ_id.ids)])
            #     domain = product.ids
            # elif 2 in id_list and 1 not in id_list:
            #     categ_id = self.env['product.category'].search([('name', '!=', 'Bridge Knives')])
            #     product = self.env['product.product'].search([('categ_id', 'in', categ_id.ids)])
            #     domain = product.ids
            # elif 3 in id_list and 1 not in id_list and 2 not in id_list:
            #     categ_id = self.env['product.category'].search([('name', '=', 'Cortex Parts')])
            #     product = self.env['product.product'].search([('categ_id', 'in', categ_id.ids)])
            #     domain = product.ids
            # else:
            #     product = self.env['product.product'].search([])
            #     domain = product.ids

        else:
            product = self.env['product.product'].search([])
            domain = product.ids

        if len(domain) <= 1:
            product_domain = "ipd.product_id = %s" % (domain[0] if domain else 'null')
        else:
            product_domain = "ipd.product_id IN %s" % (tuple(domain),)

        query = """
            SELECT 
                   ipd.product_id as product_id,
                   ipd.date as date,
                   
                   sum(CASE WHEN ipd.installed = 'true' THEN ipd.installed_knife ELSE 0 END) as installed_knife,
                   sum(CASE WHEN ipd.installed = 'true' THEN ipd.estimated_monthly_consumption  ELSE 0 END) as estimated_monthly_consumption,
                   sum(CASE WHEN ipd.installed = 'false' THEN ipd.estimated_monthly_consumption  ELSE 0 END) as monthly_consumption_qty,
                  
                   ipd.installed as installed,
                   ipd.frequency as frequency FROM installed_part_detail ipd
                JOIN installed_part ip ON (ip.id = ipd.install_part_id)
                
                WHERE %s GROUP BY ipd.product_id,ipd.date, ipd.installed, ipd.estimated_monthly_consumption, ipd.installed_knife, ipd.frequency
                ORDER BY ipd.date
                          """ % (product_domain,)
        self._cr.execute(query)
        res = self._cr.fetchall()
        data_dict = {}
        product_obj_dict = {}
        for product, date, int_qty, estimated_qty, monthly_qty, installed, frequency in res:
            if not product_obj_dict.get(product):
                product_obj_dict[product] = self.env['product.product'].browse(product)
            product = product_obj_dict.get(product)
            if data_dict.get(product) != None:
                if installed:
                    data_dict[product]['int_qty'] += int_qty
                    print(data_dict, estimated_qty)
                    data_dict[product]['estimated_qty'] += estimated_qty if estimated_qty and frequency == 'monthly' else 0
            else:
                if installed:
                    data_dict[product] = {'int_qty': int_qty if int_qty else 0, 'estimated_qty' : estimated_qty if estimated_qty and frequency == 'monthly' else 0}
                else:
                    data_dict[product] = {'int_qty': 0, 'estimated_qty': estimated_qty if estimated_qty and frequency == 'monthly' else 0}
        product_dict = {}
        for product, date, int_qty, estimated_qty, monthly_qty, installed, frequency in res:
            product_obj = product_obj_dict.get(product)
            if installed == False and frequency == 'monthly':
                for i in range(0, extend_month):
                    nextmonth = datetime.date.today() + relativedelta.relativedelta(months=i)
                    month = datetime.date.strftime(nextmonth, "%b %Y")

                    month1 = datetime.date.strftime(date, "%b %Y")
                    if month1 == month:
                        product_dict[product] = (product_dict.get(product) or 0) + monthly_qty if monthly_qty else 0
                        data_dict[product_obj][month] = product_dict.get(product)
                    elif nextmonth.year > date.year or (nextmonth.month >= date.month and nextmonth.year >= date.year):
                        data_dict[product_obj][month] = product_dict.get(product) or 0
                    else:
                        pass

        for product, date, int_qty, estimated_qty, monthly_qty, installed, frequency in res:
            product_obj = product_obj_dict.get(product)
            if frequency != 'monthly' and date:
                for i in range(0, extend_month):
                    nextmonth = datetime.date.today() + relativedelta.relativedelta(months=i)
                    month = datetime.date.strftime(nextmonth, "%b %Y")

                    if frequency == 'yearly':
                        if nextmonth.month == date.month:
                            data_dict[product_obj][month] = (monthly_qty or 0) + (estimated_qty or 0) + (data_dict[product_obj].get(month) or 0)
                    else:
                        if nextmonth.month == date.month and (nextmonth.year - date.year) % 2 == 0:
                            data_dict[product_obj][month] = (monthly_qty or 0) + (estimated_qty or 0) + (data_dict[product_obj].get(month) or 0)

        total_list = []
        for keys, values in data_dict.items():
            total_list.append(values)
        if total_list:
            result = dict(functools.reduce(operator.add, map(collections.Counter, total_list)))
            data_dict.update({'Total' : result})
        total_length = []
        data_values = {'int_qty' : 0, 'estimated_qty' : 0}
        for keys, values in data_dict.items():

            if keys not in ['Total']:
                data_values['int_qty'] += values['int_qty'] * keys.length
                data_values['estimated_qty'] += values['estimated_qty'] * keys.length
                total_length.append(data_values)
                for i in range(0, extend_month):
                    nextmonth = datetime.date.today() + relativedelta.relativedelta(months=i)
                    month = datetime.date.strftime(nextmonth, "%b %Y")

                    if values.get(month):
                        if data_values.get(month) != None:
                            data_values[month] += values.get(month) * keys.length
                        else:
                            data_values[month] = values.get(month) * keys.length

        if data_dict:
            data_dict.update({'Cortex Inches Consumed': data_values})
        data_values = {'int_qty': 0, 'estimated_qty': 0}
        for keys, values in data_dict.items():

            if keys not in ['Total', 'Cortex Inches Consumed']:

                data_values['int_qty'] += values['int_qty'] * keys.list_price

                data_values['estimated_qty'] += values['estimated_qty'] * keys.list_price
                for i in range(0, extend_month):
                    nextmonth = datetime.date.today() + relativedelta.relativedelta(months=i)
                    month = datetime.date.strftime(nextmonth, "%b %Y")

                    if values.get(month):
                        if data_values.get(month) != None:
                            data_values[month] += values.get(month) * keys.list_price
                        else:
                            data_values[month] = values.get(month) * keys.list_price
        if data_dict:
            data_dict.update({'Cortex Knife Sales': data_values})
        data_values = {'int_qty': 0, 'estimated_qty': 0}
        for keys, values in data_dict.items():

            if keys not in ['Total', 'Cortex Inches Consumed','Cortex Knife Sales']:

                data_values['int_qty'] += values['int_qty'] * keys.running_avg_cost

                data_values['estimated_qty'] += values['estimated_qty'] * keys.running_avg_cost
                for i in range(0, extend_month):
                    nextmonth = datetime.date.today() + relativedelta.relativedelta(months=i)
                    month = datetime.date.strftime(nextmonth, "%b %Y")

                    if values.get(month):
                        if data_values.get(month) != None:
                            data_values[month] += values.get(month) * keys.running_avg_cost
                        else:
                            data_values[month] = values.get(month) * keys.running_avg_cost
        if data_dict:
            data_dict.update({'Knife Costs': data_values})
        return data_dict

    @api.model
    def _get_general_ledger_lines(self, options, line_id=None):
        result = self.do_query(options)
        lines = []
        for keys, val in result.items():
            lines.append(self._get_account_title_line(keys,  (val.get('int_qty') or 0), (val.get('estimated_qty') or 0), val))

        return lines

    @api.model
    def _get_account_title_line(self, product,  int_qty, monthly_qty, balance):
        # extend_month is how many months for show consumption forecast from now
        extend_month = 6
        main_list = [
                # {'name': '', 'class': 'date'},
                # {'name': '', 'class': 'number'},
                # {'name': '', 'class': 'number'},
                {'name': "{:.2f}".format(round(product.list_price, 2)) if product not in ['Total', 'Cortex Inches Consumed','Cortex Knife Sales','Knife Costs'] else '', 'no_format': product.list_price if product not in ['Total', 'Cortex Inches Consumed','Cortex Knife Sales','Knife Costs'] else str(0), 'class': 'number'},
                {'name': "{:.2f}".format(round(product.running_avg_cost, 2)) if product not in ['Total', 'Cortex Inches Consumed', 'Cortex Knife Sales','Knife Costs' ] else '', 'class': 'number'},
                # {'name': '', 'class': 'number'},
                # {'name': '', 'class': 'number'},
                {'name': str(round(int_qty)) if product not in ['Cortex Inches Consumed', 'Cortex Knife Sales', 'Knife Costs'] else "{:.2f}".format(int_qty), 'no_format': int_qty,'class': 'number'},
                {'name': str(round(monthly_qty)) if product not in ['Cortex Inches Consumed', 'Cortex Knife Sales', 'Knife Costs'] else "{:.2f}".format(monthly_qty),'no_format': monthly_qty, 'class': 'number'},
            ]
        for i in range(0, extend_month):
            nextmonth = datetime.date.today() + relativedelta.relativedelta(months=i)
            month = datetime.date.strftime(nextmonth, "%b %Y")
            main_list.append({'name': "{:.2f}".format(round(balance.get(month, 0) + monthly_qty)) if product in ['Cortex Inches Consumed', 'Cortex Knife Sales', 'Knife Costs'] else str(balance.get(month, 0) + monthly_qty) if monthly_qty else str(balance.get(month, 0)), 'class': 'number'})
        add_class = ""
        if product in ['Total', 'Cortex Inches Consumed','Cortex Knife Sales', 'Knife Costs']:
            name = product
            add_class = "total"
        else:
            name = product.display_name
        main_list.insert(0, {'name': name, 'class': 'string', 'no_format':name})
        return {
            'id': 'account_%d' % ( 300 if product in ['Total', 'Cortex Inches Consumed','Cortex Knife Sales','Knife Costs'] else product.id),
            # 'name': name,
            'name': "",
            'title_hover': name,
            'columns': main_list,
            'level': 2,
            'unfoldable': True,
            'unfolded': None,
            # 'colspan': 4,
            'class': add_class
        }

    @api.model
    def _get_report_name(self):
        return _("Consumption Forecast")

    @api.model
    def _sort_lines(self, lines, options):
        def merge_tree(line):
            sorted_list.append(line)
            for l in sorted(tree[line['id']], key=lambda k: selected_sign * k['columns'][selected_column - k.get('colspan', 1)]['no_format']):
                merge_tree(l)
        
        def get_sorted_data(lines):
            main_data = [data for data in lines if 'total' not in data.get('class', '')]
            total_data = [data for data in lines if 'total' in data.get('class', '')]
            main_data = sorted(main_data, key=lambda k: (k['columns'][selected_column - k.get('colspan', 1)]['no_format']), reverse=is_reverse)
            sorted_lines = main_data + total_data
            return sorted_lines

        sorted_list = []
        selected_column = abs(options['selected_column']) - 1
        selected_sign = -copysign(1, options['selected_column'])
        is_reverse = False if selected_sign > 0 else True
        tree = defaultdict(list)
        if 'sortable' not in self._get_columns_name(options)[selected_column].get('class', ''):
            return lines  # Nothing to do here
        for line in lines:
            tree[line.get('parent_id')].append(line)
        
        for line in get_sorted_data(tree[None]):
            merge_tree(line)
        return sorted_list


    def open_install_part(self, options, params=None):
        if not params:
            params = {}
        id_split = params.get('id').split('account_')
        action = self.env.ref('cortex_na.installed_part_detail_action').read()[0]
        action = clean_action(action)
        action['domain'] = [('product_id', '=', int(id_split[1]))]
        return action



