"""
SICONE - Módulo de Ejecución Real FCL
Análisis de FCL Real Ejecutado vs FCL Planeado

Versión: 1.1.0 (Beta)
Fecha: Diciembre 2024
Autor: AI-MindNovation

ESTRUCTURA MODULAR:
└── ejecucion_fcl.py
    ├── Módulo 1: CARTERA (Ingresos Reales) ✅
    │   ├── Ingreso de cobros por hito
    │   ├── Conciliación automática
    │   ├── Comparación ingresos proyectados vs reales
    │   └── Alertas de cartera
    │
    ├── Módulo 2: EGRESOS REALES ✅
    │   ├── Parser automático de Excel contable
    │   ├── Clasificación de cuentas (Materiales, MO, Variables, Admin)
    │   ├── Agrupación semanal de gastos
    │   ├── Comparación egresos proyectados vs reales
    │   └── Análisis por categoría
    │
    └── Módulo 3: ANÁLISIS FCL COMPLETO (Futuro - Fase 3) 🔜
        ├── Dashboard consolidado (ingresos + egresos)
        ├── Flujo de caja real completo
        ├── Alertas integradas
        └── Exportación JSON v4.0

FUNCIONALIDADES ACTUALES (v1.1.0 Beta):
- ✅ Carga de proyección desde JSON v2.0
- ✅ Ingreso de datos de cartera (hitos + pagos reales)
- ✅ Conciliación automática (detecta sobrepagos, retenciones, etc.)
- ✅ Comparación ingresos proyectados vs reales
- ✅ Generación de alertas de cartera
- ✅ Dashboard de análisis de ingresos
- ✅ Parser automático de Excel de ejecución contable
- ✅ Clasificación automática de cuentas (34 cuentas mapeadas)
- ✅ Agrupación de gastos por semana y categoría
- ✅ Soporte para archivos acumulados anuales
- ✅ Consolidación de múltiples archivos (2 años)
- ✅ Comparación rápida vs proyección por categoría
- ✅ Exportación JSON v3.0 (proyección + cartera)
- 🔜 Dashboard de análisis de egresos (Paso 5)
- 🔜 Análisis FCL completo (Paso 6)

ROADMAP:
- v1.0.0: Módulo Cartera (ingresos) ✅
- v1.1.0: Módulo Egresos (ingreso/parser) ✅
- v1.2.0: Análisis de Egresos completo (dashboard) 🔜
- v1.3.0: Análisis FCL completo (ingresos + egresos) 🔜
- v1.4.0: Dashboard consolidado multiproyectos 🔜
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
import plotly.graph_objects as go
import plotly.express as px

# ============================================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================================

st.set_page_config(
    page_title="SICONE - Ejecución Real FCL",
    page_icon="💼",
    layout="wide"
)

# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def calcular_semana_desde_fecha(fecha_inicio: date, fecha_evento: date) -> int:
    """Calcula en qué semana del proyecto ocurrió un evento"""
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.fromisoformat(fecha_inicio).date()
    if isinstance(fecha_evento, str):
        fecha_evento = datetime.fromisoformat(fecha_evento).date()
    
    dias_transcurridos = (fecha_evento - fecha_inicio).days
    return max(1, (dias_transcurridos // 7) + 1)


def formatear_moneda(valor: float) -> str:
    """Formatea un valor como moneda colombiana"""
    return f"${valor:,.0f}"


def calcular_porcentaje(parte: float, total: float) -> float:
    """Calcula porcentaje de forma segura"""
    return (parte / total * 100) if total > 0 else 0


def mostrar_boton_cargar_otra_proyeccion():
    """
    Muestra botón para cargar otra proyección en cualquier paso
    Se muestra en el header de cada paso
    """
    if 'proyeccion_cartera' in st.session_state:
        with st.expander("🔄 Cargar Otra Proyección", expanded=False):
            st.warning("""
            ⚠️ **Advertencia:** 
            Al cargar otra proyección se perderán todos los datos no guardados del proyecto actual.
            Asegúrese de exportar el JSON antes de continuar.
            """)
            
            if st.button("🗑️ Confirmar y Cargar Nuevo Proyecto", type="secondary", use_container_width=True):
                # Limpiar todos los datos del proyecto actual
                keys_to_delete = [
                    'proyeccion_cartera',
                    'pagos_por_hito',
                    'contratos_cartera_input',
                    'widget_fecha_corte_cartera',
                    'hitos_expandidos_cartera',
                    'egresos_reales_input'
                ]
                
                for key in keys_to_delete:
                    if key in st.session_state:
                        del st.session_state[key]
                
                # Regresar al paso 1
                st.session_state.paso_ejecucion = 1
                st.rerun()


# ============================================================================
# TABLA DE CLASIFICACIÓN DE CUENTAS CONTABLES
# ============================================================================

TABLA_CLASIFICACION_CUENTAS = {
    "Aporte a fondos de pensión y/o cesantías": "Mano de Obra",
    "Aportes a administradora de riesgos laborales": "Mano de Obra",
    "Aportes cajas de compensación familiar": "Mano de Obra",
    "Auxilio de transporte": "Mano de Obra",
    "Bonificaciones no constitutivas": "Mano de Obra",
    "Casino y Restaurante": "Variables",
    "Cesantías": "Mano de Obra",
    "Combustibles (Acpm - Gasolina)": "Variables",
    "Costos indirectos": "Variables",
    "Costos no deducibles sin seguridad social": "Variables",
    "Costos sin factura electrónica": "Variables",
    "Dotación y suministro a trabajadores": "Mano de Obra",
    "Elementos de Aseo en General": "Variables",
    "Garantía de Cumplimiento": "Administracion",
    "Herramientas": "Variables",
    "Honorarios de Topografo": "Mano de Obra",
    "Honorarios Estudio de Suelos, Pavimentos, Concreto": "Mano de Obra",
    "Horas extras y recargos": "Mano de Obra",
    "Ingeniero Residente de Obra": "Mano de Obra",
    "Intereses sobre cesantías": "Administracion",
    "Materiales de Operación": "Materiales",
    "Prima de servicios": "Mano de Obra",
    "Servicios de Construcción": "Variables",
    "Sueldos": "Mano de Obra",
    "Transporte en bus o taxi": "Variables",
    "Transportes de Materiales": "Materiales",
    "Útiles, papelería y Fotocopias": "Variables",
    "Vacaciones": "Mano de Obra",
    "Materia prima": "Materiales",
    "Incapacidades": "Mano de Obra",
    "Servicio de Metalmecanica": "Variables",
    "Herramientas y otros": "Variables",
    "Parqueaderos": "Administracion",
    "Costos No deducibles no cumple requisitos Factura": "Administracion"
}

# Mapeo de categorías ejecución a proyección
MAPEO_CATEGORIAS_EJECUCION_PROYECCION = {
    "Materiales": "Materiales",
    "Mano de Obra": "Mano_Obra",
    "Variables": "Variables",  # Agrupa: Equipos + Imprevistos + Logistica
    "Administracion": "Admin"
}


# ============================================================================
# FUNCIONES DE CONCILIACIÓN
# ============================================================================

def conciliar_hito(hito: Dict) -> Dict:
    """
    Concilia pagos de un hito y determina su estado
    
    Returns:
        Dict con estado, desviación, alertas, etc.
    """
    monto_esperado = hito.get('monto_esperado', 0)
    pagos = hito.get('pagos', [])
    monto_pagado = sum([p.get('monto', 0) for p in pagos])
    
    desviacion = monto_pagado - monto_esperado
    pct_desviacion = calcular_porcentaje(desviacion, monto_esperado)
    
    # Determinar estado
    if monto_pagado == 0:
        estado = 'pendiente'
        severidad = 'media'
        emoji = '🔴'
    elif abs(pct_desviacion) <= 1:  # ±1%
        estado = 'pagado_completo'
        severidad = 'ok'
        emoji = '✅'
    elif pct_desviacion > 1:  # Sobrepago
        estado = 'sobrepago'
        severidad = 'media'
        emoji = '⚠️'
    elif pct_desviacion < -15:  # Retención significativa
        estado = 'retencion'
        severidad = 'media'
        emoji = '⚠️'
    else:  # Pago parcial
        estado = 'pago_parcial'
        severidad = 'alta'
        emoji = '🔶'
    
    # Generar mensaje de alerta
    alerta = None
    if estado == 'sobrepago':
        alerta = f"Sobrepago de {formatear_moneda(abs(desviacion))} ({pct_desviacion:.1f}%)"
    elif estado == 'retencion':
        alerta = f"Posible retención de {formatear_moneda(abs(desviacion))} ({abs(pct_desviacion):.1f}%)"
    elif estado == 'pago_parcial':
        pendiente = monto_esperado - monto_pagado
        pct_pagado = calcular_porcentaje(monto_pagado, monto_esperado)
        alerta = f"Pendiente {formatear_moneda(pendiente)} ({100-pct_pagado:.1f}%)"
    
    return {
        'estado': estado,
        'severidad': severidad,
        'emoji': emoji,
        'monto_esperado': monto_esperado,
        'monto_pagado': monto_pagado,
        'desviacion': desviacion,
        'pct_desviacion': pct_desviacion,
        'alerta': alerta
    }


def generar_alertas_cartera(contratos_cartera: List[Dict], proyeccion_df: pd.DataFrame, 
                            fecha_corte: date, semana_actual: int) -> List[Dict]:
    """
    Genera lista de alertas basadas en el estado de la cartera
    """
    alertas = []
    
    for contrato in contratos_cartera:
        for hito in contrato.get('hitos', []):
            conciliacion = conciliar_hito(hito)
            
            # Alerta de pago vencido
            fecha_venc = hito.get('fecha_vencimiento')
            if fecha_venc and conciliacion['estado'] in ['pendiente', 'pago_parcial']:
                if isinstance(fecha_venc, str):
                    fecha_venc = datetime.fromisoformat(fecha_venc).date()
                
                dias_vencido = (fecha_corte - fecha_venc).days
                if dias_vencido > 0:
                    alertas.append({
                        'tipo': 'pago_vencido',
                        'severidad': 'alta',
                        'emoji': '🔴',
                        'descripcion': f"Hito '{hito.get('descripcion')}' vencido hace {dias_vencido} días",
                        'monto': conciliacion['monto_esperado'] - conciliacion['monto_pagado'],
                        'dias_vencido': dias_vencido,
                        'contrato': contrato.get('numero')
                    })
            
            # Alerta de retención
            if conciliacion['estado'] == 'retencion':
                alertas.append({
                    'tipo': 'retencion_detectada',
                    'severidad': 'media',
                    'emoji': '⚠️',
                    'descripcion': f"Posible retención en '{hito.get('descripcion')}'",
                    'pct': abs(conciliacion['pct_desviacion']),
                    'monto': abs(conciliacion['desviacion']),
                    'contrato': contrato.get('numero')
                })
            
            # Alerta de hito pendiente en etapa pasada
            semana_esperada = hito.get('semana_esperada', 0)
            if semana_esperada < semana_actual and conciliacion['estado'] == 'pendiente':
                alertas.append({
                    'tipo': 'hito_atrasado',
                    'severidad': 'alta',
                    'emoji': '🔶',
                    'descripcion': f"Hito '{hito.get('descripcion')}' sin cobrar (sem {semana_esperada}, actual {semana_actual})",
                    'monto': conciliacion['monto_esperado'],
                    'semanas_atraso': semana_actual - semana_esperada,
                    'contrato': contrato.get('numero')
                })
    
    return alertas


# ============================================================================
# FUNCIONES DE VISUALIZACIÓN
# ============================================================================

def render_kpis_principales(resumen: Dict):
    """Renderiza KPIs principales de cartera"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Contratado",
            formatear_moneda(resumen['total_contratado'])
        )
    
    with col2:
        st.metric(
            "Total Cobrado",
            formatear_moneda(resumen['total_cobrado']),
            delta=f"{resumen['pct_cobrado']:.1f}%"
        )
    
    with col3:
        pendiente = resumen['total_pendiente']
        pct_pendiente = 100 - resumen['pct_cobrado']
        st.metric(
            "Pendiente por Cobrar",
            formatear_moneda(pendiente),
            delta=f"-{pct_pendiente:.1f}%",
            delta_color="inverse"
        )
    
    with col4:
        # Estado general
        if resumen['pct_cobrado'] >= 90:
            st.metric("Estado", "🟢 Excelente", delta=f"{resumen['pct_cobrado']:.0f}%")
        elif resumen['pct_cobrado'] >= 70:
            st.metric("Estado", "🟡 Bueno", delta=f"{resumen['pct_cobrado']:.0f}%")
        else:
            st.metric("Estado", "🔴 Atención", delta=f"{resumen['pct_cobrado']:.0f}%")


