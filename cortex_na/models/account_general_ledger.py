# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from datetime import datetime, timedelta
from odoo.addons.web.controllers.main import clean_action
from odoo.tools import float_is_zero
import re


class ReportAccountGeneralLedger(models.AbstractModel):
    _inherit = "account.general.ledger"

    def _get_query_amls(self, options, expanded_account, offset=None, limit=None):
        query, where_params = super(ReportAccountGeneralLedger, self)._get_query_amls(options, expanded_account, offset=offset, limit=limit)
        query = re.sub(r"partner.name                            AS partner_name,", "partner.display_name                            AS partner_name,",query)
        return query, where_params