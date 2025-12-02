import sys
import os
# --- PATH SETUP ---
# Add the project root to the Python path. This allows absolute imports from 'src'.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now imports like `from src.services import ...` will work from any script.

import streamlit as st



from streamlit_mermaid import st_mermaid
from streamlit_oauth import OAuth2Component
import base64
import json
from src.data import supabase_repository as db

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="INANDES Factoring ERP - Inicio",
    page_icon=os.path.join(project_root, "static", "logo_geek.png"),
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- OAUTH2 ---
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# --- AUTHENTICATION ---
# 1. Load credentials from secrets.toml
credentials = st.secrets['google_oauth']
client_id = credentials['client_id']
client_secret = credentials['client_secret']

# --- Lógica de Redirección Dinámica ---
# Si st.secrets tiene una URI, úsala (para la nube). Si no, usa la local.
try:
    # This will be used in the cloud
    redirect_uri = credentials['redirect_uri']
except KeyError:
    # This will be used for local development
    redirect_uri = "http://localhost:8504"

# authorized_users = credentials['authorized_users'] # No longer needed, managed by Supabase

# 2. Check if user is authenticated
if 'user_info' not in st.session_state:
    # Create an oauth2 component
    oauth2 = OAuth2Component(client_id, client_secret, AUTHORIZE_URL, TOKEN_URL, REVOKE_URL)
    result = oauth2.authorize_button(
        name="Continue with Google",
        icon="https://www.google.com.tw/favicon.ico",
        redirect_uri=redirect_uri,
        scope="openid email profile",
        key="google",
        use_container_width=True,
        pkce='S256',
    )
    
    if result:
        # The result contains the token, decode the id_token to get user info
        id_token = result['token']['id_token']
        
        # Verify the signature is an optional step for security
        # Here we just decode the payload to get user info
        payload = id_token.split('.')[1]
        # Add padding if needed
        payload += '=' * (-len(payload) % 4)
        decoded_payload = json.loads(base64.b64decode(payload))
        
        user_email = decoded_payload.get('email')
        if user_email:
            # 1. Check if user exists in authorized_users table
            user_record = db.get_user_by_email(user_email)

            if user_record is None:
                # User not found, add them to authorized_users
                st.info(f"Registrando nuevo usuario: {user_email}")
                user_record = db.add_new_authorized_user(user_email)
                if user_record:
                    user_id = user_record['id']
                    # Automatically grant access to 'Home' module for new users
                    home_module = db.get_module_by_name("Home")
                    if home_module is None:
                        # If 'Home' module doesn't exist, create it (one-time setup)
                        st.warning("Módulo 'Home' no encontrado. Creándolo automáticamente.")
                        home_module = db.add_module("Home", "Página de inicio de la aplicación.")
                    
                    if home_module:
                        db.add_user_module_access(user_id, home_module['id'], 'viewer')
                        st.success(f"Usuario {user_email} registrado y acceso a 'Home' concedido.")
                    else:
                        st.error("Error al configurar el módulo 'Home'. Contacte al administrador.")
                        st.stop() # Stop execution if critical setup fails
                else:
                    st.error("Error al registrar el nuevo usuario. Contacte al administrador.")
                    st.stop() # Stop execution if critical setup fails
            
            # Ensure user_record is valid after potential creation
            if user_record:
                # 2. Check if user is active
                if not user_record.get('is_active', False):
                    st.error("Su cuenta está inactiva. Por favor, contacte al administrador.")
                    st.stop() # Stop execution for inactive users

                # 3. Check module access (for 'Home' module in this case)
                # First, ensure 'Home' module exists and get its ID
                home_module = db.get_module_by_name("Home")
                if home_module is None:
                    st.error("Módulo 'Home' no configurado en la base de datos. Contacte al administrador.")
                    st.stop() # Stop execution if module not configured

                user_access = db.get_user_module_access(user_record['id'], home_module['id'])
                if user_access is None:
                    st.error("Acceso denegado al módulo 'Home'. Por favor, contacte al administrador.")
                    st.stop() # Stop execution if no access record

                # Assuming 'viewer' is the minimum hierarchy_level for basic access
                # You might want more granular checks here based on hierarchy_level
                # For now, any access record means they can proceed.

                # If all checks pass, store user info in session state
                st.session_state.user_info = decoded_payload
                st.session_state.token = result['token']
                st.session_state.user_db_id = user_record['id'] # Store DB ID for future use
                st.session_state.user_hierarchy_level = user_access['hierarchy_level'] # Store hierarchy for current module

                # Clear query parameters and rerun
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Error inesperado al procesar el usuario. Contacte al administrador.")
        else:
            st.error("No se pudo obtener la dirección de correo electrónico del usuario. Intente de nuevo.")

