# -*- coding: utf-8 -*-
{
    'name': "Payment Solution by Plutu",
    'summary': "Experience seamless payment solutions with Paylink, the premium payment gateway company in Saudi Arabia",
    'author': "Mohamed Elkmeshi",
    'website': "https://plutu.ly/?source=odoo-module",
    'category': 'Accounting/Payment Providers',
    'version': '20.0.1.4',
    'depends': ['payment', 'website'],
    'data': [
        'views/payment_plutu_templates.xml',
        'views/payment_provider_views.xml',
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',

    'license': 'LGPL-3',
}
