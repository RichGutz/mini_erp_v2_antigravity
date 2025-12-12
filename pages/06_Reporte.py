import streamlit as st
import pandas as pd
import datetime
import json
import os

from src.data import supabase_repository as db
from src.ui.header import render_header

# --- Configuration ---
st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# --- Header ---
render_header("Reporte de Operaciones")

# --- Filters ---
st.markdown("### 🔍 Filtros de Búsqueda")

with st.container(border=True):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Date Range (Last 30 days default)
        today = datetime.date.today()
        start_default = today - datetime.timedelta(days=30)
        fechas = st.date_input("Fecha de Registro", [start_default, today])
    
    with col2:
        emisor_input = st.text_input("RUC Emisor / Nombre (Búsqueda)", placeholder="Ej. 20123456789")
        # Logic to find RUC if name typed? For now keep simple: RUC or partial ID search?
        # The repo function `search_proposals_advanced` takes specific args.
        # Let's assume input is RUC for strict filter, or leave empty.
        
    with col3:
        lote_input = st.text_input("Nombre de Lote", placeholder="Ej. Contrato_2025")
        
    with col4:
        st.write("") # Spacer
        st.write("")
        btn_search = st.button("🔎 Buscar Operaciones", type="primary", use_container_width=True)

# --- Results ---
if btn_search:
    f_start = fechas[0] if len(fechas) > 0 else None
    f_end = fechas[1] if len(fechas) > 1 else f_start
    
    with st.spinner("Consultando base de datos..."):
        # Determine RUC vs Name? Repository expects RUC.
        # If user types a name, we might want to resolve it first, but let's stick to RUC for precision as per plan.
        # Actually, let's just pass text to emisor_ruc filter? No, standard is RUC.
        # IF input is not numeric (11 chars), maybe we search for emisor?
        # For this MVP, let's assume valid RUC input for exact match or empty for all.
        
        target_ruc = emisor_input.strip() if emisor_input else None
        
        results = db.search_proposals_advanced(
            emisor_ruc=target_ruc,
            fecha_inicio=f_start,
            fecha_fin=f_end,
            lote_filter=lote_input
        )
        
    if not results:
        st.warning("No se encontraron operaciones con los filtros seleccionados.")
    else:
        st.success(f"Se encontraron {len(results)} operaciones.")
        
        # --- Processing for Display ---
        data_rows = []
        for r in results:
            # Extract JSON data
            raw_json = r.get('recalculate_result_json')
            group_id = "-"
            if raw_json:
                try:
                    parsed = json.loads(raw_json)
                    group_id = parsed.get('group_id', '-')
                except:
                    pass
            
            data_rows.append({
                "ID Propuesta": r['proposal_id'],
                "Fecha Registro": r.get('fecha_registro') or r['proposal_id'].split('-')[-1][:8], # YYYYMMDD fallback
                "RUC Emisor": r['emisor_ruc'],
                "Nombre Emisor": r['emisor_nombre'],
                "Factura": r['numero_factura'],
                "Moneda": r['moneda_factura'],
                "Monto Neto": r['monto_neto_factura'],
                "Lote (Carpeta)": r['identificador_lote'],
                "Grupo": group_id,
                "Estado": r['estado']
            })
            
        df = pd.DataFrame(data_rows)
        
        # --- Client Side Filter: Group ---
        # Allow filtering result DF by Group
        groups_avail = sorted(list(set(df['Grupo'].astype(str))))
        
        col_f1, col_f2 = st.columns([1, 4])
        with col_f1:
            sel_groups = st.multiselect("Filtrar por Grupo (Resultados)", groups_avail)
            
        if sel_groups:
            df = df[df['Grupo'].astype(str).isin(sel_groups)]
            
        # --- Metrics ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Operaciones", len(df))
        
        total_pen = df[df['Moneda']=='PEN']['Monto Neto'].sum()
        total_usd = df[df['Moneda']=='USD']['Monto Neto'].sum()
        
        m2.metric("Total PEN (Neto)", f"S/ {total_pen:,.2f}")
        m3.metric("Total USD (Neto)", f"$ {total_usd:,.2f}")
        
        # --- Data Table ---
        st.dataframe(
            df, 
            use_container_width=True,
            column_config={
                "Monto Neto": st.column_config.NumberColumn(format="%.2f"),
                "Fecha Registro": st.column_config.DateColumn(format="DD-MM-YYYY"),
            },
            hide_index=True
        )
