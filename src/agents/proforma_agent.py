import streamlit as st
import google.generativeai as genai
import tempfile
import os
import json
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

# --- Project Imports ---
from src.services import pdf_parser
from src.data import supabase_repository as db
from src.core.factoring_system import SistemaFactoringCompleto

# --- Configure Gemini ---
def get_gemini_model():
    """Configures and returns the Gemini model instance."""
    try:
        api_key = st.secrets["gemini"]["api_key"]
        genai.configure(api_key=api_key)
        
        # Generation Config
        generation_config = {
            "temperature": 0.2, # Low temperature for factual tasks
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }
        
        model = genai.GenerativeModel(
            model_name="gemini-flash-latest",
            generation_config=generation_config,
        )
        return model
    except Exception as e:
        st.error(f"❌ Error configurando Gemini: {e}")
        return None

# --- Tool Logic: Parse & Calculate ---
def tool_process_invoice_pdf(file_path):
    """
    Simulates the 'Tool' execution:
    1. Parse PDF
    2. Enhance with DB Data
    3. Calculate Factoring
    4. Return JSON summary
    """
    try:
        # 1. Parse
        parsed_data = pdf_parser.extract_fields_from_pdf(file_path)
        if parsed_data.get("error"):
            return {"error": f"Parsing Error: {parsed_data['error']}"}

        # 2. Extract Data
        ruc_emisor = parsed_data.get('emisor_ruc')
        monto_neto = parsed_data.get('monto_neto', 0.0)
        
        if not ruc_emisor:
            return {"error": "No RUC found in invoice"}
            
        # 3. DB Lookup (Financial Conditions)
        db_rates = db.get_financial_conditions(str(ruc_emisor))
        
        # 4. Prepare Operation Object for Calculation
        # Defaults if not in DB
        tasa_avance = float(db_rates.get('tasa_avance', 98.0) if db_rates else 98.0)
        interes_mensual = float(db_rates.get('interes_mensual_pen', 1.25) if db_rates else 1.25) # Assuming PEN default logic for demo
        dias_minimos = int(db_rates.get('dias_minimos_interes', 15) if db_rates else 15)
        
        # Fake PLAZO for simulation (Agent will ask or assume) -> Let's assume standard logic or passed param
        # For this tool, we will calculate based on "Today" vs "Parsed Due Date" if available, else standard 30
        
        fecha_emision = parsed_data.get('fecha_emision') # String
        # Logic to determine payment date? 
        # For the agent demo, we will let the Calculation System handle defaults or return "Missing Info"
        
        # Let's emulate a standard calculation with 'SistemaFactoringCompleto'
        # We need to adapt the input format to what 'procesar_lote_originacion' expects
        
        factura_input = {
            'monto_factura_neto': monto_neto,
            'tasa_avance': tasa_avance / 100.0,
            'tasa_interes_mensual': interes_mensual / 100.0,
            'plazo_dias': 30, # Placeholder, real world needs logic
            'comision_minima': 0.0, # Simplified
            'comision_porcentual': 0.0,
            'aplica_comision_afiliacion': False
        }
        
        sistema = SistemaFactoringCompleto()
        resultado = sistema.originar_operacion(factura_input)
        
        # Enrich result with metadata
        resultado['emisor_nombre'] = db.get_razon_social_by_ruc(ruc_emisor) or "Desconocido"
        resultado['numero_factura'] = parsed_data.get('invoice_id')
        
        return resultado
        
    except Exception as e:
        return {"error": f"Processing Error: {str(e)}"}

# --- File Uploader Handler ---
def handle_file_upload():
    uploaded_file = st.sidebar.file_uploader("📂 Sube la factura (PDF) para analizar", type=["pdf"])
    
    if uploaded_file:
        # Save temp
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        return tmp_path, uploaded_file.name
    return None, None

# --- Main Render Function ---
def render_proforma_agent():
    model = get_gemini_model()
    if not model:
        st.warning("Configura tu API Key de Gemini en secrets.toml para continuar.")
        return

    # File Input
    file_path, file_name = handle_file_upload()
    
    # Initialize chat with a welcome if empty
    if not st.session_state.messages:
        initial_msg = "Hola! Soy tu creador de proformas. Sube una factura PDF y te ayudaré a calcular su liquidación teórica."
        st.session_state.messages.append({"role": "assistant", "content": initial_msg})
        st.rerun()

    # User Input
    if prompt := st.chat_input("Escribe tu mensaje..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Agent Response Logic
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # --- CONTEXT BUILDING ---
            # If a file is currently visible/uploaded, we process it implicitly if the user asks "Process this"
            # Or we check if we already processed it in session state
            
            response_text = ""
            
            # SCENARIO: User just uploaded a file and asks to process it
            if file_path and "procesar" in prompt.lower() or "calcula" in prompt.lower() or "analiza" in prompt.lower():
                with st.spinner(f"⚡ Analizando documento: {file_name}..."):
                    tool_result = tool_process_invoice_pdf(file_path)
                    
                    if tool_result.get("error"):
                        response_text = f"❌ Tuve un problema leyendo el archivo: {tool_result['error']}"
                    else:
                        # Construct a Context Prompt for Gemini
                        context_prompt = f"""
                        Act as a Financial Analyst Assistant using 'Inandes ERP'.
                        I have processed the uploaded invoice '{file_name}' using external tools.
                        
                        Here is the raw data extracted and calculated:
                        {json.dumps(tool_result,indent=2, default=str)}
                        
                        Please define a Markdown response that:
                        1. Greets the user.
                        2. Summarizes the invoice (Emisor, Number, Amount).
                        3. Presents the FINANCIAL PROPOSAL (Proforma) in a nice table. Use the calculated fields.
                        4. Ask for confirmation to save this operation.
                        """
                        
                        # Call Gemini to format the response
                        try:
                            gemini_response = model.generate_content(context_prompt)
                            response_text = gemini_response.text
                        except Exception as e:
                            response_text = f"Error conectando con IA: {e}\n\nDatos crudos:\n{tool_result}"
                            
            else:
                # Normal Conversation
                chat_history = [
                    {"role": m["role"], "parts": [m["content"]]} 
                    for m in st.session_state.messages 
                    if m["role"] != "system" # Filter if needed
                ]
                
                # Simple generation for now
                try:
                    # We pass simple history context manually or use ChatSession
                    chat = model.start_chat(history=[]) # Simplified for demo
                    gemini_response = chat.send_message(prompt)
                    response_text = gemini_response.text
                except Exception as e:
                     response_text = f"Lo siento, tuve un error: {e}"

            # Stream result
            message_placeholder.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
