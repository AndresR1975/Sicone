"""
SICONE - Módulo de Reportes Ejecutivos
Generación de reportes PDF para multiproyecto e inversiones temporales

Versión: 3.3.4 FILTRADO PARCIAL
Fecha: 20 Enero 2026
Autor: AI-MindNovation

CHANGELOG:
v3.3.4 (20-Ene-2026) - SOLUCIÓN: FILTRADO PARCIAL EXPLICADO:
- 🔍 DIAGNÓSTICO: Debug reveló que ejecucion_financiera usa semanas del proyecto (1,2,3...)
  mientras df_consolidado usa semanas globales - NO HAY MAPEO entre ambos
- ✅ SOLUCIÓN: filtrar_proyectos_por_fechas() ahora retorna proyectos SIN FILTRAR
- ✅ RESULTADO: Waterfall y métricas header SÍ se filtran (usan df_consolidado)
- ⚠️ LIMITACIÓN: Semáforo, Tabla y Pie NO se filtran (muestran totales completos)
- 📢 NUEVO: Mensajes informativos en UI explicando qué se filtra y por qué
- 🐛 DEBUG: Tabla visible en UI mostrando valores procesados

COMPORTAMIENTO ACTUAL CON FILTROS:
✅ SÍ se filtran:
  - Gráfico Waterfall (flujos del período)
  - Métricas del header (saldo total, burn rate consolidado)
  
❌ NO se filtran:
  - Gráfico Semáforo (burn rate y cobertura por proyecto)
  - Tabla de proyectos (ejecutado, saldo, burn rate)
  - Gráfico Pie (distribución de categorías)

RAZÓN TÉCNICA:
No existe forma de mapear las semanas individuales de cada proyecto con las
semanas consolidadas globales sin información adicional en el JSON.

USO:
    datos = convertir_json_a_datos(json_data, fecha_inicio=date(2024,1,1), fecha_fin=date(2024,12,31))
    pdf_bytes = generar_reporte_gerencial_pdf(datos)
"""

import io
import copy
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Matplotlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle

# Streamlit (opcional)
try:
    import streamlit as st
    STREAMLIT_DISPONIBLE = True
except ImportError:
    STREAMLIT_DISPONIBLE = False
    st = None

# ============================================================================
# CONFIGURACIÓN GLOBAL
# ============================================================================

# Verificar disponibilidad de utils
try:
    from utils import formatear_moneda as formatear_moneda_utils, obtener_valor_seguro, calcular_semanas_cobertura
    UTILS_DISPONIBLE = True
except ImportError:
    UTILS_DISPONIBLE = False


# ============================================================================
# FUNCIONES COMUNES - FORMATEO
# ============================================================================

def parsear_fecha(fecha_valor):
    """
    Convierte fecha desde múltiples formatos a objeto date
    Maneja: str (ISO), date, datetime, None
    
    Args:
        fecha_valor: Fecha en cualquier formato
    
    Returns:
        date object o date.today() como fallback
    """
    if fecha_valor is None:
        return date.today()
    
    # Si ya es date, retornar directamente
    if isinstance(fecha_valor, date) and not isinstance(fecha_valor, datetime):
        return fecha_valor
    
    # Si es datetime, convertir a date
    if isinstance(fecha_valor, datetime):
        return fecha_valor.date()
    
    # Si es string, parsear ISO format
    if isinstance(fecha_valor, str):
        try:
            # Intentar parsear ISO format completo
            return datetime.fromisoformat(fecha_valor).date()
        except:
            try:
                # Intentar parsear solo la fecha (YYYY-MM-DD)
                return datetime.strptime(fecha_valor[:10], '%Y-%m-%d').date()
            except:
                # Fallback
                return date.today()
    
    # Fallback final
    return date.today()


def parsear_timestamp(timestamp_valor):
    """
    Convierte timestamp desde múltiples formatos a objeto datetime
    Maneja: str (ISO), datetime, None
    
    Args:
        timestamp_valor: Timestamp en cualquier formato
    
    Returns:
        datetime object o datetime.now() como fallback
    """
    if timestamp_valor is None:
        return datetime.now()
    
    # Si ya es datetime, retornar directamente
    if isinstance(timestamp_valor, datetime):
        return timestamp_valor
    
    # Si es string, parsear ISO format
    if isinstance(timestamp_valor, str):
        try:
            return datetime.fromisoformat(timestamp_valor)
        except:
            try:
                # Intentar sin timezone info
                return datetime.fromisoformat(timestamp_valor.replace('Z', '+00:00'))
            except:
                # Fallback
                return datetime.now()
    
    # Fallback final
    return datetime.now()


def formatear_moneda(valor: float) -> str:
    """
    Formatea valores monetarios en formato colombiano (compartido por ambos reportes)
    
    Args:
        valor: Valor numérico a formatear
        
    Returns:
        String formateado (ej: "$250.0M", "$1.5B")
    """
    if UTILS_DISPONIBLE:
        return formatear_moneda_utils(valor)
    
    # Fallback manual
    if valor >= 1_000_000_000:
        return f"${valor/1_000_000_000:.1f}B"
    elif valor >= 1_000_000:
        return f"${valor/1_000_000:.1f}M"
    elif valor >= 1_000:
        return f"${valor/1_000:.0f}K"
    else:
        return f"${valor:,.0f}"


# ============================================================================
# REPORTE 1: GERENCIAL MULTIPROYECTO
# ============================================================================

def generar_grafico_waterfall(datos: Dict) -> Optional[bytes]:
    """
    Genera gráfico Waterfall mostrando evolución del saldo en el período disponible
    (Usado en reporte multiproyecto)
    """
    try:
        # Obtener DataFrame consolidado
        df = datos.get('df_consolidado')
        
        if df is None or df.empty:
            return None
        
        if 'saldo_consolidado' not in df.columns:
            return None
        
        # Obtener gastos fijos
        gastos_fijos_semanales = datos.get('gastos_fijos_mensuales', 0) / 4.33
        
        # Determinar período a mostrar
        # Si hay filtro activo, usar TODO el período filtrado
        # Si no hay filtro, usar últimas 6 semanas históricas
        fecha_inicio_filtro = datos.get('filtro_fecha_inicio')
        fecha_fin_filtro = datos.get('filtro_fecha_fin')
        
        if fecha_inicio_filtro or fecha_fin_filtro:
            # Con filtro: usar TODO el período disponible
            df_periodo = df.copy()
        else:
            # Sin filtro: usar últimas 6 semanas históricas (comportamiento original)
            semana_actual = datos.get('semana_actual', 0)
            if semana_actual == 0:
                return None
            
            df_periodo = df[
                (df['semana_consolidada'] >= semana_actual - 5) &
                (df['semana_consolidada'] <= semana_actual) &
                (df['es_historica'] == True)
            ].copy()
        
        if df_periodo.empty or len(df_periodo) < 2:
            return None
        
        # Calcular valores
        saldo_inicio = df_periodo.iloc[0]['saldo_consolidado']
        saldo_final = df_periodo.iloc[-1]['saldo_consolidado']
        
        # Obtener fechas del período
        fecha_inicio_periodo = df_periodo.iloc[0]['fecha']
        fecha_fin_periodo = df_periodo.iloc[-1]['fecha']
        
        # Flujos acumulados en el período
        ingresos_acum = df_periodo['ingresos_proy_total'].sum() if 'ingresos_proy_total' in df_periodo.columns else 0
        egresos_acum = df_periodo['egresos_proy_total'].sum() if 'egresos_proy_total' in df_periodo.columns else 0
        gastos_fijos_acum = gastos_fijos_semanales * len(df_periodo)
        
        # Preparar datos para waterfall con etiquetas dinámicas
        etiqueta_inicio = f"Inicio\n({fecha_inicio_periodo.strftime('%d/%m')})"
        etiqueta_fin = f"Final\n({fecha_fin_periodo.strftime('%d/%m')})"
        categorias = [etiqueta_inicio, 'Ingresos', 'Egresos\nProyectos', 'Gastos\nFijos', etiqueta_fin]
        
        valores = [
            saldo_inicio,
            ingresos_acum,
            -egresos_acum,
            -gastos_fijos_acum,
            0
        ]
        
        # Calcular posiciones
        acumulado = saldo_inicio
        posiciones_base = [0]
        alturas = [saldo_inicio]
        
        for i in range(1, 4):
            posiciones_base.append(acumulado)
            alturas.append(valores[i])
            acumulado += valores[i]
        
        posiciones_base.append(0)
        alturas.append(saldo_final)
        
        # Colores
        colores = ['#3b82f6', '#22c55e', '#ef4444', '#f97316', '#3b82f6']
        
        # Crear gráfico
        fig, ax = plt.subplots(figsize=(2.8, 2.8))
        
        # Dibujar barras
        for i in range(len(categorias)):
            ax.bar(i, alturas[i], bottom=posiciones_base[i], 
                   color=colores[i], edgecolor='white', linewidth=1.5, width=0.6)
            
            # Etiquetas
            if i == 0 or i == 4:
                y_pos = posiciones_base[i] + alturas[i] / 2
                valor_texto = formatear_moneda(alturas[i])
            else:
                y_pos = posiciones_base[i] + alturas[i] / 2
                valor_absoluto = abs(alturas[i])
                valor_texto = formatear_moneda(valor_absoluto)
            
            ax.text(i, y_pos, valor_texto, 
                   ha='center', va='center', fontsize=5, fontweight='bold', color='white')
        
        # Conectores
        for i in range(len(categorias) - 1):
            if i < 4:
                y_start = posiciones_base[i] + alturas[i]
                y_end = posiciones_base[i+1]
                ax.plot([i + 0.3, i + 0.7], [y_start, y_end], 
                       'k--', linewidth=0.8, alpha=0.5)
        
        ax.set_xticks(range(len(categorias)))
        ax.set_xticklabels(categorias, fontsize=6)
        ax.set_ylabel('Saldo', fontsize=6, fontweight='bold')
        ax.set_title('Flujo de Caja (6 semanas)', fontsize=8, fontweight='bold', pad=4)
        ax.grid(True, alpha=0.2, axis='y', linestyle='--', linewidth=0.4)
        
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: formatear_moneda(x)))
        ax.yaxis.set_major_locator(plt.MaxNLocator(4))
        ax.tick_params(axis='y', labelsize=5)
        
        plt.tight_layout(pad=0.2)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf
        
    except Exception as e:
        print(f"Error generando waterfall: {e}")
        return None


