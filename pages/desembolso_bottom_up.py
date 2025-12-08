import streamlit as st
import sys
import os

# Add root directory to path to allow imports from src
sys.path.append(os.path.abspath("."))

from src.utils.google_integration import render_simple_folder_selector, upload_file_with_sa

st.set_page_config(page_title="Testing Native Drive", page_icon="🧪", layout="wide")

st.title("🧪 Prototipo: Navegador Nativo Drive (Service Account)")
st.info("Esta página prueba la navegación de carpetas usando credenciales de Service Account directamente desde Python (Backend), sin usar componentes JS externos.")

# --- 1. Selector de Carpeta (Nativo) ---
st.write("### 1. Seleccionar Carpeta Destino")
# La función render_simple_folder_selector maneja el estado de sesión y la UI
selected_folder = render_simple_folder_selector(key="native_test_picker", label="Navegador del Repositorio")

st.markdown("---")

# --- 2. Prueba de Subida ---
st.write("### 2. Prueba de Subida de Archivo")

if selected_folder:
    st.success(f"📂 Carpeta Activa: **{selected_folder['name']}** (ID: `{selected_folder['id']}`)")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        uploaded_file = st.file_uploader("Seleccionar archivo para subir", type=['pdf', 'txt', 'png', 'jpg'])
    
    with col2:
        st.write("Metadata de subida:")
        st.json({
            "folder_name": selected_folder['name'],
            "folder_id": selected_folder['id']
        })

    if uploaded_file:
        if st.button("⬆️ Subir Archivo al Repositorio", type="primary"):
            with st.spinner("Subiendo archivo con Service Account..."):
                file_bytes = uploaded_file.getvalue()
                file_name = uploaded_file.name
                
                # Obtener credenciales
                try:
                    sa_creds = st.secrets["google_drive"]
                    
                    success, result = upload_file_with_sa(
                        file_bytes=file_bytes,
                        file_name=file_name,
                        folder_id=selected_folder['id'],
                        sa_credentials=sa_creds
                    )
                    
                    if success:
                        st.balloons()
                        st.success(f"✅ Archivo **{file_name}** subido exitosamente!")
                        st.code(f"File ID: {result}")
                    else:
                        st.error(f"❌ Error al subir: {result}")
                        
                except Exception as e:
                    st.error(f"Error de configuración/credenciales: {e}")
else:
    st.info("👈 Navega y selecciona una carpeta en la sección anterior para habilitar la subida.")
