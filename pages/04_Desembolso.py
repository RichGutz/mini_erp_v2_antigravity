import streamlit as st
import os
import sys
import datetime
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Path Setup ---
# Add root directory to path to allow imports from src
sys.path.append(os.path.abspath("."))
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

from src.data import supabase_repository as db
from src.utils.google_integration import render_folder_navigator_v2, upload_file_with_sa
from src.ui.email_component import render_email_sender
from src.utils.pdf_generators import generar_voucher_transferencia_pdf

# --- Estrategia Unificada para la URL del Backend ---
API_BASE_URL = os.getenv("BACKEND_API_URL")

# --- Configuración Page ---
st.set_page_config(
    page_title="Módulo de Desembolsos",
    page_icon="💼",
    layout="wide"
)

# --- CSS HACK: FORZAR ANCHO COMPLETO REAL Y HEADER ALINEADO ---
# --- CSS HACK REMOVED (Conflicted with Header) ---

# --- Configuración Service Account ---
try:
    # Convertir AttrDict a dict normal
    SA_CREDENTIALS = dict(st.secrets["google_drive"])
except Exception as e:
    st.error(f"Error: No se encontraron credenciales del Service Account en secrets.toml: {e}")
    st.stop()

if not API_BASE_URL:
    try:
        API_BASE_URL = st.secrets["backend_api"]["url"]
    except (KeyError, AttributeError):
        st.error("BACKEND_API_URL no configurada.")
        st.stop()

USUARIO_ID_TEST = "user_test@inandes.com"

# --- Header (Moved for Alignment) ---
from src.ui.header import render_header
render_header("Módulo de Desembolso")

# --- CSS Alignment Fix (Removed) ---
# st.markdown('''<style>
# [data-testid="stHorizontalBlock"] { 
#     align-items: center; 
# }
# </style>''', unsafe_allow_html=True)

# --- Inicialización del Session State ---
if 'facturas_aprobadas' not in st.session_state:
    st.session_state.facturas_aprobadas = []
if 'facturas_seleccionadas_desembolso' not in st.session_state:
    st.session_state.facturas_seleccionadas_desembolso = {}
if 'reload_data' not in st.session_state:
    st.session_state.reload_data = True

# Voucher State
if 'voucher_generado' not in st.session_state:
    st.session_state.voucher_generado = False
if 'current_voucher_bytes' not in st.session_state:
    st.session_state.current_voucher_bytes = None

# New States for Logic
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
if 'resultados_desembolso' not in st.session_state:
    st.session_state.resultados_desembolso = None

# --- Funciones de Ayuda ---
def parse_invoice_number(proposal_id: str) -> str:
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

def upload_helper(file_bytes, file_name, folder_id, sa_creds):
    try:
        if not file_bytes:
            return False, f"Sin contenido: {file_name}"
        # USA SERVICE ACCOUNT
        success, res_id = upload_file_with_sa(file_bytes, file_name, folder_id, sa_creds)
        if success:
             return True, f"Subido (SA): {file_name}"
        else:
             return False, f"Error {file_name}: {res_id}" 
    except Exception as e:
        return False, f"Error {file_name}: {str(e)}"

# --- Cargar Facturas ---
if st.session_state.reload_data:
    with st.spinner("Cargando facturas aprobadas pendientes de desembolso..."):
        st.session_state.facturas_aprobadas = db.get_approved_proposals_for_disbursement()
        st.session_state.facturas_seleccionadas_desembolso = {
            f['proposal_id']: False for f in st.session_state.facturas_aprobadas
        }
        st.session_state.reload_data = False

# --- UI: Header con Logos (Estandarizado) ---
# (Moved to top)


# ==============================================================================
# SECCIÓN 1: FACTURAS PENDIENTES (Full Width)
# ==============================================================================
with st.container(border=True):
    st.subheader("1. Facturas Pendientes")
    
    # Filtrar seleccionadas
    facturas_seleccionadas = [
        f for f in st.session_state.facturas_aprobadas
        if st.session_state.facturas_seleccionadas_desembolso.get(f['proposal_id'], False)
    ]

    if not st.session_state.facturas_aprobadas:
        st.info("No hay facturas aprobadas pendientes de desembolso.")
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

        # Re-evaluar seleccionadas
        facturas_seleccionadas = [
            f for f in st.session_state.facturas_aprobadas
            if st.session_state.facturas_seleccionadas_desembolso.get(f['proposal_id'], False)
        ]
        st.caption(f"Registros seleccionados: {len(facturas_seleccionadas)}")

if not facturas_seleccionadas:
    pass
