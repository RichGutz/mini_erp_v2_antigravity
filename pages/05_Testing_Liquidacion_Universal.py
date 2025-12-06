"""
Módulo de Testing Liquidación Universal
Validación visual de cálculos de liquidaciones con tabla día a día
"""

import streamlit as st
import pandas as pd
import datetime
from datetime import date, timedelta
import sys
import os

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.factoring_system import SistemaFactoringCompleto

# ============================================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Testing Liquidación Universal",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Testing Liquidación Universal")
st.markdown("**Validación visual de cálculos de liquidaciones**")
st.markdown("---")

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def calcular_devengamiento_diario(
    capital: float,
    tasa_mensual_comp: float,
    tasa_mensual_mora: float,
    fecha_desembolso: date,
    fecha_pago_teorica: date,
    fecha_pago_real: date
) -> pd.DataFrame:
    """
    Genera tabla día a día de devengamiento de intereses
    """
    sistema = SistemaFactoringCompleto()
    
    # Determinar rango de fechas (desde desembolso hasta pago real + 30 días buffer)
    fecha_inicio = fecha_desembolso
    fecha_fin = max(fecha_pago_real, fecha_pago_teorica) + timedelta(days=30)
    
    # Generar lista de fechas
    fechas = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        fechas.append(fecha_actual)
        fecha_actual += timedelta(days=1)
    
    # Calcular intereses para cada día
    datos = []
    for i, fecha in enumerate(fechas):
        dias_transcurridos = (fecha - fecha_desembolso).days
        
        # Intereses compensatorios acumulados hasta este día
        if dias_transcurridos > 0:
            interes_comp_acum = sistema._calcular_intereses_compensatorios(
                capital, tasa_mensual_comp, dias_transcurridos
            )
        else:
            interes_comp_acum = 0.0
        
        # Interés compensatorio del día (diferencia con día anterior)
        if i > 0:
            interes_comp_dia_anterior = sistema._calcular_intereses_compensatorios(
                capital, tasa_mensual_comp, dias_transcurridos - 1
            ) if dias_transcurridos > 1 else 0.0
            interes_comp_diario = interes_comp_acum - interes_comp_dia_anterior
        else:
            interes_comp_diario = 0.0
        
        # Intereses moratorios (solo después de fecha teórica)
        interes_mora_acum = 0.0
        interes_mora_diario = 0.0
        if fecha > fecha_pago_teorica:
            dias_mora = (fecha - fecha_pago_teorica).days
            interes_mora_acum = sistema._calcular_intereses_moratorios(capital, dias_mora)
            
            if dias_mora > 1:
                interes_mora_ayer = sistema._calcular_intereses_moratorios(capital, dias_mora - 1)
                interes_mora_diario = interes_mora_acum - interes_mora_ayer
            else:
                interes_mora_diario = interes_mora_acum
        
        # Determinar zona (pre-pago, pago teórico, mora)
        if fecha < fecha_pago_teorica:
            zona = "Normal"
        elif fecha == fecha_pago_teorica:
            zona = "Pago Teórico"
        else:
            zona = "Mora"
        
        # Marcar fecha real de pago
        es_pago_real = (fecha == fecha_pago_real)
        
        datos.append({
            'Fecha': fecha,
            'Día': dias_transcurridos,
            'Capital': capital,
            'Int.Comp Diario': round(interes_comp_diario, 2),
            'Int.Comp Acum': round(interes_comp_acum, 2),
            'Int.Mora Diario': round(interes_mora_diario, 2),
            'Int.Mora Acum': round(interes_mora_acum, 2),
            'Zona': zona,
            'Es Pago Real': es_pago_real
        })
    
    return pd.DataFrame(datos)


def calcular_deltas(
    interes_devengado: float,
    interes_cobrado: float,
    capital: float,
    monto_pagado: float,
    interes_moratorio: float,
    igv_interes_devengado: float,
    igv_cobrado: float,
    igv_moratorio: float
) -> dict:
    """
    Calcula todos los deltas
    """
    delta_compensatorios = interes_devengado - interes_cobrado
    delta_igv_compensatorios = igv_interes_devengado - igv_cobrado
    delta_capital = capital - monto_pagado
    
    # Saldo global = suma de todos los componentes
    saldo_global = (delta_compensatorios + delta_igv_compensatorios + 
                   interes_moratorio + igv_moratorio + delta_capital)
    
    return {
        'delta_compensatorios': delta_compensatorios,
        'delta_igv_compensatorios': delta_igv_compensatorios,
        'delta_capital': delta_capital,
        'interes_moratorio': interes_moratorio,
        'igv_moratorio': igv_moratorio,
        'saldo_global': saldo_global
    }


