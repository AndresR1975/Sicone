"""
SICONE - Módulo de Reportes Ejecutivos
Generación de reportes PDF para multiproyecto e inversiones temporales

Versión: 3.0.0 FINAL
Fecha: 29 Diciembre 2024
Autor: AI-MindNovation

REPORTES DISPONIBLES:
1. generar_reporte_gerencial_pdf(datos) - Reporte Gerencial Multiproyecto
2. generar_reporte_inversiones_pdf(datos) - Reporte Inversiones Temporales

CHANGELOG:
v3.0.0 (29-Dic-2024) - UNIFICACIÓN COMPLETA:
- ✅ Integración de reportes multiproyecto e inversiones en un solo módulo
- ✅ Funciones comunes optimizadas (formatear_moneda, estilos, etc.)
- ✅ Mejor organización en secciones claramente delimitadas
- ✅ Imports compartidos, código DRY
- ✅ Soporte para ambos tipos de reporte desde una sola importación

USO:
    from reportes_ejecutivos import generar_reporte_gerencial_pdf, generar_reporte_inversiones_pdf
"""

import io
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
    Genera gráfico Waterfall mostrando evolución del saldo en últimas 6 semanas
    (Usado en reporte multiproyecto)
    """
    try:
        # Obtener DataFrame consolidado
        df = datos.get('df_consolidado')
        
        if df is None or df.empty:
            return None
        
        if 'saldo_consolidado' not in df.columns:
            return None
        
        # Semana actual
        semana_actual = datos.get('semana_actual', 0)
        gastos_fijos_semanales = datos.get('gastos_fijos_mensuales', 0) / 4.33
        
        if semana_actual == 0:
            return None
        
        # Filtrar últimas 6 semanas históricas
        df_hist = df[
            (df['semana_consolidada'] >= semana_actual - 5) &
            (df['semana_consolidada'] <= semana_actual) &
            (df['es_historica'] == True)
        ].copy()
        
        if df_hist.empty or len(df_hist) < 2:
            return None
        
        # Calcular valores
        saldo_inicio = df_hist.iloc[0]['saldo_consolidado']
        saldo_final = df_hist.iloc[-1]['saldo_consolidado']
        
        # Flujos acumulados en el período
        ingresos_acum = df_hist['ingresos_proy_total'].sum() if 'ingresos_proy_total' in df_hist.columns else 0
        egresos_acum = df_hist['egresos_proy_total'].sum() if 'egresos_proy_total' in df_hist.columns else 0
        gastos_fijos_acum = gastos_fijos_semanales * len(df_hist)
        
        # Preparar datos para waterfall
        categorias = ['Inicio\n(Sem -6)', 'Ingresos', 'Egresos\nProyectos', 'Gastos\nFijos', 'Actual\n(Hoy)']
        
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
    (Usado en reporte multiproyecto)
    """
    try:
        proyectos = datos.get('proyectos', [])
        
        if not proyectos:
            return None
        
        # Consolidar categorías
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
        
        if not proyectos or len(proyectos) == 0:
            return None
        
        # Limitar a 5 proyectos
        proyectos_mostrar = proyectos[:5]
        
        fig, ax = plt.subplots(figsize=(5.5, 1.5))
        
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
        ax.set_title('Estado Financiero por Proyecto', fontsize=8, fontweight='bold', pad=4)
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
        
        plt.tight_layout(pad=0.2)
        
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
        fontSize=18,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    style_subtitle = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.gray,
        spaceAfter=6,
        alignment=TA_CENTER
    )
    
    elements = []
    
    # ENCABEZADO
    estado = datos['estado_caja']
    timestamp = datos['timestamp']
    
    elements.append(Paragraph("REPORTE GERENCIAL MULTIPROYECTO", style_title))
    elements.append(Paragraph(f"Generado: {timestamp.strftime('%d/%m/%Y %H:%M')}", style_subtitle))
    elements.append(Spacer(1, 0.2*inch))
    
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
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#60a5fa')),
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.whitesmoke),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 2), (-1, 2), 9),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e0f2fe')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#e0f2fe')),
        ('FONTNAME', (0, 1), (-1, 3), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, 3), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
    ]))
    
    elements.append(tabla_metricas)
    elements.append(Spacer(1, 0.15*inch))
    
    # GRÁFICOS
    waterfall_buf = generar_grafico_waterfall(datos)
    pie_buf = generar_grafico_pie_gastos(datos)
    
    graficos_data = []
    fila_graficos = []
    
    if waterfall_buf:
        waterfall_img = Image(waterfall_buf, width=2.8*inch, height=2.8*inch)
        fila_graficos.append(waterfall_img)
    else:
        fila_graficos.append(Paragraph("Waterfall no disponible", styles['Normal']))
    
    if pie_buf:
        pie_img = Image(pie_buf, width=2.8*inch, height=2.8*inch)
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
    elements.append(Spacer(1, 0.15*inch))
    
    # GRÁFICO SEMÁFORO
    semaforo_buf = generar_grafico_semaforo(datos)
    if semaforo_buf:
        semaforo_img = Image(semaforo_buf, width=5.5*inch, height=1.5*inch)
        elements.append(semaforo_img)
        elements.append(Spacer(1, 0.1*inch))
    
    # TABLA PROYECTOS
    elements.append(Paragraph("DETALLE POR PROYECTO", ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=6
    )))
    
    proyectos_data = [
        ['Proyecto', 'Ejecutado', 'Saldo', 'Burn Rate', 'Cobertura', '% Avance']
    ]
    
    proyectos = datos.get('proyectos', [])
    
    for p in proyectos[:5]:
        if UTILS_DISPONIBLE:
            nombre = obtener_valor_seguro(p, 'nombre', 'Sin nombre', str)[:30]
            ejecutado = obtener_valor_seguro(p, 'ejecutado', 0, float)
            saldo = obtener_valor_seguro(p, 'saldo_real_tesoreria', 0, float)
            burn_rate = obtener_valor_seguro(p, 'burn_rate_real', 0, float)
            avance_hitos = obtener_valor_seguro(p, 'avance_hitos_pct', 0, float)
            
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
    elements.append(Spacer(1, 0.1*inch))
    
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
    (Usado en reporte inversiones)
    """
    try:
        if not inversiones:
            return None
        
        fig, ax = plt.subplots(figsize=(5.5, 1.8))
        
        inversiones_sort = sorted(inversiones, key=lambda x: x.get('fecha_vencimiento', fecha_hoy))
        
        colores = ['#3b82f6', '#60a5fa', '#93c5fd']
        
        for idx, inv in enumerate(inversiones_sort[:3]):
            nombre = inv.get('nombre', f'Inversión {idx+1}')
            fecha_venc = inv.get('fecha_vencimiento', fecha_hoy)
            dias = (fecha_venc - fecha_hoy).days
            
            ax.barh(idx, dias, left=0, height=0.6, color=colores[idx % len(colores)],
                   edgecolor='white', linewidth=1.5)
            
            ax.text(dias / 2, idx, nombre, ha='center', va='center',
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
        inversiones_data.append([
            inv.get('instrumento', 'N/A'),
            formatear_moneda(inv.get('monto', 0)),
            f"{inv.get('plazo_dias', 0)}d",
            formatear_moneda(inv.get('retorno_neto', 0)),
            inv.get('fecha_vencimiento', date.today()).strftime('%d/%m/%Y')
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

def reconstruir_dataframe_desde_json(json_data: Dict) -> Optional[pd.DataFrame]:
    """
    Reconstruye DataFrame consolidado desde JSON para generar gráficos
    (Usado internamente por reporte multiproyecto)
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
    print("SICONE - Módulo de Reportes Ejecutivos Unificado v3.0.0")
    print("=" * 60)
    print("\nFUNCIONES DISPONIBLES:")
    print("1. generar_reporte_gerencial_pdf(datos)")
    print("2. generar_reporte_inversiones_pdf(datos)")
    print("\nMódulo listo para importar")


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
                timestamp = datos.get('timestamp', datetime.now())
                
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
                
                # Botón para generar reporte
                if st.button("📄 Generar Reporte PDF", type="primary", use_container_width=True):
                    with st.spinner("Generando reporte PDF..."):
                        try:
                            # Generar PDF
                            pdf_bytes = generar_reporte_gerencial_pdf(datos)
                            
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
                timestamp = datos_inv.get('timestamp', datetime.now())
                
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
                    # OPCIÓN A: REPORTE GERENCIAL DESDE JSON
                    # ============================================================
                    
                    if "Gerencial" in tipo_reporte and tiene_multiproyecto_json:
                        # Convertir JSON a formato de datos
                        datos_desde_json = convertir_json_a_datos(json_data)
                        
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


def convertir_json_a_datos(json_data: Dict) -> Dict:
    """
    Convierte JSON exportado al formato esperado por generar_reporte_gerencial_pdf
    """
    metadata = json_data.get('metadata', {})
    estado_caja = json_data.get('estado_caja', {})
    proyectos = json_data.get('proyectos', [])
    
    # Reconstruir DataFrame si está disponible
    df_consolidado = None
    if 'df_consolidado' in json_data:
        df_consolidado = reconstruir_dataframe_desde_json(json_data)
    
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
        'gastos_fijos_mensuales': json_data.get('gastos_fijos_mensuales', 50000000),
        'df_consolidado': df_consolidado,
        'estado_caja': estado_caja,
        'proyectos': proyectos
    }
    
    return datos
