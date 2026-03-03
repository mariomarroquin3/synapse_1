from config.database import get_cursor
# Se eliminó la auto-importación circular para evitar el ImportError
# Se eliminó la importación de account_service aquí para evitar dependencia cruzada
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
        cursor.execute("SELECT @@IDENTITY")
        row = cursor.fetchone()
        
        if row is None:
            raise Exception("Database failed to return the new User ID.")
            
        new_id = int(row[0])
        print(f"[DEBUG] User created successfully with ID: {new_id}")
        return new_id

def get_user_by_email(email: str):
    """
    Retorna un usuario por email como un diccionario.
    Devuelve None si no existe.
    """
    print("[DEBUG] Buscando usuario por email...")
    query = "SELECT * FROM [user] WHERE email = ?"

    with get_cursor() as cursor:
        cursor.execute(query, (email,))
        row = cursor.fetchone()

        if row:
            print("[DEBUG] Usuario encontrado.")
            # Convert tuple to dictionary using column names
            user_dict = dict(zip([col[0] for col in cursor.description], row))
            return user_dict
        else:
            print("[DEBUG] Usuario no encontrado.")
            return None

def get_user_by_dui(dui: str):
    """
    Retorna un usuario por DUI como un diccionario.
    Útil para validar duplicados antes de insertar.
    Devuelve None si no existe.
    """
    print(f"[DEBUG] Buscando usuario por DUI: {dui}")
    query = "SELECT * FROM [user] WHERE DUI = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (dui,))
        row = cursor.fetchone()
        if row:
            return dict(zip([col[0] for col in cursor.description], row))
        return None

def get_user_by_phone(phone_number: str):
    """
    Retorna un usuario por número de teléfono como un diccionario.
    Útil para validar duplicados antes de insertar.
    Devuelve None si no existe.
    """
    print(f"[DEBUG] Buscando usuario por teléfono: {phone_number}")
    query = "SELECT * FROM [user] WHERE phone_number = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (phone_number,))
        row = cursor.fetchone()
        if row:
            return dict(zip([col[0] for col in cursor.description], row))
        return None

def get_user_by_id(user_id: int):
    """
    Retorna un usuario por ID como un diccionario.
    Devuelve None si no existe.
    """
    print("[DEBUG] Buscando usuario por ID...")
    query = "SELECT * FROM [user] WHERE [Id_user] = ?"

    with get_cursor() as cursor:
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        
        if row:
            # Convert tuple to dictionary using column names
            user_dict = dict(zip([col[0] for col in cursor.description], row))
            print(f"[DEBUG] Usuario encontrado: {user_dict['full_name']}")
            return user_dict
        else:
            print("[DEBUG] Usuario no encontrado.")
            return None

def update_last_login(user_id: int) -> None:
    """
    Actualiza la fecha de último login.
    """
    print("[DEBUG] Actualizando último login...")
    query = """
        UPDATE [user]
        SET updated_at = Now()
        WHERE [Id_user] = ?
    """ 

    with get_cursor(commit=True) as cursor:
        cursor.execute(query, (user_id,))

    print("[DEBUG] Último login actualizado.")


def get_users_by_role_category(is_staff: bool):
    """
    Retorna una lista de usuarios (como diccionarios).
    Si is_staff es True, retorna roles 1, 3, 4, 5.
    Si is_staff es False, retorna rol 2 (Clientes).
    """
    if is_staff:
        query = "SELECT * FROM [user] WHERE role_id IN (1, 3, 4, 5)"
    else:
        query = "SELECT * FROM [user] WHERE role_id = 2"

    with get_cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


def update_user_status(user_id: int, is_active: bool) -> bool:
    """
    Activa o suspende una cuenta de usuario.
    """
    query = "UPDATE [user] SET is_active = ?, updated_at = Now() WHERE Id_user = ?"
    with get_cursor(commit=True) as cursor:
        cursor.execute(query, (is_active, user_id))
        return cursor.rowcount > 0


def update_user_role(user_id: int, role_id: int) -> bool:
    """
    Actualiza el rol de un usuario.
    """
    query = "UPDATE [user] SET role_id = ?, updated_at = Now() WHERE Id_user = ?"
    with get_cursor(commit=True) as cursor:
        cursor.execute(query, (role_id, user_id))
        return cursor.rowcount > 0