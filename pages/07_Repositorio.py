import streamlit as st
import os
from streamlit_google_picker import google_picker
from streamlit_oauth import OAuth2Component

# --- Configuración de la Página ---
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Repositorio INANDES",
    page_icon="📁"
)

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# --- Header ---
from src.ui.header import render_header
render_header("Repositorio INANDES")

# --- Access Control ---
from src.data.supabase_repository import check_user_access
user_email = ""
if 'user_info' in st.session_state and isinstance(st.session_state.user_info, dict):
    user_email = st.session_state.user_info.get('email', "")

if not check_user_access("Repositorio", user_email):
    st.error("⛔ No tienes permisos para acceder a este módulo.")
    st.stop()

# --- CSS Alignment Fix ---
st.markdown('''<style>
[data-testid="stHorizontalBlock"] { 
    align-items: center; 
}
</style>''', unsafe_allow_html=True)

st.markdown("---")

# --- Configuración ---
try:
    GOOGLE_CLIENT_ID = st.secrets["google"]["client_id"]
    GOOGLE_CLIENT_SECRET = st.secrets["google"]["client_secret"]
    GOOGLE_API_KEY = st.secrets["google"]["api_key"]
    FOLDER_ID = st.secrets["google"]["drive_folder_id"]
except KeyError as e:
    st.error(f"⚠️ **Error de configuración**: Falta la clave {e} en secrets.toml")
    st.stop()

# --- Información ---
st.info("💡 **Repositorio de Documentos INANDES** - Selecciona archivos directamente desde Google Drive.")

# --- Inicializar session state ---
if 'selected_files' not in st.session_state:
    st.session_state.selected_files = None

# --- Verificar Autenticación ---
st.markdown("### 📂 Seleccionar Archivos")

if 'token' in st.session_state and st.session_state.token:
    access_token = st.session_state.token.get('access_token')
    
    # Instrucciones
    with st.expander("📖 Cómo usar el Repositorio", expanded=False):
        st.markdown("""
        ### Funcionalidades Disponibles
        
        ✅ **Explorar carpetas** - Navega por la estructura de carpetas
        
        ✅ **Seleccionar archivos** - Elige uno o múltiples archivos
        
        ✅ **Vista previa** - Visualiza información de archivos seleccionados
        
        ✅ **Descarga directa** - Descarga archivos con un clic
        """)
    
    st.markdown("---")
    
    # Google Picker
    try:
        selected_files = google_picker(
            label="🔍 Seleccionar archivos de Google Drive",
            token=access_token,
            apiKey=GOOGLE_API_KEY,
            appId=GOOGLE_CLIENT_ID.split('-')[0],
            accept_multiple_files=True,
            allow_folders=True,  # Habilitar visualización de carpetas
            view_ids=["DOCS", "FOLDERS"],  # Mostrar documentos y carpetas
            key="google_drive_picker"
        )
        
        if selected_files:
            st.session_state.selected_files = selected_files
            
    except Exception as e:
        st.error(f"❌ Error al abrir el selector: {str(e)}")
        st.info("""
        **Posibles causas:**
        - Token de acceso expirado (intenta cerrar sesión y volver a autenticarte en Home)
        - APIs no habilitadas en Google Cloud Console
        - Problemas de permisos
        """)
    
    # --- Mostrar archivos seleccionados ---
    if st.session_state.selected_files:
        st.markdown("---")
        st.markdown("### 📋 Archivos Seleccionados")
        
        files = st.session_state.selected_files
        
        # Mostrar información de archivos
        if isinstance(files, dict):
            files = [files]
        
        for idx, file in enumerate(files):
            with st.container():
                col_info, col_actions = st.columns([3, 1])
                
                with col_info:
                    # Información del archivo
                    file_name = file.get('name', 'Sin nombre')
                    file_id = file.get('id', '')
                    file_type = file.get('mimeType', 'Desconocido')
                    
                    st.markdown(f"**{idx + 1}. {file_name}**")
                    st.caption(f"📄 Tipo: {file_type}")
                    st.caption(f"🆔 ID: {file_id}")
                
                with col_actions:
                    # Botón de descarga/vista
                    if file_id:
                        download_url = f"https://drive.google.com/file/d/{file_id}/view"
                        st.link_button("🔗 Abrir", download_url, use_container_width=True)
                
                st.markdown("---")
        
        # Botón para limpiar selección
        if st.button("🗑️ Limpiar Selección", type="secondary"):
            st.session_state.selected_files = None
            st.rerun()

else:
    st.warning("⚠️ No estás autenticado. Por favor, inicia sesión en la página de **Inicio**.")
    if st.button("🏠 Ir a Inicio"):
        st.switch_page("00_Home.py")

# --- Footer ---
st.markdown("---")
st.caption("🔒 **Seguro y confiable** - Powered by Google Drive & Google Picker API")
