"""
Script de diagnóstico para verificar qué Drives y carpetas puede ver el Service Account.
Esto ayudará a identificar por qué el Picker muestra carpetas del repositorio antiguo.
"""

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

def diagnosticar_acceso_service_account():
    """
    Verifica todos los Drives y carpetas a los que el Service Account tiene acceso.
    """
    st.title("🔍 Diagnóstico de Acceso del Service Account")
    
    try:
        # Obtener credenciales del Service Account
        sa_creds_dict = dict(st.secrets["google_drive"])
        
        # Fix de private_key
        if 'private_key' in sa_creds_dict:
            sa_creds_dict['private_key'] = sa_creds_dict['private_key'].replace('\\n', '\n')
        
        # Crear credenciales
        creds = service_account.Credentials.from_service_account_info(
            sa_creds_dict,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # Build Service
        service = build('drive', 'v3', credentials=creds)
        
        st.success(f"✅ Service Account: {sa_creds_dict.get('client_email')}")
        
        # --- 1. LISTAR SHARED DRIVES ---
        st.header("1️⃣ Shared Drives Accesibles")
        
        try:
            drives_response = service.drives().list(
                pageSize=100,
                fields='drives(id, name)'
            ).execute()
            
            drives = drives_response.get('drives', [])
            
            if drives:
                st.success(f"✅ Se encontraron {len(drives)} Shared Drive(s)")
                for drive in drives:
                    st.info(f"📂 **{drive['name']}**\n- ID: `{drive['id']}`")
            else:
                st.warning("⚠️ No se encontraron Shared Drives")
        except Exception as e:
            st.error(f"❌ Error listando Shared Drives: {e}")
        
        # --- 2. LISTAR ARCHIVOS EN "MI UNIDAD" ---
        st.header("2️⃣ Archivos en 'Mi Unidad' del Service Account")
        
        try:
            files_response = service.files().list(
                pageSize=20,
                fields='files(id, name, mimeType, owners)',
                q="'root' in parents and trashed=false"
            ).execute()
            
            files = files_response.get('files', [])
            
            if files:
                st.warning(f"⚠️ Se encontraron {len(files)} archivo(s) en Mi Unidad")
                for file in files:
                    st.write(f"- **{file['name']}** (ID: `{file['id']}`)")
            else:
                st.success("✅ No hay archivos en Mi Unidad del SA")
        except Exception as e:
            st.error(f"❌ Error listando archivos: {e}")
        
        # --- 3. LISTAR CARPETAS COMPARTIDAS ---
        st.header("3️⃣ Carpetas Compartidas con el Service Account")
        
        try:
            shared_response = service.files().list(
                pageSize=50,
                fields='files(id, name, mimeType, owners, shared, sharedWithMeTime)',
                q="sharedWithMe=true and mimeType='application/vnd.google-apps.folder' and trashed=false",
                orderBy='sharedWithMeTime desc'
            ).execute()
            
            shared_folders = shared_response.get('files', [])
            
            if shared_folders:
                st.warning(f"⚠️ Se encontraron {len(shared_folders)} carpeta(s) compartida(s)")
                for folder in shared_folders:
                    owners = folder.get('owners', [])
                    owner_email = owners[0]['emailAddress'] if owners else 'Desconocido'
                    st.write(f"- **{folder['name']}**")
                    st.caption(f"  Propietario: {owner_email} | ID: `{folder['id']}`")
            else:
                st.success("✅ No hay carpetas compartidas con el SA")
        except Exception as e:
            st.error(f"❌ Error listando carpetas compartidas: {e}")
        
        # --- 4. VERIFICAR ACCESO AL SHARED DRIVE ESPECÍFICO ---
        st.header("4️⃣ Verificar Acceso al Shared Drive Institucional")
        
        SHARED_DRIVE_ID = "0AAeC4FtltHyBUk9PVA"
        
        try:
            drive_info = service.drives().get(
                driveId=SHARED_DRIVE_ID
            ).execute()
            
            st.success(f"✅ Acceso confirmado al Shared Drive: **{drive_info['name']}**")
            st.caption(f"ID: `{drive_info['id']}`")
        except Exception as e:
            st.error(f"❌ No se puede acceder al Shared Drive institucional: {e}")
        
    except Exception as e:
        st.error(f"❌ Error general: {e}")
        import traceback
        st.code(traceback.format_exc())

if __name__ == "__main__":
    diagnosticar_acceso_service_account()
