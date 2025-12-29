"""
SICONE - Módulo de Reportes Ejecutivos
Versión: 2.0.0 - Dual Mode
Fecha: 29 Diciembre 2024
Autor: AI-MindNovation

Genera reportes ejecutivos en PDF con datos consolidados.
Soporta 2 modos:
1. Desde Multiproyecto (session_state)
2. Directo cargando JSON
"""

import streamlit as st
from datetime import datetime
import pandas as pd
from typing import Dict, List, Optional
import io
import json

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

PDF_DISPONIBLE = False

def verificar_reportlab():
    """Verifica disponibilidad de reportlab"""
    global PDF_DISPONIBLE
    try:
        from reportlab.lib.pagesizes import letter
        PDF_DISPONIBLE = True
        return True
    except ImportError:
        return False

def instalar_reportlab():
    """Instala reportlab si no está disponible"""
    import subprocess
    import sys
    
    with st.spinner("Instalando reportlab..."):
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "reportlab", "--break-system-packages", "-q"
            ])
            return verificar_reportlab()
        except Exception as e:
            st.error(f"Error instalando reportlab: {str(e)}")
            return False

# Verificar al iniciar
verificar_reportlab()


# ============================================================================
# CARGA DE DATOS
# ============================================================================

def cargar_desde_session_state() -> Optional[Dict]:
    """Carga datos desde session_state (modo desde multiproyecto)"""
    if 'json_consolidado' in st.session_state:
        return st.session_state.json_consolidado
    return None

def cargar_desde_json(archivo_json) -> Optional[Dict]:
    """Carga datos desde archivo JSON (modo directo)"""
    try:
        contenido = archivo_json.read()
        datos = json.loads(contenido.decode('utf-8'))
        return datos
    except Exception as e:
        st.error(f"Error cargando JSON: {str(e)}")
        return None

def obtener_datos() -> Optional[Dict]:
    """Obtiene datos de cualquier fuente disponible"""
    
    # Primero intentar session_state (venimos de multiproyecto)
    datos = cargar_desde_session_state()
    if datos:
        st.success("✅ Datos cargados desde análisis multiproyecto")
        return datos
    
    # Si no, pedir cargar JSON
    st.info("📁 No hay datos cargados. Por favor sube un archivo JSON consolidado.")
    
    archivo = st.file_uploader(
        "Selecciona el archivo JSON consolidado",
        type=['json'],
        help="Exporta desde el módulo Multiproyecto con el botón 'Exportar JSON'"
    )
    
    if archivo:
        datos = cargar_desde_json(archivo)
        if datos:
            # Guardar en session_state para reutilizar
            st.session_state.json_consolidado = datos
            st.success("✅ JSON cargado exitosamente")
            st.rerun()
        return datos
    
    return None


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
# PREVIEW DE REPORTE
# ============================================================================

