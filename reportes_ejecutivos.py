"""
SICONE - Módulo de Reportes Ejecutivos
Versión: 1.1.0 - Mejorado
Fecha: Diciembre 2024
Autor: Andrés Restrepo & Claude

Genera reportes ejecutivos en PDF con datos consolidados del módulo multiproyecto

MEJORAS v1.1.0:
- Detección automática de sistema operativo y entorno Python
- Instalación adaptativa según el contexto (venv, system, Windows/Linux)
- Mejor manejo de errores de permisos
- Feedback mejorado con instrucciones específicas por plataforma
- Verificación robusta de instalación
"""

import streamlit as st
from datetime import datetime
import pandas as pd
from typing import Dict, List
import io
import sys
import os
import platform
import subprocess

# Variable global para verificar disponibilidad de PDF
PDF_DISPONIBLE = False

# ============================================================================
# DETECCIÓN DE ENTORNO
# ============================================================================

def detectar_entorno():
    """
    Detecta el entorno de ejecución para adaptar la instalación
    
    Returns:
        dict: Información del entorno con las siguientes claves:
            - sistema: 'Windows', 'Linux', 'Darwin' (macOS)
            - en_venv: bool, True si está en entorno virtual
            - python_version: str, versión de Python
            - pip_path: str, ruta al ejecutable de pip
            - necesita_break_system: bool, True si necesita --break-system-packages
    """
    entorno = {
        'sistema': platform.system(),
        'en_venv': hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix),
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'pip_path': sys.executable,
        'necesita_break_system': False
    }
    
    # Determinar si necesita --break-system-packages
    # Esta opción solo es necesaria en Linux/macOS con Python 3.11+ gestionado por el sistema
    if entorno['sistema'] in ['Linux', 'Darwin'] and not entorno['en_venv']:
        version_mayor = sys.version_info.major
        version_menor = sys.version_info.minor
        if version_mayor >= 3 and version_menor >= 11:
            entorno['necesita_break_system'] = True
    
    return entorno

def obtener_comando_instalacion(entorno: dict) -> List[str]:
    """
    Genera el comando de instalación apropiado según el entorno
    
    Args:
        entorno: Diccionario con información del entorno
        
    Returns:
        List[str]: Comando de instalación como lista de argumentos
    """
    comando = [entorno['pip_path'], "-m", "pip", "install", "reportlab"]
    
    # Agregar --break-system-packages solo si es necesario
    if entorno['necesita_break_system']:
        comando.append("--break-system-packages")
    
    # En Windows y entornos virtuales, usar --user puede causar problemas, mejor omitirlo
    # En Linux/macOS sin venv y sin permisos root, intentaremos con --user
    if entorno['sistema'] in ['Linux', 'Darwin'] and not entorno['en_venv']:
        # No agregamos --user inicialmente, lo intentaremos en segundo intento si falla
        pass
    
    return comando

def obtener_instrucciones_manuales(entorno: dict) -> str:
    """
    Genera instrucciones de instalación manual específicas para el entorno
    
    Args:
        entorno: Diccionario con información del entorno
        
    Returns:
        str: Instrucciones formateadas para el entorno específico
    """
    sistema = entorno['sistema']
    en_venv = entorno['en_venv']
    
    if sistema == 'Windows':
        if en_venv:
            return """# En su terminal (PowerShell o CMD):
# Ya está en un entorno virtual, solo instale directamente
pip install reportlab

# Luego reinicie la aplicación con Ctrl+C y:
streamlit run main.py"""
        else:
            return """# En su terminal (PowerShell o CMD):
# Opción 1: Crear entorno virtual (RECOMENDADO)
python -m venv venv
venv\\Scripts\\activate
pip install reportlab

# Opción 2: Instalación directa
pip install reportlab

# Luego reinicie la aplicación con Ctrl+C y:
streamlit run main.py"""
    
    elif sistema in ['Linux', 'Darwin']:
        if en_venv:
            activacion = "source venv/bin/activate" if sistema == 'Linux' else "source venv/bin/activate"
            return f"""# En su terminal:
# Ya está en un entorno virtual
{activacion}
pip install reportlab

# Luego reinicie la aplicación con Ctrl+C y:
streamlit run main.py"""
        else:
            break_system = "--break-system-packages" if entorno['necesita_break_system'] else ""
            return f"""# En su terminal:
# Opción 1: Con entorno virtual (RECOMENDADO)
python3 -m venv venv
source venv/bin/activate
pip install reportlab

# Opción 2: Instalación de sistema (requiere permisos)
sudo pip3 install reportlab {break_system}

# Opción 3: Instalación de usuario
pip3 install reportlab --user {break_system}

# Luego reinicie la aplicación con Ctrl+C y:
streamlit run main.py"""
    
    return """# Instalación genérica:
pip install reportlab

# Luego reinicie la aplicación"""


