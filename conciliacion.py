"""
SICONE - Interfaz de Conciliación Financiera
============================================

PROPÓSITO:
----------
Interfaz Streamlit para conciliación que permite:
- Configurar período de análisis
- Cargar datos SICONE consolidados
- Ingresar saldos reales separados por cuenta (Fiducuenta + Cuenta Bancaria)
- Sumar para comparar vs consolidado SICONE
- Documentar ajustes estructurados por cuenta
- Calcular y visualizar resultados

MODELO OPERATIVO:
-----------------
SICONE trabaja con saldo consolidado total
REALIDAD tiene dos cuentas:
  - Fiducuenta: Reserva de efectivo con rendimientos
  - Cuenta Bancaria: Gestión operativa de proyectos
CONCILIACIÓN compara suma de cuentas reales vs consolidado SICONE

DISEÑO:
-------
Capa de presentación únicamente. Toda la lógica está en
modules/conciliacion_core.py para facilitar migración futura a Odoo.

AUTOR: Andrés
FECHA: Enero 2025
VERSIÓN: 1.0 MVP
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
import json
from pathlib import Path
import sys

# Importar módulo core (lógica de negocio)
# Ajustar path según ubicación de tu instalación
try:
    from modules.conciliacion_core import (
        ConciliadorSICONE,
        SaldosCuenta,
        Ajuste,
        ResultadoConciliacion,
        formatear_moneda
    )
except ImportError:
    # Si falla, agregar path manualmente
    sys.path.append(str(Path(__file__).parent.parent))
    from modules.conciliacion_core import (
        ConciliadorSICONE,
        SaldosCuenta,
        Ajuste,
        ResultadoConciliacion,
        formatear_moneda
    )

# ============================================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================================

st.set_page_config(
    page_title="SICONE - Conciliación",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# ESTILOS CSS PERSONALIZADOS
# ============================================================================

st.markdown("""
<style>
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .status-aprobado {
        color: #28a745;
        font-weight: bold;
    }
    .status-revisar {
        color: #ffc107;
        font-weight: bold;
    }
    .status-critico {
        color: #dc3545;
        font-weight: bold;
    }
    .stExpander {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
    }
    .info-box {
        background-color: #e7f3ff;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #2196F3;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# INICIALIZACIÓN DE SESSION STATE
# ============================================================================

def inicializar_session_state():
    """
    Inicializa variables de session_state si no existen.
    
    Session state mantiene el estado de la aplicación entre reruns.
    """
    if 'conciliador' not in st.session_state:
        st.session_state.conciliador = None
    
    if 'ajustes_df' not in st.session_state:
        st.session_state.ajustes_df = pd.DataFrame(columns=[
            'Fecha', 'Cuenta', 'Categoría', 'Concepto', 
            'Monto', 'Tipo', 'Evidencia', 'Observaciones'
        ])
    
    if 'saldos_reales_configurados' not in st.session_state:
        st.session_state.saldos_reales_configurados = False
    
    if 'datos_sicone_cargados' not in st.session_state:
        st.session_state.datos_sicone_cargados = False
    
    if 'resultados_conciliacion' not in st.session_state:
        st.session_state.resultados_conciliacion = None
    
    if 'mostrar_ayuda' not in st.session_state:
        st.session_state.mostrar_ayuda = False

inicializar_session_state()

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def calcular_total_consolidado_real():
    """Calcula el total consolidado real sumando ambas cuentas"""
    if not st.session_state.saldos_reales_configurados:
        return None
    
    fidu = st.session_state.conciliador.saldos_reales.get("Fiducuenta")
    banco = st.session_state.conciliador.saldos_reales.get("Cuenta Bancaria")
    
    if not fidu or not banco:
        return None
    
    return {
        "saldo_inicial": fidu.saldo_inicial + banco.saldo_inicial,
        "saldo_final": fidu.saldo_final + banco.saldo_final,
        "movimiento_neto": (fidu.saldo_final + banco.saldo_final) - 
                          (fidu.saldo_inicial + banco.saldo_inicial)
    }

def obtener_diferencia_vs_sicone():
    """Calcula diferencia entre consolidado real y SICONE"""
    consolidado_real = calcular_total_consolidado_real()
    if not consolidado_real:
        return None
    
    if not st.session_state.datos_sicone_cargados:
        return None
    
    datos_sicone = st.session_state.conciliador.datos_sicone_procesados
    consolidado_sicone = datos_sicone.get("Consolidado", {})
    
    return {
        "saldo_inicial": consolidado_real["saldo_inicial"] - consolidado_sicone.get("saldo_inicial", 0),
        "saldo_final": consolidado_real["saldo_final"] - consolidado_sicone.get("saldo_final", 0),
        "movimiento_neto": consolidado_real["movimiento_neto"] - 
                          (consolidado_sicone.get("ingresos", 0) - consolidado_sicone.get("egresos", 0))
    }

# ============================================================================
# HEADER
# ============================================================================

col_titulo, col_ayuda = st.columns([4, 1])

with col_titulo:
    st.title("🔍 Conciliación Financiera SICONE")

with col_ayuda:
    if st.button("❓ Ayuda", use_container_width=True):
        st.session_state.mostrar_ayuda = not st.session_state.mostrar_ayuda

if st.session_state.mostrar_ayuda:
    st.markdown("""
    <div class='info-box'>
        <h4 style='margin: 0; color: #1976D2;'>💡 Cómo Funciona Este Módulo</h4>
        <ul style='margin: 10px 0 0 0;'>
            <li><strong>SICONE</strong> trabaja con saldo consolidado total (suma de todas las cuentas)</li>
            <li><strong>Realidad bancaria</strong> tiene 2 cuentas separadas:
                <ul>
                    <li>🏦 <strong>Fiducuenta:</strong> Reserva de efectivo con rendimientos</li>
                    <li>💳 <strong>Cuenta Bancaria:</strong> Operación diaria de proyectos</li>
                </ul>
            </li>
            <li><strong>Este módulo</strong> te permite:
                <ol>
                    <li>Ingresar saldos reales de cada cuenta por separado</li>
                    <li>Compara la suma vs proyección SICONE</li>
                    <li>Documenta ajustes que explican diferencias</li>
                    <li>Calcula precisión del modelo</li>
                </ol>
            </li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class='info-box'>
    <h4 style='margin: 0; color: #1976D2;'>Verificación de Precisión SICONE</h4>
    <p style='margin: 5px 0 0 0; color: #555;'>
        Compara proyecciones del modelo contra realidad bancaria, documenta ajustes y 
        calcula diferencias residuales para validación de go-live y seguimiento mensual.
    </p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ============================================================================
# SIDEBAR: CONFIGURACIÓN Y NAVEGACIÓN
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Estado de la conciliación
    st.subheader("Estado del Proceso")
    
    estado_items = [
        ("📅 Período", st.session_state.conciliador is not None),
        ("📊 Datos SICONE", st.session_state.datos_sicone_cargados),
        ("💰 Saldos Reales", st.session_state.saldos_reales_configurados),
        ("🔍 Conciliación", st.session_state.resultados_conciliacion is not None)
    ]
    
    for item, completado in estado_items:
        icon = "✅" if completado else "⭕"
        st.text(f"{icon} {item}")
    
    # Mostrar diferencia preliminar si hay datos
    if st.session_state.datos_sicone_cargados and st.session_state.saldos_reales_configurados:
        diferencia = obtener_diferencia_vs_sicone()
        if diferencia:
            st.divider()
            st.subheader("⚡ Vista Rápida")
            st.metric(
                "Diferencia Saldo Final",
                formatear_moneda(abs(diferencia["saldo_final"])),
                delta=f"{diferencia['saldo_final']:+,.0f}".replace(",", "."),
                delta_color="inverse"
            )
            
            if abs(diferencia["saldo_final"]) > 50_000_000:
                st.warning("⚠️ Diferencia significativa detectada")
    
    st.divider()
    
    # Acciones rápidas
    st.subheader("Acciones Rápidas")
    
    if st.button("🔄 Nueva Conciliación", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key not in ['mostrar_ayuda']:
                del st.session_state[key]
        inicializar_session_state()
        st.rerun()
    
    if st.session_state.resultados_conciliacion:
        if st.button("📊 Ver Resumen", use_container_width=True):
            st.session_state.scroll_to_results = True

# ============================================================================
# PASO 1: CONFIGURACIÓN DEL PERÍODO
# ============================================================================

with st.expander("📅 PASO 1: Configuración del Período", expanded=not st.session_state.conciliador):
    st.markdown("""
    **Instrucciones:** Define el período que deseas conciliar. Este debe coincidir 
    con el período de tus extractos bancarios.
    
    📌 **Nota:** El período se basa en las fechas disponibles en el JSON consolidado SICONE.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fecha_inicio = st.date_input(
            "Fecha de Inicio",
            value=date(2025, 1, 1),
            help="Primer día del período a conciliar"
        )
    
    with col2:
        fecha_fin = st.date_input(
            "Fecha de Fin",
            value=date(2025, 1, 31),
            help="Último día del período a conciliar"
        )
    
    # Validar fechas
    if fecha_inicio >= fecha_fin:
        st.error("⚠️ La fecha de inicio debe ser anterior a la fecha de fin")
    else:
        dias_periodo = (fecha_fin - fecha_inicio).days + 1
        
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.info(f"📊 Período: {dias_periodo} días ({dias_periodo/7:.1f} semanas)")
        with col_info2:
            st.info(f"📆 {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}")
        
        if st.button("✅ Confirmar Período", type="primary", use_container_width=True):
            # Crear instancia de conciliador
            st.session_state.conciliador = ConciliadorSICONE(
                fecha_inicio=fecha_inicio.isoformat(),
                fecha_fin=fecha_fin.isoformat()
            )
            st.success(f"✅ Período configurado: {fecha_inicio} a {fecha_fin}")
            st.rerun()

# ============================================================================
# PASO 2: CARGA DE DATOS SICONE
# ============================================================================

if st.session_state.conciliador:
    with st.expander("📊 PASO 2: Datos SICONE (Proyectados)", expanded=not st.session_state.datos_sicone_cargados):
        st.markdown("""
        **Instrucciones:** Carga el archivo JSON consolidado de SICONE para extraer 
        las proyecciones del período seleccionado.
        
        🔍 **Qué hace el sistema:**
        - Extrae datos del consolidado multiproyecto
        - Identifica el período seleccionado
        - Calcula saldos, ingresos y egresos proyectados
        """)
        
        uploaded_json = st.file_uploader(
            "📁 Selecciona el archivo consolidado_multiproyecto.json",
            type=['json'],
            help="Archivo JSON generado por el módulo de análisis consolidado"
        )
        
        if uploaded_json:
            if st.button("📥 Cargar y Procesar JSON", type="primary"):
                with st.spinner("Cargando y extrayendo datos..."):
                    try:
                        datos = json.load(uploaded_json)
                        success = st.session_state.conciliador.cargar_datos_sicone(
                            datos_dict=datos
                        )
                        
                        if success:
                            st.session_state.datos_sicone_cargados = True
                            st.success("✅ Datos SICONE cargados correctamente")
                            
                            # Mostrar resumen detallado
                            with st.container():
                                st.subheader("📋 Resumen de Datos Extraídos")
                                
                                datos_proc = st.session_state.conciliador.datos_sicone_procesados
                                metadata = datos_proc.get("metadata", {})
                                consolidado = datos_proc.get("Consolidado", {})
                                
                                # Metadata del período
                                col_meta1, col_meta2, col_meta3 = st.columns(3)
                                with col_meta1:
                                    st.metric("Período Real", 
                                             f"{metadata.get('fecha_inicio_real')} → {metadata.get('fecha_fin_real')}")
                                with col_meta2:
                                    st.metric("Semanas Analizadas", metadata.get('semanas_analizadas', 0))
                                with col_meta3:
                                    tiene_hist = metadata.get('tiene_datos_historicos', False)
                                    st.metric("Tipo de Datos", "Histórico + Proy." if tiene_hist else "Solo Proyección")
                                
                                st.divider()
                                
                                # Datos consolidados SICONE
                                st.markdown("**💰 Saldo Consolidado SICONE (Total de Ambas Cuentas)**")
                                
                                col_saldo1, col_saldo2, col_saldo3, col_saldo4 = st.columns(4)
                                
                                with col_saldo1:
                                    st.metric(
                                        "Saldo Inicial",
                                        formatear_moneda(consolidado['saldo_inicial'])
                                    )
                                
                                with col_saldo2:
                                    st.metric(
                                        "Ingresos Proyectados",
                                        formatear_moneda(consolidado['ingresos']),
                                        delta="Ingresos"
                                    )
                                
                                with col_saldo3:
                                    st.metric(
                                        "Egresos Proyectados",
                                        formatear_moneda(consolidado['egresos']),
                                        delta="Egresos",
                                        delta_color="inverse"
                                    )
                                
                                with col_saldo4:
                                    st.metric(
                                        "Saldo Final",
                                        formatear_moneda(consolidado['saldo_final'])
                                    )
                                
                                # Alertas de coherencia
                                mov_neto_real = consolidado['saldo_final'] - consolidado['saldo_inicial']
                                mov_esperado = consolidado['ingresos'] - consolidado['egresos']
                                diferencia_calc = abs(mov_neto_real - mov_esperado)
                                
                                if diferencia_calc > 1000:
                                    st.warning(
                                        f"⚠️ Alerta: Hay una diferencia de {formatear_moneda(diferencia_calc)} "
                                        f"entre el movimiento neto real y el calculado. "
                                        f"Esto es normal si hay datos históricos reales vs proyecciones."
                                    )
                                else:
                                    st.success("✅ Los cálculos son coherentes")
                            
                            st.rerun()
                        else:
                            st.error("❌ Error al cargar datos. Verifica la estructura del JSON y el período seleccionado.")
                    
                    except json.JSONDecodeError:
                        st.error("❌ Error: El archivo no es un JSON válido")
                    except Exception as e:
                        st.error(f"❌ Error inesperado: {str(e)}")

# ============================================================================
# PASO 3: INGRESO DE SALDOS REALES
# ============================================================================

if st.session_state.datos_sicone_cargados:
    with st.expander("💰 PASO 3: Saldos Bancarios Reales (Por Cuenta)", expanded=not st.session_state.saldos_reales_configurados):
        st.markdown("""
        **Instrucciones:** Ingresa los saldos reales de cada cuenta bancaria para el 
        período seleccionado. Estos datos provienen de tus extractos bancarios.
        
        📌 **Modelo Operativo:**
        - **Fiducuenta:** Reserva de efectivo con rendimientos
        - **Cuenta Bancaria:** Gestión operativa diaria de proyectos
        - **Total:** Se suma automáticamente para comparar vs SICONE
        """)
        
        st.subheader("Ingreso de Saldos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏦 Fiducuenta")
            st.caption("Cuenta de reserva y rendimientos")
            
            fidu_saldo_ini = st.number_input(
                "Saldo Inicial ($)",
                min_value=0.0,
                step=1000000.0,
                format="%.2f",
                key="fidu_ini",
                help="Saldo al inicio del período según extracto"
            )
            fidu_saldo_fin = st.number_input(
                "Saldo Final ($)",
                min_value=0.0,
                step=1000000.0,
                format="%.2f",
                key="fidu_fin",
                help="Saldo al final del período según extracto"
            )
            
            if fidu_saldo_ini > 0 and fidu_saldo_fin > 0:
                mov_neto_fidu = fidu_saldo_fin - fidu_saldo_ini
                st.metric(
                    "Movimiento Neto", 
                    formatear_moneda(abs(mov_neto_fidu)),
                    delta=f"{mov_neto_fidu:+,.0f}".replace(",", "."),
                    delta_color="normal" if mov_neto_fidu >= 0 else "inverse"
                )
        
        with col2:
            st.markdown("### 💳 Cuenta Bancaria")
            st.caption("Operación de proyectos")
            
            banco_saldo_ini = st.number_input(
                "Saldo Inicial ($)",
                min_value=0.0,
                step=1000000.0,
                format="%.2f",
                key="banco_ini",
                help="Saldo al inicio del período según extracto"
            )
            banco_saldo_fin = st.number_input(
                "Saldo Final ($)",
                min_value=0.0,
                step=1000000.0,
                format="%.2f",
                key="banco_fin",
                help="Saldo al final del período según extracto"
            )
            
            if banco_saldo_ini > 0 and banco_saldo_fin > 0:
                mov_neto_banco = banco_saldo_fin - banco_saldo_ini
                st.metric(
                    "Movimiento Neto", 
                    formatear_moneda(abs(mov_neto_banco)),
                    delta=f"{mov_neto_banco:+,.0f}".replace(",", "."),
                    delta_color="normal" if mov_neto_banco >= 0 else "inverse"
                )
        
        # Resumen consolidado
        if all([fidu_saldo_ini, fidu_saldo_fin, banco_saldo_ini, banco_saldo_fin]):
            st.divider()
            st.subheader("📊 Consolidado Real (Suma de Ambas Cuentas)")
            
            total_ini = fidu_saldo_ini + banco_saldo_ini
            total_fin = fidu_saldo_fin + banco_saldo_fin
            total_mov = total_fin - total_ini
            
            col_t1, col_t2, col_t3 = st.columns(3)
            
            with col_t1:
                st.metric("Saldo Inicial Total", formatear_moneda(total_ini))
            with col_t2:
                st.metric("Saldo Final Total", formatear_moneda(total_fin))
            with col_t3:
                st.metric(
                    "Movimiento Neto Total",
                    formatear_moneda(abs(total_mov)),
                    delta=f"{total_mov:+,.0f}".replace(",", ".")
                )
            
            # Comparación preliminar vs SICONE
            datos_sicone = st.session_state.conciliador.datos_sicone_procesados
            consolidado_sicone = datos_sicone.get("Consolidado", {})
            
            diferencia_inicial = total_ini - consolidado_sicone.get("saldo_inicial", 0)
            diferencia_final = total_fin - consolidado_sicone.get("saldo_final", 0)
            
            st.divider()
            st.markdown("**🔍 Comparación Preliminar vs SICONE**")
            
            col_comp1, col_comp2 = st.columns(2)
            
            with col_comp1:
                st.metric(
                    "Diferencia Saldo Inicial",
                    formatear_moneda(abs(diferencia_inicial)),
                    delta=f"{diferencia_inicial:+,.0f}".replace(",", "."),
                    delta_color="off"
                )
            
            with col_comp2:
                st.metric(
                    "Diferencia Saldo Final",
                    formatear_moneda(abs(diferencia_final)),
                    delta=f"{diferencia_final:+,.0f}".replace(",", "."),
                    delta_color="off"
                )
            
            if abs(diferencia_final) > 50_000_000:
                st.warning(
                    f"⚠️ **Diferencia significativa detectada:** {formatear_moneda(abs(diferencia_final))} "
                    f"({abs(diferencia_final/total_fin*100):.1f}% del saldo final)\n\n"
                    f"Esta diferencia debe ser explicada con ajustes en el siguiente paso."
                )
            elif abs(diferencia_final) > 10_000_000:
                st.info(
                    f"ℹ️ Diferencia moderada: {formatear_moneda(abs(diferencia_final))} "
                    f"({abs(diferencia_final/total_fin*100):.1f}% del saldo final)"
                )
            else:
                st.success(
                    f"✅ Diferencia mínima: {formatear_moneda(abs(diferencia_final))} "
                    f"({abs(diferencia_final/total_fin*100):.2f}% del saldo final)"
                )
            
            st.divider()
            
            if st.button("✅ Confirmar Saldos Reales", type="primary", use_container_width=True):
                # Crear objetos SaldosCuenta
                saldos_fidu = SaldosCuenta(
                    nombre="Fiducuenta",
                    saldo_inicial=fidu_saldo_ini,
                    saldo_final=fidu_saldo_fin,
                    fuente="Manual"
                )
                
                saldos_banco = SaldosCuenta(
                    nombre="Cuenta Bancaria",
                    saldo_inicial=banco_saldo_ini,
                    saldo_final=banco_saldo_fin,
                    fuente="Manual"
                )
                
                # Configurar en el conciliador
                st.session_state.conciliador.set_saldos_reales(
                    saldos_fidu, 
                    saldos_banco
                )
                
                st.session_state.saldos_reales_configurados = True
                st.success("✅ Saldos reales configurados correctamente")
                st.rerun()
        else:
            st.info("👆 Ingresa todos los saldos para continuar")

# ============================================================================
# PASO 4: REGISTRO DE AJUSTES
# ============================================================================

if st.session_state.saldos_reales_configurados:
    with st.expander("📝 PASO 4: Registro de Ajustes", expanded=True):
        st.markdown("""
        **Instrucciones:** Documenta los movimientos que explican diferencias entre 
        SICONE y la realidad. 
        
        **Categorías principales:**
        - **Proyectos anteriores:** Ingresos/egresos de proyectos previos a SICONE
        - **Préstamos empleados:** Desembolsos y recuperaciones
        - **Movimientos internos:** Transferencias entre Fiducuenta ↔ Cuenta Bancaria
        - **Gastos/Ingresos no modelados:** Operaciones no contempladas en SICONE
        - **Ajuste de timing:** Diferencias en fechas de registro
        """)
        
        # Formulario para nuevo ajuste
        with st.form("form_nuevo_ajuste", clear_on_submit=True):
            st.subheader("➕ Agregar Nuevo Ajuste")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                fecha_ajuste = st.date_input(
                    "Fecha del Movimiento",
                    value=datetime.now().date(),
                    help="Fecha en que ocurrió el movimiento real"
                )
                
                cuenta_ajuste = st.selectbox(
                    "Cuenta Afectada",
                    ["Fiducuenta", "Cuenta Bancaria", "Ambas"],
                    help="Selecciona 'Ambas' para movimientos internos entre cuentas"
                )
            
            with col2:
                categoria_ajuste = st.selectbox(
                    "Categoría",
                    Ajuste.CATEGORIAS_VALIDAS,
                    help="Tipo de ajuste según naturaleza del movimiento"
                )
                
                tipo_ajuste = st.selectbox(
                    "Tipo de Movimiento",
                    ["Ingreso", "Egreso"],
                    help="Ingreso: aumenta saldo | Egreso: disminuye saldo"
                )
            
            with col3:
                monto_ajuste = st.number_input(
                    "Monto ($)",
                    min_value=0.0,
                    step=100000.0,
                    format="%.2f",
                    help="Valor del ajuste en pesos"
                )
            
            concepto_ajuste = st.text_input(
                "Concepto / Descripción",
                placeholder="Ej: Pago proyecto ABC-2024 completado en noviembre, Préstamo a Juan Pérez, etc.",
                help="Descripción clara y específica del ajuste"
            )
            
            col_ev, col_obs = st.columns(2)
            
            with col_ev:
                evidencia_ajuste = st.text_input(
                    "Evidencia (Opcional)",
                    placeholder="Ej: extracto_enero.pdf, email_confirmacion.pdf, factura_123",
                    help="Referencia a documento soporte"
                )
            
            with col_obs:
                observaciones_ajuste = st.text_area(
                    "Observaciones (Opcional)",
                    placeholder="Información adicional, contexto o notas",
                    height=100,
                    help="Detalles adicionales sobre el ajuste"
                )
            
            col_submit1, col_submit2 = st.columns([3, 1])
            
            with col_submit2:
                submitted = st.form_submit_button("➕ Agregar", type="primary", use_container_width=True)
            
            if submitted:
                if monto_ajuste > 0 and concepto_ajuste:
                    # Crear objeto Ajuste
                    nuevo_ajuste = Ajuste(
                        fecha=fecha_ajuste.isoformat(),
                        cuenta=cuenta_ajuste,
                        categoria=categoria_ajuste,
                        concepto=concepto_ajuste,
                        monto=monto_ajuste,
                        tipo=tipo_ajuste,
                        evidencia=evidencia_ajuste,
                        observaciones=observaciones_ajuste
                    )
                    
                    # Validar y agregar
                    valido, mensaje = nuevo_ajuste.validar()
                    
                    if valido:
                        exito, msg = st.session_state.conciliador.agregar_ajuste(nuevo_ajuste)
                        
                        if exito:
                            # Agregar a DataFrame para visualización
                            nuevo_registro = pd.DataFrame([{
                                'Fecha': fecha_ajuste,
                                'Cuenta': cuenta_ajuste,
                                'Categoría': categoria_ajuste,
                                'Concepto': concepto_ajuste,
                                'Monto': monto_ajuste,
                                'Tipo': tipo_ajuste,
                                'Evidencia': evidencia_ajuste,
                                'Observaciones': observaciones_ajuste
                            }])
                            
                            st.session_state.ajustes_df = pd.concat([
                                st.session_state.ajustes_df,
                                nuevo_registro
                            ], ignore_index=True)
                            
                            st.success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                    else:
                        st.error(f"❌ {mensaje}")
                else:
                    st.warning("⚠️ Debes ingresar al menos el Monto y el Concepto")
        
        st.divider()
        
        # Mostrar tabla de ajustes registrados
        if not st.session_state.ajustes_df.empty:
            st.subheader("📋 Ajustes Registrados")
            
            # Opciones de vista
            vista_tab1, vista_tab2 = st.tabs(["📊 Tabla Completa", "📈 Análisis"])
            
            with vista_tab1:
                # Formatear DataFrame para visualización
                df_display = st.session_state.ajustes_df.copy()
                df_display['Monto'] = df_display['Monto'].apply(lambda x: formatear_moneda(x))
                
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    height=400
                )
                
                # Opciones de gestión
                col_gest1, col_gest2 = st.columns([3, 1])
                with col_gest2:
                    if st.button("🗑️ Limpiar Todos", use_container_width=True):
                        st.session_state.ajustes_df = pd.DataFrame(columns=[
                            'Fecha', 'Cuenta', 'Categoría', 'Concepto', 
                            'Monto', 'Tipo', 'Evidencia', 'Observaciones'
                        ])
                        st.session_state.conciliador.ajustes = []
                        st.rerun()
            
            with vista_tab2:
                # Resumen por categoría
                st.markdown("**📊 Resumen por Categoría**")
                
                resumen = st.session_state.conciliador.generar_resumen_ajustes()
                
                if resumen:
                    # Convertir a DataFrame para visualización
                    resumen_data = []
                    for cat, datos in resumen.items():
                        resumen_data.append({
                            'Categoría': cat,
                            'Ingresos': formatear_moneda(datos['ingresos']),
                            'Egresos': formatear_moneda(datos['egresos']),
                            'Neto': formatear_moneda(datos['neto']),
                            'Cantidad': datos['cantidad']
                        })
                    
                    df_resumen = pd.DataFrame(resumen_data)
                    st.dataframe(df_resumen, use_container_width=True, hide_index=True)
                    
                    # Gráfico de composición
                    fig_comp = px.pie(
                        st.session_state.ajustes_df,
                        names='Categoría',
                        values='Monto',
                        title='Composición de Ajustes por Categoría',
                        hole=0.3
                    )
                    st.plotly_chart(fig_comp, use_container_width=True)
                    
                    # Gráfico por cuenta
                    fig_cuenta = px.bar(
                        st.session_state.ajustes_df,
                        x='Cuenta',
                        y='Monto',
                        color='Tipo',
                        title='Ajustes por Cuenta y Tipo',
                        barmode='group'
                    )
                    st.plotly_chart(fig_cuenta, use_container_width=True)
            
            # Validaciones automáticas
            st.divider()
            st.subheader("✅ Validaciones Automáticas")
            
            col_val1, col_val2 = st.columns(2)
            
            with col_val1:
                # Validar movimientos internos
                valido_mov_int, mensaje_mov_int = st.session_state.conciliador.validar_movimientos_internos()
                
                if valido_mov_int:
                    st.success(mensaje_mov_int)
                else:
                    st.error(mensaje_mov_int)
            
            with col_val2:
                # Validar ajustes grandes
                ajustes_grandes = st.session_state.conciliador.validar_ajustes_grandes()
                
                if ajustes_grandes:
                    st.warning(f"⚠️ {len(ajustes_grandes)} ajuste(s) > $50M")
                    with st.expander("Ver detalles"):
                        for aj in ajustes_grandes:
                            st.text(f"• {aj.concepto}: {formatear_moneda(aj.monto)}")
                else:
                    st.success("✅ No hay ajustes grandes inusuales")
        
        else:
            st.info("""
            ℹ️ **No hay ajustes registrados aún**
            
            Si las diferencias entre SICONE y la realidad son significativas, 
            debes documentar los movimientos que las explican usando el formulario superior.
            
            **Consejo:** Empieza por los ajustes más grandes y obvios (ej: proyectos anteriores, 
            préstamos conocidos) y luego refina con ajustes menores.
            """)

# ============================================================================
# PASO 5: CÁLCULO Y RESULTADOS
# ============================================================================

if st.session_state.saldos_reales_configurados:
    st.divider()
    
    col_calc1, col_calc2, col_calc3 = st.columns([2, 1, 2])
    
    with col_calc2:
        if st.button("🔍 CALCULAR CONCILIACIÓN", type="primary", use_container_width=True, key="btn_calcular_principal"):
            with st.spinner("Calculando conciliación..."):
                try:
                    resultados = st.session_state.conciliador.calcular_conciliacion()
                    st.session_state.resultados_conciliacion = resultados
                    st.success("✅ Conciliación calculada exitosamente")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al calcular conciliación: {str(e)}")

# ============================================================================
# VISUALIZACIÓN DE RESULTADOS
# ============================================================================

if st.session_state.resultados_conciliacion:
    st.divider()
    st.header("📊 Resultados de la Conciliación")
    
    resultados = st.session_state.resultados_conciliacion
    
    # Calcular métricas consolidadas
    # Sumar saldos reales de ambas cuentas
    saldo_real_total = sum(r.saldo_final_real for r in resultados.values())
    saldo_conciliado_total = sum(r.saldo_conciliado for r in resultados.values())
    diferencia_total = sum(r.diferencia_residual for r in resultados.values())
    
    # Calcular precisión consolidada
    if saldo_real_total != 0:
        precision_consolidada = 100 * (1 - abs(diferencia_total) / abs(saldo_real_total))
    else:
        precision_consolidada = 0.0
    
    # Métricas principales
    st.subheader("📈 Resumen Ejecutivo")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Saldo Real Total",
            formatear_moneda(saldo_real_total),
            help="Suma de Fiducuenta + Cuenta Bancaria"
        )
    
    with col2:
        st.metric(
            "Saldo Conciliado",
            formatear_moneda(saldo_conciliado_total),
            help="SICONE + Ajustes documentados"
        )
    
    with col3:
        st.metric(
            "Diferencia Residual",
            formatear_moneda(abs(diferencia_total)),
            delta=f"{diferencia_total:+,.0f}".replace(",", "."),
            delta_color="inverse",
            help="Diferencia aún sin explicar"
        )
    
    with col4:
        # Status general
        if precision_consolidada >= 98:
            status = "✅ APROBADO"
            color = "green"
        elif precision_consolidada >= 95:
            status = "⚠️ REVISAR"
            color = "orange"
        else:
            status = "🚨 CRÍTICO"
            color = "red"
        
        st.markdown(f"<h2 style='color: {color}; text-align: center;'>{status}</h2>", unsafe_allow_html=True)
        st.metric(
            "Precisión Total",
            f"{precision_consolidada:.2f}%",
            help="Precisión del modelo considerando ajustes"
        )
    
    # Métricas adicionales
    col_add1, col_add2, col_add3 = st.columns(3)
    
    with col_add1:
        total_ajustes = len(st.session_state.conciliador.ajustes)
        st.metric("Ajustes Documentados", total_ajustes)
    
    with col_add2:
        total_monto_ajustes = sum(aj.monto for aj in st.session_state.conciliador.ajustes)
        st.metric("Monto Total Ajustes", formatear_moneda(total_monto_ajustes))
    
    with col_add3:
        pct_explicado = (1 - abs(diferencia_total) / abs(saldo_real_total)) * 100 if saldo_real_total != 0 else 0
        st.metric("% Explicado", f"{pct_explicado:.1f}%")
    
    st.divider()
    
    # Resultados por cuenta
    tab_consolidado, tab_fiducuenta, tab_cuenta_banco = st.tabs([
        "🏢 Vista Consolidada",
        "🏦 Fiducuenta",
        "💳 Cuenta Bancaria"
    ])
    
    with tab_consolidado:
        st.subheader("📊 Análisis Consolidado")
        
        # Datos SICONE vs Real
        datos_sicone = st.session_state.conciliador.datos_sicone_procesados
        consolidado_sicone = datos_sicone.get("Consolidado", {})
        
        # Crear tabla comparativa
        comparativa_data = {
            "Concepto": [
                "Saldo Inicial",
                "Ingresos",
                "Egresos",
                "Saldo Final"
            ],
            "SICONE": [
                formatear_moneda(consolidado_sicone.get("saldo_inicial", 0)),
                formatear_moneda(consolidado_sicone.get("ingresos", 0)),
                formatear_moneda(consolidado_sicone.get("egresos", 0)),
                formatear_moneda(consolidado_sicone.get("saldo_final", 0))
            ],
            "Real": [
                formatear_moneda(sum(r.saldo_inicial_real for r in resultados.values())),
                formatear_moneda(sum(r.saldo_inicial_real for r in resultados.values()) + 
                               sum(aj.monto for aj in st.session_state.conciliador.ajustes if aj.tipo == "Ingreso") - 
                               sum(r.saldo_final_real for r in resultados.values())),
                formatear_moneda(sum(aj.monto for aj in st.session_state.conciliador.ajustes if aj.tipo == "Egreso")),
                formatear_moneda(saldo_real_total)
            ],
            "Diferencia": [
                formatear_moneda(abs(sum(r.saldo_inicial_real for r in resultados.values()) - consolidado_sicone.get("saldo_inicial", 0))),
                "-",
                "-",
                formatear_moneda(abs(diferencia_total))
            ]
        }
        
        df_comparativa = pd.DataFrame(comparativa_data)
        st.dataframe(df_comparativa, use_container_width=True, hide_index=True)
    
    # Función auxiliar para crear vista de cuenta
    def mostrar_detalle_cuenta(cuenta, resultado):
        """Muestra el detalle de conciliación de una cuenta"""
        
        # Métricas de la cuenta
        col_met1, col_met2, col_met3, col_met4 = st.columns(4)
        
        with col_met1:
            st.metric(
                "Saldo Final SICONE",
                formatear_moneda(resultado.saldo_final_sicone)
            )
        
        with col_met2:
            st.metric(
                "Saldo Final Real",
                formatear_moneda(resultado.saldo_final_real)
            )
        
        with col_met3:
            st.metric(
                "Diferencia",
                formatear_moneda(abs(resultado.diferencia_residual)),
                delta=f"{resultado.diferencia_residual:+,.0f}".replace(",", "."),
                delta_color="inverse"
            )
        
        with col_met4:
            st.metric(
                "Precisión",
                f"{resultado.precision_porcentaje:.2f}%",
                delta=resultado.get_status()
            )
        
        # Gráfico Waterfall
        st.subheader("🌊 Análisis Waterfall")
        
        fig_waterfall = go.Figure(go.Waterfall(
            name=cuenta,
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "relative", "total", "total"],
            x=[
                "Saldo Inicial<br>SICONE",
                "Ingresos<br>SICONE",
                "Egresos<br>SICONE",
                "Ajustes<br>Ingresos",
                "Ajustes<br>Egresos",
                "Saldo<br>Conciliado",
                "Saldo<br>Real"
            ],
            y=[
                resultado.saldo_inicial_sicone,
                resultado.ingresos_sicone,
                -resultado.egresos_sicone,
                resultado.ajustes_ingresos,
                -resultado.ajustes_egresos,
                resultado.saldo_conciliado,
                resultado.saldo_final_real
            ],
            text=[
                formatear_moneda(resultado.saldo_inicial_sicone),
                formatear_moneda(resultado.ingresos_sicone),
                formatear_moneda(resultado.egresos_sicone),
                formatear_moneda(resultado.ajustes_ingresos),
                formatear_moneda(resultado.ajustes_egresos),
                formatear_moneda(resultado.saldo_conciliado),
                formatear_moneda(resultado.saldo_final_real)
            ],
            textposition="outside",
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#ff6b6b"}},
            increasing={"marker": {"color": "#51cf66"}},
            totals={"marker": {"color": "#339af0"}}
        ))
        
        fig_waterfall.update_layout(
            title=f"Flujo de Conciliación - {cuenta}",
            showlegend=False,
            height=500,
            xaxis_title="",
            yaxis_title="Monto ($)"
        )
        
        # Línea de referencia del saldo real
        fig_waterfall.add_hline(
            y=resultado.saldo_final_real,
            line_dash="dash",
            line_color="red",
            annotation_text="Saldo Real",
            annotation_position="right"
        )
        
        st.plotly_chart(fig_waterfall, use_container_width=True)
        
        # Tabla detallada
        with st.expander("📋 Detalle de Cálculo"):
            detalle_data = {
                "Concepto": [
                    "Saldo Inicial SICONE",
                    "Ingresos Proyectados",
                    "Egresos Proyectados",
                    "Saldo Final SICONE",
                    "Ajustes Ingresos",
                    "Ajustes Egresos",
                    "Saldo Conciliado",
                    "Saldo Real",
                    "Diferencia Residual"
                ],
                "Monto": [
                    formatear_moneda(resultado.saldo_inicial_sicone),
                    formatear_moneda(resultado.ingresos_sicone),
                    formatear_moneda(resultado.egresos_sicone),
                    formatear_moneda(resultado.saldo_final_sicone),
                    formatear_moneda(resultado.ajustes_ingresos),
                    formatear_moneda(resultado.ajustes_egresos),
                    formatear_moneda(resultado.saldo_conciliado),
                    formatear_moneda(resultado.saldo_final_real),
                    formatear_moneda(resultado.diferencia_residual)
                ],
                "% del Saldo Final": [
                    f"{resultado.saldo_inicial_sicone/resultado.saldo_final_real*100:.1f}%" if resultado.saldo_final_real != 0 else "N/A",
                    f"{resultado.ingresos_sicone/resultado.saldo_final_real*100:.1f}%" if resultado.saldo_final_real != 0 else "N/A",
                    f"{resultado.egresos_sicone/resultado.saldo_final_real*100:.1f}%" if resultado.saldo_final_real != 0 else "N/A",
                    f"{resultado.saldo_final_sicone/resultado.saldo_final_real*100:.1f}%" if resultado.saldo_final_real != 0 else "N/A",
                    f"{resultado.ajustes_ingresos/resultado.saldo_final_real*100:.1f}%" if resultado.saldo_final_real != 0 else "N/A",
                    f"{resultado.ajustes_egresos/resultado.saldo_final_real*100:.1f}%" if resultado.saldo_final_real != 0 else "N/A",
                    f"{resultado.saldo_conciliado/resultado.saldo_final_real*100:.1f}%" if resultado.saldo_final_real != 0 else "N/A",
                    "100.0%",
                    f"{abs(resultado.diferencia_residual)/resultado.saldo_final_real*100:.2f}%" if resultado.saldo_final_real != 0 else "N/A"
                ]
            }
            
            df_detalle = pd.DataFrame(detalle_data)
            st.dataframe(df_detalle, use_container_width=True, hide_index=True)
    
    with tab_fiducuenta:
        if "Fiducuenta" in resultados:
            mostrar_detalle_cuenta("Fiducuenta", resultados["Fiducuenta"])
        else:
            st.warning("⚠️ No hay datos de Fiducuenta")
    
    with tab_cuenta_banco:
        if "Cuenta Bancaria" in resultados:
            mostrar_detalle_cuenta("Cuenta Bancaria", resultados["Cuenta Bancaria"])
        else:
            st.warning("⚠️ No hay datos de Cuenta Bancaria")

