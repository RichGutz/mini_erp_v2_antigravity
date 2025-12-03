import streamlit as st
import requests
import os
import datetime
import json
import tempfile
import sys

# --- Path Setup ---
# The main script (00_Home.py) handles adding 'src' to the path.
# This page only needs to know the project root for static assets.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# --- Module Imports from `src` ---
from src.services import pdf_parser
from src.data import supabase_repository as db
from src.utils import pdf_generators
from src.utils.pdf_generators import generar_anexo_liquidacion_pdf

# --- Estrategia Unificada para la URL del Backend ---

# 1. Intenta leer la URL desde una variable de entorno local (para desarrollo).
#    Esta es la que usarás para apuntar a Render desde tu máquina.
API_BASE_URL = os.getenv("BACKEND_API_URL")

# 2. Si no la encuentra, intenta leerla desde los secretos de Streamlit (para la nube).
if not API_BASE_URL:
    try:
        API_BASE_URL = st.secrets["backend_api"]["url"]
    except (KeyError, AttributeError):
        # 3. Si todo falla, muestra un error claro.
        st.error("La URL del backend no está configurada. Define BACKEND_API_URL o configúrala en st.secrets.")
        st.stop() # Detiene la ejecución si no hay URL

st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Calculadora de Factoring INANDES",
    page_icon="📊",
)

# --- Funciones de Ayuda y Callbacks ---
def update_date_calculations(invoice, changed_field=None):
    try:
        fecha_emision_str = invoice.get('fecha_emision_factura')
        if not fecha_emision_str:
            invoice['fecha_pago_calculada'] = ""
            invoice['plazo_credito_dias'] = 0
            invoice['plazo_operacion_calculado'] = 0
            return

        fecha_emision_dt = datetime.datetime.strptime(fecha_emision_str, "%d-%m-%Y")

        # Solo calculamos desde fecha de pago (campo plazo_credito eliminado de UI)
        if invoice.get('fecha_pago_calculada'):
            fecha_pago_dt = datetime.datetime.strptime(invoice['fecha_pago_calculada'], "%d-%m-%Y")
            if fecha_pago_dt > fecha_emision_dt:
                invoice['plazo_credito_dias'] = (fecha_pago_dt - fecha_emision_dt).days
            else:
                invoice['plazo_credito_dias'] = 0
        else:
            invoice['fecha_pago_calculada'] = ""
            invoice['plazo_credito_dias'] = 0

        if invoice.get('fecha_pago_calculada') and invoice.get('fecha_desembolso_factoring'):
            fecha_pago_dt = datetime.datetime.strptime(invoice['fecha_pago_calculada'], "%d-%m-%Y")
            fecha_desembolso_dt = datetime.datetime.strptime(invoice['fecha_desembolso_factoring'], "%d-%m-%Y")
            invoice['plazo_operacion_calculado'] = (fecha_pago_dt - fecha_desembolso_dt).days if fecha_pago_dt >= fecha_desembolso_dt else 0
        else:
            invoice['plazo_operacion_calculado'] = 0

    except (ValueError, TypeError, AttributeError):
        invoice['fecha_pago_calculada'] = ""
        invoice['plazo_operacion_calculado'] = 0

def validate_inputs(invoice):
    required_fields = {
        "emisor_nombre": "Nombre del Emisor", "emisor_ruc": "RUC del Emisor",
        "aceptante_nombre": "Nombre del Aceptante", "aceptante_ruc": "RUC del Aceptante",
        "numero_factura": "Número de Factura", "moneda_factura": "Moneda de Factura",
        "fecha_emision_factura": "Fecha de Emisión",
        "tasa_de_avance": "Tasa de Avance",
        "interes_mensual": "Interés Mensual",
        "fecha_pago_calculada": "Fecha de Pago", "fecha_desembolso_factoring": "Fecha de Desembolso",
    }
    is_valid = True
    for key, name in required_fields.items():
        if not invoice.get(key):
            is_valid = False
    
    numeric_fields = {
        "monto_total_factura": "Monto Factura Total", "monto_neto_factura": "Monto Factura Neto",
        "tasa_de_avance": "Tasa de Avance", "interes_mensual": "Interés Mensual"
    }
    for key, name in numeric_fields.items():
        if invoice.get(key, 0) <= 0:
            is_valid = False
    return is_valid

def flatten_db_proposal(proposal):
    recalc_result = proposal.get('recalculate_result', {})
    if isinstance(recalc_result, str):
        try:
            recalc_result = json.loads(recalc_result)
        except json.JSONDecodeError:
            recalc_result = {}

    desglose = recalc_result.get('desglose_final_detallado', {})
    calculos = recalc_result.get('calculo_con_tasa_encontrada', {})
    busqueda = recalc_result.get('resultado_busqueda', {})
    
    proposal['advance_amount'] = calculos.get('capital', 0)
    proposal['commission_amount'] = desglose.get('comision_estructuracion', {}).get('monto', 0)
    proposal['interes_calculado'] = desglose.get('interes', {}).get('monto', 0)
    proposal['igv_interes_calculado'] = calculos.get('igv_interes', 0)
    proposal['initial_disbursement'] = desglose.get('abono', {}).get('monto', 0)
    proposal['security_margin'] = desglose.get('margen_seguridad', {}).get('monto', 0)
    
    if 'invoice_net_amount' not in proposal or proposal['invoice_net_amount'] == 0:
        proposal['invoice_net_amount'] = recalc_result.get('calculo_con_tasa_encontrada', {}).get('mfn', 0.0)
    
    if 'advance_rate' not in proposal or proposal['advance_rate'] == 0:
        proposal['advance_rate'] = recalc_result.get('resultado_busqueda', {}).get('tasa_avance_encontrada', 0) * 100

    return proposal

