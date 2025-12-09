import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.data.supabase_client import get_supabase_client

def insert_trans_star():
    try:
        client = get_supabase_client()
        print("🚀 Attempting to Insert 'TRANS STAR HERMANOS SAC'...")

        data = {
            "TIPO": "EMISOR",
            "RUC": "20609885026",
            "Razon Social": "TRANS STAR HERMANOS SAC",
            "Depositario 1": "REBECA CASTILLO CHANG DE LUCHO",
            "DNI Depositario 1": "15726018",
            "Garante/Fiador solidario 1": "REBECA CASTILLO CHANG DE LUCHO",
            "DNI Garante/Fiador solidario 1": "15726018",
            "Institucion Financiera": "Banco de Crédito del Perú (BCP)",
            "Numero de Cuenta PEN": "30303030303030",
            "Numero de CCI PEN": "40404040040440",
            # Explicitly providing ID=2 as per user input, though usually auto-increment
            "id": 2 
        }

        # 1. Try to Select first (Diagnostic)
        print("   🔎 Checking if it exists first...")
        existing = client.table('EMISORES.ACEPTANTES').select('*').eq('RUC', '20609885026').execute()
        
        if existing.data:
            print(f"   ⚠️ RECORD FOUND! User was right. Data: {existing.data}")
            print("   (This means my previous diagnostic was wrong or RLS was blocking).")
        else:
            print("   ❌ Record NOT found via Select. Proceeding to Insert...")
            
            # 2. Insert
            response = client.table('EMISORES.ACEPTANTES').insert(data).execute()
            print("   ✅ INSERT SUCCESSFUL!")
            print(f"   Data: {response.data}")

    except Exception as e:
        print(f"\n❌ Error during operation: {e}")
        # If error is about Duplicate Key, that also proves user right
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
             print("   ✅ CONCLUSION: The record ALREADY EXISTS (Duplicate Key Error). User was correct.")

if __name__ == "__main__":
    insert_trans_star()
