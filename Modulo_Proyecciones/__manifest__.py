# -*- coding: utf-8 -*-
{
    'name': 'SICONE - Proyección de Flujo de Caja',
    'version': '1.0.0',
    'category': 'Construction',
    'summary': 'Proyección de flujo de caja para proyectos de construcción',
    'description': """
        Módulo para la gestión y proyección de flujo de caja en proyectos de construcción.
        Permite vincular proyecciones a proyectos y cotizaciones, calcular ingresos, egresos y saldos, y visualizar el detalle por periodo.
    """,
    'author': 'AI-MindNovation',
    'website': 'https://www.ai-mindnovation.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'Modulo_Cotizaciones',
    ],
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/proyeccion_fcl_views.xml',
    ],
    'installable': True,
    'application': True,
}
