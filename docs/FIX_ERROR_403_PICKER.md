# SOLUCIÓN DEFINITIVA: Error 403 en Google Picker

## 🎯 Problema Identificado

El error 403 ocurre porque el **OAuth 2.0 Client ID** en Google Cloud Console NO tiene configurado el `redirect_uri` que usa el componente `streamlit-oauth` en el módulo de Repositorio.

### Redirect URI Actual en el Código (línea 72 de 07_Repositorio.py):
```
https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app/component/streamlit_oauth.authorize
```

Este redirect_uri **DEBE** estar en la lista de "Authorized redirect URIs" en Google Cloud Console.

---

## ✅ SOLUCIÓN PASO A PASO

### 1. Ir a Google Cloud Console

https://console.cloud.google.com/apis/credentials?project=mini-erp-v2-antigravity

### 2. Editar OAuth 2.0 Client ID

Busca tu OAuth 2.0 Client ID:
```
192650838968-mr4kv4vm6qrch4qult0j5amgj3lv12nj.apps.googleusercontent.com
```

Click en el **ícono de lápiz** (editar) a la derecha.

### 3. Configurar "Authorized JavaScript origins"

En la sección **"Authorized JavaScript origins"**, asegúrate de tener:

```
https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app
```

**IMPORTANTE**: 
- ❌ NO incluyas `/` al final
- ❌ NO incluyas rutas como `/component/...`
- ✅ Solo el dominio base

### 4. Configurar "Authorized redirect URIs" ⚠️ CRÍTICO

En la sección **"Authorized redirect URIs"**, agrega **TODAS** estas URLs:

```
https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app
https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app/
https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app/component/streamlit_oauth.authorize
https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app/component/streamlit_oauth.authorize_callback
```

**Explicación**:
- La primera es para el OAuth del Home
- La tercera es la que usa el módulo Repositorio (línea 72)
- La cuarta es para el callback del componente OAuth

### 5. Habilitar Google Drive API

Ve a: https://console.cloud.google.com/apis/library?project=mini-erp-v2-antigravity

Busca y habilita:
- ✅ **Google Drive API**
- ✅ **Google Picker API**

### 6. Configurar Scopes del OAuth Consent Screen

Ve a: https://console.cloud.google.com/apis/credentials/consent?project=mini-erp-v2-antigravity

En la sección **"Scopes"**, asegúrate de tener:

- ✅ `openid`
- ✅ `email`
- ✅ `profile`
- ✅ `https://www.googleapis.com/auth/drive.file`
- ✅ `https://www.googleapis.com/auth/drive.readonly`

Si no están, agrégalos:
1. Click en "EDIT APP"
2. Click en "SAVE AND CONTINUE" hasta llegar a "Scopes"
3. Click en "ADD OR REMOVE SCOPES"
4. Busca y marca los scopes de Drive
5. Click en "UPDATE"
6. Click en "SAVE AND CONTINUE"

### 7. Guardar y Esperar

1. Click en **"SAVE"** en todas las configuraciones
2. ⏰ **Espera 5-10 minutos** para que los cambios se propaguen
3. Limpia la cache del navegador o usa modo incógnito

---

## 🔍 Verificación

### Paso 1: Verificar Configuración en Google Cloud Console

Asegúrate de que tu OAuth 2.0 Client ID tenga:

**Authorized JavaScript origins:**
```
✅ https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app
```

**Authorized redirect URIs:**
```
✅ https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app
✅ https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app/
✅ https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app/component/streamlit_oauth.authorize
✅ https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app/component/streamlit_oauth.authorize_callback
```

### Paso 2: Probar en la Aplicación

1. Ve a: https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app
2. Navega al módulo **Repositorio**
3. Click en **"Iniciar sesión con Google"**
4. Deberías ver la pantalla de consentimiento de Google (no error 403)
5. Autoriza la aplicación
6. Deberías ver "✅ Autenticado con Google"
7. Click en **"🔍 Seleccionar archivos de Google Drive"**
8. El Google Picker debería abrirse sin error 403

---

## 🐛 Si el Error Persiste

### Opción 1: Verificar en DevTools

1. Abre DevTools (F12)
2. Ve a la pestaña **Console**
3. Intenta autenticarte
4. Busca mensajes de error que mencionen:
   - `redirect_uri_mismatch`
   - `origin_mismatch`
   - `403`
5. Comparte el mensaje exacto del error

### Opción 2: Verificar el Redirect URI Exacto

El error 403 con mensaje "redirect_uri_mismatch" significa que el redirect_uri en el código NO coincide con ninguno en Google Cloud Console.

**Verifica que el redirect_uri en línea 72 de 07_Repositorio.py sea EXACTAMENTE:**
```python
redirect_uri="https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app/component/streamlit_oauth.authorize"
```

Y que esta URL EXACTA esté en "Authorized redirect URIs" en Google Cloud Console.

### Opción 3: Usar el Mismo OAuth del Home

Una alternativa es modificar el módulo Repositorio para usar el mismo OAuth que ya está autenticado en Home:

```python
# En lugar de crear un nuevo OAuth, reutilizar el token del Home
if 'token' in st.session_state:
    # Usuario ya autenticado en Home
    st.session_state.access_token = st.session_state.token.get('access_token')
```

Pero esto requiere que el OAuth del Home tenga los scopes de Drive.

---

## 📝 Resumen de Configuración Final

### Google Cloud Console - OAuth 2.0 Client ID

**Client ID:**
```
192650838968-mr4kv4vm6qrch4qult0j5amgj3lv12nj.apps.googleusercontent.com
```

**Authorized JavaScript origins:**
```
https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app
```

**Authorized redirect URIs:**
```
https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app
https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app/
https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app/component/streamlit_oauth.authorize
https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app/component/streamlit_oauth.authorize_callback
```

### OAuth Consent Screen - Scopes

```
openid
email
profile
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/drive.readonly
```

### APIs Habilitadas

```
✅ Google Drive API
✅ Google Picker API
```

---

## ⚠️ Nota Importante sobre Secrets

El módulo Repositorio usa `st.secrets["google"]` mientras que el Home usa `st.secrets["google_oauth"]`.

**Asegúrate de que tu secrets.toml en Streamlit Cloud tenga AMBAS secciones:**

```toml
[google_oauth]
client_id = "TU_CLIENT_ID.apps.googleusercontent.com"
client_secret = "TU_CLIENT_SECRET"
redirect_uri = "https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app"

[google]
client_id = "TU_CLIENT_ID.apps.googleusercontent.com"
client_secret = "TU_CLIENT_SECRET"
api_key = "TU_API_KEY_AQUI"
drive_folder_id = "1hOomiUg0Gw3VBpsyLYFcUGBLe9ujewV-"
```

**Pueden usar el mismo Client ID y Secret**, solo necesitas configurar los redirect URIs y scopes correctamente en Google Cloud Console.
