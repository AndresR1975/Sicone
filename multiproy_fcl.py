"""
SICONE - Módulo de Análisis Multiproyecto FCL
Consolidación y análisis de flujo de caja para múltiples proyectos

Versión: 1.0.0
Fecha: Diciembre 10, 2024
Autor: AI-MindNovation

FUNCIONALIDADES:
1. Carga de múltiples proyectos desde JSON completo
2. Consolidación temporal en eje único
3. Dashboard con métricas consolidadas
4. Análisis de estado de caja empresarial
5. Proyección configurable (default: 8 semanas)
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional
import os

# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

SEMANAS_FUTURO_DEFAULT = 8
COLORES_PROYECTOS = [
    '#1f77b4',  # Azul
    '#ff7f0e',  # Naranja
    '#2ca02c',  # Verde
    '#d62728',  # Rojo
    '#9467bd',  # Púrpura
    '#8c564b',  # Marrón
    '#e377c2',  # Rosa
    '#7f7f7f',  # Gris
]

ESTADO_COLORES = {
    'CRÍTICO': '#d62728',    # Rojo
    'ALERTA': '#ff7f0e',     # Naranja
    'ESTABLE': '#2ca02c',    # Verde
    'EXCEDENTE': '#1f77b4'   # Azul
}

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def formatear_moneda(valor: float) -> str:
    """Formatea un valor numérico como moneda COP"""
    if pd.isna(valor):
        return "$0"
    return f"${valor:,.0f}".replace(",", ".")

def calcular_semana_desde_fecha(fecha_inicio: date, fecha_actual: date) -> int:
    """Calcula el número de semana desde una fecha de inicio"""
    dias = (fecha_actual - fecha_inicio).days
    return max(1, (dias // 7) + 1)

def determinar_estado_liquidez(saldo: float, margen: float) -> str:
    """Determina el estado de liquidez basado en saldo y margen"""
    if saldo < 0:
        return 'CRÍTICO'
    elif saldo < margen * 0.5:
        return 'CRÍTICO'
    elif saldo < margen:
        return 'ALERTA'
    elif saldo < margen * 2:
        return 'ESTABLE'
    else:
        return 'EXCEDENTE'

# ============================================================================
# CLASE PRINCIPAL: ConsolidadorMultiproyecto
# ============================================================================

class ConsolidadorMultiproyecto:
    """
    Clase para consolidar y analizar múltiples proyectos
    """
    
    def __init__(self, semanas_futuro: int = SEMANAS_FUTURO_DEFAULT):
        self.proyectos = []
        self.semanas_futuro = semanas_futuro
        self.df_consolidado = None
        self.fecha_inicio_empresa = None
        self.fecha_actual = date.today()
        self.semana_actual_consolidada = None
    
    def cargar_proyecto(self, ruta_json: str) -> bool:
        """
        Carga un proyecto desde su JSON completo
        
        Args:
            ruta_json: Ruta al archivo JSON completo del proyecto
            
        Returns:
            bool: True si se cargó exitosamente
        """
        try:
            with open(ruta_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validar estructura mínima
            if 'proyecto' not in data:
                st.error(f"❌ JSON inválido: {ruta_json} - Falta clave 'proyecto'")
                return False
            
            # Extraer información básica
            proyecto_info = {
                'nombre': data['proyecto'].get('nombre', 'Sin nombre'),
                'fecha_inicio': datetime.fromisoformat(data['proyecto']['fecha_inicio']).date(),
                'data': data,
                'archivo': os.path.basename(ruta_json)
            }
            
            # Determinar estado del proyecto
            if proyecto_info['fecha_inicio'] > self.fecha_actual:
                proyecto_info['estado'] = 'EN_COTIZACIÓN'
            else:
                # Verificar si tiene datos reales
                tiene_egresos = data.get('egresos') and data['egresos'].get('egresos_semanales')
                tiene_cartera = data.get('cartera') and data['cartera']
                tiene_tesoreria = data.get('tesoreria') and data['tesoreria'].get('metricas_semanales')
                
                # Debug info
                st.caption(f"   📊 {proyecto_info['nombre']}: Egresos={bool(tiene_egresos)}, Cartera={bool(tiene_cartera)}, Tesorería={bool(tiene_tesoreria)}")
                
                if tiene_egresos or tiene_cartera or tiene_tesoreria:
                    proyecto_info['estado'] = 'ACTIVO'
                else:
                    proyecto_info['estado'] = 'EN_COTIZACIÓN'
            
            self.proyectos.append(proyecto_info)
            return True
            
        except Exception as e:
            st.error(f"❌ Error al cargar {ruta_json}: {str(e)}")
            return False
    
    def consolidar(self):
        """
        Consolida todos los proyectos cargados en un DataFrame único
        """
        if not self.proyectos:
            st.error("❌ No hay proyectos cargados para consolidar")
            return
        
        # Determinar rango temporal consolidado
        self._determinar_rango_temporal()
        
        # Crear eje temporal consolidado
        df_consolidado = self._crear_eje_temporal()
        
        # Agregar datos de cada proyecto
        for idx, proyecto in enumerate(self.proyectos):
            df_consolidado = self._agregar_proyecto_a_consolidado(
                df_consolidado, 
                proyecto, 
                idx
            )
        
        # Calcular métricas consolidadas
        df_consolidado = self._calcular_metricas_consolidadas(df_consolidado)
        
        # Debug: Mostrar resumen de datos consolidados
        st.caption(f"📊 **Debug Consolidación Final:**")
        st.caption(f"   • Semanas totales: {len(df_consolidado)}")
        st.caption(f"   • Semana actual: {self.semana_actual_consolidada}")
        
        if len(df_consolidado) > 0:
            primera_semana_valida = None
            for idx in range(min(5, len(df_consolidado))):
                if df_consolidado['saldo_proy_total'].iloc[idx] > 0:
                    primera_semana_valida = idx
                    break
            
            if primera_semana_valida is not None:
                st.caption(f"   • Primera semana con datos (idx {primera_semana_valida}):")
                st.caption(f"      - Saldo proy total: ${df_consolidado['saldo_proy_total'].iloc[primera_semana_valida]:,.0f}")
                st.caption(f"      - Saldo real total: ${df_consolidado['saldo_real_total'].iloc[primera_semana_valida]:,.0f}")
                st.caption(f"      - Saldo consolidado: ${df_consolidado['saldo_consolidado'].iloc[primera_semana_valida]:,.0f}")
                st.caption(f"      - Egresos proy total: ${df_consolidado['egresos_proy_total'].iloc[primera_semana_valida]:,.0f}")
            else:
                st.warning("⚠️ No se encontraron semanas con saldo_proy_total > 0")
                st.caption(f"   Primeras 3 semanas saldo_proy_total:")
                for idx in range(min(3, len(df_consolidado))):
                    st.caption(f"      - Semana {idx+1}: ${df_consolidado['saldo_proy_total'].iloc[idx]:,.0f}")
        
        self.df_consolidado = df_consolidado
    
    def _determinar_rango_temporal(self):
        """Determina el rango temporal para la consolidación"""
        # Fecha inicio: La más temprana de todos los proyectos
        fechas_inicio = [p['fecha_inicio'] for p in self.proyectos]
        self.fecha_inicio_empresa = min(fechas_inicio)
        
        # Calcular semana actual consolidada
        self.semana_actual_consolidada = calcular_semana_desde_fecha(
            self.fecha_inicio_empresa,
            self.fecha_actual
        )
        
        # Fecha fin: semana actual + semanas futuro
        self.semana_fin_consolidada = self.semana_actual_consolidada + self.semanas_futuro
    
    def _crear_eje_temporal(self) -> pd.DataFrame:
        """Crea el eje temporal consolidado"""
        semanas = list(range(1, self.semana_fin_consolidada + 1))
        
        # Crear fechas directamente como datetime (no date)
        # Convertir fecha_inicio_empresa a datetime primero
        if isinstance(self.fecha_inicio_empresa, date) and not isinstance(self.fecha_inicio_empresa, datetime):
            fecha_base = datetime.combine(self.fecha_inicio_empresa, datetime.min.time())
        else:
            fecha_base = self.fecha_inicio_empresa
        
        # Generar fechas como datetime
        fechas = [
            fecha_base + timedelta(days=(s-1)*7)
            for s in semanas
        ]
        
        df = pd.DataFrame({
            'semana_consolidada': semanas,
            'fecha': pd.to_datetime(fechas),  # Asegurar que son pandas datetime
            'es_historica': [s <= self.semana_actual_consolidada for s in semanas],
            'es_futura': [s > self.semana_actual_consolidada for s in semanas]
        })
        
        return df
    
    def _agregar_proyecto_a_consolidado(
        self, 
        df: pd.DataFrame, 
        proyecto: Dict, 
        idx: int
    ) -> pd.DataFrame:
        """
        Agrega los datos de un proyecto al DataFrame consolidado
        """
        nombre = proyecto['nombre']
        data = proyecto['data']
        fecha_inicio_proy = proyecto['fecha_inicio']
        
        # Calcular semana de inicio relativa al consolidado
        semana_inicio_rel = calcular_semana_desde_fecha(
            self.fecha_inicio_empresa,
            fecha_inicio_proy
        )
        
        # Columnas para este proyecto
        col_semana = f'semana_{nombre}'
        col_saldo_proy = f'saldo_proy_{nombre}'
        col_saldo_real = f'saldo_real_{nombre}'
        col_ingresos_proy = f'ingresos_proy_{nombre}'
        col_egresos_proy = f'egresos_proy_{nombre}'
        col_egresos_real = f'egresos_real_{nombre}'
        col_estado = f'estado_{nombre}'
        
        # Inicializar columnas
        df[col_semana] = None
        df[col_saldo_proy] = 0
        df[col_saldo_real] = 0
        df[col_ingresos_proy] = 0
        df[col_egresos_proy] = 0
        df[col_egresos_real] = 0
        df[col_estado] = proyecto['estado']
        
        # Mapear proyección semanal
        proyeccion = data.get('proyeccion_semanal', [])
        
        # DEBUG
        st.caption(f"   🔍 Mapeando {nombre}: {len(proyeccion)} semanas de proyección")
        
        semanas_mapeadas = 0
        for sem_data in proyeccion:
            semana_proy = sem_data.get('Semana')
            if semana_proy:
                semana_cons = semana_inicio_rel + semana_proy - 1
                
                if semana_cons <= len(df):
                    idx_row = semana_cons - 1
                    df.at[idx_row, col_semana] = semana_proy
                    df.at[idx_row, col_saldo_proy] = sem_data.get('Saldo_Acumulado', 0)
                    df.at[idx_row, col_ingresos_proy] = sem_data.get('Ingresos_Proyectados', 0)
                    df.at[idx_row, col_egresos_proy] = sem_data.get('Total_Egresos', 0)
                    semanas_mapeadas += 1
        
        # DEBUG
        st.caption(f"      ✓ {semanas_mapeadas} semanas mapeadas correctamente")
        if semanas_mapeadas > 0 and semana_inicio_rel <= len(df):
            idx_primera = semana_inicio_rel - 1
            if idx_primera >= 0 and idx_primera < len(df):
                st.caption(f"      Ejemplo semana 1: Saldo=${df.at[idx_primera, col_saldo_proy]:,.0f}")
        
        # Mapear datos reales (si existen)
        if proyecto['estado'] == 'ACTIVO':
            # Egresos reales
            egresos = data.get('egresos', {})
            if egresos and egresos.get('egresos_semanales'):
                for eg_sem in egresos['egresos_semanales']:
                    semana_proy = eg_sem.get('semana')
                    if semana_proy:
                        semana_cons = semana_inicio_rel + semana_proy - 1
                        
                        if semana_cons <= len(df):
                            idx_row = semana_cons - 1
                            df.at[idx_row, col_egresos_real] = eg_sem.get('total', 0)
            
            # Saldo real (de tesorería)
            tesoreria = data.get('tesoreria', {})
            if tesoreria and tesoreria.get('metricas_semanales'):
                for met_sem in tesoreria['metricas_semanales']:
                    semana_proy = met_sem.get('semana')
                    if semana_proy:
                        semana_cons = semana_inicio_rel + semana_proy - 1
                        
                        if semana_cons <= len(df):
                            idx_row = semana_cons - 1
                            df.at[idx_row, col_saldo_real] = met_sem.get('saldo', 0)
        
        return df
    
    def _calcular_metricas_consolidadas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula métricas consolidadas para cada semana"""
        
        # Identificar columnas por tipo
        cols_saldo_proy = [c for c in df.columns if c.startswith('saldo_proy_')]
        cols_saldo_real = [c for c in df.columns if c.startswith('saldo_real_')]
        cols_ingresos_proy = [c for c in df.columns if c.startswith('ingresos_proy_')]
        cols_egresos_proy = [c for c in df.columns if c.startswith('egresos_proy_')]
        cols_egresos_real = [c for c in df.columns if c.startswith('egresos_real_')]
        
        # DEBUG: Mostrar columnas encontradas
        st.caption(f"🔍 **Debug Columnas:**")
        st.caption(f"   • Saldo proy: {len(cols_saldo_proy)} columnas")
        st.caption(f"   • Egresos proy: {len(cols_egresos_proy)} columnas")
        st.caption(f"   • Egresos real: {len(cols_egresos_real)} columnas")
        
        # Sumar por tipo
        df['saldo_proy_total'] = df[cols_saldo_proy].sum(axis=1)
        df['saldo_real_total'] = df[cols_saldo_real].sum(axis=1)
        df['ingresos_proy_total'] = df[cols_ingresos_proy].sum(axis=1)
        df['egresos_proy_total'] = df[cols_egresos_proy].sum(axis=1)
        df['egresos_real_total'] = df[cols_egresos_real].sum(axis=1)
        
        # DEBUG: Mostrar valores de primera fila de cada proyecto
        st.caption(f"🔍 **Debug Primera Semana (valores individuales):**")
        for col in cols_saldo_proy:
            valor = df[col].iloc[0]
            st.caption(f"   • {col}: ${valor:,.0f}")
        
        # DEBUG: Mostrar suma
        st.caption(f"   • SUMA saldo_proy_total: ${df['saldo_proy_total'].iloc[0]:,.0f}")
        
        # Saldo consolidado: SIEMPRE usa proyectado como base
        # Solo en semanas históricas con datos reales, calcular saldo basado en flujo real
        df['saldo_consolidado'] = df['saldo_proy_total'].copy()
        
        # Para semanas con datos reales, intentar calcular saldo real
        # basado en ingresos y egresos acumulados
        for idx in range(len(df)):
            if df.at[idx, 'es_historica'] and df.at[idx, 'saldo_real_total'] > 0:
                # Si hay saldo real registrado, usarlo
                df.at[idx, 'saldo_consolidado'] = df.at[idx, 'saldo_real_total']
        
        # Calcular Burn Rate (promedio últimas 8 semanas con datos reales)
        df['burn_rate'] = 0.0
        for idx in range(len(df)):
            if df.at[idx, 'es_historica']:
                # Buscar hasta 8 semanas atrás con datos
                ventana_inicio = max(0, idx - 7)
                ventana = df.iloc[ventana_inicio:idx+1]
                
                # Usar egresos reales si existen, sino usar egresos proyectados
                egresos_ventana = ventana['egresos_real_total']
                if egresos_ventana.sum() == 0:
                    # Si no hay egresos reales, usar proyectados como estimado
                    egresos_ventana = ventana['egresos_proy_total']
                
                egresos_positivos = egresos_ventana[egresos_ventana > 0]
                
                if len(egresos_positivos) > 0:
                    df.at[idx, 'burn_rate'] = egresos_positivos.mean()
        
        # Propagar burn rate a semanas futuras
        burn_rates_historicos = df[df['es_historica']]['burn_rate']
        burn_rates_positivos = burn_rates_historicos[burn_rates_historicos > 0]
        
        if len(burn_rates_positivos) > 0:
            ultimo_burn_rate = burn_rates_positivos.iloc[-1]
        else:
            # Si no hay burn rate histórico, calcular de egresos proyectados
            ultimo_burn_rate = df[df['es_historica']]['egresos_proy_total'].mean()
        
        df.loc[df['es_futura'], 'burn_rate'] = ultimo_burn_rate
        
        # Margen de protección (Burn Rate * 8 semanas)
        df['margen_proteccion'] = df['burn_rate'] * 8
        
        # Excedente invertible
        df['excedente_invertible'] = df['saldo_consolidado'] - df['margen_proteccion']
        
        # Estado general
        df['estado_general'] = df.apply(
            lambda row: determinar_estado_liquidez(
                row['saldo_consolidado'],
                row['margen_proteccion']
            ),
            axis=1
        )
        
        # Identificar proyecto más crítico por semana
        df['proyecto_critico'] = None
        for idx in range(len(df)):
            saldos = {}
            for proyecto in self.proyectos:
                nombre = proyecto['nombre']
                col_saldo = f'saldo_real_{nombre}'
                if col_saldo in df.columns:
                    saldo = df.at[idx, col_saldo]
                    if saldo > 0:  # Solo considerar proyectos con saldo real
                        saldos[nombre] = saldo
            
            if saldos:
                proyecto_min = min(saldos, key=saldos.get)
                df.at[idx, 'proyecto_critico'] = proyecto_min
        
        return df
    
    def get_estado_actual(self) -> Dict:
        """Obtiene el estado consolidado de la semana actual"""
        if self.df_consolidado is None:
            return {}
        
        semana_actual_row = self.df_consolidado[
            self.df_consolidado['semana_consolidada'] == self.semana_actual_consolidada
        ]
        
        if len(semana_actual_row) == 0:
            return {}
        
        row = semana_actual_row.iloc[0]
        
        # Contar proyectos por estado
        estados = {}
        for proyecto in self.proyectos:
            estado = proyecto['estado']
            estados[estado] = estados.get(estado, 0) + 1
        
        return {
            'semana': int(row['semana_consolidada']),
            'fecha': row['fecha'],
            'saldo_total': float(row['saldo_consolidado']),
            'burn_rate': float(row['burn_rate']),
            'margen_proteccion': float(row['margen_proteccion']),
            'excedente_invertible': float(row['excedente_invertible']),
            'estado_general': row['estado_general'],
            'proyecto_critico': row['proyecto_critico'],
            'proyectos_activos': estados.get('ACTIVO', 0),
            'proyectos_cotizacion': estados.get('EN_COTIZACIÓN', 0),
            'total_proyectos': len(self.proyectos)
        }