def generar_grafico_pie_gastos(datos: Dict) -> Optional[bytes]:
    """
    Genera pie chart de distribución por categorías de gasto consolidadas
    Muestra proporciones (que son constantes independiente del período)
    """
    try:
        proyectos = datos.get('proyectos', [])
        
        if not proyectos:
            return None
        
        # Consolidar categorías de TODA la proyección (distribución porcentual)
        categorias = {
            'Mano de Obra': 0,
            'Materiales': 0,
            'Administración': 0,
            'Variables': 0
        }
        
        for proyecto in proyectos:
            data = proyecto.get('data', {})
            if not data:
                continue
            
            proyeccion = data.get('proyeccion_semanal', [])
            if not proyeccion:
                continue
            
            # Sumar toda la proyección (para obtener proporciones)
            for semana in proyeccion:
                categorias['Mano de Obra'] += semana.get('Mano_Obra', 0)
                categorias['Materiales'] += semana.get('Materiales', 0)
                categorias['Administración'] += semana.get('Admin', 0)
                categorias['Variables'] += (
                    semana.get('Equipos', 0) +
                    semana.get('Imprevistos', 0) +
                    semana.get('Logistica', 0)
                )
        
        if sum(categorias.values()) == 0:
            return None
        
        nombres = list(categorias.keys())
        valores = list(categorias.values())
        colores = ['#3b82f6', '#22c55e', '#f97316', '#8b5cf6']
        
        fig, ax = plt.subplots(figsize=(2.8, 2.8))
        
        def formato_label(pct):
            return f'{pct:.1f}%' if pct > 3 else ''
        
        wedges, texts, autotexts = ax.pie(valores, 
                                           labels=None,
                                           autopct=formato_label,
                                           startangle=90,
                                           colors=colores[:len(nombres)],
                                           textprops={'fontsize': 5, 'weight': 'bold', 'color': 'white'},
                                           wedgeprops={'edgecolor': 'white', 'linewidth': 1})
        
        ax.set_title('Categorías de Gasto', fontsize=8, fontweight='bold', pad=4)
        ax.legend(nombres, loc='center left', bbox_to_anchor=(0.85, 0.5),
                 fontsize=5, framealpha=0.95, ncol=1)
        
        plt.tight_layout(pad=0.2)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf
        
    except Exception as e:
        print(f"Error generando pie: {e}")
        return None


def generar_grafico_semaforo(datos: Dict) -> Optional[bytes]:
    """
    Genera semáforo de estado financiero por proyecto
    (Usado en reporte multiproyecto)
    """
    try:
        proyectos = datos.get('proyectos', [])
        
        print(f"\n🚦 DEBUG generar_grafico_semaforo:")
        print(f"  - Num proyectos: {len(proyectos)}")
        
        if not proyectos or len(proyectos) == 0:
            print("  ⚠️ Sin proyectos - retornando None")
            return None
        
        # Usar todos los proyectos dinámicamente (no limitar a 5)
        proyectos_mostrar = proyectos
        
        for i, p in enumerate(proyectos_mostrar[:3]):  # Mostrar primeros 3 para debug
            nombre = p.get('nombre', 'Sin nombre')[:20]
            saldo = p.get('saldo_real_tesoreria', 0)
            burn_rate = p.get('burn_rate_real', 0)
            ejecutado = p.get('ejecutado', 0)
            print(f"  [{i}] {nombre}: ejecutado=${ejecutado/1_000_000:.1f}M, saldo=${saldo/1_000_000:.1f}M, burn_rate=${burn_rate/1_000_000:.2f}M")
        
        fig, ax = plt.subplots(figsize=(5.5, 1.8))  # Optimizado para 4-6 proyectos
        
        nombres = []
        coberturas = []
        colores_barra = []
        
        for p in proyectos_mostrar:
            nombre = p.get('nombre', 'Sin nombre')[:20]
            saldo = p.get('saldo_real_tesoreria', 0)
            burn_rate = p.get('burn_rate_real', 0)
            
            if burn_rate > 0:
                cobertura = saldo / burn_rate
            else:
                cobertura = 100
            
            nombres.append(nombre)
            coberturas.append(min(cobertura, 100))
            
            # Color según cobertura
            if cobertura >= 20:
                colores_barra.append('#22c55e')  # Verde
            elif cobertura >= 10:
                colores_barra.append('#f97316')  # Naranja
            else:
                colores_barra.append('#ef4444')  # Rojo
        
        y_pos = np.arange(len(nombres))
        
        ax.barh(y_pos, coberturas, color=colores_barra, edgecolor='white', linewidth=1.5)
        
        # Etiquetas
        for i, (cob, col) in enumerate(zip(coberturas, colores_barra)):
            if cob < 100:
                ax.text(cob + 2, i, f'{cob:.1f}s', va='center', fontsize=6, fontweight='bold')
            else:
                ax.text(95, i, '100.0s', va='center', fontsize=6, fontweight='bold', color='white')
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(nombres, fontsize=6)
        ax.set_xlabel('Cobertura (semanas)', fontsize=7)
        ax.set_title('Estado Financiero por Proyecto', fontsize=8, fontweight='bold', pad=2)  # Reducido pad de 4 a 2
        ax.set_xlim(0, 100)
        
        # Leyenda
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#22c55e', label='Exc (≥20s)'),
            Patch(facecolor='#f97316', label='Ale (≥5s)'),
            Patch(facecolor='#ef4444', label='Crí (<5s)')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=5, framealpha=0.9)
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, axis='x', alpha=0.2, linestyle='--')
        
        plt.tight_layout(pad=0.1)  # Reducido de 0.2 a 0.1
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf
        
    except Exception as e:
        print(f"Error generando semáforo: {e}")
        return None


