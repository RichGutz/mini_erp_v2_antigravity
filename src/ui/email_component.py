import streamlit as st
from src.utils.email_integration import send_email_with_attachments

def render_email_sender(key_suffix: str, documents: list, default_email: str = "", default_subject: str = ""):
    """
    Renderiza el componente de envío de correos.
    
    Args:
        key_suffix (str): Sufijo único para las keys de los widgets.
        documents (list): Lista de diccionarios [{'name': 'X', 'bytes': b'...'}, ...]
        default_email (str): Email por defecto.
        default_subject (str): Asunto por defecto.
    """
    st.markdown("### Envío de Documentos por Correo")
    st.info("Selecciona los documentos adjuntos y envía el correo directamente al cliente.")
    
    if not documents:
        st.warning("No hay documentos disponibles para enviar en este contexto.")
        return

    with st.expander("✉️ Redactar Correo", expanded=True):
        # 1. Selector de Documentos
        st.caption("Selecciona los adjuntos:")
        selected_docs = []
        
        # Checkbox para cada doc
        cols = st.columns(2)
        for i, doc in enumerate(documents):
            # Por defecto seleccionados
            if cols[i % 2].checkbox(f"📎 {doc['name']}", value=True, key=f"chk_{i}_{key_suffix}"):
                selected_docs.append(doc)
        
        st.divider()

        # 2. Campos del Correo
        c1, c2 = st.columns([1, 2])
        to_email = c1.text_input("Destinatario", value=default_email, placeholder="cliente@empresa.com", key=f"to_{key_suffix}")
        subject = c2.text_input("Asunto", value=default_subject, placeholder="Envío de Documentos - Operación XYZ", key=f"sub_{key_suffix}")
        
        body = st.text_area("Mensaje", value="Estimados,\n\nAdjunto encontrarán los documentos relacionados a la operación reciente.\n\nSaludos formales,", height=100, key=f"body_{key_suffix}")
        
        # 3. Botón de Envío
        if st.button("📤 Enviar Correo", key=f"btn_send_{key_suffix}", type="primary", use_container_width=True):
            # Validaciones básicas de integridad
            if not to_email or not subject:
                st.error("❌ Debes indicar Destinatario y Asunto.")
                return
            
            # Validación de formato de email (simple)
            if "@" not in to_email or "." not in to_email:
                st.error(f"❌ La dirección de correo '{to_email}' no parece válida.")
                return
            
            if not selected_docs:
                st.warning("⚠️ No has seleccionado ningún archivo adjunto (puedes enviar igual si lo deseas).")
            
            with st.spinner("Conectando con servidor SMTP y enviando..."):
                ok, msg = send_email_with_attachments(
                    to_email=to_email.strip(), # Clean spaces
                    subject=subject,
                    body=body,
                    attachments=selected_docs
                )
                
                if ok:
                    st.success(f"✅ {msg}")
                    st.balloons()
                else:
                    st.error(f"❌ {msg}")
