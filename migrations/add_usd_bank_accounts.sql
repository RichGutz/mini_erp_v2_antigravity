-- Script SQL para modificar tabla EMISORES.DEUDORES
-- 1. Renombrar tabla DEUDORES a ACEPTANTES
-- 2. Agregar soporte para cuentas bancarias en PEN y USD

-- PASO 1: Renombrar la tabla
ALTER TABLE "EMISORES"."DEUDORES" 
RENAME TO "ACEPTANTES";

-- PASO 2: Renombrar columnas existentes para especificar que son PEN
ALTER TABLE "EMISORES"."ACEPTANTES" 
RENAME COLUMN "Numero de Cuenta" TO "Numero de Cuenta PEN";

ALTER TABLE "EMISORES"."ACEPTANTES" 
RENAME COLUMN "CCI" TO "Numero de CCI PEN";

-- PASO 3: Agregar nuevas columnas para cuentas en USD
ALTER TABLE "EMISORES"."ACEPTANTES" 
ADD COLUMN "Numero de Cuenta USD" TEXT;

ALTER TABLE "EMISORES"."ACEPTANTES" 
ADD COLUMN "Numero de CCI USD" TEXT;

-- Verificar cambios
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'EMISORES' 
  AND table_name = 'ACEPTANTES'
  AND (column_name LIKE '%Cuenta%' OR column_name LIKE '%CCI%')
ORDER BY column_name;
