"""
Script para verificar las fechas de las 3 facturas del lote
"""

import sys
import os
from datetime import datetime, date

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.data.supabase_repository import get_liquidacion_eventos
from src.data.supabase_client import get_supabase_client

supabase = get_supabase_client()

# Buscar las 3 facturas
facturas = ['E001-1086', 'E001-1102', 'E001-1104']

print("=" * 80)
print("VERIFICACIÓN DE FECHAS - TODAS LAS FACTURAS DEL LOTE")
print("=" * 80)

for num_factura in facturas:
    response = supabase.table('propuestas').select('proposal_id, numero_factura, fecha_desembolso_factoring').ilike('proposal_id', f'%{num_factura}%').execute()
    
    if response.data:
        propuesta = response.data[0]
        proposal_id = propuesta['proposal_id']
        fecha_desembolso = propuesta['fecha_desembolso_factoring']
        
        print(f"\n{'='*80}")
        print(f"📄 FACTURA: {num_factura}")
        print(f"{'='*80}")
        print(f"   Proposal ID: {proposal_id}")
        print(f"   Fecha Desembolso: {fecha_desembolso}")
        
        # Obtener eventos de liquidación
        eventos = get_liquidacion_eventos(proposal_id)
        
        if eventos:
            evento = eventos[-1]
            fecha_evento = evento.get('fecha_evento')
            monto_recibido = evento.get('monto_recibido', 0)
            
            print(f"\n   💰 EVENTO DE LIQUIDACIÓN:")
            print(f"      Fecha Pago (BD): {fecha_evento}")
            print(f"      Monto Recibido: S/ {monto_recibido:,.2f}")
            
            # Calcular días
            try:
                if 'T' in fecha_desembolso:
                    fecha_desemb_date = datetime.fromisoformat(fecha_desembolso.split('T')[0]).date()
                else:
                    fecha_desemb_date = datetime.strptime(fecha_desembolso, '%Y-%m-%d').date()
                
                if 'T' in fecha_evento:
                    fecha_pago_date = datetime.fromisoformat(fecha_evento.replace('Z', '+00:00')).date()
                else:
                    fecha_pago_date = datetime.strptime(fecha_evento, '%Y-%m-%d').date()
                
                dias_calculados = (fecha_pago_date - fecha_desemb_date).days
                
                print(f"\n   📊 CÁLCULO:")
                print(f"      {fecha_pago_date} - {fecha_desemb_date} = {dias_calculados} días")
                
                # Obtener días del sistema
                import json
                resultado = json.loads(evento.get('resultado_json', '{}'))
                dias_sistema = resultado.get('dias_transcurridos', 0)
                
                print(f"      Días Sistema: {dias_sistema} días")
                
                if dias_calculados == dias_sistema:
                    print(f"      ✅ FECHAS CORRECTAS")
                else:
                    print(f"      ❌ DISCREPANCIA: {abs(dias_calculados - dias_sistema)} días de diferencia")
                    
            except Exception as e:
                print(f"      ⚠️  Error calculando días: {e}")
        else:
            print(f"\n   ⚠️  NO SE ENCONTRARON EVENTOS DE LIQUIDACIÓN")

print(f"\n{'='*80}")
print("FIN DE VERIFICACIÓN")
print("=" * 80)
