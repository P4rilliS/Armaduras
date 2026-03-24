import logging
import os
from pymongo import MongoClient
from datetime import datetime
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler


# --- Importamos los archivos del proyecto ---
import database as db
import produccion as prod
import alambre as al
import generarPDF as genPDF

# Configuración de logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ESTADOS DE LA CONVERSACIÓN
# Usamos estos para que el bot sepa en qué paso de la "entrevista" va
MEDIDA, COPAS, CANTIDAD, ALAMBRE_CALIBRE, ALAMBRE_KILOS = range(5)
TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")  # Asegúrate de tener esta variable en tu .env

TECLADO = [['➕ Produccion de Armaduras'], ['🔩 Gasto de Alambre'], ['📊 Ver Totales', '📄 Descargar PDF']]
CANCELAR = ReplyKeyboardMarkup([['❌ Cancelar']], resize_keyboard=True, one_time_keyboard=True)

# --- Teclado Principal ---
def get_main_keyboard():
    return ReplyKeyboardMarkup(TECLADO, resize_keyboard=True)

# --- INICIO ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"¡Hola {user_name}! Aqui llevas a cabo el inventario de armaduras y el gasto de alambre\n\nSelecciona una opcion:",
        reply_markup=ReplyKeyboardMarkup(TECLADO, resize_keyboard=True)
    )

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela la operación y muestra el menú principal de una vez."""
    context.user_data.clear() # Limpiamos los datos que se estaban llenando
    await update.message.reply_text("Operación cancelada.", reply_markup=get_main_keyboard())
    return ConversationHandler.END


# --- PRODUCCION DE ARMADURAS ---
async def iniciar_produccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📏 Selecciona la medida:", reply_markup=prod.menu_medidas())
    return MEDIDA

async def handle_medida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Guardamos la medida elegida (100 o 140) en la memoria temporal del bot
    medida = query.data.split('_')[1]
    context.user_data['prod_medida'] = medida
    
    # Mostramos el menú de copas según la medida
    await query.edit_message_text(
        text=f"Seleccionaste {medida}. ¿De cuántas copas es?",
        reply_markup=prod.menu_copas(medida)
    )
    return COPAS

async def handle_copas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Guardamos las copas elegidas
    copas = query.data.split('_')[2]
    context.user_data['prod_copas'] = copas
    
    await query.edit_message_text(f"Perfecto: {context.user_data['prod_medida']}m con {copas}C.\n\n🔢 Dime la cantidad que hiciste:")
    return CANTIDAD

async def guardar_produccion_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cantidad = update.message.text
    
    if not cantidad.isdigit():
        await update.message.reply_text("Mano, ponme un número válido, no me vaciles.")
        return CANTIDAD

    # Sacamos los datos que veníamos guardando en user_data
    medida = context.user_data.get('prod_medida')
    copas = context.user_data.get('prod_copas')
    
    # GUARDAMOS EN MONGODB
    db.db_guardar_produccion(medida, copas, cantidad)
    
    await update.message.reply_text(
        f"✅ ¡Listo Sergio!\nRegistrado: {medida}m - {copas}C - Cantidad: {cantidad}",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END



# --- GASTO DE ALAMBRE ---

async def iniciar_alambre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔩 Selecciona el calibre del alambre:", reply_markup=al.menu_alambre())
    return ALAMBRE_CALIBRE
async def handle_calibre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    calibre = query.data.split('_')[1]
    context.user_data['alambre_calibre'] = calibre
    
    await query.edit_message_text(f"Calibre {calibre} seleccionado.\n\n🔢 Ahora dime cuántos kilos ingresaron:")
    return ALAMBRE_KILOS
async def guardar_alambre_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kilos = update.message.text.replace(',', '.')
    
    try:
        kilos_float = float(kilos)
    except ValueError:
        await update.message.reply_text("Mano, ponme un número válido para los kilos, no me vaciles.")
        return ALAMBRE_KILOS

    calibre = context.user_data.get('alambre_calibre')
    
    db.db_registrar_alambre(calibre, kilos_float)
    
    await update.message.reply_text(
        f"✅ Registrado: Calibre {calibre} - {kilos_float}kg",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

# --- VER TOTALES ---
async def ver_totales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    totales = db.db_obtener_totales()
    if not totales:
        await update.message.reply_text("Todavía no hay nada en la base de datos.")
        return

    texto = "📊 **TOTALES DE ARMADURAS**\n\n"
    for t in totales:
        # texto += f"hola aqui va"
        texto += rf"🔹 {t['_id']['m']}m \* {t['_id']['c']}C\n   Total: {t['total']}\n\n"
    
    await update.message.reply_text(texto, parse_mode='MarkdownV2')

# --- GENERAR PDF ---    

async def generar_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Llamamos a la función del otro archivo
    archivo = genPDF.crear_pdf_semanal()

    if archivo is None:
        await update.message.reply_text("Mano, todavía no hay data cargada desde el lunes.")
        return

    # Enviamos el archivo
    with open(archivo, 'rb') as doc:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=doc,
            caption="Aquí tienes el reporte de la fábrica, Sergio. ¡Dale plomo!"
        )
    
    # Borramos el archivo para que no estorbe en la carpeta
    os.remove(archivo)


# ---LIMPIAR TODO ---
async def comando_limpiar_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    exito = db.borrar_toda_la_data()
    if exito:
        mensaje = (
            "💣 **¡SISTEMA RESETEADO!**\n\n"
            "Se borraron:\n"
            "✅ Todas las armaduras ingresadas.\n"
            "✅ El alambre ingresado.\n\n"
            "Ya puedes empezar de cero."
        )
    else:        mensaje = "❌ Hubo un error al intentar borrar la data.."
    await update.message.reply_text(mensaje, parse_mode='Markdown', reply_markup=ReplyKeyboardMarkup(TECLADO, resize_keyboard=True))

# --- MAIN ---
if __name__ == '__main__':
    # Pon aquí el token que te dio el BotFather
    application = ApplicationBuilder().token(TOKEN_TELEGRAM).build()

    # Manejador de la conversación de armaduras
 

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Text('📊 Ver Totales'), ver_totales))
    application.add_handler(MessageHandler(filters.Text('📄 Descargar PDF'), generar_pdf))
    application.add_handler(CommandHandler("limpiar", comando_limpiar_todo)) # Comando para limpiar todo (solo para pruebas)

    conv_prod = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex('➕ Produccion de Armaduras'), iniciar_produccion),
                MessageHandler(filters.Regex('🔩 Gasto de Alambre'), iniciar_alambre)
            ],
            states={
                MEDIDA: [MessageHandler(filters.Regex('^❌ Cancelar$'), cancelar), CallbackQueryHandler(handle_medida, pattern='^medida_')],
                COPAS: [MessageHandler(filters.Regex('^❌ Cancelar$'), cancelar), CallbackQueryHandler(handle_copas, pattern='^copas_')],
                CANTIDAD: [MessageHandler(filters.Regex('^❌ Cancelar$'), cancelar), MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_produccion_final)],
                ALAMBRE_CALIBRE: [MessageHandler(filters.Regex('^❌ Cancelar$'), cancelar), CallbackQueryHandler(handle_calibre, pattern='^alambre_')],
                ALAMBRE_KILOS: [MessageHandler(filters.Regex('^❌ Cancelar$'), cancelar), MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_alambre_final)],
            },
            fallbacks=[CommandHandler("start", start), MessageHandler(filters.Regex('^❌ Cancelar$'), cancelar)],
            allow_reentry=True # IMPORTANTE: Permite saltar de una función a otra si te equivocas
        )
    application.add_handler(conv_prod)    




    print("El bot esta online!")
    application.run_polling()