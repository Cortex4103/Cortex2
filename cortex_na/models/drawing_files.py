# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DrawingFiles(models.Model):
    _name = 'drawing.files'
    _description = 'Drawing Files'

    file_type = fields.Selection([('igs', 'IGS'), ('pdf', 'PDF')], string='File Type')
    template_id = fields.Many2one('product.template', string="Template ID")
    attach_datas = fields.Binary(string='Name')
    upload_file_name = fields.Char('File Name')
    attachment_id = fields.Many2one('ir.attachment', string='Filename', compute='compute_attachment_id', store=True)

    @api.depends('attach_datas')
    def compute_attachment_id(self):
        for record in self:
            if record.attach_datas:
                res_model = 'drawing.files'
                res_id = record.id
                attachment = self.env['ir.attachment'].sudo().with_context(no_document=True).create({
                    'name': record.upload_file_name,
                    'datas': record.attach_datas,
                    'res_model': res_model,
                    'res_id': res_id,
                    'type': 'binary'
                })
                record.attachment_id = attachment.id
            else:
                record.attachment_id = False


