
import sys
import os
import pdfplumber
import re
import datetime

pdf_path = r"C:\Users\rguti\mini_erp_v2_antigravity\pruebas\3.12.25\PDF-DOC-E001-22820602691846.pdf"

def extract_due_date(text):
    # Pattern for "Información del crédito" table
    # Looks for lines starting with a number (quota), then a date, then an amount
    # Example: 1 24/04/2025 1,318.80
    credit_info_match = re.search(r'Informaci[oó]n del cr[eé]dito', text, re.IGNORECASE)
    if credit_info_match:
        # Search for date in the lines following "Información del crédito"
        # We look for the pattern: integer date amount
        # \b\d+\s+(\d{2}/\d{2}/\d{4})\s+
        match = re.search(r'\b\d+\s+(\d{2}/\d{2}/\d{4})\s+', text[credit_info_match.start():])
        if match:
            return match.group(1)
            
    # Fallback: Look for "Fecha de Vencimiento"
    venc_match = re.search(r'Fecha de Vencimiento\s*:?\s*(\d{2}[-/]\d{2}[-/]\d{4})', text, re.IGNORECASE)
    if venc_match:
        return venc_match.group(1)
        
    return None

try:
    print(f"Extracting due date from {pdf_path}...")
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
            
    normalized_text = re.sub(r'\s+', ' ', full_text).strip()
    due_date = extract_due_date(normalized_text)
    print(f"Due Date Found: {due_date}")
    
except Exception as e:
    print(f"Error: {e}")
