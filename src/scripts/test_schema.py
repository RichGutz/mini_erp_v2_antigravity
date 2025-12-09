import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.data.supabase_client import get_supabase_client

def test_schema_access():
    client = get_supabase_client()
    print("Testing Schema Access...\n")

    try:
        # Test 1: Using schema().from_()
        print("Test 1: Querying: schema('EMISORES').from_('ACEPTANTES')")
        try:
            response = client.schema('EMISORES').from_('ACEPTANTES').select("*", count="exact").limit(1).execute()
            if hasattr(response, 'error') and response.error:
                print(f"   Error: {response.error}")
            else:
                length = len(response.data) if response.data else 0
                print(f"   Success! Data Length: {length}")
                if length > 0:
                    print(f"   First row sample: {response.data[0]}")
        except Exception as e:
            print(f"   Test 1 Failed with Exception: {e}")

        print("\n--------------------------------\n")

        # Test 2: Using table('EMISORES.ACEPTANTES') - Mimicking app usage
        print("Test 2: Querying: table('EMISORES.ACEPTANTES')")
        try:
            response = client.table('EMISORES.ACEPTANTES').select("*", count="exact").limit(1).execute()
            if hasattr(response, 'error') and response.error:
                print(f"   Error: {response.error}")
            else:
                length = len(response.data) if response.data else 0
                print(f"   Success! Data Length: {length}")
                if length > 0:
                    print(f"   First row sample: {response.data[0]}")
        except Exception as e:
            print(f"   Test 2 Failed with Exception: {e}")

        print("\n--------------------------------\n")

        # Test 3: Using table('propuestas')
        print("Test 3: Querying: table('propuestas')")
        try:
            response = client.table('propuestas').select("*", count="exact").limit(1).execute()
            if hasattr(response, 'error') and response.error:
                print(f"   Error: {response.error}")
            else:
                length = len(response.data) if response.data else 0
                print(f"   Success! Data Length: {length}")
                if length > 0:
                    print(f"   First row sample (propuestas): {response.data[0].get('proposal_id', 'N/A')}")
        except Exception as e:
            print(f"   Test 3 Failed with Exception: {e}")

    except Exception as e:
        print(f"   Exception: {e}")

if __name__ == "__main__":
    test_schema_access()
