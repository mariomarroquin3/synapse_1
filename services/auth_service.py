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
    Retorna tupla (success: bool, result: dict | str)
    """

    print(f"[DEBUG] Intentando login para: {email}")

    user = get_user_by_email(email)

    if not user:
        print("[DEBUG] Usuario no encontrado.")
        return False, "Usuario no encontrado"

    # user ahora es un diccionario gracias al Dictionary Wrapper
    user_id = user['Id_user']
    password_hash = user['password_hash']
    is_active = user['is_active']

    if not is_active:
        print("[DEBUG] Usuario inactivo.")
        return False, "Usuario inactivo"

    if not verify_password(password, password_hash):
        print("[DEBUG] Contraseña incorrecta.")
        return False, "Credenciales incorrectas"

    update_last_login(user_id)

    print("[DEBUG] Login exitoso.")
    return True, user