def propagate_commission_changes():
    if st.session_state.get('fijar_condiciones', False) and st.session_state.invoices_data and len(st.session_state.invoices_data) > 1:
        first_invoice = st.session_state.invoices_data[0]
        first_invoice['tasa_de_avance'] = st.session_state.get(f"tasa_de_avance_0", first_invoice['tasa_de_avance'])
        first_invoice['interes_mensual'] = st.session_state.get(f"interes_mensual_0", first_invoice['interes_mensual'])
        first_invoice['interes_moratorio'] = st.session_state.get(f"interes_moratorio_0", first_invoice['interes_moratorio'])
        first_invoice['comision_afiliacion_pen'] = st.session_state.get(f"comision_afiliacion_pen_0", first_invoice['comision_afiliacion_pen'])
        first_invoice['comision_afiliacion_usd'] = st.session_state.get(f"comision_afiliacion_usd_0", first_invoice['comision_afiliacion_usd'])

        for i in range(1, len(st.session_state.invoices_data)):
            invoice = st.session_state.invoices_data[i]
            invoice['tasa_de_avance'] = first_invoice['tasa_de_avance']
            invoice['interes_mensual'] = first_invoice['interes_mensual']
            invoice['interes_moratorio'] = first_invoice['interes_moratorio']
            invoice['comision_afiliacion_pen'] = first_invoice['comision_afiliacion_pen']
            invoice['comision_afiliacion_usd'] = first_invoice['comision_afiliacion_usd']

def handle_global_payment_date_change():
    if st.session_state.get('aplicar_fecha_vencimiento_global') and st.session_state.get('fecha_vencimiento_global'):
        global_due_date_str = st.session_state.fecha_vencimiento_global.strftime('%d-%m-%Y')
        for invoice in st.session_state.invoices_data:
            invoice['fecha_pago_calculada'] = global_due_date_str
            update_date_calculations(invoice, changed_field='fecha')
        st.toast("Fecha de pago global aplicada a todas las facturas.")

def handle_global_disbursement_date_change():
    if st.session_state.get('aplicar_fecha_desembolso_global') and st.session_state.get('fecha_desembolso_global'):
        global_disbursement_date_str = st.session_state.fecha_desembolso_global.strftime('%d-%m-%Y')
        for invoice in st.session_state.invoices_data:
            invoice['fecha_desembolso_factoring'] = global_disbursement_date_str
            update_date_calculations(invoice)
        st.toast("Fecha de desembolso global aplicada a todas las facturas.")

def handle_global_tasa_avance_change():
    if st.session_state.get('aplicar_tasa_avance_global') and st.session_state.get('tasa_avance_global') is not None:
        global_tasa = st.session_state.tasa_avance_global
        for invoice in st.session_state.invoices_data:
            invoice['tasa_de_avance'] = global_tasa
        st.toast("Tasa de avance global aplicada a todas las facturas.")

def handle_global_interes_mensual_change():
    if st.session_state.get('aplicar_interes_mensual_global') and st.session_state.get('interes_mensual_global') is not None:
        global_interes = st.session_state.interes_mensual_global
        for invoice in st.session_state.invoices_data:
            invoice['interes_mensual'] = global_interes
        st.toast("Interés mensual global aplicado a todas las facturas.")

def handle_global_interes_moratorio_change():
    if st.session_state.get('aplicar_interes_moratorio_global') and st.session_state.get('interes_moratorio_global') is not None:
        global_interes_moratorio = st.session_state.interes_moratorio_global
        for invoice in st.session_state.invoices_data:
            invoice['interes_moratorio'] = global_interes_moratorio
        st.toast("Interés moratorio global aplicado a todas las facturas.")

def handle_global_min_interest_days_change():
    if st.session_state.get('aplicar_dias_interes_minimo_global'):
        global_min_days = st.session_state.dias_interes_minimo_global
        for invoice in st.session_state.invoices_data:
            invoice['dias_minimos_interes_individual'] = global_min_days
        st.toast("Días de interés mínimo global aplicado a todas las facturas.")

# --- Inicialización del Session State ---
if 'invoices_data' not in st.session_state: st.session_state.invoices_data = []
if 'pdf_datos_cargados' not in st.session_state: st.session_state.pdf_datos_cargados = False
if 'last_uploaded_pdf_files_ids' not in st.session_state: st.session_state.last_uploaded_pdf_files_ids = []
if 'last_saved_proposal_id' not in st.session_state: st.session_state.last_saved_proposal_id = ''
if 'anexo_number' not in st.session_state: st.session_state.anexo_number = ''
if 'contract_number' not in st.session_state: st.session_state.contract_number = ''
if 'fijar_condiciones' not in st.session_state: st.session_state.fijar_condiciones = False