def render_grafica_proyeccion_vs_real(proyeccion_df: pd.DataFrame, cartera: Dict, 
                                      semana_actual: int):
    """Renderiza gráfica comparativa de proyección vs cobros reales"""
    
    fig = go.Figure()
    
    # Ingresos proyectados (acumulados)
    ingresos_acum = proyeccion_df['Ingresos_Proyectados'].cumsum()
    
    fig.add_trace(go.Scatter(
        x=proyeccion_df['Semana'],
        y=ingresos_acum,
        name='Ingresos Proyectados',
        line=dict(color='blue', dash='dash', width=2),
        hovertemplate='Sem %{x}<br>Proyectado: $%{y:,.0f}<extra></extra>'
    ))
    
    # Calcular cobros reales acumulados por semana
    fecha_inicio = datetime.fromisoformat(cartera['fecha_inicio']).date()
    semanas_range = range(1, len(proyeccion_df) + 1)
    cobros_por_semana = {sem: 0 for sem in semanas_range}
    
    for contrato in cartera['contratos_cartera']:
        for hito in contrato['hitos']:
            for pago in hito.get('pagos', []):
                fecha_pago = pago['fecha']
                if isinstance(fecha_pago, str):
                    fecha_pago = datetime.fromisoformat(fecha_pago).date()
                
                semana_pago = calcular_semana_desde_fecha(fecha_inicio, fecha_pago)
                if semana_pago in cobros_por_semana:
                    cobros_por_semana[semana_pago] += pago['monto']
    
    # Acumular cobros
    cobros_acumulados = []
    acum = 0
    for sem in semanas_range:
        acum += cobros_por_semana[sem]
        cobros_acumulados.append(acum)
    
    # Cobros reales (solo hasta semana actual)
    semanas_reales = list(range(1, min(semana_actual + 1, len(proyeccion_df) + 1)))
    cobros_reales = cobros_acumulados[:len(semanas_reales)]
    
    fig.add_trace(go.Scatter(
        x=semanas_reales,
        y=cobros_reales,
        name='Cobros Reales',
        line=dict(color='green', width=3),
        hovertemplate='Sem %{x}<br>Cobrado: $%{y:,.0f}<extra></extra>'
    ))
    
    # Línea vertical en semana actual
    fig.add_vline(
        x=semana_actual,
        line_dash="dot",
        line_color="red",
        annotation_text="Semana Actual",
        annotation_position="top"
    )
    
    # Área de proyección futura
    fig.add_vrect(
        x0=semana_actual, x1=len(proyeccion_df),
        fillcolor="gray", opacity=0.1,
        layer="below", line_width=0,
        annotation_text="Proyección", annotation_position="top right"
    )
    
    fig.update_layout(
        title="📈 Comparación: Ingresos Proyectados vs Cobros Reales (Acumulados)",
        xaxis_title="Semana del Proyecto",
        yaxis_title="Monto Acumulado (COP)",
        hovermode='x unified',
        height=500,
        showlegend=True,
        legend=dict(x=0.02, y=0.98)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_tabla_alertas(alertas: List[Dict]):
    """Renderiza tabla de alertas activas"""
    if not alertas:
        st.success("✅ No hay alertas activas")
        return
    
    st.warning(f"⚠️ **{len(alertas)} Alertas Activas**")
    
    for alerta in alertas:
        with st.expander(f"{alerta['emoji']} {alerta['descripcion']}", expanded=True):
            cols = st.columns([2, 1, 1])
            
            with cols[0]:
                st.write(f"**Tipo:** {alerta['tipo'].replace('_', ' ').title()}")
                if 'contrato' in alerta:
                    st.write(f"**Contrato:** {alerta['contrato']}")
            
            with cols[1]:
                if 'monto' in alerta:
                    st.metric("Monto", formatear_moneda(alerta['monto']))
            
            with cols[2]:
                if 'dias_vencido' in alerta:
                    st.metric("Días Vencido", alerta['dias_vencido'])
                elif 'semanas_atraso' in alerta:
                    st.metric("Semanas Atraso", alerta['semanas_atraso'])
                elif 'pct' in alerta:
                    st.metric("Porcentaje", f"{alerta['pct']:.1f}%")


# ============================================================================
# FUNCIONES DE PARSER DE EGRESOS REALES
# ============================================================================

def validar_excel_egresos(archivo) -> Tuple[bool, str]:
    """
    Valida estructura del archivo Excel de egresos
    Detecta automáticamente hojas con nombre "AÑO XXXX"
    
    Returns:
        (es_valido, mensaje_error)
    """
    try:
        # Leer nombres de hojas
        xls = pd.ExcelFile(archivo)
        todas_las_hojas = xls.sheet_names
        
        # Detectar hojas de años (formato "AÑO 2024", "AÑO 2025", etc.)
        hojas_anio = [h for h in todas_las_hojas if h.startswith('AÑO ')]
        
        if not hojas_anio:
            return False, f"""
            ❌ **No se encontraron hojas de ejecución válidas**
            
            **Hojas detectadas en el archivo:**
            {', '.join(todas_las_hojas)}
            
            **Formato esperado:** Las hojas deben nombrarse como "AÑO 2024", "AÑO 2025", etc.
            
            💡 **Sugerencia:** Verifique que las hojas de ejecución estén correctamente nombradas.
            """
        
        # Validar estructura de cada hoja
        hojas_validas = []
        hojas_invalidas = []
        
        for hoja_nombre in hojas_anio:
            # Intentar con diferentes filas de encabezado
            encabezados_posibles = [7, 6, 8, 9]
            df = None
            header_usado = None
            
            for header_row in encabezados_posibles:
                try:
                    df_temp = pd.read_excel(archivo, sheet_name=hoja_nombre, header=header_row)
                    
                    # Verificar columnas clave
                    columnas_clave = ['Código contable', 'Cuenta contable', 'Débito']
                    coincidencias = sum(1 for col in columnas_clave if col in df_temp.columns)
                    
                    if coincidencias >= 2:  # Al menos 2 de 3
                        df = df_temp
                        header_usado = header_row
                        break
                except:
                    continue
            
            if df is None:
                hojas_invalidas.append(hoja_nombre)
                continue
            
            # Verificar columnas esenciales
            columnas_requeridas = ['Código contable', 'Cuenta contable', 
                                  'Fecha elaboración', 'Débito']
            columnas_encontradas = [col for col in columnas_requeridas if col in df.columns]
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            
            if columnas_faltantes:
                hojas_invalidas.append(f"{hoja_nombre} (faltan: {', '.join(columnas_faltantes)})")
                continue
            
            # Verificar que hay datos
            df_trans = df[df['Código contable'].notna()]
            df_trans = df_trans[~df_trans['Código contable'].astype(str).str.startswith('Procesado')]
            
            if len(df_trans) == 0:
                hojas_invalidas.append(f"{hoja_nombre} (sin registros)")
                continue
            
            # Hoja válida
            hojas_validas.append({
                'nombre': hoja_nombre,
                'header': header_usado,
                'registros': len(df_trans)
            })
        
        if not hojas_validas:
            detalles_invalidas = '\n            '.join([f"• {h}" for h in hojas_invalidas])
            return False, f"""
            ❌ **Ninguna hoja pasó la validación**
            
            **Hojas detectadas con problemas:**
            {detalles_invalidas}
            
            💡 **Verifique que las hojas tengan la estructura correcta de ejecución contable.**
            """
        
        # Mensaje de éxito
        detalles_validas = '\n            '.join([
            f"• {h['nombre']}: {h['registros']} registros (encabezados en fila {h['header'] + 1})"
            for h in hojas_validas
        ])
        
        mensaje_exito = f"""✅ **Archivo válido**
            
            **Hojas procesables ({len(hojas_validas)}):**
            {detalles_validas}
            """
        
        if hojas_invalidas:
            detalles_invalidas = '\n            '.join([f"• {h}" for h in hojas_invalidas])
            mensaje_exito += f"""
            
            ⚠️ **Hojas omitidas ({len(hojas_invalidas)}):**
            {detalles_invalidas}
            """
        
        return True, mensaje_exito
        
    except Exception as e:
        return False, f"Error al leer archivo: {str(e)}"
        
        if len(df_trans) == 0:
            return False, "El archivo no contiene registros transaccionales"
        
        return True, "Archivo válido"
        
    except Exception as e:
        return False, f"Error al leer archivo: {str(e)}"


def parse_excel_egresos(
    archivo,
    fecha_inicio_proyecto: date,
    nombre_centro_costo: str = None
) -> Dict:
    """
    Parsea archivo Excel de ejecución contable con múltiples hojas (años)
    Detecta automáticamente hojas "AÑO XXXX" y procesa todas
    
    Args:
        archivo: UploadedFile de Streamlit
        fecha_inicio_proyecto: Fecha de inicio del proyecto
        nombre_centro_costo: Filtrar por centro de costo específico (opcional)
    
    Returns:
        Dict con:
            - archivo: nombre del archivo
            - hojas_procesadas: lista de hojas procesadas
            - fecha_proceso: fecha de procesamiento
            - semana_ultima: última semana con datos
            - periodo_covered: rango de fechas
            - registros_procesados: cantidad total de registros
            - egresos_semanales: lista de dict por semana (consolidado)
            - totales_acumulados: dict con totales por categoría
            - cuentas_sin_clasificar: lista de cuentas no mapeadas
    """
    try:
        # Detectar hojas de años
        xls = pd.ExcelFile(archivo)
        todas_las_hojas = xls.sheet_names
        hojas_anio = [h for h in todas_las_hojas if h.startswith('AÑO ')]
        
        if not hojas_anio:
            st.error("❌ No se encontraron hojas con formato 'AÑO XXXX'")
            return None
        
        st.info(f"📊 Detectadas {len(hojas_anio)} hoja(s): {', '.join(hojas_anio)}")
        
        # Procesar cada hoja
        todos_egresos_semanales = {}  # {semana: {materiales: X, mano_obra: Y, ...}}
        todos_registros = 0
        todas_cuentas_sin_clasificar = set()
        primera_fecha_global = None
        ultima_fecha_global = None
        hojas_procesadas_info = []
        
        for hoja_nombre in sorted(hojas_anio):
            st.caption(f"   Procesando {hoja_nombre}...")
            
            # Detectar fila de encabezado para esta hoja
            encabezados_posibles = [7, 6, 8, 9]
            df = None
            
            for header_row in encabezados_posibles:
                try:
                    df_temp = pd.read_excel(archivo, sheet_name=hoja_nombre, header=header_row)
                    
                    # Verificar columnas clave
                    columnas_clave = ['Código contable', 'Cuenta contable', 'Débito']
                    if all(col in df_temp.columns for col in columnas_clave):
                        df = df_temp
                        break
                except:
                    continue
            
            if df is None:
                st.warning(f"   ⚠️ No se pudo procesar {hoja_nombre}, se omite")
                continue
            
            # Filtrar datos transaccionales
            df_trans = df[df['Código contable'].notna()].copy()
            df_trans = df_trans[~df_trans['Código contable'].astype(str).str.startswith('Procesado')]
            
            # Filtrar por centro de costo si se especifica
            if nombre_centro_costo and 'Centro de costo' in df_trans.columns:
                df_trans = df_trans[
                    df_trans['Centro de costo'].str.contains(nombre_centro_costo, case=False, na=False)
                ]
            
            if len(df_trans) == 0:
                st.warning(f"   ⚠️ {hoja_nombre} no tiene registros válidos")
                continue
            
            # Mapear cuentas a categorías
            df_trans['Categoria'] = df_trans['Cuenta contable'].map(TABLA_CLASIFICACION_CUENTAS)
            
            # Acumular cuentas sin clasificar (para reportarlas)
            cuentas_sin_clasificar_hoja = df_trans[df_trans['Categoria'].isna()]['Cuenta contable'].unique().tolist()
            todas_cuentas_sin_clasificar.update(cuentas_sin_clasificar_hoja)
            
            # NO descartar registros sin clasificar, asignarlos a categoría "Sin Clasificar"
            df_trans['Categoria'] = df_trans['Categoria'].fillna('Sin Clasificar')
            df_clasificado = df_trans.copy()
            
            if len(df_clasificado) == 0:
                st.warning(f"   ⚠️ {hoja_nombre}: no tiene registros válidos")
                continue
            
            # Convertir fecha a datetime con formato DD/MM/YYYY (europeo/colombiano)
            df_clasificado['Fecha elaboración'] = pd.to_datetime(
                df_clasificado['Fecha elaboración'], 
                format='%d/%m/%Y',
                errors='coerce'
            )
            
            # Actualizar fechas globales
            primera_fecha_hoja = df_clasificado['Fecha elaboración'].min()
            ultima_fecha_hoja = df_clasificado['Fecha elaboración'].max()
            
            if primera_fecha_global is None or primera_fecha_hoja < primera_fecha_global:
                primera_fecha_global = primera_fecha_hoja
            if ultima_fecha_global is None or ultima_fecha_hoja > ultima_fecha_global:
                ultima_fecha_global = ultima_fecha_hoja
            
            # Calcular semana del proyecto
            df_clasificado['Semana'] = df_clasificado['Fecha elaboración'].apply(
                lambda x: calcular_semana_desde_fecha(fecha_inicio_proyecto, x.date()) 
                if pd.notna(x) else None
            )
            
            # Agrupar por semana y categoría
            df_agrupado = df_clasificado.groupby(['Semana', 'Categoria'])['Débito'].sum().reset_index()
            
            # Consolidar en diccionario global
            for _, row in df_agrupado.iterrows():
                semana = int(row['Semana'])
                categoria = row['Categoria']
                monto = float(row['Débito'])
                
                if semana not in todos_egresos_semanales:
                    todos_egresos_semanales[semana] = {
                        'semana': semana,
                        'materiales': 0,
                        'mano_obra': 0,
                        'variables': 0,
                        'admin': 0,
                        'sin_clasificar': 0
                    }
                
                # Mapear categoría
                if categoria == 'Materiales':
                    todos_egresos_semanales[semana]['materiales'] += monto
                elif categoria == 'Mano de Obra':
                    todos_egresos_semanales[semana]['mano_obra'] += monto
                elif categoria == 'Variables':
                    todos_egresos_semanales[semana]['variables'] += monto
                elif categoria == 'Administracion':
                    todos_egresos_semanales[semana]['admin'] += monto
                elif categoria == 'Sin Clasificar':
                    todos_egresos_semanales[semana]['sin_clasificar'] += monto
            
            todos_registros += len(df_clasificado)
            
            # Info de hoja procesada
            hojas_procesadas_info.append({
                'nombre': hoja_nombre,
                'registros': len(df_clasificado),
                'periodo': f"{primera_fecha_hoja.strftime('%Y-%m-%d')} a {ultima_fecha_hoja.strftime('%Y-%m-%d')}"
            })
            
            st.success(f"   ✅ {hoja_nombre}: {len(df_clasificado)} registros")
        
        if not todos_egresos_semanales:
            st.error("❌ No se pudo procesar ninguna hoja con datos válidos")
            return None
        
        # Convertir a lista ordenada y calcular totales
        egresos_semanales_final = []
        for semana in sorted(todos_egresos_semanales.keys()):
            datos_semana = todos_egresos_semanales[semana]
            fecha_inicio_semana = fecha_inicio_proyecto + timedelta(weeks=semana-1)
            
            total_semana = (
                datos_semana['materiales'] + 
                datos_semana['mano_obra'] + 
                datos_semana['variables'] + 
                datos_semana['admin'] + 
                datos_semana['sin_clasificar']
            )
            
            egresos_semanales_final.append({
                'semana': semana,
                'fecha_inicio': fecha_inicio_semana.isoformat(),
                'materiales': datos_semana['materiales'],
                'mano_obra': datos_semana['mano_obra'],
                'variables': datos_semana['variables'],
                'admin': datos_semana['admin'],
                'sin_clasificar': datos_semana['sin_clasificar'],
                'total': total_semana
            })
        
        # Calcular totales acumulados
        totales_acumulados = {
            'materiales': sum([e['materiales'] for e in egresos_semanales_final]),
            'mano_obra': sum([e['mano_obra'] for e in egresos_semanales_final]),
            'variables': sum([e['variables'] for e in egresos_semanales_final]),
            'admin': sum([e['admin'] for e in egresos_semanales_final]),
            'sin_clasificar': sum([e['sin_clasificar'] for e in egresos_semanales_final]),
            'total': sum([e['total'] for e in egresos_semanales_final])
        }
        
        # Última semana
        semana_ultima = max(todos_egresos_semanales.keys())
        
        return {
            'archivo': archivo.name,
            'hojas_procesadas': [h['nombre'] for h in hojas_procesadas_info],
            'hojas_procesadas_detalle': hojas_procesadas_info,
            'fecha_proceso': datetime.now().isoformat(),
            'semana_ultima': int(semana_ultima),
            'periodo_covered': f"{primera_fecha_global.strftime('%Y-%m-%d')} a {ultima_fecha_global.strftime('%Y-%m-%d')}" if primera_fecha_global and ultima_fecha_global else "N/A",
            'registros_procesados': todos_registros,
            'registros_totales': todos_registros,
            'egresos_semanales': egresos_semanales_final,
            'totales_acumulados': totales_acumulados,
            'cuentas_sin_clasificar': list(todas_cuentas_sin_clasificar)
        }
        
    except Exception as e:
        st.error(f"❌ Error al procesar archivo: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None


# ============================================================================
# COMPONENTES DE INTERFAZ - PASO 1: CARGAR PROYECCIÓN
# ============================================================================

def render_paso_1_cargar_proyeccion():
    """Paso 1: Cargar JSON de proyección"""
    
    st.header("📁 Paso 1: Cargar Proyección Base")
    
    st.info("""
    **📍 Módulo 1: CARTERA (Ingresos Reales)**
    
    **Instrucciones:**
    1. Cargue el archivo JSON generado por el módulo de Proyección FCL
    2. El sistema validará y extraerá la información necesaria
    3. Podrá continuar al ingreso de datos de cartera (ingresos reales)
    
    *Nota: El módulo de Egresos Reales (gastos) se agregará en la siguiente fase*
    """)
    
    # Verificar si ya hay proyección cargada (desde proyeccion_fcl)
    if 'proyeccion_cartera' in st.session_state:
        proyeccion_data = st.session_state.proyeccion_cartera
        
        st.success("✅ Proyección cargada desde módulo de Proyección FCL")
        
        # Mostrar información del proyecto
        proyecto = proyeccion_data['proyecto']
        totales = proyeccion_data['totales']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"**Proyecto:** {proyecto['nombre']}")
            st.info(f"**Cliente:** {proyecto.get('cliente', 'N/A')}")
        
        with col2:
            st.info(f"**Fecha Inicio:** {proyecto['fecha_inicio']}")
            st.info(f"**Duración:** {totales['semanas_total']} semanas")
        
        with col3:
            st.info(f"**Total Proyecto:** {formatear_moneda(totales['total_proyecto'])}")
            st.info(f"**Contratos:** {len(proyeccion_data['contratos'])}")
        
        # Mostrar contratos
        st.markdown("---")
        st.subheader("💼 Contratos")
        
        for cont_key, cont_data in proyeccion_data['contratos'].items():
            with st.expander(f"{cont_key}: {cont_data.get('nombre', 'Sin nombre')}", expanded=False):
                st.metric("Monto", formatear_moneda(cont_data['monto']))
                
                if 'desglose' in cont_data:
                    st.write("**Desglose:**")
                    for concepto, monto in cont_data['desglose'].items():
                        st.write(f"- {concepto}: {formatear_moneda(monto)}")
        
        # Opción de cargar otra proyección
        st.markdown("---")
        if st.checkbox("🔄 Cargar otra proyección", value=False):
            if st.button("🗑️ Limpiar y cargar nuevo archivo"):
                del st.session_state.proyeccion_cartera
                if 'pagos_por_hito' in st.session_state:
                    del st.session_state.pagos_por_hito
                st.rerun()
        
        # Botón continuar
        st.markdown("---")
        if st.button("▶️ Continuar a Ingreso de Cartera", type="primary", use_container_width=True):
            st.session_state.paso_ejecucion = 2
            st.rerun()
        
        return  # Salir de la función
    
    # Si no hay proyección cargada, mostrar uploader
    archivo_json = st.file_uploader(
        "Seleccione archivo JSON de proyección",
        type=['json'],
        key='upload_proyeccion_cartera'
    )
    
    if archivo_json:
        try:
            proyeccion_data = json.load(archivo_json)
            
            # Validar estructura
            requeridos = ['proyecto', 'contratos', 'proyeccion_semanal', 'configuracion']
            faltan = [r for r in requeridos if r not in proyeccion_data]
            
            if faltan:
                st.error(f"❌ JSON incompleto. Faltan secciones: {', '.join(faltan)}")
                return
            
            # Guardar en session_state
            st.session_state.proyeccion_cartera = proyeccion_data
            
            # Si es JSON v3.0 con datos de cartera, cargarlos también
            if proyeccion_data.get('version') == '3.0' and 'cartera' in proyeccion_data:
                st.info("🔄 Detectado JSON v3.0 con datos de cartera. Cargando datos previos...")
                
                cartera = proyeccion_data['cartera']
                
                # Cargar contratos_cartera_input
                if 'contratos_cartera' in cartera:
                    st.session_state.contratos_cartera_input = cartera['contratos_cartera']
                
                # Reconstruir pagos_por_hito desde contratos_cartera
                pagos_por_hito = {}
                if 'contratos_cartera' in cartera:
                    for contrato in cartera['contratos_cartera']:
                        for hito in contrato.get('hitos', []):
                            hito_id = str(hito['numero'])
                            
                            # Inicializar lista si no existe
                            if hito_id not in pagos_por_hito:
                                pagos_por_hito[hito_id] = []
                            
                            # Procesar pagos según tipo de hito
                            for pago in hito.get('pagos', []):
                                # Convertir fecha string a date
                                fecha_pago = datetime.fromisoformat(pago['fecha']).date() if isinstance(pago['fecha'], str) else pago['fecha']
                                
                                if hito.get('es_compartido', False):
                                    # Hito compartido: SUMAR montos si el recibo ya existe
                                    pago_existente = next((p for p in pagos_por_hito[hito_id] if p['recibo'] == pago['recibo']), None)
                                    if pago_existente:
                                        # Sumar monto (reconstruir monto original completo)
                                        pago_existente['monto'] += pago['monto']
                                    else:
                                        # Primera vez que aparece este recibo
                                        pagos_por_hito[hito_id].append({
                                            'fecha': fecha_pago,
                                            'recibo': pago['recibo'],
                                            'monto': pago['monto']
                                        })
                                else:
                                    # Hito NO compartido: agregar directamente (solo aparece una vez)
                                    pagos_por_hito[hito_id].append({
                                        'fecha': fecha_pago,
                                        'recibo': pago['recibo'],
                                        'monto': pago['monto']
                                    })
                
                st.session_state.pagos_por_hito = pagos_por_hito
                
                # Cargar fecha_corte
                if 'fecha_corte' in cartera:
                    fecha_corte = datetime.fromisoformat(cartera['fecha_corte']).date() if isinstance(cartera['fecha_corte'], str) else cartera['fecha_corte']
                    st.session_state.widget_fecha_corte_cartera = fecha_corte
                
                # Inicializar hitos_expandidos_cartera (todos colapsados por defecto al recargar)
                hitos_proyeccion = proyeccion_data['configuracion'].get('hitos_pago', [])
                st.session_state.hitos_expandidos_cartera = set()
                
                # Mostrar resumen de datos cargados
                total_pagos = sum(len(pagos) for pagos in pagos_por_hito.values())
                hitos_con_pagos = len([h for h in pagos_por_hito.values() if len(h) > 0])
                
                st.success(f"""
                ✅ **Datos de cartera cargados:**
                - {hitos_con_pagos} hitos con pagos
                - {total_pagos} pagos registrados
                - Fecha de corte: {cartera.get('fecha_corte', 'N/A')}
                
                Puede continuar al **Paso 3** para ver el análisis o al **Paso 2** para editar.
                """)
            
            # Mostrar información del proyecto
            proyecto = proyeccion_data['proyecto']
            totales = proyeccion_data['totales']
            
            st.success("✅ Proyección cargada correctamente")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.info(f"**Proyecto:** {proyecto['nombre']}")
                st.info(f"**Cliente:** {proyecto.get('cliente', 'N/A')}")
            
            with col2:
                st.info(f"**Fecha Inicio:** {proyecto['fecha_inicio']}")
                st.info(f"**Duración:** {totales['semanas_total']} semanas")
            
            with col3:
                st.info(f"**Total Proyecto:** {formatear_moneda(totales['total_proyecto'])}")
                st.info(f"**Contratos:** {len(proyeccion_data['contratos'])}")
            
            # Mostrar contratos
            st.markdown("---")
            st.subheader("💼 Contratos")
            
            for cont_key, cont_data in proyeccion_data['contratos'].items():
                with st.expander(f"{cont_key}: {cont_data.get('nombre', 'Sin nombre')}", expanded=True):
                    st.metric("Monto", formatear_moneda(cont_data['monto']))
                    
                    if 'desglose' in cont_data:
                        st.write("**Desglose:**")
                        for concepto, monto in cont_data['desglose'].items():
                            st.write(f"- {concepto}: {formatear_moneda(monto)}")
            
            # Botón continuar
            st.markdown("---")
            
            # Determinar a qué paso saltar
            if proyeccion_data.get('version') == '3.0' and 'cartera' in proyeccion_data:
                # JSON v3.0 con datos de cartera
                st.subheader("⏭️ Seleccione el paso al que desea continuar:")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📝 Paso 2: Editar Cartera", use_container_width=True):
                        st.session_state.paso_ejecucion = 2
                        st.rerun()
                
                with col2:
                    if st.button("📊 Paso 3: Ver Análisis Cartera", type="primary", use_container_width=True):
                        st.session_state.paso_ejecucion = 3
                        st.rerun()
                
                with col3:
                    if st.button("💰 Paso 4: Ingresar Egresos", use_container_width=True):
                        st.session_state.paso_ejecucion = 4
                        st.rerun()
            else:
                # JSON v2.0 sin datos de cartera
                if st.button("▶️ Continuar a Ingreso de Cartera", type="primary", use_container_width=True):
                    st.session_state.paso_ejecucion = 2
                    st.rerun()
        
        except json.JSONDecodeError:
            st.error("❌ Error al leer el archivo JSON. Verifique que sea un archivo válido.")
        except Exception as e:
            st.error(f"❌ Error inesperado: {str(e)}")


# ============================================================================
# COMPONENTES DE INTERFAZ - PASO 2: INGRESAR CARTERA
# ============================================================================

def render_formulario_pago(contrato_idx: int, hito_idx: int, pago_idx: int, 
                           pago_data: Optional[Dict] = None) -> Dict:
    """Renderiza formulario para un pago individual"""
    
    pago_key = f"pago_{contrato_idx}_{hito_idx}_{pago_idx}"
    
    cols = st.columns([2, 2, 3, 1])
    
    with cols[0]:
        fecha_pago = st.date_input(
            "Fecha",
            value=pago_data.get('fecha') if pago_data else datetime.now().date(),
            key=f"{pago_key}_fecha",
            label_visibility="collapsed"
        )
    
    with cols[1]:
        recibo = st.text_input(
            "Recibo",
            value=pago_data.get('recibo', '') if pago_data else '',
            placeholder="RC-000",
            key=f"{pago_key}_recibo",
            label_visibility="collapsed"
        )
    
    with cols[2]:
        monto = st.number_input(
            "Monto",
            min_value=0.0,
            value=float(pago_data.get('monto', 0)) if pago_data else 0.0,
            step=1000000.0,
            format="%.0f",
            key=f"{pago_key}_monto",
            label_visibility="collapsed"
        )
    
    with cols[3]:
        eliminar = st.button("🗑️", key=f"{pago_key}_delete", help="Eliminar pago")
    
    return {
        'fecha': fecha_pago,
        'recibo': recibo,
        'monto': monto,
        'eliminar': eliminar
    }


def render_formulario_hito(contrato_idx: int, hito_idx: int, contrato_numero: str,
                           hito_data: Optional[Dict] = None):
    """Renderiza formulario para un hito"""
    
    hito_key = f"hito_{contrato_idx}_{hito_idx}"
    
    # Inicializar número de pagos si no existe
    num_pagos_key = f"{hito_key}_num_pagos"
    if num_pagos_key not in st.session_state:
        st.session_state[num_pagos_key] = len(hito_data.get('pagos', [])) if hito_data else 0
    
    with st.expander(f"Hito {hito_idx + 1}: {hito_data.get('descripcion', 'Nuevo hito') if hito_data else 'Nuevo hito'}", 
                     expanded=st.session_state[num_pagos_key] == 0):
        
        col1, col2 = st.columns(2)
        
        with col1:
            descripcion = st.text_input(
                "Descripción del Hito",
                value=hito_data.get('descripcion', '') if hito_data else f"Hito {hito_idx + 1}",
                key=f"{hito_key}_desc"
            )
            
            monto_esperado = st.number_input(
                "Monto Esperado",
                min_value=0.0,
                value=float(hito_data.get('monto_esperado', 0)) if hito_data else 0.0,
                step=1000000.0,
                format="%.0f",
                key=f"{hito_key}_monto"
            )
        
        with col2:
            semana_esperada = st.number_input(
                "Semana Esperada",
                min_value=1,
                value=int(hito_data.get('semana_esperada', 1)) if hito_data else 1,
                key=f"{hito_key}_semana"
            )
            
            fecha_vencimiento = st.date_input(
                "Fecha Vencimiento (opcional)",
                value=None,
                key=f"{hito_key}_fecha"
            )
        
        # Sección de pagos
        st.markdown("**💰 Pagos Recibidos:**")
        
        if st.session_state[num_pagos_key] == 0:
            st.info("No hay pagos registrados para este hito")
        else:
            # Encabezados
            cols = st.columns([2, 2, 3, 1])
            cols[0].markdown("**Fecha**")
            cols[1].markdown("**Recibo**")
            cols[2].markdown("**Monto**")
            cols[3].markdown("**Acc**")
        
        pagos = []
        pagos_a_eliminar = []
        
        for pago_idx in range(st.session_state[num_pagos_key]):
            pago_data_existente = None
            if hito_data and 'pagos' in hito_data and pago_idx < len(hito_data['pagos']):
                pago_data_existente = hito_data['pagos'][pago_idx]
            
            pago_form = render_formulario_pago(contrato_idx, hito_idx, pago_idx, pago_data_existente)
            
            if pago_form['eliminar']:
                pagos_a_eliminar.append(pago_idx)
            else:
                pagos.append({
                    'fecha': pago_form['fecha'],
                    'recibo': pago_form['recibo'],
                    'monto': pago_form['monto']
                })
        
        # Eliminar pagos marcados
        if pagos_a_eliminar:
            st.session_state[num_pagos_key] -= len(pagos_a_eliminar)
            st.rerun()
        
        # Botón agregar pago
        if st.button("➕ Agregar Pago", key=f"{hito_key}_add_pago"):
            st.session_state[num_pagos_key] += 1
            st.rerun()
        
        # Mostrar resumen de conciliación
        if pagos:
            total_pagado = sum([p['monto'] for p in pagos])
            desviacion = total_pagado - monto_esperado
            pct = calcular_porcentaje(desviacion, monto_esperado)
            
            st.markdown("---")
            st.markdown("**📊 Resumen de Conciliación:**")
            
            col_r1, col_r2, col_r3 = st.columns(3)
            
            with col_r1:
                st.metric("Esperado", formatear_moneda(monto_esperado))
            
            with col_r2:
                st.metric("Pagado", formatear_moneda(total_pagado))
            
            with col_r3:
                if abs(pct) <= 1:
                    st.success(f"✅ Completo ({pct:+.1f}%)")
                elif pct > 1:
                    st.warning(f"⚠️ Sobrepago (+{pct:.1f}%)")
                elif total_pagado == 0:
                    st.error(f"🔴 Pendiente")
                else:
                    st.info(f"🔶 Parcial ({calcular_porcentaje(total_pagado, monto_esperado):.1f}%)")
        
        return {
            'numero': hito_idx + 1,
            'descripcion': descripcion,
            'monto_esperado': monto_esperado,
            'semana_esperada': semana_esperada,
            'fecha_vencimiento': fecha_vencimiento if fecha_vencimiento else None,
            'pagos': pagos
        }


def render_paso_2_ingresar_cartera():
    """Paso 2: Ingresar pagos reales a hitos predefinidos"""
    
    st.header("💰 Paso 2: Registrar Pagos Recibidos")
    st.caption("📍 Módulo 1: CARTERA | Asignar pagos reales a hitos de la proyección")
    
    # Botón cargar otra proyección
    mostrar_boton_cargar_otra_proyeccion()
    
    # Botón volver
    col_v1, col_v2 = st.columns([1, 4])
    with col_v1:
        if st.button("◀️ Volver"):
            # NO limpiar datos, solo cambiar paso
            st.session_state.paso_ejecucion = 1
            st.rerun()
    
    proyeccion = st.session_state.proyeccion_cartera
    
    st.info("""
    **Los hitos de pago ya están definidos en tu proyección.**
    
    A continuación, asigna los pagos reales recibidos a cada hito.
    """)
    
    # Fecha de corte
    fecha_corte = st.date_input(
        "📅 Fecha de Corte de Cartera",
        value=datetime.now().date(),
        key='widget_fecha_corte_cartera',
        help="Fecha hasta la cual se reportan los cobros"
    )
    
    st.markdown("---")
    
    # Extraer hitos de la proyección
    hitos_proyeccion = proyeccion['configuracion'].get('hitos', [])
    
    if not hitos_proyeccion:
        st.error("❌ No se encontraron hitos en la proyección. Regrese a Proyección FCL y configure hitos.")
        return
    
    # Inicializar estructura de pagos si no existe
    if 'pagos_por_hito' not in st.session_state:
        st.session_state.pagos_por_hito = {str(h['id']): [] for h in hitos_proyeccion}
    
    # Inicializar conjunto de hitos expandidos
    if 'hitos_expandidos_cartera' not in st.session_state:
        # Por default, expandir hitos sin pagos
        st.session_state.hitos_expandidos_cartera = {
            str(h['id']) for h in hitos_proyeccion 
            if len(st.session_state.pagos_por_hito.get(str(h['id']), [])) == 0
        }
    
    # Mostrar información general
    total_proyectado = sum([h['monto'] for h in hitos_proyeccion])
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Proyectado (Hitos)", formatear_moneda(total_proyectado))
    with col2:
        st.metric("Hitos Definidos", len(hitos_proyeccion))
    
    st.markdown("---")
    
    # Renderizar cada hito
    for hito in hitos_proyeccion:
        hito_id = str(hito['id'])
        
        with st.expander(
            f"💎 Hito {hito['id']}: {hito['nombre']} : {formatear_moneda(hito['monto'])}", 
            expanded=hito_id in st.session_state.hitos_expandidos_cartera
        ):
            # Información del hito
            col_h1, col_h2, col_h3 = st.columns(3)
            
            with col_h1:
                contrato_texto = hito.get('contrato', 'N/A')
                if contrato_texto == 'ambos':
                    st.write(f"**Contrato:** Ambos (C1: {hito.get('porcentaje_c1', 0)}%, C2: {hito.get('porcentaje_c2', 0)}%)")
                else:
                    st.write(f"**Contrato:** {contrato_texto}")
            
            with col_h2:
                st.write(f"**Fase:** {hito.get('fase_vinculada', 'N/A')}")
            
            with col_h3:
                st.write(f"**Momento:** {hito.get('momento', 'N/A').title()}")
            
            st.markdown("---")
            
            # Sección de pagos
            st.markdown("**💰 Pagos Recibidos:**")
            
            # Obtener pagos actuales
            pagos_hito = st.session_state.pagos_por_hito.get(hito_id, [])
            
            if not pagos_hito:
                st.info("No hay pagos registrados para este hito")
            else:
                # Encabezados
                cols = st.columns([2, 2, 3, 1])
                cols[0].markdown("**Fecha**")
                cols[1].markdown("**Recibo**")
                cols[2].markdown("**Monto**")
                cols[3].markdown("**Acc**")
            
            # Renderizar pagos existentes
            pagos_actualizados = []
            indices_eliminar = []
            
            for idx, pago in enumerate(pagos_hito):
                pago_key = f"pago_{hito_id}_{idx}"
                cols = st.columns([2, 2, 3, 1])
                
                with cols[0]:
                    fecha_pago = st.date_input(
                        "Fecha",
                        value=pago.get('fecha', datetime.now().date()),
                        key=f"{pago_key}_fecha",
                        label_visibility="collapsed"
                    )
                
                with cols[1]:
                    recibo = st.text_input(
                        "Recibo",
                        value=pago.get('recibo', ''),
                        placeholder="RC-000",
                        key=f"{pago_key}_recibo",
                        label_visibility="collapsed"
                    )
                
                with cols[2]:
                    monto = st.number_input(
                        "Monto",
                        min_value=0.0,
                        value=float(pago.get('monto', 0)),
                        step=1000000.0,
                        format="%.0f",
                        key=f"{pago_key}_monto",
                        label_visibility="collapsed"
                    )
                
                with cols[3]:
                    if st.button("🗑️", key=f"{pago_key}_delete", help="Eliminar pago"):
                        indices_eliminar.append(idx)
                
                # Guardar pago actualizado (si no fue eliminado)
                if idx not in indices_eliminar:
                    pagos_actualizados.append({
                        'fecha': fecha_pago,
                        'recibo': recibo,
                        'monto': monto
                    })
            
            # Actualizar lista de pagos
            st.session_state.pagos_por_hito[hito_id] = pagos_actualizados
            
            # Botón agregar pago
            if st.button(f"➕ Agregar Pago", key=f"add_pago_{hito_id}"):
                st.session_state.pagos_por_hito[hito_id].append({
                    'fecha': datetime.now().date(),
                    'recibo': '',
                    'monto': 0
                })
                # Mantener hito expandido
                st.session_state.hitos_expandidos_cartera.add(hito_id)
                st.rerun()
            
            # Resumen de conciliación
            total_pagado_hito = sum([p['monto'] for p in st.session_state.pagos_por_hito[hito_id]])
            
            if total_pagado_hito > 0:
                st.markdown("---")
                st.markdown("**📊 Resumen:**")
                
                col_r1, col_r2, col_r3 = st.columns(3)
                
                with col_r1:
                    st.metric("Esperado", formatear_moneda(hito['monto']))
                
                with col_r2:
                    st.metric("Pagado", formatear_moneda(total_pagado_hito))
                
                with col_r3:
                    desv = total_pagado_hito - hito['monto']
                    pct = calcular_porcentaje(desv, hito['monto'])
                    
                    if abs(pct) <= 1:
                        st.success(f"✅ Completo ({pct:+.1f}%)")
                    elif pct > 1:
                        st.warning(f"⚠️ Sobrepago (+{pct:.1f}%)")
                    elif total_pagado_hito == 0:
                        st.error(f"🔴 Pendiente")
                    else:
                        st.info(f"🔶 Parcial ({calcular_porcentaje(total_pagado_hito, hito['monto']):.1f}%)")
    
    # Botón generar análisis
    st.markdown("---")
    
    # Verificar que haya al menos un pago
    total_pagos = sum([len(pagos) for pagos in st.session_state.pagos_por_hito.values()])
    
    if total_pagos == 0:
        st.warning("⚠️ No has registrado ningún pago. Agrega al menos un pago para continuar.")
    else:
        st.success(f"✅ {total_pagos} pagos registrados")
    
    if st.button("▶️ Generar Análisis de Cartera", type="primary", use_container_width=True, disabled=total_pagos == 0):
        # Preparar estructura de contratos_cartera_input
        # Convertir de pagos_por_hito a estructura esperada
        contratos_dict = {}
        
        for hito in hitos_proyeccion:
            hito_id = str(hito['id'])
            contrato_key = hito.get('contrato', '1')
            
            # Determinar a qué contrato(s) pertenece
            if contrato_key == 'ambos':
                contratos_keys = ['contrato_1', 'contrato_2']
            else:
                contratos_keys = [f'contrato_{contrato_key}']
            
            for idx_cont, cont_key in enumerate(contratos_keys):
                if cont_key not in contratos_dict:
                    # Buscar info del contrato en proyección
                    cont_data = proyeccion['contratos'].get(cont_key, {})
                    contratos_dict[cont_key] = {
                        'numero': cont_key,
                        'descripcion': cont_data.get('nombre', ''),
                        'monto': cont_data.get('monto', 0),
                        'hitos': []
                    }
                
                # Determinar monto esperado y proporción para este contrato
                if contrato_key == 'ambos':
                    # Hito compartido - calcular proporción basada en montos de contratos
                    cont_1_data = proyeccion['contratos'].get('contrato_1', {})
                    cont_2_data = proyeccion['contratos'].get('contrato_2', {})
                    
                    porcentaje_c1 = hito.get('porcentaje_c1', 50)
                    porcentaje_c2 = hito.get('porcentaje_c2', 50)
                    
                    # Monto esperado de cada contrato en este hito
                    monto_esperado_c1 = cont_1_data.get('monto', 0) * (porcentaje_c1 / 100)
                    monto_esperado_c2 = cont_2_data.get('monto', 0) * (porcentaje_c2 / 100)
                    total_esperado_hito = monto_esperado_c1 + monto_esperado_c2
                    
                    # Determinar proporción y monto para este contrato específico
                    if cont_key == 'contrato_1':
                        monto_esperado = monto_esperado_c1
                        proporcion = monto_esperado_c1 / total_esperado_hito if total_esperado_hito > 0 else 0.5
                        porcentaje_display = porcentaje_c1
                    else:  # contrato_2
                        monto_esperado = monto_esperado_c2
                        proporcion = monto_esperado_c2 / total_esperado_hito if total_esperado_hito > 0 else 0.5
                        porcentaje_display = porcentaje_c2
                else:
                    # Hito exclusivo de un contrato
                    monto_esperado = hito['monto']
                    proporcion = 1.0
                    porcentaje_display = 100
                
                # Obtener pagos y distribuir según proporción
                pagos_hito_completos = st.session_state.pagos_por_hito.get(hito_id, [])
                pagos_distribuidos = [
                    {
                        'fecha': p['fecha'],
                        'recibo': p['recibo'],
                        'monto': p['monto'] * proporcion
                    }
                    for p in pagos_hito_completos
                ]
                
                # Agregar hito a contrato con montos distribuidos
                contratos_dict[cont_key]['hitos'].append({
                    'numero': hito['id'],
                    'descripcion': hito['nombre'],
                    'monto_esperado': monto_esperado,
                    'semana_esperada': 1,  # TODO: calcular desde fase_vinculada
                    'fecha_vencimiento': None,
                    'pagos': pagos_distribuidos,
                    'es_compartido': contrato_key == 'ambos',
                    'porcentaje_contrato': porcentaje_display,
                    'proporcion_distribucion': proporcion * 100
                })
        
        st.session_state.contratos_cartera_input = list(contratos_dict.values())
        st.session_state.paso_ejecucion = 3
        st.rerun()


# ============================================================================
# COMPONENTES DE INTERFAZ - PASO 3: ANÁLISIS Y RESULTADOS
# ============================================================================

def render_paso_3_analisis():
    """Paso 3: Análisis de cartera (ingresos reales vs proyectados)"""
    
    st.header("📊 Análisis de Cartera - Ingresos Reales vs Proyectados")
    st.caption("📍 Módulo 1: CARTERA | Dashboard de análisis de ingresos")
    
    # Botón cargar otra proyección
    mostrar_boton_cargar_otra_proyeccion()
    
    # Botón volver
    col_v1, col_v2 = st.columns([1, 4])
    with col_v1:
        if st.button("◀️ Editar Datos"):
            st.session_state.paso_ejecucion = 2
            st.rerun()
    
    proyeccion = st.session_state.proyeccion_cartera
    contratos_cartera = st.session_state.contratos_cartera_input
    
    # Leer fecha_corte con fallback
    if 'widget_fecha_corte_cartera' in st.session_state:
        fecha_corte = st.session_state.widget_fecha_corte_cartera
    else:
        # Fallback: usar fecha actual
        fecha_corte = datetime.now().date()
        st.warning("⚠️ Usando fecha actual como fecha de corte (no se detectó fecha del paso anterior)")
    
    # Calcular semana actual
    fecha_inicio = datetime.fromisoformat(proyeccion['proyecto']['fecha_inicio']).date()
    semana_actual = calcular_semana_desde_fecha(fecha_inicio, fecha_corte)
    
    # Calcular totales
    total_contratado = sum([c['monto'] for c in contratos_cartera])
    total_cobrado = sum([
        sum([p['monto'] for p in h['pagos']])
        for c in contratos_cartera
        for h in c['hitos']
    ])
    total_pendiente = total_contratado - total_cobrado
    pct_cobrado = calcular_porcentaje(total_cobrado, total_contratado)
    
    # Crear estructura de cartera completa
    cartera = {
        'fecha_corte': fecha_corte.isoformat(),
        'fecha_inicio': proyeccion['proyecto']['fecha_inicio'],
        'semana_actual': semana_actual,
        'contratos_cartera': contratos_cartera,
        'resumen': {
            'total_contratado': total_contratado,
            'total_cobrado': total_cobrado,
            'total_pendiente': total_pendiente,
            'pct_cobrado': pct_cobrado
        }
    }
    
    # Cargar proyección en DataFrame
    proyeccion_df = pd.DataFrame(proyeccion['proyeccion_semanal'])
    
    # Calcular comparación con proyección
    ingresos_proy = proyeccion_df.loc[
        proyeccion_df['Semana'] <= semana_actual,
        'Ingresos_Proyectados'
    ].sum()
    
    desviacion = total_cobrado - ingresos_proy
    pct_desviacion = calcular_porcentaje(desviacion, ingresos_proy)
    
    cartera['comparacion_proyeccion'] = {
        'ingresos_proyectados_a_hoy': ingresos_proy,
        'cobros_reales_a_hoy': total_cobrado,
        'desviacion': desviacion,
        'pct_desviacion': pct_desviacion,
        'estado': 'adelantado' if desviacion > 0 else 'atrasado'
    }
    
    # Generar alertas
    alertas = generar_alertas_cartera(contratos_cartera, proyeccion_df, fecha_corte, semana_actual)
    cartera['alertas'] = alertas
    
    # ========================================================================
    # RENDERIZAR DASHBOARD
    # ========================================================================
    
    # KPIs principales
    render_kpis_principales(cartera['resumen'])
    
    st.markdown("---")
    
    # Gráfica proyección vs real
    st.subheader("📈 Proyección vs Ejecución Real")
    render_grafica_proyeccion_vs_real(proyeccion_df, cartera, semana_actual)
    
    # Comparación numérica
    st.markdown("---")
    st.subheader("🎯 Comparación con Proyección")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Proyectado (a hoy)",
            formatear_moneda(ingresos_proy)
        )
    
    with col2:
        st.metric(
            "Cobrado (real)",
            formatear_moneda(total_cobrado)
        )
    
    with col3:
        st.metric(
            "Desviación",
            formatear_moneda(abs(desviacion)),
            delta=f"{pct_desviacion:+.1f}%",
            delta_color="normal" if desviacion > 0 else "inverse"
        )
    
    estado = cartera['comparacion_proyeccion']['estado']
    if estado == 'adelantado':
        st.success(f"🟢 **Estado: ADELANTADO** - Cobros superan proyección en {pct_desviacion:.1f}%")
    else:
        st.error(f"🔴 **Estado: ATRASADO** - Cobros por debajo de proyección en {abs(pct_desviacion):.1f}%")
    
    # Ubicación temporal
    st.info(f"📍 **Ubicación:** Semana {semana_actual} de {len(proyeccion_df)} ({calcular_porcentaje(semana_actual, len(proyeccion_df)):.0f}% del tiempo)")
    
    st.markdown("---")
    
    # Alertas
    st.subheader("⚠️ Alertas")
    render_tabla_alertas(alertas)
    
    st.markdown("---")
    
    # Detalle por contrato
    st.subheader("📋 Detalle por Contrato")
    
    for contrato in contratos_cartera:
        with st.expander(f"{contrato['numero']}: {contrato['descripcion']}", expanded=False):
            # Totales del contrato
            total_hitos = sum([h['monto_esperado'] for h in contrato['hitos']])
            total_pagado_cont = sum([
                sum([p['monto'] for p in h['pagos']])
                for h in contrato['hitos']
            ])
            
            col_c1, col_c2, col_c3 = st.columns(3)
            
            with col_c1:
                st.metric("Contrato", formatear_moneda(contrato['monto']))
            
            with col_c2:
                st.metric("Cobrado", formatear_moneda(total_pagado_cont))
            
            with col_c3:
                pendiente_cont = contrato['monto'] - total_pagado_cont
                st.metric("Pendiente", formatear_moneda(pendiente_cont))
            
            # Tabla de hitos
            st.markdown("**Hitos:**")
            
            for hito in contrato['hitos']:
                conciliacion = conciliar_hito(hito)
                
                st.markdown(f"{conciliacion['emoji']} **{hito['descripcion']}**")
                
                col_h1, col_h2, col_h3, col_h4 = st.columns(4)
                
                with col_h1:
                    st.write(f"Esperado: {formatear_moneda(hito['monto_esperado'])}")
                
                with col_h2:
                    st.write(f"Pagado: {formatear_moneda(conciliacion['monto_pagado'])}")
                
                with col_h3:
                    st.write(f"Estado: {conciliacion['estado'].replace('_', ' ').title()}")
                
                with col_h4:
                    st.write(f"Desv: {conciliacion['pct_desviacion']:+.1f}%")
                
                if conciliacion['alerta']:
                    st.caption(f"⚠️ {conciliacion['alerta']}")
    
    # ========================================================================
    # EXPORTACIÓN
    # ========================================================================
    
    st.markdown("---")
    st.subheader("💾 Exportar Datos")
    
    # Agregar cartera al JSON de proyección
    proyeccion_completa = proyeccion.copy()
    proyeccion_completa['cartera'] = cartera
    proyeccion_completa['version'] = '3.0'
    proyeccion_completa['tipo'] = 'proyeccion_con_cartera'
    
    json_str = json.dumps(proyeccion_completa, indent=2, default=str)
    
    nombre_archivo = f"SICONE_{proyeccion['proyecto']['nombre']}_Cartera_{fecha_corte.strftime('%Y%m%d')}.json"
    
    st.download_button(
        label="📥 Descargar JSON Completo (v3.0)",
        data=json_str,
        file_name=nombre_archivo,
        mime="application/json",
        use_container_width=True
    )
    
    st.info("""
    **JSON v3.0 incluye:**
    - ✅ Proyección completa
    - ✅ Datos de cartera ingresados
    - ✅ Conciliación de hitos
    - ✅ Comparación proyección vs real
    - ✅ Alertas generadas
    """)
    
    # Botón para continuar a Egresos
    st.markdown("---")
    st.subheader("➡️ Siguiente Paso: Análisis de Egresos")
    st.info("Continúe con el análisis de gastos reales del proyecto comparándolos con la proyección.")
    
    if st.button("▶️ Continuar a Egresos Reales", type="primary", use_container_width=True):
        st.session_state.paso_ejecucion = 4
        st.rerun()


