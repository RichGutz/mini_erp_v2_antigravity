# liquidacion_por_lotes_app.py
import os

# --- Path Setup ---
# The main script (00_Home.py) handles adding 'src' to the path.
# This page only needs to know the project root for static assets.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import datetime
import requests
import json
import subprocess
from src.utils.pdf_generators import generate_lote_report_pdf

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

# --- Configuración de la Página ---
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Módulo de Liquidación INANDES",
    page_icon="💰"
)

# --- Inicialización del Session State ---
if 'vista_actual' not in st.session_state: st.session_state.vista_actual = 'busqueda'
if 'lote_encontrado' not in st.session_state: st.session_state.lote_encontrado = []
if 'facturas_seleccionadas' not in st.session_state: st.session_state.facturas_seleccionadas = {}
if 'facturas_a_liquidar' not in st.session_state: st.session_state.facturas_a_liquidar = []
if 'resultados_liquidacion_lote' not in st.session_state: st.session_state.resultados_liquidacion_lote = None
if 'global_liquidation_vars' not in st.session_state: 
    st.session_state.global_liquidation_vars = {
        'fecha_pago': datetime.date.today(), 
        'tasa_mora_anual': 1.0, 
        'tasa_interes_compensatoria_pct': 0.0 
    }
if 'contract_number' not in st.session_state: st.session_state.contract_number = ''
if 'anexo_number' not in st.session_state: st.session_state.anexo_number = ''
if 'sustento_unico' not in st.session_state: st.session_state.sustento_unico = False
if 'consolidated_proof_file' not in st.session_state: st.session_state.consolidated_proof_file = None
if 'individual_proof_files' not in st.session_state: st.session_state.individual_proof_files = {}
 


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
    calculos = recalc_result.get('calculo_con_tasa_encontrada', {})
    busqueda = recalc_result.get('resultado_busqueda', {})
    moneda = data.get('moneda_factura', 'PEN')

    st.markdown(
        f"**Emisor:** {data.get('emisor_nombre', 'N/A')} | "
        f"**Aceptante:** {data.get('aceptante_nombre', 'N/A')} | "
        f"**Factura:** {data.get('numero_factura', 'N/A')} | "
        f"**F. Pago Original:** {data.get('fecha_pago_calculada', 'N/A')} | "
        f"**Monto Total:** {data.get('moneda_factura', '')} {data.get('monto_total_factura', 0):,.2f} | "
        f"**Monto Neto:** {data.get('moneda_factura', '')} {data.get('monto_neto_factura', 0):,.2f} | "
        f"**Int. Compensatorio:** {data.get('interes_mensual', 0.0):.2f}% | "
        f"**Int. Moratorio:** {data.get('interes_moratorio', 0.0):.2f}%"
    )

    tasa_avance_pct = busqueda.get('tasa_avance_encontrada', 0) * 100
    monto_neto = data.get('monto_neto_factura', 0)
    capital = calculos.get('capital', 0)
    abono = desglose.get('abono', {})
    interes = desglose.get('interes', {})
    com_est = desglose.get('comision_estructuracion', {})
    com_afi = desglose.get('comision_afiliacion', {})
    igv_total = desglose.get('igv_total', {})
    margen = desglose.get('margen_seguridad', {})

    lines = [
        f"| Item | Monto ({moneda}) | % sobre Neto | Detalle del Cálculo |",
        "|:---|---:|---:|:---|"
    ]
    if monto_neto > 0:
        lines.extend([
            f"| Monto Neto de Factura | **{monto_neto:,.2f}** | **100.00%** | Monto a financiar |",
            f"| Tasa de Avance Aplicada | N/A | {tasa_avance_pct:.2f}% | Tasa final para redondear desembolso |",
            f"| Margen de Seguridad | {margen.get('monto', 0):,.2f} | {margen.get('porcentaje', 0):.2f}% | `Monto Neto - Capital` |",
            f"| Capital | {capital:,.2f} | {((capital / monto_neto) * 100):.2f}% | `Monto Neto * Tasa de Avance` |",
            f"| Intereses | {interes.get('monto', 0):,.2f} | {interes.get('porcentaje', 0):.2f}% | `Capital * ((1 + Tasa Diaria)^Plazo - 1)` |",
            f"| Comisión de Estructuración | {com_est.get('monto', 0):,.2f} | {com_est.get('porcentaje', 0):.2f}% | `Valor Fijo o % sobre Capital` |"
        ])
        if com_afi.get('monto', 0) > 0:
            lines.append(f"| Comisión de Afiliación | {com_afi.get('monto', 0):,.2f} | {com_afi.get('porcentaje', 0):.2f}% | `Valor Fijo` |")
        lines.extend([
            f"| IGV Total | {igv_total.get('monto', 0):,.2f} | {igv_total.get('porcentaje', 0):.2f}% | `(Intereses + Comisiones) * 18%` |",
            "| | | | |",
            f"| **Monto a Desembolsar** | **{abono.get('monto', 0):,.2f}** | **{abono.get('porcentaje', 0):.2f}%** | `Capital - (Intereses + Comisiones + IGV)` |"
        ])
    
    st.markdown("\n".join(lines), unsafe_allow_html=True)

