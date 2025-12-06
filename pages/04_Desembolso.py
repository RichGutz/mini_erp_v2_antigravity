import streamlit as st
import sys
import os
import datetime
import json
import requests

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# --- Module Imports from `src` ---
from src.data import supabase_repository as db

# --- Estrategia Unificada para la URL del Backend ---
API_BASE_URL = os.getenv("BACKEND_API_URL")

if not API_BASE_URL:
    try:
        API_BASE_URL = st.secrets["backend_api"]["url"]
    except (KeyError, AttributeError):
        st.error("La URL del backend no está configurada. Define BACKEND_API_URL o configúrala en st.secrets.")
        st.stop()

USUARIO_ID_TEST = "user_test@inandes.com"

# --- Configuración de la Página ---
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Módulo de Desembolso INANDES",
    page_icon="💵"
)

# --- Inicialización del Session State ---
if 'facturas_aprobadas' not in st.session_state:
    st.session_state.facturas_aprobadas = []
if 'facturas_seleccionadas_desembolso' not in st.session_state:
    st.session_state.facturas_seleccionadas_desembolso = {}
if 'reload_data' not in st.session_state:
    st.session_state.reload_data = True
if 'resultados_desembolso' not in st.session_state:
    st.session_state.resultados_desembolso = None

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

def get_monto_a_desembolsar(factura: dict) -> float:
    """Extrae el monto a desembolsar del recalculate_result_json"""
    try:
        recalc_json = factura.get('recalculate_result_json', '{}')
        recalc_data = json.loads(recalc_json)
        return recalc_data.get('desglose_final_detallado', {}).get('abono', {}).get('monto', 0.0)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return 0.0

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
    st.markdown("<h2 style='text-align: center; font-size: 2.4em;'>Módulo de Desembolso</h2>", unsafe_allow_html=True)
with col3:
    empty_col, logo_col = st.columns([2, 1])
    with logo_col:
        st.image(os.path.join(project_root, "static", "logo_inandes.png"), width=195)

st.markdown("---")

# --- Cargar Facturas Aprobadas Automáticamente ---
if st.session_state.reload_data:
    with st.spinner("Cargando facturas aprobadas pendientes de desembolso..."):
        st.session_state.facturas_aprobadas = db.get_approved_proposals_for_disbursement()
        # Inicializar checkboxes en False
        st.session_state.facturas_seleccionadas_desembolso = {
            f['proposal_id']: False for f in st.session_state.facturas_aprobadas
        }
        st.session_state.reload_data = False

# --- Mostrar Facturas Pendientes ---
if not st.session_state.facturas_aprobadas:
    st.info("✅ No hay facturas aprobadas pendientes de desembolso en este momento.")
