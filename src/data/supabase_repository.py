# src/data/supabase_repository.py

import os
import json
import datetime as dt
from typing import List, Dict, Any, Optional

# Internal imports
from .supabase_client import get_supabase_client

# --- Type Aliases for Clarity ---
Proposal = Dict[str, Any]

# --- Helper Functions ---

def _format_date(date_str: Optional[str]) -> Optional[str]:
    """Converts a date from DD-MM-YYYY to YYYY-MM-DD for Supabase."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return dt.datetime.strptime(date_str, '%d-%m-%Y').strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return date_str # Return original if format is already correct or different

def _convert_to_numeric(value: Any) -> Optional[float]:
    """Tries to convert a value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# --- Public Repository Functions ---

# --- Functions for Operations Module (Original `supabase_handler`) ---

def get_razon_social_by_ruc(ruc: str) -> str:
    """Fetches a company's legal name by its RUC."""
    supabase = get_supabase_client()
    if not ruc:
        return ""
    try:
        response = supabase.table('EMISORES.DEUDORES').select('"Razon Social"').eq('RUC', ruc).single().execute()
        return response.data.get('Razon Social', '') if response.data else ''
    except Exception as e:
        print(f"[ERROR in get_razon_social_by_ruc]: {e}")
        return ""

def save_proposal(session_data: Proposal, identificador_lote: str) -> tuple[bool, str]:
    """Saves a complete proposal to the 'propuestas' table."""
    supabase = get_supabase_client()
    try:
        recalculate_result_full = session_data.get('recalculate_result')
        data_to_insert = {
            'recalculate_result_json': json.dumps(recalculate_result_full) if recalculate_result_full else None,
            'emisor_nombre': session_data.get('emisor_nombre'),
            'emisor_ruc': session_data.get('emisor_ruc'),
            'aceptante_nombre': session_data.get('aceptante_nombre'),
            'aceptante_ruc': session_data.get('aceptante_ruc'),
            'numero_factura': session_data.get('numero_factura'),
            'monto_total_factura': _convert_to_numeric(session_data.get('monto_total_factura')),
            'monto_neto_factura': _convert_to_numeric(session_data.get('monto_neto_factura')),
            'moneda_factura': session_data.get('moneda_factura'),
            'fecha_emision_factura': _format_date(session_data.get('fecha_emision_factura')),
            'plazo_credito_dias': int(session_data['plazo_credito_dias']) if session_data.get('plazo_credito_dias') is not None else None,
            'fecha_desembolso_factoring': _format_date(session_data.get('fecha_desembolso_factoring')),
            'tasa_de_avance': _convert_to_numeric(session_data.get('tasa_de_avance')),
            'interes_mensual': _convert_to_numeric(session_data.get('interes_mensual')),
            'interes_moratorio': _convert_to_numeric(session_data.get('interes_moratorio')),
            'fecha_pago_calculada': _format_date(session_data.get('fecha_pago_calculada')),
            'plazo_operacion_calculado': int(session_data['plazo_operacion_calculado']) if session_data.get('plazo_operacion_calculado') is not None else None,
            'anexo_number': session_data.get('anexo_number'),
            'contract_number': session_data.get('contract_number'),
            'identificador_lote': identificador_lote,
            'estado': 'ACTIVO'
        }

        if recalculate_result_full:
            capital = recalculate_result_full.get('calculo_con_tasa_encontrada', {}).get('capital')
            data_to_insert['capital_calculado'] = _convert_to_numeric(capital)

        emisor_nombre_id = str(data_to_insert.get('emisor_nombre', 'SIN_NOMBRE')).replace(' ', '_').replace('.', '')
        numero_factura = str(data_to_insert.get('numero_factura', 'SIN_FACTURA'))
        fecha_propuesta = dt.datetime.now().strftime('%Y%m%d%H%M%S')
        data_to_insert['proposal_id'] = f"{emisor_nombre_id}-{numero_factura}-{fecha_propuesta}"

        print(f"DEBUG: Data being sent to Supabase -> {json.dumps(data_to_insert, indent=4, default=str)}")
        response = supabase.table('propuestas').insert(data_to_insert).execute()
        if hasattr(response, 'error') and response.error:
            raise Exception(response.error.message)

        return True, f"Propuesta con ID {data_to_insert['proposal_id']} guardada exitosamente."

    except Exception as e:
        print(f"[ERROR en save_proposal]: {e}")
        return False, f"Error al guardar la propuesta: {e}"

