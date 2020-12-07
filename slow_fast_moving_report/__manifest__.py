{
    'name': 'Slow Moving Report',
    'summary': 'Slow Moving /Fast Moving Items',
    'description': """
        show the Available Qty, Total Sales Qty, Last Sales and Indication
    """,
    'category': 'Inventory',
    'author': 'Higazi',
    'depends': ['base', 'stock', 'sale', 'purchase', 'AG_products'],
    'data': [
        'views/view.xml'
    ],
}
