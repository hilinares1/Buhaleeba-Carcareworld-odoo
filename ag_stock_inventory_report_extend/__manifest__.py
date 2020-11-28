# -*- coding: utf-8 -*-
{
    'name': "Inventory Report changes",
    'version': '1.1.2',
    'license': 'Other proprietary',
    'category': 'Inventory Report changes',
    'summary': """Account Invoice Report Extend""",
    'description': """
       Inventory Report changes.
    """,
    'author': "Sananaz Mansuri",
    'website': 'www.odoo.com',
    'images': [],
    'live_test_url': '',
    'depends': ['base', 'stock', 'stock_incoming_transfer_rack'],
    'data': [
        'report/inventory_report_extend.xml',
        'report/inventory_picking_report_extend.xml'
    ],
    'installable': True,
    'application': False,
}
