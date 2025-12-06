# src/utils/google_drive_manager.py

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
from typing import List, Dict, Optional

class GoogleDriveManager:
    """Gestor de Google Drive para operaciones CRUD de archivos y carpetas"""
    
    def __init__(self):
        """Inicializa la conexión con Google Drive usando credenciales de Streamlit secrets"""
        try:
            # Cargar credenciales desde secrets.toml
            credentials_dict = {
                "type": st.secrets["google_drive"]["type"],
                "project_id": st.secrets["google_drive"]["project_id"],
                "private_key_id": st.secrets["google_drive"]["private_key_id"],
                "private_key": st.secrets["google_drive"]["private_key"],
                "client_email": st.secrets["google_drive"]["client_email"],
                "client_id": st.secrets["google_drive"]["client_id"],
                "auth_uri": st.secrets["google_drive"]["auth_uri"],
                "token_uri": st.secrets["google_drive"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["google_drive"]["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["google_drive"]["client_x509_cert_url"],
            }
            
            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            
            self.service = build('drive', 'v3', credentials=credentials)
            
        except Exception as e:
            raise Exception(f"Error al conectar con Google Drive: {e}")
    
    def find_folder_by_name(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Busca una carpeta por nombre y retorna su ID
        
        Args:
            folder_name: Nombre de la carpeta a buscar
            parent_id: ID de la carpeta padre (opcional)
        
        Returns:
            ID de la carpeta o None si no existe
        """
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            items = results.get('files', [])
            return items[0]['id'] if items else None
            
        except Exception as e:
            print(f"Error al buscar carpeta: {e}")
            return None
    
    def list_folders(self, parent_id: Optional[str] = None) -> List[Dict]:
        """
        Lista todas las carpetas en una ubicación
        
        Args:
            parent_id: ID de la carpeta padre (None = raíz)
        
        Returns:
            Lista de diccionarios con información de carpetas
        """
        try:
            query = "mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, createdTime, modifiedTime)',
                orderBy='name'
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            print(f"Error al listar carpetas: {e}")
            return []
    
    def list_files(self, parent_id: Optional[str] = None) -> List[Dict]:
        """
        Lista todos los archivos en una carpeta
        
        Args:
            parent_id: ID de la carpeta padre
        
        Returns:
            Lista de diccionarios con información de archivos
        """
        try:
            query = "mimeType!='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink)',
                orderBy='name'
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            print(f"Error al listar archivos: {e}")
            return []
    
    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Crea una nueva carpeta
        
        Args:
            folder_name: Nombre de la carpeta
            parent_id: ID de la carpeta padre (None = raíz)
        
        Returns:
            ID de la carpeta creada o None si falla
        """
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            return folder.get('id')
            
        except Exception as e:
            print(f"Error al crear carpeta: {e}")
            return None
    
    def upload_file(self, file_path: str, file_name: str, parent_id: Optional[str] = None, mime_type: str = 'application/pdf') -> Optional[str]:
        """
        Sube un archivo a Google Drive
        
        Args:
            file_path: Ruta local del archivo
            file_name: Nombre del archivo en Drive
            parent_id: ID de la carpeta destino
            mime_type: Tipo MIME del archivo
        
        Returns:
            ID del archivo subido o None si falla
        """
        try:
            file_metadata = {'name': file_name}
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            media = MediaFileUpload(file_path, mimetype=mime_type)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            return file.get('id')
            
        except Exception as e:
            print(f"Error al subir archivo: {e}")
            return None
    
    def upload_file_from_bytes(self, file_bytes: bytes, file_name: str, parent_id: Optional[str] = None, mime_type: str = 'application/pdf') -> Optional[str]:
        """
        Sube un archivo desde bytes a Google Drive
        
        Args:
            file_bytes: Contenido del archivo en bytes
            file_name: Nombre del archivo en Drive
            parent_id: ID de la carpeta destino
            mime_type: Tipo MIME del archivo
        
        Returns:
            ID del archivo subido o None si falla
        """
        try:
            file_metadata = {'name': file_name}
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            from googleapiclient.http import MediaIoBaseUpload
            media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            return file.get('id')
            
        except Exception as e:
            print(f"Error al subir archivo desde bytes: {e}")
            return None
    
    def download_file(self, file_id: str) -> Optional[bytes]:
        """
        Descarga un archivo de Google Drive
        
        Args:
            file_id: ID del archivo
        
        Returns:
            Contenido del archivo en bytes o None si falla
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            return file_buffer.getvalue()
            
        except Exception as e:
            print(f"Error al descargar archivo: {e}")
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """
        Elimina un archivo o carpeta
        
        Args:
            file_id: ID del archivo o carpeta
        
        Returns:
            True si se eliminó correctamente, False si falla
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
            
        except Exception as e:
            print(f"Error al eliminar archivo: {e}")
            return False
    
    def search_files(self, query: str, parent_id: Optional[str] = None) -> List[Dict]:
        """
        Busca archivos por nombre
        
        Args:
            query: Texto a buscar en el nombre
            parent_id: ID de la carpeta donde buscar (None = todas)
        
        Returns:
            Lista de archivos que coinciden
        """
        try:
            search_query = f"name contains '{query}' and trashed=false"
            if parent_id:
                search_query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=search_query,
                spaces='drive',
                fields='files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink)',
                orderBy='name'
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            print(f"Error al buscar archivos: {e}")
            return []
