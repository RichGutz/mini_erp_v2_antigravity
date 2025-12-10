"""
Script para actualizar la fecha del evento de liquidación de E001-1104
De 2025-08-22 a 2025-09-05
"""

import sys
import os
from datetime import datetime, date

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.data.supabase_repository import get_liquidacion_eventos, get_liquidacion_resumen
from src.data.supabase_client import get_supabase_client

supabase = get_supabase_client()

# Buscar la factura E001-1104
response = supabase.table('propuestas').select('proposal_id').ilike('proposal_id', '%E001-1104%').execute()

print("=" * 80)
print("ACTUALIZACIÓN DE FECHA - FACTURA E001-1104")
print("=" * 80)

if response.data:
    proposal_id = response.data[0]['proposal_id']
    print(f"\n📄 Proposal ID: {proposal_id}")
    
    # Obtener el resumen de liquidación
    resumen = get_liquidacion_resumen(proposal_id)
    
    if resumen:
        resumen_id = resumen['id']
        print(f"📊 Liquidación Resumen ID: {resumen_id}")
        
        # Obtener eventos
        eventos = get_liquidacion_eventos(proposal_id)
        
        if eventos:
            evento = eventos[-1]  # Último evento
            evento_id = evento['id']
            fecha_actual = evento.get('fecha_evento')
            
            print(f"\n🔍 EVENTO ACTUAL:")
            print(f"   ID: {evento_id}")
            print(f"   Fecha Actual: {fecha_actual}")
            
            # Nueva fecha
            nueva_fecha = "2025-09-05T00:00:00+00:00"
            
            print(f"\n🔄 ACTUALIZANDO:")
            print(f"   Fecha Anterior: {fecha_actual}")
            print(f"   Fecha Nueva:    {nueva_fecha}")
            
            # Actualizar en Supabase
            try:
                update_response = supabase.table('liquidacion_eventos').update({
                    'fecha_evento': nueva_fecha
                }).eq('id', evento_id).execute()
                
                if update_response.data:
                    print(f"\n✅ FECHA ACTUALIZADA EXITOSAMENTE")
                    print(f"   Evento ID: {evento_id}")
                    print(f"   Nueva fecha: {nueva_fecha}")
                else:
                    print(f"\n❌ ERROR AL ACTUALIZAR")
                    print(f"   Response: {update_response}")
            except Exception as e:
                print(f"\n❌ ERROR: {e}")
        else:
            print(f"\n⚠️  NO SE ENCONTRARON EVENTOS DE LIQUIDACIÓN")
    else:
        print(f"\n⚠️  NO SE ENCONTRÓ RESUMEN DE LIQUIDACIÓN")
    
    print("\n" + "=" * 80)
else:
    print("\n❌ NO SE ENCONTRÓ LA FACTURA")
    print("=" * 80)
