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

# --- Tool 1: Extraction & Proposal ---
def tool_extract_invoice_data(file_path):
    """
    Step 1: Parse PDF and propose parameters (Rates, Dates) based on DB.
    Does NOT calculate final values yet.
    """
    try:
        # 1. Parse
        parsed_data = pdf_parser.extract_fields_from_pdf(file_path)
        if parsed_data.get("error"):
            return {"error": f"Parsing Error: {parsed_data['error']}"}

        # 2. Extract Key Data
        ruc_emisor = parsed_data.get('emisor_ruc')
        monto_neto = parsed_data.get('monto_neto', 0.0)
        cliente_nombre = parsed_data.get('cliente_nombre', "Cliente Desconocido") # Invoice Receiver
        
        if not ruc_emisor:
            return {"error": "No RUC found in invoice"}
            
        # 3. DB Lookup (Financial Conditions)
        db_rates = db.get_financial_conditions(str(ruc_emisor))
        emisor_nombre = db.get_razon_social_by_ruc(ruc_emisor) or parsed_data.get('emisor_nombre', "Desconocido")
        
        # 4. Propose Defaults
        tasa_avance = float(db_rates.get('tasa_avance', 98.0) if db_rates else 98.0)
        interes_mensual = float(db_rates.get('interes_mensual_pen', 1.25) if db_rates else 1.25) 
        dias_minimos = int(db_rates.get('dias_minimos_interes', 15) if db_rates else 15)
        
        # Default term (can be adjusted by user)
        plazo_sugerido = 30 
        
        proposal = {
            "status": "PROPOSAL_READY",
            "extracted_data": {
                "emisor_ruc": ruc_emisor,
                "emisor_nombre": emisor_nombre,
                "cliente_nombre": cliente_nombre,
                "numero_factura": parsed_data.get('invoice_id'),
                "moneda": parsed_data.get('moneda', 'PEN'),
                "monto_neto": monto_neto,
                "fecha_emision": parsed_data.get('fecha_emision'),
            },
            "proposed_params": {
                "tasa_avance_percent": tasa_avance,
                "tasa_interes_mensual_percent": interes_mensual,
                "plazo_dias": plazo_sugerido,
                "comision_minima": 0.0
            }
        }
        return proposal
        
    except Exception as e:
        return {"error": f"Extraction Error: {str(e)}"}

# --- Tool 2: Calculation ---
def tool_calculate_factoring(params):
    """
    Step 2: Calculate based on CONFIRMED parameters.
    """
    try:
        # Prepare input for system
        factura_input = {
            'monto_factura_neto': params['monto_neto'],
            'tasa_avance': params['tasa_avance_percent'] / 100.0,
            'tasa_interes_mensual': params['tasa_interes_mensual_percent'] / 100.0,
            'plazo_dias': params['plazo_dias'],
            'comision_minima': params.get('comision_minima', 0.0),
            'comision_porcentual': 0.0,
            'aplica_comision_afiliacion': False
        }
        
        sistema = SistemaFactoringCompleto()
        resultado = sistema.originar_operacion(factura_input)
        
        # Add metadata for display
        resultado['metadata'] = {
            "emisor": params.get('emisor_nombre'),
            "ruc": params.get('emisor_ruc'),
            "factura": params.get('numero_factura')
        }
        
        return resultado
    except Exception as e:
        return {"error": f"Calculation Error: {str(e)}"}

