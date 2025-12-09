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

# --- Funciones de Ayuda ---
def parse_invoice_number(proposal_id: str) -> str:
    """Extrae el número de factura del proposal_id"""
    try:
        parts = proposal_id.split('-')
        return f"{parts[1]}-{parts[2]}" if len(parts) > 2 else proposal_id
    except (IndexError, AttributeError):
        return proposal_id

def safe_decimal(value, default=0.0):
    """Convierte un valor a decimal de forma segura"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

# --- UI: CSS ---
st.markdown('''<style>
[data-testid="stHorizontalBlock"] { 
    align-items: center; 
}
</style>''', unsafe_allow_html=True)

# --- UI: Header con Logos ---
col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
with col1:
    st.image(os.path.join(project_root, "static", "logo_geek.png"), width=200)
with col2:
    st.markdown("<h2 style='text-align: center; font-size: 2.4em;'>Módulo de Aprobación</h2>", unsafe_allow_html=True)
with col3:
    empty_col, logo_col = st.columns([2, 1])
    with logo_col:
        st.image(os.path.join(project_root, "static", "logo_inandes.png"), width=195)

st.markdown("---")

# --- Cargar Facturas Activas Automáticamente ---
if st.session_state.reload_data:
    with st.spinner("Cargando facturas pendientes de aprobación..."):
        st.session_state.facturas_activas = db.get_active_proposals_for_approval()
        # Inicializar checkboxes en False
        st.session_state.facturas_seleccionadas_aprobacion = {
            f['proposal_id']: False for f in st.session_state.facturas_activas
        }
        st.session_state.reload_data = False

# --- Mostrar Facturas Pendientes ---
if not st.session_state.facturas_activas:
    st.info("✅ No hay facturas pendientes de aprobación en este momento.")
    if st.button("🔄 Recargar Lista"):
        st.session_state.reload_data = True
        st.rerun()
else:
    # Agrupar por Lote
    grouped_invoices = defaultdict(list)
    for inv in st.session_state.facturas_activas:
        lote_id = inv.get('identificador_lote', 'Sin Lote')
        grouped_invoices[lote_id].append(inv)
    
    st.container(border=True)
    st.subheader(f"1. Facturas Pendientes de Aprobación ({len(st.session_state.facturas_activas)})")
    
    if st.button("🔄 Recargar Lista", help="Actualizar la lista de facturas pendientes"):
        st.session_state.reload_data = True
        st.rerun()
    
    st.markdown("---")
    
    with st.form(key="approval_form"):
        # Iterar por cada grupo (Lote)
        for lote_id, invoices_in_batch in grouped_invoices.items():
            
            # Obtener datos del lote (Emisor fecha) del primer elemento
            first_inv = invoices_in_batch[0]
            emisor_name = first_inv.get('emisor_nombre', 'N/A')
            created_at = first_inv.get('created_at', '') # Si existe
            
            with st.container(border=True):
                # Header del Lote
                st.markdown(f"**📦 Lote:** `{lote_id}` | **Emisor:** {emisor_name} | **Cant:** {len(invoices_in_batch)}")
                
                # Header de la Tablita
                col_check, col_factura, col_aceptante, col_monto, col_fecha_desembolso = st.columns([0.5, 1.5, 2.5, 1.5, 1.5])
                
                with col_check: st.markdown("**Aprobar**")
                with col_factura: st.markdown("**Factura**")
                with col_aceptante: st.markdown("**Aceptante**")
                with col_monto: st.markdown("**Monto Neto**")
                with col_fecha_desembolso: st.markdown("**F. Desembolso**")
                
                # Filas
                for idx, factura in enumerate(invoices_in_batch):
                    col_check, col_factura, col_aceptante, col_monto, col_fecha_desembolso = st.columns([0.5, 1.5, 2.5, 1.5, 1.5])
                    
                    with col_check:
                        # Usamos el ID real como key del checkbox
                        pid = factura['proposal_id']
                        st.session_state.facturas_seleccionadas_aprobacion[pid] = st.checkbox(
                            "",
                            value=st.session_state.facturas_seleccionadas_aprobacion.get(pid, False),
                            key=f"chk_app_{pid}", # Unique Key per invoice
                            label_visibility="collapsed"
                        )
                    
                    with col_factura: st.markdown(f"`{parse_invoice_number(factura['proposal_id'])}`")
                    with col_aceptante: st.markdown(factura.get('aceptante_nombre', 'N/A'))
                    with col_monto:
                        monto = safe_decimal(factura.get('monto_neto_factura', 0))
                        moneda = factura.get('moneda_factura', 'PEN')
                        st.markdown(f"{moneda} {monto:,.2f}")
                    with col_fecha_desembolso: st.markdown(factura.get('fecha_desembolso_factoring', 'N/A'))

        st.markdown("---")
        
        # Botón Maestro
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit_button = st.form_submit_button(
                "✅ Aprobar Facturas Seleccionadas",
                type="primary",
                use_container_width=True
            )
            
    # Procesar Aprobaciones
    if submit_button:
        ids_seleccionados = [
            pid for pid, selected in st.session_state.facturas_seleccionadas_aprobacion.items()
            if selected
        ]
        
        if not ids_seleccionados:
            st.warning("⚠️ No has seleccionado ninguna factura para aprobar.")
        else:
            st.markdown("---")
            st.subheader("Procesando Aprobaciones...")
            
            success_count = 0
            error_count = 0
            
            for proposal_id in ids_seleccionados:
                try:
                    db.update_proposal_status(proposal_id, 'APROBADO')
                    # st.success(f"✅ Factura aprobada.") # Reduce noise
                    success_count += 1
                except Exception as e:
                    st.error(f"❌ Error al aprobar: {e}")
                    error_count += 1
            
            if success_count > 0:
                st.success(f"🎉 Se aprobaron {success_count} factura(s) exitosamente.")
            
            if error_count > 0:
                st.error(f"⚠️ Hubo errores en {error_count} factura(s).")
            
            st.session_state.reload_data = True
            if st.button("Continuar"):
                st.rerun()


# --- Información Adicional ---
# st.markdown("---")
with st.container(border=True):
    st.subheader("2. Información del Módulo")
    # with st.expander("ℹ️ Información del Módulo"):
    st.markdown("""
    Este módulo permite a gerencia revisar y aprobar operaciones antes de que pasen a desembolso.
    
    **Flujo de trabajo:**
    1. Las operaciones creadas en **Originación** quedan en estado `ACTIVO`
    2. Gerencia revisa y aprueba las operaciones en este módulo (Agrupadas por Lote)
    3. Al aprobar, el estado cambia a `APROBADO`
    4. Solo las operaciones `APROBADAS` están disponibles para **Desembolso**
    """)