def generar_reporte_gerencial_pdf(datos: Dict) -> bytes:
    """
    Genera el Reporte Gerencial Multiproyecto en PDF (1 página)
    
    Args:
        datos: Diccionario con datos consolidados del multiproyecto
        
    Returns:
        bytes: PDF generado
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
    except ImportError as e:
        raise ImportError("reportlab no está instalado") from e
    
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,  # Reducido de 18 a 16
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=8,  # Reducido de 12 a 8
        alignment=TA_CENTER
    )
    
    style_subtitle = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=9,  # Reducido de 10 a 9
        textColor=colors.gray,
        spaceAfter=4,  # Reducido de 6 a 4
        alignment=TA_CENTER
    )
    
    elements = []
    
    # ENCABEZADO
    estado = datos['estado_caja']
    timestamp = datos['timestamp']
    
    elements.append(Paragraph("REPORTE GERENCIAL MULTIPROYECTO", style_title))
    elements.append(Paragraph(f"Generado: {timestamp.strftime('%d/%m/%Y %H:%M')}", style_subtitle))
    
    # Indicador de filtro de fechas si está aplicado
    fecha_inicio_filtro = datos.get('filtro_fecha_inicio')
    fecha_fin_filtro = datos.get('filtro_fecha_fin')
    
    if fecha_inicio_filtro or fecha_fin_filtro:
        texto_filtro = "📅 Período filtrado: "
        if fecha_inicio_filtro and fecha_fin_filtro:
            texto_filtro += f"{fecha_inicio_filtro.strftime('%d/%m/%Y')} - {fecha_fin_filtro.strftime('%d/%m/%Y')}"
        elif fecha_inicio_filtro:
            texto_filtro += f"Desde {fecha_inicio_filtro.strftime('%d/%m/%Y')}"
        elif fecha_fin_filtro:
            texto_filtro += f"Hasta {fecha_fin_filtro.strftime('%d/%m/%Y')}"
        
        style_filtro = ParagraphStyle(
            'FiltroInfo',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#f97316'),  # Naranja para destacar
            spaceAfter=2,
            alignment=TA_CENTER
        )
        elements.append(Paragraph(texto_filtro, style_filtro))
    
    elements.append(Spacer(1, 0.12*inch))  # Reducido de 0.2 a 0.12 inch
    
    # MÉTRICAS CLAVE
    saldo_total = estado.get('saldo_total', 0)
    margen_proteccion = estado.get('margen_proteccion', 0)
    burn_rate = estado.get('burn_rate', 0)
    excedente_invertible = estado.get('excedente_invertible', 0)
    estado_general = estado.get('estado_general', 'N/A')
    proyectos_activos = estado.get('proyectos_activos', 0)
    total_proyectos = estado.get('total_proyectos', 0)
    
    if UTILS_DISPONIBLE:
        cobertura = calcular_semanas_cobertura(saldo_total, burn_rate)
    else:
        cobertura = saldo_total / burn_rate if burn_rate > 0 else 999
    
    metricas_data = [
        ['Fecha', 'Estado de Caja', 'Margen de Protección', 'Cobertura'],
        [
            timestamp.strftime('%d/%m/%Y'),
            formatear_moneda(saldo_total),
            formatear_moneda(margen_proteccion),
            f"{cobertura:.1f} semanas"
        ],
        ['Disponible Inversión', 'Burn Rate Semanal', 'Estado General', 'Proyectos Activos'],
        [
            formatear_moneda(excedente_invertible),
            formatear_moneda(burn_rate),
            estado_general,
            f"{proyectos_activos}/{total_proyectos}"
        ]
    ]
    
    tabla_metricas = Table(metricas_data, colWidths=[1.8*inch]*4)
    tabla_metricas.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),  # Reducido de 9 a 8
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),  # Reducido de 8 a 6
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#60a5fa')),
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.whitesmoke),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 2), (-1, 2), 8),  # Reducido de 9 a 8
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e0f2fe')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#e0f2fe')),
        ('FONTNAME', (0, 1), (-1, 3), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, 3), 9),  # Reducido de 10 a 9
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 3),  # Reducido de 4 a 3
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),  # Reducido de 4 a 3
    ]))
    
    elements.append(tabla_metricas)
    elements.append(Spacer(1, 0.1*inch))  # Reducido de 0.15 a 0.1 inch
    
    # GRÁFICOS
    waterfall_buf = generar_grafico_waterfall(datos)
    pie_buf = generar_grafico_pie_gastos(datos)
    
    graficos_data = []
    fila_graficos = []
    
    if waterfall_buf:
        waterfall_img = Image(waterfall_buf, width=2.6*inch, height=2.6*inch)  # Reducido de 2.8 a 2.6
        fila_graficos.append(waterfall_img)
    else:
        fila_graficos.append(Paragraph("Waterfall no disponible", styles['Normal']))
    
    if pie_buf:
        pie_img = Image(pie_buf, width=2.6*inch, height=2.6*inch)  # Reducido de 2.8 a 2.6
        fila_graficos.append(pie_img)
    else:
        fila_graficos.append(Paragraph("Pie no disponible", styles['Normal']))
    
    graficos_data.append(fila_graficos)
    
    tabla_graficos = Table(graficos_data, colWidths=[3.6*inch, 3.6*inch])
    tabla_graficos.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(tabla_graficos)
    elements.append(Spacer(1, 0.08*inch))  # Reducido de 0.15 a 0.08 inch
    
    # GRÁFICO SEMÁFORO
    semaforo_buf = generar_grafico_semaforo(datos)
    if semaforo_buf:
        semaforo_img = Image(semaforo_buf, width=5.5*inch, height=1.8*inch)  # Optimizado para 4-6 proyectos
        elements.append(semaforo_img)
        elements.append(Spacer(1, 0.06*inch))  # Reducido de 0.1 a 0.06 inch
    
    # TABLA PROYECTOS
    elements.append(Paragraph("DETALLE POR PROYECTO", ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=10,  # Reducido de 12 a 10
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=4  # Reducido de 6 a 4
    )))
    
    proyectos_data = [
        ['Proyecto', 'Ejecutado', 'Saldo', 'Burn Rate', 'Cobertura', '% Avance']
    ]
    
    proyectos = datos.get('proyectos', [])
    
    # DEBUG: print(f"\n📋 DEBUG tabla de proyectos:")
    # DEBUG: print(f"  - Num proyectos: {len(proyectos)}")
    
    # Procesar TODOS los proyectos dinámicamente (no limitar a 5)
    for i, p in enumerate(proyectos):
        if UTILS_DISPONIBLE:
            nombre = obtener_valor_seguro(p, 'nombre', 'Sin nombre', str)[:30]
            ejecutado = obtener_valor_seguro(p, 'ejecutado', 0, float)
            saldo = obtener_valor_seguro(p, 'saldo_real_tesoreria', 0, float)
            burn_rate = obtener_valor_seguro(p, 'burn_rate_real', 0, float)
            avance_hitos = obtener_valor_seguro(p, 'avance_hitos_pct', 0, float)
            
            if i < 3:  # Debug primeros 3 proyectos
                print(f"  [{i}] {nombre}: ejecutado=${ejecutado/1_000_000:.1f}M, saldo=${saldo/1_000_000:.1f}M, burn_rate=${burn_rate/1_000_000:.2f}M")
            
            if burn_rate > 0:
                cobertura = saldo / burn_rate
                cobertura_str = f"{cobertura:.1f}s"
            else:
                cobertura_str = "∞"
        else:
            nombre = p.get('nombre', 'Sin nombre')[:30]
            ejecutado = p.get('ejecutado', 0)
            saldo = p.get('saldo_real_tesoreria', 0)
            burn_rate = p.get('burn_rate_real', 0)
            avance_hitos = p.get('avance_hitos_pct', 0)
            
            if burn_rate > 0:
                cobertura_str = f"{saldo / burn_rate:.1f}s"
            else:
                cobertura_str = "∞"
        
        proyectos_data.append([
            nombre[:28],
            formatear_moneda(ejecutado),
            formatear_moneda(saldo),
            formatear_moneda(burn_rate) + "/s",
            cobertura_str,
            f"{avance_hitos:.1f}%"
        ])
    
    tabla_proyectos = Table(proyectos_data, colWidths=[2.0*inch, 1.3*inch, 1.3*inch, 1.1*inch, 0.9*inch, 0.8*inch])
    tabla_proyectos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f9ff')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    elements.append(tabla_proyectos)
    elements.append(Spacer(1, 0.06*inch))  # Reducido de 0.1 a 0.06 inch
    
    # FOOTER
    footer_text = f"SICONE | {timestamp.strftime('%d/%m/%Y %H:%M')}"
    elements.append(Paragraph(
        footer_text,
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7,
                      textColor=colors.gray, alignment=TA_CENTER)
    ))
    
    doc.build(elements)
    
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================================
# REPORTE 2: INVERSIONES TEMPORALES
# ============================================================================

def generar_gauge_liquidez(liquidez_post: float, margen_total: float, ratio: float, estado: str) -> Optional[bytes]:
    """
    Genera gráfico tipo gauge para análisis de liquidez
    (Usado en reporte inversiones)
    """
    try:
        fig, ax = plt.subplots(figsize=(2.5, 1.8))
        
        colores = {
            'ESTABLE': '#22c55e',
            'PRECAUCIÓN': '#f97316',
            'CRÍTICO': '#ef4444'
        }
        color = colores.get(estado, '#9ca3af')
        
        theta = 180 * min(ratio, 2.0) / 2.0
        
        wedge_bg = mpatches.Wedge((0, 0), 1, 0, 180, facecolor='#e5e7eb',
                                 edgecolor='white', linewidth=2)
        ax.add_patch(wedge_bg)
        
        wedge_prog = mpatches.Wedge((0, 0), 1, 0, theta, facecolor=color,
                                   edgecolor='white', linewidth=2)
        ax.add_patch(wedge_prog)
        
        circle = mpatches.Circle((0, 0), 0.6, facecolor='white', edgecolor='white')
        ax.add_patch(circle)
        
        ax.text(0, -0.05, f"{ratio:.2f}x", ha='center', va='center',
               fontsize=12, fontweight='bold', color=color)
        
        ax.text(0, -0.35, estado, ha='center', va='center',
               fontsize=7, fontweight='bold', color=color)
        
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-0.5, 1.2)
        ax.set_aspect('equal')
        ax.axis('off')
        
        plt.tight_layout(pad=0.1)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf
        
    except Exception as e:
        print(f"Error generando gauge: {e}")
        return None


def generar_pie_portafolio(inversiones: List[Dict]) -> Optional[bytes]:
    """
    Genera pie chart de composición del portafolio
    (Usado en reporte inversiones)
    """
    try:
        por_instrumento = {}
        for inv in inversiones:
            instrumento = inv.get('instrumento', 'Otro')
            monto = inv.get('monto', 0)
            por_instrumento[instrumento] = por_instrumento.get(instrumento, 0) + monto
        
        if not por_instrumento:
            return None
        
        nombres = list(por_instrumento.keys())
        valores = list(por_instrumento.values())
        colores = ['#3b82f6', '#22c55e', '#f97316', '#8b5cf6'][:len(nombres)]
        
        fig, ax = plt.subplots(figsize=(2.5, 2.5))
        
        def formato_label(pct):
            return f'{pct:.1f}%' if pct > 3 else ''
        
        wedges, texts, autotexts = ax.pie(
            valores, labels=None, autopct=formato_label, startangle=90,
            colors=colores,
            textprops={'fontsize': 6, 'weight': 'bold', 'color': 'white'},
            wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}
        )
        
        ax.set_title('Composición Portafolio', fontsize=8, fontweight='bold', pad=4)
        ax.legend(nombres, loc='center left', bbox_to_anchor=(0.85, 0.5),
                 fontsize=5, framealpha=0.95)
        
        plt.tight_layout(pad=0.2)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf
        
    except Exception as e:
        print(f"Error generando pie portafolio: {e}")
        return None


def generar_timeline_vencimientos(inversiones: List[Dict], fecha_hoy: date) -> Optional[bytes]:
    """
    Genera timeline tipo Gantt de vencimientos
    Usa mismos colores y nombres que el pie chart
    (Usado en reporte inversiones)
    """
    try:
        if not inversiones:
            return None
        
        fig, ax = plt.subplots(figsize=(5.5, 1.8))
        
        # Parsear fechas antes de ordenar
        inversiones_con_fechas = []
        for inv in inversiones:
            inv_copia = inv.copy()
            inv_copia['fecha_vencimiento_parsed'] = parsear_fecha(inv.get('fecha_vencimiento', fecha_hoy))
            inversiones_con_fechas.append(inv_copia)
        
        inversiones_sort = sorted(inversiones_con_fechas, key=lambda x: x['fecha_vencimiento_parsed'])
        
        # MISMOS COLORES QUE EL PIE CHART
        colores_base = ['#3b82f6', '#22c55e', '#f97316', '#8b5cf6']
        
        # Crear mapeo instrumento → color (igual que pie chart)
        instrumentos_unicos = []
        for inv in inversiones:
            instrumento = inv.get('instrumento', 'Otro')
            if instrumento not in instrumentos_unicos:
                instrumentos_unicos.append(instrumento)
        
        # Mapeo instrumento → color
        mapeo_colores = {}
        for idx, instr in enumerate(instrumentos_unicos):
            mapeo_colores[instr] = colores_base[idx % len(colores_base)]
        
        # Contar ocurrencias de cada instrumento para agregar números si hay duplicados
        conteo_instrumentos = {}
        for inv in inversiones:
            instrumento = inv.get('instrumento', 'Otro')
            conteo_instrumentos[instrumento] = conteo_instrumentos.get(instrumento, 0) + 1
        
        # Para tracking de números por instrumento
        num_por_instrumento = {}
        
        for idx, inv in enumerate(inversiones_sort[:3]):
            instrumento = inv.get('instrumento', 'Otro')
            fecha_venc = inv['fecha_vencimiento_parsed']  # Ya es date object
            dias = (fecha_venc - fecha_hoy).days
            
            # Obtener color del instrumento
            color = mapeo_colores.get(instrumento, colores_base[0])
            
            # Determinar nombre a mostrar
            if conteo_instrumentos[instrumento] > 1:
                # Si hay múltiples inversiones del mismo instrumento, agregar número
                if instrumento not in num_por_instrumento:
                    num_por_instrumento[instrumento] = 1
                else:
                    num_por_instrumento[instrumento] += 1
                nombre_display = f"{instrumento} {num_por_instrumento[instrumento]}"
            else:
                # Solo una inversión de este instrumento
                nombre_display = instrumento
            
            ax.barh(idx, dias, left=0, height=0.6, color=color,
                   edgecolor='white', linewidth=1.5)
            
            ax.text(dias / 2, idx, nombre_display, ha='center', va='center',
                   fontsize=6, color='white', fontweight='bold')
        
        ax.set_yticks(range(len(inversiones_sort[:3])))
        ax.set_yticklabels([])
        ax.set_xlabel('Días hasta vencimiento', fontsize=7)
        ax.set_title('Timeline de Vencimientos', fontsize=8, fontweight='bold', pad=4)
        ax.grid(True, axis='x', alpha=0.2, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        plt.tight_layout(pad=0.2)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf
        
    except Exception as e:
        print(f"Error generando timeline: {e}")
        return None


def generar_reporte_inversiones_pdf(datos: Dict) -> bytes:
    """
    Genera reporte PDF de inversiones temporales (1 página)
    
    Args:
        datos: Diccionario con información de inversiones
        
    Returns:
        bytes: PDF generado
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
    except ImportError as e:
        raise ImportError("reportlab no está instalado") from e
    
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=8,
        alignment=TA_CENTER
    )
    
    style_subtitle = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.gray,
        spaceAfter=6,
        alignment=TA_CENTER
    )
    
    style_section = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=6,
        spaceBefore=8
    )
    
    elements = []
    
    # ENCABEZADO
    elements.append(Paragraph("SICONE - Inversiones Temporales", style_title))
    elements.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", style_subtitle))
    elements.append(Spacer(1, 0.15*inch))
    
    # RESUMEN EJECUTIVO
    resumen = datos.get('resumen', {})
    resumen_data = [
        ['Total Invertido', 'Retorno Neto Total', 'Descuentos Totales', 'Plazo Promedio'],
        [
            formatear_moneda(resumen.get('total_invertido', 0)),
            formatear_moneda(resumen.get('retorno_neto_total', 0)),
            formatear_moneda(resumen.get('descuentos_totales', 0)),
            f"{resumen.get('plazo_promedio', 0):.0f} días"
        ]
    ]
    
    tabla_resumen = Table(resumen_data, colWidths=[1.8*inch]*4)
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e0f2fe')),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, 1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    elements.append(tabla_resumen)
    elements.append(Spacer(1, 0.15*inch))
    
    # GRÁFICOS
    liquidez = datos.get('liquidez', {})
    inversiones = datos.get('inversiones', [])
    
    gauge_buf = generar_gauge_liquidez(
        liquidez.get('liquidez_post', 0),
        liquidez.get('margen_total', 0),
        liquidez.get('ratio', 0),
        liquidez.get('estado', 'N/A')
    )
    
    pie_buf = generar_pie_portafolio(inversiones)
    
    graficos_data = []
    fila_graficos = []
    
    if gauge_buf:
        gauge_img = Image(gauge_buf, width=2.5*inch, height=1.8*inch)
        fila_graficos.append(gauge_img)
    else:
        fila_graficos.append(Paragraph("Gauge no disponible", styles['Normal']))
    
    if pie_buf:
        pie_img = Image(pie_buf, width=2.5*inch, height=2.5*inch)
        fila_graficos.append(pie_img)
    else:
        fila_graficos.append(Paragraph("Pie no disponible", styles['Normal']))
    
    graficos_data.append(fila_graficos)
    
    tabla_graficos = Table(graficos_data, colWidths=[3.6*inch, 3.6*inch])
    tabla_graficos.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(tabla_graficos)
    elements.append(Spacer(1, 0.1*inch))
    
    # TABLA DE INVERSIONES
    elements.append(Paragraph("Detalle de Inversiones", style_section))
    
    inversiones_data = [
        ['Instrumento', 'Monto', 'Plazo', 'Retorno Neto', 'Vencimiento']
    ]
    
    for inv in inversiones[:5]:
        # Parsear fecha correctamente (puede venir como string desde JSON)
        fecha_venc = parsear_fecha(inv.get('fecha_vencimiento'))
        
        inversiones_data.append([
            inv.get('instrumento', 'N/A'),
            formatear_moneda(inv.get('monto', 0)),
            f"{inv.get('plazo_dias', 0)}d",
            formatear_moneda(inv.get('retorno_neto', 0)),
            fecha_venc.strftime('%d/%m/%Y')
        ])
    
    tabla_inversiones = Table(inversiones_data, colWidths=[1.5*inch, 1.3*inch, 0.9*inch, 1.3*inch, 1.3*inch])
    tabla_inversiones.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f9ff')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    elements.append(tabla_inversiones)
    elements.append(Spacer(1, 0.1*inch))
    
    # TIMELINE
    timeline_buf = generar_timeline_vencimientos(inversiones, date.today())
    
    if timeline_buf:
        timeline_img = Image(timeline_buf, width=7*inch, height=1.8*inch)
        elements.append(timeline_img)
        elements.append(Spacer(1, 0.1*inch))
    
    # ALERTAS
    alertas = datos.get('alertas', [])
    
    if alertas:
        elements.append(Paragraph("Alertas", style_section))
        
        for alerta in alertas[:3]:
            elements.append(Paragraph(
                f"• {alerta}",
                ParagraphStyle('AlertText', parent=styles['Normal'],
                             fontSize=8, leftIndent=10, spaceAfter=3)
            ))
    
    # FOOTER
    elements.append(Spacer(1, 0.1*inch))
    footer_text = f"SICONE | {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    elements.append(Paragraph(
        footer_text,
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7,
                      textColor=colors.gray, alignment=TA_CENTER)
    ))
    
    doc.build(elements)
    
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================================
# FUNCIÓN AUXILIAR PARA RECONSTRUIR DATAFRAME DESDE JSON
# ============================================================================

