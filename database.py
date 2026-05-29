import os
from pymongo import MongoClient
import certifi
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Conexión
MONGO_URL = os.getenv("MONGO_URL")
client = MongoClient(MONGO_URL, tlsCAFile=certifi.where())
ENTORNO = os.getenv("ENTORNO", "produccion").lower()

if ENTORNO == "pruebas":
    db = client["Pruebas"]
    print("⚠️ Conectado a la base de datos de PRUEBAS")
else:
    db = client["FabricaResortes"]
    print("✅ Conectado a la base de datos de PRODUCCIÓN")

try:
    client.admin.command('ping')
    print("✅ ¡Conexión exitosa a MongoDB Atlas, Sergio!")
except Exception as e:
    print(f"❌ Error de conexión a Mongo: {e}")

# Las Nuevas Gavetas (Tus nombres exactos de colecciones)
col_produccion = db['produccion_armaduras']  # Lo que hace la máquina hoy
col_patio = db['inventario_patio']            # Lo que se queda en el patio sin terminar

def db_guardar_produccion(medida, copas, cantidad):
    """Registra lo que fabricó la máquina hoy."""
    registro = {
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "medida": medida,
        "copas": copas,
        "cantidad": int(cantidad),
        "timestamp": datetime.now()
    }
    return col_produccion.insert_one(registro)

def db_registrar_patio(cantidad_quedaron):
    """Guarda o PISA el patio global de hoy para evitar duplicados en la misma fecha."""
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    return col_patio.update_one(
        {"fecha": fecha_hoy},
        {"$set": {
            "cantidad_patio": int(cantidad_quedaron),
            "timestamp": datetime.now()
        }},
        upsert=True # Si no existe hoy, lo crea. Si existe, lo actualiza.
    )

def db_obtener_patio_anterior_real(fecha_referencia_str):
    """Busca el último patio registrado antes de la fecha dada (evita choques de días)."""
    formato = "%d/%m/%Y"
    dt_ref = datetime.strptime(fecha_referencia_str, formato)
    
    resultado = col_patio.find_one(
        {"timestamp": {"$lt": dt_ref}}, # Estrictamente menor a la fecha en proceso
        sort=[("timestamp", -1)]
    )
    return resultado["cantidad_patio"] if resultado else 0

def db_calcular_completadas_hoy_global(fabricadas_hoy, patio_hoy):
    """Aplica la fórmula matemática usando el patio anterior real de la fecha de hoy."""
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    patio_ayer = db_obtener_patio_anterior_real(fecha_hoy)
    completadas = (patio_ayer + int(fabricadas_hoy)) - int(patio_hoy)
    return max(0, completadas), patio_ayer

def db_obtener_totales():
    """Agrupa por medida y copas para darte el total fabricado histórico."""
    pipeline = [
        {"$group": {"_id": {"m": "$medida", "c": "$copas"}, "total": {"$sum": "$cantidad"}}}
    ]
    return list(col_produccion.aggregate(pipeline))

def borrar_toda_la_data():
    """Limpia las colecciones si ejecutas /limpiar."""
    try:
        col_produccion.delete_many({})
        col_patio.delete_many({}) 
        return True
    except Exception as e:
        print(f"Error al borrar la data: {e}")
        return False

def db_obtener_resumen_semanal_global():
    """Retorna una LISTA ordenada por fecha lista para consumir en el bot y PDF."""
    hoy = datetime.now()
    fecha_limite = hoy - timedelta(days=7)
    
    registros_prod = list(col_produccion.find({"timestamp": {"$gte": fecha_limite}}))
    
    # 1. Sumamos la máquina por fecha
    maquina_por_dia = {}
    for p in registros_prod:
        fecha = p.get("fecha")
        if fecha not in maquina_por_dia:
            maquina_por_dia[fecha] = 0
        maquina_por_dia[fecha] += p.get("cantidad", 0)
        
    # 2. Construimos la lista estructurada aplicando la matemática global
    resumen_final = []
    for fecha, total_maquina in maquina_por_dia.items():
        patio_hoy_reg = col_patio.find_one({"fecha": fecha})
        patio_hoy = patio_hoy_reg["cantidad_patio"] if patio_hoy_reg else 0
        
        patio_ayer = db_obtener_patio_anterior_real(fecha)
        completadas = max(0, (patio_ayer + total_maquina) - patio_hoy)
        
        dt_base = datetime.strptime(fecha, "%d/%m/%Y")
        
        resumen_final.append({
            "fecha": fecha,
            "maquina": total_maquina,
            "patio_ayer": patio_ayer,
            "patio_hoy": patio_hoy,
            "completadas": completadas,
            "dt": dt_base
        })
        
    # Ordenamos cronológicamente de lunes a domingo
    resumen_final.sort(key=lambda x: x["dt"])
    return resumen_final