def _display_liquidation_detail_view_batch(result_dict: dict, moneda: str, event_date_str: str, received_amount: float):
    st.markdown(f"**Fecha del Evento:** {event_date_str} | **Monto Recibido:** {received_amount:,.2f} {moneda}")

    params = result_dict.get('parametros_calculo', {})
    dias_diferencia = result_dict.get('dias_diferencia', 0)
    
    cargos = result_dict.get('desglose_cargos', {})
    creditos = result_dict.get('desglose_creditos', {})
    saldo_final = result_dict.get('liquidacion_final', {}).get('saldo_final_a_liquidar', 0)

    lines = [
        f"| Concepto | Monto ({moneda}) | Detalle del Cálculo |",
        "|:---|---:|---:|"
    ]

    capital_base = params.get('capital_base', 0)
    lines.append(f"| Capital por Liquidar Anterior | {capital_base:,.2f} | `Capital base para el cálculo actual` |")
    lines.append(f"| Pago Efectuado | {-received_amount:,.2f} | `Monto recibido en el pago actual` |")

    dias_atraso = dias_diferencia
    tasa_compensatoria_diaria = params.get('tasa_diaria_compensatoria', 0) * 100
    tasa_moratoria_diaria = params.get('tasa_diaria_moratoria', 0) * 100
    base_mora = capital_base 

    lines.append(f"| Interés Compensatorio | {cargos.get('interes_compensatorio', 0):,.2f} | `Capital ({capital_base:,.2f}) * ((1 + {tasa_compensatoria_diaria:.4f}%) ^ {dias_atraso} - 1)` |")
    lines.append(f"| IGV s/ Int. Compensatorio | {cargos.get('igv_interes_compensatorio', 0):,.2f} | `Interés Compensatorio * 18%` |")
    lines.append(f"| Interés Moratorio | {cargos.get('interes_moratorio', 0):,.2f} | `Capital ({base_mora:,.2f}) * ((1 + {tasa_moratoria_diaria:.4f}%) ^ {dias_atraso} - 1)` |")
    lines.append(f"| IGV s/ Int. Moratorio | {cargos.get('igv_interes_moratorio', 0):,.2f} | `Interés Moratorio * 18%` |")
    
    if result_dict.get('tipo_pago') == 'Anticipado':
        interes_original = params.get('interes_original_completo', 0)
        dias_anticipacion = abs(dias_diferencia)
        plazo_original = params.get('plazo_operacion_original', 0)
        plazo_real = plazo_original - dias_anticipacion
        if plazo_real < 0: plazo_real = 0
        
        lines.append(f"| Devolución de Intereses | {-creditos.get('interes_a_devolver', 0):,.2f} | `Int. Original ({interes_original:,.2f}) - Int. Real (plazo {plazo_real} días)` |")
        lines.append(f"| Devolución de IGV | {-creditos.get('igv_interes_a_devolver', 0):,.2f} | `Devolución de Intereses * 18%` |")

    if round(saldo_final, 2) >= 0:
        lines.append(f"| **Nuevo Capital por Liquidar** | **{saldo_final:,.2f}** | `Suma de todos los conceptos` |")
    else:
        lines.append(f"| **Saldo por devolver al emisor** | **{abs(saldo_final):,.2f}** | `Suma de todos los conceptos` |")

    st.markdown("\n".join(lines), unsafe_allow_html=True)

