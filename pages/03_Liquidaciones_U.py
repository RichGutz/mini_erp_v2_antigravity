# liquidacion_universal.py
import os
import streamlit as st
import datetime
import json
from decimal import Decimal, InvalidOperation

# --- Path Setup & Module Imports ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
from src.data import supabase_repository as db
from src.core.factoring_system import SistemaFactoringCompleto

# --- Page Config ---
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Módulo de Liquidación Universal INANDES",
    page_icon="🌍"
)

# --- Session State Initialization ---
def init_session_state():
    states = {
        'vista_actual_universal': 'busqueda',
        'lote_encontrado_universal': [],
        'resultados_liquidacion_universal': None,
        'global_liquidation_date_universal': datetime.date.today(),
        'global_backdoor_min_amount_universal': 100.0,
        'vouchers_universales': {}, # <--- AÑADIDO: Para guardar los vouchers
    }
    for key, value in states.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- Helper Functions ---
def parse_invoice_number(proposal_id: str) -> str:
    try:
        parts = proposal_id.split('-')
        return f"{parts[1]}-{parts[2]}" if len(parts) > 2 else proposal_id
    except (IndexError, AttributeError):
        return proposal_id

def safe_decimal(value, default=Decimal('0.0')) -> Decimal:
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        return default

# --- UI Views ---
def mostrar_busqueda_universal():
    st.header("Paso 1: Buscar Lote a Liquidar (Universal)")
    with st.form(key="search_lote_form_universal"):
        lote_id_input = st.text_input("Identificador de Lote", help="Pega aquí el identificador único del lote que deseas liquidar.")
        submit_button = st.form_submit_button(label="Buscar Lote")

    if submit_button:
        lote_id_sanitized = lote_id_input.strip()
        if not lote_id_sanitized:
            st.warning("Por favor, introduce el Identificador de Lote.")
            st.session_state.lote_encontrado_universal = []
        else:
            with st.spinner("Buscando facturas por liquidar..."):
                resultados = db.get_disbursed_proposals_by_lote(lote_id_sanitized)
                if resultados:
                    st.success(f"Se encontraron {len(resultados)} facturas desembolsadas.")
                    with st.spinner("Cargando detalles completos..."):
                        detalles_completos = [db.get_proposal_details_by_id(res.get('proposal_id')) for res in resultados]
                        st.session_state.lote_encontrado_universal = [d for d in detalles_completos if d]
                        st.session_state.vista_actual_universal = 'liquidacion'
                        st.rerun()
                else:
                    st.warning("No se encontraron facturas para el identificador de lote proporcionado.")

