
import datetime
import math
import json

# --- CÁLCULO DE DESEMBOLSO INICIAL ---

def calcular_desembolso_inicial(**kwargs) -> dict:
    """Adaptador para procesar una sola factura llamando a la lógica de lote."""
    resultado_lote = procesar_lote_desembolso_inicial([kwargs])
    if resultado_lote and resultado_lote.get("resultados_por_factura"):
        return resultado_lote["resultados_por_factura"][0]
    return resultado_lote

def procesar_lote_desembolso_inicial(lote_datos: list) -> dict:
    """
    Orquesta el cálculo del desembolso para un lote, aplicando la lógica de comisión agregada.
    """
    if not lote_datos:
        return {"error": "El lote de datos no puede estar vacío."}

    # FASE 1: Decisión Agregada sobre la Comisión (Elegir el MAYOR)
    capital_total_agregado = sum(d.get("mfn", 0) * d.get("tasa_avance", 0) for d in lote_datos)
    comision_fija_total = sum(d.get("comision_minima_aplicable", 0) for d in lote_datos)
    comision_porcentual_total = capital_total_agregado * lote_datos[0].get("comision_estructuracion_pct", 0)

    metodo_de_comision_elegido = "PORCENTAJE" if comision_porcentual_total > comision_fija_total else "FIJO_PRORRATEADO"

    # FASE 2: Cálculo Individual con la Decisión ya Tomada
    resultados_finales = []
    for datos_factura in lote_datos:
        capital_individual = datos_factura.get("mfn", 0) * datos_factura.get("tasa_avance", 0)
        
        if metodo_de_comision_elegido == "PORCENTAJE":
            comision_para_esta_factura = capital_individual * datos_factura.get("comision_estructuracion_pct", 0)
        else: # FIJO_PRORRATEADO
            comision_para_esta_factura = datos_factura.get("comision_minima_aplicable", 0)
            
        resultado_factura = _calcular_desglose_factura(
            comision_estructuracion_fija=comision_para_esta_factura,
            **datos_factura
        )
        resultados_finales.append(resultado_factura)
        
    # FASE 3: Corrección de Totales
    total_comision_corregido = sum(c['comision_estructuracion'] for c in resultados_finales)

    return {
        "metodo_comision_elegido": metodo_de_comision_elegido,
        "comision_estructuracion_total_corregida": round(total_comision_corregido, 2),
        "resultados_por_factura": resultados_finales
    }

def _calcular_desglose_factura(comision_estructuracion_fija: float, **kwargs) -> dict:
    """Calcula los detalles de UNA factura. Asume que la comisión ya fue resuelta."""
    capital = kwargs["mfn"] * kwargs["tasa_avance"]
    tasa_diaria = kwargs["interes_mensual"] / 30
    interes = capital * (((1 + tasa_diaria) ** kwargs["plazo_operacion"]) - 1)
    igv_interes = interes * kwargs["igv_pct"]
    comision_estructuracion = comision_estructuracion_fija
    igv_comision = comision_estructuracion * kwargs["igv_pct"]
    
    abono_real_teorico = capital - interes - igv_interes - comision_estructuracion - igv_comision
    
    comision_afiliacion = 0.0
    igv_afiliacion = 0.0
    if kwargs.get("aplicar_comision_afiliacion", False):
        comision_afiliacion = kwargs.get("comision_afiliacion_aplicable", 0.0)
        igv_afiliacion = comision_afiliacion * kwargs["igv_pct"]
        abono_real_teorico -= (comision_afiliacion + igv_afiliacion)

    return {
        "capital": round(capital, 2), "interes": round(interes, 2),
        "igv_interes": round(igv_interes, 2), "comision_estructuracion": round(comision_estructuracion, 2),
        "igv_comision": round(igv_comision, 2), "comision_afiliacion": round(comision_afiliacion, 2),
        "igv_afiliacion": round(igv_afiliacion, 2), "abono_real_teorico": round(abono_real_teorico, 2),
        "monto_desembolsado": math.floor(abono_real_teorico),
        "margen_seguridad": round(kwargs["mfn"] - capital, 2), "plazo_operacion": kwargs["plazo_operacion"]
    }

# --- BÚSQUEDA DE TASA DE AVANCE ---

def encontrar_tasa_de_avance(**kwargs) -> dict:
    """Adaptador para procesar una sola factura llamando a la lógica de lote."""
    resultado_lote = procesar_lote_encontrar_tasa([kwargs])
    if resultado_lote and resultado_lote.get("resultados_por_factura"):
        return resultado_lote["resultados_por_factura"][0]
    return resultado_lote

def procesar_lote_encontrar_tasa(lote_datos: list) -> dict:
    """
    Encuentra la tasa de avance para un lote, asegurando que la decisión de la comisión
    se tome a nivel de lote (el método que resulte en mayor cobro).
    """
    if not lote_datos:
        return {"error": "El lote de datos no puede estar vacío."}

    # FASE 1: Calcular Capitales Necesarios para ambos escenarios
    capitales_A = [] # Escenario A: Comisión por Porcentaje
    capitales_B = [] # Escenario B: Comisión Fija
    for datos_factura in lote_datos:
        capital_A, capital_B = _resolver_capital_dual(**datos_factura)
        capitales_A.append(capital_A)
        capitales_B.append(capital_B)

    # FASE 2: Decisión Agregada sobre la Comisión (Elegir el MAYOR)
    comision_pct = lote_datos[0].get("comision_estructuracion_pct", 0)
    comision_total_A = sum(capitales_A) * comision_pct
    comision_total_B = sum(d.get("comision_minima_aplicable", 0) for d in lote_datos)
    metodo_de_comision_elegido = "PORCENTAJE" if comision_total_A > comision_total_B else "FIJO_PRORRATEADO"

    # FASE 3: Cálculo Final Individual con la Decisión ya Tomada
    resultados_finales = []
    for i, datos_factura in enumerate(lote_datos):
        capital_necesario = capitales_A[i] if metodo_de_comision_elegido == "PORCENTAJE" else capitales_B[i]
        
        # Determinar la comisión de estructuración final para esta factura
        if metodo_de_comision_elegido == "PORCENTAJE":
            comision_final_factura = capital_necesario * comision_pct
        else: # FIJO_PRORRATEADO
            comision_final_factura = datos_factura.get("comision_minima_aplicable", 0)

        resultado_factura = _construir_respuesta_tasa_encontrada(
            capital_necesario=capital_necesario,
            comision_estructuracion_final=comision_final_factura,
            **datos_factura
        )
        resultados_finales.append(resultado_factura)

    return {
        "metodo_comision_elegido": metodo_de_comision_elegido,
        "resultados_por_factura": resultados_finales
    }

