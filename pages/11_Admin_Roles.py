import streamlit as st
import pandas as pd
import src.data.supabase_repository as repo
from src.ui.header import render_header
from src.utils.email_integration import send_email_with_attachments

st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Administración de Roles",
    page_icon="🛡️"
)
render_header("Administración de Roles y Permisos")

# --- Initialize Session State ---
if 'roles_matrix_df' not in st.session_state:
    st.session_state['roles_matrix_df'] = None

def load_data():
    """Loads the permissions matrix from Supabase."""
    matrix_data = repo.get_full_permissions_matrix()
    if matrix_data:
        df = pd.DataFrame(matrix_data)
        st.session_state['roles_matrix_df'] = df
        st.session_state['original_matrix_df'] = df.copy() # Keep copy for diffing
    else:
        st.error("No se pudieron cargar los datos de roles.")

# Load on first run
if st.session_state['roles_matrix_df'] is None:
    load_data()

# --- Main UI ---
st.write("### Matriz de Acceso por Módulo")
st.info("Asigna usuarios a los roles. 'Super User' y 'Principal' tienen control total. 'Secundario' recibe notificación al ser asignado.")

if st.session_state['roles_matrix_df'] is not None:
    # Display Data Editor
    # We want Module Name to be read-only.
    
    edited_df = st.data_editor(
        st.session_state['roles_matrix_df'],
        use_container_width=True,
        hide_index=True,
        column_config={
            "module_id": None, # Hide ID
            "module_name": st.column_config.TextColumn("Módulo", disabled=True),
            "super_user": st.column_config.TextColumn("Super User", help="Admin supremo del módulo"),
            "principal": st.column_config.TextColumn("Principal", help="Dueño del proceso"),
            "secondary": st.column_config.TextColumn("Secundario", help="Usuario delegado. Recibirá notificación.")
        },
        key="roles_editor"
    )

    if st.button("Guardar Cambios y Notificar", type="primary"):
        original = st.session_state['original_matrix_df']
        changes_log = []
        errors_log = []
        
        # Iterate over edited rows
        for index, row in edited_df.iterrows():
            module_id = row['module_id']
            module_name = row['module_name']
            
            roles_map = {
                'super_user': row['super_user'],
                'principal': row['principal'],
                'secondary': row['secondary']
            }
            
            orig_row = original[original['module_id'] == module_id].iloc[0]
            
            for role_key, new_email in roles_map.items():
                old_email = orig_row[role_key]
                
                if new_email != old_email:
                    success, msg = repo.update_module_access_role(module_id, role_key, new_email)
                    if success:
                        changes_log.append(f"[{module_name}] {role_key}: {msg}")
                        if role_key == 'secondary' and new_email:
                            principal_email = row['principal']
                            subject = f"Acceso Autorizado: Módulo {module_name}"
                            body = f"""Hola,
                            
Has sido autorizado para acceder al módulo '{module_name}'.

Autorizado por Principal: {principal_email if principal_email else 'Administrador'}

Puedes ingresar al sistema con tu credencial habitual.
                            """
                            email_ok, email_msg = send_email_with_attachments(
                                to_email=new_email,
                                subject=subject,
                                body=body,
                                cc_email=principal_email
                            )
                            if email_ok:
                                changes_log.append(f"   -> Notificación enviada a {new_email}")
                            else:
                                errors_log.append(f"   -> Falló envío de correo: {email_msg}")
                    else:
                        errors_log.append(f"[{module_name}] Error en {role_key}: {msg}")

        # Display results properly
        if changes_log:
            st.success("✅ Cambios realizados:")
            for log in changes_log:
                st.write(f"- {log}")
        
        if errors_log:
            st.error("❌ Errores encontrados:")
            for err in errors_log:
                st.write(f"- {err}")
                
        if not changes_log and not errors_log:
            st.info("ℹ️ No se detectaron cambios.")
            
        if changes_log:
            # Refresh data but DO NOT rerun immediately to let user see the message
            # We explicitly update the session state data
            updated_matrix = repo.get_full_permissions_matrix()
            if updated_matrix:
                st.session_state['roles_matrix_df'] = pd.DataFrame(updated_matrix)
                st.session_state['original_matrix_df'] = st.session_state['roles_matrix_df'].copy()
            st.warning("Los datos se han actualizado. Puedes seguir editando.")

