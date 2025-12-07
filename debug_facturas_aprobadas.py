import sys
import os

# Path setup
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.data import supabase_repository as db

# Probar la función
print("Probando get_approved_proposals_for_disbursement()...")
facturas = db.get_approved_proposals_for_disbursement()

print(f"\nTotal de facturas encontradas: {len(facturas)}")

if facturas:
    print("\nFacturas APROBADAS encontradas:")
    for f in facturas:
        print(f"  - {f.get('proposal_id')} | Estado: {f.get('estado')} | Emisor: {f.get('emisor_nombre')}")
else:
    print("\n❌ No se encontraron facturas APROBADAS")
    
# Probar también con query directa
print("\n" + "="*80)
print("Probando query directa a Supabase...")

from src.data.supabase_client import get_supabase_client
supabase = get_supabase_client()

try:
    response = supabase.table('propuestas').select('proposal_id, estado, emisor_nombre').eq('estado', 'APROBADO').execute()
    print(f"\nResultado de query directa: {len(response.data) if response.data else 0} facturas")
    
    if response.data:
        print("\nFacturas encontradas:")
        for f in response.data:
            print(f"  - {f.get('proposal_id')} | Estado: {f.get('estado')} | Emisor: {f.get('emisor_nombre')}")
    else:
        print("\n❌ Query directa tampoco encontró facturas")
        
except Exception as e:
    print(f"\n❌ Error en query directa: {e}")
