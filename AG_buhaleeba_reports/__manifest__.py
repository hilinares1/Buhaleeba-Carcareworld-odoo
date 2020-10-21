# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'AG_buhaleeba Reports',
    'author': 'Fouad',
    'depends': ['sale'],
    'data': [
        # 'report/cridet_note_inheirt.xml',
        'report/invoice_inheirt.xml',
        'report/delivery_slip_inheirt.xml',
        'report/purchase_quotation.xml',
        'report/purchase_order_inheirt.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
