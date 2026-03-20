from pymongo import MongoClient

try:
    client = MongoClient("mongodb+srv://admin:admin12345@clusterprueba.l2t7dwu.mongodb.net/?appName=clusterPrueba")
    # Intentamos pedirle algo a la base de datos
    client.admin.command('ping')
    print("✅ ¡Coronamos, Sergio! Conectado a MongoDB con éxito.")
except Exception as e:
    print(f"❌ Error de conexión: {e}")