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
if 'global_desembolso_vars' not in st.session_state:
    st.session_state.global_desembolso_vars = {
        'fecha_desembolso': datetime.date.today(),
    }
if 'sustento_unico' not in st.session_state:
    st.session_state.sustento_unico = False
if 'consolidated_proof_file' not in st.session_state:
    st.session_state.consolidated_proof_file = None
if 'individual_proof_files' not in st.session_state:
    st.session_state.individual_proof_files = {}

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

def _display_operation_profile_batch(data):
    """Muestra el perfil de operación original"""
    st.subheader("Perfil de la Operación Original")
    recalc_result_json = data.get('recalculate_result_json')
    if not recalc_result_json:
        st.warning("No se encontraron datos de cálculo en la propuesta original.")
        return

    try:
        recalc_result = json.loads(recalc_result_json)
    except json.JSONDecodeError:
        st.error("Error al leer los datos del perfil de operación original.")
        return

    desglose = recalc_result.get('desglose_final_detallado', {})
    abono = desglose.get('abono', {})
    st.metric("Monto a Desembolsar (Perfil)", f"{data.get('moneda_factura', 'PEN')} {abono.get('monto', 0):,.2f}")

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
    
    # Tabla de facturas con checkboxes
    st.markdown("#### Paso 1: Seleccionar Facturas para Desembolso")
    
    # Header de la tabla
    col_check, col_factura, col_emisor, col_aceptante, col_monto, col_fecha_emision, col_fecha_desembolso = st.columns([0.5, 1.5, 2, 2, 1.5, 1.5, 1.5])
    
    with col_check:
        st.markdown("**Seleccionar**")
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
    
    # Filas de facturas con checkboxes
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
    
    # Obtener facturas seleccionadas
    facturas_seleccionadas = [
        f for f in st.session_state.facturas_aprobadas
        if st.session_state.facturas_seleccionadas_desembolso.get(f['proposal_id'], False)
    ]
    
    # Mostrar menús de configuración solo si hay facturas seleccionadas
    if facturas_seleccionadas:
        st.markdown("#### Paso 2: Configurar Desembolso")
        
        # Checkbox para sustento único
        st.checkbox("APLICAR SUSTENTO DE PAGO ÚNICO", key="sustento_unico")
        
        with st.form(key="desembolso_form"):
            st.markdown("##### Configuración Global")
            g_vars = st.session_state.global_desembolso_vars
            g_vars['fecha_desembolso'] = st.date_input("Fecha de Desembolso para Todos", g_vars['fecha_desembolso'])
            
            # Upload de evidencia consolidada
            st.session_state.consolidated_proof_file = st.file_uploader(
                "Subir Evidencia Consolidada (PDF/Imagen)",
                type=["pdf", "png", "jpg", "jpeg"],
                key="consolidated_uploader",
                disabled=not st.session_state.sustento_unico
            )
            
            st.markdown("---")
            st.markdown("##### Facturas Seleccionadas")
            
            # Calcular total
            total_monto = 0.0
            
            # Menús individuales para cada factura seleccionada
            for i, factura in enumerate(facturas_seleccionadas):
                with st.container(border=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Factura:** {parse_invoice_number(factura['proposal_id'])} | **Emisor:** {factura.get('emisor_nombre', 'N/A')}")
                        _display_operation_profile_batch(factura)
                        
                        # Monto editable
                        monto_inicial = get_monto_a_desembolsar(factura)
                        monto_key = f"monto_desembolso_{factura['proposal_id']}"
                        if monto_key not in st.session_state:
                            st.session_state[monto_key] = monto_inicial
                        
                        st.session_state[monto_key] = st.number_input(
                            "Monto a Depositar",
                            value=st.session_state[monto_key],
                            format="%.2f",
                            key=f"md_{i}"
                        )
                        total_monto += st.session_state[monto_key]
                    
                    with col2:
                        # Upload de sustento individual
                        st.session_state.individual_proof_files[factura['proposal_id']] = st.file_uploader(
                            f"Sustento para Factura {parse_invoice_number(factura['proposal_id'])}",
                            type=["pdf", "png", "jpg", "jpeg"],
                            key=f"uploader_{i}",
                            disabled=st.session_state.sustento_unico
                        )
            
            st.markdown("---")
            st.number_input("Monto Total a Desembolsar", value=total_monto, format="%.2f", disabled=True)
            
            # Botón de desembolsar
            if st.form_submit_button("💵 Registrar Desembolso de Facturas Vía API", type="primary"):
                with st.spinner("Procesando desembolso a través de la API..."):
                    desembolsos_info = []
                    
                    for factura in facturas_seleccionadas:
                        monto_key = f"monto_desembolso_{factura['proposal_id']}"
                        monto = st.session_state.get(monto_key, get_monto_a_desembolsar(factura))
                        
                        fecha_desembolso = st.session_state.global_desembolso_vars['fecha_desembolso']
                        fecha_formateada = fecha_desembolso.strftime('%d-%m-%Y')
                        
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
                        response = requests.post(f"{API_BASE_URL}/desembolsar_lote", json=payload)
                        response.raise_for_status()
                        st.session_state.resultados_desembolso = response.json()
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Error de conexión con la API: {e}")
                        st.session_state.resultados_desembolso = None
        
        # Procesar resultados
        if st.session_state.resultados_desembolso:
            st.markdown("---")
            st.subheader("Resultados del Procesamiento")
            
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
            if st.button("Continuar"):
                st.session_state.reload_data = True
                st.session_state.resultados_desembolso = None
                st.rerun()
    else:
        st.info("👆 Selecciona al menos una factura para configurar el desembolso.")

# --- Información Adicional ---
st.markdown("---")
with st.expander("ℹ️ Información del Módulo"):
    st.markdown("""
    ### Módulo de Desembolso de Operaciones
    
    Este módulo permite procesar los desembolsos de operaciones aprobadas.
    
    **Flujo de trabajo:**
    1. El módulo muestra automáticamente todas las facturas `APROBADAS`
    2. Selecciona las facturas que deseas desembolsar usando los checkboxes
    3. Configura el monto y sustentos para cada factura seleccionada
    4. El sistema procesa el desembolso a través de la API
    5. Al completarse exitosamente, el estado cambia a `DESEMBOLSADA`
    
    **Opciones de configuración:**
    - **Monto a depositar**: Editable para cada factura
    - **Sustento único**: Subir un solo documento para todas las facturas
    - **Sustentos individuales**: Subir documentos separados por factura
    """)