def _display_forecast_table_batch(proposal_id, fecha_inicio_proyeccion, initial_capital):
    st.markdown("**Proyección de Deuda Post-Pago (Interés Compuesto Diario)**")
    payload = {"proposal_id": proposal_id, "fecha_inicio_proyeccion": fecha_inicio_proyeccion, "initial_capital": initial_capital}
    try:
        response = requests.post(f"{API_BASE_URL}/liquidaciones/get_projected_balance", json=payload)
        response.raise_for_status()
        forecast_data = response.json()
        if forecast_data.get('error') or not forecast_data.get('proyeccion_futura'):
            return

        proyeccion = forecast_data['proyeccion_futura']
        
        def render_chunk_as_pivoted_table(chunk):
            if not chunk: return
            header = "| Concepto | " + " | ".join([d['fecha'] for d in chunk]) + " |"
            separator = "|:---| " + " | ".join(["---:" for _ in chunk]) + " |"
            row_capital_ant = "| Capital Anterior | " + " | ".join([f"{d['capital_anterior']:,.2f}" for d in chunk]) + " |"
            row_int_comp = "| (+) Int. Compensatorio | " + " | ".join([f"{d['interes_compensatorio']:,.2f}" for d in chunk]) + " |"
            row_igv_comp = "| (+) IGV Comp. | " + " | ".join([f"{d['igv_compensatorio']:,.2f}" for d in chunk]) + " |"
            row_int_mora = "| (+) Int. Moratorio | " + " | ".join([f"{d['interes_moratorio']:,.2f}" for d in chunk]) + " |"
            row_igv_mora = "| (+) IGV Mora. | " + " | ".join([f"{d['igv_moratorio']:,.2f}" for d in chunk]) + " |"
            row_nuevo_cap = "| **Nuevo Capital** | " + " | ".join([f"**{d['capital_proyectado']:,.2f}**" for d in chunk]) + " |"
            st.markdown("\n".join([header, separator, row_capital_ant, row_int_comp, row_igv_comp, row_int_mora, row_igv_mora, row_nuevo_cap]), unsafe_allow_html=True)

        render_chunk_as_pivoted_table(proyeccion[0:15])
        if len(proyeccion) > 15: 
            st.markdown("&nbsp;") # Spacer
            render_chunk_as_pivoted_table(proyeccion[15:30])

    except requests.exceptions.RequestException as e:
        st.warning(f"No se pudo obtener la proyección de deuda: {e}")