def render_preview_reporte(datos: Dict):
    """Muestra preview del reporte en pantalla"""
    
    metadata = datos.get('metadata', {})
    estado = datos.get('estado_caja', {})
    proyectos = datos.get('proyectos', [])
    
    st.markdown("## 📊 Preview del Reporte")
    st.caption(f"Generado: {metadata.get('fecha_generacion', 'N/A')}")
    
    st.markdown("---")
    
    # Resumen Ejecutivo
    st.markdown("### 💰 Resumen Ejecutivo")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Saldo Total",
            formatear_moneda(estado.get('saldo_total', 0))
        )
    
    with col2:
        st.metric(
            "Burn Rate Total",
            f"{formatear_moneda(estado.get('burn_rate_total', 0))}/sem"
        )
    
    with col3:
        st.metric(
            "Margen Protección",
            formatear_moneda(estado.get('margen_proteccion', 0)),
            help=f"{metadata.get('semanas_margen', 8)} semanas"
        )
    
    with col4:
        st.metric(
            "Excedente Invertible",
            formatear_moneda(estado.get('excedente_invertible', 0))
        )
    
    st.markdown("---")
    
    # Estado de Proyectos
    st.markdown("### 📁 Estado de Proyectos")
    
    if proyectos:
        df_proyectos = pd.DataFrame(proyectos)
        df_proyectos['saldo_actual'] = df_proyectos['saldo_actual'].apply(formatear_moneda)
        df_proyectos['burn_rate_semanal'] = df_proyectos['burn_rate_semanal'].apply(
            lambda x: f"{formatear_moneda(x)}/sem"
        )
        
        st.dataframe(
            df_proyectos,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay proyectos para mostrar")
    
    st.markdown("---")


# ============================================================================
# GENERACIÓN DE PDF
# ============================================================================

def generar_pdf_simple(datos: Dict) -> bytes:
    """Genera PDF básico con reportlab"""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Metadata
    metadata = datos.get('metadata', {})
    estado = datos.get('estado_caja', {})
    proyectos = datos.get('proyectos', [])
    
    # Título
    y = height - inch
    c.setFont("Helvetica-Bold", 20)
    c.drawString(inch, y, "SICONE - Reporte Ejecutivo Multiproyecto")
    
    y -= 0.3 * inch
    c.setFont("Helvetica", 10)
    c.drawString(inch, y, f"Generado: {metadata.get('fecha_generacion', 'N/A')}")
    c.drawString(inch, y - 15, f"Versión: {metadata.get('version', 'N/A')}")
    
    # Resumen Ejecutivo
    y -= 0.5 * inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(inch, y, "Resumen Ejecutivo")
    
    y -= 0.3 * inch
    c.setFont("Helvetica", 10)
    
    items = [
        f"Saldo Total: {formatear_moneda(estado.get('saldo_total', 0))}",
        f"Burn Rate Total: {formatear_moneda(estado.get('burn_rate_total', 0))}/semana",
        f"Margen Protección ({metadata.get('semanas_margen', 8)} sem): {formatear_moneda(estado.get('margen_proteccion', 0))}",
        f"Excedente Invertible: {formatear_moneda(estado.get('excedente_invertible', 0))}",
        f"Estado: {estado.get('estado_general', 'N/A')}"
    ]
    
    for item in items:
        c.drawString(inch + 20, y, f"• {item}")
        y -= 20
    
    # Proyectos
    y -= 0.3 * inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(inch, y, "Proyectos")
    
    y -= 0.3 * inch
    c.setFont("Helvetica", 9)
    
    for i, proyecto in enumerate(proyectos, 1):
        if y < 2 * inch:
            c.showPage()
            y = height - inch
        
        c.drawString(inch + 20, y, f"{i}. {proyecto.get('nombre', 'N/A')}")
        y -= 15
        c.drawString(inch + 40, y, f"Estado: {proyecto.get('estado', 'N/A')}")
        y -= 15
        c.drawString(inch + 40, y, f"Saldo: {formatear_moneda(proyecto.get('saldo_actual', 0))}")
        y -= 15
        c.drawString(inch + 40, y, f"Burn Rate: {formatear_moneda(proyecto.get('burn_rate_semanal', 0))}/sem")
        y -= 25
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
    """Interfaz principal del módulo de reportes"""
    
    st.title("📊 Reportes Ejecutivos")
    st.caption("Genera reportes PDF con datos consolidados del análisis multiproyecto")
    
    # Verificar instalación de reportlab
    if not PDF_DISPONIBLE:
        st.warning("⚠️ reportlab no está instalado. Se requiere para generar PDFs.")
        if st.button("🔧 Instalar reportlab"):
            if instalar_reportlab():
                st.success("✅ reportlab instalado exitosamente")
                st.rerun()
        return
    
    st.markdown("---")
    
    # Obtener datos
    datos = obtener_datos()
    
    if not datos:
        st.info("👆 Carga datos para continuar")
        return
    
    # Mostrar preview
    render_preview_reporte(datos)
    
    # Botones de acción
    st.markdown("### 🎬 Acciones")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        if st.button("📄 Generar PDF", type="primary", use_container_width=True):
            with st.spinner("Generando PDF..."):
                try:
                    pdf_bytes = generar_pdf_simple(datos)
                    
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"reporte_multiproyecto_{timestamp}.pdf"
                    
                    st.download_button(
                        label="💾 Descargar PDF",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf"
                    )
                    
                    st.success("✅ PDF generado exitosamente")
                    
                except Exception as e:
                    st.error(f"❌ Error generando PDF: {str(e)}")
    
    with col2:
        if st.button("🔄 Recargar Datos", use_container_width=True):
            if 'json_consolidado' in st.session_state:
                del st.session_state.json_consolidado
            st.rerun()
    
    with col3:
        if st.button("🏠 Volver", use_container_width=True):
            st.session_state.modulo_actual = 'multiproyecto'
            st.rerun()


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    main()
