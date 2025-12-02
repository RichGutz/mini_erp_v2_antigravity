from datetime import datetime, timedelta
from decimal import Decimal, getcontext

# Set precision for Decimal calculations
getcontext().prec = 30

def _safe_get(data: dict, key: str, default_value=0, target_type=Decimal):
    """
    Safely gets a value from a dictionary, handles None, and converts its type.
    """
    value = data.get(key)
    if value is None:
        return Decimal(default_value)
    try:
        return target_type(str(value)) # Convert to string before Decimal to avoid float inaccuracies
    except (ValueError, TypeError):
        return Decimal(default_value)

def calcular_liquidacion(
    datos_operacion: dict,
    monto_recibido: float,
    fecha_pago_real_str: str,
    tasa_interes_compensatoria_pct: float,
    tasa_interes_moratoria_pct: float
) -> dict:
    """
    Calcula la liquidación de una operación de factoring.
    """
    try:
        # 1. Extraer y validar datos clave
        fecha_pago_esperada_str = datos_operacion.get('fecha_pago_calculada')
        if not fecha_pago_esperada_str:
            raise ValueError("La 'fecha_pago_calculada' es inválida o no fue encontrada.")

        capital_desembolsado = _safe_get(datos_operacion, 'capital_calculado')
        interes_original = _safe_get(datos_operacion, 'interes_calculado')
        plazo_operacion_original = _safe_get(datos_operacion, 'plazo_operacion_calculado', target_type=int)
        interes_mensual_pct = _safe_get(datos_operacion, 'interes_mensual')
        igv_pct = Decimal('0.18')

        fecha_pago_esperada = datetime.strptime(fecha_pago_esperada_str, '%d-%m-%Y')
        fecha_pago_real = datetime.strptime(fecha_pago_real_str, '%d-%m-%Y')

    except (ValueError, TypeError, AttributeError) as e:
        return {"error": f"Error en los datos de entrada: {e}"}

    # 2. Calcular diferencias y tasas
    dias_diferencia = (fecha_pago_real - fecha_pago_esperada).days
    if abs(dias_diferencia) > 365 * 5:
        return {"error": f"El número de días de diferencia ({dias_diferencia}) excede el límite. Revise las fechas."}

    monto_recibido_dec = Decimal(str(monto_recibido))
    diferencia_monto_pago = capital_desembolsado - monto_recibido_dec
    tasa_diaria_compensatoria = (Decimal(str(tasa_interes_compensatoria_pct)) / Decimal('100')) / Decimal('30')
    tasa_diaria_moratoria = (Decimal(str(tasa_interes_moratoria_pct)) / Decimal('100')) / Decimal('30')
    tasa_diaria_original = (interes_mensual_pct / Decimal('100')) / Decimal('30') if interes_mensual_pct else Decimal('0')

    # 3. Inicializar variables
    base_moratorio_calc = Decimal('0')
    cargo_por_diferencia = Decimal('0')
    credito_por_diferencia = Decimal('0')
    interes_compensatorio_final_calc, igv_interes_compensatorio_final_calc = Decimal('0'), Decimal('0')
    interes_moratorio_final_calc, igv_interes_moratorio_final_calc = Decimal('0'), Decimal('0')
    interes_a_devolver_final_calc, igv_interes_a_devolver_final_calc = Decimal('0'), Decimal('0')

    if diferencia_monto_pago > 0:
        cargo_por_diferencia = diferencia_monto_pago
    else:
        credito_por_diferencia = abs(diferencia_monto_pago)

    # 4. Lógica de cálculo principal
    if dias_diferencia > 0:
        capital_base_para_interes_calc = abs(capital_desembolsado)
        
        interes_compensatorio_final_calc = capital_base_para_interes_calc * ((Decimal('1') + tasa_diaria_compensatoria) ** dias_diferencia - Decimal('1'))
        igv_interes_compensatorio_final_calc = interes_compensatorio_final_calc * igv_pct
        
        base_moratorio_calc = capital_base_para_interes_calc
        interes_moratorio_final_calc = base_moratorio_calc * ((Decimal('1') + tasa_diaria_moratoria) ** dias_diferencia - Decimal('1'))
        igv_interes_moratorio_final_calc = interes_moratorio_final_calc * igv_pct

    elif dias_diferencia < 0:
        dias_anticipacion = abs(dias_diferencia)
        plazo_real = plazo_operacion_original - dias_anticipacion
        if plazo_real < 0: plazo_real = 0
        interes_real_calculado = capital_desembolsado * ((Decimal('1') + tasa_diaria_original) ** plazo_real - Decimal('1'))
        interes_a_devolver_final_calc = interes_original - interes_real_calculado
        if interes_a_devolver_final_calc < 0: interes_a_devolver_final_calc = Decimal('0')
        igv_interes_a_devolver_final_calc = interes_a_devolver_final_calc * igv_pct

    # 5. Calcular saldo final
    total_owed_before_payment = capital_desembolsado + interes_compensatorio_final_calc + igv_interes_compensatorio_final_calc + \
                                interes_moratorio_final_calc + igv_interes_moratorio_final_calc

    saldo_final = total_owed_before_payment - monto_recibido_dec

    # 6. Preparar el resultado final
    resultado_liquidacion = {
        "parametros_calculo": {
            "capital_base": float(abs(capital_desembolsado).quantize(Decimal('0.01'))),
            "base_calculo_mora": float(abs(base_moratorio_calc).quantize(Decimal('0.01'))),
            "tasa_interes_compensatoria_pct": tasa_interes_compensatoria_pct,
            "tasa_interes_moratoria_pct": tasa_interes_moratoria_pct,
            "interes_original_completo": float(interes_original.quantize(Decimal('0.01'))),
            "plazo_operacion_original": plazo_operacion_original,
            "capital_no_pagado_en_fecha_pago": float(cargo_por_diferencia.quantize(Decimal('0.01'))),
            "pago_excedente_sobre_capital": float(credito_por_diferencia.quantize(Decimal('0.01'))),
            "tasa_diaria_compensatoria": float(tasa_diaria_compensatoria),
            "tasa_diaria_moratoria": float(tasa_diaria_moratoria),
            "tasa_diaria_original": float(tasa_diaria_original)
        },
        "dias_diferencia": dias_diferencia,
        "tipo_pago": "Tardío" if dias_diferencia > 0 else ("Anticipado" if dias_diferencia < 0 else "A Tiempo"),
        "cargo_por_diferencia": float(cargo_por_diferencia.quantize(Decimal('0.01'))),
        "credito_por_diferencia": float(credito_por_diferencia.quantize(Decimal('0.01'))),
        "desglose_cargos": {
            "interes_compensatorio": float(interes_compensatorio_final_calc.quantize(Decimal('0.01'))),
            "igv_interes_compensatorio": float(igv_interes_compensatorio_final_calc.quantize(Decimal('0.01'))),
            "interes_moratorio": float(interes_moratorio_final_calc.quantize(Decimal('0.01'))),
            "igv_interes_moratorio": float(igv_interes_moratorio_final_calc.quantize(Decimal('0.01'))),
            "total_cargos": float((interes_compensatorio_final_calc + igv_interes_compensatorio_final_calc + interes_moratorio_final_calc + igv_interes_moratorio_final_calc + cargo_por_diferencia).quantize(Decimal('0.01')))
        },
        "desglose_creditos": {
            "interes_a_devolver": float(interes_a_devolver_final_calc.quantize(Decimal('0.01'))),
            "igv_interes_a_devolver": float(igv_interes_a_devolver_final_calc.quantize(Decimal('0.01'))),
            "total_creditos": float((interes_a_devolver_final_calc + igv_interes_a_devolver_final_calc + credito_por_diferencia).quantize(Decimal('0.01')))
        },
        "liquidacion_final": {
            "saldo_final_a_liquidar": float(saldo_final.quantize(Decimal('0.01')))
        },
        "proyeccion_futura": []
    }

    return resultado_liquidacion

