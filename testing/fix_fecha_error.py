import sys
import os

file_path = r"C:\Users\rguti\mini_erp_v2_antigravity\pages\01_Operaciones.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Target to replace
target = """            if fecha_pago_dt >= fecha_desembolso_dt:
                invoice['plazo_operacion_calculado'] = (fecha_pago_dt - fecha_desembolso_dt).days
            else:"""

# Replacement
replacement = """            if fecha_pago_dt >= fecha_desembolso_dt:
                invoice['plazo_operacion_calculado'] = (fecha_pago_dt - fecha_desembolso_dt).days
                invoice['fecha_error'] = False  # Fechas válidas
            else:"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ Fix aplicado exitosamente")
else:
    print("❌ Target no encontrado")
    print("Buscando variaciones...")
