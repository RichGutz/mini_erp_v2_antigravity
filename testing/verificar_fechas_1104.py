"""
Script para verificar la fecha exacta del evento de liquidación de E001-1104
"""

import sys
import os
from datetime import datetime, date

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.data.supabase_repository import get_liquidacion_eventos
from src.data.supabase_client import get_supabase_client

supabase = get_supabase_client()

# Buscar la factura E001-1104
response = supabase.table('propuestas').select('proposal_id, fecha_desembolso_factoring').ilike('proposal_id', '%E001-1104%').execute()

print("=" * 80)
print("VERIFICACIÓN DE FECHAS - FACTURA E001-1104")
print("=" * 80)

if response.data:
    propuesta = response.data[0]
    proposal_id = propuesta['proposal_id']
    fecha_desembolso_str = propuesta['fecha_desembolso_factoring']
    
    print(f"\n📄 Proposal ID: {proposal_id}")
    print(f"📅 Fecha Desembolso (BD): {fecha_desembolso_str}")
    
    # Parsear fecha de desembolso
    try:
        if 'T' in fecha_desembolso_str:
            fecha_desembolso = datetime.fromisoformat(fecha_desembolso_str.split('T')[0]).date()
        else:
            fecha_desembolso = datetime.strptime(fecha_desembolso_str, '%Y-%m-%d').date()
        print(f"📅 Fecha Desembolso (parseada): {fecha_desembolso}")
    except:
        print(f"❌ Error parseando fecha de desembolso")
        fecha_desembolso = None
    
    # Obtener evento de liquidación
    eventos = get_liquidacion_eventos(proposal_id)
    
    if eventos:
        evento = eventos[-1]  # Último evento
        fecha_evento_str = evento.get('fecha_evento')
        
        print(f"\n🔍 EVENTO DE LIQUIDACIÓN:")
        print(f"   Fecha Evento (BD): {fecha_evento_str}")
        
        # Parsear fecha de evento
        try:
            if 'T' in fecha_evento_str:
                fecha_evento = datetime.fromisoformat(fecha_evento_str.replace('Z', '+00:00')).date()
            else:
                fecha_evento = datetime.strptime(fecha_evento_str, '%Y-%m-%d').date()
            print(f"   Fecha Evento (parseada): {fecha_evento}")
        except Exception as e:
            print(f"   ❌ Error parseando fecha de evento: {e}")
            fecha_evento = None
        
        # Calcular días reales
        if fecha_desembolso and fecha_evento:
            dias_reales = (fecha_evento - fecha_desembolso).days
            print(f"\n📊 CÁLCULO DE DÍAS:")
            print(f"   Fecha Desembolso: {fecha_desembolso}")
            print(f"   Fecha Pago Real:  {fecha_evento}")
            print(f"   Días Reales:      {dias_reales} días")
            
            # Comparar con lo que dice el sistema
            import json
            resultado = json.loads(evento.get('resultado_json', '{}'))
            dias_sistema = resultado.get('dias_transcurridos', 0)
            print(f"   Días Sistema:     {dias_sistema} días")
            
            if dias_reales != dias_sistema:
                print(f"\n   ❌ DISCREPANCIA DETECTADA:")
                print(f"      Diferencia: {abs(dias_reales - dias_sistema)} días")
                print(f"      El sistema calculó {dias_sistema} días cuando deberían ser {dias_reales} días")
            else:
                print(f"\n   ✅ Los días coinciden")
        
        print("\n" + "=" * 80)
else:
    print("\n❌ NO SE ENCONTRÓ LA FACTURA")
    print("=" * 80)
