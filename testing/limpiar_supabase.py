"""
Script para limpiar tablas operacionales de Supabase
Borra solo los datos generados en el proceso (propuestas, desembolsos, liquidaciones)
NO borra tablas de configuración (usuarios, módulos, catálogo de empresas)

USO:
    python limpiar_datos_supabase.py
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.supabase_client import get_supabase_client

def limpiar_tablas_operacionales():
    """
    Limpia todas las tablas operacionales de Supabase
    """
    supabase = get_supabase_client()
    
    # Tablas operacionales a limpiar (en orden para respetar foreign keys)
    tablas_operacionales = [
        'liquidacion_eventos',      # Primero los eventos de liquidación
        'liquidaciones_resumen',    # Luego el resumen de liquidaciones
        'desembolso_eventos',       # Eventos de desembolso
        'desembolsos_resumen',      # Resumen de desembolsos
        'auditoria_eventos',        # Eventos de auditoría
        'propuestas'                # Finalmente las propuestas (padre de todo)
    ]
    
    print("=" * 70)
    print("LIMPIEZA DE TABLAS OPERACIONALES DE SUPABASE")
    print("=" * 70)
    print()
    print("⚠️  ADVERTENCIA: Este script borrará TODOS los datos operacionales.")
    print()
    print("Tablas que SE BORRARÁN:")
    for tabla in tablas_operacionales:
        print(f"  ✅ {tabla}")
    
    print()
    print("Tablas que NO SE BORRARÁN (configuración):")
    print("  ❌ authorized_users")
    print("  ❌ modules")
    print("  ❌ user_module_access")
    print("  ❌ EMISORES.ACEPTANTES")
    print()
    
    confirmacion = input("¿Estás seguro de continuar? (escribe 'SI' para confirmar): ")
    
    if confirmacion != "SI":
        print("\n❌ Operación cancelada por el usuario.")
        return
    
    print("\n🔄 Iniciando limpieza...\n")
    
    total_eliminados = 0
    
    for tabla in tablas_operacionales:
        try:
            print(f"Limpiando tabla: {tabla}...", end=" ")
            
            # Obtener todos los registros
            response = supabase.table(tabla).select('*').execute()
            count = len(response.data) if response.data else 0
            
            if count == 0:
                print(f"✓ Ya está vacía (0 registros)")
                continue
            
            # Borrar todos los registros
            if tabla == 'propuestas':
                for record in response.data:
                    supabase.table(tabla).delete().eq('proposal_id', record['proposal_id']).execute()
            else:
                for record in response.data:
                    supabase.table(tabla).delete().eq('id', record['id']).execute()
            
            total_eliminados += count
            print(f"✓ {count} registros eliminados")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            continue
    
    print()
    print("=" * 70)
    print(f"✅ Limpieza completada. Total de registros eliminados: {total_eliminados}")
    print("=" * 70)
    print()
    print("Las siguientes tablas permanecen intactas:")
    print("  - authorized_users (usuarios autorizados)")
    print("  - modules (módulos del sistema)")
    print("  - user_module_access (permisos de acceso)")
    print("  - EMISORES.ACEPTANTES (catálogo de empresas)")
    print()


if __name__ == "__main__":
    try:
        limpiar_tablas_operacionales()
    except KeyboardInterrupt:
        print("\n\n❌ Operación interrumpida por el usuario.")
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
