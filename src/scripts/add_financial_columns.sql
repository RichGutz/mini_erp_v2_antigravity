-- Agregar columnas financieras a la tabla EMISORES.ACEPTANTES

ALTER TABLE IF EXISTS public."EMISORES.ACEPTANTES"
ADD COLUMN IF NOT EXISTS tasa_avance FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS interes_mensual_pen FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS interes_moratorio_pen FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS interes_mensual_usd FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS interes_moratorio_usd FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS comision_estructuracion_pen FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS comision_estructuracion_usd FLOAT DEFAULT 0.0;

-- Comentarios explicativos
COMMENT ON COLUMN public."EMISORES.ACEPTANTES".tasa_avance IS 'Tasa de Avance (%) por defecto';
COMMENT ON COLUMN public."EMISORES.ACEPTANTES".interes_mensual_pen IS 'Tasa Mensual PEN (%) por defecto';
COMMENT ON COLUMN public."EMISORES.ACEPTANTES".comision_estructuracion_pen IS 'Comisión Estructuración Flat PEN por defecto';
