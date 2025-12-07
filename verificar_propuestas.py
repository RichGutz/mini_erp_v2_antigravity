"""
Script para verificar propuestas en Supabase
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.data.supabase_client import get_supabase_client

supabase = get_supabase_client()

# Obtener todas las propuestas
print("Obteniendo todas las propuestas...")
response = supabase.table('propuestas').select('proposal_id, identificador_lote, estado, emisor_nombre, numero_factura').execute()

if response.data:
    print(f"\nTotal de propuestas: {len(response.data)}\n")
    
    # Agrupar por lote
    lotes = {}
    for prop in response.data:
        lote = prop.get('identificador_lote', 'SIN_LOTE')
        if lote not in lotes:
            lotes[lote] = []
        lotes[lote].append(prop)
    
    print(f"Total de lotes: {len(lotes)}\n")
    print("=" * 80)
    
    for lote_id, propuestas in lotes.items():
        print(f"\nLOTE: {lote_id}")
        print(f"Propuestas: {len(propuestas)}")
        print("-" * 80)
        for p in propuestas:
            print(f"  - {p.get('emisor_nombre', 'N/A')} | {p.get('numero_factura', 'N/A')} | Estado: {p.get('estado', 'N/A')}")
            print(f"    ID: {p.get('proposal_id', 'N/A')}")
        print()
else:
    print("No se encontraron propuestas en la base de datos")
