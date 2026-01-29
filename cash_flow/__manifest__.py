{
    'name': 'Cash Flow Tool',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Finance',
    'author': 'AI-MindNovation',
    'website': 'https://www.ai-mindnovation.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'sale',
    ],
    'summary': 'Herramienta integral de flujo de caja, cotizaciones y análisis financiero para proyectos de construcción.',
    'description': 'Módulo Odoo que migra y amplía las funcionalidades de la plataforma SICONE desarrollada en Python + Streamlit, integrando cotizaciones, flujo de caja, conciliación y reportes ejecutivos.',
    'data': [
        'views/cotizador_menu.xml',
        'views/sale_order_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'images': ['static/description/icon.png'],
}
