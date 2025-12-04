# Casos de Liquidación Universal - Dashboard Interactivo
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Casos de Liquidación Universal",
    page_icon="📊"
)

st.title("📊 Casos de Liquidación Universal - Herramienta de Análisis")

st.markdown("""
Esta herramienta te permite visualizar y entender los **6 casos** del algoritmo de liquidación universal.
Usa la calculadora interactiva para experimentar con diferentes valores y ver cómo se clasifican.
""")

# Definición de los 6 casos
CASOS = {
    "Caso 1": {
        "nombre": "LIQUIDADO - Caso 1",
        "condiciones": "ΔInt < 0 AND ΔCap < 0 AND Saldo < 0",
        "descripcion": "Cliente pagó de más en intereses Y en capital",
        "accion": "Generar notas de crédito, devolver dinero al cliente",
        "color": "#10b981",  # Verde
        "ejemplo": {"delta_int": -10, "delta_cap": -50, "saldo": -60}
    },
    "Caso 2": {
        "nombre": "EN PROCESO - Caso 2",
        "condiciones": "ΔInt < 0 AND ΔCap > 0 AND Saldo > 0",
        "descripcion": "Cliente pagó de más en intereses PERO de menos en capital",
        "accion": "Generar NC por intereses, crear nuevo calendario de pagos",
        "color": "#f59e0b",  # Naranja
        "ejemplo": {"delta_int": -10, "delta_cap": 50, "saldo": 40}
    },
    "Caso 3": {
        "nombre": "EN PROCESO - Caso 3",
        "condiciones": "ΔInt > 0 AND ΔCap > 0 AND Saldo > 0",
        "descripcion": "Cliente pagó de menos en intereses Y en capital",
        "accion": "Facturar intereses adicionales, nuevo calendario",
        "color": "#ef4444",  # Rojo
        "ejemplo": {"delta_int": 10, "delta_cap": 50, "saldo": 60}
    },
    "Caso 4": {
        "nombre": "EN PROCESO - Caso 4",
        "condiciones": "ΔInt > 0 AND ΔCap < 0 AND Saldo > 0",
        "descripcion": "Cliente pagó de menos en intereses PERO de más en capital",
        "accion": "Facturar intereses, evaluar moratorios",
        "color": "#f97316",  # Naranja oscuro
        "ejemplo": {"delta_int": 30, "delta_cap": -10, "saldo": 20}
    },
    "Caso 5": {
        "nombre": "LIQUIDADO - Caso 5",
        "condiciones": "ΔInt > 0 AND ΔCap < 0 AND Saldo < 0",
        "descripcion": "Cliente pagó de menos en intereses PERO mucho más en capital",
        "accion": "Facturar intereses, devolver exceso de capital",
        "color": "#06b6d4",  # Cyan
        "ejemplo": {"delta_int": 10, "delta_cap": -50, "saldo": -40}
    },
    "Caso 6": {
        "nombre": "LIQUIDADO - Caso 6",
        "condiciones": "ΔInt < 0 AND ΔCap > 0 AND Saldo < 0",
        "descripcion": "Cliente pagó mucho más en intereses PERO de menos en capital",
        "accion": "Generar NC por intereses, devolver saldo negativo",
        "color": "#8b5cf6",  # Púrpura
        "ejemplo": {"delta_int": -50, "delta_cap": 10, "saldo": -40}
    }
}

# Tabs para organizar el contenido
tab1, tab2, tab3 = st.tabs(["🧮 Calculadora Interactiva", "📋 Tabla de Referencia", "📊 Visualización de Casos"])

