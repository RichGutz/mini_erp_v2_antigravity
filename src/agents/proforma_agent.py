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

from datetime import date, datetime

# --- Tool 1: Extraction & Proposal ---
def tool_extract_invoice_data(file_path):
    """
    Step 1: Parse PDF and propose parameters.
    Leaves 'plazo_dias' as None to force explicit user input or confirmation based on dates.
    """
    try:
        # 1. Parse
        parsed_data = pdf_parser.extract_fields_from_pdf(file_path)
        if parsed_data.get("error"):
            return {"error": f"Parsing Error: {parsed_data['error']}"}

        # 2. Extract Key Data
        ruc_emisor = parsed_data.get('emisor_ruc')
        monto_neto = parsed_data.get('monto_neto', 0.0)
        cliente_nombre = parsed_data.get('cliente_nombre', "Cliente Desconocido")
        fecha_emision = parsed_data.get('fecha_emision')
        fecha_vencimiento = parsed_data.get('fecha_vencimiento') # Might be None
        
        if not ruc_emisor:
            return {"error": "No RUC found in invoice"}
            
        # 3. DB Lookup
        db_rates = db.get_financial_conditions(str(ruc_emisor))
        emisor_nombre = db.get_razon_social_by_ruc(ruc_emisor) or parsed_data.get('emisor_nombre', "Desconocido")
        
        # 4. Propose Defaults
        tasa_avance = float(db_rates.get('tasa_avance', 98.0) if db_rates else 98.0)
        interes_mensual = float(db_rates.get('interes_mensual_pen', 1.25) if db_rates else 1.25) 
        
        # Critical: Do NOT assume 30 days. Try to calculate from parsed dates, else None.
        plazo_sugerido = None
        if fecha_emision and fecha_vencimiento:
            try:
                # Simple attempt to parse ISO or basic formats (Agent can correct later)
                # assuming input is YYYY-MM-DD for now or let LLM handle it.
                # For safety, we leave it as None to force verification unless perfectly clear.
                pass 
            except:
                pass

        proposal = {
            "status": "PROPOSAL_READY",
            "extracted_data": {
                "emisor_ruc": ruc_emisor,
                "emisor_nombre": emisor_nombre,
                "cliente_nombre": cliente_nombre,
                "numero_factura": parsed_data.get('invoice_id'),
                "moneda": parsed_data.get('moneda', 'PEN'),
                "monto_neto": monto_neto,
                "fecha_emision": fecha_emision,
                "fecha_vencimiento_pdf": fecha_vencimiento
            },
            "proposed_params": {
                "tasa_avance_percent": tasa_avance,
                "tasa_interes_mensual_percent": interes_mensual,
                "plazo_dias": plazo_sugerido, # Explicitly explicit
                "comision_minima": 0.0,
                "fecha_desembolso": datetime.now().strftime("%Y-%m-%d"), # Assume today as anchor
                "fecha_pago_esperada": fecha_vencimiento # Propose PDF due date
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
        # The logic for auto-triggering extraction is now moved into the chat input handling
        # to allow the user to explicitly "analizar" the document.
        # This block will now only reset the state on new file upload.

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
            
            # CASE 1: Trigger Analysis
            if st.session_state.agent_state in ["IDLE", "CALCULATED"] and file_path and any(k in prompt.lower() for k in ["analizar", "procesar", "leer", "extraer"]):
                with st.spinner(f"⚡ Analizando {file_name}..."):
                    result = tool_extract_invoice_data(file_path)
                    st.session_state.extracted_proposal = result
                    st.session_state.agent_state = "WAITING_CONFIRMATION"
                    
                    # Smart Message Construction
                    p = result['proposed_params']
                    e = result['extracted_data']
                    
                    msg = f"🔍 **Análisis de {file_name}**\n\n"
                    msg += f"- **Emisor**: {e['emisor_nombre']}\n"
                    msg += f"- **Monto**: {e['moneda']} {e['monto_neto']:,.2f}\n"
                    msg += f"- **Tasas BD**: Mensual {p['tasa_interes_mensual_percent']}%, Adelanto {p['tasa_avance_percent']}%\n\n"
                    
                    if p['plazo_dias'] is None:
                        msg += "⚠️ **Falta definir fechas:**\n"
                        msg += f"El PDF indica vencimiento el: *{e.get('fecha_vencimiento_pdf', 'No detectado')}*.\n"
                        msg += "**¿Cuál es la Fecha de Desembolso y la Fecha de Pago real?**"
                    else:
                        msg += f"Plazo calculado: {p['plazo_dias']} días. ¿Confirmas?"

                    response_text = msg

            # CASE 2: Handle Confirmation/Edit
            elif st.session_state.agent_state == "WAITING_CONFIRMATION":
                current = st.session_state.extracted_proposal
                
                context_prompt = f"""
                Act as a Financial Analyst.
                Current State: WAITING_FOR_USER_CONFIRMATION.
                
                Data: {json.dumps(current, default=str)}
                User Message: "{prompt}"
                Today: {datetime.now().strftime("%Y-%m-%d")}
                
                GOAL: Secure a precise 'plazo_dias' (term in days).
                
                Logic:
                1. If user provides Dates (e.g. "Payment on Dec 30"), calculate days from 'fecha_desembolso' (default today).
                2. If user provides explicit Days (e.g. "30 days"), use that.
                3. If 'plazo_dias' is still Unknown/None, DO NOT CONFIRM. Ask again.
                
                Output JSON:
                {{
                    "confirmed": boolean, (Only true if we have specific plazo_dias AND user said yes/confirm)
                    "final_params": {{
                        "monto_neto": float,
                        "tasa_avance_percent": float,
                        "tasa_interes_mensual_percent": float,
                        "plazo_dias": int, (MUST BE INTEGER)
                        "comision_minima": float,
                        "emisor_nombre": str,
                        "emisor_ruc": str,
                        "numero_factura": str
                    }},
                    "reply_to_user": "Message. If not confirmed, ask for the missing data clearly."
                }}
                """
                
                try:
                    gen_resp = model.generate_content(context_prompt)
                    text_resp = gen_resp.text.replace("```json", "").replace("```", "")
                    decision = json.loads(text_resp)
                    
                    if decision["confirmed"] and decision["final_params"]["plazo_dias"] is not None:
                        # PERFORM CALCULATION
                        calc_result = tool_calculate_factoring(decision["final_params"])
                        
                        final_prompt = f"""
                        Act as Financial Analyst.
                        Calculation Result: {json.dumps(calc_result, default=str)}
                        Create a Proforma Table (Markdown). Use MONEY format (S/ or $).
                        End with: "Para guardar esta operación, confirma con 'Guardar'."
                        """
                        final_gen = model.generate_content(final_prompt)
                        response_text = final_gen.text
                        st.session_state.agent_state = "CALCULATED"
                    else:
                        response_text = decision["reply_to_user"]
                        
                except Exception as e:
                    response_text = f"Error: {e}. Por favor, indica explícitamente la Fecha de Pago."

            # CASE 3: Normal Chat
            else:
                try:
                    chat = model.start_chat(history=[]) 
                    r = chat.send_message(prompt)
                    response_text = r.text
                except Exception as e:
                    response_text = f"Error: {e}"

            message_placeholder.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