# ============================================================================
# COMPONENTES DE INTERFAZ - PASO 4: INGRESAR EGRESOS REALES
# ============================================================================

def render_paso_4_ingresar_egresos():
    """Paso 4: Ingresar egresos reales desde Excel contable"""
    
    st.header("💰 Paso 4: Ingresar Egresos Reales")
    st.caption("📍 Módulo 2: EGRESOS | Gastos de ejecución contable")
    
    # Botón cargar otra proyección
    mostrar_boton_cargar_otra_proyeccion()
    
    # Botón volver
    col_v1, col_v2 = st.columns([1, 4])
    with col_v1:
        if st.button("◀️ Volver a Cartera"):
            st.session_state.paso_ejecucion = 3
            st.rerun()
    
    st.markdown("---")
    
    # Verificar que existe proyección cargada
    if 'proyeccion_cartera' not in st.session_state:
        st.error("⚠️ No hay proyección cargada. Por favor regrese al Paso 1.")
        return
    
    proyeccion = st.session_state.proyeccion_cartera
    fecha_inicio = datetime.fromisoformat(proyeccion['proyecto']['fecha_inicio']).date()
    nombre_proyecto = proyeccion['proyecto']['nombre']
    
    # Instrucciones
    st.info("""
    **📁 Instrucciones:**
    
    Cargue el archivo Excel de ejecución contable:
    - **Formato:** Un archivo con múltiples hojas, una por año
    - **Hojas:** Nombradas como "AÑO 2024", "AÑO 2025", etc.
    - **Estructura:** Encabezados en fila 8, datos transaccionales desde fila 9
    - **Columnas requeridas:** Código contable, Cuenta contable, Fecha elaboración, Débito
    - **Ejemplo:** `OBRA_CARLOS_VELEZ.xlsx` con hojas "AÑO 2024" y "AÑO 2025"
    
    El sistema:
    - Detectará automáticamente todas las hojas "AÑO XXXX"
    - Procesará cada año por separado
    - Consolidará los datos automáticamente
    - Clasificará gastos en: 💎 Materiales | 👷 Mano de Obra | 📦 Variables | 🏢 Administración
    """)
    
    # Upload de archivo
    st.subheader("📁 Cargar Archivo de Ejecución")
    
    archivo_subido = st.file_uploader(
        "Seleccione el archivo Excel con ejecución contable",
        type=['xlsx'],
        key='upload_egresos',
        help="Archivo con hojas 'AÑO 2024', 'AÑO 2025', etc."
    )
    
    if not archivo_subido:
        st.warning("⚠️ Por favor cargue el archivo Excel para continuar.")
        return
    
    # Validar archivo
    st.markdown("---")
    st.subheader("✅ Validación de Archivo")
    
    with st.expander(f"📄 {archivo_subido.name}", expanded=True):
        es_valido, mensaje = validar_excel_egresos(archivo_subido)
        
        if es_valido:
            st.success("✅ Validación exitosa")
            st.markdown(mensaje)
        else:
            st.error("❌ Validación fallida")
            st.markdown(mensaje)
            return
    
    # Botón de procesamiento
    st.markdown("---")
    st.subheader("🔄 Procesamiento de Datos")
    
    if st.button("🚀 Procesar Archivo", type="primary", use_container_width=True):
        
        with st.spinner("Procesando hojas del archivo..."):
            datos_egresos = parse_excel_egresos(
                archivo=archivo_subido,
                fecha_inicio_proyecto=fecha_inicio,
                nombre_centro_costo=None
            )
        
        if not datos_egresos:
            st.error("❌ No se pudo procesar el archivo.")
            return
        
        # Guardar en session_state
        st.session_state.egresos_reales_input = datos_egresos
        
        # Mostrar resumen consolidado
        st.success("✅ Datos procesados exitosamente")
        
        st.markdown("### 📊 Resumen del Procesamiento")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Hojas procesadas", len(datos_egresos['hojas_procesadas']))
        
        with col2:
            st.metric("Total registros", f"{datos_egresos['registros_procesados']:,}")
        
        with col3:
            st.metric("Período", datos_egresos['periodo_covered'])
        
        # Detalle por hoja
        if 'hojas_procesadas_detalle' in datos_egresos:
            st.markdown("#### 📑 Detalle por hoja:")
            for hoja_info in datos_egresos['hojas_procesadas_detalle']:
                st.write(f"• **{hoja_info['nombre']}**: {hoja_info['registros']:,} registros | {hoja_info['periodo']}")
        
        # Alertas de cuentas sin clasificar
        if datos_egresos['cuentas_sin_clasificar']:
            st.warning(f"⚠️ {len(datos_egresos['cuentas_sin_clasificar'])} cuenta(s) sin clasificar:")
            for cuenta in datos_egresos['cuentas_sin_clasificar'][:5]:
                st.write(f"   • {cuenta}")
            if len(datos_egresos['cuentas_sin_clasificar']) > 5:
                st.write(f"   • ... y {len(datos_egresos['cuentas_sin_clasificar'])-5} más")
    
    # Mostrar vista previa si ya hay datos procesados
    if 'egresos_reales_input' in st.session_state:
        st.markdown("---")
        st.subheader("📊 Vista Previa de Datos Procesados")
        
        datos = st.session_state.egresos_reales_input
        
        # KPIs principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Gastado",
                formatear_moneda(datos['totales_acumulados']['total'])
            )
        
        with col2:
            st.metric(
                "Semanas con Datos",
                f"1 a {datos['semana_ultima']}"
            )
        
        with col3:
            st.metric(
                "Registros",
                f"{datos['registros_procesados']:,}"
            )
        
        with col4:
            hojas_procesadas = datos.get('hojas_procesadas', [])
            st.metric(
                "Hojas procesadas",
                len(hojas_procesadas) if hojas_procesadas else 1
            )
        
        # Totales por categoría
        st.markdown("### 💰 Totales por Categoría")
        
        totales = datos['totales_acumulados']
        total_general = totales['total']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "💎 Materiales",
                formatear_moneda(totales['materiales']),
                delta=f"{calcular_porcentaje(totales['materiales'], total_general):.1f}%"
            )
            st.metric(
                "👷 Mano de Obra",
                formatear_moneda(totales['mano_obra']),
                delta=f"{calcular_porcentaje(totales['mano_obra'], total_general):.1f}%"
            )
        
        with col2:
            st.metric(
                "📦 Variables",
                formatear_moneda(totales['variables']),
                delta=f"{calcular_porcentaje(totales['variables'], total_general):.1f}%"
            )
            st.metric(
                "🏢 Administración",
                formatear_moneda(totales['admin']),
                delta=f"{calcular_porcentaje(totales['admin'], total_general):.1f}%"
            )
        
        with col3:
            # Mostrar "Sin Clasificar" solo si hay montos
            sin_clasificar = totales.get('sin_clasificar', 0)
            if sin_clasificar > 0:
                st.metric(
                    "❓ Sin Clasificar",
                    formatear_moneda(sin_clasificar),
                    delta=f"{calcular_porcentaje(sin_clasificar, total_general):.1f}%",
                    help="Cuentas contables que aún no están mapeadas en la tabla de clasificación"
                )
        
        # Tabla semanal (últimas 10 semanas)
        st.markdown("### 📅 Egresos Semanales (Últimas 10 Semanas)")
        
        egresos_semanales = datos['egresos_semanales']
        ultimas_semanas = egresos_semanales[-10:] if len(egresos_semanales) > 10 else egresos_semanales
        
        df_preview = pd.DataFrame(ultimas_semanas)
        
        # Incluir sin_clasificar solo si hay datos
        columnas_base = ['semana', 'materiales', 'mano_obra', 'variables', 'admin']
        nombres_base = ['Semana', 'Materiales', 'Mano Obra', 'Variables', 'Admin']
        
        if sin_clasificar > 0:
            columnas_base.append('sin_clasificar')
            nombres_base.append('Sin Clasificar')
        
        columnas_base.append('total')
        nombres_base.append('Total')
        
        df_preview_display = df_preview[columnas_base].copy()
        df_preview_display.columns = nombres_base
        
        # Formatear como moneda
        columnas_a_formatear = ['Materiales', 'Mano Obra', 'Variables', 'Admin']
        if sin_clasificar > 0:
            columnas_a_formatear.append('Sin Clasificar')
        columnas_a_formatear.append('Total')
        
        for col in columnas_a_formatear:
            df_preview_display[col] = df_preview_display[col].apply(lambda x: formatear_moneda(x))
        
        st.dataframe(df_preview_display, use_container_width=True, hide_index=True)
        
        # Comparación rápida vs proyección (si existe)
        if 'proyeccion_semanal' in proyeccion:
            try:
                st.markdown("### ⚡ Comparación Rápida vs Proyección")
                
                df_proy = pd.DataFrame(proyeccion['proyeccion_semanal'])
                
                # Verificar que existen las columnas necesarias
                if 'semana' not in df_proy.columns:
                    st.warning("⚠️ No se puede mostrar comparación: estructura de proyección incompatible")
                else:
                    # Calcular totales proyectados por categoría (acumulado hasta semana última)
                    semana_ultima = datos['semana_ultima']
                    df_proy_filtrado = df_proy[df_proy['semana'] <= semana_ultima]
                    
                    # Obtener valores con .get() para evitar KeyError si no existen
                    proy_materiales = df_proy_filtrado.get('materiales', pd.Series([0])).sum()
                    proy_mano_obra = df_proy_filtrado.get('mano_obra', pd.Series([0])).sum()
                    proy_equipos = df_proy_filtrado.get('equipos', pd.Series([0])).sum()
                    proy_imprevistos = df_proy_filtrado.get('imprevistos', pd.Series([0])).sum()
                    proy_logistica = df_proy_filtrado.get('logistica', pd.Series([0])).sum()
                    proy_admin = df_proy_filtrado.get('admin', pd.Series([0])).sum()
                    
                    # Variables = Equipos + Imprevistos + Logística
                    proy_variables = proy_equipos + proy_imprevistos + proy_logistica
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        desv_mat = totales['materiales'] - proy_materiales
                        pct_mat = calcular_porcentaje(desv_mat, proy_materiales) if proy_materiales > 0 else 0
                        st.metric(
                            "Materiales",
                            f"{'+' if desv_mat > 0 else ''}{pct_mat:.1f}%",
                            delta=formatear_moneda(desv_mat),
                            delta_color="inverse"
                        )
                    
                    with col2:
                        desv_mo = totales['mano_obra'] - proy_mano_obra
                        pct_mo = calcular_porcentaje(desv_mo, proy_mano_obra) if proy_mano_obra > 0 else 0
                        st.metric(
                            "Mano de Obra",
                            f"{'+' if desv_mo > 0 else ''}{pct_mo:.1f}%",
                            delta=formatear_moneda(desv_mo),
                            delta_color="inverse"
                        )
                    
                    with col3:
                        desv_var = totales['variables'] - proy_variables
                        pct_var = calcular_porcentaje(desv_var, proy_variables) if proy_variables > 0 else 0
                        st.metric(
                            "Variables",
                            f"{'+' if desv_var > 0 else ''}{pct_var:.1f}%",
                            delta=formatear_moneda(desv_var),
                            delta_color="inverse"
                        )
                    
                    with col4:
                        desv_admin = totales['admin'] - proy_admin
                        pct_admin = calcular_porcentaje(desv_admin, proy_admin) if proy_admin > 0 else 0
                        st.metric(
                            "Administración",
                            f"{'+' if desv_admin > 0 else ''}{pct_admin:.1f}%",
                            delta=formatear_moneda(desv_admin),
                            delta_color="inverse"
                        )
            
            except Exception as e:
                st.warning(f"⚠️ No se pudo generar comparación vs proyección: {str(e)}")
                # Continuar sin mostrar la comparación
        
        # Botón generar análisis
        st.markdown("---")
        
        if st.button("▶️ Generar Análisis de Egresos", type="primary", use_container_width=True):
            st.session_state.paso_ejecucion = 5
            st.rerun()