def determinar_caso_y_recomendacion(delta_comp: float, delta_capital: float, saldo_global: float) -> dict:
    """
    Determina el caso (1-6) y retorna recomendaciones
    """
    sistema = SistemaFactoringCompleto()
    estado, accion = sistema._clasificar_caso_liquidacion(delta_comp, delta_capital, saldo_global)
    
    # Extraer número de caso
    caso_num = "No clasificado"
    if "Caso 1" in estado:
        caso_num = "1"
    elif "Caso 2" in estado:
        caso_num = "2"
    elif "Caso 3" in estado:
        caso_num = "3"
    elif "Caso 4" in estado:
        caso_num = "4"
    elif "Caso 5" in estado:
        caso_num = "5"
    elif "Caso 6" in estado:
        caso_num = "6"
    
    # Mapeo de recomendaciones detalladas
    recomendaciones_detalladas = {
        "1": {
            "emoji": "🔴",
            "titulo": "CASO 1: Liquidado con Devolución",
            "descripcion": "Se cobró de más en intereses Y se recibió más capital del debido",
            "acciones": [
                "Emitir Notas de Crédito por el exceso de intereses cobrados",
                "Devolver al cliente el saldo negativo total (valor absoluto)",
                "Marcar operación como LIQUIDADA"
            ]
        },
        "2": {
            "emoji": "🟡",
            "titulo": "CASO 2: En Proceso - NC y Nuevo Calendario",
            "descripcion": "Se cobró de más en intereses PERO el pago no cubrió el capital",
            "acciones": [
                "Emitir Notas de Crédito por exceso de intereses",
                "NO devolver cash (el saldo positivo compensa)",
                "Generar nuevo calendario de pagos para el remanente",
                "Seguir devengando intereses sobre el saldo"
            ]
        },
        "3": {
            "emoji": "🟠",
            "titulo": "CASO 3: En Proceso - Facturar y Nuevo Calendario",
            "descripcion": "Faltan intereses por cobrar Y el pago no cubrió el capital",
            "acciones": [
                "Facturar los intereses faltantes",
                "Generar nuevo calendario de pagos",
                "Seguir devengando intereses (compensatorios y potencialmente moratorios)"
            ]
        },
        "4": {
            "emoji": "🟠",
            "titulo": "CASO 4: En Proceso - Facturar y Evaluar Mora",
            "descripcion": "Faltan intereses por cobrar PERO se recibió más capital del debido",
            "acciones": [
                "Facturar los intereses faltantes",
                "Generar nuevo calendario para el saldo positivo",
                "Evaluar si aplican intereses moratorios según fecha de pago"
            ]
        },
        "5": {
            "emoji": "🔵",
            "titulo": "CASO 5: Liquidado - Facturar y Devolver",
            "descripcion": "Faltan intereses por cobrar PERO se recibió más capital del debido (saldo negativo)",
            "acciones": [
                "Facturar los intereses faltantes",
                "Devolver al cliente el exceso de capital",
                "Marcar operación como LIQUIDADA"
            ]
        },
        "6": {
            "emoji": "🔴",
            "titulo": "CASO 6: Liquidado - NC y Devolución",
            "descripcion": "Se cobró de más en intereses Y el capital no fue liquidado (saldo negativo)",
            "acciones": [
                "Emitir Notas de Crédito por exceso de intereses",
                "Devolver al cliente el saldo negativo total",
                "Marcar operación como LIQUIDADA"
            ]
        }
    }
    
    return {
        'caso': caso_num,
        'estado': estado,
        'accion_basica': accion,
        'detalles': recomendaciones_detalladas.get(caso_num, {
            "emoji": "⚠️",
            "titulo": "Caso No Clasificado",
            "descripcion": "Requiere revisión manual",
            "acciones": ["Revisar manualmente los valores"]
        })
    }


