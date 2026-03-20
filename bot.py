import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler,
)

# --- Importamos tus archivos ---
import database as db
import produccion as prod
print("funciones en produccion.py:", dir(prod))
import alambre as al

# Configuración de logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ESTADOS DE LA CONVERSACIÓN
# Usamos estos para que el bot sepa en qué paso de la "entrevista" va
MEDIDA, COPAS, CANTIDAD = range(3)
ALAMBRE_CALIBRE, ALAMBRE_KILOS = range(3, 5)

# --- Teclado Principal ---
def get_main_keyboard():
    keyboard = [['➕ Produccion de Armaduras'], ['🔩 Gasto de Alambre'], ['📊 Ver Totales', '📄 Descargar PDF']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- INICIO ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"¡Hola {user_name}! Aqui llevas a cabo el inventario de armaduras y el gasto de alambre\n\nSelecciona una opcion:",
        reply_markup=get_main_keyboard()
    )

# --- FLUJO DE PRODUCCIÓN ---
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

# --- VER TOTALES (MODIFICADO) ---
async def ver_totales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    totales = db.db_obtener_totales()
    if not totales:
        await update.message.reply_text("Todavía no hay nada en la base de datos.")
        return

    texto = "📊 **TOTALES DE ARMADURAS**\n\n"
    for t in totales:
        texto += f"🔹 {t['_id']['m']}m \* {t['_id']['c']}C\n   Total: {t['total']}\n\n"
    
    await update.message.reply_text(texto, parse_mode='MarkdownV2')

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# --- MAIN ---
if __name__ == '__main__':
    # Pon aquí el token que te dio el BotFather
    application = ApplicationBuilder().token("7917378484:AAHtwC-Q2fJ_A2WPvP8KtvB_ssfw8zKGzwo").build()

    # Manejador de la conversación de armaduras
    conv_prod = ConversationHandler(
        entry_points=[MessageHandler(filters.Text('➕ Registrar Producción'), iniciar_produccion)],
        states={
            MEDIDA: [CallbackQueryHandler(handle_medida, pattern='^medida_')],
            COPAS: [CallbackQueryHandler(handle_copas, pattern='^copas_')],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_produccion_final)]
        },
        fallbacks=[CommandHandler('cancel', cancelar)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_prod)
    application.add_handler(MessageHandler(filters.Text('📊 Ver Totales'), ver_totales))

    print("El bot esta online!")
    application.run_polling()