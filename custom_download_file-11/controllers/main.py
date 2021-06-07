from odoo import http
from odoo.http import request


class FileDispatcher(http.Controller):

    @http.route('/custom_download_file/get_file/', type='http', auth='user')
    def handler(self, **kwargs):
        obj = request.env[kwargs.get('model')]
        obj.setup(kwargs.get('record_id'))
        data = kwargs.get('data')
        ctx = {
            'payslip_number':(kwargs.get('context') if kwargs.get('context') else False)
        }
        response = request.make_response(obj.get_content(data), headers=[
            ('Content-Type', 'application/octet-stream;charset=utf-8;'),
            ('Content-Disposition', u'attachment; filename={};'.format(obj.with_context(ctx).get_filename()))
        ], cookies={
            'fileToken': kwargs.get('token'),
        })
        return response

    # def handler(self, **kwargs):
    #     obj = request.env[kwargs.get('model')]
    #     obj.setup(kwargs.get('record_id'))
    #     data = kwargs.get('data')
    #     context = ast.literal_eval(kwargs.get('context'))
    #     ctx = {
    #         'period_days': context.get('period_days')
    #     }
    #     response = request.make_response(obj.with_context(context).get_content(data), headers=[
    #         ('Content-Type', 'application/octet-stream;charset=utf-8;'),
    #         ('Content-Disposition', u'attachment; filename={};'.format(obj.with_context(ctx).get_filename()))
    #     ], cookies={
    #         'fileToken': kwargs.get('token'),
    #     })
    #     return response

