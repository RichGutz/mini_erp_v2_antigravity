import streamlit as st
import requests
import json
from streamlit_google_picker import google_picker
import streamlit_google_picker.uploaded_file as lib_upl # Import for monkeypatching
import uuid  # Para generar keys únicas por sesión
import io

# --- CONFIGURACIÓN SHARED DRIVE ---
# ID de la carpeta raíz del repositorio en el SHARED DRIVE
# Link: https://drive.google.com/drive/u/1/folders/1Jv1r9kixL982gL-RCyPnhOY3W-qI0CLq
REPOSITORIO_FOLDER_ID = "1Jv1r9kixL982gL-RCyPnhOY3W-qI0CLq"
# -------------------------------------

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

# --- HELPER: Listar Carpetas con Service Account (Backend del Browser Nativo) ---
def list_folders_with_sa(parent_id, sa_creds):
    """
    Lista las subcarpetas dentro de parent_id usando credenciales de Service Account.
    Retorna lista de dicts: [{'id': '...', 'name': '...'}]
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_info(
            sa_creds, scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=creds)

        # Query solo carpetas y que no estén en la papelera
        query = f"'{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        
        results = service.files().list(
            q=query,
            pageSize=50,
            fields="nextPageToken, files(id, name)",
            includeItemsFromAllDrives=True, # Necesario para Shared Drives
            supportsAllDrives=True
        ).execute()
        
        return results.get('files', [])
    except Exception as e:
        st.error(f"Error listando carpetas: {e}")
        return []

# ---------------------------------------------------------

def get_service_account_token():
    """
    Genera un access_token FRESCO del Service Account para usar en el Google Picker.
    IMPORTANTE: Se genera un token nuevo en cada llamada para evitar problemas de caché.
    """
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests
        
        # Obtener credenciales del Service Account
        sa_creds_dict = dict(st.secrets["google_drive"])
        
        # Fix de private_key si viene con \\n en lugar de \n
        if 'private_key' in sa_creds_dict:
            original_key = sa_creds_dict['private_key']
            sa_creds_dict['private_key'] = original_key.replace('\\n', '\n')
        
        # Crear credenciales con scope de Drive
        creds = service_account.Credentials.from_service_account_info(
            sa_creds_dict,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # FORZAR refresh para obtener token FRESCO (no en caché)
        creds.refresh(google.auth.transport.requests.Request())
        
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

    # 2. Obtener token del USUARIO para el Picker (navegación)
    # ESTRATEGIA HÍBRIDA WORKSPACE:
    # - Picker: Usa token del USUARIO para poder "ver" y navegar Shared Drives.
    # - Upload: Usa Service Account para escribir (autorizado en el Shared Drive).
    user_token = st.session_state.get('token')
    if not user_token:
        st.warning("⚠️ Para ver el Repositorio Institucional, inicia sesión con Google.")
        return
        
    # --- DIAGNÓSTICO EN UI (MEJORADO) ---
    st.info("ℹ️ MODO HÍBRIDO: Picker usa TU cuenta para ver Shared Drives. Upload usa Service Account.")
    with st.expander("🔍 HERRAMIENTA DE DIAGNÓSTICO (ESTADO PIKER)", expanded=True):
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.write("**1. Sesión de Usuario:**")
            user_info = st.session_state.get('user_info', {})
            st.code(f"Usuario: {user_info.get('email', 'N/A')}")
            st.caption("Este usuario se usa para NAVEGAR y SOLICITAR permisos de vista.")

        with col_d2:
            st.write("**2. Token en Picker:**")
            st.code(f"Tipo: User Token (Bearer)")
            if user_token:
                st.success("✅ Token Presente")
            else:
                st.error("❌ Sin Token")
        
        st.write("**3. Validación de Permisos (Scopes):**")
        if user_token:
            try:
                # Consultar scopes reales a Google
                token_info_url = f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={user_token}"
                resp = requests.get(token_info_url)
                if resp.status_code == 200:
                    info = resp.json()
                    st.json(info) # Mostrar info cruda para transparencia
                    
                    scopes = info.get('scope', '').split(' ')
                    has_drive = 'https://www.googleapis.com/auth/drive' in scopes
                    
                    if has_drive:
                        st.success("✅ Scope '.../auth/drive' ACTIVO (Permite ver Shared Drives)")
                    else:
                        st.error("❌ FALTA Scope '.../auth/drive'. Necesitarás re-autenticar.")
                else:
                    st.error(f"❌ Token inválido (Error {resp.status_code})")
                    st.json(resp.json())
            except Exception as e:
                st.error(f"Error validando: {e}")
    # --------------------------------
    
    # Botón para forzar refresh del Picker (limpiar caché)
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refrescar Picker", key=f"refresh_picker_{key}"):
            # Limpiar UUID de sesión para forzar recreación del Picker
            if 'picker_session_id' in st.session_state:
                del st.session_state.picker_session_id
            st.rerun()
    
    # 3. Render Picker (usa token del USUARIO para mostrar su Drive)
    # IMPORTANTE: Key única por sesión para evitar caché entre sesiones pero estable en la misma sesión
    if 'picker_session_id' not in st.session_state:
        st.session_state.picker_session_id = str(uuid.uuid4())
    
    picker_key = f"picker_{key}_{st.session_state.picker_session_id}"
    app_id = client_id.split('-')[0] if client_id else None
    
    selected_folder = None
    with patch_picker_flatten():
        selected_folder = google_picker(
            label="📂 Seleccionar Carpeta en Repositorio",
            token=user_token,  # ✅ Usuario navega
            apiKey=api_key,
            appId=app_id,
            view_ids=["FOLDERS"],
            allow_folders=True,
            accept_multiple_files=False,
            key=picker_key  # Key única por sesión
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
            st.error(f"Error procesando la selección del picker: {e}")

from googleapiclient.http import MediaIoBaseUpload

def upload_file_with_sa(file_bytes, file_name, folder_id, sa_credentials):
    """
    Uploads a file to Google Drive using a Service Account.
    :param sa_credentials: Path to JSON file (str) OR dictionary with credentials (dict)
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        # Load credentials
        # Check if it's NOT a string (path). If so, treat as dict/AttrDict.
        if not isinstance(sa_credentials, str):
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
            fields='id',
            supportsAllDrives=True  # ✅ Soporte para Shared Drives
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


