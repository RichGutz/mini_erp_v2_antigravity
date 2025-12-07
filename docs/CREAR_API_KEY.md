# Crear API Key para Google Drive Picker

## Estado Actual
✅ OAuth 2.0 Client ID configurado
✅ OAuth 2.0 Client Secret configurado  
✅ Folder ID configurado
⚠️ **Falta: API Key**

## Pasos para Crear API Key

### 1. Ir a Google Cloud Console
Abre: https://console.cloud.google.com/apis/credentials?project=mini-erp-v2-antigravity

### 2. Crear API Key
1. Click en **"+ CREATE CREDENTIALS"** (arriba)
2. Selecciona **"API key"**
3. Se creará una nueva API Key
4. **Copia la API Key** (algo como: `AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567`)

### 3. (Opcional pero Recomendado) Restringir el API Key
1. Click en el API Key recién creado
2. En **"API restrictions"**:
   - Selecciona **"Restrict key"**
   - Marca:
     - ✅ Google Drive API
     - ✅ Google Picker API
3. Click **"SAVE"**

### 4. Actualizar secrets.toml
Reemplaza `TU_API_KEY_AQUI` con tu API Key real:

```toml
api_key = "AIzaSy_TU_API_KEY_REAL_AQUI"
```

### 5. Reiniciar Streamlit
Después de actualizar el archivo, reinicia tu servidor de Streamlit.

---

## Verificar que las APIs están Habilitadas

Asegúrate de que estas APIs están habilitadas en tu proyecto:

1. Ve a: https://console.cloud.google.com/apis/library?project=mini-erp-v2-antigravity
2. Busca y habilita:
   - ✅ **Google Drive API**
   - ✅ **Google Picker API**

---

## Archivo secrets.toml Actual

Tu archivo ya tiene esta estructura (solo falta reemplazar el API Key):

```toml
[google]
client_id = "TU_CLIENT_ID.apps.googleusercontent.com"
client_secret = "TU_CLIENT_SECRET"
api_key = "TU_API_KEY_AQUI"  # ← REEMPLAZAR ESTO
drive_folder_id = "1hOomiUg0Gw3VBpsyLYFcUGBLe9ujewV-"
```
