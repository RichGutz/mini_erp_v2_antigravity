import sys
import os
import datetime
import pandas as pd
from decimal import Decimal

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.core.factoring_system import SistemaFactoringCompleto

def run_test():
    print("=== INICIANDO TEST DE VALIDACIÓN CONTRA CSV ===")
    
    # 1. Definir Datos Base del CSV (Hardcoded para simplificar el parsing de un CSV no estructurado)
    # Estos valores vienen de las líneas 1-7 del CSV
    CAPITAL = 17822.00537
    FECHA_DESEMBOLSO = datetime.date(2024, 12, 24)
    TASA_MENSUAL = 0.02
    TASA_MORATORIA = 0.03
    INTERES_COBRADO_ORIGINAL = 1202.835049
    IGV_INTERES_ORIGINAL = 216.5103088
    
    # 2. Definir Escenarios de Prueba (Del CSV líneas 118-126)
    # Formato: (Nombre, Fecha Pago, Monto Pagado, Saldo Esperado CSV)
    escenarios = [
        {
            "nombre": "Liquidacion 1 (Pago Anticipado - 62 días)",
            "fecha_pago": datetime.date(2025, 2, 24), # 62 días (Línea 72 del CSV)
            "monto_pagado": 17700.00,
            "saldo_esperado": -410.19
        },
        {
            "nombre": "Liquidacion 2 (Pago Parcial - 62 días)",
            "fecha_pago": datetime.date(2025, 2, 24), # 62 días
            "monto_pagado": 18000.00, 
            "saldo_esperado": -710.19
        },
        {
            "nombre": "Liquidacion 3 (Pago Exacto - Backdoor)",
            "fecha_pago": datetime.date(2025, 4, 1),
            "monto_pagado": 17822.00, # Aprox
            "saldo_esperado": 0.01 # Debería activar backdoor
        },
        {
            "nombre": "Liquidacion 5 (Mora)",
            "fecha_pago": datetime.date(2025, 4, 6), # 103 días
            "monto_pagado": 16350.00,
            "saldo_esperado": 1652.30
        },
        {
            "nombre": "Liquidacion 9A (Pago Parcial con Mora)",
            "fecha_pago": datetime.date(2025, 4, 4), # 101 días
            "monto_pagado": 17850.00,
            "saldo_esperado": 80.09
        }
    ]

    sistema = SistemaFactoringCompleto()

    # Test específico para 9B (Nuevo Calendario)
    print("\nProbando: Liquidacion 9B (Nuevo Calendario)")
    capital_remanente = 80.09
    fecha_inicio_remanente = datetime.date(2025, 4, 4) # Fecha de corte de la 9A
    
    operacion_remanente = {
        "id_operacion": "TEST-CSV-9B",
        "capital_operacion": capital_remanente,
        "monto_desembolsado": capital_remanente, 
        "interes_compensatorio": 0.0, # Nuevo calendario empieza limpio
        "igv_interes": 0.0,
        "tasa_interes_mensual": TASA_MENSUAL,
        "fecha_desembolso": fecha_inicio_remanente,
        "fecha_vencimiento": fecha_inicio_remanente # Vence el mismo día (deuda exigible)
    }
    
    # Simular al 06/04/2025 (2 días después)
    fecha_simulacion = datetime.date(2025, 4, 6)
    saldo_esperado_9b = 80.40 # Línea 155 del CSV (aprox)
    
    # Nota: Para 9B, el CSV calcula moratorios desde el día 1.
    # Mi sistema calculará moratorios si fecha_pago > fecha_vencimiento.
    
    resultado_9b = sistema.liquidar_operacion_con_back_door(
        operacion=operacion_remanente,
        fecha_pago=fecha_simulacion,
        monto_pagado=0.0, # Solo queremos ver cuánto debe
        monto_minimo=100.0
    )
    
    # En 9B, el saldo es Saldo Global + Monto Pagado (0) = Saldo Global.
    # Pero ojo: Liquidación calcula "cuánto falta pagar".
    # Si pagué 0, el saldo global es la deuda total.
    
    saldo_calculado_9b = resultado_9b['saldo_global']
    diferencia_9b = abs(saldo_calculado_9b - saldo_esperado_9b)
    
    print(f"  Fecha Simulacion: {fecha_simulacion}")
    print(f"  Saldo Esperado (CSV): {saldo_esperado_9b}")
    print(f"  Saldo Calculado (Sys): {saldo_calculado_9b:.2f}")
    print(f"  Diferencia: {diferencia_9b:.2f}")
    
    if diferencia_9b < 0.10:
        print("  ✅ RESULTADO: COINCIDE")
    else:
        print("  ❌ RESULTADO: DISCREPANCIA")
        print("  Desglose Calculado 9B:")
        print(f"    Interés Devengado: {resultado_9b['interes_devengado']}")
        print(f"    Moratorios: {resultado_9b['interes_moratorio']}")
        print(f"    Delta Capital: {resultado_9b['delta_capital']}")



    # Configurar operación base
    operacion_base = {
        "id_operacion": "TEST-CSV",
        "capital_operacion": CAPITAL,
        "monto_desembolsado": 16244.94, # Irrelevante para el cálculo de liquidación
        "interes_compensatorio": INTERES_COBRADO_ORIGINAL,
        "igv_interes": IGV_INTERES_ORIGINAL,
        "tasa_interes_mensual": TASA_MENSUAL,
        "fecha_desembolso": FECHA_DESEMBOLSO,
        "fecha_vencimiento": datetime.date(2025, 4, 1) # Asumimos vencimiento original en fecha de pago base
    }

    print(f"\nDatos Base:")
    print(f"Capital: {CAPITAL}")
    print(f"Fecha Desembolso: {FECHA_DESEMBOLSO}")
    print(f"Tasa Mensual: {TASA_MENSUAL}")
    print("-" * 60)

    for caso in escenarios:
        print(f"\nProbando: {caso['nombre']}")
        
        resultado = sistema.liquidar_operacion_con_back_door(
            operacion=operacion_base,
            fecha_pago=caso['fecha_pago'],
            monto_pagado=caso['monto_pagado'],
            monto_minimo=100.0 # Configuración default
        )
        
        saldo_calculado = resultado['saldo_global']
        diferencia = abs(saldo_calculado - caso['saldo_esperado'])
        
        print(f"  Fecha Pago: {caso['fecha_pago']}")
        print(f"  Monto Pagado: {caso['monto_pagado']}")
        print(f"  Saldo Esperado (CSV): {caso['saldo_esperado']}")
        print(f"  Saldo Calculado (Sys): {saldo_calculado:.2f}")
        print(f"  Diferencia: {diferencia:.2f}")
        
        if diferencia < 0.10: # Tolerancia de 10 céntimos
            print("  ✅ RESULTADO: COINCIDE")
        else:
            print("  ❌ RESULTADO: DISCREPANCIA")
            # Mostrar desglose si falla
            print("  Desglose Calculado:")
            print(f"    Interés Devengado: {resultado['interes_devengado']}")
            print(f"    Moratorios: {resultado['interes_moratorio']}")
            print(f"    Delta Capital: {resultado['delta_capital']}")

if __name__ == "__main__":
    run_test()
