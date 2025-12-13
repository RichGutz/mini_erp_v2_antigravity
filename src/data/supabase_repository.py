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
    
    # Robustification: Convert to string and strip whitespace
    clean_ruc = str(ruc).strip()
    
    try:
        response = supabase.table('EMISORES.ACEPTANTES').select('"Razon Social"').eq('RUC', clean_ruc).single().execute()
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

        # Persist Group ID within JSON for Reporting
        if recalculate_result_full:
            recalculate_result_full['group_id'] = session_data.get('group_id')
            data_to_insert['recalculate_result_json'] = json.dumps(recalculate_result_full)

        emisor_nombre_id = str(data_to_insert.get('emisor_nombre', 'SIN_NOMBRE')).replace(' ', '_').replace('.', '')
        numero_factura = str(data_to_insert.get('numero_factura', 'SIN_FACTURA'))
        fecha_propuesta = dt.datetime.now().strftime('%Y%m%d')
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
        response = supabase.table('EMISORES.ACEPTANTES').select('*').eq('RUC', ruc).single().execute()
        return response.data if response.data else None
    except Exception as e:
        print(f"[ERROR in get_signatory_data_by_ruc]: {e}")
        return None

# --- Functions for Liquidation & Disbursement Modules ---

def get_proposals_by_lote(lote_id: str, estado_filter: str = 'APROBADO') -> List[Proposal]:
    """Retrieves a list of proposals for a specific batch ID filtered by status.
    
    Args:
        lote_id: Batch identifier
        estado_filter: Status to filter by (default: 'APROBADO' for disbursement)
    """
    supabase = get_supabase_client()
    try:
        response = supabase.table('propuestas').select(
            'proposal_id, emisor_nombre, aceptante_nombre, monto_neto_factura, moneda_factura, anexo_number, contract_number, recalculate_result_json, estado'
        ).eq('identificador_lote', lote_id).eq('estado', estado_filter).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR en get_proposals_by_lote]: {e}")
        return []

def get_active_proposals_for_approval() -> List[Proposal]:
    """Fetches all proposals in ACTIVO status for approval module.
    
    Returns:
        List of proposals pending approval
    """
    supabase = get_supabase_client()
    try:
        response = supabase.table('propuestas').select('*').eq('estado', 'ACTIVO').execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR en get_active_proposals_for_approval]: {e}")
        return []

def get_approved_proposals_for_disbursement() -> List[Proposal]:
    """Fetches all proposals in APROBADO status for disbursement module.
    
    Returns:
        List of proposals pending disbursement
    """
    supabase = get_supabase_client()
    try:
        response = supabase.table('propuestas').select('*').eq('estado', 'APROBADO').execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR en get_approved_proposals_for_disbursement]: {e}")
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

def get_liquidated_proposals_by_lote(lote_id: str) -> List[Proposal]:
    """Retrieves proposals with liquidation data (EN PROCESO or LIQUIDADA states)."""
    supabase = get_supabase_client()
    try:
        # Buscar propuestas que contengan "EN PROCESO" o "LIQUIDADA" en su estado
        # Estos son los únicos estados que tienen eventos de liquidación
        response = supabase.table('propuestas').select(
            'proposal_id, emisor_nombre, aceptante_nombre, monto_neto_factura, moneda_factura, anexo_number, contract_number, recalculate_result_json, estado, numero_factura'
        ).eq('identificador_lote', lote_id).or_('estado.like.%EN PROCESO%,estado.like.%LIQUIDADA%').execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR en get_liquidated_proposals_by_lote]: {e}")
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
        response = supabase.table('authorized_users').select('*').eq('email', email).limit(1).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        # print(f"[ERROR in get_user_by_email]: {e}") # Suppress noise for checks
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

# --- Functions for Registro de Clientes Module ---

