import streamlit as st
import sys
import os
from datetime import datetime

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.utils.google_drive_manager import GoogleDriveManager

# --- Configuración de la Página ---
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Repositorio INANDES",
    page_icon="📁"
)

# --- Inicialización del Session State ---
if 'drive_manager' not in st.session_state:
    try:
        st.session_state.drive_manager = GoogleDriveManager()
        st.session_state.drive_connected = True
    except Exception as e:
        st.session_state.drive_connected = False
        st.session_state.drive_error = str(e)

if 'current_folder_id' not in st.session_state:
    st.session_state.current_folder_id = None
if 'current_folder_name' not in st.session_state:
    st.session_state.current_folder_name = "Raíz"
if 'breadcrumbs' not in st.session_state:
    st.session_state.breadcrumbs = []
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

# --- Funciones de Ayuda ---
def format_file_size(size_bytes):
    """Formatea el tamaño del archivo en formato legible"""
    if not size_bytes:
        return "N/A"
    try:
        size = int(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    except:
        return "N/A"

def format_date(date_str):
    """Formatea la fecha en formato legible"""
    if not date_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y %H:%M')
    except:
        return date_str

def get_file_icon(mime_type):
    """Retorna un icono según el tipo de archivo"""
    if not mime_type:
        return "📄"
    if 'pdf' in mime_type:
        return "📕"
    if 'image' in mime_type:
        return "🖼️"
    if 'video' in mime_type:
        return "🎥"
    if 'audio' in mime_type:
        return "🎵"
    if 'spreadsheet' in mime_type or 'excel' in mime_type:
        return "📊"
    if 'document' in mime_type or 'word' in mime_type:
        return "📝"
    if 'presentation' in mime_type or 'powerpoint' in mime_type:
        return "📊"
    return "📄"

def navigate_to_folder(folder_id, folder_name):
    """Navega a una carpeta específica"""
    if folder_id != st.session_state.current_folder_id:
        # Agregar a breadcrumbs
        st.session_state.breadcrumbs.append({
            'id': st.session_state.current_folder_id,
            'name': st.session_state.current_folder_name
        })
    st.session_state.current_folder_id = folder_id
    st.session_state.current_folder_name = folder_name

def navigate_back():
    """Navega a la carpeta anterior"""
    if st.session_state.breadcrumbs:
        previous = st.session_state.breadcrumbs.pop()
        st.session_state.current_folder_id = previous['id']
        st.session_state.current_folder_name = previous['name']

# --- UI: CSS ---
st.markdown('''<style>
[data-testid="stHorizontalBlock"] { 
    align-items: center; 
}
.folder-item {
    padding: 10px;
    border-radius: 5px;
    margin: 5px 0;
    cursor: pointer;
}
.folder-item:hover {
    background-color: #f0f2f6;
}
</style>''', unsafe_allow_html=True)

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

# --- Verificar Conexión ---
if not st.session_state.drive_connected:
    st.error(f"❌ Error al conectar con Google Drive: {st.session_state.get('drive_error', 'Error desconocido')}")
    st.info("Verifica que las credenciales estén configuradas correctamente en `.streamlit/secrets.toml`")
    st.stop()

# --- Sidebar: Navegación ---
with st.sidebar:
    st.markdown("### 🗂️ Navegación")
    
    # Botón de inicio
    if st.button("🏠 Ir a Raíz", use_container_width=True):
        st.session_state.current_folder_id = None
        st.session_state.current_folder_name = "Raíz"
        st.session_state.breadcrumbs = []
        st.rerun()
    
    # Breadcrumbs
    if st.session_state.breadcrumbs:
        st.markdown("**Ruta:**")
        for i, crumb in enumerate(st.session_state.breadcrumbs):
            if st.button(f"📁 {crumb['name']}", key=f"breadcrumb_{i}", use_container_width=True):
                # Navegar a este nivel
                st.session_state.breadcrumbs = st.session_state.breadcrumbs[:i]
                st.session_state.current_folder_id = crumb['id']
                st.session_state.current_folder_name = crumb['name']
                st.rerun()
    
    st.markdown(f"**Actual:** 📂 {st.session_state.current_folder_name}")
    
    st.markdown("---")
    
    # Búsqueda
    st.markdown("### 🔍 Búsqueda")
    search_input = st.text_input("Buscar archivos", value=st.session_state.search_query, placeholder="Nombre del archivo...")
    if st.button("Buscar", use_container_width=True):
        st.session_state.search_query = search_input
        st.rerun()
    
    if st.session_state.search_query and st.button("Limpiar búsqueda", use_container_width=True):
        st.session_state.search_query = ""
        st.rerun()
    
    st.markdown("---")
    
    # Acciones
    st.markdown("### ⚙️ Acciones")
    
    # Crear carpeta
    with st.expander("➕ Crear Carpeta"):
        new_folder_name = st.text_input("Nombre de la carpeta", key="new_folder_name")
        if st.button("Crear", key="create_folder_btn"):
            if new_folder_name:
                folder_id = st.session_state.drive_manager.create_folder(
                    new_folder_name,
                    st.session_state.current_folder_id
                )
                if folder_id:
                    st.success(f"✅ Carpeta '{new_folder_name}' creada")
                    st.rerun()
                else:
                    st.error("❌ Error al crear carpeta")
            else:
                st.warning("Ingresa un nombre para la carpeta")
    
    # Subir archivo
    with st.expander("📤 Subir Archivo"):
        uploaded_file = st.file_uploader("Selecciona un archivo", type=['pdf', 'png', 'jpg', 'jpeg', 'xlsx', 'docx'])
        if uploaded_file and st.button("Subir", key="upload_file_btn"):
            file_bytes = uploaded_file.read()
            mime_type = uploaded_file.type
            file_id = st.session_state.drive_manager.upload_file_from_bytes(
                file_bytes,
                uploaded_file.name,
                st.session_state.current_folder_id,
                mime_type
            )
            if file_id:
                st.success(f"✅ Archivo '{uploaded_file.name}' subido")
                st.rerun()
            else:
                st.error("❌ Error al subir archivo")

# --- Main Content ---
st.markdown(f"## 📂 {st.session_state.current_folder_name}")

# Mostrar resultados de búsqueda o contenido de carpeta
if st.session_state.search_query:
    st.info(f"🔍 Buscando: **{st.session_state.search_query}**")
    files = st.session_state.drive_manager.search_files(
        st.session_state.search_query,
        st.session_state.current_folder_id
    )
    folders = []
else:
    # Listar carpetas
    folders = st.session_state.drive_manager.list_folders(st.session_state.current_folder_id)
    # Listar archivos
    files = st.session_state.drive_manager.list_files(st.session_state.current_folder_id)

# Mostrar carpetas
if folders:
    st.markdown("### 📁 Carpetas")
    for folder in folders:
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        
        with col1:
            if st.button(f"📁 {folder['name']}", key=f"folder_{folder['id']}", use_container_width=True):
                navigate_to_folder(folder['id'], folder['name'])
                st.rerun()
        
        with col2:
            st.markdown(f"*Creado: {format_date(folder.get('createdTime'))}*")
        
        with col3:
            st.markdown(f"*Modificado: {format_date(folder.get('modifiedTime'))}*")
        
        with col4:
            if st.button("🗑️", key=f"delete_folder_{folder['id']}", help="Eliminar carpeta"):
                if st.session_state.drive_manager.delete_file(folder['id']):
                    st.success(f"✅ Carpeta eliminada")
                    st.rerun()
                else:
                    st.error("❌ Error al eliminar")
    
    st.markdown("---")

# Mostrar archivos
if files:
    st.markdown("### 📄 Archivos")
    
    # Tabla de archivos
    for file in files:
        col1, col2, col3, col4, col5 = st.columns([0.3, 2.5, 1.5, 1.5, 1.2])
        
        with col1:
            st.markdown(f"## {get_file_icon(file.get('mimeType'))}")
        
        with col2:
            st.markdown(f"**{file['name']}**")
            if file.get('webViewLink'):
                st.markdown(f"[Ver en Drive]({file['webViewLink']})")
        
        with col3:
            st.markdown(f"*{format_file_size(file.get('size'))}*")
        
        with col4:
            st.markdown(f"*{format_date(file.get('modifiedTime'))}*")
        
        with col5:
            # Botón de eliminar
                if st.button("🗑️", key=f"delete_file_{file['id']}", help="Eliminar archivo"):
                    if st.session_state.drive_manager.delete_file(file['id']):
                        st.success(f"✅ Archivo eliminado")
                        st.rerun()
                    else:
                        st.error("❌ Error al eliminar")
        
        st.markdown("---")

elif not folders:
    st.info("📭 Esta carpeta está vacía")

# --- Footer ---
st.markdown("---")
with st.expander("ℹ️ Información del Módulo"):
    st.markdown("""
    ### Repositorio INANDES
    
    Este módulo te permite gestionar archivos en Google Drive de forma independiente.
    
    **Funcionalidades:**
    - 📂 Navegar por carpetas
    - 🔍 Buscar archivos
    - ➕ Crear carpetas
    - 📤 Subir archivos
    - ⬇️ Descargar archivos
    - 🗑️ Eliminar archivos y carpetas
    
    **Estructura recomendada:**
    ```
    INANDES/
      └── [Emisor]/
          └── [Contrato]/
              └── [Anexo]/
                  ├── PDFs...
    ```
    """)

