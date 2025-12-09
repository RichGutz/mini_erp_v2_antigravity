import os
import json
import datetime
import tempfile
import requests
import streamlit as st

# --- Project Imports ---
# This page only needs to know the project root for static assets.
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
    [data-testid="stHorizontalBlock"] { 
        align-items: flex-start; 
    }
    .stButton>button.red-button {
        background-color: #FF4B4B;
        color: white;
        border-color: #FF4B4B;
    }
    .stButton>button.red-button:hover {
        background-color: #FF6F6F;
        border-color: #FF6F6F;
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


# --- Session State Initialization ---
defaults = {
    'invoices_data': [],
    'pdf_datos_cargados': False,
    'last_uploaded_pdf_files_ids': [],
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
col1, col2, col3 = st.columns([0.25, 0.5, 0.25], vertical_alignment="center")
with col1:
    st.image(os.path.join(project_root, "static", "logo_geek.png"), width=200)
with col2:
    st.markdown("<h2 style='text-align: center; font-size: 2.4em;'>Módulo de Originación</h2>", unsafe_allow_html=True)
with col3:
    empty_col, logo_col = st.columns([2, 1])
    with logo_col:
        st.image(os.path.join(project_root, "static", "logo_inandes.png"), width=195)


# --- Section 1: File Upload ---
with st.expander("📂 Carga de Facturas (PDF)", expanded=True):
    uploaded_pdf_files = st.file_uploader("Seleccionar archivos", type=["pdf"], key="pdf_uploader_main", accept_multiple_files=True)

    if uploaded_pdf_files:
        current_file_ids = [f.file_id for f in uploaded_pdf_files]
        
        # Reset if new files uploaded
        if "last_uploaded_pdf_files_ids" not in st.session_state or \
           current_file_ids != st.session_state.last_uploaded_pdf_files_ids:
            st.session_state.invoices_data = []
            st.session_state.last_uploaded_pdf_files_ids = current_file_ids
            st.session_state.pdf_datos_cargados = False
            st.session_state.original_uploads_cache = []

        if not st.session_state.pdf_datos_cargados:
            for uploaded_file in uploaded_pdf_files:
                # 1. Cache raw content
                file_bytes_content = uploaded_file.getvalue()
                st.session_state.original_uploads_cache.append({
                    'name': uploaded_file.name,
                    'bytes': file_bytes_content
                })

                # 2. Process File
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(file_bytes_content)
                    temp_file_path = tmp.name

                with st.spinner(f"Procesando {uploaded_file.name}..."):
                    try:
                        parsed_data = pdf_parser.extract_fields_from_pdf(temp_file_path)
                        if parsed_data.get("error"):
                            st.error(f"Error al procesar el PDF {uploaded_file.name}: {parsed_data['error']}")
                        else:
                            # Initialize Invoice Object
                            invoice_entry = {
                                'emisor_ruc': parsed_data.get('emisor_ruc', ''),
                                'aceptante_ruc': parsed_data.get('aceptante_ruc', ''),
                                'fecha_emision_factura': parsed_data.get('fecha_emision', ''),
                                'monto_total_factura': parsed_data.get('monto_total', 0.0),
                                'monto_neto_factura': parsed_data.get('monto_neto', 0.0),
                                'moneda_factura': parsed_data.get('moneda', 'PEN'),
                                'numero_factura': parsed_data.get('invoice_id', ''),
                                'parsed_pdf_name': uploaded_file.name,
                                'file_id': uploaded_file.file_id,
                                'emisor_nombre': db.get_razon_social_by_ruc(parsed_data.get('emisor_ruc', '')),
                                'aceptante_nombre': db.get_razon_social_by_ruc(parsed_data.get('aceptante_ruc', '')),
                                'plazo_credito_dias': None,
                                'fecha_desembolso_factoring': '',
                                'tasa_de_avance': st.session_state.default_tasa_de_avance,
                                'interes_mensual': st.session_state.default_interes_mensual,
                                'interes_moratorio': st.session_state.default_interes_moratorio,
                                'comision_afiliacion_pen': st.session_state.default_comision_afiliacion_pen,
                                'comision_afiliacion_usd': st.session_state.default_comision_afiliacion_usd,
                                'aplicar_comision_afiliacion': False,
                                'detraccion_porcentaje': 0.0,
                                'fecha_pago_calculada': parsed_data.get('fecha_vencimiento', ''),
                                'plazo_operacion_calculado': 0,
                                'initial_calc_result': None,
                                'recalculate_result': None,
                                'dias_minimos_interes_individual': 15,
                            }
                            st.session_state.invoices_data.append(invoice_entry)
                            st.success(f"Datos de {uploaded_file.name} cargados.")
                    except Exception as e:
                        st.error(f"Error al parsear el PDF {uploaded_file.name}: {e}")
                    finally:
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
            st.session_state.pdf_datos_cargados = True


# --- Section 2: Global Configuration ---
if st.session_state.invoices_data:
    st.markdown("---")
    st.subheader("Configuración Global")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("##### Comisiones Globales")
        st.write("---")
        st.write("**Com. de Estructuración**")
        st.checkbox("Aplicar Comisión de Estructuración", key='aplicar_comision_estructuracion_global')
        st.number_input("Comisión de Estructuración (%)", min_value=0.0, key='comision_estructuracion_pct_global', format="%.2f", disabled=not st.session_state.get('aplicar_comision_estructuracion_global', False))
        st.number_input("Comisión Mínima (PEN)", min_value=0.0, key='comision_estructuracion_min_pen_global', format="%.2f", disabled=not st.session_state.get('aplicar_comision_estructuracion_global', False))
        st.number_input("Comisión Mínima (USD)", min_value=0.0, key='comision_estructuracion_min_usd_global', format="%.2f", disabled=not st.session_state.get('aplicar_comision_estructuracion_global', False))
        
        st.write("**Com. de Afiliación**")
        st.checkbox("Aplicar Comisión de Afiliación", key='aplicar_comision_afiliacion_global')
        st.number_input("Monto Comisión Afiliación (PEN)", min_value=0.0, key='comision_afiliacion_pen_global', format="%.2f", disabled=not st.session_state.get('aplicar_comision_afiliacion_global', False))
        st.number_input("Monto Comisión Afiliación (USD)", min_value=0.0, key='comision_afiliacion_usd_global', format="%.2f", disabled=not st.session_state.get('aplicar_comision_afiliacion_global', False))

    with col2:
        st.write("##### Tasas Globales")
        st.checkbox("Aplicar Tasa de Avance Global", key='aplicar_tasa_avance_global', on_change=handle_global_tasa_avance_change)
        st.number_input("Tasa de Avance Global (%)", key='tasa_avance_global', min_value=0.0, format="%.2f", disabled=not st.session_state.get('aplicar_tasa_avance_global', False), on_change=handle_global_tasa_avance_change)
        
        st.checkbox("Aplicar Interés Mensual Global", key='aplicar_interes_mensual_global', on_change=handle_global_interes_mensual_change)
        st.number_input("Interés Mensual Global (%)", key='interes_mensual_global', min_value=0.0, format="%.2f", disabled=not st.session_state.get('aplicar_interes_mensual_global', False), on_change=handle_global_interes_mensual_change)
        
        st.checkbox("Aplicar Interés Moratorio Global", key='aplicar_interes_moratorio_global', on_change=handle_global_interes_moratorio_change)
        st.number_input("Interés Moratorio Global (%)", key='interes_moratorio_global', min_value=0.0, format="%.2f", disabled=not st.session_state.get('aplicar_interes_moratorio_global', False), on_change=handle_global_interes_moratorio_change)

    with col3:
        st.write("##### Fechas Globales")
        st.checkbox("Aplicar Fecha de Pago Global", key='aplicar_fecha_vencimiento_global', on_change=handle_global_payment_date_change)
        st.date_input("Fecha de Pago Global", key='fecha_vencimiento_global', format="DD-MM-YYYY", disabled=not st.session_state.get('aplicar_fecha_vencimiento_global', False), on_change=handle_global_payment_date_change)
        
        st.checkbox("Aplicar Fecha de Desembolso Global", key='aplicar_fecha_desembolso_global', on_change=handle_global_disbursement_date_change)
        st.date_input("Fecha de Desembolso Global", key='fecha_desembolso_global', format="DD-MM-YYYY", disabled=not st.session_state.get('aplicar_fecha_desembolso_global', False), on_change=handle_global_disbursement_date_change)
        
        st.write("**Días Mínimos de Interés**")
        st.checkbox("Aplicar Días Mínimos", key='aplicar_dias_interes_minimo_global', on_change=handle_global_min_interest_days_change)
        st.number_input("Valor Días Mínimos", key='dias_interes_minimo_global', min_value=0, step=1, on_change=handle_global_min_interest_days_change)


# --- Section 3: Invoice Form ---
if st.session_state.invoices_data:
    for idx, invoice in enumerate(st.session_state.invoices_data):
        st.markdown("---")
        st.write(f"### Factura {idx + 1}: {invoice.get('parsed_pdf_name', 'N/A')}")

        with st.container():
            st.write("##### Involucrados")
            c1, c2, c3, c4 = st.columns(4)
            with c1: invoice['emisor_nombre'] = st.text_input("NOMBRE DEL EMISOR", value=invoice.get('emisor_nombre', ''), key=f"emisor_nombre_{idx}")
            with c2: invoice['emisor_ruc'] = st.text_input("RUC DEL EMISOR", value=invoice.get('emisor_ruc', ''), key=f"emisor_ruc_{idx}")
            with c3: invoice['aceptante_nombre'] = st.text_input("NOMBRE DEL ACEPTANTE", value=invoice.get('aceptante_nombre', ''), key=f"aceptante_nombre_{idx}")
            with c4: invoice['aceptante_ruc'] = st.text_input("RUC DEL ACEPTANTE", value=invoice.get('aceptante_ruc', ''), key=f"aceptante_ruc_{idx}")

        with st.container():
            st.write("##### Montos y Moneda")
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
            st.write("##### Fechas y Plazos")
            
            # Callbacks for date widgets to sync logic
            def _on_fecha_pago_changed(i):
                dt_obj = st.session_state.get(f"fecha_pago_calculada_{i}")
                st.session_state.invoices_data[i]['fecha_pago_calculada'] = dt_obj.strftime('%d-%m-%Y') if dt_obj else ''
                update_date_calculations(st.session_state.invoices_data[i], changed_field='fecha', idx=i)

            def _on_fecha_desembolso_changed(i):
                dt_obj = st.session_state.get(f"fecha_desembolso_factoring_{i}")
                st.session_state.invoices_data[i]['fecha_desembolso_factoring'] = dt_obj.strftime('%d-%m-%Y') if dt_obj else ''
                update_date_calculations(st.session_state.invoices_data[i], idx=i)

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                # Emission Date
                em_obj = to_date_obj(invoice.get('fecha_emision_factura'))
                new_em = st.date_input("Fecha Emisión", value=em_obj or datetime.date.today(), key=f"fetcha_em_input_{idx}", format="DD-MM-YYYY", disabled=bool(em_obj))
                if not em_obj: invoice['fecha_emision_factura'] = new_em.strftime('%d-%m-%Y')

            with c2:
                des_obj = to_date_obj(invoice.get('fecha_desembolso_factoring'))
                st.date_input("Fecha Desembolso", value=des_obj or datetime.date.today(), key=f"fecha_desembolso_factoring_{idx}", format="DD-MM-YYYY", on_change=_on_fecha_desembolso_changed, args=(idx,))

            with c3:
                pag_obj = to_date_obj(invoice.get('fecha_pago_calculada'))
                st.date_input("Fecha Pago", value=pag_obj or datetime.date.today(), key=f"fecha_pago_calculada_{idx}", format="DD-MM-YYYY", on_change=_on_fecha_pago_changed, args=(idx,))

            with c4:
                plazo = st.session_state.invoices_data[idx].get('plazo_operacion_calculado', 0)
                if st.session_state.invoices_data[idx].get('fecha_error', False):
                    st.warning("⚠️ Fecha Pago < Desembolso")
                st.text_input("Plazo (días)", value=str(plazo), disabled=True, key=f"plazo_operacion_calculado_{idx}")

            with c5:
                invoice['dias_minimos_interes_individual'] = st.number_input("Días Mínimos", value=invoice.get('dias_minimos_interes_individual', 15), min_value=0, key=f"dias_minimos_interes_individual_{idx}")

        with st.container():
            st.write("##### Tasas y Comisiones")
            is_locked = idx > 0 and st.session_state.fijar_condiciones
            c1, c2, c3 = st.columns(3)
            with c1: invoice['tasa_de_avance'] = st.number_input("Tasa de Avance (%)", min_value=0.0, value=invoice.get('tasa_de_avance', 98.0), key=f"tasa_de_avance_{idx}", disabled=is_locked, on_change=propagate_commission_changes)
            with c2: invoice['interes_mensual'] = st.number_input("Interés Mensual (%)", min_value=0.0, value=invoice.get('interes_mensual', 1.25), key=f"interes_mensual_{idx}", disabled=is_locked, on_change=propagate_commission_changes)
            with c3: invoice['interes_moratorio'] = st.number_input("Interés Moratorio (%)", min_value=0.0, value=invoice.get('interes_moratorio', 2.5), key=f"interes_moratorio_{idx}", disabled=is_locked, on_change=propagate_commission_changes)

        st.markdown("---")
        
        # --- Results Display ---
        if invoice.get('recalculate_result'):
            with st.container():
                st.write("##### Perfil de la Operación")
                st.markdown(
                    f"**Emisor:** {invoice.get('emisor_nombre')} | **Aceptante:** {invoice.get('aceptante_nombre')} | "
                    f"**Factura:** {invoice.get('numero_factura')} | **Monto Neto:** {invoice.get('moneda_factura')} {invoice.get('monto_neto_factura', 0):,.2f}"
                )
                
                # Extract calculation details
                res = invoice['recalculate_result']
                desglose = res.get('desglose_final_detallado', {})
                calc = res.get('calculo_con_tasa_encontrada', {})
                
                # ... (Display Table Logic preserved but simplified for readability) ...
                moneda = invoice.get('moneda_factura', 'PEN')
                capital = calc.get('capital', 0)
                monto_neto = invoice.get('monto_neto_factura', 0)
                interes = desglose.get('interes', {})
                abono = desglose.get('abono', {})
                
                # Simple Table using markdown
                md_table = f"""
| Concepto | Monto ({moneda}) | Detalle |
| :--- | :--- | :--- |
| **Monto Neto** | **{monto_neto:,.2f}** | |
| Capital Financiado | {capital:,.2f} | {((capital/monto_neto)*100):.2f}% del Neto |
| Intereses | {interes.get('monto', 0):,.2f} | {calc.get('plazo_operacion', 0)} días |
| **Abono al Cliente** | **{abono.get('monto', 0):,.2f}** | **Monto a Desembolsar** |
"""
                st.markdown(md_table)


    # --- Action Buttons ---
    st.markdown("---")
    has_results = any(inv.get('recalculate_result') for inv in st.session_state.invoices_data)
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
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

    with col_btn2:
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
            st.download_button("⬇️ Descargar Perfil", p['bytes'], p['filename'], "application/pdf")

    with col_btn3:
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
            st.download_button("⬇️ Descargar Liquidación", l['bytes'], l['filename'], "application/pdf")


    # --- Section 4: Save & Upload ---
    st.markdown("---")
    st.subheader("📚 Formalización y Guardado")
    
    with st.container(border=True):
        st.info("Paso Final: Upload & Save")
        
        c1, c2 = st.columns(2)
        contract = c1.text_input("Nro. Contrato", key="input_contract_number")
        annex = c2.text_input("Nro. Anexo", key="input_annex_number")
        
        st.write("Seleccionar Carpeta Google Drive:")
        folder_info = render_folder_navigator_v2(key="orig_folder_nav")
        
        if folder_info:
            st.success(f"📂 Carpeta: {folder_info['name']}")
        
        if st.button("💾 Guardar y Subir", type="primary", use_container_width=True, disabled=not folder_info):
            if not contract or not annex:
                st.error("Faltan datos de contrato/anexo")
            elif not st.session_state.invoices_data:
                st.error("No hay datos")
            else:
                with st.spinner("Guardando..."):
                    # 1. Save DB
                    lote_id = f"LOTE_{contract}_{annex}".replace(" ", "_")
                    saved_count = 0
                    
                    for inv in st.session_state.invoices_data:
                        if inv.get('recalculate_result'):
                            inv['contract_number'] = contract
                            inv['anexo_number'] = annex
                            ok, msg = db.save_proposal(inv, lote_id)
                            if ok: saved_count += 1
                    
                    st.success(f"✅ {saved_count} Registros guardados en BD")

                    # 2. Upload Files to Drive
                    drive_errs = []
                    
                    # Upload Perfil
                    if 'last_generated_perfil_pdf' in st.session_state:
                        f = st.session_state['last_generated_perfil_pdf']
                        ok, res = upload_file_with_sa(f['bytes'], f['filename'], folder_info['id'], SA_CREDENTIALS)
                        if ok: st.write(f"✅ Perfil subido: {f['filename']}")
                        else: drive_errs.append(res)

                    # Upload Liquidacion
                    if 'last_generated_liquidacion_pdf' in st.session_state:
                        f = st.session_state['last_generated_liquidacion_pdf']
                        ok, res = upload_file_with_sa(f['bytes'], f['filename'], folder_info['id'], SA_CREDENTIALS)
                        if ok: st.write(f"✅ Liquidación subida: {f['filename']}")
                        else: drive_errs.append(res)

                    # Upload Originals
                    if 'original_uploads_cache' in st.session_state:
                         for f in st.session_state.original_uploads_cache:
                            ok, res = upload_file_with_sa(f['bytes'], f['name'], folder_info['id'], SA_CREDENTIALS)
                            if ok: st.write(f"✅ Original subido: {f['name']}")
                            else: drive_errs.append(res)
                    
                    if not drive_errs:
                        st.balloons()
                        # Enable Email Sender Persistence
                        st.session_state.show_email_originacion = True
                        st.session_state.email_docs_originacion = []
                        
                        # Populate Email Docs
                        if 'last_generated_perfil_pdf' in st.session_state:
                             p = st.session_state['last_generated_perfil_pdf']
                             st.session_state.email_docs_originacion.append({'name': p['filename'], 'bytes': p['bytes']})
                        
                        if 'last_generated_liquidacion_pdf' in st.session_state:
                             l = st.session_state['last_generated_liquidacion_pdf']
                             st.session_state.email_docs_originacion.append({'name': l['filename'], 'bytes': l['bytes']})
                             
                        if 'original_uploads_cache' in st.session_state:
                            for f in st.session_state.original_uploads_cache:
                                st.session_state.email_docs_originacion.append({'name': f['name'], 'bytes': f['bytes']})
                                
                    else:
                        st.error(f"Errores subiendo Drive: {drive_errs}")

    # --- Email Sender (Persistent) ---
    if st.session_state.get('show_email_originacion'):
        st.markdown("---")
        render_email_sender(key_suffix="originacion", documents=st.session_state.get('email_docs_originacion', []))