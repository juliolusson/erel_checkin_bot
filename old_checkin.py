from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import json
from datetime import datetime
from pytz import timezone

# Cargar base de datos
def load_users():
    with open('users_db.json', 'r') as file:
        return json.load(file)

# Procesar nombres y horarios en un solo flujo
async def process_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Obtener texto enviado
        text = update.message.text

        # Dividir en líneas
        lines = text.strip().split("\n")
        nombres_lista = lines[:-1]  # Todos menos la última línea
        fecha_hora = lines[-1]  # Última línea para fecha y hora

        # Validar nombres
        db = load_users()
        approved_users = db.get('approved', {})
        resultados = []

        for nombre in nombres_lista:
            asignado = False
            for user_id, info in approved_users.items():
                if info['name'].lower() == nombre.lower():
                    resultados.append(f"✅ {nombre} - @{info['username']}")
                    asignado = True
                    break
            if not asignado:
                resultados.append(f"❌ {nombre} - *Usuario no encontrado*")

        # Validar formato de fecha y hora
        fecha, horas = fecha_hora.split(" ")  # Separar fecha y horas
        inicio, fin = horas.split("-")  # Separar inicio y fin

        # Validar fecha y horas
        datetime.strptime(fecha, "%m-%d-%Y")  # MM-DD-YYYY
        datetime.strptime(inicio, "%H:%M")   # HH:MM
        datetime.strptime(fin, "%H:%M")      # HH:MM

        if inicio >= fin:
            raise ValueError("La hora de inicio debe ser antes que la hora de fin.")

        # Guardar datos en contexto
        context.user_data['schedule'] = {
            'fecha': fecha,
            'inicio': inicio,
            'fin': fin
        }

        # Confirmar resultados
        mensaje_resultado = (
            "📋 *Resultados del Roster:*\n" + "\n".join(resultados) + "\n\n"
            "🕒 *Programación guardada:*\n"
            f"📅 Fecha: {fecha}\n"
            f"⏰ Horario: {inicio}-{fin}\n\n"
            "Confirma si deseas continuar o cancelar."
        )
        botones = [
            [InlineKeyboardButton("✅ Confirmar", callback_data='confirm_roster')],
            [InlineKeyboardButton("❌ Cancelar", callback_data='cancel_roster')]
        ]


        await update.message.reply_text(
            mensaje_resultado,
            reply_markup=InlineKeyboardMarkup(botones),
            parse_mode="Markdown"
        )

    except Exception as e:
        # Enviar error en formato
        print(f"Error detectado: {e}")  # Mostrar en consola para depuración
        await update.message.reply_text(
            "❌ *Formato inválido.*\n"
            "Por favor usa el formato correcto:\n"
            "`MM-DD-YYYY HH:MM-HH:MM`\n\n"
            "✅ *Ejemplo:* 01-06-2025 07:00-08:30",
            parse_mode="Markdown"
        )

async def confirm_roster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Confirmar programación al administrador
    await update.callback_query.message.reply_text("✅ Programación confirmada.")
    await update.callback_query.answer()

    # Obtener programación desde el contexto
    schedule = context.user_data.get('schedule', {})
    fecha = schedule.get('fecha')
    inicio = schedule.get('inicio')

    # Ajustar zona horaria (reemplaza 'America/New_York' por tu zona si es diferente)
    local_tz = timezone('America/New_York')
    fecha_hora_local = local_tz.localize(datetime.strptime(f"{fecha} {inicio}", "%m-%d-%Y %H:%M"))
    fecha_hora_utc = fecha_hora_local.astimezone(timezone('UTC'))

    # Programar el trabajo en UTC
    context.job_queue.run_once(send_to_channel, fecha_hora_utc, chat_id='-1002253871334', name="roster_job")

async def send_to_channel(context: ContextTypes.DEFAULT_TYPE):
    # Mensaje programado para el canal
    await context.bot.send_message(
        chat_id='-1002253871334',
        text="📋 *Check-in Programado:*\nRecuerda confirmar asistencia.",
        parse_mode="Markdown"
    )


async def schedule_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Obtener los detalles de la programación
    schedule = context.user_data.get('schedule', {})
    fecha = schedule.get('fecha')
    inicio = schedule.get('inicio')

    # Formato combinado para fecha y hora
    fecha_hora = datetime.strptime(f"{fecha} {inicio}", "%m-%d-%Y %H:%M")

    # Programar mensaje en el canal
    context.job_queue.run_once(
        callback=send_to_channel,  # Función que enviará el mensaje
        when=fecha_hora,          # Fecha y hora programadas
        chat_id='-1002253871334', # ID del canal
        name="roster_job"         # Nombre del job
    )

async def send_to_channel(context: ContextTypes.DEFAULT_TYPE):
    # Enviar el mensaje programado
    await context.bot.send_message(
        chat_id='-1002253871334',
        text="📋 *Check-in Programado:*\nRecuerda confirmar asistencia.",
        parse_mode="Markdown"
    )


async def cancel_roster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("❌ Programación cancelada.")
    await update.callback_query.answer()

