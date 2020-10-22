
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{

    'name': 'AG_buhaleeba Reports',
    'depends': ['account','purchase','stock'],
    'data': [
        'report/start.xml',
        
        'report/quotation_purchase_inheirt.xml',
        'report/order_purchase_inheirt.xml',
        'report/delivery_slip_inheirt.xml',
        'report/invoice_inheirt.xml',

    ],
    'demo': [
    ],
    'license': 'AGPL-3',
    'application': True,
    'installable': True,
    'auto_install': False,
}