else:
    # ==============================================================================
    # SECCIÓN 2: GENERAR VOUCHER (Full Width)
    # ==============================================================================
    # ==============================================================================
    # SECCIÓN 2: GENERAR VOUCHER (Full Width)
    # ==============================================================================
    with st.container(border=True):
        st.subheader("2. Generar Voucher")
        monto_total = sum(get_monto_a_desembolsar(f) for f in facturas_seleccionadas)
        moneda = facturas_seleccionadas[0].get('moneda_factura', 'PEN')
        
        # Validar Datos Emisor
        emisor_ruc = facturas_seleccionadas[0].get('emisor_ruc')
        datos_emisor = {}
        if emisor_ruc:
            datos_emisor = db.get_signatory_data_by_ruc(str(emisor_ruc))
        
        if not datos_emisor:
            st.error("⚠️ El emisor no tiene datos bancarios registrados. No se puede generar voucher ni mostrar cuentas.")
        else:
            # 3 Column Layout
            col_total, col_voucher, col_transfer = st.columns([1, 1, 1], gap="small")
            
            # --- COL 1: TOTAL A TRANSFERIR ---
            with col_total:
                # Added min-height to simulate full-height column alignment
                # Adjusted to 190px based on user feedback (220px was too tall)
                st.markdown(
                    f"""
                    <div style="background-color: #f0f2f6; padding: 25px 20px; border-radius: 4px; text-align: center; border: 1px solid #ddd; min-height: 190px; display: flex; flex-direction: column; justify-content: center;">
                        <div style="color: #666; font-size: 0.85em; font-weight: 600; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">Total a Transferir</div>
                        <div style="color: #333; font-size: 2.2em; font-weight: 700;">{moneda} {monto_total:,.2f}</div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

            # --- COL 2: VOUCHER ACTIONS ---
            with col_voucher:
                if st.button("Generar Voucher PDF", type="primary", use_container_width=True):
                    try:
                        facturas_para_pdf = [{
                            'numero_factura': parse_invoice_number(f['proposal_id']),
                            'emisor_nombre': f.get('emisor_nombre', 'N/A'),
                            'monto': get_monto_a_desembolsar(f)
                        } for f in facturas_seleccionadas]
                        
                        pdf_bytes = generar_voucher_transferencia_pdf(
                            datos_emisor=datos_emisor,
                            monto_total=monto_total,
                            moneda=moneda,
                            facturas=facturas_para_pdf,
                            fecha_generacion=datetime.date.today()
                        )
                        
                        if pdf_bytes:
                            st.session_state.voucher_generado = True
                            st.session_state.current_voucher_bytes = pdf_bytes
                            st.success("Voucher Generado")
                        else:
                            st.error("Error al generar PDF")
                    except Exception as e:
                        st.error(f"Excepción: {e}")

                # Spacer logic to keep alignment if button is missing? 
                # Or just render the button if exists. User wants alignment with this.
                if st.session_state.current_voucher_bytes:
                     st.download_button(
                        label="Descargar Voucher",
                        data=st.session_state.current_voucher_bytes,
                        file_name="voucher_transferencia.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    # Render invisible spacer to maintain grid structure? 
                    # User asked for alignment of the NEXT column's box to the Download button.
                    # If Download button is missing, the box in Col 3 will still be pushed down by CSS below.
                    st.write("") 

            # --- COL 3: TRANSFER ACTIONS & BANK DATA ---
            with col_transfer:
                if st.button("Iniciar Transferencia BCP", type="primary", use_container_width=True):
                    st.toast("Conexión con BCP Empresas iniciada.")
                
                # Dynamic keys based on currency
                cta_key = f"Numero de Cuenta {moneda}"
                cci_key = f"Numero de CCI {moneda}"

                # Removed margin-top to align with natural flow (aligns with Descargar button in next col)
                st.markdown(f"""
                <div style="margin-top: 0px; font-size: 0.85em; color: #444; background-color: white; padding: 15px; border: 1px solid #ddd; border-radius: 4px;">
                    <div style="margin-bottom: 4px;"><strong>Beneficiario:</strong> {datos_emisor.get('Razon Social', 'N/A')}</div>
                    <div style="margin-bottom: 4px;"><strong>Banco:</strong> {datos_emisor.get('Institucion Financiera', 'N/A')}</div>
                    <div style="margin-bottom: 4px;"><strong>Cuenta:</strong> {datos_emisor.get(cta_key, 'N/A')}</div>
                     <div><strong>CCI:</strong> {datos_emisor.get(cci_key, 'N/A')}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Add bottom spacer row
            st.write("")
            st.write("")

    # ==============================================================================
    # SECCIÓN 3: FORMALIZACIÓN (Full Width)
    # ==============================================================================
    with st.container(border=True):
        st.subheader("3. Formalización")
        
        # Configuración Global
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.session_state.global_desembolso_vars['fecha_desembolso'] = st.date_input(
                "Fecha de Desembolso", 
                st.session_state.global_desembolso_vars['fecha_desembolso']
            )
        with col_g2:
            st.checkbox("SUSTENTO DE PAGO ÚNICO", key="sustento_unico")
            if st.session_state.sustento_unico:
                st.session_state.consolidated_proof_file = st.file_uploader(
                    "Subir Evidencia Consolidada", type=["pdf", "png", "jpg"], key="consolidated_uploader"
                )

        st.markdown("##### Detalle de Sustentos")
        total_monto_check = 0.0
        
        for factura in facturas_seleccionadas:
            pid = factura['proposal_id']
            # Mini container por factura
            with st.container(border=True):
                dc1, dc2 = st.columns([1, 1])
                with dc1:
                    st.markdown(f"**Factura:** `{parse_invoice_number(pid)}`")
                    monto_key = f"monto_desembolso_{pid}"
                    if monto_key not in st.session_state:
                         st.session_state[monto_key] = get_monto_a_desembolsar(factura)
                    
                    val = st.number_input("Monto:", key=monto_key, format="%.2f")
                    total_monto_check += val
                
                with dc2:
                    if not st.session_state.sustento_unico:
                        st.session_state.individual_proof_files[pid] = st.file_uploader(
                            "Sustento Individual", type=["pdf", "png", "jpg"], key=f"uploader_{pid}"
                        )
                    else:
                        st.caption("Usando sustento global")

    # ==============================================================================
    # SECCIÓN 4: SELECCIÓN DE CARPETA (Full Width - Abajo)
    # ==============================================================================
    with st.container(border=True):
        st.subheader("4. Selección de Carpeta Destino")
        
        # Render del Navegador
        selected_folder = render_folder_navigator_v2(key="native_browser_final")
        
        if selected_folder:
             st.info(f"📂 **Destino Seleccionado:** `{selected_folder['name']}`")
             
             # MOVIDO: Botón dentro del contenedor y condicional a la carpeta
             st.markdown("---")
             if st.button("REGISTRAR DESEMBOLSO Y SUBIR ARCHIVOS", type="primary", use_container_width=True):
                
                # Validaciones de sustento
                if st.session_state.sustento_unico and not st.session_state.consolidated_proof_file:
                     st.error("Falta el archivo de sustento consolidado.")
                     st.stop()
                
                with st.spinner("Procesando Desembolsos (API + Drive + BD)..."):
                    # A) API Call
                    desembolsos_info = []
                    for factura in facturas_seleccionadas:
                        pid = factura['proposal_id']
                        monto = st.session_state.get(f"monto_desembolso_{pid}", 0.0)
                        fecha_fmt = st.session_state.global_desembolso_vars['fecha_desembolso'].strftime('%d-%m-%Y')
                        desembolsos_info.append({
                            "proposal_id": pid,
                            "monto_desembolsado": monto,
                            "fecha_desembolso_real": fecha_fmt,
                        })
                    
                    payload = {
                        "usuario_id": USUARIO_ID_TEST,
                        "desembolsos": desembolsos_info
                    }
                    
                    api_success = False
                    try:
                        if API_BASE_URL:
                             response = requests.post(f"{API_BASE_URL}/desembolsar_lote", json=payload)
                             response.raise_for_status()
                             st.session_state.resultados_desembolso = response.json()
                             api_success = True
                        else:
                             st.error("No API URL")
                    except Exception as e:
                        st.error(f"Error API: {e}")
                    
                    # B) Upload Files (Si API OK)
                    if api_success:
                        folder_id = selected_folder['id']
                        upload_tasks = []
                        
                        # 1. Voucher
                        if st.session_state.current_voucher_bytes:
                                first_lote = facturas_seleccionadas[0].get('identificador_lote', 'Lote')
                                v_name = f"{first_lote}_Voucher_Transferencia.pdf"
                                upload_tasks.append((st.session_state.current_voucher_bytes, v_name))
                        
                        # 2. Sustentos
                        if st.session_state.sustento_unico:
                            f_obj = st.session_state.consolidated_proof_file
                            if f_obj:
                                    first_lote = facturas_seleccionadas[0].get('identificador_lote', 'Lote')
                                    s_name = f"{first_lote}_Sustento_Global.pdf"
                                    upload_tasks.append((f_obj.getvalue(), s_name))
                        else:
                            for factura in facturas_seleccionadas:
                                pid = factura['proposal_id']
                                f_obj = st.session_state.individual_proof_files.get(pid)
                                if f_obj:
                                    lote = factura.get('identificador_lote', 'Lote')
                                    inv = parse_invoice_number(pid)
                                    i_name = f"{lote}_{inv}_Sustento.pdf"
                                    upload_tasks.append((f_obj.getvalue(), i_name))
                        
                        # 3. Execute
                        results_msg = []
                        errors_count = 0
                        
                        if upload_tasks:
                            curr_bar = st.progress(0, text="Iniciando carga de archivos...")
                            total_files = len(upload_tasks)
                            
                            with ThreadPoolExecutor(max_workers=5) as executor:
                                future_to_file = {
                                    executor.submit(upload_helper, b, n, folder_id, SA_CREDENTIALS): n 
                                    for b, n in upload_tasks
                                }
                                
                                for i, future in enumerate(as_completed(future_to_file)):
                                    success, msg = future.result()
                                    results_msg.append(msg)
                                    if not success:
                                        errors_count += 1
                                    prog = (i + 1) / total_files
                                    curr_bar.progress(prog, text=f"Subiendo {i+1}/{total_files}...")
                            
                            curr_bar.empty()
                            
                            with st.expander("Resultados de Carga", expanded=errors_count > 0):
                                for msg in results_msg:
                                    if "Error" in msg: st.error(msg)
                                    else: st.write(msg)
                        
                        st.balloons()
                        st.success("¡Desembolso Completado Exitosamente!")

                        # --- EMAIL SENDER INTEGRATION (State Persistence) ---
                        st.session_state.show_email_desembolso = True
                        st.session_state.email_docs_desembolso = []
                        
                        # 1. Voucher
                        if st.session_state.current_voucher_bytes:
                                first_lote = facturas_seleccionadas[0].get('identificador_lote', 'Lote')
                                v_name = f"{first_lote}_Voucher_Transferencia.pdf"
                                st.session_state.email_docs_desembolso.append({'name': v_name, 'bytes': st.session_state.current_voucher_bytes})
                        
                        # 2. Sustentos
                        if st.session_state.sustento_unico:
                            f_obj = st.session_state.consolidated_proof_file
                            if f_obj:
                                    first_lote = facturas_seleccionadas[0].get('identificador_lote', 'Lote')
                                    s_name = f"{first_lote}_Sustento_Global.pdf"
                                    st.session_state.email_docs_desembolso.append({'name': s_name, 'bytes': f_obj.getvalue()})
                        else:
                            for factura in facturas_seleccionadas:
                                pid = factura['proposal_id']
                                f_obj = st.session_state.individual_proof_files.get(pid)
                                if f_obj:
                                    lote = factura.get('identificador_lote', 'Lote')
                                    inv = parse_invoice_number(pid)
                                    i_name = f"{lote}_{inv}_Sustento.pdf"
                                    st.session_state.email_docs_desembolso.append({'name': i_name, 'bytes': f_obj.getvalue()})
                        # ----------------------------------------------------
                        
                        # Actualizar estados visualmente
                        for res in st.session_state.resultados_desembolso.get('resultados_del_lote', []):
                                if res.get('status') == 'SUCCESS':
                                    pass
                        
                        if st.button("Recargar Página"):
                            st.session_state.reload_data = True
                            st.session_state.show_email_desembolso = False # Reset on reload
                            st.rerun()

        else:
             st.warning("Navega y selecciona una carpeta destino para habilitar el botón final.")


    if st.session_state.get('show_email_desembolso', False):
         with st.container(border=True):
             st.subheader("5. Envío de Reportes por Correo")
             
             # Try to get meaningful default subject
             lote_id = "Lote"
             if facturas_seleccionadas:
                 lote_id = facturas_seleccionadas[0].get('identificador_lote', 'Lote')
             
             render_email_sender(
                 key_suffix="desembolso", 
                 documents=st.session_state.get('email_docs_desembolso', []),
                 default_subject=f"Sustentos de Desembolso - {lote_id}",
                 default_email=""
             )
    
    elif facturas_seleccionadas and not selected_folder:
        pass # Warning already shown above


# --- Sidebar Boton Rojo ---
with st.sidebar:
    st.markdown('---')
    if st.button('🔄 Actualizar', key='sidebar_refresh_btn', type='primary', use_container_width=True, help='Recargar lista desde Base de Datos'):
        st.session_state.reload_data = True
        st.rerun()
