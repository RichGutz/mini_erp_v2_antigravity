
# desembolsos_app.py

import streamlit as st
import sys
import os
import datetime
import requests
import json

# --- Path Setup ---
# The main script (00_Home.py) handles adding 'src' to the path.
# This page only needs to know the project root for static assets.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# --- Module Imports from `src` ---
from src.data import supabase_repository as db

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

USUARIO_ID_TEST = "user_test@inandes.com" # Hardcoded for now

# --- Configuración de la Página ---
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Módulo de Desembolso INANDES",
    page_icon="💵"
)

# --- Inicialización del Session State ---
if 'vista_actual' not in st.session_state: st.session_state.vista_actual = 'busqueda'
if 'lote_encontrado' not in st.session_state: st.session_state.lote_encontrado = []
if 'facturas_seleccionadas' not in st.session_state: st.session_state.facturas_seleccionadas = {}
if 'facturas_a_desembolsar' not in st.session_state: st.session_state.facturas_a_desembolsar = []
if 'resultados_desembolso_lote' not in st.session_state: st.session_state.resultados_desembolso_lote = None
if 'global_desembolso_vars' not in st.session_state: 
    st.session_state.global_desembolso_vars = {
        'fecha_desembolso': datetime.date.today(), 
    }
if 'contract_number' not in st.session_state: st.session_state.contract_number = ''
if 'anexo_number' not in st.session_state: st.session_state.anexo_number = ''
if 'sustento_unico' not in st.session_state: st.session_state.sustento_unico = False
if 'consolidated_proof_file' not in st.session_state: st.session_state.consolidated_proof_file = None
if 'individual_proof_files' not in st.session_state: st.session_state.individual_proof_files = {}
if 'monto_total_desembolso' not in st.session_state: st.session_state.monto_total_desembolso = 0.0


# --- Funciones de Ayuda ---
def parse_invoice_number(proposal_id: str) -> str:
    try:
        parts = proposal_id.split('-')
        return f"{parts[1]}-{parts[2]}" if len(parts) > 2 else proposal_id
    except (IndexError, AttributeError):
        return proposal_id

# --- Funciones de Despliegue de Información ---
def _display_operation_profile_batch(data):
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

# --- Lógica de Vistas ---
def mostrar_busqueda():
    st.header("Paso 1: Buscar Lote para Desembolsar")
    with st.form(key="search_lote_form"):
        lote_id_input = st.text_input("Identificador de Lote", help="Pega aquí el identificador único del lote.")
        submit_button = st.form_submit_button(label="Buscar Lote")

    if submit_button:
        lote_id_sanitized = lote_id_input.strip()
        if not lote_id_sanitized:
            st.warning("Por favor, introduce el Identificador de Lote.")
            st.session_state.lote_encontrado = []
        else:
            with st.spinner("Buscando facturas activas en el lote..."):
                resultados = db.get_proposals_by_lote(lote_id_sanitized)
                st.session_state.lote_encontrado = resultados
                if resultados:
                    st.success(f"Se encontraron {len(resultados)} facturas activas.")
                    st.session_state.facturas_seleccionadas = {f['proposal_id']: True for f in resultados}
                else:
                    st.warning("No se encontraron facturas activas para el identificador de lote proporcionado.")

    if st.session_state.lote_encontrado:
        st.markdown("---")
        st.subheader("Paso 2: Seleccionar Facturas para Desembolso")
        with st.form(key="select_invoices_form"):
            for f in st.session_state.lote_encontrado:
                st.checkbox(f"**Factura:** {parse_invoice_number(f['proposal_id'])} | **Emisor:** {f.get('emisor_nombre', 'N/A')} | **Estado:** {f.get('estado', 'N/A')}", 
                            value=st.session_state.facturas_seleccionadas.get(f['proposal_id'], True), 
                            key=f['proposal_id'])
            
            if st.form_submit_button("Cargar Facturas para Desembolsar"):
                ids = [f['proposal_id'] for f in st.session_state.lote_encontrado if st.session_state.get(f['proposal_id'], False)]
                
                if not ids:
                    st.warning("No has seleccionado ninguna factura.")
                else:
                    with st.spinner(f"Cargando detalles para {len(ids)} facturas..."):
                        detalles = [db.get_proposal_details_by_id(pid) for pid in ids]
                        facturas_cargadas = [d for d in detalles if d and not d.get('error')]
                        
                        if facturas_cargadas:
                            st.session_state.facturas_a_desembolsar = facturas_cargadas
                            for d in st.session_state.facturas_a_desembolsar:
                                recalc_json = d.get('recalculate_result_json', '{}')
                                try:
                                    recalc_data = json.loads(recalc_json)
                                    monto_perfil = recalc_data.get('desglose_final_detallado', {}).get('abono', {}).get('monto', 0.0)
                                except (json.JSONDecodeError, AttributeError):
                                    monto_perfil = 0.0
                                d['monto_a_depositar_ui'] = monto_perfil
                            st.session_state.vista_actual = 'desembolso'
                            st.rerun()
                        else:
                            st.error("Error: No se pudieron cargar los detalles para las facturas seleccionadas.")

