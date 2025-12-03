# Prompts Aprobados

Este documento sirve como repositorio central para los prompts que han sido validados y aprobados por el usuario.

## Estructura
Cada entrada debe contener:
- **Título**: Breve descripción del propósito del prompt.
- **Prompt**: El contenido exacto del prompt.
- **Fecha de Aprobación**: Cuándo fue validado.
- **Contexto/Notas**: (Opcional) Para qué situación específica se diseñó.

---

## [Ejemplo] Prompt de Inicialización
**Fecha:** 2025-12-02
**Contexto:** Prompt inicial para configurar el comportamiento del agente.

```markdown
Eres un experto desarrollador Python...
```

---

## [Borrador] Prompt Maestro de Migración (Legacy -> V2)
**Fecha:** 2025-12-02
**Contexto:** Estándar para migrar módulos del ERP antiguo a la nueva arquitectura V2 (FastAPI + Streamlit).

```markdown
**Rol:** Ingeniero de Software Senior (Python/FastAPI/Streamlit).
**Objetivo:** Migrar el módulo `[NOMBRE_DEL_MODULO]` a la arquitectura V2.

**Fases de Trabajo:**

1.  **Análisis y Mapa de Variables:**
    *   Analiza el código legacy proporcionado.
    *   Genera un "Mapa de Variables" identificando: Entradas, Variables de Proceso (cálculos intermedios) y Salidas (Outputs finales).
    *   *Regla:* Mantén los nombres de variables originales del negocio para facilitar la trazabilidad.

2.  **Documentación Preliminar:**
    *   Crea/Actualiza `documentation/[nombre_modulo].md` con la lógica detectada.

3.  **Implementación (Arquitectura V2):**
    *   **Backend (`src/api/`):** Crea endpoints en FastAPI para la lógica de negocio. Separa la lógica en servicios (`src/services/`) si es compleja.
    *   **Frontend (`pages/`):** Crea la interfaz en Streamlit. *Importante:* El frontend solo debe consumir la API, no realizar cálculos de negocio directos.

4.  **Verificación:**
    *   Sigue los pasos de `testing/procedimientos_testeo.md`.
    *   Indica qué comandos ejecutar para validar (ej: `uvicorn` para backend, `streamlit` para frontend).
```

---

## [Borrador] Prompt Corrección Bug: Credenciales Supabase
**Fecha:** 2025-12-02
**Contexto:** Error "Supabase credentials not found" al ejecutar scripts o backend local.

```markdown
**Rol:** Backend Developer (Python).
**Problema:** El cliente de Supabase (`src/data/supabase_client.py`) falla al no encontrar `SUPABASE_URL` y `SUPABASE_KEY` cuando se ejecuta fuera de Streamlit (ej: scripts, uvicorn).
**Causa Raíz:** Falta cargar las variables del archivo `.env` en el entorno local.

**Tareas:**
1.  **Dependencias:**
    *   Agregar `python-dotenv` a `requirements.txt`.
2.  **Código (`src/data/supabase_client.py`):**
    *   Importar `load_dotenv` de `dotenv`.
    *   Llamar a `load_dotenv()` al inicio de `get_supabase_client` (o a nivel de módulo) para asegurar que las variables del `.env` se carguen en `os.environ`.
3.  **Verificación:**
    *   Asegurar que el código siga siendo compatible con Streamlit Cloud (donde no hay `.env` pero sí `st.secrets`).
```

### Ejecución (2025-12-02)
**Estado:** Completado (Código implementado).
**Cambios Realizados:**
1.  Agregado `python-dotenv` a `requirements.txt`.
2.  Modificado `src/data/supabase_client.py` para usar `load_dotenv()`.
3.  Creado `.env.example` como guía.
**Nota:** La verificación automática falló porque falta el archivo `.env` real con las credenciales. El usuario debe crearlo manualmente basándose en el ejemplo.

---

## [Borrador] Prompt Corrección Bug: Fecha de Emisión en UI
**Fecha:** 2025-12-02
**Contexto:** La interfaz de Operaciones muestra la fecha de hoy en lugar de la fecha parseada del PDF.

```markdown
**Rol:** Frontend Developer (Streamlit).
**Problema:** El campo "Fecha de Emisión" en `pages/01_Operaciones.py` muestra la fecha actual en lugar de la fecha extraída del PDF.
**Causa Raíz:** El widget `st.date_input` (línea ~463) no tiene el parámetro `value` configurado, por lo que Streamlit usa `datetime.date.today()` por defecto.

**Tareas:**
1.  **Código (`pages/01_Operaciones.py`, línea ~463):**
    *   Agregar el parámetro `value=fecha_emision_obj if fecha_emision_obj else datetime.date.today()` al `st.date_input` de "Fecha de Emisión".
2.  **Verificación:**
    *   Subir un PDF de prueba (`pruebas/E001-1142.pdf`).
    *   Confirmar que la fecha mostrada coincide con la del PDF (26-08-2025) y no con la fecha actual.
```

### Ejecución (2025-12-02)
**Estado:** Completado.
**Cambios Realizados:**
1.  Modificado `pages/01_Operaciones.py` línea 463: Agregado parámetro `value` al `st.date_input`.
2.  Corregido import incorrecto en línea 18: Cambiado de `pages.liquidacion_builder` a `src.utils.pdf_generators`.
**Resultado:** El campo "Fecha de Emisión" ahora muestra correctamente la fecha parseada del PDF.

---