def aplicar_estilos_tabla(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica estilos condicionales a la tabla de devengamiento
    """
    def colorear_fila(row):
        if row['Es Pago Real']:
            return ['background-color: #FFD700; font-weight: bold'] * len(row)  # Dorado para pago real
        elif row['Zona'] == 'Normal':
            return ['background-color: #90EE90'] * len(row)  # Verde claro
        elif row['Zona'] == 'Pago Teórico':
            return ['background-color: #FFFFE0'] * len(row)  # Amarillo claro
        elif row['Zona'] == 'Mora':
            return ['background-color: #FFB6C1'] * len(row)  # Rojo claro
        else:
            return [''] * len(row)
    
    return df.style.apply(colorear_fila, axis=1)


# ============================================================================
# INICIALIZACIÓN DE SESSION STATE
# ============================================================================

if 'testing_inputs' not in st.session_state:
    st.session_state.testing_inputs = {
        'capital': 17822.01,
        'tasa_comp': 0.02,
        'tasa_mora': 0.03,
        'fecha_desembolso': date(2025, 1, 1),
        'fecha_pago_teorica': date(2025, 3, 1),
        'intereses_cobrados': 1202.84,
        'igv_cobrado': 216.51,
        'fecha_pago_real': date(2025, 2, 15),
        'monto_pagado': 18000.0
    }

# ============================================================================
# TABS PRINCIPALES
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Inputs",
    "📅 Tabla Diaria",
    "📊 Análisis de Deltas",
    "💡 Recomendaciones"
])

# ============================================================================
# TAB 1: INPUTS
# ============================================================================

with tab1:
    st.header("Parámetros de la Liquidación")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Datos de la Operación")
        
        capital = st.number_input(
            "Capital Desembolsado (S/)",
            min_value=0.0,
            value=st.session_state.testing_inputs['capital'],
            step=100.0,
            format="%.2f",
            key="input_capital"
        )
        
        tasa_comp = st.number_input(
            "Tasa Interés Mensual Compensatorio (%)",
            min_value=0.0,
            max_value=100.0,
            value=st.session_state.testing_inputs['tasa_comp'] * 100,
            step=0.1,
            format="%.2f",
            key="input_tasa_comp"
        ) / 100
        
        tasa_mora = st.number_input(
            "Tasa Interés Mensual Moratorio (%)",
            min_value=0.0,
            max_value=100.0,
            value=st.session_state.testing_inputs['tasa_mora'] * 100,
            step=0.1,
            format="%.2f",
            key="input_tasa_mora"
        ) / 100
        
        fecha_desembolso = st.date_input(
            "Fecha de Desembolso",
            value=st.session_state.testing_inputs['fecha_desembolso'],
            key="input_fecha_desembolso"
        )
        
        fecha_pago_teorica = st.date_input(
            "Fecha de Pago Teórica (Vencimiento)",
            value=st.session_state.testing_inputs['fecha_pago_teorica'],
            key="input_fecha_pago_teorica"
        )
    
    with col2:
        st.subheader("Datos de Cobro y Pago")
        
        intereses_cobrados = st.number_input(
            "Intereses Compensatorios Cobrados (S/)",
            min_value=0.0,
            value=st.session_state.testing_inputs['intereses_cobrados'],
            step=10.0,
            format="%.2f",
            key="input_intereses_cobrados"
        )
        
        igv_cobrado = st.number_input(
            "IGV Cobrado sobre Intereses (S/)",
            min_value=0.0,
            value=st.session_state.testing_inputs['igv_cobrado'],
            step=10.0,
            format="%.2f",
            key="input_igv_cobrado"
        )
        
        st.markdown("---")
        st.markdown("### 📍 Fecha Real de Pago")
        st.info("Modifica esta fecha para ver el impacto en los cálculos")
        
        fecha_pago_real = st.date_input(
            "Fecha Real de Pago",
            value=st.session_state.testing_inputs['fecha_pago_real'],
            key="input_fecha_pago_real"
        )
        
        monto_pagado = st.number_input(
            "Monto Pagado (S/)",
            min_value=0.0,
            value=st.session_state.testing_inputs['monto_pagado'],
            step=100.0,
            format="%.2f",
            key="input_monto_pagado"
        )
    
    # Actualizar session state
    st.session_state.testing_inputs.update({
        'capital': capital,
        'tasa_comp': tasa_comp,
        'tasa_mora': tasa_mora,
        'fecha_desembolso': fecha_desembolso,
        'fecha_pago_teorica': fecha_pago_teorica,
        'intereses_cobrados': intereses_cobrados,
        'igv_cobrado': igv_cobrado,
        'fecha_pago_real': fecha_pago_real,
        'monto_pagado': monto_pagado
    })
    
    # Botón de cálculo
    st.markdown("---")
    if st.button("🔄 Recalcular Todo", type="primary", use_container_width=True):
        st.success("✅ Cálculos actualizados. Revisa las otras pestañas.")
        st.rerun()

# ============================================================================
# TAB 2: TABLA DIARIA
# ============================================================================

with tab2:
    st.header("Devengamiento Día a Día")
    
    # Generar tabla
    df_diario = calcular_devengamiento_diario(
        capital=st.session_state.testing_inputs['capital'],
        tasa_mensual_comp=st.session_state.testing_inputs['tasa_comp'],
        tasa_mensual_mora=st.session_state.testing_inputs['tasa_mora'],
        fecha_desembolso=st.session_state.testing_inputs['fecha_desembolso'],
        fecha_pago_teorica=st.session_state.testing_inputs['fecha_pago_teorica'],
        fecha_pago_real=st.session_state.testing_inputs['fecha_pago_real']
    )
    
    # Métricas resumen
    col1, col2, col3, col4 = st.columns(4)
    
    dias_transcurridos = (st.session_state.testing_inputs['fecha_pago_real'] - 
                         st.session_state.testing_inputs['fecha_desembolso']).days
    
    with col1:
        st.metric("Días Transcurridos", f"{dias_transcurridos} días")
    
    with col2:
        plazo_teorico = (st.session_state.testing_inputs['fecha_pago_teorica'] - 
                        st.session_state.testing_inputs['fecha_desembolso']).days
        st.metric("Plazo Teórico", f"{plazo_teorico} días")
    
    with col3:
        dias_mora = max(0, (st.session_state.testing_inputs['fecha_pago_real'] - 
                           st.session_state.testing_inputs['fecha_pago_teorica']).days)
        st.metric("Días de Mora", f"{dias_mora} días", 
                 delta="⚠️ Mora" if dias_mora > 0 else "✅ Sin mora")
    
    with col4:
        total_filas = len(df_diario)
        st.metric("Total Días Mostrados", f"{total_filas} días")
    
    st.markdown("---")
    
    # Leyenda de colores
    st.markdown("""
    **Leyenda de colores:**
    - 🟢 **Verde**: Período normal (antes del vencimiento)
    - 🟡 **Amarillo**: Fecha de pago teórica
    - 🔴 **Rojo**: Período de mora (después del vencimiento)
    - 🟠 **Dorado**: Fecha real de pago
    """)
    
    # Mostrar tabla con estilos
    st.dataframe(
        aplicar_estilos_tabla(df_diario),
        use_container_width=True,
        height=500
    )
    
    # Opción de descarga
    csv = df_diario.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Tabla como CSV",
        data=csv,
        file_name=f"devengamiento_diario_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

# ============================================================================
# TAB 3: ANÁLISIS DE DELTAS
# ============================================================================

with tab3:
    st.header("Análisis de Deltas")
    
    # Calcular intereses devengados al día del pago real
    sistema = SistemaFactoringCompleto()
    dias_para_calculo = (st.session_state.testing_inputs['fecha_pago_real'] - 
                        st.session_state.testing_inputs['fecha_desembolso']).days
    
    interes_devengado = sistema._calcular_intereses_compensatorios(
        st.session_state.testing_inputs['capital'],
        st.session_state.testing_inputs['tasa_comp'],
        dias_para_calculo
    )
    
    igv_devengado = interes_devengado * 0.18
    
    # Calcular moratorios si aplica
    dias_mora = max(0, (st.session_state.testing_inputs['fecha_pago_real'] - 
                       st.session_state.testing_inputs['fecha_pago_teorica']).days)
    
    if dias_mora > 0:
        interes_moratorio = sistema._calcular_intereses_moratorios(
            st.session_state.testing_inputs['capital'],
            dias_mora
        )
        igv_moratorio = interes_moratorio * 0.18
    else:
        interes_moratorio = 0.0
        igv_moratorio = 0.0
    
    # Calcular deltas
    deltas = calcular_deltas(
        interes_devengado=interes_devengado,
        interes_cobrado=st.session_state.testing_inputs['intereses_cobrados'],
        capital=st.session_state.testing_inputs['capital'],
        monto_pagado=st.session_state.testing_inputs['monto_pagado'],
        interes_moratorio=interes_moratorio,
        igv_interes_devengado=igv_devengado,
        igv_cobrado=st.session_state.testing_inputs['igv_cobrado'],
        igv_moratorio=igv_moratorio
    )
    
    # Métricas principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Delta Compensatorios",
            f"S/ {deltas['delta_compensatorios']:,.2f}",
            delta="Cobrado de más" if deltas['delta_compensatorios'] < 0 else "Falta cobrar"
        )
    
    with col2:
        st.metric(
            "Delta Capital",
            f"S/ {deltas['delta_capital']:,.2f}",
            delta="Pagado de más" if deltas['delta_capital'] < 0 else "Falta pagar"
        )
    
    with col3:
        st.metric(
            "Saldo Global",
            f"S/ {deltas['saldo_global']:,.2f}",
            delta="A favor del cliente" if deltas['saldo_global'] < 0 else "A favor de Inandes"
        )
    
    st.markdown("---")
    
    # Tabla de desglose
    st.subheader("Desglose Detallado")
    
    desglose_data = {
        'Concepto': [
            'Intereses Devengados',
            'Intereses Cobrados',
            'Delta Compensatorios',
            '',
            'IGV Devengado',
            'IGV Cobrado',
            'Delta IGV',
            '',
            'Capital Operación',
            'Monto Pagado',
            'Delta Capital',
            '',
            'Intereses Moratorios',
            'IGV Moratorios',
            '',
            'SALDO GLOBAL'
        ],
        'Monto (S/)': [
            f"{interes_devengado:,.2f}",
            f"{st.session_state.testing_inputs['intereses_cobrados']:,.2f}",
            f"{deltas['delta_compensatorios']:,.2f}",
            '',
            f"{igv_devengado:,.2f}",
            f"{st.session_state.testing_inputs['igv_cobrado']:,.2f}",
            f"{deltas['delta_igv_compensatorios']:,.2f}",
            '',
            f"{st.session_state.testing_inputs['capital']:,.2f}",
            f"{st.session_state.testing_inputs['monto_pagado']:,.2f}",
            f"{deltas['delta_capital']:,.2f}",
            '',
            f"{interes_moratorio:,.2f}",
            f"{igv_moratorio:,.2f}",
            '',
            f"{deltas['saldo_global']:,.2f}"
        ]
    }
    
    df_desglose = pd.DataFrame(desglose_data)
    st.dataframe(df_desglose, use_container_width=True, hide_index=True)

# ============================================================================
# TAB 4: RECOMENDACIONES
# ============================================================================

with tab4:
    st.header("Caso Detectado y Recomendaciones")
    
    # Determinar caso
    caso_info = determinar_caso_y_recomendacion(
        delta_comp=deltas['delta_compensatorios'],
        delta_capital=deltas['delta_capital'],
        saldo_global=deltas['saldo_global']
    )
    
    # Mostrar caso detectado
    st.markdown(f"## {caso_info['detalles']['emoji']} {caso_info['detalles']['titulo']}")
    st.info(caso_info['detalles']['descripcion'])
    
    st.markdown("### Acciones Recomendadas:")
    for i, accion in enumerate(caso_info['detalles']['acciones'], 1):
        st.markdown(f"{i}. {accion}")
    
    st.markdown("---")
    
    # Tabla de referencia de todos los casos
    st.subheader("📚 Referencia de los 6 Casos")
    
    casos_referencia = pd.DataFrame([
        {
            'Caso': '1',
            'Delta Comp': 'NEGATIVO',
            'Delta Capital': 'NEGATIVO',
            'Saldo Global': 'NEGATIVO',
            'Estado': 'LIQUIDADO',
            'Consecuencia': 'Devolver dinero + NC'
        },
        {
            'Caso': '2',
            'Delta Comp': 'NEGATIVO',
            'Delta Capital': 'POSITIVO',
            'Saldo Global': 'POSITIVO',
            'Estado': 'EN PROCESO',
            'Consecuencia': 'NC + Nuevo calendario'
        },
        {
            'Caso': '3',
            'Delta Comp': 'POSITIVO',
            'Delta Capital': 'POSITIVO',
            'Saldo Global': 'POSITIVO',
            'Estado': 'EN PROCESO',
            'Consecuencia': 'Facturar + Nuevo calendario'
        },
        {
            'Caso': '4',
            'Delta Comp': 'POSITIVO',
            'Delta Capital': 'NEGATIVO',
            'Saldo Global': 'POSITIVO',
            'Estado': 'EN PROCESO',
            'Consecuencia': 'Facturar + Evaluar moratorios'
        },
        {
            'Caso': '5',
            'Delta Comp': 'POSITIVO',
            'Delta Capital': 'NEGATIVO',
            'Saldo Global': 'NEGATIVO',
            'Estado': 'LIQUIDADO',
            'Consecuencia': 'Facturar + Devolver exceso'
        },
        {
            'Caso': '6',
            'Delta Comp': 'NEGATIVO',
            'Delta Capital': 'POSITIVO',
            'Saldo Global': 'NEGATIVO',
            'Estado': 'LIQUIDADO',
            'Consecuencia': 'NC + Devolver saldo'
        }
    ])
    
    # Resaltar el caso actual
    def resaltar_caso_actual(row):
        if row['Caso'] == caso_info['caso']:
            return ['background-color: #FFD700; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    st.dataframe(
        casos_referencia.style.apply(resaltar_caso_actual, axis=1),
        use_container_width=True,
        hide_index=True
    )
    
    st.caption("💡 El caso resaltado en dorado es el detectado para esta liquidación")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption("🧪 Módulo de Testing Liquidación Universal | Mini ERP V2")
