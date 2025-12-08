import streamlit as st
import os
import sys
import datetime
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data import supabase_repository as db

from src.utils.google_integration import render_simple_folder_selector, upload_file_to_drive, upload_file_with_sa
from src.utils.pdf_generators import generar_voucher_transferencia_pdf

# --- Estrategia Unificada para la URL del Backend ---
API_BASE_URL = os.getenv("BACKEND_API_URL")

# --- Configuración Service Account ---
# Usar credenciales del Service Account desde secrets.toml
try:
    SA_CREDENTIALS = st.secrets["google_drive"]  # CORREGIDO: era "service_account", debe ser "google_drive"
except Exception as e:
    st.error(f"❌ Error: No se encontraron credenciales del Service Account en secrets.toml: {e}")
    st.stop()

if not API_BASE_URL:
    try:
        API_BASE_URL = st.secrets["backend_api"]["url"]
    except (KeyError, AttributeError):
        st.error("❌ BACKEND_API_URL no configurada.")
        st.stop()
USUARIO_ID_TEST = "user_test@inandes.com"

# --- Page Config ---
st.set_page_config(
    layout="wide",
    page_title="Módulo de Desembolsos",
    page_icon="💵"
)

st.title("💵 Módulo de Desembolsos")

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
        return 0.0

        return 0.0

def upload_helper(file_bytes, file_name, folder_id, sa_creds):
    try:
        if not file_bytes:
            return False, f"Sin contenido: {file_name}"
        
        # USA SERVICE ACCOUNT (opcion 2)
        success, res_id = upload_file_with_sa(file_bytes, file_name, folder_id, sa_creds)
        
        if success:
             return True, f"✅ Subido (SA): {file_name}"
        else:
             return False, f"❌ Error {file_name}: {res_id}" 
    except Exception as e:
        return False, f"❌ Error {file_name}: {str(e)}"

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
# SECCIÓN 1: TABLA DE FACTURAS
# ==============================================================================
st.markdown("### 1. Facturas Pendientes")

# Contar seleccionadas (Definir antes de usar)
facturas_seleccionadas = [
    f for f in st.session_state.facturas_aprobadas
    if st.session_state.facturas_seleccionadas_desembolso.get(f['proposal_id'], False)
]

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
            # Update selection state
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

    # Re-evaluar seleccionadas tras renderizar checkboxes
    facturas_seleccionadas = [
        f for f in st.session_state.facturas_aprobadas
        if st.session_state.facturas_seleccionadas_desembolso.get(f['proposal_id'], False)
    ]
    
    st.write(f"📝 Facturas seleccionadas: {len(facturas_seleccionadas)}")

st.divider()

if not facturas_seleccionadas:
    st.info("👆 Selecciona al menos una factura para proceder.")
