odoo.define('cortex_na.account_financial_report_backend', function (require) {
    'use strict';

    var core = require('web.core');
    var Widget = require('web.Widget');
    var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
    var AbstractAction = require('web.AbstractAction');
    var ActionManager = require('web.ActionManager');
    var framework = require('web.framework');
    var session = require('web.session');
    var _t = core._t;
    var _lt = core._lt;
    var ReportWidget = require(
        'cortex_na.account_financial_report_widget'
        );

    var report_backend = AbstractAction.extend({
    hasControlPanel: true,
        // Stores all the parameters of the action.
        events: {
            'click .o_account_financial_reports_print': 'print',
            'click .o_account_financial_reports_export': 'export',
        },
        init: function (parent, action) {

            this.actionManager = parent;
            this.given_context = {};
            this.odoo_context = action.context;
            this.controller_url = action.context.url;
            if (action.context.context) {
                this.given_context = action.context.context;
            }
            this.given_context.active_id = action.context.active_id ||
                action.params.active_id;
            this.given_context.model = action.context.active_model || false;
            this.given_context.ttype = action.context.ttype || false;
            return this._super.apply (this, arguments);
        },
        willStart: function () {
            return $.when(this.get_html());
        },
        set_html: function () {
            var self = this;
            var def = $.when();
            if (!this.report_widget) {
                this.report_widget = new ReportWidget(this, this.given_context);
                def = this.report_widget.appendTo(this.$el);
            }
            def.then(function () {
                self.report_widget.$el.html(self.html);
            });
        },

        start: function() {
            this.$('.o_content').addClass('custom_class');
            this.set_html();
            return this._super();
        },
        // Fetches the html and is previous report.context if any, else create it
        get_html: function() {
            var self = this;
            var defs = [];
            return this._rpc({
                model: 'report_cashflow_cortex_na_template',
                method: 'get_html',
                args: [self.given_context],
                context: self.odoo_context,

            })
            .then(function (result) {
                self.html = result.html;
                defs.push(self.update_cp());
                return $.when.apply($, defs);
            });
        },
        // Updates the control panel and render the elements that have yet
        // to be rendered
        update_cp: function () {
            if (this.$buttons) {
                var status = {
                    breadcrumbs: this.actionManager.get_breadcrumbs(),
                    cp_content: {$buttons: this.$buttons},
                };
                return this.update_control_panel(status);
            }
        },
        do_show: function () {
            this._super();
            this.update_cp();
        },

        export: function () {
            var self = this;
            console.log(self.odoo_context)
            this._rpc({
                model: 'report_cashflow_cortex_na_template',
                method: 'generate_excel_report',
                context: self.odoo_context,
                args: [this.given_context.active_id],

            })
            .then(function(result){
                self.do_action(result);
            });
        },


    });

    core.action_registry.add(
        'account_financial_report_backend',
        report_backend
        );
    return report_backend;
});