if 'aplicar_comision_afiliacion_global' not in st.session_state: st.session_state.aplicar_comision_afiliacion_global = False
if 'comision_afiliacion_pen_global' not in st.session_state: st.session_state.comision_afiliacion_pen_global = 200.0
if 'comision_afiliacion_usd_global' not in st.session_state: st.session_state.comision_afiliacion_usd_global = 50.0

if 'aplicar_comision_estructuracion_global' not in st.session_state: st.session_state.aplicar_comision_estructuracion_global = False
if 'comision_estructuracion_pct_global' not in st.session_state: st.session_state.comision_estructuracion_pct_global = 0.5
if 'comision_estructuracion_min_pen_global' not in st.session_state: st.session_state.comision_estructuracion_min_pen_global = 200.0
if 'comision_estructuracion_min_usd_global' not in st.session_state: st.session_state.comision_estructuracion_min_usd_global = 50.0

if 'aplicar_fecha_vencimiento_global' not in st.session_state: st.session_state.aplicar_fecha_vencimiento_global = False
if 'fecha_vencimiento_global' not in st.session_state: st.session_state.fecha_vencimiento_global = datetime.date.today()

if 'aplicar_fecha_desembolso_global' not in st.session_state: st.session_state.aplicar_fecha_desembolso_global = False
if 'fecha_desembolso_global' not in st.session_state: st.session_state.fecha_desembolso_global = datetime.date.today()

if 'aplicar_dias_interes_minimo_global' not in st.session_state: st.session_state.aplicar_dias_interes_minimo_global = False
if 'dias_interes_minimo_global' not in st.session_state: st.session_state.dias_interes_minimo_global = 15

if 'default_comision_afiliacion_pen' not in st.session_state: st.session_state.default_comision_afiliacion_pen = 200.0
if 'default_comision_afiliacion_usd' not in st.session_state: st.session_state.default_comision_afiliacion_usd = 50.0
if 'default_tasa_de_avance' not in st.session_state: st.session_state.default_tasa_de_avance = 98.0
if 'default_interes_mensual' not in st.session_state: st.session_state.default_interes_mensual = 1.25
if 'default_interes_moratorio' not in st.session_state: st.session_state.default_interes_moratorio = 2.5

if 'aplicar_tasa_avance_global' not in st.session_state: st.session_state.aplicar_tasa_avance_global = False
if 'tasa_avance_global' not in st.session_state: st.session_state.tasa_avance_global = st.session_state.default_tasa_de_avance
if 'aplicar_interes_mensual_global' not in st.session_state: st.session_state.aplicar_interes_mensual_global = False
if 'interes_mensual_global' not in st.session_state: st.session_state.interes_mensual_global = st.session_state.default_interes_mensual
if 'aplicar_interes_moratorio_global' not in st.session_state: st.session_state.aplicar_interes_moratorio_global = False
if 'interes_moratorio_global' not in st.session_state: st.session_state.interes_moratorio_global = st.session_state.default_interes_moratorio

# --- UI: Título y CSS ---
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

# --- Comments for Buttons ---
COMMENT_CALCULAR = "Revise todos los parámetros antes de calcular. Si después de ejecutar el cálculo detecta algún error de ingreso, puede corregir la variable y volver a calcular."
COMMENT_GRABAR = "Suba a la base de datos si está seguro de los detalles de la operación. Puede Generar perfil de operation sin subir a la base de datos."
COMMENT_PERFIL = "Genere el perfil completo de la operación sin haber subido a base de datos para revisar y habiendo subido a base de datos para obtener los IDs de lotes."
COMMENT_LIQUIDACION = "Una vez registrada la operación en base de datos, genere el reporte de liquidación para el cliente."


col1, col2, col3 = st.columns([0.25, 0.5, 0.25], vertical_alignment="center")
with col1:
    st.image(os.path.join(project_root, "static", "logo_geek.png"), width=200)
with col2:
    st.markdown("<h2 style='text-align: center; font-size: 2.4em;'>Módulo de Originación</h2>", unsafe_allow_html=True)
with col3:
    empty_col, logo_col = st.columns([2, 1])
    with logo_col:
        st.image(os.path.join(project_root, "static", "logo_inandes.png"), width=195)

# --- UI: Carga de Archivos ---
with st.expander("", expanded=True):
    uploaded_pdf_files = st.file_uploader("Seleccionar archivos", type=["pdf"], key="pdf_uploader_main", accept_multiple_files=True)

    if uploaded_pdf_files:
        current_file_ids = [f.file_id for f in uploaded_pdf_files]
        if "last_uploaded_pdf_files_ids" not in st.session_state or \
           current_file_ids != st.session_state.last_uploaded_pdf_files_ids:
            st.session_state.invoices_data = []
            st.session_state.last_uploaded_pdf_files_ids = current_file_ids
            st.session_state.pdf_datos_cargados = False

        if not st.session_state.pdf_datos_cargados:
            for uploaded_file in uploaded_pdf_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    temp_file_path = tmp.name

                with st.spinner(f"Procesando {uploaded_file.name}..."):
                    try:
                        parsed_data = pdf_parser.extract_fields_from_pdf(temp_file_path)
                        if parsed_data.get("error"):
                            st.error(f"Error al procesar el PDF {uploaded_file.name}: {parsed_data['error']}")
                        else:
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
                                'fecha_pago_calculada': '',
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

