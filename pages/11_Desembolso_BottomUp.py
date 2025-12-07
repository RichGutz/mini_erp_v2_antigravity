import streamlit as st
import os
import sys
import datetime
import json

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data import supabase_repository as db
from src.utils.google_integration import render_simple_folder_selector

# --- Page Config ---
st.set_page_config(
    layout="wide",
    page_title="Desembolso Bottom-Up",
    page_icon="🏗️"
)

st.title("🏗️ Desembolso Bottom-Up (Reconstrucción)")

# --- Inicialización del Session State ---
if 'facturas_aprobadas' not in st.session_state:
    st.session_state.facturas_aprobadas = []
if 'facturas_seleccionadas_desembolso' not in st.session_state:
    st.session_state.facturas_seleccionadas_desembolso = {}
if 'reload_data' not in st.session_state:
    st.session_state.reload_data = True

# --- Funciones de Ayuda ---
def parse_invoice_number(proposal_id: str) -> str:
    """Extrae el número de factura del proposal_id"""
    try:
        parts = proposal_id.split('-')
        return f"{parts[1]}-{parts[2]}" if len(parts) > 2 else proposal_id
    except (IndexError, AttributeError):
        return proposal_id

def get_monto_a_desembolsar(factura: dict) -> float:
    try:
        recalc_json = factura.get('recalculate_result_json', '{}')
        recalc_data = json.loads(recalc_json)
        return recalc_data.get('desglose_final_detallado', {}).get('abono', {}).get('monto', 0.0)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return 0.0

# --- Cargar Facturas ---
if st.session_state.reload_data:
    with st.spinner("Cargando facturas aprobadas pendientes de desembolso..."):
        st.session_state.facturas_aprobadas = db.get_approved_proposals_for_disbursement()
        st.session_state.facturas_seleccionadas_desembolso = {
            f['proposal_id']: False for f in st.session_state.facturas_aprobadas
        }
        st.session_state.reload_data = False

# --- DIAGNÓSTICO RÁPIDO ---
if 'token' not in st.session_state:
    st.error("⚠️ No hay token de autenticación. Por favor ve a 'Home' e inicia sesión con Google.")
    st.stop()

# ==============================================================================
# SECCIÓN 1: SELECTOR DE CARPETAS (CRÍTICO - SIEMPRE VISIBLE)
# ==============================================================================
st.markdown("### 1. Selector de Carpeta Google Drive (Componente Base)")
st.info("Este componente debe ser visible SIEMPRE, seleccione o no facturas.")

try:
    folder = render_simple_folder_selector(key="picker_bottom_up", label="Seleccionar Carpeta Destino")
    if folder:
        st.success(f"✅ Carpeta Seleccionada: {folder.get('name')} (ID: {folder.get('id')})")
    else:
        st.info("Esperando selección de carpeta...")
except Exception as e:
    st.error(f"❌ Error al renderizar el selector: {e}")

st.divider()

# ==============================================================================
# SECCIÓN 2: TABLA DE FACTURAS (Lógica de Negocio)
# ==============================================================================
st.markdown("### 2. Facturas Pendientes")

if not st.session_state.facturas_aprobadas:
    st.info("✅ No hay facturas aprobadas pendientes de desembolso.")
else:
    # Header de la tabla
    cols = st.columns([0.5, 1.5, 1.5, 2, 2, 1.5])
    headers = ["Sel", "Factura", "Lote", "Emisor", "Aceptante", "Monto"]
    for col, h in zip(cols, headers): 
        col.markdown(f"**{h}**")
        
    for idx, factura in enumerate(st.session_state.facturas_aprobadas):
        col_check, col_factura, col_lote, col_emisor, col_aceptante, col_monto = st.columns([0.5, 1.5, 1.5, 2, 2, 1.5])
        
        with col_check:
            st.session_state.facturas_seleccionadas_desembolso[factura['proposal_id']] = st.checkbox(
                "",
                value=st.session_state.facturas_seleccionadas_desembolso.get(factura['proposal_id'], False),
                key=f"check_bu_{idx}",
                label_visibility="collapsed"
            )
        col_factura.markdown(f"`{parse_invoice_number(factura['proposal_id'])}`")
        col_lote.markdown(f"`{factura.get('identificador_lote', 'N/A')}`")
        col_emisor.markdown(factura.get('emisor_nombre', 'N/A'))
        col_aceptante.markdown(factura.get('aceptante_nombre', 'N/A'))
        col_monto.markdown(f"{factura.get('moneda_factura', 'PEN')} {get_monto_a_desembolsar(factura):,.2f}")

    # Contar seleccionadas
    facturas_seleccionadas = [
        f for f in st.session_state.facturas_aprobadas
        if st.session_state.facturas_seleccionadas_desembolso.get(f['proposal_id'], False)
    ]
    
    st.write(f"📝 Facturas seleccionadas: {len(facturas_seleccionadas)}")
    
    if facturas_seleccionadas:
        st.success("✅ Hay facturas seleccionadas. (Aquí iría la lógica de Vouchers)")
    else:
        st.warning("⚠️ Selecciona facturas para continuar.")
