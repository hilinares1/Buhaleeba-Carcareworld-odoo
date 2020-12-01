{
    'name': 'Bank Reconciliation Statement Date',
    'version': '13.0.1.0',
    'author': 'Bincy',
    'company': 'Appsgate',
    'website': 'http://www.appsgate.net',
    'category': 'Accounting',
    'summary': 'Chnaging the curent date on button click',
    'description': """ Get bank statement date by the button click """,
    'depends': ['account','bank_reconciliation'],
    'data': [

        'views/bank_st-date.xml',

    ],

    'installable': True,
    'auto_install': False,
}
