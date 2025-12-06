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
from src.utils.pdf_generators import generate_liquidacion_universal_pdf

# --- Page Config ---
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Módulo de Liquidación INANDES",
    page_icon="💰"
)

# --- Session State Initialization ---
def init_session_state():
    states = {
        'vista_actual_universal': 'busqueda',
        'lote_encontrado_universal': [],
        'resultados_liquidacion_universal': None,
        'global_liquidation_date_universal': datetime.date.today(),
        'global_backdoor_min_amount_universal': 100.0,
        'vouchers_universales': {}, # <--- AÑADIDO: Para guardar los vouchers individuales
        'voucher_global_liquidacion': None, # <--- NUEVO: Para voucher consolidado
        'usar_voucher_unico_liquidacion': False, # <--- NUEVO: Checkbox de control
        'fechas_pago_individuales': {}, # <--- NUEVO: Para almacenar fechas individuales por factura
        'previous_global_date': None, # <--- NUEVO: Para detectar cambios en la fecha global
    }
    for key, default_value in states.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# --- Helper Functions ---
def parse_date_flexible(date_str):
    """
    Parsea una fecha que puede venir en formato DD-MM-YYYY o YYYY-MM-DD (ISO).
    Retorna un objeto datetime.date.
    """
    if not date_str:
        return None
    
    # Intentar formato DD-MM-YYYY primero
    try:
        return datetime.datetime.strptime(date_str, '%d-%m-%Y').date()
    except ValueError:
        pass
    
    # Intentar formato ISO YYYY-MM-DD
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        pass
    
    # Si ninguno funciona, intentar parsear como ISO con fromisoformat
    try:
        return datetime.date.fromisoformat(date_str)
    except (ValueError, AttributeError):
        raise ValueError(f"No se pudo parsear la fecha: {date_str}")

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

def extraer_numero_correlativo(proposal_id: str) -> int:
    """
    Extrae el número correlativo del proposal_id.
    Formato esperado: EMISOR-SERIE-NUMERO-TIMESTAMP
    Ejemplo: TRANS_STAR_HERMANOS_SAC-E001-1104-20251205164005
    Retorna: 1104
    """
    try:
        parts = proposal_id.split('-')
        if len(parts) >= 3:
            return int(parts[2])
        return 0
    except (IndexError, ValueError, AttributeError):
        return 0