# ============================================================================
# VERIFICACIÓN E INSTALACIÓN
# ============================================================================

def verificar_reportlab():
    """Verifica e intenta importar reportlab"""
    global PDF_DISPONIBLE
    
    try:
        from reportlab.lib.pagesizes import letter
        PDF_DISPONIBLE = True
        return True
    except ImportError:
        PDF_DISPONIBLE = False
        return False

def instalar_reportlab():
    """
    Instala reportlab con detección automática de entorno y feedback detallado
    
    FUNCIONAMIENTO:
    1. Detecta el entorno de ejecución (OS, venv, versión Python)
    2. Construye el comando de instalación apropiado
    3. Intenta la instalación con feedback en tiempo real
    4. Si falla por permisos en Linux/macOS, reintenta con --user
    5. Verifica que la instalación fue exitosa
    
    Returns:
        bool: True si la instalación fue exitosa, False en caso contrario
    """
    try:
        # Detectar entorno
        status_container = st.empty()
        progress_bar = st.progress(0)
        
        status_container.info("🔍 Detectando entorno de ejecución...")
        progress_bar.progress(10)
        
        entorno = detectar_entorno()
        
        # Mostrar información del entorno
        with st.expander("ℹ️ Información del entorno detectado"):
            st.write(f"**Sistema Operativo:** {entorno['sistema']}")
            st.write(f"**Python:** {entorno['python_version']}")
            st.write(f"**Entorno Virtual:** {'Sí' if entorno['en_venv'] else 'No'}")
            st.write(f"**Requiere --break-system-packages:** {'Sí' if entorno['necesita_break_system'] else 'No'}")
        
        # Construir comando de instalación
        comando = obtener_comando_instalacion(entorno)
        
        status_container.info(f"📦 Instalando reportlab...")
        st.caption(f"Ejecutando: `{' '.join(comando[2:])}`")  # Mostrar solo parte legible
        progress_bar.progress(25)
        
        # Intentar instalación
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        progress_bar.progress(60)
        
        # Si falla por permisos en Linux/macOS sin venv, reintentar con --user
        if resultado.returncode != 0 and entorno['sistema'] in ['Linux', 'Darwin'] and not entorno['en_venv']:
            if "Permission denied" in resultado.stderr or "EACCES" in resultado.stderr or "[Errno 13]" in resultado.stderr:
                status_container.warning("⚠️ Permiso denegado. Reintentando con instalación de usuario...")
                progress_bar.progress(40)
                
                # Agregar --user al comando
                comando_user = comando.copy()
                if "--break-system-packages" not in comando_user:
                    comando_user.append("--user")
                else:
                    # Insertar --user antes de --break-system-packages
                    idx = comando_user.index("--break-system-packages")
                    comando_user.insert(idx, "--user")
                
                st.caption(f"Ejecutando: `{' '.join(comando_user[2:])}`")
                
                resultado = subprocess.run(
                    comando_user,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                progress_bar.progress(75)
        
        # Verificar resultado
        if resultado.returncode == 0:
            status_container.success("✅ reportlab instalado correctamente")
            progress_bar.progress(90)
            
            # Verificar que realmente se puede importar
            try:
                import importlib
                importlib.invalidate_caches()  # Limpiar cache de imports
                reportlab_module = importlib.import_module('reportlab')
                
                global PDF_DISPONIBLE
                PDF_DISPONIBLE = True
                progress_bar.progress(100)
                
                st.success(f"✅ reportlab versión {reportlab_module.Version} disponible")
                return True
                
            except ImportError as ie:
                status_container.error("⚠️ Instalado pero no se puede importar. Reinicie la aplicación.")
                st.warning("**Acción requerida:** Detenga la aplicación (Ctrl+C) y reinicie con `streamlit run main.py`")
                progress_bar.progress(100)
                return False
        else:
            # Instalación falló
            status_container.error("❌ Error en instalación")
            
            # Analizar el error para dar feedback específico
            error_msg = resultado.stderr.lower()
            
            if "permission" in error_msg or "eacces" in error_msg or "[errno 13]" in error_msg:
                st.error("**Error de Permisos:** No tiene permisos suficientes para instalar paquetes.")
                st.info("**Soluciones:**")
                st.markdown("""
                1. **Usar entorno virtual** (RECOMENDADO):
                   - Cree un venv y ejecute la aplicación desde allí
                2. **Instalación de usuario**:
                   - Use la instalación manual con la opción `--user`
                3. **Permisos de administrador**:
                   - En Linux/macOS: use `sudo` en la instalación manual
                """)
            
            elif "not found" in error_msg or "no such file" in error_msg:
                st.error("**Error:** No se encontró pip o Python.")
                st.info("Verifique que Python y pip están correctamente instalados")
            
            else:
                st.error("**Error desconocido en la instalación**")
            
            with st.expander("🔍 Ver detalles completos del error"):
                st.code(resultado.stderr, language="bash")
            
            return False
            
    except subprocess.TimeoutExpired:
        st.error("⏱️ Timeout: La instalación tomó demasiado tiempo (>120s)")
        st.info("Intente la instalación manual en su terminal")
        return False
        
    except Exception as e:
        st.error(f"❌ Error inesperado durante la instalación: {str(e)}")
        with st.expander("🔍 Ver detalles del error"):
            st.exception(e)
        return False


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
    
    # Importar reportlab aquí (lazy import)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    except ImportError as e:
        raise ImportError("reportlab no está instalado. Use el botón 'Instalar reportlab' primero.") from e
    
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
    # DETALLE DE PROYECTOS
    # =================================================================
    
    proyectos = datos['proyectos']
    
    elements.append(Paragraph("DETALLE POR PROYECTO", ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=8
    )))
    
    # Tabla de proyectos
    proyectos_data = [['Proyecto', 'Estado', 'Presupuesto', 'Ejecutado', 'Saldo', 'Avance']]
    
    for p in proyectos:
        presupuesto = p.get('presupuesto_total', 0)
        ejecutado = p.get('ejecutado', 0)
        avance = (ejecutado / presupuesto * 100) if presupuesto > 0 else 0
        
        proyectos_data.append([
            p['nombre'][:30],  # Truncar nombres largos
            p['estado'],
            formatear_moneda(presupuesto),
            formatear_moneda(ejecutado),
            formatear_moneda(p.get('saldo_real_tesoreria', 0)),
            f"{avance:.1f}%"
        ])
    
    tabla_proyectos = Table(proyectos_data, colWidths=[2.0*inch, 0.9*inch, 1.1*inch, 1.1*inch, 1.1*inch, 0.8*inch])
    tabla_proyectos.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        
        # Datos
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f9ff')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(tabla_proyectos)
    elements.append(Spacer(1, 0.2*inch))
    
    # =================================================================
    # ALERTAS
    # =================================================================
    
    alertas = datos.get('alertas', [])
    
    if alertas:
        elements.append(Paragraph("ALERTAS Y RECOMENDACIONES", ParagraphStyle(
            'AlertHeader',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#dc2626'),
            spaceAfter=6
        )))
        
        for alerta in alertas[:5]:  # Máximo 5 alertas
            elements.append(Paragraph(
                f"• {alerta}",
                ParagraphStyle('AlertText', parent=styles['Normal'], fontSize=9, leftIndent=10)
            ))
    
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
    
    # Verificar reportlab
    if not verificar_reportlab():
        st.warning("⚠️ La biblioteca 'reportlab' no está instalada")
        st.info("📦 **reportlab** es necesaria para generar reportes PDF de alta calidad")
        
        st.markdown("---")
        
        col_inst1, col_inst2 = st.columns(2)
        
        with col_inst1:
            st.markdown("### 🔧 Instalación Automática")
            st.caption("El sistema detectará su entorno y ajustará la instalación automáticamente")
            
            # Mostrar información del entorno antes de instalar
            entorno = detectar_entorno()
            with st.expander("ℹ️ Vista previa del entorno"):
                st.write(f"**SO:** {entorno['sistema']}")
                st.write(f"**Python:** {entorno['python_version']}")
                st.write(f"**Entorno Virtual:** {'Sí ✅' if entorno['en_venv'] else 'No ❌'}")
                
                if not entorno['en_venv']:
                    st.warning("⚠️ No está usando entorno virtual. Se recomienda crear uno para evitar conflictos.")
            
            if st.button("🚀 Instalar reportlab ahora", type="primary", use_container_width=True):
                if instalar_reportlab():
                    st.balloons()
                    st.success("✅ ¡Instalación exitosa!")
                    
                    # Botón para recargar
                    if st.button("🔄 Recargar módulo", type="primary"):
                        st.rerun()
                else:
                    st.warning("⚠️ La instalación automática falló. Por favor, use el método manual.")
        
        with col_inst2:
            st.markdown("### 📝 Instalación Manual")
            st.caption("Instrucciones específicas para su sistema")
            
            # Obtener instrucciones específicas para este entorno
            entorno = detectar_entorno()
            instrucciones = obtener_instrucciones_manuales(entorno)
            
            st.code(instrucciones, language="bash")
            
            if not entorno['en_venv']:
                st.info("💡 **Recomendación:** Crear un entorno virtual evita conflictos y problemas de permisos")
            
            st.markdown("")
            if st.button("🔄 Verificar si ya está instalado", use_container_width=True):
                if verificar_reportlab():
                    st.success("✅ ¡reportlab está instalado! Recargando módulo...")
                    import time
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Aún no está instalado. Complete la instalación manual primero.")
        
        st.markdown("---")
        
        # Diagnóstico detallado
        with st.expander("🔍 Información de Diagnóstico Completa"):
            st.markdown("#### Entorno Python")
            st.write("**Python executable:**", sys.executable)
            st.write("**Python version:**", sys.version)
            st.write("**Sistema Operativo:**", f"{platform.system()} {platform.release()}")
            st.write("**Arquitectura:**", platform.machine())
            
            entorno = detectar_entorno()
            st.write("**En entorno virtual:**", "Sí" if entorno['en_venv'] else "No")
            st.write("**Requiere --break-system-packages:**", "Sí" if entorno['necesita_break_system'] else "No")
            
            st.markdown("#### Pip")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "--version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                st.code(result.stdout, language="bash")
            except Exception as e:
                st.error(f"❌ Error al ejecutar pip: {e}")
            
            st.markdown("#### Paquetes instalados (relacionados con PDF)")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "list"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                # Filtrar solo paquetes relevantes
                lineas = result.stdout.split('\n')
                relevantes = [l for l in lineas if any(x in l.lower() for x in ['report', 'pdf', 'pillow', 'image'])]
                if relevantes:
                    st.code('\n'.join(relevantes), language="text")
                else:
                    st.caption("No se encontraron paquetes relacionados con PDF")
            except Exception as e:
                st.error(f"❌ Error al listar paquetes: {e}")
        
        st.stop()
    
    # Si llegamos aquí, reportlab está disponible
    st.success("✅ reportlab está disponible")
    
    # Verificar que existan datos
    if 'datos_reportes' not in st.session_state:
        st.warning("⚠️ No hay datos disponibles para generar reportes")
        st.info("📋 **Instrucciones:**\n"
                "1. Vaya al módulo **Análisis Multiproyecto**\n"
                "2. Cargue y consolide sus proyectos\n"
                "3. Haga clic en **'Exportar datos para reportes'**\n"
                "4. Regrese aquí para generar reportes")
        
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
                    
                except ImportError as e:
                    st.error("❌ Error: reportlab no está instalado correctamente")
                    st.info("Reinicie la aplicación y vuelva a intentar. Si el problema persiste, instale manualmente.")
                except Exception as e:
                    st.error(f"❌ Error al generar reporte: {str(e)}")
                    with st.expander("🔍 Ver detalles del error"):
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
