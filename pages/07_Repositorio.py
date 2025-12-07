import streamlit as st
import os

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

# --- Configuración del Folder ID ---
# Carpeta raíz del Repositorio INANDES en Google Drive
FOLDER_ID = "1hOomiUg0Gw3VBpsyLYFcUGBLe9ujewV-"

# --- Información ---
st.info("💡 **Repositorio de Documentos INANDES** - Navega, crea carpetas y sube archivos directamente en Google Drive.")

# --- Embed Google Drive ---
if FOLDER_ID == "REEMPLAZAR_CON_FOLDER_ID":
    st.warning("⚠️ **Configuración pendiente**: El administrador debe configurar el Folder ID de Google Drive.")
    st.markdown("""
    **Instrucciones para el administrador:**
    1. Abre Google Drive y navega a la carpeta raíz del repositorio
    2. Copia el Folder ID de la URL (la parte después de `/folders/`)
    3. Edita este archivo y reemplaza `REEMPLAZAR_CON_FOLDER_ID` con el ID real
    4. Haz commit y push para desplegar
    """)
else:
    # Embed Google Drive con vista de grid
    iframe_html = f"""
    <iframe src="https://drive.google.com/embeddedfolderview?id={FOLDER_ID}#grid" 
            style="width:100%; height:700px; border:1px solid #ddd; border-radius:8px;">
    </iframe>
    """
    st.markdown(iframe_html, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Instrucciones
    with st.expander("📖 Cómo usar el Repositorio"):
        st.markdown("""
        ### Funcionalidades Disponibles
        
        ✅ **Navegar carpetas** - Click en las carpetas para explorar
        
        ✅ **Crear carpetas** - Click derecho → Nueva carpeta
        
        ✅ **Subir archivos** - Arrastra archivos o usa el botón de subir
        
        ✅ **Descargar archivos** - Click derecho → Descargar
        
        ✅ **Organizar** - Mover, renombrar, eliminar archivos y carpetas
        
        ### Notas Importantes
        
        - Necesitas tener acceso a la carpeta de Google Drive
        - Los cambios se sincronizan automáticamente
        - Sin límites de profundidad de carpetas
        - Soporta todos los tipos de archivos
        """)

# --- Footer ---
st.markdown("---")
st.caption("🔒 **Seguro y confiable** - Powered by Google Drive")
