import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.data.supabase_repository import get_all_modules, update_module_access_role

email = "rgutil@gmail.com"
print(f"--- STARTING SECURE SETUP FOR {email} ---")

try:
    modules = get_all_modules()
    print(f"Found {len(modules)} modules in database.")

    for m in modules:
        print(f"Assigning 'super_user' role for module: {m['name']} (ID: {m['id']})...")
        success, msg = update_module_access_role(m['id'], 'super_user', email)
        if success:
            print(f"  ✅ Success: {msg}")
        else:
            print(f"  ❌ Error: {msg}")

    print("--- SETUP COMPLETE ---")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
