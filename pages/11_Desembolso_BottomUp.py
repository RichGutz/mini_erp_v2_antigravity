import streamlit as st
import os
import sys
import datetime
import json
import requests

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data import supabase_repository as db
from src.utils.google_integration import render_simple_folder_selector, upload_file_to_drive
from src.utils.pdf_generators import generar_voucher_transferencia_pdf

# --- Estrategia Unificada para la URL del Backend ---
API_BASE_URL = os.getenv("BACKEND_API_URL")
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
    page_title="Desembolso Bottom-Up",
    page_icon="🏗️"
)

st.title("🏗️ Desembolso Bottom-Up (Reconstrucción)")

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
# SECCIÓN 1: TABLA DE FACTURAS (Lógica de Negocio)
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

# ==============================================================================
# SECCIÓN 2: GENERAR VOUCHER (Condicional)
# ==============================================================================
if facturas_seleccionadas:
    st.markdown("### 2. Generar Voucher de Transferencia")
    
    monto_total = sum(get_monto_a_desembolsar(f) for f in facturas_seleccionadas)
    moneda = facturas_seleccionadas[0].get('moneda_factura', 'PEN')
    
    st.markdown(f"**Monto Total a Transferir:** {moneda} {monto_total:,.2f}")
    
    emisor_ruc = facturas_seleccionadas[0].get('emisor_ruc')
    if emisor_ruc:
        datos_emisor = db.get_signatory_data_by_ruc(str(emisor_ruc))
        if datos_emisor:
            if st.button("📄 Generar Voucher PDF", type="secondary"):
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
                        st.success("✅ Voucher generado.")
                    else:
                        st.error("❌ Error generando PDF.")
                except Exception as e:
                    st.error(f"❌ Excepción: {e}")
            
            if st.session_state.current_voucher_bytes:
                 st.download_button(
                    label="⬇️ Descargar Voucher Generado",
                    data=st.session_state.current_voucher_bytes,
                    file_name="voucher_transferencia.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("⚠️ No hay datos bancarios para este emisor.")
    else:
        st.error("❌ Emisor sin RUC.")

st.divider()

# ==============================================================================
# SECCIÓN 3.5: SELECTOR DE CARPETAS (CRÍTICO - SIEMPRE VISIBLE)
# ==============================================================================
st.markdown("### 3.5 Selección de Carpeta Destino (Google Drive)")
st.info("Componente técnico obligatorio: Debe estar visible permanentemente.")

try:
    folder = render_simple_folder_selector(key="picker_bottom_up", label="Seleccionar Carpeta Destino")
    if folder:
        st.success(f"✅ Carpeta Seleccionada: {folder.get('name')} (ID: {folder.get('id')})")
    else:
        st.info("👆 Selecciona carpeta antes de procesar.")
except Exception as e:
    st.error(f"❌ Error al renderizar el selector: {e}")

st.divider()

# ==============================================================================
# SECCIÓN 4: CONFIGURACIÓN Y DESEMBOLSO FINAL (Condicional)
# ==============================================================================
if facturas_seleccionadas:
    st.markdown("### 4. Configuración y Desembolso")
    
    # 4.1 Config Global
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.session_state.global_desembolso_vars['fecha_desembolso'] = st.date_input(
            "Fecha de Desembolso (Real)", 
            st.session_state.global_desembolso_vars['fecha_desembolso']
        )
    with col_g2:
        st.checkbox("Aplicar Sustento de Pago Único", key="sustento_unico")
        
        # Upload Consolidado
        st.session_state.consolidated_proof_file = st.file_uploader(
            "Subir Evidencia Consolidada (PDF/Imagen)",
            type=["pdf", "png", "jpg", "jpeg"],
            key="consolidated_uploader",
            disabled=not st.session_state.sustento_unico
        )

    st.markdown("---")
    
    # 4.2 Configuración Individual (Monto & Sustento)
    st.markdown("#### Configuración por Factura")
    
    for i, factura in enumerate(facturas_seleccionadas):
        with st.container(border=True):
            col1, col2 = st.columns(2)
            
            pid = factura['proposal_id']
            with col1:
                st.markdown(f"**Factura:** {parse_invoice_number(pid)}")
                monto_inicial = get_monto_a_desembolsar(factura)
                
                # State for amount
                monto_key = f"monto_desembolso_{pid}"
                if monto_key not in st.session_state:
                    st.session_state[monto_key] = monto_inicial
                
                st.session_state[monto_key] = st.number_input(
                    f"Monto a Depositar ({pid})",
                    value=st.session_state[monto_key],
                    format="%.2f",
                    key=f"input_monto_{i}"
                )
            
            with col2:
                # Upload Individual
                st.session_state.individual_proof_files[pid] = st.file_uploader(
                    f"Sustento individual",
                    type=["pdf", "png", "jpg", "jpeg"],
                    key=f"uploader_ind_{i}",
                    disabled=st.session_state.sustento_unico
                )

    st.markdown("---")
    
    # 4.4 BOTÓN MAESTRO
    st.markdown("### ✅ Acción Final")
    
    if st.button("💵 Registrar Desembolso y Subir Archivos", type="primary", use_container_width=True):
        
        # Validación
        folder = st.session_state.get("picker_bottom_up") # Usamos la key del picker
        if not folder:
            st.error("❌ ERROR: Debes seleccionar una carpeta de Drive en la Sección 1.")
            st.stop()
            
        with st.spinner("Procesando Desembolsos (API + Drive + BD)..."):
            
            # A) Prepare API Payload
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
            
            # B) Call API
            api_success = False
            try:
                response = requests.post(f"{API_BASE_URL}/desembolsar_lote", json=payload)
                response.raise_for_status()
                st.session_state.resultados_desembolso = response.json()
                api_success = True
            except Exception as e:
                st.error(f"❌ Error API: {e}")
                
            # C) Upload Files if API OK
            if api_success:
                st.success("✅ Base de datos actualizada corrextamente.")
                
                folder_id = folder['id']
                access_token = st.session_state.token['access_token']
                upload_errors = []
                upload_count = 0
                
                # Upload Voucher
                if st.session_state.current_voucher_bytes:
                    first_lote = facturas_seleccionadas[0].get('identificador_lote', 'Lote')
                    v_name = f"{first_lote}_Voucher_Transferencia.pdf"
                    ok, res = upload_file_to_drive(st.session_state.current_voucher_bytes, v_name, folder_id, access_token)
                    if ok: upload_count += 1
                    else: upload_errors.append(f"Voucher: {res}")
                
                # Upload Evidence
                if st.session_state.sustento_unico:
                    f_obj = st.session_state.consolidated_proof_file
                    if f_obj:
                         first_lote = facturas_seleccionadas[0].get('identificador_lote', 'Lote')
                         ext = f_obj.name.split('.')[-1]
                         s_name = f"{first_lote}_Sustento_Global.{ext}"
                         ok, res = upload_file_to_drive(f_obj.getvalue(), s_name, folder_id, access_token)
                         if ok: upload_count += 1
                         else: upload_errors.append(f"Global: {res}")
                else:
                    for factura in facturas_seleccionadas:
                        pid = factura['proposal_id']
                        f_obj = st.session_state.individual_proof_files.get(pid)
                        if f_obj:
                            lote = factura.get('identificador_lote', 'Lote')
                            inv = parse_invoice_number(pid)
                            ext = f_obj.name.split('.')[-1]
                            i_name = f"{lote}_{inv}_Sustento.{ext}"
                            ok, res = upload_file_to_drive(f_obj.getvalue(), i_name, folder_id, access_token)
                            if ok: upload_count += 1
                            else: upload_errors.append(f"Sustento {inv}: {res}")
                            
                if not upload_errors:
                    st.balloons()
                    st.success(f"✨ ¡Todo listo! {upload_count} archivos subidos a Drive.")
                    
                    # Process Results Display
                    resultados = st.session_state.resultados_desembolso.get('resultados_del_lote', [])
                    for res in resultados:
                        pid = res.get('proposal_id')
                        status = res.get('status')
                        if status == 'SUCCESS':
                            db.update_proposal_status(pid, 'DESEMBOLSADA')
                            
                    if st.button("🔄 Finalizar y Recargar"):
                        st.session_state.reload_data = True
                        st.session_state.resultados_desembolso = None
                        st.session_state.current_voucher_bytes = None
                        st.rerun()
                else:
                    st.error(f"Hubo errores subiendo archivos: {upload_errors}")
