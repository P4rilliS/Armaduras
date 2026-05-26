from fpdf import FPDF
from datetime import datetime, timedelta
import database as db

def crear_pdf_semanal():
    resumen = db.db_obtener_resumen_semanal_global()

    if not resumen:
        return None

    hoy = datetime.now()
    pdf = FPDF()
    pdf.add_page()
    
    # ENCABEZADO PRO PARA LA OFICINA
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, "REPORTE DE PLANTA - INVENTARIO SEMANAL", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 8, f"Generado el: {hoy.strftime('%d/%m/%Y %I:%M %p')} (Hora VE)", ln=True, align='C')
    pdf.ln(5)

    # TABLA
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(190, 10, "1. MOVIMIENTO DE DIARIO EN PLANTA (TOTALES GENERALES)", ln=True, fill=True)
    pdf.ln(3)

    # Encabezados de la tabla
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(35, 8, "Dia / Fecha", 1, 0, 'C', True)
    pdf.cell(35, 8, "Maquina (Hoy)", 1, 0, 'C', True)
    pdf.cell(40, 8, "Patio Cierre Ant.", 1, 0, 'C', True)
    pdf.cell(40, 8, "Patio Hoy", 1, 0, 'C', True)
    pdf.cell(40, 8, "Completadas", 1, 1, 'C', True)

    pdf.set_font("Arial", size=9)
    dias_semana = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
    
    dias_ordenados = sorted(resumen.items(), key=lambda x: x[1]['timestamp'])
    gran_total_completadas = 0

    for fecha, datos in dias_ordenados:
        dt = datos['timestamp']
        nombre_dia = dias_semana[dt.weekday()]
        
        # Buscamos el patio anterior
        fecha_ayer_dt = dt - timedelta(days=1)
        if dt.weekday() == 0: 
            fecha_ayer_dt = dt - timedelta(days=3)
            
        fecha_ayer_str = fecha_ayer_dt.strftime("%d/%m/%Y")
        patio_ayer_reg = db.col_patio.find_one({"fecha": fecha_ayer_str})
        patio_ayer = patio_ayer_reg["cantidad_patio"] if patio_ayer_reg else 0
        
        # Fórmula Sergio
        completadas = (patio_ayer + datos['maquina']) - datos['patio']
        completadas = max(0, completadas)
        gran_total_completadas += completadas

        # Escribimos la fila
        pdf.cell(35, 7, f"{nombre_dia} ({fecha[:5]})", 1, 0, 'C')
        pdf.cell(35, 7, str(datos['maquina']), 1, 0, 'C')
        pdf.cell(40, 7, str(patio_ayer), 1, 0, 'C')
        pdf.cell(40, 7, str(datos['patio']), 1, 0, 'C')
        
        pdf.set_font("Arial", "B", 9)
        pdf.cell(40, 7, str(completadas), 1, 1, 'C')
        pdf.set_font("Arial", size=9)

    # TOTAL GENERAL
    pdf.ln(5)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, f"TOTAL GENERAL COMPLETADAS EN LA SEMANA: {gran_total_completadas} Unidades", ln=True)

    nombre_archivo = f"Reporte_Planta_{hoy.strftime('%Y%m%d')}.pdf"
    pdf.output(nombre_archivo)
    return nombre_archivo