def consolidar_egresos_multiples_archivos(lista_datos: List[Dict]) -> Dict:
    """
    Consolida datos de múltiples archivos de egresos en uno solo
    
    Args:
        lista_datos: Lista de diccionarios con datos parseados
    
    Returns:
        Dict consolidado con estructura similar a parse_excel_egresos
    """
    if len(lista_datos) == 1:
        return lista_datos[0]
    
    # Consolidar egresos semanales
    egresos_consolidados = {}
    
    for datos in lista_datos:
        for egreso_semanal in datos['egresos_semanales']:
            semana = egreso_semanal['semana']
            
            if semana not in egresos_consolidados:
                egresos_consolidados[semana] = {
                    'semana': semana,
                    'fecha_inicio': egreso_semanal['fecha_inicio'],
                    'materiales': 0,
                    'mano_obra': 0,
                    'variables': 0,
                    'admin': 0,
                    'total': 0
                }
            
            egresos_consolidados[semana]['materiales'] += egreso_semanal['materiales']
            egresos_consolidados[semana]['mano_obra'] += egreso_semanal['mano_obra']
            egresos_consolidados[semana]['variables'] += egreso_semanal['variables']
            egresos_consolidados[semana]['admin'] += egreso_semanal['admin']
            egresos_consolidados[semana]['total'] += egreso_semanal['total']
    
    # Convertir a lista ordenada
    egresos_semanales_final = sorted(egresos_consolidados.values(), key=lambda x: x['semana'])
    
    # Calcular totales acumulados
    totales_acumulados = {
        'materiales': sum([e['materiales'] for e in egresos_semanales_final]),
        'mano_obra': sum([e['mano_obra'] for e in egresos_semanales_final]),
        'variables': sum([e['variables'] for e in egresos_semanales_final]),
        'admin': sum([e['admin'] for e in egresos_semanales_final]),
        'total': sum([e['total'] for e in egresos_semanales_final])
    }
    
    # Consolidar metadatos
    archivos_nombres = [d['archivo'] for d in lista_datos]
    registros_totales = sum([d['registros_procesados'] for d in lista_datos])
    semana_ultima = max([d['semana_ultima'] for d in lista_datos])
    
    # Consolidar cuentas sin clasificar
    cuentas_sin_clasificar = []
    for datos in lista_datos:
        cuentas_sin_clasificar.extend(datos.get('cuentas_sin_clasificar', []))
    cuentas_sin_clasificar = list(set(cuentas_sin_clasificar))  # Eliminar duplicados
    
    return {
        'archivo': f"{len(lista_datos)} archivos: {', '.join(archivos_nombres)}",
        'fecha_proceso': datetime.now().isoformat(),
        'semana_ultima': semana_ultima,
        'periodo_covered': "Consolidado",
        'registros_procesados': registros_totales,
        'egresos_semanales': egresos_semanales_final,
        'totales_acumulados': totales_acumulados,
        'cuentas_sin_clasificar': cuentas_sin_clasificar
    }


