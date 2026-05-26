from fpdf import FPDF
from datetime import datetime, timedelta
import os
import database as db

def crear_pdf_semanal():
    # 1. Configurar fechas (Desde el lunes de esta semana hasta hoy)
    hoy = datetime.now()
    lunes_pasado = hoy - timedelta(days=hoy.weekday())
    inicio_semana = lunes_pasado.replace(hour=0, minute=0, second=0, microsecond=0)

    # 2. Traer la data desde el lunes
    datos_prod = list(db.col_produccion.find({"timestamp": {"$gte": inicio_semana}}).sort("timestamp", 1))

    if not datos_prod:
        return None

    pdf = FPDF()
    pdf.add_page()
    
    # ENCABEZADO
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, "REPORTE DE PLANTA - INVENTARIO SEMANAL", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 8, f"Desde: {inicio_semana.strftime('%d/%m/%Y')} hasta {hoy.strftime('%d/%m/%Y %I:%M %p')}", ln=True, align='C')
    pdf.ln(5)

    # --- SECCIÓN UNIQUE: DETALLE DE PRODUCCIÓN E INVENTARIO ---
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(190, 10, "1. MOVIMIENTO DE DIARIO EN PLANTA", ln=True, fill=True)
    pdf.ln(3)

    # Encabezados de la tabla adaptada a tu fórmula Sergio
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(25, 8, "Fecha", 1, 0, 'C', True)
    pdf.cell(30, 8, "Medida", 1, 0, 'C', True)
    pdf.cell(25, 8, "Maquina", 1, 0, 'C', True)
    pdf.cell(28, 8, "Patio (Ayer)", 1, 0, 'C', True)
    pdf.cell(28, 8, "Patio (Hoy)", 1, 0, 'C', True)
    pdf.cell(30, 8, "Completadas", 1, 1, 'C', True)

    pdf.set_font("Arial", size=9)
    
    resumen_completadas = {}
    gran_total_completadas = 0

    # Recorremos los datos de la máquina día por día
    for d in datos_prod:
        fecha_str = d['timestamp'].strftime("%d/%m")
        medida = d['medida']
        copas = d['copas']
        fabricadas_hoy = d['cantidad']
        
        # Buscamos el patio registrado para ese mismo día y medida
        patio_hoy_reg = db.col_patio.find_one({
            "medida": medida,
            "copas": copas,
            "fecha": d['fecha']
        })
        patio_hoy = patio_hoy_reg["cantidad_patio"] if patio_hoy_reg else 0
        
        # Aquí ejecutamos tu fórmula mágica Sergio (que busca de manera inteligente hacia atrás)
        # Para que en el PDF histórico use la data correspondiente, calculamos usando la función base
        completadas, patio_ayer = db.db_calcular_completadas_hoy(medida, copas, fabricadas_hoy, patio_hoy)
        
        # Escribimos la fila en la tabla
        pdf.cell(25, 7, fecha_str, 1, 0, 'C')
        pdf.cell(30, 7, f"{medida}m - {copas}C", 1, 0, 'C')
        pdf.cell(25, 7, str(fabricadas_hoy), 1, 0, 'C')
        pdf.cell(28, 7, str(patio_ayer), 1, 0, 'C')
        pdf.cell(28, 7, str(patio_hoy), 1, 0, 'C')
        
        pdf.set_font("Arial", "B", 9)
        pdf.cell(30, 7, str(completadas), 1, 1, 'C')
        pdf.set_font("Arial", size=9)
        
        # Agrupamos los totales semanales de lo que realmente se completó listo para despacho
        clave = f"{medida}m - {copas}C"
        resumen_completadas[clave] = resumen_completadas.get(clave, 0) + completadas
        gran_total_completadas += completadas

    # --- SECCIÓN 2: RESUMEN TOTAL DE ARMADURAS LISTAS ---
    pdf.ln(8)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "2. RESUMEN DE ARMADURAS COMPLETADAS (LISTAS)", ln=True, fill=True)
    pdf.ln(3)
    
    pdf.set_font("Arial", size=10)
    for tipo, total in resumen_completadas.items():
        pdf.cell(190, 7, f"   > {tipo}: {total} unidades listas", ln=True)
    
    pdf.ln(3)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(190, 8, f"TOTAL GENERAL COMPLETADAS EN LA SEMANA: {gran_total_completadas}", ln=True)

    # 4. Guardar archivo temporal
    nombre_archivo = f"Reporte_Inventario_{hoy.strftime('%Y%m%d')}.pdf"
    pdf.output(nombre_archivo)
    return nombre_archivo
