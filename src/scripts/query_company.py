import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.data.supabase_client import get_supabase_client

def query_ruc(ruc):
    client = get_supabase_client()
    print(f"🔎 Buscando RUC: {ruc}...")
    
    found = False
    
    # 1. Try EMISORES.ACEPTANTES
    try:
        res = client.table('EMISORES.ACEPTANTES').select('*').eq('RUC', ruc).execute()
        if res.data:
            print(f"✅ Encontrado en EMISORES.ACEPTANTES:")
            print(res.data[0].get('Razon Social'))
            found = True
    except Exception as e:
        print(f"⚠️ Error en ACEPTANTES: {e}")

    # 2. Try EMISORES.DEUDORES (old name?)
    if not found:
        try:
            res = client.table('EMISORES.DEUDORES').select('*').eq('RUC', ruc).execute()
            if res.data:
                print(f"✅ Encontrado en EMISORES.DEUDORES:")
                print(res.data[0].get('Razon Social'))
                found = True
        except Exception as e:
            pass
            
    if not found:
        print("❌ No encontrado en ninguna tabla.")

if __name__ == "__main__":
    query_ruc("20609885026")