# ============================================================================
# FUNCIONES DE VISUALIZACIÓN
# ============================================================================

def render_metricas_principales(estado: Dict):
    """Renderiza las métricas principales del dashboard"""
    
    st.markdown("### 💰 Estado de Caja Empresarial")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Saldo Total",
            formatear_moneda(estado['saldo_total']),
            help="Saldo consolidado de todos los proyectos"
        )
    
    with col2:
        color_estado = ESTADO_COLORES.get(estado['estado_general'], '#gray')
        st.markdown(
            f"""
            <div style="text-align: center; padding: 10px; background-color: {color_estado}20; border-radius: 5px; border: 2px solid {color_estado};">
                <div style="font-size: 0.8rem; color: #666;">Estado General</div>
                <div style="font-size: 1.5rem; font-weight: bold; color: {color_estado};">{estado['estado_general']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        st.metric(
            "Proyectos Activos",
            f"{estado['proyectos_activos']}/{estado['total_proyectos']}",
            help="Proyectos en ejecución vs total"
        )
    
    with col4:
        if estado['proyecto_critico']:
            st.metric(
                "Proyecto Más Crítico",
                estado['proyecto_critico'],
                help="Proyecto con menor saldo"
            )
        else:
            st.metric(
                "Proyecto Más Crítico",
                "N/A",
                help="No hay proyectos activos"
            )


def render_metricas_cobertura(estado: Dict):
    """Renderiza métricas de cobertura operativa"""
    
    st.markdown("### 📈 Análisis de Cobertura Operativa")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Burn Rate Consolidado",
            f"{formatear_moneda(estado['burn_rate'])} / semana",
            help="Promedio de gastos semanales (últimas 8 semanas)"
        )
    
    with col2:
        st.metric(
            "Margen Requerido (8 sem)",
            formatear_moneda(estado['margen_proteccion']),
            help="Burn Rate × 8 semanas"
        )
    
    with col3:
        if estado['burn_rate'] > 0:
            semanas_cobertura = estado['saldo_total'] / estado['burn_rate']
            color = "normal" if semanas_cobertura >= 8 else "inverse"
        else:
            semanas_cobertura = 999
            color = "normal"
        
        st.metric(
            "Cobertura Disponible",
            f"{semanas_cobertura:.1f} semanas",
            delta="✅ Suficiente" if semanas_cobertura >= 8 else "⚠️ Insuficiente",
            delta_color=color,
            help="Semanas que puede operar con saldo actual"
        )


def render_excedente_invertible(estado: Dict):
    """Renderiza información del excedente invertible"""
    
    st.markdown("### 💵 Excedente Invertible Consolidado")
    
    excedente = estado['excedente_invertible']
    
    if excedente > 0:
        st.success(f"**{formatear_moneda(excedente)}** disponibles para inversión")
        st.caption("💡 Fondos que exceden el margen de protección requerido")
    elif excedente == 0:
        st.info("Sin excedente disponible (saldo = margen de protección)")
    else:
        st.warning(f"⚠️ Déficit de **{formatear_moneda(abs(excedente))}** respecto al margen recomendado")


def render_timeline_consolidado(consolidador: ConsolidadorMultiproyecto):
    """Renderiza la gráfica timeline consolidado"""
    
    st.markdown("### 📊 Timeline Consolidado - Saldo Empresarial")
    
    df = consolidador.df_consolidado
    
    if df is None or len(df) == 0:
        st.warning("No hay datos para visualizar")
        return
    
    # Convertir fechas de Pandas Timestamp a Python datetime para Plotly
    fechas_py = []
    for f in df['fecha']:
        if hasattr(f, 'to_pydatetime'):
            fechas_py.append(f.to_pydatetime())
        else:
            fechas_py.append(f)
    
    # Crear figura
    fig = go.Figure()
    
    # Línea de saldo consolidado
    fig.add_trace(go.Scatter(
        x=fechas_py,
        y=df['saldo_consolidado'],
        mode='lines',
        name='Saldo Consolidado',
        line=dict(color='#1f77b4', width=3),
        hovertemplate='<b>Semana %{customdata[0]}</b><br>' +
                      'Fecha: %{x|%Y-%m-%d}<br>' +
                      'Saldo: $%{y:,.0f}<br>' +
                      '<extra></extra>',
        customdata=df[['semana_consolidada']].values
    ))
    
    # Línea de margen de protección
    fig.add_trace(go.Scatter(
        x=fechas_py,
        y=df['margen_proteccion'],
        mode='lines',
        name='Margen de Protección',
        line=dict(color='#d62728', width=2, dash='dash'),
        hovertemplate='<b>Margen de Protección</b><br>' +
                      'Monto: $%{y:,.0f}<br>' +
                      '<extra></extra>'
    ))
    
    # Marcar semana actual
    semana_actual_data = df[df['semana_consolidada'] == consolidador.semana_actual_consolidada]
    if len(semana_actual_data) > 0:
        # Convertir Pandas Timestamp a Python datetime puro
        fecha_ts = semana_actual_data['fecha'].iloc[0]
        if hasattr(fecha_ts, 'to_pydatetime'):
            fecha_actual = fecha_ts.to_pydatetime()
        else:
            fecha_actual = fecha_ts
        
        # Usar add_vline SIN annotation_text para evitar error de sum()
        fig.add_vline(
            x=fecha_actual,
            line_dash="dot",
            line_color="gray",
            line_width=2
        )
        
        # Agregar anotación manualmente en lugar de usar annotation_text
        fig.add_annotation(
            x=fecha_actual,
            y=1,
            yref="paper",
            text="Hoy",
            showarrow=False,
            yshift=10,
            font=dict(size=10, color="gray")
        )
    
    # Sombrear zona de riesgo (debajo del margen)
    # Usar fechas_py ya convertidas anteriormente
    fig.add_trace(go.Scatter(
        x=fechas_py + fechas_py[::-1],
        y=[0]*len(df) + df['margen_proteccion'].tolist()[::-1],
        fill='toself',
        fillcolor='rgba(214, 39, 40, 0.1)',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Configuración
    fig.update_layout(
        xaxis_title="Fecha",
        yaxis_title="Monto (COP)",
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# FUNCIÓN PRINCIPAL DEL MÓDULO
# ============================================================================

def main():
    """Función principal del módulo multiproyecto"""
    
    st.title("🏢 SICONE - Análisis Multiproyecto FCL")
    st.caption("Consolidación y análisis de flujo de caja empresarial")
    
    st.markdown("---")
    
    # Sidebar: Configuración
    with st.sidebar:
        st.markdown("### ⚙️ Configuración")
        
        semanas_futuro = st.slider(
            "Horizonte de Análisis",
            min_value=4,
            max_value=16,
            value=SEMANAS_FUTURO_DEFAULT,
            step=1,
            help="Semanas a proyectar hacia adelante"
        )
        
        st.markdown("---")
        st.markdown("### 📁 Proyectos Cargados")
    
    # Paso 1: Cargar proyectos
    st.markdown("## 📥 Paso 1: Cargar Proyectos")
    
    archivos_json = st.file_uploader(
        "Seleccione los archivos JSON completos de los proyectos",
        type=['json'],
        accept_multiple_files=True,
        help="Cargar archivos SICONE_*_Completo_*.json"
    )
    
    if not archivos_json:
        st.info("👆 Cargue 2 o más archivos JSON para comenzar el análisis")
        return
    
    # Cargar proyectos
    consolidador = ConsolidadorMultiproyecto(semanas_futuro=semanas_futuro)
    
    with st.spinner("Cargando proyectos..."):
        proyectos_cargados = 0
        for archivo in archivos_json:
            # Guardar temporalmente
            temp_path = f"/tmp/{archivo.name}"
            with open(temp_path, 'wb') as f:
                f.write(archivo.getvalue())
            
            if consolidador.cargar_proyecto(temp_path):
                proyectos_cargados += 1
    
    if proyectos_cargados == 0:
        st.error("❌ No se pudo cargar ningún proyecto")
        return
    
    st.success(f"✅ {proyectos_cargados} proyecto(s) cargado(s) exitosamente")
    
    # Mostrar lista de proyectos en sidebar
    with st.sidebar:
        for i, proyecto in enumerate(consolidador.proyectos, 1):
            emoji = "🟢" if proyecto['estado'] == 'ACTIVO' else "🔵"
            st.caption(f"{emoji} {i}. {proyecto['nombre']} ({proyecto['estado']})")
    
    st.markdown("---")
    
    # Paso 2: Consolidar
    if st.button("🔄 Consolidar y Analizar", type="primary", use_container_width=True):
        with st.spinner("Consolidando datos..."):
            consolidador.consolidar()
            st.session_state.consolidador = consolidador
            st.success("✅ Consolidación completada")
            st.rerun()
    
    # Mostrar dashboard si ya está consolidado
    if 'consolidador' in st.session_state:
        consolidador = st.session_state.consolidador
        
        st.markdown("---")
        st.markdown("## 📊 Dashboard Consolidado")
        
        # Obtener estado actual
        estado = consolidador.get_estado_actual()
        
        if not estado:
            st.error("❌ No se pudo obtener el estado actual")
            return
        
        # Renderizar secciones del dashboard
        render_metricas_principales(estado)
        
        st.markdown("---")
        
        render_metricas_cobertura(estado)
        
        st.markdown("---")
        
        render_excedente_invertible(estado)
        
        st.markdown("---")
        
        render_timeline_consolidado(consolidador)


if __name__ == "__main__":
    main()
