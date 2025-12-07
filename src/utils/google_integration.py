import streamlit as st
import requests
import json
from streamlit_google_picker import google_picker

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
    
    Args:
        key (str): Unique key for the component.
        file_data (bytes): The file content to upload.
        file_name (str): The name of the file.
        label (str): Label for the section.
    """
    st.markdown("---")
    st.write(f"##### {label}")

    # Check authentication
    if 'token' not in st.session_state or not st.session_state.token:
        st.warning("⚠️ Debes iniciar sesión con Google en el Home para usar esta función.")
        return

    # 1. Google Picker Config
    # We reuse the secrets structure we verified in the Repositorio fix
    try:
        picker_secrets = st.secrets["google"] # Use the 'google' section which usually has the API Key
        client_secrets = st.secrets["google_oauth"] # Use 'google_oauth' for Client ID
        
        # Fallback logic if structure differs (based on previous sessions)
        api_key = picker_secrets.get("api_key") or st.secrets.get("GOOGLE_API_KEY")
        client_id = client_secrets.get("client_id") or st.secrets.get("GOOGLE_CLIENT_ID")
        
    except Exception:
        st.error("Error de configuración: Faltan secretos de Google (API Key o Client ID).")
        return

    # 2. Render Picker
    # picker_result will be None until user selects
    picker_key = f"picker_{key}"
    
    # Extract appId safely
    app_id = client_id.split('-')[0] if client_id else None
    
    selected_folder = google_picker(
        token=st.session_state.token['access_token'],
        apiKey=api_key,
        appId=app_id,
        view_ids=["FOLDERS"], # Only show folders
        allow_folders=True,
        key=picker_key
    )

    # 3. Handle Selection & Upload
    if selected_folder:
        # The picker returns a list of selected items (or single object depending on config)
        # streamlit-google-picker typically returns detailed object
        
        # Safely extract folder ID and Name
        try:
            # Assuming 'docs' or similar structure, typically it returns the docs array if multiple
            # If not array, it might be the object directly. Let's inspect based on common usage or handle both.
            if isinstance(selected_folder, list) and len(selected_folder) > 0:
                doc = selected_folder[0]
            else:
                doc = selected_folder
                
            folder_id = doc.get("id")
            folder_name = doc.get("name")
            
            if folder_id:
                st.info(f"📁 Carpeta seleccionada: **{folder_name}**")
                
                # Upload Button
                if st.button(f"⬆️ Confirmar subida de: {file_name}", key=f"btn_upload_{key}", type="primary"):
                    with st.spinner("Subiendo archivo a Google Drive..."):
                        success, result = upload_file_to_drive(
                            file_data=file_data,
                            file_name=file_name,
                            folder_id=folder_id,
                            access_token=st.session_state.token['access_token']
                        )
                        
                        if success:
                            st.success(f"✅ ¡Archivo guardado exitosamente en Drive!")
                            # Optional: Show link to file
                            # file_url = f"https://drive.google.com/file/d/{result.get('id')}/view"
                            # st.markdown(f"[Ver archivo en Drive]({file_url})")
                        else:
                            st.error(f"❌ Error al subir: {result}")
            else:
                st.warning("No se pudo identificar la carpeta seleccionada.")

        except Exception as e:
            st.error(f"Error procesando la selección del Picker: {e}")

def render_simple_folder_selector(key, label="Seleccionar Carpeta Destino"):
    """
    Renders a Google Picker to select a folder and stores the result in st.session_state[key].
    Returns the selected folder info (dict) or None.
    
    Args:
        key (str): Unique key for session state storage.
        label (str): Label for the section.
    """
    st.markdown(f"**{label}**")

    # Check authentication
    if 'token' not in st.session_state or not st.session_state.token:
        st.warning("⚠️ Debes iniciar sesión con Google en el Home.")
        return None

    # 1. Google Picker Config
    try:
        picker_secrets = st.secrets["google"]
        client_secrets = st.secrets["google_oauth"]
        api_key = picker_secrets.get("api_key") or st.secrets.get("GOOGLE_API_KEY")
        client_id = client_secrets.get("client_id") or st.secrets.get("GOOGLE_CLIENT_ID")
    except Exception:
        st.error("Error de configuración de Google Secrets.")
        return None

    # 2. Render Picker
    picker_key = f"simple_picker_{key}"
    
    # Extract appId safely
    app_id = client_id.split('-')[0] if client_id else None

    # Use arguments matching 07_Repositorio.py
    selected_folder = google_picker(
        label="📂 Seleccionar Carpeta",
        token=st.session_state.token['access_token'],
        apiKey=api_key,
        appId=app_id,
        view_ids=["FOLDERS"],
        mimeTypes="application/vnd.google-apps.folder", # Force folder selection
        allow_folders=True, # Critical for folder view
        support_drives=True,
        multiselect=False,
        key=picker_key
    )

    # 3. Handle Selection
    if selected_folder:
        try:
            if isinstance(selected_folder, list) and len(selected_folder) > 0:
                doc = selected_folder[0]
            else:
                doc = selected_folder
                
            folder_id = doc.get("id")
            folder_name = doc.get("name")
            
            if folder_id:
                # Store in session state for external access
                st.session_state[key] = {
                    'id': folder_id,
                    'name': folder_name
                }
                st.success(f"📂 Carpeta Destino: **{folder_name}**")
                return st.session_state[key]
            
        except Exception as e:
            st.error(f"Error procesando selección: {e}")
            
    # If already selected in previous run, show it
    if key in st.session_state:
         curr = st.session_state[key]
         st.success(f"📂 Carpeta Destino: **{curr['name']}**")
         return curr
         
    return None
