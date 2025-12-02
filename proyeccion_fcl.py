"""
SICONE - Módulo de Proyección de Flujo de Caja
Fase 1: Configuración y Proyección de Ingresos/Egresos

Versión: 1.2.1
Fecha: Diciembre 2025
Autor: AI-MindNovation

CHANGELOG v1.2.1 (CRÍTICO):
- FIX: Ruana clasificada correctamente en fase Cubierta (no en Complementarios)
- FIX: Vuelto a modelo de distribución LINEAL (como Excel de referencia)
- REASON: Excel NO usa desembolsos escalonados y NO genera saldos negativos
- VALIDATION: Verificado contra Formato_Proyeccion_de_Obra_y_Flujo_de_Caja

CHANGELOG v1.2:
- FEATURE: Interfaz para editar porcentajes Mat/MO por concepto sin discriminar
- FEATURE: Alertas visuales de saldos negativos con análisis detallado
- FIX: Reclasificación de conceptos de techos según mapa mental SICONE
- FIX: Nombre de archivo descargable incluye nombre del proyecto
- IMPROVEMENT: Dashboard de déficit con gráfica y tabla de semanas críticas

CHANGELOG v1.1:
- FIX: Hito 'Fin de Obra' ahora se ejecuta al FINAL de la fase Entrega
- FIX: Eliminada asignación redundante de fecha_inicio_fcl
"""

import streamlit as st
import pandas as pd
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import plotly.graph_objects as go

# ============================================================================
# FUNCIONES DE CARGA DE DATOS
# ============================================================================

def cargar_cotizacion_desde_bd(proyecto_id: int) -> dict:
    """Carga la cotización más reciente de un proyecto desde BD"""
    conn = sqlite3.connect('sicone.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT datos_json 
        FROM cotizaciones 
        WHERE proyecto_id = ?
        ORDER BY fecha_guardado DESC 
        LIMIT 1
    """, (proyecto_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return json.loads(result[0])
    return None

def obtener_proyectos_con_cotizaciones() -> List[Tuple]:
    """Obtiene lista de proyectos que tienen cotizaciones guardadas"""
    conn = sqlite3.connect('sicone.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT
            p.id, 
            p.nombre, 
            p.cliente, 
            c.fecha_guardado,
            c.total_costo_directo
        FROM proyectos p
        INNER JOIN cotizaciones c ON p.id = c.proyecto_id
        ORDER BY c.fecha_guardado DESC
    """)
    
    proyectos = cursor.fetchall()
    conn.close()
    
    return proyectos

# ============================================================================
# FUNCIONES DE EXTRACCIÓN DE CONCEPTOS (SIN HARDCODING)
# ============================================================================

def extraer_conceptos_dinamico(cotizacion: dict) -> Dict:
    """
    Extrae TODOS los conceptos del JSON de cotización
    Retorna diccionario con estructura:
    {
        'Concepto': {
            'total': float,
            'materiales': float,
            'equipos': float,
            'mano_obra': float,
            'admin': float (opcional),
            'fuente': str,
            'items': dict (opcional)
        }
    }
    """
    conceptos = {}
    
    # 1. DISEÑOS Y PLANIFICACIÓN (solo diseños base × área)
    if 'disenos' in cotizacion:
        disenos_base = sum([
            v.get('precio_unitario', 0) 
            for v in cotizacion['disenos'].values()
        ])
        
        # Multiplicar por área del proyecto
        area_base = cotizacion.get('proyecto', {}).get('area_base', 1)
        total_disenos = disenos_base * area_base
        
        conceptos['Diseños y Planificación'] = {
            'total': total_disenos,
            'materiales': 0,
            'equipos': 0,
            'mano_obra': total_disenos,  # Diseños es mano de obra profesional
            'fuente': 'disenos'
        }
    
    # 2. ESTRUCTURA
    if 'estructura' in cotizacion:
        est = cotizacion['estructura']
        cantidad = est.get('cantidad', 1)
        
        total_estructura = (
            est.get('precio_materiales', 0) + 
            est.get('precio_equipos', 0) + 
            est.get('precio_mano_obra', 0)
        ) * cantidad
        
        conceptos['Estructura'] = {
            'total': total_estructura,
            'materiales': est.get('precio_materiales', 0) * cantidad,
            'equipos': est.get('precio_equipos', 0) * cantidad,
            'mano_obra': est.get('precio_mano_obra', 0) * cantidad,
            'fuente': 'estructura'
        }
    
    # 3. MAMPOSTERÍA
    if 'mamposteria' in cotizacion:
        mam = cotizacion['mamposteria']
        cantidad = mam.get('cantidad', 1)
        
        total_mamposteria = (
            mam.get('precio_materiales', 0) + 
            mam.get('precio_equipos', 0) + 
            mam.get('precio_mano_obra', 0)
        ) * cantidad
        
        conceptos['Mampostería'] = {
            'total': total_mamposteria,
            'materiales': mam.get('precio_materiales', 0) * cantidad,
            'equipos': mam.get('precio_equipos', 0) * cantidad,
            'mano_obra': mam.get('precio_mano_obra', 0) * cantidad,
            'fuente': 'mamposteria'
        }
    
    # 4. TECHOS Y COMPLEMENTARIOS (de mamposteria_techos)
    if 'mamposteria_techos' in cotizacion:
        techos_cubierta = {}
        techos_complementarios = {}
        
        # Clasificación según mapa mental SICONE
        # CUBIERTA: Cubiertas exteriores principales + RUANA
        items_cubierta = [
            'Ruana',  # ← VA EN CUBIERTA
            'Cubierta, Superboard y Manto',
            'Cubierta, Superboard y Shingle',
            'Canoas',
            'Tapacanal y Lagrimal'
        ]
        
        # COMPLEMENTARIOS: Elementos que van con Estructura/Mampostería
        items_complementarios = [
            'Contramarcos - Ventana',
            'Contramarcos - Puerta',
            'Embudos y Boquillas',
            'Entrepiso Placa Fácil',
            'Pérgolas y Estructura sin Techo'
        ]
        
        for item, datos in cotizacion['mamposteria_techos'].items():
            cant = datos.get('cantidad', 0)
            if cant > 0:
                subtotal = (
                    datos.get('precio_materiales', 0) +
                    datos.get('precio_equipos', 0) +
                    datos.get('precio_mano_obra', 0)
                ) * cant
                
                detalle = {
                    'cantidad': cant,
                    'materiales': datos.get('precio_materiales', 0) * cant,
                    'equipos': datos.get('precio_equipos', 0) * cant,
                    'mano_obra': datos.get('precio_mano_obra', 0) * cant,
                    'total': subtotal
                }
                
                if item in items_cubierta:
                    techos_cubierta[item] = detalle
                elif item in items_complementarios:
                    techos_complementarios[item] = detalle
        
        # Agrupar Techos/Cubierta (solo cubiertas principales)
        if techos_cubierta:
            conceptos['Techos (Cubierta)'] = {
                'total': sum([v['total'] for v in techos_cubierta.values()]),
                'materiales': sum([v['materiales'] for v in techos_cubierta.values()]),
                'equipos': sum([v['equipos'] for v in techos_cubierta.values()]),
                'mano_obra': sum([v['mano_obra'] for v in techos_cubierta.values()]),
                'items': techos_cubierta,
                'fuente': 'mamposteria_techos'
            }
        
        # Agrupar Complementarios de Techos (van con Estructura/Mampostería)
        if techos_complementarios:
            conceptos['Complementarios (Techos)'] = {
                'total': sum([v['total'] for v in techos_complementarios.values()]),
                'materiales': sum([v['materiales'] for v in techos_complementarios.values()]),
                'equipos': sum([v['equipos'] for v in techos_complementarios.values()]),
                'mano_obra': sum([v['mano_obra'] for v in techos_complementarios.values()]),
                'items': techos_complementarios,
                'fuente': 'mamposteria_techos'
            }
    
    # 5. CIMENTACIONES
    if 'opcion_cimentacion' in cotizacion:
        opcion = cotizacion['opcion_cimentacion']
        cim_key = 'cimentacion_opcion1' if opcion == 'Opción 1' else 'cimentacion_opcion2'
        
        if cim_key in cotizacion:
            total_cimentacion = sum([
                v.get('cantidad', 0) * v.get('precio_unitario', 0)
                for v in cotizacion[cim_key].values()
            ])
            
            # Aplicar AIU de cimentación
            if 'aiu_cimentacion' in cotizacion:
                aiu_cim = cotizacion['aiu_cimentacion']
                factor_aiu_cim = 1 + (
                    aiu_cim.get('pct_comision', 0) + 
                    aiu_cim.get('pct_aiu', 0)
                ) / 100
                total_cimentacion *= factor_aiu_cim
            
            # NO APLICAR discriminación hardcoded - dejar que usuario configure
            conceptos['Cimentaciones'] = {
                'total': total_cimentacion,
                'materiales': 0,  # Usuario configura
                'equipos': 0,     # Usuario configura
                'mano_obra': 0,   # Usuario configura
                'fuente': cim_key,
                'items': cotizacion[cim_key]
            }
    
    # 6. COMPLEMENTARIOS (sección principal)
    if 'complementarios' in cotizacion:
        total_complementarios = sum([
            v.get('cantidad', 0) * v.get('precio_unitario', 0)
            for v in cotizacion['complementarios'].values()
        ])
        
        # Aplicar AIU de complementarios
        if 'aiu_complementarios' in cotizacion:
            aiu_comp = cotizacion['aiu_complementarios']
            factor_aiu_comp = 1 + (
                aiu_comp.get('pct_comision', 0) + 
                aiu_comp.get('pct_aiu', 0)
            ) / 100
            total_complementarios *= factor_aiu_comp
        
        # NO APLICAR discriminación hardcoded - dejar que usuario configure
        conceptos['Complementarios'] = {
            'total': total_complementarios,
            'materiales': 0,  # Usuario configura
            'equipos': 0,     # Usuario configura
            'mano_obra': 0,   # Usuario configura
            'fuente': 'complementarios',
            'items': cotizacion['complementarios']
        }
    
    # 7. PERSONAL PROFESIONAL
    if 'personal_profesional' in cotizacion:
        total_prof = 0
        for puesto, datos in cotizacion['personal_profesional'].items():
            total_prof += (
                datos.get('valor_mes', 0) * 
                (1 + datos.get('pct_prestaciones', 0) / 100) *
                datos.get('dedicacion', 0) *
                datos.get('meses', 0) *
                datos.get('cantidad', 0)
            )
        
        conceptos['Personal Profesional'] = {
            'total': total_prof,
            'materiales': 0,
            'equipos': 0,
            'mano_obra': total_prof,
            'fuente': 'personal_profesional'
        }
    
    # 8. PERSONAL ADMINISTRATIVO
    if 'personal_administrativo' in cotizacion:
        total_admin = 0
        for puesto, datos in cotizacion['personal_administrativo'].items():
            total_admin += (
                datos.get('valor_mes', 0) * 
                (1 + datos.get('pct_prestaciones', 0) / 100) *
                datos.get('dedicacion', 0) *
                datos.get('meses', 0) *
                datos.get('cantidad', 0)
            )
        
        conceptos['Personal Administrativo'] = {
            'total': total_admin,
            'materiales': 0,
            'equipos': 0,
            'mano_obra': 0,
            'admin': total_admin,
            'fuente': 'personal_administrativo'
        }
    
    # 9. OTROS CONCEPTOS ADMINISTRATIVOS
    if 'otros_admin' in cotizacion:
        total_otros = 0
        for categoria, datos in cotizacion['otros_admin'].items():
            if isinstance(datos, dict) and 'items_detalle' in datos:
                total_otros += sum(datos['items_detalle'].values())
        
        conceptos['Otros Conceptos Admin'] = {
            'total': total_otros,
            'materiales': 0,
            'equipos': 0,
            'mano_obra': 0,
            'admin': total_otros,
            'fuente': 'otros_admin'
        }
    
    return conceptos

