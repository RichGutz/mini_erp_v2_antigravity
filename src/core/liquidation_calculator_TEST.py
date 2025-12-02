from datetime import datetime, timedelta
from decimal import Decimal, getcontext
import json
import os
import sys
import csv
from jinja2 import Template
from weasyprint import HTML

# --- PATH SETUP ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- CONSTANTS ---
getcontext().prec = 30
IGV_PCT = Decimal('0.18')

# =================================================================================
# ALGORITMO LEGACY (El original, renombrado)
# =================================================================================
def calcular_liquidacion_LEGACY(
    datos_operacion: dict,
    monto_recibido: float,
    fecha_pago_real_str: str,
    tasa_interes_compensatoria_pct: float,
    tasa_interes_moratoria_pct: float
) -> dict:
    try:
        fecha_pago_esperada = datetime.strptime(datos_operacion['fecha_pago_calculada'], '%d-%m-%Y')
        fecha_pago_real = datetime.strptime(fecha_pago_real_str, '%d-%m-%Y')
        dias_diferencia = (fecha_pago_real - fecha_pago_esperada).days
        capital_desembolsado = Decimal(str(datos_operacion['capital_calculado']))
        saldo_final = capital_desembolsado - Decimal(str(monto_recibido))
        return {"liquidacion_final": {"saldo_final_a_liquidar": float(saldo_final)}, "dias_diferencia": dias_diferencia, "tipo_pago": "Anticipado" if dias_diferencia < 0 else "Tardío"}
    except Exception as e:
        return {"error": str(e)}

# =================================================================================
# ALGORITMO DE RECONCILIACIÓN (El nuevo, basado en nuestro pseudocódigo)
# =================================================================================
def calcular_liquidacion_RECONCILIACION(datos_evento: dict) -> dict:
    try:
        # --- FASE 1: LECTURA DE DATOS DEL EVENTO Y ORIGINACIÓN ---
        capital_desembolsado = Decimal(str(datos_evento['capital_desembolsado']))
        interes_original_cobrado = Decimal(str(datos_evento['interes_original_cobrado']))
        igv_interes_original_cobrado = Decimal(str(datos_evento['igv_interes_original_cobrado']))
        fecha_desembolso = datetime.strptime(datos_evento['fecha_desembolso'], '%d-%m-%Y')
        fecha_pago_calculada_original = datetime.strptime(datos_evento['fecha_pago_calculada_original'], '%d-%m-%Y')
        fecha_pago_actual = datetime.strptime(datos_evento['fecha_pago_actual'], '%d-%m-%Y')
        monto_recibido = Decimal(str(datos_evento['monto_recibido']))
        tasa_compensatoria_pct = Decimal(str(datos_evento['tasa_compensatoria_pct']))
        tasa_moratoria_pct = Decimal(str(datos_evento['tasa_moratoria_pct']))

        # --- FASE 2: CÁLCULO DEL INTERÉS REAL DEVENGADO ---
        # Se define la base sobre la cual se calculan los intereses de liquidación.
        base_calculo_liquidacion = capital_desembolsado + interes_original_cobrado + igv_interes_original_cobrado

        tasa_diaria_compensatoria = tasa_compensatoria_pct / 30
        dias_transcurridos = (fecha_pago_actual - fecha_desembolso).days
        interes_compensatorio_real = base_calculo_liquidacion * ((1 + tasa_diaria_compensatoria) ** dias_transcurridos - 1)

        interes_moratorio_real = Decimal(0)
        if fecha_pago_actual > fecha_pago_calculada_original:
            tasa_diaria_moratoria = tasa_moratoria_pct / 30
            dias_de_mora = (fecha_pago_actual - fecha_pago_calculada_original).days
            interes_moratorio_real = base_calculo_liquidacion * ((1 + tasa_diaria_moratoria) ** dias_de_mora - 1)

        interes_real_devengado_total = interes_compensatorio_real + interes_moratorio_real
        igv_interes_real_devengado = interes_real_devengado_total * IGV_PCT

        # --- FASE 3: CÁLCULO DEL AJUSTE FINAL ---
        ajuste_de_interes = interes_real_devengado_total - interes_original_cobrado
        ajuste_de_igv = igv_interes_real_devengado - igv_interes_original_cobrado
        ajuste_total = ajuste_de_interes + ajuste_de_igv

        # --- FASE 4: DETERMINACIÓN DEL SALDO DE LA OPERACIÓN ---
        deuda_total_final = capital_desembolsado + ajuste_total
        saldo_final = deuda_total_final - monto_recibido

        estado_final = ""
        nuevo_capital_pendiente = Decimal(0)
        saldo_a_favor = Decimal(0)

        if abs(saldo_final) < Decimal('0.01'): # Consider zero if difference is less than a cent
            estado_final = "LIQUIDADA"
        elif saldo_final < 0:
            estado_final = "LIQUIDADA (CON DEVOLUCIÓN)"
            saldo_a_favor = -saldo_final
        else:
            estado_final = "EN PROCESO DE LIQUIDACIÓN"
            nuevo_capital_pendiente = saldo_final

        # --- FASE 5: PREPARAR Y DEVOLVER RESULTADO DEL EVENTO ---
        return {
            "estado_operacion": estado_final,
            "capital_final_pendiente": float(nuevo_capital_pendiente.quantize(Decimal('0.01'))),
            "saldo_a_favor_cliente": float(saldo_a_favor.quantize(Decimal('0.01'))),
            "desglose_calculo": {
                "base_calculo_liquidacion": float(base_calculo_liquidacion.quantize(Decimal('0.01'))),
                "interes_compensatorio_real": float(interes_compensatorio_real.quantize(Decimal('0.01'))),
                "interes_moratorio_real": float(interes_moratorio_real.quantize(Decimal('0.01'))),
                "igv_interes_real_devengado": float(igv_interes_real_devengado.quantize(Decimal('0.01'))),
                "interes_real_devengado_total": float(interes_real_devengado_total.quantize(Decimal('0.01'))),
                "ajuste_de_interes": float(ajuste_de_interes.quantize(Decimal('0.01'))),
                "ajuste_de_igv": float(ajuste_de_igv.quantize(Decimal('0.01'))),
                "ajuste_total": float(ajuste_total.quantize(Decimal('0.01'))),
                "deuda_total_final": float(deuda_total_final.quantize(Decimal('0.01'))),
                "monto_recibido": float(monto_recibido.quantize(Decimal('0.01'))),
                "saldo_final_calculado": float(saldo_final.quantize(Decimal('0.01')))
            }
        }
    except Exception as e:
        return {"error": str(e)}

