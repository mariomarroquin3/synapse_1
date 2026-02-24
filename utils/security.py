import bcrypt


def hash_password(password: str) -> str:
    """
    Genera un hash seguro usando bcrypt.
    """
    print("[DEBUG] Iniciando hash de contraseña...")

    if not password:
        raise ValueError("La contraseña no puede estar vacía.")

    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()

    hashed = bcrypt.hashpw(password_bytes, salt)

    print("[DEBUG] Hash generado correctamente.")

    # Guardamos como string para almacenar en Access
    return hashed.decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifica si la contraseña coincide con el hash almacenado.
    """
    print("[DEBUG] Verificando contraseña...")

    if not password or not stored_hash:
        print("[DEBUG] Password o hash vacío.")
        return False

    password_bytes = password.encode("utf-8")
    stored_hash_bytes = stored_hash.encode("utf-8")

    result = bcrypt.checkpw(password_bytes, stored_hash_bytes)

    print(f"[DEBUG] Resultado verificación: {result}")

    return result