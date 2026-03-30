from fpdf import FPDF
from datetime import datetime, timedelta
import os
import database as db

def crear_pdf_semanal():
    # 1. Configurar fechas (Lunes a hoy)
    hoy = datetime.now()
    lunes_pasado = hoy - timedelta(days=hoy.weekday())
    inicio_semana = lunes_pasado.replace(hour=0, minute=0, second=0, microsecond=0)

    # 2. Traer la data
    datos_prod = list(db.col_produccion.find({"timestamp": {"$gte": inicio_semana}}))
    datos_alambre = list(db.col_alambre.find({"timestamp": {"$gte": inicio_semana}}))

    if not datos_prod and not datos_alambre:
        return None

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, "REPORTE DE PLANTA - SEMANAL", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 10, f"Desde: {inicio_semana.strftime('%d/%m/%Y')} hasta {hoy.strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)

    # --- SECCIÓN 1: PRODUCCIÓN DE ARMADURAS ---
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(190, 10, "1. DETALLE DE PRODUCCION", ln=True, fill=True)
    pdf.set_font("Arial", size=10)
    
    resumen_tipos = {} # Diccionario para agrupar (ej: {"1.00m-12C": 50})
    gran_total_armaduras = 0

    if datos_prod:
        for d in datos_prod:
            fecha_str = d['timestamp'].strftime("%d/%m %H:%M")
            linea = f"* {fecha_str} | {d['medida']}m - {d['copas']}C | Cant: {d['cantidad']}"
            pdf.cell(190, 7, linea, ln=True)
            
            # Lógica para agrupar totales por tipo
            clave = f"{d['medida']}m - {d['copas']}C"
            resumen_tipos[clave] = resumen_tipos.get(clave, 0) + d['cantidad']
            gran_total_armaduras += d['cantidad']

        # Imprimir el resumen por tipos
        pdf.ln(3)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(190, 8, "RESUMEN POR TIPO DE ARMADURA:", ln=True)
        pdf.set_font("Arial", size=10)
        for tipo, total in resumen_tipos.items():
            pdf.cell(190, 7, f"   > {tipo}: {total} unidades", ln=True)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(190, 8, f"TOTAL GENERAL ARMADURAS: {gran_total_armaduras}", ln=True)
    else:
        pdf.cell(190, 8, "No hubo producción esta semana.", ln=True)

    pdf.ln(5)

    # --- SECCIÓN 2: GASTO DE ALAMBRE ---
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "2. GASTO DE ALAMBRE (ENTRADAS)", ln=True, fill=True)
    pdf.set_font("Arial", size=10)

    total_kg = 0 # Inicializamos siempre en 0 para evitar errores
    if datos_alambre:
        for a in datos_alambre:
            linea = f"* {a['timestamp'].strftime('%d/%m')} | Calibre: {a['calibre']} | Peso: {a['kilos']}kg"
            pdf.cell(190, 7, linea, ln=True)
            total_kg += a['kilos']
        
        pdf.ln(2)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(190, 8, f"TOTAL ALAMBRE SEMANAL: {total_kg}kg", ln=True)
    else:
        pdf.cell(190, 8, "No se registraron bobinas nuevas.", ln=True)

    # 4. Guardar archivo temporal
    nombre_archivo = f"Reporte_{hoy.strftime('%Y%m%d')}.pdf"
    pdf.output(nombre_archivo)
    return nombre_archivo