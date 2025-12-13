import streamlit as st
import sys
import os
import datetime
import json
import random
from collections import defaultdict

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# --- Module Imports from `src` ---
from src.data import supabase_repository as db
from src.ui.email_component import render_email_sender

# --- Configuración de la Página ---
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="✅"
)

# --- Header ---
from src.ui.header import render_header
render_header("Módulo de Aprobación")

# --- CSS Alignment Fix ---
st.markdown('''<style>
[data-testid="stHorizontalBlock"] { 
    align-items: center; 
}
</style>''', unsafe_allow_html=True)

# --- Auto-Reload Logic on Entry ---
if st.session_state.get('last_page') != '03_Aprobacion':
    st.session_state.reload_data = True
    st.session_state.last_page = '03_Aprobacion'

# --- Inicialización del Session State ---
if 'facturas_activas' not in st.session_state:
    st.session_state.facturas_activas = []
if 'facturas_seleccionadas_aprobacion' not in st.session_state:
    st.session_state.facturas_seleccionadas_aprobacion = {}
if 'reload_data' not in st.session_state:
    st.session_state.reload_data = True
if 'last_approved_invoices' not in st.session_state:
    st.session_state.last_approved_invoices = [] # List of dicts {num, amount}
if 'last_approved_total' not in st.session_state:
    st.session_state.last_approved_total = 0.0
if 'last_approved_emisor' not in st.session_state:
    st.session_state.last_approved_emisor = ""
if 'email_body_version' not in st.session_state:
    st.session_state.email_body_version = 0

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
    """Calcula el monto a desembolsar desde el JSON de recálculo"""
    try:
        recalc_json = factura.get('recalculate_result_json', '{}')
        if isinstance(recalc_json, dict):
             recalc_data = recalc_json
        else:
             recalc_data = json.loads(recalc_json)
        
        return recalc_data.get('desglose_final_detallado', {}).get('abono', {}).get('monto', 0.0)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return 0.0

def toggle_batch_selection(batch_key, invoice_ids):
    """Callback para seleccionar/deseleccionar todo el lote"""
    # El valor del checkbox maestro ya se actualizó en session_state antes de llamar al callback
    master_val = st.session_state[batch_key]
    for pid in invoice_ids:
        # Actualizar el diccionario de valores lógicos
        st.session_state.facturas_seleccionadas_aprobacion[pid] = master_val
        # Actualizar el estado visual del widget (si existe o se va crear)
        st.session_state[f"chk_app_{pid}"] = master_val

def render_status_brick(text, is_green):
    color = "#2e7d32" if is_green else "#c62828"
    bg = "#e8f5e9" if is_green else "#ffebee"
    return f"""
    <div style="background-color: {bg}; color: {color}; padding: 2px 6px; border-radius: 4px; font-weight: bold; text-align: center; border: 1px solid {color}; font-size: 0.8em; width: fit-content;">
        {text}
    </div>
    """

# --- UI: CSS ---
# --- UI: CSS & Header (Moved to top) ---

# --- Cargar Facturas Activas Automáticamente ---
if st.session_state.reload_data:
    with st.spinner("Cargando facturas pendientes de aprobación..."):
        st.session_state.facturas_activas = db.get_active_proposals_for_approval()
        # Inicializar checkboxes y SIMULACIÓN DE ESTADOS
        for f in st.session_state.facturas_activas:
            pid = f['proposal_id']
            # Inicializar en el diccionario lógico
            if pid not in st.session_state.facturas_seleccionadas_aprobacion:
                st.session_state.facturas_seleccionadas_aprobacion[pid] = False
            
            # Inicializar la KEY del widget
            widget_key = f"chk_app_{pid}"
            if widget_key not in st.session_state:
                st.session_state[widget_key] = st.session_state.facturas_seleccionadas_aprobacion[pid]

            # --- SIMULACIÓN DE ESTADOS RANDOM ---
            # Solo asignar si no existen, para mantener consistencia en la sesión
            if 'status_cavali' not in f:
                f['status_cavali'] = random.choice(['ENVIADO', 'CONFIRMADA'])
            if 'status_letra' not in f:
                f['status_letra'] = random.choice(['ENVIADA', 'FIRMADA'])
                
        st.session_state.reload_data = False

# --- Mostrar Facturas Pendientes ---
if not st.session_state.facturas_activas:
    st.info("✅ No hay facturas pendientes de aprobación en este momento.")
    st.info("✅ No hay facturas pendientes de aprobación en este momento.")
    # Button moved to Sidebar
