# -*- coding: utf-8 -*-

# Part of Sananaz Mansuri See LICENSE file for full copyright and licensing details.
{
    'name': "AG Retransfer Approval",
    'version': '1.0.0',
    'license': 'Other proprietary',
    'category': 'Inventory',
    'summary': """AG Retransfer Approval""",
    'description': """
        AG Retransfer Approval
    """,
    'author': "Sananaz Mansuri",
    'website': 'www.odoo.com',
    'live_test_url': '',
    'depends': [
        'stock',
    ],
    'data': [
        'views/stock_picking_view.xml',
        'wizard/stock_return_picking_view.xml',
    ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
