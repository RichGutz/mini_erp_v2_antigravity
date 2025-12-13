import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.data.supabase_repository import get_all_modules

modules = get_all_modules()
print("--- MODULES IN DATABASE ---")
for m in modules:
    print(f"ID: {m['id']} | Name: '{m['name']}' | Key: '{m.get('key_name', 'N/A')}'")
