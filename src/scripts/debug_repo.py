import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.data import supabase_repository as db

def test_repo_function():
    print("🚀 Testing supabase_repository.get_razon_social_by_ruc...\n")
    
    # Known RUC from previous successful test
    test_ruc = "20603718489" 
    
    print(f"1. Testing with string RUC: '{test_ruc}'")
    try:
        name = db.get_razon_social_by_ruc(test_ruc)
        if name:
            print(f"   ✅ Success! Found: {name}")
        else:
            print(f"   ❌ Failed. Returned empty string.")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

    # Test with numeric RUC (if python treats it as int)
    print(f"\n2. Testing with int RUC: {int(test_ruc)}")
    try:
        name = db.get_razon_social_by_ruc(int(test_ruc))
        if name:
            print(f"   ✅ Success! Found: {name}")
        else:
            print(f"   ❌ Failed. Returned empty string.")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        
    print(f"\n3. Testing with Non-Existent RUC: '12345678901'")
    try:
        name = db.get_razon_social_by_ruc("12345678901")
        if name == "":
            print(f"   ✅ Success! Correctly returned empty string for missing user.")
        else:
            print(f"   ⚠️ Unexpected result: {name}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_repo_function()
