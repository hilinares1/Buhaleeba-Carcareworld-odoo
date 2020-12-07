# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#    you can modify it under the terms of the GNU OPL (v1), Version 1.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU OPL (OPL v1) for more details.
#
##############################################################################

{
    'name': "Stock Ageing Analysis",
    'version': '13.0.1.0.0',
    'summary': """Product Ageing Analysis With Filterations""",
    'description': """With this module, we can perform stock ageing analysis with optional filters such
                as location, category""",
    'author': "Cybrosys Techno Solutions",
    'website': "https://www.cybrosys.com",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'category': 'Stock',
    'depends': ['product', 'stock'],
    'data': [
             'security/ir.model.access.csv',
             'wizard/product_ageing.xml',
             'report/report_ageing_products.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'price': 19,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
    'application': False,
}
