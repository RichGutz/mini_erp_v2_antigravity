import streamlit as st
import requests
import json
from streamlit_google_picker import google_picker
import streamlit_google_picker.uploaded_file as lib_upl # Import for monkeypatching

# --- SHARED MONKEYPATCH ---
from contextlib import contextmanager

@contextmanager
def patch_picker_flatten():
    """
    Context manager to monkeypatch streamlit_google_picker's flatten_picker_result.
    This prevents the library from listing folder contents (which fails due to permissions)
    and handles result parsing robustly (List vs GooglePickerResult vs Dict).
    """
    original_flatten = lib_upl.flatten_picker_result
    
    def safe_flatten_picker_result(picker_result, token, use_cache=True):
         # picker_result might be a list directly or a dict with 'docs'
         if isinstance(picker_result, list):
             raw_docs = picker_result
         else:
             raw_docs = picker_result.get("docs", [])
             
         # The library expects objects with attributes (f.id), but our code uses .get()
         # We create a hybrid class to satisfy both.
         class PickerFile:
             def __init__(self, data):
                 self.data = data
                 for k, v in data.items():
                     setattr(self, k, v)
             def get(self, key, default=None):
                 return self.data.get(key, default)
             def __getitem__(self, key):
                 return self.data[key]
                 
         return [PickerFile(d) for d in raw_docs]

    try:
        lib_upl.flatten_picker_result = safe_flatten_picker_result
        yield
    finally:
        lib_upl.flatten_picker_result = original_flatten
# --------------------------

