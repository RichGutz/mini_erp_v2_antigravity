import streamlit as st
import time
import os

def render_xml_cavali_integration(invoices_data):
    """
    Renders the XML Integration widget for Cavali.
    Matches uploaded XMLs with existing PDF invoices and simulates API submission.
    """
    st.markdown("---")
    st.subheader("5. Integración XML - Cavali (Factoring Electrónico)")
    
    with st.expander("⚙️ Configuración de Conexión y Credenciales", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Auth URL", value="https://auth.cavali.com.pe/oauth2/token", key="cavali_auth_url")
            st.text_input("Base URL API", value="https://api.cavali.com.pe/v1", key="cavali_base_url")
        with c2:
            st.text_input("Client ID", type="password", key="cavali_client_id")
            st.text_input("Client Secret", type="password", key="cavali_client_secret")
            st.text_input("API Key (Ocp-Apim-Subscription-Key)", type="password", key="cavali_api_key")
            
        if st.button("🔌 Probar Conexión (Simulación)"):
            with st.spinner("Conectando con Cavali..."):
                time.sleep(1.5)
                st.success("✅ Conexión Exitosa. Token Obtenido.")

    st.info("ℹ️ Carga los archivos XML correspondientes a las facturas procesadas. El sistema emparejará automáticamente por nombre de archivo (ej. `F001-123.pdf` <-> `F001-123.xml`).")

    # 1. XML Uploader
    uploaded_xmls = st.file_uploader("Cargar XMLs", type=["xml"], accept_multiple_files=True, key="cavali_xml_uploader")
    
    # 2. Matching Logic
    if invoices_data:
        # Map invoice filenames (without extension) for easy lookup
        # Assuming parsed_pdf_name is like "ABC.pdf"
        invoice_map = {}
        for inv in invoices_data:
            fname = inv.get('parsed_pdf_name', '')
            base_name = os.path.splitext(fname)[0]
            invoice_map[base_name] = inv
            inv['has_xml_match'] = False # Reset status

        xml_status = [] # List of dicts for visualization
        
        if uploaded_xmls:
            for xml_file in uploaded_xmls:
                xml_base = os.path.splitext(xml_file.name)[0]
                
                if xml_base in invoice_map:
                    # Match found!
                    invoice_map[xml_base]['has_xml_match'] = True
                    xml_status.append({"name": xml_file.name, "status": "MATCH", "msg": "✅ Vinculado"})
                else:
                    # Orphan XML
                    xml_status.append({"name": xml_file.name, "status": "ORPHAN", "msg": "⚠️ Sin PDF"})

        # Check for missing XMLs (Invoices that didn't get a match)
        for base, inv in invoice_map.items():
            if not inv.get('has_xml_match'):
                 # We don't display a brick for every missing one in the XML section necessarily, 
                 # but we can list them or show a recap brick.
                 pass

        # 3. Visual Feedback (Bricks)
        if uploaded_xmls:
            st.write("###### Estado de Archivos XML:")
            cols = st.columns(4)
            for i, item in enumerate(xml_status):
                col = cols[i % 4]
                color = "#e6fffa" if item['status'] == "MATCH" else "#fff4e6" # Greenish vs Orangish
                border = "#38b2ac" if item['status'] == "MATCH" else "#ed8936"
                
                col.markdown(
                    f"""
                    <div style="background-color: {color}; padding: 8px; border-radius: 4px; border: 1px solid {border}; margin-bottom: 8px; font-size: 0.85em;">
                        <strong>{item['status']}</strong><br>
                        {item['name']}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
        
        # 4. Global Status Summary
        total_inv = len(invoices_data)
        matches = sum(1 for inv in invoices_data if inv.get('has_xml_match'))
        missing = total_inv - matches
        
        st.markdown(f"**Resumen de Cobertura:** {matches}/{total_inv} facturas tienen XML.")
        
        if missing > 0:
            st.warning(f"⚠️ Faltan XMLs para {missing} facturas.")
        elif total_inv > 0:
            st.success("✅ Cobertura Completa: Todas las facturas tienen su XML.")

        # 5. Submit Button
        submit_disabled = matches == 0
        if st.button("🚀 Enviar a Cavali (Simulación)", type="primary", disabled=submit_disabled, use_container_width=True):
             with st.spinner("Validando estructuras XML..."):
                 time.sleep(1)
             with st.spinner("Autenticando API..."):
                 time.sleep(1)
             with st.spinner(f"Enviando {matches} documentos..."):
                 time.sleep(2)
                 
             st.balloons()
             st.success(f"✅ Operación Exitosa: {matches} facturas registradas correctamente en Cavali.")
             st.json({
                 "transaction_id": "TX-9988776655",
                 "status": "COMPLETED",
                 "processed_count": matches,
                 "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
             })
    else:
        st.info("Carga facturas PDF primero para habilitar la integración.")