# TAB 1: CALCULADORA INTERACTIVA
with tab1:
    st.header("Calculadora Interactiva de Casos")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Ingresa los valores")
        
        capital_op = st.number_input("Capital Operación (S/)", value=1000.0, step=10.0)
        interes_original = st.number_input("Interés Original Cobrado (S/)", value=50.0, step=5.0)
        interes_devengado = st.number_input("Interés Devengado Calculado (S/)", value=50.0, step=5.0)
        monto_pagado = st.number_input("Monto Pagado por Cliente (S/)", value=1050.0, step=10.0)
        
        # Cálculos
        delta_int = interes_devengado - interes_original
        delta_cap = capital_op - monto_pagado
        saldo_global = delta_int + delta_cap
        
        st.markdown("---")
        st.subheader("Resultados del Cálculo")
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Delta Intereses", f"S/ {delta_int:,.2f}", 
                     delta=f"{'+' if delta_int >= 0 else ''}{delta_int:,.2f}")
        col_b.metric("Delta Capital", f"S/ {delta_cap:,.2f}",
                     delta=f"{'+' if delta_cap >= 0 else ''}{delta_cap:,.2f}")
        col_c.metric("Saldo Global", f"S/ {saldo_global:,.2f}",
                     delta=f"{'+' if saldo_global >= 0 else ''}{saldo_global:,.2f}")
        
        # Clasificación del caso
        caso_resultado = None
        for caso_key, caso_data in CASOS.items():
            ej = caso_data["ejemplo"]
            # Verificar condiciones
            if delta_int < 0 and delta_cap < 0 and saldo_global < 0:
                caso_resultado = "Caso 1"
            elif delta_int < 0 and delta_cap > 0 and saldo_global > 0:
                caso_resultado = "Caso 2"
            elif delta_int > 0 and delta_cap > 0 and saldo_global > 0:
                caso_resultado = "Caso 3"
            elif delta_int > 0 and delta_cap < 0 and saldo_global > 0:
                caso_resultado = "Caso 4"
            elif delta_int > 0 and delta_cap < 0 and saldo_global < 0:
                caso_resultado = "Caso 5"
            elif delta_int < 0 and delta_cap > 0 and saldo_global < 0:
                caso_resultado = "Caso 6"
        
        if caso_resultado:
            caso_info = CASOS[caso_resultado]
            st.markdown("---")
            st.markdown(f"### Resultado: **{caso_info['nombre']}**")
            st.info(f"**Descripción:** {caso_info['descripcion']}")
            st.success(f"**Acción Recomendada:** {caso_info['accion']}")
    
    with col2:
        st.subheader("Visualización del Caso")
        
        # Gráfico de barras
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Delta Intereses',
            x=['Componentes'],
            y=[delta_int],
            marker_color='#3b82f6' if delta_int >= 0 else '#ef4444',
            text=[f"S/ {delta_int:,.2f}"],
            textposition='auto',
        ))
        
        fig.add_trace(go.Bar(
            name='Delta Capital',
            x=['Componentes'],
            y=[delta_cap],
            marker_color='#8b5cf6' if delta_cap >= 0 else '#10b981',
            text=[f"S/ {delta_cap:,.2f}"],
            textposition='auto',
        ))
        
        fig.update_layout(
            title="Componentes del Saldo Global",
            barmode='stack',
            height=400,
            showlegend=True,
            yaxis_title="Monto (S/)",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Indicador de saldo
        st.markdown("### Saldo Global")
        if saldo_global < 0:
            st.error(f"**Saldo Negativo:** S/ {saldo_global:,.2f} - Cliente pagó de más, hay que devolverle")
        elif saldo_global > 0:
            st.warning(f"**Saldo Positivo:** S/ {saldo_global:,.2f} - Cliente debe dinero")
        else:
            st.success(f"**Saldo Cero:** S/ {saldo_global:,.2f} - Operación liquidada perfectamente")

# TAB 2: TABLA DE REFERENCIA
with tab2:
    st.header("Tabla de Referencia de los 6 Casos")
    
    # Crear DataFrame
    tabla_data = []
    for caso_key, caso_data in CASOS.items():
        tabla_data.append({
            "Caso": caso_data["nombre"],
            "Condiciones": caso_data["condiciones"],
            "Descripción": caso_data["descripcion"],
            "Acción Recomendada": caso_data["accion"]
        })
    
    df = pd.DataFrame(tabla_data)
    
    # Mostrar tabla con estilo
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("### Leyenda de Símbolos")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**ΔInt**: Delta de Intereses (Devengado - Original)")
    with col2:
        st.markdown("**ΔCap**: Delta de Capital (Capital - Pagado)")
    with col3:
        st.markdown("**Saldo**: Saldo Global (ΔInt + ΔCap)")

# TAB 3: VISUALIZACIÓN DE CASOS
with tab3:
    st.header("Visualización de los 6 Casos")
    
    # Selector de caso
    caso_seleccionado = st.selectbox(
        "Selecciona un caso para visualizar:",
        options=list(CASOS.keys()),
        format_func=lambda x: CASOS[x]["nombre"]
    )
    
    caso_info = CASOS[caso_seleccionado]
    ejemplo = caso_info["ejemplo"]
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown(f"### {caso_info['nombre']}")
        st.markdown(f"**Condiciones:** `{caso_info['condiciones']}`")
        st.info(caso_info['descripcion'])
        st.success(f"**Acción:** {caso_info['accion']}")
        
        st.markdown("---")
        st.markdown("### Ejemplo Numérico")
        st.write(f"**Delta Intereses:** S/ {ejemplo['delta_int']:,.2f}")
        st.write(f"**Delta Capital:** S/ {ejemplo['delta_cap']:,.2f}")
        st.write(f"**Saldo Global:** S/ {ejemplo['saldo']:,.2f}")
    
    with col2:
        # Gráfico del ejemplo
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Delta Intereses',
            x=['Ejemplo'],
            y=[ejemplo['delta_int']],
            marker_color='#3b82f6' if ejemplo['delta_int'] >= 0 else '#ef4444',
            text=[f"S/ {ejemplo['delta_int']:,.2f}"],
            textposition='auto',
        ))
        
        fig.add_trace(go.Bar(
            name='Delta Capital',
            x=['Ejemplo'],
            y=[ejemplo['delta_cap']],
            marker_color='#8b5cf6' if ejemplo['delta_cap'] >= 0 else '#10b981',
            text=[f"S/ {ejemplo['delta_cap']:,.2f}"],
            textposition='auto',
        ))
        
        fig.update_layout(
            title=f"Ejemplo: {caso_info['nombre']}",
            barmode='stack',
            height=400,
            showlegend=True,
            yaxis_title="Monto (S/)",
        )
        
        st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #6b7280; font-size: 0.875rem;'>
    <p>💡 <b>Tip:</b> Usa la calculadora interactiva para experimentar con diferentes valores y entender cómo funcionan los casos.</p>
</div>
""", unsafe_allow_html=True)
