# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import fields, models, api

class MachineCenterOEM(models.Model):
    _name = 'machine.center.oem'
    _description = 'Machine Center OEM'
    _rec_name = 'name'

    name = fields.Char(string='Machine Center OEM')


class LengthOfKnives(models.Model):
    _name = 'length.of.knives'
    _description = 'Length of Knives'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Float(string='Length of Knives',digits='New Knife Precision')     

class KnifeProvider(models.Model):
    _name = 'knife.provider'
    _description = 'Knife Provider'
    _rec_name = 'name'

    name = fields.Char(string='Knife Provider')

class DrumheadLocation(models.Model):
    _name = 'drumhead.location'
    _description = 'Drumhead Location'
    _rec_name = 'name'

    name = fields.Char(string='Knife Provider')


class KnifeLengths(models.Model):
    _name = 'knife.length'
    _description = 'Knife Lengths'
    _rec_name = 'name'

    name = fields.Char(string='Knife Lengths')


class Numbers(models.Model):
    _name = 'numbers'
    _description = 'Numbers'
    _rec_name = 'name'

    name = fields.Integer(string='Number')


class KnivesPerSegment(models.Model):
    _name = 'knives.per.segment'
    _description = 'Knives Per Segment'
    _rec_name = 'name'

    name = fields.Integer(string='Number')


class Head(models.Model):
    _name = 'head'
    _description = '#/Head'
    _rec_name = 'name'

    name = fields.Integer(string='#/Head')

    @api.model
    def set_data_head(self):
        for i in range(41):
            self.create({'name':i})


class OfHeads(models.Model):
    _name = 'of.head'
    _description = '# Of Heads'
    _rec_name = 'name'

    name = fields.Integer(string='# Of Heads')

    @api.model
    def set_of_head_data(self):
        print('----------------------test-------------------------')
        for i in range(221):
            print('i////////////////////////////////--------------', i)
            self.create({'name': i})

class ShiftsEdge(models.Model):
    _name = 'shifts.edge'
    _description = 'Shifts/Edge'
    _rec_name = 'name'

    name = fields.Integer(string='Shifts/Edge')


class OfShifts(models.Model):
    _name = 'of.shifts'
    _description = '# of Shifts'
    _rec_name = 'name'

    name = fields.Integer(string='# of Shifts')


class Days(models.Model):
    _name = 'days'
    _description = 'Days'
    _rec_name = 'name'

    name = fields.Integer(string='Days')