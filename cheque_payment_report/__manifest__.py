# -*- coding: utf-8 -*-

{
    'name': ' cheque Payment Report',
    'author': 'Ahmed Said',
    'summary': 'Make reporting for Cheque',
    'version': '1.0',
    'depends': ['account', 'base','base_accounting_kit'],
    'data': [
        'views/cheque_payment.xml',
        'report/cheque_payment_report.xml',
        'report/report_templates.xml'
    ],
}
