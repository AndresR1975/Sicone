"""
SICONE - Módulo de Reportes Ejecutivos
Versión: 1.0.0 - Fase 1
Fecha: Diciembre 2024
Autor: Andrés Restrepo & Claude

Genera reportes ejecutivos en PDF con datos consolidados del módulo multiproyecto
"""

import streamlit as st
from datetime import datetime
import pandas as pd
from typing import Dict, List
import io

# Importar bibliotecas para PDF
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    PDF_DISPONIBLE = True
except ImportError:
    PDF_DISPONIBLE = False
    st.warning("⚠️ reportlab no está instalado. Instalando...")
    import subprocess
    subprocess.check_call(["pip", "install", "reportlab", "--break-system-packages"])
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    PDF_DISPONIBLE = True


# ============================================================================
# UTILIDADES
# ============================================================================

def formatear_moneda(valor):
    """Formatea valores monetarios"""
    if valor >= 1_000_000_000:
        return f"${valor/1_000_000_000:.2f}B"
    elif valor >= 1_000_000:
        return f"${valor/1_000_000:.1f}M"
    elif valor >= 1_000:
        return f"${valor/1_000:.0f}K"
    else:
        return f"${valor:,.0f}"


# ============================================================================
# GENERACIÓN DE REPORTE GERENCIAL
# ============================================================================

