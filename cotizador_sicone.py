"""
SICONE - Sistema de Cotización para Construcción
Versión: 1.0 - MVP Streamlit
Autor: AI-MindNovation
Fecha: Noviembre 2025

Este módulo permite crear cotizaciones estructuradas para proyectos de construcción
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go

# ============================================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================================
st.set_page_config(
    page_title="SICONE - Cotizador",
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
        margin-bottom: 2rem;
    }
    .section-title {
        font-size: 1.8rem;
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3498db;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# ESTRUCTURA DE DATOS (basada en Excel de SICONE)
# ============================================================================

# Categorías principales de construcción
CATEGORIAS_CONSTRUCCION = {
    "Diseños y Planificación": {
        "items": [
            "Diseño Arquitectónico",
            "Diseño Estructural",
            "Diseño de Redes",
            "Estudio de Suelos",
            "Topografía",
            "Licencias y Permisos"
        ],
        "unidad_default": "gl"
    },
    "Estructura": {
        "items": [
            "Cimentación",
            "Columnas",
            "Vigas",
            "Placa de Entrepiso",
            "Escaleras",
            "Acero de Refuerzo"
        ],
        "unidad_default": "m3"
    },
    "Mampostería": {
        "items": [
            "Muro Exterior",
            "Muro Interior",
            "Dinteles",
            "Remates",
            "Enchapes"
        ],
        "unidad_default": "m2"
    },
    "Cubierta": {
        "items": [
            "Estructura de Cubierta",
            "Teja/Superboard",
            "Manto",
            "Shingle",
            "Impermeabilización"
        ],
        "unidad_default": "m2"
    },
    "Instalaciones": {
        "items": [
            "Eléctrica",
            "Hidráulica",
            "Sanitaria",
            "Gas",
            "Telecomunicaciones"
        ],
        "unidad_default": "pt"
    },
    "Acabados": {
        "items": [
            "Pisos",
            "Pañetes",
            "Pintura",
            "Carpintería Metálica",
            "Carpintería de Madera"
        ],
        "unidad_default": "m2"
    }
}

# Conceptos adicionales (AIU)
CONCEPTOS_AIU = [
    "Comisión de Ventas",
    "Imprevistos",
    "Administración",
    "Logística",
    "Utilidad"
]

# Porcentajes sugeridos para AIU (editables)
PORCENTAJES_AIU_DEFAULT = {
    "Comisión de Ventas": 3.0,
    "Imprevistos": 5.0,
    "Administración": 12.0,
    "Logística": 2.0,
    "Utilidad": 15.0
}

# ============================================================================
# FUNCIONES DE NEGOCIO
# ============================================================================

def inicializar_session_state():
    """Inicializa variables de sesión"""
    if 'cotizacion' not in st.session_state:
        st.session_state.cotizacion = {
            'proyecto': {},
            'items': [],
            'aiu': {}
        }
    
    if 'contador_items' not in st.session_state:
        st.session_state.contador_items = 0

def agregar_item(categoria, descripcion, cantidad, unidad, precio_unitario):
    """Agrega un ítem a la cotización"""
    item = {
        'id': st.session_state.contador_items,
        'categoria': categoria,
        'descripcion': descripcion,
        'cantidad': cantidad,
        'unidad': unidad,
        'precio_unitario': precio_unitario,
        'subtotal': cantidad * precio_unitario
    }
    st.session_state.cotizacion['items'].append(item)
    st.session_state.contador_items += 1

def eliminar_item(item_id):
    """Elimina un ítem de la cotización"""
    st.session_state.cotizacion['items'] = [
        item for item in st.session_state.cotizacion['items'] 
        if item['id'] != item_id
    ]

def calcular_resumen():
    """Calcula resumen de la cotización"""
    items = st.session_state.cotizacion['items']
    
    if not items:
        return {
            'costos_directos': 0,
            'aiu': {},
            'total_aiu': 0,
            'total_proyecto': 0,
            'por_categoria': {}
        }
    
    # Costos directos por categoría
    df_items = pd.DataFrame(items)
    costos_directos = df_items['subtotal'].sum()
    
    por_categoria = df_items.groupby('categoria')['subtotal'].sum().to_dict()
    
    # Calcular AIU
    aiu_config = st.session_state.cotizacion.get('aiu', PORCENTAJES_AIU_DEFAULT)
    aiu_valores = {}
    total_aiu = 0
    
    for concepto, porcentaje in aiu_config.items():
        valor = costos_directos * (porcentaje / 100)
        aiu_valores[concepto] = valor
        total_aiu += valor
    
    # Total proyecto
    total_proyecto = costos_directos + total_aiu
    
    return {
        'costos_directos': costos_directos,
        'aiu': aiu_valores,
        'total_aiu': total_aiu,
        'total_proyecto': total_proyecto,
        'por_categoria': por_categoria
    }

def generar_excel_cotizacion():
    """Genera archivo Excel de la cotización"""
    resumen = calcular_resumen()
    
    # Crear writer
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        
        # Hoja 1: Detalle de Items
        if st.session_state.cotizacion['items']:
            df_items = pd.DataFrame(st.session_state.cotizacion['items'])
            df_items = df_items[['categoria', 'descripcion', 'cantidad', 'unidad', 'precio_unitario', 'subtotal']]
            df_items.columns = ['Categoría', 'Descripción', 'Cantidad', 'Unidad', 'Precio Unit.', 'Subtotal']
            df_items.to_excel(writer, sheet_name='Detalle Items', index=False)
        
        # Hoja 2: Resumen por Categoría
        if resumen['por_categoria']:
            df_categoria = pd.DataFrame([
                {'Categoría': cat, 'Valor': val, 'Peso': val/resumen['costos_directos']}
                for cat, val in resumen['por_categoria'].items()
            ])
            df_categoria.to_excel(writer, sheet_name='Resumen Categorías', index=False)
        
        # Hoja 3: AIU y Total
        df_aiu = pd.DataFrame([
            {'Concepto': 'Costos Directos', 'Valor': resumen['costos_directos'], 'Peso': resumen['costos_directos']/resumen['total_proyecto']},
            *[{'Concepto': concepto, 'Valor': valor, 'Peso': valor/resumen['total_proyecto']} 
              for concepto, valor in resumen['aiu'].items()],
            {'Concepto': 'Total AIU', 'Valor': resumen['total_aiu'], 'Peso': resumen['total_aiu']/resumen['total_proyecto']},
            {'Concepto': 'TOTAL PROYECTO', 'Valor': resumen['total_proyecto'], 'Peso': 1.0}
        ])
        df_aiu.to_excel(writer, sheet_name='Resumen Total', index=False)
    
    return output.getvalue()

# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
    inicializar_session_state()
    
    # Título
    st.markdown('<h1 class="main-title">🏗️ SICONE - Sistema de Cotización</h1>', unsafe_allow_html=True)
    
    # Sidebar - Información del Proyecto
    with st.sidebar:
        st.markdown("### 📋 Información del Proyecto")
        
        nombre_proyecto = st.text_input("Nombre del Proyecto", value=st.session_state.cotizacion['proyecto'].get('nombre', ''))
        cliente = st.text_input("Cliente", value=st.session_state.cotizacion['proyecto'].get('cliente', ''))
        ubicacion = st.text_input("Ubicación", value=st.session_state.cotizacion['proyecto'].get('ubicacion', ''))
        
        col1, col2 = st.columns(2)
        with col1:
            area = st.number_input("Área (m²)", min_value=0.0, value=st.session_state.cotizacion['proyecto'].get('area', 0.0))
        with col2:
            niveles = st.number_input("Niveles", min_value=1, value=st.session_state.cotizacion['proyecto'].get('niveles', 1))
        
        fecha_cotizacion = st.date_input("Fecha Cotización", value=datetime.now())
        
        # Guardar info del proyecto
        st.session_state.cotizacion['proyecto'] = {
            'nombre': nombre_proyecto,
            'cliente': cliente,
            'ubicacion': ubicacion,
            'area': area,
            'niveles': niveles,
            'fecha': fecha_cotizacion
        }
        
        st.markdown("---")
        
        # Configuración de AIU
        st.markdown("### 💼 Configuración AIU")
        aiu_config = {}
        for concepto, porcentaje_default in PORCENTAJES_AIU_DEFAULT.items():
            aiu_config[concepto] = st.number_input(
                concepto,
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.cotizacion.get('aiu', {}).get(concepto, porcentaje_default),
                step=0.5,
                format="%.1f%%"
            )
        
        st.session_state.cotizacion['aiu'] = aiu_config
    
    # Tabs principales
    tab1, tab2, tab3 = st.tabs(["➕ Agregar Items", "📊 Resumen", "📥 Exportar"])
    
    # ========================================================================
    # TAB 1: AGREGAR ITEMS
    # ========================================================================
    with tab1:
        st.markdown('<h2 class="section-title">Agregar Ítems de Construcción</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            categoria = st.selectbox(
                "Categoría",
                options=list(CATEGORIAS_CONSTRUCCION.keys())
            )
            
            descripcion = st.text_input("Descripción del Ítem")
            
            col_cant, col_unidad = st.columns(2)
            with col_cant:
                cantidad = st.number_input("Cantidad", min_value=0.0, value=1.0, step=0.01)
            with col_unidad:
                unidad = st.selectbox(
                    "Unidad",
                    options=["m2", "m3", "ml", "un", "gl", "kg", "ton", "pt"],
                    index=0
                )
            
            precio_unitario = st.number_input(
                "Precio Unitario ($)",
                min_value=0.0,
                step=1000.0,
                format="%.2f"
            )
            
            subtotal = cantidad * precio_unitario
            st.metric("Subtotal", f"${subtotal:,.2f}")
            
            if st.button("➕ Agregar Ítem", type="primary", use_container_width=True):
                if descripcion and cantidad > 0 and precio_unitario > 0:
                    agregar_item(categoria, descripcion, cantidad, unidad, precio_unitario)
                    st.success("✅ Ítem agregado correctamente")
                    st.rerun()
                else:
                    st.error("⚠️ Complete todos los campos correctamente")
        
        with col2:
            st.markdown("#### 📝 Ítems Agregados")
            
            if st.session_state.cotizacion['items']:
                df_items = pd.DataFrame(st.session_state.cotizacion['items'])
                
                # Mostrar tabla
                for idx, item in enumerate(st.session_state.cotizacion['items']):
                    with st.expander(f"**{item['categoria']}** - {item['descripcion']}", expanded=False):
                        col_a, col_b, col_c = st.columns([2, 2, 1])
                        
                        with col_a:
                            st.write(f"**Cantidad:** {item['cantidad']} {item['unidad']}")
                            st.write(f"**Precio Unit.:** ${item['precio_unitario']:,.2f}")
                        
                        with col_b:
                            st.write(f"**Subtotal:** ${item['subtotal']:,.2f}")
                        
                        with col_c:
                            if st.button("🗑️", key=f"del_{item['id']}", help="Eliminar ítem"):
                                eliminar_item(item['id'])
                                st.rerun()
            else:
                st.info("👆 Agrega ítems usando el formulario de la izquierda")
    
    # ========================================================================
    # TAB 2: RESUMEN
    # ========================================================================
    with tab2:
        st.markdown('<h2 class="section-title">Resumen de Cotización</h2>', unsafe_allow_html=True)
        
        resumen = calcular_resumen()
        
        if resumen['total_proyecto'] > 0:
            # Métricas principales
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "💰 Costos Directos",
                    f"${resumen['costos_directos']:,.0f}",
                    delta=f"{(resumen['costos_directos']/resumen['total_proyecto']*100):.1f}%"
                )
            
            with col2:
                st.metric(
                    "📊 Total AIU",
                    f"${resumen['total_aiu']:,.0f}",
                    delta=f"{(resumen['total_aiu']/resumen['total_proyecto']*100):.1f}%"
                )
            
            with col3:
                st.metric(
                    "🏗️ TOTAL PROYECTO",
                    f"${resumen['total_proyecto']:,.0f}"
                )
            
            with col4:
                num_items = len(st.session_state.cotizacion['items'])
                st.metric(
                    "📋 Ítems",
                    f"{num_items}"
                )
            
            st.markdown("---")
            
            # Gráficos
            col_grafico1, col_grafico2 = st.columns(2)
            
            with col_grafico1:
                st.markdown("#### 📊 Distribución por Categoría")
                
                df_categoria = pd.DataFrame([
                    {'Categoría': cat, 'Valor': val}
                    for cat, val in resumen['por_categoria'].items()
                ])
                
                fig_pie = px.pie(
                    df_categoria,
                    values='Valor',
                    names='Categoría',
                    title='Costos por Categoría'
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_grafico2:
                st.markdown("#### 💼 Desglose AIU")
                
                df_aiu = pd.DataFrame([
                    {'Concepto': concepto, 'Valor': valor}
                    for concepto, valor in resumen['aiu'].items()
                ])
                
                fig_bar = px.bar(
                    df_aiu,
                    x='Concepto',
                    y='Valor',
                    title='Valores AIU',
                    text='Valor'
                )
                fig_bar.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # Tabla resumen detallada
            st.markdown("#### 📋 Detalle Completo")
            
            col_tabla1, col_tabla2 = st.columns(2)
            
            with col_tabla1:
                st.markdown("**Por Categoría:**")
                df_cat_display = pd.DataFrame([
                    {
                        'Categoría': cat,
                        'Valor': f"${val:,.2f}",
                        'Peso %': f"{(val/resumen['costos_directos']*100):.2f}%"
                    }
                    for cat, val in resumen['por_categoria'].items()
                ])
                st.dataframe(df_cat_display, use_container_width=True, hide_index=True)
            
            with col_tabla2:
                st.markdown("**AIU:**")
                df_aiu_display = pd.DataFrame([
                    {
                        'Concepto': concepto,
                        'Valor': f"${valor:,.2f}",
                        'Peso %': f"{(valor/resumen['total_proyecto']*100):.2f}%"
                    }
                    for concepto, valor in resumen['aiu'].items()
                ])
                st.dataframe(df_aiu_display, use_container_width=True, hide_index=True)
        
        else:
            st.info("📝 Agrega ítems en la pestaña 'Agregar Items' para ver el resumen")
    
    # ========================================================================
    # TAB 3: EXPORTAR
    # ========================================================================
    with tab3:
        st.markdown('<h2 class="section-title">Exportar Cotización</h2>', unsafe_allow_html=True)
        
        if resumen['total_proyecto'] > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📥 Descargar Excel")
                st.write("Descarga la cotización completa en formato Excel")
                
                excel_data = generar_excel_cotizacion()
                nombre_archivo = f"Cotizacion_{st.session_state.cotizacion['proyecto'].get('nombre', 'Proyecto')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                
                st.download_button(
                    label="📥 Descargar Excel",
                    data=excel_data,
                    file_name=nombre_archivo,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )
            
            with col2:
                st.markdown("### 📄 Vista Previa")
                st.write("Resumen para compartir:")
                
                st.markdown(f"""
                **Proyecto:** {st.session_state.cotizacion['proyecto'].get('nombre', 'N/A')}  
                **Cliente:** {st.session_state.cotizacion['proyecto'].get('cliente', 'N/A')}  
                **Ubicación:** {st.session_state.cotizacion['proyecto'].get('ubicacion', 'N/A')}  
                **Área:** {st.session_state.cotizacion['proyecto'].get('area', 0):.2f} m²  
                **Fecha:** {st.session_state.cotizacion['proyecto'].get('fecha', 'N/A')}  
                
                ---
                
                **Costos Directos:** ${resumen['costos_directos']:,.2f}  
                **Total AIU:** ${resumen['total_aiu']:,.2f}  
                **TOTAL PROYECTO:** ${resumen['total_proyecto']:,.2f}
                """)
        else:
            st.info("📝 Completa la cotización para poder exportar")
        
        st.markdown("---")
        
        # Opción de limpiar cotización
        st.markdown("### ⚠️ Zona de Peligro")
        if st.button("🗑️ Limpiar Cotización Completa", type="secondary"):
            if st.button("✅ Confirmar Limpieza"):
                st.session_state.cotizacion = {
                    'proyecto': {},
                    'items': [],
                    'aiu': {}
                }
                st.session_state.contador_items = 0
                st.success("✅ Cotización limpiada")
                st.rerun()

# ============================================================================
# EJECUTAR APLICACIÓN
# ============================================================================
if __name__ == "__main__":
    main()