def _resolver_capital_dual(**kwargs) -> tuple[float, float]:
    """Resuelve el capital necesario para un monto objetivo bajo ambos esquemas de comisión."""
    tasa_diaria = kwargs["interes_mensual"] / 30
    factor_interes = ((1 + tasa_diaria) ** kwargs["plazo_operacion"]) - 1
    costo_fijo_afiliacion = 0.0
    if kwargs.get("aplicar_comision_afiliacion", False):
        costo_fijo_afiliacion = kwargs.get("comision_afiliacion_aplicable", 0) * (1 + kwargs["igv_pct"])

    # Escenario A: Comisión por Porcentaje
    costo_variable_A = (factor_interes + kwargs["comision_estructuracion_pct"]) * (1 + kwargs["igv_pct"])
    capital_A = (kwargs["monto_objetivo"] + costo_fijo_afiliacion) / (1 - costo_variable_A) if (1 - costo_variable_A) > 0 else 0

    # Escenario B: Comisión Fija
    costo_variable_B = factor_interes * (1 + kwargs["igv_pct"])
    costo_fijo_estructuracion = kwargs["comision_minima_aplicable"] * (1 + kwargs["igv_pct"])
    costos_fijos_totales_B = costo_fijo_estructuracion + costo_fijo_afiliacion
    capital_B = (kwargs["monto_objetivo"] + costos_fijos_totales_B) / (1 - costo_variable_B) if (1 - costo_variable_B) > 0 else 0
    
    return capital_A, capital_B

def _construir_respuesta_tasa_encontrada(capital_necesario: float, comision_estructuracion_final: float, **kwargs) -> dict:
    """Construye el diccionario de respuesta final para una factura con la comisión ya decidida."""
    mfn = kwargs["mfn"]
    if mfn == 0: return {"error": "MFN no puede ser cero."}

    capital = capital_necesario
    tasa_diaria = kwargs["interes_mensual"] / 30
    factor_interes = ((1 + tasa_diaria) ** kwargs["plazo_operacion"]) - 1
    interes = capital * factor_interes
    igv_interes = interes * kwargs["igv_pct"]
    
    # LA LÓGICA DE DECISIÓN YA NO ESTÁ AQUÍ. Se usa el valor pre-calculado.
    comision_estructuracion = comision_estructuracion_final
    igv_comision_estructuracion = comision_estructuracion * kwargs["igv_pct"]
    
    comision_afiliacion = 0.0
    igv_afiliacion = 0.0
    if kwargs.get("aplicar_comision_afiliacion", False):
        comision_afiliacion = kwargs.get("comision_afiliacion_aplicable", 0)
        igv_afiliacion = comision_afiliacion * kwargs["igv_pct"]
    
    abono_real = capital - interes - igv_interes - comision_estructuracion - igv_comision_estructuracion - comision_afiliacion - igv_afiliacion
    margen_seguridad = mfn - capital
    total_igv = igv_interes + igv_comision_estructuracion + igv_afiliacion
    tasa_avance_encontrada = capital / mfn

    desglose = {
        "abono": {"monto": round(abono_real, 2), "porcentaje": round((abono_real / mfn) * 100, 3)},
        "interes": {"monto": round(interes, 2), "porcentaje": round((interes / mfn) * 100, 3)},
        "comision_estructuracion": {"monto": round(comision_estructuracion, 2), "porcentaje": round((comision_estructuracion / mfn) * 100, 3)},
        "comision_afiliacion": {"monto": round(comision_afiliacion, 2), "porcentaje": round((comision_afiliacion / mfn) * 100, 3)},
        "igv_total": {"monto": round(total_igv, 2), "porcentaje": round((total_igv / mfn) * 100, 3)},
        "margen_seguridad": {"monto": round(margen_seguridad, 2), "porcentaje": round((margen_seguridad / mfn) * 100, 3)}
    }

    return {
        "resultado_busqueda": {
            "tasa_avance_encontrada": round(tasa_avance_encontrada, 6),
            "abono_real_calculado": round(abono_real, 2),
            "monto_objetivo": kwargs["monto_objetivo"]
        },
        "calculo_con_tasa_encontrada": {
            "capital": round(capital, 2), "interes": round(interes, 2), "igv_interes": round(igv_interes, 2),
            "comision_estructuracion": round(comision_estructuracion, 2), "igv_comision_estructuracion": round(igv_comision_estructuracion, 2),
            "comision_afiliacion": round(comision_afiliacion, 2), "igv_afiliacion": round(igv_afiliacion, 2),
            "margen_seguridad": round(margen_seguridad, 2), "plazo_operacion": kwargs["plazo_operacion"]
        },
        "desglose_final_detallado": desglose
    }

if __name__ == '__main__':
    pass
