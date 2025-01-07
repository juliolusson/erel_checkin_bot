from handlers import roster_menu
from checkin import process_all, confirm_roster, cancel_roster
from checkin_handler import register_checkin_handlers
from config import BOT_TOKEN, ADMIN_ID
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from handlers import (
    main_menu,
    get_main_menu,
    list_users,
    remove_user,
    confirm_remove_user,
    delete_user,
    edit_user,
    request_new_name,
    save_new_name,
    refresh_menu,
    back_to_menu,
    pending_requests,
    approve_user,
    deny_user,
)

# Iniciar el bot
app = ApplicationBuilder().token(BOT_TOKEN).post_init(lambda app: app.job_queue.start()).build()


# Función para verificar si es admin
def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID


# Comandos
app.add_handler(CommandHandler("start", main_menu))

# Botones – Solo accesibles para el admin
app.add_handler(CallbackQueryHandler(list_users, pattern="list_users"))
app.add_handler(CallbackQueryHandler(remove_user, pattern="remove_user"))
app.add_handler(CallbackQueryHandler(confirm_remove_user, pattern="remove_.*"))
app.add_handler(CallbackQueryHandler(confirm_remove_user, pattern="confirm_remove_.*"))
app.add_handler(CallbackQueryHandler(delete_user, pattern="delete_.*"))
app.add_handler(CallbackQueryHandler(edit_user, pattern="edit_user"))
app.add_handler(CallbackQueryHandler(request_new_name, pattern="edit_.*"))
app.add_handler(CallbackQueryHandler(refresh_menu, pattern="refresh"))
app.add_handler(CallbackQueryHandler(back_to_menu, pattern="back"))
app.add_handler(CallbackQueryHandler(roster_menu, pattern='^roster$'))



# Aprobar/Denegar usuarios
app.add_handler(CallbackQueryHandler(pending_requests, pattern="pending_requests"))
app.add_handler(CallbackQueryHandler(approve_user, pattern="approve_.*"))
app.add_handler(CallbackQueryHandler(deny_user, pattern="deny_.*"))

# Manejadores para el botón "Roster" y check-in
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_all))
app.add_handler(CallbackQueryHandler(confirm_roster, pattern='^confirm_roster$'))
app.add_handler(CallbackQueryHandler(cancel_roster, pattern='^cancel_roster$'))


# Guardar nuevo nombre después de edición
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_name))

# Registro para Check-in
register_checkin_handlers(app)

# Iniciar el bot
app.run_polling()
