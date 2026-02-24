import bcrypt

from models.user_model import (
    get_user_by_email,
    update_last_login
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara contraseña en texto plano con hash almacenado.
    """
    print("[DEBUG] Verificando contraseña...")

    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def login(email: str, password: str):
    """
    Autentica usuario por email.
    """

    print(f"[DEBUG] Intentando login para: {email}")

    user = get_user_by_email(email)

    if not user:
        print("[DEBUG] Usuario no encontrado.")
        return False, "Usuario no encontrado"

    # ⚠️ IMPORTANTE
    # user es una tupla porque fetchone() devuelve tuple en pyodbc
    # Debemos acceder por índice

    # Ajusta estos índices según el orden real de tu tabla
    user_id = user[0]
    password_hash = user[3]   # ajusta si el orden cambia
    is_active = user[9]       # ajusta si el orden cambia

    if not is_active:
        print("[DEBUG] Usuario inactivo.")
        return False, "Usuario inactivo"

    if not verify_password(password, password_hash):
        print("[DEBUG] Contraseña incorrecta.")
        return False, "Credenciales incorrectas"

    update_last_login(user_id)

    print("[DEBUG] Login exitoso.")
    return True, user