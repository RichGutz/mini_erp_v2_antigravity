import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.data.supabase_repository import get_supabase_client

def dump_access():
    s = get_supabase_client()
    res = s.table('user_module_access').select('*').execute()
    print("--- Access Table ---")
    vals = res.data if res.data else []
    for v in vals:
        print(v)
    print(f"Total rows: {len(vals)}")

if __name__ == "__main__":
    dump_access()
