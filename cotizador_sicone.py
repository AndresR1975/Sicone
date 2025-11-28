"""
SICONE - Sistema de Cotización v2.0
Versión completa basada en formato Excel real de SICONE
Autor: AI-MindNovation
Fecha: Noviembre 2025
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# ============================================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================================
st.set_page_config(
    page_title="SICONE v2.0 - Cotizador",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# ESTILOS CSS
# ============================================================================
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .section-title {
        font-size: 1.5rem;
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
        margin-top: 1.5rem;
    }
    .stExpander {
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# MODELOS DE DATOS
# ============================================================================

@dataclass
class ProyectoInfo:
    """Información general del proyecto"""
    nombre: str = ""
    cliente: str = ""
    direccion: str = ""
    telefono: str = ""
    business_manager: str = ""
    medio_contacto: str = ""
    area_base: float = 0.0
    area_cubierta: float = 0.0
    area_entrepiso: float = 0.0
    niveles: int = 1
    muro_tipo: str = "sencillo"
    fecha: datetime = field(default_factory=datetime.now)

@dataclass
class ItemDiseno:
    """Item de Diseños y Planificación (se multiplica por área_base)"""
    nombre: str
    precio_unitario: float = 0.0
    
    def calcular_subtotal(self, area_base: float) -> float:
        return area_base * self.precio_unitario

@dataclass
class ItemEstandar:
    """Item estándar con Materiales, Equipos y Mano de Obra"""
    nombre: str
    unidad: str
    cantidad: float = 0.0
    precio_materiales: float = 0.0
    precio_equipos: float = 0.0
    precio_mano_obra: float = 0.0
    
    def calcular_subtotal(self) -> float:
        return (
            self.cantidad * self.precio_materiales +
            self.cantidad * self.precio_equipos +
            self.cantidad * self.precio_mano_obra
        )

@dataclass
class ItemCimentacion:
    """Item de cimentación (cantidad × precio unitario)"""
    nombre: str
    unidad: str
    cantidad: float = 0.0
    precio_unitario: float = 0.0
    
    def calcular_subtotal(self) -> float:
        return self.cantidad * self.precio_unitario

@dataclass
class PersonalAdmin:
    """Personal administrativo con cálculo de prestaciones"""
    nombre: str
    cantidad: int = 1
    valor_mes: float = 0.0
    pct_prestaciones: float = 54.0  # %
    dedicacion: float = 0.5  # 0.0 - 1.0
    meses: int = 6
    
    def calcular_total(self) -> float:
        return (
            self.cantidad *
            self.valor_mes *
            (1 + self.pct_prestaciones / 100) *
            self.dedicacion *
            self.meses
        )

# ============================================================================
# INICIALIZACIÓN DE SESSION STATE
# ============================================================================

def inicializar_session_state():
    """Inicializa todas las variables de sesión"""
    
    if 'proyecto' not in st.session_state:
        st.session_state.proyecto = ProyectoInfo()
    
    # DISEÑOS Y PLANIFICACIÓN
    if 'disenos' not in st.session_state:
        st.session_state.disenos = {
            'Diseño Arquitectónico': ItemDiseno('Diseño Arquitectónico', 0.0),
            'Diseño Estructural': ItemDiseno('Diseño Estructural', 21000.0),
            'Desarrollo del Proyecto': ItemDiseno('Desarrollo del Proyecto', 18900.0),
            'Visita Técnica': ItemDiseno('Visita Técnica', 0.0)
        }
    
    # ESTRUCTURA
    if 'estructura' not in st.session_state:
        st.session_state.estructura = ItemEstandar(
            'Estructura General', 'gl', 1.03, 127386450, 0, 0
        )
    
    # MAMPOSTERÍA
    if 'mamposteria' not in st.session_state:
        st.session_state.mamposteria = ItemEstandar(
            'Mampostería', 'm²', 845.0, 67000, 7500, 45000
        )
    
    # MAMPOSTERÍA Y TECHOS (antes "Otros")
    if 'mamposteria_techos' not in st.session_state:
        st.session_state.mamposteria_techos = {
            'Cubierta, Superboard y Manto': ItemEstandar('Cubierta, Superboard y Manto', 'm²', 120.0, 175000, 5000, 40000),
            'Ruana': ItemEstandar('Ruana', 'ml', 0.0, 40000, 0, 20000),
            'Contramarcos - Ventana': ItemEstandar('Contramarcos - Ventana', 'ml', 0.0, 15000, 1500, 8500),
            'Contramarcos - Puerta': ItemEstandar('Contramarcos - Puerta', 'ml', 0.0, 15000, 1500, 8500),
            'Embudos y Boquillas': ItemEstandar('Embudos y Boquillas', 'und', 0.0, 60000, 0, 10000),
            'Cubierta, Superboard y Shingle': ItemEstandar('Cubierta, Superboard y Shingle', 'm²', 137.5, 210000, 5000, 50000),
            'Entrepiso Placa Fácil': ItemEstandar('Entrepiso Placa Fácil', 'm²', 159.02, 175000, 5000, 35000),
            'Canoas': ItemEstandar('Canoas', 'ml', 0.0, 85000, 10000, 35000),
            'Pérgolas y Estructura sin Techo': ItemEstandar('Pérgolas y Estructura sin Techo', 'm²', 108.16, 175000, 15000, 45000),
            'Tapacanal y Lagrimal': ItemEstandar('Tapacanal y Lagrimal', 'ml', 0.0, 80000, 5000, 35000)
        }
    
    # CIMENTACIONES
    if 'opcion_cimentacion' not in st.session_state:
        st.session_state.opcion_cimentacion = 'Opción 2'
    
    if 'cimentacion_opcion1' not in st.session_state:
        st.session_state.cimentacion_opcion1 = {
            'Pilas a 3m y 5m': ItemCimentacion('Pilas a 3m y 5m', 'und', 73, 1340000),
            'Cimentación Vigas y Losa': ItemCimentacion('Cimentación Vigas y Losa', 'm²', 385.06, 280000)
        }
    
    if 'cimentacion_opcion2' not in st.session_state:
        st.session_state.cimentacion_opcion2 = {
            'Pilotes de Apoyo': ItemCimentacion('Pilotes de Apoyo', 'und', 210, 320000),
            'Cimentación Vigas y Losa': ItemCimentacion('Cimentación Vigas y Losa', 'm²', 385.06, 280000)
        }
    
    # COMPLEMENTARIOS
    if 'complementarios' not in st.session_state:
        st.session_state.complementarios = {
            'Red Aguas Lluvias': ItemCimentacion('Red Aguas Lluvias', 'gl', 1, 6150000),
            'Red Hidrosanitaria': ItemCimentacion('Red Hidrosanitaria', 'gl', 1, 13520000),
            'Estructura Escalas Metálicas': ItemCimentacion('Estructura Escalas Metálicas', 'und', 2, 8600000),
            'Campamento y baño': ItemCimentacion('Campamento y baño', 'gl', 1, 3000000),
            'Cerramiento en tela': ItemCimentacion('Cerramiento en tela', 'ml', 200, 14500),
            'Canoa Metálica Calibre 24': ItemCimentacion('Canoa Metálica Calibre 24', 'ml', 51, 145000),
            'Ruana Metálica Calibre 24': ItemCimentacion('Ruana Metálica Calibre 24', 'ml', 62, 58000),
            'Revoque': ItemCimentacion('Revoque', 'm²', 1690, 32500),
            'Fajas, Ranuras y Filetes': ItemCimentacion('Fajas, Ranuras y Filetes', 'ml', 1859, 7000),
            'Otros conceptos': ItemCimentacion('Otros conceptos', 'gl', 0, 0)
        }
    
    # PERSONAL PROFESIONAL
    if 'personal_profesional' not in st.session_state:
        st.session_state.personal_profesional = {
            'Director de Obra': PersonalAdmin('Director de Obra', 1, 4407865, 54.0, 0.5, 6),
            'Supervisor Técnico': PersonalAdmin('Supervisor Técnico', 1, 1889085, 54.0, 0.3, 6),
            'Profesional Presupuesto': PersonalAdmin('Profesional Presupuesto', 1, 2896597, 54.0, 0.3, 6),
            'Arquitecto Diseñador': PersonalAdmin('Arquitecto Diseñador', 1, 1259390, 54.0, 0.3, 3),
            'Oficial Obra': PersonalAdmin('Oficial Obra', 1, 2266902, 54.0, 0.3, 3),
            'Ayudante de Obra': PersonalAdmin('Ayudante de Obra', 1, 811488, 54.0, 0.2, 2)
        }
    
    # PERSONAL ADMINISTRATIVO
    if 'personal_administrativo' not in st.session_state:
        st.session_state.personal_administrativo = {
            'Contador': PersonalAdmin('Contador', 1, 3000000, 54.0, 0.2, 6),
            'Auxiliar Contable': PersonalAdmin('Auxiliar Contable', 1, 1500000, 54.0, 0.3, 6),
            'Auxiliar Administrativa': PersonalAdmin('Auxiliar Administrativa', 1, 1200000, 54.0, 0.5, 6)
        }
    
    # OTROS CONCEPTOS ADMINISTRACIÓN
    if 'otros_admin' not in st.session_state:
        st.session_state.otros_admin = {
            'Pólizas de Seguros': 3000000,
            'Pagos Provisionales': 0,
            'Pagos Mensuales': 7511240,
            'Dotaciones': 0,
            'Pagos de Obra': 0,
            'SISO': 3000000,
            'Asesores Externos': 0,
            'Impuestos': 18199247,
            'Costos Fijos': 4989444,
            'Descuentos': 0,
            'Pagos a Terceros': 0
        }
    
    # CONFIGURACIÓN AIU
    if 'config_aiu' not in st.session_state:
        st.session_state.config_aiu = {
            'Comisión de Ventas (%)': 3.0,
            'Imprevistos (%)': 5.0,
            'Administración (%)': 12.0,
            'Logística (%)': 2.0,
            'Utilidad (%)': 15.0
        }
    
    # % AIU CIMENTACIONES Y COMPLEMENTARIOS
    if 'aiu_cimentacion' not in st.session_state:
        st.session_state.aiu_cimentacion = {
            'pct_comision': 3.0,
            'pct_aiu': 47.0,
            'logistica': 0
        }
    
    if 'aiu_complementarios' not in st.session_state:
        st.session_state.aiu_complementarios = {
            'pct_comision': 0.0,
            'pct_aiu': 15.0,
            'logistica': 0
        }

# ============================================================================
# FUNCIONES DE CÁLCULO
# ============================================================================

def calcular_disenos():
    """Calcula subtotal de Diseños (usa SOLO área_base)"""
    area_base = st.session_state.proyecto.area_base
    total = sum([
        item.calcular_subtotal(area_base) 
        for item in st.session_state.disenos.values()
    ])
    return total

def calcular_estructura():
    """Calcula subtotal de Estructura"""
    return st.session_state.estructura.calcular_subtotal()

def calcular_mamposteria():
    """Calcula subtotal de Mampostería"""
    return st.session_state.mamposteria.calcular_subtotal()

def calcular_mamposteria_techos():
    """Calcula subtotal de Mampostería y Techos"""
    total = sum([
        item.calcular_subtotal() 
        for item in st.session_state.mamposteria_techos.values()
    ])
    return total

def calcular_cimentacion():
    """Calcula total de cimentación según opción seleccionada"""
    opcion = st.session_state.opcion_cimentacion
    
    if opcion == 'Opción 1':
        items = st.session_state.cimentacion_opcion1
    else:
        items = st.session_state.cimentacion_opcion2
    
    subtotal = sum([item.calcular_subtotal() for item in items.values()])
    
    # Agregar AIU específico de cimentación
    comision = subtotal * (st.session_state.aiu_cimentacion['pct_comision'] / 100)
    aiu = subtotal * (st.session_state.aiu_cimentacion['pct_aiu'] / 100)
    logistica = st.session_state.aiu_cimentacion['logistica']
    
    total = subtotal + comision + aiu + logistica
    
    return {
        'subtotal': subtotal,
        'comision': comision,
        'aiu': aiu,
        'logistica': logistica,
        'total': total
    }

def calcular_complementarios():
    """Calcula total de complementarios"""
    subtotal = sum([
        item.calcular_subtotal() 
        for item in st.session_state.complementarios.values()
    ])
    
    # Agregar AIU específico de complementarios
    comision = subtotal * (st.session_state.aiu_complementarios['pct_comision'] / 100)
    aiu = subtotal * (st.session_state.aiu_complementarios['pct_aiu'] / 100)
    logistica = st.session_state.aiu_complementarios['logistica']
    
    total = subtotal + comision + aiu + logistica
    
    return {
        'subtotal': subtotal,
        'comision': comision,
        'aiu': aiu,
        'logistica': logistica,
        'total': total
    }

def calcular_administracion_detallada():
    """Calcula administración detallada"""
    total_prof = sum([
        p.calcular_total() 
        for p in st.session_state.personal_profesional.values()
    ])
    
    total_admin = sum([
        p.calcular_total() 
        for p in st.session_state.personal_administrativo.values()
    ])
    
    total_otros = sum(st.session_state.otros_admin.values())
    
    total = total_prof + total_admin + total_otros
    
    return {
        'personal_profesional': total_prof,
        'personal_administrativo': total_admin,
        'otros_conceptos': total_otros,
        'total': total
    }

def calcular_resumen_global():
    """Calcula resumen global del proyecto"""
    
    # COTIZACIÓN 1: Diseños + Estructura + Mampostería + Mampostería y Techos
    disenos = calcular_disenos()
    estructura = calcular_estructura()
    mamposteria = calcular_mamposteria()
    mamposteria_techos = calcular_mamposteria_techos()
    
    costos_directos_cot1 = disenos + estructura + mamposteria + mamposteria_techos
    
    # COTIZACIÓN 2: Cimentaciones + Complementarios
    cimentacion = calcular_cimentacion()
    complementarios = calcular_complementarios()
    
    costos_directos_cot2 = cimentacion['total'] + complementarios['total']
    
    # TOTAL COSTOS DIRECTOS (base para AIU general)
    # IMPORTANTE: Para AIU general, NO incluir AIU específico de cimentación/complementarios
    total_base_aiu = disenos + estructura + mamposteria + mamposteria_techos
    
    # AIU GENERAL (se aplica solo sobre Cotización 1)
    admin_detallada = calcular_administracion_detallada()
    
    # Usuario puede modificar el % de administración
    pct_admin_calculado = (admin_detallada['total'] / total_base_aiu * 100) if total_base_aiu > 0 else 0
    pct_admin_final = st.session_state.config_aiu['Administración (%)']
    
    comision_ventas = total_base_aiu * (st.session_state.config_aiu['Comisión de Ventas (%)'] / 100)
    imprevistos = total_base_aiu * (st.session_state.config_aiu['Imprevistos (%)'] / 100)
    administracion = total_base_aiu * (pct_admin_final / 100)
    logistica = total_base_aiu * (st.session_state.config_aiu['Logística (%)'] / 100)
    utilidad = total_base_aiu * (st.session_state.config_aiu['Utilidad (%)'] / 100)
    
    total_aiu_general = comision_ventas + imprevistos + administracion + logistica + utilidad
    
    # TOTALES POR COTIZACIÓN
    total_cot1 = costos_directos_cot1 + total_aiu_general
    total_cot2 = cimentacion['total'] + complementarios['total']
    
    # TOTAL PROYECTO
    total_proyecto = total_cot1 + total_cot2
    
    # PRECIO POR M²
    area_base = st.session_state.proyecto.area_base
    precio_m2 = total_proyecto / area_base if area_base > 0 else 0
    
    return {
        'cotizacion1': {
            'disenos': disenos,
            'estructura': estructura,
            'mamposteria': mamposteria,
            'mamposteria_techos': mamposteria_techos,
            'costos_directos': costos_directos_cot1,
            'aiu': {
                'comision_ventas': comision_ventas,
                'imprevistos': imprevistos,
                'administracion': administracion,
                'logistica': logistica,
                'utilidad': utilidad,
                'total': total_aiu_general
            },
            'total': total_cot1
        },
        'cotizacion2': {
            'cimentacion': cimentacion,
            'complementarios': complementarios,
            'total': total_cot2
        },
        'administracion_detallada': admin_detallada,
        'pct_admin_calculado': pct_admin_calculado,
        'total_proyecto': total_proyecto,
        'precio_m2': precio_m2
    }

# ============================================================================
# INTERFAZ - SIDEBAR
# ============================================================================

def render_sidebar():
    """Render sidebar con información del proyecto"""
    with st.sidebar:
        st.markdown("### 📋 Información del Proyecto")
        
        st.session_state.proyecto.nombre = st.text_input(
            "Nombre del Proyecto", 
            value=st.session_state.proyecto.nombre
        )
        
        st.session_state.proyecto.cliente = st.text_input(
            "Cliente", 
            value=st.session_state.proyecto.cliente
        )
        
        st.session_state.proyecto.direccion = st.text_input(
            "Dirección", 
            value=st.session_state.proyecto.direccion
        )
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.proyecto.telefono = st.text_input(
                "Teléfono", 
                value=st.session_state.proyecto.telefono
            )
        with col2:
            st.session_state.proyecto.business_manager = st.text_input(
                "Business Manager", 
                value=st.session_state.proyecto.business_manager
            )
        
        st.session_state.proyecto.medio_contacto = st.text_input(
            "Medio de Contacto", 
            value=st.session_state.proyecto.medio_contacto
        )
        
        st.markdown("---")
        st.markdown("### 📐 Áreas del Proyecto")
        
        st.session_state.proyecto.area_base = st.number_input(
            "Área de la Base (m²)",
            min_value=0.0,
            value=st.session_state.proyecto.area_base,
            step=0.01,
            help="Área principal que se usa como multiplicador en Diseños"
        )
        
        st.session_state.proyecto.area_cubierta = st.number_input(
            "Área de Cubierta (m²)",
            min_value=0.0,
            value=st.session_state.proyecto.area_cubierta,
            step=0.01
        )
        
        st.session_state.proyecto.area_entrepiso = st.number_input(
            "Área de Entrepiso (m²)",
            min_value=0.0,
            value=st.session_state.proyecto.area_entrepiso,
            step=0.01
        )
        
        st.session_state.proyecto.niveles = st.number_input(
            "Niveles",
            min_value=1,
            value=st.session_state.proyecto.niveles
        )
        
        st.session_state.proyecto.muro_tipo = st.selectbox(
            "Tipo de Muro",
            options=["sencillo", "doble"],
            index=0 if st.session_state.proyecto.muro_tipo == "sencillo" else 1
        )
        
        st.markdown("---")
        st.markdown("### 💼 Configuración AIU General")
        st.caption("Aplica a Diseños + Estructura + Mampostería + Techos")
        
        for concepto in st.session_state.config_aiu.keys():
            st.session_state.config_aiu[concepto] = st.number_input(
                concepto,
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.config_aiu[concepto],
                step=0.5,
                format="%.1f"
            )

# ============================================================================
# INTERFAZ - TAB 1: DISEÑOS, ESTRUCTURA Y MAMPOSTERÍA
# ============================================================================

def render_tab_disenos_estructura():
    """Tab 1: Diseños, Estructura, Mampostería y Techos"""
    
    st.markdown('<h2 class="section-title">📐 Diseños, Estructura, Mampostería y Techos</h2>', unsafe_allow_html=True)
    
    # DISEÑOS Y PLANIFICACIÓN
    with st.expander("📐 Diseños y Planificación", expanded=True):
        st.caption(f"Los valores se multiplican por el Área de la Base: {st.session_state.proyecto.area_base:.2f} m²")
        
        df_disenos_data = []
        for nombre, item in st.session_state.disenos.items():
            df_disenos_data.append({
                'Ítem': nombre,
                'Precio Unitario ($/m²)': item.precio_unitario,
                'Subtotal': item.calcular_subtotal(st.session_state.proyecto.area_base)
            })
        
        df_disenos = pd.DataFrame(df_disenos_data)
        
        edited_disenos = st.data_editor(
            df_disenos,
            column_config={
                'Precio Unitario ($/m²)': st.column_config.NumberColumn(
                    format="$%.2f",
                    min_value=0
                ),
                'Subtotal': st.column_config.NumberColumn(
                    format="$%.2f",
                    disabled=True
                )
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Actualizar session state
        for idx, row in edited_disenos.iterrows():
            nombre = row['Ítem']
            st.session_state.disenos[nombre].precio_unitario = row['Precio Unitario ($/m²)']
        
        total_disenos = calcular_disenos()
        st.metric("**Total Diseños y Planificación**", f"${total_disenos:,.2f}")
    
    # ESTRUCTURA
    with st.expander("🏗️ Estructura", expanded=True):
        item = st.session_state.estructura
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            item.cantidad = st.number_input("Cantidad", value=item.cantidad, min_value=0.0, step=0.01, key='est_cant')
        with col2:
            item.precio_materiales = st.number_input("Materiales ($)", value=item.precio_materiales, min_value=0.0, step=1000.0, key='est_mat')
        with col3:
            item.precio_equipos = st.number_input("Equipos ($)", value=item.precio_equipos, min_value=0.0, step=1000.0, key='est_eq')
        with col4:
            item.precio_mano_obra = st.number_input("Mano de Obra ($)", value=item.precio_mano_obra, min_value=0.0, step=1000.0, key='est_mo')
        
        total_estructura = calcular_estructura()
        st.metric("**Total Estructura**", f"${total_estructura:,.2f}")
    
    # MAMPOSTERÍA
    with st.expander("🧱 Mampostería", expanded=True):
        item = st.session_state.mamposteria
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            item.cantidad = st.number_input("Cantidad (m²)", value=item.cantidad, min_value=0.0, step=0.01, key='mam_cant')
        with col2:
            item.precio_materiales = st.number_input("Materiales ($)", value=item.precio_materiales, min_value=0.0, step=1000.0, key='mam_mat')
        with col3:
            item.precio_equipos = st.number_input("Equipos ($)", value=item.precio_equipos, min_value=0.0, step=1000.0, key='mam_eq')
        with col4:
            item.precio_mano_obra = st.number_input("Mano de Obra ($)", value=item.precio_mano_obra, min_value=0.0, step=1000.0, key='mam_mo')
        
        total_mamposteria = calcular_mamposteria()
        st.metric("**Total Mampostería**", f"${total_mamposteria:,.2f}")
    
    # MAMPOSTERÍA Y TECHOS
    with st.expander("🏠 Mampostería y Techos", expanded=True):
        
        df_mt_data = []
        for nombre, item in st.session_state.mamposteria_techos.items():
            df_mt_data.append({
                'Ítem': nombre,
                'Unidad': item.unidad,
                'Cantidad': item.cantidad,
                'Materiales': item.precio_materiales,
                'Equipos': item.precio_equipos,
                'Mano de Obra': item.precio_mano_obra,
                'Subtotal': item.calcular_subtotal()
            })
        
        df_mt = pd.DataFrame(df_mt_data)
        
        edited_mt = st.data_editor(
            df_mt,
            column_config={
                'Unidad': st.column_config.TextColumn(disabled=True),
                'Cantidad': st.column_config.NumberColumn(min_value=0, format="%.2f"),
                'Materiales': st.column_config.NumberColumn(min_value=0, format="$%.2f"),
                'Equipos': st.column_config.NumberColumn(min_value=0, format="$%.2f"),
                'Mano de Obra': st.column_config.NumberColumn(min_value=0, format="$%.2f"),
                'Subtotal': st.column_config.NumberColumn(format="$%.2f", disabled=True)
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Actualizar session state
        for idx, row in edited_mt.iterrows():
            nombre = row['Ítem']
            st.session_state.mamposteria_techos[nombre].cantidad = row['Cantidad']
            st.session_state.mamposteria_techos[nombre].precio_materiales = row['Materiales']
            st.session_state.mamposteria_techos[nombre].precio_equipos = row['Equipos']
            st.session_state.mamposteria_techos[nombre].precio_mano_obra = row['Mano de Obra']
        
        total_mt = calcular_mamposteria_techos()
        st.metric("**Total Mampostería y Techos**", f"${total_mt:,.2f}")

# ============================================================================
# INTERFAZ - TAB 2: CIMENTACIONES
# ============================================================================

def render_tab_cimentaciones():
    """Tab 2: Cimentaciones"""
    
    st.markdown('<h2 class="section-title">⚙️ Cimentaciones</h2>', unsafe_allow_html=True)
    
    st.session_state.opcion_cimentacion = st.radio(
        "Seleccione la opción de cimentación:",
        options=['Opción 1', 'Opción 2'],
        index=0 if st.session_state.opcion_cimentacion == 'Opción 1' else 1,
        horizontal=True
    )
    
    if st.session_state.opcion_cimentacion == 'Opción 1':
        st.markdown("### Opción 1: Zapatas y Vigas de Concreto")
        items = st.session_state.cimentacion_opcion1
    else:
        st.markdown("### Opción 2: Pilotes de Apoyo")
        items = st.session_state.cimentacion_opcion2
    
    df_cim_data = []
    for nombre, item in items.items():
        df_cim_data.append({
            'Ítem': nombre,
            'Unidad': item.unidad,
            'Cantidad': item.cantidad,
            'Precio Unitario': item.precio_unitario,
            'Subtotal': item.calcular_subtotal()
        })
    
    df_cim = pd.DataFrame(df_cim_data)
    
    edited_cim = st.data_editor(
        df_cim,
        column_config={
            'Unidad': st.column_config.TextColumn(disabled=True),
            'Cantidad': st.column_config.NumberColumn(min_value=0, format="%.2f"),
            'Precio Unitario': st.column_config.NumberColumn(min_value=0, format="$%.2f"),
            'Subtotal': st.column_config.NumberColumn(format="$%.2f", disabled=True)
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Actualizar session state
    for idx, row in edited_cim.iterrows():
        nombre = row['Ítem']
        items[nombre].cantidad = row['Cantidad']
        items[nombre].precio_unitario = row['Precio Unitario']
    
    st.markdown("---")
    st.markdown("### Configuración AIU Cimentaciones")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.session_state.aiu_cimentacion['pct_comision'] = st.number_input(
            "Comisión (%)",
            value=st.session_state.aiu_cimentacion['pct_comision'],
            min_value=0.0,
            max_value=100.0,
            step=0.5,
            key='cim_com'
        )
    with col2:
        st.session_state.aiu_cimentacion['pct_aiu'] = st.number_input(
            "AIU (%)",
            value=st.session_state.aiu_cimentacion['pct_aiu'],
            min_value=0.0,
            max_value=100.0,
            step=0.5,
            key='cim_aiu'
        )
    with col3:
        st.session_state.aiu_cimentacion['logistica'] = st.number_input(
            "Logística ($)",
            value=st.session_state.aiu_cimentacion['logistica'],
            min_value=0.0,
            step=1000.0,
            key='cim_log'
        )
    
    cimentacion = calcular_cimentacion()
    
    st.markdown("### Resumen Cimentación")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Subtotal", f"${cimentacion['subtotal']:,.2f}")
    col2.metric("Comisión", f"${cimentacion['comision']:,.2f}")
    col3.metric("AIU", f"${cimentacion['aiu']:,.2f}")
    col4.metric("**TOTAL**", f"${cimentacion['total']:,.2f}")

# ============================================================================
# INTERFAZ - TAB 3: COMPLEMENTARIOS
# ============================================================================

def render_tab_complementarios():
    """Tab 3: Complementarios"""
    
    st.markdown('<h2 class="section-title">🔧 Complementarios</h2>', unsafe_allow_html=True)
    
    df_comp_data = []
    for nombre, item in st.session_state.complementarios.items():
        df_comp_data.append({
            'Ítem': nombre,
            'Unidad': item.unidad,
            'Cantidad': item.cantidad,
            'Precio Unitario': item.precio_unitario,
            'Subtotal': item.calcular_subtotal()
        })
    
    df_comp = pd.DataFrame(df_comp_data)
    
    edited_comp = st.data_editor(
        df_comp,
        column_config={
            'Unidad': st.column_config.TextColumn(disabled=True),
            'Cantidad': st.column_config.NumberColumn(min_value=0, format="%.2f"),
            'Precio Unitario': st.column_config.NumberColumn(min_value=0, format="$%.2f"),
            'Subtotal': st.column_config.NumberColumn(format="$%.2f", disabled=True)
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Actualizar session state
    for idx, row in edited_comp.iterrows():
        nombre = row['Ítem']
        st.session_state.complementarios[nombre].cantidad = row['Cantidad']
        st.session_state.complementarios[nombre].precio_unitario = row['Precio Unitario']
    
    st.markdown("---")
    st.markdown("### Configuración AIU Complementarios")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.session_state.aiu_complementarios['pct_comision'] = st.number_input(
            "Comisión (%)",
            value=st.session_state.aiu_complementarios['pct_comision'],
            min_value=0.0,
            max_value=100.0,
            step=0.5,
            key='comp_com'
        )
    with col2:
        st.session_state.aiu_complementarios['pct_aiu'] = st.number_input(
            "AIU (%)",
            value=st.session_state.aiu_complementarios['pct_aiu'],
            min_value=0.0,
            max_value=100.0,
            step=0.5,
            key='comp_aiu'
        )
    with col3:
        st.session_state.aiu_complementarios['logistica'] = st.number_input(
            "Logística ($)",
            value=st.session_state.aiu_complementarios['logistica'],
            min_value=0.0,
            step=1000.0,
            key='comp_log'
        )
    
    complementarios = calcular_complementarios()
    
    st.markdown("### Resumen Complementarios")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Subtotal", f"${complementarios['subtotal']:,.2f}")
    col2.metric("Comisión", f"${complementarios['comision']:,.2f}")
    col3.metric("AIU", f"${complementarios['aiu']:,.2f}")
    col4.metric("**TOTAL**", f"${complementarios['total']:,.2f}")

# ============================================================================
# INTERFAZ - TAB 4: ADMINISTRACIÓN
# ============================================================================

def render_tab_administracion():
    """Tab 4: Administración Detallada"""
    
    st.markdown('<h2 class="section-title">💼 Administración</h2>', unsafe_allow_html=True)
    
    subtab1, subtab2, subtab3, subtab4 = st.tabs([
        "Personal Profesional", 
        "Personal Administrativo", 
        "Otros Conceptos",
        "Resumen"
    ])
    
    # SUB-TAB 1: PERSONAL PROFESIONAL
    with subtab1:
        st.markdown("### Personal Profesional y Técnico")
        
        df_prof_data = []
        for nombre, p in st.session_state.personal_profesional.items():
            df_prof_data.append({
                'Nombre': nombre,
                'Cant': p.cantidad,
                'Valor/Mes': p.valor_mes,
                '% Prest': p.pct_prestaciones,
                'Dedicación': p.dedicacion,
                'Meses': p.meses,
                'Total': p.calcular_total()
            })
        
        df_prof = pd.DataFrame(df_prof_data)
        
        edited_prof = st.data_editor(
            df_prof,
            column_config={
                'Nombre': st.column_config.TextColumn(disabled=True),
                'Cant': st.column_config.NumberColumn(min_value=0, format="%d"),
                'Valor/Mes': st.column_config.NumberColumn(min_value=0, format="$%.2f"),
                '% Prest': st.column_config.NumberColumn(min_value=0, max_value=100, format="%.1f"),
                'Dedicación': st.column_config.NumberColumn(min_value=0.0, max_value=1.0, format="%.2f"),
                'Meses': st.column_config.NumberColumn(min_value=0, format="%d"),
                'Total': st.column_config.NumberColumn(format="$%.2f", disabled=True)
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Actualizar session state
        for idx, row in edited_prof.iterrows():
            nombre = row['Nombre']
            p = st.session_state.personal_profesional[nombre]
            p.cantidad = int(row['Cant'])
            p.valor_mes = row['Valor/Mes']
            p.pct_prestaciones = row['% Prest']
            p.dedicacion = row['Dedicación']
            p.meses = int(row['Meses'])
    
    # SUB-TAB 2: PERSONAL ADMINISTRATIVO
    with subtab2:
        st.markdown("### Personal Administrativo")
        
        df_admin_data = []
        for nombre, p in st.session_state.personal_administrativo.items():
            df_admin_data.append({
                'Nombre': nombre,
                'Cant': p.cantidad,
                'Valor/Mes': p.valor_mes,
                '% Prest': p.pct_prestaciones,
                'Dedicación': p.dedicacion,
                'Meses': p.meses,
                'Total': p.calcular_total()
            })
        
        df_admin = pd.DataFrame(df_admin_data)
        
        edited_admin = st.data_editor(
            df_admin,
            column_config={
                'Nombre': st.column_config.TextColumn(disabled=True),
                'Cant': st.column_config.NumberColumn(min_value=0, format="%d"),
                'Valor/Mes': st.column_config.NumberColumn(min_value=0, format="$%.2f"),
                '% Prest': st.column_config.NumberColumn(min_value=0, max_value=100, format="%.1f"),
                'Dedicación': st.column_config.NumberColumn(min_value=0.0, max_value=1.0, format="%.2f"),
                'Meses': st.column_config.NumberColumn(min_value=0, format="%d"),
                'Total': st.column_config.NumberColumn(format="$%.2f", disabled=True)
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Actualizar session state
        for idx, row in edited_admin.iterrows():
            nombre = row['Nombre']
            p = st.session_state.personal_administrativo[nombre]
            p.cantidad = int(row['Cant'])
            p.valor_mes = row['Valor/Mes']
            p.pct_prestaciones = row['% Prest']
            p.dedicacion = row['Dedicación']
            p.meses = int(row['Meses'])
    
    # SUB-TAB 3: OTROS CONCEPTOS
    with subtab3:
        st.markdown("### Otros Conceptos Administrativos")
        
        df_otros_data = []
        for nombre, valor in st.session_state.otros_admin.items():
            df_otros_data.append({
                'Concepto': nombre,
                'Valor': valor
            })
        
        df_otros = pd.DataFrame(df_otros_data)
        
        edited_otros = st.data_editor(
            df_otros,
            column_config={
                'Concepto': st.column_config.TextColumn(disabled=True),
                'Valor': st.column_config.NumberColumn(min_value=0, format="$%.2f")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Actualizar session state
        for idx, row in edited_otros.iterrows():
            nombre = row['Concepto']
            st.session_state.otros_admin[nombre] = row['Valor']
    
    # SUB-TAB 4: RESUMEN
    with subtab4:
        st.markdown("### Resumen Administración")
        
        admin_det = calcular_administracion_detallada()
        resumen = calcular_resumen_global()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Personal Profesional", f"${admin_det['personal_profesional']:,.2f}")
        col2.metric("Personal Administrativo", f"${admin_det['personal_administrativo']:,.2f}")
        col3.metric("Otros Conceptos", f"${admin_det['otros_conceptos']:,.2f}")
        col4.metric("**TOTAL**", f"${admin_det['total']:,.2f}")
        
        st.markdown("---")
        
        st.info(f"""
        **% Administración Calculado:** {resumen['pct_admin_calculado']:.2f}%  
        **% Administración Configurado (Sidebar):** {st.session_state.config_aiu['Administración (%)']:.2f}%
        
        💡 Puedes modificar el % en el sidebar si deseas usar un valor diferente al calculado.
        """)

# ============================================================================
# INTERFAZ - TAB 5: RESUMEN GLOBAL
# ============================================================================

def render_tab_resumen():
    """Tab 5: Resumen Global"""
    
    st.markdown('<h2 class="section-title">📊 Resumen Global del Proyecto</h2>', unsafe_allow_html=True)
    
    resumen = calcular_resumen_global()
    
    # MÉTRICAS PRINCIPALES
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Proyecto", f"${resumen['total_proyecto']:,.2f}")
    col2.metric("📐 Precio por m²", f"${resumen['precio_m2']:,.2f}")
    col3.metric("🏗️ Área Base", f"{st.session_state.proyecto.area_base:.2f} m²")
    
    st.markdown("---")
    
    # DOS COTIZACIONES
    col_cot1, col_cot2 = st.columns(2)
    
    with col_cot1:
        st.markdown("### 📋 Cotización 1: Diseños + Estructura + Mampostería")
        
        cot1 = resumen['cotizacion1']
        
        st.markdown("**Costos Directos:**")
        st.write(f"- Diseños: ${cot1['disenos']:,.2f}")
        st.write(f"- Estructura: ${cot1['estructura']:,.2f}")
        st.write(f"- Mampostería: ${cot1['mamposteria']:,.2f}")
        st.write(f"- Mampostería y Techos: ${cot1['mamposteria_techos']:,.2f}")
        st.write(f"**Subtotal Costos Directos: ${cot1['costos_directos']:,.2f}**")
        
        st.markdown("**AIU:**")
        st.write(f"- Comisión Ventas: ${cot1['aiu']['comision_ventas']:,.2f}")
        st.write(f"- Imprevistos: ${cot1['aiu']['imprevistos']:,.2f}")
        st.write(f"- Administración: ${cot1['aiu']['administracion']:,.2f}")
        st.write(f"- Logística: ${cot1['aiu']['logistica']:,.2f}")
        st.write(f"- Utilidad: ${cot1['aiu']['utilidad']:,.2f}")
        st.write(f"**Total AIU: ${cot1['aiu']['total']:,.2f}**")
        
        st.success(f"### **TOTAL COTIZACIÓN 1: ${cot1['total']:,.2f}**")
    
    with col_cot2:
        st.markdown("### 📋 Cotización 2: Cimentaciones + Complementarios")
        
        cot2 = resumen['cotizacion2']
        
        st.markdown("**Cimentaciones:**")
        st.write(f"- Subtotal: ${cot2['cimentacion']['subtotal']:,.2f}")
        st.write(f"- Comisión: ${cot2['cimentacion']['comision']:,.2f}")
        st.write(f"- AIU: ${cot2['cimentacion']['aiu']:,.2f}")
        st.write(f"**Total Cimentación: ${cot2['cimentacion']['total']:,.2f}**")
        
        st.markdown("**Complementarios:**")
        st.write(f"- Subtotal: ${cot2['complementarios']['subtotal']:,.2f}")
        st.write(f"- Comisión: ${cot2['complementarios']['comision']:,.2f}")
        st.write(f"- AIU: ${cot2['complementarios']['aiu']:,.2f}")
        st.write(f"**Total Complementarios: ${cot2['complementarios']['total']:,.2f}**")
        
        st.success(f"### **TOTAL COTIZACIÓN 2: ${cot2['total']:,.2f}**")
    
    st.markdown("---")
    
    # GRÁFICOS
    col_grafico1, col_grafico2 = st.columns(2)
    
    with col_grafico1:
        st.markdown("#### Distribución Costos Directos")
        
        categorias_costos = {
            'Diseños': resumen['cotizacion1']['disenos'],
            'Estructura': resumen['cotizacion1']['estructura'],
            'Mampostería': resumen['cotizacion1']['mamposteria'],
            'Mampostería y Techos': resumen['cotizacion1']['mamposteria_techos'],
            'Cimentaciones': resumen['cotizacion2']['cimentacion']['subtotal'],
            'Complementarios': resumen['cotizacion2']['complementarios']['subtotal']
        }
        
        df_costos = pd.DataFrame([
            {'Categoría': k, 'Valor': v} 
            for k, v in categorias_costos.items() if v > 0
        ])
        
        if not df_costos.empty:
            fig_pie = px.pie(
                df_costos,
                values='Valor',
                names='Categoría',
                title='Costos por Categoría'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_grafico2:
        st.markdown("#### Comparación Cotizaciones")
        
        df_comparacion = pd.DataFrame([
            {'Cotización': 'Cotización 1', 'Monto': resumen['cotizacion1']['total']},
            {'Cotización': 'Cotización 2', 'Monto': resumen['cotizacion2']['total']}
        ])
        
        fig_bar = px.bar(
            df_comparacion,
            x='Cotización',
            y='Monto',
            title='Comparación entre Cotizaciones',
            text='Monto'
        )
        fig_bar.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)

# ============================================================================
# INTERFAZ - TAB 6: EXPORTAR
# ============================================================================

def render_tab_exportar():
    """Tab 6: Exportar"""
    
    st.markdown('<h2 class="section-title">📥 Exportar Cotización</h2>', unsafe_allow_html=True)
    
    resumen = calcular_resumen_global()
    
    st.markdown("### 📄 Vista Previa")
    
    st.markdown(f"""
    **Proyecto:** {st.session_state.proyecto.nombre}  
    **Cliente:** {st.session_state.proyecto.cliente}  
    **Dirección:** {st.session_state.proyecto.direccion}  
    **Área Base:** {st.session_state.proyecto.area_base:.2f} m²  
    
    ---
    
    **Cotización 1 (Diseños + Estructura + Mampostería):** ${resumen['cotizacion1']['total']:,.2f}  
    **Cotización 2 (Cimentaciones + Complementarios):** ${resumen['cotizacion2']['total']:,.2f}  
    **TOTAL PROYECTO:** ${resumen['total_proyecto']:,.2f}  
    **Precio por m²:** ${resumen['precio_m2']:,.2f}
    """)
    
    st.markdown("---")
    
    # GENERAR EXCEL (simplificado por ahora)
    if st.button("📥 Generar y Descargar Excel", type="primary"):
        st.info("Funcionalidad de exportación Excel en desarrollo. Por ahora usa el resumen visual.")

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Aplicación principal"""
    
    inicializar_session_state()
    
    # TÍTULO
    st.markdown('<h1 class="main-title">🏗️ SICONE v2.0 - Sistema de Cotización</h1>', unsafe_allow_html=True)
    
    # SIDEBAR
    render_sidebar()
    
    # TABS PRINCIPALES
    tabs = st.tabs([
        "📐 Diseños y Estructura",
        "⚙️ Cimentaciones",
        "🔧 Complementarios",
        "💼 Administración",
        "📊 Resumen",
        "📥 Exportar"
    ])
    
    with tabs[0]:
        render_tab_disenos_estructura()
    
    with tabs[1]:
        render_tab_cimentaciones()
    
    with tabs[2]:
        render_tab_complementarios()
    
    with tabs[3]:
        render_tab_administracion()
    
    with tabs[4]:
        render_tab_resumen()
    
    with tabs[5]:
        render_tab_exportar()

if __name__ == "__main__":
    main()
