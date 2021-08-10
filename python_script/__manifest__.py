# -*- coding: utf-8 -*-
{
    'name': "Python Script",

    'summary': "Runing Python Scripts",

    'description': """
        App to run pyton scripts from Odoo.
    """,

    'author': "Mounir Lahsini",
    'version': '1.0',
    'installable': True,
    'website': 'https://github.com/mounirlahsini',

    'depends': ['base'],

    'data': [
        'security/ir.model.access.csv',
        'views/python_script_views.xml',
    ],

    'demo': [
    ],
}