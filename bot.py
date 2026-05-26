import logging
import os
from pymongo import MongoClient
from datetime import datetime
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# --- Importamos los archivos del proyecto ---
import database as db
import produccion as prod
import generarPDF as genPDF  # <--- Re-activado Sergio

# Configuración de logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.Application").setLevel(logging.WARNING)

# ESTADOS DE LA CONVERSACIÓN
MEDIDA, COPAS, CANTIDAD, PATIO_CANTIDAD = range(4)
TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")

# TECLADO CON NUEVO BOTÓN
TECLADO = [['➕ Produccion de Armaduras'], ['⏳ Inventario de Patio'], ['📊 Ver Totales', '📄 Descargar PDF']]
CANCELAR = ReplyKeyboardMarkup([['❌ Cancelar']], resize_keyboard=True, one_time_keyboard=True)

# --- Teclado Principal ---
def get_main_keyboard():
    return ReplyKeyboardMarkup(TECLADO, resize_keyboard=True)

# --- INICIO ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"¡Hola {user_name}! Aquí llevas el control de la máquina y el inventario del patio.\n\nSelecciona una opción:",
        reply_markup=get_main_keyboard()
    )

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela la operación y muestra el menú principal de una vez."""
    context.user_data.clear() 
    await update.message.reply_text("Operación cancelada.", reply_markup=get_main_keyboard())
    return ConversationHandler.END


# --- FLUJO COMÚN PARA SELECCIONAR MEDIDA Y COPAS ---
async def iniciar_produccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['accion'] = 'produccion'
    await update.message.reply_text("📏 Selecciona la medida:", reply_markup=prod.menu_medidas())
    return MEDIDA

async def iniciar_patio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['accion'] = 'patio'
    # Saltamos la pregunta de la medida, Sergio. Directo al grano:
    await update.message.reply_text("⏳ **Inventario General de Patio**\n\n🔢 Dime la cantidad TOTAL de armaduras que quedaron HOY sin completar:")
    return PATIO_CANTIDAD # Le decimos al bot que espere el número de una vez

async def handle_medida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    medida = query.data.split('_')[1]
    context.user_data['prod_medida'] = medida
    
    await query.edit_message_text(
        text=f"Seleccionaste {medida}m. ¿De cuántas copas?",
        reply_markup=prod.menu_copas(medida)
    )
    return COPAS

async def handle_copas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    copas = query.data.split('_')[2]
    context.user_data['prod_copas'] = copas
    
    # Como patio entra directo, aquí solo llega lo de la máquina
    await query.edit_message_text(f"Perfecto: {context.user_data['prod_medida']}m con {copas}C.\n\n🔢 Cantidad fabricada por la máquina hoy:")
    return CANTIDAD

# --- GUARDAR PRODUCCIÓN DE LA MÁQUINA ---
async def guardar_produccion_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    cantidad = update.message.text
    
    if not cantidad.isdigit():
        await update.message.reply_text(f"{user_name}, coloca un número entero válido.")
        return CANTIDAD

    medida = context.user_data.get('prod_medida')
    copas = context.user_data.get('prod_copas')
    
    db.db_guardar_produccion(medida, copas, cantidad)
    
    await update.message.reply_text(
        f"✅ ¡Listo {user_name}!\nRegistrado en Máquina: {medida}m - {copas}C - Cantidad: {cantidad}",
        reply_markup=get_main_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END


# --- GUARDAR INVENTARIO DE PATIO Y SACAR CUENTA ---
async def guardar_patio_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    patio_hoy = update.message.text
    
    if not patio_hoy.isdigit():
        await update.message.reply_text(f"{user_name}, coloca un número entero válido.")
        return PATIO_CANTIDAD

    # 1. Sumamos TODO lo que hizo la máquina hoy (todas las medidas combinadas)
    hoy_str = datetime.now().strftime("%d/%m/%Y")
    registros_hoy = list(db.col_produccion.find({"fecha": hoy_str}))
    fabricadas_hoy = sum(r["cantidad"] for r in registros_hoy)

    # 2. Guardamos el patio global en Mongo
    db.db_registrar_patio(patio_hoy)
    
    # 3. Tu fórmula mágica sin importar la medida
    completadas, patio_ayer = db.db_calcular_completadas_hoy_global(fabricadas_hoy, patio_hoy)
    
    mensaje = (
        f"✅ ¡Inventario global guardado, {user_name}!\n\n"
        f"📊 **REPORTE GENERAL DE LA PLANTA**\n"
        f"📦 Quedaron del cierre anterior (Total): {patio_ayer}\n"
        f"⚙️ Fabricó la máquina hoy (Total): {fabricadas_hoy}\n"
        f"⏳ Quedan en patio hoy (Total): {patio_hoy}\n\n"
        f"🛠️ **TOTAL ARMADURAS COMPLETADAS HOY: {completadas}**"
    )
    
    await update.message.reply_text(mensaje, reply_markup=get_main_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# --- VER TOTALES ---
async def ver_totales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    totales = db.db_obtener_totales()
    if not totales:
        await update.message.reply_text("No hay nada en la base de datos.")
        return

    texto = "📊 *TOTALES DE ARMADURAS HISTÓRICOS*\n\n"
    for t in totales:
        texto += f"🔹 *{t['_id']['m']}m* - *{t['_id']['c']}C*\n      Total Máquina: {t['total']}\n\n"
    
    await update.message.reply_text(texto, parse_mode='Markdown')


# --- ENVIAR PDF RE-ACTIVADO ---
async def generar_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text("⏳ Generando el reporte PDF para la oficina, espera un momento...")

    archivo = genPDF.crear_pdf_semanal()

    if archivo is None:
        await update.message.reply_text(f"Mano {user_name}, todavía no hay data cargada esta semana para armar el PDF.")
        return

    with open(archivo, 'rb') as doc:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=doc,
            caption=f"¡Aquí tienes el reporte de inventario listo Sergio!"
        )
    os.remove(archivo)


# --- RESETEAR SISTEMA ---
async def comando_limpiar_todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    exito = db.borrar_toda_la_data()
    if exito:
        mensaje = (
            "💣 **¡SISTEMA RESETEADO!**\n\n"
            "Se borraron:\n"
            "✅ Todas las armaduras de la máquina.\n"
            "✅ Todos los históricos del patio.\n\n"
            "Ya puedes empezar de cero, Sergio."
        )
    else:
        mensaje = "❌ Hubo un error al intentar borrar la data.."
        
    await update.message.reply_text(mensaje, parse_mode='Markdown', reply_markup=get_main_keyboard())


# --- MAIN ---
if __name__ == '__main__':
    if not TOKEN_TELEGRAM:
        print("❌ ERROR: No se encontró la variable TOKEN_TELEGRAM. Revisa Railway.")
        exit(1)
    
    application = ApplicationBuilder().token(TOKEN_TELEGRAM).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^📊 Ver Totales'), ver_totales))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^📄 Descargar PDF'), generar_pdf)) # <--- Mapeado de vuelta
    application.add_handler(CommandHandler("limpiar", comando_limpiar_todo))

    conv_prod = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('➕ Produccion de Armaduras'), iniciar_produccion),
            MessageHandler(filters.Regex('⏳ Inventario de Patio'), iniciar_patio)
        ],
        states={
            MEDIDA: [MessageHandler(filters.Regex('^❌ Cancelar$'), cancelar), CallbackQueryHandler(handle_medida, pattern='^medida_')],
            COPAS: [MessageHandler(filters.Regex('^❌ Cancelar$'), cancelar), CallbackQueryHandler(handle_copas, pattern='^copas_')],
            CANTIDAD: [MessageHandler(filters.Regex('^❌ Cancelar$'), cancelar), MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_produccion_final)],
            PATIO_CANTIDAD: [MessageHandler(filters.Regex('^❌ Cancelar$'), cancelar), MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_patio_final)],
        },
        fallbacks=[CommandHandler("start", start), MessageHandler(filters.Regex('^❌ Cancelar$'), cancelar)],
        allow_reentry=True
    )
    application.add_handler(conv_prod)

    print("El bot esta online!")
    application.run_polling()
