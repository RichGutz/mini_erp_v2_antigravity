import pdfplumber
import re
import datetime

def text_to_float(text_number: str) -> float:
    """
    Converts a Spanish number in text format to a float.
    Handles integers, decimals, and common currency phrasing.
    """
    text_number = text_number.upper().strip()

    # Handle fractional part like "Y 40/100" or "CON 40/100"
    fractional_part = 0.0
    fraction_match = re.search(r'(Y|CON)\s*(\d+)/100', text_number)
    if fraction_match:
        try:
            fractional_part = float(fraction_match.group(2)) / 100
            text_number = text_number[:fraction_match.start()].strip()
        except (ValueError, IndexError):
            fractional_part = 0.0

    num_map = {
        "CERO": 0, "UN": 1, "UNO": 1, "DOS": 2, "TRES": 3, "CUATRO": 4, "CINCO": 5,
        "SEIS": 6, "SIETE": 7, "OCHO": 8, "NUEVE": 9, "DIEZ": 10,
        "ONCE": 11, "DOCE": 12, "TRECE": 13, "CATORCE": 14, "QUINCE": 15,
        "DIECISEIS": 16, "DIECISIETE": 17, "DIECIOCHO": 18, "DIECINUEVE": 19,
        "VEINTE": 20, "VEINTIUN": 21, "VEINTIUNO": 21, "VEINTIDOS": 22, "VEINTITRES": 23,
        "VEINTICUATRO": 24, "VEINTICINCO": 25, "VEINTISEIS": 26, "VEINTISIETE": 27,
        "VEINTIOCHO": 28, "VEINTINUEVE": 29,
        "TREINTA": 30, "CUARENTA": 40, "CINCUENTA": 50, "SESENTA": 60, "SETENTA": 70,
        "OCHENTA": 80, "NOVENTA": 90,
        "CIEN": 100, "CIENTO": 100, "DOSCIENTOS": 200, "TRESCIENTOS": 300,
        "CUATROCIENTOS": 400, "QUINIENTOS": 500, "SEISCIENTOS": 600,
        "SETECIENTOS": 700, "OCHOCIENTOS": 800, "NOVECIENTOS": 900
    }
    
    text_number = re.sub(r'\s+Y\s+', ' ', text_number)

    words = text_number.split()
    total_sum = 0
    current_number = 0

    for word in words:
        if word in num_map:
            current_number += num_map[word]
        elif word == "MIL":
            if current_number == 0:
                current_number = 1
            total_sum += current_number * 1000
            current_number = 0
        elif word in ["MILLON", "MILLONES"]:
            if current_number == 0:
                current_number = 1
            total_sum += current_number * 1000000
            current_number = 0
            
    total_sum += current_number
    return float(total_sum + fractional_part)

def extract_fields_from_pdf(pdf_path: str) -> dict:
    """
    Extracts key fields from a PDF invoice based on updated user requirements.
    Detraction logic has been removed.
    """
    extracted_data = {}
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
            
        normalized_text = re.sub(r'\s+', ' ', full_text).strip()

        # --- RUC Data ---
        all_rucs = re.findall(r'\b(20\d{9}|10\d{9})\b', normalized_text)
        if all_rucs:
            extracted_data['emisor_ruc'] = all_rucs[0]
            if len(all_rucs) > 1:
                extracted_data['aceptante_ruc'] = all_rucs[1]

        # --- Invoice ID ---
        invoice_match = re.search(r'\b([EF][A-Z0-9]{3}-\d{1,8})\b', normalized_text)
        if invoice_match:
            extracted_data['invoice_id'] = invoice_match.group(1)

        # --- Emission Date ---
        # Regex to find dates in DD/MM/YYYY, DD-MM-YYYY, or YYYY-MM-DD formats.
        # It prioritizes dates following "Fecha de Emisión".
        date_match = re.search(r'Fecha de Emisi[oó]n\s*:?\s*(\d{2}[-/]\d{2}[-/]\d{4}|\d{4}[-/]\d{2}[-/]\d{2})', normalized_text, re.IGNORECASE)
        if not date_match:
            # If not found, search for any date in the document with the specified formats.
            date_match = re.search(r'\b(\d{2}[-/]\d{2}[-/]\d{4}|\d{4}[-/]\d{2}[-/]\d{2})\b', normalized_text)

        if date_match:
            date_str = date_match.group(1).replace('/', '-')
            try:
                # Attempt to parse as YYYY-MM-DD first
                dt_object = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                # If successful, format to DD-MM-YYYY
                extracted_data['fecha_emision'] = dt_object.strftime('%d-%m-%Y')
            except ValueError:
                # If it fails, it's likely already in DD-MM-YYYY, so just store it.
                extracted_data['fecha_emision'] = date_str

        # --- Currency ---
        son_line_match = re.search(r'SON:.*?((?:SOLES|PEN)|(?:DOLAR|DOLARES|USD|US\$))', normalized_text, re.IGNORECASE)
        if son_line_match:
            currency_name = son_line_match.group(1).upper()
            if "SOL" in currency_name or "PEN" in currency_name:
                extracted_data['moneda'] = "PEN"
            elif "DOLAR" in currency_name or "USD" in currency_name:
                extracted_data['moneda'] = "USD"
        else:
            if re.search(r'(S/|SOLES|PEN)', normalized_text, re.IGNORECASE):
                 extracted_data['moneda'] = "PEN"
            elif re.search(r'(\$|USD|DOLARES|DOLAR AMERICANO)', normalized_text, re.IGNORECASE):
                 extracted_data['moneda'] = "USD"

        # --- Total Amount ---
        total_match_numeric = re.search(r'Importe Total\s*:\s*(?:S/|\$)?\s*([\d,]+\.\d{2})', normalized_text, re.IGNORECASE)
        if total_match_numeric:
            total_amount_str = total_match_numeric.group(1).replace(',', '')
            extracted_data['monto_total'] = float(total_amount_str)
        else:
            son_match = re.search(r'SON:\s*(.*?)(?:SOLES|D[OÓ]LAR|USD|PEN)', normalized_text, re.IGNORECASE)
            if son_match:
                text_amount = son_match.group(1).strip()
                extracted_data['monto_total'] = text_to_float(text_amount)

        # --- Net Amount ---
        net_amount_match = re.search(r'(Monto neto pendiente de pago|SUBTOTAL VENTA)\s*:\s*(?:S/|\$)?\s*([\d,]+\.\d{2})', normalized_text, re.IGNORECASE)
        if net_amount_match:
            net_amount_str = net_amount_match.group(2).replace(',', '')
            extracted_data['monto_neto'] = float(net_amount_str)

        # --- Final Logic for Amounts (Simplified) ---
        # If monto_neto is not found, it defaults to monto_total.
        if extracted_data.get('monto_total') and not extracted_data.get('monto_neto'):
            extracted_data['monto_neto'] = extracted_data['monto_total']

    except Exception as e:
        extracted_data["error"] = str(e)
    
    # Ensure all required fields are present, defaulting to None
    required_fields = ['emisor_ruc', 'aceptante_ruc', 'invoice_id', 'fecha_emision', 'moneda', 'monto_total', 'monto_neto']
    for field in required_fields:
        if field not in extracted_data:
            extracted_data[field] = None
            
    return extracted_data