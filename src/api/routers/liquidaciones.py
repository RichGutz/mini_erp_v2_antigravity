import sys
import os
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# --- Configuración de Path para Módulos ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from core.liquidation_calculator import calcular_liquidacion, proyectar_saldo_diario
from data.supabase_repository import (
    get_proposal_details_by_id,
    get_or_create_liquidacion_resumen,
    add_liquidacion_evento,
    update_liquidacion_resumen_saldo,
    get_liquidacion_resumen,
    get_liquidacion_eventos,
    update_proposal_status,
    add_audit_event
)

router = APIRouter()

# --- Modelos de Datos (Pydantic) ---

class LiquidacionInfo(BaseModel):
    proposal_id: str
    monto_recibido: float
    fecha_pago_real: str # Format: DD-MM-YYYY
    tasa_interes_compensatoria_pct: float
    tasa_interes_moratoria_pct: float
    is_first_payment: bool

class ProcesarLiquidacionRequest(BaseModel):
    usuario_id: str
    liquidaciones: List[LiquidacionInfo]

class GetProjectedBalanceRequest(BaseModel):
    proposal_id: str
    fecha_inicio_proyeccion: str # Format 'YYYY-MM-DD' from ISO format
    initial_capital: Optional[float] = None

# --- Endpoints de Gestión de Estado ---

@router.post("/procesar_liquidacion_lote")
async def procesar_liquidacion_lote_endpoint(request: ProcesarLiquidacionRequest):
    resultados = []
    for liquidacion in request.liquidaciones:
        proposal_id = liquidacion.proposal_id
        try:
            # 1. Obtener datos y estado actual
            datos_operacion = get_proposal_details_by_id(proposal_id)
            if not datos_operacion:
                raise HTTPException(status_code=404, detail=f"Propuesta {proposal_id} no encontrada.")
            
            estado_anterior = datos_operacion.get('estado', 'DESCONOCIDO')
            if estado_anterior not in ['DESEMBOLSADA', 'EN PROCESO DE LIQUIDACION']:
                raise HTTPException(status_code=400, detail=f"Factura {proposal_id} no está en un estado válido para liquidar.")

            # 2. Preparar y ejecutar el cálculo de liquidación (reutilizando lógica anterior)
            # (Esta sección es una adaptación de la lógica del endpoint /liquidar_factura)
            fecha_str_original = datos_operacion.get('fecha_pago_calculada')
            if fecha_str_original:
                try:
                    fecha_obj = datetime.fromisoformat(fecha_str_original.split('T')[0])
                    datos_operacion['fecha_pago_calculada'] = fecha_obj.strftime('%d-%m-%Y')
                except (ValueError, TypeError): pass
            
            recalc_json_str = datos_operacion.get('recalculate_result_json')
            if recalc_json_str:
                try:
                    recalc_data = json.loads(recalc_json_str)
                    calculos = recalc_data.get('calculo_con_tasa_encontrada', {})
                    desglose = recalc_data.get('desglose_final_detallado', {})
                    datos_operacion['capital_calculado'] = calculos.get('capital')
                    datos_operacion['interes_calculado'] = desglose.get('interes', {}).get('monto')
                except (json.JSONDecodeError, AttributeError): pass

            liquidacion_previa = get_liquidacion_resumen(proposal_id)
            eventos_liquidacion = get_liquidacion_eventos(proposal_id)
            fecha_ultimo_evento_str = None
            if eventos_liquidacion:
                fecha_ultimo_evento_str = eventos_liquidacion[-1]['fecha_evento']

            if not liquidacion.is_first_payment and liquidacion_previa and liquidacion_previa.get('saldo_actual') is not None:
                datos_operacion['capital_calculado'] = liquidacion_previa['saldo_actual']
                if fecha_ultimo_evento_str:
                    datos_operacion['fecha_pago_calculada'] = datetime.fromisoformat(fecha_ultimo_evento_str.split('+')[0]).strftime('%d-%m-%Y')

            params_calculo = {
                "datos_operacion": datos_operacion,
                "monto_recibido": liquidacion.monto_recibido,
                "fecha_pago_real_str": liquidacion.fecha_pago_real,
                "tasa_interes_compensatoria_pct": liquidacion.tasa_interes_compensatoria_pct,
                "tasa_interes_moratoria_pct": liquidacion.tasa_interes_moratoria_pct
            }
            resultado_calculo = calcular_liquidacion(**params_calculo)

            # 3. Determinar nuevo estado y guardar todo en una transacción
            saldo_final = resultado_calculo.get('liquidacion_final', {}).get('saldo_final_a_liquidar', 0)
            nuevo_estado = 'LIQUIDADA' if saldo_final <= 0 else 'EN PROCESO DE LIQUIDACION'

            # Guardar evento de liquidación
            liquidacion_resumen_id = get_or_create_liquidacion_resumen(proposal_id, datos_operacion)
            add_liquidacion_evento(
                liquidacion_resumen_id=liquidacion_resumen_id,
                tipo_evento=resultado_calculo.get('tipo_pago', 'Desconocido'),
                fecha_evento=datetime.strptime(liquidacion.fecha_pago_real, '%d-%m-%Y'),
                monto_recibido=liquidacion.monto_recibido,
                dias_diferencia=resultado_calculo.get('dias_diferencia', 0),
                resultado_json=resultado_calculo
            )
            update_liquidacion_resumen_saldo(liquidacion_resumen_id, saldo_final)
            
            # Actualizar estado de la propuesta
            update_proposal_status(proposal_id, nuevo_estado)

            # 4. Registrar evento de auditoría
            add_audit_event(
                usuario_id=request.usuario_id,
                entidad_id=proposal_id,
                accion="LIQUIDACION",
                estado_anterior=estado_anterior,
                estado_nuevo=nuevo_estado,
                detalles_adicionales=liquidacion.dict()
            )

            resultados.append({"proposal_id": proposal_id, "status": "SUCCESS", "message": f"Liquidación registrada. Nuevo estado: {nuevo_estado}", "resultado_calculo": resultado_calculo})

        except Exception as e:
            resultados.append({"proposal_id": proposal_id, "status": "ERROR", "message": str(e)})
    
    return {"resultados_del_lote": resultados}

