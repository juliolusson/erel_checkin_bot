import json
import os

DB_FILE = 'users_db.json'

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
                with open(DB_FILE, 'w') as file_w:
                    json.dump(data, file_w, indent=4)
            except json.JSONDecodeError:
                with open(DB_FILE, 'w') as file_w:
                    json.dump({"approved": {}, "pending": {}}, file_w, indent=4)

initialize_database()

def load_users():
    with open(DB_FILE, 'r') as file:
        return json.load(file)

def save_database(data):
    with open(DB_FILE, 'w') as file:
        json.dump(data, file, indent=4)

def add_user(user_id, name, username):
    db = load_users()
    if "approved" not in db:
        db["approved"] = {}
    # Se añade "checked_in": False para el nuevo usuario aprobado
    db["approved"][str(user_id)] = {
        "name": name,
        "username": username,
        "id": user_id,
        "checked_in": False
    }
    save_database(db)

def add_pending_user(user_id, name, username):
    db = load_users()
    if "pending" not in db:
        db["pending"] = {}
    db["pending"][str(user_id)] = {"name": name, "username": username, "id": user_id}
    save_database(db)

def remove_user(user_id):
    db = load_users()
    if "approved" in db and str(user_id) in db["approved"]:
        del db["approved"][str(user_id)]
    save_database(db)

def get_all_users():
    db = load_users()
    return db.get("approved", {})

def get_pending_users():
    db = load_users()
    return db.get("pending", {})

def user_exists(user_id):
    db = load_users()
    return str(user_id) in db.get("approved", {})

# Función para marcar check-in (true/false) de un usuario en "approved"
def set_check_in(user_id, status=True):
    db = load_users()
    if str(user_id) in db["approved"]:
        db["approved"][str(user_id)]["checked_in"] = status
        save_database(db)
