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

    # Strip whitespace from stored_hash (common issue with Access database)
    stored_hash = stored_hash.strip()
    
    password_bytes = password.encode("utf-8")
    stored_hash_bytes = stored_hash.encode("utf-8")

    try:
        result = bcrypt.checkpw(password_bytes, stored_hash_bytes)
    except ValueError as e:
        print(f"[DEBUG] Error verificando hash: {e}")
        print(f"[DEBUG] Hash recibido: {stored_hash[:20]}...")
        return False

    print(f"[DEBUG] Resultado verificación: {result}")

    return result