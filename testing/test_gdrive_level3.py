#!/usr/bin/env python3
"""
Script de prueba independiente para verificar creación de carpetas nivel 3 en Google Drive.
Este script NO afecta la aplicación Streamlit principal.
"""

import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import Optional

class GoogleDriveTest:
    """Prueba de creación de carpetas multinivel"""
    
    def __init__(self, credentials_path: str):
        """Inicializa conexión con Google Drive usando archivo JSON de credenciales"""
        try:
            # Leer credenciales desde archivo JSON
            with open(credentials_path, 'r') as f:
                credentials_dict = json.load(f)
            
            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            
            self.service = build('drive', 'v3', credentials=credentials)
            print("✓ Conexión a Google Drive exitosa")
            
        except Exception as e:
            print(f"✗ Error al conectar: {e}")
            raise
    
    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """Crea una carpeta y retorna su ID"""
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
                print(f"  → Creando '{folder_name}' dentro de parent_id: {parent_id}")
            else:
                print(f"  → Creando '{folder_name}' en raíz")
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id, name, parents'
            ).execute()
            
            folder_id = folder.get('id')
            print(f"  ✓ Carpeta creada: {folder_name} (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            print(f"  ✗ Error al crear '{folder_name}': {e}")
            return None
    
    def delete_folder(self, folder_id: str, folder_name: str):
        """Elimina una carpeta"""
        try:
            self.service.files().delete(fileId=folder_id).execute()
            print(f"  ✓ Eliminada: {folder_name}")
        except Exception as e:
            print(f"  ✗ Error al eliminar '{folder_name}': {e}")
    
    def test_three_levels(self):
        """Prueba creación de estructura de 3 niveles"""
        print("\n" + "="*60)
        print("PRUEBA: Creación de Carpetas en 3 Niveles")
        print("="*60)
        
        created_folders = []
        
        try:
            # Nivel 1: Raíz → Test Trans Star
            print("\n[NIVEL 1] Raíz → Test Trans Star")
            folder1_id = self.create_folder("Test Trans Star")
            if not folder1_id:
                print("✗ FALLO en nivel 1")
                return False
            created_folders.append((folder1_id, "Test Trans Star"))
            
            # Nivel 2: Test Trans Star → Test Contrato Uno
            print("\n[NIVEL 2] Test Trans Star → Test Contrato Uno")
            folder2_id = self.create_folder("Test Contrato Uno", folder1_id)
            if not folder2_id:
                print("✗ FALLO en nivel 2")
                return False
            created_folders.append((folder2_id, "Test Contrato Uno"))
            
            # Nivel 3: Test Contrato Uno → Test Anexo 1
            print("\n[NIVEL 3] Test Contrato Uno → Test Anexo 1")
            folder3_id = self.create_folder("Test Anexo 1", folder2_id)
            if not folder3_id:
                print("✗ FALLO en nivel 3")
                return False
            created_folders.append((folder3_id, "Test Anexo 1"))
            
            print("\n" + "="*60)
            print("✓ ÉXITO: Se crearon las 3 carpetas correctamente")
            print("="*60)
            return True
            
        finally:
            # Limpiar carpetas de prueba
            print("\n[LIMPIEZA] Eliminando carpetas de prueba...")
            for folder_id, folder_name in reversed(created_folders):
                self.delete_folder(folder_id, folder_name)
            print("\n✓ Limpieza completada")


def main():
    """Función principal"""
    # Ruta al archivo de credenciales
    credentials_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'secrets oauth',
        'mini-erp-v2-antigravity-cc079f4da448.json'
    )
    
    if not os.path.exists(credentials_path):
        print(f"✗ Error: No se encuentra el archivo de credenciales en: {credentials_path}")
        return
    
    try:
        tester = GoogleDriveTest(credentials_path)
        success = tester.test_three_levels()
        
        print("\n" + "="*60)
        if success:
            print("CONCLUSIÓN: La API de Google Drive PERMITE crear carpetas de nivel 3")
            print("El problema debe estar en la aplicación Streamlit (Session State, navegación, etc.)")
        else:
            print("CONCLUSIÓN: Hay un problema con la API de Google Drive o permisos")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Error fatal: {e}")


if __name__ == "__main__":
    main()
