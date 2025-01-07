import json
import os

DB_FILE = 'users_db.json'

# Crear o cargar base de datos con estructura existente
def initialize_database():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as file:
            json.dump({"approved": {}, "pending": {}}, file, indent=4)
    else:
        with open(DB_FILE, 'r') as file:
            try:
                data = json.load(file)
                if "approved" not in data:
                    data["approved"] = {}
                if "pending" not in data:
                    data["pending"] = {}
                with open(DB_FILE, 'w') as file:
                    json.dump(data, file, indent=4)
            except json.JSONDecodeError:
                with open(DB_FILE, 'w') as file:
                    json.dump({"approved": {}, "pending": {}}, file, indent=4)

# Llamar a la inicialización
initialize_database()

# Funciones existentes
def load_users():
    with open(DB_FILE, 'r') as file:
        return json.load(file)

def save_database(data):
    with open(DB_FILE, 'w') as file:
        json.dump(data, file, indent=4)


# Añadir usuario aprobado
def add_user(user_id, name, username):
    db = load_users()
    if "approved" not in db:
        db["approved"] = {}
    db["approved"][str(user_id)] = {"name": name, "username": username, "id": user_id}
    save_database(db)

# Añadir usuario pendiente
def add_pending_user(user_id, name, username):
    db = load_users()
    if "pending" not in db:
        db["pending"] = {}
    db["pending"][str(user_id)] = {"name": name, "username": username, "id": user_id}
    save_database(db)

# Eliminar usuario aprobado
def remove_user(user_id):
    db = load_users()
    if "approved" in db and str(user_id) in db["approved"]:
        del db["approved"][str(user_id)]
    save_database(db)

# Obtener todos los usuarios aprobados
def get_all_users():
    db = load_users()
    return db.get("approved", {})

# Obtener usuarios pendientes
def get_pending_users():
    db = load_users()
    return db.get("pending", {})

# Verificar si el usuario existe
def user_exists(user_id):
    db = load_users()
    return str(user_id) in db.get("approved", {})
