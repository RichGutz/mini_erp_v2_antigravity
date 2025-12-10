"""
Módulo de Testing Liquidación Universal - VERSIÓN FINAL
Tabla día a día con interés compuesto y comparación VISUAL vs SISTEMA
"""

import streamlit as st
import pandas as pd
import datetime
from datetime import date, timedelta
import sys
import os
import json

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.factoring_system import SistemaFactoringCompleto
from src.data.supabase_repository import (
    get_proposal_details_by_id,
    get_liquidacion_eventos,
    get_liquidated_proposals_by_lote
)

# ============================================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Testing Liquidación Universal",
    page_icon="🧪",
    layout="wide"
)

# --- Header ---
from src.ui.header import render_header
render_header("Testing Liquidación Universal")

# ============================================================================
# FUNCIONES DE CÁLCULO CON INTERÉS COMPUESTO
# ============================================================================

def calcular_interes_compuesto_diario(capital: float, tasa_mensual: float, dias: int) -> float:
    """
    Calcula interés compuesto usando la fórmula del Excel:
    (1 + tasa_mensual/30)^dias - 1) × capital
    """
    if dias <= 0:
        return 0.0
    return ((1 + tasa_mensual / 30) ** dias - 1) * capital


def generar_tabla_devengamiento(
    capital: float,
    tasa_comp: float,
    tasa_mora: float,
    fecha_desembolso: date,
    fecha_vencimiento: date,
    fecha_pago_real: date,
    dias_minimos: int = 15
) -> pd.DataFrame:
    """
    Genera tabla día a día de devengamiento con interés compuesto
    """
    # Determinar rango de fechas
    fecha_inicio = fecha_desembolso
    fecha_fin = max(fecha_pago_real, fecha_vencimiento) + timedelta(days=5)
    
    # Calcular intereses mínimos (constante para todos los días)
    interes_minimo = calcular_interes_compuesto_diario(capital, tasa_comp, dias_minimos)
    igv_minimo = interes_minimo * 0.18
    
    datos = []
    fecha_actual = fecha_inicio
    dia_num = 0
    
    while fecha_actual <= fecha_fin:
        dias_desde_desembolso = (fecha_actual - fecha_desembolso).days
        
        # Calcular intereses compensatorios acumulados (con días reales)
        interes_comp_acum = calcular_interes_compuesto_diario(capital, tasa_comp, dias_desde_desembolso)
        
        # Intereses devengados = MAX(reales, mínimos)
        interes_devengado = max(interes_comp_acum, interes_minimo)
        igv_devengado = interes_devengado * 0.18
        
        # Calcular intereses moratorios acumulados (solo después de vencimiento)
        if fecha_actual > fecha_vencimiento:
            dias_mora = (fecha_actual - fecha_vencimiento).days
            interes_mora_acum = calcular_interes_compuesto_diario(capital, tasa_mora, dias_mora)
        else:
            dias_mora = 0
            interes_mora_acum = 0.0
        
        # Determinar zona para colores
        if fecha_actual < fecha_vencimiento:
            zona = "Normal"
        elif fecha_actual == fecha_vencimiento:
            zona = "Vencimiento"
        elif fecha_actual == fecha_pago_real:
            zona = "Pago Real"
        else:
            zona = "Mora"
        
        datos.append({
            'Día': dia_num,
            'Fecha': fecha_actual.strftime('%Y-%m-%d'),
            'Int.Comp Acum': round(interes_comp_acum, 2),
            'IGV Comp': round(interes_comp_acum * 0.18, 2),
            'Int.Mínimo (15d)': round(interes_minimo, 2),
            'Int.Devengado': round(interes_devengado, 2),
            'IGV Devengado': round(igv_devengado, 2),
            'Int.Mora Acum': round(interes_mora_acum, 2),
            'IGV Mora': round(interes_mora_acum * 0.18, 2),
            'Zona': zona,
            'Es Pago Real': (fecha_actual == fecha_pago_real)
        })
        
        fecha_actual += timedelta(days=1)
        dia_num += 1
    
    return pd.DataFrame(datos)


