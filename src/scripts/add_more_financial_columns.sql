-- Agregar 4 columnas financieras ADICIONALES a la tabla EMISORES.ACEPTANTES

ALTER TABLE IF EXISTS public."EMISORES.ACEPTANTES"
ADD COLUMN IF NOT EXISTS comision_estructuracion_pct FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS comision_afiliacion_pen FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS comision_afiliacion_usd FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS dias_minimos_interes INTEGER DEFAULT 0;

-- Comentarios explicativos
COMMENT ON COLUMN public."EMISORES.ACEPTANTES".comision_estructuracion_pct IS 'Comisión Estructuración Porcentual (%) por defecto';
COMMENT ON COLUMN public."EMISORES.ACEPTANTES".comision_afiliacion_pen IS 'Comisión Afiliación Monto Fijo (PEN) por defecto';
COMMENT ON COLUMN public."EMISORES.ACEPTANTES".dias_minimos_interes IS 'Días Mínimos de Interés (Deductible)';
