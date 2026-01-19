"""
SICONE - Módulo de Conciliación SIMPLIFICADO
SIN dependencia de conciliacion_core.py
TODO inline para evitar problemas de caché
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from datetime import datetime

# Exportar main
__all__ = ['main']

def formatear_moneda(valor):
    """Formatea un valor como moneda colombiana"""
    return f"${valor:,.0f}"

def main():
    """Función principal"""
    
    st.title("🔍 Conciliación Financiera SICONE")
    st.caption("Versión Simplificada v2.0")
    
    # Inicializar session_state
    if 'saldos_iniciales' not in st.session_state:
        st.session_state.saldos_iniciales = {}
    if 'saldos_finales' not in st.session_state:
        st.session_state.saldos_finales = {}
    if 'datos_sicone' not in st.session_state:
        st.session_state.datos_sicone = None
    if 'ajustes' not in st.session_state:
        st.session_state.ajustes = []
    if 'fecha_inicio' not in st.session_state:
        st.session_state.fecha_inicio = None
    if 'fecha_fin' not in st.session_state:
        st.session_state.fecha_fin = None
    
    # PASO 1: Período de análisis
    st.subheader("📅 PASO 1: Período de Análisis")
    
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input(
            "Fecha Inicio",
            value=st.session_state.fecha_inicio if st.session_state.fecha_inicio else datetime(2025, 1, 1).date(),
            key='fecha_inicio_input'
        )
        st.session_state.fecha_inicio = fecha_inicio
    
    with col2:
        fecha_fin = st.date_input(
            "Fecha Fin",
            value=st.session_state.fecha_fin if st.session_state.fecha_fin else datetime(2025, 12, 31).date(),
            key='fecha_fin_input'
        )
        st.session_state.fecha_fin = fecha_fin
    
    st.info(f"📊 Período: {fecha_inicio.strftime('%Y-%m-%d')} a {fecha_fin.strftime('%Y-%m-%d')}")
    
    # PASO 2: Cargar datos SICONE
    st.divider()
    st.subheader("📂 PASO 2: Datos SICONE")
    
    archivo_json = st.file_uploader("Subir consolidado SICONE (JSON)", type=['json'], key='json_sicone')
    
    if archivo_json:
        try:
            datos = json.load(archivo_json)
            st.session_state.datos_sicone = datos
            
            # Extraer saldo del estado_caja
            saldo_sicone = datos.get('estado_caja', {}).get('saldo_total', 0)
            
            st.success(f"✅ Datos cargados - Saldo SICONE: {formatear_moneda(saldo_sicone)}")
            
        except Exception as e:
            st.error(f"Error al cargar JSON: {e}")
    
    # PASO 3: Saldos INICIALES y FINALES reales
    if st.session_state.datos_sicone:
        st.divider()
        st.subheader("💰 PASO 3: Saldos Reales de Cuentas")
        
        st.markdown("#### Saldos INICIALES (al inicio del período)")
        col1, col2 = st.columns(2)
        
        with col1:
            saldo_inicial_fidu = st.number_input(
                "Saldo Inicial Fiducuenta",
                min_value=0.0,
                value=st.session_state.saldos_iniciales.get('Fiducuenta', 0.0),
                step=1000000.0,
                format="%.2f",
                key='saldo_inicial_fidu'
            )
            st.session_state.saldos_iniciales['Fiducuenta'] = saldo_inicial_fidu
        
        with col2:
            saldo_inicial_banco = st.number_input(
                "Saldo Inicial Cuenta Bancaria",
                min_value=0.0,
                value=st.session_state.saldos_iniciales.get('Cuenta Bancaria', 0.0),
                step=1000000.0,
                format="%.2f",
                key='saldo_inicial_banco'
            )
            st.session_state.saldos_iniciales['Cuenta Bancaria'] = saldo_inicial_banco
        
        saldo_inicial_real_total = saldo_inicial_fidu + saldo_inicial_banco
        
        st.markdown("#### Saldos FINALES (al final del período)")
        col3, col4 = st.columns(2)
        
        with col3:
            saldo_final_fidu = st.number_input(
                "Saldo Final Fiducuenta",
                min_value=0.0,
                value=st.session_state.saldos_finales.get('Fiducuenta', 0.0),
                step=1000000.0,
                format="%.2f",
                key='saldo_final_fidu'
            )
            st.session_state.saldos_finales['Fiducuenta'] = saldo_final_fidu
        
        with col4:
            saldo_final_banco = st.number_input(
                "Saldo Final Cuenta Bancaria",
                min_value=0.0,
                value=st.session_state.saldos_finales.get('Cuenta Bancaria', 0.0),
                step=1000000.0,
                format="%.2f",
                key='saldo_final_banco'
            )
            st.session_state.saldos_finales['Cuenta Bancaria'] = saldo_final_banco
        
        saldo_final_real_total = saldo_final_fidu + saldo_final_banco
        
        col_i, col_f = st.columns(2)
        col_i.info(f"**Saldo Inicial Real Total:** {formatear_moneda(saldo_inicial_real_total)}")
        col_f.info(f"**Saldo Final Real Total:** {formatear_moneda(saldo_final_real_total)}")
    
    # PASO 4: Ajustes
    if st.session_state.saldos_iniciales and st.session_state.saldos_finales:
        st.divider()
        st.subheader("⚙️ PASO 4: Ajustes del Período")
        
        st.warning("""
        ⚠️ **IMPORTANTE:** 
        - El sistema calcula AUTOMÁTICAMENTE el ajuste inicial para normalizar el punto de partida
        - **NO incluyas** un ajuste manual de "diferencia histórica inicial" en el JSON
        - Solo registra aquí los ajustes ADICIONALES del período (ingresos/egresos no modelados, etc.)
        """)
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            archivo_id_key = f"json_ajustes_{hash(str(st.session_state.get('last_upload_time', '')))}"
            archivo_ajustes = st.file_uploader("Importar ajustes (JSON)", type=['json'], key=archivo_id_key)
        
        with col2:
            if st.button("➕ Agregar", use_container_width=True):
                st.session_state.agregar_ajuste = True
        
        with col3:
            if st.button("💾 Exportar", use_container_width=True, disabled=len(st.session_state.ajustes)==0):
                # Exportar ajustes
                json_ajustes = json.dumps(st.session_state.ajustes, indent=2, ensure_ascii=False)
                st.download_button(
                    "⬇️ Descargar JSON",
                    data=json_ajustes,
                    file_name=f"ajustes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
        
        # Importar ajustes
        if archivo_ajustes:
            archivo_id = f"{archivo_ajustes.name}_{archivo_ajustes.size}"
            if st.session_state.get('ultimo_archivo_ajustes') != archivo_id:
                try:
                    ajustes_data = json.load(archivo_ajustes)
                    st.session_state.ajustes = ajustes_data
                    st.session_state.ultimo_archivo_ajustes = archivo_id
                    st.session_state.last_upload_time = datetime.now()
                    st.success(f"✅ {len(ajustes_data)} ajustes importados")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        # Agregar ajuste manual
        if st.session_state.get('agregar_ajuste', False):
            with st.form("form_nuevo_ajuste"):
                st.markdown("**Nuevo Ajuste:**")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    fecha_aj = st.date_input("Fecha", value=datetime.now().date())
                    cuenta_aj = st.selectbox("Cuenta", ["Fiducuenta", "Cuenta Bancaria", "Ambas"])
                
                with col2:
                    categoria_aj = st.selectbox("Categoría", [
                        "Ajuste de timing",
                        "Ingresos no modelados",
                        "Egresos no modelados",
                        "Gastos no modelados",
                        "Proyectos anteriores (pre-SICONE)",
                        "Préstamos empleados - Recuperación",
                        "Otro"
                    ])
                    tipo_aj = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                
                with col3:
                    monto_aj = st.number_input("Monto ($)", min_value=0.0, step=100000.0, format="%.2f")
                
                concepto_aj = st.text_input("Concepto")
                
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.form_submit_button("💾 Guardar", type="primary", use_container_width=True):
                        nuevo_ajuste = {
                            "fecha": fecha_aj.isoformat(),
                            "categoria": categoria_aj,
                            "concepto": concepto_aj,
                            "cuenta": cuenta_aj,
                            "tipo": tipo_aj,
                            "monto": monto_aj,
                            "observaciones": "",
                            "evidencia": ""
                        }
                        st.session_state.ajustes.append(nuevo_ajuste)
                        st.session_state.agregar_ajuste = False
                        st.success("✅ Ajuste agregado")
                        st.rerun()
                
                with col_cancel:
                    if st.form_submit_button("❌ Cancelar", use_container_width=True):
                        st.session_state.agregar_ajuste = False
                        st.rerun()
        
        # Mostrar ajustes con edición
        if st.session_state.ajustes:
            st.markdown("**Ajustes Registrados:**")
            
            total_ing = sum(a['monto'] for a in st.session_state.ajustes if a['tipo'] == 'Ingreso')
            total_egr = sum(a['monto'] for a in st.session_state.ajustes if a['tipo'] == 'Egreso')
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Ingresos", formatear_moneda(total_ing))
            col2.metric("Egresos", formatear_moneda(total_egr))
            col3.metric("Neto", formatear_moneda(total_ing - total_egr))
            
            # Lista con editar y eliminar
            for idx, ajuste in enumerate(st.session_state.ajustes):
                col1, col2, col3 = st.columns([6, 1, 1])
                with col1:
                    st.text(f"#{idx}: {ajuste['concepto'][:50]} - {ajuste['tipo']} {formatear_moneda(ajuste['monto'])}")
                with col2:
                    if st.button("✏️", key=f"edit_{idx}"):
                        st.session_state[f'editando_{idx}'] = True
                        st.rerun()
                with col3:
                    if st.button("🗑️", key=f"del_{idx}"):
                        st.session_state.ajustes.pop(idx)
                        st.rerun()
                
                # Formulario de edición
                if st.session_state.get(f'editando_{idx}', False):
                    with st.form(f"form_edit_{idx}"):
                        st.markdown(f"**Editando Ajuste #{idx}:**")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            fecha_ed = st.date_input("Fecha", value=pd.to_datetime(ajuste['fecha']).date())
                            cuenta_ed = st.selectbox("Cuenta", ["Fiducuenta", "Cuenta Bancaria", "Ambas"],
                                                    index=["Fiducuenta", "Cuenta Bancaria", "Ambas"].index(ajuste['cuenta']))
                        
                        with col2:
                            categorias = ["Ajuste de timing", "Ingresos no modelados", "Egresos no modelados",
                                        "Gastos no modelados", "Proyectos anteriores (pre-SICONE)",
                                        "Préstamos empleados - Recuperación", "Otro"]
                            categoria_ed = st.selectbox("Categoría", categorias,
                                                       index=categorias.index(ajuste['categoria']) if ajuste['categoria'] in categorias else 0)
                            tipo_ed = st.selectbox("Tipo", ["Ingreso", "Egreso"],
                                                  index=["Ingreso", "Egreso"].index(ajuste['tipo']))
                        
                        with col3:
                            monto_ed = st.number_input("Monto ($)", value=float(ajuste['monto']),
                                                      min_value=0.0, step=100000.0, format="%.2f")
                        
                        concepto_ed = st.text_input("Concepto", value=ajuste['concepto'])
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.form_submit_button("💾 Guardar", type="primary", use_container_width=True):
                                st.session_state.ajustes[idx] = {
                                    "fecha": fecha_ed.isoformat(),
                                    "categoria": categoria_ed,
                                    "concepto": concepto_ed,
                                    "cuenta": cuenta_ed,
                                    "tipo": tipo_ed,
                                    "monto": monto_ed,
                                    "observaciones": ajuste.get('observaciones', ''),
                                    "evidencia": ajuste.get('evidencia', '')
                                }
                                st.session_state[f'editando_{idx}'] = False
                                st.success("✅ Actualizado")
                                st.rerun()
                        
                        with col_cancel:
                            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                                st.session_state[f'editando_{idx}'] = False
                                st.rerun()
    
    # PASO 5: CALCULAR
    if st.session_state.datos_sicone and st.session_state.saldos_iniciales and st.session_state.saldos_finales:
        st.divider()
        st.subheader("🔍 PASO 5: Calcular Conciliación")
        
        if st.button("CALCULAR", type="primary", use_container_width=True):
            # CÁLCULO CON AJUSTE INICIAL AUTOMÁTICO
            
            # 1. Extraer saldo SICONE del JSON
            saldo_sicone_json = st.session_state.datos_sicone.get('estado_caja', {}).get('saldo_total', 0)
            
            # 2. Saldos reales
            saldo_inicial_real = sum(st.session_state.saldos_iniciales.values())
            saldo_final_real = sum(st.session_state.saldos_finales.values())
            
            # 3. AJUSTE INICIAL AUTOMÁTICO
            # Normaliza el punto de partida
            # Hace que ambos partan del mismo valor para validar flujos del período
            ajuste_inicial_auto = saldo_sicone_json - saldo_inicial_real
            
            # 4. Ajustes del período (del usuario)
            ajustes_ing = sum(a['monto'] for a in st.session_state.ajustes if a['tipo'] == 'Ingreso')
            ajustes_egr = sum(a['monto'] for a in st.session_state.ajustes if a['tipo'] == 'Egreso')
            ajustes_periodo_neto = ajustes_ing - ajustes_egr
            
            # 5. Saldo SICONE Ajustado TOTAL
            # = Saldo SICONE + Ajuste Inicial Automático + Ajustes del Período
            # Nota: Ajuste inicial ya está "incluido" en saldo_sicone_json
            # pero lo separamos conceptualmente para claridad
            saldo_sicone_ajustado = saldo_sicone_json + ajustes_periodo_neto
            
            # 6. Diferencia final
            # Lo que SICONE proyecta vs lo que realmente hay
            diferencia = saldo_sicone_ajustado - saldo_final_real
            precision = 100 * (1 - abs(diferencia) / abs(saldo_final_real)) if saldo_final_real != 0 else 0
            
            # Guardar resultados
            st.session_state.resultados = {
                'saldo_inicial_sicone': saldo_sicone_json,
                'saldo_inicial_real': saldo_inicial_real,
                'ajuste_inicial': ajuste_inicial_auto,  # Calculado automáticamente
                'ajustes_neto': ajustes_periodo_neto,    # Del usuario
                'saldo_sicone_ajustado': saldo_sicone_ajustado,
                'saldo_final_real': saldo_final_real,
                'diferencia': diferencia,
                'precision': precision,
                'ajustes_ing': ajustes_ing,
                'ajustes_egr': ajustes_egr
            }
            
            st.success("✅ Cálculo completado")
            st.rerun()
    
    # RESULTADOS CON 3 TABS
    if 'resultados' in st.session_state:
        st.divider()
        st.header("📊 Resultados")
        
        res = st.session_state.resultados
        
        # Métricas principales
        col1, col2, col3 = st.columns(3)
        col1.metric("Saldo Final Real", formatear_moneda(res['saldo_final_real']))
        col2.metric("Diferencia", formatear_moneda(abs(res['diferencia'])))
        
        estado = "✅ OK" if res['precision'] >= 98 else "⚠️ REVISAR" if res['precision'] >= 95 else "🚨 CRÍTICO"
        col3.metric("Precisión", f"{res['precision']:.2f}%", delta=estado)
        
        # Fórmula completa
        st.info(f"""
        **💡 Fórmula de Conciliación Completa:**
        
        **Paso 1: Ajuste Inicial (Automático)**
        ```
        Ajuste Inicial = Saldo SICONE - Saldo Inicial Real
        {formatear_moneda(res['ajuste_inicial'])} = {formatear_moneda(res['saldo_inicial_sicone'])} - {formatear_moneda(res['saldo_inicial_real'])}
        ```
        
        **Paso 2: Saldo SICONE Ajustado**
        ```
        Saldo SICONE Ajustado = Saldo SICONE + Ajuste Inicial + Ajustes del Período
        {formatear_moneda(res['saldo_sicone_ajustado'])} = {formatear_moneda(res['saldo_inicial_sicone'])} + {formatear_moneda(res['ajuste_inicial'])} + {formatear_moneda(res['ajustes_neto'])}
        ```
        
        **Paso 3: Diferencia**
        ```
        Diferencia = Saldo SICONE Ajustado - Saldo Final Real
        {formatear_moneda(res['diferencia'])} = {formatear_moneda(res['saldo_sicone_ajustado'])} - {formatear_moneda(res['saldo_final_real'])}
        ```
        """)
        
        # Interpretación
        if abs(res['diferencia']) > 1000:
            if res['diferencia'] > 0:
                st.warning(f"""
                **📊 Interpretación:** SICONE proyecta **{formatear_moneda(abs(res['diferencia']))} más** que el saldo real.
                
                - **Saldo SICONE Ajustado:** {formatear_moneda(res['saldo_sicone_ajustado'])}
                - **Saldo Final Real:** {formatear_moneda(res['saldo_final_real'])}
                - **Diferencia:** {formatear_moneda(abs(res['diferencia']))}
                
                **Posibles causas:**
                - 💰 **Ingresos sobreestimados:** SICONE proyectó ingresos que no se recibieron completamente
                - 💸 **Egresos no registrados:** Gastos reales que no están en el modelo SICONE
                - 🔄 **Timing:** Diferencias temporales en registro de transacciones
                """)
            else:
                st.warning(f"""
                **📊 Interpretación:** El saldo real es **{formatear_moneda(abs(res['diferencia']))} mayor** que lo proyectado.
                
                - **Saldo Final Real:** {formatear_moneda(res['saldo_final_real'])}
                - **Saldo SICONE Ajustado:** {formatear_moneda(res['saldo_sicone_ajustado'])}
                - **Diferencia:** {formatear_moneda(abs(res['diferencia']))}
                
                **Posibles causas:**
                - 💰 **Ingresos adicionales:** Se recibieron ingresos no proyectados en SICONE
                - 💸 **Egresos subestimados:** Los gastos reales fueron menores
                - 🔄 **Timing:** Diferencias temporales en registro de transacciones
                """)
        else:
            st.success(f"✅ **Excelente conciliación:** La diferencia es de solo {formatear_moneda(abs(res['diferencia']))}")
        
        # TABS DE ANÁLISIS
        st.divider()
        st.subheader("📈 Análisis Visual")
        
        tab1, tab2, tab3 = st.tabs(["📊 Comparación General", "🎯 Desglose de Ajustes", "🏦 Análisis Consolidado"])
        
        # TAB 1: Comparación General
        with tab1:
            st.markdown("### Comparación: Saldos Reales (Azul) vs SICONE Proyectados (Naranja)")
            
            # Gráfico de barras
            fig_comp = go.Figure()
            
            # Por cuenta
            for i, (cuenta, saldo) in enumerate(st.session_state.saldos_finales.items()):
                # Real
                fig_comp.add_trace(go.Bar(
                    name=f"{cuenta} - Real",
                    x=[cuenta],
                    y=[saldo],
                    text=[formatear_moneda(saldo)],
                    textposition='auto',
                    marker_color='#3498db',
                    legendgroup='real'
                ))
                # SICONE (proporcional)
                proporcion = saldo / res['saldo_final_real'] if res['saldo_final_real'] > 0 else 0.5
                saldo_sicone_cuenta = res['saldo_sicone_ajustado'] * proporcion
                fig_comp.add_trace(go.Bar(
                    name=f"{cuenta} - SICONE",
                    x=[cuenta],
                    y=[saldo_sicone_cuenta],
                    text=[formatear_moneda(saldo_sicone_cuenta)],
                    textposition='auto',
                    marker_color='#e67e22',
                    legendgroup='sicone'
                ))
            
            fig_comp.update_layout(
                barmode='group',
                height=450,
                yaxis_title="Monto ($)",
                xaxis_title="Cuenta",
                template="plotly_white"
            )
            st.plotly_chart(fig_comp, use_container_width=True)
            
            # Tabla resumen
            st.markdown("### 📋 Resumen Detallado")
            
            resumen_data = []
            for cuenta, saldo_final in st.session_state.saldos_finales.items():
                saldo_inicial = st.session_state.saldos_iniciales.get(cuenta, 0)
                proporcion = saldo_final / res['saldo_final_real'] if res['saldo_final_real'] > 0 else 0.5
                saldo_sicone_cuenta = res['saldo_sicone_ajustado'] * proporcion
                diferencia_cuenta = saldo_sicone_cuenta - saldo_final
                
                resumen_data.append({
                    'Cuenta': cuenta,
                    'Saldo Inicial': formatear_moneda(saldo_inicial),
                    'Saldo Final Real': formatear_moneda(saldo_final),
                    'Saldo Final SICONE': formatear_moneda(saldo_sicone_cuenta),
                    'Diferencia': formatear_moneda(abs(diferencia_cuenta)),
                    'Estado': "✅" if abs(diferencia_cuenta) < 1000000 else "⚠️"
                })
            
            df_resumen = pd.DataFrame(resumen_data)
            st.dataframe(df_resumen, use_container_width=True, hide_index=True)
        
        # TAB 2: Desglose de Ajustes
        with tab2:
            st.markdown("### 🎯 Impacto de Ajustes")
            
            if st.session_state.ajustes:
                # Gráfico de torta
                ajustes_por_categoria = {}
                for ajuste in st.session_state.ajustes:
                    key = f"{ajuste['tipo']} - {ajuste['categoria']}"
                    if key not in ajustes_por_categoria:
                        ajustes_por_categoria[key] = 0
                    monto = ajuste['monto'] if ajuste['tipo'] == 'Ingreso' else -ajuste['monto']
                    ajustes_por_categoria[key] += monto
                
                fig_ajustes = go.Figure(data=[go.Pie(
                    labels=list(ajustes_por_categoria.keys()),
                    values=[abs(v) for v in ajustes_por_categoria.values()],
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
                st.markdown("### 📝 Detalle de Ajustes")
                df_ajustes = pd.DataFrame(st.session_state.ajustes)
                st.dataframe(df_ajustes[['fecha', 'categoria', 'concepto', 'tipo', 'monto', 'cuenta']], 
                           use_container_width=True, hide_index=True)
            else:
                st.info("No hay ajustes registrados")
        
        # TAB 3: Análisis Consolidado
        with tab3:
            st.markdown("### 🏦 Flujo Consolidado")
            
            # Métricas
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Saldo Inicial SICONE", formatear_moneda(res['saldo_inicial_sicone']))
            col2.metric("Saldo Inicial Real", formatear_moneda(res['saldo_inicial_real']))
            col3.metric("Ajustes Neto", formatear_moneda(res['ajustes_neto']))
            col4.metric("Diferencia Final", formatear_moneda(abs(res['diferencia'])))
            
            # Waterfall consolidado
            fig = go.Figure(go.Waterfall(
                x=["Saldo SICONE", "+ Ajustes", "= SICONE Ajustado", "vs Saldo Real", "= Diferencia"],
                y=[
                    res['saldo_inicial_sicone'],
                    res['ajustes_neto'],
                    0,  # total
                    -res['saldo_final_real'],
                    0   # total final
                ],
                measure=["absolute", "relative", "total", "relative", "total"],
                text=[
                    formatear_moneda(res['saldo_inicial_sicone']),
                    formatear_moneda(res['ajustes_neto']),
                    formatear_moneda(res['saldo_sicone_ajustado']),
                    formatear_moneda(res['saldo_final_real']),
                    formatear_moneda(abs(res['diferencia']))
                ],
                textposition="outside",
                connector={"line": {"color": "rgb(100, 100, 100)", "dash": "dot"}},
                increasing={"marker": {"color": "#2ecc71"}},
                decreasing={"marker": {"color": "#e74c3c"}},
                totals={"marker": {"color": "#3498db"}}
            ))
            
            fig.update_layout(
                title="Conciliación SICONE<br><sub>Saldo Inicial → Ajustes → Saldo Final → Comparación con Real</sub>",
                height=600,
                showlegend=False,
                yaxis_title="Monto ($)",
                template="plotly_white",
                xaxis={'type': 'category'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Explicación del ajuste inicial
            st.markdown("### 💡 Ajuste Inicial Automático")
            
            if res['ajuste_inicial'] != 0:
                st.info(f"""
                **Ajuste Inicial Calculado:** {formatear_moneda(abs(res['ajuste_inicial']))} ({'Ingreso' if res['ajuste_inicial'] > 0 else 'Egreso'})
                
                **Propósito:** Normalizar el punto de partida para validar los flujos del período.
                
                **Cálculo:**
                ```
                Saldo Inicial SICONE:  {formatear_moneda(res['saldo_inicial_sicone'])}
                Saldo Inicial Real:    {formatear_moneda(res['saldo_inicial_real'])}
                ─────────────────────────────────────────────
                Ajuste Inicial:        {formatear_moneda(res['ajuste_inicial'])}
                ```
                
                **Interpretación:**
                - Este ajuste representa TODO lo anterior al período de análisis ({st.session_state.fecha_inicio} a {st.session_state.fecha_fin})
                - Permite validar SOLO los flujos del período actual
                - "Esto es lo anterior al período, después te ocupas de ello"
                - Los ajustes adicionales se aplican a los flujos del período
                
                **Validación:**
                Con este ajuste, ambos puntos de partida son iguales, permitiendo comparar:
                - ✅ Flujos proyectados SICONE vs Flujos reales del período
                - ✅ Saldo final proyectado vs Saldo final real
                """)
            else:
                st.success("""
                ✅ **Saldos iniciales coinciden exactamente**
                
                No se requiere ajuste inicial. Los saldos iniciales de SICONE y las cuentas reales son iguales.
                """)

if __name__ == "__main__":
    st.set_page_config(page_title="Conciliación", page_icon="🔍", layout="wide")
    main()
