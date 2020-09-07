# -*- coding: utf-8 -*-
#############################################################################
#
#
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

{
    'name': 'Sale Discount on Total Amount',
    'version': '13.0.1.0.0',
    'category': 'Sales Management',
    'summary': "Discount on Total in Sale and Invoice With Discount Limit and Approval",
    'description': """

Sale Discount for Total Amount
=======================
Module to manage discount on total amount in Sale.
        as an specific amount or percentage
""",
    'depends': ['sale',
                'account',
                ],
    'data': [
        # 'views/sale_view.xml',
        'views/account_invoice_view.xml',
        'views/invoice_report.xml',
        # 'views/sale_order_report.xml',
        'views/res_config_view.xml',

    ],
    'demo': [
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'application': True,
    'installable': True,
    'auto_install': False,
}