def render_simple_folder_selector(key, label="Seleccionar Carpeta Destino"):
    """
    Navegador Nativo de Carpetas Institucional.
    Reemplaza al Google Picker para garantizar restricción de vista.
    Usa el Service Account para listar carpetas.
    """
    st.markdown(f"**{label}**")
    
    # 1. Configuración de Session State para navegación
    nav_key_id = f"nav_folder_id_{key}"
    nav_key_name = f"nav_folder_name_{key}"
    nav_key_history = f"nav_history_{key}" # Lista de tuplas (id, name)
    sel_key = f"selected_folder_{key}"

    # Inicialización
    if nav_key_id not in st.session_state:
        st.session_state[nav_key_id] = REPOSITORIO_FOLDER_ID
        st.session_state[nav_key_name] = "📁 REPOSITORIO_INANDES (Raíz)"
        st.session_state[nav_key_history] = []
    
    # Si ya se seleccionó una carpeta definitiva
    if sel_key in st.session_state:
        curr = st.session_state[sel_key]
        col_info, col_change = st.columns([4, 1])
        with col_info:
            st.success(f"✅ Destino Seleccionado: **{curr['name']}**")
        with col_change:
            if st.button("🔄 Cambiar", key=f"change_{key}"):
                del st.session_state[sel_key]
                st.rerun()
        return curr

    # 2. UI del Navegador
    current_id = st.session_state[nav_key_id]
    current_name = st.session_state[nav_key_name]
    
    # Header de Navegación
    st.info(f"📍 Estás en: **{current_name}**")
    
    # Botones de Acción (Atrás / Seleccionar Actual)
    col_back, col_select = st.columns([1, 3])
    with col_back:
        if st.session_state[nav_key_history]:
            if st.button("⬅️ Subir Nivel", key=f"btn_back_{key}"):
                # Pop del historial
                last_id, last_name = st.session_state[nav_key_history].pop()
                st.session_state[nav_key_id] = last_id
                st.session_state[nav_key_name] = last_name
                st.rerun()
        else:
            st.button("⬅️ Atrás", disabled=True, key=f"btn_back_disabled_{key}")

    with col_select:
        if st.button(f"✅ Seleccionar esta carpeta", key=f"btn_sel_curr_{key}", type="primary", use_container_width=True):
            st.session_state[sel_key] = {'id': current_id, 'name': current_name}
            st.rerun()

    st.markdown("---")
    st.markdown("📂 **Subcarpetas Disponibles:**")

    # 3. Listar Contenido (Backend SA)
    try:
        sa_creds = st.secrets["google_drive"]
        subfolders = list_folders_with_sa(current_id, sa_creds)
    except Exception as e:
        st.error(f"Error accediendo al repositorio: {e}")
        subfolders = []

    if not subfolders:
        st.caption("*(Carpeta vacía o sin subcarpetas)*")
    else:
        # Grid de carpetas: Usamos columnas para que sea más compacto
        for folder in subfolders:
            f_name = folder['name']
            f_id = folder['id']
            
            if st.button(f"📁 {f_name}", key=f"nav_to_{f_id}_{key}", use_container_width=True):
                # Navegar hacia dentro
                st.session_state[nav_key_history].append((current_id, current_name))
                st.session_state[nav_key_id] = f_id
                st.session_state[nav_key_name] = f_name
                st.rerun()

    return None


