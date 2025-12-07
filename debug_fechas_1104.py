"""
Script para verificar TODAS las fechas de la factura E001-1104
"""

import sys
import os
from datetime import datetime, date, timedelta

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.data.supabase_client import get_supabase_client

supabase = get_supabase_client()

# Buscar la factura E001-1104
response = supabase.table('propuestas').select('*').ilike('proposal_id', '%E001-1104%').execute()

print("=" * 80)
print("ANÁLISIS COMPLETO DE FECHAS - FACTURA E001-1104")
print("=" * 80)

if response.data:
    propuesta = response.data[0]
    
    print(f"\n📄 Proposal ID: {propuesta['proposal_id']}")
    print(f"\n📅 TODAS LAS FECHAS EN LA BD:")
    print(f"   fecha_emision_factura:        {propuesta.get('fecha_emision_factura')}")
    print(f"   fecha_desembolso_factoring:   {propuesta.get('fecha_desembolso_factoring')}")
    print(f"   fecha_pago_calculada:         {propuesta.get('fecha_pago_calculada')}")
    print(f"   created_at:                   {propuesta.get('created_at')}")
    print(f"   updated_at:                   {propuesta.get('updated_at')}")
    
    # Calcular qué fecha daría 22 días
    fecha_pago = date(2025, 8, 22)
    dias_sistema = 22
    fecha_desembolso_teorica = fecha_pago - timedelta(days=dias_sistema)
    
    print(f"\n🔍 CÁLCULO INVERSO:")
    print(f"   Si el sistema calculó 22 días...")
    print(f"   Y la fecha de pago es 2025-08-22...")
    print(f"   Entonces usó como desembolso: {fecha_desembolso_teorica}")
    
    # Comparar con fecha de emisión
    fecha_emision = propuesta.get('fecha_emision_factura')
    if fecha_emision:
        print(f"\n💡 COMPARACIÓN:")
        print(f"   Fecha Emisión:           {fecha_emision}")
        print(f"   Fecha Desembolso (BD):   {propuesta.get('fecha_desembolso_factoring')}")
        print(f"   Fecha calculada inversa: {fecha_desembolso_teorica}")
        
        # Calcular días desde emisión
        try:
            fecha_emision_date = datetime.strptime(fecha_emision, '%Y-%m-%d').date()
            dias_desde_emision = (fecha_pago - fecha_emision_date).days
            print(f"\n   Días desde EMISIÓN hasta PAGO: {dias_desde_emision} días")
            
            if dias_desde_emision == 22:
                print(f"   ⚠️  ¡EL SISTEMA ESTÁ USANDO LA FECHA DE EMISIÓN EN LUGAR DE DESEMBOLSO!")
        except:
            pass
    
    print("\n" + "=" * 80)
else:
    print("\n❌ NO SE ENCONTRÓ LA FACTURA")
    print("=" * 80)