# --- UI: Configuración Global ---
if st.session_state.invoices_data:
    st.markdown("---")
    st.subheader("Configuración Global")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("##### Comisiones Globales")
        st.write("---")
        st.write("**Com. de Estructuración**")
        st.checkbox(
            "Aplicar Comisión de Estructuración", 
            key='aplicar_comision_estructuracion_global',
            help="Si se marca, la comisión de estructuración se calculará sobre el capital total y se dividirá entre todas las facturas cargadas."
        )
        st.number_input(
            "Comisión de Estructuración (%)",
            min_value=0.0,
            key='comision_estructuracion_pct_global',
            format="%.2f",
            disabled=not st.session_state.get('aplicar_comision_estructuracion_global', False)
        )
        st.number_input(
            "Comisión Mínima (PEN)",
            min_value=0.0,
            key='comision_estructuracion_min_pen_global',
            format="%.2f",
            disabled=not st.session_state.get('aplicar_comision_estructuracion_global', False)
        )
        st.number_input(
            "Comisión Mínima (USD)",
            min_value=0.0,
            key='comision_estructuracion_min_usd_global',
            format="%.2f",
            disabled=not st.session_state.get('aplicar_comision_estructuracion_global', False)
        )
        
        st.write("**Com. de Afiliación**")
        st.checkbox(
            "Aplicar Comisión de Afiliación", 
            key='aplicar_comision_afiliacion_global',
            help="Si se marca, la comisión de afiliación se dividirá entre todas las facturas cargadas."
        )
        st.number_input(
            "Monto Comisión Afiliación (PEN)",
            min_value=0.0,
            key='comision_afiliacion_pen_global',
            format="%.2f",
            disabled=not st.session_state.get('aplicar_comision_afiliacion_global', False)
        )
        st.number_input(
            "Monto Comisión Afiliación (USD)",
            min_value=0.0,
            key='comision_afiliacion_usd_global',
            format="%.2f",
            disabled=not st.session_state.get('aplicar_comision_afiliacion_global', False)
        )

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
        st.checkbox("Aplicar Fecha de Pago Global",key='aplicar_fecha_vencimiento_global',on_change=handle_global_payment_date_change)
        st.date_input("Fecha de Pago Global",key='fecha_vencimiento_global',format="DD-MM-YYYY",disabled=not st.session_state.get('aplicar_fecha_vencimiento_global', False),on_change=handle_global_payment_date_change)
        st.checkbox("Aplicar Fecha de Desembolso Global",key='aplicar_fecha_desembolso_global',help="Si se marca, la fecha de desembolso seleccionada se aplicará a todas las facturas.",on_change=handle_global_disbursement_date_change)
        st.date_input("Fecha de Desembolso Global",key='fecha_desembolso_global',format="DD-MM-YYYY",disabled=not st.session_state.get('aplicar_fecha_desembolso_global', False),on_change=handle_global_disbursement_date_change)
        st.write("**Días Mínimos de Interés**")
        st.checkbox("Aplicar Días Mínimos", key='aplicar_dias_interes_minimo_global', on_change=handle_global_min_interest_days_change)
        st.number_input("Valor Días Mínimos", key='dias_interes_minimo_global', min_value=0, step=1, on_change=handle_global_min_interest_days_change)


    