@router.post("/simular_liquidacion_lote")
async def simular_liquidacion_lote_endpoint(request: ProcesarLiquidacionRequest):
    resultados = []
    for liquidacion in request.liquidaciones:
        proposal_id = liquidacion.proposal_id
        try:
            # 1. Obtener datos y estado actual
            datos_operacion = get_proposal_details_by_id(proposal_id)
            if not datos_operacion:
                raise HTTPException(status_code=404, detail=f"Propuesta {proposal_id} no encontrada.")
            
            estado_anterior = datos_operacion.get('estado', 'DESCONOCIDO')
            if estado_anterior not in ['DESEMBOLSADA', 'EN PROCESO DE LIQUIDACION']:
                raise HTTPException(status_code=400, detail=f"Factura {proposal_id} no está en un estado válido para liquidar.")

            # 2. Preparar y ejecutar el cálculo de liquidación (reutilizando lógica anterior)
            # (Esta sección es una adaptación de la lógica del endpoint /liquidar_factura)
            fecha_str_original = datos_operacion.get('fecha_pago_calculada')
            if fecha_str_original:
                try:
                    fecha_obj = datetime.fromisoformat(fecha_str_original.split('T')[0])
                    datos_operacion['fecha_pago_calculada'] = fecha_obj.strftime('%d-%m-%Y')
                except (ValueError, TypeError): pass
            
            recalc_json_str = datos_operacion.get('recalculate_result_json')
            if recalc_json_str:
                try:
                    recalc_data = json.loads(recalc_json_str)
                    calculos = recalc_data.get('calculo_con_tasa_encontrada', {})
                    desglose = recalc_data.get('desglose_final_detallado', {})
                    datos_operacion['capital_calculado'] = calculos.get('capital')
                    datos_operacion['interes_calculado'] = desglose.get('interes', {}).get('monto')
                except (json.JSONDecodeError, AttributeError): pass

            liquidacion_previa = get_liquidacion_resumen(proposal_id)
            eventos_liquidacion = get_liquidacion_eventos(proposal_id)
            fecha_ultimo_evento_str = None
            if eventos_liquidacion:
                fecha_ultimo_evento_str = eventos_liquidacion[-1]['fecha_evento']

            if not liquidacion.is_first_payment and liquidacion_previa and liquidacion_previa.get('saldo_actual') is not None:
                datos_operacion['capital_calculado'] = liquidacion_previa['saldo_actual']
                if fecha_ultimo_evento_str:
                    datos_operacion['fecha_pago_calculada'] = datetime.fromisoformat(fecha_ultimo_evento_str.split('+')[0]).strftime('%d-%m-%Y')

            params_calculo = {
                "datos_operacion": datos_operacion,
                "monto_recibido": liquidacion.monto_recibido,
                "fecha_pago_real_str": liquidacion.fecha_pago_real,
                "tasa_interes_compensatoria_pct": liquidacion.tasa_interes_compensatoria_pct,
                "tasa_interes_moratoria_pct": liquidacion.tasa_interes_moratoria_pct
            }
            resultado_calculo = calcular_liquidacion(**params_calculo)

            resultados.append({"proposal_id": proposal_id, "status": "SUCCESS", "message": "Simulación de liquidación exitosa.", "resultado_calculo": resultado_calculo})

        except Exception as e:
            resultados.append({"proposal_id": proposal_id, "status": "ERROR", "message": str(e)})
    
    return {"resultados_del_lote": resultados}

@router.post("/get_projected_balance")
async def get_projected_balance_endpoint(request: GetProjectedBalanceRequest):
    try:
        # 1. Obtener detalles de la propuesta
        proposal_details = get_proposal_details_by_id(request.proposal_id)
        if not proposal_details:
            raise HTTPException(status_code=404, detail="Proposal not found")

        # 2. Extraer tasas de interés
        interes_compensatorio = proposal_details.get('interes_mensual')
        interes_moratorio = proposal_details.get('interes_moratorio')
        if interes_compensatorio is None or interes_moratorio is None:
            raise HTTPException(status_code=400, detail="Tasas de interés no encontradas en la propuesta.")

        # 3. Validar y convertir fecha
        try:
            fecha_inicio = datetime.fromisoformat(request.fecha_inicio_proyeccion.split('+')[0]).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use ISO format.")

        # 4. Llamar a la función de proyección
        proyeccion = proyectar_saldo_diario(
            capital_inicial=request.initial_capital,
            fecha_inicio=fecha_inicio,
            tasa_compensatoria_mensual=interes_compensatorio,
            tasa_moratoria_mensual=interes_moratorio,
            dias_proyeccion=30  # Proyectar por 30 días por defecto
        )

        return {"proyeccion_futura": proyeccion}

    except Exception as e:
        # Log the exception details here if you have a logger
        raise HTTPException(status_code=500, detail=str(e))
