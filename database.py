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

def db_registrar_patio(cantidad_quedaron):
    """Registra el total global que quedó en el patio HOY sin terminar."""
    registro = {
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "cantidad_patio": int(cantidad_quedaron),
        "timestamp": datetime.now()
    }
    return col_patio.insert_one(registro)

def db_obtener_ultimo_patio_global():
    """Busca el último registro del patio general (lo que quedó el viernes/ayer)."""
    resultado = col_patio.find_one(
        {},
        sort=[("timestamp", -1)]
    )
    return resultado["cantidad_patio"] if resultado else 0

def db_calcular_completadas_hoy_global(fabricadas_hoy, patio_hoy):
    """Aplica tu fórmula con los totales generales de la planta, Sergio."""
    patio_ayer = db_obtener_ultimo_patio_global()
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
    """Trae la producción y el patio de los últimos 7 días agrupados por fecha."""
    # Buscamos los últimos 7 días de producción
    hoy = datetime.now()
    fecha_limite = hoy - timedelta(days=7)
    
    # Traemos la data ordenada por fecha
    registros_prod = list(col_produccion.find({"timestamp": {"$gte": fecha_limite}}).sort("timestamp", 1))
    
    resumen = {}
    
    # Agrupamos lo de la máquina por día
    for p in registros_prod:
        fecha = p.get("fecha")
        if fecha not in resumen:
            resumen[fecha] = {"maquina": 0, "patio": 0, "timestamp": p.get("timestamp")}
        resumen[fecha]["maquina"] += p.get("cantidad", 0)
        
    # Le metemos el patio que corresponda a cada día
    for fecha in resumen.keys():
        patio_reg = col_patio.find_one({"fecha": fecha})
        resumen[fecha]["patio"] = patio_reg["cantidad_patio"] if patio_reg else 0

    return resumen
