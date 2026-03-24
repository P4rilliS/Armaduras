import os
from pymongo import MongoClient
from datetime import datetime

# Conexión (Cámbialo por tu URI de Atlas)
MONGO_URL = os.getenv("MONGO_URL")
client = MongoClient(MONGO_URL)
# client = MongoClient("mongodb+srv://admin:admin12345@clusterprueba.l2t7dwu.mongodb.net/?appName=clusterPrueba") 
db = client['FabricaResortes']

# Gavetas
col_produccion = db['produccion_armaduras']
col_alambre = db['gasto_alambre']

def db_guardar_produccion(medida, copas, cantidad):
    registro = {
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "medida": medida,
        "copas": copas,
        "cantidad": int(cantidad),
        "timestamp": datetime.now()
    }
    return col_produccion.insert_one(registro)

def db_registrar_alambre(calibre, kilos):
    registro = {
        "fecha": datetime.now(),
        "calibre": calibre,
        "kilos": float(kilos),
        "timestamp": datetime.now()
    }
    return col_alambre.insert_one(registro)

def db_obtener_totales():
    # Agrupa por medida y copas para darte el total de la historia
    pipeline = [
        {"$group": {"_id": {"m": "$medida", "c": "$copas"}, "total": {"$sum": "$cantidad"}}}
    ]
    return list(col_produccion.aggregate(pipeline))

def borrar_toda_la_data():
    """Borra todos los documentos de ventas y ajustes."""
    try:
        col_produccion.delete_many({})
        col_alambre.delete_many({}) 
        return True
    except Exception as e:
        print(f"Error al borrar la data: {e}")
        return False