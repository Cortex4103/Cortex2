# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def _get_default_author(self):
        return self.env.user.partner_id

    # is_sale_activity = fields.Boolean
    subject_compute = fields.Char(string='Subject', compute='compute_subject', store=True)
    record_name = fields.Char('Source', help="Name get of the related document.")
    author_id = fields.Many2one(
        'res.partner', 'User', index=True,
        ondelete='set null', default=_get_default_author,
        help="Author of the message. If not set, email_from may hold an email address that did not match any partner.")
    model = fields.Char('Related Record', index=True)
    body_content = fields.Html('Body Contents', default='', sanitize_style=True)
    customer_id = fields.Many2one('res.partner', 'Customer')
    note = fields.Html('Note', default='', sanitize_style=True)

    @api.model
    def create(self, vals_list):
        res = super(MailMessage, self).create(vals_list)
        if (res.model == 'sale.order' or res.model == 'crm.lead' or res.model == 'res.partner') and res.res_id:
            if res.model == 'res.partner':
                res.customer_id = res.res_id
            else:
                res.customer_id = self.env[res.model].browse(res.res_id).partner_id.id
        return res

    @api.depends('subject', 'record_name', 'body', 'body_content')
    def compute_subject(self):
        for record in self:
            value = ''
            if record.subject:
                value = record.subject
            elif record.record_name:
                value = record.record_name
            elif record.body:
                value_list = record.body.split('>', 1)
                value = value_list[1][:-4]
            elif record.body_content:
                value = 'Record Updated'
            record.subject_compute = value

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if self._context.get('activity_dashboard'):
            list_id = []
            partner_record = self.search([('model','=','res.partner')])
            if partner_record:
                res_list = [record.res_id for record in partner_record]
                partner = self.env['res.partner'].search([('id','in',res_list),('customer_rank','>', 0)])
                msg_ids = self.search([('res_id','in',partner.ids),('model','=','res.partner')])
                list_id = msg_ids.ids

            domain += ['|',('id', 'in' ,list_id), ('model', 'in', ['crm.lead', 'sale.order'])]
            return super(MailMessage, self.sudo()).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False,
                       lazy=True, expand=False, expand_limit=None, expand_orderby=False):
        if self._context.get('activity_dashboard'):
            list_id = []
            partner_record = self.search([('model','=','res.partner')])
            if partner_record:
                res_list = [record.res_id for record in partner_record]
                partner = self.env['res.partner'].search([('id','in',res_list),('customer_rank','>', 0)])
                msg_ids = self.search([('res_id','in',partner.ids),('model','=','res.partner')])
                list_id = msg_ids.ids

            domain += ['|',('id', 'in' ,list_id), ('model', 'in', ['crm.lead', 'sale.order'])]
        return super(MailMessage, self).web_read_group(domain=domain, fields=fields, groupby=groupby, limit=limit, offset=offset, orderby=orderby,
                       lazy=lazy, expand=expand, expand_limit=expand_limit, expand_orderby=expand_orderby)

    def open_related_document(self):
        self.ensure_one()
        return {
            'name': _('Sales Orders'),
            'view_mode': 'form',
            'res_model': self.model,
            'type': 'ir.actions.act_window',
            'res_id': self.res_id,
            'context': dict(self._context, create=False)
        }

    def cron_set_body_mail_message(self):
        # update body content in old data
        message_obj = self.search([('body', '=', ''), ('body_content', '=', '')])
        subtype_ids = [value.subtype_id.id for value in message_obj if value.subtype_id]
        subtypes = self.env['mail.message.subtype'].sudo().browse(subtype_ids).read(['internal', 'description', 'id'])
        subtypes_dict = dict((subtype['id'], subtype) for subtype in subtypes)
        for value in message_obj:
            if not value.body and value.tracking_value_ids:
                subtype = ''
                if value.subtype_id and subtypes_dict.get(value.subtype_id.id)['description']:
                    subtype = '<p>' + subtypes_dict.get(value.subtype_id.id)['description'] + '</p>'
                body = '<ul class="o_mail_thread_message_tracking">'
                for tracking in value.tracking_value_ids:
                    old_value = tracking.get_old_display_value()[0]
                    new_value = tracking.get_new_display_value()[0]
                    body += '<li>' + tracking.field_desc + ': <span> ' + \
                            (str(old_value) if old_value else '') + \
                            ((' </span> <span class="fa fa-long-arrow-right" role="img" aria-label="Changed" title="Changed"/> ')
                             if old_value and old_value != new_value else '') + \
                            (('<span>' + str(new_value) + '</span>') if old_value != new_value else '') + '</li>'
                body += '</ul>'
                value.body_content = subtype + body
        # Update note in old data
        message_obj = self.search([('note', '=', '')])
        for value in message_obj:
            value.note = value.body or value.body_content
        # Update Customer in old data
        message_obj = self.search([('model', 'in', ['sale.order', 'crm.lead', 'res.partner']), ('res_id', '!=', False), ('customer_id','=', None)])
        for value in message_obj:
            try:
                if value.model == 'res.partner':
                    value.customer_id = value.res_id
                else:
                    value.customer_id = self.env[value.model].browse(value.res_id).partner_id.id
            except Exception as e:
                _logger.info("Customer not set for model %s of related document id %s" % (value.model, value.res_id))


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_create(self, values_list):
        res = super(MailThread, self)._message_create(values_list)
        subtype_ids = [value.subtype_id.id for value in res if value.subtype_id]
        subtypes = self.env['mail.message.subtype'].sudo().browse(subtype_ids).read(['internal', 'description', 'id'])
        subtypes_dict = dict((subtype['id'], subtype) for subtype in subtypes)
        for value in res:
            if not value.body and value.tracking_value_ids:
                subtype = ''
                if value.subtype_id and subtypes_dict.get(value.subtype_id.id)['description']:
                    subtype = '<p>' + subtypes_dict.get(value.subtype_id.id)['description'] + '</p>'
                body = '<ul class="o_mail_thread_message_tracking">'
                for tracking in value.tracking_value_ids:
                    old_value = tracking.get_old_display_value()[0]
                    new_value = tracking.get_new_display_value()[0]
                    body += '<li>' + tracking.field_desc + ': <span> ' + \
                            (str(old_value) if old_value else '') + \
                            ((' </span> <span class="fa fa-long-arrow-right" role="img" aria-label="Changed" title="Changed"/> ')
                             if old_value and old_value != new_value else '') + \
                            (('<span>' + str(new_value)+ '</span>' ) if old_value != new_value else '') + '</li>'
                body += '</ul>'
                value.body_content = subtype + body
            value.note = value.body or value.body_content
        return res

    def _message_post_process_attachments(self, attachments, attachment_ids, message_values):
        """ Preprocess attachments for mail_thread.message_post() or mail_mail.create().

        :param list attachments: list of attachment tuples in the form ``(name,content)``, #todo xdo update that
                                 where content is NOT base64 encoded
        :param list attachment_ids: a list of attachment ids, not in tomany command form
        :param dict message_data: model: the model of the attachments parent record,
          res_id: the id of the attachments parent record
        """
        return_values = super(MailThread, self)._message_post_process_attachments(attachments, attachment_ids, message_values)
        if self._context.get('active_model') == 'purchase.order':
            # Attach drawing files with PO mail 
            drawing_attachment_ids = []
            if attachment_ids:
                # taking advantage of cache looks better in this case, to check
                filtered_drawing_attachment_ids = self.env['ir.attachment'].sudo().browse(attachment_ids).filtered(lambda a: a.res_model in ['drawing.files', 'product.template'])
                drawing_attachment_ids += [(4, id) for id in filtered_drawing_attachment_ids.ids]

            return_values['attachment_ids'] = return_values.get('attachment_ids', []) + drawing_attachment_ids
        return return_values


class MailTracking(models.Model):
    _inherit = 'mail.tracking.value'

    def get_display_value(self, type):
        assert type in ('new', 'old')
        result = []
        for record in self:
            if record.field_type in ['integer', 'float', 'char', 'text', 'monetary']:
                result.append(getattr(record, '%s_value_%s' % (type, record.field_type)))
            elif record.field_type == 'datetime':
                if record['%s_value_datetime' % type]:
                    new_datetime = getattr(record, '%s_value_datetime' % type)
                    result.append('%sZ' % new_datetime)
                else:
                    result.append(record['%s_value_datetime' % type])
            elif record.field_type == 'date':
                if record['%s_value_datetime' % type]:
                    new_date = record['%s_value_datetime' % type]
                    result.append(fields.Date.to_string(new_date))
                else:
                    result.append(record['%s_value_datetime' % type])
            elif record.field_type == 'boolean':
                result.append(bool(record['%s_value_integer' % type]))
            else:
                result.append(record['%s_value_char' % type])
        if isinstance(result[0],float):
            result[0] = round(result[0],2)
        return result