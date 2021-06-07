odoo.define('cortex_na.time', function (require) {
"use strict";

var time = require('web.time');
var translation = require('web.translation');
var utils = require('web.utils');

var lpad = utils.lpad;
var rpad = utils.rpad;
var _t = translation._t;


function getLangDatetimeFormat() {
        return this.strftime_to_moment_format(_t.database.parameters.date_format);
}

time.getLangDatetimeFormat= getLangDatetimeFormat;


});