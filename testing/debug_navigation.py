# Script para debuggear la navegación de carpetas
# Simula el flujo de navegación para identificar el problema

class SessionState:
    def __init__(self):
        self.current_folder_id = None
        self.current_folder_name = "Raíz"
        self.breadcrumbs = []

def navigate_to_folder(state, folder_id, folder_name):
    """Función original con el problema"""
    print(f"\n--- Navegando a: {folder_name} (ID: {folder_id}) ---")
    print(f"ANTES - current_folder_id: {state.current_folder_id}")
    print(f"ANTES - breadcrumbs: {state.breadcrumbs}")
    
    if folder_id != state.current_folder_id:
        state.breadcrumbs.append({
            'id': state.current_folder_id,
            'name': state.current_folder_name
        })
    
    state.current_folder_id = folder_id
    state.current_folder_name = folder_name
    
    print(f"DESPUÉS - current_folder_id: {state.current_folder_id}")
    print(f"DESPUÉS - breadcrumbs: {state.breadcrumbs}")

# Simular navegación en 3 niveles
state = SessionState()

print("="*60)
print("SIMULACIÓN DE NAVEGACIÓN")
print("="*60)

# Nivel 1: Raíz -> Carpeta A
navigate_to_folder(state, "folder_a_id", "Carpeta A")

# Nivel 2: Carpeta A -> Carpeta B
navigate_to_folder(state, "folder_b_id", "Carpeta B")

# Nivel 3: Carpeta B -> Carpeta C
navigate_to_folder(state, "folder_c_id", "Carpeta C")

print("\n" + "="*60)
print("ESTADO FINAL")
print("="*60)
print(f"current_folder_id: {state.current_folder_id}")
print(f"current_folder_name: {state.current_folder_name}")
print(f"breadcrumbs: {state.breadcrumbs}")

print("\n" + "="*60)
print("ANÁLISIS: ¿Cuál es el parent_id cuando creo carpeta en nivel 3?")
print("="*60)
print(f"El parent_id sería: {state.current_folder_id}")
print(f"Esto debería ser: folder_c_id ✓")