# ============================================================================
# FUNCIONES DE ASIGNACIÓN A CONTRATOS
# ============================================================================
def asignar_contratos(conceptos: Dict, cotizacion: dict) -> Tuple[Dict, Dict]:
    """
    Asigna conceptos a contratos usando resumen_calculado del JSON.
    Si no existe resumen_calculado, usa método de cálculo tradicional.
    
    ARQUITECTURA MEJORADA:
    - Usa resumen_calculado del cotizador (fuente única de verdad)
    - Garantiza consistencia de valores entre módulos
    - Elimina recálculos y diferencias por redondeos
    - Mantiene retrocompatibilidad con JSON antiguos
    
    Args:
        conceptos: Dict con conceptos extraídos (usado como fallback)
        cotizacion: Dict con datos completos del JSON
        
    Returns:
        Tuple[Dict, Dict]: (contrato_1, contrato_2)
    """
    
    # ========================================================================
    # MÉTODO PREFERIDO: Usar resumen_calculado del JSON
    # ========================================================================
    
    if 'resumen_calculado' in cotizacion and cotizacion['resumen_calculado'] is not None:
        resumen = cotizacion['resumen_calculado']
        
        # Extraer contratos directamente (valores exactos del cotizador)
        c1_data = resumen['contratos']['contrato_1']
        c2_data = resumen['contratos']['contrato_2']
        
        # Construir estructura esperada por FCL
        contrato_1 = {
            'nombre': c1_data['nombre'],
            'monto': c1_data['monto'],
            'conceptos': [k for k in c1_data['desglose'].keys() if k != 'AIU (incluye Utilidad)'],
            'desglose': c1_data['desglose'],
            'materiales': 0,
            'equipos': 0,
            'mano_obra': 0,
            'admin': 0,
            'aiu': c1_data['desglose'].get('AIU (incluye Utilidad)', 0)
        }
        
        contrato_2 = {
            'nombre': c2_data['nombre'],
            'monto': c2_data['monto'],
            'conceptos': list(c2_data['desglose'].keys()),
            'desglose': c2_data['desglose'],
            'materiales': 0,
            'equipos': 0,
            'mano_obra': 0,
            'admin': 0,
            'aiu': 0  # C2 ya incluye AIU en cada concepto
        }
        
        # Calcular totales de Mat/MO/Equipos/Admin desde conceptos_para_fcl
        if 'conceptos_para_fcl' in resumen:
            conceptos_fcl = resumen['conceptos_para_fcl']
            
            for concepto_nombre, datos in conceptos_fcl.items():
                if datos.get('contrato') == 'contrato_1':
                    contrato_1['materiales'] += datos.get('materiales', 0)
                    contrato_1['equipos'] += datos.get('equipos', 0)
                    contrato_1['mano_obra'] += datos.get('mano_obra', 0)
                    contrato_1['admin'] += datos.get('admin', 0)
                elif datos.get('contrato') == 'contrato_2':
                    contrato_2['materiales'] += datos.get('materiales', 0)
                    contrato_2['equipos'] += datos.get('equipos', 0)
                    contrato_2['mano_obra'] += datos.get('mano_obra', 0)
                    contrato_2['admin'] += datos.get('admin', 0)
        
        return contrato_1, contrato_2
    
    # ========================================================================
    # MÉTODO FALLBACK: Cálculo tradicional (retrocompatibilidad)
    # ========================================================================
    
    contrato_1 = {
        'nombre': 'Contrato 1 - Obra Gris',
        'conceptos': [
            'Diseños y Planificación',
            'Estructura',
            'Mampostería',
            'Complementarios (Techos)',
            'Techos (Cubierta)'
        ],
        'monto': 0,
        'materiales': 0,
        'equipos': 0,
        'mano_obra': 0,
        'admin': 0,
        'aiu': 0,
        'desglose': {}
    }
    
    contrato_2 = {
        'nombre': 'Contrato 2 - Cimentación y Obras Complementarias',
        'conceptos': [
            'Cimentaciones',
            'Complementarios'
        ],
        'monto': 0,
        'materiales': 0,
        'equipos': 0,
        'mano_obra': 0,
        'admin': 0,
        'aiu': 0,
        'desglose': {}
    }
    
    # Calcular base constructiva C1 (sin Diseños que ya incluye admin)
    base_constructiva_c1 = 0
    
    # Calcular montos de Contrato 1
    for concepto in contrato_1['conceptos']:
        if concepto in conceptos:
            datos = conceptos[concepto]
            
            # Sumar al desglose
            contrato_1['desglose'][concepto] = datos['total']
            
            # Acumular por categorías
            contrato_1['materiales'] += datos.get('materiales', 0)
            contrato_1['equipos'] += datos.get('equipos', 0)
            contrato_1['mano_obra'] += datos.get('mano_obra', 0)
            contrato_1['admin'] += datos.get('admin', 0)
            
            # Base constructiva (excluye Diseños)
            if concepto != 'Diseños y Planificación':
                base_constructiva_c1 += datos['total']
    
    # Aplicar AIU GENERAL sobre C1 (incluye utilidad)
    if 'config_aiu' in cotizacion:
        config_aiu = cotizacion['config_aiu']
        
        comision_pct = config_aiu.get('Comisión de Ventas (%)', 0) / 100
        imprevistos_pct = config_aiu.get('Imprevistos (%)', 0) / 100
        admin_pct_config = config_aiu.get('Administración (%)', 0) / 100
        logistica_pct = config_aiu.get('Logística (%)', 0) / 100
        utilidad_pct = config_aiu.get('Utilidad (%)', 0) / 100
        
        # CÁLCULO DE % ADMIN REAL (como en cotizador)
        # Calcular Admin detallada desde conceptos
        admin_detallada_total = 0
        if 'Personal Profesional' in conceptos:
            admin_detallada_total += conceptos['Personal Profesional']['total']
        if 'Personal Administrativo' in conceptos:
            admin_detallada_total += conceptos['Personal Administrativo']['total']
        if 'Otros Conceptos Admin' in conceptos:
            admin_detallada_total += conceptos['Otros Conceptos Admin']['total']
        
        # Calcular % Admin REAL sobre base constructiva
        admin_pct_real = (admin_detallada_total / base_constructiva_c1) if base_constructiva_c1 > 0 else 0
        
        # Usar el MAYOR entre config y real (como hace el cotizador)
        admin_pct = max(admin_pct_config, admin_pct_real)
        
        # AIU TOTAL incluye utilidad (como en cotizador)
        factor_aiu_total = comision_pct + imprevistos_pct + admin_pct + logistica_pct + utilidad_pct
        
        aiu_total_c1 = base_constructiva_c1 * factor_aiu_total
        
        # Desglosar para visualización
        contrato_1['aiu'] = aiu_total_c1
        contrato_1['desglose']['AIU (incluye Utilidad)'] = aiu_total_c1
    
    # Monto total C1
    contrato_1['monto'] = sum(contrato_1['desglose'].values())
    
    # Calcular montos de Contrato 2 (ya incluyen AIU)
    for concepto in contrato_2['conceptos']:
        if concepto in conceptos:
            datos = conceptos[concepto]
            
            # Sumar al desglose
            contrato_2['desglose'][concepto] = datos['total']
            
            # Acumular categorías
            contrato_2['materiales'] += datos.get('materiales', 0)
            contrato_2['equipos'] += datos.get('equipos', 0)
            contrato_2['mano_obra'] += datos.get('mano_obra', 0)
            contrato_2['admin'] += datos.get('admin', 0)
            
            # El AIU ya está incluido en Cimentaciones y Complementarios
            # pero lo separamos para visualización
            if concepto == 'Cimentaciones' and 'aiu_cimentacion' in cotizacion:
                # Estimar AIU incluido
                aiu_cim = cotizacion['aiu_cimentacion']
                factor_aiu = (aiu_cim.get('pct_comision', 0) + aiu_cim.get('pct_aiu', 0)) / 100
                base_cim = datos['total'] / (1 + factor_aiu)
                aiu_incluido = datos['total'] - base_cim
                contrato_2['aiu'] += aiu_incluido
            
            elif concepto == 'Complementarios' and 'aiu_complementarios' in cotizacion:
                aiu_comp = cotizacion['aiu_complementarios']
                factor_aiu = (aiu_comp.get('pct_comision', 0) + aiu_comp.get('pct_aiu', 0)) / 100
                base_comp = datos['total'] / (1 + factor_aiu)
                aiu_incluido = datos['total'] - base_comp
                contrato_2['aiu'] += aiu_incluido
    
    # Monto total C2 (AIU y utilidad ya incluidos en Cimentaciones y Complementarios)
    contrato_2['monto'] = sum(contrato_2['desglose'].values())
    
    return contrato_1, contrato_2