def get_signatory_data_by_ruc(ruc: str) -> Optional[Dict[str, Any]]:
    """
    Fetches signatory data (legal name, address, etc.) for a given RUC.
    This is used for populating PDF reports like the EFIDE report.
    """
    supabase = get_supabase_client()
    if not ruc:
        return ""
    try:
        response = supabase.table('EMISORES.DEUDORES').select('*').eq('RUC', ruc).single().execute()
        return response.data if response.data else None
    except Exception as e:
        print(f"[ERROR in get_signatory_data_by_ruc]: {e}")
        return None

# --- Functions for Liquidation & Disbursement Modules ---

def get_proposals_by_lote(lote_id: str) -> List[Proposal]:
    """Retrieves a list of active proposals for a specific batch ID."""
    supabase = get_supabase_client()
    try:
        response = supabase.table('propuestas').select(
            'proposal_id, emisor_nombre, aceptante_nombre, monto_neto_factura, moneda_factura, anexo_number, contract_number, recalculate_result_json, estado'
        ).eq('identificador_lote', lote_id).eq('estado', 'ACTIVO').execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR en get_proposals_by_lote]: {e}")
        return []

def get_disbursed_proposals_by_lote(lote_id: str) -> List[Proposal]:
    """Retrieves a list of disbursed or in-liquidation proposals for a specific batch ID."""
    supabase = get_supabase_client()
    try:
        response = supabase.table('propuestas').select(
            'proposal_id, emisor_nombre, aceptante_nombre, monto_neto_factura, moneda_factura, anexo_number, contract_number, recalculate_result_json, estado'
        ).eq('identificador_lote', lote_id).in_('estado', ['DESEMBOLSADA', 'EN PROCESO DE LIQUIDACION']).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR en get_disbursed_proposals_by_lote]: {e}")
        return []

def get_proposal_details_by_id(proposal_id: str) -> Optional[Proposal]:
    """Retrieves all details for a single proposal by its ID."""
    supabase = get_supabase_client()
    try:
        response = supabase.table('propuestas').select('*').eq('proposal_id', proposal_id).single().execute()
        return response.data if response.data else None
    except Exception as e:
        print(f"[ERROR en get_proposal_details_by_id]: {e}")
        return None

def update_proposal_status(proposal_id: str, status: str) -> None:
    """Updates the status of a single proposal."""
    supabase = get_supabase_client()
    try:
        supabase.table('propuestas').update({'estado': status}).eq('proposal_id', proposal_id).execute()
    except Exception as e:
        print(f"[ERROR en update_proposal_status]: {e}")
        raise

# --- Liquidation Specific ---