else:
    # User is authenticated, show the main app
    user_info = st.session_state.user_info
    st.write(f"Welcome, *{user_info.get('name', 'User')}*!")
    
    if st.button("Logout"):
        del st.session_state.user_info
        del st.session_state.token
        st.rerun()

    # --- NAVIGATION ---
    def switch_page(page_name):
        # For manual switching, we must provide the full path from the root.
        st.switch_page(f"pages/{page_name}.py")

    # --- DATA & ORDER ---
    MODULES = {
        "Registro": {"status": "📝 Planeado", "help": "Manejo de nuevos clientes, incluyendo la creación de perfiles, generación de contratos y gestión de firmas electrónicas.", "page": None},
        "Originación": {"status": "✅ En Producción", "help": "Gestión de operaciones para clientes existentes. Permite crear anexos, procesar facturas y generar los perfiles de la operación.", "page": "01_Operaciones"},
        "Desembolso": {"status": "✅ En Producción", "help": "Automatiza la solicitud de Letras Electrónicas, contrasta datos y gestiona la aprobación del desembolso.", "page": "02_Desembolsos"},
        "Liquidación": {"status": "✅ En Producción", "help": "Procesa los pagos recibidos, determina si fueron a tiempo, anticipados o tardíos, y calcula los ajustes finales.", "page": "03_Liquidaciones"},
        "Reporte": {"status": "📝 Planeado", "help": "Generación de reportes gerenciales (volumen, mora, etc.) y tributarios para el análisis y control del negocio.", "page": None},
        "Calculadora Factoring": {"status": "✅ En Producción", "help": "Permite realizar simulaciones y cálculos manuales de operaciones de factoring.", "page": "07_Calculadora_Factoring"}
    }

    DISPLAY_ORDER = ["Registro", "Originación", "Desembolso", "Liquidación", "Reporte", "Calculadora Factoring"]

    # --- STYLING ---
    st.markdown("""<style>
        /* Center align the main header logos and title */
        [data-testid="stHorizontalBlock"] { 
            align-items: center; 
        }
    </style>""", unsafe_allow_html=True)

    # --- HEADER ---
    col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
    with col1:
        st.image(os.path.join(project_root, "static", "logo_geek.png"), width=200)
    with col2:
        st.markdown("<h1 style='text-align: center; color: black;'>ERP Factoring</h1>", unsafe_allow_html=True)
    with col3:
        empty_col, logo_col = st.columns([1, 2])
        with logo_col:
            st.image(os.path.join(project_root, "static", "logo_inandes.png"), width=195)

    st.markdown("&nbsp;")

    # --- MODULE NAVIGATION ---
    st.subheader("Flujo de Módulos del Sistema", divider='blue')

    # Create a 3-column layout
    cols = st.columns(3)

    for i, module_name in enumerate(DISPLAY_ORDER):
        details = MODULES[module_name]
        is_prod = details['status'] == "✅ En Producción"
        col = cols[i % 3]

        with col:
            with st.container(border=True):
                # Set title color based on status
                title_color = "green" if is_prod else "red"
                st.markdown(f'<h4 style="color:{title_color};">{module_name}</h4>', unsafe_allow_html=True)
                
                st.markdown("&nbsp;") # Spacer for vertical alignment
                
                # --- NEW BUTTON LOGIC ---
                if details["page"]:
                    # Use a standard 'if' block to handle navigation instead of on_click
                    if st.button(f"Ir a {module_name}", help=details["help"], key=f"btn_{module_name}", use_container_width=True):
                        switch_page(details['page'])
                else:
                    st.button("Próximamente", 
                              disabled=True, 
                              help=details["help"],
                              key=f"btn_{module_name}",
                              use_container_width=True)

    # --- INTERACTIVE FLOWCHART ---
    st.markdown("&nbsp;")
    st.subheader("Hoja de Ruta Visual (Work in Progress)", divider='blue')

    mermaid_code = """graph TD
        A["Start Operacion de Factoring Aprobada"] --> B{Es una operacion nueva};

        B --o|Si| SW_MODULO_CLIENTES["Módulo Registro"];
        SW_MODULO_CLIENTES --> SW_PASO_1["Crear perfil de cliente RUC, firmas, contactos, etc"];
        SW_PASO_1 --> SW_PASO_2["Crear Repositorio Google Drive Razon Social con subcarpetas Legal y Riesgos"];
        SW_PASO_2 --> SW_GEN_DOCS["SW Con datos del cliente y plantillas, se generan Contrato, Pagare y Acuerdos"];
        SW_GEN_DOCS --> SW_SEND_KEYNUA["SW Se envia a Keynua via API para firma electronica"];
        SW_SEND_KEYNUA --> SW_KEYNUA_CONFIRM["SW Confirmacion de firma recibida via API"];
        SW_KEYNUA_CONFIRM --> K;

        B --o|No| SW_MODULO_OPERACIONES["Módulo Originación"];
        SW_MODULO_OPERACIONES --> SW_CREAR_ANEXO["Crear Anexo de Contrato y su carpeta en G.Drive"];
        SW_CREAR_ANEXO --> K;

        K["Subir facturas a la nueva carpeta del anexo"] --> SW_PROCESAR_FACTURAS["SW Procesa facturas con logica de frontend_app_V.CLI.py"];
        SW_PROCESAR_FACTURAS --> SW_CREAR_PERFIL_OP["SW Crea perfil de operacion y lo sube a Supabase"];
        SW_CREAR_PERFIL_OP --> L["Enviar correo de confirmacion al pagador"];
        L --> M{Pagador contesto?};
        M --o|No| N_STANDBY["Operacion en Stand-By"];
        N_STANDBY --> L;
        M --o|Si| O["Preparar Proforma PDF y Solicitud Word"];

        O --> P["Subir XML de facturas a Cavali"];
        P --> Q{Hay conformidad de las facturas?};
        Q --o|No| R_STANDBY["Operacion en Stand-By e Insistir por correo para conformidad"];
        R_STANDBY --> Q;

        Q --o|Si| SW_MODULO_DESEMBOLSO["Módulo Desembolso"];
        SW_MODULO_DESEMBOLSO --> SW_GET_CAVALI["Solicita y recibe Letra Electronica de Cavali"];
        SW_GET_CAVALI --> SW_CONTRASTE["Contrasta datos Cavali vs. Proforma de Supabase"];
        SW_CONTRASTE --> VERIFICACION{Datos coinciden?};
        VERIFICACION --o|No| SW_GET_CAVALI;
        VERIFICACION --o|Si| SW_APROBACION["Se aprueba el desembolso"];
        SW_APROBACION --> T["Desembolsar"];
        T --> SW_FACTURACION["Genera datos/formato para Modulo de Facturacion Electronica"];

        SW_FACTURACION --> SW_MODULO_LIQUIDACION["Módulo Liquidación"];
        SW_MODULO_LIQUIDACION --> SW_RECEPCION_PAGO["Recibir evidencia de pago voucher"];
        SW_RECEPCION_PAGO --> SW_COMPARAR_FECHAS["Comparar Fecha de Pago Real vs. Fecha Esperada"];
        SW_COMPARAR_FECHAS --> TIPO_PAGO{Completo o Parcial};

        TIPO_PAGO --o|Completo| TIPO_PAGO_COMPLETO{Tipo de Pago Completo};
        TIPO_PAGO_COMPLETO --o|Anticipado| SW_PAGO_ANTICIPADO["SW Calcula intereses en exceso"];
        SW_PAGO_ANTICIPADO --> SW_GEN_NC["SW Registra necesidad de Nota de Credito Neteo"];
        SW_GEN_NC --> CIERRE_FINAL;
        TIPO_PAGO_COMPLETO --o|A Tiempo| CIERRE_FINAL;
        TIPO_PAGO_COMPLETO --o|Tardio| SW_PAGO_TARDIO["SW Calcula Intereses Compensatorios y Moratorios opcional"];
        SW_PAGO_TARDIO --> SW_GEN_FACTURA["SW Registra necesidad de Nueva Factura por intereses"];
        SW_GEN_FACTURA --> CIERRE_FINAL;

        TIPO_PAGO --o|Parcial| TIPO_PAGO_PARCIAL{Tipo de Pago Parcial};
        TIPO_PAGO_PARCIAL --o|A Tiempo| EN_PROCESO_LIQUIDACION["EN PROCESO DE LIQUIDACION"];
        TIPO_PAGO_PARCIAL --o|Tardio| EN_PROCESO_LIQUIDACION;
        EN_PROCESO_LIQUIDACION --> SW_RECEPCION_PAGO;

        CIERRE_FINAL["Marcar Operacion como LIQUIDADA"] --> MODULO_REPORTE["Módulo Reporte"];
        MODULO_REPORTE --> REPORTES_GERENCIALES["Reportes Gerenciales"];
        MODULO_REPORTE --> REPORTES_TRIBUTARIOS["Reportes Tributarios"];

        REPORTES_GERENCIALES --> REPORTE_VOLUMEN_CARTERA["Reportes de Volumen de Cartera"];
        REPORTES_GERENCIALES --> CARTERA_MORA["Cartera en Mora"];
        REPORTES_GERENCIALES --> RETRASOS["Retrasos"];
        REPORTES_GERENCIALES --> COBRANZA_COACTIVA["en cobranza coactivia"];
        REPORTES_GERENCIALES --> REPORTE_GERENCIAL_INTERACTIVO["Reporte Gerencial Interactivo"];

        REPORTES_TRIBUTARIOS --> REPORTE_FACTURAS["Reporte de Facturas"];
        REPORTES_TRIBUTARIOS --> REPORTE_LIQUIDACIONES["Reporte de Liquidaciones"];
        REPORTES_TRIBUTARIOS --> REPORTE_DESEMBOLSOS["Reporte de Desembolsos"];

        REPORTE_VOLUMEN_CARTERA --> Z;
        CARTERA_MORA --> Z;
        RETRASOS --> Z;
        COBRANZA_COACTIVA --> Z;
        REPORTE_GERENCIAL_INTERACTIVO --> Z;
        REPORTE_FACTURAS --> Z;
        REPORTE_LIQUIDACIONES --> Z;
        REPORTE_DESEMBOLSOS --> Z;
        Z["End Proceso Finalizado"];

        SW_CALCULADORA_FACTORING["Módulo Calculadora Factoring"];

        classDef standby fill:#f9f,stroke:#333,stroke-width:2px
        classDef module fill:#ff0000,stroke:#333,stroke-width:2px

        class N_STANDBY,R_STANDBY,H_STANDBY,EN_PROCESO_LIQUIDACION standby
        class SW_MODULO_CLIENTES,SW_MODULO_OPERACIONES,SW_MODULO_DESEMBOLSO,SW_MODULO_LIQUIDACION,MODULO_REPORTE,REPORTES_GERENCIALES,REPORTES_TRIBUTARIOS,SW_CALCULADORA_FACTORING module
    """
    st_mermaid(mermaid_code, height="800px")
