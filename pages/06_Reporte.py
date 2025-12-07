import streamlit as st
import os

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
with col1:
    st.image(os.path.join(project_root, "static", "logo_geek.png"), width=200)
with col2:
    st.title("Reportes Gerenciales")
with col3:
    empty_col, logo_col = st.columns([2, 1])
    with logo_col:
        st.image(os.path.join(project_root, "static", "logo_inandes.png"), width=195)

st.markdown("---")

st.info("🚧 **Módulo en Construcción** 🚧")
st.write("Próximamente encontrarás aquí los reportes gerenciales y tributarios.")
