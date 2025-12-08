import streamlit as st
import sys
import os
import re

# Path setup
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data import supabase_repository as db

# Page config
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Módulo de Registro",
    page_icon="📋"
)

# Session state
if 'vista_registro' not in st.session_state:
    st.session_state.vista_registro = 'busqueda'  # 'busqueda', 'crear', 'editar'
if 'registro_encontrado' not in st.session_state:
    st.session_state.registro_encontrado = None

# CSS para campos obligatorios
st.markdown('''<style>
[data-testid="stHorizontalBlock"] { 
    align-items: center; 
}
.campo-obligatorio {
    background-color: #fff3cd;
    padding: 10px;
    border-radius: 5px;
    border-left: 4px solid #ffc107;
}
</style>''', unsafe_allow_html=True)

# Header
col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
with col1:
    st.image(os.path.join(project_root, "static", "logo_geek.png"), width=200)
with col2:
    st.markdown("<h2 style='text-align: center; font-size: 2.4em;'>Módulo de Registro</h2>", unsafe_allow_html=True)
with col3:
    empty_col, logo_col = st.columns([2, 1])
    with logo_col:
        st.image(os.path.join(project_root, "static", "logo_inandes.png"), width=195)


# Vistas
def mostrar_busqueda():
    """Vista principal: búsqueda por RUC"""
    st.header("Búsqueda de Emisor/Aceptante")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        ruc_buscar = st.text_input("🔍 Buscar por RUC", max_chars=11, help="Ingresa el RUC de 11 dígitos")
    with col2:
        st.write("")  # Espaciador
        st.write("")  # Espaciador
        if st.button("➕ Nuevo Registro", type="primary", use_container_width=True):
            st.session_state.vista_registro = 'crear'
            st.session_state.registro_encontrado = None
            st.rerun()
    
    if ruc_buscar:
        if not re.match(r'^\d{11}$', ruc_buscar):
            st.warning("⚠️ El RUC debe tener exactamente 11 dígitos numéricos")
        else:
            # Buscar en base de datos (búsqueda EXACTA por RUC)
            try:
                from src.data.supabase_repository import get_supabase_client
                supabase = get_supabase_client()
                response = supabase.table('EMISORES.ACEPTANTES').select('*').eq('RUC', ruc_buscar).execute()
                registros = response.data if response.data else []
            except Exception as e:
                st.error(f"Error al buscar: {str(e)}")
                registros = []
            
            if registros:
                st.success(f"✅ Se encontró registro con RUC: {ruc_buscar}")
                st.session_state.registro_encontrado = registros[0]
                st.session_state.vista_registro = 'editar'
                st.rerun()
            else:
                st.info(f"ℹ️ No se encontró ningún registro con RUC: {ruc_buscar}")
                if st.button("Crear nuevo registro con este RUC"):
                    st.session_state.registro_encontrado = {'RUC': ruc_buscar}
                    st.session_state.vista_registro = 'crear'
                    st.rerun()
    else:
        st.info("💡 Ingresa un RUC para buscar o crea un nuevo registro")