def reconstruir_dataframe_desde_json(json_data: Dict, fecha_inicio=None, fecha_fin=None) -> Optional[pd.DataFrame]:
    """
    Reconstruye DataFrame consolidado desde JSON para generar gráficos
    (Usado internamente por reporte multiproyecto)
    
    Args:
        json_data: Diccionario con datos del JSON
        fecha_inicio: Fecha inicio para filtrar (opcional)
        fecha_fin: Fecha fin para filtrar (opcional)
    
    Returns:
        DataFrame con datos consolidados, filtrado por fechas si se especifica
    """
    try:
        df_data = json_data.get('df_consolidado')
        
        if not df_data or not df_data.get('semanas'):
            return None
        
        df = pd.DataFrame({
            'semana_consolidada': df_data.get('semanas', []),
            'fecha': pd.to_datetime(df_data.get('fechas', [])),
            'saldo_consolidado': df_data.get('saldo_consolidado', []),
            'ingresos_proy_total': df_data.get('ingresos_proy_total', []),
            'egresos_proy_total': df_data.get('egresos_proy_total', []),
            'es_historica': df_data.get('es_historica', []),
            'burn_rate': df_data.get('burn_rate', [])
        })
        
        # Aplicar filtros de fecha si se especificaron
        if fecha_inicio is not None:
            fecha_inicio_dt = pd.to_datetime(fecha_inicio)
            df = df[df['fecha'] >= fecha_inicio_dt]
        
        if fecha_fin is not None:
            fecha_fin_dt = pd.to_datetime(fecha_fin)
            df = df[df['fecha'] <= fecha_fin_dt]
        
        return df
        
    except Exception as e:
        try:
            import streamlit as st_local
            st_local.warning(f"⚠️ No se pudo reconstruir DataFrame: {str(e)}")
        except:
            pass
        return None


