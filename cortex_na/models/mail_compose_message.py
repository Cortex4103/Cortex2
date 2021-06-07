# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools , _
from odoo.tools import email_re
import base64
from odoo.exceptions import UserError, Warning
import logging

_logger = logging.getLogger(__name__)


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    attach_drawing = fields.Boolean('Attach Drawing',default=False)

    @api.onchange('attach_drawing')
    def onchange_attch_drawing(self):
        if self.attach_drawing:
            if self.env.context.get('active_id'):
                current_po = self.env['purchase.order'].search([('id','=',self.env.context.get('active_id'))])
                if current_po.order_line:
                    lst_of_attachment = []
                    for product in current_po.order_line.mapped('product_id'):
                        product_tmpl_id = product.product_tmpl_id
                        for attachment in product_tmpl_id.list_of_attachment:
                            lst_of_attachment.append([4, attachment.attachment_id.id])
                        
                        if product.drawing_pdf:
                            attachment = self.env['ir.attachment'].sudo().search([('res_model','=', 'product.template'),('res_id', '=', str(product_tmpl_id.id)),('res_field','=', 'drawing_pdf')])
                            if attachment:
                                attachment.name = product.file_name
                                lst_of_attachment.append([4, attachment.id])
                    
                    if lst_of_attachment:
                        self.write({'attachment_ids' : lst_of_attachment})
                    else:
                        raise Warning(_("No any attachment exist in the PO products."))

                

