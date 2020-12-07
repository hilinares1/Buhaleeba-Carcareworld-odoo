# -*- coding: utf-8 -*-

# Part of Sananaz Mansuri See LICENSE file for full copyright and licensing details.
{
    'name': "Stock Incoming Transfer Rack",
    'version': '1.5.0',
    'license': 'Other proprietary',
    'category': 'Inventory',
    'summary': """Stock Incoming Transfer Rack""",
    'description': """
        Stock Incoming Transfer Rack
    """,
    'author': "Sananaz Mansuri",
    'website': 'www.odoo.com',
    'live_test_url': '',
    'depends': [
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_view.xml',
        'views/stock_rack_shelf_view.xml',
        'views/stock_quant_view.xml',
    ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