def mostrar_desembolso():
    st.header("Paso 3: Configurar y Ejecutar Desembolso")
    if st.button("<- Volver a la búsqueda"):
        st.session_state.vista_actual = 'busqueda'
        st.session_state.lote_encontrado = []
        st.session_state.facturas_a_desembolsar = []
        st.session_state.resultados_desembolso_lote = None
        st.rerun()

    # Calcular el total para el campo de suma
    total_monto_calculado = sum(f.get('monto_a_depositar_ui', 0) for f in st.session_state.facturas_a_desembolsar)

    # Mover el checkbox aquí para que controle la UI en tiempo real
    st.checkbox("APLICAR SUSTENTO DE PAGO UNICO", key="sustento_unico")

    with st.form(key="desembolso_form"):
        st.markdown("#### Configuración Global")
        g_vars = st.session_state.global_desembolso_vars
        g_vars['fecha_desembolso'] = st.date_input("Fecha de Desembolso para Todos", g_vars['fecha_desembolso'])
        
        # El file_uploader permanece dentro del form, pero ahora su estado
        # (disabled) será controlado correctamente por el checkbox de fuera.
        st.session_state.consolidated_proof_file = st.file_uploader(
            "Subir Evidencia Consolidada (PDF/Imagen)", 
            type=["pdf", "png", "jpg", "jpeg"], 
            key="consolidated_uploader",
            disabled=not st.session_state.sustento_unico
        )
        
        st.markdown("---")
        st.markdown("#### Facturas del Lote")
        for i, f in enumerate(st.session_state.facturas_a_desembolsar):
            with st.container(border=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"##### Factura: {parse_invoice_number(f['proposal_id'])} | Emisor: {f.get('emisor_nombre', 'N/A')}")
                    _display_operation_profile_batch(f)
                    f['monto_a_depositar_ui'] = st.number_input("Monto a Depositar", value=f['monto_a_depositar_ui'], format="%.2f", key=f"md_{i}")
                
                with col2:
                    st.session_state.individual_proof_files[f['proposal_id']] = st.file_uploader(
                        f"Sustento para Factura {parse_invoice_number(f['proposal_id'])}", 
                        type=["pdf", "png", "jpg", "jpeg"], 
                        key=f"uploader_{i}",
                        disabled=st.session_state.sustento_unico
                    )
        
        st.markdown("---")
        st.number_input("Monto a Depositar (Total Lote)", value=total_monto_calculado, key="monto_total_desembolso", format="%.2f")


        if st.form_submit_button("Registrar Desembolso de Facturas Vía API", type="primary"):
            with st.spinner("Procesando desembolso en lote a través de la API..."):
                desembolsos_info = []
                for factura in st.session_state.facturas_a_desembolsar:
                    info = {
                        "proposal_id": factura['proposal_id'],
                        "monto_desembolsado": factura['monto_a_depositar_ui'],
                        "fecha_desembolso_real": st.session_state.global_desembolso_vars['fecha_desembolso'].strftime('%d-%m-%Y'), 
                    }
                    desembolsos_info.append(info)
                
                payload = {
                    "usuario_id": USUARIO_ID_TEST,
                    "desembolsos": desembolsos_info
                }

                try:
                    response = requests.post(f"{API_BASE_URL}/desembolsar_lote", json=payload)
                    response.raise_for_status()
                    st.session_state.resultados_desembolso_lote = response.json()
                    st.success("¡Lote procesado por la API!")
                except requests.exceptions.RequestException as e:
                    st.error(f"Error de conexión con la API: {e}")
                    st.session_state.resultados_desembolso_lote = None

    if st.session_state.resultados_desembolso_lote:
        st.markdown("---")
        st.header("Paso 4: Resultados del Procesamiento")
        
        resultados = st.session_state.resultados_desembolso_lote.get('resultados_del_lote', [])
        
        success_count = 0
        error_count = 0

        if resultados:
            st.subheader("Detalle de la Respuesta de la API:")
            st.dataframe(resultados) # Display the raw API response in a dataframe

            # Removed the spinner here
            for res in resultados:
                status = res.get('status', 'ERROR')
                message = res.get('message', 'No hay mensaje.')
                pid = res.get('proposal_id', 'N/A')
                
                # Changed st.info to st.write for persistence
                st.write(f"API Response for Factura {parse_invoice_number(pid)}: Status={status}, Message={message}")

                if status == 'SUCCESS':
                    try:
                        db.update_proposal_status(pid, 'DESEMBOLSADA')
                        st.toast(f"✅ Factura {parse_invoice_number(pid)}: {message}. Estado actualizado a DESEMBOLSADA.")
                        success_count += 1
                    except Exception as e:
                        st.error(f"❌ Factura {parse_invoice_number(pid)}: {message}. Error al actualizar estado: {e}")
                        error_count += 1
                else:
                    st.error(f"❌ Factura {parse_invoice_number(pid)}: {message}")
                    error_count += 1
            
            if success_count > 0:
                st.success(f"✅ Se actualizaron {success_count} facturas a DESEMBOLSADA.")
            if error_count > 0:
                st.error(f"❌ Hubo errores al procesar {error_count} facturas. Por favor, revisa los detalles anteriores.")

        else:
            st.warning("La API no devolvió resultados para el lote.")

        if st.button("Finalizar y Volver"):
            st.session_state.vista_actual = 'busqueda'
            st.session_state.lote_encontrado = []
            st.session_state.facturas_a_desembolsar = []
            st.session_state.resultados_desembolso_lote = None
            st.rerun()

# --- UI: Título y CSS ---
st.markdown('''<style>
[data-testid="stHorizontalBlock"] { 
    align-items: center; 
}
</style>''', unsafe_allow_html=True)

col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
with col1:
    st.image(os.path.join(project_root, "static", "logo_geek.png"), width=200)
with col2:
    st.markdown("<h2 style='text-align: center; font-size: 2.4em;'>Módulo de Desembolso</h2>", unsafe_allow_html=True)
with col3:
    empty_col, logo_col = st.columns([2, 1])
    with logo_col:
        st.image(os.path.join(project_root, "static", "logo_inandes.png"), width=195)

# --- Lógica de Control de Vistas ---
if st.session_state.vista_actual == 'busqueda':
    mostrar_busqueda()
elif st.session_state.vista_actual == 'desembolso':
    mostrar_desembolso()
