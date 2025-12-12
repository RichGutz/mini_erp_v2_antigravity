import streamlit as st
import pandas as pd
import datetime

def render_letras_cavali_integration(invoices_data):
    """
    Renders the 'Letras - Cavali' integration section.
    Displays a Data Table with details for Bills of Exchange (Letras).
    """
    st.markdown("---")
    st.subheader("6. Integración Letras - Cavali (Simulación)")
    
    if not invoices_data:
        st.info("No hay facturas para procesar.")
        return

    st.write("Configura los parámetros globales para la generación de Letras:")
    
    col1, col2 = st.columns(2)
    with col1:
        lugar_giro = st.text_input("📍 Lugar de Giro", value="Lima", key="letras_lugar_giro")
    with col2:
        lugar_pago = st.text_input("🏦 Lugar de Pago", value="Banco de la Nación", key="letras_lugar_pago")

    st.write("### Detalle de Letras a Generar")
    
    # Prepare Data for Table
    letras_data = []
    for idx, inv in enumerate(invoices_data):
        
        # Extract Data
        # Monto: Using 'monto_neto_factura' as the base for the Bill Amount
        monto = inv.get('monto_neto_factura', 0.0)
        moneda = inv.get('moneda_factura', 'PEN')
        
        # Fechas
        fecha_giro = datetime.date.today()
        # Fecha Vencimiento: usually 'fecha_pago_calculada'
        fecha_venc = inv.get('fecha_pago_calculada', 'S/D')
        
        # Participants (Fallback to N/A if missing)
        girador_nombre = inv.get('emisor_nombre', 'N/D')
        girador_dir = "Dirección Fiscal Emisor (Simulada)" # Data not always in context
        
        aceptante_nombre = inv.get('aceptante_nombre', 'N/D')
        aceptante_dir = "Dirección Fiscal Aceptante (Simulada)"
        
        letras_data.append({
            "N° Factura / Ref": inv.get('numero_factura', f'REF-{idx+1}'),
            "Monto": f"{monto:,.2f}",
            "Moneda": moneda,
            "Fecha Giro": fecha_giro,
            "Fecha Vencimiento": fecha_venc,
            "Girador (Emisor)": girador_nombre,
            # "Dirección Girador": girador_dir, # Too wide for simple table? Let's hide for cleanliness or use expander
            "Aceptante (Pagador)": aceptante_nombre,
            # "Dirección Aceptante": aceptante_dir,
            "Lugar Pago": lugar_pago
        })
    
    if letras_data:
        df_letras = pd.DataFrame(letras_data)
        st.dataframe(df_letras, use_container_width=True, hide_index=True)
        
        st.caption(f"Total Letras: {len(letras_data)} | Lugar de Giro: {lugar_giro}")
        
        if st.button("📄 Generar Archivo TXT/Excel (Simulación)", type="primary", use_container_width=True):
             st.toast("✅ Archivo de Letras generado correctamente (Simulado). ready_for_cavali.txt")
             st.balloons()
    else:
        st.warning("No se pudieron extraer datos para las letras.")
