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
                    # Evitar procesamiento múltiple (prevenir loop infinito)
                    archivo_id = f"{archivo_ajustes.name}_{archivo_ajustes.size}"
                    
                    if st.session_state.get('ultimo_archivo_procesado') != archivo_id:
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
                            
                            # Marcar archivo como procesado
                            st.session_state.ultimo_archivo_procesado = archivo_id
                            
                            st.success(f"✅ {len(ajustes_data)} ajustes importados")
                            time.sleep(0.5)
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
            
            # MOSTRAR AJUSTES - VERSIÓN SIMPLIFICADA QUE SÍ FUNCIONA
            if st.session_state.conciliador and st.session_state.conciliador.ajustes:
                # Forzar sincronización SIEMPRE
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
                
                # Métricas
                total_ing = st.session_state.ajustes_df[st.session_state.ajustes_df['Tipo'] == 'Ingreso']['Monto'].sum()
                total_egr = st.session_state.ajustes_df[st.session_state.ajustes_df['Tipo'] == 'Egreso']['Monto'].sum()
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Ingresos", f"${total_ing:,.0f}")
                col2.metric("Egresos", f"${total_egr:,.0f}")
                col3.metric("Neto", f"${(total_ing - total_egr):,.0f}")
                
                # Tabla
                st.dataframe(st.session_state.ajustes_df[['Fecha', 'Cuenta', 'Categoría', 'Concepto', 'Tipo', 'Monto']], 
                           use_container_width=True, hide_index=False)
                
                # Botones eliminar y editar
                st.caption("**Acciones:**")
                for idx in range(len(st.session_state.ajustes_df)):
                    col1, col2, col3 = st.columns([5, 1, 1])
                    with col1:
                        row = st.session_state.ajustes_df.iloc[idx]
                        st.text(f"#{idx}: {row['Concepto'][:40]}... - {row['Tipo']} ${row['Monto']:,.0f}")
                    with col2:
                        if st.button("✏️", key=f"edit_{idx}", help="Editar"):
                            st.session_state[f'editando_{idx}'] = True
                            st.rerun()
                    with col3:
                        if st.button("🗑️", key=f"del_{idx}", help="Eliminar"):
                            st.session_state.conciliador.ajustes.pop(idx)
                            st.rerun()
                
                # Formularios de edición
                for idx in range(len(st.session_state.ajustes_df)):
                    if st.session_state.get(f'editando_{idx}', False):
                        with st.expander(f"✏️ Editando Ajuste #{idx}", expanded=True):
                            row = st.session_state.ajustes_df.iloc[idx]
                            
                            with st.form(f"form_edit_{idx}"):
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    fecha_ed = st.date_input("Fecha", value=pd.to_datetime(row['Fecha']).date())
                                    cuenta_ed = st.selectbox("Cuenta", ["Fiducuenta", "Cuenta Bancaria", "Ambas"],
                                                            index=["Fiducuenta", "Cuenta Bancaria", "Ambas"].index(row['Cuenta']))
                                
                                with col2:
                                    categoria_ed = st.selectbox("Categoría", Ajuste.CATEGORIAS_VALIDAS,
                                                               index=Ajuste.CATEGORIAS_VALIDAS.index(row['Categoría']))
                                    tipo_ed = st.selectbox("Tipo", ["Ingreso", "Egreso"],
                                                          index=["Ingreso", "Egreso"].index(row['Tipo']))
                                
                                with col3:
                                    monto_ed = st.number_input("Monto ($)", value=float(row['Monto']),
                                                              min_value=0.0, step=100000.0, format="%.2f")
                                
                                concepto_ed = st.text_input("Concepto", value=row['Concepto'])
                                
                                col_save, col_cancel = st.columns(2)
                                with col_save:
                                    if st.form_submit_button("💾 Guardar", type="primary", use_container_width=True):
                                        # Actualizar en conciliador
                                        ajuste_actualizado = Ajuste(
                                            fecha=fecha_ed.isoformat(),
                                            categoria=categoria_ed,
                                            concepto=concepto_ed,
                                            cuenta=cuenta_ed,
                                            tipo=tipo_ed,
                                            monto=monto_ed
                                        )
                                        st.session_state.conciliador.ajustes[idx] = ajuste_actualizado
                                        st.session_state[f'editando_{idx}'] = False
                                        st.success("✅ Ajuste actualizado")
                                        st.rerun()
                                
                                with col_cancel:
                                    if st.form_submit_button("❌ Cancelar", use_container_width=True):
                                        st.session_state[f'editando_{idx}'] = False
                                        st.rerun()
    
    # ========================================================================
    # PASO 5: CÁLCULO
    # ========================================================================
    
    if st.session_state.saldos_reales_configurados and st.session_state.conciliador:
        st.divider()
        st.subheader("🔍 Calcular Conciliación")
        
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("CALCULAR", type="primary", use_container_width=True):
                try:
                    with st.spinner("Calculando..."):
                        resultados = st.session_state.conciliador.calcular_conciliacion()
                        st.session_state.resultados_conciliacion = resultados
                    st.success("✅ Listo!")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al calcular: {str(e)}")
                    with st.expander("Ver detalles del error"):
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
        
        # Gráficos mejorados con colores y explicaciones
        st.subheader("📈 Análisis Visual")
        
        # Mostrar fórmula de conciliación
        st.info("""
        **💡 Fórmula de Conciliación:**
        
        `Saldo Final SICONE = Saldo Inicial + Ingresos SICONE - Egresos SICONE + Ajustes Neto`
        
        `Diferencia = Saldo Final SICONE - Saldo Final Real`
        """)
        
        # Análisis de la diferencia
        diferencia_total_val = sum(r.diferencia_residual for r in resultados.values())
        
        if abs(diferencia_total_val) > 1000:
            if diferencia_total_val > 0:
                st.warning(f"""
                **📊 Interpretación:** SICONE proyecta **${abs(diferencia_total_val):,.0f} más** que el saldo real.
                
                **Posibles causas:**
                - 💰 **Ingresos sobreestimados:** SICONE proyectó ingresos que no se recibieron
                - 💸 **Egresos no registrados:** Gastos reales que no están en el modelo SICONE
                - 🔄 **Timing:** Diferencias temporales en registro de transacciones
                """)
            else:
                st.warning(f"""
                **📊 Interpretación:** El saldo real es **${abs(diferencia_total_val):,.0f} mayor** que lo proyectado por SICONE.
                
                **Posibles causas:**
                - 💰 **Ingresos adicionales:** Se recibieron ingresos no proyectados en SICONE
                - 💸 **Egresos subestimados:** SICONE proyectó más gastos de los que realmente ocurrieron
                - 🔄 **Timing:** Diferencias temporales en registro de transacciones
                """)
        else:
            st.success(f"✅ **Excelente conciliación:** La diferencia es de solo ${abs(diferencia_total_val):,.0f}")
        
        # Tabs mejorados
        tab1, tab2, tab3 = st.tabs(["📊 Comparación General", "🎯 Desglose de Ajustes", "🏦 Análisis por Cuenta"])
        
        with tab1:
            # Gráfico de barras comparativo con colores mejorados
            fig_comp = go.Figure()
            
            # Colores: Azul para Real, Naranja para SICONE
            colores_real = ['#3498db', '#5dade2']  # Azules
            colores_sicone = ['#e67e22', '#f39c12']  # Naranjas
            
            cuentas = list(resultados.keys())
            for i, (cuenta, resultado) in enumerate(resultados.items()):
                fig_comp.add_trace(go.Bar(
                    name=f"{cuenta} - Real",
                    x=[cuenta],
                    y=[resultado.saldo_final_real],
                    text=[formatear_moneda(resultado.saldo_final_real)],
                    textposition='auto',
                    marker_color=colores_real[i % len(colores_real)],
                    legendgroup='real'
                ))
                fig_comp.add_trace(go.Bar(
                    name=f"{cuenta} - SICONE",
                    x=[cuenta],
                    y=[resultado.saldo_conciliado],
                    text=[formatear_moneda(resultado.saldo_conciliado)],
                    textposition='auto',
                    marker_color=colores_sicone[i % len(colores_sicone)],
                    legendgroup='sicone'
                ))
            
            fig_comp.update_layout(
                title="Comparación: Saldos Reales (Azul) vs SICONE Proyectados (Naranja)",
                barmode='group',
                height=450,
                yaxis_title="Monto ($)",
                xaxis_title="Cuenta",
                template="plotly_white"
            )
            st.plotly_chart(fig_comp, use_container_width=True)
            
            # Tabla resumen mejorada
            st.markdown("### 📋 Resumen Detallado")
            resumen_data = []
            for cuenta, resultado in resultados.items():
                diferencia = resultado.diferencia_residual
                estado = "✅ OK" if abs(diferencia) < 1000000 else "⚠️ Revisar" if abs(diferencia) < 10000000 else "🚨 Crítico"
                
                resumen_data.append({
                    'Cuenta': cuenta,
                    'Saldo Inicial': formatear_moneda(resultado.saldo_inicial_sicone),
                    'Ingresos': formatear_moneda(resultado.ingresos_sicone),
                    'Egresos': formatear_moneda(resultado.egresos_sicone),
                    'Ajustes Neto': formatear_moneda(resultado.ajustes_ingresos - resultado.ajustes_egresos),
                    'Saldo SICONE': formatear_moneda(resultado.saldo_conciliado),
                    'Saldo Real': formatear_moneda(resultado.saldo_final_real),
                    'Diferencia': formatear_moneda(abs(diferencia)),
                    'Estado': estado,
                    'Precisión': f"{resultado.precision:.2f}%"
                })
            
            df_resumen = pd.DataFrame(resumen_data)
            st.dataframe(df_resumen, use_container_width=True, hide_index=True)
        
        with tab2:
            # Desglose de ajustes
            st.markdown("**Impacto de Ajustes:**")
            
            if st.session_state.conciliador.ajustes:
                # Agrupar por tipo y cuenta
                ajustes_por_tipo = {}
                for ajuste in st.session_state.conciliador.ajustes:
                    key = f"{ajuste.tipo} - {ajuste.categoria}"
                    if key not in ajustes_por_tipo:
                        ajustes_por_tipo[key] = 0
                    ajustes_por_tipo[key] += ajuste.monto if ajuste.tipo == "Ingreso" else -ajuste.monto
                
                # Gráfico de torta
                fig_ajustes = go.Figure(data=[go.Pie(
                    labels=list(ajustes_por_tipo.keys()),
                    values=[abs(v) for v in ajustes_por_tipo.values()],
                    hole=.3,
                    textinfo='label+percent+value',
                    texttemplate='%{label}<br>%{value:$,.0f}<br>(%{percent})'
                )])
                fig_ajustes.update_layout(
                    title="Distribución de Ajustes por Categoría",
                    height=500
                )
                st.plotly_chart(fig_ajustes, use_container_width=True)
                
                # Tabla de ajustes
                st.markdown("**Detalle de Ajustes:**")
                ajustes_data = []
                for i, ajuste in enumerate(st.session_state.conciliador.ajustes):
                    ajustes_data.append({
                        '#': i,
                        'Fecha': ajuste.fecha,
                        'Categoría': ajuste.categoria,
                        'Concepto': ajuste.concepto,
                        'Tipo': ajuste.tipo,
                        'Monto': formatear_moneda(ajuste.monto),
                        'Cuenta': ajuste.cuenta
                    })
                
                df_ajustes = pd.DataFrame(ajustes_data)
                st.dataframe(df_ajustes, use_container_width=True, hide_index=True)
            else:
                st.info("No hay ajustes registrados")
        
        with tab3:
            # Waterfall mejorado con diferencia a la izquierda
            st.markdown("### 🏦 Análisis Detallado por Cuenta")
            
            for cuenta, resultado in resultados.items():
                st.markdown(f"#### {cuenta}")
                
                # Métricas con colores
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Saldo Inicial", formatear_moneda(resultado.saldo_inicial_sicone))
                col2.metric("Flujo Neto", formatear_moneda(resultado.ingresos_sicone - resultado.egresos_sicone))
                col3.metric("Ajustes Neto", formatear_moneda(resultado.ajustes_ingresos - resultado.ajustes_egresos))
                
                diferencia_val = resultado.diferencia_residual
                estado_icon = "✅" if abs(diferencia_val) < 1000000 else "⚠️"
                col4.metric("Diferencia", formatear_moneda(abs(diferencia_val)), delta=estado_icon)
                
                # Fórmula específica de esta cuenta
                st.info(f"""
                **Fórmula para {cuenta}:**
                
                `{formatear_moneda(resultado.saldo_inicial_sicone)} (Inicial) + {formatear_moneda(resultado.ingresos_sicone)} (Ingresos) - {formatear_moneda(resultado.egresos_sicone)} (Egresos) + {formatear_moneda(resultado.ajustes_ingresos - resultado.ajustes_egresos)} (Ajustes) = {formatear_moneda(resultado.saldo_conciliado)} (SICONE)`
                
                `{formatear_moneda(resultado.saldo_conciliado)} (SICONE) - {formatear_moneda(resultado.saldo_final_real)} (Real) = {formatear_moneda(diferencia_val)} (Diferencia)`
                """)
                
                # Waterfall mejorado - Diferencia primero a la izquierda
                valores_waterfall = [
                    diferencia_val,  # Diferencia primero (ROJO)
                    resultado.saldo_final_real,  # Saldo Real (AZUL)
                    resultado.ingresos_sicone,  # Ingresos
                    -resultado.egresos_sicone,  # Egresos
                    resultado.ajustes_ingresos - resultado.ajustes_egresos,  # Ajustes
                    0  # Total = Saldo SICONE
                ]
                
                etiquetas_waterfall = [
                    "⚠️ Diferencia",
                    "Saldo Real",
                    "+ Ingresos",
                    "- Egresos",
                    "+ Ajustes",
                    "= SICONE"
                ]
                
                medidas = ["relative", "absolute", "relative", "relative", "relative", "total"]
                
                # Colores: Rojo para diferencia, Azul para Real, Naranja para SICONE, gris para flujos
                colores = ['#e74c3c', '#3498db', '#95a5a6', '#95a5a6', '#95a5a6', '#e67e22']
                
                fig = go.Figure(go.Waterfall(
                    x=etiquetas_waterfall,
                    y=valores_waterfall,
                    measure=medidas,
                    text=[formatear_moneda(abs(v)) for v in [
                        diferencia_val,
                        resultado.saldo_final_real,
                        resultado.ingresos_sicone,
                        resultado.egresos_sicone,
                        resultado.ajustes_ingresos - resultado.ajustes_egresos,
                        resultado.saldo_conciliado
                    ]],
                    textposition="outside",
                    connector={"line": {"color": "rgb(100, 100, 100)", "dash": "dot"}},
                    increasing={"marker": {"color": "#2ecc71"}},
                    decreasing={"marker": {"color": "#e74c3c"}},
                    totals={"marker": {"color": "#e67e22"}}
                ))
                
                fig.update_layout(
                    title=f"Flujo de Conciliación - {cuenta}<br><sub>🔴 Diferencia | 🔵 Real | 🟠 SICONE</sub>",
                    height=500,
                    showlegend=False,
                    yaxis_title="Monto ($)",
                    template="plotly_white",
                    xaxis={'type': 'category'}
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Explicación de la diferencia para esta cuenta
                if abs(diferencia_val) > 1000:
                    if diferencia_val > 0:
                        st.warning(f"""
                        **📊 Explicación para {cuenta}:**
                        
                        SICONE proyecta **${abs(diferencia_val):,.0f} más** que el saldo real.
                        
                        **Causas posibles:**
                        - 💰 Ingresos sobreestimados: SICONE proyectó {formatear_moneda(resultado.ingresos_sicone)} pero no se recibieron completos
                        - 💸 Egresos no registrados: Gastos reales que no están en el modelo SICONE
                        """)
                    else:
                        st.info(f"""
                        **📊 Explicación para {cuenta}:**
                        
                        El saldo real es **${abs(diferencia_val):,.0f} mayor** que lo proyectado.
                        
                        **Causas posibles:**
                        - 💰 Ingresos adicionales no proyectados en SICONE
                        - 💸 Egresos menores: SICONE proyectó {formatear_moneda(resultado.egresos_sicone)} pero los gastos reales fueron menores
                        """)
                
                st.divider()

# ============================================================================
# ENTRY POINT
# ============================================================================

# Exportar función main para que sea accesible desde main.py
__all__ = ['main']

if __name__ == "__main__":
    # Si se ejecuta directamente (para testing)
    st.set_page_config(page_title="Conciliación", page_icon="🔍", layout="wide")
    main()
