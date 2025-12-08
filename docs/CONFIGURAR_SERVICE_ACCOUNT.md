# Guía: Configurar Service Account para Uploads del ERP

## 📋 Objetivo

Permitir que el ERP suba archivos a Google Drive de forma centralizada, independientemente del usuario que esté logueado.

## 🔑 Service Account Email

```
inandes-drive-service@mini-erp-v2-antigravity.iam.gserviceaccount.com
```

**IMPORTANTE:** Este es el "usuario virtual" del ERP. Todos los archivos subidos desde el ERP serán propiedad de esta cuenta.

---

## 📁 Paso 1: Crear o Seleccionar Carpeta Centralizada

### Opción A: Crear Nueva Carpeta

1. Ve a [Google Drive](https://drive.google.com)
2. Click en **"+ Nuevo"** → **"Carpeta"**
3. Nombre sugerido: **"ERP - Documentos Centralizados"**
4. Click en **"Crear"**

### Opción B: Usar Carpeta Existente

1. Ve a Google Drive
2. Localiza la carpeta donde quieres centralizar los documentos del ERP
3. Continúa con el Paso 2

---

## 🔓 Paso 2: Compartir Carpeta con el Service Account

### Instrucciones Detalladas:

1. **Click derecho** en la carpeta que creaste/seleccionaste

2. Selecciona **"Compartir"** (o **"Share"**)

3. En el campo **"Agregar personas y grupos"**:
   - Pega este email completo:
   ```
   inandes-drive-service@mini-erp-v2-antigravity.iam.gserviceaccount.com
   ```

4. En el menú desplegable de permisos, selecciona:
   - ✅ **"Editor"** (permite al ERP crear y modificar archivos)
   - ❌ NO uses "Lector" (solo lectura, el upload fallará)
   - ❌ NO uses "Comentador" (no permite subir archivos)

5. **OPCIONAL - Desmarcar "Notificar a las personas":**
   - El Service Account es una cuenta virtual (no recibe emails)
   - Puedes desmarcar esta opción sin problema

6. Click en **"Enviar"** o **"Compartir"**

---

## ✅ Paso 3: Verificar que se Compartió Correctamente

### Verificación Visual:

1. Abre la carpeta en Google Drive

2. En la parte superior derecha, verás un ícono de personas 👥

3. Click en ese ícono → Verás la lista de personas con acceso

4. Deberías ver:
   ```
   inandes-drive-service@mini-erp... [Editor]
   [Tu nombre/email] [Propietario]
   ```

### Verificación Alternativa:

1. Click derecho en la carpeta → **"Compartir"**

2. En la sección **"Personas con acceso"** deberías ver:
   - `inandes-drive-service@mini-erp-v2-antigravity.iam.gserviceaccount.com` - **Editor**

---

## 🎯 Paso 4: Probar Upload desde el ERP

### Prueba en Módulo Originación:

1. Abre el ERP y loguéate con tu cuenta de Google

2. Ve al módulo **"Originación"**

3. Completa el formulario y genera un perfil de operación

4. En la sección **"Guardar en Google Drive"**:
   - Click en **"📂 Guardar en Drive (Seleccionar Carpeta)"**
   - Navega y selecciona la carpeta que compartiste con el Service Account
   - Click en **"⬆️ Confirmar subida"**

5. **Resultado esperado:**
   - ✅ Mensaje: "Subiendo archivo a Google Drive con Service Account..."
   - ✅ Mensaje de éxito: "✅ ¡Archivo guardado exitosamente en Drive!"
   - ✅ Caption: "📎 File ID: [id-del-archivo]"

6. **Verificación en Google Drive:**
   - Ve a la carpeta
   - Deberías ver el archivo PDF subido
   - Click derecho → "Detalles"
   - Propietario: `inandes-drive-service@mini-erp-v2-antigravity...`

---

## ❌ Resolución de Problemas

### Problema 1: Error "Permission denied" o "403 Forbidden"

**Causa:** El Service Account no tiene permisos en la carpeta seleccionada

**Solución:**
1. Verifica que compartiste la carpeta correcta
2. Verifica que el email del Service Account esté bien escrito (sin espacios extra)
3. Verifica que el permiso sea **"Editor"** (no "Lector")
4. Espera 1-2 minutos (los permisos pueden tardar en propagarse)
5. Intenta de nuevo

---

### Problema 2: El Picker no muestra ninguna carpeta

**Causa:** No has iniciado sesión en el ERP (Home)

**Solución:**
1. Ve a la página de **Home**
2. Click en el botón de login con Google
3. Autoriza el acceso
4. Vuelve al módulo donde estabas

---

### Problema 3: Error "No se encontraron credenciales del Service Account"

**Causa:** Problema con la configuración de secrets.toml

**Solución:**
1. Verifica que el archivo `.streamlit/secrets.toml` tenga la sección `[google_drive]`
2. Si estás en Streamlit Cloud, verifica los Secrets en el dashboard
3. Contacta al administrador del ERP

---

## 📖 Estructura Recomendada de Carpetas

Para mejor organización, sugerimos esta estructura:

```
📁 ERP - Documentos Centralizados
├── 📁 Originación
│   ├── 📁 [EMISOR 1]
│   │   ├── 📁 Contrato_001
│   │   │   ├── 📁 Anexo_001
│   │   │   └── 📁 Anexo_002
│   │   └── 📁 Contrato_002
│   └── 📁 [EMISOR 2]
├── 📁 Desembolso
│   └── 📁 Vouchers
└── 📁 Liquidación
    └── 📁 Anexos de Liquidación
```

**Importante:** Solo necesitas compartir la carpeta raíz con el Service Account. Las subcarpetas heredan los permisos automáticamente.

---

## 🔐 Seguridad y Mejores Prácticas

### ✅ Buenas Prácticas:

1. **Carpeta dedicada:** Crea una carpeta específica para el ERP, no uses tu carpeta personal
2. **Permisos mínimos:** El Service Account solo debe tener acceso a las carpetas del ERP
3. **Organización:** Mantén una estructura de subcarpetas clara
4. **Backup:** Google Drive mantiene versiones automáticas de los archivos

### ❌ Evitar:

1. No compartas la carpeta raíz de tu Drive completo
2. No des permisos de "Propietario" al Service Account (solo "Editor")
3. No elimines el acceso del Service Account después de configurarlo

---

## 📞 Soporte

Si tienes problemas con la configuración:

1. Verifica que seguiste todos los pasos de esta guía
2. Revisa la sección de **Resolución de Problemas**
3. Contacta al administrador del sistema