# ============================================================================
# EXPORTACIÓN
# ============================================================================

if st.session_state.resultados_conciliacion:
    st.divider()
    st.header("💾 Exportación y Documentación")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        nombre_archivo = st.text_input(
            "Nombre del archivo",
            value=f"conciliacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
    
    with col_exp2:
        ruta_exportacion = st.text_input(
            "Ruta de exportación",
            value="./data/conciliaciones/"
        )
    
    if st.button("📥 Exportar Conciliación Completa", type="primary"):
        try:
            # Crear directorio si no existe
            Path(ruta_exportacion).mkdir(parents=True, exist_ok=True)
            
            ruta_completa = Path(ruta_exportacion) / nombre_archivo
            
            exito = st.session_state.conciliador.exportar_conciliacion(str(ruta_completa))
            
            if exito:
                st.success(f"✅ Conciliación exportada exitosamente a: {ruta_completa}")
                
                # Mostrar preview del JSON exportado
                with st.expander("👁️ Preview del archivo exportado"):
                    with open(ruta_completa, 'r', encoding='utf-8') as f:
                        contenido = json.load(f)
                    st.json(contenido)
            else:
                st.error("❌ Error al exportar la conciliación")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    
    # Información sobre reportes futuros
    st.info("""
    📄 **Próximamente:** Generación de reporte PDF ejecutivo
    
    El reporte incluirá:
    - Resumen ejecutivo con métricas clave
    - Gráficos waterfall por cuenta
    - Detalle de ajustes documentados
    - Validaciones y recomendaciones
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
col_foot1, col_foot2 = st.columns([3, 1])

with col_foot1:
    st.caption("SICONE - Sistema Integrado de Construcción Eficiente | Módulo de Conciliación v1.0 MVP")
    st.caption("Desarrollado por Andrés | Enero 2025")

with col_foot2:
    if st.button("📖 Ver Documentación", use_container_width=True):
        st.session_state.mostrar_ayuda = not st.session_state.mostrar_ayuda
        st.rerun()
