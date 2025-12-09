import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.data.supabase_client import get_supabase_client

def test_connection():
    try:
        print("1. Initializing Supabase Client...")
        supabase = get_supabase_client()
        print("   ✅ Client Initialized.")
        
        print("\n2. Testing RLS Bypass (Querying 'EMISORES.ACEPTANTES')...")
        # Query just one row to test read access
        response = supabase.table('EMISORES.ACEPTANTES').select("count", count="exact").execute()
        
        print(f"   ✅ Query Successful!")
        print(f"   📊 Row Count: {response.count}")
        print("   INFO: If Row Count > 0, Service Role Key is working and bypassing RLS.")
        
    except Exception as e:
        print(f"\n❌ ERRORED: {e}")
        print("   POSSIBLE CAUSES:")
        print("   - Using Anon Key instead of Service Role Key (RLS blocking).")
        print("   - Secrets not configured correctly.")

if __name__ == "__main__":
    test_connection()
