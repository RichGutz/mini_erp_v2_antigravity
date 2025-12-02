# Procedimientos de Testeo y Lanzamiento Local

## 🚀 Resumen Rápido (Comandos para Copiar y Pegar)

Abre dos terminales de PowerShell en la carpeta raíz del proyecto (`mini_erp_v2_antigravity`).

**Terminal 1: Backend (API)**
```powershell
# Configurar URL del backend (opcional si ya está en .env, pero recomendado para asegurar)
$env:BACKEND_API_URL="http://127.0.0.1:8000"

# Iniciar el servidor
uvicorn src.api.main:app --reload --port 8000
```

**Terminal 2: Frontend (Streamlit)**
```powershell
# Configurar URL del backend para que Streamlit sepa dónde conectar
$env:BACKEND_API_URL="http://127.0.0.1:8000"

# Iniciar la aplicación
streamlit run 00_Home.py
```

---

Este documento detalla los pasos necesarios para levantar el entorno de desarrollo local y realizar pruebas en el Mini ERP v2.

## Prerrequisitos

- Python 3.12+ instalado.
- Entorno virtual activado (recomendado).
- Variables de entorno configuradas (especialmente `SUPABASE_URL`, `SUPABASE_KEY` y `BACKEND_API_URL`).

## 1. Iniciar el Backend (API)

El backend está construido con FastAPI y se encuentra en `src/api/main.py`. Debe ejecutarse primero para que el frontend pueda comunicarse con él.

**Comando:**
```powershell
# Desde la raíz del proyecto (mini_erp_v2_antigravity)
$env:BACKEND_API_URL="http://127.0.0.1:8000"
uvicorn src.api.main:app --reload --port 8000
```

- `--reload`: Habilita el reinicio automático al detectar cambios en el código.
- `--port 8000`: Puerto por defecto (asegúrate de que coincida con `BACKEND_API_URL`).

**Verificación:**
- Abre tu navegador en `http://127.0.0.1:8000/docs`. Deberías ver la documentación interactiva (Swagger UI) de la API.

## 2. Iniciar el Frontend (Streamlit)

El frontend es una aplicación Streamlit cuyo punto de entrada es `00_Home.py`.

**Comando:**
```powershell
# Abre una NUEVA terminal (mantén la del backend corriendo)
# Desde la raíz del proyecto
$env:BACKEND_API_URL="http://127.0.0.1:8000"
streamlit run 00_Home.py
```

**Verificación:**
- Streamlit abrirá automáticamente una pestaña en tu navegador (usualmente en `http://localhost:8501`).
- Deberías ver la página de inicio del Mini ERP.

## 3. Flujo de Prueba Típico (Liquidaciones)

1.  **Navegación**: Ve a la página **Liquidaciones** en el menú lateral.
2.  **Búsqueda**: Ingresa un ID de Lote válido (existente en Supabase) y haz clic en "Buscar Lote".
3.  **Selección**: Selecciona las facturas que deseas liquidar.
4.  **Simulación**:
    - Ajusta las fechas y montos si es necesario.
    - Haz clic en "Simular Liquidación".
    - Verifica que los cálculos mostrados en pantalla sean coherentes.
5.  **Persistencia**:
    - Haz clic en "Guardar Liquidación en Supabase".
    - Verifica que aparezca el mensaje de éxito.
6.  **Reporte**:
    - Haz clic en "Generar Reporte PDF".
    - Descarga y abre el PDF para validar el formato y los datos.

## 4. Solución de Problemas Comunes

-   **Error de Conexión**: Si el frontend muestra errores de conexión con la API, verifica que:
    -   El backend (`uvicorn`) esté corriendo sin errores en la terminal.
    -   La variable de entorno `BACKEND_API_URL` apunte a `http://127.0.0.1:8000` (o la URL correcta).
-   **Cambios no reflejados**: Si editas código de `src` y Streamlit no lo detecta, intenta reiniciar el servidor de Streamlit (Ctrl+C y volver a ejecutar). El backend con `--reload` debería actualizarse solo.