def proyectar_saldo_diario(capital_inicial: float, fecha_inicio: datetime.date,
                           tasa_compensatoria_mensual: float, tasa_moratoria_mensual: float,
                           dias_proyeccion: int) -> list:
    """
    Proyecta el saldo diario de un capital, aplicando intereses compensatorios y moratorios.
    """
    proyeccion = []
    current_capital = Decimal(str(capital_inicial))
    current_date = fecha_inicio

    tasa_diaria_compensatoria = (Decimal(str(tasa_compensatoria_mensual)) / Decimal('100')) / Decimal('30')
    tasa_diaria_moratoria = (Decimal(str(tasa_moratoria_mensual)) / Decimal('100')) / Decimal('30')
    igv_pct = Decimal('0.18')

    for i in range(dias_proyeccion):
        interes_compensatorio_dia = current_capital * tasa_diaria_compensatoria
        igv_compensatorio_dia = interes_compensatorio_dia * igv_pct

        base_moratorio_dia = current_capital
        interes_moratorio_dia = base_moratorio_dia * tasa_diaria_moratoria
        igv_moratorio_dia = interes_moratorio_dia * igv_pct

        capital_al_inicio_del_dia = current_capital
        current_capital += interes_compensatorio_dia + igv_compensatorio_dia + \
                           interes_moratorio_dia + igv_moratorio_dia

        proyeccion.append({
            "fecha": current_date.strftime('%d-%m-%Y'),
            "capital_anterior": float(capital_al_inicio_del_dia.quantize(Decimal('0.01'))),
            "interes_compensatorio": float(interes_compensatorio_dia.quantize(Decimal('0.01'))),
            "igv_compensatorio": float(igv_compensatorio_dia.quantize(Decimal('0.01'))),
            "interes_moratorio": float(interes_moratorio_dia.quantize(Decimal('0.01'))),
            "igv_moratorio": float(igv_moratorio_dia.quantize(Decimal('0.01'))),
            "capital_proyectado": float(current_capital.quantize(Decimal('0.01')))
        })

        current_date += timedelta(days=1)

    return proyeccion

def procesar_lote_liquidacion(lote_datos: list) -> dict:
    """
    Procesa un lote de solicitudes de liquidación.
    """
    resultados_lote = []
    for datos_liquidacion in lote_datos:
        try:
            # Aquí necesitaríamos una forma de obtener los 'datos_operacion' para cada una.
            # Esto es una simplificación y requerirá una función que busque en la DB.
            # Por ahora, asumimos que los datos necesarios vienen en el payload.
            resultado = calcular_liquidacion(
                datos_operacion=datos_liquidacion.get('datos_operacion', {}),
                monto_recibido=datos_liquidacion.get('monto_recibido'),
                fecha_pago_real_str=datos_liquidacion.get('fecha_pago_real_str'),
                tasa_interes_compensatoria_pct=datos_liquidacion.get('tasa_interes_compensatoria_pct'),
                tasa_interes_moratoria_pct=datos_liquidacion.get('tasa_interes_moratoria_pct')
            )
            resultados_lote.append(resultado)
        except Exception as e:
            resultados_lote.append({"error": f"Error procesando item: {e}"})
    
    return {"resultados_por_factura": resultados_lote}