{
    'name': 'Forecast Analysis Report',
    'summary': 'Forecast Analysis Report',
    'description': """
    Forecast Analysis Report
    """,
    'category': 'Inventory',
    'author': 'Higazi',
    'depends': ['base', 'stock', 'sale', 'purchase','AG_products'],
    'data': [
        'security/ir.model.access.csv',
        'views/view.xml'
    ],
}
