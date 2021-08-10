# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.translate import _
from odoo.exceptions import Warning


class PythonScript(models.Model):
    _name = "python.script"
    _description = 'Python Script'
    
    name = fields.Char(string='Name',size=1024,required=True)
    code = fields.Text(string='Python Code',required=True)
    result = fields.Text(string='Result',readonly=True)
    active = fields.Boolean(default=True, string="Active")
        
    
    def run_script(self):
        localdict = {'self': self, 'user_obj': self.env.user}
        for obj in self:
            try :
                exec(obj.code, localdict)
                if localdict.get('result', False):
                    self.write({'result': localdict['result']})
                else : 
                    self.write({'result': ''})
            except Exception as e:
                raise Warning('Python script was not able to run ! message : %s' %(e))
                
        return True