def serialize_resultado_for_json(resultado: dict) -> dict:
    """
    Convierte objetos date/datetime a strings para que sean serializables a JSON.
    """
    import datetime
    serialized = {}
    for key, value in resultado.items():
        if isinstance(value, (datetime.date, datetime.datetime)):
            serialized[key] = value.isoformat()
        elif isinstance(value, list):
            # Serializar listas recursivamente
            serialized[key] = [
                serialize_resultado_for_json(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, dict):
            # Serializar diccionarios recursivamente
            serialized[key] = serialize_resultado_for_json(value)
        else:
            serialized[key] = value
    return serialized

def generar_tabla_calculo_liquidacion(resultado: dict, factura_original: dict) -> str:
    """
    Genera tabla markdown con desglose detallado de cálculos de liquidación.
    Enfocado en comparar DEVENGADO vs FACTURADO.
    """
    if resultado.get("error"):
        return f"**Error:** {resultado.get('error')}"
    
    lines = []
    lines.append("| Item | Monto (S/) | Fórmula de Cálculo | Detalle del Cálculo |")
    lines.append("| :--- | :--- | :--- | :--- |")
    
    # Datos originales de la operación
    capital_op = resultado.get('capital_operacion', 0)
    monto_desemb = resultado.get('monto_desembolsado', 0)
    monto_pagado = resultado.get('monto_pagado', 0)
    
    lines.append(f"| **DATOS DE LA OPERACIÓN** | | | |")
    lines.append(f"| Capital Operación | {capital_op:,.2f} | `Dato original` | Capital financiado |")
    lines.append(f"| Monto Desembolsado | {monto_desemb:,.2f} | `Dato original` | Monto entregado al cliente |")
    lines.append(f"| Monto Pagado | {monto_pagado:,.2f} | `Dato de entrada` | Monto recibido del cliente |")
    
    # Cálculo de días
    dias_trans = resultado.get('dias_transcurridos', 0)
    dias_para_interes = resultado.get('dias_para_calculo_interes', dias_trans)
    dias_minimos = resultado.get('dias_minimos_aplicados', 0)
    dias_mora = resultado.get('dias_mora', 0)
    fecha_liq = resultado.get('fecha_liquidacion', 'N/A')
    
    lines.append(f"| | | | |")
    lines.append(f"| **PERÍODOS** | | | |")
    lines.append(f"| Fecha de Liquidación | - | `Dato de entrada` | {fecha_liq} |")
    lines.append(f"| Días Transcurridos | {dias_trans} | `Fecha Liq - Fecha Desemb` | Días desde desembolso |")
    
    # Mostrar si se aplicó la regla de días mínimos
    if dias_para_interes > dias_trans:
        lines.append(f"| **Días para Cálculo de Interés** | **{dias_para_interes}** | `max(Días Trans, Mínimo)` | **Se aplicó regla de {dias_minimos} días mínimos** |")
    else:
        lines.append(f"| Días para Cálculo de Interés | {dias_para_interes} | `Días transcurridos` | No se aplicó regla de mínimos |")
    
    lines.append(f"| Días de Mora | {dias_mora} | `Fecha Liq - Fecha Venc` | Días de atraso |")
    
    # COMPARACIÓN: DEVENGADO VS FACTURADO
    interes_dev = resultado.get('interes_devengado', 0)
    igv_int_dev = resultado.get('igv_interes_devengado', 0)
    tasa_mensual = factura_original.get('interes_mensual', 0) if factura_original else 0
    
    # Obtener valores originales del recalculate_result_json
    interes_original = 0
    igv_original = 0
    
    if factura_original:
        try:
            recalc_json = json.loads(factura_original.get('recalculate_result_json', '{}'))
            desglose = recalc_json.get('desglose_final_detallado', {})
            calculos = recalc_json.get('calculo_con_tasa_encontrada', {})
            
            # Interés original está en calculos, no en desglose
            interes_original = float(calculos.get('interes', 0))
            
            # IGV está en calculos, no en desglose
            igv_original = float(calculos.get('igv_interes', 0))
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            pass
    
    lines.append(f"| | | | |")
    lines.append(f"| **COMPARACIÓN: DEVENGADO VS FACTURADO** | | | |")
    lines.append(f"| | | | |")
    
    # Intereses Compensatorios
    lines.append(f"| **Interés Compensatorio** | | | |")
    lines.append(f"| → Facturado (Original) | {interes_original:,.2f} | `Valor en operación original` | Interés cobrado al desembolsar |")
    lines.append(f"| → Devengado (Calculado) | {interes_dev:,.2f} | `Capital × Tasa × (Días/30)` | `{capital_op:,.2f} × {tasa_mensual:.2f}% × ({dias_para_interes}/30) = {interes_dev:,.2f}` |")
    
    # Calcular delta manualmente para asegurar consistencia
    delta_int = interes_dev - interes_original
    delta_signo = "+" if delta_int >= 0 else ""
    lines.append(f"| → **Diferencia (Delta)** | **{delta_signo}{delta_int:,.2f}** | `Devengado - Facturado` | `{interes_dev:,.2f} - {interes_original:,.2f} = {delta_int:,.2f}` |")
    
    lines.append(f"| | | | |")
    
    # IGV sobre Intereses
    lines.append(f"| **IGV sobre Intereses** | | | |")
    lines.append(f"| → Facturado (Original) | {igv_original:,.2f} | `Valor en operación original` | IGV cobrado al desembolsar |")
    lines.append(f"| → Devengado (Calculado) | {igv_int_dev:,.2f} | `Interés Devengado × 18%` | `{interes_dev:,.2f} × 18% = {igv_int_dev:,.2f}` |")
    
    # Calcular delta manualmente para asegurar consistencia
    delta_igv_int = igv_int_dev - igv_original
    delta_igv_signo = "+" if delta_igv_int >= 0 else ""
    lines.append(f"| → **Diferencia (Delta)** | **{delta_igv_signo}{delta_igv_int:,.2f}** | `Devengado - Facturado` | `{igv_int_dev:,.2f} - {igv_original:,.2f} = {delta_igv_int:,.2f}` |")
    
    # Intereses moratorios (si hay mora)
    if dias_mora > 0:
        interes_mor = resultado.get('interes_moratorio', 0)
        igv_mor = resultado.get('igv_moratorio', 0)
        
        lines.append(f"| | | | |")
        lines.append(f"| **INTERESES MORATORIOS** | | | |")
        lines.append(f"| → Interés Moratorio | {interes_mor:,.2f} | `Capital × Tasa Mora × (Días/30)` | {dias_mora} días de mora |")
        lines.append(f"| → IGV Moratorio | {igv_mor:,.2f} | `Interés Mora × 18%` | `{interes_mor:,.2f} × 18% = {igv_mor:,.2f}` |")
    
    # Capital
    # Calcular delta manualmente para asegurar consistencia
    delta_cap = capital_op - monto_pagado
    delta_cap_signo = "+" if delta_cap >= 0 else ""
    
    lines.append(f"| | | | |")
    lines.append(f"| **CAPITAL** | | | |")
    lines.append(f"| → Capital Operación | {capital_op:,.2f} | `Dato original` | Capital a recuperar |")
    lines.append(f"| → Monto Pagado | {monto_pagado:,.2f} | `Dato de entrada` | Monto recibido |")
    lines.append(f"| → **Diferencia (Delta)** | **{delta_cap_signo}{delta_cap:,.2f}** | `Capital - Pagado` | `{capital_op:,.2f} - {monto_pagado:,.2f} = {delta_cap:,.2f}` |")
    
    # Saldo global
    saldo_original = resultado.get('saldo_original', 0)
    saldo_global = resultado.get('saldo_global', 0)
    
    # Obtener deltas del resultado para mostrar el cálculo exacto
    delta_int_resultado = resultado.get('delta_intereses', 0)
    delta_igv_resultado = resultado.get('delta_igv_intereses', 0)
    interes_mora_resultado = resultado.get('interes_moratorio', 0)
    igv_mora_resultado = resultado.get('igv_moratorio', 0)
    delta_cap_resultado = resultado.get('delta_capital', 0)
    
    lines.append(f"| | | | |")
    lines.append(f"| **SALDO GLOBAL** | | | |")
    lines.append(f"| Componentes del Saldo: | | | |")
    lines.append(f"| → Delta Intereses | {delta_int_resultado:,.2f} | `Del cálculo` | - |")
    lines.append(f"| → Delta IGV Intereses | {delta_igv_resultado:,.2f} | `Del cálculo` | - |")
    lines.append(f"| → Interés Moratorio | {interes_mora_resultado:,.2f} | `Del cálculo` | - |")
    lines.append(f"| → IGV Moratorio | {igv_mora_resultado:,.2f} | `Del cálculo` | - |")
    lines.append(f"| → Delta Capital | {delta_cap_resultado:,.2f} | `Del cálculo` | - |")
    lines.append(f"| **Saldo antes de Backdoor** | **{saldo_original:,.2f}** | `Suma de componentes` | `{delta_int_resultado:,.2f} + {delta_igv_resultado:,.2f} + {interes_mora_resultado:,.2f} + {igv_mora_resultado:,.2f} + {delta_cap_resultado:,.2f} = {saldo_original:,.2f}` |")
    
    # Backdoor
    backdoor_aplicado = resultado.get('back_door_aplicado', False)
    if backdoor_aplicado:
        monto_min = resultado.get('monto_minimo_configurado', 0)
        reducciones = resultado.get('reducciones_aplicadas', [])
        
        lines.append(f"| | | | |")
        lines.append(f"| **BACKDOOR** | | | |")
        lines.append(f"| Condición | Saldo < {monto_min:,.2f} | `Saldo < Mínimo` | Backdoor activado |")
        
        if reducciones:
            lines.append(f"| | | | |")
            for i, red in enumerate(reducciones, 1):
                concepto = red.get('concepto', 'N/A')
                valor_antes = red.get('valor_antes', 0)
                valor_despues = red.get('valor_despues', 0)
                saldo_resultante = red.get('saldo_resultante', 0)
                lines.append(f"| {i}. {concepto} | {valor_antes:,.2f} → {valor_despues:,.2f} | `Reducción` | Saldo: {saldo_resultante:,.2f} |")
    
    # Resultado final
    estado = resultado.get('estado_operacion', 'N/A')
    accion = resultado.get('accion_recomendada', 'N/A')
    
    lines.append(f"| | | | |")
    lines.append(f"| **RESULTADO FINAL** | | | |")
    lines.append(f"| **Saldo Global Final** | **{saldo_global:,.2f}** | `Después de backdoor` | Saldo final |")
    lines.append(f"| Estado | {estado} | `Clasificación` | - |")
    lines.append(f"| Acción | {accion} | `Recomendación` | - |")
    
    return "\n".join(lines)

# --- CSS para alineación del header ---
st.markdown('''<style>
[data-testid="stHorizontalBlock"] { 
    align-items: center; 
}
</style>''', unsafe_allow_html=True)

# --- Header Estándar ---
col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
with col1:
    st.image(os.path.join(project_root, "static", "logo_geek.png"), width=200)
with col2:
    st.markdown("<h2 style='text-align: center;'>Módulo de Liquidación</h2>", unsafe_allow_html=True)
with col3:
    empty_col, logo_col = st.columns([2, 1])
    with logo_col:
        st.image(os.path.join(project_root, "static", "logo_inandes.png"), width=195)

# --- UI Views ---
def mostrar_busqueda_universal():
    st.header("Paso 1: Buscar Lote a Liquidar")
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
                        detalles_filtrados = [d for d in detalles_completos if d]
                        # Ordenar por número correlativo ascendente
                        detalles_ordenados = sorted(detalles_filtrados, key=lambda x: extraer_numero_correlativo(x.get('proposal_id', '')))
                        st.session_state.lote_encontrado_universal = detalles_ordenados
                        st.session_state.vista_actual_universal = 'liquidacion'
                        st.rerun()
                else:
                    st.warning("No se encontraron facturas para el identificador de lote proporcionado.")

def mostrar_liquidacion_universal():
    st.header("Paso 2: Configurar y Ejecutar Liquidación")
    if st.button("<- Volver a la búsqueda"):
        st.session_state.vista_actual_universal = 'busqueda'
        st.session_state.lote_encontrado_universal = []
        st.session_state.resultados_liquidacion_universal = None
        st.session_state.vouchers_universales = {} # Limpiar vouchers individuales
        st.session_state.voucher_global_liquidacion = None # Limpiar voucher global
        st.session_state.usar_voucher_unico_liquidacion = False # Resetear checkbox
        st.session_state.fechas_pago_individuales = {} # Limpiar fechas individuales
        st.session_state.previous_global_date = None # Resetear fecha previa
        st.rerun()

    # Inicializar fechas individuales si no existen (primera vez que se carga el lote)
    for factura in st.session_state.lote_encontrado_universal:
        proposal_id = factura.get('proposal_id')
        if proposal_id not in st.session_state.fechas_pago_individuales:
            st.session_state.fechas_pago_individuales[proposal_id] = st.session_state.global_liquidation_date_universal

    # Checkbox para controlar tipo de voucher (FUERA del form)
    st.checkbox(
        "APLICAR VOUCHER DE PAGO ÚNICO PARA TODO EL LOTE", 
        key="usar_voucher_unico_liquidacion",
        help="Si se marca, se subirá un solo voucher para todas las facturas. Si no, se subirá un voucher por factura."
    )

    with st.form(key="universal_liquidation_form"):
        st.subheader("Configuración Global de Liquidación")
        cols = st.columns(2)
        
        # Capturar la fecha global actual
        fecha_global_actual = cols[0].date_input("Fecha de Pago Global", value=st.session_state.global_liquidation_date_universal)
        st.session_state.global_backdoor_min_amount_universal = cols[1].number_input("Monto Máximo para Backdoor (S/)", value=st.session_state.global_backdoor_min_amount_universal, format="%.2f", help="El backdoor se activa cuando el saldo es menor a este monto")
        
        # Uploader global (habilitado solo si checkbox está marcado)
        st.session_state.voucher_global_liquidacion = st.file_uploader(
            "Subir Voucher de Pago Consolidado (PDF/Imagen)",
            type=["pdf", "png", "jpg", "jpeg"],
            key="voucher_global_uploader",
            disabled=not st.session_state.usar_voucher_unico_liquidacion,
            help="Voucher único que aplica a todas las facturas del lote"
        )
        
        # Detectar si la fecha global cambió y sincronizar automáticamente
        if st.session_state.previous_global_date is None:
            # Primera vez: establecer la fecha previa
            st.session_state.previous_global_date = fecha_global_actual
        elif fecha_global_actual != st.session_state.previous_global_date:
            # La fecha global cambió: sincronizar todas las fechas individuales
            for i, factura in enumerate(st.session_state.lote_encontrado_universal):
                proposal_id = factura.get('proposal_id', f'factura_{i}')
                st.session_state.fechas_pago_individuales[proposal_id] = fecha_global_actual
                # CRÍTICO: Actualizar también la key del widget para que se refleje visualmente
                st.session_state[f"fecha_{proposal_id}"] = fecha_global_actual
            
            st.session_state.previous_global_date = fecha_global_actual
        
        # Actualizar la fecha global en session_state
        st.session_state.global_liquidation_date_universal = fecha_global_actual
        
        # Botón opcional para sincronización manual (por homogeneidad de interfaz)
        if st.form_submit_button("🔄 Aplicar Fecha Global a Todas las Facturas", type="secondary"):
            # Sincronizar manualmente todas las fechas
            for i, factura in enumerate(st.session_state.lote_encontrado_universal):
                proposal_id = factura.get('proposal_id', f'factura_{i}')
                st.session_state.fechas_pago_individuales[proposal_id] = fecha_global_actual
                # CRÍTICO: Actualizar también la key del widget para que se refleje visualmente
                st.session_state[f"fecha_{proposal_id}"] = fecha_global_actual
            st.rerun()
        
        st.markdown("---")
        
        facturas_inputs = {}
        fechas_pago_inputs = {}  # Almacenar fechas de pago por factura
        
        for i, factura in enumerate(st.session_state.lote_encontrado_universal):
            proposal_id = factura.get('proposal_id', f'factura_{i}')
            with st.container(border=True):
                monto_neto = safe_decimal(factura.get('monto_neto_factura'))
                st.markdown(f"**Factura:** {parse_invoice_number(proposal_id)} | **Emisor:** {factura.get('emisor_nombre', 'N/A')} | **Monto Neto:** S/ {monto_neto:,.2f}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    facturas_inputs[proposal_id] = st.number_input(
                        "Monto Recibido", 
                        value=float(monto_neto), 
                        key=f"monto_{proposal_id}",
                        format="%.2f"
                    )
                with col2:
                    # Fecha de pago individual sincronizada con la fecha global
                    # CORRECCIÓN WARNING: Inicializar la key en session_state si no existe
                    key_fecha = f"fecha_{proposal_id}"
                    if key_fecha not in st.session_state:
                        st.session_state[key_fecha] = st.session_state.fechas_pago_individuales.get(proposal_id, fecha_global_actual)
                    
                    # Renderizar widget SIN pasar 'value' para evitar warning de conflicto
                    # Streamlit usará automáticamente el valor de session_state[key_fecha]
                    fechas_pago_inputs[proposal_id] = st.date_input(
                        "Fecha de Pago",
                        key=key_fecha
                    )
                    
                    # Actualizar el diccionario interno con el valor actual del widget (por si el usuario lo cambió manualmente)
                    st.session_state.fechas_pago_individuales[proposal_id] = st.session_state[key_fecha]
                with col3:
                    st.session_state.vouchers_universales[proposal_id] = st.file_uploader(
                        f"Voucher para Factura {parse_invoice_number(proposal_id)}",
                        type=["pdf", "png", "jpg", "jpeg"],
                        key=f"uploader_{proposal_id}",
                        disabled=st.session_state.usar_voucher_unico_liquidacion,
                        help="Voucher individual para esta factura (deshabilitado si se usa voucher único)"
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
                fecha_pago_factura = fechas_pago_inputs.get(proposal_id, st.session_state.global_liquidation_date_universal)  # Nuevo: usar fecha individual
                
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
                        "interes_compensatorio": float(safe_decimal(calculo_tasa.get('interes'))),  # ← CORREGIDO: interes está en calculo_tasa
                        "igv_interes": float(safe_decimal(calculo_tasa.get('igv_interes'))),  # ← CORREGIDO: igv_interes está en calculo_tasa
                        "tasa_interes_mensual": float(safe_decimal(factura.get('interes_mensual')) / 100),
                        "fecha_desembolso": parse_date_flexible(fecha_desembolso_str),
                        "fecha_vencimiento": parse_date_flexible(fecha_vencimiento_str),
                    }

                    # Obtener días mínimos de la factura (con fallback a 15)
                    dias_minimos = factura.get('dias_minimos_interes_individual', 15)

                    resultado = sistema.liquidar_operacion_con_back_door(
                        operacion=operacion,
                        fecha_pago=fecha_pago_factura,  # Cambiado: usar fecha individual en lugar de global
                        monto_pagado=monto_pagado,
                        monto_minimo=st.session_state.global_backdoor_min_amount_universal,
                        dias_minimos_interes=dias_minimos
                    )
                    resultados_finales.append(resultado)

                except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
                    st.error(f"Error procesando factura {parse_invoice_number(proposal_id)}: {e}")
            
            st.session_state.resultados_liquidacion_universal = resultados_finales
            st.success("Cálculo de liquidación universal completado.")

    if st.session_state.resultados_liquidacion_universal:
        st.markdown("---")
        st.header("Paso 3: Resultados de la Liquidación")

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

                # Tabla detallada de cálculos (similar a Operaciones)
                st.markdown("---")
                st.write("##### Desglose Detallado de la Liquidación")
                
                # Obtener factura original para datos adicionales
                proposal_id = resultado.get('id_operacion')
                factura_original = next((f for f in st.session_state.lote_encontrado_universal if f.get('proposal_id') == proposal_id), None)
                
                # Generar y mostrar tabla markdown
                tabla_md = generar_tabla_calculo_liquidacion(resultado, factura_original)
                st.markdown(tabla_md, unsafe_allow_html=True)
        
        
        # Botones de acción en columnas
        col_pdf, col_save = st.columns(2)
        
        with col_pdf:
            if st.button("📄 Bajar Perfil de Liquidación", type="secondary", use_container_width=True):
                with st.spinner("Generando PDF de liquidación..."):
                    try:
                        if st.session_state.resultados_liquidacion_universal:
                            # Generar PDF con los resultados de liquidación
                            pdf_bytes = generate_liquidacion_universal_pdf(
                                st.session_state.resultados_liquidacion_universal,
                                st.session_state.lote_encontrado_universal
                            )
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            output_filename = f"liquidacion_universal_{timestamp}.pdf"
                            
                            st.download_button(
                                label=f"⬇️ Descargar {output_filename}",
                                data=pdf_bytes,
                                file_name=output_filename,
                                mime="application/pdf",
                                use_container_width=True
                            )
                        else:
                            st.warning("No hay resultados de liquidación para generar el PDF.")
                    except Exception as e:
                        st.error(f"Error al generar el PDF: {e}")
        
        with col_save:
            if st.button("💾 Guardar Liquidaciones en Supabase", type="primary", use_container_width=True):
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

                            # Serializar resultado para JSON (convertir fechas a strings)
                            resultado_serializado = serialize_resultado_for_json(resultado)

                            db.add_liquidacion_evento(
                                liquidacion_resumen_id=resumen_id,
                                tipo_evento="Liquidación Universal",
                                fecha_evento=st.session_state.global_liquidation_date_universal,
                                monto_recibido=resultado['monto_pagado'],
                                dias_diferencia=resultado['dias_mora'],
                                resultado_json=resultado_serializado
                            )

                            db.update_liquidacion_resumen_saldo(resumen_id, resultado['saldo_global'])
                            db.update_proposal_status(proposal_id, resultado['estado_operacion'])

                        st.success("¡Liquidaciones guardadas exitosamente en Supabase!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Ocurrió un error al guardar en la base de datos: {e}")

# --- Main App Logic ---
st.title("💰 Módulo de Liquidación")

if st.session_state.vista_actual_universal == 'busqueda':
    mostrar_busqueda_universal()
elif st.session_state.vista_actual_universal == 'liquidacion':
    mostrar_liquidacion_universal()

# --- Diagrama de Flujo de los 6 Casos ---
st.markdown("---")
st.markdown("### 📊 Diagrama de Flujo: Los 6 Casos de Liquidación")

from streamlit_mermaid import st_mermaid

mermaid_code = """
graph TD
    Start([Inicio: Liquidación]) --> CalcDeltas[Calcular Deltas<br/>ΔInt = Devengado - Original<br/>ΔCap = Capital - Pagado<br/>Saldo = ΔInt + ΔCap]
    
    CalcDeltas --> CheckSaldo{Saldo Global}
    
    CheckSaldo -->|Saldo < 0| SaldoNeg[Saldo Negativo<br/>Cliente pagó de más]
    CheckSaldo -->|Saldo > 0| SaldoPos[Saldo Positivo<br/>Cliente debe dinero]
    
    SaldoNeg --> CheckNeg1{ΔInt < 0 AND<br/>ΔCap < 0?}
    CheckNeg1 -->|Sí| Caso1[CASO 1: LIQUIDADO<br/>Devolver todo el exceso]
    CheckNeg1 -->|No| CheckNeg2{ΔInt > 0 AND<br/>ΔCap < 0?}
    CheckNeg2 -->|Sí| Caso5[CASO 5: LIQUIDADO<br/>Facturar Int + Devolver Cap]
    CheckNeg2 -->|No| Caso6[CASO 6: LIQUIDADO<br/>NC + Devolver saldo]
    
    SaldoPos --> CheckPos1{ΔInt < 0 AND<br/>ΔCap > 0?}
    CheckPos1 -->|Sí| Caso2[CASO 2: EN PROCESO<br/>NC + Calendario]
    CheckPos1 -->|No| CheckPos2{ΔInt > 0 AND<br/>ΔCap > 0?}
    CheckPos2 -->|Sí| Caso3[CASO 3: EN PROCESO<br/>Facturar + Calendario]
    CheckPos2 -->|No| Caso4[CASO 4: EN PROCESO<br/>Facturar Int + Evaluar]
    
    Caso1 --> End([Fin])
    Caso2 --> End
    Caso3 --> End
    Caso4 --> End
    Caso5 --> End
    Caso6 --> End
    
    style Caso1 fill:#10b981,stroke:#059669,color:#fff
    style Caso5 fill:#06b6d4,stroke:#0891b2,color:#fff
    style Caso6 fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style Caso2 fill:#f59e0b,stroke:#d97706,color:#fff
    style Caso3 fill:#ef4444,stroke:#dc2626,color:#fff
    style Caso4 fill:#f97316,stroke:#ea580c,color:#fff
    style SaldoNeg fill:#fef3c7,stroke:#f59e0b
    style SaldoPos fill:#fee2e2,stroke:#ef4444
"""

st_mermaid(mermaid_code, height=800)

st.markdown("""
**Leyenda:**
- 🟢 **Verde/Cyan/Púrpura**: Casos LIQUIDADOS (saldo negativo)
- 🟠 **Naranja/Rojo**: Casos EN PROCESO (saldo positivo)
- **ΔInt**: Delta de Intereses
- **ΔCap**: Delta de Capital
""")
