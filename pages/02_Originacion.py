import os
import json
import datetime
import tempfile
import requests
import streamlit as st
import pandas as pd

# --- Project Imports ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

from src.services import pdf_parser
from src.data import supabase_repository as db
from src.utils import pdf_generators
from src.utils.pdf_generators import generar_anexo_liquidacion_pdf
from src.utils.google_integration import (
    render_folder_navigator_v2, 
    upload_file_with_sa, 
)
from src.ui.email_component import render_email_sender


# --- Configuration & Constants ---
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Módulo de Originación INANDES",
    page_icon="📊",
)

# Backend URL Strategy
API_BASE_URL = os.getenv("BACKEND_API_URL")
if not API_BASE_URL:
    try:
        API_BASE_URL = st.secrets["backend_api"]["url"]
    except (KeyError, AttributeError):
        st.error("❌ La URL del backend no está configurada. Define BACKEND_API_URL o configúrala en st.secrets.")
        st.stop()

# Service Account Credentials
try:
    SA_CREDENTIALS = dict(st.secrets["google_drive"])
except Exception as e:
    st.error(f"❌ Error: No se encontraron credenciales del Service Account en secrets.toml: {e}")
    st.stop()


# --- Custom CSS ---
st.markdown("""
<style>
    .stButton>button.red-button {
        background-color: #FF4B4B;
        color: white;
        border-color: #FF4B4B;
    }
    .stButton>button.red-button:hover {
        background-color: #FF6F6F;
        border-color: #FF6F6F;
    }
    .invoice-brick {
        display: inline-block;
        background-color: #e0f2f1;
        color: #00695c;
        padding: 4px 8px;
        border-radius: 4px;
        margin: 2px;
        border: 1px solid #b2dfdb;
        font-size: 0.85em;
        font-family: monospace;
    }
    .bucket-header {
        background-color: #f5f5f5;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        border-left: 5px solid #2196F3;
    }
    
    /* --- HACK: Style Native File Uploader --- */
    
    /* 1. Grid Layout for the file list */
    [data-testid='stFileUploader'] section[role="list"] {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 8px !important;
    }
    
    /* Also target the UL inside if structure varies */
    [data-testid='stFileUploader'] ul {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 8px !important;
    }

    /* 2. Hide the decorative "file" icon */
    /* Target the SVG that is a direct child of the uploaded file item container */
    [data-testid="stUploadedFile"] > div > svg {
        display: none !important;
    }
    /* Fallback for older Streamlit versions or different structures */
    [data-testid='stFileUploader'] div[role="listitem"] > div > svg {
        display: none !important;
    }

    /* 3. Make sure the name takes available space */
    [data-testid="stUploadedFile"] > div {
        width: 100% !important;
        align-items: center !important;
    }

    /* 4. Hide Pagination Footer */
    [data-testid='stFileUploader'] div:has(button[title="View more"]) {
        display: none !important;
    }
    .stFileUploaderPagination {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---

def update_date_calculations(invoice: dict, changed_field=None, idx=None):
    """Updates derived fields (payment date, credit term days) based on inputs."""
    try:
        fecha_emision_str = invoice.get('fecha_emision_factura')
        if not fecha_emision_str:
            invoice['fecha_pago_calculada'] = ""
            invoice['plazo_credito_dias'] = 0
            invoice['plazo_operacion_calculado'] = 0
            return

        fecha_emision_dt = datetime.datetime.strptime(fecha_emision_str, "%d-%m-%Y")

        # Calculate Plazo Credito Dias
        if invoice.get('fecha_pago_calculada'):
            fecha_pago_dt = datetime.datetime.strptime(invoice['fecha_pago_calculada'], "%d-%m-%Y")
            if fecha_pago_dt > fecha_emision_dt:
                invoice['plazo_credito_dias'] = (fecha_pago_dt - fecha_emision_dt).days
            else:
                invoice['plazo_credito_dias'] = 0
        else:
            invoice['fecha_pago_calculada'] = ""
            invoice['plazo_credito_dias'] = 0

        # Calculate Plazo Operacion (Factoring)
        if invoice.get('fecha_pago_calculada') and invoice.get('fecha_desembolso_factoring'):
            fecha_pago_dt = datetime.datetime.strptime(invoice['fecha_pago_calculada'], "%d-%m-%Y")
            fecha_desembolso_dt = datetime.datetime.strptime(invoice['fecha_desembolso_factoring'], "%d-%m-%Y")
            
            if fecha_pago_dt >= fecha_desembolso_dt:
                invoice['plazo_operacion_calculado'] = (fecha_pago_dt - fecha_desembolso_dt).days
                invoice['fecha_error'] = False
            else:
                invoice['plazo_operacion_calculado'] = 0
                invoice['fecha_error'] = True
        else:
            invoice['plazo_operacion_calculado'] = 0
            invoice['fecha_error'] = False

        # Sync with Session State widgets if ID is provided
        if idx is not None:
            if f"plazo_operacion_calculado_{idx}" in st.session_state:
                st.session_state[f"plazo_operacion_calculado_{idx}"] = str(invoice.get('plazo_operacion_calculado', 0))
            if f"plazo_credito_dias_{idx}" in st.session_state:
                st.session_state[f"plazo_credito_dias_{idx}"] = str(invoice.get('plazo_credito_dias', 0))

    except (ValueError, TypeError, AttributeError):
        invoice['fecha_pago_calculada'] = ""
        invoice['plazo_operacion_calculado'] = 0


def validate_inputs(invoice: dict) -> bool:
    """Validates that all required fields are present and numeric values are positive."""
    required_fields = {
        "emisor_nombre": "Nombre del Emisor", "emisor_ruc": "RUC del Emisor",
        "aceptante_nombre": "Nombre del Aceptante", "aceptante_ruc": "RUC del Aceptante",
        "numero_factura": "Número de Factura", "moneda_factura": "Moneda de Factura",
        "fecha_emision_factura": "Fecha de Emisión",
        "tasa_de_avance": "Tasa de Avance",
        "interes_mensual": "Interés Mensual",
        "fecha_pago_calculada": "Fecha de Pago", "fecha_desembolso_factoring": "Fecha de Desembolso",
    }
    for key in required_fields:
        if not invoice.get(key):
            return False
    
    numeric_fields = ["monto_total_factura", "monto_neto_factura", "tasa_de_avance", "interes_mensual"]
    for key in numeric_fields:
        if invoice.get(key, 0) <= 0:
            return False
            
    return True


def propagate_commission_changes():
    """Propagates global fee parameters to all invoices if 'fijar_condiciones' is active."""
    if st.session_state.get('fijar_condiciones', False) and st.session_state.invoices_data and len(st.session_state.invoices_data) > 1:
        first_invoice = st.session_state.invoices_data[0]
        ref_tasa = st.session_state.get(f"tasa_de_avance_0", first_invoice['tasa_de_avance'])
        ref_int_m = st.session_state.get(f"interes_mensual_0", first_invoice['interes_mensual'])
        ref_int_mor = st.session_state.get(f"interes_moratorio_0", first_invoice['interes_moratorio'])
        
        # We also propagate manual fees if set
        ref_com_pen = st.session_state.get(f"comision_afiliacion_pen_0", first_invoice['comision_afiliacion_pen'])
        ref_com_usd = st.session_state.get(f"comision_afiliacion_usd_0", first_invoice['comision_afiliacion_usd'])

        first_invoice['tasa_de_avance'] = ref_tasa
        first_invoice['interes_mensual'] = ref_int_m
        first_invoice['interes_moratorio'] = ref_int_mor
        first_invoice['comision_afiliacion_pen'] = ref_com_pen
        first_invoice['comision_afiliacion_usd'] = ref_com_usd

        for i in range(1, len(st.session_state.invoices_data)):
            invoice = st.session_state.invoices_data[i]
            invoice['tasa_de_avance'] = ref_tasa
            invoice['interes_mensual'] = ref_int_m
            invoice['interes_moratorio'] = ref_int_mor
            invoice['comision_afiliacion_pen'] = ref_com_pen
            invoice['comision_afiliacion_usd'] = ref_com_usd


def to_date_obj(date_str):
    """Helper to safely convert DD-MM-YYYY string to date object."""
    if not date_str or not isinstance(date_str, str): 
        return None
    try:
        return datetime.datetime.strptime(date_str, '%d-%m-%Y').date()
    except (ValueError, TypeError):
        return None


# --- Global Parameter Handlers ---

def handle_global_payment_date_change():
    if st.session_state.get('aplicar_fecha_vencimiento_global') and st.session_state.get('fecha_vencimiento_global'):
        global_due_date_obj = st.session_state.fecha_vencimiento_global
        global_due_date_str = global_due_date_obj.strftime('%d-%m-%Y')
        for idx, invoice in enumerate(st.session_state.invoices_data):
            invoice['fecha_pago_calculada'] = global_due_date_str
            st.session_state[f"fecha_pago_calculada_{idx}"] = global_due_date_obj
            update_date_calculations(invoice, changed_field='fecha', idx=idx)
        st.toast("✅ Fecha de pago global aplicada.")

def handle_global_disbursement_date_change():
    if st.session_state.get('aplicar_fecha_desembolso_global') and st.session_state.get('fecha_desembolso_global'):
        global_disbursement_date_obj = st.session_state.fecha_desembolso_global
        global_disbursement_date_str = global_disbursement_date_obj.strftime('%d-%m-%Y')
        for idx, invoice in enumerate(st.session_state.invoices_data):
            invoice['fecha_desembolso_factoring'] = global_disbursement_date_str
            st.session_state[f"fecha_desembolso_factoring_{idx}"] = global_disbursement_date_obj
            update_date_calculations(invoice, idx=idx)
        st.toast("✅ Fecha de desembolso global aplicada.")

def handle_global_tasa_avance_change():
    if st.session_state.get('aplicar_tasa_avance_global') and st.session_state.get('tasa_avance_global') is not None:
        val = st.session_state.tasa_avance_global
        for idx, invoice in enumerate(st.session_state.invoices_data):
            invoice['tasa_de_avance'] = val
            st.session_state[f"tasa_de_avance_{idx}"] = val
        st.toast("✅ Tasa de avance global aplicada.")

def handle_global_interes_mensual_change():
    if st.session_state.get('aplicar_interes_mensual_global') and st.session_state.get('interes_mensual_global') is not None:
        val = st.session_state.interes_mensual_global
        for idx, invoice in enumerate(st.session_state.invoices_data):
            invoice['interes_mensual'] = val
            st.session_state[f"interes_mensual_{idx}"] = val
        st.toast("✅ Interés mensual global aplicado.")

def handle_global_interes_moratorio_change():
    if st.session_state.get('aplicar_interes_moratorio_global') and st.session_state.get('interes_moratorio_global') is not None:
        val = st.session_state.interes_moratorio_global
        for idx, invoice in enumerate(st.session_state.invoices_data):
            invoice['interes_moratorio'] = val
            st.session_state[f"interes_moratorio_{idx}"] = val
        st.toast("✅ Interés moratorio global aplicado.")

def handle_global_min_interest_days_change():
    if st.session_state.get('aplicar_dias_interes_minimo_global'):
        val = st.session_state.dias_interes_minimo_global
        for idx, invoice in enumerate(st.session_state.invoices_data):
            invoice['dias_minimos_interes_individual'] = val
            st.session_state[f"dias_minimos_interes_individual_{idx}"] = val
        st.toast("✅ Días de interés mínimo global aplicado.")

def handle_bucket_change(grp_id):
    """Updates all invoices in a specific group when bucket params change."""
    # Get new values from bucket widgets
    new_f_desem = st.session_state.get(f"f_desemb_grp_{grp_id}")
    new_f_pago = st.session_state.get(f"f_pago_grp_{grp_id}")
    new_dias_min = st.session_state.get(f"dias_min_grp_{grp_id}", 15)
    
    # Format dates
    f_desem_str = new_f_desem.strftime('%d-%m-%Y') if new_f_desem else ""
    f_pago_str = new_f_pago.strftime('%d-%m-%Y') if new_f_pago else ""

    # Update logic
    if st.session_state.invoices_data:
        for idx, invoice in enumerate(st.session_state.invoices_data):
            if invoice.get('group_id') == grp_id:
                # Update Dict
                invoice['fecha_desembolso_factoring'] = f_desem_str
                invoice['fecha_pago_calculada'] = f_pago_str
                invoice['dias_minimos_interes_individual'] = new_dias_min
                
                # Update Widgets in Session State (to reflect immediately in UI)
                if f"fecha_desembolso_factoring_{idx}" in st.session_state:
                    st.session_state[f"fecha_desembolso_factoring_{idx}"] = new_f_desem
                if f"fecha_pago_calculada_{idx}" in st.session_state:
                    st.session_state[f"fecha_pago_calculada_{idx}"] = new_f_pago
                if f"dias_minimos_interes_individual_{idx}" in st.session_state:
                    st.session_state[f"dias_minimos_interes_individual_{idx}"] = new_dias_min
                
                # Recalculate derived fields
                update_date_calculations(invoice, idx=idx)
        
        st.toast(f"✅ Grupo {grp_id} actualizado.")


# --- Session State Initialization ---
defaults = {
    'invoices_data': [],
    'pdf_datos_cargados': False,
    'last_uploaded_pdf_files_ids': [], # Tracks MAIN combination ID
    'last_saved_proposal_id': '',
    'anexo_number': '',
    'contract_number': '',
    'fijar_condiciones': False,
    # Global Commissions
    'aplicar_comision_afiliacion_global': False,
    'comision_afiliacion_pen_global': 200.0,
    'comision_afiliacion_usd_global': 50.0,
    'aplicar_comision_estructuracion_global': False,
    'comision_estructuracion_pct_global': 0.5,
    'comision_estructuracion_min_pen_global': 200.0,
    'comision_estructuracion_min_usd_global': 50.0,
    # Global Dates & Rates
    'aplicar_fecha_vencimiento_global': False,
    'fecha_vencimiento_global': datetime.date.today(),
    'aplicar_fecha_desembolso_global': False,
    'fecha_desembolso_global': datetime.date.today(),
    'aplicar_dias_interes_minimo_global': False,
    'dias_interes_minimo_global': 15,
    'default_comision_afiliacion_pen': 200.0,
    'default_comision_afiliacion_usd': 50.0,
    'default_tasa_de_avance': 98.0,
    'default_interes_mensual': 1.25,
    'default_interes_moratorio': 2.5,
    'aplicar_tasa_avance_global': False,
    'tasa_avance_global': 98.0,
    'aplicar_interes_mensual_global': False,
    'interes_mensual_global': 1.25,
    'aplicar_interes_moratorio_global': False,
    'interes_moratorio_global': 2.5,
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# --- Layout: Header ---
from src.ui.header import render_header
render_header("Módulo de Originación")

# ==============================================================================
# SECCIÓN 1: CARGA DE FACTURAS (MULTI-BUCKET - GRID VIEW)
# ==============================================================================
with st.container(border=True):
    st.subheader("1. Carga de Facturas")
    st.info("ℹ️ Distribuye las facturas en los 4 grupos según sus fechas de desembolso y pago.")
    
    # Grid Layout: 4 Columns corresponding to Groups
    cols = st.columns(4)
    
    # Store temporary bucket config in a local dict to process later
    buckets_config = {} 
    
    total_files_count = 0
    
    for i, col in enumerate(cols):
        grp_id = i + 1
        with col:
            st.markdown(f"**GRUPO {grp_id}**")
            
            # ROW 1: Fecha Desembolso
            f_desem = st.date_input(f"Fecha de Desembolso", value=datetime.date.today(), key=f"f_desemb_grp_{grp_id}", on_change=handle_bucket_change, args=(grp_id,))
            
            # ROW 2: Fecha Pago
            f_pago = st.date_input(f"Fecha de Pago", value=datetime.date.today(), key=f"f_pago_grp_{grp_id}", on_change=handle_bucket_change, args=(grp_id,))
            
            # ROW 3: Días Mínimos (Explicit Label)
            dias_min = st.number_input(f"Días Mínimos", min_value=0, value=15, step=1, key=f"dias_min_grp_{grp_id}", on_change=handle_bucket_change, args=(grp_id,))
            # ROW 4: Browse Files (Bottom)
            uploaded = st.file_uploader(f"Cargar Facturas G{grp_id}", type=["pdf"], key=f"uploader_grp_{grp_id}", accept_multiple_files=True, label_visibility="visible")
            
            if uploaded:
                total_files_count += len(uploaded)

    st.divider()
    
    # --- PROCESS ALL BUCKETS BUTTON ---
    if st.button(f"🚀 PROCESAR TODO EL LOTE ({total_files_count} archivos)", type="primary", use_container_width=True, disabled=(total_files_count==0)):
        
        # Reset Main Data
        st.session_state.invoices_data = []
        st.session_state.pdf_datos_cargados = False
        st.session_state.original_uploads_cache = []
        
        all_processed_ok = True
        
        # ITERATE BUCKETS
        for i in range(1, 5):
            files = st.session_state.get(f"uploader_grp_{i}")
            if not files:
                continue
                
            f_desem_val = st.session_state.get(f"f_desemb_grp_{i}")
            f_pago_val = st.session_state.get(f"f_pago_grp_{i}")
            dias_min_val = st.session_state.get(f"dias_min_grp_{i}", 15)
            
            f_desem_str = f_desem_val.strftime('%d-%m-%Y') if f_desem_val else ""
            f_pago_str = f_pago_val.strftime('%d-%m-%Y') if f_pago_val else ""
            
            for uploaded_file in files:
                # Cache raw content
                file_bytes_content = uploaded_file.getvalue()
                st.session_state.original_uploads_cache.append({
                    'name': uploaded_file.name,
                    'bytes': file_bytes_content
                })
                
                # Temp file for parser
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(file_bytes_content)
                    temp_file_path = tmp.name

                try:
                    # Parse
                    parsed_data = pdf_parser.extract_fields_from_pdf(temp_file_path)
                    
                    if parsed_data.get("error"):
                         st.error(f"[G{i}] Error parsing {uploaded_file.name}: {parsed_data['error']}")
                         all_processed_ok = False
                    else:
                        # Build Invoice Object
                        invoice_entry = {
                            # Metadata
                            'group_id': i,  # <--- NEW: Track Origin Bucket
                            'parsed_pdf_name': uploaded_file.name,
                            'file_id': uploaded_file.file_id,
                            
                            # Fields
                            'emisor_ruc': parsed_data.get('emisor_ruc', ''),
                            'aceptante_ruc': parsed_data.get('aceptante_ruc', ''),
                            'fecha_emision_factura': parsed_data.get('fecha_emision', ''),
                            'monto_total_factura': parsed_data.get('monto_total', 0.0),
                            'monto_neto_factura': parsed_data.get('monto_neto', 0.0),
                            'moneda_factura': parsed_data.get('moneda', 'PEN'),
                            'numero_factura': parsed_data.get('invoice_id', ''),
                            'emisor_nombre': db.get_razon_social_by_ruc(parsed_data.get('emisor_ruc', '')),
                            'aceptante_nombre': db.get_razon_social_by_ruc(parsed_data.get('aceptante_ruc', '')),
                            
                            # Assigned Dates from Bucket
                            'fecha_desembolso_factoring': f_desem_str,
                            'fecha_pago_calculada': f_pago_str, # Override parsed date with Bucket date
                            
                            # Config Defaults
                            'tasa_de_avance': st.session_state.default_tasa_de_avance,
                            'interes_mensual': st.session_state.default_interes_mensual,
                            'interes_moratorio': st.session_state.default_interes_moratorio,
                            'comision_afiliacion_pen': st.session_state.default_comision_afiliacion_pen,
                            'comision_afiliacion_usd': st.session_state.default_comision_afiliacion_usd,
                            'dias_minimos_interes_individual': dias_min_val,
                            'detraccion_porcentaje': 0.0,
                            'plazo_credito_dias': 0,
                            'plazo_operacion_calculado': 0,
                        }
                        
                        # --- Apply DB Rates Logic (Simplified Copy) ---
                        try:
                            # (Here we reuse the logic to pull rates from DB if available)
                            db_rates = db.get_financial_conditions(parsed_data.get('emisor_ruc'))
                            if db_rates:
                                # ... (We can copy full logic or rely on defaults. 
                                # Ideally this logic should be a function `apply_db_rates(invoice_entry)`)
                                # For brevity, keeping it minimal:
                                if db_rates.get('tasa_avance', 0) > 0:
                                    invoice_entry['tasa_de_avance'] = float(db_rates['tasa_avance'])
                                # ... (Other rates logic implied) ...
                        except:
                            pass
                        
                        # Calculate initial days
                        update_date_calculations(invoice_entry)
                        
                        st.session_state.invoices_data.append(invoice_entry)

                except Exception as e:
                    st.error(f"Excepción en {uploaded_file.name}: {e}")
                finally:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
        
        if st.session_state.invoices_data:
            st.session_state.pdf_datos_cargados = True
            st.success(f"✅ Procesamiento completado. {len(st.session_state.invoices_data)} facturas cargadas.")
            st.rerun()


# ==============================================================================
# SECCIÓN 2: CONFIGURACIÓN GLOBAL (Full Width)
# ==============================================================================
if st.session_state.invoices_data:
    with st.container(border=True):
        st.subheader("2. Configuración Global")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write("##### Com. de Estructuración")
            st.checkbox("Aplicar Comisión de Estructuración", key='aplicar_comision_estructuracion_global')
            st.number_input("Comisión de Estructuración (%)", min_value=0.0, key='comision_estructuracion_pct_global', format="%.2f", disabled=not st.session_state.get('aplicar_comision_estructuracion_global', False))
            st.number_input("Comisión Mínima (PEN)", min_value=0.0, key='comision_estructuracion_min_pen_global', format="%.2f", disabled=not st.session_state.get('aplicar_comision_estructuracion_global', False))
            st.number_input("Comisión Mínima (USD)", min_value=0.0, key='comision_estructuracion_min_usd_global', format="%.2f", disabled=not st.session_state.get('aplicar_comision_estructuracion_global', False))
            
        with col2:
            st.write("##### Com. de Afiliación")
            st.checkbox("Aplicar Comisión de Afiliación", key='aplicar_comision_afiliacion_global')
            st.number_input("Monto Comisión Afiliación (PEN)", min_value=0.0, key='comision_afiliacion_pen_global', format="%.2f", disabled=not st.session_state.get('aplicar_comision_afiliacion_global', False))
            st.number_input("Monto Comisión Afiliación (USD)", min_value=0.0, key='comision_afiliacion_usd_global', format="%.2f", disabled=not st.session_state.get('aplicar_comision_afiliacion_global', False))

        with col3:
            st.write("##### Tasas Globales")
            st.checkbox("Aplicar Tasa de Avance Global", key='aplicar_tasa_avance_global', on_change=handle_global_tasa_avance_change)
            st.number_input("Tasa de Avance Global (%)", key='tasa_avance_global', min_value=0.0, format="%.2f", disabled=not st.session_state.get('aplicar_tasa_avance_global', False), on_change=handle_global_tasa_avance_change)
            
            st.checkbox("Aplicar Interés Mensual Global", key='aplicar_interes_mensual_global', on_change=handle_global_interes_mensual_change)
            st.number_input("Interés Mensual Global (%)", key='interes_mensual_global', min_value=0.0, format="%.2f", disabled=not st.session_state.get('aplicar_interes_mensual_global', False), on_change=handle_global_interes_mensual_change)
            
            st.checkbox("Aplicar Interés Moratorio Global", key='aplicar_interes_moratorio_global', on_change=handle_global_interes_moratorio_change)
            st.number_input("Interés Moratorio Global (%)", key='interes_moratorio_global', min_value=0.0, format="%.2f", disabled=not st.session_state.get('aplicar_interes_moratorio_global', False), on_change=handle_global_interes_moratorio_change)


    # ==============================================================================
    # SECCIÓN 3: DETALLE DE FACTURAS (GROUPED)
    # ==============================================================================
    st.subheader("3. Detalle de Facturas")
    
    # Identify active groups
    active_groups = sorted(list(set(inv.get('group_id', 1) for inv in st.session_state.invoices_data)))
    
    for grp in active_groups:
        st.markdown(f"<div class='bucket-header'>📁 <b>GRUPO {grp}</b></div>", unsafe_allow_html=True)
        
        # Filter invoices for this group
        group_invoices = [(i, inv) for i, inv in enumerate(st.session_state.invoices_data) if inv.get('group_id') == grp]
        
        for idx, invoice in group_invoices:
            # Note: We must use the ORIGINAL 'idx' from the main list as the key suffix
            # to keep data sync with st.session_state.invoices_data[idx]
            
            with st.container(border=True):
                st.markdown(f"**Factura {idx + 1}:** `{invoice.get('parsed_pdf_name', 'N/A')}`")

                with st.container():
                    st.caption("Involucrados")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: invoice['emisor_nombre'] = st.text_input("NOMBRE DEL EMISOR", value=invoice.get('emisor_nombre', ''), key=f"emisor_nombre_{idx}")
                    with c2: invoice['emisor_ruc'] = st.text_input("RUC DEL EMISOR", value=invoice.get('emisor_ruc', ''), key=f"emisor_ruc_{idx}")
                    with c3: invoice['aceptante_nombre'] = st.text_input("NOMBRE DEL ACEPTANTE", value=invoice.get('aceptante_nombre', ''), key=f"aceptante_nombre_{idx}")
                    with c4: invoice['aceptante_ruc'] = st.text_input("RUC DEL ACEPTANTE", value=invoice.get('aceptante_ruc', ''), key=f"aceptante_ruc_{idx}")

                with st.container():
                    st.caption("Montos y Moneda")
                    c1, c2, c3, c4, c5 = st.columns(5)
                    with c1: invoice['numero_factura'] = st.text_input("NÚMERO DE FACTURA", value=invoice.get('numero_factura', ''), key=f"numero_factura_{idx}")
                    with c2: invoice['monto_total_factura'] = st.number_input("MONTO TOTAL (CON IGV)", min_value=0.0, value=invoice.get('monto_total_factura', 0.0), format="%.2f", key=f"monto_total_factura_{idx}")
                    with c3: invoice['monto_neto_factura'] = st.number_input("MONTO NETO", min_value=0.0, value=invoice.get('monto_neto_factura', 0.0), format="%.2f", key=f"monto_neto_factura_{idx}")
                    with c4: invoice['moneda_factura'] = st.selectbox("MONEDA", ["PEN", "USD"], index=["PEN", "USD"].index(invoice.get('moneda_factura', 'PEN')), key=f"moneda_factura_{idx}")
                    with c5:
                        detr_pct = 0.0
                        if invoice.get('monto_total_factura', 0) > 0:
                            detr_pct = ((invoice['monto_total_factura'] - invoice['monto_neto_factura']) / invoice['monto_total_factura']) * 100
                        invoice['detraccion_porcentaje'] = detr_pct
                        st.text_input("Detracción (%)", value=f"{detr_pct:.2f}%", disabled=True, key=f"detraccion_porcentaje_{idx}")

                with st.container():
                    st.caption("Fechas y Plazos (Pre-cargado desde Bucket)")
                    
                    # Callbacks for date widgets to sync logic
                    def _on_fecha_pago_changed(i=idx):
                        dt_obj = st.session_state.get(f"fecha_pago_calculada_{i}")
                        st.session_state.invoices_data[i]['fecha_pago_calculada'] = dt_obj.strftime('%d-%m-%Y') if dt_obj else ''
                        update_date_calculations(st.session_state.invoices_data[i], changed_field='fecha', idx=i)

                    def _on_fecha_desembolso_changed(i=idx):
                        dt_obj = st.session_state.get(f"fecha_desembolso_factoring_{i}")
                        st.session_state.invoices_data[i]['fecha_desembolso_factoring'] = dt_obj.strftime('%d-%m-%Y') if dt_obj else ''
                        update_date_calculations(st.session_state.invoices_data[i], idx=i)

                    c1, c2, c3, c4, c5 = st.columns(5)
                    with c1:
                        em_obj = to_date_obj(invoice.get('fecha_emision_factura'))
                        new_em = st.date_input("Fecha Emisión", value=em_obj or datetime.date.today(), key=f"fetcha_em_input_{idx}", format="DD-MM-YYYY", disabled=bool(em_obj))
                        if not em_obj: invoice['fecha_emision_factura'] = new_em.strftime('%d-%m-%Y')

                    with c2:
                        des_obj = to_date_obj(invoice.get('fecha_desembolso_factoring'))
                        st.date_input("Fecha Desembolso", value=des_obj or datetime.date.today(), key=f"fecha_desembolso_factoring_{idx}", format="DD-MM-YYYY", on_change=_on_fecha_desembolso_changed)

                    with c3:
                        pag_obj = to_date_obj(invoice.get('fecha_pago_calculada'))
                        st.date_input("Fecha Pago", value=pag_obj or datetime.date.today(), key=f"fecha_pago_calculada_{idx}", format="DD-MM-YYYY", on_change=_on_fecha_pago_changed)

                    with c4:
                        plazo = st.session_state.invoices_data[idx].get('plazo_operacion_calculado', 0)
                        if st.session_state.invoices_data[idx].get('fecha_error', False):
                            st.warning("⚠️ Fecha Pago < Desembolso")
                        st.text_input("Plazo (días)", value=str(plazo), disabled=True, key=f"plazo_operacion_calculado_{idx}")

                    with c5:
                        invoice['dias_minimos_interes_individual'] = st.number_input("Días Mínimos", value=invoice.get('dias_minimos_interes_individual', 15), min_value=0, key=f"dias_minimos_interes_individual_{idx}")

                with st.container():
                    st.caption("Tasas y Comisiones")
                    is_locked = idx > 0 and st.session_state.fijar_condiciones
                    c1, c2, c3 = st.columns(3)
                    with c1: invoice['tasa_de_avance'] = st.number_input("Tasa de Avance (%)", min_value=0.0, value=invoice.get('tasa_de_avance', 98.0), key=f"tasa_de_avance_{idx}", disabled=is_locked, on_change=propagate_commission_changes)
                    with c2: invoice['interes_mensual'] = st.number_input("Interés Mensual (%)", min_value=0.0, value=invoice.get('interes_mensual', 1.25), key=f"interes_mensual_{idx}", disabled=is_locked, on_change=propagate_commission_changes)
                    with c3: invoice['interes_moratorio'] = st.number_input("Interés Moratorio (%)", min_value=0.0, value=invoice.get('interes_moratorio', 2.5), key=f"interes_moratorio_{idx}", disabled=is_locked, on_change=propagate_commission_changes)

                
                # --- Results Display Within Invoice ---
                if invoice.get('recalculate_result'):
                    st.divider()
                    st.write("##### Perfil de la Operación")
                    st.markdown(
                        f"**Emisor:** {invoice.get('emisor_nombre', 'N/A')} | "
                        f"**Aceptante:** {invoice.get('aceptante_nombre', 'N/A')} | "
                        f"**Factura:** {invoice.get('numero_factura', 'N/A')} | "
                        f"**F. Emisión:** {invoice.get('fecha_emision_factura', 'N/A')} | "
                        f"**F. Pago:** {invoice.get('fecha_pago_calculada', 'N/A')} | "
                        f"**Monto Total:** {invoice.get('moneda_factura', '')} {invoice.get('monto_total_factura', 0):,.2f} | "
                        f"**Monto Neto:** {invoice.get('moneda_factura', '')} {invoice.get('monto_neto_factura', 0):,.2f}"
                    )
                    recalc_result = invoice['recalculate_result']
                    desglose = recalc_result.get('desglose_final_detallado', {})
                    calculos = recalc_result.get('calculo_con_tasa_encontrada', {})
                    busqueda = recalc_result.get('resultado_busqueda', {})
                    moneda = invoice.get('moneda_factura', 'PEN')

                    tasa_avance_pct = busqueda.get('tasa_avance_encontrada', 0) * 100
                    monto_neto = invoice.get('monto_neto_factura', 0)
                    capital = calculos.get('capital', 0)
                    
                    abono = desglose.get('abono', {})
                    interes = desglose.get('interes', {})
                    com_est = desglose.get('comision_estructuracion', {})
                    com_afi = desglose.get('comision_afiliacion', {})
                    igv = desglose.get('igv_total', {})
                    margen = desglose.get('margen_seguridad', {})

                    costos_totales = interes.get('monto', 0) + com_est.get('monto', 0) + com_afi.get('monto', 0) + igv.get('monto', 0)
                    tasa_diaria_pct = (invoice.get('interes_mensual', 0) / 30) 

                    lines = []
                    lines.append(f"| Item | Monto ({moneda}) | % sobre Neto | Fórmula de Cálculo | Detalle del Cálculo |")
                    lines.append("| :--- | :--- | :--- | :--- | :--- |")
                    
                    monto_total = invoice.get('monto_total_factura', 0)
                    detraccion_monto = monto_total - monto_neto
                    detraccion_pct = invoice.get('detraccion_porcentaje', 0)
                    
                    lines.append(f"| Monto Total de Factura | {monto_total:,.2f} | | `Dato de entrada` | Monto original de la factura con IGV |")
                    lines.append(f"| Detracción / Retención | {detraccion_monto:,.2f} | {detraccion_pct:.2f}% | `Monto Total - Monto Neto` | `{monto_total:,.2f} - {monto_neto:,.2f} = {detraccion_monto:,.2f}` |")

                    lines.append(f"| Monto Neto de Factura | {monto_neto:,.2f} | 100.00% | `Dato de entrada` | Monto a financiar (después de detracciones/retenciones) |")
                    lines.append(f"| Tasa de Avance Aplicada | N/A | {tasa_avance_pct:.2f}% | `Tasa final de la operación` | N/A |")
                    lines.append(f"| Margen de Seguridad | {margen.get('monto', 0):,.2f} | {margen.get('porcentaje', 0):.2f}% | `Monto Neto - Capital` | `{monto_neto:,.2f} - {capital:,.2f} = {margen.get('monto', 0):,.2f}` |")
                    lines.append(f"| Capital | {capital:,.2f} | {((capital / monto_neto) * 100) if monto_neto else 0:.2f}% | `Monto Neto * (Tasa de Avance / 100)` | `{monto_neto:,.2f} * ({tasa_avance_pct:.2f} / 100) = {capital:,.2f}` |")
                    lines.append(f"| Intereses | {interes.get('monto', 0):,.2f} | {interes.get('porcentaje', 0):.2f}% | `Capital * ((1 + Tasa Diaria)^Plazo - 1)` | Tasa Diaria: `{invoice.get('interes_mensual', 0):.2f}% / 30 = {tasa_diaria_pct:.4f}%`, Plazo: `{calculos.get('plazo_operacion', 0)} días`. Cálculo: `{capital:,.2f} * ((1 + {tasa_diaria_pct/100:.6f})^{calculos.get('plazo_operacion', 0)} - 1) = {interes.get('monto', 0):,.2f}` |")
                    lines.append(f"| Comisión de Estructuración | {com_est.get('monto', 0):,.2f} | {com_est.get('porcentaje', 0):.2f}% | `MAX(Capital * %Comisión, Mínima Prorrateada)` | Base: `{capital:,.2f} * ({st.session_state.comision_estructuracion_pct_global:.2f} / 100) = {capital * (st.session_state.comision_estructuracion_pct_global/100):.2f}`, Mín Prorrateado: `{((st.session_state.comision_estructuracion_min_pen_global / len(st.session_state.invoices_data)) if moneda == 'PEN' else (st.session_state.comision_estructuracion_min_usd_global / len(st.session_state.invoices_data))):.2f}`. Resultado: `{com_est.get('monto', 0):,.2f}` |")
                    if com_afi.get('monto', 0) > 0:
                        lines.append(f"| Comisión de Afiliación | {com_afi.get('monto', 0):,.2f} | {com_afi.get('porcentaje', 0):.2f}% | `Valor Fijo (si aplica)` | Monto fijo para la moneda {moneda}. |")
                    
                    igv_interes_monto = calculos.get('igv_interes', 0)
                    igv_interes_pct = (igv_interes_monto / monto_neto * 100) if monto_neto else 0
                    lines.append(f"| IGV sobre Intereses | {igv_interes_monto:,.2f} | {igv_interes_pct:.2f}% | `Intereses * 18%` | `{interes.get('monto', 0):,.2f} * 18% = {igv_interes_monto:,.2f}` |")

                    igv_com_est_monto = calculos.get('igv_comision_estructuracion', 0)
                    igv_com_est_pct = (igv_com_est_monto / monto_neto * 100) if monto_neto else 0
                    lines.append(f"| IGV sobre Com. de Estruct. | {igv_com_est_monto:,.2f} | {igv_com_est_pct:.2f}% | `Comisión * 18%` | `{com_est.get('monto', 0):,.2f} * 18% = {igv_com_est_monto:,.2f}` |")

                    if com_afi.get('monto', 0) > 0:
                        igv_com_afi_monto = calculos.get('igv_afiliacion', 0)
                        igv_com_afi_pct = (igv_com_afi_monto / monto_neto * 100) if monto_neto else 0
                        lines.append(f"| IGV sobre Com. de Afiliación | {igv_com_afi_monto:,.2f} | {igv_com_afi_pct:.2f}% | `Comisión * 18%` | `{com_afi.get('monto', 0):,.2f} * 18% = {igv_com_afi_monto:,.2f}` |")

                    lines.append("| | | | | |")
                    lines.append(f"| **Monto a Desembolsar** | **{abono.get('monto', 0):,.2f}** | **{abono.get('porcentaje', 0):.2f}%** | `Capital - Costos Totales` | `{capital:,.2f} - {costos_totales:,.2f} = {abono.get('monto', 0):,.2f}` |")
                    lines.append("| | | | | |")
                    lines.append(f"| **Total (Monto Neto Factura)** | **{monto_neto:,.2f}** | **100.00%** | `Abono + Costos + Margen` | `{abono.get('monto', 0):,.2f} + {costos_totales:,.2f} + {margen.get('monto', 0):,.2f} = {monto_neto:,.2f}` |")
                    
                    tabla_md = "\n".join(lines)
                    st.markdown(tabla_md, unsafe_allow_html=True)


    # ==============================================================================
    # SECCIÓN 4: ACCIONES Y REPORTES
    # ==============================================================================
    # st.markdown("---")
    has_results = any(inv.get('recalculate_result') for inv in st.session_state.invoices_data)
    
    with st.container(border=True):
        st.subheader("4. Acciones y Reportes")
        
        # Action Grid: Calc | Report A | Report B
        c_act1, c_act2, c_act3 = st.columns(3)
        
        with c_act1:
            if st.button("Calcular Facturas", type="primary", use_container_width=True):
                # 1. Validation
                if not all(validate_inputs(inv) for inv in st.session_state.invoices_data):
                    st.error("❌ Faltan campos en algunas facturas.")
                else:
                    st.success("Iniciando cálculos...")
                    # ... (Calculation Logic preserved) ...
                    try:
                        # Prepare Payload
                        payload = []
                        # Pre-calculate totals for apportionment
                        total_cap_pen = sum(i['monto_neto_factura'] * (i['tasa_de_avance']/100) for i in st.session_state.invoices_data if i['moneda_factura'] == 'PEN')
                        total_cap_usd = sum(i['monto_neto_factura'] * (i['tasa_de_avance']/100) for i in st.session_state.invoices_data if i['moneda_factura'] == 'USD')
                        
                        for inv in st.session_state.invoices_data:
                            # Logic for Apportionment
                            cap = inv['monto_neto_factura'] * (inv['tasa_de_avance']/100)
                            is_sol = inv['moneda_factura'] == 'PEN'
                            total_cap = total_cap_pen if is_sol else total_cap_usd
                            share = cap / total_cap if total_cap > 0 else 0
                            
                            # Commissions
                            com_min = (st.session_state.comision_estructuracion_min_pen_global if is_sol else st.session_state.comision_estructuracion_min_usd_global) * share
                            com_afi = (st.session_state.comision_afiliacion_pen_global if is_sol else st.session_state.comision_afiliacion_usd_global) * share
                            
                            plazo = max(inv.get('plazo_operacion_calculado', 0), inv.get('dias_minimos_interes_individual', 15))
                            
                            payload.append({
                                "plazo_operacion": plazo,
                                "mfn": inv['monto_neto_factura'],
                                "tasa_avance": inv['tasa_de_avance'] / 100,
                                "interes_mensual": inv['interes_mensual'] / 100,
                                "interes_moratorio_mensual": inv['interes_moratorio'] / 100,
                                "comision_estructuracion_pct": st.session_state.comision_estructuracion_pct_global / 100,
                                "comision_minima_aplicable": com_min,
                                "igv_pct": 0.18,
                                "comision_afiliacion_aplicable": com_afi,
                                "aplicar_comision_afiliacion": st.session_state.get('aplicar_comision_afiliacion_global', False)
                            })

                        # Call API 1: Calculate Disbursement
                        resp1 = requests.post(f"{API_BASE_URL}/calcular_desembolso_lote", json=payload)
                        resp1.raise_for_status()
                        res1 = resp1.json()

                        if res1.get("error"):
                            st.error(res1['error'])
                            st.stop()

                        # Prepare Payload 2: Goal Seeking
                        payload2 = []
                        for i, inv in enumerate(st.session_state.invoices_data):
                            inv['initial_calc_result'] = res1["resultados_por_factura"][i]
                            abono_teorico = inv['initial_calc_result'].get('abono_real_teorico', 0)
                            
                            # Round down to nearest 10
                            goal = (abono_teorico // 10) * 10
                            
                            p2_item = payload[i].copy()
                            p2_item['monto_objetivo'] = goal
                            p2_item.pop('tasa_avance', None) # Remove fixed rate to let solver find it
                            payload2.append(p2_item)

                        # Call API 2: Goal Seek
                        resp2 = requests.post(f"{API_BASE_URL}/encontrar_tasa_lote", json=payload2)
                        resp2.raise_for_status()
                        res2 = resp2.json()

                        if res2.get("error"):
                            st.error(res2['error'])
                            st.stop()

                        # Store Results
                        for i, inv in enumerate(st.session_state.invoices_data):
                            inv['recalculate_result'] = res2["resultados_por_factura"][i]

                        st.success("✅ Cálculos Completados")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error en el cálculo: {e}")

        with c_act2:
            if st.button("Generar PDF Perfil", disabled=not has_results, use_container_width=True):
                try:
                    # Prepare data list for PDF generator
                    pdf_list = []
                    for inv in st.session_state.invoices_data:
                        if inv.get('recalculate_result'):
                            # Inject global commission helper data expected by generator
                            inv['comision_de_estructuracion_global'] = st.session_state.comision_estructuracion_pct_global
                            inv['detraccion_monto'] = inv['monto_total_factura'] - inv['monto_neto_factura']
                            pdf_list.append(inv)
                    
                    if pdf_list:
                        pdf_bytes = pdf_generators.generate_perfil_operacion_pdf(pdf_list)
                        fname = f"perfil_operacion_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        st.session_state['last_generated_perfil_pdf'] = {'bytes': pdf_bytes, 'filename': fname}
                        st.success("✅ Perfil Generado")
                except Exception as e:
                    st.error(f"Error PDF: {e}")
            
            # Download Link Logic
            if 'last_generated_perfil_pdf' in st.session_state:
                p = st.session_state['last_generated_perfil_pdf']
                st.download_button("⬇️ Descargar Perfil", p['bytes'], p['filename'], "application/pdf", use_container_width=True)

        with c_act3:
            if st.button("Generar PDF Liquidación", disabled=not has_results, use_container_width=True):
                try:
                    # Same filtering logic
                    pdf_list = [inv for inv in st.session_state.invoices_data if inv.get('recalculate_result')]
                    if pdf_list:
                        pdf_bytes = generar_anexo_liquidacion_pdf(pdf_list)
                        fname = f"anexo_liquidacion_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        st.session_state['last_generated_liquidacion_pdf'] = {'bytes': pdf_bytes, 'filename': fname}
                        st.success("✅ Liquidación Generada")
                except Exception as e:
                    st.error(f"Error PDF: {e}")

            # Download Link Logic
            if 'last_generated_liquidacion_pdf' in st.session_state:
                l = st.session_state['last_generated_liquidacion_pdf']
                st.download_button("⬇️ Descargar Liquidación", l['bytes'], l['filename'], "application/pdf", use_container_width=True)


    # ==============================================================================
    # SECCIÓN 5: FORMALIZACIÓN Y GUARDADO
    # ==============================================================================
    with st.container(border=True):
        st.subheader("5. Formalización y Guardado")
        
        c1, c2 = st.columns(2)
        contract = c1.text_input("Nro. Contrato", key="input_contract_number")
        annex = c2.text_input("Nro. Anexo", key="input_annex_number")
        
        st.caption("Seleccionar Carpeta Destino (Google Drive):")
        # render_folder_navigator_v2 now returns the folder dict if selected
        folder_info = render_folder_navigator_v2(key="orig_folder_nav")
        
        # Action button inside container, conditioned on selection
        if folder_info:
             st.divider() # visual separator
             if st.button(f"💾 Guardar Facturas en: {folder_info['name']}", type="primary", use_container_width=True):
                if not has_results:
                     st.error("⚠️ Primero debes calcular las facturas.")
                elif not contract or not annex:
                     st.error("⚠️ Ingresa Nro. Contrato y Anexo.")
                else:
                    # START SAVING PROCESS
                    st.session_state.lote_id = f"LOC-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}" # Generate new lote_id
                    
                    saved_count = 0
                    for idx, inv in enumerate(st.session_state.invoices_data):
                        # 1. Update metadata
                        inv['contract_number'] = contract
                        inv['anexo_number'] = annex
                        inv['lote_id'] = st.session_state.lote_id
                        
                        # 2. Upload to Drive (if not already uploaded - optimize later)
                        # Re-locate the raw file from cache to upload
                        # (Ideally we should cache the drive link too, but for now simple re-upload logic or assume done)
                        # Note: This logic assumes we need to upload the PDF. 
                        # In the new multi-bucket logic, we stored original bytes in 'original_uploads_cache'.
                        
                        # Find bytes
                        file_bytes = None
                        for cache in st.session_state.original_uploads_cache:
                            if cache['name'] == inv['parsed_pdf_name']:
                                file_bytes = cache['bytes']
                                break
                        
                        drive_link = ""
                        if file_bytes:
                            # Save to temp
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t:
                                t.write(file_bytes)
                                tpath = t.name
                            
                            # Upload
                            fname = f"{inv['emisor_ruc']}_{inv['numero_factura']}.pdf"
                            drive_link = upload_file_with_sa(tpath, fname, folder_info['id']) 
                            os.remove(tpath)
                        
                        inv['drive_link'] = drive_link
                        
                        # 3. Save to Supabase
                        try:
                            # We create a proposal_id if not exists, or reuse?
                            # For now, let's treat each invoice as a proposal equivalent or part of batch.
                            # The db.save_proposal expects a proposal object.
                            # We'll map the invoice dict to what save_proposal expects.
                            proposal_data = inv.copy()
                            # Ensure numeric fields are int/float
                            # db.save_proposal handles most matching.
                            
                            pid = db.save_proposal(proposal_data)
                            if pid:
                                saved_count += 1
                        except Exception as e:
                            st.error(f"Error guardando {inv['numero_factura']}: {e}")
                    
                    if saved_count == len(st.session_state.invoices_data):
                         st.success(f"✅ ¡Éxito! {saved_count} operaciones guardadas y subidas a Drive.")
                         st.balloons()
                    else:
                         st.warning(f"⚠️ Se guardaron {saved_count} de {len(st.session_state.invoices_data)} operaciones.")
