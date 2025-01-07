from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from config import CHANNEL_ID
from database import load_users

# Variables globales
pending_list = []  # Lista temporal para procesar nombres detectados

# Cargar base de datos
users_db = load_users()

# Paso 1: Enviar lista para revisión
def start_checkin(update: Update, context: CallbackContext) -> None:
    global pending_list

    # Obtener lista enviada por el usuario
    message = update.message.text
    pending_list = [name.strip() for name in message.split('\n') if name.strip()]

    # Verificar usuarios registrados
    detected_users = []
    unregistered_users = []

    for name in pending_list:
        match = next((user for user in users_db['approved'] if user['name'] == name), None)
        if match:
            detected_users.append(f"{name} (@{match['username']})")
        else:
            unregistered_users.append(name)

    # Crear mensaje de revisión
    review_message = "<b>Revisión de nombres detectados:</b>\n\n"
    review_message += "\n<b>Registrados:</b>\n" + '\n'.join(detected_users) if detected_users else "No hay usuarios registrados."
    review_message += "\n\n<b>No registrados:</b>\n" + '\n'.join(unregistered_users) if unregistered_users else "\nTodos están registrados."

    # Botones para confirmar o cancelar
    buttons = [
        [InlineKeyboardButton("✅ Confirmar", callback_data="confirm_list")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_list")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    update.message.reply_text(review_message, parse_mode="HTML", reply_markup=reply_markup)


# Paso 2: Confirmar lista y enviarla al canal
def confirm_list(update: Update, context: CallbackContext) -> None:
    global pending_list

    mentions = []
    for name in pending_list:
        user = next((user for user in users_db['approved'] if user['name'] == name), None)
        if user:
            mentions.append(f"@{user['username']}")

    # Enviar lista al canal
    if mentions:
        context.bot.send_message(chat_id=CHANNEL_ID, text=f"<b>Conductores programados:</b>\n{' '.join(mentions)}", parse_mode="HTML")

    update.callback_query.message.edit_text("✅ Lista enviada al canal.", parse_mode="HTML")


# Paso 3: Cancelar proceso
def cancel_list(update: Update, context: CallbackContext) -> None:
    global pending_list
    pending_list = []
    update.callback_query.message.edit_text("❌ Proceso cancelado.", parse_mode="HTML")


# Registrar comandos
def register_checkin_handlers(dispatcher):
    dispatcher.add_handler(CallbackQueryHandler(confirm_list, pattern='^confirm_list$'))
    dispatcher.add_handler(CallbackQueryHandler(cancel_list, pattern='^cancel_list$'))
