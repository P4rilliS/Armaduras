from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def menu_alambre():
   calibres = ["2.32", "1.37"]
   keyboard = []
    
   # Vamos saltando de 2 en 2 para armar las parejas
   for i in range(0, len(calibres), 2):
        # Agarramos el calibre actual y el que sigue
        fila = [
            InlineKeyboardButton(calibres[i], callback_data=f"alambre_{calibres[i]}"),
            InlineKeyboardButton(calibres[i+1], callback_data=f"alambre_{calibres[i+1]}")
        ]
        keyboard.append(fila) # Metemos la pareja en el teclado
        
   return InlineKeyboardMarkup(keyboard)

def formato_reporte_alambre(datos_semanales):
    # Lógica para preparar el texto que irá al PDF o al mensaje
    texto = "📦 REGISTRO DE ALAMBRE\n"
    for item in datos_semanales:
        texto += f"- {item['calibre']}: {item['kilos']}kg\n"
    return texto