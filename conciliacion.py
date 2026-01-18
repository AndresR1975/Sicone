"""
SICONE - Módulo de Conciliación Financiera
==========================================

PROPÓSITO:
----------
Interfaz de conciliación que permite:
- Configurar período de análisis
- Cargar datos SICONE consolidados
- Ingresar saldos reales separados por cuenta (Fiducuenta + Cuenta Bancaria)
- Sumar para comparar vs consolidado SICONE
- Documentar ajustes estructurados por cuenta
- Calcular y visualizar resultados

ARQUITECTURA SICONE:
--------------------
Este módulo se integra con el sistema de navegación personalizado de SICONE.
NO usa st.set_page_config() porque ya está configurado en main.py.
Exporta una función main() que es llamada desde main.py.

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
import time
from pathlib import Path

# Importar módulo core (lógica de negocio)
try:
    import conciliacion_core
    from conciliacion_core import (
        ConciliadorSICONE,
        SaldosCuenta,
        Ajuste,
        ResultadoConciliacion,
        formatear_moneda
    )
except ImportError as e:
    st.error(f"❌ Error al importar conciliacion_core: {e}")
    st.info("**Solución:** Asegúrese de que `conciliacion_core.py` esté en el mismo directorio")
    st.stop()

# ============================================================================
# ESTILOS CSS PERSONALIZADOS
# ============================================================================

CUSTOM_CSS = """
<style>
    .info-box {
        background-color: #e7f3ff;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #2196F3;
        margin: 10px 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
</style>
"""

# ============================================================================
# INICIALIZACIÓN DE SESSION STATE
# ============================================================================

def inicializar_session_state():
    """Inicializa variables de session_state si no existen"""
    if 'conciliador' not in st.session_state:
        st.session_state.conciliador = None
    
    if 'ajustes_df' not in st.session_state:
        st.session_state.ajustes_df = pd.DataFrame(columns=[
            'Fecha', 'Cuenta', 'Categoría', 'Concepto', 
            'Monto', 'Tipo', 'Evidencia', 'Observaciones'
        ])
    
    # CRÍTICO: Sincronizar dataframe con ajustes del conciliador
    if 'conciliador' in st.session_state and st.session_state.conciliador is not None:
        if st.session_state.conciliador.ajustes and st.session_state.ajustes_df.empty:
            # Reconstruir dataframe desde ajustes
            datos_df = []
            for ajuste in st.session_state.conciliador.ajustes:
                datos_df.append({
                    'Fecha': ajuste.fecha,
                    'Cuenta': ajuste.cuenta,
                    'Categoría': ajuste.categoria,
                    'Concepto': ajuste.concepto,
                    'Monto': ajuste.monto,
                    'Tipo': ajuste.tipo,
                    'Evidencia': ajuste.evidencia,
                    'Observaciones': ajuste.observaciones
                })
            st.session_state.ajustes_df = pd.DataFrame(datos_df)
    
    if 'saldos_reales_configurados' not in st.session_state:
        st.session_state.saldos_reales_configurados = False
    
    if 'datos_sicone_cargados' not in st.session_state:
        st.session_state.datos_sicone_cargados = False
    
    if 'resultados_conciliacion' not in st.session_state:
        st.session_state.resultados_conciliacion = None
    
    if 'mostrar_ayuda' not in st.session_state:
        st.session_state.mostrar_ayuda = False

# ============================================================================
# FUNCIÓN PRINCIPAL (EXPORTADA PARA MAIN.PY)
# ============================================================================

def main():
    """
    Función principal del módulo de conciliación.
    
    Esta función es llamada desde main.py cuando el usuario selecciona
    el módulo de Conciliación.
    
    NOTA: NO incluye st.set_page_config() porque ya está configurado en main.py
    """
    
    # Aplicar estilos
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    
    # Inicializar session state
    inicializar_session_state()
    
    # ========================================================================
    # HEADER
    # ========================================================================
    
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
                <li><strong>SICONE</strong> trabaja con saldo consolidado total</li>
                <li><strong>Realidad bancaria</strong> tiene 2 cuentas separadas:
                    <ul>
                        <li>🏦 <strong>Fiducuenta:</strong> Reserva de efectivo con rendimientos</li>
                        <li>💳 <strong>Cuenta Bancaria:</strong> Operación diaria de proyectos</li>
                    </ul>
                </li>
                <li><strong>Este módulo</strong> compara la suma de cuentas reales vs SICONE</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class='info-box'>
        <h4 style='margin: 0; color: #1976D2;'>Verificación de Precisión SICONE</h4>
        <p style='margin: 5px 0 0 0; color: #555;'>
            Compara proyecciones del modelo contra realidad bancaria y documenta diferencias.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # ========================================================================
    # SIDEBAR: ESTADO DEL PROCESO
    # ========================================================================
    
    with st.sidebar:
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
    
    # ========================================================================
    # PASO 1: CONFIGURACIÓN DEL PERÍODO
    # ========================================================================
    
    with st.expander("📅 PASO 1: Configuración del Período", expanded=not st.session_state.conciliador):
        st.markdown("""
        **Instrucciones:** Define el período que deseas conciliar.
        
        ✅ **Ahora puedes usar cualquier rango de fechas** desde el inicio de tus proyectos.
        
        💡 **Ejemplos de períodos:**
        - Desde mayo 2024 (inicio de proyectos más antiguos)
        - Un mes específico (ej: diciembre 2025)
        - Un trimestre completo
        - Año completo 2024 o 2025
        
        📊 El sistema extraerá datos de todos los proyectos activos en ese período.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fecha_inicio = st.date_input(
                "Fecha de Inicio",
                value=date(2025, 1, 1)
            )
        
        with col2:
            fecha_fin = st.date_input(
                "Fecha de Fin",
                value=date(2025, 1, 31)
            )
        
        if fecha_inicio >= fecha_fin:
            st.error("⚠️ La fecha de inicio debe ser anterior a la fecha de fin")
        else:
            dias_periodo = (fecha_fin - fecha_inicio).days + 1
            st.info(f"📊 Período: {dias_periodo} días")
            
            if st.button("✅ Confirmar Período", type="primary"):
                st.session_state.conciliador = ConciliadorSICONE(
                    fecha_inicio=fecha_inicio.isoformat(),
                    fecha_fin=fecha_fin.isoformat()
                )
                st.success(f"✅ Período configurado")
                st.rerun()
    
    # ========================================================================
    # PASO 2: CARGA DE DATOS SICONE
    # ========================================================================
    
    if st.session_state.conciliador:
        with st.expander("📊 PASO 2: Datos SICONE", expanded=not st.session_state.datos_sicone_cargados):
            uploaded_json = st.file_uploader(
                "📁 Selecciona consolidado_multiproyecto.json",
                type=['json']
            )
            
            if uploaded_json and st.button("📥 Cargar JSON", type="primary"):
                with st.spinner("Cargando..."):
                    try:
                        # Cargar JSON
                        datos = json.load(uploaded_json)
                        
                        # Verificar estructura básica
                        if "df_consolidado" not in datos:
                            st.error("❌ El JSON no contiene 'df_consolidado'. Verifica que sea el archivo correcto.")
                            st.stop()
                        
                        # Intentar cargar datos
                        success = st.session_state.conciliador.cargar_datos_sicone(datos_dict=datos)
                        
                        if success:
                            st.session_state.datos_sicone_cargados = True
                            
                            # Mostrar datos extraídos
                            datos_proc = st.session_state.conciliador.datos_sicone_procesados
                            if datos_proc:
                                st.success("✅ Datos cargados correctamente")
                                
                                metadata = datos_proc.get("metadata", {})
                                consolidado = datos_proc.get("Consolidado", {})
                                
                                with st.expander("📋 Ver datos extraídos", expanded=True):
                                    col1, col2, col3, col4 = st.columns(4)
                                    with col1:
                                        st.metric("Período", f"{metadata.get('fecha_inicio_real')} → {metadata.get('fecha_fin_real')}")
                                    with col2:
                                        st.metric("Semanas", metadata.get('semanas_analizadas', 0))
                                    with col3:
                                        st.metric("Proyectos", metadata.get('proyectos_procesados', 0))
                                    with col4:
                                        st.metric("Saldo Final", formatear_moneda(consolidado.get('saldo_final', 0)))
                                    
                                    st.divider()
                                    
                                    col_det1, col_det2, col_det3 = st.columns(3)
                                    with col_det1:
                                        st.metric("Saldo Inicial", formatear_moneda(consolidado.get('saldo_inicial', 0)))
                                    with col_det2:
                                        st.metric("Ingresos Período", formatear_moneda(consolidado.get('ingresos', 0)))
                                    with col_det3:
                                        st.metric("Egresos Período", formatear_moneda(consolidado.get('egresos', 0)))
                                    
                                    movimiento_neto = consolidado.get('saldo_final', 0) - consolidado.get('saldo_inicial', 0)
                                    st.info(f"💰 **Movimiento Neto del Período:** {formatear_moneda(abs(movimiento_neto))} " + 
                                           ("📈 (Aumento)" if movimiento_neto > 0 else "📉 (Disminución)"))
                                    
                                    # Mostrar desglose de egresos por proyecto si está disponible
                                    if 'proyectos_detalle' in metadata:
                                        with st.expander("📊 Desglose por Proyecto"):
                                            proyectos_df = pd.DataFrame(metadata['proyectos_detalle'])
                                            proyectos_df['saldo_inicial'] = proyectos_df['saldo_inicial'].apply(lambda x: formatear_moneda(x))
                                            proyectos_df['ingresos'] = proyectos_df['ingresos'].apply(lambda x: formatear_moneda(x))
                                            proyectos_df['egresos'] = proyectos_df['egresos'].apply(lambda x: formatear_moneda(x))
                                            proyectos_df['saldo_final'] = proyectos_df['saldo_final'].apply(lambda x: formatear_moneda(x))
                                            st.dataframe(proyectos_df, use_container_width=True)
                            
                            st.rerun()
                        else:
                            st.error("❌ No se pudieron extraer datos del período seleccionado")
                            
                            # Intentar dar información útil sobre por qué falló
                            if "proyectos" in datos:
                                proyectos_activos = [p for p in datos["proyectos"] if p.get("estado") == "ACTIVO"]
                                st.warning(f"⚠️ Se encontraron {len(proyectos_activos)} proyectos activos en el JSON")
                                
                                if proyectos_activos:
                                    st.info("📅 **Posibles causas:**\n"
                                           "- El período seleccionado no coincide con las fechas de ningún proyecto activo\n"
                                           "- Los proyectos no tienen datos de tesorería para ese período\n\n"
                                           "**Sugerencia:** Revisa las fechas de inicio de tus proyectos en el JSON")
                                    
                                    # Mostrar fechas de inicio de proyectos
                                    with st.expander("🔍 Ver fechas de inicio de proyectos"):
                                        for p in proyectos_activos[:5]:  # Máximo 5
                                            nombre = p.get("nombre", "Sin nombre")
                                            fecha_inicio = p.get("data", {}).get("proyecto", {}).get("fecha_inicio", "No disponible")
                                            st.text(f"• {nombre}: {fecha_inicio}")
                                else:
                                    st.error("❌ No hay proyectos activos en el JSON")
                            else:
                                st.error("❌ El JSON no tiene la estructura esperada (falta 'proyectos')")
                                st.info("Verifica que el archivo sea un 'consolidado_multiproyecto.json' válido")
                    
                    except json.JSONDecodeError as e:
                        st.error(f"❌ Error al leer JSON: El archivo no es un JSON válido")
                        st.exception(e)
                    except KeyError as e:
                        st.error(f"❌ Error de estructura: Falta la clave {str(e)} en el JSON")
                        st.info("Verifica que el archivo sea un 'consolidado_multiproyecto.json' válido")
                    except Exception as e:
                        st.error(f"❌ Error inesperado: {str(e)}")
                        st.exception(e)
    
    # ========================================================================
    # PASO 3: SALDOS REALES
    # ========================================================================
    
    if st.session_state.datos_sicone_cargados:
        with st.expander("💰 PASO 3: Saldos Reales", expanded=not st.session_state.saldos_reales_configurados):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🏦 Fiducuenta")
                st.caption("Ingrese los saldos según extracto de la Fiducuenta")
                fidu_ini = st.number_input("Saldo Inicial ($)", min_value=0.0, step=1000000.0, format="%.2f", key="fidu_ini", help="Saldo al inicio del período según extracto")
                if fidu_ini > 0:
                    st.caption(f"💰 {formatear_moneda(fidu_ini)}")
                fidu_fin = st.number_input("Saldo Final ($)", min_value=0.0, step=1000000.0, format="%.2f", key="fidu_fin", help="Saldo al final del período según extracto")
                if fidu_fin > 0:
                    st.caption(f"💰 {formatear_moneda(fidu_fin)}")
            
            with col2:
                st.markdown("### 💳 Cuenta Bancaria")
                st.caption("Ingrese los saldos según extracto de la Cuenta Bancaria")
                banco_ini = st.number_input("Saldo Inicial ($)", min_value=0.0, step=1000000.0, format="%.2f", key="banco_ini", help="Saldo al inicio del período según extracto")
                if banco_ini > 0:
                    st.caption(f"💰 {formatear_moneda(banco_ini)}")
                banco_fin = st.number_input("Saldo Final ($)", min_value=0.0, step=1000000.0, format="%.2f", key="banco_fin", help="Saldo al final del período según extracto")
                if banco_fin > 0:
                    st.caption(f"💰 {formatear_moneda(banco_fin)}")
            
            if all([fidu_ini, fidu_fin, banco_ini, banco_fin]):
                st.divider()
                if st.button("✅ Confirmar Saldos", type="primary"):
                    saldos_fidu = SaldosCuenta("Fiducuenta", fidu_ini, fidu_fin, "Manual")
                    saldos_banco = SaldosCuenta("Cuenta Bancaria", banco_ini, banco_fin, "Manual")
                    st.session_state.conciliador.set_saldos_reales(saldos_fidu, saldos_banco)
                    st.session_state.saldos_reales_configurados = True
                    st.success("✅ Saldos configurados")
                    st.rerun()
    
    # ========================================================================
    # PASO 4: AJUSTES
    # ========================================================================
    
    if st.session_state.saldos_reales_configurados:
        with st.expander("📝 PASO 4: Ajustes", expanded=True):
            
            # Botones de exportar/importar ajustes
            col_tools1, col_tools2, col_tools3 = st.columns([1, 1, 2])
            
            with col_tools1:
                if st.session_state.conciliador and st.session_state.conciliador.ajustes:
                    # Preparar datos para exportar
                    ajustes_export = []
                    for ajuste in st.session_state.conciliador.ajustes:
                        ajustes_export.append({
                            "fecha": ajuste.fecha,
                            "categoria": ajuste.categoria,
                            "concepto": ajuste.concepto,
                            "cuenta": ajuste.cuenta,
                            "tipo": ajuste.tipo,
                            "monto": ajuste.monto,
                            "observaciones": ajuste.observaciones,
                            "evidencia": ajuste.evidencia
                        })
                    
                    ajustes_json = json.dumps(ajustes_export, indent=2, ensure_ascii=False)
                    
                    st.download_button(
                        label="📥 Exportar Ajustes",
                        data=ajustes_json,
                        file_name=f"ajustes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        help="Descarga los ajustes actuales en formato JSON",
                        use_container_width=True
                    )
            
            with col_tools2:
                archivo_ajustes = st.file_uploader(
                    "Importar",
                    type=['json'],
                    help="Carga ajustes desde un archivo JSON",
                    key="import_ajustes",
                    label_visibility="collapsed"
                )
                
                if archivo_ajustes is not None:
                    try:
                        ajustes_data = json.load(archivo_ajustes)
                        
                        # Limpiar todo
                        st.session_state.conciliador.ajustes = []
                        
                        # Recrear dataframe desde cero
                        datos_df = []
                        
                        # Cargar cada ajuste
                        for aj_data in ajustes_data:
                            ajuste = Ajuste(
                                fecha=aj_data.get('fecha', ''),
                                categoria=aj_data.get('categoria', ''),
                                concepto=aj_data.get('concepto', ''),
                                cuenta=aj_data.get('cuenta', 'Ambas'),
                                tipo=aj_data.get('tipo', 'Ingreso'),
                                monto=aj_data.get('monto', 0.0),
                                observaciones=aj_data.get('observaciones', ''),
                                evidencia=aj_data.get('evidencia', '')
                            )
                            st.session_state.conciliador.ajustes.append(ajuste)
                            
                            # Agregar al dataframe
                            datos_df.append({
                                'Fecha': aj_data.get('fecha', ''),
                                'Cuenta': aj_data.get('cuenta', ''),
                                'Categoría': aj_data.get('categoria', ''),
                                'Concepto': aj_data.get('concepto', ''),
                                'Monto': aj_data.get('monto', 0.0),
                                'Tipo': aj_data.get('tipo', ''),
                                'Evidencia': aj_data.get('evidencia', ''),
                                'Observaciones': aj_data.get('observaciones', '')
                            })
                        
                        # Recrear dataframe completo
                        st.session_state.ajustes_df = pd.DataFrame(datos_df)
                        
                        st.success(f"✅ {len(ajustes_data)} ajustes importados")
                        time.sleep(0.5)  # Pequeña pausa para que se vea el mensaje
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            
            st.divider()
            
            # DEBUG INFO - TEMPORAL
            with st.expander("🔍 Debug Info", expanded=False):
                st.write(f"Ajustes en conciliador: {len(st.session_state.conciliador.ajustes) if st.session_state.conciliador else 0}")
                st.write(f"Filas en dataframe: {len(st.session_state.ajustes_df)}")
                st.write(f"DataFrame vacío: {st.session_state.ajustes_df.empty}")
                if st.session_state.conciliador and st.session_state.conciliador.ajustes:
                    st.write("Ajustes en conciliador:")
                    for i, aj in enumerate(st.session_state.conciliador.ajustes):
                        st.write(f"  {i}: {aj.concepto} - ${aj.monto:,.0f}")
            
            with st.form("form_ajuste", clear_on_submit=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    fecha_aj = st.date_input("Fecha", value=datetime.now().date())
                    cuenta_aj = st.selectbox("Cuenta", ["Fiducuenta", "Cuenta Bancaria", "Ambas"])
                
                with col2:
                    categoria_aj = st.selectbox("Categoría", Ajuste.CATEGORIAS_VALIDAS)
                    tipo_aj = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                
                with col3:
                    monto_aj = st.number_input("Monto ($)", min_value=0.0, step=100000.0, format="%.2f", help="Ingrese el monto del ajuste")
                
                concepto_aj = st.text_input("Concepto")
                
                if st.form_submit_button("➕ Agregar", type="primary"):
                    if monto_aj > 0 and concepto_aj:
                        ajuste = Ajuste(
                            fecha=fecha_aj.isoformat(),
                            cuenta=cuenta_aj,
                            categoria=categoria_aj,
                            concepto=concepto_aj,
                            monto=monto_aj,
                            tipo=tipo_aj
                        )
                        
                        exito, msg = st.session_state.conciliador.agregar_ajuste(ajuste)
                        if exito:
                            nuevo_registro = pd.DataFrame([{
                                'Fecha': fecha_aj,
                                'Cuenta': cuenta_aj,
                                'Categoría': categoria_aj,
                                'Concepto': concepto_aj,
                                'Monto': monto_aj,
                                'Tipo': tipo_aj,
                                'Evidencia': '',
                                'Observaciones': ''
                            }])
                            st.session_state.ajustes_df = pd.concat([
                                st.session_state.ajustes_df, 
                                nuevo_registro
                            ], ignore_index=True)
                            st.success(msg)
                            st.rerun()
            
            # Mostrar ajustes si existen EN EL CONCILIADOR (no solo en dataframe)
            tiene_ajustes = (st.session_state.conciliador and 
                           len(st.session_state.conciliador.ajustes) > 0)
            
            if tiene_ajustes:
                # Sincronizar dataframe si está desincronizado
                if st.session_state.ajustes_df.empty or len(st.session_state.ajustes_df) != len(st.session_state.conciliador.ajustes):
                    datos_df = []
                    for ajuste in st.session_state.conciliador.ajustes:
                        datos_df.append({
                            'Fecha': ajuste.fecha,
                            'Cuenta': ajuste.cuenta,
                            'Categoría': ajuste.categoria,
                            'Concepto': ajuste.concepto,
                            'Monto': ajuste.monto,
                            'Tipo': ajuste.tipo,
                            'Evidencia': ajuste.evidencia,
                            'Observaciones': ajuste.observaciones
                        })
                    st.session_state.ajustes_df = pd.DataFrame(datos_df)
                
                st.divider()
                st.markdown("### 📋 Ajustes Registrados")
                
                # Resumen rápido primero
                col_sum1, col_sum2, col_sum3 = st.columns(3)
                total_ingresos_ajustes = st.session_state.ajustes_df[st.session_state.ajustes_df['Tipo'] == 'Ingreso']['Monto'].sum()
                total_egresos_ajustes = st.session_state.ajustes_df[st.session_state.ajustes_df['Tipo'] == 'Egreso']['Monto'].sum()
                
                with col_sum1:
                    st.metric("📈 Total Ingresos", formatear_moneda(total_ingresos_ajustes))
                with col_sum2:
                    st.metric("📉 Total Egresos", formatear_moneda(total_egresos_ajustes))
                with col_sum3:
                    st.metric("💰 Efecto Neto", formatear_moneda(total_ingresos_ajustes - total_egresos_ajustes))
                
                st.caption(f"**Total de ajustes:** {len(st.session_state.ajustes_df)}")
                
                # Tabla simple para vista rápida
                st.markdown("**Vista Rápida:**")
                df_display = st.session_state.ajustes_df.copy()
                df_display['Monto'] = df_display['Monto'].apply(lambda x: f"${x:,.0f}")
                st.dataframe(df_display[['Fecha', 'Cuenta', 'Categoría', 'Concepto', 'Tipo', 'Monto']], 
                           use_container_width=True, hide_index=True)
                
                st.divider()
                st.markdown("**Detalles y Edición:**")
                
                # Mostrar tabla editable
                for idx, row in st.session_state.ajustes_df.iterrows():
                    with st.expander(f"#{idx} - {row['Concepto'][:50]}... ({formatear_moneda(row['Monto'])})"):
                        col_info1, col_info2, col_info3 = st.columns(3)
                        
                        with col_info1:
                            st.text(f"📅 Fecha: {row['Fecha']}")
                            st.text(f"🏦 Cuenta: {row['Cuenta']}")
                        
                        with col_info2:
                            st.text(f"📂 Categoría: {row['Categoría']}")
                            st.text(f"💰 Monto: {formatear_moneda(row['Monto'])}")
                        
                        with col_info3:
                            st.text(f"🔄 Tipo: {row['Tipo']}")
                        
                        if row['Observaciones']:
                            st.caption(f"📝 Obs: {row['Observaciones']}")
                        
                        # Botones de acción
                        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
                        
                        with col_btn1:
                            if st.button("✏️ Editar", key=f"edit_{idx}", use_container_width=True):
                                st.session_state[f'editing_{idx}'] = True
                                st.rerun()
                        
                        with col_btn2:
                            if st.button("🗑️ Eliminar", key=f"delete_{idx}", use_container_width=True, type="secondary"):
                                # Eliminar del dataframe
                                st.session_state.ajustes_df = st.session_state.ajustes_df.drop(idx).reset_index(drop=True)
                                # Eliminar del conciliador
                                st.session_state.conciliador.ajustes.pop(idx)
                                st.success(f"✅ Ajuste #{idx} eliminado")
                                st.rerun()
                        
                        # Formulario de edición si está activado
                        if st.session_state.get(f'editing_{idx}', False):
                            st.divider()
                            st.markdown("**Editar Ajuste:**")
                            
                            with st.form(f"form_edit_{idx}"):
                                col_ed1, col_ed2, col_ed3 = st.columns(3)
                                
                                with col_ed1:
                                    fecha_ed = st.date_input("Fecha", value=pd.to_datetime(row['Fecha']).date(), key=f"fecha_ed_{idx}")
                                    cuenta_ed = st.selectbox("Cuenta", ["Fiducuenta", "Cuenta Bancaria", "Ambas"], 
                                                            index=["Fiducuenta", "Cuenta Bancaria", "Ambas"].index(row['Cuenta']), 
                                                            key=f"cuenta_ed_{idx}")
                                
                                with col_ed2:
                                    categoria_ed = st.selectbox("Categoría", Ajuste.CATEGORIAS_VALIDAS,
                                                               index=Ajuste.CATEGORIAS_VALIDAS.index(row['Categoría']),
                                                               key=f"cat_ed_{idx}")
                                    tipo_ed = st.selectbox("Tipo", ["Ingreso", "Egreso"],
                                                          index=["Ingreso", "Egreso"].index(row['Tipo']),
                                                          key=f"tipo_ed_{idx}")
                                
                                with col_ed3:
                                    monto_ed = st.number_input("Monto ($)", value=float(row['Monto']), 
                                                              min_value=0.0, step=100000.0, format="%.2f",
                                                              key=f"monto_ed_{idx}")
                                
                                concepto_ed = st.text_input("Concepto", value=row['Concepto'], key=f"concepto_ed_{idx}")
                                observaciones_ed = st.text_area("Observaciones", value=row.get('Observaciones', ''), key=f"obs_ed_{idx}")
                                
                                col_save, col_cancel = st.columns(2)
                                
                                with col_save:
                                    if st.form_submit_button("💾 Guardar", type="primary", use_container_width=True):
                                        # Actualizar en dataframe
                                        st.session_state.ajustes_df.at[idx, 'Fecha'] = fecha_ed
                                        st.session_state.ajustes_df.at[idx, 'Cuenta'] = cuenta_ed
                                        st.session_state.ajustes_df.at[idx, 'Categoría'] = categoria_ed
                                        st.session_state.ajustes_df.at[idx, 'Concepto'] = concepto_ed
                                        st.session_state.ajustes_df.at[idx, 'Monto'] = monto_ed
                                        st.session_state.ajustes_df.at[idx, 'Tipo'] = tipo_ed
                                        st.session_state.ajustes_df.at[idx, 'Observaciones'] = observaciones_ed
                                        
                                        # Actualizar en conciliador
                                        ajuste_actualizado = Ajuste(
                                            fecha=fecha_ed.isoformat(),
                                            categoria=categoria_ed,
                                            concepto=concepto_ed,
                                            cuenta=cuenta_ed,
                                            tipo=tipo_ed,
                                            monto=monto_ed,
                                            observaciones=observaciones_ed
                                        )
                                        st.session_state.conciliador.ajustes[idx] = ajuste_actualizado
                                        
                                        # Desactivar modo edición
                                        st.session_state[f'editing_{idx}'] = False
                                        st.success(f"✅ Ajuste #{idx} actualizado")
                                        st.rerun()
                                
                                with col_cancel:
                                    if st.form_submit_button("❌ Cancelar", use_container_width=True):
                                        st.session_state[f'editing_{idx}'] = False
                                        st.rerun()
    
    # ========================================================================
    # PASO 5: CÁLCULO
    # ========================================================================
    
    if st.session_state.saldos_reales_configurados:
        st.divider()
        
        # Validar que el conciliador existe
        if not st.session_state.conciliador:
            st.error("⚠️ Error: Conciliador no inicializado. Por favor recarga los datos.")
        else:
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button("🔍 CALCULAR", type="primary", use_container_width=True, key="btn_calcular"):
                    with st.spinner("Calculando..."):
                        try:
                            resultados = st.session_state.conciliador.calcular_conciliacion()
                            st.session_state.resultados_conciliacion = resultados
                            st.success("✅ Conciliación calculada")
                            time.sleep(0.3)
                            st.rerun()
                        except AttributeError as e:
                            st.error(f"❌ Error de método: {str(e)}")
                            st.info("💡 Intenta recargar el JSON en PASO 2")
                        except Exception as e:
                            st.error(f"❌ Error al calcular: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
    
    # ========================================================================
    # RESULTADOS
    # ========================================================================
    
    if st.session_state.resultados_conciliacion:
        st.divider()
        st.header("📊 Resultados")
        
        resultados = st.session_state.resultados_conciliacion
        
        # Métricas
        col1, col2, col3 = st.columns(3)
        
        saldo_real_total = sum(r.saldo_final_real for r in resultados.values())
        diferencia_total = sum(r.diferencia_residual for r in resultados.values())
        precision = 100 * (1 - abs(diferencia_total) / abs(saldo_real_total)) if saldo_real_total != 0 else 0
        
        with col1:
            st.metric("Saldo Real Total", formatear_moneda(saldo_real_total))
        with col2:
            st.metric("Diferencia", formatear_moneda(abs(diferencia_total)))
        with col3:
            status = "✅ OK" if precision >= 98 else "⚠️ REVISAR" if precision >= 95 else "🚨 CRÍTICO"
            st.metric("Precisión", f"{precision:.2f}%", delta=status)
        
        # Gráficos por cuenta
        for cuenta, resultado in resultados.items():
            with st.expander(f"🏦 {cuenta}", expanded=True):
                fig = go.Figure(go.Waterfall(
                    x=["Inicial", "Ingresos", "Egresos", "Ajustes", "Final"],
                    y=[
                        resultado.saldo_inicial_sicone,
                        resultado.ingresos_sicone,
                        -resultado.egresos_sicone,
                        resultado.ajustes_ingresos - resultado.ajustes_egresos,
                        resultado.saldo_conciliado
                    ],
                    text=[formatear_moneda(v) for v in [
                        resultado.saldo_inicial_sicone,
                        resultado.ingresos_sicone,
                        resultado.egresos_sicone,
                        resultado.ajustes_ingresos - resultado.ajustes_egresos,
                        resultado.saldo_conciliado
                    ]],
                    textposition="outside"
                ))
                fig.update_layout(title=f"Conciliación {cuenta}", height=400)
                st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Si se ejecuta directamente (para testing)
    st.set_page_config(page_title="Conciliación", page_icon="🔍", layout="wide")
    main()