def get_service_account_token():
    """
    Genera un access_token temporal del Service Account para usar en el Google Picker.
    Esto permite que el Picker muestre SOLO carpetas del Drive del SA (no del usuario).
    """
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests
        
        # Obtener credenciales del Service Account
        sa_creds_dict = dict(st.secrets["google_drive"])
        
        # Fix de private_key si viene con \\n en lugar de \n
        if 'private_key' in sa_creds_dict:
            # CORREGIDO: era \\\\n, debe ser \\n
            original_key = sa_creds_dict['private_key']
            sa_creds_dict['private_key'] = original_key.replace('\\n', '\n')
            
            # Debug: verificar si se hizo el reemplazo
            if '\\n' in original_key:
                st.info("🔧 Debug: Private key tenía \\n, se convirtió a saltos de línea reales")
        
        # Crear credenciales con scope de Drive
        creds = service_account.Credentials.from_service_account_info(
            sa_creds_dict,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # Refrescar para obtener access_token
        creds.refresh(google.auth.transport.requests.Request())
        
        # Debug: confirmar que se generó el token
        if creds.token:
            st.success(f"✅ Token del Service Account generado exitosamente (longitud: {len(creds.token)})")
        
        return creds.token
        
    except Exception as e:
        st.error(f"❌ Error generando token del Service Account: {e}")
        import traceback
        st.code(traceback.format_exc())  # Mostrar stack trace completo
        return None
# --------------------------

def upload_file_to_drive(file_data, file_name, folder_id, access_token):
    """
    Uploads a file (bytes) to a specific Google Drive folder using the Drive API v3 (REST).
    """
    try:
        metadata = {
            "name": file_name,
            "parents": [folder_id]
        }
        
        # 1. Initiate upload (multipart)
        files = {
            'data': ('metadata', json.dumps(metadata), 'application/json'),
            'file': (file_name, file_data, 'application/pdf')
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers=headers,
            files=files
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"Error {response.status_code}: {response.text}"
            
    except Exception as e:
        return False, str(e)

def render_drive_picker_uploader(key, file_data, file_name, label="Guardar en Google Drive"):
    """
    Renders a Google Picker to select a folder, then uploads the file_data to that folder.
    
    IMPORTANTE: El Picker Y el Upload usan el Service Account.
    - Picker muestra SOLO carpetas del Drive del SA (documentos confidenciales)
    - Usuario navega dentro del Drive del SA únicamente
    - Upload usa credenciales del SA (centralizado)
    """
    st.markdown("---")
    st.write(f"##### {label}")

    # Check authentication del usuario (para tracking/audit)
    if 'token' not in st.session_state or not st.session_state.token:
        st.warning("⚠️ Debes iniciar sesión con Google en el Home para usar esta función.")
        return

    # 1. Google Picker Config
    try:
        picker_secrets = st.secrets["google"]
        client_secrets = st.secrets["google_oauth"]
        api_key = picker_secrets.get("api_key") or st.secrets.get("GOOGLE_API_KEY")
        client_id = client_secrets.get("client_id") or st.secrets.get("GOOGLE_CLIENT_ID")
    except Exception:
        st.error("Error de configuración: Faltan secretos de Google.")
        return

    # 2. Generar token del Service Account para el Picker
    sa_token = get_service_account_token()
    if not sa_token:
        st.error("❌ No se pudo generar token del Service Account para el Picker.")
        return
    
    # 3. Render Picker (usa token del SA para mostrar Drive del SA)
    picker_key = f"picker_{key}"
    app_id = client_id.split('-')[0] if client_id else None
    
    selected_folder = None
    with patch_picker_flatten():
        selected_folder = google_picker(
            label="📂 Repositorio Institucional (Drive del ERP)",
            token=sa_token,  # ✅ CAMBIADO: Usa token del SA
            apiKey=api_key,
            appId=app_id,
            view_ids=["FOLDERS"],
            allow_folders=True,
            accept_multiple_files=False,
            key=picker_key
        )

    # 4. Handle Selection & Upload (con Service Account)
    if selected_folder:
        try:
            if len(selected_folder) > 0:
                doc = selected_folder[0]
                
                if hasattr(doc, 'get'):
                    folder_id = doc.get("id")
                    folder_name = doc.get("name")
                elif hasattr(doc, 'id'):
                     folder_id = doc.id
                     folder_name = getattr(doc, 'name', 'Carpeta')
                else:
                    return

                if folder_id:
                    st.info(f"📁 Carpeta seleccionada: **{folder_name}**")
                    if st.button(f"⬆️ Confirmar subida de: {file_name}", key=f"btn_upload_{key}", type="primary"):
                        with st.spinner("Subiendo archivo a Google Drive con Service Account..."):
                            # Obtener credenciales del Service Account
                            try:
                                sa_creds = st.secrets["google_drive"]
                            except Exception as e:
                                st.error(f"❌ Error: No se encontraron credenciales del Service Account: {e}")
                                return
                            
                            # Upload con Service Account (centralizado)
                            success, result = upload_file_with_sa(
                                file_bytes=file_data,
                                file_name=file_name,
                                folder_id=folder_id,
                                sa_credentials=sa_creds
                            )
                            
                            if success:
                                st.success(f"✅ ¡Archivo guardado exitosamente en Drive!")
                                st.caption(f"📎 File ID: {result}")
                            else:
                                st.error(f"❌ Error al subir: {result}")
            else:
                st.warning("No se seleccionó ninguna carpeta.")

        except Exception as e:
            st.error(f"Error procesando la selección del Picker: {e}")

def render_simple_folder_selector(key, label="Seleccionar Carpeta Destino"):
    """
    Renders a Google Picker just to select a folder.
    Returns the selected folder info (dict) or None.
    
    IMPORTANTE: Usa token del Service Account para mostrar SOLO Drive del SA.
    """
    st.markdown(f"**{label}**")

    # Check authentication del usuario (para tracking/audit)
    if 'token' not in st.session_state or not st.session_state.token:
        st.warning("⚠️ Debes iniciar sesión con Google en el Home.")
        return None

    # Google Picker Config
    try:
        picker_secrets = st.secrets["google"]
        client_secrets = st.secrets["google_oauth"]
        api_key = picker_secrets.get("api_key") or st.secrets.get("GOOGLE_API_KEY")
        client_id = client_secrets.get("client_id") or st.secrets.get("GOOGLE_CLIENT_ID")
    except Exception:
        st.error("Error de configuración de Google Secrets.")
        return None

    # Generar token del Service Account para el Picker
    sa_token = get_service_account_token()
    if not sa_token:
        st.error("❌ No se pudo generar token del Service Account para el Picker.")
        return None

    picker_key = f"simple_picker_{key}"
    app_id = client_id.split('-')[0] if client_id else None

    selected_folder = None
    with patch_picker_flatten():
        selected_folder = google_picker(
            label="📂 Repositorio Institucional (Drive del ERP)",
            token=sa_token,  # ✅ CAMBIADO: Usa token del SA
            apiKey=api_key,
            appId=app_id,
            view_ids=["FOLDERS"],
            allow_folders=True, # Critical for folder view
            accept_multiple_files=False, # Use this instead of multiselect
            key=picker_key
        )

    # Handle Selection
    if selected_folder:
        try:
            if len(selected_folder) > 0:
                doc = selected_folder[0]
                
                folder_id = None
                folder_name = None
                
                if hasattr(doc, 'get'):
                    folder_id = doc.get("id")
                    folder_name = doc.get("name")
                elif hasattr(doc, 'id'):
                     folder_id = doc.id
                     folder_name = getattr(doc, 'name', 'Carpeta')
                
                if folder_id:
                    st.session_state[key] = {
                        'id': folder_id,
                        'name': folder_name
                    }
                    st.success(f"📂 Carpeta Destino: **{folder_name}**")
                    return st.session_state[key]
            
        except Exception as e:
            st.error(f"Error procesando selección: {e}")
            
    # If already selected, show it
    if key in st.session_state:
         curr = st.session_state[key]
         col_info, col_change = st.columns([4, 1])
         with col_info:
             st.success(f"📂 Carpeta Destino: **{curr['name']}**")
         with col_change:
             if st.button("🔄 Cambiar", key=f"change_{key}"):
                 del st.session_state[key]
                 st.rerun()
         return curr
         

    return None

import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

def upload_file_with_sa(file_bytes, file_name, folder_id, sa_credentials):
    """
    Uploads a file to Google Drive using a Service Account.
    :param sa_credentials: Path to JSON file (str) OR dictionary with credentials (dict)
    """
    try:
        # Load credentials
        if isinstance(sa_credentials, dict):
            # Clonar para no modificar el original de st.secrets (que podría ser inmutable)
            info = dict(sa_credentials)
            if 'private_key' in info:
                # Fix común para Streamlit Secrets: reemplazar \\n con \n real
                info['private_key'] = info['private_key'].replace('\\n', '\n')
            
            creds = service_account.Credentials.from_service_account_info(
                info, 
                scopes=['https://www.googleapis.com/auth/drive']
            )
        else:
            creds = service_account.Credentials.from_service_account_file(
                sa_credentials, 
                scopes=['https://www.googleapis.com/auth/drive']
            )
        
        # Build Service
        service = build('drive', 'v3', credentials=creds)
        
        # File Metadata
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        # Media Upload
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype='application/pdf')
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        return True, file.get('id')
        
    except Exception as e:
        # Debugging Info Propagation
        debug_msg = str(e)
        if isinstance(sa_credentials, dict) and 'private_key' in sa_credentials:
             pk = sa_credentials['private_key']
             # Mostrar si tiene saltos de linea o no
             debug_msg += f" | KeyLen: {len(pk)} | HasRealNewLine: {'\\n' in pk} | HasEscapedNewLine: {'\\\\n' in pk} | Start: {pk[:10]}..."
        return False, debug_msg

