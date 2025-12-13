import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data.supabase_repository import get_all_modules, add_module

APP_MODULES = [
    "Registro",
    "Originacion",
    "Aprobacion",
    "Desembolso",
    "Liquidacion",
    "Reporte",
    "Repositorio",
    "Calculadora",
    "Roles"
]

def populate():
    print("--- Populating Modules ---")
    current = get_all_modules()
    current_names = [m['name'] for m in current]
    print(f"Existing: {current_names}")
    
    for mod in APP_MODULES:
        if mod not in current_names:
            print(f"Adding {mod}...")
            res = add_module(mod, f"Modulo de {mod}")
            if res:
                print(f" -> Added {mod}")
            else:
                print(f" -> Failed to add {mod}")
        else:
            print(f"Skipping {mod} (already exists)")

    print("Done.")

if __name__ == "__main__":
    populate()