else:
    # Agrupar por Lote
    grouped_invoices = defaultdict(list)
    for inv in st.session_state.facturas_activas:
        lote_id = inv.get('identificador_lote', 'Sin Lote')
        grouped_invoices[lote_id].append(inv)
    
    st.container(border=True)
    st.subheader(f"1. Facturas Pendientes de Aprobación ({len(st.session_state.facturas_activas)})")
    
    st.subheader(f"1. Facturas Pendientes de Aprobación ({len(st.session_state.facturas_activas)})")
    
    # Button moved to Sidebar
    
    st.markdown("---")
    
    # with st.form(key="approval_form"):  <-- DELETED FORM WRAPPER
    # Iterar por cada grupo (Lote)
    for lote_id, invoices_in_batch in grouped_invoices.items():
        
        # Obtener datos del lote (Emisor fecha) del primer elemento
        first_inv = invoices_in_batch[0]
        emisor_name = first_inv.get('emisor_nombre', 'N/A')
        created_at = first_inv.get('created_at', '') # Si existe
        
        # IDs de este lote
        batch_pids = [inv['proposal_id'] for inv in invoices_in_batch]
        
        # Calcular estado actual del "Select All" para este lote
        # True si TODOS los del lote están en True
        all_selected = all(st.session_state.facturas_seleccionadas_aprobacion.get(pid, False) for pid in batch_pids)
        
        with st.container(border=True):
            # Header del Lote
            st.markdown(f"**📦 Lote:** `{lote_id}` | **Emisor:** {emisor_name} | **Cant:** {len(invoices_in_batch)}")
            
            # Header de la Tablita
            # Adjusted Columns: Added 'Cavali' and 'Letra'
            col_check, col_factura, col_aceptante, col_monto, col_desembolso, col_cavali, col_letra = st.columns([0.4, 1.2, 1.8, 1.0, 1.0, 1.1, 1.1])
            
            with col_check: 
                # Checkbox Maestro para este lote
                batch_key = f"select_all_{lote_id}"
                st.checkbox(
                    "Todo", # Label corto o vacío
                    value=all_selected,
                    key=batch_key,
                    on_change=toggle_batch_selection,
                    args=(batch_key, batch_pids),
                    label_visibility="collapsed"
                )
            with col_factura: st.markdown("**Factura**")
            with col_aceptante: st.markdown("**Aceptante**")
            with col_monto: st.markdown("**M. Neto**")
            with col_desembolso: st.markdown("**Desembolso**")
            with col_cavali: st.markdown("**Est. Cavali**")
            with col_letra: st.markdown("**Est. Letra**")
            
            # Filas
            for idx, factura in enumerate(invoices_in_batch):
                col_check, col_factura, col_aceptante, col_monto, col_desembolso, col_cavali, col_letra = st.columns([0.4, 1.2, 1.8, 1.0, 1.0, 1.1, 1.1])
                
                with col_check:
                    # Usamos el ID real como key del checkbox
                    pid = factura['proposal_id']
                    # IMPORTANTE: No pasar 'value' si ya existe en session_state para evitar warning
                    # El valor se maneja via key y callbacks
                    is_checked = st.checkbox(
                        "",
                        # value=... REMOVED to avoid conflict with key in session_state
                        key=f"chk_app_{pid}", # Unique Key per invoice
                        label_visibility="collapsed"
                    )
                    # Sincronizar el diccionario lógico con el widget
                    st.session_state.facturas_seleccionadas_aprobacion[pid] = is_checked
                
                with col_factura: st.markdown(f"`{parse_invoice_number(factura['proposal_id'])}`")
                with col_aceptante: st.markdown(factura.get('aceptante_nombre', 'N/A'))
                with col_monto:
                    monto = safe_decimal(factura.get('monto_neto_factura', 0))
                    moneda = factura.get('moneda_factura', 'PEN')
                    st.markdown(f"{moneda} {monto:,.2f}")
                with col_desembolso:
                    monto_des = get_monto_a_desembolsar(factura)
                    moneda = factura.get('moneda_factura', 'PEN')
                    # Resaltar en negrita si es > 0, es el valor clave
                    val_str = f"**{moneda} {monto_des:,.2f}**" if monto_des > 0 else f"{moneda} 0.00"
                    st.markdown(val_str)
                with col_cavali:
                    stat = factura.get('status_cavali', 'PENDIENTE')
                    st.markdown(render_status_brick(stat, stat=='CONFIRMADA'), unsafe_allow_html=True)
                with col_letra:
                    stat = factura.get('status_letra', 'PENDIENTE')
                    st.markdown(render_status_brick(stat, stat=='FIRMADA'), unsafe_allow_html=True)

    st.markdown("---")
    
    # Botón Maestro
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Checkbox "Forzar" hidden logic or always visible? 
        # Requirement: "The user could approve even without both in green with a WARNING... User must check 'Confirmar aprobación forzada'"
        force_approval = st.checkbox("⚠️ Confirmar aprobación forzada (Ignorar estados incompletos)", 
                                     help="Marcar para proceder con la aprobación aunque Cavali o Letras no estén confirmados.")
        
        submit_button = st.button(
            "✅ Aprobar Facturas Seleccionadas",
            type="primary",
            use_container_width=True
        )
            
    # Procesar Aprobaciones
    if submit_button:
        # Recuperar objetos completos de facturas seleccionadas para calcular totales
        # Tenemos que buscarlas en facturas_activas
        selected_ids = [
            pid for pid, selected in st.session_state.facturas_seleccionadas_aprobacion.items()
            if selected
        ]
        
        selected_invoices_objs = [
            f for f in st.session_state.facturas_activas 
            if f['proposal_id'] in selected_ids
        ]
        
        if not selected_invoices_objs:
            st.warning("⚠️ No has seleccionado ninguna factura para aprobar.")
        else:
            # --- Validar Estados Cavali/Letras ---
            issues_found = []
            for inv in selected_invoices_objs:
                cavali = inv.get('status_cavali', 'ENVIADO')
                letra = inv.get('status_letra', 'ENVIADA')
                inv_num = parse_invoice_number(inv['proposal_id'])
                
                if cavali != 'CONFIRMADA' or letra != 'FIRMADA':
                    issues_found.append(f"{inv_num} (Cavali: {cavali}, Letra: {letra})")
            
            if issues_found and not force_approval:
                st.error("⛔ DETENIDO: Las siguientes facturas no tienen los estados confirmados:")
                for issue in issues_found:
                    st.markdown(f"- {issue}")
                st.warning("👉 Si desea proceder de todos modos, marque la casilla 'Confirmar aprobación forzada' arriba y presione Aprobar nuevamente.")
                st.stop() # Detener ejecución aquí
                
            st.markdown("---")
            st.subheader("Procesando Aprobaciones...")
            
            success_count = 0
            error_count = 0
            approved_list_temp = []
            total_desembolso_temp = 0.0
            last_emisor_temp = ""
            
            # Asumimos que si se aprueban varias, suelen ser del mismo emisor
            if selected_invoices_objs:
                last_emisor_temp = selected_invoices_objs[0].get('emisor_nombre', 'Desconocido')
            
            for invoice in selected_invoices_objs:
                proposal_id = invoice['proposal_id']
                try:
                    db.update_proposal_status(proposal_id, 'APROBADO')
                    
                    inv_num = parse_invoice_number(proposal_id)
                    mont_des = get_monto_a_desembolsar(invoice)
                    
                    # Store dict for detailed listing
                    approved_list_temp.append({
                        'num': inv_num,
                        'amount': mont_des
                    })
                    total_desembolso_temp += mont_des
                    
                    success_count += 1
                except Exception as e:
                    st.error(f"❌ Error al aprobar: {e}")
                    error_count += 1
            
            if success_count > 0:
                # Actualizar estado para el email
                st.session_state.last_approved_invoices = approved_list_temp
                st.session_state.last_approved_total = total_desembolso_temp
                st.session_state.last_approved_emisor = last_emisor_temp
                st.session_state.email_body_version += 1 # Force widget refresh
                
                st.success(f"🎉 Se aprobaron {success_count} factura(s) exitosamente.")
                st.balloons()
            
            if error_count > 0:
                st.error(f"⚠️ Hubo errores en {error_count} factura(s).")
            
            # Recargar y rerun automático (sin botón Continuar)
            st.session_state.reload_data = True
            st.rerun()


