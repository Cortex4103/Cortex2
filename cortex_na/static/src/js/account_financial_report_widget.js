odoo.define('cortex_na.account_financial_report_widget', function
    (require) {
    'use strict';

    var Widget = require('web.Widget');
    var ActionManager = require('web.ActionManager');


    var accountFinancialReportWidget = Widget.extend({
        events: {
            'click .sort_date':
                'sort_date_click',
            'click .quotations_click_toggle':
                'quotations_click_toggle_link',
            'click .quotations_click':
                'quotations_click_link',
            'click .rfqs_click':
                'rfqs_click_link',
            'click .purchase_order_click':
                'purchase_order_click_link',
            'click .acc_pay_click':
                'acc_pay_click_link',
            'click .sale_order_click':
                'sale_order_click_link',
            'click .rec_click':
                'rec_click_link',
            'click .o_account_financial_reports_web_action':
                'boundLink',
            'click .o_account_financial_reports_web_action_multi':
                'boundLinkmulti',
            'click .o_account_financial_reports_web_action_monetary':
                'boundLinkMonetary',
            'click .o_account_financial_reports_web_action_monetary_multi':
                'boundLinkMonetarymulti',
        },
        init: function (parent, action) {
            this.actionManager = parent;
            this.given_context = {};
            this.odoo_context = parent.odoo_context;
            this._super.apply(this, arguments);
            this.eventListeners = [];
        },
        start: function () {
            return this._super.apply(this, arguments);
        },

        sort_date_click: function (e) {
            $('#open_receivables_id').DataTable({
                retrieve: true,
                paging: false
            });
            $('#open_payables_id').DataTable({
                retrieve: true,
                paging: false
            });
            $('#balance_so_id').DataTable({
                retrieve: true,
                paging: false
            });
            $('#balance_po_id').DataTable({
                retrieve: true,
                paging: false
            });
            $('#balance_quotations_id').DataTable({
                retrieve: true,
                paging: false
            });
            $('#balance_rfqs_id').DataTable({
                retrieve: true,
                paging: false
            });
            $('.dataTables_length').addClass('hide_table');
            $('.dataTables_filter').addClass('hide_table');
            $('.dataTables_info').addClass('hide_table');
            $('.dataTables_paginate.paging_simple_numbers').addClass('hide_table');
        },

        quotations_click_toggle_link: function (e) {
            if (($('.quote_main.hide_table').length) || ($('.rfq_main.hide_table').length)) {
                $('.quote_main').removeClass('hide_table')
                $('.rfq_main').removeClass('hide_table')
                $('.with_out_quote_main').addClass('hide_table')
                $('.no_table').addClass('hide_table')
                $('.show_title').addClass('hide_table')
                $('.hide_title').removeClass('hide_table')
            } else {
                $('.quote_main').addClass('hide_table')
                $('.rfq_main').addClass('hide_table')
                $('.with_out_quote_main').removeClass('hide_table')
                $('.no_table').addClass('hide_table')
                $('.show_title').removeClass('hide_table')
                $('.hide_title').addClass('hide_table')
            }
        },

        quotations_click_link: function (e) {
            this.resizeColumnWidth('quotations_click');
            if (($('.balance_quotations_lines.hide_table').length) && ($('.balance_quotations_total_amounts.hide_table').length)) {
                $('.balance_quotations_lines').removeClass('hide_table')
                $('.balance_quotations_total_amounts').removeClass('hide_table')

            } else {
                $('.balance_quotations_lines').addClass('hide_table')
                $('.balance_quotations_total_amounts').addClass('hide_table')

            }
        },

        rfqs_click_link: function (e) {
            this.resizeColumnWidth('rfqs_click');
            if (($('.balance_rfqs_lines.hide_table').length) && ($('.balance_rfqs_lines_total_amounts.hide_table').length)) {
                $('.balance_rfqs_lines').removeClass('hide_table')
                $('.balance_rfqs_lines_total_amounts').removeClass('hide_table')

            } else {
                $('.balance_rfqs_lines').addClass('hide_table')
                $('.balance_rfqs_lines_total_amounts').addClass('hide_table')

            }
        },

        purchase_order_click_link: function (e) {
            this.resizeColumnWidth('purchase_order');
            if (($('.balance_po_lines.hide_table').length) && ($('.balance_po_lines_total_amounts.hide_table').length)) {
                $('.balance_po_lines').removeClass('hide_table')
                $('.balance_po_lines_total_amounts').removeClass('hide_table')

            } else {
                $('.balance_po_lines').addClass('hide_table')
                $('.balance_po_lines_total_amounts').addClass('hide_table')

            }
        },

        acc_pay_click_link: function (e) {
            this.resizeColumnWidth('acc_pay');
            if (($('.balance_open_payables_lines.hide_table').length) && ($('.balance_opp_lines_total_amounts.hide_table').length)) {
                $('.balance_open_payables_lines').removeClass('hide_table')
                $('.balance_opp_lines_total_amounts').removeClass('hide_table')

            } else {
                $('.balance_open_payables_lines').addClass('hide_table')
                $('.balance_opp_lines_total_amounts').addClass('hide_table')

            }
        },

        sale_order_click_link: function (e) {
            this.resizeColumnWidth('sale_order');
            if (($('.balance_so_lines.hide_table').length) && ($('.balance_so_lines_total_amounts.hide_table').length)) {
                $('.balance_so_lines').removeClass('hide_table')
                $('.balance_so_lines_total_amounts').removeClass('hide_table')

            } else {
                $('.balance_so_lines').addClass('hide_table')
                $('.balance_so_lines_total_amounts').addClass('hide_table')

            }
        },

        rec_click_link: function (e) {
            this.resizeColumnWidth('rec_click')
            if (($('.balance_open_receivables_lines.hide_table').length) && ($('.balance_opr_lines_total_amounts.hide_table').length)) {
                $('.balance_open_receivables_lines').removeClass('hide_table')
                $('.balance_opr_lines_total_amounts').removeClass('hide_table')
                //                var self = this;
                //                return this._rpc({
                //                    model: 'report_cashflow_cortex_na_template',
                //                    method: 'write',
                //                    args: [this.odoo_context.active_id,{ar:'true'}],
                //                    context: this.odoo_context,
                //                })
            } else {
                $('.balance_open_receivables_lines').addClass('hide_table')
                $('.balance_opr_lines_total_amounts').addClass('hide_table')
                //                var self = this;
                //                return this._rpc({
                //                    model: 'report_cashflow_cortex_na_template',
                //                    method: 'excel_elems',
                //                    context: {'ar':'false'},
                //                })
            }
        },

        /**
         * Used to bind event listeners so that they can be unbound when the list
         * is destroyed.
         * There is no reverse method (list._removeEventListener) because there is
         * no issue with removing an non-existing listener.
         *
         * @private
         * @param {string} type event name
         * @param {EventTarget} el event target
         * @param {Function} callback callback function to attach
         * @param {Object} options event listener options
        */
        _addEventListener: function (type, el, callback, options) {
            el.addEventListener(type, callback, options);
            this.eventListeners.push({ type, el, callback, options });
        },
        resizeColumnWidth: function (e) {
            console.log('valuess', e)
            let th;
            if (e == 'rec_click') {
                th = $('#open_receivables_id thead tr th');
            } else if (e == 'sale_order') {
                th = $('#balance_so_id thead tr th');
            }
            else if (e == 'quotations_click') {
                th = $('#balance_quotations_id thead tr th');
            }
            else if (e == 'rfqs_click') {
                th = $('#balance_rfqs_id thead tr th');
            }
            else if (e == 'acc_pay') {
                th = $('#open_payables_id thead tr th');
            }
            else if (e == 'purchase_order') {
                th = $('#balance_po_id thead tr th');
            }
            console.log('thhh', th)
            for (let i = 0; i < th.length; i++) {
                let $th = $(th[i])
                const resizeHandle = document.createElement('span');
                resizeHandle.classList = 'o_resize';
                resizeHandle.onclick = this._onClickResize.bind(this);
                resizeHandle.onmousedown = this._onStartResize.bind(this);
                console.log('resizeHandle', resizeHandle)
                $th.append(resizeHandle);
            }
        },
        /**
         * We want to override any default mouse behaviour when clicking on the resize handles
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickResize: function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
        },

        /**
         * Handles the resize feature on the column headers
         *
         * @private
         * @param {MouseEvent} ev
        */
        _onStartResize: function (ev) {
            // Only triggered by left mouse button
            if (ev.which !== 1) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();

            this.isResizing = true;
            console.log(this)
            console.log('el',this.el)
            const th = ev.target.closest('th');
            const $th = $(th);
            const table = $th.closest('table')[0];
            console.log(table)
            console.log('clo thhh',th)
            table.style.width = `${table.offsetWidth}px`;
            const thPosition = [...th.parentNode.children].indexOf(th);
            const resizingColumnElements = [...table.getElementsByTagName('tr')]
                .filter(tr => tr.children.length === th.parentNode.children.length)
                .map(tr => tr.children[thPosition]);
            const optionalDropdown = this.el.getElementsByClassName('o_optional_columns')[0];
            const initialX = ev.pageX;
            const initialWidth = th.offsetWidth;
            const initialTableWidth = table.offsetWidth;
            const initialDropdownX = optionalDropdown ? optionalDropdown.offsetLeft : null;
            const resizeStoppingEvents = [
                'keydown',
                'mousedown',
                'mouseup',
            ];

            // Apply classes to table and selected column
            table.classList.add('o_resizing');
            resizingColumnElements.forEach(el => el.classList.add('o_column_resizing'));

            // Mousemove event : resize header
            const resizeHeader = ev => {
                ev.preventDefault();
                ev.stopPropagation();
                const delta = ev.pageX - initialX;
                const newWidth = Math.max(10, initialWidth + delta);
                const tableDelta = newWidth - initialWidth;
                th.style.width = `${newWidth}px`;
                table.style.width = `${initialTableWidth + tableDelta}px`;
                if (optionalDropdown) {
                    optionalDropdown.style.left = `${initialDropdownX + tableDelta}px`;
                }
            };
            this._addEventListener('mousemove', window, resizeHeader);

            // Mouse or keyboard events : stop resize
            const stopResize = ev => {
                // Ignores the initial 'left mouse button down' event in order
                // to not instantly remove the listener
                if (ev.type === 'mousedown' && ev.which === 1) {
                    return;
                }
                ev.preventDefault();
                ev.stopPropagation();
                // We need a small timeout to not trigger a click on column header
                clearTimeout(this.resizeTimeout);
                this.resizeTimeout = setTimeout(() => {
                    this.isResizing = false;
                }, 100);
                window.removeEventListener('mousemove', resizeHeader);
                table.classList.remove('o_resizing');
                resizingColumnElements.forEach(el => el.classList.remove('o_column_resizing'));
                resizeStoppingEvents.forEach(stoppingEvent => {
                    window.removeEventListener(stoppingEvent, stopResize);
                });

                // we remove the focus to make sure that the there is no focus inside
                // the tr.  If that is the case, there is some css to darken the whole
                // thead, and it looks quite weird with the small css hover effect.
                document.activeElement.blur();
            };
            // We have to listen to several events to properly stop the resizing function. Those are:
            // - mousedown (e.g. pressing right click)
            // - mouseup : logical flow of the resizing feature (drag & drop)
            // - keydown : (e.g. pressing 'Alt' + 'Tab' or 'Windows' key)
            resizeStoppingEvents.forEach(stoppingEvent => {
                this._addEventListener(stoppingEvent, window, stopResize);
            });
        },

        boundLink: function (e) {
            var res_model = $(e.target).data('res-model');
            var res_id = $(e.target).data('active-id');
            return this.do_action({
                type: 'ir.actions.act_window',
                res_model: res_model,
                res_id: res_id,
                views: [[false, 'form']],
                target: 'current',
            });
        },
        boundLinkmulti: function (e) {
            var res_model = $(e.target).data('res-model');
            var domain = $(e.target).data('domain');
            if (!res_model) {
                res_model = $(e.target.parentElement).data('res-model');
            }
            if (!domain) {
                domain = $(e.target.parentElement).data('domain');
            }
            return this.do_action({
                type: 'ir.actions.act_window',
                name: this._toTitleCase(res_model.split('.').join(' ')),
                res_model: res_model,
                domain: domain,
                views: [[false, "list"], [false, "form"]],
                target: 'current',
            });
        },
        boundLinkMonetary: function (e) {
            var res_model = $(e.target.parentElement).data('res-model');
            var res_id = $(e.target.parentElement).data('active-id');
            if (!res_model) {
                res_model = $(e.target).data('res-model');
            }
            if (!res_id) {
                res_id = $(e.target).data('active-id');
            }
            if (res_model && res_id) {
                return this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: res_model,
                    res_id: res_id,
                    views: [[false, 'form']],
                    target: 'current',

                });
            }
        },
        boundLinkMonetarymulti: function (e) {
            var res_model = $(e.target.parentElement).data('res-model');
            var domain = $(e.target.parentElement).data('domain');
            return this.do_action({
                type: 'ir.actions.act_window',
                res_model: res_model,
                domain: domain,
                views: [[false, "list"], [false, "form"]],
                target: 'current',
            });
        },
        _toTitleCase: function (str) {
            return str.replace(/\w\S*/g, function (txt) {
                return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
            });
        },
    });
    return accountFinancialReportWidget;

});
