import sys
import os

# Path setup
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.data import supabase_repository as db
from src.data.supabase_client import get_supabase_client

# Obtener estructura de la tabla EMISORES.ACEPTANTES
supabase = get_supabase_client()

print("Consultando estructura de tabla EMISORES.ACEPTANTES...")
print("="*80)

try:
    # Obtener un registro de ejemplo para ver los campos
    response = supabase.table('EMISORES.ACEPTANTES').select('*').limit(1).execute()
    
    if response.data:
        print("\nCampos disponibles en EMISORES.ACEPTANTES:")
        print("-"*80)
        for key in response.data[0].keys():
            value = response.data[0][key]
            print(f"  - {key}: {type(value).__name__} = {value}")
    else:
        print("\n❌ No hay registros en la tabla")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
