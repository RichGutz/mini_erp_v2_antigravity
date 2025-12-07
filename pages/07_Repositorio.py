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

# --- UI: Header ---
col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
with col1:
    st.image(os.path.join(project_root, "static", "logo_geek.png"), width=200)
with col2:
    st.markdown("<h2 style='text-align: center; font-size: 2.4em;'>📁 Repositorio INANDES</h2>", unsafe_allow_html=True)
with col3:
    empty_col, logo_col = st.columns([2, 1])
    with logo_col:
        st.image(os.path.join(project_root, "static", "logo_inandes.png"), width=195)

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
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'selected_files' not in st.session_state:
    st.session_state.selected_files = None

# --- OAuth2 Component ---
AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/drive.readonly"

oauth2 = OAuth2Component(
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    AUTHORIZATION_URL,
    TOKEN_URL,
    TOKEN_URL,
    None
)

# --- Autenticación ---
st.markdown("### 🔐 Autenticación")

if not st.session_state.access_token:
    # Mostrar botón de login
    try:
        result = oauth2.authorize_button(
            name="Iniciar sesión con Google",
            icon="https://www.google.com/favicon.ico",
            redirect_uri="https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app/component/streamlit_oauth.authorize",
            scope=SCOPE,
            key="google_oauth",
            extras_params={"access_type": "offline", "prompt": "consent"},
        )
        
        if result and 'token' in result:
            st.session_state.access_token = result.get('token')
            st.rerun()
        else:
            st.info("👆 Inicia sesión con tu cuenta de Google para acceder al repositorio")
            st.stop()
    except Exception as e:
        st.error(f"❌ Error de autenticación: {str(e)}")
        st.warning("💡 **Solución**: Recarga la página (F5) e intenta nuevamente")
        if st.button("🔄 Recargar página"):
            st.rerun()
        st.stop()
else:
    # Mostrar estado autenticado
    col_auth1, col_auth2 = st.columns([3, 1])
    with col_auth1:
        st.success("✅ Autenticado con Google")
    with col_auth2:
        if st.button("🚪 Cerrar sesión"):
            st.session_state.access_token = None
            st.session_state.selected_files = None
            st.rerun()

st.markdown("---")

# --- Google Picker (solo si está autenticado) ---
if st.session_state.access_token:
    st.markdown("### 📂 Seleccionar Archivos")
    
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
            token=st.session_state.access_token,
            # apiKey=GOOGLE_API_KEY,  # Comentado - causa error developerKey
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
        - Token de acceso expirado (intenta cerrar sesión y volver a autenticarte)
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

# --- Footer ---
st.markdown("---")
st.caption("🔒 **Seguro y confiable** - Powered by Google Drive & Google Picker API")