# ============================================================================
# FUNCIONES DE CONFIGURACIÓN DE FASES Y HITOS
# ============================================================================

def obtener_totales_admin_imprevistos_logistica(cotizacion: dict, conceptos: Dict) -> Dict:
    """
    Extrae totales de Admin, Imprevistos y Logística para distribución por fases
    
    Admin incluye: Personal Profesional + Personal Administrativo + Otros Admin
    Estos se distribuirán proporcionalmente por duración de fases
    """
    totales = {
        'admin': 0,
        'imprevistos': 0,
        'logistica': 0
    }
    
    # Obtener totales de conceptos administrativos
    if 'Personal Profesional' in conceptos:
        totales['admin'] += conceptos['Personal Profesional']['total']
    
    if 'Personal Administrativo' in conceptos:
        totales['admin'] += conceptos['Personal Administrativo']['total']
    
    if 'Otros Conceptos Admin' in conceptos:
        totales['admin'] += conceptos['Otros Conceptos Admin']['total']
    
    # Obtener % de AIU de la configuración
    if 'config_aiu' in cotizacion:
        config = cotizacion['config_aiu']
        
        # Calcular base imponible (suma de conceptos constructivos, excluyendo admin)
        base_imponible = sum([
            c['total'] for nombre, c in conceptos.items()
            if nombre not in ['Personal Profesional', 'Personal Administrativo', 'Otros Conceptos Admin']
        ])
        
        # Calcular Imprevistos y Logística
        totales['imprevistos'] = base_imponible * (config.get('Imprevistos (%)', 0) / 100)
        totales['logistica'] = base_imponible * (config.get('Logística (%)', 0) / 100)
    
    return totales

def generar_configuracion_fases_default(conceptos: Dict) -> List[Dict]:
    """
    Genera configuración por defecto de fases según mapeo acordado
    
    Admin (Personal + Otros) se distribuye por duración de fases
    """
    fases = [
        {
            'nombre': 'Procesos Administrativos',
            'conceptos': ['Diseños y Planificación'],
            'duracion_semanas': None,  # Usuario ingresa
            'pct_admin': 20,  # 20% del admin total
            'pct_imprevistos': 0,
            'pct_logistica': 20,
            'porcentajes_usuario': {
                'materiales': 0,  # Diseños es 100% MO
                'mano_obra': 100
            }
        },
        {
            'nombre': 'Cimentación',
            'conceptos': ['Cimentaciones'],
            'duracion_semanas': None,
            'pct_admin': 0,
            'pct_imprevistos': 30,
            'pct_logistica': 20,
            'porcentajes_usuario': {
                'materiales': 70,  # Para conceptos sin discriminar
                'mano_obra': 30
            }
        },
        {
            'nombre': 'Estructura, Mampostería y Complementarios',
            'conceptos': [
                'Estructura',
                'Mampostería',
                'Complementarios (Techos)',
                'Complementarios'
            ],
            'duracion_semanas': None,
            'pct_admin': 60,
            'pct_imprevistos': 50,
            'pct_logistica': 40,
            'porcentajes_usuario': {
                'materiales': 65,
                'mano_obra': 35
            }
        },
        {
            'nombre': 'Cubierta',
            'conceptos': ['Techos (Cubierta)'],
            'duracion_semanas': None,
            'pct_admin': 15,
            'pct_imprevistos': 15,
            'pct_logistica': 15,
            'porcentajes_usuario': {
                'materiales': 60,
                'mano_obra': 40
            }
        },
        {
            'nombre': 'Entrega',
            'conceptos': [],  # Solo ajustes finales
            'duracion_semanas': None,
            'pct_admin': 5,
            'pct_imprevistos': 5,
            'pct_logistica': 5,
            'porcentajes_usuario': {
                'materiales': 10,
                'mano_obra': 90
            }
        }
    ]
    
    return fases

def aplicar_discriminacion_inteligente(concepto_datos: Dict, fase_config: Dict) -> Dict:
    """
    Aplica discriminación de materiales/MO de forma inteligente:
    - Si el concepto YA tiene discriminación → usar esos valores
    - Si NO tiene discriminación → aplicar % del usuario
    """
    total = concepto_datos['total']
    
    # Verificar si ya tiene discriminación
    tiene_materiales = concepto_datos.get('materiales', 0) > 0
    tiene_mano_obra = concepto_datos.get('mano_obra', 0) > 0
    tiene_equipos = concepto_datos.get('equipos', 0) > 0
    
    if tiene_materiales or tiene_mano_obra or tiene_equipos:
        # YA ESTÁ DISCRIMINADO - usar valores del concepto
        return {
            'materiales': concepto_datos.get('materiales', 0),
            'equipos': concepto_datos.get('equipos', 0),
            'mano_obra': concepto_datos.get('mano_obra', 0),
            'admin': concepto_datos.get('admin', 0),
            'fuente_discriminacion': 'cotizacion'
        }
    else:
        # NO ESTÁ DISCRIMINADO - aplicar % del usuario
        pct_mat = fase_config['porcentajes_usuario']['materiales'] / 100
        pct_mo = fase_config['porcentajes_usuario']['mano_obra'] / 100
        
        return {
            'materiales': total * pct_mat,
            'equipos': 0,
            'mano_obra': total * pct_mo,
            'admin': concepto_datos.get('admin', 0),
            'fuente_discriminacion': 'usuario'
        }

