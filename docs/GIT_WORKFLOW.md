# Política de Branches y Despliegue Git

**Fecha:** 04/12/2025

## Regla Fundamental

Todos los cambios de código **DEBEN** pushearse a la rama `main` para que se desplieguen en Streamlit Cloud. Streamlit Cloud está configurado para desplegar automáticamente desde `main`.

> [!IMPORTANT]
> **PROTOCOLO ESTRICTO:** Ver `docs/PROTOCOLO_GIT_STRICTO.md`.
> El usuario requiere confirmación PASO A PASO (Add -> Wait -> Commit -> Wait -> Push).
> **NO ENCADENAR COMANDOS.**

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

## Procedimiento de Push (A Prueba de Errores)

### Paso 1: Verificar Branch Actual
```bash
git branch
```
**Resultado esperado:** Debe mostrar `* main`
- ✅ Si estás en `main`, continúa al Paso 2
- ❌ Si estás en otro branch, ejecuta: `git checkout main`

### Paso 2: Limpiar Locks de Git (Prevención)
```bash
# PowerShell
Get-ChildItem -Path .git -Filter "*.lock" -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue
```
**Propósito:** Eliminar archivos `.lock` que causan errores frecuentes

### Paso 3: Verificar Estado del Repositorio
```bash
git status
```
**Revisar:**
- ¿Hay archivos modificados? → Deben estar en "Changes to be committed" (verde)
- ¿Hay archivos sin trackear que quieres incluir? → Usa `git add <archivo>`

### Paso 4: Agregar Archivos al Staging
```bash
git add <archivo1> <archivo2>
# O para agregar todos los cambios:
git add .
```
**Importante:** NO agregar archivos sensibles (secrets, PDFs de prueba, etc.)

### Paso 5: Hacer Commit
```bash
git commit -m "Descripción clara del cambio"
```
**Formato del mensaje:**
- `feat:` para nuevas funcionalidades
- `fix:` para correcciones de bugs
- `docs:` para documentación
- `refactor:` para refactorización sin cambios funcionales

### Paso 6: Sincronizar con Remoto (Crítico)
```bash
git fetch origin
git status
```
**Revisar el output:**
- Si dice "Your branch is up to date" → Continúa al Paso 7
- Si dice "Your branch is behind" → Ejecuta: `git pull origin main --no-edit`
- Si dice "Your branch is ahead" → Continúa al Paso 7

### Paso 7: Push a Main
```bash
git push origin main
```
**Resultado esperado:** Debe mostrar "Writing objects" y terminar con "Exit code: 0"

### Paso 8: Verificar Despliegue
1. Espera 2-3 minutos
2. Abre Streamlit Cloud en incógnito
3. Verifica que los cambios estén desplegados

## Solución de Problemas Comunes

### Error: "index.lock exists"
```bash
Remove-Item -Force .git\index.lock
```

### Error: "Updates were rejected"
```bash
# Opción 1: Pull y merge
git pull origin main --no-edit
git push origin main

# Opción 2: Si estás seguro de tus cambios locales
git push origin main --force-with-lease  # ⚠️ Usar con precaución
```

### Error: "Merge conflict"
```bash
# 1. Ver archivos en conflicto
git status

# 2. Editar manualmente los archivos para resolver conflictos
# 3. Marcar como resueltos
git add <archivo-resuelto>

# 4. Completar el merge
git commit -m "Merge: Resolver conflictos"

# 5. Push
git push origin main
```

### Error: "Failed to push some refs"
```bash
# Verificar que estés en main
git branch

# Limpiar y reintentar
git fetch origin
git pull origin main --no-edit
git push origin main
```

## Checklist Rápido (Copiar y Pegar)

```bash
# 1. Verificar branch
git branch

# 2. Limpiar locks
Get-ChildItem -Path .git -Filter "*.lock" -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue

# 3. Agregar cambios
git add <archivos>

# 4. Commit
git commit -m "tipo: descripción"

# 5. Sincronizar
git fetch origin
git pull origin main --no-edit

# 6. Push
git push origin main
```

## Incidente Crítico: Bloqueo por Secretos (DLP)

**Fecha:** 07/12/2025

**Problema:**
GitHub tiene un sistema de protección de secretos (Secret Scanning) que **bloquea inmediatamente** cualquier push que contenga strings que parezcan claves API, secretos de cliente o tokens reales (especialmente de Google, AWS, etc.).

**Síntoma:**
El comando git push falla con un mensaje como:
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: Secret detection violation: Google OAuth Client Secret

**Consecuencia:**
Los agentes de IA entran en un bucle infinito de intentos fallidos, tratando de corregir el error sin éxito, consumiendo mucho tiempo y créditos.

**Regla de Oro:**
 **NUNCA** incluir secretos reales en archivos de documentación, ejemplos de código, o comentarios. Ni siquiera si el archivo está en .gitignore (ya que si cometes el error de agregarlo con git add, el daño está hecho).
 Usar siempre **PLACEHOLDERS** claros:
   - client_secret = "TU_CLIENT_SECRET_AQUI"
   - api_key = "TU_API_KEY_AQUI"

**Procedimiento de Recuperación (Si ocurre):**
Si accidentalmente hiciste un commit con un secreto:

1.  **NO hagas push.** Fallará.
2.  **Elimina el secreto** del archivo inmediatamente.
3.  **Enmienda el commit** (esto reescribe la historia local para que el secreto nunca haya existido en ese commit):
    git add <archivo_corregido>
    git commit --amend --no-edit
4.  **Haz push:**
    git push origin main

**Nota:** Si el secreto se commiteó en un commit anterior (no el último), la solución es mucho más compleja (reset soft o rebase interactivo). Por eso la prevención es clave.
