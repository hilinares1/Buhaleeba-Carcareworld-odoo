# -*- coding: utf-8 -*-
{
    'name': "Period Closing",

    'summary': """
         Accounts Localization by AppsGate""",

    'description': """
        Accounting Period Year Closing V10
    """,

    'author': "AppsGate",
    'website': "http://www.apps-gate.net",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '13.0',

    # any module necessary for this one to work correctly
    'depends': ['base','account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'wizard/od_period_closing.xml',
        'views/menu.xml',
    ],
    # only loaded in demonstration mode
     'installable': True,
     'application': False,
}