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

st.title("🧪 Testing Liquidación Universal")
st.markdown("**Auditoría Visual: Tabla Día a Día con Interés Compuesto**")
st.markdown("---")

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
    fecha_pago_real: date
) -> pd.DataFrame:
    """
    Genera tabla día a día de devengamiento con interés compuesto
    """
    # Determinar rango de fechas
    fecha_inicio = fecha_desembolso
    fecha_fin = max(fecha_pago_real, fecha_vencimiento) + timedelta(days=5)
    
    datos = []
    fecha_actual = fecha_inicio
    dia_num = 0
    
    while fecha_actual <= fecha_fin:
        dias_desde_desembolso = (fecha_actual - fecha_desembolso).days
        
        # Calcular intereses compensatorios acumulados
        interes_comp_acum = calcular_interes_compuesto_diario(capital, tasa_comp, dias_desde_desembolso)
        
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
                    st.session_state.facturas_lote = propuestas
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
            visual_igv_comp = fila_pago.iloc[0]['IGV Comp']
            visual_interes_mora = fila_pago.iloc[0]['Int.Mora Acum']
            visual_igv_mora = fila_pago.iloc[0]['IGV Mora']
        else:
            visual_interes_comp = 0
            visual_igv_comp = 0
            visual_interes_mora = 0
            visual_igv_mora = 0
        
        # Mostrar header
        st.subheader(f"📄 {propuesta.get('numero_factura', 'N/A')} - {propuesta.get('emisor_nombre', 'N/A')}")
        
        # Métricas clave
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Capital", f"S/ {capital:,.2f}")
        with col2:
            st.metric("Tasa Comp", f"{tasa_comp*100:.2f}%")
        with col3:
            st.metric("Tasa Mora", f"{tasa_mora*100:.2f}%")
        with col4:
            dias_totales = (fecha_pago_real - fecha_desembolso).days
            st.metric("Días Totales", f"{dias_totales}")
        
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
        df_display = df_devengamiento[['Día', 'Fecha', 'Int.Comp Acum', 'IGV Comp', 'Int.Mora Acum', 'IGV Mora']].copy()
        
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
        
        # Interés Compensatorio
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("Interés Compensatorio")
        with col2:
            st.markdown(f"S/ {visual_interes_comp:,.2f}")
        with col3:
            st.markdown(f"S/ {sistema['interes_devengado']:,.2f}")
            diff = abs(visual_interes_comp - sistema['interes_devengado'])
            if diff < 0.01:
                st.success("✅")
            else:
                st.error(f"❌ Δ {diff:,.2f}")
        
        # IGV Compensatorio
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("IGV Compensatorio")
        with col2:
            st.markdown(f"S/ {visual_igv_comp:,.2f}")
        with col3:
            st.markdown(f"S/ {sistema['igv_devengado']:,.2f}")
            diff = abs(visual_igv_comp - sistema['igv_devengado'])
            if diff < 0.01:
                st.success("✅")
            else:
                st.error(f"❌ Δ {diff:,.2f}")
        
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
        
        # Resumen
        checks = [
            abs(visual_interes_comp - sistema['interes_devengado']) < 0.01,
            abs(visual_igv_comp - sistema['igv_devengado']) < 0.01,
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
