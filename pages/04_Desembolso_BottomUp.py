import streamlit as st
import os
import sys

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.google_integration import render_simple_folder_selector

# --- Page Config ---
st.set_page_config(
    layout="wide",
    page_title="Desembolso Bottom-Up",
    page_icon="🏗️"
)

st.title("🏗️ Desembolso Bottom-Up (Reconstrucción)")

st.info("Paso 1: Verificar que el selector de carpetas funciona AQUÍ antes de agregar más lógica.")

# --- DIAGNÓSTICO RÁPIDO ---
if 'token' not in st.session_state:
    st.error("⚠️ No hay token de autenticación. Por favor ve a 'Home' e inicia sesión con Google.")
    st.stop()

# --- COMPONENTE CRÍTICO: PICKER ---
st.write("### 1. Selector de Carpeta Google Drive")

try:
    folder = render_simple_folder_selector(key="picker_bottom_up", label="Seleccionar Carpeta Destino")
    
    if folder:
        st.success(f"✅ Carpeta Seleccionada: {folder.get('name')} (ID: {folder.get('id')})")
    else:
        st.info("Esperando selección...")

except Exception as e:
    st.error(f"❌ Error al renderizar el selector: {e}")
