import streamlit as st
import os
import sys

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Page Config ---
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Agentes IA Inandes",
    page_icon="🤖"
)

# --- Access Control ---
from src.data.supabase_repository import check_user_access
# Retrieve User Email safely
user_email = ""
if 'user_info' in st.session_state and isinstance(st.session_state.user_info, dict):
    user_email = st.session_state.user_info.get('email', "")

# Assuming everyone with access to the app can see agents for now, or restriction:
# if not check_user_access("Agentes", user_email): ...

# --- Header ---
from src.ui.header import render_header
render_header("Agentes Inteligentes")

# --- Agent Selection ---
with st.sidebar:
    st.markdown("### 🤖 Selector de Agente")
    selected_agent = st.selectbox(
        "Elige tu asistente:",
        ["Creador de Proformas", "Analista de Riesgos (Inactivo)"]
    )
    st.markdown("---")
    if st.button("🗑️ Limpiar Conversación"):
        st.session_state.messages = []
        st.rerun()

# --- Main Interface ---
st.title(f"{selected_agent}")
st.caption("Potenciado por Google Gemini Pro 1.5")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Agent Specific Logic ---
if selected_agent == "Creador de Proformas":
    from src.agents.proforma_agent import render_proforma_agent
    render_proforma_agent()
else:
    st.info("Este agente aún no está disponible.")
