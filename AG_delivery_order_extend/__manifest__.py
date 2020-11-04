# -*- coding: utf-8 -*-

{
    "name": "Delivery Order states added",
    "summary": "Delivery Order states added",
    "version": "1.0.0",
    "license": "Other proprietary",
    'author': "Sananaz Mansuri",
    'website': 'www.odoo.com',
    "category": "Inventory",
    "depends": [
        "stock", "sale_management", "odoo_multi_channel_sale"
    ],
    "data": [
        'views/stock_picking_view.xml',
        'views/sale_order.xml',
    ],
    'qweb': [
    ],
    "installable": True,
}
