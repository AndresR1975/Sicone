"""
SICONE - Sistema Integrado de Construcción Eficiente
Punto de entrada principal de la plataforma

Versión: 1.0
Fecha: Diciembre 2025
Autor: Andrés Restrepo & Daniel
"""

import streamlit as st
import sys
import os
import sqlite3
from datetime import datetime

# ============================================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================================

st.set_page_config(
    page_title="SICONE - Plataforma Integral",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    
    .module-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #e5e7eb;
        margin: 10px 0;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .module-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .metric-card {
        background: #f9fafb;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNCIONES DE BASE DE DATOS
# ============================================================================

def init_database():
    """Inicializa la base de datos si no existe"""
    db_path = 'sicone.db'
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Crear tabla de proyectos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS proyectos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre VARCHAR(255) NOT NULL,
        cliente VARCHAR(255),
        direccion TEXT,
        area_construida DECIMAL(10,2),
        fecha_inicio DATE,
        estado VARCHAR(50),
        modulo_origen VARCHAR(50),
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Crear tabla de cotizaciones
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cotizaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id INTEGER,
        nombre VARCHAR(255) NOT NULL,
        datos_json TEXT NOT NULL,
        total_costo_directo DECIMAL(15,2),
        area_base DECIMAL(10,2),
        fecha_guardado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (proyecto_id) REFERENCES proyectos(id)
    )
    ''')
    
    conn.commit()
    conn.close()

def get_estadisticas():
    """Obtiene estadísticas rápidas del sistema"""
    conn = sqlite3.connect('sicone.db')
    cursor = conn.cursor()
    
    # Proyectos totales
    cursor.execute("SELECT COUNT(*) FROM proyectos")
    total_proyectos = cursor.fetchone()[0]
    
    # Cotizaciones guardadas
    cursor.execute("SELECT COUNT(*) FROM cotizaciones")
    total_cotizaciones = cursor.fetchone()[0]
    
    # Proyectos activos
    cursor.execute("SELECT COUNT(*) FROM proyectos WHERE estado IN ('contratado', 'en_ejecucion')")
    proyectos_activos = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_proyectos': total_proyectos,
        'total_cotizaciones': total_cotizaciones,
        'proyectos_activos': proyectos_activos
    }

# ============================================================================
# INICIALIZACIÓN
# ============================================================================

def inicializar_session_state():
    """Inicializa las variables de session_state"""
    if 'modulo_actual' not in st.session_state:
        st.session_state.modulo_actual = None
    
    if 'usuario_actual' not in st.session_state:
        st.session_state.usuario_actual = {
            'nombre_completo': 'Andrés Restrepo',
            'rol': 'Administrador'
        }

# ============================================================================
# DEFINICIÓN DE MÓDULOS
# ============================================================================

MODULOS_DISPONIBLES = {
    'cotizaciones': {
        'nombre': 'Cotizaciones',
        'icono': '💰',
        'descripcion': 'Generar cotizaciones detalladas de proyectos',
        'estado': 'activo',
        'version': 'v3.0'
    },
    'flujo_caja': {
        'nombre': 'Flujo de Caja',
        'icono': '📊',
        'descripcion': 'Proyección y seguimiento de flujo de caja',
        'estado': 'activo',
        'version': 'v1.0'
    },
    'multiproyecto': {
        'nombre': 'Análisis Multiproyecto',
        'icono': '🏢',
        'descripcion': 'Dashboard ejecutivo consolidado de múltiples proyectos',
        'estado': 'activo',
        'version': 'v1.0'
    },
    'reportes': {
        'nombre': 'Reportes',
        'icono': '📈',
        'descripcion': 'Reportes ejecutivos y análisis',
        'estado': 'activo',
        'version': 'v1.0'
    },
    'conciliacion': {
        'nombre': 'Conciliación Financiera',
        'icono': '🔍',
        'descripcion': 'Comparar proyecciones SICONE vs saldos reales bancarios',
        'estado': 'activo',
        'version': 'v1.0'
    }
}

# ============================================================================
# FUNCIONES DE RENDERIZADO
# ============================================================================

def render_home():
    """Renderiza la página de inicio"""
    # Header
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">🏗️ SICONE</h1>
        <p style="color: #e0e7ff; margin: 5px 0 0 0;">
            Sistema Integrado de Construcción Eficiente
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Bienvenida
    st.markdown(f"### 👋 Bienvenido, {st.session_state.usuario_actual['nombre_completo']}")
    st.markdown("Seleccione un módulo para comenzar:")
    
    # Mostrar módulos en tarjetas
    cols = st.columns(3)
    
    for idx, (key, modulo) in enumerate(MODULOS_DISPONIBLES.items()):
        with cols[idx % 3]:
            # Estado del módulo
            if modulo['estado'] == 'activo':
                estado_badge = "🟢 Activo"
                estado_color = "#10b981"
            elif modulo['estado'] == 'desarrollo':
                estado_badge = "🟡 En Desarrollo"
                estado_color = "#f59e0b"
            else:
                estado_badge = "⚪ Próximamente"
                estado_color = "#6b7280"
            
            # Tarjeta del módulo
            st.markdown(f"""
            <div class="module-card">
                <h2 style="margin: 0;">{modulo['icono']} {modulo['nombre']}</h2>
                <p style="color: #6b7280; margin: 10px 0;">
                    {modulo['descripcion']}
                </p>
                <p style="color: {estado_color}; font-weight: bold; margin: 5px 0;">
                    {estado_badge}
                </p>
                <p style="color: #9ca3af; font-size: 0.875rem; margin: 5px 0;">
                    {modulo['version']}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Botón de acceso
            if modulo['estado'] == 'activo':
                if st.button(
                    f"{modulo['icono']} Abrir {modulo['nombre']}", 
                    key=f"btn_{key}",
                    use_container_width=True,
                    type="primary"
                ):
                    st.session_state.modulo_actual = key
                    st.rerun()
            else:
                st.button(
                    f"⏳ Próximamente",
                    key=f"btn_{key}",
                    use_container_width=True,
                    disabled=True
                )
    
    # Estadísticas rápidas
    st.markdown("---")
    st.markdown("### 📊 Panel de Control")
    
    try:
        stats = get_estadisticas()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="margin: 0; color: #3b82f6;">🏗️ Proyectos</h3>
                <p style="font-size: 2rem; font-weight: bold; margin: 10px 0;">{stats['total_proyectos']}</p>
                <p style="color: #6b7280; margin: 0;">Total registrados</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="margin: 0; color: #10b981;">✅ Activos</h3>
                <p style="font-size: 2rem; font-weight: bold; margin: 10px 0;">{stats['proyectos_activos']}</p>
                <p style="color: #6b7280; margin: 0;">En ejecución</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="margin: 0; color: #8b5cf6;">📈 Módulos</h3>
                <p style="font-size: 2rem; font-weight: bold; margin: 10px 0;">{len([m for m in MODULOS_DISPONIBLES.values() if m['estado'] == 'activo'])}</p>
                <p style="color: #6b7280; margin: 0;">Disponibles</p>
            </div>
            """, unsafe_allow_html=True)
    
    except Exception as e:
        st.warning(f"No se pudieron cargar las estadísticas: {e}")

def render_modulo_cotizaciones():
    """Renderiza el módulo de cotizaciones"""
    # Botón de regreso
    with st.sidebar:
        if st.button("◄ Volver al Inicio", use_container_width=True):
            st.session_state.modulo_actual = None
            st.rerun()
        st.markdown("---")
        st.markdown(f"👤 **Usuario:** {st.session_state.usuario_actual['nombre_completo']}")
        st.caption(f"Rol: {st.session_state.usuario_actual['rol']}")
    
    # Importar y ejecutar el módulo de cotizaciones
    try:
        import cotizador_sicone
        cotizador_sicone.main()
        
    except ImportError as e:
        st.error(f"❌ Error al importar el módulo de cotizaciones: {e}")
        st.info("**Solución:** Asegúrese de que `cotizador_sicone.py` esté en el mismo directorio que `main.py`")
    except AttributeError:
        st.error("❌ Error: El módulo `cotizador_sicone.py` no tiene una función `main()`")
        st.info("**Solución:** Verifique que el archivo tiene la estructura correcta")
    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")
        st.exception(e)

def render_modulo_flujo_caja():
    """Renderiza el módulo de Flujo de Caja con submenú Proyección/Cartera"""
    # Botón de regreso
    with st.sidebar:
        if st.button("◄ Volver al Inicio", use_container_width=True):
            st.session_state.modulo_actual = None
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 Flujo de Caja")
        
        # Inicializar submodulo si no existe
        if 'submodulo_fcl' not in st.session_state:
            st.session_state.submodulo_fcl = 'proyeccion'
        
        submodulo = st.radio(
            "Seleccione:",
            ["🏗️ Proyección FCL", "💼 Ejecución Real FCL"],
            index=0 if st.session_state.submodulo_fcl == 'proyeccion' else 1,
            key='radio_submodulo_fcl'
        )
        
        # Actualizar submodulo
        if "Proyección" in submodulo:
            st.session_state.submodulo_fcl = 'proyeccion'
        else:
            st.session_state.submodulo_fcl = 'ejecucion'
        
        st.markdown("---")
        st.markdown(f"👤 **Usuario:** {st.session_state.usuario_actual['nombre_completo']}")
        st.caption(f"Rol: {st.session_state.usuario_actual['rol']}")
    
    # Renderizar submódulo correspondiente
    if st.session_state.submodulo_fcl == 'proyeccion':
        try:
            import importlib
            import proyeccion_fcl
            
            if 'STREAMLIT_ENV' in os.environ:
                importlib.reload(proyeccion_fcl)
            
            proyeccion_fcl.main()
        
        except ImportError as e:
            st.error(f"❌ Error al importar proyeccion_fcl: {e}")
        except Exception as e:
            st.error(f"❌ Error inesperado: {e}")
            st.exception(e)
    
    else:  # ejecucion
        try:
            import importlib
            import ejecucion_fcl
            
            if 'STREAMLIT_ENV' in os.environ:
                importlib.reload(ejecucion_fcl)
            
            ejecucion_fcl.main()
        
        except ImportError as e:
            st.error(f"❌ Error al importar ejecucion_fcl: {e}")
            st.info("**Solución:** Asegúrese de que `ejecucion_fcl.py` esté en el mismo directorio")
        except Exception as e:
            st.error(f"❌ Error inesperado: {e}")
            st.exception(e)

def render_modulo_multiproyecto():
    """Renderiza el módulo de Análisis Multiproyecto"""
    # Botón de regreso
    with st.sidebar:
        if st.button("◄ Volver al Inicio", use_container_width=True):
            st.session_state.modulo_actual = None
            st.rerun()
        st.markdown("---")
        st.markdown(f"👤 **Usuario:** {st.session_state.usuario_actual['nombre_completo']}")
        st.caption(f"Rol: {st.session_state.usuario_actual['rol']}")
    
    # Importar y ejecutar el módulo de análisis multiproyecto
    try:
        import importlib
        import multiproy_fcl
        
        if 'STREAMLIT_ENV' in os.environ:
            importlib.reload(multiproy_fcl)
        
        multiproy_fcl.main()
    
    except ImportError as e:
        st.error(f"❌ Error al importar el módulo de análisis multiproyecto: {e}")
        st.info("**Solución:** Asegúrese de que `multiproy_fcl.py` esté en el mismo directorio que `main.py`")
    except AttributeError:
        st.error("❌ Error: El módulo `multiproy_fcl.py` no tiene una función `main()`")
        st.info("**Solución:** Verifique que el archivo tiene la estructura correcta")
    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")
        st.exception(e)

def render_modulo_reportes():
    """Renderiza el módulo de Reportes Ejecutivos"""
    # Botón de regreso
    with st.sidebar:
        if st.button("◄ Volver al Inicio", use_container_width=True):
            st.session_state.modulo_actual = None
            st.rerun()
        st.markdown("---")
        st.markdown(f"👤 **Usuario:** {st.session_state.usuario_actual['nombre_completo']}")
        st.caption(f"Rol: {st.session_state.usuario_actual['rol']}")
    
    # Importar y ejecutar el módulo de reportes
    try:
        import importlib
        import reportes_ejecutivos
        
        if 'STREAMLIT_ENV' in os.environ:
            importlib.reload(reportes_ejecutivos)
        
        reportes_ejecutivos.main()
    
    except ImportError as e:
        st.error(f"❌ Error al importar el módulo de reportes: {e}")
        st.info("**Solución:** Asegúrese de que `reportes_ejecutivos.py` esté en el mismo directorio que `main.py`")
    except AttributeError:
        st.error("❌ Error: El módulo `reportes_ejecutivos.py` no tiene una función `main()`")
        st.info("**Solución:** Verifique que el archivo tiene la estructura correcta")
    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")
        st.exception(e)

def render_modulo_conciliacion():
    """Renderiza el módulo de Conciliación Financiera"""
    # Botón de regreso
    with st.sidebar:
        if st.button("◄ Volver al Inicio", use_container_width=True):
            st.session_state.modulo_actual = None
            st.rerun()
        st.markdown("---")
        st.markdown(f"👤 **Usuario:** {st.session_state.usuario_actual['nombre_completo']}")
        st.caption(f"Rol: {st.session_state.usuario_actual['rol']}")
    
    # Importar y ejecutar el módulo de conciliación
    try:
        import importlib
        import conciliacion
        
        # Recargar en desarrollo
        if 'STREAMLIT_ENV' in os.environ:
            importlib.reload(conciliacion)
        
        # Ejecutar función main
        conciliacion.main()
    
    except ImportError as e:
        st.error(f"❌ Error al importar el módulo de conciliación: {e}")
        st.info("**Solución:** Asegúrese de que `conciliacion.py` y `conciliacion_core.py` estén en el mismo directorio que `main.py`")
    except AttributeError:
        st.error("❌ Error: El módulo `conciliacion.py` no tiene una función `main()`")
        st.info("**Solución:** Verifique que el archivo tiene la estructura correcta con la función main() exportada")
    except Exception as e:
        st.error(f"❌ Error inesperado en conciliación: {e}")
        import traceback
        with st.expander("Ver detalles del error"):
            st.code(traceback.format_exc())

# ============================================================================
# MAIN - PUNTO DE ENTRADA
# ============================================================================

def main():
    """Función principal de la aplicación"""
    # Inicializar BD
    init_database()
    
    # Inicializar session state
    inicializar_session_state()
    
    # Router de módulos
    if st.session_state.modulo_actual is None:
        render_home()
    elif st.session_state.modulo_actual == 'cotizaciones':
        render_modulo_cotizaciones()
    elif st.session_state.modulo_actual == 'flujo_caja':
        render_modulo_flujo_caja()
    elif st.session_state.modulo_actual == 'multiproyecto':
        render_modulo_multiproyecto()
    elif st.session_state.modulo_actual == 'reportes':
        render_modulo_reportes()
    elif st.session_state.modulo_actual == 'conciliacion':
        render_modulo_conciliacion()
    else:
        st.error(f"Módulo '{st.session_state.modulo_actual}' no reconocido")
        if st.button("Volver al inicio"):
            st.session_state.modulo_actual = None
            st.rerun()

if __name__ == "__main__":
    main()
