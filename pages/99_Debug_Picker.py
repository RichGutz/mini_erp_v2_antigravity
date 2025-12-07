import streamlit as st
import os
import sys

# Path setup
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.google_integration import render_simple_folder_selector

st.set_page_config(title="DEBUG PICKER", layout="wide")

st.title("🛠️ Page: DEBUG PICKER")

# 1. Check Session State
st.subheader("1. Session State Check")
if 'token' not in st.session_state:
    st.error("❌ 'token' NO está en session_state. Ve a Home e inicia sesión.")
else:
    st.success("✅ 'token' encontrado en session_state.")
    st.json(st.session_state.token.get('user_info', 'No user info'))

# 2. Check Secrets
st.subheader("2. Secrets Check")
try:
    picker_secrets = st.secrets["google"]
    client_secrets = st.secrets["google_oauth"]
    st.success("✅ Secrets 'google' y 'google_oauth' encontrados.")
except Exception as e:
    st.error(f"❌ Error leyendo secrets: {e}")

# 3. Render Picker
st.subheader("3. Render Picker Component")
st.write("Llamando a `render_simple_folder_selector`...")

if st.button("Reset Picker Key"):
    if 'debug_test_picker_standalone' in st.session_state:
        del st.session_state['debug_test_picker_standalone']
    st.rerun()

try:
    result = render_simple_folder_selector(key="debug_test_picker_standalone", label="Selector de Diagnóstico")
    st.write("---")
    st.write(f"**Resultado del Picker:** {result}")
    
    if result:
        st.success(f"¡Selección exitosa! ID: {result.get('id')}")
except Exception as e:
    st.error(f"❌ Excepción al renderizar: {e}")
    import traceback
    st.code(traceback.format_exc())