# --- File Uploader Handler ---
def handle_file_upload():
    uploaded_file = st.sidebar.file_uploader("📂 Sube la factura (PDF) para analizar", type=["pdf"])
    
    if uploaded_file:
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

    # Initialize Session State for Agent Flow
    if "agent_state" not in st.session_state:
        st.session_state.agent_state = "IDLE" # IDLE, WAITING_CONFIRMATION, CALCULATED
    if "current_file" not in st.session_state:
        st.session_state.current_file = None
    if "extracted_proposal" not in st.session_state:
        st.session_state.extracted_proposal = None

    # File Input
    file_path, file_name = handle_file_upload()
    
    # Handle New File Upload
    if file_path and file_path != st.session_state.current_file:
        st.session_state.current_file = file_path
        st.session_state.agent_state = "IDLE" # Reset on new file
        # Auto-trigger extraction
        with st.spinner(f"⚡ Analizando {file_name}..."):
            result = tool_extract_invoice_data(file_path)
            st.session_state.extracted_proposal = result
            st.session_state.agent_state = "WAITING_CONFIRMATION"
            
            # Add implicit System Message to chat
            msg = f"He leído **{file_name}**. Emisor: {result['extracted_data']['emisor_nombre']}. Monto: {result['extracted_data']['monto_neto']}.\n"
            msg += f"Propongo: Tasa Mensual **{result['proposed_params']['tasa_interes_mensual_percent']}%**, Adelanto **{result['proposed_params']['tasa_avance_percent']}%**, Plazo **{result['proposed_params']['plazo_dias']} días**.\n"
            msg += "¿Estás de acuerdo o quieres cambiar algún valor?"
            st.session_state.messages.append({"role": "assistant", "content": msg})

    # Chat UI
    if not st.session_state.messages:
        st.session_state.messages.append({"role": "assistant", "content": "Hola! Sube una factura y validaremos los datos antes de calcular."})

    # Render Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User Input
    if prompt := st.chat_input("Escribe tu respuesta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Agent Response Logic
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # --- FLOW LOGIC ---
            response_text = "..."
            
            if st.session_state.agent_state == "WAITING_CONFIRMATION":
                # We expect the user to confirm or edit params
                # We use Gemini to interpret the user's intent and JSON-fy the final params
                current_proposal = st.session_state.extracted_proposal
                
                context_prompt = f"""
                You are a Financial Assistant.
                Current State: WAITING_FOR_USER_CONFIRMATION of Invoice Parameters.
                
                Original Extracted Data: {json.dumps(current_proposal['extracted_data'], default=str)}
                Original Proposed Params: {json.dumps(current_proposal['proposed_params'], default=str)}
                
                User Message: "{prompt}"
                
                Task:
                1. Interpret if the user CONFIRMS or wants to MODIFY values.
                2. If they modify (e.g. "change rate to 1.5"), update the params.
                3. Return a JSON with the FINAL parameters to use for calculation.
                4. Also return a boolean 'confirmed'.
                
                Output JSON Format ONLY:
                {{
                    "confirmed": true/false,
                    "final_params": {{
                        "monto_neto": float,
                        "tasa_avance_percent": float,
                        "tasa_interes_mensual_percent": float,
                        "plazo_dias": int,
                        "comision_minima": float,
                        "emisor_nombre": str,
                        "emisor_ruc": str,
                        "numero_factura": str
                    }},
                    "reply_to_user": "Text message confirming what we are doing"
                }}
                """
                
                try:
                    gen_resp = model.generate_content(context_prompt)
                    # Clean markdown code blocks from response
                    text_resp = gen_resp.text.replace("```json", "").replace("```", "")
                    decision = json.loads(text_resp)
                    
                    if decision["confirmed"]:
                        # PERFORM CALCULATION
                        calc_result = tool_calculate_factoring(decision["final_params"])
                        
                        # Generate Presentation
                        final_prompt = f"""
                        Act as Financial Analyst.
                        Calculation Result: {json.dumps(calc_result, default=str)}
                        
                        Create a nice Markdown summary of this Operation Profile (Proforma).
                        Include:
                        - Header: Operation for {decision['final_params']['emisor_nombre']}
                        - Table with: Amount, Net to Disburse, Interest, Fees.
                        - Ask if they want to save/process this.
                        """
                        final_gen = model.generate_content(final_prompt)
                        response_text = final_gen.text
                        st.session_state.agent_state = "CALCULATED"
                    else:
                        # Just update params conceptually or ask for clarification (Agent reply)
                        response_text = decision["reply_to_user"]
                        
                except Exception as e:
                    response_text = f"Error interpretando tu respuesta: {e}. Intenta decir 'Confirmar' o 'Cambiar tasa a X'."

            else:
                # Normal chat (Idle or Post-Calculation)
                # Simple generation
                try:
                    chat = model.start_chat(history=[]) 
                    r = chat.send_message(prompt)
                    response_text = r.text
                except Exception as e:
                    response_text = f"Error: {e}"

            message_placeholder.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
