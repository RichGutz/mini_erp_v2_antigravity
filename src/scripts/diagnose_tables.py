import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.data.supabase_client import get_supabase_client

def diagnose_tables():
    client = get_supabase_client()
    print("🚀 Diagnosing Table Names...\n")

    candidates = [
        "EMISORES.ACEPTANTES",
        '"EMISORES.ACEPTANTES"',
        "emisores.aceptantes",
        "aceptantes",
        "EMISORES_ACEPTANTES", 
        "EMISORES.DEUDORES"
    ]

    for table_name in candidates:
        try:
            print(f"🔎 Testing: {table_name}")
            # Try to fetch 1 row
            response = client.table(table_name).select("*", count="exact").limit(1).execute()
            
            if hasattr(response, 'error') and response.error:
                print(f"   ❌ Error: {response.error.message}")
            else:
                count = response.count if response.count is not None else "Unknown"
                length = len(response.data) if response.data else 0
                print(f"   ✅ Success! Count: {count}, Data Length: {length}")
                if length > 0:
                    print(f"   🎉 FOUND DATA in: {table_name}")
                    print(f"   First row sample: {response.data[0]}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            
    print("\n🏁 Log finished.")

if __name__ == "__main__":
    diagnose_tables()