# --- NATIVE BROWSER V2 (Minimalist) ---
def render_folder_navigator_v2(key, label="Navegador del Repositorio"):
    """
    Renderiza un navegador de carpetas nativo (Streamlit puro) usando list_folders_with_sa.
    Mejoras V2 Minimalista: 
    - Breadcrumbs interactivos (botones).
    - Lista vertical simple (sin iconos).
    - Filtro de búsqueda.
    """
    
    # 1. Configuración de Session State
    nav_key_id = f"nav_folder_id_{key}"
    nav_key_name = f"nav_folder_name_{key}"
    nav_key_history = f"nav_history_{key}" # Lista de tuplas (id, name)
    sel_key = f"selected_folder_{key}"

    # Inicialización
    if nav_key_id not in st.session_state:
        st.session_state[nav_key_id] = REPOSITORIO_FOLDER_ID
        st.session_state[nav_key_name] = "Inicio"
        st.session_state[nav_key_history] = []
    
    current_id = st.session_state[nav_key_id]
    current_name = st.session_state[nav_key_name]
    
    # --- A. HEADER & BREADCRUMBS ---
    # Layout: [ Label ]
    #         [ Btn1 > Btn2 > BtnCurrent ]
    
    st.markdown(f"**{label}**")
    
    # Breadcrumbs construction
    # History + Current
    # We render them as a sequence of small buttons
    
    # Full history including current for rendering
    full_history = st.session_state[nav_key_history] + [(current_id, current_name)]
    
    cols = st.columns(len(full_history) + 2) # dynamic columns
    
    # Always show "Root" button if history is empty? 
    # Logic: iterate history and make buttons
    
    # Better: Use a single container and horizontal scroll or just wrap buttons? 
    # Streamlit columns are strict. Let's try to put them in a dedicated container with columns.
    
    # To avoid column explosion, we'll just put "Up" button + Current text, 
    # OR explicit buttons for the last 3 levels.
    # User wanted "breadcrumb buttons".
    
    # Let's try a different approach for breadcrumbs: standard columns for elements
    bc_cols = st.columns([1] * len(full_history) + [8 - len(full_history)] if len(full_history) < 8 else [1]*8)
    
    for i, (fid, fname) in enumerate(full_history):
        # Prevent index out of bounds if deep nesting (basic protection)
        if i >= 8: break 
        
        with bc_cols[i]:
            # If it's the last one (current), maybe just text? OR disabled button?
            is_current = (i == len(full_history) - 1)
            
            if st.button(fname, key=f"bc_{key}_{i}_{fid}", disabled=is_current, type="secondary" if not is_current else "primary", use_container_width=True):
                # Navigate to this level
                # Need to slice history
                # If I click index i, I want to keep history up to i-1
                new_history = full_history[:i]
                target_id = fid
                target_name = fname
                
                st.session_state[nav_key_history] = new_history
                st.session_state[nav_key_id] = target_id
                st.session_state[nav_key_name] = target_name
                st.rerun()

    st.markdown("---")

    # --- B. SEARCH FILTER ---
    filter_text = st.text_input("Filtrar carpetas...", key=f"filter_{key}", placeholder="Escribe para buscar...")

    # --- C. CONTENT LIST (Vertical) ---
    with st.spinner(f"Cargando..."):
        try:
            sa_creds = st.secrets["google_drive"]
            subfolders = list_folders_with_sa(current_id, sa_creds)
        except Exception as e:
            st.error(f"Error: {e}")
            subfolders = []
            
    if not subfolders:
        st.caption("(Vacío)")
    else:
        # Filter logic
        if filter_text:
            subfolders = [f for f in subfolders if filter_text.lower() in f['name'].lower()]

        # Header of List
        h1, h2, h3 = st.columns([6, 2, 2])
        with h1: st.caption("Nombre")
        with h2: st.caption("Acción")
        with h3: st.caption("Selección")
        
        for folder in subfolders:
            c1, c2, c3 = st.columns([6, 2, 2])
            f_name = folder['name']
            f_id = folder['id']
            
            with c1:
                # Name as button to enter? Or simple text? User said "Click en nombre = Entrar"
                if st.button(f_name, key=f"nav_to_{f_id}_{key}", use_container_width=True):
                     st.session_state[nav_key_history].append((current_id, current_name))
                     st.session_state[nav_key_id] = f_id
                     st.session_state[nav_key_name] = f_name
                     st.rerun()
            
            with c2:
                # Redundant "Open"? User said "Remove redundancy". 
                # Maybe just keep metadata? Or empty?
                # Let's keep it clean, maybe empty or date if we had it.
                pass

            with c3:
                # Select Button
                # Check if currently selected
                current_selection = st.session_state.get(sel_key)
                is_selected = current_selection and current_selection['id'] == f_id
                
                label_sel = "Seleccionado" if is_selected else "Seleccionar"
                type_sel = "primary" if is_selected else "secondary"
                
                if st.button(label_sel, key=f"sel_{f_id}_{key}", type=type_sel, use_container_width=True):
                    # Capture Full Path explicitly at moment of selection
                    # Path = History + Current + Child
                    child_path = st.session_state[nav_key_history] + [(current_id, current_name), (f_id, f_name)]
                    
                    st.session_state[sel_key] = {
                        'id': f_id, 
                        'name': f_name, 
                        'full_path': child_path
                    }
                    st.rerun()

    # --- D. ACTION FOOTER ---
    st.markdown("---")
    
    # 1. footer layout
    c_info, c_main_action = st.columns([7, 3])
    
    selected_data = st.session_state.get(sel_key)
    
    with c_info:
        if selected_data:
             st.success(f"✅ Destino final: **{selected_data['name']}**")
        else:
             st.info(f"📂 Estás en: **{current_name}**")

    with c_main_action:
        if selected_data:
             if st.button("Cambiar / Borrar", key=f"clear_sel_{key}", use_container_width=True):
                 del st.session_state[sel_key]
                 st.rerun()
        else:
             # Allow selecting the CURRENT folder itself (e.g. if I am inside 'Anexo 1')
             if st.button(f"Seleccionar '{current_name}'", key=f"sel_curr_{key}", type="primary", use_container_width=True):
                 # Path = History + Current
                 cur_path = st.session_state[nav_key_history] + [(current_id, current_name)]
                 
                 st.session_state[sel_key] = {
                     'id': current_id, 
                     'name': current_name, 
                     'full_path': cur_path
                 }
                 st.rerun()
                
    return selected_data

