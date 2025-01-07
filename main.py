# main.py

from config import BOT_TOKEN, CHANNEL_ID
from handlers import (
    main_menu,
    list_users,
    remove_user,
    confirm_remove_user,
    delete_user,
    edit_user,
    request_new_name,
    save_new_name,
    refresh_menu,
    back_to_menu,
    roster_menu,  # Botón "Roster"
    pending_requests,
    approve_user,
    deny_user
)
from checkin_handler import (
    register_checkin_handlers,
    start_checkin,
    handle_date_input,
    ask_date_time
)
from database import load_users, save_database
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Botón "Check-in"
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)

    if query.data == "do_checkin":
        data = load_users()
        if user_id in data["approved"]:
            data["approved"][user_id]["checked_in"] = True
            save_database(data)
            await query.answer("¡Check-in registrado!")
        else:
            await query.answer("No estás en la lista aprobada.")

# /prueba (opcional)
async def prueba_publicar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Check-in", callback_data="do_checkin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    data = load_users()
    text_lines = ["Usuarios registrados:"]
    for uid, info in data["approved"].items():
        status = "✅" if info.get("checked_in") else "❌"
        text_lines.append(f"- {info['name']} {status}")

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text="\n".join(text_lines),
        reply_markup=reply_markup
    )

# Maneja la lista de nombres cuando se pulsa “Roster”
async def handle_roster_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_for_roster"):
        context.user_data["waiting_for_roster"] = False
        await start_checkin(update, context)
    else:
        pass

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # 1) Handlers de comandos
    app.add_handler(CommandHandler("start", main_menu))
    app.add_handler(CommandHandler("prueba", prueba_publicar))

    # 2) Botones principales (CallbackQueryHandler) – Menú Admin
    app.add_handler(CallbackQueryHandler(list_users, pattern="^list_users$"))
    app.add_handler(CallbackQueryHandler(remove_user, pattern="^remove_user$"))
    app.add_handler(CallbackQueryHandler(confirm_remove_user, pattern="^remove_.*"))
    app.add_handler(CallbackQueryHandler(confirm_remove_user, pattern="^confirm_remove_.*"))
    app.add_handler(CallbackQueryHandler(delete_user, pattern="^delete_.*"))
    app.add_handler(CallbackQueryHandler(edit_user, pattern="^edit_user$"))
    app.add_handler(CallbackQueryHandler(request_new_name, pattern="^edit_.*"))
    app.add_handler(CallbackQueryHandler(refresh_menu, pattern="^refresh$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back$"))
    app.add_handler(CallbackQueryHandler(roster_menu, pattern="^roster$"))
    # OJO: Ajusta el pattern a lo que tengas en el botón Roster, p.ej. "^roster$"

    # 3) Subflujos (ej. pedir fecha/hora)
    #    Si "ask_date_time" está en checkin_handler.py, impórtalo y agrégalo aquí.
    app.add_handler(CallbackQueryHandler(ask_date_time, pattern="^ask_date_time$"))

    # 4) Maneja fecha/hora del check-in (nuevo flujo)
    #    Este MessageHandler se activa cuando user_data["waiting_for_date_time"] = True
    #    y el usuario escribe "2025-01-07 07:00-08:30", etc.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_input))

    # 5) Maneja la lista de nombres (cuando se pulsa “Roster” y se setea waiting_for_roster)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_roster_text))

    # 6) Resto de tus flujos antiguos (procesos extra).
    #    Si ya no usas process_all, quítalo.
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_all))  # <-- QUITA si no lo usas

    # 7) Resto de CallbackQueryHandlers (Aprobar/Denegar usuarios)
    app.add_handler(CallbackQueryHandler(pending_requests, pattern="^pending_requests$"))
    app.add_handler(CallbackQueryHandler(approve_user, pattern="^approve_.*"))
    app.add_handler(CallbackQueryHandler(deny_user, pattern="^deny_.*"))

    # 8) Handlers genéricos de mensajes (si usas save_new_name o similar)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_name))

    # 9) Registra handlers específicos del checkin_handler
    register_checkin_handlers(app)

    # 10) Botón "Check-in"
    app.add_handler(CallbackQueryHandler(button_callback, pattern="^do_checkin$"))

    # 11) Corre la app
    app.run_polling()

if __name__ == "__main__":
    main()
