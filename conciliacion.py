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
    if 'saldos_reales' not in st.session_state:
        st.session_state.saldos_reales = {}
    if 'datos_sicone' not in st.session_state:
        st.session_state.datos_sicone = None
    if 'ajustes' not in st.session_state:
        st.session_state.ajustes = []
    
    # PASO 1: Cargar datos SICONE
    st.subheader("📂 PASO 1: Datos SICONE")
    
    archivo_json = st.file_uploader("Subir consolidado SICONE (JSON)", type=['json'], key='json_sicone')
    
    if archivo_json:
        try:
            datos = json.load(archivo_json)
            st.session_state.datos_sicone = datos
            
            # Extraer saldo
            saldo_sicone = datos.get('estado_caja', {}).get('saldo_total', 0)
            
            st.success(f"✅ Datos cargados - Saldo SICONE: {formatear_moneda(saldo_sicone)}")
            
        except Exception as e:
            st.error(f"Error al cargar JSON: {e}")
    
    # PASO 2: Saldos reales
    if st.session_state.datos_sicone:
        st.divider()
        st.subheader("💰 PASO 2: Saldos Reales")
        
        col1, col2 = st.columns(2)
        
        with col1:
            saldo_fiducuenta = st.number_input(
                "Saldo Fiducuenta",
                min_value=0.0,
                value=st.session_state.saldos_reales.get('Fiducuenta', 0.0),
                step=1000000.0,
                format="%.2f",
                key='saldo_fidu'
            )
            st.session_state.saldos_reales['Fiducuenta'] = saldo_fiducuenta
        
        with col2:
            saldo_banco = st.number_input(
                "Saldo Cuenta Bancaria",
                min_value=0.0,
                value=st.session_state.saldos_reales.get('Cuenta Bancaria', 0.0),
                step=1000000.0,
                format="%.2f",
                key='saldo_banco'
            )
            st.session_state.saldos_reales['Cuenta Bancaria'] = saldo_banco
        
        saldo_real_total = saldo_fiducuenta + saldo_banco
        st.info(f"**Saldo Real Total:** {formatear_moneda(saldo_real_total)}")
    
    # PASO 3: Ajustes
    if st.session_state.saldos_reales:
        st.divider()
        st.subheader("⚙️ PASO 3: Ajustes (Opcional)")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            archivo_ajustes = st.file_uploader("Importar ajustes (JSON)", type=['json'], key='json_ajustes')
        
        with col2:
            if st.button("➕ Agregar Manual", use_container_width=True):
                st.session_state.agregar_ajuste = True
        
        # Importar ajustes
        if archivo_ajustes:
            try:
                ajustes_data = json.load(archivo_ajustes)
                st.session_state.ajustes = ajustes_data
                st.success(f"✅ {len(ajustes_data)} ajustes importados")
            except Exception as e:
                st.error(f"Error: {e}")
        
        # Mostrar ajustes
        if st.session_state.ajustes:
            st.markdown("**Ajustes Registrados:**")
            
            total_ing = sum(a['monto'] for a in st.session_state.ajustes if a['tipo'] == 'Ingreso')
            total_egr = sum(a['monto'] for a in st.session_state.ajustes if a['tipo'] == 'Egreso')
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Ingresos", formatear_moneda(total_ing))
            col2.metric("Egresos", formatear_moneda(total_egr))
            col3.metric("Neto", formatear_moneda(total_ing - total_egr))
            
            # Tabla
            df_ajustes = pd.DataFrame(st.session_state.ajustes)
            st.dataframe(df_ajustes[['fecha', 'concepto', 'tipo', 'monto']], use_container_width=True)
    
    # PASO 4: CALCULAR
    if st.session_state.datos_sicone and st.session_state.saldos_reales:
        st.divider()
        st.subheader("🔍 PASO 4: Calcular Conciliación")
        
        if st.button("CALCULAR", type="primary", use_container_width=True):
            # CÁLCULO DIRECTO
            saldo_sicone = st.session_state.datos_sicone.get('estado_caja', {}).get('saldo_total', 0)
            
            # Ajustes
            ajustes_ing = sum(a['monto'] for a in st.session_state.ajustes if a['tipo'] == 'Ingreso')
            ajustes_egr = sum(a['monto'] for a in st.session_state.ajustes if a['tipo'] == 'Egreso')
            ajustes_neto = ajustes_ing - ajustes_egr
            
            # Saldo ajustado
            saldo_sicone_ajustado = saldo_sicone + ajustes_neto
            
            # Saldo real
            saldo_real = sum(st.session_state.saldos_reales.values())
            
            # Diferencia
            diferencia = saldo_sicone_ajustado - saldo_real
            precision = 100 * (1 - abs(diferencia) / abs(saldo_real)) if saldo_real != 0 else 0
            
            # Guardar resultados
            st.session_state.resultados = {
                'saldo_sicone': saldo_sicone,
                'ajustes_neto': ajustes_neto,
                'saldo_sicone_ajustado': saldo_sicone_ajustado,
                'saldo_real': saldo_real,
                'diferencia': diferencia,
                'precision': precision
            }
            
            st.success("✅ Cálculo completado")
            st.rerun()
    
    # RESULTADOS
    if 'resultados' in st.session_state:
        st.divider()
        st.header("📊 Resultados")
        
        res = st.session_state.resultados
        
        # Métricas
        col1, col2, col3 = st.columns(3)
        col1.metric("Saldo Real", formatear_moneda(res['saldo_real']))
        col2.metric("Diferencia", formatear_moneda(abs(res['diferencia'])))
        
        estado = "✅ OK" if res['precision'] >= 98 else "⚠️ REVISAR" if res['precision'] >= 95 else "🚨 CRÍTICO"
        col3.metric("Precisión", f"{res['precision']:.2f}%", delta=estado)
        
        # Fórmula
        st.info(f"""
        **💡 Fórmula de Conciliación:**
        
        `Saldo Final SICONE = Saldo Inicial SICONE + Ajustes Neto`
        
        `{formatear_moneda(res['saldo_sicone'])} + {formatear_moneda(res['ajustes_neto'])} = {formatear_moneda(res['saldo_sicone_ajustado'])}`
        
        `Diferencia = Saldo SICONE Ajustado - Saldo Real`
        
        `{formatear_moneda(res['saldo_sicone_ajustado'])} - {formatear_moneda(res['saldo_real'])} = {formatear_moneda(res['diferencia'])}`
        """)
        
        # Interpretación
        if abs(res['diferencia']) > 1000:
            if res['diferencia'] > 0:
                st.warning(f"""
                **📊 Interpretación:** SICONE proyecta **{formatear_moneda(abs(res['diferencia']))} más** que el saldo real.
                
                - **Saldo SICONE Ajustado:** {formatear_moneda(res['saldo_sicone_ajustado'])}
                - **Saldo Real:** {formatear_moneda(res['saldo_real'])}
                - **Diferencia:** {formatear_moneda(abs(res['diferencia']))}
                
                **Posibles causas:**
                - 💰 **Ingresos sobreestimados:** SICONE proyectó ingresos que no se recibieron completamente
                - 💸 **Egresos no registrados:** Gastos reales que no están en el modelo SICONE
                """)
            else:
                st.warning(f"""
                **📊 Interpretación:** El saldo real es **{formatear_moneda(abs(res['diferencia']))} mayor** que lo proyectado.
                
                - **Saldo Real:** {formatear_moneda(res['saldo_real'])}
                - **Saldo SICONE Ajustado:** {formatear_moneda(res['saldo_sicone_ajustado'])}
                - **Diferencia:** {formatear_moneda(abs(res['diferencia']))}
                
                **Posibles causas:**
                - 💰 **Ingresos adicionales:** Se recibieron ingresos no proyectados en SICONE
                - 💸 **Egresos subestimados:** Los gastos reales fueron menores
                """)
        
        # Gráfico
        st.subheader("📈 Visualización")
        
        fig = go.Figure(go.Waterfall(
            x=["Saldo SICONE", "+ Ajustes", "= SICONE Ajustado", "- Saldo Real", "= Diferencia"],
            y=[
                res['saldo_sicone'],
                res['ajustes_neto'],
                0,
                -res['saldo_real'],
                0
            ],
            measure=["absolute", "relative", "total", "relative", "total"],
            text=[
                formatear_moneda(res['saldo_sicone']),
                formatear_moneda(res['ajustes_neto']),
                formatear_moneda(res['saldo_sicone_ajustado']),
                formatear_moneda(res['saldo_real']),
                formatear_moneda(abs(res['diferencia']))
            ],
            textposition="outside"
        ))
        
        fig.update_layout(
            title="Conciliación SICONE",
            height=500,
            yaxis_title="Monto ($)"
        )
        
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    st.set_page_config(page_title="Conciliación", page_icon="🔍", layout="wide")
    main()
