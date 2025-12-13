import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data.supabase_repository import get_all_modules, get_full_permissions_matrix

def check():
    print("--- Checking Modules ---")
    modules = get_all_modules()
    print(f"Found {len(modules)} modules.")
    for m in modules:
        print(f"- {m.get('name')}")
        
    print("\n--- Checking Matrix ---")
    matrix = get_full_permissions_matrix()
    print(f"Matrix size: {len(matrix)}")
    if matrix:
        print("Sample row:", matrix[0])

if __name__ == "__main__":
    check()