# ============================================================================
# FUNCIONES PRINCIPALES - NAVEGACIÓN Y ESTRUCTURA MODULAR
# ============================================================================

def main():
    """Función principal del módulo de ejecución real FCL"""
    
    st.title("💼 SICONE - Ejecución Real FCL")
    st.caption("Análisis de FCL Real Ejecutado vs FCL Planeado")
    
    # Inicializar paso si no existe
    if 'paso_ejecucion' not in st.session_state:
        st.session_state.paso_ejecucion = 1
    
    # Inicializar módulo activo si no existe (futuro: 'cartera' o 'egresos')
    if 'modulo_ejecucion_activo' not in st.session_state:
        st.session_state.modulo_ejecucion_activo = 'cartera'  # Solo cartera en v1.0
    
    # =======================================================================
    # NOTA DESARROLLO MODULAR:
    # El sistema está diseñado para 2 módulos integrados:
    # 1. CARTERA (Ingresos Reales) - Pasos 1-3 ✅
    # 2. EGRESOS REALES (Gastos) - Pasos 4-5 ✅
    # 3. ANÁLISIS FCL COMPLETO - Paso 6 🔜
    # 
    # Flujo:
    # Paso 1: Cargar Proyección
    # Paso 2: Ingresar Cartera (ingresos reales)
    # Paso 3: Análisis Cartera
    # Paso 4: Ingresar Egresos (gastos reales)
    # Paso 5: Análisis Egresos
    # Paso 6: Análisis FCL Completo (ingresos + egresos)
    # =======================================================================
    
    paso = st.session_state.paso_ejecucion
    
    # Indicador de progreso
    progress_labels = {
        1: "📁 Cargar Proyección",
        2: "💰 Ingresar Cartera",
        3: "📊 Análisis Cartera",
        4: "💰 Ingresar Egresos",
        5: "📊 Análisis Egresos"
    }
    
    # Determinar total de pasos (5 por ahora, 6 cuando se implemente FCL completo)
    total_pasos = 5
    
    st.progress(paso / total_pasos, text=f"Paso {paso}/{total_pasos}: {progress_labels.get(paso, 'Análisis')}")
    
    st.markdown("---")
    
    # Renderizar paso correspondiente
    if paso == 1:
        render_paso_1_cargar_proyeccion()
    
    elif paso == 2:
        if 'proyeccion_cartera' not in st.session_state:
            st.error("❌ No se ha cargado una proyección. Regresando al paso 1...")
            st.session_state.paso_ejecucion = 1
            st.rerun()
        else:
            render_paso_2_ingresar_cartera()
    
    elif paso == 3:
        if 'contratos_cartera_input' not in st.session_state:
            st.error("❌ No se han ingresado datos de cartera. Regresando al paso 2...")
            st.session_state.paso_ejecucion = 2
            st.rerun()
        else:
            render_paso_3_analisis()
    
    elif paso == 4:
        if 'proyeccion_cartera' not in st.session_state:
            st.error("❌ No se ha cargado una proyección. Regresando al paso 1...")
            st.session_state.paso_ejecucion = 1
            st.rerun()
        else:
            render_paso_4_ingresar_egresos()
    
    elif paso == 5:
        if 'egresos_reales_input' not in st.session_state:
            st.error("❌ No se han ingresado datos de egresos. Regresando al paso 4...")
            st.session_state.paso_ejecucion = 4
            st.rerun()
        else:
            render_paso_5_analisis_egresos()


