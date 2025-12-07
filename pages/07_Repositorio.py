import streamlit as st
import os
from streamlit_google_picker import google_picker

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
# Obtener credenciales de secrets.toml
try:
    GOOGLE_CLIENT_ID = st.secrets["google"]["client_id"]
    GOOGLE_CLIENT_SECRET = st.secrets["google"]["client_secret"]
    GOOGLE_API_KEY = st.secrets["google"]["api_key"]
    FOLDER_ID = st.secrets["google"]["drive_folder_id"]
except KeyError as e:
    st.error(f"⚠️ **Error de configuración**: Falta la clave {e} en secrets.toml")
    st.info("""
    **Instrucciones para configurar:**
    
    1. Edita el archivo `.streamlit/secrets.toml`
    2. Agrega las siguientes líneas:
    
    ```toml
    [google]
    client_id = "TU_CLIENT_ID.apps.googleusercontent.com"
    client_secret = "TU_CLIENT_SECRET"
    api_key = "TU_API_KEY"
    drive_folder_id = "1hOomiUg0Gw3VBpsyLYFcUGBLe9ujewV-"
    ```
    
    3. Obtén las credenciales desde Google Cloud Console:
       - Ve a APIs & Services → Credentials
       - Crea OAuth 2.0 Client ID (Web application)
       - Crea API Key
       - Habilita Google Drive API y Google Picker API
    """)
    st.stop()

# --- Información ---
st.info("💡 **Repositorio de Documentos INANDES** - Selecciona archivos directamente desde Google Drive con una interfaz interactiva.")

# --- Inicializar session state ---
if 'selected_files' not in st.session_state:
    st.session_state.selected_files = None

# --- Google Picker ---
st.markdown("### 📂 Seleccionar Archivos")

# Instrucciones
with st.expander("📖 Cómo usar el Repositorio", expanded=False):
    st.markdown("""
    ### Funcionalidades Disponibles
    
    ✅ **Autenticación segura** - Inicia sesión con tu cuenta de Google
    
    ✅ **Explorar carpetas** - Navega por la estructura de carpetas
    
    ✅ **Seleccionar archivos** - Elige uno o múltiples archivos
    
    ✅ **Vista previa** - Visualiza información de archivos seleccionados
    
    ✅ **Descarga directa** - Descarga archivos con un clic
    
    ### Notas Importantes
    
    - Necesitas autenticarte con Google la primera vez
    - Los archivos seleccionados se muestran en una tabla
    - Puedes descargar archivos usando los enlaces directos
    - La sesión se mantiene mientras uses la aplicación
    """)

st.markdown("---")

# Botón para abrir el picker
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    if st.button("🔍 Abrir Selector de Archivos", type="primary", use_container_width=True):
        # Abrir Google Picker
        try:
            selected_files = google_picker(
                clientId=GOOGLE_CLIENT_ID,
                developerKey=GOOGLE_API_KEY,
                appId=GOOGLE_CLIENT_ID.split('-')[0],  # Extraer App ID del Client ID
                folderId=FOLDER_ID,
                multiselect=True,
                showUploadView=True,
                showUploadFolders=True,
            )
            
            if selected_files:
                st.session_state.selected_files = selected_files
                st.rerun()
        except Exception as e:
            st.error(f"❌ Error al abrir el selector: {str(e)}")
            st.info("""
            **Posibles causas:**
            - Credenciales incorrectas en secrets.toml
            - APIs no habilitadas en Google Cloud Console
            - Problemas de autenticación
            
            Verifica tu configuración y vuelve a intentar.
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
    # Mensaje cuando no hay archivos seleccionados
    st.info("👆 Haz clic en el botón para abrir el selector de archivos de Google Drive")

# --- Footer ---
st.markdown("---")
st.caption("🔒 **Seguro y confiable** - Powered by Google Drive & Google Picker API")
