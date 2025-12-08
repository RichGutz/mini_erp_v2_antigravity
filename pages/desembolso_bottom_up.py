import streamlit as st
import sys
import os

# Add root directory to path to allow imports from src
sys.path.append(os.path.abspath("."))

from src.utils.google_integration import list_folders_with_sa, upload_file_with_sa, REPOSITORIO_FOLDER_ID

# --- PROTOTIPO V2: NAVEGADOR MEJORADO ---
def render_folder_navigator_v2(key, label="Navegador del Repositorio"):
    st.subheader(f"📂 {label}")
    
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
    
    # --- A. BREADCRUMBS (Ruta Visual) ---
    # Construir ruta: [Inicio] > [Carpeta A] > [Carpeta B]
    # No son clickeables fácilmente en st standard sin hacks, así que lo hacemos visual
    path_text = " / ".join([h[1] for h in st.session_state[nav_key_history]] + [current_name])
    st.caption(f"📍 Ruta actual: **{path_text}**")
    
    # --- B. ACCIONES PRINCIPALES ---
    col_back, col_select = st.columns([1, 4])
    with col_back:
        if st.session_state[nav_key_history]:
            if st.button("⬅️ Atrás", key=f"btn_back_{key}", use_container_width=True):
                last_id, last_name = st.session_state[nav_key_history].pop()
                st.session_state[nav_key_id] = last_id
                st.session_state[nav_key_name] = last_name
                st.rerun()
        else:
             st.button("🚫 Raíz", disabled=True, key=f"btn_root_{key}", use_container_width=True)
             
    with col_select:
        # Botón para seleccionar la carpeta actual como destino
        if st.button(f"✅ Seleccionar: [{current_name}]", key=f"btn_sel_{key}", type="primary", use_container_width=True):
            st.session_state[sel_key] = {'id': current_id, 'name': current_name}
            st.rerun()

    st.markdown("---")

    # --- C. VISTA DE CARPETAS (Explorador) ---
    # Si ya hay selección, mostrarla arriba
    if sel_key in st.session_state:
        curr = st.session_state[sel_key]
        st.success(f"🎯 Carpeta Destino Seleccionada: **{curr['name']}**")
        if st.button("❌ Cancelar Selección", key=f"cancel_sel_{key}"):
            del st.session_state[sel_key]
            st.rerun()
        return curr

    # Listar contenido
    with st.spinner(f"Cargando contenido de '{current_name}'..."):
        try:
            sa_creds = st.secrets["google_drive"]
            subfolders = list_folders_with_sa(current_id, sa_creds)
        except Exception as e:
            st.error(f"Error accediendo a drive: {e}")
            subfolders = []
            
    if not subfolders:
        st.info("📭 Esta carpeta no tiene subcarpetas.")
    else:
        # GRID LAYOUT: 3 columnas
        cols = st.columns(3)
        for i, folder in enumerate(subfolders):
            col = cols[i % 3]
            with col:
                # Usamos un contenedor con borde para que parezca una "tarjeta"
                with st.container(border=True):
                    st.write(f"📁 **{folder['name']}**")
                    if st.button("Abrir ➡️", key=f"open_{folder['id']}_{key}", use_container_width=True):
                        # Navegar
                        st.session_state[nav_key_history].append((current_id, current_name))
                        st.session_state[nav_key_id] = folder['id']
                        st.session_state[nav_key_name] = folder['name']
                        st.rerun()
                        
    return None

# --- LAYOUT DE 2 COLUMNAS (Lado a Lado) ---
col_left, col_right = st.columns([3, 2], gap="large")

with col_left:
    # --- 1. Selector de Carpeta (Nativo) ---
    # Usamos el componente v2 directamente
    selected_folder = render_folder_navigator_v2(key="native_test_v2")

with col_right:
    # --- 2. Prueba de Subida (Panel Derecho) ---
    st.subheader("🚀 Prueba de Subida")
    st.info("Sube un archivo de prueba a la carpeta seleccionada en el panel izquierdo.")

    if selected_folder:
        # Mostrar info compacta de carpeta seleccionada
        with st.container(border=True):
            st.write(f"📂 **Destino:** `{selected_folder['name']}`")
            # st.caption(f"ID: {selected_folder['id']}")
            
            uploaded_file = st.file_uploader("Seleccionar archivo", type=['pdf', 'txt', 'png', 'jpg'])
            
            if uploaded_file:
                if st.button("⬆️ Subir Archivo Ahora", type="primary", use_container_width=True):
                    with st.spinner("Subiendo..."):
                        file_bytes = uploaded_file.getvalue()
                        file_name = uploaded_file.name
                        
                        try:
                            sa_creds = st.secrets["google_drive"]
                            success, result = upload_file_with_sa(
                                file_bytes=file_bytes,
                                file_name=file_name,
                                folder_id=selected_folder['id'],
                                sa_credentials=sa_creds
                            )
                            
                            if success:
                                st.balloons()
                                st.success(f"✅ **{file_name}** subido!")
                                # st.code(f"ID: {result}")
                            else:
                                st.error(f"❌ Error: {result}")
                        except Exception as e:
                            st.error(f"Error config: {e}")
    else:
        st.warning("👈 Selecciona una carpeta a la izquierda para habilitar la subida.")