# ============================================================================
# COMPONENTES DE INTERFAZ - PASO 5: ANÁLISIS DE EGRESOS
# ============================================================================

def render_paso_5_analisis_egresos():
    """Paso 5: Análisis de egresos reales vs proyectados"""
    
    st.header("📊 Análisis de Egresos - Gastos Reales vs Proyectados")
    st.caption("📍 Módulo 2: EGRESOS | Dashboard de análisis de gastos")
    
    # Botón cargar otra proyección
    mostrar_boton_cargar_otra_proyeccion()
    
    # Botón volver
    col_v1, col_v2 = st.columns([1, 4])
    with col_v1:
        if st.button("◀️ Editar Datos"):
            st.session_state.paso_ejecucion = 4
            st.rerun()
    
    st.markdown("---")
    
    # TODO: Implementar análisis completo de egresos
    # Por ahora, mostrar placeholder
    
    st.info("""
    ### 🚧 En Desarrollo
    
    **Próximas funcionalidades (v1.1.0):**
    
    1. **KPIs de Egresos:**
       - Total gastado vs presupuestado
       - Desviación por categoría
       - Estado de ejecución presupuestal
    
    2. **Gráfica Proyección vs Real:**
       - Egresos proyectados acumulados
       - Gastos reales acumulados
       - Línea de semana actual
    
    3. **Comparación por Categoría:**
       - Materiales: Proyectado vs Real
       - Mano de Obra: Proyectado vs Real
       - Variables: Proyectado vs Real
       - Administración: Proyectado vs Real
    
    4. **Sistema de Alertas:**
       - Sobrecostos por categoría
       - Tendencias de gasto
       - Proyecciones de déficit
    
    5. **Exportación JSON v4.0:**
       - Proyección + Cartera + Egresos
    """)
    
    # Mostrar datos cargados (preview)
    if 'egresos_reales_input' in st.session_state:
        datos = st.session_state.egresos_reales_input
        
        st.markdown("### 📊 Datos Cargados")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Gastado", formatear_moneda(datos['totales_acumulados']['total']))
        
        with col2:
            st.metric("Semanas", f"1 a {datos['semana_ultima']}")
        
        with col3:
            st.metric("Registros", f"{datos['registros_procesados']:,}")
    
    # Botón temporal para regresar
    st.markdown("---")
    
    if st.button("◀️ Volver a Cartera", use_container_width=True):
        st.session_state.paso_ejecucion = 3
        st.rerun()


