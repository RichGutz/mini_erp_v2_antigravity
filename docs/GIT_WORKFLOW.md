# Política de Branches y Despliegue Git

**Fecha:** 04/12/2025

## Regla Fundamental

Todos los cambios de código **DEBEN** pushearse a la rama `main` para que se desplieguen en Streamlit Cloud. Streamlit Cloud está configurado para desplegar automáticamente desde `main`.

## Workflow de Git

### 1. Desarrollo Normal
- Trabajar en `main`
- Hacer commits frecuentes con mensajes descriptivos
- Push a `origin main` para desplegar a producción

### 2. Creación de Branches de Backup
- **Solo cuando el usuario lo solicite explícitamente**
- **Propósito:** Grabar un estado funcional del proyecto
- **Formato del nombre:** `backup/DD-MM-YYYY-HHMM` (ejemplo: `backup/03-12-2025-2217`)
- **Comandos:**
  ```bash
  git checkout -b backup/03-12-2025-2217
  git push origin backup/03-12-2025-2217
  git checkout main  # Volver a main inmediatamente
  ```

### 3. Reglas Importantes

❌ **NO hacer:**
- NO trabajar en branches de backup
- NO hacer cambios en branches que no sean `main` sin instrucción explícita del usuario

✅ **SÍ hacer:**
- Los branches de backup son **solo para preservar** estados funcionales
- Después de crear un backup, **volver inmediatamente a `main`** para continuar trabajando
- Siempre verificar en qué branch estás antes de hacer cambios: `git branch`

## Lección Aprendida

**Incidente del 04/12/2025:**
Todos los cambios de prorrateo de comisión se hicieron en el branch `backup/03-12-2025-2217` en lugar de `main`, causando que Streamlit Cloud no recibiera las actualizaciones durante varias horas. Esto generó confusión y debugging innecesario.

## Solución si Ocurre de Nuevo

Si accidentalmente trabajaste en un branch de backup:

```bash
# 1. Verificar en qué branch estás
git branch

# 2. Si no estás en main, cambiar a main
git checkout main

# 3. Copiar cambios del branch de backup
git show backup/NOMBRE:archivo.py > archivo.py

# 4. Commit y push a main
git add archivo.py
git commit -m "Descripción del cambio"
git push origin main
```

## Verificación Pre-Push

Antes de cada push, verificar:
1. ¿Estoy en `main`? → `git branch` (debe mostrar `* main`)
2. ¿Mis cambios están commiteados? → `git status`
3. ¿Voy a pushear a `main`? → `git push origin main`