def mostrar_liquidacion_universal():
    st.header("Paso 2: Configurar y Ejecutar Liquidación Universal")
    if st.button("<- Volver a la búsqueda"):
        st.session_state.vista_actual_universal = 'busqueda'
        st.session_state.lote_encontrado_universal = []
        st.session_state.resultados_liquidacion_universal = None
        st.session_state.vouchers_universales = {} # Limpiar vouchers al volver
        st.rerun()

    with st.form(key="universal_liquidation_form"):
        st.subheader("Configuración Global de Liquidación")
        cols = st.columns(2)
        st.session_state.global_liquidation_date_universal = cols[0].date_input("Fecha de Pago Global", value=st.session_state.global_liquidation_date_universal)
        st.session_state.global_backdoor_min_amount_universal = cols[1].number_input("Monto Mínimo para Backdoor (S/)", value=st.session_state.global_backdoor_min_amount_universal, format="%.2f")
        
        st.markdown("---")
        
        facturas_inputs = {}
        for i, factura in enumerate(st.session_state.lote_encontrado_universal):
            proposal_id = factura.get('proposal_id', f'factura_{i}')
            with st.container(border=True):
                monto_neto = safe_decimal(factura.get('monto_neto_factura'))
                st.markdown(f"**Factura:** {parse_invoice_number(proposal_id)} | **Emisor:** {factura.get('emisor_nombre', 'N/A')} | **Monto Neto:** S/ {monto_neto:,.2f}")
                
                col1, col2 = st.columns(2)
                with col1:
                    facturas_inputs[proposal_id] = st.number_input(
                        "Monto Recibido", 
                        value=float(monto_neto), 
                        key=f"monto_{proposal_id}",
                        format="%.2f"
                    )
                with col2:
                    # <--- AÑADIDO: Uploader para el voucher de depósito ---
                    st.session_state.vouchers_universales[proposal_id] = st.file_uploader(
                        "Voucher de Depósito",
                        type=["pdf", "png", "jpg", "jpeg"],
                        key=f"uploader_{proposal_id}"
                    )

        submit_button = st.form_submit_button("Calcular Liquidación Universal", type="primary")

    if submit_button:
        # Lógica de cálculo (sin cambios)
        with st.spinner("Ejecutando nuevo motor de liquidación..."):
            sistema = SistemaFactoringCompleto()
            resultados_finales = []

            for factura in st.session_state.lote_encontrado_universal:
                proposal_id = factura.get('proposal_id')
                monto_pagado = facturas_inputs.get(proposal_id, 0.0)
                
                try:
                    recalc_json = json.loads(factura.get('recalculate_result_json', '{}'))
                    calculo_tasa = recalc_json.get('calculo_con_tasa_encontrada', {})
                    desglose = recalc_json.get('desglose_final_detallado', {})

                    fecha_desembolso_str = factura.get('fecha_desembolso_factoring')
                    fecha_vencimiento_str = factura.get('fecha_pago_calculada')

                    if not fecha_desembolso_str or not fecha_vencimiento_str:
                        st.error(f"Factura {parse_invoice_number(proposal_id)} no tiene fecha_desembolso_factoring o fecha_pago_calculada.")
                        continue

                    operacion = {
                        "id_operacion": proposal_id,
                        "capital_operacion": float(safe_decimal(calculo_tasa.get('capital'))),
                        "monto_desembolsado": float(safe_decimal(desglose.get('abono', {}).get('monto'))),
                        "interes_compensatorio": float(safe_decimal(desglose.get('interes', {}).get('monto'))),
                        "igv_interes": float(safe_decimal(desglose.get('interes', {}).get('igv'))),
                        "tasa_interes_mensual": float(safe_decimal(factura.get('interes_mensual')) / 100),
                        "fecha_desembolso": datetime.datetime.strptime(fecha_desembolso_str, '%d-%m-%Y').date(),
                        "fecha_vencimiento": datetime.datetime.strptime(fecha_vencimiento_str, '%d-%m-%Y').date(),
                    }

                    resultado = sistema.liquidar_operacion_con_back_door(
                        operacion=operacion,
                        fecha_pago=st.session_state.global_liquidation_date_universal,
                        monto_pagado=monto_pagado,
                        monto_minimo=st.session_state.global_backdoor_min_amount_universal
                    )
                    resultados_finales.append(resultado)

                except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
                    st.error(f"Error procesando factura {parse_invoice_number(proposal_id)}: {e}")
            
            st.session_state.resultados_liquidacion_universal = resultados_finales
            st.success("Cálculo de liquidación universal completado.")

    if st.session_state.resultados_liquidacion_universal:
        st.markdown("---")
        st.header("Paso 3: Resultados de la Liquidación Universal")

        for resultado in st.session_state.resultados_liquidacion_universal:
            with st.container(border=True):
                st.markdown(f"#### Factura: {parse_invoice_number(resultado.get('id_operacion'))}")
                
                if resultado.get("error"):
                    st.error(f"Error en cálculo: {resultado.get('error')}")
                    continue

                cols = st.columns(4)
                cols[0].metric("Saldo Global Final", f"S/ {resultado.get('saldo_global', 0):,.2f}")
                cols[1].metric("Estado", resultado.get('estado_operacion', 'N/A'))
                cols[2].metric("Días de Mora", resultado.get('dias_mora', 0))
                
                backdoor_aplicado = resultado.get('back_door_aplicado', False)
                cols[3].metric("Backdoor Aplicado", "Sí" if backdoor_aplicado else "No")

                if backdoor_aplicado:
                    st.info(f"Acción: {resultado.get('accion_recomendada')}")
                    st.write("Reducciones aplicadas:")
                    st.json(resultado.get('reducciones_aplicadas'))

                with st.expander("Ver desglose completo del cálculo"):
                    st.json(resultado)
        
        if st.button("Guardar Liquidaciones en Supabase", type="primary"):
            # Lógica de guardado (sin cambios, pero ahora se podría incluir el voucher)
            # Por ahora, solo se añade el uploader al front.
            with st.spinner("Guardando liquidaciones en Supabase..."):
                try:
                    for i, resultado in enumerate(st.session_state.resultados_liquidacion_universal):
                        if resultado.get("error"):
                            continue
                        
                        proposal_id = resultado['id_operacion']
                        factura_original = next((f for f in st.session_state.lote_encontrado_universal if f.get('proposal_id') == proposal_id), None)
                        if not factura_original:
                            st.warning(f"No se encontró la factura original para {proposal_id}. Saltando guardado.")
                            continue

                        resumen_id = db.get_or_create_liquidacion_resumen(proposal_id, factura_original)

                        db.add_liquidacion_evento(
                            liquidacion_resumen_id=resumen_id,
                            tipo_evento="Liquidación Universal",
                            fecha_evento=st.session_state.global_liquidation_date_universal,
                            monto_recibido=resultado['monto_pagado'],
                            dias_diferencia=resultado['dias_mora'],
                            resultado_json=resultado
                        )

                        db.update_liquidacion_resumen_saldo(resumen_id, resultado['saldo_global'])
                        db.update_proposal_status(proposal_id, resultado['estado_operacion'])

                    st.success("¡Liquidaciones guardadas exitosamente en Supabase!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Ocurrió un error al guardar en la base de datos: {e}")

# --- Main App Logic ---
st.title("🌍 Módulo de Liquidación Universal")
st.markdown("Esta es la nueva versión del sistema de liquidación que utiliza el motor de cálculo corregido y la lógica de `backdoor`.")

if st.session_state.vista_actual_universal == 'busqueda':
    mostrar_busqueda_universal()
elif st.session_state.vista_actual_universal == 'liquidacion':
    mostrar_liquidacion_universal()