# --- Lógica de Vistas ---
def mostrar_busqueda():
    st.header("Paso 1: Buscar Lote a Liquidar")
    with st.form(key="search_lote_form"):
        lote_id_input = st.text_input("Identificador de Lote", help="Pega aquí el identificador único del lote que deseas liquidar.")
        submit_button = st.form_submit_button(label="Buscar Lote")

    if submit_button:
        lote_id_sanitized = lote_id_input.strip()
        if not lote_id_sanitized:
            st.warning("Por favor, introduce el Identificador de Lote.")
            st.session_state.lote_encontrado = []
        else:
            with st.spinner("Buscando facturas por liquidar..."):
                resultados = db.get_disbursed_proposals_by_lote(lote_id_sanitized)
                st.session_state.lote_encontrado = resultados
                if resultados:
                    st.success(f"Se encontraron {len(resultados)} facturas por liquidar.")
                    
                    # --- BEGIN: Fetch full details for all proposals in the lote ---
                    with st.spinner("Cargando detalles de las facturas..."):
                        detalles_completos = []
                        for res in resultados:
                            proposal_id = res.get('proposal_id')
                            if proposal_id:
                                detalles = db.get_proposal_details_by_id(proposal_id)
                                if detalles:
                                    detalles_completos.append(detalles)
                        st.session_state.lote_encontrado = detalles_completos
                    # --- END: Fetch full details for all proposals in the lote ---

                    if st.session_state.lote_encontrado:
                        st.session_state.anexo_number = st.session_state.lote_encontrado[0].get('anexo_number', '')
                        st.session_state.contract_number = st.session_state.lote_encontrado[0].get('contract_number', '')
                        st.session_state.facturas_seleccionadas = {f['proposal_id']: True for f in st.session_state.lote_encontrado}

                        # --- BEGIN: Update global vars with data from the first proposal ---
                        first_proposal_details = st.session_state.lote_encontrado[0]
                        st.session_state.global_liquidation_vars['tasa_interes_compensatoria_pct'] = first_proposal_details.get('interes_mensual', 0.0)
                        st.session_state.global_liquidation_vars['tasa_mora_anual'] = first_proposal_details.get('interes_moratorio', 0.0)
                        # --- END: Update global vars with data from the first proposal ---
                else:
                    st.warning("No se encontraron facturas desembolsadas o en proceso de liquidación para el identificador de lote proporcionado.")

    if st.session_state.lote_encontrado:
        st.markdown("---")
        st.subheader("Paso 2: Seleccionar Facturas")
        with st.form(key="select_invoices_form"):
            for f in st.session_state.lote_encontrado:
                st.checkbox(f"**Factura:** {parse_invoice_number(f['proposal_id'])} | **Emisor:** {f.get('emisor_nombre', 'N/A')} | **Estado:** {f.get('estado', 'N/A')}", 
                            value=st.session_state.facturas_seleccionadas.get(f['proposal_id'], True), 
                            key=f['proposal_id'])
            if st.form_submit_button("Cargar Historias para Liquidar"):
                ids = []
                for f in st.session_state.lote_encontrado:
                    checkbox_key = f['proposal_id']
                    if st.session_state.get(checkbox_key, False): # Check the actual state of the checkbox
                        ids.append(checkbox_key)
                
                if not ids:
                    st.warning("No has seleccionado ninguna factura.")
                else:
                    with st.spinner(f"Cargando detalles para {len(ids)} facturas..."):
                        detalles = [db.get_proposal_details_by_id(pid) for pid in ids]
                        facturas_cargadas = [d for d in detalles if d and not d.get('error')]
                        
                        if facturas_cargadas:
                            st.session_state.facturas_a_liquidar = facturas_cargadas
                            st.session_state.anexo_number = st.session_state.facturas_a_liquidar[0].get('anexo_number', '')
                            st.session_state.contract_number = st.session_state.facturas_a_liquidar[0].get('contract_number', '')
                            for d in st.session_state.facturas_a_liquidar:
                                d['local_liquidation_vars'] = st.session_state.global_liquidation_vars.copy()
                                d['local_liquidation_vars']['tasa_interes_compensatoria_pct'] = d.get('interes_mensual', 0.0)
                            st.session_state.vista_actual = 'liquidacion'
                            st.rerun()
                        else:
                            st.error("Error: No se pudieron cargar los detalles para ninguna de las facturas seleccionadas. Revisa la base de datos.")