# ============================================================================
# PLACEHOLDER PARA FUTURO MÓDULO DE EGRESOS REALES (v1.1.0+)
# ============================================================================

# TODO v1.1.0: Agregar funciones para módulo de egresos
# 
# def render_paso_1_cargar_proyeccion_egresos():
#     """Paso 1: Cargar proyección para análisis de egresos"""
#     pass
#
# def render_paso_2_ingresar_egresos():
#     """Paso 2: Ingresar/parsear egresos reales desde contabilidad"""
#     # Estructura del Excel de ejecución (AÑO_2025_OBRA_CARLOS_VELEZ.xlsx):
#     # - Encabezados en fila 8
#     # - Columnas: Código contable, Cuenta, Fecha elaboración, Débito
#     # - Mapeo de cuentas a categorías de proyección:
#     #   71050501 (Materia prima) → Materiales
#     #   71050502 (Materiales de Operación) → Materiales
#     #   71XXXXX (Mano de Obra) → Mano_Obra
#     #   etc.
#     # - Agrupar por semana y categoría
#     pass
#
# def render_paso_3_analisis_egresos():
#     """Paso 3: Análisis de egresos reales vs proyectados"""
#     # KPIs:
#     # - Total gastado vs presupuestado
#     # - Desviación por categoría (Materiales, MO, Equipos, Admin, etc.)
#     # - Alertas de sobrecostos por categoría
#     # - Gráfica: Egresos proyectados vs reales por semana (acumulado)
#     # - Tabla: Egresos por categoría (proyectado vs real)
#     pass
#
# def render_paso_4_analisis_fcl_completo():
#     """Paso 4: Análisis FCL completo (ingresos + egresos)"""
#     # Dashboard consolidado:
#     # - Gráfica FCL: Ingresos, Egresos, Flujo Neto (proyectado vs real)
#     # - Saldo acumulado proyectado vs real
#     # - KPIs integrados:
#     #   - Margen neto proyectado vs real
#     #   - Desviación en flujo de caja
#     #   - Semanas con saldo negativo (real vs proyectado)
#     # - Alertas consolidadas (cartera + sobrecostos)
#     pass


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    main()
