import os
from pymongo import MongoClient
from datetime import datetime

# Conexión
MONGO_URL = os.getenv("MONGO_URL")
client = MongoClient(MONGO_URL)
db = client['FabricaResortes']

try:
    client.admin.command('ping')
    print("✅ ¡Conexión exitosa a MongoDB Atlas, Sergio!")
except Exception as e:
    print(f"❌ Error de conexión a Mongo: {e}")

# Las Nuevas Gavetas
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

def db_registrar_patio(medida, copas, cantidad_quedaron):
    """Registra lo que se quedó en el patio HOY sin terminar."""
    registro = {
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "medida": medida,
        "copas": copas,
        "cantidad_patio": int(cantidad_quedaron),
        "timestamp": datetime.now()
    }
    return col_patio.insert_one(registro)

def db_obtener_ultimo_patio(medida, copas):
    """Busca el último registro del patio (lo que quedó de ayer)."""
    resultado = col_patio.find_one(
        {"medida": medida, "copas": copas},
        sort=[("timestamp", -1)]
    )
    return resultado["cantidad_patio"] if resultado else 0

def db_calcular_completadas_hoy(medida, copas, fabricadas_hoy, patio_hoy):
    """Aplica tu fórmula matemática, Sergio."""
    # 1. Buscamos lo que quedó de ayer
    patio_ayer = db_obtener_ultimo_patio(medida, copas)
    
    # 2. Aplicamos tu lógica: (Ayer + Máquina) - Hoy
    completadas = (patio_ayer + int(fabricadas_hoy)) - int(patio_hoy)
    
    # Si por un error humano da negativo, lo dejamos en 0
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
