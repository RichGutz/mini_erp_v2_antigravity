import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.data.supabase_repository import get_supabase_client

supabase = get_supabase_client()

print("--- PERMISSIONS DUMP ---")
# Get all modules
modules = supabase.table('modules').select('*').execute().data
# Get all access records with user emails (join logic simulated)
access_records = supabase.table('user_module_access').select('*, authorized_users(email), modules(name)').execute().data

# Group by Module
module_map = {m['id']: m['name'] for m in modules}
module_roles = {m['name']: [] for m in modules}

for record in access_records:
    mod_name = record['modules']['name'] if record.get('modules') else 'Unknown'
    user_email = record['authorized_users']['email'] if record.get('authorized_users') else 'Unknown'
    role = record['role']
    module_roles[mod_name].append(f"{user_email} ({role})")

for mod_name, roles in module_roles.items():
    print(f"Module: {mod_name}")
    if not roles:
        print("  [WARNING] NO ROLES ASSIGNED (Default Open)")
    else:
        for r in roles:
            print(f"  - {r}")
