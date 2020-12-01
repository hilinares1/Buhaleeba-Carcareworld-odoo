# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Import Journal Entry from CSV or Excel File',
    'version': '13.0.0.1',
    'sequence': 4,
    'category': 'Accounting',
    'summary': 'Import Data App for import journal entry import account move line import account move import mass journal entries import multiple journal entries excel import journal entry excel import accounting entry  import opening journal entry import opening balance',
    'description': """
	Used to import the journal entry from the xls or csv data file.

    """,
    'author': 'Appsgate',
    'website': 'https://www.apps-gate.net',

    'depends': ['base','sale_management','account'],
    'data': ["account_move.xml"
            ],
    'qweb': [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,

}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