# =================================================================================
# FUNCIÓN PARA GENERAR PDF COMPARATIVO
# =================================================================================
def generar_pdf_comparativo(inputs, resultado_legacy, resultado_universal):
    template_html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Reporte Comparativo de Algoritmos de Liquidación</title>
        <style>
            body { font-family: sans-serif; margin: 2em; }
            h1, h2, h3 { color: #333; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 1em; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .monospace { font-family: monospace; background: #eee; padding: 2px 4px; white-space: pre-wrap; word-break: break-all; }
        </style>
    </head>
    <body>
        <h1>Reporte Comparativo de Algoritmos</h1>
        <p>Fecha de Reporte: {{ fecha_reporte }}</p>
        <h2>Datos de Entrada para la Simulación</h2>
        <pre class="monospace">{{ inputs_str }}</pre>
        <h2>Resultados</h2>
        <table>
            <tr>
                <th>Métrica</th>
                <th>Resultado Algoritmo LEGACY</th>
                <th>Resultado Algoritmo RECONCILIACIÓN</th>
            </tr>
            <tr>
                <td>Saldo Final / Capital Pendiente</td>
                <td class="monospace">{{ saldo_legacy }}</td>
                <td class="monospace">{{ saldo_universal }}</td>
            </tr>
            <tr>
                <td>Estado de la Operación</td>
                <td class="monospace">{{ estado_legacy }}</td>
                <td class="monospace">{{ estado_universal }}</td>
            </tr>
        </table>
        <h2>Desglose Completo</h2>
        <h3>Resultado Legacy</h3>
        <pre class="monospace">{{ resultado_legacy_str }}</pre>
        <h3>Resultado Reconciliación</h3>
        <pre class="monospace">{{ resultado_universal_str }}</pre>
    </body>
    </html>
    """
    # Prepare data
    template_data = {
        "fecha_reporte": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "inputs_str": json.dumps(inputs, indent=4, ensure_ascii=False),
        "saldo_legacy": resultado_legacy.get('liquidacion_final', {}).get('saldo_final_a_liquidar', 'N/A'),
        "estado_legacy": resultado_legacy.get('tipo_pago', 'N/A'),
        "saldo_universal": resultado_universal.get('capital_final_pendiente', 'N/A'),
        "estado_universal": resultado_universal.get('estado_operacion', 'N/A'),
        "resultado_legacy_str": json.dumps(resultado_legacy, indent=4, ensure_ascii=False),
        "resultado_universal_str": json.dumps(resultado_universal, indent=4, ensure_ascii=False)
    }
    # Generate PDF
    html_out = Template(template_html).render(template_data)
    output_folder = os.path.join(project_root, 'documentation')
    os.makedirs(output_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join(output_folder, f"comparativa_algoritmos_{timestamp}.pdf")
    HTML(string=html_out).write_pdf(output_filename)
    print(f"PDF Comparativo guardado en: {output_filename}")

# =================================================================================
# BLOQUE DE PRUEBA PRINCIPAL
# =================================================================================
if __name__ == "__main__":
    # --- 1. Definir datos para la simulación (primer evento de pago) ---
    datos_originacion = {
        "capital_calculado": 6834.81,
        "interes_calculado": 311.58,
        "fecha_pago_calculada": "01-04-2025",
        "fecha_desembolso": "01-01-2025",
        "tasa_compensatoria_pct": 2.0, # Tasa mensual
        "tasa_moratoria_pct": 3.0, # Tasa mensual
        "interes_original_cobrado": 1202.835049, # Nuevo dato
        "igv_interes_original_cobrado": 216.5103088 # Nuevo dato
    }
    pago_evento = {
        "monto_recibido": 3000.00,
        "fecha_pago_actual": "17-03-2025"
    }

    # --- 2. Ejecutar Algoritmo LEGACY ---
    print("--- Ejecutando Algoritmo LEGACY ---")
    resultado_legacy = calcular_liquidacion_LEGACY(
        datos_operacion=datos_originacion,
        monto_recibido=pago_evento["monto_recibido"],
        fecha_pago_real_str=pago_evento["fecha_pago_actual"],
        tasa_interes_compensatoria_pct=0, 
        tasa_interes_moratoria_pct=0
    )
    print(json.dumps(resultado_legacy, indent=4))

    # --- 3. Ejecutar Algoritmo RECONCILIACIÓN ---
    print("\n--- Ejecutando Algoritmo RECONCILIACIÓN ---")
    datos_evento_reconciliacion = {
        "capital_desembolsado": datos_originacion["capital_calculado"],
        "interes_original_cobrado": datos_originacion["interes_original_cobrado"],
        "igv_interes_original_cobrado": datos_originacion["igv_interes_original_cobrado"],
        "fecha_desembolso": datos_originacion["fecha_desembolso"],
        "fecha_pago_calculada_original": datos_originacion["fecha_pago_calculada"],
        "fecha_pago_actual": pago_evento["fecha_pago_actual"],
        "monto_recibido": pago_evento["monto_recibido"],
        "tasa_compensatoria_pct": datos_originacion["tasa_compensatoria_pct"],
        "tasa_moratoria_pct": datos_originacion["tasa_moratoria_pct"]
    }
    resultado_reconciliacion = calcular_liquidacion_RECONCILIACION(datos_evento_reconciliacion)
    print(json.dumps(resultado_reconciliacion, indent=4))

    # --- 4. Generar PDF Comparativo ---
    print("\n--- Generando PDF Comparativo ---")
    inputs_reporte = {"datos_originacion": datos_originacion, "pago_evento": pago_evento}
    generar_pdf_comparativo(inputs_reporte, resultado_legacy, resultado_reconciliacion)

    print("\n--- FIN DE LA SIMULACIÓN COMPARATIVA ---")