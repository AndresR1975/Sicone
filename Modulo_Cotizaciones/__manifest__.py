# -*- coding: utf-8 -*-
{
    'name': 'SICONE - Sistema Integrado de Construcción Eficiente',
    'version': '1.0.0',
    'category': 'Construction',
    'summary': 'Sistema de cotizaciones y gestión de proyectos de construcción',
    'description': """
        SICONE - Sistema Integrado de Construcción Eficiente
        =====================================================
        
        Módulo completo para la gestión de cotizaciones de construcción que incluye:
        
        * Gestión de Proyectos de Construcción
        * Cotizaciones con versionamiento y auditoría
        * Dos capítulos independientes:
            - Capítulo 1: Diseños, Estructura, Mampostería y Techos
            - Capítulo 2: Cimentaciones y Complementarios
        * Gestión de Personal Profesional y Administrativo
        * Cálculo automático de AIU (Administración, Imprevistos, Utilidad)
        * Generación de contratos separados o integrados
        * Importación/Exportación de Excel
        * Reportes ejecutivos en PDF
        
        Características principales:
        ----------------------------
        - Versionamiento completo de cotizaciones
        - Auditoría de cambios por usuario y fecha
        - Estructura flexible para casos particulares
        - Manejo de dos contratos independientes
        - Catálogo de precios históricos
        - Cálculos automáticos con valores sugeridos editables
    """,
    'author': 'AI-MindNovation',
    'website': 'https://www.ai-mindnovation.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
        'sale',
        'account',
        'project',
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'data': [
        # Seguridad
        'security/ir.model.access.csv',

        'data/secuencias.xml',
        'data/sicone_project_sequence.xml',
        # 'data/precios_referencia_data.xml',
          
        # Vistas
        'views/proyecto_views.xml',
        'views/project_project_inherit_views.xml',
        'views/sale_order_view.xml',
        'views/cotizacion_template_views.xml',
        'views/cotizacion_ponderada_views.xml',
        'views/menus.xml',
        'views/import_excel_wizard_view.xml',
        
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/banner.png', 'static/description/icon.png'],
}
