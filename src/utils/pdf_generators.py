# src/utils/pdf_generators.py

import os
import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from typing import List, Dict, Any

# --- Helper Functions for Templates ---

def _format_currency(value: float, currency: str = "PEN") -> str:
    """Formats a number as currency with a thousands separator and symbol."""
    if value is None:
        return ""
    try:
        val = float(value)
    except (ValueError, TypeError):
        return str(value)
    return f"{currency} {val:,.2f}"

# --- Main PDF Generation Logic ---

def _generate_pdf_in_memory(
    template_name: str,
    template_data: Dict[str, Any]
) -> bytes | None:
    """
    Core PDF generation function that returns the PDF as bytes.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    templates_dir = os.path.join(project_root, 'src', 'templates')
    
    env = Environment(loader=FileSystemLoader(templates_dir))
    env.filters['format_currency'] = _format_currency
    template = env.get_template(template_name)

    html_out = template.render(template_data)
    
    base_url = project_root
    return HTML(string=html_out, base_url=base_url).write_pdf()

# --- Public Functions for Specific Reports ---

def generate_perfil_operacion_pdf(invoices_data: List[Dict[str, Any]]) -> bytes | None:
    """
    Generates the 'Perfil de Operación' PDF for one or more invoices and returns it as bytes.
    """
    # --- Calculate Totals for the Consolidated Summary ---
    total_monto_total_factura = sum(inv.get('monto_total_factura', 0) for inv in invoices_data)
    total_detraccion_monto = sum(inv.get('detraccion_monto', 0) for inv in invoices_data)
    total_monto_neto_factura = sum(inv.get('monto_neto_factura', 0) for inv in invoices_data)
    total_margen_seguridad = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('margen_seguridad', {}).get('monto', 0) for inv in invoices_data)
    total_capital = sum(inv.get('recalculate_result', {}).get('calculo_con_tasa_encontrada', {}).get('capital', 0) for inv in invoices_data)
    total_intereses = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('interes', {}).get('monto', 0) for inv in invoices_data)
    total_igv_interes = sum(inv.get('recalculate_result', {}).get('calculo_con_tasa_encontrada', {}).get('igv_interes', 0) for inv in invoices_data)
    total_comision_estructuracion = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('comision_estructuracion', {}).get('monto', 0) for inv in invoices_data)
    total_igv_com_est = sum(inv.get('recalculate_result', {}).get('calculo_con_tasa_encontrada', {}).get('igv_comision_estructuracion', 0) for inv in invoices_data)
    total_comision_afiliacion = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('comision_afiliacion', {}).get('monto', 0) for inv in invoices_data)
    total_igv_com_afi = sum(inv.get('recalculate_result', {}).get('calculo_con_tasa_encontrada', {}).get('igv_afiliacion', 0) for inv in invoices_data)
    total_monto_desembolsar = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('abono', {}).get('monto', 0) for inv in invoices_data)

    template_data = {
        'invoices': invoices_data,
        'print_date': datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
        'total_monto_total_factura': total_monto_total_factura,
        'total_detraccion_monto': total_detraccion_monto,
        'total_monto_neto_factura': total_monto_neto_factura,
        'total_margen_seguridad': total_margen_seguridad,
        'total_capital': total_capital,
        'total_intereses': total_intereses,
        'total_igv_interes': total_igv_interes,
        'total_comision_estructuracion': total_comision_estructuracion,
        'total_igv_com_est': total_igv_com_est,
        'total_comision_afiliacion': total_comision_afiliacion,
        'total_igv_com_afi': total_igv_com_afi,
        'total_monto_desembolsar': total_monto_desembolsar,
    }
    return _generate_pdf_in_memory("perfil_operacion.html", template_data)

def generate_efide_report_pdf(invoices_data: List[Dict[str, Any]], signatory_data: Dict[str, Any]) -> bytes | None:
    """
    Generates the EFIDE report PDF with all calculations and returns it as bytes.
    """
    # --- Calculate Totals for the Footer ---
    total_monto_total_factura = sum(inv.get('monto_total_factura', 0) for inv in invoices_data)
    total_detraccion_monto = sum(inv.get('detraccion_monto', 0) for inv in invoices_data)
    total_monto_neto_factura = sum(inv.get('monto_neto_factura', 0) for inv in invoices_data)
    
    weighted_sum_tasa_avance = sum(
        inv.get('monto_neto_factura', 0) * inv.get('recalculate_result', {}).get('resultado_busqueda', {}).get('tasa_avance_encontrada', 0)
        for inv in invoices_data
    )
    total_tasa_avance_aplicada = (weighted_sum_tasa_avance / total_monto_neto_factura) if total_monto_neto_factura > 0 else 0
    
    total_margen_seguridad = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('margen_seguridad', {}).get('monto', 0) for inv in invoices_data)
    total_capital = sum(inv.get('recalculate_result', {}).get('calculo_con_tasa_encontrada', {}).get('capital', 0) for inv in invoices_data)
    total_intereses = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('interes', {}).get('monto', 0) for inv in invoices_data)
    total_comision_estructuracion = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('comision_estructuracion', {}).get('monto', 0) for inv in invoices_data)
    total_comision_afiliacion = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('comision_afiliacion', {}).get('monto', 0) for inv in invoices_data)
    
    total_igv = sum(
        inv.get('recalculate_result', {}).get('calculo_con_tasa_encontrada', {}).get('igv_interes', 0) +
        inv.get('recalculate_result', {}).get('calculo_con_tasa_encontrada', {}).get('igv_comision_estructuracion', 0) +
        inv.get('recalculate_result', {}).get('calculo_con_tasa_encontrada', {}).get('igv_afiliacion', 0)
        for inv in invoices_data
    )
    
    total_monto_desembolsar = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('abono', {}).get('monto', 0) for inv in invoices_data)

    template_data = {
        'invoices': invoices_data,
        'print_date': datetime.datetime.now(),
        'main_invoice': invoices_data[0] if invoices_data else {},
        'signatory_data': signatory_data or {}, # Ensure it's a dict
        'total_monto_total_factura': total_monto_total_factura,
        'total_detraccion_monto': total_detraccion_monto,
        'total_monto_neto_factura': total_monto_neto_factura,
        'total_tasa_avance_aplicada': total_tasa_avance_aplicada,
        'total_margen_seguridad': total_margen_seguridad,
        'total_capital': total_capital,
        'total_intereses': total_intereses,
        'total_comision_estructuracion': total_comision_estructuracion,
        'total_comision_afiliacion': total_comision_afiliacion,
        'total_igv': total_igv,
        'total_monto_desembolsar': total_monto_desembolsar,
    }
    
    return _generate_pdf_in_memory("reporte_efide.html", template_data)

def generate_lote_report_pdf(report_data: Dict[str, Any]) -> bytes | None:
    """
    (Placeholder) Generates the batch liquidation report PDF and returns it as bytes.
    """
    return _generate_pdf_in_memory("reporte_lote.html", report_data)

def generate_liquidacion_consolidada_pdf(report_data: Dict[str, Any]) -> bytes | None:
    """
    Generates the consolidated liquidation PDF (formerly V6) and returns it as bytes.
    """
    return _generate_pdf_in_memory("liquidacion_consolidada.html", report_data)

def generar_anexo_liquidacion_pdf(invoices_data: List[Dict[str, Any]]) -> bytes | None:
    """
    Generates the 'Anexo de Liquidación' PDF and returns it as bytes.
    """
    if not invoices_data:
        return None

    first_inv = invoices_data[0]
    
    # --- Calculate Totals ---
    total_monto_neto = sum(inv.get('monto_neto_factura', 0) for inv in invoices_data)
    total_capital = sum(inv.get('recalculate_result', {}).get('calculo_con_tasa_encontrada', {}).get('capital', 0) for inv in invoices_data)
    total_intereses = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('interes', {}).get('monto', 0) for inv in invoices_data)
    total_monto_desembolsar = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('abono', {}).get('monto', 0) for inv in invoices_data)
    
    total_comision_est = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('comision_estructuracion', {}).get('monto', 0) for inv in invoices_data)
    total_comision_afi = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('comision_afiliacion', {}).get('monto', 0) for inv in invoices_data)
    total_comisiones = total_comision_est + total_comision_afi
    
    total_margen_seguridad = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('margen_seguridad', {}).get('monto', 0) for inv in invoices_data)
    
    total_igv = sum(inv.get('recalculate_result', {}).get('desglose_final_detallado', {}).get('igv_total', {}).get('monto', 0) for inv in invoices_data)
    
    # Note: In the template, 'neto_desembolsar' seems to be the same as 'monto_desembolsar' 
    # (Capital - Costos), but let's verify the logic. 
    # Usually: Capital - Interes - Comisiones - IGV - Margen = Monto a Desembolsar.
    # The template shows 'Monto a desembolsar' in the main table, which usually matches the final amount.
    # But the summary table lists Comisiones, Margen, IGV separately.
    # If 'Monto a desembolsar' in the main table is the FINAL amount, then the summary table logic might be redundant or display breakdown.
    # Let's assume 'neto_desembolsar' is the final amount to pay.
    
    template_data = {
        'anexo_number': first_inv.get('anexo_number', 'PENDIENTE'),
        'print_date': datetime.datetime.now(),
        'emisor': {
            'nombre': first_inv.get('emisor_nombre', ''),
            'ruc': first_inv.get('emisor_ruc', '')
        },
        'pagador': {
            'nombre': first_inv.get('aceptante_nombre', ''),
            'ruc': first_inv.get('aceptante_ruc', '')
        },
        'moneda': first_inv.get('moneda_factura', 'PEN'),
        'invoices': invoices_data,
        'totals': {
            'monto_neto': total_monto_neto,
            'capital': total_capital,
            'intereses': total_intereses,
            'monto_desembolsar': total_monto_desembolsar, # This is usually the final amount
            'comisiones': total_comisiones,
            'margen_seguridad': total_margen_seguridad,
            'igv': total_igv,
            'neto_desembolsar': total_monto_desembolsar # Using same value for now
        },
        'deposit_info': {
            'forma_desembolso': 'TRANSFERENCIA',
            'beneficiario': first_inv.get('emisor_nombre', ''),
            'dni_beneficiario': '',
            'ruc_beneficiario': first_inv.get('emisor_ruc', ''),
            'banco': 'N/A',
            'deposito_cta': 'N/A',
            'cci': 'N/A',
            'tipo_cuenta': 'N/A'
        }
    }
    
    return _generate_pdf_in_memory("anexo_liquidacion.html", template_data)

def generate_liquidacion_universal_pdf(resultados_liquidacion: List[Dict[str, Any]], facturas_originales: List[Dict[str, Any]]) -> bytes | None:
    """
    Generates the 'Liquidación Universal' PDF showing liquidation results and returns it as bytes.
    """
    if not resultados_liquidacion:
        return None
    
    # Combinar resultados con facturas originales
    liquidaciones_completas = []
    for resultado in resultados_liquidacion:
        proposal_id = resultado.get('id_operacion')
        factura_original = next((f for f in facturas_originales if f.get('proposal_id') == proposal_id), {})
        
        liquidacion = {
            'resultado': resultado,
            'factura': factura_original
        }
        liquidaciones_completas.append(liquidacion)
    
    template_data = {
        'liquidaciones': liquidaciones_completas,
        'print_date': datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
    }
    
    return _generate_pdf_in_memory("liquidacion_universal.html", template_data)

def generar_voucher_transferencia_pdf(
    datos_emisor: Dict[str, Any],
    monto_total: float,
    moneda: str,
    facturas: List[Dict[str, Any]],
    fecha_generacion: datetime.date = None
) -> bytes | None:
    """
    Genera PDF de voucher de transferencia bancaria.
    
    Args:
        datos_emisor: Datos del emisor (razon_social, ruc, banco, cuenta, cci)
        monto_total: Monto total a transferir
        moneda: Moneda (PEN/USD)
        facturas: Lista de facturas incluidas en la transferencia
        fecha_generacion: Fecha de generación del voucher (default: hoy)
    
    Returns:
        bytes: PDF generado
    """
    if fecha_generacion is None:
        fecha_generacion = datetime.date.today()
    
    # Convertir monto a letras (simplificado)
    def numero_a_letras(numero):
        """Convierte número a letras (versión simplificada)"""
        if numero == 0:
            return "CERO"
        # Implementación básica - en producción usar librería como num2words
        return f"{numero:,.2f}"
    
    template_data = {
        'fecha_generacion': fecha_generacion.strftime('%d-%m-%Y'),
        'hora_generacion': datetime.datetime.now().strftime('%H:%M:%S'),
        'emisor': {
            'razon_social': datos_emisor.get('Razon Social', 'N/A'),
            'ruc': datos_emisor.get('RUC', 'N/A'),
            'banco': datos_emisor.get('Institucion Financiera', 'N/A'),
            # Seleccionar cuenta según moneda
            'numero_cuenta': datos_emisor.get(f'Numero de Cuenta {moneda}', 'N/A'),
            'cci': datos_emisor.get(f'Numero de CCI {moneda}', 'N/A')
        },
        'monto_total': monto_total,
        'monto_letras': numero_a_letras(monto_total),
        'moneda': moneda,
        'facturas': facturas,
        'num_facturas': len(facturas)
    }
    
    return _generate_pdf_in_memory("voucher_transferencia.html", template_data)