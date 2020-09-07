# !/usr/bin/env python
# -*- coding: utf-8 -*-
{
    'name': 'Purchase Total Discount',
    'version': '1.0',
    'author': 'MNP',
    'description': """
    """,
    'depends': ['purchase', 'odx_sale_discount_total'],
    'data': [
        'views/purchase_view.xml',
        # 'views/vendor_bill_view.xml',
        # 'views/report_purchaseorder.xml'

    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
