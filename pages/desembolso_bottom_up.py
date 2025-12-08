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

from src.data import supabase_repository as db
from src.utils.google_integration import render_folder_navigator_v2, upload_file_with_sa
from src.utils.pdf_generators import generar_voucher_transferencia_pdf

# --- Estrategia Unificada para la URL del Backend ---
API_BASE_URL = os.getenv("BACKEND_API_URL")

# --- Configuración Page ---
st.set_page_config(
    page_title="Módulo de Desembolsos (Nativo)",
    page_icon="💵",
    layout="wide"
)

# --- CSS HACK: FORZAR ANCHO COMPLETO REAL ---
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100% !important;
    }
    [data-testid="stHorizontalBlock"] {
        gap: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Configuración Service Account ---
try:
    # Convertir AttrDict a dict normal para upload_file_with_sa
    SA_CREDENTIALS = dict(st.secrets["google_drive"])
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

# --- HEADER ---
st.title("💵 Módulo de Desembolsos (Nativo)")
st.info("Navegación segura a través de Service Account. Los archivos se centralizan en el repositorio institucional.")

# --- LAYOUT PRINCIPAL (2 Columnas) ---
col_app, col_browser = st.columns([2, 1], gap="small")

# === COLUMNA IZQUIERDA: LÓGICA DE NEGOCIO (App) ===
with col_app:
    with st.container(border=True):
        st.subheader("1. Facturas Pendientes")
        
        # Filtrar seleccionadas
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
            st.caption(f"📝 Registros seleccionados: {len(facturas_seleccionadas)}")

        st.divider()

        if not facturas_seleccionadas:
            st.warning("👆 Selecciona al menos una factura para habilitar las opciones de desembolso.")
        else:
            # --- 2. GENERAR VOUCHER ---
            st.subheader("2. Generar Voucher")
            monto_total = sum(get_monto_a_desembolsar(f) for f in facturas_seleccionadas)
            moneda = facturas_seleccionadas[0].get('moneda_factura', 'PEN')
            
            c_v1, c_v2 = st.columns([2, 1])
            c_v1.info(f"**Total a Transferir:** {moneda} {monto_total:,.2f}")
            
            emisor_ruc = facturas_seleccionadas[0].get('emisor_ruc')
            if emisor_ruc:
                datos_emisor = db.get_signatory_data_by_ruc(str(emisor_ruc))
                if datos_emisor:
                    with c_v2:
                        if st.button("📄 Generar Voucher", use_container_width=True):
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
                                    st.success("✅ Generado")
                                else:
                                    st.error("❌ Error PDF")
                            except Exception as e:
                                st.error(f"Excepción: {e}")
                    
                    if st.session_state.current_voucher_bytes:
                         st.download_button(
                            label="⬇️ Descargar Voucher",
                            data=st.session_state.current_voucher_bytes,
                            file_name="voucher_transferencia.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.error("⚠️ Emisor sin datos bancarios registrados.")
            else:
                st.error("❌ Factura sin RUC de Emisor.")

            st.divider()

            # --- 3. FORMALIZACIÓN (Configuración y Sustentos) ---
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

            st.markdown("##### Detalle")
            total_monto_check = 0.0
            
            for factura in facturas_seleccionadas:
                pid = factura['proposal_id']
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
                            st.caption("ℹ️ Usando sustento global")

# === COLUMNA DERECHA: NAVEGADOR NATIVO (Browser) ===
with col_browser:
    # Usamos un contenedor con borde para simular la "Celda Simple" (1/3 de ancho)
    with st.container(border=True):
        # Render del Navegador (Importado de Utils)
        # Importante: Este componente gestiona su propio estado
        selected_folder = render_folder_navigator_v2(key="native_browser_final")
        
        # Espacio para info de la carpeta seleccionada
        if selected_folder:
             st.info(f"📂 **Destino:** `{selected_folder['name']}`")
        else:
             st.warning("👈 Navega y selecciona una carpeta destino.")

# --- FOOTER / ACCIONES FINALES ---
st.markdown("---")

# Botón de Ejecución Global
if facturas_seleccionadas and selected_folder:
    if st.button("🚀 REGISTRAR DESEMBOLSO Y SUBIR ARCHIVOS", type="primary", use_container_width=True):
        
        # Validaciones
        if st.session_state.sustento_unico and not st.session_state.consolidated_proof_file:
             st.error("❌ Falta el archivo de sustento consolidado.")
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
                # Simulamos o llamamos API real
                if API_BASE_URL:
                     response = requests.post(f"{API_BASE_URL}/desembolsar_lote", json=payload)
                     response.raise_for_status()
                     st.session_state.resultados_desembolso = response.json()
                     api_success = True
                else:
                     st.error("No API URL")
            except Exception as e:
                st.error(f"❌ Error API: {e}")
            
            # B) Upload Files (Si API OK)
            if api_success:
                folder_id = selected_folder['id'] # DEL NATIVE BROWSER
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
                            if "❌" in msg: st.error(msg)
                            else: st.write(msg)
                
                st.balloons()
                st.success("✨ ¡Desembolso Completado Exitosamente!")
                
                # Actualizar estados visualmente
                for res in st.session_state.resultados_desembolso.get('resultados_del_lote', []):
                        if res.get('status') == 'SUCCESS':
                            # Hack para actualizar sin recargar todo DB inmediatamente si no se quiere
                            pass
                
                if st.button("🔄 Recargar Página"):
                    st.session_state.reload_data = True
                    st.rerun()

elif facturas_seleccionadas and not selected_folder:
    st.warning("⚠️ Faltas seleccionar una carpeta de destino en el panel derecho (Navegador).")
