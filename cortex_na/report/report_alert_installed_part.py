# -*- coding: utf-8 -*-

from datetime import datetime,timedelta
from odoo import api, fields, models, _


class CronAlertInstalledPartReport(models.AbstractModel):
    _name = 'report.cortex_na.cron_alert_installed_part_report'
    _description = 'Installed Part Stock Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        parts_data = None
        if self._context.get('data'):
            parts_data = self._context.get('data')
        return {
            'doc_ids': docids,
            'doc_model': 'product.template',
            'data': data,
            'parts_data': parts_data
        }