# ============================================================================
# MAIN PARA TESTING
# ============================================================================

if __name__ == "__main__":
    pass
    # DEBUG: print("SICONE - Módulo de Reportes Ejecutivos Unificado v3.0.0")
    # DEBUG: print("=" * 60)
    # DEBUG: print("\nFUNCIONES DISPONIBLES:")
    # DEBUG: print("1. generar_reporte_gerencial_pdf(datos)")
    # DEBUG: print("2. generar_reporte_inversiones_pdf(datos)")
    # DEBUG: print("\nMódulo listo para importar")


# ============================================================================
# INTERFAZ STREAMLIT - MÓDULO DE REPORTES
# ============================================================================

def main():
    """
    Función principal del módulo de reportes (interfaz Streamlit)
    """
    import streamlit as st
    import json
    
    st.title("📊 Reportes Ejecutivos")
    st.markdown("---")
    
    # ========================================================================
    # TABS: Desde Consolidado / Desde JSON
    # ========================================================================
    
    tab1, tab2 = st.tabs(["📈 Desde Datos Consolidados", "📁 Desde Archivo JSON"])
    
    # ========================================================================
    # TAB 1: GENERAR DESDE DATOS CONSOLIDADOS
    # ========================================================================
    
    with tab1:
        st.markdown("### Generar Reporte desde Multiproyecto Activo")
        
        # Verificar qué datos hay disponibles
        tiene_multiproyecto = 'datos_reportes' in st.session_state
        tiene_inversiones = 'datos_inversiones' in st.session_state
        
        if not tiene_multiproyecto and not tiene_inversiones:
            st.warning("⚠️ No hay datos consolidados disponibles")
            st.info("👉 Ve al módulo **Multiproyecto** y consolida los proyectos primero")
            
            if st.button("🔙 Ir a Multiproyecto"):
                st.session_state.modulo_actual = 'multiproyecto'
                st.rerun()
        
        else:
            # Selector de tipo de reporte
            opciones = []
            indices_disabled = []
            
            if tiene_multiproyecto:
                opciones.append("📊 Reporte Gerencial Multiproyecto")
            else:
                opciones.append("📊 Reporte Gerencial Multiproyecto (sin datos)")
                indices_disabled.append(0)
            
            if tiene_inversiones:
                opciones.append("💰 Reporte Inversiones Temporales")
            else:
                opciones.append("💰 Reporte Inversiones Temporales (sin datos)")
                if len(opciones) == 2:
                    indices_disabled.append(1)
            
            # Radio selector
            tipo_reporte = st.radio(
                "Selecciona tipo de reporte:",
                opciones,
                help="Genera el reporte según los datos disponibles en session_state"
            )
            
            st.markdown("---")
            
            # ================================================================
            # OPCIÓN A: REPORTE GERENCIAL
            # ================================================================
            
            if "Gerencial" in tipo_reporte and tiene_multiproyecto:
                datos = st.session_state.datos_reportes
                timestamp = parsear_timestamp(datos.get('timestamp', datetime.now()))
                
                # Mostrar info de datos
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Fecha de Datos", timestamp.strftime('%d/%m/%Y %H:%M'))
                with col2:
                    edad_minutos = (datetime.now() - timestamp).total_seconds() / 60
                    if edad_minutos < 5:
                        st.success(f"✅ Actualizado hace {edad_minutos:.0f} minutos")
                    else:
                        st.warning(f"⚠️ Datos con {edad_minutos:.0f} minutos de antigüedad")
                
                st.markdown("---")
                
                # Resumen de datos
                estado = datos.get('estado_caja', {})
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    saldo = estado.get('saldo_total', 0)
                    st.metric("Saldo Total", f"${saldo/1_000_000:.1f}M")
                with col2:
                    burn_rate = estado.get('burn_rate', 0)
                    st.metric("Burn Rate", f"${burn_rate/1_000_000:.1f}M/semana")
                with col3:
                    proyectos = estado.get('total_proyectos', 0)
                    st.metric("Proyectos", proyectos)
                
                st.markdown("---")
                
                # ================================================================
                # SELECTOR DE PERÍODO (FILTRO DE FECHAS) - MULTIPROYECTO ACTIVO
                # ================================================================
                
                st.subheader("📅 Período del Reporte")
                
                # Obtener rango de fechas disponibles del DataFrame
                df_consolidado = datos.get('df_consolidado')
                if df_consolidado is not None and not df_consolidado.empty:
                    fecha_min = df_consolidado['fecha'].min().date()
                    fecha_max = df_consolidado['fecha'].max().date()
                    
                    st.caption(f"📊 Datos disponibles: {fecha_min.strftime('%d/%m/%Y')} - {fecha_max.strftime('%d/%m/%Y')}")
                else:
                    fecha_min = None
                    fecha_max = None
                
                # Opciones de período
                tipo_periodo = st.radio(
                    "Selecciona el rango temporal:",
                    [
                        "📊 Ver Todo (Sin filtro)",
                        "📅 Rango Personalizado",
                        "⏮️ Últimas 12 semanas",
                        "⏮️ Últimas 26 semanas (6 meses)",
                        "▶️ Solo Históricas (hasta hoy)",
                        "▶️ Solo Proyectadas (desde hoy)"
                    ],
                    help="Filtra los datos del reporte por período de tiempo",
                    key="periodo_multiproyecto"
                )
                
                # Mensaje informativo sobre qué se filtra
                st.info("""
                ℹ️ **Nota sobre filtrado:**  
                • **Waterfall**: SÍ se filtra por el período seleccionado  
                • **Métricas del header**: SÍ se filtran (saldo total, burn rate)  
                • **Semáforo, Tabla, Pie**: NO se filtran (muestran totales completos del proyecto)  
                  
                *Razón técnica: No es posible mapear las semanas individuales de cada proyecto  
                con las semanas consolidadas globales sin información adicional.*
                """)
                
                # Variables para almacenar fechas de filtro
                fecha_inicio_filtro = None
                fecha_fin_filtro = None
                
                # Procesar según el tipo de período seleccionado
                if tipo_periodo == "📅 Rango Personalizado":
                    col1, col2 = st.columns(2)
                    with col1:
                        fecha_inicio_filtro = st.date_input(
                            "Fecha Inicio:",
                            value=fecha_min if fecha_min else date.today(),
                            min_value=fecha_min,
                            max_value=fecha_max,
                            help="Inicio del período a reportar",
                            key="fecha_inicio_multiproyecto"
                        )
                    with col2:
                        fecha_fin_filtro = st.date_input(
                            "Fecha Fin:",
                            value=fecha_max if fecha_max else date.today(),
                            min_value=fecha_min,
                            max_value=fecha_max,
                            help="Fin del período a reportar",
                            key="fecha_fin_multiproyecto"
                        )
                    
                    # Validación
                    if fecha_inicio_filtro and fecha_fin_filtro and fecha_inicio_filtro > fecha_fin_filtro:
                        st.error("⚠️ La fecha de inicio debe ser anterior a la fecha fin")
                
                elif tipo_periodo == "⏮️ Últimas 12 semanas":
                    fecha_fin_filtro = date.today()
                    fecha_inicio_filtro = fecha_fin_filtro - timedelta(weeks=12)
                    st.info(f"📊 Mostrando desde {fecha_inicio_filtro.strftime('%d/%m/%Y')} hasta {fecha_fin_filtro.strftime('%d/%m/%Y')}")
                
                elif tipo_periodo == "⏮️ Últimas 26 semanas (6 meses)":
                    fecha_fin_filtro = date.today()
                    fecha_inicio_filtro = fecha_fin_filtro - timedelta(weeks=26)
                    st.info(f"📊 Mostrando desde {fecha_inicio_filtro.strftime('%d/%m/%Y')} hasta {fecha_fin_filtro.strftime('%d/%m/%Y')}")
                
                elif tipo_periodo == "▶️ Solo Históricas (hasta hoy)":
                    fecha_inicio_filtro = fecha_min
                    fecha_fin_filtro = date.today()
                    st.info(f"📊 Mostrando datos históricos hasta hoy ({fecha_fin_filtro.strftime('%d/%m/%Y')})")
                
                elif tipo_periodo == "▶️ Solo Proyectadas (desde hoy)":
                    fecha_inicio_filtro = date.today()
                    fecha_fin_filtro = fecha_max
                    st.info(f"📊 Mostrando proyecciones desde hoy ({fecha_inicio_filtro.strftime('%d/%m/%Y')})")
                
                st.markdown("---")
                
                # Botón para generar reporte
                if st.button("📄 Generar Reporte PDF", type="primary", use_container_width=True):
                    with st.spinner("Generando reporte PDF..."):
                        try:
                            # Aplicar filtros si hay fechas seleccionadas
                            if fecha_inicio_filtro or fecha_fin_filtro:
                                # Clonar datos para no modificar session_state
                                datos_filtrados = copy.deepcopy(datos)
                                
                                # Filtrar DataFrame consolidado
                                if df_consolidado is not None and not df_consolidado.empty:
                                    df_filtrado = df_consolidado.copy()
                                    if fecha_inicio_filtro:
                                        df_filtrado = df_filtrado[df_filtrado['fecha'] >= pd.to_datetime(fecha_inicio_filtro)]
                                    if fecha_fin_filtro:
                                        df_filtrado = df_filtrado[df_filtrado['fecha'] <= pd.to_datetime(fecha_fin_filtro)]
                                    
                                    datos_filtrados['df_consolidado'] = df_filtrado
                                    
                                    # Filtrar proyectos y recalcular estado_caja
                                    proyectos_originales = datos.get('proyectos', [])
                                    gastos_fijos_mensuales = datos.get('gastos_fijos_mensuales', 50000000)
                                    
                                    proyectos_filtrados = filtrar_proyectos_por_fechas(
                                        proyectos_originales,
                                        df_filtrado,
                                        fecha_inicio_filtro,
                                        fecha_fin_filtro
                                    )
                                    
                                    estado_caja_filtrado = recalcular_estado_caja(
                                        proyectos_filtrados,
                                        gastos_fijos_mensuales
                                    )
                                    
                                    datos_filtrados['proyectos'] = proyectos_filtrados
                                    datos_filtrados['estado_caja'] = estado_caja_filtrado
                                    datos_filtrados['filtro_fecha_inicio'] = fecha_inicio_filtro
                                    datos_filtrados['filtro_fecha_fin'] = fecha_fin_filtro
                                    
                                    # DEBUG VISIBLE
                                    st.markdown("### 🐛 DEBUG - Datos Filtrados")
                                    st.write(f"**Proyectos filtrados:** {len(proyectos_filtrados)}")
                                    debug_data = []
                                    for i, p in enumerate(proyectos_filtrados[:6]):
                                        debug_data.append({
                                            '#': i + 1,
                                            'Proyecto': p.get('nombre', 'N/A')[:25],
                                            'Ejecutado (M)': f"${p.get('ejecutado', 0)/1_000_000:.1f}",
                                            'Saldo (M)': f"${p.get('saldo_real_tesoreria', 0)/1_000_000:.1f}",
                                            'Burn Rate (M)': f"${p.get('burn_rate_real', 0)/1_000_000:.2f}",
                                        })
                                    # pandas ya importado al inicio
                                    df_debug = pd.DataFrame(debug_data)
                                    st.dataframe(df_debug, use_container_width=True)
                                    
                                    datos_a_usar = datos_filtrados
                                else:
                                    datos_a_usar = datos
                            else:
                                datos_a_usar = datos
                            
                            # Generar PDF
                            pdf_bytes = generar_reporte_gerencial_pdf(datos_a_usar)
                            
                            # Ofrecer descarga
                            filename = f"Reporte_Gerencial_{timestamp.strftime('%Y%m%d_%H%M')}.pdf"
                            
                            st.success("✅ Reporte generado exitosamente")
                            
                            st.download_button(
                                label="💾 Descargar Reporte PDF",
                                data=pdf_bytes,
                                file_name=filename,
                                mime="application/pdf",
                                use_container_width=True
                            )
                            
                        except Exception as e:
                            st.error(f"❌ Error generando reporte: {str(e)}")
                            with st.expander("Ver detalles del error"):
                                import traceback
                                st.code(traceback.format_exc())
            
            # ================================================================
            # OPCIÓN B: REPORTE INVERSIONES
            # ================================================================
            
            elif "Inversiones" in tipo_reporte and tiene_inversiones:
                datos_inv = st.session_state.datos_inversiones
                timestamp = parsear_timestamp(datos_inv.get('timestamp', datetime.now()))
                
                # Mostrar info de datos
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Fecha de Datos", timestamp.strftime('%d/%m/%Y %H:%M'))
                with col2:
                    edad_minutos = (datetime.now() - timestamp).total_seconds() / 60
                    if edad_minutos < 5:
                        st.success(f"✅ Actualizado hace {edad_minutos:.0f} minutos")
                    else:
                        st.warning(f"⚠️ Datos con {edad_minutos:.0f} minutos de antigüedad")
                
                st.markdown("---")
                
                # Resumen de inversiones
                resumen = datos_inv.get('resumen', {})
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_inv = resumen.get('total_invertido', 0)
                    st.metric("Total Invertido", f"${total_inv/1_000_000:.1f}M")
                with col2:
                    retorno = resumen.get('retorno_neto_total', 0)
                    st.metric("Retorno Neto", f"${retorno/1_000_000:.2f}M")
                with col3:
                    plazo = resumen.get('plazo_promedio', 0)
                    st.metric("Plazo Promedio", f"{plazo:.0f} días")
                
                # Segunda fila
                col1, col2, col3 = st.columns(3)
                with col1:
                    liquidez = datos_inv.get('liquidez', {})
                    ratio = liquidez.get('ratio', 0)
                    st.metric("Ratio Liquidez", f"{ratio:.2f}x")
                with col2:
                    estado_liq = liquidez.get('estado', 'N/A')
                    color_estado = {
                        'ESTABLE': '🟢',
                        'PRECAUCIÓN': '🟡',
                        'CRÍTICO': '🔴'
                    }.get(estado_liq, '⚪')
                    st.metric("Estado", f"{color_estado} {estado_liq}")
                with col3:
                    num_inv = len(datos_inv.get('inversiones', []))
                    st.metric("Inversiones", num_inv)
                
                st.markdown("---")
                
                # Botón para generar reporte
                if st.button("📄 Generar Reporte PDF", type="primary", use_container_width=True):
                    with st.spinner("Generando reporte de inversiones..."):
                        try:
                            # Generar PDF
                            pdf_bytes = generar_reporte_inversiones_pdf(datos_inv)
                            
                            # Ofrecer descarga
                            filename = f"Inversiones_{timestamp.strftime('%Y%m%d_%H%M')}.pdf"
                            
                            st.success("✅ Reporte generado exitosamente")
                            
                            st.download_button(
                                label="💾 Descargar Reporte PDF",
                                data=pdf_bytes,
                                file_name=filename,
                                mime="application/pdf",
                                use_container_width=True
                            )
                            
                        except Exception as e:
                            st.error(f"❌ Error generando reporte: {str(e)}")
                            with st.expander("Ver detalles del error"):
                                import traceback
                                st.code(traceback.format_exc())
    
    # ========================================================================
    # TAB 2: GENERAR DESDE JSON
    # ========================================================================
    
    with tab2:
        st.markdown("### Generar Reporte desde Archivo JSON")
        st.caption("Carga un archivo JSON exportado desde Multiproyecto")
        
        # Upload de archivo
        uploaded_file = st.file_uploader(
            "Selecciona archivo JSON",
            type=['json'],
            help="Sube un JSON exportado desde el módulo Multiproyecto"
        )
        
        if uploaded_file is not None:
            try:
                # Leer JSON
                json_data = json.load(uploaded_file)
                
                # Verificar qué datos contiene el JSON
                tiene_multiproyecto_json = 'estado_caja' in json_data and 'proyectos' in json_data
                tiene_inversiones_json = 'inversiones_temporales' in json_data and json_data['inversiones_temporales'] is not None
                
                if not tiene_multiproyecto_json and not tiene_inversiones_json:
                    st.error("❌ El JSON no contiene datos válidos para generar reportes")
                    st.info("El JSON debe contener 'estado_caja' y 'proyectos' o 'inversiones_temporales'")
                else:
                    # Mostrar info del JSON
                    metadata = json_data.get('metadata', {})
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        version = metadata.get('version', 'N/A')
                        st.metric("Versión JSON", version)
                    with col2:
                        # Intentar ambos nombres (exportación o generación)
                        fecha_export = metadata.get('fecha_exportacion') or metadata.get('fecha_generacion', 'N/A')
                        st.metric("Fecha Export", fecha_export[:10] if len(fecha_export) > 10 else fecha_export)
                    with col3:
                        proyectos_json = len(json_data.get('proyectos', []))
                        st.metric("Proyectos", proyectos_json)
                    
                    # Segunda fila con más métricas
                    if tiene_multiproyecto_json:
                        estado_caja = json_data.get('estado_caja', {})
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            saldo = estado_caja.get('saldo_total', 0)
                            st.metric("Saldo Total", f"${saldo/1_000_000:.1f}M")
                        with col2:
                            burn_rate = estado_caja.get('burn_rate', 0)
                            st.metric("Burn Rate", f"${burn_rate/1_000_000:.1f}M/semana")
                        with col3:
                            margen = estado_caja.get('margen_proteccion', 0)
                            st.metric("Margen Protección", f"${margen/1_000_000:.1f}M")
                    
                    st.markdown("---")
                    
                    # Selector de tipo de reporte
                    opciones = []
                    
                    if tiene_multiproyecto_json:
                        opciones.append("📊 Reporte Gerencial Multiproyecto")
                    else:
                        opciones.append("📊 Reporte Gerencial Multiproyecto (sin datos)")
                    
                    if tiene_inversiones_json:
                        opciones.append("💰 Reporte Inversiones Temporales")
                    else:
                        opciones.append("💰 Reporte Inversiones Temporales (sin datos)")
                    
                    tipo_reporte = st.radio(
                        "Selecciona tipo de reporte:",
                        opciones,
                        help="Genera el reporte según los datos disponibles en el JSON"
                    )
                    
                    st.markdown("---")
                    
                    # ============================================================
                    # SELECTOR DE PERÍODO (FILTRO DE FECHAS)
                    # ============================================================
                    
                    if "Gerencial" in tipo_reporte and tiene_multiproyecto_json:
                        st.subheader("📅 Período del Reporte")
                        
                        # Obtener rango de fechas disponibles del JSON
                        df_data = json_data.get('df_consolidado', {})
                        fechas_disponibles = df_data.get('fechas', [])
                        
                        if fechas_disponibles:
                            fecha_min = pd.to_datetime(fechas_disponibles[0]).date()
                            fecha_max = pd.to_datetime(fechas_disponibles[-1]).date()
                            
                            st.caption(f"📊 Datos disponibles: {fecha_min.strftime('%d/%m/%Y')} - {fecha_max.strftime('%d/%m/%Y')}")
                        else:
                            fecha_min = None
                            fecha_max = None
                        
                        # Opciones de período
                        tipo_periodo = st.radio(
                            "Selecciona el rango temporal:",
                            [
                                "📊 Ver Todo (Sin filtro)",
                                "📅 Rango Personalizado",
                                "⏮️ Últimas 12 semanas",
                                "⏮️ Últimas 26 semanas (6 meses)",
                                "▶️ Solo Históricas (hasta hoy)",
                                "▶️ Solo Proyectadas (desde hoy)"
                            ],
                            help="Filtra los datos del reporte por período de tiempo"
                        )
                        
                        # Variables para almacenar fechas de filtro
                        fecha_inicio_filtro = None
                        fecha_fin_filtro = None
                        
                        # Procesar según el tipo de período seleccionado
                        if tipo_periodo == "📅 Rango Personalizado":
                            col1, col2 = st.columns(2)
                            with col1:
                                fecha_inicio_filtro = st.date_input(
                                    "Fecha Inicio:",
                                    value=fecha_min if fecha_min else date.today(),
                                    min_value=fecha_min,
                                    max_value=fecha_max,
                                    help="Inicio del período a reportar"
                                )
                            with col2:
                                fecha_fin_filtro = st.date_input(
                                    "Fecha Fin:",
                                    value=fecha_max if fecha_max else date.today(),
                                    min_value=fecha_min,
                                    max_value=fecha_max,
                                    help="Fin del período a reportar"
                                )
                            
                            # Validación
                            if fecha_inicio_filtro and fecha_fin_filtro and fecha_inicio_filtro > fecha_fin_filtro:
                                st.error("⚠️ La fecha de inicio debe ser anterior a la fecha fin")
                        
                        elif tipo_periodo == "⏮️ Últimas 12 semanas":
                            fecha_fin_filtro = date.today()
                            fecha_inicio_filtro = fecha_fin_filtro - timedelta(weeks=12)
                            st.info(f"📊 Mostrando desde {fecha_inicio_filtro.strftime('%d/%m/%Y')} hasta {fecha_fin_filtro.strftime('%d/%m/%Y')}")
                        
                        elif tipo_periodo == "⏮️ Últimas 26 semanas (6 meses)":
                            fecha_fin_filtro = date.today()
                            fecha_inicio_filtro = fecha_fin_filtro - timedelta(weeks=26)
                            st.info(f"📊 Mostrando desde {fecha_inicio_filtro.strftime('%d/%m/%Y')} hasta {fecha_fin_filtro.strftime('%d/%m/%Y')}")
                        
                        elif tipo_periodo == "▶️ Solo Históricas (hasta hoy)":
                            fecha_inicio_filtro = fecha_min
                            fecha_fin_filtro = date.today()
                            st.info(f"📊 Mostrando datos históricos hasta hoy ({fecha_fin_filtro.strftime('%d/%m/%Y')})")
                        
                        elif tipo_periodo == "▶️ Solo Proyectadas (desde hoy)":
                            fecha_inicio_filtro = date.today()
                            fecha_fin_filtro = fecha_max
                            st.info(f"📊 Mostrando proyecciones desde hoy ({fecha_inicio_filtro.strftime('%d/%m/%Y')})")
                        
                        # Opción "Ver Todo" no establece filtros (None, None)
                        
                        st.markdown("---")
                    
                    # ============================================================
                    # OPCIÓN A: REPORTE GERENCIAL DESDE JSON
                    # ============================================================
                    
                    if "Gerencial" in tipo_reporte and tiene_multiproyecto_json:
                        # Convertir JSON a formato de datos con filtros de fecha
                        datos_desde_json = convertir_json_a_datos(
                            json_data, 
                            fecha_inicio=fecha_inicio_filtro,
                            fecha_fin=fecha_fin_filtro
                        )
                        
                        # ============================================================
                        # DEBUG VISIBLE EN UI
                        # ============================================================
                        if fecha_inicio_filtro or fecha_fin_filtro:
                            with st.expander("🐛 DEBUG - Info de Filtrado", expanded=True):
                                st.markdown("### Filtros Aplicados")
                                st.write(f"**Fecha Inicio:** {fecha_inicio_filtro}")
                                st.write(f"**Fecha Fin:** {fecha_fin_filtro}")
                                
                                st.markdown("### Proyectos Procesados")
                                proyectos_debug = datos_desde_json.get('proyectos', [])
                                st.write(f"**Total proyectos:** {len(proyectos_debug)}")
                                
                                if proyectos_debug:
                                    debug_data = []
                                    for i, p in enumerate(proyectos_debug[:6]):  # Mostrar todos
                                        debug_data.append({
                                            '#': i + 1,
                                            'Proyecto': p.get('nombre', 'N/A')[:25],
                                            'Ejecutado (M)': f"${p.get('ejecutado', 0)/1_000_000:.1f}",
                                            'Saldo (M)': f"${p.get('saldo_real_tesoreria', 0)/1_000_000:.1f}",
                                            'Burn Rate (M)': f"${p.get('burn_rate_real', 0)/1_000_000:.2f}",
                                            'Semanas': len(p.get('ejecucion_financiera', []))
                                        })
                                    
                                    # pandas ya importado al inicio
                                    df_debug = pd.DataFrame(debug_data)
                                    st.dataframe(df_debug, use_container_width=True)
                                    
                                    st.markdown("### Estado Consolidado")
                                    estado = datos_desde_json.get('estado_caja', {})
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("Saldo Total", f"${estado.get('saldo_total', 0)/1_000_000:.1f}M")
                                    with col2:
                                        st.metric("Burn Rate", f"${estado.get('burn_rate', 0)/1_000_000:.2f}M/sem")
                                    with col3:
                                        st.metric("Proyectos Activos", estado.get('proyectos_activos', 0))
                        
                        # Botón para generar
                        if st.button("📄 Generar Reporte desde JSON", type="primary", use_container_width=True):
                            with st.spinner("Generando reporte PDF desde JSON..."):
                                try:
                                    # Generar PDF
                                    pdf_bytes = generar_reporte_gerencial_pdf(datos_desde_json)
                                    
                                    # Ofrecer descarga
                                    fecha_str = metadata.get('fecha_exportacion') or metadata.get('fecha_generacion', datetime.now().isoformat())
                                    timestamp_str = fecha_str[:19].replace(':', '').replace('-', '')
                                    filename = f"Reporte_JSON_{timestamp_str}.pdf"
                                    
                                    st.success("✅ Reporte generado exitosamente desde JSON")
                                    
                                    st.download_button(
                                        label="💾 Descargar Reporte PDF",
                                        data=pdf_bytes,
                                        file_name=filename,
                                        mime="application/pdf",
                                        use_container_width=True
                                    )
                                    
                                except Exception as e:
                                    st.error(f"❌ Error generando reporte: {str(e)}")
                                    with st.expander("Ver detalles del error"):
                                        import traceback
                                        st.code(traceback.format_exc())
                    
                    # ============================================================
                    # OPCIÓN B: REPORTE INVERSIONES DESDE JSON
                    # ============================================================
                    
                    elif "Inversiones" in tipo_reporte and tiene_inversiones_json:
                        datos_inv_json = json_data['inversiones_temporales']
                        
                        # Mostrar resumen
                        resumen = datos_inv_json.get('resumen', {})
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            total_inv = resumen.get('total_invertido', 0)
                            st.metric("Total Invertido", f"${total_inv/1_000_000:.1f}M")
                        with col2:
                            retorno = resumen.get('retorno_neto_total', 0)
                            st.metric("Retorno Neto", f"${retorno/1_000_000:.2f}M")
                        with col3:
                            plazo = resumen.get('plazo_promedio', 0)
                            st.metric("Plazo Promedio", f"{plazo:.0f} días")
                        
                        st.markdown("---")
                        
                        # Botón para generar
                        if st.button("📄 Generar Reporte desde JSON", type="primary", use_container_width=True):
                            with st.spinner("Generando reporte de inversiones desde JSON..."):
                                try:
                                    # Generar PDF
                                    pdf_bytes = generar_reporte_inversiones_pdf(datos_inv_json)
                                    
                                    # Ofrecer descarga
                                    fecha_str = metadata.get('fecha_exportacion') or metadata.get('fecha_generacion', datetime.now().isoformat())
                                    timestamp_str = fecha_str[:19].replace(':', '').replace('-', '')
                                    filename = f"Inversiones_JSON_{timestamp_str}.pdf"
                                    
                                    st.success("✅ Reporte de inversiones generado exitosamente desde JSON")
                                    
                                    st.download_button(
                                        label="💾 Descargar Reporte PDF",
                                        data=pdf_bytes,
                                        file_name=filename,
                                        mime="application/pdf",
                                        use_container_width=True
                                    )
                                    
                                except Exception as e:
                                    st.error(f"❌ Error generando reporte: {str(e)}")
                                    with st.expander("Ver detalles del error"):
                                        import traceback
                                        st.code(traceback.format_exc())
                
            except json.JSONDecodeError:
                st.error("❌ Error: El archivo no es un JSON válido")
            except Exception as e:
                st.error(f"❌ Error procesando archivo: {str(e)}")
        
        else:
            st.info("👆 Sube un archivo JSON para comenzar")


