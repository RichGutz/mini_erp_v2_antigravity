import sys
import os
import streamlit as st
from streamlit_mermaid import st_mermaid
from streamlit_oauth import OAuth2Component
import base64
import json
from src.data import supabase_repository as db

# --- PATH SETUP ---
# Add the project root to the Python path. This allows absolute imports from 'src'.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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

# --- AUTHENTICATION SETUP ---
# 1. Load credentials from secrets.toml
credentials = st.secrets['google_oauth']
client_id = credentials['client_id']
client_secret = credentials['client_secret']

# --- Lógica de Redirección Dinámica ---
try:
    # This will be used in the cloud
    redirect_uri = credentials['redirect_uri']
except KeyError:
    # This will be used for local development
    redirect_uri = "http://localhost:8504"

# ==========================================
# MAIN APP LOGIC
# ==========================================

if 'user_info' not in st.session_state:
    # ------------------------------------------
    # CASE 1: NOT AUTHENTICATED -> LANDING PAGE
    # ------------------------------------------
    
    # 1. Hide Sidebar
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True
    )

    # 2. Centered Layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True) # Top spacing
        
        # Logos Container - Centered and Resized
        with st.container(border=False):
            # Using [2, 3, 3, 2] to center the two logos horizontally
            # This pushes them towards the center while giving them enough space (30% width each)
            lc1, lc2, lc3, lc4 = st.columns([2, 3, 3, 2])
            
            with lc2:
                # Logo Geesoft
                st.image(os.path.join(project_root, "static", "logo_geek.png"), width=220) 
            with lc3:
                # Logo Inandes
                st.image(os.path.join(project_root, "static", "logo_inandes.png"), width=220)
        
        st.markdown("<h3 style='text-align: center; color: #666; font-weight: normal;'>Acceso Corporativo</h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # 3. Login Button & Logic
        oauth2 = OAuth2Component(client_id, client_secret, AUTHORIZE_URL, TOKEN_URL, REVOKE_URL)
        result = oauth2.authorize_button(
            name="Iniciar Sesión con Google",
            icon="https://www.google.com.tw/favicon.ico",
            redirect_uri=redirect_uri,
            scope="openid email profile https://www.googleapis.com/auth/drive",
            key="google",
            use_container_width=True,
            pkce='S256',
        )
        
        if result:
            # The result contains the token, decode the id_token to get user info
            id_token = result['token']['id_token']
            
            # Decode payload
            payload = id_token.split('.')[1]
            payload += '=' * (-len(payload) % 4)
            decoded_payload = json.loads(base64.b64decode(payload))
            
            user_email = decoded_payload.get('email')
            if user_email:
                # 1. Check if user exists in authorized_users table
                user_record = db.get_user_by_email(user_email)

                if user_record is None:
                    # User not found, attempt autoregistration
                    st.info(f"Registrando nuevo usuario: {user_email}")
                    user_record = db.add_new_authorized_user(user_email)
                    if user_record:
                        user_id = user_record['id']
                        # Grant Home access
                        home_module = db.get_module_by_name("Home")
                        if home_module is None:
                            st.warning("Módulo 'Home' no encontrado. Creándolo automáticamente.")
                            home_module = db.add_module("Home", "Página de inicio de la aplicación.")
                        
                        if home_module:
                            db.add_user_module_access(user_id, home_module['id'], 'viewer')
                            st.success(f"Usuario registrado correctamente.")
                        else:
                            st.error("Error crítico: No se pudo configurar acceso a 'Home'.")
                            st.stop()
                    else:
                        st.error("Error al registrar el nuevo usuario en base de datos.")
                        st.stop()
                
                # Verify active status and access
                if user_record:
                    if not user_record.get('is_active', False):
                        st.error("Su cuenta está inactiva. Contacte al administrador.")
                        st.stop()

                    home_module = db.get_module_by_name("Home")
                    if home_module:
                        user_access = db.get_user_module_access(user_record['id'], home_module['id'])
                        if user_access is None:
                            st.error("No tiene permisos para acceder al módulo 'Home'.")
                            st.stop()

                        # --- SUCCESSFUL LOGIN ---
                        st.session_state.user_info = decoded_payload
                        
                        # Store token (string only)
                        if isinstance(result['token'], dict):
                            st.session_state.token = result['token'].get('access_token')
                        else:
                            st.session_state.token = result['token']
                            
                        st.session_state.user_db_id = user_record['id']
                        st.session_state.user_hierarchy_level = user_access['hierarchy_level']

                        st.query_params.clear()
                        st.rerun()
                    else:
                         st.error("Configuración de sistema incompleta (Módulo Home missing).")
            else:
                st.error("No se pudo obtener el email del proveedor de identidad.")

else:
    # ------------------------------------------
    # CASE 2: AUTHENTICATED -> DASHBOARD
    # ------------------------------------------
    
    user_info = st.session_state.user_info
    
    # Sidebar Logout
    with st.sidebar:
        st.write(f"Hola, *{user_info.get('name', 'User')}*")
        if st.button("Cerrar Sesión", use_container_width=True, type="primary"):
            del st.session_state.user_info
            if 'token' in st.session_state:
                del st.session_state.token
            st.rerun()
        st.divider()

    st.write(f"Bienvenido al ERP, *{user_info.get('name', 'User')}*!")
    
    # --- NAVIGATION HELPER ---
    def switch_page(page_name):
        st.switch_page(f"pages/{page_name}.py")

    # --- MODULES CONFIG ---
    MODULES = {
        "Registro": {"status": "✅ En Producción", "help": "Gestión de emisores y aceptantes. Permite crear, consultar y modificar registros de clientes.", "page": "01_Registro"},
        "Originación": {"status": "✅ En Producción", "help": "Gestión de operaciones para clientes existentes. Permite crear anexos, procesar facturas y generar los perfiles de la operación.", "page": "02_Originacion"},
        "Aprobación": {"status": "✅ En Producción", "help": "Revisión y aprobación gerencial de operaciones. Permite aprobar operaciones antes de que pasen a desembolso.", "page": "03_Aprobacion"},
        "Desembolso": {"status": "✅ En Producción", "help": "Automatiza la solicitud de Letras Electrónicas, contrasta datos y gestiona la aprobación del desembolso.", "page": "04_Desembolso"},
        "Liquidación": {"status": "✅ En Producción", "help": "Procesa los pagos recibidos, determina si fueron a tiempo, anticipados o tardíos, y calcula los ajustes finales.", "page": "05_Liquidacion"},
        "Reporte": {"status": "📝 Planeado", "help": "Generación de reportes gerenciales (volumen, mora, etc.) y tributarios.", "page": "06_Reporte"},
        "Repositorio": {"status": "✅ En Producción", "help": "Gestor documental integrado con Google Drive. Visualización y descarga de expedientes.", "page": "07_Repositorio"},
        "Calculadora": {"status": "✅ En Producción", "help": "Simulaciones y cálculos manuales de operaciones de factoring.", "page": "08_Calculadora_Factoring"},
        "Limpieza BD": {"status": "⚠️ Mantenimiento", "help": "Herramientas para purgar y corregir datos en Base de Datos.", "page": "09_Limpieza_Base_Datos"},
        "Testing Liq.": {"status": "🧪 Testing", "help": "Módulo de pruebas unitarias y validación para el motor de liquidaciones.", "page": "10_Testing_Liquidacion_Universal"}
    }

    # --- MODULE NAVIGATION GRID ---
    st.subheader("Mapa de Módulos del Sistema", divider='blue')

    grid_layout = [
        ["Registro", "Originación", "Aprobación", "Desembolso"],
        ["Liquidación", "Reporte", "Repositorio", "Calculadora"],
        ["Limpieza BD", "Testing Liq.", None, None]
    ]

    for row in grid_layout:
        cols = st.columns(4)
        for i, module_name in enumerate(row):
            with cols[i]:
                if module_name is None:
                    st.write("")
                else:
                    details = MODULES[module_name]
                    status_text = details['status']
                    
                    if "✅" in status_text:
                        title_color = "green"
                    elif "⚠️" in status_text:
                        title_color = "orange"
                    elif "🧪" in status_text:
                        title_color = "purple"
                    else:
                        title_color = "gray"

                    with st.container(border=True):
                        st.markdown(f'<h4 style="color:{title_color}; text-align:center;">{module_name}</h4>', unsafe_allow_html=True)
                        st.caption(f"Status: {status_text}")
                        st.markdown("&nbsp;")
                        
                        if st.button(f"Abrir", help=details["help"], key=f"btn_{module_name}", use_container_width=True):
                            switch_page(details['page'])

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