def configurar_hitos_default(contrato_1: Dict, contrato_2: Dict) -> List[Dict]:
    """
    Genera configuración por defecto de hitos según acuerdo con cliente
    """
    hitos = [
        {
            'id': 1,
            'nombre': 'Anticipo Procesos Administrativos',
            'contrato': 1,
            'porcentaje': 50,
            'monto': contrato_1['monto'] * 0.50,
            'fase_vinculada': 'Procesos Administrativos',
            'momento': 'inicio'
        },
        {
            'id': 2,
            'nombre': 'Inicio Cimentación',
            'contrato': 2,
            'porcentaje': 50,
            'monto': contrato_2['monto'] * 0.50,
            'fase_vinculada': 'Cimentación',
            'momento': 'inicio'
        },
        {
            'id': 3,
            'nombre': 'Fin Cimentación / Inicio Obra Gris',
            'contrato': 'ambos',
            'porcentaje_c1': 40,
            'porcentaje_c2': 40,
            'monto': contrato_1['monto'] * 0.40 + contrato_2['monto'] * 0.40,
            'fase_vinculada': 'Estructura, Mampostería y Complementarios',
            'momento': 'inicio'
        },
        {
            'id': 4,
            'nombre': 'Fin de Obra',
            'contrato': 'ambos',
            'porcentaje_c1': 10,
            'porcentaje_c2': 10,
            'monto': contrato_1['monto'] * 0.10 + contrato_2['monto'] * 0.10,
            'fase_vinculada': 'Entrega',
            'momento': 'fin'  # CRÍTICO: Al FIN de Entrega, no al inicio
        }
    ]
    
    return hitos

# ============================================================================
# FUNCIONES DE PROYECCIÓN
# ============================================================================

def generar_proyeccion_completa(
    conceptos: Dict,
    fases_config: List[Dict],
    hitos: List[Dict],
    contrato_1: Dict,
    contrato_2: Dict,
    totales_aiu: Dict,
    fecha_inicio: datetime
) -> pd.DataFrame:
    """
    Genera la proyección completa semana a semana
    Incluye: ingresos proyectados, egresos por categoría, flujo neto, saldo
    """
    
    # 1. Calcular duración total
    duracion_total = sum([f['duracion_semanas'] for f in fases_config if f['duracion_semanas']])
    
    # 2. Crear DataFrame base
    proyeccion = []
    semana_actual = 1
    saldo_acumulado = 0
    
    for fase in fases_config:
        duracion = fase['duracion_semanas']
        if not duracion or duracion <= 0:
            continue
        
        # Calcular egresos de esta fase
        egresos_fase = {
            'materiales': 0,
            'equipos': 0,
            'mano_obra': 0,
            'admin': 0,
            'imprevistos': 0,
            'logistica': 0
        }
        
        # Sumar conceptos de la fase
        for nombre_concepto in fase['conceptos']:
            if nombre_concepto in conceptos:
                concepto_datos = conceptos[nombre_concepto]
                
                # Aplicar discriminación inteligente
                discriminacion = aplicar_discriminacion_inteligente(concepto_datos, fase)
                
                egresos_fase['materiales'] += discriminacion['materiales']
                egresos_fase['equipos'] += discriminacion['equipos']
                egresos_fase['mano_obra'] += discriminacion['mano_obra']
                egresos_fase['admin'] += discriminacion['admin']
        
        # Agregar Admin/Imprevistos/Logística prorrateados
        egresos_fase['admin'] += totales_aiu['admin'] * (fase['pct_admin'] / 100)
        egresos_fase['imprevistos'] += totales_aiu['imprevistos'] * (fase['pct_imprevistos'] / 100)
        egresos_fase['logistica'] += totales_aiu['logistica'] * (fase['pct_logistica'] / 100)
        
        # Distribuir semanalmente de forma LINEAL (como Excel)
        egresos_semanales = {
            k: v / duracion for k, v in egresos_fase.items()
        }
        
        # Generar registros semanales
        for semana_fase in range(1, duracion + 1):
            # Calcular ingresos de esta semana
            ingresos_semana = 0
            
            # Verificar si hay hitos en esta semana
            for hito in hitos:
                if hito['fase_vinculada'] == fase['nombre']:
                    if (hito['momento'] == 'inicio' and semana_fase == 1) or \
                       (hito['momento'] == 'fin' and semana_fase == duracion):
                        ingresos_semana += hito['monto']
            
            # Calcular totales
            total_egresos = sum(egresos_semanales.values())
            flujo_neto = ingresos_semana - total_egresos
            saldo_acumulado += flujo_neto
            
            # Agregar registro
            fecha = fecha_inicio + timedelta(weeks=semana_actual - 1)
            
            proyeccion.append({
                'Semana': semana_actual,
                'Fecha': fecha.strftime('%Y-%m-%d'),
                'Fase': fase['nombre'],
                'Semana_Fase': semana_fase,
                'Ingresos_Proyectados': ingresos_semana,
                'Materiales': egresos_semanales['materiales'],
                'Equipos': egresos_semanales['equipos'],
                'Mano_Obra': egresos_semanales['mano_obra'],
                'Admin': egresos_semanales['admin'],
                'Imprevistos': egresos_semanales['imprevistos'],
                'Logistica': egresos_semanales['logistica'],
                'Total_Egresos': total_egresos,
                'Flujo_Neto': flujo_neto,
                'Saldo_Acumulado': saldo_acumulado
            })
            
            semana_actual += 1
    
    return pd.DataFrame(proyeccion)

# ============================================================================
# INTERFACE DE USUARIO - PASO 1: CARGAR COTIZACIÓN
# ============================================================================

def render_paso_1_cargar_cotizacion():
    """Paso 1: Seleccionar y cargar cotización base"""
    
    st.header("📋 Paso 1: Cargar Cotización Base")
    
    st.markdown("""
    Seleccione la cotización del proyecto para configurar la proyección de flujo de caja.
    Los datos de la cotización se usarán para calcular los egresos proyectados.
    """)
    
    # Tabs para las dos opciones
    tab1, tab2 = st.tabs(["📁 Proyectos Guardados", "📤 Cargar JSON"])
    
    with tab1:
        proyectos = obtener_proyectos_con_cotizaciones()
        
        if proyectos:
            # Crear opciones de visualización
            opciones = []
            for p in proyectos:
                fecha_str = p[3][:10] if p[3] else 'Sin fecha'
                opciones.append(
                    f"{p[1]} - {p[2]} (${p[4]:,.0f}) - {fecha_str}"
                )
            
            proyecto_sel = st.selectbox(
                "Seleccione proyecto:",
                options=range(len(opciones)),
                format_func=lambda x: opciones[x],
                key="sel_proyecto_fcl"
            )
            
            # Mostrar info del proyecto seleccionado
            proyecto_id, nombre, cliente, fecha, total = proyectos[proyecto_sel]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Proyecto", nombre)
            with col2:
                st.metric("Cliente", cliente)
            with col3:
                st.metric("Total Cotización", f"${total:,.0f}")
            
            if st.button("✅ Cargar esta cotización", type="primary", use_container_width=True):
                # Cargar cotización
                cotizacion = cargar_cotizacion_desde_bd(proyecto_id)
                
                if cotizacion:
                    st.session_state.cotizacion_fcl = cotizacion
                    st.session_state.proyecto_fcl_id = proyecto_id
                    st.session_state.paso_fcl = 2
                    st.success("✅ Cotización cargada correctamente")
                    st.rerun()
                else:
                    st.error("❌ Error al cargar la cotización")
        else:
            st.info("ℹ️ No hay proyectos con cotizaciones guardadas. Use la pestaña 'Cargar JSON'.")
    
    with tab2:
        uploaded_file = st.file_uploader(
            "Seleccione archivo JSON de cotización",
            type=['json'],
            key="upload_json_fcl"
        )
        
        if uploaded_file:
            try:
                cotizacion = json.load(uploaded_file)
                
                # Validar estructura mínima
                if 'proyecto' in cotizacion:
                    st.success("✅ Archivo JSON válido")
                    
                    # Mostrar resumen
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Proyecto", cotizacion['proyecto'].get('nombre', 'N/A'))
                    with col2:
                        st.metric("Cliente", cotizacion['proyecto'].get('cliente', 'N/A'))
                    with col3:
                        area = cotizacion['proyecto'].get('area_base', 0)
                        st.metric("Área Base", f"{area:.2f} m²")
                    
                    if st.button("✅ Continuar con esta cotización", type="primary", use_container_width=True):
                        st.session_state.cotizacion_fcl = cotizacion
                        st.session_state.proyecto_fcl_id = None  # No está en BD
                        st.session_state.paso_fcl = 2
                        st.rerun()
                else:
                    st.error("❌ El archivo JSON no tiene la estructura correcta")
            except json.JSONDecodeError:
                st.error("❌ Error al leer el archivo JSON")

# ============================================================================
# INTERFACE DE USUARIO - PASO 2: CONFIGURAR CONTRATOS Y FASES
# ============================================================================