else:
    # ==============================================================================
    # SECCIÓN 2: GENERAR VOUCHER
    # ==============================================================================
    st.markdown("### 2. Generar Voucher de Transferencia")
    
    monto_total = sum(get_monto_a_desembolsar(f) for f in facturas_seleccionadas)
    moneda = facturas_seleccionadas[0].get('moneda_factura', 'PEN')
    
    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        st.info(f"**Monto Total a Transferir:** {moneda} {monto_total:,.2f}")
    
    emisor_ruc = facturas_seleccionadas[0].get('emisor_ruc')
    if emisor_ruc:
        datos_emisor = db.get_signatory_data_by_ruc(str(emisor_ruc))
        if datos_emisor:
            with col_v2:
                if st.button("📄 Calcular y Generar Voucher", type="secondary", use_container_width=True):
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
                            st.success("✅ Voucher Ok")
                        else:
                            st.error("❌ Error")
                    except Exception as e:
                        st.error(f"❌ Excepción: {e}")
            
            if st.session_state.current_voucher_bytes:
                 st.download_button(
                    label="⬇️ Descargar PDF Voucher",
                    data=st.session_state.current_voucher_bytes,
                    file_name="voucher_transferencia.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.warning("⚠️ No hay datos bancarios.")
    else:
        st.error("❌ Emisor sin RUC.")




    # ==============================================================================
    # SECCIÓN 4: FORMALIZACIÓN Y DESEMBOLSO
    # ==============================================================================
    st.markdown("---")
    st.subheader("⚙️ 3. Formalización")
    
    # CONTAINER PRINCIPAL - COPYING ORIGINACION STYLE
    with st.container(border=True):
        st.info("Paso Final: Configure los parámetros y seleccione la carpeta de destino.")
        
        # 3.1 CONFIGURACIÓN GLOBAL
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.session_state.global_desembolso_vars['fecha_desembolso'] = st.date_input(
                "Fecha de Desembolso (para todas)", 
                st.session_state.global_desembolso_vars['fecha_desembolso']
            )
        with col_g2:
            st.checkbox("APLICAR SUSTENTO DE PAGO ÚNICO", key="sustento_unico")
            if st.session_state.sustento_unico:
                st.session_state.consolidated_proof_file = st.file_uploader(
                    "Subir Evidencia Consolidada", type=["pdf", "png", "jpg"], key="consolidated_uploader"
                )

        st.markdown("---")
        st.markdown("##### Detalle por Factura")

        # 3.2 DETALLE POR FACTURA (Restaurado)
        total_monto = 0.0
        for i, factura in enumerate(facturas_seleccionadas):
            pid = factura['proposal_id']
            
            # Container per invoice to group visual elements
            with st.container(border=True):
                c1, c2 = st.columns([1, 1])
                
                with c1:
                    st.markdown(f"**Factura:** `{parse_invoice_number(pid)}`")
                    st.caption(f"Emisor: {factura.get('emisor_nombre', 'N/A')}")
                    
                    monto_key = f"monto_desembolso_{pid}"
                    if monto_key not in st.session_state:
                         st.session_state[monto_key] = get_monto_a_desembolsar(factura)
                    
                    # Widget updates session_state automatically via key
                    current_val = st.number_input(
                        "Monto a Depositar",
                        key=monto_key,
                        format="%.2f"
                    )
                    total_monto += current_val
                
                with c2:
                    if not st.session_state.sustento_unico:
                        st.session_state.individual_proof_files[pid] = st.file_uploader(
                            "Subir Sustento",
                            type=["pdf", "png", "jpg"],
                            key=f"uploader_{pid}"
                        )
                    else:
                        st.info("ℹ️ Sustento Global Activo")
        
        st.markdown(f"**Total a Desembolsar:** {total_monto:,.2f}")
        st.markdown("---")



        st.markdown("---")
        st.markdown("### 4. Selección de Carpeta Destino")
        st.info("Selecciona la carpeta en Google Drive donde se guardarán los sustentos y el voucher.")
        
        folder = None
        try:
            # Picker movido al paso 4
            folder = render_simple_folder_selector(key="picker_section_4_moved", label="Seleccionar Carpeta")
            if folder:
                    st.success(f"✅ Carpeta Seleccionada: **{folder.get('name')}**")
            else:
                    st.warning("👆 Por favor selecciona una carpeta.")
        except Exception as e:
            st.error(f"Error en Picker: {e}")

        st.markdown("---")
        st.markdown("### Acciones Finales")
        
        # 3.3 BOTÓN DE EJECUCIÓN
        if st.button("💵 Registrar Desembolso y Subir Archivos", type="primary", use_container_width=True):
            
            # Validación
            if not folder:
                st.error("❌ ERROR: Debes seleccionar una carpeta de Drive.")
                st.stop()
                
            with st.spinner("Procesando Desembolsos (API + Drive + BD)..."):
                
                 # A) Call API
                desembolsos_info = []
                for factura in facturas_seleccionadas:
                    pid = factura['proposal_id']
                    monto_key = f"monto_desembolso_{pid}"
                    monto = st.session_state.get(monto_key, get_monto_a_desembolsar(factura))
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
                    response = requests.post(f"{API_BASE_URL}/desembolsar_lote", json=payload)
                    response.raise_for_status()
                    st.session_state.resultados_desembolso = response.json()
                    api_success = True
                except Exception as e:
                    st.error(f"❌ Error API: {e}")
                
                 # B) Upload Files (PARALLEL OPTIMIZATION with SA)
                if api_success:
                    folder_id = folder['id']
                    # access_token ya no es necesario para la subida con SA
                    upload_tasks = []
                    
                    # 1. Prepare Voucher Task
                    if st.session_state.current_voucher_bytes:
                         first_lote = facturas_seleccionadas[0].get('identificador_lote', 'Lote')
                         v_name = f"{first_lote}_Voucher_Transferencia.pdf"
                         upload_tasks.append((st.session_state.current_voucher_bytes, v_name))
                    
                    # 2. Prepare Evidence Tasks
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
                    
                    # 3. Execute Parallel Uploads
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
                                # Update Progress
                                prog = (i + 1) / total_files
                                curr_bar.progress(prog, text=f"Subiendo {i+1}/{total_files}...")
                        
                        curr_bar.empty()
                        
                        # Show Summary
                        with st.expander("Resultados de Carga (vDebug 2.0)", expanded=errors_count > 0):
                            for msg in results_msg:
                                if "❌" in msg:
                                    st.error(msg)
                                else:
                                    st.write(msg)
                    else:
                        st.info("⚠️ No habían archivos para subir.")
                                
                    st.balloons()
                    st.success("✨ ¡Proceso Completado!")
                    
                    # Update DB Status Local (Visual)
                    for res in st.session_state.resultados_desembolso.get('resultados_del_lote', []):
                         if res.get('status') == 'SUCCESS':
                             db.update_proposal_status(res.get('proposal_id'), 'DESEMBOLSADA')
                             
                    if st.button("🔄 Recargar"):
                        st.session_state.reload_data = True
                        st.rarun()
