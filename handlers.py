from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from database import get_all_users, load_users, save_database
from config import ADMIN_ID
import datetime
import telegram
import json


def get_main_menu():
	buttons = [
		[InlineKeyboardButton("📋 Check-in", callback_data="start_checkin")],
		[InlineKeyboardButton("🔙 Regresar", callback_data="back_main")]
	]
	return InlineKeyboardMarkup(buttons)

# MENÚ PARA USUARIOS NORMALES
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:  # Si no es admin
        # Guardar al usuario en pendientes
        db = get_all_users()

        # Asegurar que 'pending' existe
        if 'pending' not in db:
            db['pending'] = {}  # Crear clave si no existe

        # Añadir usuario a 'pending' si no está ya registrado
        if str(user_id) not in db['pending']:
            db['pending'][str(user_id)] = {
                "name": update.effective_user.full_name,
                "username": update.effective_user.username,
                "id": user_id
            }
            save_database(db)

        # Notificar solicitud enviada
        await update.message.reply_text(
            "Your request has been sent to the admin for approval!"
        )
    else:
        # Mostrar menú completo para el admin en formato de dos columnas
        keyboard = [
            [InlineKeyboardButton("📋 List Users", callback_data='list_users'),
             InlineKeyboardButton("👥 Pending Approvals", callback_data='pending_requests')],
            [InlineKeyboardButton("❌ Remove User", callback_data='remove_user'),
             InlineKeyboardButton("✏️ Edit User", callback_data='edit_user')],
             [InlineKeyboardButton("📝 Roster", callback_data='roster')],
            [InlineKeyboardButton("🔄 Refresh Menu", callback_data='refresh')]
        ]

        # Crear el menú con botones organizados
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Actualizar menú según si es un callback o un mensaje nuevo
        if update.callback_query:
            await update.callback_query.message.edit_text(
                "Admin Menu:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "Admin Menu:",
                reply_markup=reply_markup
            )




# LISTAR USUARIOS APROBADOS
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
	# Cargar la base de datos completa
	db = load_users()
	users = db.get('approved', {})  # Obtener solo los usuarios aprobados

	# Verificar si no hay usuarios aprobados
	if not users:
		message = "No approved users found."
	else:
		# Crear lista de usuarios aprobados
		user_list = "\n".join([
			f"{u['name']} (@{u['username']}) - ID: {uid}"
			for uid, u in users.items()
		])
		message = f"✅ Approved Users:\n\n{user_list}"

	# Botón para regresar
	keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='back')]]
	reply_markup = InlineKeyboardMarkup(keyboard)

	# Mostrar la lista o el mensaje
	await update.callback_query.message.edit_text(message, reply_markup=reply_markup)



# SOLICITUDES PENDIENTES
async def pending_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
	# Cargar la base de datos completa
	db = load_users()
	users = db.get('pending', {})  # Obtener solo los pendientes como diccionario

	# Verificar si no hay solicitudes pendientes
	if not users:
		message = "No pending requests."
		keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='back')]]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await update.callback_query.message.edit_text(message, reply_markup=reply_markup)
		return

	# Construir el teclado dinámico con usuarios pendientes
	keyboard = []
	for uid, u in users.items():
		keyboard.append([
			InlineKeyboardButton(f"{u['name']} (@{u['username']})", callback_data=f"approve_{uid}"),
			InlineKeyboardButton("❌ Deny", callback_data=f"deny_{uid}")
		])

	# Añadir botón para regresar al menú principal
	keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='back')])

	# Mostrar lista de solicitudes pendientes
	reply_markup = InlineKeyboardMarkup(keyboard)
	await update.callback_query.message.edit_text("👥 Pending Requests:", reply_markup=reply_markup)


# APROBAR USUARIO
async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.data.split("_")[-1]  # Obtener ID del usuario

	# Cargar base de datos
	db = load_users()
	pending_users = db.get('pending', {})
	approved_users = db.get('approved', {})

	if user_id in pending_users:
		# Mover a la lista de aprobados
		approved_users[user_id] = pending_users.pop(user_id)
		db['approved'] = approved_users
		db['pending'] = pending_users
		save_database(db)

		# Notificar al usuario aprobado
		try:
			await context.bot.send_message(
				chat_id=user_id,
				text="✅ You have been approved!"
			)
		except Exception:
			pass  # El usuario pudo haber bloqueado el bot

		# Confirmar al admin
		await query.edit_message_text(
			text=f"User {approved_users[user_id]['name']} has been approved."
		)
	else:
		await query.edit_message_text(text="User not found or already approved.")


# DENEGAR USUARIO
async def deny_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.data.split("_")[-1]  # Obtener ID del usuario

	# Cargar base de datos
	db = load_users()
	pending_users = db.get('pending', {})

	if user_id in pending_users:
		# Eliminar de la lista de pendientes
		pending_users.pop(user_id)
		db['pending'] = pending_users
		save_database(db)

		# Notificar al usuario denegado
		try:
			await context.bot.send_message(
				chat_id=user_id,
				text="❌ Your request has been denied."
			)
		except Exception:
			pass  # El usuario pudo haber bloqueado el bot

		# Confirmar al admin
		await query.edit_message_text(
			text=f"User {user_id} has been denied."
		)
	else:
		await query.edit_message_text(text="User not found or already denied.")




