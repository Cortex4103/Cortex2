odoo.define('cortex_na.FormView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var config = require('web.config');
var Context = require('web.Context');
var core = require('web.core');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');
var FormView = require('web.FormView')

var _lt = core._lt;

FormView.include({
        _setSubViewLimit: function (attrs) {
        var view = attrs.views && attrs.views[attrs.mode];
        var limit = view && view.arch.attrs.limit && parseInt(view.arch.attrs.limit, 10);
        attrs.limit = limit || attrs.Widget.prototype.limit || 5000;
    },
    });
    return FormView;
});