# --- UI: Formulario Principal ---
if st.session_state.invoices_data:
    for idx, invoice in enumerate(st.session_state.invoices_data):
        st.markdown("---")
        st.write(f"### Factura {idx + 1}: {invoice.get('parsed_pdf_name', 'N/A')}")

        with st.container():
            st.write("##### Involucrados")
            col_emisor_nombre, col_emisor_ruc, col_aceptante_nombre, col_aceptante_ruc = st.columns(4)
            with col_emisor_nombre:
                invoice['emisor_nombre'] = st.text_input("NOMBRE DEL EMISOR", value=invoice.get('emisor_nombre', ''), key=f"emisor_nombre_{idx}", label_visibility="visible")
            with col_emisor_ruc:
                invoice['emisor_ruc'] = st.text_input("RUC DEL EMISOR", value=invoice.get('emisor_ruc', ''), key=f"emisor_ruc_{idx}", label_visibility="visible")
            with col_aceptante_nombre:
                invoice['aceptante_nombre'] = st.text_input("NOMBRE DEL ACEPTANTE", value=invoice.get('aceptante_nombre', ''), key=f"aceptante_nombre_{idx}", label_visibility="visible")
            with col_aceptante_ruc:
                invoice['aceptante_ruc'] = st.text_input("RUC DEL ACEPTANTE", value=invoice.get('aceptante_ruc', ''), key=f"aceptante_ruc_{idx}", label_visibility="visible")

        with st.container():
            st.write("##### Montos y Moneda")
            col_num_factura, col_monto_total, col_monto_neto, col_moneda, col_detraccion = st.columns(5)
            with col_num_factura:
                invoice['numero_factura'] = st.text_input("NÚMERO DE FACTURA", value=invoice.get('numero_factura', ''), key=f"numero_factura_{idx}", label_visibility="visible")
            with col_monto_total:
                invoice['monto_total_factura'] = st.number_input("MONTO FACTURA TOTAL (CON IGV)", min_value=0.0, value=invoice.get('monto_total_factura', 0.0), format="%.2f", key=f"monto_total_factura_{idx}", label_visibility="visible")
            with col_monto_neto:
                invoice['monto_neto_factura'] = st.number_input("MONTO FACTURA NETO", min_value=0.0, value=invoice.get('monto_neto_factura', 0.0), format="%.2f", key=f"monto_neto_factura_{idx}", label_visibility="visible")
            with col_moneda:
                invoice['moneda_factura'] = st.selectbox("MONEDA DE FACTURA", ["PEN", "USD"], index=["PEN", "USD"].index(invoice.get('moneda_factura', 'PEN')), key=f"moneda_factura_{idx}", label_visibility="visible")
            with col_detraccion:
                detraccion_retencion_pct = 0.0
                if invoice.get('monto_total_factura', 0) > 0:
                    detraccion_retencion_pct = ((invoice['monto_total_factura'] - invoice['monto_neto_factura']) / invoice['monto_total_factura']) * 100
                invoice['detraccion_porcentaje'] = detraccion_retencion_pct
                st.text_input("Detracción / Retención (%)", value=f"{detraccion_retencion_pct:.2f}%", disabled=True, key=f"detraccion_porcentaje_{idx}", label_visibility="visible")

        with st.container():
            st.write("##### Fechas y Plazos")

            def to_date_obj(date_str):
                if not date_str or not isinstance(date_str, str): return None
                try:
                    return datetime.datetime.strptime(date_str, '%d-%m-%Y').date()
                except (ValueError, TypeError):
                    return None

            col_fecha_emision, col_fecha_pago, col_fecha_desembolso, col_plazo_operacion, col_dias_minimos = st.columns(5)

            with col_fecha_emision:
                fecha_emision_obj = to_date_obj(invoice.get('fecha_emision_factura'))
                
                is_disabled = bool(fecha_emision_obj)

                nueva_fecha_emision_obj = st.date_input(
                    "Fecha de Emisión",
                    value=fecha_emision_obj if fecha_emision_obj else datetime.date.today(),
                    key=f"fecha_emision_factura_{idx}",
                    format="DD-MM-YYYY",
                    disabled=is_disabled
                )

                if not is_disabled:
                    if nueva_fecha_emision_obj:
                        invoice['fecha_emision_factura'] = nueva_fecha_emision_obj.strftime('%d-%m-%Y')
                    else:
                        invoice['fecha_emision_factura'] = ''

            def fecha_pago_changed(idx):
                new_date_obj = st.session_state.get(f"fecha_pago_calculada_{idx}")
                if new_date_obj:
                    st.session_state.invoices_data[idx]['fecha_pago_calculada'] = new_date_obj.strftime('%d-%m-%Y')
                else:
                    st.session_state.invoices_data[idx]['fecha_pago_calculada'] = ''
                update_date_calculations(st.session_state.invoices_data[idx], changed_field='fecha')

            def fecha_desembolso_changed(idx):
                new_date_obj = st.session_state.get(f"fecha_desembolso_factoring_{idx}")
                if new_date_obj:
                    st.session_state.invoices_data[idx]['fecha_desembolso_factoring'] = new_date_obj.strftime('%d-%m-%Y')
                else:
                    st.session_state.invoices_data[idx]['fecha_desembolso_factoring'] = ''
                update_date_calculations(st.session_state.invoices_data[idx])

            with col_fecha_pago:
                fecha_pago_obj = to_date_obj(invoice.get('fecha_pago_calculada'))
                st.date_input(
                    "Fecha de Pago",
                    value=fecha_pago_obj if fecha_pago_obj else datetime.date.today(),
                    key=f"fecha_pago_calculada_{idx}",
                    format="DD-MM-YYYY",
                    on_change=fecha_pago_changed,
                    args=(idx,)
                )

            with col_fecha_desembolso:
                fecha_desembolso_obj = to_date_obj(invoice.get('fecha_desembolso_factoring'))
                st.date_input(
                    "Fecha de Desembolso",
                    value=fecha_desembolso_obj if fecha_desembolso_obj else datetime.date.today(),
                    key=f"fecha_desembolso_factoring_{idx}",
                    format="DD-MM-YYYY",
                    on_change=fecha_desembolso_changed,
                    args=(idx,)
                )

            with col_plazo_operacion:
                # Leer directamente desde session_state para obtener el valor actualizado
                plazo_actual = st.session_state.invoices_data[idx].get('plazo_operacion_calculado', 0)
                st.number_input("Plazo de Operación (días)", value=plazo_actual, disabled=True, key=f"plazo_operacion_calculado_{idx}", label_visibility="visible")
            
            with col_dias_minimos:
                invoice['dias_minimos_interes_individual'] = st.number_input("Días Mín. Interés", value=invoice.get('dias_minimos_interes_individual', 15), min_value=0, step=1, key=f"dias_minimos_interes_individual_{idx}")

        with st.container():
            st.write("##### Tasas y Comisiones")
            is_disabled = idx > 0 and st.session_state.fijar_condiciones

            col_tasa_avance, col_interes_mensual, col_interes_moratorio = st.columns(3)
            with col_tasa_avance:
                invoice['tasa_de_avance'] = st.number_input("Tasa de Avance (%)", min_value=0.0, value=invoice.get('tasa_de_avance', st.session_state.default_tasa_de_avance), format="%.2f", key=f"tasa_de_avance_{idx}", on_change=propagate_commission_changes, disabled=is_disabled)
            with col_interes_mensual:
                invoice['interes_mensual'] = st.number_input("Interés Mensual (%)", min_value=0.0, value=invoice.get('interes_mensual', st.session_state.default_interes_mensual), format="%.2f", key=f"interes_mensual_{idx}", on_change=propagate_commission_changes, disabled=is_disabled)
            with col_interes_moratorio:
                invoice['interes_moratorio'] = st.number_input("Interés Moratorio (%)", min_value=0.0, value=invoice.get('interes_moratorio', st.session_state.default_interes_moratorio), format="%.2f", key=f"interes_moratorio_{idx}", on_change=propagate_commission_changes, disabled=is_disabled)

        st.markdown("---")

        col_resultados, = st.columns(1)
        with col_resultados:
            if invoice.get('recalculate_result'):
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

    # --- Pasos 3 y 4: Grabar e Imprimir ---
    st.markdown("---")
    st.subheader("Acciones de la Operación")

    st.write("##### Datos de Contrato (para Grabar)")
    col_anexo, col_contrato = st.columns(2)
    with col_anexo:
        st.text_input("Número de Anexo", key="anexo_number_global")
    with col_contrato:
        st.text_input("Número de Contrato", key="contract_number_global")

    st.markdown("---")

    # Define conditions for disabling buttons
    has_recalc_result = any(invoice.get('recalculate_result') for invoice in st.session_state.invoices_data)
    contract_fields_filled = bool(st.session_state.anexo_number_global) and bool(st.session_state.contract_number_global)
    can_save_proposal = has_recalc_result and contract_fields_filled
    can_print_profiles = has_recalc_result

    # Create horizontal buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Calcular Facturas", key="calculate_all_invoices", help=COMMENT_CALCULAR, type="primary", use_container_width=True):
            all_valid = True
            for idx_btn, invoice_btn in enumerate(st.session_state.invoices_data):
                if not validate_inputs(invoice_btn):
                    st.error(f"La Factura {idx_btn + 1} ({invoice_btn.get('parsed_pdf_name', 'N/A')}) tiene campos incompletos o inválidos.")
                    all_valid = False
            
            if not all_valid:
                st.warning("No se pueden calcular todas las facturas. Por favor, revisa los errores mencionados arriba.")
            else:
                st.success("Todas las facturas son válidas. Iniciando cálculos en lote...")
                
                lote_desembolso_payload = []
                num_invoices = len(st.session_state.invoices_data)
                
                for invoice_btn in st.session_state.invoices_data:
                    comision_pen_apportioned = st.session_state.get('comision_afiliacion_pen_global', 0.0) / num_invoices if num_invoices > 0 else 0
                    comision_usd_apportioned = st.session_state.get('comision_afiliacion_usd_global', 0.0) / num_invoices if num_invoices > 0 else 0
                    comision_estructuracion_pct = st.session_state.comision_estructuracion_pct_global
                    comision_min_pen_apportioned_struct = st.session_state.comision_estructuracion_min_pen_global / num_invoices if num_invoices > 0 else 0
                    comision_min_usd_apportioned_struct = st.session_state.comision_estructuracion_min_usd_global / num_invoices if num_invoices > 0 else 0

                    if invoice_btn['moneda_factura'] == 'USD':
                        comision_minima_aplicable = comision_min_usd_apportioned_struct
                        comision_afiliacion_aplicable = comision_usd_apportioned
                    else:
                        comision_minima_aplicable = comision_min_pen_apportioned_struct
                        comision_afiliacion_aplicable = comision_pen_apportioned

                    plazo_real = invoice_btn.get('plazo_operacion_calculado', 0)
                    plazo_para_api = plazo_real
                    if st.session_state.get('aplicar_dias_interes_minimo_global', False):
                        dias_minimos_a_usar = invoice_btn.get('dias_minimos_interes_individual', 15)
                        plazo_para_api = max(plazo_real, dias_minimos_a_usar)

                    api_data = {
                        "plazo_operacion": plazo_para_api,
                        "mfn": invoice_btn['monto_neto_factura'],
                        "tasa_avance": invoice_btn['tasa_de_avance'] / 100,
                        "interes_mensual": invoice_btn['interes_mensual'] / 100,
                        "interes_moratorio_mensual": invoice_btn['interes_moratorio'] / 100,
                        "comision_estructuracion_pct": comision_estructuracion_pct / 100,
                        "comision_minima_aplicable": comision_minima_aplicable,
                        "igv_pct": 0.18,
                        "comision_afiliacion_aplicable": comision_afiliacion_aplicable,
                        "aplicar_comision_afiliacion": st.session_state.get('aplicar_comision_afiliacion_global', False)
                    }
                    lote_desembolso_payload.append(api_data)

                try:
                    with st.spinner("Calculando desembolso inicial para todas las facturas..."):
                        response = requests.post(f"{API_BASE_URL}/calcular_desembolso_lote", json=lote_desembolso_payload)
                        response.raise_for_status()
                        initial_calc_results_lote = response.json()

                    if initial_calc_results_lote.get("error"):
                        st.error(f"Error en el cálculo de desembolso en lote: {initial_calc_results_lote.get('error')}")
                        st.stop()

                    lote_encontrar_tasa_payload = []
                    for idx_btn, invoice_btn in enumerate(st.session_state.invoices_data):
                        invoice_btn['initial_calc_result'] = initial_calc_results_lote["resultados_por_factura"][idx_btn]
                        
                        if invoice_btn['initial_calc_result'] and 'abono_real_teorico' in invoice_btn['initial_calc_result']:
                            abono_real_teorico = invoice_btn['initial_calc_result']['abono_real_teorico']
                            monto_desembolsar_objetivo = (abono_real_teorico // 10) * 10

                            api_data_recalculate = lote_desembolso_payload[idx_btn].copy()
                            api_data_recalculate["monto_objetivo"] = monto_desembolsar_objetivo
                            api_data_recalculate.pop("tasa_avance", None)
                            
                            lote_encontrar_tasa_payload.append(api_data_recalculate)
                        else:
                            invoice_btn['recalculate_result'] = None

                    if lote_encontrar_tasa_payload:
                        with st.spinner("Ajustando tasa de avance para todas las facturas..."):
                            response_recalculate = requests.post(f"{API_BASE_URL}/encontrar_tasa_lote", json=lote_encontrar_tasa_payload)
                            response_recalculate.raise_for_status()
                            recalculate_results_lote = response_recalculate.json()

                        if recalculate_results_lote.get("error"):
                            st.error(f"Error en el ajuste de tasa en lote: {recalculate_results_lote.get('error')}")
                            st.stop()
                        
                        for idx_btn, invoice_btn in enumerate(st.session_state.invoices_data):
                            if idx_btn < len(recalculate_results_lote.get("resultados_por_factura", [])):
                                invoice_btn['recalculate_result'] = recalculate_results_lote["resultados_por_factura"][idx_btn]

                    st.success("¡Cálculo de todas las facturas completado!")
                    st.rerun()

                except requests.exceptions.RequestException as e:
                    st.error(f"Error de conexión con la API: {e}")

    with col2:
        if st.button("GRABAR Propuesta", disabled=not can_save_proposal, help=COMMENT_GRABAR, use_container_width=True):
            if can_save_proposal:
                anexo_number_str = st.session_state.anexo_number_global
                contract_number_str = st.session_state.contract_number_global
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                identificador_lote = f"LOTE-{contract_number_str}-{anexo_number_str}-{timestamp}"

                for idx_btn, invoice_btn in enumerate(st.session_state.invoices_data):
                    if invoice_btn.get('recalculate_result'):
                        with st.spinner(f"Guardando propuesta para Factura {idx_btn + 1}..."):
                            anexo_number_int = int(anexo_number_str) if anexo_number_str else None
                            contract_number_int = int(contract_number_str) if contract_number_str else None
                            
                            temp_session_data = {
                                'emisor_nombre': invoice_btn.get('emisor_nombre'),
                                'emisor_ruc': invoice_btn.get('emisor_ruc'),
                                'aceptante_nombre': invoice_btn.get('aceptante_nombre'),
                                'aceptante_ruc': invoice_btn.get('aceptante_ruc'),
                                'numero_factura': invoice_btn.get('numero_factura'),
                                'monto_total_factura': invoice_btn.get('monto_total_factura'),
                                'monto_neto_factura': invoice_btn.get('monto_neto_factura'),
                                'moneda_factura': invoice_btn.get('moneda_factura'),
                                'fecha_emision_factura': invoice_btn.get('fecha_emision_factura'),
                                'plazo_credito_dias': invoice_btn.get('plazo_credito_dias'),
                                'fecha_desembolso_factoring': invoice_btn.get('fecha_desembolso_factoring'),
                                'tasa_de_avance': invoice_btn.get('tasa_de_avance'),
                                'interes_mensual': invoice_btn.get('interes_mensual'),
                                'interes_moratorio': invoice_btn.get('interes_moratorio'),
                                'comision_de_estructuracion': invoice_btn.get('comision_de_estructuracion'),
                                'comision_minima_pen': invoice_btn.get('comision_minima_pen'),
                                'comision_minima_usd': invoice_btn.get('comision_minima_usd'),
                                'comision_afiliacion_pen': invoice_btn.get('comision_afiliacion_pen'),
                                'comision_afiliacion_usd': invoice_btn.get('comision_afiliacion_usd'),
                                'aplicar_comision_afiliacion': invoice_btn.get('aplicar_comision_afiliacion'),
                                'detraccion_porcentaje': invoice_btn.get('detraccion_porcentaje'),
                                'fecha_pago_calculada': invoice_btn.get('fecha_pago_calculada'),
                                'plazo_operacion_calculado': invoice_btn.get('plazo_operacion_calculado'),
                                'initial_calc_result': invoice_btn.get('initial_calc_result'),
                                'recalculate_result': invoice_btn.get('recalculate_result'),
                                'anexo_number': anexo_number_int,
                                'contract_number': contract_number_int,
                            }
                            success, message = db.save_proposal(temp_session_data, identificador_lote=identificador_lote)
                            if success:
                                st.success(message)
                                if "Propuesta con ID" in message:
                                    start_index = message.find("ID ") + 3
                                    end_index = message.find(" guardada")
                                    newly_saved_id = message[start_index:end_index]
                                    invoice_btn['proposal_id'] = newly_saved_id
                                    invoice_btn['identificador_lote'] = identificador_lote
                                    st.session_state.last_saved_proposal_id = newly_saved_id

                                    if 'accumulated_proposals' not in st.session_state:
                                        st.session_state.accumulated_proposals = []
                                    
                                    full_proposal_details = db.get_proposal_details_by_id(newly_saved_id)
                                    if full_proposal_details and 'proposal_id' in full_proposal_details:
                                        if not any(p.get('proposal_id') == newly_saved_id for p in st.session_state.accumulated_proposals):
                                            st.session_state.accumulated_proposals.append(full_proposal_details)
                                            st.success(f"Propuesta {newly_saved_id} añadida a la lista de impresión.")
                            else:
                                st.error(message)
                else:
                    st.warning("No hay resultados de cálculo para guardar.")

    with col3:
        if st.button("Generar Perfil", disabled=not can_print_profiles, help=COMMENT_PERFIL, use_container_width=True):
            if can_print_profiles:
                st.write("Generando PDF...")
                
                invoices_to_print = []
                num_invoices_for_pdf = len([inv for inv in st.session_state.invoices_data if inv.get('recalculate_result')])
                for invoice_btn in st.session_state.invoices_data:
                    if invoice_btn.get('recalculate_result'):
                        invoice_btn['detraccion_monto'] = invoice_btn.get('monto_total_factura', 0) - invoice_btn.get('monto_neto_factura', 0)
                        invoice_btn['comision_de_estructuracion_global'] = st.session_state.comision_estructuracion_pct_global
                        invoice_btn['comision_minima_pen_global'] = st.session_state.comision_estructuracion_min_pen_global
                        invoice_btn['comision_minima_usd_global'] = st.session_state.comision_estructuracion_min_usd_global
                        invoice_btn['num_invoices'] = num_invoices_for_pdf
                        invoices_to_print.append(invoice_btn)

                if invoices_to_print:
                    try:
                        pdf_bytes = pdf_generators.generate_perfil_operacion_pdf(invoices_to_print)
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_filename = f"perfiles_consolidados_{timestamp}.pdf"
                        st.download_button(
                            label=f"Descargar {output_filename}",
                            data=pdf_bytes,
                            file_name=output_filename,
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"Error al generar el PDF de perfiles: {e}")
                else:
                    st.warning("No hay perfiles calculados para imprimir.")
            else:
                st.warning("No hay resultados de cálculo para generar perfiles.")

    with col4:
        if st.button("Generar Liquidación", disabled=not can_print_profiles, help=COMMENT_LIQUIDACION, use_container_width=True):
            if can_print_profiles:
                # Find all invoices that have a result to generate the report
                invoices_to_generate_anexo = [inv for inv in st.session_state.invoices_data if inv.get('recalculate_result')]

                if invoices_to_generate_anexo:
                    st.write("Generando Anexo de Liquidación...")
                    try:
                        # Generate the PDF using the new builder
                        pdf_bytes = generar_anexo_liquidacion_pdf(invoices_to_generate_anexo) # Changed function call
                        
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        # Use a more generic filename for the consolidated annex
                        output_filename = f"anexo_liquidacion_{timestamp}.pdf"
                        
                        st.download_button(
                            label=f"Descargar {output_filename}",
                            data=pdf_bytes,
                            file_name=output_filename,
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"Error al generar la liquidación: {e}")
                else:
                    st.warning("No se encontraron facturas con resultados calculados para generar el anexo de liquidación.")
            else:
                st.warning("No hay resultados de cálculo para generar el anexo de liquidación.")
    
    st.markdown("---")
    st.write("#### Descripción de las Acciones:")
    comment_string = (
        f"- **Calcular Facturas:** {COMMENT_CALCULAR}\n\n"
        f"- **GRABAR Propuesta:** {COMMENT_GRABAR}\n\n"
        f"- **Generar Perfil:** {COMMENT_PERFIL}\n\n"
        f"- **Generar Liquidación:** {COMMENT_LIQUIDACION}"
    )
    st.markdown(comment_string)