def extraer_datos_sistema(ultimo_evento: dict) -> dict:
    """
    Extrae los datos de la liquidación del SISTEMA
    """
    resultado = json.loads(ultimo_evento.get('resultado_json', '{}'))
    
    # Extraer número de caso del estado
    estado = resultado.get('estado_operacion', 'N/A')
    caso_num = "No clasificado"
    for i in range(1, 7):
        if f"Caso {i}" in estado:
            caso_num = str(i)
            break
    
    return {
        'interes_devengado': resultado.get('interes_devengado', 0.0),
        'igv_devengado': resultado.get('igv_interes_devengado', 0.0),
        'interes_moratorio': resultado.get('interes_moratorio', 0.0),
        'igv_moratorio': resultado.get('igv_moratorio', 0.0),
        'delta_compensatorios': resultado.get('delta_intereses', 0.0),
        'delta_igv': resultado.get('delta_igv_intereses', 0.0),
        'delta_capital': resultado.get('delta_capital', 0.0),
        'saldo_global': resultado.get('saldo_global', 0.0),
        'caso': caso_num,
        'dias_transcurridos': resultado.get('dias_transcurridos', 0),
        'dias_mora': resultado.get('dias_mora', 0)
    }


def parse_fecha(fecha_str):
    """Parsea fechas en múltiples formatos"""
    if not fecha_str:
        return date.today()
    try:
        return datetime.datetime.fromisoformat(fecha_str.replace('Z', '+00:00')).date()
    except:
        try:
            return datetime.datetime.strptime(fecha_str.split('T')[0], '%Y-%m-%d').date()
        except:
            return date.today()


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


# ============================================================================
# INICIALIZACIÓN DE SESSION STATE
# ============================================================================

if 'facturas_lote' not in st.session_state:
    st.session_state.facturas_lote = []

if 'facturas_seleccionadas' not in st.session_state:
    st.session_state.facturas_seleccionadas = []

# ============================================================================
# SECCIÓN 1: INPUT DE LOTE
# ============================================================================

st.header("1️⃣ Cargar Lote")

col1, col2 = st.columns([3, 1])

with col1:
    lote_id = st.text_input(
        "ID de Lote",
        placeholder="Ejemplo: LOTE-20251206-001",
        key="input_lote_id"
    )

with col2:
    st.markdown("")
    st.markdown("")
    if st.button("🔍 Cargar Lote", type="primary", use_container_width=True):
        if lote_id:
            with st.spinner("Buscando facturas liquidadas..."):
                propuestas = get_liquidated_proposals_by_lote(lote_id)
                
                if propuestas:
                    # Ordenar facturas por número correlativo ascendente
                    propuestas_ordenadas = sorted(propuestas, key=lambda x: extraer_numero_correlativo(x.get('proposal_id', '')))
                    st.session_state.facturas_lote = propuestas_ordenadas
                    st.session_state.facturas_seleccionadas = []
                    st.success(f"✅ Se encontraron {len(propuestas)} facturas liquidadas")
                    st.rerun()
                else:
                    st.warning("⚠️ No se encontraron facturas liquidadas en este lote")
                    st.session_state.facturas_lote = []
        else:
            st.warning("⚠️ Ingresa un ID de lote")

# ============================================================================
# SECCIÓN 2: SELECCIÓN DE FACTURAS
# ============================================================================

if st.session_state.facturas_lote:
    st.markdown("---")
    st.header("2️⃣ Seleccionar Facturas a Auditar")
    
    st.markdown("**Facturas disponibles:**")
    
    for idx, factura in enumerate(st.session_state.facturas_lote):
        col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
        
        with col1:
            seleccionada = st.checkbox(
                "",
                key=f"check_{idx}",
                value=factura['proposal_id'] in st.session_state.facturas_seleccionadas
            )
            
            if seleccionada and factura['proposal_id'] not in st.session_state.facturas_seleccionadas:
                st.session_state.facturas_seleccionadas.append(factura['proposal_id'])
            elif not seleccionada and factura['proposal_id'] in st.session_state.facturas_seleccionadas:
                st.session_state.facturas_seleccionadas.remove(factura['proposal_id'])
        
        with col2:
            st.markdown(f"**{factura.get('numero_factura', 'N/A')}**")
        
        with col3:
            st.markdown(f"{factura.get('emisor_nombre', 'N/A')}")
        
        with col4:
            monto = factura.get('monto_neto_factura', 0)
            st.markdown(f"S/ {monto:,.2f}")
    
    st.markdown("")
    
    if st.session_state.facturas_seleccionadas:
        st.info(f"📌 {len(st.session_state.facturas_seleccionadas)} factura(s) seleccionada(s)")

# ============================================================================
# SECCIÓN 3: AUDITORÍA CON TABLA DÍA A DÍA
# ============================================================================