# --- Sección 2: Notificación por Correo (Reemplaza Información) ---
# st.markdown("---")
with st.container(border=True):
    st.subheader("2. Notificación de Aprobación")
    
    # Construct Body
    body_text = ""
    if st.session_state.last_approved_invoices:
        emisor = st.session_state.last_approved_emisor
        total = st.session_state.last_approved_total
        currency = "S/" # Default hardcoded for now or fetch from last invoice
        
        body_text = f"Estimados,\n\nSe informa que se han aprobado las siguientes facturas del emisor **{emisor}** por un monto total a desembolsar de **{currency} {total:,.2f}**:\n\n"
        
        for item in st.session_state.last_approved_invoices:
            # Handle if it was legacy string list or new dict list
            if isinstance(item, dict):
                body_text += f"- Factura {item['num']} ({currency} {item['amount']:,.2f})\n"
            else:
                body_text += f"- {item}\n"
                
        body_text += "\nSaludos cordiales,\nGerencia"
    else:
        # Fallback para cuando no hay facturas recientes (evitar texto de 'Adjuntos')
        body_text = "Estimados,\n\nSe notifica la aprobación de operaciones.\n\nSaludos cordiales,"
    
    # Use version in the key to force re-render with new value
    key_suffix_dynamic = f"aprobacion_v{st.session_state.email_body_version}"
    
    render_email_sender(
        key_suffix=key_suffix_dynamic,
        documents=[], # No attachments typically for just approval notification
        default_subject=f"Notificación de Aprobación - {st.session_state.last_approved_emisor}" if st.session_state.last_approved_emisor else "Notificación de Aprobación",
        default_body=body_text
    )


# --- Sidebar Recargar Data ---
with st.sidebar:
    st.markdown('---')
    if st.button(' Recargar Data', type='primary', use_container_width=True, help='Actualizar la lista de facturas pendientes'):
        st.session_state.reload_data = True
        st.rerun()