def create_emisor_deudor(data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Crea un nuevo emisor o deudor en la tabla EMISORES.ACEPTANTES.
    
    Args:
        data: Diccionario con los campos del emisor/deudor
              Campos obligatorios: RUC, Razon Social, tipo
    
    Returns:
        Tuple (success: bool, message: str)
    """
    import re
    supabase = get_supabase_client()
    try:
        # Validar campos obligatorios (TIPO es el nombre correcto en la BD)
        tipo_value = data.get('TIPO') or data.get('tipo')  # Aceptar ambos por compatibilidad
        if not data.get('RUC') or not data.get('Razon Social') or not tipo_value:
            return False, "Faltan campos obligatorios: RUC, Razon Social, TIPO"
        
        # Validar RUC (11 dígitos)
        if not re.match(r'^\d{11}$', str(data.get('RUC', ''))):
            return False, "RUC debe tener 11 dígitos numéricos"
        
        # Validar tipo
        if tipo_value not in ['EMISOR', 'ACEPTANTE']:
            return False, "TIPO debe ser 'EMISOR' o 'ACEPTANTE'"
        
        # Asegurar que se use TIPO (nombre correcto)
        if 'tipo' in data and 'TIPO' not in data:
            data['TIPO'] = data.pop('tipo')
        
        # Verificar si ya existe
        existing = supabase.table('EMISORES.ACEPTANTES').select('RUC').eq('RUC', data['RUC']).execute()
        if existing.data:
            return False, f"Ya existe un registro con RUC {data['RUC']}"
        
        # Insertar
        response = supabase.table('EMISORES.ACEPTANTES').insert(data).execute()
        return True, f"Registro creado exitosamente: {data['Razon Social']}"
    except Exception as e:
        print(f"[ERROR en create_emisor_deudor]: {e}")
        return False, f"Error al crear registro: {str(e)}"


def update_emisor_deudor(ruc: str, data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Actualiza un emisor o deudor existente.
    
    Args:
        ruc: RUC del registro a actualizar
        data: Diccionario con los campos a actualizar
    
    Returns:
        Tuple (success: bool, message: str)
    """
    supabase = get_supabase_client()
    try:
        # Verificar que existe
        existing = supabase.table('EMISORES.ACEPTANTES').select('*').eq('RUC', ruc).execute()
        if not existing.data:
            return False, f"No se encontró registro con RUC {ruc}"
        
        # Validar tipo si se está actualizando (aceptar TIPO o tipo)
        tipo_value = data.get('TIPO') or data.get('tipo')
        if tipo_value and tipo_value not in ['EMISOR', 'ACEPTANTE']:
            return False, "TIPO debe ser 'EMISOR' o 'ACEPTANTE'"
        
        # Asegurar que se use TIPO (nombre correcto)
        if 'tipo' in data and 'TIPO' not in data:
            data['TIPO'] = data.pop('tipo')
        
        # Actualizar (no permitir cambiar RUC)
        data_to_update = {k: v for k, v in data.items() if k != 'RUC'}
        response = supabase.table('EMISORES.ACEPTANTES').update(data_to_update).eq('RUC', ruc).execute()
        return True, "Registro actualizado exitosamente"
    except Exception as e:
        print(f"[ERROR en update_emisor_deudor]: {e}")
        return False, f"Error al actualizar registro: {str(e)}"


def get_all_emisores_deudores(tipo: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtiene todos los emisores/deudores, opcionalmente filtrados por tipo.
    
    Args:
        tipo: Opcional - 'EMISOR' o 'ACEPTANTE' para filtrar
    
    Returns:
        Lista de diccionarios con los registros
    """
    supabase = get_supabase_client()
    try:
        query = supabase.table('EMISORES.ACEPTANTES').select('*')
        if tipo:
            query = query.eq('tipo', tipo)
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR en get_all_emisores_deudores]: {e}")
        return []


def search_emisores_deudores(search_term: str) -> List[Dict[str, Any]]:
    """
    Busca emisores/deudores por RUC o Razón Social.
    
    Args:
        search_term: Término de búsqueda
    
    Returns:
        Lista de diccionarios con los registros encontrados
    """
    supabase = get_supabase_client()
    try:
        # Buscar por RUC o Razón Social (case insensitive)
        response = supabase.table('EMISORES.ACEPTANTES').select('*').or_(
            f'RUC.ilike.%{search_term}%,"Razon Social".ilike.%{search_term}%'
        ).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR en search_emisores_deudores]: {e}")
        return []

def get_financial_conditions(ruc: str) -> Optional[Dict[str, float]]:
    """
    Retrieves default financial conditions for a given RUC from EMISORES.ACEPTANTES.
    Returns a dict with keys matching the DB columns.
    """
    if not ruc:
        return None
    supabase = get_supabase_client()
    try:
        response = supabase.table('EMISORES.ACEPTANTES').select(
            'tasa_avance, interes_mensual_pen, interes_moratorio_pen, interes_mensual_usd, interes_moratorio_usd, comision_estructuracion_pen, comision_estructuracion_usd, comision_estructuracion_pct, comision_afiliacion_pen, comision_afiliacion_usd, dias_minimos_interes'
        ).eq('RUC', ruc).single().execute()
        return response.data if response.data else None
    except Exception as e:
        print(f"[ERROR in get_financial_conditions]: {e}")
        return None

def search_proposals_advanced(
    emisor_ruc: Optional[str] = None, 
    fecha_inicio: Optional[dt.date] = None, 
    fecha_fin: Optional[dt.date] = None,
    lote_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search proposals with multiple optional filters.
    """
    supabase = get_supabase_client()
    try:
        query = supabase.table('propuestas').select('*')
        
        if emisor_ruc:
            query = query.eq('emisor_ruc', emisor_ruc)
        
        if lote_filter:
            query = query.ilike('identificador_lote', f"%{lote_filter}%")
            
        # Execute query without date filters (DB doesn't have reliable created_at)
        response = query.order('proposal_id', desc=True).execute()
        data = response.data if response.data else []
        
        # Filter by Date in Python (using proposal_id suffix YYYYMMDD)
        filtered_data = []
        if fecha_inicio or fecha_fin:
            for item in data:
                pid = item.get('proposal_id', '')
                parts = pid.split('-')
                if len(parts) >= 3:
                    date_str = parts[-1] # Expecting YYYYMMDD
                    if len(date_str) == 8 and date_str.isdigit():
                        try:
                            item_date = dt.datetime.strptime(date_str, '%Y%m%d').date()
                            
                            if fecha_inicio and item_date < fecha_inicio:
                                continue
                            if fecha_fin and item_date > fecha_fin:
                                continue
                                
                            filtered_data.append(item)
                        except:
                            filtered_data.append(item) # Keep if cant parse? Or skip? Skip is safer for strict filter
                    else:
                        filtered_data.append(item) 
                else:
                    filtered_data.append(item)
            return filtered_data
        else:
            return data

    except Exception as e:
        print(f"[ERROR in search_proposals_advanced]: {e}")
        return []

# --- Enhanced User Management & Roles ---

def get_all_modules() -> List[Dict[str, Any]]:
    """Retrieves all modules from the 'modules' table."""
    supabase = get_supabase_client()
    try:
        response = supabase.table('modules').select('*').order('id').execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR in get_all_modules]: {e}")
        return []

def get_all_authorized_users() -> List[Dict[str, Any]]:
    """Retrieves all authorized users."""
    supabase = get_supabase_client()
    try:
        response = supabase.table('authorized_users').select('*').execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR in get_all_authorized_users]: {e}")
        return []

