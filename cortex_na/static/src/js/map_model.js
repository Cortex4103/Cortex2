odoo.define('cortex_na.MapModel', function (require) {
    'use strict';

    var AbstractModel = require('web.AbstractModel');
    var session = require('web.session');
    var core = require('web.core');
    var _t = core._t;
    var MapModel = require('web_map.MapModel');

    MapModel.include({
        load: function (params) {
            this._super.apply(this, arguments);
            this.data.limit = 500;
            return this._fetchData();
        },
    });
    return MapModel;
});
