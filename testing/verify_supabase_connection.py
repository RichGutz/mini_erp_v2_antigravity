from src.data.supabase_client import get_supabase_client
import os

print("--- Verificando conexión a Supabase ---")

# Verificar si las variables de entorno están cargadas (deberían cargarse al importar get_supabase_client -> load_dotenv)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if url:
    print(f"SUPABASE_URL encontrada: {url[:10]}...")
else:
    print("ERROR: SUPABASE_URL no encontrada en variables de entorno.")

if key:
    print(f"SUPABASE_KEY encontrada: {key[:10]}...")
else:
    print("ERROR: SUPABASE_KEY no encontrada en variables de entorno.")

try:
    client = get_supabase_client()
    print("SUCCESS: Cliente Supabase inicializado correctamente.")
except Exception as e:
    print(f"FAILURE: Error al inicializar cliente: {e}")
