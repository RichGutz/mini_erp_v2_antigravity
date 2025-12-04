# Los 6 Casos del Algoritmo de Liquidación Universal

## Matriz de Decisión

La clasificación se basa en 3 valores:
- **ΔInt** (Delta Intereses) = Interés Devengado - Interés Original
- **ΔCap** (Delta Capital) = Capital Operación - Monto Pagado  
- **Saldo Global** = ΔInt + ΔCap

---

## Caso 1: LIQUIDADO - Cliente pagó TODO de más
**Condiciones:** ΔInt < 0 AND ΔCap < 0 AND Saldo < 0

**Ejemplo:**
- Capital: S/ 1,000
- Interés Original: S/ 50
- Interés Devengado: S/ 40 (pagó 10 días antes)
- Monto Pagado: S/ 1,100

**Cálculo:**
- ΔInt = 40 - 50 = **-10** (pagó de más en intereses)
- ΔCap = 1,000 - 1,100 = **-100** (pagó de más en capital)
- Saldo = -10 + (-100) = **-110**

**Acción:** Generar notas de crédito, devolver S/ 110 al cliente

---

## Caso 2: EN PROCESO - Pagó de más en intereses, de menos en capital
**Condiciones:** ΔInt < 0 AND ΔCap > 0 AND Saldo > 0

**Ejemplo:**
- Capital: S/ 1,000
- Interés Original: S/ 50
- Interés Devengado: S/ 40
- Monto Pagado: S/ 900

**Cálculo:**
- ΔInt = 40 - 50 = **-10** (pagó de más en intereses)
- ΔCap = 1,000 - 900 = **+100** (debe capital)
- Saldo = -10 + 100 = **+90**

**Acción:** Generar NC por S/ 10 de intereses, crear calendario para S/ 100 de capital

---

## Caso 3: EN PROCESO - Cliente debe TODO
**Condiciones:** ΔInt > 0 AND ΔCap > 0 AND Saldo > 0

**Ejemplo:**
- Capital: S/ 1,000
- Interés Original: S/ 50
- Interés Devengado: S/ 60 (se atrasó)
- Monto Pagado: S/ 900

**Cálculo:**
- ΔInt = 60 - 50 = **+10** (debe intereses)
- ΔCap = 1,000 - 900 = **+100** (debe capital)
- Saldo = 10 + 100 = **+110**

**Acción:** Facturar S/ 10 de intereses adicionales, nuevo calendario para S/ 110

---

## Caso 4: EN PROCESO - Debe intereses, pagó de más en capital
**Condiciones:** ΔInt > 0 AND ΔCap < 0 AND Saldo > 0

**Ejemplo:**
- Capital: S/ 1,000
- Interés Original: S/ 50
- Interés Devengado: S/ 80 (se atrasó mucho)
- Monto Pagado: S/ 1,050

**Cálculo:**
- ΔInt = 80 - 50 = **+30** (debe intereses)
- ΔCap = 1,000 - 1,050 = **-50** (pagó de más en capital)
- Saldo = 30 + (-50) = **-20** ❌ PERO Saldo debe ser > 0 para Caso 4

**Ejemplo Correcto:**
- Interés Devengado: S/ 70
- ΔInt = 70 - 50 = **+20**
- ΔCap = 1,000 - 1,010 = **-10**
- Saldo = 20 + (-10) = **+10** ✓

**Acción:** Facturar S/ 20 de intereses, evaluar moratorios

---

## Caso 5: LIQUIDADO - Debe intereses, pagó MUCHO más en capital
**Condiciones:** ΔInt > 0 AND ΔCap < 0 AND Saldo < 0

**Ejemplo:**
- Capital: S/ 1,000
- Interés Original: S/ 50
- Interés Devengado: S/ 60
- Monto Pagado: S/ 1,100

**Cálculo:**
- ΔInt = 60 - 50 = **+10** (debe intereses)
- ΔCap = 1,000 - 1,100 = **-100** (pagó de más en capital)
- Saldo = 10 + (-100) = **-90**

**Acción:** Facturar S/ 10 de intereses, devolver S/ 90 de exceso de capital

---

## Caso 6: LIQUIDADO - Pagó MUCHO más en intereses, debe capital
**Condiciones:** ΔInt < 0 AND ΔCap > 0 AND Saldo < 0

**Ejemplo:**
- Capital: S/ 1,000
- Interés Original: S/ 50
- Interés Devengado: S/ 30
- Monto Pagado: S/ 1,010

**Cálculo:**
- ΔInt = 30 - 50 = **-20** (pagó de más en intereses)
- ΔCap = 1,000 - 1,010 = **-10** (pagó de más en capital)
- Saldo = -20 + (-10) = **-30** ❌ PERO ΔCap debe ser > 0 para Caso 6

**Ejemplo Correcto:**
- Monto Pagado: S/ 990
- ΔInt = 30 - 50 = **-20** (pagó de más en intereses)
- ΔCap = 1,000 - 990 = **+10** (debe capital)
- Saldo = -20 + 10 = **-10** ✓

**Acción:** Generar NC por S/ 20 de intereses, devolver S/ 10 de saldo negativo

---

## Tabla Resumen

| Caso | ΔInt | ΔCap | Saldo | Estado | Acción Principal |
|------|------|------|-------|--------|------------------|
| 1 | Negativo | Negativo | Negativo | LIQUIDADO | Devolver todo el exceso |
| 2 | Negativo | Positivo | Positivo | EN PROCESO | NC + Calendario |
| 3 | Positivo | Positivo | Positivo | EN PROCESO | Facturar + Calendario |
| 4 | Positivo | Negativo | Positivo | EN PROCESO | Facturar intereses |
| 5 | Positivo | Negativo | Negativo | LIQUIDADO | Facturar + Devolver |
| 6 | Negativo | Positivo | Negativo | LIQUIDADO | NC + Devolver |

---

## Regla Mnemotécnica

**LIQUIDADO** = Saldo Negativo (cliente pagó de más en total)
**EN PROCESO** = Saldo Positivo (cliente debe dinero)

**Positivo (+)** = Cliente DEBE
**Negativo (-)** = Cliente PAGÓ DE MÁS
