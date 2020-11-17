# -*- coding: utf-8 -*-

{
    'name': 'Report Enhancement',
    'version': '2.2.4',
    'category': 'Purchase',
    'summary': """This app allow you to check the inv qty and qty to be invoiced in purchase analysis and send the due invoice notifications to salesperson""",
    'depends': [
        'purchase',
        'base',
        'account',
    ],
    'description': """
                   """,
    'author': 'Appsgate',
    'website': 'http://www.apps-gate.net',
    'support': '',
    'images': [],
    'data': [
        'security/ir.model.access.csv',
        # 'views/customer_overdue.xml',

        'report/entry_analysis.xml',

    ],
    'installable': True,
    'application': False,
}

