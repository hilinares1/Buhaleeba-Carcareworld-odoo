# -*- coding: utf-8 -*-

# Part of Sananaz Mansuri See LICENSE file for full copyright and licensing details.
{
    'name': "AG Purchase Order Landed Costs",
    'version': '1.0.0',
    'license': 'Other proprietary',
    'category': 'Inventory',
    'summary': """AG Purchase Order Landed Costs""",
    'description': """
        AG Purchase Order Landed Costs
    """,
    'author': "Sananaz Mansuri",
    'website': 'www.odoo.com',
    'live_test_url': '',
    'depends': [
        'purchase',
        'stock_landed_costs',
    ],
    'data': [
        'views/purchase_order_view.xml',
    ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
