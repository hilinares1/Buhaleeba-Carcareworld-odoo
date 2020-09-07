# -*- coding: utf-8 -*-

{
    'name': 'Sale & Purchase Customization',
    'category': 'Sale, Purchase',
    'sequence': 14,
    'summary': 'Purchase Order is created while conforming the Sale Order and vice versa ',
    'description': """
        Adding sequence to  customers and including it in name get and name search. 
        New fields is added in both sale order and purchase order. While confirming sale order,a purchase
        order is created based on the corresponding sale order and vice versa.
    """,
    'author': 'Odox SoftHub / Albin /Ashif',
    'website': 'https://www.odoxsofthub.com',
    'version': '13.0.0.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'purchase', 'report_xlsx', 'mail',
                'product','web'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sale_purchase_customization_data.xml',
        'data/bill_of_lading_status_update.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner.xml',
        'views/sale_views.xml',
        'views/purchase_views.xml',
        'views/purchase_landing_cost_view.xml',
        'views/account_move_views.xml',
        'report/invoice_report.xml',
        'report/sale_report_template.xml',
        'report/purchase_report.xml',
        'report/rfq_print.xml',
        'views/purchase_shipment_view.xml',
        'views/ir_attachment_view.xml',
        'report/instruction_report_template.xml',
        'report/purchase_instruction_report_template.xml',
        'report/report.xml',
        'report/mastex_tocb_report_view.xml',
        'wizard/mail_compose_message_view.xml',
        'views/product_view.xml',
        'report/external_layout_standard.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
}
