# -*- coding: utf-8 -*-
{
    'name': 'CSR Upcycling',
    'summary': 'Department-wise upcycling pipeline with HR and Inventory insights',
    'version': '19.0.1.0.0',
    'category': 'Sustainability',
    'author': 'CSR Labs',
    'website': 'https://example.com/csr-upcycling',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'product', 'stock'],
    'data': [
        'security/csr_security.xml',
        'security/ir.model.access.csv',
        'views/csr_upcycle_request_views.xml',
        'views/product_inherit_views.xml',
        'views/hr_department_inherit_views.xml',
        'views/analytics_views.xml',
        'views/menu_views.xml',
        'data/demo_data.xml',
    ],
    'application': True,
    'installable': True,
}
