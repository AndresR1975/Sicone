"""
SICONE - Módulo de Reportes Ejecutivos
Versión: 1.3.2
Fecha: 28 Diciembre 2024
Autor: Andrés Restrepo & Claude

MEJORAS v1.3.2 (28-Dic-2024):
- 🎨 Timeline mejorado: Muestra semanas NEGATIVAS (pasado visible)
- ✅ Eje X: -6 a +6 semanas (antes solo 0 a 6)
- ✅ Línea vertical en "Hoy" (semana 0)
- ✅ Marcadores más grandes y visibles
- 🎨 Semáforo mejorado: Leyenda VERTICAL a la derecha
- ✅ Líneas de referencia MÁS VISIBLES (sólidas, alpha 0.4)
- ✅ 4 categorías en leyenda (Excedente, Estable, Alerta, Crítico)
- 📊 Gráfico PIE implementado (opcional, comentado)
- ✅ Distribución de gastos ejecutados por proyecto
- ✅ Leyenda vertical a la derecha

FIX v1.3.1 (28-Dic-2024):
- 🐛 Corregido error de dimensiones en Timeline
- 📐 Optimización para caber en 1 página
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

# Matplotlib para gráficos
import matplotlib
matplotlib.use('Agg')  # Backend sin interfaz gráfica
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Importar utilidades compartidas
try:
    from utils_formateo import (
        formatear_moneda,
        formatear_porcentaje,
        formatear_fecha,
        obtener_valor_seguro,
        generar_timestamp,
        calcular_semanas_cobertura,
        obtener_info_estado_financiero,
        FORMATO_REGIONAL
    )
    UTILS_DISPONIBLE = True
except ImportError:
    st.warning("⚠️ utils_formateo.py no encontrado. Usando funciones locales.")
    UTILS_DISPONIBLE = False
    
    # Función local de respaldo
    def formatear_moneda(valor):
        if valor >= 1_000_000_000:
            return f"${valor/1_000_000_000:.2f}MM"
        elif valor >= 1_000_000:
            return f"${valor/1_000_000:.1f}M"
        elif valor >= 1_000:
            return f"${valor/1_000:.0f}K"
        else:
            return f"${valor:,.0f}"

# Variable global para verificar disponibilidad de PDF
PDF_DISPONIBLE = False

# ============================================================================
# DETECCIÓN DE ENTORNO
# ============================================================================

def detectar_entorno():
    """
    Detecta el entorno de ejecución para adaptar la instalación
    
    Returns:
        dict: Información del entorno
    """
    entorno = {
        'sistema': platform.system(),
        'en_venv': hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix),
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'pip_path': sys.executable,
        'necesita_break_system': False
    }
    
    if entorno['sistema'] in ['Linux', 'Darwin'] and not entorno['en_venv']:
        version_mayor = sys.version_info.major
        version_menor = sys.version_info.minor
        if version_mayor >= 3 and version_menor >= 11:
            entorno['necesita_break_system'] = True
    
    return entorno

def obtener_comando_instalacion(entorno: dict) -> List[str]:
    """Genera el comando de instalación apropiado según el entorno"""
    comando = [entorno['pip_path'], "-m", "pip", "install", "reportlab"]
    
    if entorno['necesita_break_system']:
        comando.append("--break-system-packages")
    
    return comando

def obtener_instrucciones_manuales(entorno: dict) -> str:
    """Genera instrucciones de instalación manual específicas para el entorno"""
    sistema = entorno['sistema']
    en_venv = entorno['en_venv']
    
    if sistema == 'Windows':
        if en_venv:
            return """# En su terminal (PowerShell o CMD):
pip install reportlab
streamlit run main.py"""
        else:
            return """# En su terminal (PowerShell o CMD):
# Opción 1: Crear entorno virtual (RECOMENDADO)
python -m venv venv
venv\\Scripts\\activate
pip install reportlab

# Opción 2: Instalación directa
pip install reportlab

streamlit run main.py"""
    
    elif sistema in ['Linux', 'Darwin']:
        if en_venv:
            return f"""# En su terminal:
pip install reportlab
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

