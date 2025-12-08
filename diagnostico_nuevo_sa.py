"""
Script de diagnóstico para verificar qué carpetas puede ver el nuevo Service Account
"""
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
import google.auth.transport.requests

# Cargar credenciales del nuevo Service Account
with open('secrets oauth/mini-erp-v2-antigravity-850849b1e68d.json', 'r') as f:
    sa_creds_dict = json.load(f)

# Crear credenciales
SCOPES = ['https://www.googleapis.com/auth/drive']
credentials = service_account.Credentials.from_service_account_info(
    sa_creds_dict,
    scopes=SCOPES
)

# Crear servicio de Drive
service = build('drive', 'v3', credentials=credentials)

print("=" * 80)
print("DIAGNÓSTICO: Carpetas accesibles por kaizen-drive-service")
print("=" * 80)

try:
    # Listar archivos y carpetas
    results = service.files().list(
        pageSize=100,
        fields="files(id, name, mimeType, parents, driveId, shared, owners)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    items = results.get('files', [])
    
    if not items:
        print("\n❌ NO SE ENCONTRARON CARPETAS NI ARCHIVOS")
        print("\nPosibles causas:")
        print("1. El Service Account no tiene acceso a ninguna carpeta")
        print("2. La carpeta no está compartida correctamente")
        print("3. Faltan permisos en el Service Account")
    else:
        print(f"\n✅ Se encontraron {len(items)} items\n")
        
        folders = [item for item in items if item['mimeType'] == 'application/vnd.google-apps.folder']
        files = [item for item in items if item['mimeType'] != 'application/vnd.google-apps.folder']
        
        print(f"📁 CARPETAS ({len(folders)}):")
        print("-" * 80)
        for folder in folders:
            print(f"  Nombre: {folder['name']}")
            print(f"  ID: {folder['id']}")
            print(f"  Shared: {folder.get('shared', False)}")
            if 'owners' in folder:
                owners = [o.get('emailAddress', 'N/A') for o in folder['owners']]
                print(f"  Propietarios: {', '.join(owners)}")
            print()
        
        if files:
            print(f"\n📄 ARCHIVOS ({len(files)}):")
            print("-" * 80)
            for file in files[:5]:  # Solo primeros 5
                print(f"  {file['name']} (ID: {file['id']})")
            if len(files) > 5:
                print(f"  ... y {len(files) - 5} archivos más")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nDetalles del error:")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
