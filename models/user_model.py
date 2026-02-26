from config.database import get_cursor
from models.user_model import create_user, get_user_by_email, get_user_by_dui, get_user_by_phone
from services.account_service import create_account_for_user  # <--- Agregar esta línea
from utils.security import hash_password, verify_password

def create_user(role_id: int, email: str, password_hash: str, nit: str | None, 
                dui: str, full_name: str, gender: str, phone_number: str | None, 
                is_active: bool = True) -> int:
    
    query = """
        INSERT INTO [user] (
            role_id, email, password_hash, NIT, DUI, 
            full_name, gender, phone_number, created_at, updated_at, is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, Now(), Now(), ?)
    """

    # We use the 'with' block to ensure the cursor is active
    with get_cursor(commit=True) as cursor:
        # Step 1: Execute the Insert
        cursor.execute(query, (
            role_id, email, password_hash, nit, dui, 
            full_name, gender, phone_number, is_active
        ))
        
        # Step 2: Get the ID immediately after
        # Use a semicolon for some providers, or a separate execute
        cursor.execute("SELECT @@IDENTITY")
        row = cursor.fetchone()
        
        if row is None:
            raise Exception("Database failed to return the new User ID.")
            
        new_id = int(row[0])
        print(f"[DEBUG] User created successfully with ID: {new_id}")
        return new_id
def get_user_by_email(email: str):
    """
    Retorna un usuario por email.
    Devuelve None si no existe.
    """

    print("[DEBUG] Buscando usuario por email...")

    query = "SELECT * FROM user WHERE email = ?"

    with get_cursor() as cursor:
        cursor.execute(query, (email,))
        row = cursor.fetchone()

        if row:
            print("[DEBUG] Usuario encontrado.")
        else:
            print("[DEBUG] Usuario no encontrado.")

        return row


def get_user_by_dui(dui: str):
    """
    Retorna un usuario por DUI.
    Útil para validar duplicados antes de insertar.
    """
    print(f"[DEBUG] Buscando usuario por DUI: {dui}")
    query = "SELECT * FROM user WHERE DUI = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (dui,))
        return cursor.fetchone()


def get_user_by_phone(phone_number: str):
    """
    Retorna un usuario por número de teléfono.
    Útil para validar duplicados antes de insertar.
    """
    print(f"[DEBUG] Buscando usuario por teléfono: {phone_number}")
    query = "SELECT * FROM user WHERE phone_number = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (phone_number,))
        return cursor.fetchone()


def get_user_by_id(user_id: int):
    """
    Retorna un usuario por ID.
    """

    print("[DEBUG] Buscando usuario por ID...")

    query = "SELECT * FROM [user] WHERE [Id_user] = ?"

    with get_cursor() as cursor:
        cursor.execute(query, (user_id,))
        return cursor.fetchone()


def update_last_login(user_id: int) -> None:
    """
    Actualiza la fecha de último login.
    """

    print("[DEBUG] Actualizando último login...")

    query = """
        UPDATE [user]
        SET updated_at = Now()
        WHERE id = ?
    """ # Se corrigió Id_user a id para consistencia con get_user_by_id

    with get_cursor(commit=True) as cursor:
        cursor.execute(query, (user_id,))

    print("[DEBUG] Último login actualizado.")