streamlit run main.py"""
    
    return """# Instalación genérica:
pip install reportlab
streamlit run main.py"""


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
    """Instala reportlab con detección automática de entorno"""
    try:
        status_container = st.empty()
        progress_bar = st.progress(0)
        
        status_container.info("🔍 Detectando entorno de ejecución...")
        progress_bar.progress(10)
        
        entorno = detectar_entorno()
        
        with st.expander("ℹ️ Información del entorno detectado"):
            st.write(f"**Sistema Operativo:** {entorno['sistema']}")
            st.write(f"**Python:** {entorno['python_version']}")
            st.write(f"**Entorno Virtual:** {'Sí' if entorno['en_venv'] else 'No'}")
            st.write(f"**Requiere --break-system-packages:** {'Sí' if entorno['necesita_break_system'] else 'No'}")
        
        comando = obtener_comando_instalacion(entorno)
        
        status_container.info(f"📦 Instalando reportlab...")
        st.caption(f"Ejecutando: `{' '.join(comando[2:])}`")
        progress_bar.progress(25)
        
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        progress_bar.progress(60)
        
        # Reintento con --user si falla por permisos
        if resultado.returncode != 0 and entorno['sistema'] in ['Linux', 'Darwin'] and not entorno['en_venv']:
            if "Permission denied" in resultado.stderr or "EACCES" in resultado.stderr or "[Errno 13]" in resultado.stderr:
                status_container.warning("⚠️ Permiso denegado. Reintentando con instalación de usuario...")
                progress_bar.progress(40)
                
                comando_user = comando.copy()
                if "--break-system-packages" not in comando_user:
                    comando_user.append("--user")
                else:
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
        
        if resultado.returncode == 0:
            status_container.success("✅ reportlab instalado correctamente")
            progress_bar.progress(90)
            
            try:
                import importlib
                importlib.invalidate_caches()
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
            status_container.error("❌ Error en instalación")
            
            error_msg = resultado.stderr.lower()
            
            if "permission" in error_msg or "eacces" in error_msg or "[errno 13]" in error_msg:
                st.error("**Error de Permisos:** No tiene permisos suficientes")
                st.info("""**Soluciones:**
                1. Usar entorno virtual (RECOMENDADO)
                2. Instalación de usuario con --user
                3. Permisos de administrador con sudo
                """)
            
            elif "not found" in error_msg or "no such file" in error_msg:
                st.error("**Error:** No se encontró pip o Python")
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
# GENERACIÓN DE GRÁFICOS (Preparado para Fase 2)
# ============================================================================

def generar_grafico_timeline(datos: Dict) -> bytes:
    """
    Genera gráfico de evolución temporal del saldo consolidado
    
    Args:
        datos: Diccionario con datos consolidados
        
    Returns:
        bytes: Imagen PNG del gráfico
    """
    try:
        # Extraer datos históricos
        saldo_total = datos.get('saldo_total', 0)
        semana_actual = datos.get('semana', 0)
        burn_rate = datos.get('burn_rate', 0)
        
        # Generar datos (6 semanas atrás + 6 adelante)
        semanas_historicas = 6
        semanas_futuras = 6
        
        # Construir arrays coordinados
        semanas = []
        saldos = []
        
        # Histórico (semanas NEGATIVAS)
        for i in range(-semanas_historicas, 0):
            semanas.append(i)
            # Saldo histórico = saldo actual + (burn_rate × semanas desde entonces)
            saldo_hist = saldo_total + (burn_rate * abs(i))
            saldos.append(saldo_hist)
        
        # Semana actual (0)
        semanas.append(0)
        saldos.append(saldo_total)
        
        # Proyección (semanas POSITIVAS)
        for i in range(1, semanas_futuras + 1):
            semanas.append(i)
            saldo_proy = max(0, saldo_total - (burn_rate * i))
            saldos.append(saldo_proy)
        
        # Separar para graficar
        idx_actual = semanas_historicas  # Índice de semana 0
        semanas_hist = semanas[:idx_actual + 1]  # Incluye semana 0
        saldos_hist = saldos[:idx_actual + 1]
        semanas_proy = semanas[idx_actual:]  # Overlap en semana 0
        saldos_proy = saldos[idx_actual:]
        
        # Crear gráfico
        fig, ax = plt.subplots(figsize=(6.5, 1.8))
        
        # Línea histórica (azul)
        ax.plot(semanas_hist, saldos_hist, 
                color='#3b82f6', linewidth=2.5, marker='o', markersize=4,
                label='Histórico', zorder=3)
        
        # Línea proyección (naranja)
        ax.plot(semanas_proy, saldos_proy, 
                color='#f97316', linewidth=2.5, linestyle='--', marker='s', markersize=4,
                label='Proyección', zorder=3)
        
        # Línea vertical en semana actual
        ax.axvline(x=0, color='gray', linestyle=':', linewidth=1.5, alpha=0.7, 
                   label='Hoy', zorder=2)
        
        # Línea en cero
        ax.axhline(y=0, color='red', linestyle=':', linewidth=1, alpha=0.5, zorder=1)
        
        # Área sombreada para proyección
        ax.fill_between(semanas_proy, 0, saldos_proy, 
                        alpha=0.1, color='#f97316', zorder=0)
        
        # Formateo
        ax.set_xlabel('Semanas (relativo a hoy)', fontsize=7, fontweight='bold')
        ax.set_ylabel('Saldo', fontsize=7, fontweight='bold')
        ax.set_title('Evolución del Saldo', fontsize=9, fontweight='bold', pad=5)
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        ax.legend(loc='upper right', fontsize=6, framealpha=0.9, ncol=3)
        
        # IMPORTANTE: Fijar límites del eje X para mostrar negativo y positivo
        ax.set_xlim(-semanas_historicas - 0.5, semanas_futuras + 0.5)
        
        # Formato de moneda en eje Y
        ax.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, p: formatear_moneda(x) if UTILS_DISPONIBLE else f"${x/1e6:.0f}M"
        ))
        
        # Reducir número de ticks
        ax.yaxis.set_major_locator(plt.MaxNLocator(5))
        ax.xaxis.set_major_locator(plt.MaxNLocator(7))  # Mostrar -6, -3, 0, 3, 6
        ax.tick_params(axis='both', labelsize=6)
        
        plt.tight_layout(pad=0.3)
        
        # Guardar a bytes
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf
        
    except Exception as e:
        st.error(f"Error generando gráfico timeline: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None

def generar_grafico_semaforo(datos: Dict) -> bytes:
    """
    Genera semáforo de estado financiero por proyecto
    
    Args:
        datos: Diccionario con datos consolidados
        
    Returns:
        bytes: Imagen PNG del gráfico
    """
    try:
        proyectos = datos.get('proyectos', [])
        
        if not proyectos:
            return None
        
        # Preparar datos
        nombres = []
        coberturas = []
        colores = []
        
        for p in proyectos:
            nombre = p.get('nombre', 'Sin nombre')[:12]  # Más corto
            saldo = p.get('saldo_real_tesoreria', 0)
            burn_rate = p.get('burn_rate_real', 0)
            
            # Calcular cobertura
            if burn_rate > 0:
                cobertura = saldo / burn_rate
            else:
                cobertura = 100  # Cobertura "infinita"
            
            # Determinar color según cobertura
            if cobertura >= 20:
                color = '#22c55e'  # Verde - EXCEDENTE
            elif cobertura >= 10:
                color = '#3b82f6'  # Azul - ESTABLE
            elif cobertura >= 5:
                color = '#f97316'  # Naranja - ALERTA
            else:
                color = '#dc2626'  # Rojo - CRÍTICO
            
            nombres.append(nombre)
            coberturas.append(min(cobertura, 100))  # Cap para visualización
            colores.append(color)
        
        # Crear gráfico más compacto
        altura = min(2.5, len(proyectos) * 0.35 + 0.4)
        fig, ax = plt.subplots(figsize=(6.5, altura))
        
        # Barras horizontales más delgadas
        y_pos = np.arange(len(nombres))
        bars = ax.barh(y_pos, coberturas, color=colores, height=0.5, 
                      edgecolor='white', linewidth=1)
        
        # Etiquetas más pequeñas
        ax.set_yticks(y_pos)
        ax.set_yticklabels(nombres, fontsize=7)
        ax.set_xlabel('Cobertura (semanas)', fontsize=7, fontweight='bold')
        ax.set_title('Estado Financiero por Proyecto', fontsize=9, fontweight='bold', pad=5)
        
        # Líneas de referencia MÁS VISIBLES
        ax.axvline(x=20, color='#22c55e', linestyle='-', linewidth=2, alpha=0.4, zorder=1)
        ax.axvline(x=10, color='#3b82f6', linestyle='-', linewidth=2, alpha=0.4, zorder=1)
        ax.axvline(x=5, color='#f97316', linestyle='-', linewidth=2, alpha=0.4, zorder=1)
        
        # Valores en las barras
        for i, (bar, cob) in enumerate(zip(bars, coberturas)):
            width = bar.get_width()
            label_x = width + 1 if width < 80 else width - 2
            ax.text(label_x, bar.get_y() + bar.get_height()/2, 
                   f'{cob:.1f}s', 
                   ha='left' if width < 80 else 'right',
                   va='center', fontsize=6, fontweight='bold',
                   color='black' if width < 80 else 'white')
        
        # Formateo compacto
        ax.set_xlim(0, 105)
        ax.grid(axis='x', alpha=0.2, linestyle='--', linewidth=0.5)
        ax.tick_params(axis='both', labelsize=6)
        ax.invert_yaxis()  # Primer proyecto arriba
        
        # LEYENDA VERTICAL A LA DERECHA
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#22c55e', edgecolor='black', linewidth=0.5, label='Excedente (≥20s)'),
            Patch(facecolor='#3b82f6', edgecolor='black', linewidth=0.5, label='Estable (≥10s)'),
            Patch(facecolor='#f97316', edgecolor='black', linewidth=0.5, label='Alerta (≥5s)'),
            Patch(facecolor='#dc2626', edgecolor='black', linewidth=0.5, label='Crítico (<5s)')
        ]
        ax.legend(handles=legend_elements, 
                 loc='center right',  # A la derecha
                 bbox_to_anchor=(1.22, 0.5),  # Fuera del gráfico
                 fontsize=6, 
                 framealpha=0.9, 
                 ncol=1,  # Vertical (1 columna)
                 handlelength=1.5, 
                 handletextpad=0.5,
                 borderpad=0.8)
        
        plt.tight_layout(pad=0.3)
        
        # Guardar a bytes con espacio extra para leyenda
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf
        
    except Exception as e:
        st.error(f"Error generando gráfico semáforo: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None

def generar_grafico_comparacion(datos: Dict) -> bytes:
    """
    FASE 2: Genera gráfico de comparación planeación vs ejecución
    
    Args:
        datos: Diccionario con datos consolidados
        
    Returns:
        bytes: Imagen PNG del gráfico
    """
    # Placeholder - será implementado en Fase 2
    return None

def generar_grafico_pie_gastos(datos: Dict) -> bytes:
    """
    Genera pie chart de distribución de gastos ejecutados por proyecto
    
    Args:
        datos: Diccionario con datos consolidados
        
    Returns:
        bytes: Imagen PNG del gráfico
    """
    try:
        proyectos = datos.get('proyectos', [])
        
        if not proyectos:
            return None
        
        # Preparar datos
        nombres = []
        ejecutados = []
        colores_personalizados = ['#3b82f6', '#22c55e', '#f97316', '#8b5cf6', '#ec4899', '#14b8a6']
        
        for p in proyectos:
            nombre = p.get('nombre', 'Sin nombre')[:12]
            ejecutado = p.get('ejecutado', 0)
            
            if ejecutado > 0:  # Solo incluir proyectos con gasto
                nombres.append(nombre)
                ejecutados.append(ejecutado)
        
        if not ejecutados:
            return None
        
        # Crear gráfico compacto
        fig, ax = plt.subplots(figsize=(6.5, 2.2))
        
        # Calcular porcentajes
        total = sum(ejecutados)
        porcentajes = [(e/total)*100 for e in ejecutados]
        
        # Función para formato de labels
        def formato_label(pct, allvals):
            absolute = int(pct/100.*sum(allvals))
            return f'{pct:.1f}%\n{formatear_moneda(absolute) if UTILS_DISPONIBLE else f"${absolute/1e6:.0f}M"}'
        
        # Gráfico de pie
        wedges, texts, autotexts = ax.pie(ejecutados, 
                                           labels=None,  # Labels en leyenda
                                           autopct=lambda pct: formato_label(pct, ejecutados),
                                           startangle=90,
                                           colors=colores_personalizados[:len(nombres)],
                                           textprops={'fontsize': 6, 'weight': 'bold'},
                                           wedgeprops={'edgecolor': 'white', 'linewidth': 1.5})
        
        # Título
        ax.set_title('Distribución de Gastos por Proyecto', 
                    fontsize=9, fontweight='bold', pad=10)
        
        # Leyenda a la derecha vertical
        ax.legend(nombres, 
                 loc='center left',
                 bbox_to_anchor=(1.05, 0.5),
                 fontsize=6,
                 framealpha=0.9,
                 ncol=1)
        
        plt.tight_layout(pad=0.3)
        
        # Guardar a bytes
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return buf
        
    except Exception as e:
        st.error(f"Error generando gráfico pie: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None


# ============================================================================
# GENERACIÓN DE REPORTE GERENCIAL
# ============================================================================

def generar_reporte_gerencial_pdf(datos: Dict) -> bytes:
    """
    Genera el Reporte Gerencial en PDF (1 página)
    
    Estructura según diseño de Andrés:
    - Encabezado: Fecha, Estado de caja, Margen, Cobertura, etc.
    - Cuerpo: Detalle por proyecto
    - Pie: Alertas relevantes
    - [FASE 2] Gráficos: Timeline, Semáforo, Comparación, Pie
    """
    
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
    
    elements.append(Paragraph("REPORTE GERENCIAL MULTIPROYECTO", style_title))
    elements.append(Paragraph(
        f"Generado: {timestamp.strftime('%d/%m/%Y %H:%M')}",
        style_subtitle
    ))
    elements.append(Spacer(1, 0.2*inch))
    
    # Tabla de métricas clave CON FORMATO COLOMBIANO
    saldo_total = obtener_valor_seguro(estado, 'saldo_total', 0, float) if UTILS_DISPONIBLE else estado.get('saldo_total', 0)
    margen_proteccion = obtener_valor_seguro(estado, 'margen_proteccion', 0, float) if UTILS_DISPONIBLE else estado.get('margen_proteccion', 0)
    burn_rate = obtener_valor_seguro(estado, 'burn_rate', 0, float) if UTILS_DISPONIBLE else estado.get('burn_rate', 0)
    excedente_invertible = obtener_valor_seguro(estado, 'excedente_invertible', 0, float) if UTILS_DISPONIBLE else estado.get('excedente_invertible', 0)
    estado_general = obtener_valor_seguro(estado, 'estado_general', 'N/A', str) if UTILS_DISPONIBLE else estado.get('estado_general', 'N/A')
    proyectos_activos = obtener_valor_seguro(estado, 'proyectos_activos', 0, int) if UTILS_DISPONIBLE else estado.get('proyectos_activos', 0)
    total_proyectos = obtener_valor_seguro(estado, 'total_proyectos', 0, int) if UTILS_DISPONIBLE else estado.get('total_proyectos', 0)
    
    # Calcular cobertura
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
    
    tabla_metricas = Table(metricas_data, colWidths=[1.8*inch, 1.8*inch, 1.8*inch, 1.8*inch])
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
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(tabla_metricas)
    elements.append(Spacer(1, 0.15*inch))  # Reducido de 0.3
    
    # =================================================================
    # GRÁFICOS EJECUTIVOS (Compactos para caber en 1 página)
    # =================================================================
    
    # Timeline - Evolución del saldo
    timeline_img = generar_grafico_timeline(datos)
    if timeline_img:
        elements.append(Paragraph("EVOLUCIÓN DEL SALDO", ParagraphStyle(
            'GraphHeader',
            parent=styles['Heading2'],
            fontSize=10,  # Reducido de 12
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=4  # Reducido de 6
        )))
        img = Image(timeline_img, width=6.5*inch, height=1.6*inch)  # Reducido de 2.2
        elements.append(img)
        elements.append(Spacer(1, 0.1*inch))  # Reducido de 0.2
    
    # Semáforo - Estado por proyecto
    semaforo_img = generar_grafico_semaforo(datos)
    if semaforo_img:
        elements.append(Paragraph("ESTADO POR PROYECTO", ParagraphStyle(
            'GraphHeader2',
            parent=styles['Heading2'],
            fontSize=10,  # Reducido de 12
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=4  # Reducido de 6
        )))
        num_proyectos = len(datos.get('proyectos', []))
        altura_semaforo = min(2.2, num_proyectos * 0.35 + 0.4)  # Más compacto
        img = Image(semaforo_img, width=6.5*inch, height=altura_semaforo*inch)
        elements.append(img)
        elements.append(Spacer(1, 0.15*inch))  # Reducido de 0.3
    
    # Gráfico Pie - Distribución de gastos (OPCIONAL - comentado para mantener 1 página)
    # DESCOMENTAR si deseas agregar el gráfico de pie (puede requerir 2 páginas)
    """
    pie_img = generar_grafico_pie_gastos(datos)
    if pie_img:
        elements.append(Paragraph("DISTRIBUCIÓN DE GASTOS", ParagraphStyle(
            'GraphHeader3',
            parent=styles['Heading2'],
            fontSize=10,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=4
        )))
        img = Image(pie_img, width=6.5*inch, height=2.0*inch)
        elements.append(img)
        elements.append(Spacer(1, 0.15*inch))
    """
    
    # =================================================================
    # DETALLE DE PROYECTOS CON MANEJO SEGURO DE DATOS
    # =================================================================
    
    proyectos = datos.get('proyectos', [])
    
    elements.append(Paragraph("DETALLE POR PROYECTO", ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=10,  # Reducido de 14
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=4  # Reducido de 8
    )))
    
    # Tabla de proyectos con campos optimizados
    # CAMBIO v1.2.1: Eliminamos Estado (todos son ACTIVO), agregamos % Avance desde hitos
    # Incluimos: Ejecutado, Saldo, Burn Rate, Cobertura, % Avance
    proyectos_data = [['Proyecto', 'Ejecutado', 'Saldo', 'Burn Rate', 'Cobertura', '% Avance']]
    
    for p in proyectos:
        # Extraer valores de forma segura usando los nombres reales del consolidador
        if UTILS_DISPONIBLE:
            nombre = obtener_valor_seguro(p, 'nombre', 'Sin nombre', str)
            
            # Campos que existen en el consolidador
            ejecutado = obtener_valor_seguro(p, 'ejecutado', 0, float)
            saldo = obtener_valor_seguro(p, 'saldo_real_tesoreria', 0, float)
            burn_rate = obtener_valor_seguro(p, 'burn_rate_real', 0, float)
            
            # NUEVO v1.2.1: % Avance desde hitos (agregado en multiproy_fcl.py)
            avance_hitos = obtener_valor_seguro(p, 'avance_hitos_pct', 0, float)
            
            # Calcular cobertura (semanas)
            if burn_rate > 0:
                cobertura = saldo / burn_rate
                cobertura_str = f"{cobertura:.1f}s"
            else:
                cobertura_str = "∞"
        else:
            # Versión sin utils
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
            nombre[:28],  # Truncar nombres largos
            formatear_moneda(ejecutado),
            formatear_moneda(saldo),
            formatear_moneda(burn_rate) + "/s",  # Por semana
            cobertura_str,
            f"{avance_hitos:.1f}%"
        ])
    
    tabla_proyectos = Table(proyectos_data, colWidths=[2.0*inch, 1.3*inch, 1.3*inch, 1.1*inch, 0.9*inch, 0.8*inch])
    tabla_proyectos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),  # Reducido de 8
        ('BOTTOMPADDING', (0, 0), (-1, 0), 3),  # Reducido de 6
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f9ff')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),  # Reducido de 8
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),  # Reducido de 4
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),  # Reducido de 4
    ]))
    
    elements.append(tabla_proyectos)
    elements.append(Spacer(1, 0.1*inch))  # Reducido de 0.2
    
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
        
        for alerta in alertas[:5]:
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
                    
                    if st.button("🔄 Recargar módulo", type="primary"):
                        st.rerun()
                else:
                    st.warning("⚠️ La instalación automática falló. Por favor, use el método manual.")
        
        with col_inst2:
            st.markdown("### 📝 Instalación Manual")
            st.caption("Instrucciones específicas para su sistema")
            
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
                lineas = result.stdout.split('\n')
                relevantes = [l for l in lineas if any(x in l.lower() 
                             for x in ['report', 'pdf', 'pillow', 'image'])]
                if relevantes:
                    st.code('\n'.join(relevantes), language="text")
                else:
                    st.caption("No se encontraron paquetes relacionados con PDF")
            except Exception as e:
                st.error(f"❌ Error al listar paquetes: {e}")
        
        st.stop()
    
    # Si llegamos aquí, reportlab está disponible
    st.success("✅ reportlab está disponible")
    
    # ================================================================
    # DIAGNÓSTICO DE DATOS (Para debugging)
    # ================================================================
    
    if 'datos_reportes' in st.session_state:
        with st.expander("🔍 DEBUG: Estructura de datos (para desarrollo)"):
            datos = st.session_state.datos_reportes
            
            st.markdown("#### Claves principales:")
            st.write(list(datos.keys()))
            
            st.markdown("#### Estado de caja:")
            st.json(datos.get('estado_caja', {}))
            
            if datos.get('proyectos'):
                st.markdown("#### Primer proyecto (estructura completa):")
                st.json(datos['proyectos'][0])
                
                st.markdown("#### Claves disponibles en proyectos:")
                if datos['proyectos']:
                    claves = set()
                    for p in datos['proyectos']:
                        claves.update(p.keys())
                    st.write(sorted(list(claves)))
    
    # ================================================================
    # VERIFICAR DATOS
    # ================================================================
    
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
        color_map = {'EXCEDENTE': '🟢', 'AJUSTADO': '🟡', 'CRÍTICO': '🔴', 'ESTABLE': '🔵'}
        st.metric("Estado", f"{color_map.get(estado, '⚪')} {estado}")
    
    st.markdown("---")
    
    # ================================================================
    # SELECTOR DE TIPO DE REPORTE
    # ================================================================
    
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
            <p style="color: #9ca3af; font-size: 0.85em; margin-top: 10px;">
                <strong>Formato:</strong> Cifras en millones (M) y miles de millones (MM) - Estándar colombiano
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🎯 Generar Reporte Gerencial", use_container_width=True, type="primary"):
            with st.spinner("Generando reporte..."):
                try:
                    pdf_bytes = generar_reporte_gerencial_pdf(datos)
                    
                    st.success("✅ Reporte generado exitosamente")
                    
                    # Botón de descarga
                    timestamp = generar_timestamp() if UTILS_DISPONIBLE else datetime.now().strftime("%Y%m%d_%H%M")
                    st.download_button(
                        label="⬇️ Descargar PDF",
                        data=pdf_bytes,
                        file_name=f"Reporte_Gerencial_{timestamp}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                except ImportError as e:
                    st.error("❌ Error: reportlab no está instalado correctamente")
                    st.info("Reinicie la aplicación y vuelva a intentar.")
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
                'Nombre': p.get('nombre', 'Sin nombre'),
                'Ejecutado': p.get('ejecutado', 0),
                'Saldo': p.get('saldo_real_tesoreria', 0),
                'Burn Rate': p.get('burn_rate_real', 0),
                '% Avance': p.get('avance_hitos_pct', 0),
                'Hitos': f"{p.get('hitos_completados', 0)}/{p.get('hitos_totales', 0)}"
            }
            for p in datos['proyectos']
        ])
        st.dataframe(df_proyectos, use_container_width=True)


if __name__ == "__main__":
    main()
