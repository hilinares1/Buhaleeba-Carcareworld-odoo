# -*- coding: utf-8 -*-
# License: Odoo Proprietary License v1.0

{
    'name': 'Dynamic Accounting Reports - PDF, Excel',
    'version': '13.0.1.0.3',
    'category': 'Invoicing Management',
    'summary': 'All in One Dynamic Accounting Reports For Odoo & '
               'Export the Report in PDF or Excel',
    'sequence': '10',
    'live_test_url': 'https://www.youtube.com/watch?v=TIR7RUOEs_0',
    'author': 'Odoo Mates',
    'license': 'OPL-1',
    'price': 40,
    'currency': 'USD',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'website': '',
    'depends': ['accounting_pdf_reports'],
    'demo': [],
    'data': [
        'views/report_templates.xml',
        'views/dynamic_reports.xml',
        'report/report_om_account_pdf.xml',
        'report/reports.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.gif'],
    'qweb': [
        'static/src/xml/*.xml'
    ],
}
