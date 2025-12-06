"""
Módulo de Testing Liquidación Universal - REFACTORIZADO
Auditoría visual de liquidaciones: SISTEMA vs VISUAL
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
st.markdown("**Auditoría Visual: SISTEMA vs CÁLCULO INDEPENDIENTE**")
st.markdown("---")

# ============================================================================
# FUNCIONES DE CÁLCULO
# ============================================================================

def calcular_liquidacion_visual(propuesta: dict, ultimo_evento: dict) -> dict:
    """
    Calcula la liquidación de forma independiente (VISUAL)
    """
    sistema = SistemaFactoringCompleto()
    
    # Parsear datos
    recalc_data = json.loads(propuesta.get('recalculate_result_json', '{}'))
    capital = recalc_data.get('calculo_con_tasa_encontrada', {}).get('capital', 0.0)
    interes_original = recalc_data.get('desglose_final_detallado', {}).get('interes', {}).get('monto', 0.0)
    igv_interes_original = recalc_data.get('calculo_con_tasa_encontrada', {}).get('igv_interes', 0.0)
    
    tasa_comp = propuesta.get('interes_mensual', 0.02)
    tasa_mora = propuesta.get('interes_moratorio', 0.03)
    
    # Parsear fechas (pueden venir con o sin hora)
    def parse_fecha(fecha_str):
        if not fecha_str:
            return date.today()
        # Intentar con timestamp completo primero
        try:
            return datetime.datetime.fromisoformat(fecha_str.replace('Z', '+00:00')).date()
        except:
            # Intentar solo fecha
            try:
                return datetime.datetime.strptime(fecha_str.split('T')[0], '%Y-%m-%d').date()
            except:
                return date.today()
    
    fecha_desembolso = parse_fecha(propuesta.get('fecha_desembolso_factoring'))
    fecha_pago_teorica = parse_fecha(propuesta.get('fecha_pago_calculada'))
    fecha_pago_real = parse_fecha(ultimo_evento.get('fecha_evento'))
    monto_pagado = ultimo_evento.get('monto_recibido', 0.0)
    
    # Calcular días transcurridos (desde desembolso hasta pago real)
    dias_transcurridos = (fecha_pago_real - fecha_desembolso).days
    
    # IMPORTANTE: Aplicar regla de días mínimos (igual que el sistema)
    # El sistema usa max(dias_transcurridos, 15) por defecto
    dias_minimos = 15
    dias_para_interes = max(dias_transcurridos, dias_minimos)
    
    # Calcular días de mora (desde vencimiento hasta pago real)
    dias_mora = max(0, (fecha_pago_real - fecha_pago_teorica).days)
    
    # Calcular intereses devengados (usando días_para_interes, NO dias_transcurridos)
    interes_devengado = sistema._calcular_intereses_compensatorios(capital, tasa_comp, dias_para_interes)
    igv_devengado = interes_devengado * 0.18
    
    # Calcular moratorios
    if dias_mora > 0:
        interes_moratorio = sistema._calcular_intereses_moratorios(capital, dias_mora)
        igv_moratorio = interes_moratorio * 0.18
    else:
        interes_moratorio = 0.0
        igv_moratorio = 0.0
    
    # Calcular deltas
    delta_compensatorios = interes_devengado - interes_original
    delta_igv = igv_devengado - igv_interes_original
    delta_capital = capital - monto_pagado
    
    saldo_global = delta_compensatorios + delta_igv + interes_moratorio + igv_moratorio + delta_capital
    
    # Clasificar caso
    estado, accion = sistema._clasificar_caso_liquidacion(delta_compensatorios, delta_capital, saldo_global)
    
    # Extraer número de caso
    caso_num = "No clasificado"
    for i in range(1, 7):
        if f"Caso {i}" in estado:
            caso_num = str(i)
            break
    
    return {
        'capital': capital,
        'dias_transcurridos': dias_para_interes,  # Usar días_para_interes (con mínimo aplicado)
        'dias_mora': dias_mora,
        'interes_devengado': interes_devengado,
        'igv_devengado': igv_devengado,
        'interes_moratorio': interes_moratorio,
        'igv_moratorio': igv_moratorio,
        'delta_compensatorios': delta_compensatorios,
        'delta_igv': delta_igv,
        'delta_capital': delta_capital,
        'saldo_global': saldo_global,
        'caso': caso_num,
        'estado': estado
    }


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
        'capital': resultado.get('capital_operacion', 0.0),
        'dias_transcurridos': resultado.get('dias_transcurridos', 0),
        'dias_mora': resultado.get('dias_mora', 0),
        'interes_devengado': resultado.get('interes_devengado', 0.0),
        'igv_devengado': resultado.get('igv_interes_devengado', 0.0),
        'interes_moratorio': resultado.get('interes_moratorio', 0.0),
        'igv_moratorio': resultado.get('igv_moratorio', 0.0),
        'delta_compensatorios': resultado.get('delta_intereses', 0.0),
        'delta_igv': resultado.get('delta_igv_intereses', 0.0),
        'delta_capital': resultado.get('delta_capital', 0.0),
        'saldo_global': resultado.get('saldo_global', 0.0),
        'caso': caso_num,
        'estado': estado
    }


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
    st.markdown("")  # Espaciado
    st.markdown("")  # Espaciado
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
    
    # Crear tabla de selección
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
# SECCIÓN 3: AUDITORÍA
# ============================================================================

if st.session_state.facturas_seleccionadas:
    st.markdown("---")
    st.header("3️⃣ Auditoría: VISUAL vs SISTEMA")
    
    for proposal_id in st.session_state.facturas_seleccionadas:
        # Obtener datos
        propuesta = get_proposal_details_by_id(proposal_id)
        eventos = get_liquidacion_eventos(proposal_id)
        
        if not propuesta or not eventos:
            st.error(f"❌ No se pudieron cargar los datos de {proposal_id}")
            continue
        
        ultimo_evento = eventos[-1]
        
        # Calcular VISUAL y extraer SISTEMA
        visual = calcular_liquidacion_visual(propuesta, ultimo_evento)
        sistema = extraer_datos_sistema(ultimo_evento)
        
        # Mostrar comparación con estructura similar al módulo de liquidaciones
        st.subheader(f"📄 {propuesta.get('numero_factura', 'N/A')} - {propuesta.get('emisor_nombre', 'N/A')}")
        
        # Crear tabla comparativa con secciones
        st.markdown("#### 📊 Comparación: VISUAL vs SISTEMA")
        
        # SECCIÓN 1: DATOS DE LA OPERACIÓN
        st.markdown("##### DATOS DE LA OPERACIÓN")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Concepto**")
        with col2:
            st.markdown("**VISUAL**")
        with col3:
            st.markdown("**SISTEMA**")
        
        st.markdown("---")
        
        # Capital
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("Capital Operación")
        with col2:
            st.markdown(f"S/ {visual['capital']:,.2f}")
        with col3:
            st.markdown(f"S/ {sistema['capital']:,.2f}")
            if abs(visual['capital'] - sistema['capital']) < 0.01:
                st.success("✅")
            else:
                st.error(f"❌ Δ {abs(visual['capital'] - sistema['capital']):,.2f}")
        
        st.markdown("")
        
        # SECCIÓN 2: PERÍODOS
        st.markdown("##### PERÍODOS")
        
        # Días Transcurridos
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("Días Transcurridos")
        with col2:
            st.markdown(f"{visual['dias_transcurridos']} días")
        with col3:
            st.markdown(f"{sistema['dias_transcurridos']} días")
            if visual['dias_transcurridos'] == sistema['dias_transcurridos']:
                st.success("✅")
            else:
                st.error(f"❌ Δ {abs(visual['dias_transcurridos'] - sistema['dias_transcurridos'])} días")
        
        # Días de Mora
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("Días de Mora")
        with col2:
            st.markdown(f"{visual['dias_mora']} días")
        with col3:
            st.markdown(f"{sistema['dias_mora']} días")
            if visual['dias_mora'] == sistema['dias_mora']:
                st.success("✅")
            else:
                st.error(f"❌ Δ {abs(visual['dias_mora'] - sistema['dias_mora'])} días")
        
        st.markdown("")
        
        # SECCIÓN 3: COMPARACIÓN DEVENGADO VS FACTURADO
        st.markdown("##### COMPARACIÓN: DEVENGADO VS FACTURADO")
        
        # Interés Devengado
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Interés Compensatorio Devengado**")
        with col2:
            st.markdown(f"S/ {visual['interes_devengado']:,.2f}")
        with col3:
            st.markdown(f"S/ {sistema['interes_devengado']:,.2f}")
            diff = abs(visual['interes_devengado'] - sistema['interes_devengado'])
            if diff < 0.01:
                st.success("✅")
            else:
                st.error(f"❌ Δ {diff:,.2f}")
        
        # IGV Devengado
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("IGV Devengado")
        with col2:
            st.markdown(f"S/ {visual['igv_devengado']:,.2f}")
        with col3:
            st.markdown(f"S/ {sistema['igv_devengado']:,.2f}")
            diff = abs(visual['igv_devengado'] - sistema['igv_devengado'])
            if diff < 0.01:
                st.success("✅")
            else:
                st.error(f"❌ Δ {diff:,.2f}")
        
        st.markdown("")
        
        # SECCIÓN 4: INTERESES MORATORIOS
        if visual['dias_mora'] > 0 or sistema['dias_mora'] > 0:
            st.markdown("##### INTERESES MORATORIOS")
            
            # Interés Moratorio
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("Interés Moratorio")
            with col2:
                st.markdown(f"S/ {visual['interes_moratorio']:,.2f}")
            with col3:
                st.markdown(f"S/ {sistema['interes_moratorio']:,.2f}")
                diff = abs(visual['interes_moratorio'] - sistema['interes_moratorio'])
                if diff < 0.01:
                    st.success("✅")
                else:
                    st.error(f"❌ Δ {diff:,.2f}")
            
            # IGV Moratorio
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("IGV Moratorio")
            with col2:
                st.markdown(f"S/ {visual['igv_moratorio']:,.2f}")
            with col3:
                st.markdown(f"S/ {sistema['igv_moratorio']:,.2f}")
                diff = abs(visual['igv_moratorio'] - sistema['igv_moratorio'])
                if diff < 0.01:
                    st.success("✅")
                else:
                    st.error(f"❌ Δ {diff:,.2f}")
            
            st.markdown("")
        
        # SECCIÓN 5: DELTAS
        st.markdown("##### DELTAS")
        
        # Delta Compensatorios
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("Delta Compensatorios")
        with col2:
            st.markdown(f"S/ {visual['delta_compensatorios']:,.2f}")
        with col3:
            st.markdown(f"S/ {sistema['delta_compensatorios']:,.2f}")
            diff = abs(visual['delta_compensatorios'] - sistema['delta_compensatorios'])
            if diff < 0.01:
                st.success("✅")
            else:
                st.error(f"❌ Δ {diff:,.2f}")
        
        # Delta IGV
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("Delta IGV")
        with col2:
            st.markdown(f"S/ {visual['delta_igv']:,.2f}")
        with col3:
            st.markdown(f"S/ {sistema['delta_igv']:,.2f}")
            diff = abs(visual['delta_igv'] - sistema['delta_igv'])
            if diff < 0.01:
                st.success("✅")
            else:
                st.error(f"❌ Δ {diff:,.2f}")
        
        # Delta Capital
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("Delta Capital")
        with col2:
            st.markdown(f"S/ {visual['delta_capital']:,.2f}")
        with col3:
            st.markdown(f"S/ {sistema['delta_capital']:,.2f}")
            diff = abs(visual['delta_capital'] - sistema['delta_capital'])
            if diff < 0.01:
                st.success("✅")
            else:
                st.error(f"❌ Δ {diff:,.2f}")
        
        st.markdown("")
        
        # SECCIÓN 6: SALDO GLOBAL
        st.markdown("##### SALDO GLOBAL")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Saldo Global Final**")
        with col2:
            st.markdown(f"**S/ {visual['saldo_global']:,.2f}**")
        with col3:
            st.markdown(f"**S/ {sistema['saldo_global']:,.2f}**")
            diff = abs(visual['saldo_global'] - sistema['saldo_global'])
            if diff < 0.01:
                st.success("✅ Coincide")
            else:
                st.error(f"❌ Δ {diff:,.2f}")
        
        # Caso Detectado
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Caso Detectado**")
        with col2:
            st.markdown(f"**Caso {visual['caso']}**")
        with col3:
            st.markdown(f"**Caso {sistema['caso']}**")
            if visual['caso'] == sistema['caso']:
                st.success("✅ Coincide")
            else:
                st.error("❌ Diferente")
        
        st.markdown("")
        
        # Resumen de auditoría
        total_checks = 0
        total_errors = 0
        
        # Contar verificaciones
        checks = [
            abs(visual['capital'] - sistema['capital']) < 0.01,
            visual['dias_transcurridos'] == sistema['dias_transcurridos'],
            visual['dias_mora'] == sistema['dias_mora'],
            abs(visual['interes_devengado'] - sistema['interes_devengado']) < 0.01,
            abs(visual['igv_devengado'] - sistema['igv_devengado']) < 0.01,
            abs(visual['interes_moratorio'] - sistema['interes_moratorio']) < 0.01,
            abs(visual['igv_moratorio'] - sistema['igv_moratorio']) < 0.01,
            abs(visual['delta_compensatorios'] - sistema['delta_compensatorios']) < 0.01,
            abs(visual['delta_igv'] - sistema['delta_igv']) < 0.01,
            abs(visual['delta_capital'] - sistema['delta_capital']) < 0.01,
            abs(visual['saldo_global'] - sistema['saldo_global']) < 0.01,
            visual['caso'] == sistema['caso']
        ]
        
        total_checks = len(checks)
        total_errors = sum(1 for check in checks if not check)
        
        if total_errors == 0:
            st.success(f"✅ **AUDITORÍA EXITOSA** - Todos los cálculos coinciden ({total_checks} verificaciones)")
        else:
            st.error(f"❌ **DISCREPANCIAS DETECTADAS** - {total_errors} diferencia(s) encontrada(s) de {total_checks} verificaciones")
        
        st.markdown("---")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption("🧪 Módulo de Testing Liquidación Universal | Mini ERP V2")
