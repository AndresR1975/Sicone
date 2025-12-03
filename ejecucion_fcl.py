"""
SICONE - Módulo de Ejecución Real FCL
Análisis de FCL Real Ejecutado vs FCL Planeado

Versión: 1.0.0
Fecha: Diciembre 2024
Autor: AI-MindNovation

ESTRUCTURA MODULAR:
└── ejecucion_fcl.py
    ├── Módulo 1: CARTERA (Ingresos Reales)
    │   ├── Ingreso de cobros por hito
    │   ├── Conciliación automática
    │   ├── Comparación ingresos proyectados vs reales
    │   └── Alertas de cartera
    │
    └── Módulo 2: EGRESOS REALES (Futuro - Fase 2)
        ├── Ingreso/Parser de gastos contables
        ├── Categorización de egresos
        ├── Comparación egresos proyectados vs reales
        └── Alertas de sobrecostos

FUNCIONALIDADES ACTUALES (v1.0.0 - MÓDULO CARTERA):
- Carga de proyección desde JSON v2.0
- Ingreso de datos de cartera (hitos + pagos reales)
- Conciliación automática (detecta sobrepagos, retenciones, etc.)
- Comparación ingresos proyectados vs reales
- Generación de alertas de cartera
- Dashboard de análisis de ingresos
- Exportación JSON v3.0 (proyección + cartera)

ROADMAP:
- v1.0.0: Módulo Cartera (ingresos) ✅
- v1.1.0: Módulo Egresos Reales (gastos) 🔜
- v1.2.0: Análisis FCL completo (ingresos + egresos) 🔜
- v1.3.0: Dashboard consolidado multiproyectos 🔜
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
            f"💎 Hito {hito['id']}: {hito['nombre']} - {formatear_moneda(hito['monto'])}", 
            expanded=len(st.session_state.pagos_por_hito.get(hito_id, [])) == 0
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
            
            for cont_key in contratos_keys:
                if cont_key not in contratos_dict:
                    # Buscar info del contrato en proyección
                    cont_data = proyeccion['contratos'].get(cont_key, {})
                    contratos_dict[cont_key] = {
                        'numero': cont_key,
                        'descripcion': cont_data.get('nombre', ''),
                        'monto': cont_data.get('monto', 0),
                        'hitos': []
                    }
                
                # Agregar hito a contrato
                pagos_hito = st.session_state.pagos_por_hito.get(hito_id, [])
                
                contratos_dict[cont_key]['hitos'].append({
                    'numero': hito['id'],
                    'descripcion': hito['nombre'],
                    'monto_esperado': hito['monto'],
                    'semana_esperada': 1,  # TODO: calcular desde fase_vinculada
                    'fecha_vencimiento': None,
                    'pagos': pagos_hito
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
    
    # Botón volver
    col_v1, col_v2 = st.columns([1, 4])
    with col_v1:
        if st.button("◀️ Editar Datos"):
            st.session_state.paso_ejecucion = 2
            st.rerun()
    
    proyeccion = st.session_state.proyeccion_cartera
    contratos_cartera = st.session_state.contratos_cartera_input
    fecha_corte = st.session_state.widget_fecha_corte_cartera  # Leer del widget
    
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
    # El sistema está diseñado para 2 módulos:
    # 1. CARTERA (Ingresos Reales) - v1.0.0 ✅
    # 2. EGRESOS REALES (Gastos) - v1.1.0 🔜
    # 
    # Estructura futura (v1.1.0+):
    # - Usuario selecciona módulo (tabs o sidebar)
    # - Cada módulo tiene sus propios pasos
    # - Al final: análisis integrado FCL completo
    # =======================================================================
    
    # Por ahora, solo módulo de cartera
    paso = st.session_state.paso_ejecucion
    
    # Indicador de progreso
    progress_labels = {
        1: "📁 Cargar Proyección",
        2: "💰 Ingresar Cartera",
        3: "📊 Análisis"
    }
    
    st.progress(paso / 3, text=f"Paso {paso}/3: {progress_labels[paso]}")
    
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
