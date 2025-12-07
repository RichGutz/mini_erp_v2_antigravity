"""
Script para analizar la factura E001-1104
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
from src.data.supabase_client import get_supabase_client

supabase = get_supabase_client()

# Buscar la factura E001-1104
response = supabase.table('propuestas').select('*').ilike('proposal_id', '%E001-1104%').execute()

print("=" * 80)
print("ANÁLISIS DE FACTURA E001-1104")
print("=" * 80)

if response.data:
    for propuesta in response.data:
        print(f"\n📄 PROPUESTA:")
        print(f"   Proposal ID: {propuesta['proposal_id']}")
        print(f"   Número Factura: {propuesta.get('numero_factura', 'N/A')}")
        print(f"   Emisor: {propuesta.get('emisor_nombre', 'N/A')}")
        print(f"   Estado: {propuesta.get('estado', 'N/A')}")
        print(f"   Monto Neto: S/ {propuesta.get('monto_neto_factura', 0):,.2f}")
        
        print(f"\n📅 FECHAS:")
        print(f"   Fecha Emisión: {propuesta.get('fecha_emision_factura', 'N/A')}")
        print(f"   Fecha Desembolso: {propuesta.get('fecha_desembolso_factoring', 'N/A')}")
        print(f"   Fecha Pago Calculada: {propuesta.get('fecha_pago_calculada', 'N/A')}")
        print(f"   Plazo Crédito: {propuesta.get('plazo_credito_dias', 'N/A')} días")
        
        print(f"\n💰 TASAS:")
        print(f"   Tasa de Avance: {propuesta.get('tasa_de_avance', 0):.2f}%")
        print(f"   Interés Mensual: {propuesta.get('interes_mensual', 0):.2f}%")
        print(f"   Interés Moratorio: {propuesta.get('interes_moratorio', 0):.2f}%")
        
        # Obtener recalculate_result_json
        import json
        recalc = json.loads(propuesta.get('recalculate_result_json', '{}'))
        if recalc:
            calculo = recalc.get('calculo_con_tasa_encontrada', {})
            print(f"\n📊 CÁLCULOS ORIGINALES:")
            print(f"   Capital: S/ {calculo.get('capital', 0):,.2f}")
            print(f"   Interés: S/ {calculo.get('interes', 0):,.2f}")
            print(f"   IGV Interés: S/ {calculo.get('igv_interes', 0):,.2f}")
        
        # Obtener eventos de liquidación
        proposal_id = propuesta['proposal_id']
        eventos = get_liquidacion_eventos(proposal_id)
        
        if eventos:
            print(f"\n🔍 EVENTOS DE LIQUIDACIÓN ({len(eventos)} eventos):")
            for idx, evento in enumerate(eventos, 1):
                print(f"\n   Evento #{idx}:")
                print(f"      Tipo: {evento.get('tipo_evento', 'N/A')}")
                print(f"      Fecha Evento: {evento.get('fecha_evento', 'N/A')}")
                print(f"      Monto Recibido: S/ {evento.get('monto_recibido', 0):,.2f}")
                
                resultado = json.loads(evento.get('resultado_json', '{}'))
                if resultado:
                    print(f"\n      📈 RESULTADO DE LIQUIDACIÓN:")
                    print(f"         Estado: {resultado.get('estado_operacion', 'N/A')}")
                    print(f"         Días Transcurridos: {resultado.get('dias_transcurridos', 'N/A')}")
                    print(f"         Días Mora: {resultado.get('dias_mora', 'N/A')}")
                    print(f"         Capital Operación: S/ {resultado.get('capital_operacion', 0):,.2f}")
                    print(f"         Monto Pagado: S/ {resultado.get('monto_pagado', 0):,.2f}")
                    print(f"         Interés Devengado: S/ {resultado.get('interes_devengado', 0):,.2f}")
                    print(f"         IGV Devengado: S/ {resultado.get('igv_interes_devengado', 0):,.2f}")
                    print(f"         Interés Moratorio: S/ {resultado.get('interes_moratorio', 0):,.2f}")
                    print(f"         IGV Moratorio: S/ {resultado.get('igv_moratorio', 0):,.2f}")
                    print(f"         Delta Capital: S/ {resultado.get('delta_capital', 0):,.2f}")
                    print(f"         Delta Intereses: S/ {resultado.get('delta_intereses', 0):,.2f}")
                    print(f"         Delta IGV: S/ {resultado.get('delta_igv_intereses', 0):,.2f}")
                    print(f"         Saldo Global: S/ {resultado.get('saldo_global', 0):,.2f}")
        
        print("\n" + "=" * 80)
else:
    print("\n❌ NO SE ENCONTRÓ LA FACTURA E001-1104")
    print("=" * 80)
