import bcrypt
import re
from typing import Tuple, List


def validate_password(password: str) -> Tuple[bool, List[str]]:
    """
    Valida una contraseña contra requisitos de complejidad.
    
    Requisitos:
    - Mínimo 8 caracteres
    - Al menos una MAYÚSCULA (A-Z)
    - Al menos una minúscula (a-z)
    - Al menos un número (0-9)
    - Al menos un carácter especial (!@#$%^&*)
    
    Args:
        password (str): Contraseña en texto plano a validar
        
    Returns:
        Tuple[bool, List[str]]: 
            - bool: True si la contraseña cumple todos los requisitos
            - List[str]: Lista de requisitos faltantes (vacía si cumple todos)
            
    Example:
        >>> is_valid, missing = validate_password("Test123!")
        >>> is_valid
        True
        >>> missing
        []
        
        >>> is_valid, missing = validate_password("test123")
        >>> is_valid
        False
        >>> missing
        ['Mínimo 8 caracteres', 'Al menos una MAYÚSCULA', 'Carácter especial']
    """
    missing_requirements = []
    
    if not password:
        return False, [
            "Mínimo 8 caracteres",
            "Al menos una MAYÚSCULA",
            "Al menos una minúscula",
            "Al menos un número",
            "Carácter especial (!@#$%^&*)"
        ]
    
    # Validación 1: Mínimo 8 caracteres
    if len(password) < 8:
        missing_requirements.append("Mínimo 8 caracteres")
    
    # Validación 2: Al menos una MAYÚSCULA
    if not re.search(r'[A-Z]', password):
        missing_requirements.append("Al menos una MAYÚSCULA")
    
    # Validación 3: Al menos una minúscula
    if not re.search(r'[a-z]', password):
        missing_requirements.append("Al menos una minúscula")
    
    # Validación 4: Al menos un número
    if not re.search(r'[0-9]', password):
        missing_requirements.append("Al menos un número")
    
    # Validación 5: Al menos un carácter especial
    if not re.search(r'[!@#$%^&*]', password):
        missing_requirements.append("Carácter especial (!@#$%^&*)")
    
    is_valid = len(missing_requirements) == 0
    return is_valid, missing_requirements


def hash_password(password: str) -> str:
    """
    Genera un hash seguro usando bcrypt.
    
    IMPORTANTE: Asegúrate de que la contraseña haya pasado validate_password()
    antes de llamar a esta función.
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