# ============================================================================
# FUNCIONES DE FILTRADO POR FECHAS
# ============================================================================

def filtrar_proyectos_por_fechas(proyectos: List[Dict], df_consolidado: pd.DataFrame, fecha_inicio=None, fecha_fin=None) -> List[Dict]:
    """
    LIMITACIÓN TÉCNICA: Esta función NO puede filtrar proyectos individuales.
    
    PROBLEMA:
    - ejecucion_financiera tiene números de semana del proyecto (1,2,3...)
    - df_consolidado tiene semana_consolidada global (números diferentes)
    - No existe mapeo entre ambos → imposible filtrar correctamente
    
    RESULTADO:
    - Waterfall SÍ se filtra (usa df_consolidado)
    - Métricas header SÍ se filtran (recalculadas desde df_consolidado)
    - Semáforo, Tabla, Pie NO se filtran (muestran totales del proyecto)
    """
    return proyectos



def recalcular_estado_caja(proyectos_filtrados: List[Dict], gastos_fijos_mensuales: float) -> Dict:
    """
    Recalcula el estado de caja consolidado basado en proyectos filtrados
    
    Args:
        proyectos_filtrados: Lista de proyectos con métricas recalculadas
        gastos_fijos_mensuales: Gastos fijos mensuales de la empresa
    
    Returns:
        Diccionario con estado_caja recalculado
    """
    # Sumar saldos y burn rates de todos los proyectos
    saldo_total = sum(p.get('saldo_real_tesoreria', 0) for p in proyectos_filtrados)
    burn_rate_proyectos = sum(p.get('burn_rate_real', 0) for p in proyectos_filtrados)
    
    # Gastos fijos semanales
    gastos_fijos_semanales = gastos_fijos_mensuales / 4.33
    
    # Burn rate total
    burn_rate_total = burn_rate_proyectos + gastos_fijos_semanales
    
    # Margen de protección (8 semanas por defecto)
    margen_proteccion = burn_rate_total * 8
    
    # Excedente invertible
    excedente_invertible = max(0, saldo_total - margen_proteccion)
    
    # Estado general
    if saldo_total > margen_proteccion:
        estado_general = "EXCEDENTE"
    elif saldo_total > margen_proteccion * 0.5:
        estado_general = "SALUDABLE"
    else:
        estado_general = "ALERTA"
    
    # Proyectos activos (con saldo > 0)
    proyectos_activos = sum(1 for p in proyectos_filtrados if p.get('saldo_real_tesoreria', 0) > 0)
    
    return {
        'saldo_total': saldo_total,
        'burn_rate': burn_rate_total,
        'burn_rate_proyectos': burn_rate_proyectos,
        'gastos_fijos_semanales': gastos_fijos_semanales,
        'margen_proteccion': margen_proteccion,
        'excedente_invertible': excedente_invertible,
        'estado_general': estado_general,
        'proyectos_activos': proyectos_activos,
        'proyectos_terminados': 0,
        'total_proyectos': len(proyectos_filtrados)
    }


