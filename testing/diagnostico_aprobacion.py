import sys
import os

# Path setup
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from src.data import supabase_repository as db

print("=== DIAGNÓSTICO: Módulo de Aprobación ===\n")

# 1. Verificar todas las propuestas en la base de datos
print("1. Consultando TODAS las propuestas...")
supabase = db.get_supabase_client()
response = supabase.table('propuestas').select('*').execute()
all_proposals = response.data if response.data else []

print(f"   Total de propuestas en BD: {len(all_proposals)}\n")

if all_proposals:
    print("2. Detalles de cada propuesta:")
    for i, prop in enumerate(all_proposals, 1):
        print(f"\n   Propuesta {i}:")
        print(f"   - proposal_id: {prop.get('proposal_id')}")
        print(f"   - numero_factura: {prop.get('numero_factura')}")
        print(f"   - emisor_nombre: {prop.get('emisor_nombre')}")
        print(f"   - estado: {prop.get('estado')}")
        print(f"   - estado_propuesta: {prop.get('estado_propuesta')}")
        print(f"   - status: {prop.get('status')}")
        print(f"   - created_at: {prop.get('created_at')}")

# 3. Probar la función get_active_proposals_for_approval
print("\n\n3. Probando get_active_proposals_for_approval()...")
active_proposals = db.get_active_proposals_for_approval()
print(f"   Propuestas retornadas: {len(active_proposals)}")

if active_proposals:
    for prop in active_proposals:
        print(f"   - {prop.get('proposal_id')}: {prop.get('numero_factura')}")
else:
    print("   ❌ No se encontraron propuestas activas")

# 4. Buscar por diferentes variantes de estado
print("\n\n4. Buscando por diferentes campos de estado...")
for field in ['estado', 'estado_propuesta', 'status']:
    try:
        response = supabase.table('propuestas').select('*').eq(field, 'ACTIVO').execute()
        count = len(response.data) if response.data else 0
        print(f"   - Campo '{field}' = 'ACTIVO': {count} resultados")
    except Exception as e:
        print(f"   - Campo '{field}': Error - {e}")

print("\n=== FIN DEL DIAGNÓSTICO ===")