def mostrar_formulario_crear():
    """Vista de creación de nuevo registro con TODOS los campos"""
    st.header("Crear Nuevo Emisor/Aceptante")
    
    if st.button("← Volver a la búsqueda"):
        st.session_state.vista_registro = 'busqueda'
        st.session_state.registro_encontrado = None
        st.rerun()
    
    # Obtener RUC pre-cargado si viene de búsqueda
    ruc_precargado = st.session_state.registro_encontrado.get('RUC', '') if st.session_state.registro_encontrado else ''
    
    with st.form("form_crear"):
        st.markdown("### 📋 Campos Obligatorios")
        st.markdown('<div class="campo-obligatorio">', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            ruc = st.text_input("RUC *", value=ruc_precargado, max_chars=11, help="11 dígitos numéricos")
        with col2:
            tipo = st.selectbox("Tipo *", ["EMISOR", "ACEPTANTE"])
        
        razon_social = st.text_input("Razón Social *")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("### 📝 Campos Opcionales")
        st.markdown("---")
        
        # Depositarios
        st.subheader("Depositarios")
        col1, col2 = st.columns(2)
        with col1:
            depositario_1 = st.text_input("Depositario 1")
        with col2:
            dni_depositario_1 = st.text_input("DNI Depositario 1", max_chars=8)
        
        # Garantes/Fiadores
        st.subheader("Garantes/Fiadores Solidarios")
        col1, col2 = st.columns(2)
        with col1:
            garante_1 = st.text_input("Garante/Fiador solidario 1")
            garante_2 = st.text_input("Garante/Fiador solidario 2")
        with col2:
            dni_garante_1 = st.text_input("DNI Garante/Fiador solidario 1", max_chars=8)
            dni_garante_1 = st.text_input("DNI Garante/Fiador solidario 1", max_chars=8)
            dni_garante_2 = st.text_input("DNI Garante/Fiador solidario 2", max_chars=8)
        
        # Datos de Contacto
        st.subheader("Datos de Contacto (Emails)")
        col1, col2 = st.columns(2)
        with col1:
            correo_1 = st.text_input("Correo Electrónico 1", help="Email principal para notificaciones")
        with col2:
            correo_2 = st.text_input("Correo Electrónico 2", help="Email secundario (cc)")
        
        # Datos bancarios
        st.subheader("Datos Bancarios")
        
        # Lista de bancos de Perú
        bancos_peru = [
            "",  # Opción vacía
            "Banco de Crédito del Perú (BCP)",
            "BBVA Perú",
            "Scotiabank Perú",
            "Interbank",
            "Banco Pichincha",
            "Banco de Comercio",
            "Banco Interamericano de Finanzas (BanBif)",
            "Banco GNB Perú",
            "Banco Falabella",
            "Banco Ripley",
            "Banco Santander Perú",
            "Citibank Perú",
            "Banco Azteca",
            "Banco Cencosud (Scotiabank)",
            "ICBC Peru Bank",
            "Mibanco",
            "Banco de la Nación",
            "Banco Agropecuario (Agrobanco)",
            "Caja Municipal de Ahorro y Crédito",
            "Otro"
        ]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            institucion_financiera = st.selectbox("Institución Financiera", bancos_peru)
        with col2:
            numero_cuenta = st.text_input("Número de Cuenta (PEN)")
        with col3:
            cci = st.text_input("Número de CCI (PEN)", max_chars=20)
        
        submitted = st.form_submit_button("Crear Registro", type="primary")
        
        if submitted:
            # Validar campos obligatorios
            if not ruc or not razon_social or not tipo:
                st.error("❌ Por favor completa todos los campos obligatorios (RUC, Razón Social, Tipo)")
            elif not re.match(r'^\d{11}$', ruc):
                st.error("❌ El RUC debe tener exactamente 11 dígitos numéricos")
            else:
                # Crear registro con TODOS los campos
                data = {
                    'RUC': ruc,
                    'Razon Social': razon_social,
                    'TIPO': tipo,
                    'Depositario 1': depositario_1 or None,
                    'DNI Depositario 1': dni_depositario_1 or None,
                    'Garante/Fiador solidario 1': garante_1 or None,
                    'DNI Garante/Fiador solidario 1': dni_garante_1 or None,
                    'Garante/Fiador solidario 2': garante_2 or None,
                    'DNI Garante/Fiador solidario 2': dni_garante_2 or None,
                    'Institucion Financiera': institucion_financiera or None,
                    'Numero de Cuenta PEN': numero_cuenta or None,
                    'Numero de CCI PEN': cci or None,
                    'Correo Electronico 1': correo_1 or None,
                    'Correo Electronico 2': correo_2 or None
                }
                
                success, message = db.create_emisor_deudor(data)
                if success:
                    st.success(f"✅ {message}")
                    st.balloons()
                    st.session_state.vista_registro = 'busqueda'
                    st.session_state.registro_encontrado = None
                    st.rerun()
                else:
                    st.error(f"❌ {message}")


def mostrar_formulario_editar():
    """Vista de edición mostrando TODOS los campos"""
    st.header("Editar Emisor/Aceptante")
    
    if st.button("← Volver a la búsqueda"):
        st.session_state.vista_registro = 'busqueda'
        st.session_state.registro_encontrado = None
        st.rerun()
    
    registro = st.session_state.registro_encontrado
    if not registro:
        st.error("❌ No hay registro seleccionado")
        return
    
    st.info(f"**RUC:** {registro.get('RUC', 'N/A')} (no se puede modificar)")
    
    with st.form("form_editar"):
        st.markdown("### 📋 Campos Obligatorios")
        st.markdown('<div class="campo-obligatorio">', unsafe_allow_html=True)
        
        razon_social = st.text_input("Razón Social *", value=registro.get('Razon Social', ''))
        tipo = st.selectbox("Tipo *", ["EMISOR", "ACEPTANTE"], 
                           index=0 if registro.get('TIPO') == 'EMISOR' else 1)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("### 📝 Campos Opcionales")
        st.markdown("---")
        
        # Depositarios
        st.subheader("Depositarios")
        col1, col2 = st.columns(2)
        with col1:
            depositario_1 = st.text_input("Depositario 1", value=registro.get('Depositario 1', '') or '')
        with col2:
            dni_depositario_1 = st.text_input("DNI Depositario 1", value=registro.get('DNI Depositario 1', '') or '', max_chars=8)
        
        # Garantes/Fiadores
        st.subheader("Garantes/Fiadores Solidarios")
        col1, col2 = st.columns(2)
        with col1:
            garante_1 = st.text_input("Garante/Fiador solidario 1", value=registro.get('Garante/Fiador solidario 1', '') or '')
            garante_2 = st.text_input("Garante/Fiador solidario 2", value=registro.get('Garante/Fiador solidario 2', '') or '')
        with col2:
            dni_garante_1 = st.text_input("DNI Garante/Fiador solidario 1", value=registro.get('DNI Garante/Fiador solidario 1', '') or '', max_chars=8)
            dni_garante_2 = st.text_input("DNI Garante/Fiador solidario 2", value=registro.get('DNI Garante/Fiador solidario 2', '') or '', max_chars=8)
        
        # Datos de Contacto
        st.subheader("Datos de Contacto (Emails)")
        col1, col2 = st.columns(2)
        with col1:
            correo_1 = st.text_input("Correo Electrónico 1", value=registro.get('Correo Electronico 1', '') or '', help="Email principal para notificaciones")
        with col2:
            correo_2 = st.text_input("Correo Electrónico 2", value=registro.get('Correo Electronico 2', '') or '', help="Email secundario (cc)")
        
        # Datos bancarios
        st.subheader("Datos Bancarios")
        
        # Lista de bancos de Perú
        bancos_peru = [
            "",  # Opción vacía
            "Banco de Crédito del Perú (BCP)",
            "BBVA Perú",
            "Scotiabank Perú",
            "Interbank",
            "Banco Pichincha",
            "Banco de Comercio",
            "Banco Interamericano de Finanzas (BanBif)",
            "Banco GNB Perú",
            "Banco Falabella",
            "Banco Ripley",
            "Banco Santander Perú",
            "Citibank Perú",
            "Banco Azteca",
            "Banco Cencosud (Scotiabank)",
            "ICBC Peru Bank",
            "Mibanco",
            "Banco de la Nación",
            "Banco Agropecuario (Agrobanco)",
            "Caja Municipal de Ahorro y Crédito",
            "Otro"
        ]
        
        # Obtener valor actual y encontrar índice
        valor_actual = registro.get('Institucion Financiera', '') or ''
        try:
            index_banco = bancos_peru.index(valor_actual) if valor_actual in bancos_peru else 0
        except ValueError:
            index_banco = 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            institucion_financiera = st.selectbox("Institución Financiera", bancos_peru, index=index_banco)
        with col2:
            numero_cuenta = st.text_input("Número de Cuenta (PEN)", value=registro.get('Numero de Cuenta PEN', '') or '')
        with col3:
            cci = st.text_input("Número de CCI (PEN)", value=registro.get('Numero de CCI PEN', '') or '', max_chars=20)
        
        submitted = st.form_submit_button("Guardar Cambios", type="primary")
        
        if submitted:
            if not razon_social:
                st.error("❌ La Razón Social es obligatoria")
            else:
                # Actualizar con TODOS los campos
                data = {
                    'Razon Social': razon_social,
                    'TIPO': tipo,
                    'Depositario 1': depositario_1 or None,
                    'DNI Depositario 1': dni_depositario_1 or None,
                    'Garante/Fiador solidario 1': garante_1 or None,
                    'DNI Garante/Fiador solidario 1': dni_garante_1 or None,
                    'Garante/Fiador solidario 2': garante_2 or None,
                    'DNI Garante/Fiador solidario 2': dni_garante_2 or None,
                    'Institucion Financiera': institucion_financiera or None,
                    'Numero de Cuenta PEN': numero_cuenta or None,
                    'Numero de CCI PEN': cci or None,
                    'Correo Electronico 1': correo_1 or None,
                    'Correo Electronico 2': correo_2 or None
                }
                
                success, message = db.update_emisor_deudor(registro['RUC'], data)
                if success:
                    st.success(f"✅ {message}")
                    st.session_state.vista_registro = 'busqueda'
                    st.session_state.registro_encontrado = None
                    st.rerun()
                else:
                    st.error(f"❌ {message}")


# Router
if st.session_state.vista_registro == 'busqueda':
    mostrar_busqueda()
elif st.session_state.vista_registro == 'crear':
    mostrar_formulario_crear()
elif st.session_state.vista_registro == 'editar':
    mostrar_formulario_editar()
