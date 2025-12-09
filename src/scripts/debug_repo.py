
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.data import supabase_repository as db

def test_ruc(ruc_to_test):
    print(f"\n[TEST] Testing supabase_repository.get_razon_social_by_ruc for RUC: {ruc_to_test}...\n")
    
    print(f"1. Testing with string RUC: '{ruc_to_test}'")
    try:
        name = db.get_razon_social_by_ruc(ruc_to_test)
        if name:
            print(f"   [SUCCESS] Found: {name}")
        else:
            print(f"   [FAILED] Returned empty string for RUC: {ruc_to_test}.")
    except Exception as e:
        print(f"   [EXCEPTION] {e}")

    # Test with numeric RUC (checking robust handling)
    try:
        ruc_int = int(ruc_to_test)
        print(f"\n2. Testing with int RUC: {ruc_int}")
        try:
            name = db.get_razon_social_by_ruc(ruc_int)
            if name:
                print(f"   [SUCCESS] Found: {name}")
            else:
                print(f"   [FAILED] Returned empty string for RUC: {ruc_to_test}.")
        except Exception as e:
            print(f"   [EXCEPTION] {e}")
    except ValueError:
        print(f"\n2. Testing with int RUC: SKIPPED (Not a number)")

if __name__ == "__main__":
    print("--- STARTING LOCAL REPRODUCTION ---")
    test_ruc("20609885026") # Emisor reported failing
    test_ruc("20380336384") # Aceptante reported failing
    print("--- END ---")
