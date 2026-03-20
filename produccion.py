from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def menu_medidas():
    keyboard = [
        [InlineKeyboardButton("📏 1.00 Metro", callback_data='medida_100')],
        [InlineKeyboardButton("📏 1.40 Metros", callback_data='medida_140')]
    ]
    return InlineKeyboardMarkup(keyboard)

def menu_copas(medida):
    if medida == "100":
        opciones = [["9 Copas", "100_9"], ["10 Copas", "100_10"]]
    else:
        opciones = [["12 Copas", "140_12"], ["13 Copas", "140_13"], ["14 Copas", "140_14"]]
    
    keyboard = [[InlineKeyboardButton(texto, callback_data=f"copas_{data}")] for texto, data in opciones]
    return InlineKeyboardMarkup(keyboard)