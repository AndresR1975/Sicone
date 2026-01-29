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
    'author': 'SICONE SAS',
    'website': 'https://www.sicone.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
    ],
    'data': [
        # Seguridad
        'security/sicone_security.xml',
        'security/ir.model.access.csv',
        
        # Datos iniciales
        'data/precios_referencia_data.xml',
        'data/secuencias.xml',
        
        # Vistas
        'views/proyecto_views.xml',
        'views/cotizacion_views.xml',
        'views/cotizacion_version_views.xml',
        'views/precio_referencia_views.xml',
        'views/menus.xml',
        
        # Wizards
        'wizard/importar_excel_views.xml',
        'wizard/exportar_excel_views.xml',
        
        # Reportes
        'report/cotizacion_report.xml',
        'report/cotizacion_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
