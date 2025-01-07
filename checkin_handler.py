# checkin_handler.py

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    CallbackContext,
    ContextTypes,
    CallbackQueryHandler
)
from config import CHANNEL_ID
from database import load_users, save_database
import datetime

# Usamos context.user_data en vez de variables globales
# para almacenar la lista y la fecha/hora temporal.
# Así evitamos conflictos cuando varios usuarios (o el admin) interactúan.

async def start_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    1) El admin envía la lista de nombres en líneas separadas.
    2) Verificamos quién está 'approved' en users_db.json.
    3) Mostramos al admin un resumen (registrados y no registrados).
    4) Luego pedimos fecha/hora de inicio para programar el check-in.
    """
    message = update.message.text
    user_db = load_users()  # Carga la BD completa

    # Guardamos la lista cruda en user_data para siguientes pasos.
    roster_list = [line.strip() for line in message.split('\n') if line.strip()]
    context.user_data["roster_list"] = roster_list  # Almacenamos la lista

    # Verificamos qué nombres coinciden con la BD
    detected, unregistered = [], []
    for name in roster_list:
        # Ojo: 'approved' es un dict con claves = user_id y valores = datos
        match = next(
            (user_info for user_info in user_db["approved"].values()
             if user_info["name"] == name),
            None
        )
        if match:
            detected.append(f"{name} (@{match['username']})")
        else:
            unregistered.append(name)

    # Armamos el texto de revisión
    review_text = "<b>Revisión de nombres detectados:</b>\n\n"
    if detected:
        review_text += "<b>Registrados:</b>\n" + "\n".join(detected)
    else:
        review_text += "No hay usuarios registrados.\n"

    if unregistered:
        review_text += "\n\n<b>No registrados:</b>\n" + "\n".join(unregistered)
    else:
        review_text += "\n\nTodos están registrados."

    # Mostramos botones para continuar
    keyboard = [
        [InlineKeyboardButton("Siguiente: Fecha/Hora", callback_data="ask_date_time")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_roster_setup")]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        review_text,
        parse_mode="HTML",
        reply_markup=markup
    )



async def ask_date_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "Indica la fecha/hora para programar el check-in.\n"
        "Formato: YYYY-MM-DD HH:MM-HH:MM\n\n"
        "Ejemplo: 2025-01-10 07:00-08:30"
    )
    context.user_data["waiting_for_date_time"] = True  # ¡Clave!

async def handle_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_date_time"):
        return  # Ignora si no estamos esperando fecha/hora

    context.user_data["waiting_for_date_time"] = False
    user_input = update.message.text.strip()
    try:
        date_part, time_part = user_input.split(" ")
        start_str, end_str = time_part.split("-")

        date_obj = datetime.datetime.strptime(date_part, "%Y-%m-%d").date()
        start_time = datetime.datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.datetime.strptime(end_str, "%H:%M").time()

        start_dt = datetime.datetime.combine(date_obj, start_time)
        end_dt = datetime.datetime.combine(date_obj, end_time)
        if start_dt >= end_dt:
            raise ValueError("La hora de inicio debe ser anterior a la de fin.")

        context.user_data["start_dt"] = start_dt
        context.user_data["end_dt"] = end_dt

        keyboard = [
            [InlineKeyboardButton("✅ Confirmar", callback_data="confirm_roster_schedule")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_roster_setup")]
        ]
        await update.message.reply_text(
            f"Fecha: {date_part}\nHora inicio: {start_str}\nHora fin: {end_str}\n\n"
            "¿Deseas programar este rango?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await update.message.reply_text(
            "❌ Formato inválido.\n"
            "Usa: `YYYY-MM-DD HH:MM-HH:MM`\n\n"
            "Ejemplo: `2025-01-10 07:00-08:30`",
            parse_mode="Markdown"
        )
        context.user_data["waiting_for_date_time"] = True  # reintentamos



async def confirm_roster_schedule(update, context: CallbackContext) -> None:
    """
    1) Usamos JobQueue para programar el envío de check-in al canal.
    2) El jobQueue llamará a send_checkin_message en la hora indicada.
    """
    query = update.callback_query
    await query.answer()

    dt = context.user_data.get("checkin_datetime")
    roster_list = context.user_data.get("roster_list", [])

    if not dt or not roster_list:
        await query.message.edit_text("No hay fecha/hora o lista. Operación cancelada.")
        return

    # Programamos el job
    job_queue = context.job_queue
    job_queue.run_once(
        send_checkin_message,
        when=dt,
        data={"roster_list": roster_list},
        name="checkin_job"
    )

    await query.message.edit_text(
        f"✅ Check-in programado para {dt}. Se enviará al canal en la hora indicada.",
        parse_mode="HTML"
    )


async def send_checkin_message(context: CallbackContext):
    """
    Se ejecuta automáticamente a la hora programada.
    Envía el mensaje de check-in al canal, mencionando a cada usuario si corresponde.
    """
    job_data = context.job.data  # data={"roster_list": ...}
    roster_list = job_data["roster_list"]

    user_db = load_users()

    # Construimos menciones
    mentions = []
    for name in roster_list:
        match = next(
            (user_info for user_info in user_db["approved"].values()
             if user_info["name"] == name),
            None
        )
        if match:
            mentions.append(f"@{match['username']}")

    if not mentions:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text="No se detectaron usuarios registrados para el check-in."
        )
        return

    # Mensaje final
    text = (
        "<b>¡Check-in abierto!</b>\n\n"
        "Conductores programados:\n"
        + "\n".join(mentions)
        + "\n\nPulsa el botón para confirmar tu asistencia."
    )

    # Botón de check-in
    keyboard = [[InlineKeyboardButton("Check-in", callback_data="do_checkin")]]
    markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        parse_mode="HTML",
        reply_markup=markup
    )


async def cancel_roster_setup(update: Update, context: CallbackContext) -> None:
    """
    Cancela todo el proceso.
    """
    query = update.callback_query
    await query.answer()

    # Limpiamos variables temporales
    context.user_data.pop("roster_list", None)
    context.user_data.pop("checkin_datetime", None)
    context.user_data.pop("waiting_for_date_time", None)

    await query.message.edit_text("❌ Proceso cancelado.")


def register_checkin_handlers(app):
    """
    Registra los handlers necesarios.
    Asegúrate de llamar a register_checkin_handlers(app) en tu main.py.
    """

    # Nota: si ya tienes un CommandHandler("roster", ...) en otra parte,
    # haz que llame a 'start_checkin' al recibir la lista.
    # O bien puedes usar ConversationHandler; esto es un ejemplo simplificado.

    # CallbackQueries
    app.add_handler(CallbackQueryHandler(ask_date_time, pattern="^ask_date_time$"))
    app.add_handler(CallbackQueryHandler(confirm_roster_schedule, pattern="^confirm_roster_schedule$"))
    app.add_handler(CallbackQueryHandler(cancel_roster_setup, pattern="^cancel_roster_setup$"))

    # El check-in final (cuando el conductor pulsa el botón "Check-in")
    # se maneja con un CallbackQueryHandler en main.py o aquí, como prefieras.
    # Podrías hacer algo como:
    # app.add_handler(CallbackQueryHandler(checkin_button_callback, pattern="^do_checkin$"))

    # Manejo del input de fecha/hora (texto).
    # Necesitas un MessageHandler que capture el texto mientras se espera la fecha.
    # Ejemplo:
    # from telegram.ext import MessageHandler, filters
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_input))

    # OJO: Asegúrate de que no choque con otros MessageHandlers que tengas para /start u otros.
