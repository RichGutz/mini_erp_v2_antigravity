import pandas as pd

# Leer el archivo Excel
archivo = r'C:\Users\rguti\mini_erp_v2_antigravity\pruebas\06.12.2025\CASOS.LIQUIDACIONES.TESTING.TOOL.xlsx'

try:
    # Leer todas las hojas
    excel_file = pd.ExcelFile(archivo)
    print(f"Hojas disponibles: {excel_file.sheet_names}\n")
    
    # Leer cada hoja
    for sheet_name in excel_file.sheet_names:
        print(f"\n{'='*80}")
        print(f"HOJA: {sheet_name}")
        print(f"{'='*80}\n")
        
        df = pd.read_excel(archivo, sheet_name=sheet_name)
        print(f"Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
        print(f"\nColumnas: {list(df.columns)}\n")
        print(df.to_string())
        print("\n")
except Exception as e:
    print(f"Error: {e}")