def mostrar_liquidacion():
    st.header("Paso 3: Configurar y Ejecutar Liquidación")
    if st.button("<- Volver a la búsqueda"):
        st.session_state.vista_actual = 'busqueda'
        st.session_state.lote_encontrado = []
        st.session_state.facturas_a_liquidar = []
        st.session_state.resultados_liquidacion_lote = None
        
        st.rerun()

    # --- Configuración Global (Fuera del Formulario) ---
    with st.container(border=True):
        st.markdown("#### Configuración Global")
        g_vars = st.session_state.global_liquidation_vars
        cols = st.columns(3) # 3 columnas
        g_vars['fecha_pago'] = cols[0].date_input("Fecha de Pago", g_vars['fecha_pago'])
        g_vars['tasa_interes_compensatoria_pct'] = cols[1].number_input("Tasa Interés Compensatorio (% Mensual)", g_vars['tasa_interes_compensatoria_pct'], format="%.2f")
        g_vars['tasa_mora_anual'] = cols[2].number_input("Tasa Interés Moratorio (% Mensual)", g_vars['tasa_mora_anual'], format="%.2f")
        
        if st.button("Propagar Globales a Todas"):
            for f in st.session_state.facturas_a_liquidar:
                # Preservar el monto_recibido actual antes de copiar las globales
                current_monto_recibido = f['local_liquidation_vars'].get('monto_recibido', 0.0)
                f['local_liquidation_vars'] = g_vars.copy()
                f['local_liquidation_vars']['monto_recibido'] = current_monto_recibido
            st.toast("Valores globales propagados.")
            st.rerun()

    st.markdown("---")

    st.markdown("---")
    st.checkbox("APLICAR SUSTENTO DE PAGO UNICO", key="sustento_unico")
    st.session_state.consolidated_proof_file = st.file_uploader(
        "Subir Evidencia Consolidada (PDF/Imagen)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="consolidated_uploader",
        disabled=not st.session_state.sustento_unico
    )

    # --- Formulario Principal para Liquidación ---
    with st.form(key="liquidation_form"):
        st.markdown("#### Facturas del Lote")
        for i, f in enumerate(st.session_state.facturas_a_liquidar):
            with st.container(border=True):
                st.markdown(f"##### Factura: {parse_invoice_number(f['proposal_id'])} | Emisor: {f.get('emisor_nombre', 'N/A')}")
                
                # --- Perfil de la Operación Original (Replicado de liquidacion_app.py) ---
                _display_operation_profile_batch(f)

                # --- Historial de Pagos Registrados (Replicado de liquidacion_app.py) ---
                eventos_liquidacion = db.get_liquidacion_eventos(f['proposal_id'])
                if eventos_liquidacion:
                    st.markdown("###### Historial de Pagos Registrados")
                    for j, event in enumerate(eventos_liquidacion):
                        resultado = json.loads(event['resultado_json']) if isinstance(event['resultado_json'], str) else event['resultado_json']
                        fecha_evento_str = datetime.datetime.fromisoformat(event['fecha_evento'].split('+')[0]).strftime('%d-%m-%Y')
                        _display_liquidation_detail_view_batch(resultado, f.get('moneda_factura', 'PEN'), fecha_evento_str, event['monto_recibido'])
                        
                        # Proyección de Deuda Post-Pago si es el último evento y hay saldo
                        if (j == len(eventos_liquidacion) - 1) and (resultado.get('liquidacion_final', {}).get('saldo_final_a_liquidar', 0) > 0):
                            st.markdown("---")
                            _display_forecast_table_batch(f['proposal_id'], event['fecha_evento'], abs(resultado.get('liquidacion_final', {}).get('saldo_final_a_liquidar', 0)))
                            st.markdown("---")

                st.markdown("##### Variables de Liquidación Locales")
                l_vars = f['local_liquidation_vars']
                l_cols = st.columns(4) # 4 columnas
                l_vars['fecha_pago'] = l_cols[0].date_input("Fecha de Pago", l_vars['fecha_pago'], key=f"fl_{i}")
                
                # Por defecto, el monto recibido es el neto de la factura.
                # El usuario puede ajustarlo manualmente si el pago fue parcial.
                l_vars['monto_recibido'] = f.get('monto_neto_factura', 0.0)
                
                l_vars['monto_recibido'] = l_cols[1].number_input("Monto Recibido", value=l_vars.get('monto_recibido', 0.0), format="%.2f", key=f"mr_{i}")
                l_vars['tasa_interes_compensatoria_pct'] = l_cols[2].number_input("Tasa Interés Compensatorio (% Mensual)", l_vars['tasa_interes_compensatoria_pct'], format="%.2f", key=f"tic_{i}")
                l_vars['tasa_mora_anual'] = l_cols[3].number_input("Tasa Interés Moratorio (% Mensual)", l_vars['tasa_mora_anual'], format="%.2f", key=f"tm_{i}")
                
                st.markdown("###### Agregar Sustento Individual")
                st.session_state.individual_proof_files[f['proposal_id']] = st.file_uploader(
                    f"Sustento para Factura {parse_invoice_number(f['proposal_id'])}",
                    type=["pdf", "png", "jpg", "jpeg"],
                    key=f"uploader_{i}",
                    disabled=st.session_state.sustento_unico
                )

        if st.form_submit_button("Simular Liquidación", type="primary"):
            with st.spinner("Simulando liquidación en lote..."):
                lote_payload = []
                for factura in st.session_state.facturas_a_liquidar:
                    eventos_previos = db.get_liquidacion_eventos(factura['proposal_id'])
                    loc_vars = factura['local_liquidation_vars']
                    payload = {
                        "proposal_id": factura['proposal_id'],
                        "monto_recibido": loc_vars['monto_recibido'],
                        "fecha_pago_real": loc_vars['fecha_pago'].strftime('%d-%m-%Y'), 
                        "tasa_interes_compensatoria_pct": loc_vars['tasa_interes_compensatoria_pct'],
                        "tasa_interes_moratoria_pct": loc_vars['tasa_mora_anual'] / 12,
                        "is_first_payment": not bool(eventos_previos)
                    }
                    lote_payload.append(payload)
                try:
                    response = requests.post(f"{API_BASE_URL}/liquidaciones/simular_liquidacion_lote", json={"usuario_id": "system", "liquidaciones": lote_payload})
                    response.raise_for_status()
                    st.session_state.resultados_liquidacion_lote = response.json()
                    st.success("¡Simulación de lote completada con éxito!")
                    
                    
                except requests.exceptions.RequestException as e:
                    st.error(f"Error de conexión con la API: {e}")

    if st.session_state.resultados_liquidacion_lote:
        st.markdown("---")
        st.header("Paso 4: Resultados de la Liquidación")
        for i, f in enumerate(st.session_state.facturas_a_liquidar):
            st.write(f"**Factura: {parse_invoice_number(f['proposal_id'])}**")
            res = st.session_state.resultados_liquidacion_lote['resultados_del_lote'][i]['resultado_calculo']
            loc_vars = f['local_liquidation_vars']
            _display_liquidation_detail_view_batch(
                res, 
                f.get('moneda_factura', 'PEN'), 
                loc_vars['fecha_pago'].strftime('%d-%m-%Y'), 
                loc_vars['monto_recibido']
            )
            
            saldo_final_actual = res.get('liquidacion_final', {}).get('saldo_final_a_liquidar', 0)
            if saldo_final_actual > 0:
                st.markdown("---")
                _display_forecast_table_batch(
                    f['proposal_id'], 
                    loc_vars['fecha_pago'].isoformat(),
                    abs(saldo_final_actual)
                )
                st.markdown("---")

        

        # Botón para generar PDF (siempre visible después de liquidar)
        if st.button("Generar Reporte PDF"):
            with st.spinner("Generando reporte..."):
                report_data = {
                    'contract_number': st.session_state.contract_number,
                    'anexo_number': st.session_state.anexo_number,
                    'report_date': datetime.date.today().strftime('%d-%m-%Y'),
                    'facturas': [],
                    'summary': {}
                }
                total_capital = 0
                total_pagado = 0
                total_cargos = 0
                total_creditos = 0
                saldo_consolidado = 0

                for i, f in enumerate(st.session_state.facturas_a_liquidar):
                    res = st.session_state.resultados_liquidacion_lote['resultados_del_lote'][i]['resultado_calculo']
                    factura_data = {
                        'numero_factura': parse_invoice_number(f['proposal_id']),
                        'emisor_nombre': f.get('emisor_nombre'),
                        'moneda': f.get('moneda_factura'),
                        'monto_neto_factura': f.get('monto_neto_factura'),
                        'capital_original': json.loads(f.get('recalculate_result_json', '{}')).get('calculo_con_tasa_encontrada', {}).get('capital', 0.0),
                        'fecha_pago_original': f.get('fecha_pago_calculada'),
                        'plazo_original': f.get('plazo_operacion_calculado'),
                        'liquidation_params': {
                            **f['local_liquidation_vars'],
                            'fecha_pago': f['local_liquidation_vars']['fecha_pago'].strftime('%d-%m-%Y'),
                            'tasa_interes_moratoria_pct': f['local_liquidation_vars']['tasa_mora_anual'] / 12
                        },
                        'result': res
                    }
                    report_data['facturas'].append(factura_data)
                    total_capital += factura_data['capital_original']
                    total_pagado += f['local_liquidation_vars']['monto_recibido']
                    total_cargos += res.get('desglose_cargos', {}).get('total_cargos', 0)
                    total_creditos += res.get('desglose_creditos', {}).get('total_creditos', 0)
                    saldo_consolidado += res.get('liquidacion_final', {}).get('saldo_final_a_liquidar', 0)
                
                report_data['summary'] = {
                    'moneda': report_data['facturas'][0]['moneda'] if report_data['facturas'] else 'PEN',
                    'total_capital_desembolsado': total_capital,
                    'total_pagado': total_pagado,
                    'total_cargos': total_cargos,
                    'total_creditos': total_creditos,
                    'saldo_final_consolidado': saldo_consolidado
                }

                pdf_bytes = generate_lote_report_pdf(report_data)

                if pdf_bytes:
                    output_filename = f"reporte_liquidacion_lote_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    st.success(f"Reporte generado: {output_filename}")
                    st.download_button(
                        label="Descargar Reporte PDF",
                        data=pdf_bytes,
                        file_name=output_filename,
                        mime="application/pdf"
                    )
                else:
                    st.error("Error: No se pudo generar el PDF. Revisa los logs para más detalles.")

        if st.session_state.resultados_liquidacion_lote:
            if st.button("Guardar Liquidación en Supabase"):
                with st.spinner("Guardando liquidación en lote..."):
                    lote_payload = []
                    for factura in st.session_state.facturas_a_liquidar:
                        eventos_previos = db.get_liquidacion_eventos(factura['proposal_id'])
                        loc_vars = factura['local_liquidation_vars']
                        payload = {
                            "proposal_id": factura['proposal_id'],
                            "monto_recibido": loc_vars['monto_recibido'],
                            "fecha_pago_real": loc_vars['fecha_pago'].strftime('%d-%m-%Y'), 
                            "tasa_interes_compensatoria_pct": loc_vars['tasa_interes_compensatoria_pct'],
                            "tasa_interes_moratoria_pct": loc_vars['tasa_mora_anual'] / 12,
                            "is_first_payment": not bool(eventos_previos)
                        }
                        lote_payload.append(payload)
                    try:
                        response = requests.post(f"{API_BASE_URL}/liquidaciones/procesar_liquidacion_lote", json={"usuario_id": "system", "liquidaciones": lote_payload})
                        response.raise_for_status()
                        st.session_state.resultados_liquidacion_lote = response.json()
                        st.success("¡Lote liquidado y guardado con éxito!")
                        
                        
                    except requests.exceptions.RequestException as e:
                        st.error(f"Error de conexión con la API: {e}")

        # Botón para finalizar y volver (siempre visible después de liquidar)
        if st.button("Finalizar y Volver"):
            st.session_state.vista_actual = 'busqueda'
            st.session_state.lote_encontrado = []
            st.session_state.facturas_a_liquidar = []
            st.session_state.resultados_liquidacion_lote = None
            
            st.rerun()


# --- UI: Título y CSS ---

st.markdown("""<style>
[data-testid=\"stHorizontalBlock\"] {
   align-items: center;
}
</style>""", unsafe_allow_html=True)


col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
with col1:
    st.image(os.path.join(project_root, "static", "logo_geek.png"), width=200)
with col2:
    st.markdown("<h2 style='text-align: center; font-size: 2.4em;'>Módulo de Liquidación</h2>", unsafe_allow_html=True)
with col3:
    empty_col, logo_col = st.columns([2, 1])
    with logo_col:
        st.image(os.path.join(project_root, "static", "logo_inandes.png"), width=195)

# --- Lógica de Control de Vistas ---
if st.session_state.vista_actual == 'busqueda':
    mostrar_busqueda()
elif st.session_state.vista_actual == 'liquidacion':
    mostrar_liquidacion()
