import streamlit as st
import os

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# --- Header ---
from src.ui.header import render_header
render_header("Reportes Gerenciales")

st.markdown("---")

st.info("🚧 **Módulo en Construcción** 🚧")
st.write("Próximamente encontrarás aquí los reportes gerenciales y tributarios.")
