import bcrypt
from database import get_connection
from models.user_model import get_user_by_username


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara contraseña en texto plano con hash almacenado.
    """
    try:
        print("Verificando contraseña...")
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception as e:
        print("Error verificando password:", e)
        return False


def update_last_login(user_id: int):
    """
    Actualiza el campo last_login en Access.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        UPDATE user
        SET last_login = AHORA()
        WHERE id = ?
        """

        cursor.execute(query, (user_id,))
        conn.commit()

        cursor.close()
        conn.close()

        print(f"Last login actualizado para user_id={user_id}")

    except Exception as e:
        print("Error actualizando last_login:", e)


def login(username: str, password: str):
    """
    Autentica usuario.
    Retorna (True, user_data) si éxito.
    Retorna (False, mensaje_error) si falla.
    """

    print(f"Intentando login para: {username}")

    user = get_user_by_username(username)

    if not user:
        print("Usuario no encontrado")
        return False, "Usuario no encontrado"

    # Si tu user_model devuelve tupla, ajusta índices.
    # Asumamos que devuelve dict:
    # user = {
    #   "id": ...,
    #   "username": ...,
    #   "password_hash": ...,
    #   "is_active": ...
    # }

    if not user["is_active"]:
        print("Usuario inactivo")
        return False, "Usuario inactivo"

    if not verify_password(password, user["password_hash"]):
        print("Password incorrecto")
        return False, "Credenciales incorrectas"

    update_last_login(user["id"])

    print("Login exitoso")
    return True, user