if st.session_state.facturas_seleccionadas:
    st.markdown("---")
    st.header("3️⃣ Auditoría: Tabla Día a Día")
    
    for proposal_id in st.session_state.facturas_seleccionadas:
        # Obtener datos
        propuesta = get_proposal_details_by_id(proposal_id)
        eventos = get_liquidacion_eventos(proposal_id)
        
        if not propuesta or not eventos:
            st.error(f"❌ No se pudieron cargar los datos de {proposal_id}")
            continue
        
        ultimo_evento = eventos[-1]
        
        # Extraer datos de la propuesta
        recalc_data = json.loads(propuesta.get('recalculate_result_json', '{}'))
        capital = recalc_data.get('calculo_con_tasa_encontrada', {}).get('capital', 0.0)
        
        # IMPORTANTE: Las tasas vienen en porcentaje (2.0 = 2%), convertir a decimal
        tasa_comp = propuesta.get('interes_mensual', 2.0) / 100  # 2.0% -> 0.02
        tasa_mora = propuesta.get('interes_moratorio', 3.0) / 100  # 3.0% -> 0.03
        
        fecha_desembolso = parse_fecha(propuesta.get('fecha_desembolso_factoring'))
        fecha_vencimiento = parse_fecha(propuesta.get('fecha_pago_calculada'))
        fecha_pago_real = parse_fecha(ultimo_evento.get('fecha_evento'))
        
        # Generar tabla día a día
        df_devengamiento = generar_tabla_devengamiento(
            capital, tasa_comp, tasa_mora,
            fecha_desembolso, fecha_vencimiento, fecha_pago_real
        )
        
        # Extraer datos del sistema
        sistema = extraer_datos_sistema(ultimo_evento)
        
        # Obtener valores VISUAL del día del pago real
        fila_pago = df_devengamiento[df_devengamiento['Es Pago Real'] == True]
        if not fila_pago.empty:
            visual_interes_comp = fila_pago.iloc[0]['Int.Comp Acum']
            visual_interes_devengado = fila_pago.iloc[0]['Int.Devengado']
            visual_igv_devengado = fila_pago.iloc[0]['IGV Devengado']
            visual_interes_mora = fila_pago.iloc[0]['Int.Mora Acum']
            visual_igv_mora = fila_pago.iloc[0]['IGV Mora']
            visual_interes_minimo = fila_pago.iloc[0]['Int.Mínimo (15d)']
        else:
            visual_interes_comp = 0
            visual_interes_devengado = 0
            visual_igv_devengado = 0
            visual_interes_mora = 0
            visual_igv_mora = 0
            visual_interes_minimo = 0
        
        # Días reales
        dias_reales = (fecha_pago_real - fecha_desembolso).days
        
        # Mostrar header
        st.subheader(f"📄 {propuesta.get('numero_factura', 'N/A')} - {propuesta.get('emisor_nombre', 'N/A')}")
        
        # Métricas clave
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Capital", f"S/ {capital:,.2f}")
        with col2:
            st.metric("Tasa Comp", f"{tasa_comp*100:.2f}%")
        with col3:
            st.metric("Tasa Mora", f"{tasa_mora*100:.2f}%")
        with col4:
            dias_reales = (fecha_pago_real - fecha_desembolso).days
            st.metric("Días Reales", f"{dias_reales}")
        with col5:
            dias_sistema = sistema['dias_transcurridos']
            st.metric("Días Sistema", f"{dias_sistema}", 
                     delta=f"Mínimo aplicado" if dias_sistema > dias_reales else "Sin mínimo")
        
        st.markdown("---")
        
        # Tabla día a día con colores
        st.markdown("#### 📅 Tabla de Devengamiento Día a Día (Interés Compuesto)")
        
        def aplicar_colores(row):
            if row['Es Pago Real']:
                return ['background-color: #FFD700; font-weight: bold'] * len(row)
            elif row['Zona'] == 'Normal':
                return ['background-color: #90EE90'] * len(row)
            elif row['Zona'] == 'Vencimiento':
                return ['background-color: #FFFFE0; font-weight: bold'] * len(row)
            elif row['Zona'] == 'Mora':
                return ['background-color: #FFB6C1'] * len(row)
            else:
                return [''] * len(row)
        
        # Mostrar solo columnas relevantes
        df_display = df_devengamiento[['Día', 'Fecha', 'Int.Comp Acum', 'IGV Comp', 'Int.Mínimo (15d)', 'Int.Devengado', 'IGV Devengado', 'Int.Mora Acum', 'IGV Mora']].copy()
        
        st.dataframe(
            df_devengamiento.style.apply(aplicar_colores, axis=1),
            use_container_width=True,
            height=400
        )
        
        st.markdown("""
        **Leyenda:**
        - 🟢 Verde: Período normal
        - 🟡 Amarillo: Fecha de vencimiento
        - 🔴 Rojo: Período de mora
        - 🟠 Dorado: Fecha real de pago
        """)
        
        st.markdown("---")
        
        # Comparación VISUAL vs SISTEMA
        st.markdown("#### 📊 Comparación: VISUAL vs SISTEMA")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Concepto**")
        with col2:
            st.markdown("**VISUAL (Compuesto)**")
        with col3:
            st.markdown("**SISTEMA**")
        
        st.markdown("---")
        
        # SECCIÓN: DÍAS
        st.markdown("##### DÍAS")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("Días Reales (Desemb → Pago)")
        with col2:
            st.markdown(f"{dias_reales} días")
        with col3:
            st.markdown(f"{sistema['dias_transcurridos']} días")
            if dias_reales == sistema['dias_transcurridos']:
                st.success("✅")
            else:
                st.error(f"❌ Δ {abs(dias_reales - sistema['dias_transcurridos'])} días")
        
        st.markdown("")
        
        # SECCIÓN: INTERESES COMPENSATORIOS
        st.markdown("##### INTERESES COMPENSATORIOS")
        
        # Interés con días reales
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"Int. Comp ({dias_reales} días reales)")
        with col2:
            st.markdown(f"S/ {visual_interes_comp:,.2f}")
        with col3:
            st.markdown("-")
        
        # Interés mínimo (15 días)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Int. Comp Mínimo (15 días)**")
        with col2:
            st.markdown(f"**S/ {visual_interes_minimo:,.2f}**")
        with col3:
            st.markdown("-")
        
        # Interés devengado final (máximo)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Int. Devengado Final (MAX)**")
        with col2:
            st.markdown(f"**S/ {visual_interes_devengado:,.2f}**")
            if visual_interes_devengado == visual_interes_minimo:
                st.caption("(Se aplicó mínimo)")
            else:
                st.caption("(Se usó real)")
        with col3:
            st.markdown(f"S/ {sistema['interes_devengado']:,.2f}")
            diff = abs(visual_interes_devengado - sistema['interes_devengado'])
            if diff < 0.01:
                st.success("✅")
            else:
                st.error(f"❌ Δ {diff:,.2f}")
        
        # IGV Compensatorio
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("IGV Compensatorio")
        with col2:
            st.markdown(f"S/ {visual_igv_devengado:,.2f}")
        with col3:
            st.markdown(f"S/ {sistema['igv_devengado']:,.2f}")
            diff = abs(visual_igv_devengado - sistema['igv_devengado'])
            if diff < 0.01:
                st.success("✅")
            else:
                st.error(f"❌ Δ {diff:,.2f}")
        
        st.markdown("")
        
        # Interés Moratorio
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("Interés Moratorio")
        with col2:
            st.markdown(f"S/ {visual_interes_mora:,.2f}")
        with col3:
            st.markdown(f"S/ {sistema['interes_moratorio']:,.2f}")
            diff = abs(visual_interes_mora - sistema['interes_moratorio'])
            if diff < 0.01:
                st.success("✅")
            else:
                st.error(f"❌ Δ {diff:,.2f}")
        
        # IGV Moratorio
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("IGV Moratorio")
        with col2:
            st.markdown(f"S/ {visual_igv_mora:,.2f}")
        with col3:
            st.markdown(f"S/ {sistema['igv_moratorio']:,.2f}")
            diff = abs(visual_igv_mora - sistema['igv_moratorio'])
            if diff < 0.01:
                st.success("✅")
            else:
                st.error(f"❌ Δ {diff:,.2f}")
        
        
        st.markdown("")
        
        # NUEVA SECCIÓN: RESUMEN DE LIQUIDACIÓN
        st.markdown("##### 💰 RESUMEN DE LIQUIDACIÓN")
        st.markdown("**Componentes del Sistema:**")
        
        # Obtener datos del sistema desde el resultado_json del evento
        resultado_sistema = json.loads(ultimo_evento.get('resultado_json', '{}'))
        monto_pagado = resultado_sistema.get('monto_pagado', 0)
        capital_operacion = resultado_sistema.get('capital_operacion', 0)
        delta_capital = sistema.get('delta_capital', 0)
        delta_compensatorios = sistema.get('delta_compensatorios', 0)
        delta_igv = sistema.get('delta_igv', 0)
        interes_moratorio = sistema.get('interes_moratorio', 0)
        igv_moratorio = sistema.get('igv_moratorio', 0)
        saldo_global = sistema.get('saldo_global', 0)
        
        # Tabla de resumen
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**💵 PAGOS Y CAPITAL**")
        with col2:
            st.markdown("**Monto (S/)**")
        with col3:
            st.markdown("")
        
        st.markdown("---")
        
        # Monto recibido
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("💰 Monto Recibido")
        with col2:
            st.markdown(f"S/ {monto_pagado:,.2f}")
        with col3:
            st.markdown("(Pago del cliente)")
        
        # Capital operación
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("📊 Capital Operación")
        with col2:
            st.markdown(f"S/ {capital_operacion:,.2f}")
        with col3:
            st.markdown("(Capital a recuperar)")
        
        # Delta capital
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**📉 Delta Capital**")
        with col2:
            delta_cap_color = "🟢" if delta_capital <= 0 else "🔴"
            st.markdown(f"**{delta_cap_color} S/ {delta_capital:,.2f}**")
        with col3:
            if delta_capital > 0:
                st.markdown("(Capital pendiente)")
            elif delta_capital < 0:
                st.markdown("(Sobrepago de capital)")
            else:
                st.markdown("(Capital liquidado)")
        
        st.markdown("")
        
        # Intereses
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**📈 INTERESES**")
        with col2:
            st.markdown("")
        with col3:
            st.markdown("")
        
        st.markdown("---")
        
        # Delta compensatorios
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("Δ Intereses Compensatorios")
        with col2:
            delta_int_color = "🟢" if delta_compensatorios <= 0 else "🔴"
            st.markdown(f"{delta_int_color} S/ {delta_compensatorios:,.2f}")
        with col3:
            if delta_compensatorios > 0:
                st.markdown("(A facturar)")
            elif delta_compensatorios < 0:
                st.markdown("(Nota de crédito)")
            else:
                st.markdown("(Sin diferencia)")
        
        # Delta IGV
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("Δ IGV Intereses")
        with col2:
            delta_igv_color = "🟢" if delta_igv <= 0 else "🔴"
            st.markdown(f"{delta_igv_color} S/ {delta_igv:,.2f}")
        with col3:
            if delta_igv > 0:
                st.markdown("(A facturar)")
            elif delta_igv < 0:
                st.markdown("(Nota de crédito)")
            else:
                st.markdown("(Sin diferencia)")
        
        # Intereses moratorios (si aplica)
        if interes_moratorio > 0 or igv_moratorio > 0:
            st.markdown("")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("⚠️ Interés Moratorio")
            with col2:
                st.markdown(f"🔴 S/ {interes_moratorio:,.2f}")
            with col3:
                st.markdown("(A facturar)")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("⚠️ IGV Moratorio")
            with col2:
                st.markdown(f"🔴 S/ {igv_moratorio:,.2f}")
            with col3:
                st.markdown("(A facturar)")
        
        st.markdown("")
        st.markdown("---")
        
        # Saldo global final
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**💵 SALDO GLOBAL FINAL**")
        with col2:
            if saldo_global > 0:
                st.markdown(f"**🔴 S/ {saldo_global:,.2f}**")
            elif saldo_global < 0:
                st.markdown(f"**🟢 S/ {saldo_global:,.2f}**")
            else:
                st.markdown(f"**✅ S/ {saldo_global:,.2f}**")
        with col3:
            if saldo_global > 0:
                st.markdown("**(Cliente debe)**")
            elif saldo_global < 0:
                st.markdown("**(A devolver)**")
            else:
                st.markdown("**(Liquidado)**")
        
        st.markdown("")
        
        # Resumen de validación
        checks = [
            abs(visual_interes_devengado - sistema['interes_devengado']) < 0.01,
            abs(visual_igv_devengado - sistema['igv_devengado']) < 0.01,
            abs(visual_interes_mora - sistema['interes_moratorio']) < 0.01,
            abs(visual_igv_mora - sistema['igv_moratorio']) < 0.01
        ]
        
        total_errors = sum(1 for check in checks if not check)
        
        if total_errors == 0:
            st.success("✅ **AUDITORÍA EXITOSA** - Los cálculos con interés compuesto coinciden con el sistema")
        else:
            st.error(f"❌ **DISCREPANCIAS DETECTADAS** - {total_errors} diferencia(s). El sistema probablemente usa interés simple.")
        
        st.markdown("---")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption("🧪 Módulo de Testing Liquidación Universal | Interés Compuesto")
st.caption("Fórmula: (1 + tasa/30)^días - 1) × capital")
