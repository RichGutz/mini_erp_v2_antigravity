# Crear API Key SIN Restricciones (Para Debugging)

## Opción Simplificada para Resolver Error 403

Si no encuentras la opción de HTTP referrers o quieres probar rápidamente, crea una API Key sin restricciones de aplicación.

---

## Pasos

### 1. Ir a Google Cloud Console - Credentials

https://console.cloud.google.com/apis/credentials?project=mini-erp-v2-antigravity

### 2. Crear Nueva API Key

1. Click en **"+ CREATE CREDENTIALS"** (botón azul arriba)
2. Selecciona **"API key"**
3. Se creará una nueva API Key
4. **Copia la API Key** (ejemplo: `AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567`)
5. Click en **"RESTRICT KEY"** (o cierra el popup y edita la key)

### 3. Configurar la API Key

En la página de edición de la API Key:

#### A. Application restrictions (Restricciones de Aplicación)

**Selecciona:**
- ⚪ **None** ← Selecciona esta opción

Esto permite que la API Key funcione desde cualquier origen (menos seguro, pero útil para debugging).

#### B. API restrictions (Restricciones de API)

**Selecciona:**
- ⚪ **Restrict key** ← Selecciona esta opción

**Marca estas APIs:**
- ✅ Google Drive API
- ✅ Google Picker API

### 4. Guardar

Click en **"SAVE"** (botón azul abajo)

---

## Actualizar secrets.toml en Streamlit Cloud

### Opción A: Desde Streamlit Cloud Dashboard

1. Ve a: https://share.streamlit.io/
2. Click en tu app: **mini_erp_v2_antigravity**
3. Click en **"Settings"** (⚙️)
4. Click en **"Secrets"**
5. Edita la sección `[google]`:

```toml
[google]
client_id = "TU_CLIENT_ID.apps.googleusercontent.com"
client_secret = "TU_CLIENT_SECRET"
api_key = "TU_NUEVA_API_KEY_AQUI"  # ← Pega tu nueva API Key
drive_folder_id = "1hOomiUg0Gw3VBpsyLYFcUGBLe9ujewV-"
```

6. Click **"Save"**
7. La app se reiniciará automáticamente

---

## Verificación

1. Espera 2-3 minutos para que la app se reinicie
2. Ve a tu app: https://minierpv2antigravity-wwnqmavykpjtsogtphufpa.streamlit.app
3. Navega al módulo **Repositorio**
4. Intenta abrir el Google Picker
5. El error 403 debería desaparecer

---

## ⚠️ Importante: Seguridad

**Esta configuración (None) es menos segura** porque permite que cualquier sitio web use tu API Key.

**Para producción**, deberías:
1. Probar que funciona con "None"
2. Una vez confirmado, cambiar a "HTTP referrers"
3. Agregar solo tu dominio de Streamlit Cloud

**Pero para debugging ahora, "None" es la opción más rápida.**

---

## Si el Error Persiste

Si después de esto el error 403 persiste, el problema está en:
- **OAuth 2.0 Client ID** (JavaScript origins y redirect URIs)
- No en el API Key

Asegúrate de haber configurado también el OAuth 2.0 Client ID según la guía principal.
