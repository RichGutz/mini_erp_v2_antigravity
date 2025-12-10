"""
Script para verificar la fecha de pago de la factura E001-1086 - TRANS STAR HERMANOS SAC
"""

import sys
import os
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.data.supabase_repository import (
    get_proposal_details_by_id,
    get_liquidacion_eventos
)

# Buscar la propuesta que contenga E001-1086
proposal_id_pattern = "TRANS_STAR_HERMANOS_SAC-E001-1086"

# Primero, necesitamos encontrar el proposal_id exacto
from src.data.supabase_client import get_supabase_client

supabase = get_supabase_client()

# Buscar propuestas que contengan el patrón
response = supabase.table('propuestas').select('proposal_id, numero_factura, emisor_nombre, fecha_pago_calculada, estado').ilike('proposal_id', f'%{proposal_id_pattern}%').execute()

print("=" * 80)
print("BÚSQUEDA DE FACTURA E001-1086 - TRANS STAR HERMANOS SAC")
print("=" * 80)

if response.data:
    for propuesta in response.data:
        print(f"\n📄 PROPUESTA ENCONTRADA:")
        print(f"   Proposal ID: {propuesta['proposal_id']}")
        print(f"   Número Factura: {propuesta.get('numero_factura', 'N/A')}")
        print(f"   Emisor: {propuesta.get('emisor_nombre', 'N/A')}")
        print(f"   Estado: {propuesta.get('estado', 'N/A')}")
        print(f"   Fecha Pago Calculada (BD): {propuesta.get('fecha_pago_calculada', 'N/A')}")
        
        # Obtener detalles completos
        proposal_id = propuesta['proposal_id']
        detalles = get_proposal_details_by_id(proposal_id)
        
        if detalles:
            print(f"\n📋 DETALLES COMPLETOS:")
            print(f"   Fecha Emisión: {detalles.get('fecha_emision_factura', 'N/A')}")
            print(f"   Fecha Desembolso: {detalles.get('fecha_desembolso_factoring', 'N/A')}")
            print(f"   Fecha Pago Calculada: {detalles.get('fecha_pago_calculada', 'N/A')}")
            print(f"   Plazo Crédito: {detalles.get('plazo_credito_dias', 'N/A')} días")
        
        # Obtener eventos de liquidación
        eventos = get_liquidacion_eventos(proposal_id)
        
        if eventos:
            print(f"\n🔍 EVENTOS DE LIQUIDACIÓN ({len(eventos)} eventos):")
            for idx, evento in enumerate(eventos, 1):
                print(f"\n   Evento #{idx}:")
                print(f"      Tipo: {evento.get('tipo_evento', 'N/A')}")
                print(f"      Fecha Evento: {evento.get('fecha_evento', 'N/A')}")
                print(f"      Monto Recibido: {evento.get('monto_recibido', 'N/A')}")
                print(f"      Días Diferencia: {evento.get('dias_diferencia', 'N/A')}")
                print(f"      Orden: {evento.get('orden_evento', 'N/A')}")
                
                # Parsear resultado_json si existe
                import json
                resultado = json.loads(evento.get('resultado_json', '{}'))
                if resultado:
                    print(f"      Estado Operación: {resultado.get('estado_operacion', 'N/A')}")
                    print(f"      Días Transcurridos: {resultado.get('dias_transcurridos', 'N/A')}")
                    print(f"      Días Mora: {resultado.get('dias_mora', 'N/A')}")
        else:
            print(f"\n⚠️  NO SE ENCONTRARON EVENTOS DE LIQUIDACIÓN")
        
        print("\n" + "=" * 80)
else:
    print("\n❌ NO SE ENCONTRÓ LA FACTURA")
    print("=" * 80)
