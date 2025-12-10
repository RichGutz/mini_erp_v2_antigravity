import streamlit as st
import sys
import os
import datetime
import json
from collections import defaultdict

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# --- Module Imports from `src` ---
from src.data import supabase_repository as db
from src.ui.email_component import render_email_sender

# --- Configuración de la Página ---
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Módulo de Aprobación INANDES",
    page_icon="✅"
)

# --- Inicialización del Session State ---
if 'facturas_activas' not in st.session_state:
    st.session_state.facturas_activas = []
if 'facturas_seleccionadas_aprobacion' not in st.session_state:
    st.session_state.facturas_seleccionadas_aprobacion = {}
if 'reload_data' not in st.session_state:
    st.session_state.reload_data = True
if 'last_approved_invoices' not in st.session_state:
    st.session_state.last_approved_invoices = [] # List of strings (Invoice Numbers)
if 'last_approved_total' not in st.session_state:
    st.session_state.last_approved_total = 0.0
if 'last_approved_emisor' not in st.session_state:
    st.session_state.last_approved_emisor = ""
if 'email_body_version' not in st.session_state:
    st.session_state.email_body_version = 0

# ... (omitted)

            if success_count > 0:
                # Actualizar estado para el email
                st.session_state.last_approved_invoices = approved_list_temp
                st.session_state.last_approved_total = total_desembolso_temp
                st.session_state.last_approved_emisor = last_emisor_temp
                st.session_state.email_body_version += 1 # Force widget refresh
                
                st.success(f"🎉 Se aprobaron {success_count} factura(s) exitosamente.")
                st.balloons()

# ... (omitted)

    # Use version in the key to force re-render with new value
    key_suffix_dynamic = f"aprobacion_v{st.session_state.email_body_version}"
    
    render_email_sender(
        key_suffix=key_suffix_dynamic,
        documents=[], # No attachments typically for just approval notification
        default_subject=f"Notificación de Aprobación - {st.session_state.last_approved_emisor}" if st.session_state.last_approved_emisor else "Notificación de Aprobación",
        default_body=body_text
    )