def generar_reporte_gerencial_pdf(datos: Dict) -> bytes:
    """
    Genera el Reporte Gerencial en PDF (1 página)
    
    Estructura según diseño de Andrés:
    - Encabezado: Fecha, Estado de caja, Margen, Cobertura, etc.
    - Cuerpo: Timeline, Semáforo, Comparación, Pie de gastos
    - Pie: Alertas relevantes
    """
    
    # Crear buffer de memoria para el PDF
    buffer = io.BytesIO()
    
    # Crear documento PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para título
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
    
    # Contenido del PDF
    elements = []
    
    # =================================================================
    # ENCABEZADO
    # =================================================================
    
    estado = datos['estado_caja']
    timestamp = datos['timestamp']
    
    # Título
    elements.append(Paragraph("REPORTE GERENCIAL MULTIPROYECTO", style_title))
    elements.append(Paragraph(
        f"Generado: {timestamp.strftime('%d/%m/%Y %H:%M')}",
        style_subtitle
    ))
    elements.append(Spacer(1, 0.2*inch))
    
    # Tabla de métricas clave
    cobertura = estado['saldo_total'] / estado['burn_rate'] if estado['burn_rate'] > 0 else 999
    
    metricas_data = [
        ['Fecha', 'Estado de Caja', 'Margen de Protección', 'Cobertura'],
        [
            timestamp.strftime('%d/%m/%Y'),
            formatear_moneda(estado['saldo_total']),
            formatear_moneda(estado['margen_proteccion']),
            f"{cobertura:.1f} semanas"
        ],
        ['Disponible Inversión', 'Burn Rate Semanal', 'Estado General', 'Proyectos Activos'],
        [
            formatear_moneda(estado.get('excedente_invertible', 0)),
            formatear_moneda(estado['burn_rate']),
            estado['estado_general'],
            f"{estado['proyectos_activos']}/{estado['total_proyectos']}"
        ]
    ]
    
    tabla_metricas = Table(metricas_data, colWidths=[1.8*inch, 1.8*inch, 1.8*inch, 1.8*inch])
    tabla_metricas.setStyle(TableStyle([
        # Encabezados
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        
        # Segunda fila de encabezados
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#60a5fa')),
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.whitesmoke),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 2), (-1, 2), 9),
        
        # Valores
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e0f2fe')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#e0f2fe')),
        ('FONTNAME', (0, 1), (-1, 3), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, 3), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(tabla_metricas)
    elements.append(Spacer(1, 0.3*inch))
    
    # =================================================================
    # CUERPO - INFORMACIÓN DE PROYECTOS
    # =================================================================
    
    elements.append(Paragraph("📊 Detalle de Proyectos", styles['Heading2']))
    elements.append(Spacer(1, 0.1*inch))
    
    # Tabla de proyectos
    proyectos_data = [['Proyecto', 'Estado', 'Presupuesto', 'Ejecutado', '% Avance', 'Saldo']]
    
    for proyecto in datos['proyectos']:
        presupuesto = proyecto.get('presupuesto_total', 0)
        ejecutado = proyecto.get('ejecutado', 0)
        avance = (ejecutado / presupuesto * 100) if presupuesto > 0 else 0
        saldo = proyecto.get('saldo_real_tesoreria', 0)
        
        proyectos_data.append([
            proyecto['nombre'][:20],  # Truncar nombre
            proyecto['estado'],
            formatear_moneda(presupuesto),
            formatear_moneda(ejecutado),
            f"{avance:.1f}%",
            formatear_moneda(saldo)
        ])
    
    tabla_proyectos = Table(proyectos_data, colWidths=[1.5*inch, 1*inch, 1.2*inch, 1.2*inch, 0.8*inch, 1.1*inch])
    tabla_proyectos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(tabla_proyectos)
    elements.append(Spacer(1, 0.3*inch))
    
    # =================================================================
    # ANÁLISIS DE COBERTURA
    # =================================================================
    
    elements.append(Paragraph("📈 Análisis de Cobertura", styles['Heading2']))
    elements.append(Spacer(1, 0.1*inch))
    
    # Determinar veces de cobertura
    if estado['margen_proteccion'] > 0:
        veces_cobertura = estado['saldo_total'] / estado['margen_proteccion']
    else:
        veces_cobertura = 999
    
    cobertura_data = [
        ['Concepto', 'Valor'],
        ['Burn Rate Proyectos', formatear_moneda(estado.get('burn_rate_proyectos', 0))],
        ['Gastos Fijos Semanales', formatear_moneda(estado.get('gastos_fijos_semanales', 0))],
        ['Burn Rate Total Semanal', formatear_moneda(estado['burn_rate'])],
        ['Margen Requerido (8 sem)', formatear_moneda(estado['margen_proteccion'])],
        ['Veces de Cobertura', f"{veces_cobertura:.2f}x"],
    ]
    
    tabla_cobertura = Table(cobertura_data, colWidths=[4*inch, 2.8*inch])
    tabla_cobertura.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fef3c7')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(tabla_cobertura)
    elements.append(Spacer(1, 0.3*inch))
    
    # =================================================================
    # PIE - ALERTAS Y RECOMENDACIONES
    # =================================================================
    
    elements.append(Paragraph("⚠️ Alertas y Recomendaciones", styles['Heading2']))
    elements.append(Spacer(1, 0.1*inch))
    
    # Generar alertas
    alertas = []
    
    if estado['estado_general'] == 'EXCEDENTE':
        alertas.append("✅ Liquidez suficiente para operación normal")
        alertas.append(f"✅ Excedente invertible de {formatear_moneda(estado.get('excedente_invertible', 0))}")
    elif estado['estado_general'] == 'AJUSTADO':
        alertas.append("🟡 Liquidez ajustada - Monitorear burn rate")
        alertas.append("🟡 Considerar optimización de gastos")
    else:
        alertas.append("🔴 CRÍTICO: Liquidez insuficiente")
        alertas.append("🔴 ACCIÓN INMEDIATA: Revisar proyección de ingresos")
    
    if cobertura < 12:
        alertas.append(f"⚠️ Cobertura de solo {cobertura:.1f} semanas (recomendado: 12+)")
    
    # Proyectos terminados
    if estado.get('proyectos_terminados', 0) > 0:
        alertas.append(f"ℹ️ {estado['proyectos_terminados']} proyecto(s) terminado(s)")
    
    # Crear lista de alertas
    alertas_text = "<br/>".join([f"• {alerta}" for alerta in alertas])
    
    style_alertas = ParagraphStyle(
        'Alertas',
        parent=styles['Normal'],
        fontSize=9,
        leading=14,
        leftIndent=10
    )
    
    elements.append(Paragraph(alertas_text, style_alertas))
    
    # =================================================================
    # FOOTER
    # =================================================================
    
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(
        f"_____<br/>Generado por SICONE - Sistema Integrado de Construcción Eficiente<br/>{timestamp.strftime('%d de %B de %Y, %H:%M')}",
        style_subtitle
    ))
    
    # Construir PDF
    doc.build(elements)
    
    # Obtener bytes del PDF
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
    """Función principal del módulo de reportes"""
    
    st.markdown("# 📊 Reportes Ejecutivos")
    st.caption("Genere reportes profesionales con los datos consolidados")
    
    # Verificar que existan datos
    if 'datos_reportes' not in st.session_state:
        st.warning("⚠️ No hay datos disponibles para generar reportes")
        st.info("📋 **Instrucciones:**\n"
                "1. Vaya al módulo **Análisis Multiproyecto**\n"
                "2. Cargue y consolide sus proyectos\n"
                "3. Regrese aquí para generar reportes")
        
        if st.button("🏢 Ir a Análisis Multiproyecto"):
            st.session_state.modulo_actual = 'multiproyecto'
            st.rerun()
        return
    
    # Cargar datos
    datos = st.session_state.datos_reportes
    
    # Mostrar información de los datos
    st.success(f"✅ Datos cargados correctamente")
    
    col_info1, col_info2, col_info3 = st.columns(3)
    
    with col_info1:
        edad = (datetime.now() - datos['timestamp']).total_seconds() / 60
        if edad < 1:
            st.metric("Actualización", "Reciente", delta="hace < 1 min")
        else:
            st.metric("Actualización", f"Hace {edad:.0f} min")
    
    with col_info2:
        st.metric("Proyectos", len(datos['proyectos']))
    
    with col_info3:
        estado = datos['estado_caja']['estado_general']
        color_map = {'EXCEDENTE': '🟢', 'AJUSTADO': '🟡', 'CRÍTICO': '🔴'}
        st.metric("Estado", f"{color_map.get(estado, '⚪')} {estado}")
    
    st.markdown("---")
    
    # Selector de tipo de reporte
    st.markdown("### 📄 Seleccione el tipo de reporte")
    
    col_tipo1, col_tipo2 = st.columns(2)
    
    with col_tipo1:
        st.markdown("""
        <div style="padding: 20px; border: 2px solid #3b82f6; border-radius: 10px; background-color: #eff6ff;">
            <h4 style="color: #1e40af;">📊 Reporte Gerencial</h4>
            <p style="color: #64748b;">Dashboard ejecutivo con métricas clave, estado de proyectos y alertas</p>
            <ul style="color: #64748b; font-size: 0.9em;">
                <li>Estado de caja consolidado</li>
                <li>Análisis de cobertura</li>
                <li>Detalle por proyecto</li>
                <li>Alertas y recomendaciones</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🎯 Generar Reporte Gerencial", use_container_width=True, type="primary"):
            with st.spinner("Generando reporte..."):
                try:
                    pdf_bytes = generar_reporte_gerencial_pdf(datos)
                    
                    st.success("✅ Reporte generado exitosamente")
                    
                    # Botón de descarga
                    st.download_button(
                        label="⬇️ Descargar PDF",
                        data=pdf_bytes,
                        file_name=f"Reporte_Gerencial_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"❌ Error al generar reporte: {str(e)}")
                    st.exception(e)
    
    with col_tipo2:
        st.markdown("""
        <div style="padding: 20px; border: 2px solid #10b981; border-radius: 10px; background-color: #f0fdf4;">
            <h4 style="color: #065f46;">💰 Reporte de Inversiones</h4>
            <p style="color: #64748b;">Análisis detallado de instrumentos financieros y rentabilidad</p>
            <ul style="color: #64748b; font-size: 0.9em;">
                <li>Monto total invertido</li>
                <li>Retorno neto por instrumento</li>
                <li>Gantt de vencimientos</li>
                <li>Costos y comisiones</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("💎 Generar Reporte de Inversiones", use_container_width=True):
            st.info("🚧 Reporte de Inversiones disponible en Fase 2")
            st.caption("Este reporte estará disponible próximamente")
    
    st.markdown("---")
    
    # Vista previa de datos
    with st.expander("🔍 Vista Previa de Datos"):
        st.markdown("#### Estado de Caja")
        st.json(datos['estado_caja'])
        
        st.markdown("#### Proyectos")
        df_proyectos = pd.DataFrame([
            {
                'Nombre': p['nombre'],
                'Estado': p['estado'],
                'Presupuesto': p.get('presupuesto_total', 0),
                'Ejecutado': p.get('ejecutado', 0),
                'Saldo': p.get('saldo_real_tesoreria', 0)
            }
            for p in datos['proyectos']
        ])
        st.dataframe(df_proyectos, use_container_width=True)


if __name__ == "__main__":
    main()
