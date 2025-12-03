
import os

# Este script fue usado para corregir la propagación de variables globales en Streamlit.
# El problema era que actualizar el diccionario de datos no actualizaba los widgets individuales
# porque Streamlit mantiene el estado del widget en session_state[key].
# Se usó este script para hacer reemplazos masivos y seguros frente a problemas de indentación.

file_path = r"C:\Users\rguti\mini_erp_v2_antigravity\pages\01_Operaciones.py"

# Replacements
replacements = [
    (
        "        for invoice in st.session_state.invoices_data:\n            invoice['tasa_de_avance'] = global_tasa",
        "        for idx, invoice in enumerate(st.session_state.invoices_data):\n            invoice['tasa_de_avance'] = global_tasa\n            st.session_state[f\"tasa_de_avance_{idx}\"] = global_tasa"
    ),
    (
        "        for invoice in st.session_state.invoices_data:\n            invoice['interes_mensual'] = global_interes",
        "        for idx, invoice in enumerate(st.session_state.invoices_data):\n            invoice['interes_mensual'] = global_interes\n            st.session_state[f\"interes_mensual_{idx}\"] = global_interes"
    ),
    (
        "        for invoice in st.session_state.invoices_data:\n            invoice['interes_moratorio'] = global_interes_moratorio",
        "        for idx, invoice in enumerate(st.session_state.invoices_data):\n            invoice['interes_moratorio'] = global_interes_moratorio\n            st.session_state[f\"interes_moratorio_{idx}\"] = global_interes_moratorio"
    ),
    (
        "        for invoice in st.session_state.invoices_data:\n            invoice['dias_minimos_interes_individual'] = global_min_days",
        "        for idx, invoice in enumerate(st.session_state.invoices_data):\n            invoice['dias_minimos_interes_individual'] = global_min_days\n            st.session_state[f\"dias_minimos_interes_individual_{idx}\"] = global_min_days"
    ),
    (
        "        global_due_date_str = st.session_state.fecha_vencimiento_global.strftime('%d-%m-%Y')\n        for invoice in st.session_state.invoices_data:\n            invoice['fecha_pago_calculada'] = global_due_date_str\n            update_date_calculations(invoice, changed_field='fecha')",
        "        global_due_date_obj = st.session_state.fecha_vencimiento_global\n        global_due_date_str = global_due_date_obj.strftime('%d-%m-%Y')\n        for idx, invoice in enumerate(st.session_state.invoices_data):\n            invoice['fecha_pago_calculada'] = global_due_date_str\n            st.session_state[f\"fecha_pago_calculada_{idx}\"] = global_due_date_obj\n            update_date_calculations(invoice, changed_field='fecha')"
    ),
    (
        "        global_disbursement_date_str = st.session_state.fecha_desembolso_global.strftime('%d-%m-%Y')\n        for invoice in st.session_state.invoices_data:\n            invoice['fecha_desembolso_factoring'] = global_disbursement_date_str\n            update_date_calculations(invoice)",
        "        global_disbursement_date_obj = st.session_state.fecha_desembolso_global\n        global_disbursement_date_str = global_disbursement_date_obj.strftime('%d-%m-%Y')\n        for idx, invoice in enumerate(st.session_state.invoices_data):\n            invoice['fecha_desembolso_factoring'] = global_disbursement_date_str\n            st.session_state[f\"fecha_desembolso_factoring_{idx}\"] = global_disbursement_date_obj\n            update_date_calculations(invoice)"
    )
]

# Nota: Este script asume que el archivo existe en la ruta especificada.
# Para usarlo, descomentar las siguientes líneas:

# with open(file_path, "r", encoding="utf-8") as f:
#     content = f.read()

# for target, replacement in replacements:
#     if target in content:
#         content = content.replace(target, replacement)
#     else:
#         print(f"Target not found:\n{target}")

# with open(file_path, "w", encoding="utf-8") as f:
#     f.write(content)

# print("File updated successfully.")
