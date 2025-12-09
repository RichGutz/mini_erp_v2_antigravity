# 🛡️ Guía de Seguridad: Supabase Row Level Security (RLS)

Esta guía detalla los pasos para "blindar" tu base de datos Supabase, asegurando que solo el aplicativo (usando credenciales de administrador) pueda leer/escribir datos, bloqueando cualquier acceso público no autorizado.

## 1. El Concepto Clave: Keys
Supabase te da dos llaves:
1.  **`anon` key (Public):** Se usa en el frontend. Si tienes RLS activado, esta llave respeta las reglas (ej: "solo ver mis datos"). Si RLS está desactivado, ¡esta llave puede leer todo!
2.  **`service_role` key (Secret):** Es la "Llave Maestra". **Ignora el RLS**. Esta es la que debe usar tu backend/Streamlit para tener acceso total sin restricciones.

> **⚠️ IMPORTANTE:** Para que esta guía funcione sin romper tu app, debes asegurarte de que en tu `secrets.toml` estés usando la **`service_role` key**, NO la `anon` key.

## 2. Pasos para Blindar (SQL)
Ejecuta estos comandos en el **SQL Editor** de tu panel de Supabase.

### Paso A (Alternativa Turbo): Activar para TODAS las tablas 🚀
Si no quieres escribir línea por línea, copia y pega este bloque de código. **Esto activará RLS automáticamente en TODAS las tablas del esquema `public`.**

```sql
DO $$ 
DECLARE 
    r RECORD; 
BEGIN 
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP 
        EXECUTE 'ALTER TABLE "public"."' || r.tablename || '" ENABLE ROW LEVEL SECURITY;'; 
    END LOOP; 
END $$;
```

### Paso A (Manual): Activar en tablas específicas
Si prefieres tener control manual:

```sql
-- Activar RLS en tablas críticas
ALTER TABLE "EMISORES.ACEPTANTES" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "EMISORES.DEUDORES" ENABLE ROW LEVEL SECURITY; -- (Si existe)
ALTER TABLE "EMISORES.EMISORES" ENABLE ROW LEVEL SECURITY; -- (Si existe)
ALTER TABLE "OPERACIONES.PROPUESTAS" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "OPERACIONES.LIQUIDACIONES_RESUMEN" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "OPERACIONES.LIQUIDACIONES_EVENTOS" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "HERRAMIENTAS.AUDITORIA" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "USUARIOS" ENABLE ROW LEVEL SECURITY;
```

### Paso B: Política de "Denegación Total" para el público (Opcional pero recomendado)
Aunque activar RLS ya bloquea por defecto, es buena práctica ser explícito: "El rol anónimo no puede hacer nada".

```sql
-- Crear política para rechazar acceso anónimo explícitamente (ejemplo para una tabla)
CREATE POLICY "Bloquear acceso anonimo"
ON "public"."USUARIOS"
AS RESTRICTIVE
FOR ALL
TO anon
USING (false);
```
*(Nota: Al activar RLS sin crear políticas `FOR SELECT/INSERT/etc`, el efecto por defecto ya es bloquear al rol `anon` y `authenticated`, así que el Paso A suele ser suficiente para empezar).*

## 3. Verificación
1.  Ve a tu archivo local `.streamlit/secrets.toml`.
2.  Busca la sección `[supabase]`.
3.  Verifica que el valor de `key` corresponda al **`service_role` secret** que aparece en tu Dashboard de Supabase (Settings > API).
    *   Si dice `public-anon...`, **CÁMBIALO** por el `service_role...`.
4.  Reinicia tu app Streamlit.
5.  Prueba guardar o leer datos. Debería funcionar perfectamente (porque eres Admin).
6.  Intenta acceder a tus tablas usando la `anon` key desde un cliente externo (Postman o script JS): Debería dar error o devolver lista vacía.

## 4. Resultado
*   **Tu App:** Funciona ✅ (Usa Llave Maestra).
*   **Hackers con Anon Key:** Bloqueados ⛔ (RLS activo y sin políticas de acceso público).