def convertir_json_a_datos(json_data: Dict, fecha_inicio=None, fecha_fin=None) -> Dict:
    """
    Convierte JSON exportado al formato esperado por generar_reporte_gerencial_pdf
    
    Args:
        json_data: Diccionario con datos del JSON consolidado
        fecha_inicio: Fecha inicio para filtrar (opcional)
        fecha_fin: Fecha fin para filtrar (opcional)
    
    Returns:
        Diccionario con datos procesados y filtrados
    """
    # DEBUG: print(f"\n{'='*80}")
    # DEBUG: print(f"🔄 DEBUG convertir_json_a_datos:")
    # DEBUG: print(f"  - fecha_inicio: {fecha_inicio}")
    # DEBUG: print(f"  - fecha_fin: {fecha_fin}")
    # DEBUG: print(f"{'='*80}")
    
    metadata = json_data.get('metadata', {})
    estado_caja_original = json_data.get('estado_caja', {})
    proyectos_originales = json_data.get('proyectos', [])
    gastos_fijos_mensuales = metadata.get('gastos_fijos_mensuales', 50000000)
    
    # DEBUG: print(f"  - Num proyectos originales: {len(proyectos_originales)}")
    for i, p in enumerate(proyectos_originales[:2]):
        print(f"    ORIGINAL [{i}] {p.get('nombre')}: ejecutado=${p.get('ejecutado', 0)/1_000_000:.1f}M")
    
    # Reconstruir DataFrame si está disponible, aplicando filtros de fecha
    df_consolidado = None
    if 'df_consolidado' in json_data:
        df_consolidado = reconstruir_dataframe_desde_json(
            json_data, 
            fecha_inicio=fecha_inicio, 
            fecha_fin=fecha_fin
        )
    
    # Aplicar filtrado de proyectos y recalcular estado_caja si hay filtros activos
    if fecha_inicio or fecha_fin:
        print(f"  ✅ HAY FILTROS - Aplicando filtrado...")
        # Filtrar proyectos por fechas
        proyectos_filtrados = filtrar_proyectos_por_fechas(
            proyectos_originales, 
            df_consolidado, 
            fecha_inicio, 
            fecha_fin
        )
        
        print(f"\n  - Num proyectos filtrados: {len(proyectos_filtrados)}")
        for i, p in enumerate(proyectos_filtrados[:2]):
            print(f"    FILTRADO [{i}] {p.get('nombre')}: ejecutado=${p.get('ejecutado', 0)/1_000_000:.1f}M, burn_rate=${p.get('burn_rate_real', 0)/1_000_000:.2f}M")
        
        # Recalcular estado de caja con proyectos filtrados
        estado_caja = recalcular_estado_caja(proyectos_filtrados, gastos_fijos_mensuales)
        proyectos = proyectos_filtrados
    else:
        print(f"  ⚠️ SIN FILTROS - Usando datos originales")
        # Sin filtros, usar datos originales
        estado_caja = estado_caja_original
        proyectos = proyectos_originales
    
    # Parsear timestamp (intentar exportacion o generacion)
    fecha_str = metadata.get('fecha_exportacion') or metadata.get('fecha_generacion', datetime.now().isoformat())
    try:
        timestamp = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
    except:
        timestamp = datetime.now()
    
    # Construir estructura de datos
    datos = {
        'timestamp': timestamp,
        'semana_actual': metadata.get('semana_actual', 0),  # ✅ FIX: Leer desde metadata
        'gastos_fijos_mensuales': gastos_fijos_mensuales,  # ✅ FIX: Leer desde metadata, no raíz
        'df_consolidado': df_consolidado,
        'estado_caja': estado_caja,
        'proyectos': proyectos,
        # Agregar información de filtros aplicados
        'filtro_fecha_inicio': fecha_inicio,
        'filtro_fecha_fin': fecha_fin
    }
    
    return datos