# ELIMINAR USUARIO
async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query

	# Obtener la lista de usuarios aprobados
	db = load_users()
	users = db.get('approved', {})  # Revisar la sección 'approved'

	# Verificar si hay usuarios aprobados
	if not users:
		await query.edit_message_text("No approved users found.")
		return

	# Crear botones para seleccionar usuario a eliminar
	keyboard = [
		[InlineKeyboardButton(f"{u['name']} – ID: {uid}", callback_data=f"remove_{uid}")]
		for uid, u in users.items()
	]
	keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='back')])

	# Mostrar menú
	reply_markup = InlineKeyboardMarkup(keyboard)
	await query.edit_message_text("Select a user to remove:", reply_markup=reply_markup)



# CONFIRMAR ELIMINACIÓN DE USUARIO
async def confirm_remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.data.split("_")[-1]  # Obtener ID del usuario

	# Obtener la lista de usuarios aprobados
	db = load_users()
	users = db.get('approved', {})

	if user_id in users:
		# Eliminar al usuario
		user_info = users.pop(user_id)
		db['approved'] = users  # Actualizar la base de datos
		save_database(db)

		# Notificar al usuario eliminado
		try:
			await context.bot.send_message(
				chat_id=user_id,
				text="❌ You have been removed from the system."
			)
		except Exception:
			pass  # El usuario podría haber bloqueado el bot

		# Confirmar al administrador
		await query.edit_message_text(
			text=f"User {user_info['name']} (@{user_info['username']}) has been removed."
		)
	else:
		await query.edit_message_text(text="User not found or already removed.")




# ELIMINAR DEFINITIVO
async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.data.split('_')[1]  # Obtener ID del usuario

	# Cargar base de datos
	db = load_users()
	approved_users = db.get('approved', {})

	# Verificar si el usuario existe
	if user_id in approved_users:
		del approved_users[user_id]  # Eliminar usuario
		db['approved'] = approved_users
		save_database(db)

		# Confirmar eliminación
		await query.message.edit_text(f"User with ID {user_id} removed successfully.")
	else:
		await query.message.edit_text("User not found.")

	# Regresar al menú principal
	await main_menu(update, context)



# REFRESCAR MENÚ — SOLUCIÓN SIMPLIFICADA
async def refresh_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Obtener hora actual de actualización
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Refrescar datos (simula obtener datos actualizados)
    db = load_users()
    users = db.get('approved', {})
    total_users = len(users)

    # Mensaje actualizado
    message = f"✅ Last Updated: {now}\n👥 Total Users: {total_users}"

    # Actualizar solo los datos sin cambiar el menú
    await query.edit_message_text(message)




# VOLVER AL MENÚ
async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await main_menu(update, context)

# EDITAR USUARIO
async def edit_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	await query.answer()

	# Cargar base de datos
	db = load_users()
	users = db.get('approved', {})

	# Verifica si hay usuarios cargados
	if not users:
		await query.message.edit_text("No users available to edit.")
		return

	# Crear botones para los usuarios aprobados
	keyboard = []
	for uid, u in users.items():
		# Verificar claves necesarias
		if 'name' in u and 'id' in u:
			keyboard.append([
				InlineKeyboardButton(
					f"{u['name']} – ID: {uid}",
					callback_data=f"edit_{uid}"
				)
			])

	# Botón para regresar
	keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='back')])

	# Responder con el menú
	reply_markup = InlineKeyboardMarkup(keyboard)

	# Mostrar menú de selección o actualizar si ya está mostrado
	if query.message.text != "Select a user to edit:":
		await query.message.edit_text(
			text="Select a user to edit:",
			reply_markup=reply_markup
		)
	elif query.message.reply_markup != reply_markup:
		# Actualiza solo el teclado si el texto ya es igual
		await query.message.edit_reply_markup(reply_markup=reply_markup)


# SOLICITAR NUEVO NOMBRE PARA USUARIO
async def request_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	await query.answer()

	# Obtener ID del usuario desde el callback_data
	user_id = query.data.split("_")[1]

	# Cargar base de datos
	db = load_users()
	users = db.get('approved', {})

	# Verificar si el usuario existe
	if user_id in users:
		# Guardar ID en contexto
		context.user_data['edit_user_id'] = user_id

		# Solicitar nuevo nombre
		await query.message.edit_text(
			f"Enter a new name for {users[user_id]['name']}:"
		)
	else:
		# Usuario no encontrado
		await query.message.edit_text("User not found.")


# GUARDAR NUEVO NOMBRE
async def save_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
	# Verificar si existe el ID en contexto
	user_id = context.user_data.get('edit_user_id')
	if user_id:
		# Cargar base de datos
		db = get_all_users()
		approved_users = db.get('approved', {})

		# Confirmar ID y actualizar nombre
		if user_id in approved_users:
			approved_users[user_id]['name'] = update.message.text
			save_database(db)

			# Confirmar el cambio
			await update.message.reply_text(
				f"User name updated successfully to: {update.message.text}!"
			)
		else:
			await update.message.reply_text(
				"User not found or already removed."
			)
	else:
		await update.message.reply_text(
			"No user selected for editing."
		)

	# Regresar al menú principal
	await main_menu(update, context)


# Callback para el botón de Roster
async def roster_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["waiting_for_roster"] = True
    await update.callback_query.message.edit_text(
        "Por favor, envíame la lista de nombres (Nombre y Apellido) en líneas separadas.\n\n"
        "*Ejemplo:*\n"
        "`Julio Lusson`\n"
        "`Elite Rider`\n"
        "_Nota: Asegúrate de escribirlos correctamente para que puedan ser asignados._",
        parse_mode="Markdown"
    )
    # Activamos una bandera para que el siguiente mensaje de texto
    # se maneje en la nueva lógica (start_checkin).
    context.user_data["waiting_for_roster"] = True