def get_full_permissions_matrix() -> List[Dict[str, Any]]:
    """
    Retrieves a joined Matrix of Modules -> Users per Role.
    Returns a list of dicts: 
    [
        {
            'module_id': 1, 
            'module_name': 'Registro', 
            'super_user': 'super@example.com', 
            'principal': 'boss@example.com', 
            'secondary': 'worker@example.com'
        }, ...
    ]
    Note: For this MVP, if multiple users share a role, we might only show one or comma separate.
    We will assume SINGLE assignment per role/module for the simplified Matrix UI.
    """
    modules = get_all_modules()
    users = get_all_authorized_users()
    user_map = {u['id']: u['email'] for u in users} # ID -> Email
    
    # Get all access records
    supabase = get_supabase_client()
    try:
        access_response = supabase.table('user_module_access').select('*').execute()
        access_list = access_response.data if access_response.data else []
    except Exception as e:
        print(f"[ERROR getting user_module_access]: {e}")
        access_list = []

    matrix = []
    for mod in modules:
        row = {
            'module_id': mod['id'],
            'module_name': mod['name'],
            'super_user': '',
            'principal': '',
            'secondary': ''
        }
        
        # Filter access for this module
        mod_access = [a for a in access_list if a['module_id'] == mod['id']]
        
        for acc in mod_access:
            role = acc.get('hierarchy_level', '').lower()
            uid = acc.get('user_id')
            email = user_map.get(uid, '')
            
            if role == 'super_user':
                row['super_user'] = email # Last one wins if multiple
            elif role == 'principal':
                row['principal'] = email
            elif role == 'secondary':
                row['secondary'] = email
                
        matrix.append(row)
        
    return matrix

