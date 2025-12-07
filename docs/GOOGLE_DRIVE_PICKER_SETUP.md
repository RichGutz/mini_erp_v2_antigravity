# Configuración de Google Drive Picker para Repositorio

## Instrucciones de Configuración

Para usar el módulo de Repositorio con Google Drive Picker, necesitas configurar las credenciales de Google Cloud.

### 1. Crear Proyecto en Google Cloud Console

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Anota el **Project ID**

### 2. Habilitar APIs

1. Ve a **APIs & Services** → **Library**
2. Busca y habilita:
   - **Google Drive API**
   - **Google Picker API**

### 3. Crear OAuth 2.0 Client ID

1. Ve a **APIs & Services** → **Credentials**
2. Click en **Create Credentials** → **OAuth client ID**
3. Selecciona **Web application**
4. Configura:
   - **Name**: Mini ERP V2 Antigravity
   - **Authorized JavaScript origins**:
     - `http://localhost:8501` (para desarrollo local)
     - Tu URL de producción si aplica
   - **Authorized redirect URIs**:
     - `http://localhost:8501` (para desarrollo local)
     - Tu URL de producción si aplica
5. Guarda y anota:
   - **Client ID** (termina en `.apps.googleusercontent.com`)
   - **Client Secret**

### 4. Crear API Key

1. En **APIs & Services** → **Credentials**
2. Click en **Create Credentials** → **API Key**
3. Anota el **API Key**
4. (Opcional) Restringe el API Key:
   - Click en el API Key creado
   - En **API restrictions**, selecciona **Restrict key**
   - Marca **Google Drive API** y **Google Picker API**

### 5. Configurar secrets.toml

Edita el archivo `.streamlit/secrets.toml` y agrega:

```toml
[google]
client_id = "TU_CLIENT_ID.apps.googleusercontent.com"
client_secret = "TU_CLIENT_SECRET"
api_key = "TU_API_KEY"
drive_folder_id = "1hOomiUg0Gw3VBpsyLYFcUGBLe9ujewV-"
```

**Nota**: El `drive_folder_id` es el ID de la carpeta raíz del repositorio en Google Drive. Puedes obtenerlo de la URL de la carpeta:
`https://drive.google.com/drive/folders/[FOLDER_ID]`

### 6. Verificar Configuración

1. Reinicia el servidor de Streamlit
2. Navega al módulo "Repositorio"
3. Si la configuración es correcta, verás el botón "Abrir Selector de Archivos"
4. Si hay errores, se mostrarán mensajes de error con instrucciones

## Solución de Problemas

### Error: "Falta la clave ... en secrets.toml"
- Verifica que el archivo `.streamlit/secrets.toml` existe
- Confirma que todas las claves están presentes: `client_id`, `client_secret`, `api_key`, `drive_folder_id`

### Error al abrir el selector
- Verifica que las APIs están habilitadas en Google Cloud Console
- Confirma que las credenciales son correctas
- Revisa que las URLs autorizadas incluyen tu URL actual

### El picker no muestra archivos
- Verifica que el `drive_folder_id` es correcto
- Confirma que la cuenta de Google tiene acceso a la carpeta
- Revisa los permisos de la carpeta en Google Drive
