# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import requests
import uuid
import logging
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GeoCoder(models.AbstractModel):
    _inherit = "base.geocoder"

    @api.model
    def _call_openstreetmap(self, addr, **kw):
        """
        Use Openstreemap Nominatim service to retrieve location
        :return: (latitude, longitude) or None if not found
        """
        if not addr:
            _logger.info('invalid address given')
            return None
        url = 'https://nominatim.openstreetmap.org/search'
        headers = {"User-Agent": 'contextily-' + uuid.uuid4().hex}
        try:
            result = requests.get(url, {'format': 'json', 'q': addr} ,headers=headers).json()
            _logger.info('openstreetmap nominatim service called')
        except Exception as e:
            self._raise_query_error(e)
        geo = result[0]
        return float(geo['lat']), float(geo['lon'])