def update_module_access_role(module_id: int, role: str, email: str) -> tuple[bool, str]:
    """
    Updates who holds a specific role (super_user, principal, secondary) for a module.
    If email is empty, removes the role assignment.
    If email is new, creates authorized_user if needed (optional) or errors.
    This Implementation assumes ONE user per role per module (replaces existing).
    """
    supabase = get_supabase_client()
    
    # 1. Resolve User
    if not email:
        # Removal logic: Delete all entries for this module + role
        try:
            # We need to find IDs to delete? Or just delete by filter
            supabase.table('user_module_access').delete().eq('module_id', module_id).eq('hierarchy_level', role).execute()
            return True, f"Rol {role} removido del módulo."
        except Exception as e:
            return False, f"Error removiendo rol: {e}"

    clean_email = email.lower().strip()
    user = get_user_by_email(clean_email)
    
    if not user:
        # Option: Auto-create user? Let's say yes for smooth UX, or block.
        # Plan said "Assign Users", implying they might need to exist. 
        # But 'authorized_users' table feels like the whitelist.
        # Let's auto-add to authorized_users if not exists?
        # User prompt: "El secundario podra entrar solo si el principal lo autoriza".
        # This implies adding them effectively authorizes them.
        new_user = add_new_authorized_user(clean_email)
        if not new_user:
            return False, f"No se pudo crear/encontrar usuario {clean_email}"
        user_id = new_user['id']
    else:
        user_id = user['id']

    # 2. Update Access
    # Strategy: Delete old user for this role/module, Insert new one.
    try:
        # Remove old holder of this role
        supabase.table('user_module_access').delete().eq('module_id', module_id).eq('hierarchy_level', role).execute()
        
        # Insert new holder
        new_access = {
            'user_id': user_id,
            'module_id': module_id,
            'hierarchy_level': role
        }
        supabase.table('user_module_access').insert(new_access).execute()
        return True, f"Usuario {clean_email} asignado como {role}."
    except Exception as e:
        print(f"[ERROR updating access]: {e}")
        return False, f"Error DB: {e}"

def check_user_access(module_name: str, user_email: str) -> bool:
    """
    Checks if a user has access to a specific module.
    Logic:
    1. If module has NO roles assigned (empty matrix for this module) -> Allow All (Default Open).
    2. If module HAS roles assigned -> Only allow if user is in [Super, Principal, Secondary].
    """
    supabase = get_supabase_client()
    try:
        # Get Module ID
        mod = get_module_by_name(module_name)
        if not mod:
            return True # Module doesn't exist? Fail open or closed? Let's say Open for dev.
        
        module_id = mod['id']
        
        # Get all access entries for this module
        # We can optimize this by query count, but let's just fetch
        access_response = supabase.table('user_module_access').select('user_id').eq('module_id', module_id).execute()
        access_list = access_response.data if access_response.data else []
        
        # RULE 1: Default Open
        if not access_list:
            return True
            
        # RULE 2: Strict Check
        if not user_email:
            return False # No email, no access if restricted
            
        user = get_user_by_email(user_email)
        if not user:
            return False
            
        user_id = user['id']
        
        # Check if user_id is in access_list
        allowed_ids = [a['user_id'] for a in access_list]
        return user_id in allowed_ids
        
    except Exception as e:
        print(f"[ERROR check_user_access]: {e}")
        return True # Fail Open to avoid locking everyone out on error? Or False? Safer is False but for this project maybe True? Let's stick to True (Open) for stability.
