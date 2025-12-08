"""
Script de diagnóstico CLI para verificar qué Drives y carpetas puede ver el Service Account.
Ejecuta en terminal sin necesidad de Streamlit.
"""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

def diagnosticar_acceso_service_account():
    """
    Verifica todos los Drives y carpetas a los que el Service Account tiene acceso.
    """
    print("=" * 80)
    print("🔍 DIAGNÓSTICO DE ACCESO DEL SERVICE ACCOUNT")
    print("=" * 80)
    
    try:
        # Leer secrets desde archivo local
        with open('.streamlit/secrets.toml', 'r') as f:
            content = f.read()
        
        # Parsear manualmente la sección [google_drive]
        import toml
        secrets = toml.load('.streamlit/secrets.toml')
        sa_creds_dict = secrets['google_drive']
        
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
        
        print(f"\n✅ Service Account: {sa_creds_dict.get('client_email')}")
        print("=" * 80)
        
        # --- 1. LISTAR SHARED DRIVES ---
        print("\n1️⃣  SHARED DRIVES ACCESIBLES")
        print("-" * 80)
        
        try:
            drives_response = service.drives().list(
                pageSize=100,
                fields='drives(id, name)'
            ).execute()
            
            drives = drives_response.get('drives', [])
            
            if drives:
                print(f"✅ Se encontraron {len(drives)} Shared Drive(s):\n")
                for drive in drives:
                    print(f"   📂 {drive['name']}")
                    print(f"      ID: {drive['id']}\n")
            else:
                print("⚠️  No se encontraron Shared Drives\n")
        except Exception as e:
            print(f"❌ Error listando Shared Drives: {e}\n")
        
        # --- 2. LISTAR ARCHIVOS EN "MI UNIDAD" ---
        print("\n2️⃣  ARCHIVOS EN 'MI UNIDAD' DEL SERVICE ACCOUNT")
        print("-" * 80)
        
        try:
            files_response = service.files().list(
                pageSize=20,
                fields='files(id, name, mimeType)',
                q="'root' in parents and trashed=false"
            ).execute()
            
            files = files_response.get('files', [])
            
            if files:
                print(f"⚠️  Se encontraron {len(files)} archivo(s) en Mi Unidad:\n")
                for file in files:
                    print(f"   - {file['name']} (ID: {file['id']})\n")
            else:
                print("✅ No hay archivos en Mi Unidad del SA\n")
        except Exception as e:
            print(f"❌ Error listando archivos: {e}\n")
        
        # --- 3. LISTAR CARPETAS COMPARTIDAS ---
        print("\n3️⃣  CARPETAS COMPARTIDAS CON EL SERVICE ACCOUNT")
        print("-" * 80)
        
        try:
            shared_response = service.files().list(
                pageSize=50,
                fields='files(id, name, mimeType, owners, shared, sharedWithMeTime)',
                q="sharedWithMe=true and mimeType='application/vnd.google-apps.folder' and trashed=false",
                orderBy='sharedWithMeTime desc'
            ).execute()
            
            shared_folders = shared_response.get('files', [])
            
            if shared_folders:
                print(f"⚠️  Se encontraron {len(shared_folders)} carpeta(s) compartida(s):\n")
                for folder in shared_folders:
                    owners = folder.get('owners', [])
                    owner_email = owners[0]['emailAddress'] if owners else 'Desconocido'
                    print(f"   📁 {folder['name']}")
                    print(f"      Propietario: {owner_email}")
                    print(f"      ID: {folder['id']}\n")
            else:
                print("✅ No hay carpetas compartidas con el SA\n")
        except Exception as e:
            print(f"❌ Error listando carpetas compartidas: {e}\n")
        
        # --- 4. VERIFICAR ACCESO AL SHARED DRIVE ESPECÍFICO ---
        print("\n4️⃣  VERIFICAR ACCESO AL SHARED DRIVE INSTITUCIONAL")
        print("-" * 80)
        
        SHARED_DRIVE_ID = "0AAeC4FtltHyBUk9PVA"
        
        try:
            drive_info = service.drives().get(
                driveId=SHARED_DRIVE_ID
            ).execute()
            
            print(f"✅ Acceso confirmado al Shared Drive: {drive_info['name']}")
            print(f"   ID: {drive_info['id']}\n")
        except Exception as e:
            print(f"❌ No se puede acceder al Shared Drive institucional: {e}\n")
        
        print("=" * 80)
        print("✅ DIAGNÓSTICO COMPLETADO")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnosticar_acceso_service_account()
