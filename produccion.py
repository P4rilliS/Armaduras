from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def menu_medidas():
    keyboard = [
        [InlineKeyboardButton("📏 1.00 Metro", callback_data='medida_100')],
        [InlineKeyboardButton("📏 1.40 Metros", callback_data='medida_140')],
        [InlineKeyboardButton("📏 1.60 Metros", callback_data='medida_160')],
        [InlineKeyboardButton("📏 2.0 Metros", callback_data='medida_200')]
    ]
    return InlineKeyboardMarkup(keyboard)

def menu_copas(medida):
    if medida == "100":
        opciones = [["9 Copas", "100_9"], ["10 Copas", "100_10"]]
    elif medida == "140":
        opciones = [["12 Copas", "140_12"], ["13 Copas", "140_13"], ["14 Copas", "140_14"]]
    elif medida == "160":
        opciones = [["16 Copas", "160_16"], ["17 Copas", "160_17"]]
    else: # medida == "200"
        opciones = [["19 Copas", "200_19"], ["20 Copas", "200_20"]]
    
    
    keyboard = [[InlineKeyboardButton(texto, callback_data=f"copas_{data}")] for texto, data in opciones]
    return InlineKeyboardMarkup(keyboard)