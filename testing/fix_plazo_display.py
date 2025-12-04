import sys
import os
import re

file_path = r"C:\Users\rguti\mini_erp_v2_antigravity\pages\01_Operaciones.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Modify function definition
old_def = "def update_date_calculations(invoice, changed_field=None):"
new_def = "def update_date_calculations(invoice, changed_field=None, idx=None):"
content = content.replace(old_def, new_def)

# 2. Add session state update logic inside function
# We look for the end of the function (before except block) to insert the update logic
# Or better, insert it after the calculations are done but before return/except
# The function has multiple return points? No, just one early return.
# But the main logic ends before `except`.

# Let's insert it right before `except (ValueError, TypeError, AttributeError):`
insert_marker = "    except (ValueError, TypeError, AttributeError):"
update_logic = """
        if idx is not None:
            if f"plazo_operacion_calculado_{idx}" in st.session_state:
                st.session_state[f"plazo_operacion_calculado_{idx}"] = str(invoice.get('plazo_operacion_calculado', 0))
            if f"plazo_credito_dias_{idx}" in st.session_state:
                st.session_state[f"plazo_credito_dias_{idx}"] = str(invoice.get('plazo_credito_dias', 0))

"""
content = content.replace(insert_marker, update_logic + insert_marker)

# 3. Update calls
# handle_global_payment_date_change
content = content.replace("update_date_calculations(invoice, changed_field='fecha')", "update_date_calculations(invoice, changed_field='fecha', idx=idx)")

# handle_global_disbursement_date_change
content = content.replace("update_date_calculations(invoice)", "update_date_calculations(invoice, idx=idx)")

# fecha_emision_changed
# It calls: update_date_calculations(st.session_state.invoices_data[idx], changed_field='fecha')
content = content.replace("update_date_calculations(st.session_state.invoices_data[idx], changed_field='fecha')", "update_date_calculations(st.session_state.invoices_data[idx], changed_field='fecha', idx=idx)")

# fecha_pago_changed
# Same call signature
# The replace above handles it? No, string match.
# Let's check if there are other variations.

# fecha_desembolso_changed
# Calls: update_date_calculations(st.session_state.invoices_data[idx])
content = content.replace("update_date_calculations(st.session_state.invoices_data[idx])", "update_date_calculations(st.session_state.invoices_data[idx], idx=idx)")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ update_date_calculations updated successfully")
