-- 🚨 DESACTIVAR SEGURIDAD (RLS) EN TODAS LAS TABLAS 🚨
-- Ejecuta esto en el SQL Editor de Supabase para volver a hacer públicas las tablas.

ALTER TABLE "EMISORES.ACEPTANTES" DISABLE ROW LEVEL SECURITY;
ALTER TABLE "propuestas" DISABLE ROW LEVEL SECURITY;
ALTER TABLE "liquidaciones_resumen" DISABLE ROW LEVEL SECURITY;
ALTER TABLE "liquidacion_eventos" DISABLE ROW LEVEL SECURITY;
ALTER TABLE "desembolsos_resumen" DISABLE ROW LEVEL SECURITY;
ALTER TABLE "desembolso_eventos" DISABLE ROW LEVEL SECURITY;
ALTER TABLE "auditoria_eventos" DISABLE ROW LEVEL SECURITY;
ALTER TABLE "modules" DISABLE ROW LEVEL SECURITY;
ALTER TABLE "authorized_users" DISABLE ROW LEVEL SECURITY;
ALTER TABLE "user_module_access" DISABLE ROW LEVEL SECURITY;

-- Si tienes EMISORES.DEUDORES también:
-- ALTER TABLE "EMISORES.DEUDORES" DISABLE ROW LEVEL SECURITY;

-- Confirmación (Opcional, para limpiar policies antiguas si quieres, pero DISABLE es suficiente)
-- DROP POLICY IF EXISTS "Enable read access for all users" ON "propuestas";
