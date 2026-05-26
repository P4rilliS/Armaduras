from pymongo import MongoClient

try:
    client = MongoClient("mongodb+srv://@clusterprueba.l2t7dwu.mongodb.net/?appName=clusterPrueba")
    # Intentamos pedirle algo a la base de datos
    client.admin.command('ping')
    print("✅ ¡Coronamos")
except Exception as e:
    print(f"❌ Error de conexión: {e}")