def render_paso_2_configurar_proyecto():
    """Paso 2: Configurar contratos, fases y cronograma"""
    
    cotizacion = st.session_state.cotizacion_fcl
    
    st.header("⚙️ Paso 2: Configuración del Proyecto")
    
    # Botón volver
    if st.button("◀️ Volver a selección de cotización"):
        st.session_state.paso_fcl = 1
        st.rerun()
    
    st.markdown("---")
    
    # Extraer conceptos
    if 'conceptos_fcl' not in st.session_state:
        with st.spinner("Extrayendo conceptos de la cotización..."):
            conceptos = extraer_conceptos_dinamico(cotizacion)
            st.session_state.conceptos_fcl = conceptos
    else:
        conceptos = st.session_state.conceptos_fcl
    
    # Asignar contratos
    if 'contratos_fcl' not in st.session_state:
        c1, c2 = asignar_contratos(conceptos, cotizacion)
        st.session_state.contratos_fcl = {'contrato_1': c1, 'contrato_2': c2}
    
    contratos = st.session_state.contratos_fcl
    
    # Mostrar resumen de contratos
    st.subheader("📊 Resumen de Contratos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"#### 📄 {contratos['contrato_1']['nombre']}")
        st.metric("Monto Total", f"${contratos['contrato_1']['monto']:,.0f}")
        
        with st.expander("Ver desglose"):
            for concepto, monto in contratos['contrato_1']['desglose'].items():
                if 'AIU' in concepto:
                    st.write(f"• **{concepto}:** ${monto:,.0f} ⚙️")
                else:
                    st.write(f"• **{concepto}:** ${monto:,.0f}")
    
    with col2:
        st.markdown(f"#### 📄 {contratos['contrato_2']['nombre']}")
        st.metric("Monto Total", f"${contratos['contrato_2']['monto']:,.0f}")
        
        with st.expander("Ver desglose"):
            for concepto, monto in contratos['contrato_2']['desglose'].items():
                st.write(f"• **{concepto}:** ${monto:,.0f}")
            if contratos['contrato_2']['aiu'] > 0:
                st.caption(f"   (AIU y utilidad incluidos: ${contratos['contrato_2']['aiu']:,.0f})")
    
    st.markdown("---")
    
    # ========================================================================
    # CONFIGURACIÓN DE FECHA DE INICIO (ACTUALIZADO)
    # ========================================================================
    
    st.subheader("📅 Fecha de Inicio del Proyecto")
    
    # Mostrar contexto de cotización si existe
    if 'fecha_guardado' in cotizacion:
        try:
            fecha_cot = datetime.fromisoformat(cotizacion['fecha_guardado']).strftime('%d/%m/%Y')
            st.caption(f"ℹ️ Cotización creada el: {fecha_cot}")
        except:
            pass
    
    # Helper de semanas (opcional, colapsable)
    with st.expander("🔧 Calcular fecha automáticamente", expanded=False):
        st.markdown("""
        Si no conoce la fecha exacta de inicio, use este calculador para estimar 
        la fecha basándose en cuántas semanas faltan para iniciar el proyecto.
        """)
        
        semanas_adelante = st.slider(
            "¿En cuántas semanas inicia el proyecto?",
            min_value=0,
            max_value=24,
            value=4,
            key="slider_semanas",
            help="0 = Hoy, 4 = En 4 semanas, etc."
        )
        
        fecha_calculada = datetime.now() + timedelta(weeks=semanas_adelante)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if semanas_adelante == 0:
                st.info(f"📅 Fecha calculada: **{fecha_calculada.strftime('%d/%m/%Y')}** (Hoy)")
            else:
                st.info(f"📅 Fecha calculada: **{fecha_calculada.strftime('%d/%m/%Y')}** (En {semanas_adelante} semanas)")
        
        with col2:
            if st.button("✅ Usar esta fecha", type="secondary", use_container_width=True):
                st.session_state.fecha_inicio_calculada = fecha_calculada.date()
                st.success("Fecha aplicada ✓")
                st.rerun()
    
    # Input principal (siempre visible)
    # Preservar fecha: widget > calculada > actual
    if 'fecha_inicio_fcl' in st.session_state:
        fecha_default = st.session_state.fecha_inicio_fcl
    elif 'fecha_inicio_calculada' in st.session_state:
        fecha_default = st.session_state.fecha_inicio_calculada
    else:
        fecha_default = datetime.now().date()
    
    fecha_inicio = st.date_input(
        "Fecha de inicio del proyecto:",
        value=fecha_default,
        min_value=datetime(2020, 1, 1).date(),
        max_value=datetime(2030, 12, 31).date(),
        key="fecha_inicio_fcl",
        help="Fecha en la que inicia la ejecución del proyecto (Fase 1: Procesos Administrativos)"
    )
    
    # Mostrar información contextual
    col1, col2 = st.columns(2)
    
    with col1:
        hoy = datetime.now().date()
        dias_diff = (fecha_inicio - hoy).days
        
        if dias_diff > 0:
            semanas_diff = dias_diff // 7
            dias_restantes = dias_diff % 7
            
            if dias_restantes > 0:
                texto_semanas = f"{semanas_diff} semanas y {dias_restantes} días"
            else:
                texto_semanas = f"{semanas_diff} semanas"
            
            st.info(f"⏭️ El proyecto inicia en **{dias_diff} días** (~{texto_semanas})")
        elif dias_diff < 0:
            semanas_diff = abs(dias_diff) // 7
            st.warning(f"⚠️ Fecha en el pasado: inició hace **{abs(dias_diff)} días** (~{semanas_diff} semanas)")
        else:
            st.success("✅ El proyecto inicia **HOY**")
    
    with col2:
        # Calcular fecha fin estimada si ya hay duraciones configuradas
        duracion_total = sum([
            f.get('duracion_semanas', 0) 
            for f in st.session_state.get('fases_config_fcl', [])
        ])
        
        if duracion_total > 0:
            fecha_fin = fecha_inicio + timedelta(weeks=duracion_total)
            st.metric("🏁 Fin estimado", fecha_fin.strftime('%d/%m/%Y'))
        else:
            st.caption("ℹ️ Configure las fases abajo para ver fecha de fin")
    
    st.markdown("---")
    
    # ========================================================================
    # CONFIGURAR FASES Y CRONOGRAMA
    # ========================================================================
    
    st.subheader("📅 Configuración de Cronograma")
    
    # Generar configuración default si no existe
    if 'fases_config_fcl' not in st.session_state:
        fases = generar_configuracion_fases_default(conceptos)
        st.session_state.fases_config_fcl = fases
    
    fases = st.session_state.fases_config_fcl
    
    st.markdown("#### ⏱️ Duración de Fases (en semanas)")
    
    st.markdown("""
    Configure la duración estimada de cada fase del proyecto. Los porcentajes de materiales 
    y mano de obra se aplicarán solo a conceptos que no tengan esta discriminación en la cotización.
    """)
    
    duraciones_actualizadas = False
    
    # Tabla de configuración de fases
    for i, fase in enumerate(fases):
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
            
            with col1:
                st.markdown(f"**{fase['nombre']}**")
                if fase['conceptos']:
                    st.caption(f"Incluye: {', '.join(fase['conceptos'][:2])}{'...' if len(fase['conceptos']) > 2 else ''}")
            
            with col2:
                duracion = st.number_input(
                    "Semanas",
                    min_value=1,
                    max_value=52,
                    value=fase['duracion_semanas'] if fase['duracion_semanas'] else 4,
                    key=f"dur_fase_{i}",
                    label_visibility="collapsed"
                )
                if duracion != fase['duracion_semanas']:
                    fases[i]['duracion_semanas'] = duracion
                    duraciones_actualizadas = True
            
            with col3:
                st.caption(f"Mat: {fase['porcentajes_usuario']['materiales']}%")
            
            with col4:
                st.caption(f"M.O.: {fase['porcentajes_usuario']['mano_obra']}%")
            
            with col5:
                # Mostrar íconos de AIU asignado
                if fase.get('pct_admin', 0) > 0:
                    st.caption("💼")
                if fase.get('pct_imprevistos', 0) > 0:
                    st.caption("⚠️")
            
            st.markdown("---")
    
    if duraciones_actualizadas:
        st.session_state.fases_config_fcl = fases
    
    st.markdown("---")
    
    # ========================================================================
    # EDITAR PORCENTAJES MAT/MO (SOLO PARA CONCEPTOS SIN DISCRIMINAR)
    # ========================================================================
    
    st.markdown("#### 🔢 Distribución de Costos por Concepto")
    
    st.info("""
    📌 **¿Para qué sirve esto?**  
    
    Los conceptos que no tienen discriminación de costos en la cotización (como Cimentación y Complementarios) 
    necesitan una estimación de cómo se distribuyen entre Materiales, Equipos y Mano de Obra.
    
    Ajuste estos porcentajes según su experiencia con proyectos similares.
    """)
    
    porcentajes_actualizados = False
    
    # Identificar qué conceptos necesitan estimación
    conceptos_editables = {}
    
    for fase in fases:
        for nombre_concepto in fase['conceptos']:
            if nombre_concepto in conceptos:
                concepto_datos = conceptos[nombre_concepto]
                # Verificar si NO tiene discriminación completa
                tiene_discriminacion = (
                    concepto_datos.get('materiales', 0) > 0 or
                    concepto_datos.get('equipos', 0) > 0 or
                    concepto_datos.get('mano_obra', 0) > 0
                )
                
                if not tiene_discriminacion and nombre_concepto not in conceptos_editables:
                    conceptos_editables[nombre_concepto] = {
                        'fase': fase['nombre'],
                        'total': concepto_datos['total'],
                        'pct_materiales': fase['porcentajes_usuario']['materiales'],
                        'pct_mano_obra': fase['porcentajes_usuario']['mano_obra']
                    }
    
    if conceptos_editables:
        st.markdown("**Conceptos que requieren estimación:**")
        
        for i, (nombre_concepto, datos) in enumerate(conceptos_editables.items()):
            with st.expander(f"⚙️ {nombre_concepto} (${datos['total']:,.0f})", expanded=False):
                st.caption(f"📍 Fase asociada: {datos['fase']}")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    materiales = st.number_input(
                        "Materiales (%)",
                        min_value=0,
                        max_value=100,
                        value=datos['pct_materiales'],
                        step=5,
                        key=f"concepto_mat_{i}",
                        help="Porcentaje del costo que corresponde a materiales"
                    )
                
                with col2:
                    mano_obra = st.number_input(
                        "Mano de Obra (%)",
                        min_value=0,
                        max_value=100,
                        value=datos['pct_mano_obra'],
                        step=5,
                        key=f"concepto_mo_{i}",
                        help="Porcentaje del costo que corresponde a mano de obra"
                    )
                
                with col3:
                    equipos = 100 - materiales - mano_obra
                    
                    if equipos >= 0:
                        st.metric("Equipos (%)", equipos, 
                                 help="Calculado automáticamente como: 100% - Materiales - M.O.")
                        
                        if materiales + mano_obra == 100:
                            st.success("✅ 100%")
                        elif materiales + mano_obra < 100:
                            st.info(f"ℹ️ {equipos}% para equipos")
                    else:
                        st.error(f"❌ Excede 100% por {abs(equipos)}%")
                
                # Actualizar si cambió
                if materiales != datos['pct_materiales'] or mano_obra != datos['pct_mano_obra']:
                    # Actualizar en la fase correspondiente
                    for fase in fases:
                        if fase['nombre'] == datos['fase']:
                            fase['porcentajes_usuario']['materiales'] = materiales
                            fase['porcentajes_usuario']['mano_obra'] = mano_obra
                            porcentajes_actualizados = True
                            break
                
                # Mostrar estimación en pesos
                st.caption(f"💰 Estimación: Materiales ${datos['total'] * materiales/100:,.0f} | "
                          f"M.O. ${datos['total'] * mano_obra/100:,.0f} | "
                          f"Equipos ${datos['total'] * equipos/100:,.0f}")
        
        if porcentajes_actualizados:
            st.session_state.fases_config_fcl = fases
            st.success("✅ Porcentajes actualizados")
    else:
        st.success("✅ Todos los conceptos tienen discriminación completa en la cotización")
    
    st.markdown("---")
    
    # Calcular y mostrar duración total y cronograma
    duracion_total = sum([f['duracion_semanas'] for f in fases if f['duracion_semanas']])
    
    if duracion_total > 0:
        meses_total = duracion_total / 4
        fecha_fin_proyecto = fecha_inicio + timedelta(weeks=duracion_total)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🗓️ Inicio", fecha_inicio.strftime('%d/%m/%Y'))
        
        with col2:
            st.metric("⏱️ Duración Total", f"{duracion_total} semanas", delta=f"{meses_total:.1f} meses")
        
        with col3:
            st.metric("🏁 Fin Estimado", fecha_fin_proyecto.strftime('%d/%m/%Y'))
        
        # Timeline visual de fases
        with st.expander("📊 Ver Timeline de Fases", expanded=False):
            st.markdown("#### Cronograma Detallado")
            
            fecha_actual = fecha_inicio
            
            for i, fase in enumerate(fases):
                if fase['duracion_semanas']:
                    fecha_fin_fase = fecha_actual + timedelta(weeks=fase['duracion_semanas'])
                    
                    # Calcular semana del proyecto
                    semana_inicio_fase = ((fecha_actual - fecha_inicio).days // 7) + 1
                    semana_fin_fase = ((fecha_fin_fase - fecha_inicio).days // 7)
                    
                    st.markdown(
                        f"**{i+1}. {fase['nombre']}**  \n"
                        f"📅 {fecha_actual.strftime('%d/%m/%Y')} → {fecha_fin_fase.strftime('%d/%m/%Y')}  \n"
                        f"⏱️ {fase['duracion_semanas']} semanas (Semanas {semana_inicio_fase}-{semana_fin_fase} del proyecto)  \n"
                        f"📦 Conceptos: {', '.join(fase['conceptos']) if fase['conceptos'] else 'Ajustes finales'}"
                    )
                    
                    st.markdown("---")
                    
                    fecha_actual = fecha_fin_fase
    
    st.markdown("---")
    
    # ========================================================================
    # CONFIGURAR HITOS DE PAGO
    # ========================================================================
    
    st.subheader("💰 Hitos de Pago")
    
    st.markdown("""
    Los hitos de pago están configurados según el acuerdo estándar con el cliente. 
    Puede revisar el detalle a continuación.
    """)
    
    if 'hitos_fcl' not in st.session_state:
        hitos = configurar_hitos_default(contratos['contrato_1'], contratos['contrato_2'])
        st.session_state.hitos_fcl = hitos
    
    hitos = st.session_state.hitos_fcl
    
    # Mostrar tabla de hitos
    hitos_data = []
    for h in hitos:
        if h['contrato'] == 'ambos':
            porcentaje_str = f"C1: {h['porcentaje_c1']}%, C2: {h['porcentaje_c2']}%"
            contrato_str = "Ambos"
        else:
            porcentaje_str = f"{h.get('porcentaje', '-')}%"
            contrato_str = f"Contrato {h['contrato']}"
        
        hitos_data.append({
            'Hito': h['nombre'],
            'Contrato': contrato_str,
            'Porcentaje': porcentaje_str,
            'Monto': f"${h['monto']:,.0f}",
            'Fase Vinculada': h['fase_vinculada'],
            'Momento': h['momento'].capitalize()
        })
    
    hitos_df = pd.DataFrame(hitos_data)
    
    st.dataframe(hitos_df, use_container_width=True, hide_index=True)
    
    # Resumen de ingresos
    total_ingresos = sum([h['monto'] for h in hitos])
    total_contratos = contratos['contrato_1']['monto'] + contratos['contrato_2']['monto']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("💰 Total Contratos", f"${total_contratos:,.0f}")
    
    with col2:
        st.metric("💵 Total Hitos", f"${total_ingresos:,.0f}")
    
    if abs(total_ingresos - total_contratos) > 1:  # Tolerancia de $1
        st.warning(f"⚠️ Diferencia detectada: ${abs(total_ingresos - total_contratos):,.0f}")
    else:
        st.success("✅ Los hitos suman correctamente el 100% de los contratos")
    
    # Botón continuar
    st.markdown("---")
    
    if st.button("▶️ Generar Proyección", type="primary", use_container_width=True):
        # Validar que todas las fases tengan duración
        if all([f['duracion_semanas'] for f in fases]):
            # fecha_inicio ya está en session_state desde el widget
            st.session_state.paso_fcl = 3
            st.rerun()
        else:
            st.error("❌ Por favor ingrese la duración de todas las fases")

# Continúo en el siguiente archivo debido al límite de longitud...
# ============================================================================
# CONTINUACIÓN DE proyeccion_fcl.py - PARTE 2
# Copiar este contenido al final del archivo proyeccion_fcl.py
# ============================================================================

# ============================================================================
# INTERFACE DE USUARIO - PASO 3: VISUALIZAR PROYECCIÓN
# ============================================================================

def render_paso_3_proyeccion():
    """Paso 3: Visualizar y analizar la proyección generada"""
    
    st.header("📊 Paso 3: Proyección de Flujo de Caja")
    
    # Botón volver
    if st.button("◀️ Volver a configuración"):
        st.session_state.paso_fcl = 2
        st.rerun()
    
    # Obtener datos de session_state
    cotizacion = st.session_state.cotizacion_fcl
    conceptos = st.session_state.conceptos_fcl
    fases = st.session_state.fases_config_fcl
    hitos = st.session_state.hitos_fcl
    contratos = st.session_state.contratos_fcl
    fecha_inicio = st.session_state.fecha_inicio_fcl
    
    # Calcular totales de AIU
    if 'totales_aiu_fcl' not in st.session_state:
        totales_aiu = obtener_totales_admin_imprevistos_logistica(cotizacion, conceptos)
        st.session_state.totales_aiu_fcl = totales_aiu
    else:
        totales_aiu = st.session_state.totales_aiu_fcl
    
    # Generar proyección
    if 'proyeccion_df' not in st.session_state:
        with st.spinner("Generando proyección..."):
            proyeccion_df = generar_proyeccion_completa(
                conceptos=conceptos,
                fases_config=fases,
                hitos=hitos,
                contrato_1=contratos['contrato_1'],
                contrato_2=contratos['contrato_2'],
                totales_aiu=totales_aiu,
                fecha_inicio=datetime.combine(fecha_inicio, datetime.min.time())
            )
            st.session_state.proyeccion_df = proyeccion_df
    else:
        proyeccion_df = st.session_state.proyeccion_df
    
    # KPIs principales
    st.subheader("📈 Indicadores Principales")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_ingresos = proyeccion_df['Ingresos_Proyectados'].sum()
    total_egresos = proyeccion_df['Total_Egresos'].sum()
    saldo_final = proyeccion_df['Saldo_Acumulado'].iloc[-1]
    semanas_total = len(proyeccion_df)
    
    with col1:
        st.metric("💰 Total Ingresos", f"${total_ingresos:,.0f}")
    
    with col2:
        st.metric("💸 Total Egresos", f"${total_egresos:,.0f}")
    
    with col3:
        st.metric("📊 Saldo Final", f"${saldo_final:,.0f}", 
                  delta=f"{(saldo_final/total_ingresos*100):.1f}%" if total_ingresos > 0 else "0%")
    
    with col4:
        st.metric("⏱️ Duración", f"{semanas_total} semanas", 
                  delta=f"{semanas_total/4:.1f} meses")
    
    st.markdown("---")
    
    # ========================================================================
    # ALERTAS DE SALDOS NEGATIVOS
    # ========================================================================
    
    saldo_minimo = proyeccion_df['Saldo_Acumulado'].min()
    
    if saldo_minimo < 0:
        semanas_negativas = proyeccion_df[proyeccion_df['Saldo_Acumulado'] < 0]
        primera_semana_deficit = semanas_negativas['Semana'].iloc[0]
        ultima_semana_deficit = semanas_negativas['Semana'].iloc[-1]
        
        st.error(f"""
        ⚠️ **ALERTA DE FLUJO DE CAJA**
        
        La proyección muestra **saldos negativos** en {len(semanas_negativas)} semanas del proyecto.
        
        - **Saldo más bajo:** ${saldo_minimo:,.0f}
        - **Primera semana afectada:** Semana {primera_semana_deficit}
        - **Última semana afectada:** Semana {ultima_semana_deficit}
        
        **Esto significa:**
        - El proyecto requiere financiamiento adicional temporal
        - Los hitos de pago no están sincronizados con los egresos
        - Se necesita capital de trabajo para cubrir el déficit
        
        **Soluciones sugeridas:**
        1. **Negociar hitos de pago intermedios** con el cliente
        2. **Ajustar el cronograma** para equilibrar ingresos/egresos
        3. **Considerar línea de crédito** por ${abs(saldo_minimo):,.0f}
        4. **Revisar distribución de conceptos** entre fases
        """)
        
        # Gráfica específica de déficit
        with st.expander("📊 Ver Análisis Detallado de Déficit", expanded=True):
            fig_deficit = go.Figure()
            
            # Saldo acumulado con relleno
            fig_deficit.add_trace(go.Scatter(
                x=proyeccion_df['Semana'],
                y=proyeccion_df['Saldo_Acumulado'],
                fill='tozeroy',
                fillcolor='rgba(239, 68, 68, 0.3)',
                line=dict(color='rgb(239, 68, 68)', width=3),
                name='Saldo Acumulado',
                hovertemplate='Semana %{x}<br>Saldo: $%{y:,.0f}<extra></extra>'
            ))
            
            # Línea en cero
            fig_deficit.add_hline(
                y=0, 
                line_dash="dash", 
                line_color="black",
                line_width=2,
                annotation_text="Línea de equilibrio",
                annotation_position="right"
            )
            
            # Resaltar zona de déficit
            fig_deficit.add_vrect(
                x0=primera_semana_deficit - 0.5,
                x1=ultima_semana_deficit + 0.5,
                fillcolor="rgba(255, 0, 0, 0.1)",
                line_width=0,
                annotation_text=f"Zona de Déficit ({len(semanas_negativas)} semanas)",
                annotation_position="top left"
            )
            
            fig_deficit.update_layout(
                title='Análisis de Saldo Acumulado - Identificación de Déficit',
                xaxis_title='Semana',
                yaxis_title='Saldo ($)',
                height=450,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_deficit, use_container_width=True)
            
            # Tabla de semanas críticas
            st.markdown("**Semanas con Saldo Negativo:**")
            semanas_criticas = proyeccion_df[proyeccion_df['Saldo_Acumulado'] < 0][
                ['Semana', 'Fecha', 'Fase', 'Ingresos_Proyectados', 'Total_Egresos', 
                 'Flujo_Neto', 'Saldo_Acumulado']
            ].copy()
            
            # Formatear montos
            for col in ['Ingresos_Proyectados', 'Total_Egresos', 'Flujo_Neto', 'Saldo_Acumulado']:
                semanas_criticas[col] = semanas_criticas[col].apply(lambda x: f"${x:,.0f}")
            
            st.dataframe(semanas_criticas, use_container_width=True, hide_index=True)
    else:
        st.success(f"""
        ✅ **FLUJO DE CAJA SALUDABLE**
        
        El proyecto mantiene saldo positivo durante toda la ejecución.
        
        - **Saldo mínimo:** ${saldo_minimo:,.0f}
        - **Saldo final:** ${saldo_final:,.0f}
        
        No se requiere financiamiento adicional en condiciones ideales.
        """)
    
    st.markdown("---")
    
    # Tabs para diferentes vistas
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Gráficas", 
        "📋 Tabla Detallada", 
        "💰 Análisis por Fase",
        "💾 Guardar"
    ])
    
    with tab1:
        render_graficas_proyeccion(proyeccion_df)
    
    with tab2:
        render_tabla_detallada(proyeccion_df)
    
    with tab3:
        render_analisis_fases(proyeccion_df, fases)
    
    with tab4:
        render_opciones_guardar(proyeccion_df, cotizacion)

def render_graficas_proyeccion(df: pd.DataFrame):
    """Renderiza gráficas de la proyección"""
    
    st.subheader("📈 Flujo de Caja Proyectado")
    
    # Gráfica 1: Ingresos vs Egresos vs Saldo
    fig1 = go.Figure()
    
    fig1.add_trace(go.Bar(
        x=df['Semana'],
        y=df['Ingresos_Proyectados'],
        name='Ingresos',
        marker_color='rgb(34, 197, 94)',
        hovertemplate='Semana %{x}<br>Ingresos: $%{y:,.0f}<extra></extra>'
    ))
    
    fig1.add_trace(go.Bar(
        x=df['Semana'],
        y=-df['Total_Egresos'],
        name='Egresos',
        marker_color='rgb(239, 68, 68)',
        hovertemplate='Semana %{x}<br>Egresos: $%{y:,.0f}<extra></extra>'
    ))
    
    fig1.add_trace(go.Scatter(
        x=df['Semana'],
        y=df['Saldo_Acumulado'],
        name='Saldo Acumulado',
        mode='lines+markers',
        line=dict(color='rgb(59, 130, 246)', width=3),
        marker=dict(size=6),
        yaxis='y2',
        hovertemplate='Semana %{x}<br>Saldo: $%{y:,.0f}<extra></extra>'
    ))
    
    fig1.update_layout(
        title='Ingresos, Egresos y Saldo Acumulado',
        xaxis_title='Semana',
        yaxis_title='Monto ($)',
        yaxis2=dict(
            title='Saldo Acumulado ($)',
            overlaying='y',
            side='right'
        ),
        hovermode='x unified',
        height=500,
        barmode='relative'
    )
    
    st.plotly_chart(fig1, use_container_width=True)
    
    # Gráfica 2: Composición de Egresos por Categoría
    st.subheader("📊 Composición de Egresos")
    
    fig2 = go.Figure()
    
    categorias = ['Materiales', 'Equipos', 'Mano_Obra', 'Admin', 'Imprevistos', 'Logistica']
    colores = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#6366f1']
    
    for cat, color in zip(categorias, colores):
        fig2.add_trace(go.Bar(
            x=df['Semana'],
            y=df[cat],
            name=cat.replace('_', ' '),
            marker_color=color,
            hovertemplate='%{y:,.0f}<extra></extra>'
        ))
    
    fig2.update_layout(
        title='Distribución de Egresos por Categoría',
        xaxis_title='Semana',
        yaxis_title='Monto ($)',
        barmode='stack',
        hovermode='x unified',
        height=500
    )
    
    st.plotly_chart(fig2, use_container_width=True)
    
    # Gráfica 3: Torta de Egresos Totales
    st.subheader("🥧 Distribución Total de Egresos")
    
    totales_cat = {
        'Materiales': df['Materiales'].sum(),
        'Equipos': df['Equipos'].sum(),
        'Mano de Obra': df['Mano_Obra'].sum(),
        'Administración': df['Admin'].sum(),
        'Imprevistos': df['Imprevistos'].sum(),
        'Logística': df['Logistica'].sum()
    }
    
    fig3 = go.Figure(data=[go.Pie(
        labels=list(totales_cat.keys()),
        values=list(totales_cat.values()),
        hole=0.4,
        marker=dict(colors=colores),
        hovertemplate='%{label}<br>$%{value:,.0f}<br>%{percent}<extra></extra>'
    )])
    
    fig3.update_layout(
        title='Distribución Total por Categoría de Egreso',
        height=500
    )
    
    st.plotly_chart(fig3, use_container_width=True)

def render_tabla_detallada(df: pd.DataFrame):
    """Renderiza tabla detallada de la proyección"""
    
    st.subheader("📋 Proyección Detallada por Semana")
    
    # Opciones de filtrado
    col1, col2 = st.columns(2)
    
    with col1:
        fases_unicas = df['Fase'].unique()
        fase_filtro = st.multiselect(
            "Filtrar por fase:",
            options=fases_unicas,
            default=fases_unicas,
            key="filtro_fase_tabla"
        )
    
    with col2:
        mostrar_solo_ingresos = st.checkbox(
            "Mostrar solo semanas con ingresos",
            value=False,
            key="filtro_ingresos"
        )
    
    # Aplicar filtros
    df_filtrado = df[df['Fase'].isin(fase_filtro)].copy()
    
    if mostrar_solo_ingresos:
        df_filtrado = df_filtrado[df_filtrado['Ingresos_Proyectados'] > 0]
    
    # Formatear columnas para display
    df_display = df_filtrado.copy()
    
    columnas_moneda = [
        'Ingresos_Proyectados', 'Materiales', 'Equipos', 'Mano_Obra',
        'Admin', 'Imprevistos', 'Logistica', 'Total_Egresos', 
        'Flujo_Neto', 'Saldo_Acumulado'
    ]
    
    for col in columnas_moneda:
        df_display[col] = df_display[col].apply(lambda x: f"${x:,.0f}")
    
    # Renombrar columnas para mejor presentación
    df_display = df_display.rename(columns={
        'Ingresos_Proyectados': 'Ingresos',
        'Mano_Obra': 'Mano de Obra',
        'Admin': 'Administración',
        'Logistica': 'Logística',
        'Total_Egresos': 'Total Egresos',
        'Flujo_Neto': 'Flujo Neto',
        'Saldo_Acumulado': 'Saldo Acum.'
    })
    
    # Mostrar tabla
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=600
    )
    
    # Botón de descarga
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar CSV",
        data=csv,
        file_name=f"proyeccion_fcl_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

