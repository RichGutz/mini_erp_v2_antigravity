# 🛑 PROTOCOLO DE DESPLIEGUE ESTRICTO (PINNED TASK)

**LEER ESTO ANTES DE EJECUTAR CUALQUIER COMANDO GIT**

El usuario EXIGE un protocolo paso-a-paso para evitar errores de sincronización y bloqueos.
**BAJO NINGUNA CIRCUNSTANCIA** debes encadenar comandos (ej: `git add . && git commit...`).

## El Algoritmo "Paso a Paso" (The Step-by-Step Algorithm)

Cada acción es un bloque atómico. Debes notificar al usuario y ESPERAR su confirmación visual o implícita antes de pasar al siguiente bloque.

### 1️⃣ STAGE (Preparar)
1. Ejecuta: `git add <archivos>` (o `git add .` si es seguro).
2. Verifica: `git status`.
3. **STOP:** Informa al output que has hecho el stage.

### 2️⃣ COMMIT (Guardar)
1. Ejecuta: `git commit -m "Mensaje descriptivo"`
2. Verifica el output del commit.
3. **STOP:** Informa al output que el commit está listo.

### 3️⃣ PUSH (Subir)
1. Ejecuta: `git push origin <rama>`
2. **ESPERAR:** El push puede tardar. No interrumpas.
3. Verifica: Output debe decir `Use 'git pull' ...` o éxito `remote: ... done`.
4. **STOP:** Informa al usuario: "Exito Total".

---

## ⚠️ PROHIBIDO
*   ❌ `git add . && git commit -m "..." && git push` (NO encadenar)
*   ❌ Asumir que el push funcionó sin leer el output.
*   ❌ Hacer cambios masivos sin un backup previo.

Si rompes este protocolo, el usuario detendrá la sesión.
