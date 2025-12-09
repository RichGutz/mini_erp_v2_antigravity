# 🚀 PLAN MAESTRO DE SALIDA A PRODUCCIÓN (Roadmap to Production)

Este documento detalla la estrategia para transformar el MVP actual ("Mini ERP V2") en un producto de software profesional, seguro y escalable.

## 🚨 FASE 0: SEGURIDAD CRÍTICA (Inmediato)
> **Estado:** 🔴 **EMERGENCIA**
> **Objetivo:** Cerrar brechas de seguridad graves antes de cualquier otra cosa.

> [!NOTE]
> **HITO ALCANZADO:** El estado actual del código (Rama: `backup/erp_funcionando_antes_refactor`) representa el **producto más sofisticado y funcional** logrado hasta la fecha. Este punto sirve como "Golden Copy" antes de iniciar la reingeniería.

1.  **Privatizar Repositorio (URGENTE)**
    *   [x] Cambiar visibilidad de GitHub a **Private**.
    *   [ ] Verificar que `secrets.toml`, `.env` y credenciales JSON **nunca** hayan sido commiteados. Si lo fueron, rotar todas las claves inmediatamente.
2.  **Blindar Supabase (URGENTE)**
    *   [ ] Activar **Row Level Security (RLS)** en todas las tablas. (Actualmente es "público" si tienes la key anónima).
    *   [ ] Configurar políticas de acceso: "Solo usuarios autenticados pueden leer/escribir su propia data".
    *   [ ] Desactivar acceso público a tablas sensibles (`EMISORES`, `PROPUESTAS`, `USUARIOS`).
3.  **Gestión de Secretos**
    *   [ ] Auditoría de `st.secrets`: Asegurar que **ninguna** key esté harcodeada en el código.
    *   [ ] Rotación de Key de Service Account (Google Drive) y Keys de Supabase por precaución.

## 🏗️ FASE 1: ESTANDARIZACIÓN DE CÓDIGO (Refactoring)
> **Estado:** 🟡 Pendiente
> **Objetivo:** Eliminar "Código Frankenstein" y deuda técnica.

1.  **Unificación de Estilo**
    *   [ ] Implementar **Black** o **Ruff** para formateo automático (evitar mezclas de comillas, indentaciones, etc.).
    *   [ ] Estandarizar nombres de variables (snake_case para Python, nombres descriptivos).
2.  **Modularización**
    *   [ ] Extraer lógica de negocio compleja (cálculos de `Originacion` y `Liquidacion`) de la UI (`pages/`) a `src/services/` o `src/core/`.
    *   [ ] Centralizar *todas* las llamadas a BD en `src/data/supabase_repository.py`.
    *   [ ] Centralizar estilos CSS en un solo archivo `assets/style.css` en lugar de `st.markdown` dispersos.
3.  **Limpieza**
    *   [ ] Eliminar código comentado/muerto.
    *   [ ] Unificar imports (absolutos vs relativos).

## 🎨 FASE 2: UI/UX PROFESIONAL
> **Estado:** 🟡 Pendiente
> **Objetivo:** Que no parezca un "proyecto de ciencias", sino un SaaS.

1.  **Design System**
    *   [ ] Definir paleta de colores oficial y tipografía.
    *   [ ] Crear componentes reutilizables UI en `src/ui/` (Botones estándar, Tarjetas de Info, Modales).
2.  **Feedback al Usuario**
    *   [ ] Estandarizar mensajes (Toast vs Success vs Balloons). No abusar de los globos.
    *   [ ] Spinners de carga consistentes en todas las operaciones largas.
3.  **Navegación**
    *   [ ] Mejorar el Sidebar.
    *   [ ] Breadcrumbs o indicación clara de "Dónde estoy".

## 📚 FASE 3: DOCUMENTACIÓN Y PROCESOS
> **Estado:** 🟢 Iniciado
> **Objetivo:** Que el proyecto sobreviva sin ti (Bus Factor > 1).

1.  **Documentación Técnica**
    *   [ ] `README.md` robusto: Cómo instalar, cómo correr local, arquitectura.
    *   [ ] Docstrings en todas las funciones complejas.
    *   [ ] Diagrama de Arquitectura (Mermaid) actualizado.
2.  **Documentación de Usuario**
    *   [ ] Manual de Usuario (PDF o Wiki) para los empleados.
    *   [ ] Tooltips integrados en la UI (signo de interrogación `?` en campos confusos).
3.  **CI/CD (DevOps)**
    *   [ ] Pipeline básico de GitHub Actions (Linting automático).
    *   [ ] Entornos separados (Dev vs Prod) en Supabase y Render.

## 🧪 FASE 4: TESTING
> **Estado:** ⚪ No Iniciado
> **Objetivo:** Dormir tranquilo cuando haces deploy.

1.  **Tests Unitarios**
    *   [ ] Tests para cálculos financieros (Intereses, Moras).
    *   [ ] Tests para parsers de PDF.
2.  **Tests de Integración**
    *   [ ] Flujo completo: Carga -> Cálculo -> Guardado -> Drive.
