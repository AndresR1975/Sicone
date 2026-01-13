"""
SICONE - Módulo de Análisis Multiproyecto FCL
Consolidación y análisis de flujo de caja para múltiples proyectos

Versión: 2.1.6 FINAL
Fecha: 29 Diciembre 2024
Autor: AI-MindNovation

VERSIÓN 2.1.6 (29-Dic-2024) - FIX VALORES DE PROYECTOS:
- 🔧 FIX CRÍTICO: Ahora extrae valores CORRECTOS de cada proyecto
  - Antes: p.get('saldo_actual', 0) → Siempre retornaba 0
  - Ahora: p.get('saldo_real_tesoreria', 0) → Valores reales ✅
  - Campos ya existen en consolidador.proyectos, solo copiarlos
  - Tabla de proyectos ahora muestra valores correctos
  - Gráfico de barras ahora muestra coberturas correctas
  - PDFs desde JSON ahora 100% idénticos a PDFs desde Multiproyecto ✅

VERSIÓN 2.1.5 (29-Dic-2024) - NOMBRES CORRECTOS PARA REPORTES:
- 🔧 FIX: Campos en JSON con nombres correctos
  - estado_caja.burn_rate (no burn_rate_total)
  - Conteos correctos de proyectos activos

MEJORA IMPORTANTE v1.5.0 (28-Dic-2024):
- 🎯 CAMBIO: % de avance ahora es PONDERADO POR MONTO (no solo hitos cumplidos)
- ✅ Más preciso gerencialmente: refleja trabajo real ejecutado
- ✅ Fórmula: sum(avance_hito_i × peso_hito_i) donde peso = monto_hito / total_montos
- ✅ Hitos parciales sí aportan al avance total
- ✅ Ejemplo: Hito al 88% cuenta como 88%, no como 0%
- ✅ Cap de avance individual al 100% (sobrepagos no inflan el total)

FIX v1.4.2 (28-Dic-2024):
- 🐛 FIX: Prevenir conteo duplicado de hitos compartidos (ambos contratos)

FIX v1.4.1 (28-Dic-2024):
- 🐛 FIX: Nombre de clave correcto es 'contratos_cartera' no 'contratos'

NUEVO v1.4.0 (28-Dic-2024):
- ✅ Extracción de hitos desde configuración del proyecto
- ✅ Cálculo de % avance basado en hitos
- ✅ Nuevos campos: avance_hitos_pct, suma_montos_hitos, hitos_totales

HISTÓRICO:
v1.3.2 (27-Dic-2024): Fix línea azul histórica vs proyección
- 🎯 FIX FINAL: Línea azul ahora solo muestra datos HISTÓRICOS (hasta hoy)
- ✅ ANTES: Línea azul se dibujaba para TODAS las semanas (histórico + futuro)
- ✅ AHORA: Línea azul SOLO hasta semana actual, línea naranja desde ahí
- ✅ RESULTADO: Ya NO hay dos líneas en las semanas futuras
- ✅ LÓGICA: Azul = histórico, Naranja = proyección (sin superposición)

HISTÓRICO:
v1.3.1 (27-Dic-2024): Fix error Timestamp
v1.3.0 (27-Dic-2024): Cambio fundamental gastos fijos
v1.2.2 (26-Dic-2024): Fix inicio proyección
v1.2.1 (26-Dic-2024): Loop corregido
v1.2.0 (26-Dic-2024): Fix consistencia
v1.1.0 (26-Dic-2024): Rediseño conceptual (error)
v1.0.4 (26-Dic-2024): Proyección iterativa
v1.0.3 (26-Dic-2024): 3 correcciones gastos fijos
v1.0.2 (26-Dic-2024): Gastos fijos semana por semana
v1.0.1 (26-Dic-2024): Gastos fijos históricos
v1.0.0 (10-Dic-2024): Versión inicial

FUNCIONALIDADES:
1. Carga de múltiples proyectos desde JSON completo
2. Consolidación temporal en eje único
3. Dashboard con métricas consolidadas
4. Análisis de estado de caja empresarial
5. Proyección configurable (default: 8 semanas)
6. Gastos fijos empresariales (mensuales → semanales)
7. Cálculo correcto de gastos fijos históricos
8. Líneas históricas vs proyección claramente separadas
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
# DIAGNÓSTICO TEMPORAL - BORRAR DESPUÉS
# ============================================================================
import streamlit as st

st.write("### 🔍 Diagnóstico de Reportes")

# Test 1: Verificar si el archivo existe
import os
existe = os.path.exists('reportes_ejecutivos.py')
st.write(f"1. Archivo reportes_ejecutivos.py existe: {'✅' if existe else '❌'}")

# Test 2: Intentar importar
try:
    from reportes_ejecutivos import (
        generar_reporte_gerencial_pdf,
        generar_reporte_inversiones_pdf
    )
    st.write("2. Import de funciones: ✅ EXITOSO")
    st.write(f"   - generar_reporte_gerencial_pdf: ✅")
    st.write(f"   - generar_reporte_inversiones_pdf: ✅")
except Exception as e:
    st.write(f"2. Import de funciones: ❌ ERROR")
    st.error(f"Error: {e}")

st.write("---")
# ============================================================================

# Importar módulo de inversiones temporales
try:
    from inversiones_temporales import (
        Inversion, calcular_excedente_invertible, analizar_riesgo_liquidez,
        generar_recomendaciones, get_info_instrumento, calcular_resumen_portafolio,
        validar_rentabilidad_inversion, crear_timeline_vencimientos, obtener_tasas_en_vivo,
        PLAZOS_MINIMOS_RECOMENDADOS, TASAS_REFERENCIA, COMISIONES, RETENCION_FUENTE, GMF
    )
    INVERSIONES_DISPONIBLES = True
except ImportError:
    INVERSIONES_DISPONIBLES = False
    st.warning("⚠️ Módulo de inversiones no disponible")

# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

SEMANAS_FUTURO_DEFAULT = 8
SEMANAS_MARGEN_DEFAULT = 8  # Semanas de margen de protección (configurable)
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
    
    def __init__(self, semanas_futuro: int = SEMANAS_FUTURO_DEFAULT, gastos_fijos_mensuales: float = 50_000_000, semanas_margen: int = SEMANAS_MARGEN_DEFAULT):
        self.proyectos = []
        self.semanas_futuro = semanas_futuro
        self.semanas_margen = semanas_margen  # Semanas para margen de protección
        self.gastos_fijos_mensuales = gastos_fijos_mensuales
        self.gastos_fijos_semanales = gastos_fijos_mensuales / 4.33  # Promedio semanas/mes
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
            
            # Calcular excedente del proyecto
            if 'totales' in data and 'egresos' in data:
                presupuesto_egresos = data['totales'].get('total_egresos', 0)
                ejecutado = sum(eg.get('total', 0) for eg in data['egresos'].get('egresos_semanales', []))
                proyecto_info['presupuesto_egresos'] = presupuesto_egresos
                proyecto_info['ejecutado'] = ejecutado
                proyecto_info['excedente'] = presupuesto_egresos - ejecutado
                proyecto_info['por_ejecutar'] = presupuesto_egresos - ejecutado
            else:
                proyecto_info['presupuesto_egresos'] = 0
                proyecto_info['ejecutado'] = 0
                proyecto_info['excedente'] = 0
                proyecto_info['por_ejecutar'] = 0
            
            # Obtener saldo real de tesorería (última semana)
            proyecto_info['semana_actual_proyecto'] = 0
            if 'tesoreria' in data and 'metricas_semanales' in data['tesoreria']:
                metricas = data['tesoreria']['metricas_semanales']
                if metricas:
                    ultima_metrica = metricas[-1]
                    proyecto_info['saldo_real_tesoreria'] = ultima_metrica.get('saldo_final_real', 0)
                    proyecto_info['burn_rate_real'] = ultima_metrica.get('burn_rate_acum', 0)
                    proyecto_info['semana_actual_proyecto'] = ultima_metrica.get('semana', 0)
                else:
                    proyecto_info['saldo_real_tesoreria'] = 0
                    proyecto_info['burn_rate_real'] = 0
            else:
                proyecto_info['saldo_real_tesoreria'] = 0
                proyecto_info['burn_rate_real'] = 0
            
            # Calcular semana de fin estimada
            if proyecto_info['burn_rate_real'] > 0 and proyecto_info['por_ejecutar'] > 0:
                semanas_restantes = proyecto_info['por_ejecutar'] / proyecto_info['burn_rate_real']
                proyecto_info['semanas_restantes'] = semanas_restantes
                proyecto_info['semana_fin_estimada'] = proyecto_info['semana_actual_proyecto'] + semanas_restantes
            else:
                # Usar duración proyectada si no hay burn rate
                if 'totales' in data and 'semanas_total' in data['totales']:
                    proyecto_info['semanas_restantes'] = data['totales']['semanas_total'] - proyecto_info['semana_actual_proyecto']
                    proyecto_info['semana_fin_estimada'] = data['totales']['semanas_total']
                else:
                    proyecto_info['semanas_restantes'] = 0
                    proyecto_info['semana_fin_estimada'] = proyecto_info['semana_actual_proyecto']
            
            # Capital disponible del proyecto
            proyecto_info['capital_disponible'] = proyecto_info['excedente'] + proyecto_info['saldo_real_tesoreria']
            
            # ================================================================
            # NUEVO v1.2.1: Calcular % de avance desde hitos (ponderado por monto)
            # ================================================================
            if 'configuracion' in data and 'hitos' in data['configuracion']:
                hitos_config = data['configuracion']['hitos']
                total_hitos = len(hitos_config)
                
                # Calcular % de avance ponderado por monto (no solo hitos cumplidos)
                avance_ponderado = 0.0
                suma_montos_esperados = 0.0
                hitos_procesados = set()  # Para evitar contar hitos compartidos dos veces
                
                if 'cartera' in data and data['cartera'] and 'contratos_cartera' in data['cartera']:
                    # Primera pasada: calcular suma total de montos esperados (sin duplicados)
                    for contrato in data['cartera']['contratos_cartera']:
                        if 'hitos' in contrato:
                            for hito_cartera in contrato['hitos']:
                                numero_hito = hito_cartera.get('numero')
                                
                                if numero_hito not in hitos_procesados:
                                    monto_esperado = hito_cartera.get('monto_esperado', 0)
                                    suma_montos_esperados += monto_esperado
                                    hitos_procesados.add(numero_hito)
                    
                    # Segunda pasada: calcular avance ponderado
                    hitos_procesados.clear()  # Resetear para segunda pasada
                    
                    for contrato in data['cartera']['contratos_cartera']:
                        if 'hitos' in contrato:
                            for hito_cartera in contrato['hitos']:
                                numero_hito = hito_cartera.get('numero')
                                
                                # Solo procesar si no se ha contado antes (evita duplicados)
                                if numero_hito not in hitos_procesados:
                                    monto_esperado = hito_cartera.get('monto_esperado', 0)
                                    pagos = hito_cartera.get('pagos', [])
                                    monto_pagado = sum([p.get('monto', 0) for p in pagos])
                                    
                                    if monto_esperado > 0:
                                        # % de avance de este hito (cap al 100%)
                                        avance_hito = min(100.0, (monto_pagado / monto_esperado) * 100)
                                        
                                        # Peso de este hito en el total
                                        peso = monto_esperado / suma_montos_esperados if suma_montos_esperados > 0 else 0
                                        
                                        # Contribución ponderada al avance total
                                        avance_ponderado += avance_hito * peso
                                    
                                    # Marcar como procesado
                                    hitos_procesados.add(numero_hito)
                
                # Guardar % de avance ponderado
                if suma_montos_esperados > 0:
                    proyecto_info['avance_hitos_pct'] = avance_ponderado
                    proyecto_info['suma_montos_hitos'] = suma_montos_esperados
                    proyecto_info['hitos_totales'] = total_hitos
                else:
                    proyecto_info['avance_hitos_pct'] = 0
                    proyecto_info['suma_montos_hitos'] = 0
                    proyecto_info['hitos_totales'] = total_hitos
            else:
                # No hay hitos configurados
                proyecto_info['avance_hitos_pct'] = 0
                proyecto_info['suma_montos_hitos'] = 0
                proyecto_info['hitos_totales'] = 0
            
            # Determinar estado del proyecto
            if proyecto_info['fecha_inicio'] > self.fecha_actual:
                proyecto_info['estado'] = 'EN_COTIZACIÓN'
            else:
                # Verificar si tiene datos reales
                tiene_egresos = data.get('egresos') and data['egresos'].get('egresos_semanales')
                tiene_cartera = data.get('cartera') and data['cartera']
                tiene_tesoreria = data.get('tesoreria') and data['tesoreria'].get('metricas_semanales')
                
                if tiene_egresos or tiene_cartera or tiene_tesoreria:
                    # Verificar si ya terminó
                    if proyecto_info['por_ejecutar'] <= 0:
                        proyecto_info['estado'] = 'TERMINADO'
                    else:
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
        
        # Debug: Mostrar resumen de datos consolidados (comentado para producción)
        # st.caption(f"📊 **Debug Consolidación Final:**")
        # st.caption(f"   • Semanas totales: {len(df_consolidado)}")
        # st.caption(f"   • Semana actual: {self.semana_actual_consolidada}")
        
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
        
        # DEBUG (comentado para producción)
        # st.caption(f"   🔍 Mapeando {nombre}: {len(proyeccion)} semanas de proyección")
        
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
        
        # DEBUG (comentado para producción)
        # st.caption(f"      ✓ {semanas_mapeadas} semanas mapeadas correctamente")
        # if semanas_mapeadas > 0 and semana_inicio_rel <= len(df):
        #     idx_primera = semana_inicio_rel - 1
        #     if idx_primera >= 0 and idx_primera < len(df):
        #         st.caption(f"      Ejemplo semana 1: Saldo=${df.at[idx_primera, col_saldo_proy]:,.0f}")
        
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
                            df.at[idx_row, col_saldo_real] = met_sem.get('saldo_final_real', 0)  # ← Corregido
        
        return df
    
    def _calcular_metricas_consolidadas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula métricas consolidadas para cada semana"""
        
        # Identificar columnas por tipo
        cols_saldo_proy = [c for c in df.columns if c.startswith('saldo_proy_')]
        cols_saldo_real = [c for c in df.columns if c.startswith('saldo_real_')]
        cols_ingresos_proy = [c for c in df.columns if c.startswith('ingresos_proy_')]
        cols_egresos_proy = [c for c in df.columns if c.startswith('egresos_proy_')]
        cols_egresos_real = [c for c in df.columns if c.startswith('egresos_real_')]
        
        # DEBUG: Mostrar columnas encontradas (comentado para producción)
        # st.caption(f"🔍 **Debug Columnas:**")
        # st.caption(f"   • Saldo proy: {len(cols_saldo_proy)} columnas")
        # st.caption(f"   • Egresos proy: {len(cols_egresos_proy)} columnas")
        # st.caption(f"   • Egresos real: {len(cols_egresos_real)} columnas")
        
        # Sumar por tipo
        df['saldo_proy_total'] = df[cols_saldo_proy].sum(axis=1)
        df['saldo_real_total'] = df[cols_saldo_real].sum(axis=1)
        df['ingresos_proy_total'] = df[cols_ingresos_proy].sum(axis=1)
        df['egresos_proy_total'] = df[cols_egresos_proy].sum(axis=1)
        df['egresos_real_total'] = df[cols_egresos_real].sum(axis=1)
        
        # DEBUG: Mostrar valores de primera fila de cada proyecto (comentado para producción)
        # st.caption(f"🔍 **Debug Primera Semana (valores individuales):**")
        # for col in cols_saldo_proy:
        #     valor = df[col].iloc[0]
        #     st.caption(f"   • {col}: ${valor:,.0f}")
        # st.caption(f"   • SUMA saldo_proy_total: ${df['saldo_proy_total'].iloc[0]:,.0f}")
        
        # Saldo consolidado: Usar datos reales cuando existan
        # Cuando terminen, proyectar desde último saldo real conocido
        df['saldo_consolidado'] = 0.0
        
        # Por cada proyecto, calcular su contribución al saldo consolidado
        for proyecto in self.proyectos:
            nombre = proyecto['nombre']
            col_saldo_real = f'saldo_real_{nombre}'
            col_saldo_proy = f'saldo_proy_{nombre}'
            col_ingresos_proy = f'ingresos_proy_{nombre}'
            col_egresos_proy = f'egresos_proy_{nombre}'
            
            if col_saldo_real not in df.columns or col_saldo_proy not in df.columns:
                continue
            
            # Encontrar última semana con datos reales
            saldos_reales = df[col_saldo_real]
            ultima_semana_real = None
            ultimo_saldo_real = 0
            
            for idx in range(len(df)):
                if saldos_reales.iloc[idx] > 0:
                    ultima_semana_real = idx
                    ultimo_saldo_real = saldos_reales.iloc[idx]
            
            # Construir saldo por semana para este proyecto
            saldo_proyecto = []
            for idx in range(len(df)):
                if ultima_semana_real is not None and idx <= ultima_semana_real:
                    # Usar saldo real si existe
                    if saldos_reales.iloc[idx] > 0:
                        saldo_proyecto.append(saldos_reales.iloc[idx])
                    else:
                        # Usar proyección mientras no haya datos reales
                        saldo_proyecto.append(df[col_saldo_proy].iloc[idx])
                else:
                    # Después de última semana real, proyectar desde último saldo conocido
                    if ultima_semana_real is not None and idx > ultima_semana_real:
                        # Calcular flujos desde última semana real
                        flujo_acum = 0
                        for j in range(ultima_semana_real + 1, idx + 1):
                            ingresos = df[col_ingresos_proy].iloc[j] if j < len(df) else 0
                            egresos = df[col_egresos_proy].iloc[j] if j < len(df) else 0
                            flujo_acum += (ingresos - egresos)
                        saldo_proyecto.append(ultimo_saldo_real + flujo_acum)
                    else:
                        # No hay datos reales, usar proyección
                        saldo_proyecto.append(df[col_saldo_proy].iloc[idx])
            
            # Sumar al consolidado
            df['saldo_consolidado'] += pd.Series(saldo_proyecto, index=df.index)
        
        # Asegurar que saldos no sean negativos
        df['saldo_consolidado'] = df['saldo_consolidado'].clip(lower=0)
        
        # CRÍTICO: Agregar columna de gastos fijos empresariales
        df['gastos_fijos_semanales'] = self.gastos_fijos_semanales
        
        # Aplicar gastos fijos a semanas HISTÓRICAS para consistencia con dashboard
        # CRÍTICO: Calcular basándose en semanas desde inicio de empresa, NO semana_consolidada
        if self.gastos_fijos_semanales > 0:
            # Crear columna de gastos fijos acumulados
            df['gastos_fijos_acumulados'] = 0.0
            
            # Iterar sobre los índices REALES del DataFrame
            for idx in df.index:
                # Calcular número de semanas desde inicio de empresa hasta esta fecha
                fecha_semana = pd.Timestamp(df.at[idx, 'fecha'])
                fecha_inicio = pd.Timestamp(self.fecha_inicio_empresa)
                semanas_desde_inicio = max(0, ((fecha_semana - fecha_inicio).days // 7))
                
                # Gastos fijos acumulados = semanas × costo_semanal
                df.at[idx, 'gastos_fijos_acumulados'] = self.gastos_fijos_semanales * semanas_desde_inicio
                
                # Descontar de semanas HISTÓRICAS solamente
                if df.at[idx, 'es_historica']:
                    saldo_actual = df.at[idx, 'saldo_consolidado']
                    df.at[idx, 'saldo_consolidado'] = max(0, saldo_actual - df.at[idx, 'gastos_fijos_acumulados'])
        else:
            df['gastos_fijos_acumulados'] = 0.0
        
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
        
        # NO propagar burn rate constante - se calculará dinámicamente considerando finalizaciones
        # df.loc[df['es_futura'], 'burn_rate'] = ultimo_burn_rate
        
        # Calcular saldo ajustado con gastos fijos para proyección futura
        # Considera finalización de proyectos y presupuesto limitado
        df['saldo_consolidado_ajustado'] = df['saldo_consolidado'].copy()
        df['burn_rate_proyectado'] = df['burn_rate'].copy()  # Nueva columna para burn rate futuro
        
        # Para semanas futuras, proyectar considerando finalizaciones
        if len(df[df['es_futura']]) > 0:
            # CRÍTICO: Obtener el saldo de la ÚLTIMA semana histórica
            # (que ya tiene gastos fijos descontados)
            df_historico = df[df['es_historica']]
            if len(df_historico) > 0:
                # Usar el último saldo histórico como punto de partida
                saldo_base = df_historico['saldo_consolidado'].iloc[-1]
                
                # DEBUG: Verificar valores
                ultima_semana_hist = df_historico.iloc[-1]
                print(f"\n{'='*60}")
                print(f"DEBUG - INICIO PROYECCIÓN:")
                print(f"{'='*60}")
                print(f"Última semana histórica: {ultima_semana_hist['semana_consolidada']}")
                print(f"Fecha: {ultima_semana_hist['fecha']}")
                print(f"Saldo consolidado (con GF): ${saldo_base:,.0f}")
                print(f"Gastos fijos acumulados: ${ultima_semana_hist['gastos_fijos_acumulados']:,.0f}")
                print(f"{'='*60}\n")
            else:
                # Si no hay histórico, usar el primer valor
                saldo_base = df['saldo_consolidado'].iloc[0]
            
            # Proyectar por proyecto considerando presupuesto y fin
            saldos_proyectados_por_semana = []
            burn_rates_por_semana = []
            
            # Iniciar con el último saldo histórico (ya incluye gastos fijos descontados)
            saldo_actual_proyeccion = saldo_base
            
            for idx in df[df['es_futura']].index:
                semana_consolidada = df.at[idx, 'semana_consolidada']
                
                # Calcular egresos de proyectos activos en esta semana
                egresos_proyectos = 0
                presupuesto_restante_total = 0
                proyectos_activos_count = 0
                
                for proyecto in self.proyectos:
                    # Calcular semana del proyecto
                    fecha_inicio = proyecto['fecha_inicio']
                    # Convertir a int() para evitar error con numpy.int64
                    semana_cons_int = int(semana_consolidada)
                    fecha_semana = self.fecha_inicio_empresa + timedelta(days=(semana_cons_int-1)*7)
                    semana_proyecto = ((fecha_semana - fecha_inicio).days // 7) + 1
                    
                    # Calcular presupuesto restante
                    semana_actual_proy = proyecto.get('semana_actual_proyecto', 0)
                    por_ejecutar = proyecto.get('por_ejecutar', 0)
                    
                    # Solo considerar si está dentro de su duración estimada
                    semana_fin_est = proyecto.get('semana_fin_estimada', 0)
                    
                    if semana_proyecto > 0 and semana_proyecto <= semana_fin_est and por_ejecutar > 0:
                        # Proyecto activo en esta semana
                        burn_rate_proy = proyecto.get('burn_rate_real', 0)
                        
                        # Calcular cuánto presupuesto queda
                        semanas_desde_hoy = semana_proyecto - semana_actual_proy
                        presupuesto_consumido = burn_rate_proy * semanas_desde_hoy
                        presupuesto_restante = max(0, por_ejecutar - presupuesto_consumido)
                        
                        if presupuesto_restante > 0:
                            # Limitar egresos al presupuesto restante
                            egreso_semana = min(burn_rate_proy, presupuesto_restante)
                            egresos_proyectos += egreso_semana
                            presupuesto_restante_total += presupuesto_restante
                            proyectos_activos_count += 1
                
                burn_rates_por_semana.append(egresos_proyectos)
                
                # Obtener ingresos de ESTA semana específica
                ingresos_esta_semana = df.at[idx, 'ingresos_proy_total']
                
                # Calcular saldo proyectado de forma ITERATIVA
                # Saldo esta semana = Saldo anterior + Ingresos - Egresos - Gastos fijos
                saldo_actual_proyeccion = (
                    saldo_actual_proyeccion + 
                    ingresos_esta_semana - 
                    egresos_proyectos - 
                    self.gastos_fijos_semanales
                )
                
                # No permitir saldos negativos
                saldo_actual_proyeccion = max(0, saldo_actual_proyeccion)
                
                saldos_proyectados_por_semana.append(saldo_actual_proyeccion)
                df.at[idx, 'burn_rate_proyectado'] = egresos_proyectos + self.gastos_fijos_semanales
            
            # Asignar saldos proyectados
            for i, idx in enumerate(df[df['es_futura']].index):
                df.at[idx, 'saldo_consolidado_ajustado'] = saldos_proyectados_por_semana[i]
                df.at[idx, 'burn_rate'] = burn_rates_por_semana[i]  # Burn rate de proyectos solamente
        
        # ============================================================
        # FIX v2.0.2 FINAL: Margen de Protección
        # ============================================================
        # HISTÓRICO: Variable (refleja burn rate real de cada semana)
        # FUTURO: Constante desde HOY (proyección lineal)
        
        # Paso 1: Obtener burn rate ACTUAL
        df_actual = df[df['semana_consolidada'] == self.semana_actual_consolidada]
        if len(df_actual) > 0:
            burn_rate_actual = df_actual['burn_rate'].iloc[0]
        else:
            # Fallback: último burn rate histórico
            df_hist = df[df['es_historica']]
            burn_rate_actual = df_hist['burn_rate'].iloc[-1] if len(df_hist) > 0 else 0
        
        # Paso 2: Calcular margen HISTÓRICO (variable)
        df.loc[df['es_historica'], 'margen_proteccion'] = (
            df.loc[df['es_historica'], 'burn_rate'] + self.gastos_fijos_semanales
        ) * self.semanas_margen
        
        # Paso 3: Calcular margen FUTURO (constante)
        margen_proteccion_futuro = (burn_rate_actual + self.gastos_fijos_semanales) * self.semanas_margen
        df.loc[df['es_futura'], 'margen_proteccion'] = margen_proteccion_futuro
        
        print(f"\n{'='*60}")
        print(f"MARGEN DE PROTECCIÓN v2.1.0")
        print(f"{'='*60}")
        print(f"Semanas de Margen: {self.semanas_margen}")
        print(f"Burn Rate Actual: ${burn_rate_actual:,.0f}/semana")
        print(f"Gastos Fijos: ${self.gastos_fijos_semanales:,.0f}/semana")
        print(f"Margen Futuro (constante): ${margen_proteccion_futuro:,.0f}")
        print(f"  = (${burn_rate_actual:,.0f} + ${self.gastos_fijos_semanales:,.0f}) × {self.semanas_margen} semanas")
        print(f"Histórico: Variable | Futuro: Constante desde HOY")
        print(f"{'='*60}\n")
        
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
        
        # Capital total consolidado
        # saldo_consolidado YA tiene gastos fijos descontados en semanas históricas
        if self.df_consolidado is not None and len(semana_actual_row) > 0:
            total_saldos_reales = float(row['saldo_consolidado'])
        else:
            # Fallback: usar suma de JSON si no hay consolidado
            total_saldos_reales = sum(p.get('saldo_real_tesoreria', 0) for p in self.proyectos)
        
        # Para información adicional (no se suma al capital)
        total_excedentes = sum(p.get('excedente', 0) for p in self.proyectos)
        
        # Burn rate consolidado actual (proyectos + gastos fijos)
        burn_rate_proyectos = float(row['burn_rate'])
        burn_rate_total = burn_rate_proyectos + self.gastos_fijos_semanales
        
        # ============================================================
        # FIX v2.1.0: Margen de protección CORRECTO
        # ============================================================
        # Fórmula: Burn Rate Total × Semanas de Margen
        # Ejemplo: $86M/sem × 8 sem = $687M
        margen_proteccion = burn_rate_total * self.semanas_margen
        
        # Excedente invertible
        excedente_invertible = total_saldos_reales - margen_proteccion
        
        # Estado general basado en capital real
        estado_general = determinar_estado_liquidez(total_saldos_reales, margen_proteccion)
        
        return {
            'semana': int(row['semana_consolidada']),
            'fecha': row['fecha'],
            'saldo_total': float(total_saldos_reales),  # ← Solo saldos reales
            'total_saldos_reales': float(total_saldos_reales),
            'total_excedentes_info': float(total_excedentes),  # Solo info, no se suma
            'burn_rate': float(burn_rate_total),  # ← Incluye gastos fijos
            'burn_rate_proyectos': float(burn_rate_proyectos),
            'gastos_fijos_semanales': float(self.gastos_fijos_semanales),
            'semanas_margen': int(self.semanas_margen),  # Semanas configuradas para margen
            'margen_proteccion': float(margen_proteccion),
            'excedente_invertible': float(excedente_invertible),
            'estado_general': estado_general,
            'proyecto_critico': row['proyecto_critico'],
            'proyectos_activos': estados.get('ACTIVO', 0),
            'proyectos_terminados': estados.get('TERMINADO', 0),
            'proyectos_cotizacion': estados.get('EN_COTIZACIÓN', 0),
            'total_proyectos': len(self.proyectos)
        }


# ============================================================================
# FUNCIONES DE VISUALIZACIÓN
# ============================================================================

def render_exportar_json_simple(consolidador: ConsolidadorMultiproyecto, estado: Dict):
    """Renderiza botón para exportar JSON consolidado CON TODOS LOS DATOS para reportes"""
    st.markdown("### 📦 Exportar Datos Consolidados")
    st.caption("Guarda el estado actual del análisis en formato JSON para cargar en reportes")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("📥 Exportar JSON Consolidado", type="primary", use_container_width=True):
            import json
            from pathlib import Path
            
            # =================================================================
            # PREPARAR DATOS COMPLETOS PARA REPORTES
            # =================================================================
            
            # 1. DATOS DEL DATAFRAME (para Waterfall)
            df_data = None
            if consolidador.df_consolidado is not None and not consolidador.df_consolidado.empty:
                df = consolidador.df_consolidado
                semana_actual = estado['semana']
                
                # Filtrar últimas 6 semanas históricas + futuras
                df_export = df[
                    (df['semana_consolidada'] >= semana_actual - 5) &
                    (df['semana_consolidada'] <= semana_actual + 8)
                ].copy()
                
                # Convertir a formato JSON-serializable
                df_data = {
                    "semanas": df_export['semana_consolidada'].tolist(),
                    "fechas": df_export['fecha'].astype(str).tolist() if 'fecha' in df_export.columns else [],
                    "saldo_consolidado": df_export['saldo_consolidado'].tolist() if 'saldo_consolidado' in df_export.columns else [],
                    "ingresos_proy_total": df_export['ingresos_proy_total'].tolist() if 'ingresos_proy_total' in df_export.columns else [],
                    "egresos_proy_total": df_export['egresos_proy_total'].tolist() if 'egresos_proy_total' in df_export.columns else [],
                    "es_historica": df_export['es_historica'].tolist() if 'es_historica' in df_export.columns else [],
                    "burn_rate": df_export['burn_rate'].tolist() if 'burn_rate' in df_export.columns else []
                }
            
            # 2. PROYECTOS COMPLETOS (para Pie Chart y Tabla)
            proyectos_completos = []
            for p in consolidador.proyectos:
                proyecto_data = {
                    "nombre": p['nombre'],
                    "estado": p['estado'],
                    # Campos con nombres correctos que YA EXISTEN en consolidador.proyectos
                    "saldo_real_tesoreria": float(p.get('saldo_real_tesoreria', 0)),  # ✅
                    "burn_rate_real": float(p.get('burn_rate_real', 0)),  # ✅
                    "avance_hitos_pct": float(p.get('avance_hitos_pct', 0)),  # ✅
                    "monto_contrato": float(p.get('presupuesto_egresos', 0)),  # ✅ Campo correcto
                    "ejecutado": float(p.get('ejecutado', 0)),  # ✅
                    # DATOS COMPLETOS para gráficos
                    "data": p.get('data', {})  # Incluye proyeccion_semanal completa
                }
                proyectos_completos.append(proyecto_data)
            
            # 3. PREPARAR JSON COMPLETO
            # Contar proyectos activos correctamente
            proyectos_activos = sum(1 for p in consolidador.proyectos if p['estado'] == 'ACTIVO')
            proyectos_terminados = sum(1 for p in consolidador.proyectos if p['estado'] == 'TERMINADO')
            
            json_data = {
                "metadata": {
                    "version": "2.1.5",
                    "fecha_generacion": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "semana_actual": int(estado['semana']),
                    "total_proyectos": len(consolidador.proyectos),  # ✅ Total real
                    "gastos_fijos_mensuales": float(consolidador.gastos_fijos_mensuales),
                    "semanas_margen": int(estado['semanas_margen']),
                    "semanas_futuro": int(consolidador.semanas_futuro)
                },
                "estado_caja": {
                    "saldo_total": float(estado['saldo_total']),
                    "burn_rate": float(estado['burn_rate']),  # ✅ Nombre correcto (sin _total)
                    "burn_rate_proyectos": float(estado['burn_rate_proyectos']),
                    "gastos_fijos_semanales": float(estado['gastos_fijos_semanales']),
                    "margen_proteccion": float(estado['margen_proteccion']),
                    "excedente_invertible": float(estado['excedente_invertible']),
                    "estado_general": estado['estado_general'],
                    "proyectos_activos": int(proyectos_activos),  # ✅ Conteo correcto
                    "proyectos_terminados": int(proyectos_terminados),
                    "total_proyectos": len(consolidador.proyectos)  # ✅ Total correcto
                },
                "df_consolidado": df_data,  # Datos del DataFrame
                "proyectos": proyectos_completos  # Proyectos completos
            }
            
            # Crear directorio si no existe
            Path('reportes').mkdir(exist_ok=True)
            
            # Generar nombre de archivo con timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ruta_json = f'reportes/consolidado_multiproyecto_{timestamp}.json'
            ruta_latest = 'reportes/consolidado_multiproyecto_latest.json'
            
            # Guardar archivo versionado
            with open(ruta_json, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            # Guardar archivo "latest" (siempre sobrescribe)
            with open(ruta_latest, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            # Guardar en session_state
            st.session_state.json_consolidado = json_data
            
            st.success(f"✅ JSON exportado exitosamente")
            st.caption(f"📁 Guardado en: {ruta_json}")
            st.caption(f"📊 Incluye: DataFrame completo + Proyectos con categorías de gasto")
            
            # Botón de descarga
            json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="💾 Descargar JSON",
                data=json_str,
                file_name=f'consolidado_{timestamp}.json',
                mime='application/json'
            )
    
    with col2:
        if 'json_consolidado' in st.session_state:
            st.metric(
                "Último Export",
                st.session_state.json_consolidado['metadata']['fecha_generacion'][-8:],
                help="Hora del último export"
            )


def render_metricas_principales(estado: Dict):
    """Renderiza las métricas principales del dashboard"""
    
    st.markdown("### 💰 Estado de Caja Empresarial")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Saldo Total",
            formatear_moneda(estado['saldo_total']),
            help="Suma de saldos reales de tesorería de todos los proyectos"
        )
        # Mostrar solo saldos reales (no excedentes por separado para evitar confusión)
        st.caption(f"   🏦 Efectivo disponible en proyectos")
    
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
        # Mostrar proyectos terminados si existen
        if estado.get('proyectos_terminados', 0) > 0:
            st.caption(f"   ✅ {estado['proyectos_terminados']} terminado(s)")
    
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
            help="Gastos semanales: Proyectos + Gastos Fijos"
        )
        # Desglose
        st.caption(f"   Proyectos: ${estado['burn_rate_proyectos']:,.0f}")
        st.caption(f"   Gastos Fijos: ${estado['gastos_fijos_semanales']:,.0f}")
    
    with col2:
        st.metric(
            f"Margen Requerido ({estado.get('semanas_margen', 8)} sem)",
            formatear_moneda(estado['margen_proteccion']),
            help=f"Burn Rate Total × {estado.get('semanas_margen', 8)} semanas"
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
    
    # Explicación de las líneas
    st.caption("""
    **Línea Azul (Saldo Consolidado):** Flujo de caja consolidado incluyendo gastos fijos empresariales (${:,.0f}/semana).  
    **Línea Naranja (Proyección):** Continuación proyectada considerando egresos de proyectos activos y gastos fijos.  
    **Línea Roja (Margen de Protección):** Reserva de 8 semanas de burn rate total para contingencias.
    """.format(consolidador.gastos_fijos_semanales))
    
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
    
    # Filtrar solo datos históricos para la línea azul
    df_historico = df[df['es_historica']]
    fechas_historicas = [fechas_py[i] for i in df_historico.index]
    
    # Línea de saldo consolidado (SOLO HISTÓRICO)
    fig.add_trace(go.Scatter(
        x=fechas_historicas,
        y=df_historico['saldo_consolidado'],
        mode='lines',
        name='Saldo Consolidado',
        line=dict(color='#1f77b4', width=3),
        hovertemplate='<b>Semana %{customdata[0]}</b><br>' +
                      'Fecha: %{x|%Y-%m-%d}<br>' +
                      'Saldo: $%{y:,.0f}<br>' +
                      '<i>(Incluye gastos fijos empresariales)</i><br>' +
                      '<extra></extra>',
        customdata=df_historico[['semana_consolidada']].values
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
    
    # Línea de proyección con gastos fijos (solo semanas futuras)
    df_futuro = df[df['es_futura']].copy()
    if len(df_futuro) > 0:
        # Agregar el último punto histórico para conectar la línea
        idx_ultima_historica = df[df['es_historica']].index[-1]
        df_transicion = pd.concat([
            df.iloc[[idx_ultima_historica]],
            df_futuro
        ])
        
        fechas_futuro = [fechas_py[i] for i in df_transicion.index]
        
        fig.add_trace(go.Scatter(
            x=fechas_futuro,
            y=df_transicion['saldo_consolidado_ajustado'],
            mode='lines',
            name='Proyección',
            line=dict(color='#ff7f0e', width=2, dash='dot'),
            hovertemplate='<b>Proyección</b><br>' +
                          'Fecha: %{x|%Y-%m-%d}<br>' +
                          'Saldo: $%{y:,.0f}<br>' +
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


def render_inversiones_temporales(estado: Dict):
    """Renderiza sección de inversiones temporales"""
    
    if not INVERSIONES_DISPONIBLES:
        st.warning("⚠️ Módulo de inversiones temporales no disponible")
        return
    
    st.markdown("### 💰 Inversiones Temporales")
    st.caption("Optimiza excedentes de liquidez con instrumentos financieros")
    
    # Configuración del margen de seguridad
    col_config1, col_config2 = st.columns([1, 1])
    
    with col_config1:
        # Obtener tasas (desde session_state o API)
        if 'tasas_actualizadas' not in st.session_state:
            st.session_state.tasas_actualizadas = {
                'DTF': TASAS_REFERENCIA['DTF'],
                'IBR': TASAS_REFERENCIA['IBR'],
                'fuente': 'Manual'
            }
        
        st.metric(
            "Tasa DTF Ref.",
            f"{st.session_state.tasas_actualizadas['DTF']:.2f}% EA",
            help=f"Fuente: {st.session_state.tasas_actualizadas.get('fuente', 'Manual')}"
        )
    
    with col_config2:
        if st.button("🔄 Actualizar Tasas", help="Obtener tasas actuales del Banco de la República"):
            with st.spinner("Consultando Banco de la República..."):
                tasas_nuevas = obtener_tasas_en_vivo()
                if tasas_nuevas.get('error'):
                    st.warning(f"⚠️ {tasas_nuevas['error']}\nUsando tasas por defecto.")
                else:
                    st.session_state.tasas_actualizadas = tasas_nuevas
                    st.success(f"✅ Tasas actualizadas\nIBR: {tasas_nuevas['IBR']:.2f}% EA")
                    st.rerun()
    
    # ============================================================
    # FIX v2.1.1: Excedente invertible con margen FIJO
    # ============================================================
    # Margen = Burn Rate Total × semanas_margen (sin % adicional)
    # Excedente = Saldo Total - Margen de Protección
    # Usuario decide cuánto del excedente invertir
    
    saldo_total = estado['saldo_total']
    margen_proteccion = estado['margen_proteccion']  # Fórmula: burn_rate_total × semanas_margen
    
    # Excedente disponible para inversión
    excedente_invertible = saldo_total - margen_proteccion
    porcentaje_excedente = (excedente_invertible / saldo_total * 100) if saldo_total > 0 else 0
    
    excedente_info = {
        'saldo_total': saldo_total,
        'margen_total': margen_proteccion,  # = $687M (con 8 semanas)
        'excedente_invertible': excedente_invertible,
        'porcentaje_excedente': porcentaje_excedente
    }
    
    # Mostrar capital disponible
    st.markdown("#### 💼 Capital Disponible para Inversión")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Saldo Total",
            formatear_moneda(excedente_info['saldo_total'])
        )
    
    with col2:
        st.metric(
            "Margen Total",
            formatear_moneda(excedente_info['margen_total']),
            help=f"Margen de protección fijo: Burn Rate Total × {estado.get('semanas_margen', 8)} semanas (NO incluye % adicional)"
        )
    
    with col3:
        st.metric(
            "💎 Excedente Invertible",
            formatear_moneda(excedente_info['excedente_invertible']),
            delta=f"{excedente_info['porcentaje_excedente']:.1f}% del saldo",
            help="Capital disponible para inversión sin comprometer operación"
        )
    
    if excedente_info['excedente_invertible'] <= 0:
        st.warning("⚠️ No hay excedente disponible para inversión. Enfocarse en liquidez operativa.")
        return
    
    st.markdown("---")
    
    # Recomendaciones automáticas
    st.markdown("#### 💡 Estrategias Recomendadas")
    st.caption("Aplica una estrategia predefinida con 1 click o configura manualmente")
    
    recomendaciones = generar_recomendaciones(
        excedente_info['excedente_invertible'],
        excedente_info['margen_total']
    )
    
    if recomendaciones and recomendaciones[0].get('nombre') != 'Sin Recomendación':
        # Mostrar recomendaciones en columns
        num_recs = len(recomendaciones)
        cols_rec = st.columns(num_recs)
        
        for idx, (col, rec) in enumerate(zip(cols_rec, recomendaciones), 1):
            with col:
                # Card de recomendación
                emoji_rec = "✅" if rec.get('recomendada') else ("📊" if rec['nombre'] == 'Balanceada' else "⚡")
                st.markdown(f"**{emoji_rec} {rec['nombre']}**")
                st.caption(rec['descripcion'])
                
                st.metric(
                    "Total a Invertir",
                    formatear_moneda(rec['monto']),
                    delta=f"{(rec['monto']/excedente_info['excedente_invertible']*100):.0f}% del excedente"
                )
                
                st.caption(f"**Riesgo:** {rec['riesgo']}")
                
                # Distribución
                with st.expander("Ver distribución"):
                    for dist in rec['distribucion']:
                        st.caption(f"• {dist['porcentaje']}% en {dist['instrumento']} ({dist['plazo']}d): {formatear_moneda(dist['monto'])}")
                
                # Botón para aplicar
                if st.button(f"Aplicar {rec['nombre']}", key=f"aplicar_rec_{idx}", use_container_width=True):
                    # Forzar valores DIRECTAMENTE en los widget keys
                    # Esto hace que los widgets se rendericen con estos valores
                    for inv_idx, dist in enumerate(rec['distribucion'], 1):
                        # Forzar valores en las keys que los widgets usan
                        st.session_state[f'inv_{inv_idx}_activa'] = True
                        st.session_state[f'inv_{inv_idx}_instrumento'] = dist['instrumento']
                        st.session_state[f'inv_{inv_idx}_plazo'] = dist['plazo']
                        st.session_state[f'inv_{inv_idx}_monto'] = int(dist['monto'])
                        
                        # Tasa según instrumento
                        if dist['instrumento'] == 'CDT':
                            tasa_sugerida = st.session_state.tasas_actualizadas.get('DTF', 13.25)
                        elif dist['instrumento'] == 'Fondo Corto Plazo':
                            tasa_sugerida = st.session_state.tasas_actualizadas.get('IBR', 12.80) + 0.5
                        else:
                            tasa_sugerida = st.session_state.tasas_actualizadas.get('IBR', 12.80)
                        st.session_state[f'inv_{inv_idx}_tasa'] = tasa_sugerida
                    
                    st.success(f"✅ Estrategia {rec['nombre']} aplicada")
                    st.rerun()
    else:
        st.info(recomendaciones[0]['mensaje'] if recomendaciones else "No hay recomendaciones disponibles")
    
    st.markdown("---")
    
    # Configurar 3 inversiones
    st.markdown("#### ⚙️ Configurar Inversiones")
    st.caption("Configure hasta 3 alternativas de inversión con diferentes instrumentos y plazos")
    
    inversiones = []
    
    # Crear 3 tabs para las inversiones
    tab1, tab2, tab3 = st.tabs(["📊 Inversión 1", "📊 Inversión 2", "📊 Inversión 3"])
    
    for idx, tab in enumerate([tab1, tab2, tab3], 1):
        with tab:
            # ============================================
            # PATRÓN CORRECTO STREAMLIT:
            # 1. Inicializar session_state si no existe
            # 2. Widget SIN value parameter, solo key
            # 3. session_state tiene control total
            # ============================================
            
            # Inicializar checkbox si no existe
            if f'inv_{idx}_activa' not in st.session_state:
                st.session_state[f'inv_{idx}_activa'] = (idx == 1)
            
            col_inv1, col_inv2 = st.columns([2, 1])
            
            with col_inv1:
                activa = st.checkbox(
                    f"Activar Inversión {idx}",
                    key=f"inv_{idx}_activa"  # Sin value=, session_state controla
                )
            
            if not activa:
                st.info(f"Inversión {idx} desactivada")
                continue
            
            # Selección de instrumento
            col_inst1, col_inst2 = st.columns(2)
            
            with col_inst1:
                # Inicializar instrumento si no existe
                if f'inv_{idx}_instrumento' not in st.session_state:
                    if idx == 1:
                        st.session_state[f'inv_{idx}_instrumento'] = 'CDT'
                    elif idx == 2:
                        st.session_state[f'inv_{idx}_instrumento'] = 'Fondo Liquidez'
                    else:
                        st.session_state[f'inv_{idx}_instrumento'] = 'Fondo Corto Plazo'
                
                instrumentos_lista = ['CDT', 'Fondo Liquidez', 'Fondo Corto Plazo', 'Cuenta Remunerada']
                
                # Calcular índice basado en session_state
                try:
                    idx_default = instrumentos_lista.index(st.session_state[f'inv_{idx}_instrumento'])
                except (ValueError, KeyError):
                    idx_default = 0
                
                instrumento = st.selectbox(
                    "🏦 Instrumento",
                    options=instrumentos_lista,
                    index=idx_default,  # Necesario para selectbox
                    key=f"inv_{idx}_instrumento"
                )
            
            with col_inst2:
                # Plazos disponibles según instrumento
                if instrumento == 'CDT':
                    plazos_disponibles = [30, 60, 90, 180, 360]
                elif instrumento in ['Fondo Liquidez', 'Fondo Corto Plazo']:
                    plazos_disponibles = [30, 60, 90]
                else:  # Cuenta Remunerada
                    plazos_disponibles = [1, 7, 15, 30, 60, 90]
                
                # Inicializar plazo si no existe o no es válido
                if f'inv_{idx}_plazo' not in st.session_state or st.session_state[f'inv_{idx}_plazo'] not in plazos_disponibles:
                    if idx == 1:
                        st.session_state[f'inv_{idx}_plazo'] = 90
                    elif idx == 2:
                        st.session_state[f'inv_{idx}_plazo'] = 180 if 180 in plazos_disponibles else 90
                    else:
                        st.session_state[f'inv_{idx}_plazo'] = 60 if 60 in plazos_disponibles else plazos_disponibles[0]
                
                # Calcular índice basado en session_state
                try:
                    idx_plazo = plazos_disponibles.index(st.session_state[f'inv_{idx}_plazo'])
                except (ValueError, KeyError):
                    idx_plazo = 0
                
                plazo = st.selectbox(
                    "⏱️ Plazo (días)",
                    options=plazos_disponibles,
                    index=idx_plazo,  # Necesario para selectbox
                    key=f"inv_{idx}_plazo"
                )
                
                # Mostrar plazo mínimo recomendado
                plazo_minimo = PLAZOS_MINIMOS_RECOMENDADOS.get(instrumento, 30)
                if plazo < plazo_minimo and instrumento != 'Cuenta Remunerada':
                    st.caption(f"   ⚠️ Mínimo recomendado: {plazo_minimo} días")
            
            # Monto y tasa
            col_monto1, col_monto2 = st.columns(2)
            
            with col_monto1:
                # Inicializar monto si no existe
                if f'inv_{idx}_monto' not in st.session_state:
                    if idx == 1:
                        st.session_state[f'inv_{idx}_monto'] = int(excedente_info['excedente_invertible'] * 0.50)
                    elif idx == 2:
                        st.session_state[f'inv_{idx}_monto'] = int(excedente_info['excedente_invertible'] * 0.30)
                    else:
                        st.session_state[f'inv_{idx}_monto'] = int(excedente_info['excedente_invertible'] * 0.15)
                
                monto = st.number_input(
                    "💵 Monto a Invertir",
                    min_value=0,
                    max_value=int(excedente_info['excedente_invertible']),
                    step=10_000_000,
                    format="%d",
                    key=f"inv_{idx}_monto"  # Sin value=, session_state controla
                )
                
                porcentaje_usado = (monto / excedente_info['excedente_invertible'] * 100) if excedente_info['excedente_invertible'] > 0 else 0
                st.caption(f"   {porcentaje_usado:.1f}% del excedente")
            
            with col_monto2:
                # Inicializar tasa si no existe
                if f'inv_{idx}_tasa' not in st.session_state:
                    # Calcular tasa según instrumento
                    if instrumento == 'CDT':
                        st.session_state[f'inv_{idx}_tasa'] = st.session_state.tasas_actualizadas.get('DTF', 13.25)
                    elif instrumento == 'Fondo Corto Plazo':
                        st.session_state[f'inv_{idx}_tasa'] = st.session_state.tasas_actualizadas.get('IBR', 12.80) + 0.5
                    elif instrumento == 'Fondo Liquidez':
                        st.session_state[f'inv_{idx}_tasa'] = st.session_state.tasas_actualizadas.get('IBR', 12.80)
                    else:  # Cuenta Remunerada
                        st.session_state[f'inv_{idx}_tasa'] = 4.5
                
                tasa_ea = st.number_input(
                    "📈 Tasa EA (%)",
                    min_value=0.0,
                    max_value=30.0,
                    step=0.1,
                    format="%.2f",
                    key=f"inv_{idx}_tasa"  # Sin value=, session_state controla
                )
            
            # Crear objeto inversión
            if monto > 0:
                comision = COMISIONES.get(instrumento, 0)
                inv = Inversion(
                    nombre=f"Inversión {idx}",
                    monto=monto,
                    plazo_dias=plazo,
                    tasa_ea=tasa_ea,
                    instrumento=instrumento,
                    comision_anual=comision
                )
                
                # Validar rentabilidad
                validacion = validar_rentabilidad_inversion(inv)
                
                # Mostrar alertas ANTES de las métricas
                if validacion['alertas']:
                    for alerta in validacion['alertas']:
                        if alerta['nivel'] == 'CRÍTICO':
                            st.error(f"{alerta['emoji']} **{alerta['mensaje']}**\n\n{alerta['detalle']}\n\n💡 {alerta['recomendacion']}")
                        elif alerta['nivel'] == 'ADVERTENCIA':
                            st.warning(f"{alerta['emoji']} **{alerta['mensaje']}**\n\n{alerta['detalle']}\n\n💡 {alerta['recomendacion']}")
                        else:
                            st.info(f"{alerta['emoji']} **{alerta['mensaje']}**\n\n{alerta['detalle']}\n\n💡 {alerta['recomendacion']}")
                
                inversiones.append(inv)
                
                # Mostrar cálculos
                resultado = inv.calcular_retorno_neto()
                
                st.markdown(f"**📊 Proyección Inversión {idx}:**")
                
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                
                with col_r1:
                    st.metric(
                        "Retorno Bruto",
                        formatear_moneda(resultado['retorno_bruto']),
                        help="Antes de descuentos"
                    )
                
                with col_r2:
                    st.metric(
                        "Descuentos",
                        formatear_moneda(resultado['descuentos_totales']),
                        delta=f"-{(resultado['descuentos_totales']/resultado['retorno_bruto']*100):.1f}%",
                        delta_color="inverse",
                        help=f"Comisión: ${resultado['comision']:,.0f} | Retención: ${resultado['retencion_fuente']:,.0f} | GMF: ${resultado['gmf']:,.0f}"
                    )
                
                with col_r3:
                    # Color ROJO si retorno negativo, VERDE si positivo
                    retorno_neto = resultado['retorno_neto']
                    roi_neto = resultado['roi_neto']
                    
                    st.metric(
                        "💰 Retorno Neto",
                        formatear_moneda(retorno_neto),
                        delta=f"{'+' if roi_neto >= 0 else ''}{roi_neto:.2f}%",
                        delta_color="normal" if retorno_neto >= 0 else "inverse",
                        help="Después de todos los descuentos"
                    )
                
                with col_r4:
                    tasa_efectiva = resultado['tasa_efectiva_neta']
                    st.metric(
                        "Tasa Efectiva",
                        f"{tasa_efectiva:.2f}% EA",
                        delta=f"{tasa_efectiva - tasa_ea:.2f}% vs nominal" if tasa_efectiva < tasa_ea else None,
                        delta_color="inverse" if tasa_efectiva < tasa_ea else "normal",
                        help="Tasa real después de descuentos"
                    )
            
            # Mostrar información del instrumento
            with st.expander(f"ℹ️ ¿Por qué invertir en {instrumento}?"):
                info = get_info_instrumento(instrumento)
                if info:
                    st.markdown(f"**{info['nombre_completo']}**")
                    st.caption(info['descripcion'])
                    
                    col_info1, col_info2 = st.columns(2)
                    
                    with col_info1:
                        st.markdown("**Ventajas:**")
                        for ventaja in info['ventajas']:
                            st.caption(ventaja)
                    
                    with col_info2:
                        st.markdown("**Desventajas:**")
                        for desventaja in info['desventajas']:
                            st.caption(desventaja)
                    
                    st.info(f"💡 **Mejor para:** {info['mejor_para']}")
                    
                    col_det1, col_det2, col_det3 = st.columns(3)
                    with col_det1:
                        st.caption(f"🔒 **Liquidez:** {info['liquidez']}")
                    with col_det2:
                        st.caption(f"⚠️ **Riesgo:** {info['riesgo']}")
                    with col_det3:
                        st.caption(f"💰 **Comisión:** {info['comision']}")
    
    # Resumen consolidado de inversiones
    if inversiones:
        st.markdown("---")
        st.markdown("#### 📊 Resumen Consolidado")
        
        resumen = calcular_resumen_portafolio(inversiones)
        monto_total_inv = resumen['monto_total']
        
        col_res1, col_res2, col_res3, col_res4 = st.columns(4)
        
        with col_res1:
            st.metric(
                "Total Invertido",
                formatear_moneda(monto_total_inv),
                delta=f"{resumen['numero_inversiones']} inversión(es)"
            )
        
        with col_res2:
            st.metric(
                "Retorno Neto Total",
                formatear_moneda(resumen['retorno_neto_total']),
                delta=f"+{resumen['roi_promedio_ponderado']:.2f}%"
            )
        
        with col_res3:
            st.metric(
                "Descuentos Totales",
                formatear_moneda(resumen['descuentos_totales']),
                delta=f"-{(resumen['descuentos_totales']/resumen['retorno_bruto_total']*100):.1f}%",
                delta_color="inverse"
            )
        
        with col_res4:
            st.metric(
                "Plazo Promedio",
                f"{resumen['plazo_promedio_ponderado']:.0f} días"
            )
        
        # Validación: Monto total vs Excedente disponible
        excedente_disponible = excedente_info['excedente_invertible']
        porcentaje_usado = (monto_total_inv / excedente_disponible * 100) if excedente_disponible > 0 else 0
        
        if monto_total_inv > excedente_disponible:
            # SOBRE-INVERSIÓN - Alerta crítica
            exceso = monto_total_inv - excedente_disponible
            st.error(
                f"🚨 **ALERTA CRÍTICA:** Total invertido ({formatear_moneda(monto_total_inv)}) "
                f"excede el excedente disponible ({formatear_moneda(excedente_disponible)}) "
                f"por {formatear_moneda(exceso)} ({porcentaje_usado:.1f}% del excedente). "
                f"Reducir montos para evitar comprometer liquidez operativa."
            )
        elif porcentaje_usado > 90:
            # INVERSIÓN ALTA - Advertencia
            st.warning(
                f"⚠️ **ADVERTENCIA:** Estás invirtiendo {porcentaje_usado:.1f}% del excedente disponible. "
                f"Considera mantener mayor reserva de liquidez."
            )
        elif porcentaje_usado > 75:
            # INVERSIÓN MODERADA-ALTA - Info
            st.info(
                f"ℹ️ Invirtiendo {porcentaje_usado:.1f}% del excedente disponible. "
                f"Liquidez remanente: {formatear_moneda(excedente_disponible - monto_total_inv)}."
            )
        else:
            # INVERSIÓN SALUDABLE
            st.success(
                f"✅ Inversión saludable: {porcentaje_usado:.1f}% del excedente. "
                f"Reserva disponible: {formatear_moneda(excedente_disponible - monto_total_inv)}."
            )
        
        # Análisis de riesgo
        st.markdown("#### ⚖️ Análisis de Riesgo de Liquidez")
        
        riesgo = analizar_riesgo_liquidez(
            estado['saldo_total'],
            monto_total_inv,
            excedente_info['margen_total']
        )
        
        col_riesgo1, col_riesgo2, col_riesgo3 = st.columns(3)
        
        with col_riesgo1:
            st.metric(
                "Liquidez Post-Inversión",
                formatear_moneda(riesgo['liquidez_post_inversion']),
                delta=f"{riesgo['porcentaje_invertido']:.1f}% invertido"
            )
        
        with col_riesgo2:
            st.metric(
                "Ratio de Cobertura",
                f"{riesgo['ratio_cobertura']:.2f}x",
                help="Veces que la liquidez cubre el margen total"
            )
        
        with col_riesgo3:
            st.metric(
                f"{riesgo['emoji']} Estado",
                riesgo['estado'],
                help=f"Nivel de riesgo: {riesgo['nivel_riesgo']}"
            )
        
        # Alertas
        if riesgo['nivel_riesgo'] in ['ALTO', 'CRÍTICO']:
            st.error(f"⚠️ **ALERTA:** Liquidez {riesgo['nivel_riesgo']} post-inversión. Considere reducir montos o diversificar plazos.")
        elif riesgo['nivel_riesgo'] == 'MEDIO':
            st.warning(f"⚠️ Liquidez ajustada. Ratio de cobertura: {riesgo['ratio_cobertura']:.2f}x (recomendado >2.0x)")
        else:
            st.success(f"✅ Liquidez adecuada. Inversiones dentro de parámetros seguros.")
        
        # Timeline de vencimientos
        st.markdown("---")
        st.markdown("#### 📅 Timeline de Vencimientos")
        
        timeline_data = crear_timeline_vencimientos(inversiones)
        
        if timeline_data['inversiones']:
            from datetime import datetime, date
            import pandas as pd
            import plotly.express as px
            
            # Preparar datos para plotly express
            df_timeline = []
            for inv_data in timeline_data['inversiones']:
                # Convertir date a datetime si es necesario
                fecha_inicio = inv_data['fecha_inicio']
                fecha_venc = inv_data['fecha_vencimiento']
                
                if isinstance(fecha_inicio, date) and not isinstance(fecha_inicio, datetime):
                    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
                if isinstance(fecha_venc, date) and not isinstance(fecha_venc, datetime):
                    fecha_venc = datetime.combine(fecha_venc, datetime.min.time())
                
                # Convertir a pd.Timestamp para compatibilidad total con px.timeline
                fecha_inicio = pd.Timestamp(fecha_inicio)
                fecha_venc = pd.Timestamp(fecha_venc)
                
                df_timeline.append({
                    'Inversión': inv_data['nombre'],
                    'Start': fecha_inicio,
                    'Finish': fecha_venc,
                    'Instrumento': inv_data['instrumento'],
                    'Monto': formatear_moneda(inv_data['monto']),
                    'Retorno': formatear_moneda(inv_data['retorno_neto']),
                    'Plazo': f"{inv_data['plazo_dias']} días"
                })
            
            df = pd.DataFrame(df_timeline)
            
            # Crear timeline con plotly express
            fig = px.timeline(
                df, 
                x_start="Start", 
                x_end="Finish", 
                y="Inversión",
                color="Instrumento",
                hover_data=['Monto', 'Retorno', 'Plazo'],
                title="Cronograma de Vencimientos"
            )
            
            # Invertir eje Y para que la primera inversión esté arriba
            fig.update_yaxes(autorange="reversed")
            
            # Línea vertical "Hoy" - usar add_shape en lugar de add_vline
            fecha_hoy = timeline_data['fecha_inicio']
            
            # Convertir a datetime si es necesario
            if isinstance(fecha_hoy, date) and not isinstance(fecha_hoy, datetime):
                fecha_hoy = datetime.combine(fecha_hoy, datetime.min.time())
            
            # Convertir a pd.Timestamp
            fecha_hoy_ts = pd.Timestamp(fecha_hoy)
            
            # Usar add_shape en lugar de add_vline (compatible con Timestamps)
            fig.add_shape(
                type="line",
                x0=fecha_hoy_ts,
                x1=fecha_hoy_ts,
                y0=0,
                y1=1,
                yref="paper",  # Línea vertical completa (de 0 a 1 en coordenadas paper)
                line=dict(
                    color="gray",
                    width=2,
                    dash="dot"
                )
            )
            
            # Agregar anotación "Hoy"
            fig.add_annotation(
                x=fecha_hoy_ts,
                y=1,
                yref="paper",
                text="Hoy",
                showarrow=False,
                yshift=10,
                font=dict(size=10, color="gray")
            )
            
            # Layout
            fig.update_layout(
                title="Cronograma de Vencimientos",
                xaxis_title="Fecha",
                yaxis_title="",
                showlegend=False,
                height=300 + len(timeline_data['inversiones']) * 40,
                hovermode='closest',
                xaxis=dict(
                    type='date',
                    tickformat='%d/%m/%Y'
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Resumen de vencimientos
            col_time1, col_time2, col_time3 = st.columns(3)
            
            with col_time1:
                st.metric(
                    "Próximo Vencimiento",
                    timeline_data['inversiones'][0]['fecha_vencimiento'].strftime('%d/%m/%Y'),
                    delta=f"{timeline_data['inversiones'][0]['plazo_dias']} días"
                )
            
            with col_time2:
                st.metric(
                    "Capital a Recuperar",
                    formatear_moneda(timeline_data['capital_total']),
                    help="Capital total invertido"
                )
            
            with col_time3:
                st.metric(
                    "Retorno Total Esperado",
                    formatear_moneda(timeline_data['retorno_total']),
                    delta=f"+{(timeline_data['retorno_total']/timeline_data['capital_total']*100):.2f}%"
                )


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
        
        # GASTOS FIJOS EMPRESARIALES (primero, más prominente)
        st.markdown("#### 💼 Gastos Fijos Empresariales")
        gastos_fijos_mensuales = st.number_input(
            "Monto mensual (COP)",
            min_value=0,
            value=50_000_000,
            step=1_000_000,
            format="%d",
            help="Gastos fijos empresariales: nómina administrativa, arriendo oficina, servicios, etc.",
            key="gastos_fijos_input"
        )
        
        gastos_fijos_semanales = gastos_fijos_mensuales / 4.33
        st.caption(f"   ≈ ${gastos_fijos_semanales:,.0f} / semana")
        
        st.markdown("---")
        
        # Horizonte de análisis (segundo)
        st.markdown("#### 📅 Horizonte de Proyección")
        semanas_futuro = st.slider(
            "Semanas a futuro",
            min_value=4,
            max_value=16,
            value=SEMANAS_FUTURO_DEFAULT,
            step=1,
            help="Semanas a proyectar hacia adelante desde hoy"
        )
        
        st.markdown("---")
        
        # Semanas de margen de protección
        st.markdown("#### 🛡️ Margen de Protección")
        semanas_margen = st.slider(
            "Semanas de margen",
            min_value=4,
            max_value=16,
            value=SEMANAS_MARGEN_DEFAULT,
            step=1,
            help="Número de semanas de burn rate total a mantener como reserva de contingencia"
        )
        st.caption(f"   Margen = Burn Rate Total × {semanas_margen} semanas")
        
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
    consolidador = ConsolidadorMultiproyecto(
        semanas_futuro=semanas_futuro,
        gastos_fijos_mensuales=gastos_fijos_mensuales,
        semanas_margen=semanas_margen
    )
    
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
            st.session_state.gastos_fijos_mensuales = gastos_fijos_mensuales
            st.session_state.semanas_futuro = semanas_futuro
            st.session_state.semanas_margen = semanas_margen
            st.success("✅ Consolidación completada")
            st.rerun()
    
    # Mostrar dashboard si ya está consolidado
    if 'consolidador' in st.session_state:
        consolidador_previo = st.session_state.consolidador
        
        # Verificar si cambiaron los parámetros
        gastos_fijos_previos = st.session_state.get('gastos_fijos_mensuales', gastos_fijos_mensuales)
        semanas_futuro_previas = st.session_state.get('semanas_futuro', semanas_futuro)
        semanas_margen_previas = st.session_state.get('semanas_margen', semanas_margen)
        
        cambio_gastos = gastos_fijos_previos != gastos_fijos_mensuales
        cambio_horizonte = semanas_futuro_previas != semanas_futuro
        cambio_margen = semanas_margen_previas != semanas_margen
        
        if cambio_gastos or cambio_horizonte or cambio_margen:
            # Reconsolidar con nuevos parámetros
            with st.spinner("Recalculando..."):
                if cambio_gastos:
                    consolidador_previo.gastos_fijos_semanales = gastos_fijos_mensuales / 4.33
                if cambio_horizonte:
                    consolidador_previo.semanas_futuro = semanas_futuro
                if cambio_margen:
                    consolidador_previo.semanas_margen = semanas_margen
                
                consolidador_previo.consolidar()
                st.session_state.consolidador = consolidador_previo
                st.session_state.gastos_fijos_mensuales = gastos_fijos_mensuales
                st.session_state.semanas_futuro = semanas_futuro
                st.session_state.semanas_margen = semanas_margen
        
        consolidador = st.session_state.consolidador
        
        # Obtener estado actual
        estado = consolidador.get_estado_actual()
        
        if not estado:
            st.error("❌ No se pudo obtener el estado actual")
            return
        
        # GUARDAR DATOS PARA MÓDULO DE REPORTES
        st.session_state.datos_reportes = {
            'timestamp': datetime.now(),
            'estado_caja': estado,
            'proyectos': consolidador.proyectos,
            'df_consolidado': consolidador.df_consolidado,
            'gastos_fijos_mensuales': gastos_fijos_mensuales,
            'semanas_futuro': semanas_futuro,
            'semana_actual': consolidador.semana_actual_consolidada
        }
        
        # SIDEBAR: Métricas dinámicas
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 📊 Estado Actual")
            
            # Cobertura
            if estado['burn_rate'] > 0:
                cobertura_semanas = estado['saldo_total'] / estado['burn_rate']
                st.metric(
                    "Cobertura",
                    f"{cobertura_semanas:.1f} semanas",
                    help="Semanas de operación con capital disponible"
                )
            else:
                st.metric("Cobertura", "∞ semanas", help="Sin gastos proyectados")
            
            # Margen requerido
            st.metric(
                "Margen Requerido",
                formatear_moneda(estado['margen_proteccion']),
                help="8 semanas de burn rate total"
            )
            
            # Estado de liquidez
            color_map = {
                'EXCEDENTE': '🟢',
                'AJUSTADO': '🟡',
                'CRÍTICO': '🔴'
            }
            emoji = color_map.get(estado['estado_general'], '⚪')
            st.metric(
                "Estado",
                f"{emoji} {estado['estado_general']}",
                help="Estado de liquidez empresarial"
            )
        
        st.markdown("---")
        st.markdown("## 📊 Dashboard Consolidado")
        
        # Renderizar secciones del dashboard
        render_metricas_principales(estado)
        
        st.markdown("---")
        
        render_metricas_cobertura(estado)
        
        st.markdown("---")
        
        render_excedente_invertible(estado)
        
        st.markdown("---")
        
        render_timeline_consolidado(consolidador)
        
        st.markdown("---")
        
        # Sección de Inversiones Temporales
        if INVERSIONES_DISPONIBLES:
            render_inversiones_temporales(estado)
        
        st.markdown("---")
        
        # Sección de Exportar JSON
        render_exportar_json_simple(consolidador, estado)
        
        st.markdown("---")
        
        # SECCIÓN DE REPORTES
        st.markdown("### 📊 Generar Reportes Ejecutivos")
        st.caption("Acceda al módulo de reportes con los datos consolidados actuales")
        
        col_rep1, col_rep2, col_rep3 = st.columns([2, 2, 1])
        
        with col_rep1:
            if st.button("📄 Ver Reportes Ejecutivos", use_container_width=True, type="primary"):
                st.session_state.modulo_actual = 'reportes'
                st.rerun()
        
        with col_rep2:
            # Mostrar edad de datos
            if 'datos_reportes' in st.session_state:
                edad = (datetime.now() - st.session_state.datos_reportes['timestamp']).total_seconds() / 60
                if edad < 1:
                    st.success(f"✅ Datos actualizados (hace {edad*60:.0f} segundos)")
                else:
                    st.info(f"ℹ️ Datos actualizados hace {edad:.0f} minutos")
            else:
                st.warning("⚠️ No hay datos guardados para reportes")
        
        with col_rep3:
            st.caption("💡 Los reportes usan los datos consolidados actuales")



if __name__ == "__main__":
    main()
