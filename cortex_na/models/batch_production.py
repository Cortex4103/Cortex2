# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning


class BatchProduction(models.Model):
    """ Batch Production"""
    _name = 'batch.production'
    _description = 'Batch Production'
    _rec_name = 'batch_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    batch_number = fields.Char(string='Batch No', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.company.currency_id)
    grade = fields.Char(string='Grade', tracking=True)
    size = fields.Char(string='Size (mm)', tracking=True)
    per_inch = fields.Float(string='Profile Weight/Inch (G)', default=30, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', tracking=True)
    total_weight = fields.Float(string='Total Weight', tracking=True)
    batch_detail_ids = fields.One2many('batch.production.detail', 'batch_production_id', 'Batch Detail', copy=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('cancel', 'Cancel')], string='Status', default='draft', tracking=True)
    total_kg = fields.Float(string='Total (KG)', compute='compute_total_kg', tracking=True)
    weight_loss = fields.Float(string='Weight Loss', compute='compute_weight_loss', tracking=True)
    service_charge_ids = fields.One2many('service.charge', 'batch_production_id', 'Service Charges', copy=True)
    service_charge_total = fields.Float(string='Service Charges Total', compute='compute_service_charges_total')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', copy=False)
    total_knife_inches = fields.Float(string='Total knife inches', compute='compute_total_knife_inches')
    profile_cost = fields.Float(string='Profile Cost (Total)')
    service_cost = fields.Float(string='Service Cost (Unit)')
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type', domain="[('code', '=', 'mrp_operation')]")
    mrp_type = fields.Selection([('production', 'Production'), ('conversion', 'Conversion')], string='Manufacturing Type', default='production', tracking=True)
    isTransfer = fields.Boolean(string='Transfer',default='False')
    distribution_type = fields.Selection([('common', 'Common Service'), ('specific', 'Specific Service')], string='Service Distribution')
    distribution_service_ids = fields.One2many('distribution.service', 'batch_production_id', 'Distribution Service', copy=True)
    distribution_service_total = fields.Float(string='Distribution Service Charges Total', compute='compute_distribution_service_total')

    @api.onchange('mrp_type')
    def _onchange_mrp_type(self):
        if self.mrp_type:
            if self.mrp_type == 'conversion':
                self.per_inch, self.total_weight, self.profile_cost, self.service_cost = 0, 0, 0, 0
            elif self.mrp_type == 'production':
                self.per_inch = 30

    @api.depends('batch_detail_ids','batch_detail_ids.qty_kg')
    def compute_total_kg(self):
        for record in self:
            weight = 0
            if record.batch_detail_ids:
                weight = [line.qty_kg for line in record.batch_detail_ids]
                if weight:
                    weight = sum(weight)
                else:
                    weight = 0
            record.total_kg = weight

    @api.depends('total_weight', 'total_kg')
    def compute_weight_loss(self):
        for record in self:
            record.weight_loss = record.total_weight - record.total_kg

    @api.depends('service_charge_ids','service_charge_ids.subtotal')
    def compute_service_charges_total(self):
        for record in self:
            total = 0
            for line in record.service_charge_ids:
                total += line.subtotal
            record.service_charge_total = total

    @api.depends('distribution_service_ids','distribution_service_ids.subtotal')
    def compute_distribution_service_total(self):
        for record in self:
            total = 0
            for line in record.distribution_service_ids:
                total += line.subtotal
            record.distribution_service_total = total

    @api.depends('batch_detail_ids', 'batch_detail_ids.quantity', 'batch_detail_ids.p_length')
    def compute_total_knife_inches(self):
        for record in self:
            total = 0
            if record.batch_detail_ids:
                total = [line.quantity * line.p_length for line in record.batch_detail_ids]
                if total:
                    total = sum(total)
                else:
                    total = 0
            record.total_knife_inches = total

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    def action_confirm(self):
        if self.batch_detail_ids:
            mo_list = []
            if self.mrp_type == 'production':
                weight_loss = self.weight_loss
                total_kg = self.total_kg
                if total_kg:
                    line_dict = {mrp_line.id: round(mrp_line.qty_kg + mrp_line.qty_kg * weight_loss / total_kg, 0) for mrp_line in self.batch_detail_ids}
                    line_list = sum(line_dict.values())
                    if line_list > self.total_weight:
                        line_dict = {mrp_line.id: round(round(mrp_line.qty_kg, 0) + round(mrp_line.qty_kg, 0) * weight_loss / total_kg, 0) for mrp_line in self.batch_detail_ids}
                else:
                    line_dict = {mrp_line.id: 0 for mrp_line in self.batch_detail_ids}
                for line in self.batch_detail_ids:
                    product = line.product_id
                    mo_dict = {'product_id': product.id, 'product_qty': line.quantity, 'bom_id':line.bom_id.id,
                                    'product_uom_id': product.uom_id.id,'batch_production_id': self.id, 'picking_type_id': self.picking_type_id.id}
                    if self.partner_id:
                        mo_dict['partner_id'] = self.partner_id.id
                    mo_obj = self.env['mrp.production'].create(mo_dict)
                    mo_obj.sudo()._onchange_move_raw()
                    mo_obj.move_raw_ids.update({'product_uom_qty': line_dict.get(line.id)})
                    mo_obj.sudo()._onchange_bom()
                    mo_obj._onchange_service_charges()
                    mo_obj.onchange_picking_type()
            else:
                for line in self.batch_detail_ids:
                    product = line.product_id
                    mo_dict = {'product_id': product.id, 'product_qty': line.quantity, 'bom_id':line.bom_id.id,
                                    'product_uom_id': product.uom_id.id,'batch_production_id': self.id, 'picking_type_id': self.picking_type_id.id}
                    if self.partner_id:
                        mo_dict['partner_id'] = self.partner_id.id
                    mo_list.append(mo_dict)
                if mo_list:
                    mo_obj = self.env['mrp.production'].create(mo_list)
                    for mo in mo_obj:
                        mo.sudo()._onchange_move_raw()
                        mo.sudo()._onchange_bom()
                        mo._onchange_service_charges()
                        mo.onchange_picking_type()
        self.write({'state': 'confirm'})
        return True

    def action_cancel(self):
        production_obj = self.env['mrp.production']
        domain = [('batch_production_id','=',self.id)]
        production_done = production_obj.search([('state','=','done')] + domain)
        if production_done:
            raise Warning(_('You cannot cancel batch production because of its manufacturing order once it is done.'))
        production_open = production_obj.search([('state', 'not in', ('done','cancel'))] + domain)
        if production_open:
            for mo in production_open:
                mo.action_cancel()
        self.write({'state': 'cancel'})
        return True

    def action_open_mo(self):
        return {
            'name': _('Manufacturing Orders'),
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('batch_production_id', '=', self.id)],
        }

    def action_open_landed_cost(self):
        return {
            'name': _('Landed Costs'),
            'res_model': 'stock.landed.cost',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('batch_production_id', '=', self.id)],
        }

    def action_transfer_from_batch_order(self):
        result = self.env['mrp.production'].search([('batch_production_id', '=', self.id)])
        mo_name = []
        if all(res.state in ['done'] for res in result) or (len(result) > 1 and all(res.state in ['done','cancel'] for res in result)):
            return {
                'name': _('Create Transfer'),
                'type': 'ir.actions.act_window',
                'res_model': 'open.wizard',
                'view_mode': 'form',
                'view_id': self.env.ref('cortex_na.transfer_from_mo').id,
                'context': {},
                'target': 'new'
            }
        else:
            if all(res.state == 'cancel' for res in result):
                raise Warning(_('There is not any completed Manufacturing order, so you can not create transfer'))
            else:
                for res in result:
                    if res.state != 'cancel' and res.state != 'done':
                        mo_name.append(res.name)
                mo_name = ' , '.join(mo_name)
                raise Warning(_('Following Manufacturing Orders are not ready to transfer - %s ') % mo_name)
       
    def action_open_internal_transfer(self):
        return {
            'name': _('Transfer Orders'),
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('batch_id', '=', self.id)],
        }

    def action_batch_from_batch_order(self):
        batch_order = [[5,0]]
        batch_line = []
        input_value = False
        bom_order = self.env['mrp.bom'].search([], order='id desc')
        for line in self.batch_detail_ids:
            for bom in bom_order.filtered(lambda b: line.product_id.id in b.bom_line_ids.mapped('product_id').ids):
                batch_line.append(line.product_id.id)
                batch_order.append([0,0,{
                    'product_id':bom.product_tmpl_id.id,
                    'bom_id':bom.id,
                    'quantity': line.quantity,
                    'p_length':line.p_length,
                    'input_product_id':line.product_id.id
                }])
                break
            if line.product_id.id not in batch_line:
                input_value = True
                batch_order.append([0,0,{
                        'quantity': line.quantity,
                        'p_length':line.p_length,
                        'input_product_id':line.product_id.id
                    }])

        return {
            'name': _('Create Batch Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'batch.order',
            'view_mode': 'form',
            'view_id': self.env.ref('cortex_na.batch_order_form_batch_order').id,
            'context': {'default_batch_detail_ids':batch_order , 'input_value':input_value},
            'target': 'new'
        }
       
    @api.onchange('purchase_order_id')
    def onchange_purchase_order_id(self):
        if self.purchase_order_id:
            mo_order = self.env['mrp.production'].search([('batch_production_id', '=', self._origin.id),('state','!=','cancel')])
            item_list_for_batch_mo,list_product_id = [[5,0]],[]
            for line in self.purchase_order_id.order_line:
                if self.distribution_type == 'common':
                    item_list_for_batch_mo.append([0,0,{
                        'product_id': line.product_id.id,
                        'quantity': line.product_qty,
                        'product_uom_id': line.product_uom.id,
                        'price_unit': line.price_unit
                    }])
                elif self.distribution_type == 'specific':
                    for mo in mo_order:
                        if line.product_id.id in mo.product_id.service_products.ids:
                            list_product_id.append(line.product_id.id)
                            item_list_for_batch_mo.append([0,0,{
                                'product_id': line.product_id.id,
                                'quantity': line.product_qty,
                                'product_uom_id': line.product_uom.id,
                                'price_unit': line.price_unit,
                                'currency_id': line.currency_id.id,
                                'production_id': mo.id
                            }])
                            mo.write({'partner_id': self.purchase_order_id.partner_id.id,
                                'currency_id': self.purchase_order_id.currency_id.id,'purchase_order_id':self.purchase_order_id.id})
                    if line.product_id.id not in list_product_id:
                        item_list_for_batch_mo.append([0,0,{
                            'product_id': line.product_id.id,
                            'quantity': line.product_qty,
                            'product_uom_id': line.product_uom.id,
                            'price_unit': line.price_unit,
                            'subtotal': line.product_qty * line.price_unit,
                            'currency_id': line.currency_id.id
                        }])

            if self.distribution_type == 'common':
                self.update({'distribution_service_ids': item_list_for_batch_mo})
                self.update({'service_charge_ids': [[5,0]]})        
            elif self.distribution_type == 'specific':          
                self.update({'service_charge_ids': item_list_for_batch_mo})
        else:
            if self.state == 'confirm':
                raise Warning(_("Please select purchase order"))

    @api.onchange('distribution_type')
    def onchange_distribution_type(self):
        if self.purchase_order_id:
            self.onchange_purchase_order_id()

    def action_distribute_cost(self):
        total_quantity,total_length,price,price_length,price_weight = 0,0,0,0,0
        item_list,distribute_product = [],[]
        self.write({'service_charge_ids': [[5,0]]}) 
        mo_order = self.env['mrp.production'].search([('batch_production_id', '=', self.id),('state','!=','cancel')])
        
        for batch_line in self.batch_detail_ids:
            total_quantity += batch_line.quantity
            total_length += batch_line.quantity * batch_line.p_length

        for line in self.distribution_service_ids:
            if line.distribution_on == 'quantity':
                price = (line.subtotal/total_quantity) if total_quantity else 0
                if mo_order:
                    for mo in mo_order:
                        item_list.append((0, 0, {
                                'product_id': line.product_id.id,
                                'quantity': mo.product_qty,
                                'product_uom_id': line.product_uom_id.id,
                                'price_unit': price,
                                'production_id': mo.id,
                                'subtotal': mo.product_qty * price
                        }))
            elif line.distribution_on == 'length':
                product_name = []
                price_length = (line.subtotal/total_length) if total_length else 0
                for batch_line in self.batch_detail_ids:
                    if batch_line.p_length:
                        if mo_order:
                            for mo in mo_order:
                                if batch_line.product_id.id == mo.product_id.id:
                                    item_list.append((0,0,{
                                        'product_id': line.product_id.id,
                                        'quantity': mo.product_qty,
                                        'product_uom_id': line.product_uom_id.id,
                                        'price_unit': price_length * batch_line.p_length,
                                        'production_id': mo.id,
                                        'subtotal': mo.product_qty * price_length * batch_line.p_length
                                    }))
                    else:
                        product_name.append(batch_line.product_id.display_name)
                if len(product_name) >= 1:
                    product_name = ' ,\n'.join(product_name)        
                    raise UserError(_('Following batch details product does not have length - \n %s.') % product_name)
            elif line.distribution_on == 'weight':
                price_weight = (line.subtotal/self.total_kg) if self.total_kg else 0
                for batch_line in self.batch_detail_ids:
                    if batch_line.qty_kg:
                        if mo_order:
                            for mo in mo_order:
                                if batch_line.product_id.id == mo.product_id.id:
                                    item_list.append((0,0,{
                                        'product_id': line.product_id.id,
                                        'quantity': batch_line.qty_kg,
                                        'product_uom_id': line.product_uom_id.id,
                                        'price_unit': price_weight,
                                        'production_id': mo.id,
                                        'subtotal': batch_line.qty_kg * price_weight
                                    }))
            else:
                distribute_product.append(line.product_id.display_name)
        if len(distribute_product) >= 1:
            distribute_product = ' ,\n'.join(distribute_product)        
            raise UserError(_('Please select distribution on for - \n %s.') % distribute_product)
            
        self.write({'service_charge_ids': item_list})

    @api.model
    def create(self, vals):
        vals['batch_number'] = self.env['ir.sequence'].next_by_code('batch.production')
        return super(BatchProduction, self).create(vals)

    def write(self, vals):
        res = super(BatchProduction, self).write(vals)
        if self.service_charge_ids.ids != [] and self.distribution_type == 'specific':
            product_name = []
            for service_charge in self.service_charge_ids:
                if service_charge.production_id.id is False:
                    product_name.append(service_charge.product_id.display_name)
            product_name = ' ,\n'.join(product_name)
            if product_name:
                raise Warning(_('Please select manufacturing order for service charges - \n %s.') % product_name)
        return res

    def read(self, fields=None, load='_classic_read'):
        result = super(BatchProduction, self).read(fields, load=load)
        rec = self.env['stock.picking'].search([('batch_id', '=', result[0]['id'])])
        if rec and result[0]['id'] and result[0]['state'] == 'confirm':
            result[0]['isTransfer'] = 'true'
        return result

class BatchProductionDetail(models.Model):
    """ Batch Production Detail"""
    _name = '' \
            'batch.production.detail'
    _description = 'Batch Production Detail'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Material', copy=True , required=True)
    p_length = fields.Float(string='Length', copy=True)
    quantity = fields.Float(string='Quantity',digits='New Cortex Precision')
    batch_production_id = fields.Many2one('batch.production', string='Batch Production', ondelete='cascade')
    per_inch = fields.Float(related='batch_production_id.per_inch', string='Profile Weight/Inch (G)')
    profile_weight = fields.Float(string='Profile Weight (G)', compute='compute_profile_weight')
    qty_kg = fields.Float(string='Total Weight(KG)', compute='compute_qty_kg')
    profile_cost_per_knife = fields.Float(string='Profile Cost/ Knife', compute='compute_profile_cost_per_knife')
    service_cost_per_knife = fields.Float(string='Service Cost/ Knife', compute='compute_service_cost_per_knife')
    total_cost_per_knife = fields.Float(string='Total Cost/ Knife', compute='compute_total_cost_per_knife')
    input_product_id = fields.Many2one('product.product', string='Input Product', store=True, readonly=True )

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.p_length = self.product_id.length
            bom_id = self.env['mrp.bom'].search(['|', ('product_id', '=', self.product_id.id), '&', ('product_id', '=', False),
                                                 ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
                                                 ], limit=1)
            self.bom_id = bom_id.id
        else:
            self.p_length = 0
            self.bom_id = None

    @api.onchange('bom_id','bom_id.bom_line_ids','bom_id.bom_line_ids.product_id')
    def onchange_bom(self):
        for record in self:
            if record.bom_id.bom_line_ids:
                record.input_product_id = record.bom_id.bom_line_ids[0].product_id.id
           
    @api.depends('p_length', 'per_inch')
    def compute_profile_weight(self):
        for record in self:
            record.profile_weight = record.p_length * record.per_inch

    @api.depends('profile_weight', 'quantity')
    def compute_qty_kg(self):
        for record in self:
            record.qty_kg = record.quantity * record.profile_weight / 1000

    @api.depends('quantity', 'p_length', 'batch_production_id.profile_cost', 'batch_production_id.total_knife_inches')
    def compute_profile_cost_per_knife(self):
        for record in self:
            profile_cost_inch = 0
            if record.batch_production_id and record.batch_production_id.total_knife_inches:
                profile_cost_inch = record.p_length * record.batch_production_id.profile_cost / record.batch_production_id.total_knife_inches
            record.profile_cost_per_knife = profile_cost_inch

    @api.depends('quantity', 'batch_production_id.service_cost')
    def compute_service_cost_per_knife(self):
        for record in self:
            service_cost_inch = 0
            if record.batch_production_id:
                service_cost_inch = record.batch_production_id.service_cost
            record.service_cost_per_knife = service_cost_inch

    @api.depends('profile_cost_per_knife', 'service_cost_per_knife')
    def compute_total_cost_per_knife(self):
        for record in self:
            record.total_cost_per_knife = record.profile_cost_per_knife + record.service_cost_per_knife