## Prompt Simplificación UI: Eliminar Campo "Plazo de Crédito"
**Fecha:** 2025-12-02
**Contexto:** El usuario reporta que el campo "Plazo de Crédito (días)" no le sirve y prefiere trabajar solo con "Fecha de Pago".

```markdown
**Rol:** Frontend Developer (Streamlit).
**Objetivo:** Simplificar la UI del módulo de Operaciones eliminando el campo "Plazo de Crédito (días)" y dejando solo "Fecha de Pago".

**Análisis Previo:**
- El campo `plazo_credito_dias` debe mantenerse internamente (se calcula automáticamente)
- La validación debe cambiar de `plazo_credito_dias` a `fecha_pago_calculada`
- Riesgo: BAJO (cambios seguros y bien delimitados)

**Tareas:**
1.  **Función `update_date_calculations`:**
    *   Eliminar bloque `if changed_field == 'plazo'`
    *   Simplificar lógica para calcular solo desde fecha de pago
    *   Mantener cálculo automático de `plazo_credito_dias` (interno)

2.  **Función `validate_inputs`:**
    *   Cambiar validación: `"plazo_credito_dias"` → `"fecha_pago_calculada"`

3.  **UI (líneas ~456-508):**
    *   Reducir columnas de 6 a 5
    *   Eliminar callback `plazo_changed`
    *   Eliminar widget `st.number_input` de "Plazo de Crédito (días)"

4.  **Verificación:**
    *   Probar carga de PDF
    *   Ingresar fecha de pago manualmente
    *   Verificar que `plazo_operacion_calculado` se muestre correctamente
```

### Ejecución (2025-12-02)
**Estado:** Completado.
**Cambios Realizados:**
1.  Simplificada función `update_date_calculations` (líneas 43-80): Eliminados bloques de cálculo desde plazo.
2.  Actualizada función `validate_inputs` (línea 234): Cambiada validación a `fecha_pago_calculada`.
3.  Reducidas columnas de 6 a 5 (línea 456).
4.  Eliminado callback `plazo_changed` (líneas 477-480).
5.  Eliminado widget `st.number_input` de plazo (líneas 498-508).
**Resultado:** UI simplificada. El usuario solo ingresa "Fecha de Pago" y el sistema calcula automáticamente el plazo interno.

**Fix Adicional (2025-12-02):**
- Agregado parámetro `value` a widgets `st.date_input` de fecha de pago y desembolso
- **Problema resuelto:** Los cambios en las fechas ahora actualizan inmediatamente el "Plazo de Operación (días)"
- Commit: `fix: Agregar value a date_input para cálculos inmediatos de plazo`

**Fix Adicional 2 (2025-12-02):**
- Modificado widget de "Plazo de Operación" para leer directamente desde `st.session_state.invoices_data[idx]`
- **Problema resuelto:** El plazo de operación ahora se actualiza correctamente cuando cambian las fechas
- **Causa raíz:** El widget leía de la variable local `invoice` que no se actualizaba después de los callbacks
- Commit: `fix: Plazo de operación ahora lee desde session_state para actualización inmediata`

**Validación de Fechas (2025-12-02):**
- Agregado warning cuando la fecha de pago es anterior a la fecha de desembolso
- **Lógica de negocio:** La fecha de desembolso debe ser anterior a la fecha de pago
- **Comportamiento:** Si las fechas están en orden incorrecto, muestra warning y plazo = 0
- Commit: `feat: Agregar warning cuando fecha de pago es anterior a fecha de desembolso`

---

## [Validado] Método de Testing del Algoritmo Universal
**Fecha:** 2025-12-02
**Contexto:** Validación rigurosa del motor de cálculo `src/core/factoring_system.py` contra escenarios de negocio reales.

```markdown
**Objetivo:** Asegurar que el algoritmo de "Liquidación Universal" coincida matemáticamente con la lógica de negocio definida en el archivo `CASOS.LIQUIDACIONES.COMPREHENSIVE.CHRISTIE.FEEDBACK.csv`.

**Metodología:**
1.  **Script Automatizado:** Se creó `testing/test_liquidacion_csv.py`.
2.  **Datos de Entrada:** Extraídos directamente del CSV (Capital: 17,822.01, Tasa: 2%, Mora: 3%).
3.  **Escenarios Validados:**
    *   **Liquidación 1 (Pago Anticipado):** Verifica devolución de intereses cobrados en exceso.
    *   **Liquidación 2 (Pago Parcial):** Verifica saldo negativo (deuda de Inandes al cliente) por pago parcial anticipado.
    *   **Liquidación 3 (Back Door):** Verifica que saldos menores al mínimo (S/ 100) se perdonen automáticamente (Saldo 0.01 -> 0.00).
    *   **Liquidación 5 (Mora):** Verifica cálculo de intereses moratorios (3% mensual) sobre días de atraso.
    *   **Liquidación 9A (Pago Parcial con Mora):** Verifica cálculo complejo donde el pago parcial cubre intereses y mora, dejando un remanente de capital.
    *   **Liquidación 9B (Nuevo Calendario):** Verifica que el remanente de la 9A se convierta correctamente en el capital inicial de un nuevo calendario.

**Resultados:**
✅ Todos los escenarios pasaron con coincidencia exacta (o diferencia < 0.01 por redondeo).
- El algoritmo implementa fielmente la fórmula de interés compuesto (Excel POWER).
- La lógica de "Back Door" (reducción en cascada) funciona según lo especificado.
- La transición de mora a nuevo calendario (9A -> 9B) es correcta.

**Artefacto:** `testing/test_liquidacion_csv.py` (Disponible en el repositorio para regression testing).
```
