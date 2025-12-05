import streamlit as st
import sys
import os
import re

# Path setup
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data import supabase_repository as db

# Page config
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Módulo de Registro de Clientes",
    page_icon="📋"
)

# Session state
if 'vista_registro' not in st.session_state:
    st.session_state.vista_registro = 'lista'  # 'lista', 'crear', 'editar'
if 'registro_seleccionado' not in st.session_state:
    st.session_state.registro_seleccionado = None

# CSS
st.markdown('''<style>
[data-testid="stHorizontalBlock"] { 
    align-items: center; 
}
</style>''', unsafe_allow_html=True)

# Header
col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
with col1:
    st.image(os.path.join(project_root, "static", "logo_geek.png"), width=200)
with col2:
    st.markdown("<h2 style='text-align: center;'>Módulo de Registro de Clientes</h2>", unsafe_allow_html=True)
with col3:
    empty_col, logo_col = st.columns([2, 1])
    with logo_col:
        st.image(os.path.join(project_root, "static", "logo_inandes.png"), width=195)

# Vistas
def mostrar_lista():
    """Vista principal: lista de emisores/deudores"""
    st.header("Gestión de Emisores y Deudores")
    
    # Filtros
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("🔍 Buscar por RUC o Razón Social", key="search_input")
    with col2:
        filtro_tipo = st.selectbox("Filtrar por Tipo", ["Todos", "EMISOR", "DEUDOR"])
    with col3:
        if st.button("➕ Nuevo Registro", type="primary", use_container_width=True):
            st.session_state.vista_registro = 'crear'
            st.rerun()
    
    # Obtener datos
    try:
        if search:
            registros = db.search_emisores_deudores(search)
        else:
            tipo_filtro = None if filtro_tipo == "Todos" else filtro_tipo
            registros = db.get_all_emisores_deudores(tipo_filtro)
    except AttributeError as e:
        st.error(f"⚠️ Error: Las funciones CRUD no están disponibles. Por favor, reinicia la aplicación.")
        st.info("💡 **Solución temporal:** Streamlit Cloud necesita reiniciar completamente. Espera 1-2 minutos y recarga la página.")
        st.code(f"Error técnico: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"Error al obtener registros: {str(e)}")
        st.stop()
    
    # Mostrar tabla
    if registros:
        st.write(f"**Total de registros:** {len(registros)}")
        
        for registro in registros:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 3, 1, 1])
                with col1:
                    st.write(f"**RUC:** {registro.get('RUC', 'N/A')}")
                with col2:
                    st.write(f"**Razón Social:** {registro.get('Razon Social', 'N/A')}")
                with col3:
                    tipo = registro.get('tipo', 'N/A')
                    color = "🟢" if tipo == "EMISOR" else "🔵"
                    st.write(f"{color} **{tipo}**")
                with col4:
                    if st.button("✏️ Editar", key=f"edit_{registro['RUC']}", use_container_width=True):
                        st.session_state.registro_seleccionado = registro
                        st.session_state.vista_registro = 'editar'
                        st.rerun()
    else:
        st.info("No se encontraron registros")


def mostrar_formulario_crear():
    """Vista de creación de nuevo registro"""
    st.header("Crear Nuevo Emisor/Deudor")
    
    if st.button("← Volver a la lista"):
        st.session_state.vista_registro = 'lista'
        st.rerun()
    
    with st.form("form_crear"):
        st.subheader("Campos Obligatorios")
        
        col1, col2 = st.columns(2)
        with col1:
            ruc = st.text_input("RUC *", max_chars=11, help="11 dígitos numéricos")
        with col2:
            tipo = st.selectbox("Tipo *", ["EMISOR", "DEUDOR"])
        
        razon_social = st.text_input("Razón Social *")
        
        st.info("💡 **Nota:** Puedes agregar más campos según la estructura de tu tabla en Supabase")
        
        submitted = st.form_submit_button("Crear Registro", type="primary")
        
        if submitted:
            # Validar
            if not ruc or not razon_social or not tipo:
                st.error("Por favor completa todos los campos obligatorios")
            elif not re.match(r'^\d{11}$', ruc):
                st.error("El RUC debe tener exactamente 11 dígitos numéricos")
            else:
                # Crear registro
                data = {
                    'RUC': ruc,
                    'Razon Social': razon_social,
                    'tipo': tipo
                }
                
                success, message = db.create_emisor_deudor(data)
                if success:
                    st.success(message)
                    st.balloons()
                    st.session_state.vista_registro = 'lista'
                    st.rerun()
                else:
                    st.error(message)


def mostrar_formulario_editar():
    """Vista de edición de registro existente"""
    st.header("Editar Emisor/Deudor")
    
    if st.button("← Volver a la lista"):
        st.session_state.vista_registro = 'lista'
        st.session_state.registro_seleccionado = None
        st.rerun()
    
    registro = st.session_state.registro_seleccionado
    if not registro:
        st.error("No hay registro seleccionado")
        return
    
    st.info(f"**RUC:** {registro['RUC']} (no se puede modificar)")
    
    with st.form("form_editar"):
        razon_social = st.text_input("Razón Social *", value=registro.get('Razon Social', ''))
        tipo = st.selectbox("Tipo *", ["EMISOR", "DEUDOR"], 
                           index=0 if registro.get('tipo') == 'EMISOR' else 1)
        
        submitted = st.form_submit_button("Guardar Cambios", type="primary")
        
        if submitted:
            if not razon_social:
                st.error("La Razón Social es obligatoria")
            else:
                data = {
                    'Razon Social': razon_social,
                    'tipo': tipo
                }
                
                success, message = db.update_emisor_deudor(registro['RUC'], data)
                if success:
                    st.success(message)
                    st.session_state.vista_registro = 'lista'
                    st.session_state.registro_seleccionado = None
                    st.rerun()
                else:
                    st.error(message)


# Router
if st.session_state.vista_registro == 'lista':
    mostrar_lista()
elif st.session_state.vista_registro == 'crear':
    mostrar_formulario_crear()
elif st.session_state.vista_registro == 'editar':
    mostrar_formulario_editar()
