odoo.define('cortex_na.TourManager', function (require) {
"use strict";

var core = require("web.core");
var TourManager = require('web_tour.TourManager');


TourManager.include({
    update: function (tour_name) {
        return;
    }
});
return TourManager;
});