else:
    st.subheader(f"💵 Facturas Aprobadas Pendientes de Desembolso ({len(st.session_state.facturas_aprobadas)})")
    
    # Botón de recargar
    if st.button("🔄 Recargar Lista", help="Actualizar la lista de facturas pendientes"):
        st.session_state.reload_data = True
        st.rerun()
    
    st.markdown("---")
    
    # Tabla de facturas
    with st.form(key="disbursement_form"):
        # Header de la tabla
        col_check, col_factura, col_emisor, col_aceptante, col_monto, col_fecha_emision, col_fecha_desembolso = st.columns([0.5, 1.5, 2, 2, 1.5, 1.5, 1.5])
        
        with col_check:
            st.markdown("**Desembolsar**")
        with col_factura:
            st.markdown("**Factura**")
        with col_emisor:
            st.markdown("**Emisor**")
        with col_aceptante:
            st.markdown("**Aceptante**")
        with col_monto:
            st.markdown("**Monto a Desembolsar**")
        with col_fecha_emision:
            st.markdown("**F. Emisión**")
        with col_fecha_desembolso:
            st.markdown("**F. Desembolso**")
        
        st.markdown("---")
        
        # Filas de facturas
        for idx, factura in enumerate(st.session_state.facturas_aprobadas):
            col_check, col_factura, col_emisor, col_aceptante, col_monto, col_fecha_emision, col_fecha_desembolso = st.columns([0.5, 1.5, 2, 2, 1.5, 1.5, 1.5])
            
            with col_check:
                st.session_state.facturas_seleccionadas_desembolso[factura['proposal_id']] = st.checkbox(
                    "",
                    value=st.session_state.facturas_seleccionadas_desembolso.get(factura['proposal_id'], False),
                    key=f"check_desembolso_{idx}",
                    label_visibility="collapsed"
                )
            
            with col_factura:
                st.markdown(f"`{parse_invoice_number(factura['proposal_id'])}`")
            
            with col_emisor:
                st.markdown(factura.get('emisor_nombre', 'N/A'))
            
            with col_aceptante:
                st.markdown(factura.get('aceptante_nombre', 'N/A'))
            
            with col_monto:
                monto = get_monto_a_desembolsar(factura)
                moneda = factura.get('moneda_factura', 'PEN')
                st.markdown(f"{moneda} {monto:,.2f}")
            
            with col_fecha_emision:
                st.markdown(factura.get('fecha_emision_factura', 'N/A'))
            
            with col_fecha_desembolso:
                st.markdown(factura.get('fecha_desembolso_factoring', 'N/A'))
        
        st.markdown("---")
        
        # Botón de desembolsar
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit_button = st.form_submit_button(
                "💵 Desembolsar Facturas Seleccionadas",
                type="primary",
                use_container_width=True
            )
    
    # Procesar desembolsos
    if submit_button:
        # Obtener IDs seleccionados
        ids_seleccionados = [
            pid for pid, selected in st.session_state.facturas_seleccionadas_desembolso.items()
            if selected
        ]
        
        if not ids_seleccionados:
            st.warning("⚠️ No has seleccionado ninguna factura para desembolsar.")
        else:
            st.markdown("---")
            st.subheader("Procesando Desembolsos...")
            
            # Preparar payload para la API
            desembolsos_info = []
            for factura in st.session_state.facturas_aprobadas:
                if factura['proposal_id'] in ids_seleccionados:
                    monto = get_monto_a_desembolsar(factura)
                    fecha_desembolso = factura.get('fecha_desembolso_factoring', datetime.date.today().strftime('%Y-%m-%d'))
                    
                    # Convertir fecha de YYYY-MM-DD a DD-MM-YYYY para la API
                    try:
                        fecha_obj = datetime.datetime.strptime(fecha_desembolso, '%Y-%m-%d')
                        fecha_formateada = fecha_obj.strftime('%d-%m-%Y')
                    except:
                        fecha_formateada = datetime.date.today().strftime('%d-%m-%Y')
                    
                    info = {
                        "proposal_id": factura['proposal_id'],
                        "monto_desembolsado": monto,
                        "fecha_desembolso_real": fecha_formateada,
                    }
                    desembolsos_info.append(info)
            
            payload = {
                "usuario_id": USUARIO_ID_TEST,
                "desembolsos": desembolsos_info
            }
            
            # Llamar a la API
            try:
                with st.spinner("Procesando desembolso a través de la API..."):
                    response = requests.post(f"{API_BASE_URL}/desembolsar_lote", json=payload)
                    response.raise_for_status()
                    st.session_state.resultados_desembolso = response.json()
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Error de conexión con la API: {e}")
                st.session_state.resultados_desembolso = None
            
            # Procesar resultados
            if st.session_state.resultados_desembolso:
                resultados = st.session_state.resultados_desembolso.get('resultados_del_lote', [])
                
                success_count = 0
                error_count = 0
                
                for res in resultados:
                    status = res.get('status', 'ERROR')
                    message = res.get('message', 'No hay mensaje.')
                    pid = res.get('proposal_id', 'N/A')
                    
                    if status == 'SUCCESS':
                        try:
                            db.update_proposal_status(pid, 'DESEMBOLSADA')
                            st.success(f"✅ Factura {parse_invoice_number(pid)}: {message}. Estado actualizado a DESEMBOLSADA.")
                            success_count += 1
                        except Exception as e:
                            st.error(f"❌ Factura {parse_invoice_number(pid)}: Error al actualizar estado: {e}")
                            error_count += 1
                    else:
                        st.error(f"❌ Factura {parse_invoice_number(pid)}: {message}")
                        error_count += 1
                
                st.markdown("---")
                
                if success_count > 0:
                    st.success(f"🎉 Se desembolsaron {success_count} factura(s) exitosamente.")
                
                if error_count > 0:
                    st.error(f"⚠️ Hubo errores al procesar {error_count} factura(s).")
                
                # Recargar datos
                st.session_state.reload_data = True
                
                if st.button("Continuar"):
                    st.rerun()

# --- Información Adicional ---
st.markdown("---")
with st.expander("ℹ️ Información del Módulo"):
    st.markdown("""
    ### Módulo de Desembolso de Operaciones
    
    Este módulo permite procesar los desembolsos de operaciones aprobadas.
    
    **Flujo de trabajo:**
    1. Las operaciones aprobadas en el módulo de **Aprobación** quedan en estado `APROBADO`
    2. Este módulo muestra automáticamente todas las facturas `APROBADAS`
    3. Selecciona las facturas que deseas desembolsar
    4. El sistema procesa el desembolso a través de la API
    5. Al completarse exitosamente, el estado cambia a `DESEMBOLSADA`
    6. Solo las operaciones `DESEMBOLSADAS` están disponibles para **Liquidación**
    
    **Nota:** El monto a desembolsar se calcula automáticamente del perfil de operación original.
    """)
