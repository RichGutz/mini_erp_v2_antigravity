"""
Módulo de Limpieza de Base de Datos
Interfaz para limpiar tablas operacionales de Supabase de forma segura
"""

import streamlit as st
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.supabase_client import get_supabase_client

# ============================================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Limpieza de Base de Datos",
    page_icon="🗑️",
    layout="wide"
)

# --- Header y Configuración ---
from src.ui.header import render_header
render_header("Limpieza de Base de Datos")

# --- CSS Alignment Fix ---
st.markdown('''<style>
[data-testid="stHorizontalBlock"] { 
    align-items: center; 
}
</style>''', unsafe_allow_html=True)

# ============================================================================
# FUNCIONES
# ============================================================================

def contar_registros_tabla(supabase, tabla):
    """Cuenta los registros en una tabla"""
    try:
        response = supabase.table(tabla).select('*', count='exact').execute()
        return response.count if hasattr(response, 'count') else len(response.data)
    except Exception as e:
        return f"Error: {str(e)}"


def limpiar_tabla(supabase, tabla):
    """Limpia todos los registros de una tabla"""
    try:
        # Obtener todos los registros
        response = supabase.table(tabla).select('*').execute()
        count = len(response.data) if response.data else 0
        
        if count == 0:
            return 0, "Tabla ya vacía"
        
        # Borrar todos los registros
        if tabla == 'propuestas':
            # Para propuestas, usar proposal_id
            for record in response.data:
                supabase.table(tabla).delete().eq('proposal_id', record['proposal_id']).execute()
        else:
            # Para otras tablas, usar id
            for record in response.data:
                supabase.table(tabla).delete().eq('id', record['id']).execute()
        
        return count, "Éxito"
        
    except Exception as e:
        return 0, f"Error: {str(e)}"


# ============================================================================
# ESTADO DE SESIÓN
# ============================================================================

if 'confirmacion_limpieza' not in st.session_state:
    st.session_state.confirmacion_limpieza = False

if 'limpieza_ejecutada' not in st.session_state:
    st.session_state.limpieza_ejecutada = False

# ============================================================================
# UI PRINCIPAL
# ============================================================================

# Información de las tablas
st.header("📊 Estado Actual de las Tablas")

tablas_operacionales = [
    ('propuestas', 'Propuestas de factoring guardadas'),
    ('liquidaciones_resumen', 'Resumen de liquidaciones'),
    ('liquidacion_eventos', 'Eventos de liquidación'),
    ('desembolsos_resumen', 'Resumen de desembolsos'),
    ('desembolso_eventos', 'Eventos de desembolso'),
    ('auditoria_eventos', 'Registro de auditoría')
]

tablas_configuracion = [
    ('authorized_users', 'Usuarios autorizados del sistema'),
    ('modules', 'Módulos del sistema'),
    ('user_module_access', 'Permisos de acceso por usuario'),
    ('EMISORES.ACEPTANTES', 'Catálogo de empresas (RUC y razones sociales)')
]

# Obtener cliente de Supabase
try:
    supabase = get_supabase_client()
    
    # Mostrar tablas operacionales
    st.subheader("✅ Tablas que SE LIMPIARÁN")
    
    col1, col2, col3 = st.columns([3, 5, 2])
    
    with col1:
        st.markdown("**Tabla**")
    with col2:
        st.markdown("**Descripción**")
    with col3:
        st.markdown("**Registros**")
    
    st.markdown("---")
    
    total_registros_operacionales = 0
    
    for tabla, descripcion in tablas_operacionales:
        col1, col2, col3 = st.columns([3, 5, 2])
        
        with col1:
            st.markdown(f"`{tabla}`")
        with col2:
            st.markdown(descripcion)
        with col3:
            count = contar_registros_tabla(supabase, tabla)
            if isinstance(count, int):
                total_registros_operacionales += count
                st.metric("", f"{count:,}")
            else:
                st.error(count)
    
    st.markdown("---")
    st.metric("**Total de registros a eliminar**", f"{total_registros_operacionales:,}", 
             delta="Datos operacionales")
    
    st.markdown("")
    
    # Mostrar tablas de configuración
    st.subheader("❌ Tablas que NO SE TOCARÁN (Configuración)")
    
    col1, col2, col3 = st.columns([3, 5, 2])
    
    with col1:
        st.markdown("**Tabla**")
    with col2:
        st.markdown("**Descripción**")
    with col3:
        st.markdown("**Registros**")
    
    st.markdown("---")
    
    for tabla, descripcion in tablas_configuracion:
        col1, col2, col3 = st.columns([3, 5, 2])
        
        with col1:
            st.markdown(f"`{tabla}`")
        with col2:
            st.markdown(descripcion)
        with col3:
            count = contar_registros_tabla(supabase, tabla)
            if isinstance(count, int):
                st.info(f"{count:,}")
            else:
                st.error(count)
    
    # Sección de limpieza
    st.markdown("---")
    st.header("🗑️ Ejecutar Limpieza")
    
    if total_registros_operacionales == 0:
        st.success("✅ No hay datos operacionales para limpiar. La base de datos ya está limpia.")
    else:
        st.warning(f"⚠️ **ADVERTENCIA:** Esta acción eliminará **{total_registros_operacionales:,} registros** de forma permanente.")
        
        st.markdown("")
        
        # Checkbox de confirmación
        confirmacion = st.checkbox(
            f"Entiendo que se eliminarán {total_registros_operacionales:,} registros de forma permanente",
            key="checkbox_confirmacion"
        )
        
        st.session_state.confirmacion_limpieza = confirmacion
        
        st.markdown("")
        
        # Botón de limpieza
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button(
                "🗑️ EJECUTAR LIMPIEZA",
                type="primary",
                disabled=not st.session_state.confirmacion_limpieza,
                use_container_width=True
            ):
                # Ejecutar limpieza
                st.session_state.limpieza_ejecutada = True
                
                with st.spinner("Limpiando base de datos..."):
                    resultados = []
                    total_eliminados = 0
                    
                    # Limpiar en orden (respetando foreign keys)
                    for tabla, descripcion in tablas_operacionales:
                        count, status = limpiar_tabla(supabase, tabla)
                        total_eliminados += count
                        resultados.append({
                            'tabla': tabla,
                            'registros': count,
                            'status': status
                        })
                    
                    # Mostrar resultados
                    st.success(f"✅ Limpieza completada. Total de registros eliminados: {total_eliminados:,}")
                    
                    st.markdown("### Detalle de la limpieza:")
                    
                    for resultado in resultados:
                        if resultado['status'] == "Éxito":
                            if resultado['registros'] > 0:
                                st.success(f"✓ `{resultado['tabla']}`: {resultado['registros']:,} registros eliminados")
                            else:
                                st.info(f"○ `{resultado['tabla']}`: Ya estaba vacía")
                        else:
                            st.error(f"✗ `{resultado['tabla']}`: {resultado['status']}")
                    
                    # Resetear confirmación
                    st.session_state.confirmacion_limpieza = False
                    
                    st.markdown("")
                    st.info("💡 Recarga la página para ver el estado actualizado de las tablas.")

except Exception as e:
    st.error(f"❌ Error al conectar con Supabase: {str(e)}")
    st.info("Verifica que las credenciales de Supabase estén configuradas correctamente.")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption("🗑️ Módulo de Limpieza de Base de Datos | Mini ERP V2")
st.caption("⚠️ **Importante:** Esta herramienta solo elimina datos operacionales. Los usuarios, módulos y catálogos permanecen intactos.")