def get_liquidacion_resumen(proposal_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the liquidation summary for a given proposal_id."""
    supabase = get_supabase_client()
    try:
        response = supabase.table('liquidaciones_resumen').select('*').eq('proposal_id', proposal_id).limit(1).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[ERROR en get_liquidacion_resumen]: {e}")
        return None

def get_liquidacion_eventos(proposal_id: str) -> List[Dict[str, Any]]:
    """Retrieves all liquidation events for a proposal, ordered by date."""
    supabase = get_supabase_client()
    try:
        resumen = get_liquidacion_resumen(proposal_id)
        if not resumen:
            return []
        resumen_id = resumen['id']
        response = supabase.table('liquidacion_eventos').select('*').eq('liquidacion_resumen_id', resumen_id).order('orden_evento', desc=False).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR en get_liquidacion_eventos]: {e}")
        return []

def get_or_create_liquidacion_resumen(proposal_id: str, datos_operacion: Proposal) -> str:
    """Gets or creates a liquidation summary entry and returns its ID."""
    supabase = get_supabase_client()
    existing_resumen = get_liquidacion_resumen(proposal_id)
    if existing_resumen:
        return existing_resumen['id']

    try:
        recalc_data = json.loads(datos_operacion.get('recalculate_result_json', '{}'))
        capital = recalc_data.get('calculo_con_tasa_encontrada', {}).get('capital', 0.0)
        new_entry = {
            "proposal_id": proposal_id,
            "saldo_actual": capital,
            "capital_original": capital,
        }
        response = supabase.table('liquidaciones_resumen').insert(new_entry).execute()
        if response.data:
            return response.data[0]['id']
        else:
            raise Exception(f"Failed to create liquidacion_resumen: {getattr(response, 'error', 'Unknown error')}")
    except Exception as e:
        print(f"[ERROR en get_or_create_liquidacion_resumen]: {e}")
        raise

def add_liquidacion_evento(liquidacion_resumen_id: str, tipo_evento: str, fecha_evento: dt.date, monto_recibido: float, dias_diferencia: int, resultado_json: dict) -> None:
    """Adds a new event to the liquidacion_eventos table."""
    supabase = get_supabase_client()
    try:
        last_event_response = supabase.table('liquidacion_eventos').select('orden_evento').eq('liquidacion_resumen_id', liquidacion_resumen_id).order('orden_evento', desc=True).limit(1).execute()
        last_orden = last_event_response.data[0]['orden_evento'] if last_event_response.data else 0
        
        new_event = {
            "liquidacion_resumen_id": liquidacion_resumen_id,
            "orden_evento": last_orden + 1,
            "tipo_evento": tipo_evento,
            "fecha_evento": fecha_evento.isoformat(),
            "monto_recibido": monto_recibido,
            "dias_diferencia": dias_diferencia,
            "resultado_json": json.dumps(resultado_json)
        }
        supabase.table('liquidacion_eventos').insert(new_event).execute()
    except Exception as e:
        print(f"[ERROR en add_liquidacion_evento]: {e}")
        raise

def update_liquidacion_resumen_saldo(liquidacion_resumen_id: str, saldo_actual: float) -> None:
    """Updates the saldo_actual in the liquidaciones_resumen table."""
    supabase = get_supabase_client()
    try:
        supabase.table('liquidaciones_resumen').update({'saldo_actual': saldo_actual}).eq('id', liquidacion_resumen_id).execute()
    except Exception as e:
        print(f"[ERROR en update_liquidacion_resumen_saldo]: {e}")
        raise

# --- Disbursement Specific ---

def get_desembolso_resumen(proposal_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the disbursement summary for a given proposal_id."""
    supabase = get_supabase_client()
    try:
        response = supabase.table('desembolsos_resumen').select('*').eq('proposal_id', proposal_id).limit(1).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[ERROR en get_desembolso_resumen]: {e}")
        return None

def get_or_create_desembolso_resumen(proposal_id: str, datos_operacion: Proposal) -> str:
    """Gets or creates a disbursement summary and returns its ID."""
    supabase = get_supabase_client()
    existing_resumen = get_desembolso_resumen(proposal_id)
    if existing_resumen:
        return existing_resumen['id']
    
    try:
        recalc_data = json.loads(datos_operacion.get('recalculate_result_json', '{}'))
        abono = recalc_data.get('desglose_final_detallado', {}).get('abono', {}).get('monto', 0.0)
        new_entry = {
            "proposal_id": proposal_id,
            "monto_desembolsado_total": abono,
        }
        response = supabase.table('desembolsos_resumen').insert(new_entry).execute()
        if response.data:
            return response.data[0]['id']
        else:
            raise Exception(f"Failed to create desembolso_resumen: {getattr(response, 'error', 'Unknown error')}")
    except Exception as e:
        print(f"[ERROR en get_or_create_desembolso_resumen]: {e}")
        raise

def add_desembolso_evento(desembolso_resumen_id: str, tipo_evento: str, fecha_evento: dt.date, monto_desembolsado: float) -> None:
    """Adds a new event to the desembolso_eventos table."""
    supabase = get_supabase_client()
    try:
        last_event_response = supabase.table('desembolso_eventos').select('orden_evento').eq('desembolso_resumen_id', desembolso_resumen_id).order('orden_evento', desc=True).limit(1).execute()
        last_orden = last_event_response.data[0]['orden_evento'] if last_event_response.data else 0
        
        new_event = {
            "desembolso_resumen_id": desembolso_resumen_id,
            "orden_evento": last_orden + 1,
            "tipo_evento": tipo_evento,
            "fecha_evento": fecha_evento.isoformat(),
            "monto_desembolsado": monto_desembolsado,
        }
        supabase.table('desembolso_eventos').insert(new_event).execute()
    except Exception as e:
        print(f"[ERROR en add_desembolso_evento]: {e}")
        raise

# --- Auditing ---

def add_audit_event(usuario_id: str, entidad_id: str, accion: str, estado_anterior: str, estado_nuevo: str, detalles_adicionales: dict) -> None:
    """Adds a new event to the auditoria_eventos table."""
    supabase = get_supabase_client()
    try:
        new_event = {
            "usuario_id": usuario_id,
            "entidad_id": entidad_id,
            "accion": accion,
            "estado_anterior": estado_anterior,
            "estado_nuevo": estado_nuevo,
            "detalles_adicionales": json.dumps(detalles_adicionales),
            "timestamp": dt.datetime.now().isoformat()
        }
        supabase.table('auditoria_eventos').insert(new_event).execute()
    except Exception as e:
        print(f"[ERROR en add_audit_event]: {e}")
        # Not raising exception here to avoid rolling back the main operation if audit fails
        pass

# --- Functions for User Management & Access Control ---

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieves a user's record from 'authorized_users' by email."""
    supabase = get_supabase_client()
    try:
        response = supabase.table('authorized_users').select('*').eq('email', email).single().execute()
        return response.data if response.data else None
    except Exception as e:
        print(f"[ERROR in get_user_by_email]: {e}")
        return None

def add_new_authorized_user(email: str) -> Optional[Dict[str, Any]]:
    """Adds a new user to 'authorized_users'."""
    supabase = get_supabase_client()
    try:
        response = supabase.table('authorized_users').insert({'email': email}).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[ERROR in add_new_authorized_user]: {e}")
        return None

def get_module_by_name(module_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves a module's record from 'modules' by name."""
    supabase = get_supabase_client()
    try:
        response = supabase.table('modules').select('*').eq('name', module_name).single().execute()
        return response.data if response.data else None
    except Exception as e:
        print(f"[ERROR in get_module_by_name]: {e}")
        return None

def get_user_module_access(user_id: int, module_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a user's access record for a specific module from 'user_module_access'."""
    supabase = get_supabase_client()
    try:
        response = supabase.table('user_module_access').select('*').eq('user_id', user_id).eq('module_id', module_id).single().execute()
        return response.data if response.data else None
    except Exception as e:
        print(f"[ERROR in get_user_module_access]: {e}")
        return None

def add_user_module_access(user_id: int, module_id: int, hierarchy_level: str = 'viewer') -> Optional[Dict[str, Any]]:
    """Grants a user access to a module with a specified hierarchy level."""
    supabase = get_supabase_client()
    try:
        response = supabase.table('user_module_access').insert({'user_id': user_id, 'module_id': module_id, 'hierarchy_level': hierarchy_level}).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[ERROR in add_user_module_access]: {e}")
        return None

def add_module(name: str, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Adds a new module to the 'modules' table."""
    supabase = get_supabase_client()
    try:
        response = supabase.table('modules').insert({'name': name, 'description': description}).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[ERROR in add_module]: {e}")
        return None
