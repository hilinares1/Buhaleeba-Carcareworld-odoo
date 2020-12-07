# -*- coding: utf-8 -*-

# Part of Sananaz Mansuri See LICENSE file for full copyright and licensing details.

{

    'name': 'Odoo Tax Custom Report',
    'version': '1.1.1',
    'category': 'Accounting & Finance',
    'summary': 'Odoo Tax Custom Report. This module print customer invoice and vendor bill.',
    'description': """
        - Odoo Tax Custom Report
        
        This module print customer invoice and vendor bill
            """,
    'author': 'Sananaz Mansuri',
    'website': 'www.odoo.com',
    'depends': [
        'account',
    ],
    'data': [
        'wizard/invoice_wizard.xml',
        'report/invoice_report.xml',
     ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