def render_analisis_fases(df: pd.DataFrame, fases: List[Dict]):
    """Renderiza análisis detallado por fase"""
    
    st.subheader("💰 Análisis Financiero por Fase")
    
    for fase in fases:
        if not fase['duracion_semanas']:
            continue
        
        # Filtrar datos de esta fase
        df_fase = df[df['Fase'] == fase['nombre']]
        
        if len(df_fase) == 0:
            continue
        
        with st.expander(f"📊 {fase['nombre']} ({fase['duracion_semanas']} semanas)", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            total_ingresos_fase = df_fase['Ingresos_Proyectados'].sum()
            total_egresos_fase = df_fase['Total_Egresos'].sum()
            flujo_neto_fase = total_ingresos_fase - total_egresos_fase
            
            with col1:
                st.metric("💰 Ingresos", f"${total_ingresos_fase:,.0f}")
            
            with col2:
                st.metric("💸 Egresos", f"${total_egresos_fase:,.0f}")
            
            with col3:
                st.metric("📊 Flujo Neto", f"${flujo_neto_fase:,.0f}")
            
            with col4:
                promedio_semanal = total_egresos_fase / len(df_fase)
                st.metric("📉 Egreso Semanal Prom.", f"${promedio_semanal:,.0f}")
            
            # Desglose de egresos
            st.markdown("**Desglose de Egresos:**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"• Materiales: ${df_fase['Materiales'].sum():,.0f}")
                st.write(f"• Equipos: ${df_fase['Equipos'].sum():,.0f}")
            
            with col2:
                st.write(f"• Mano de Obra: ${df_fase['Mano_Obra'].sum():,.0f}")
                st.write(f"• Administración: ${df_fase['Admin'].sum():,.0f}")
            
            with col3:
                st.write(f"• Imprevistos: ${df_fase['Imprevistos'].sum():,.0f}")
                st.write(f"• Logística: ${df_fase['Logistica'].sum():,.0f}")
            
            # Conceptos incluidos
            st.markdown("**Conceptos incluidos:**")
            for concepto in fase['conceptos']:
                st.write(f"✓ {concepto}")

def render_opciones_guardar(df: pd.DataFrame, cotizacion: dict):
    """Renderiza opciones para guardar la proyección"""
    
    st.subheader("💾 Guardar Proyección")
    
    st.info("""
    💡 **Próximos pasos:** 
    - La proyección se guardará en la base de datos para uso en módulos de ejecución y análisis
    - Podrá comparar esta proyección con la ejecución real del proyecto
    - Los datos se vincularán al proyecto seleccionado
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        nombre_proyeccion = st.text_input(
            "Nombre de la proyección:",
            value=f"Proyección {cotizacion['proyecto']['nombre']} - {datetime.now().strftime('%Y-%m-%d')}",
            key="nombre_proyeccion"
        )
    
    with col2:
        notas = st.text_area(
            "Notas (opcional):",
            placeholder="Ej: Proyección inicial, versión 1.0, etc.",
            key="notas_proyeccion"
        )
    
    if st.button("💾 Guardar Proyección en Base de Datos", type="primary", use_container_width=True):
        try:
            # Guardar en BD
            conn = sqlite3.connect('sicone.db')
            cursor = conn.cursor()
            
            # Verificar si tabla existe, si no, crearla
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS proyecciones_fcl (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proyecto_id INTEGER,
                    nombre TEXT NOT NULL,
                    datos_json TEXT NOT NULL,
                    fecha_creacion TEXT NOT NULL,
                    notas TEXT,
                    semanas_total INTEGER,
                    total_ingresos REAL,
                    total_egresos REAL,
                    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id)
                )
            """)
            
            # Preparar datos para guardar
            proyeccion_json = df.to_json(orient='records', date_format='iso')
            
            # Insertar en tabla
            cursor.execute("""
                INSERT INTO proyecciones_fcl 
                (proyecto_id, nombre, datos_json, fecha_creacion, notas, semanas_total, total_ingresos, total_egresos)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                st.session_state.get('proyecto_fcl_id'),
                nombre_proyeccion,
                proyeccion_json,
                datetime.now().isoformat(),
                notas,
                len(df),
                float(df['Ingresos_Proyectados'].sum()),
                float(df['Total_Egresos'].sum())
            ))
            
            conn.commit()
            conn.close()
            
            st.success("✅ Proyección guardada correctamente en la base de datos")
            st.balloons()
            
        except sqlite3.Error as e:
            st.error(f"❌ Error al guardar: {e}")
    
    st.markdown("---")
    
    # Opciones de exportación
    st.markdown("### 📤 Exportar Datos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Exportar CSV
        # Obtener nombre del proyecto y limpiarlo
        nombre_proyecto = cotizacion.get('proyecto', {}).get('nombre', 'proyecto')
        nombre_limpio = nombre_proyecto.replace(' ', '_').replace('/', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f"{nombre_limpio}_proyeccion_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Exportar JSON
        json_str = df.to_json(orient='records', date_format='iso', indent=2)
        st.download_button(
            label="📥 Descargar JSON",
            data=json_str,
            file_name=f"{nombre_limpio}_proyeccion_{timestamp}.json",
            mime="application/json",
            use_container_width=True
        )

# ============================================================================
# FUNCIÓN PRINCIPAL DEL MÓDULO
# ============================================================================

def main():
    """
    Función principal del módulo de Proyección FCL
    """
    
    # Inicializar session_state
    if 'paso_fcl' not in st.session_state:
        st.session_state.paso_fcl = 1
    
    # Router de pasos
    if st.session_state.paso_fcl == 1:
        render_paso_1_cargar_cotizacion()
    
    elif st.session_state.paso_fcl == 2:
        render_paso_2_configurar_proyecto()
    
    elif st.session_state.paso_fcl == 3:
        render_paso_3_proyeccion()
    
    else:
        st.error("Error: Paso no válido")
        st.session_state.paso_fcl = 1

# ============================================================================
# EJECUCIÓN
# ============================================================================

# main() disponible para importación

