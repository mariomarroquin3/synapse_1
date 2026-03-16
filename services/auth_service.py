import bcrypt
from typing import Tuple, Dict, Any

from models.user_model import (
    get_user_by_email,
    update_last_login,
    get_user_by_id,
    update_user_password
)
from utils.security import verify_password as verify_pwd, validate_password, hash_password


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


def change_password(user_id: int, current_password: str, new_password: str) -> Tuple[bool, str]:
    """
    Cambia la contraseña de un usuario.
    
    Validaciones:
    1. Usuario existe y está activo
    2. Contraseña actual es correcta
    3. Nueva contraseña cumple requisitos de complejidad
    4. Nueva contraseña es diferente a la actual
    
    Args:
        user_id (int): ID del usuario
        current_password (str): Contraseña actual en texto plano
        new_password (str): Nueva contraseña en texto plano
        
    Returns:
        Tuple[bool, str]: (success: bool, message: str)
        
    Example:
        >>> success, msg = change_password(123, "OldPass123!", "NewPass456!")
        >>> if success:
        ...     print("Contraseña actualizada")
        ... else:
        ...     print(f"Error: {msg}")
    """
    print(f"[AUTH_SERVICE] Intentando cambio de contraseña para user_id={user_id}")
    
    try:
        # 1. Verificar que el usuario existe
        user = get_user_by_id(user_id)
        if not user:
            print(f"[AUTH_SERVICE] Usuario {user_id} no encontrado")
            return False, "Usuario no encontrado"
        
        # 2. Verificar que está activo
        if not user.get('is_active', False):
            print(f"[AUTH_SERVICE] Usuario {user_id} inactivo")
            return False, "Tu cuenta está inactiva"
        
        # 3. Verificar contraseña actual
        stored_hash = user.get('password_hash', '')
        if not verify_password(current_password, stored_hash):
            print(f"[AUTH_SERVICE] Contraseña actual incorrecta para user_id={user_id}")
            return False, "La contraseña actual es incorrecta"
        
        # 4. Validar nueva contraseña
        is_valid, missing_reqs = validate_password(new_password)
        if not is_valid:
            missing_text = ", ".join(missing_reqs)
            print(f"[AUTH_SERVICE] Nueva contraseña no cumple requisitos: {missing_text}")
            return False, f"Requisitos faltantes: {missing_text}"
        
        # 5. Verificar que nueva contraseña es diferente
        if verify_password(new_password, stored_hash):
            print(f"[AUTH_SERVICE] Nueva contraseña es igual a la actual")
            return False, "La nueva contraseña debe ser diferente a la actual"
        
        # 6. Hash de la nueva contraseña (DESPUÉS de validación)
        new_hash = hash_password(new_password)
        
        # 7. Actualizar en base de datos
        update_user_password(user_id, new_hash)
        
        print(f"[AUTH_SERVICE] ✅ Contraseña actualizada exitosamente para user_id={user_id}")
        return True, "Contraseña actualizada exitosamente"
        
    except Exception as e:
        error_msg = f"Error al cambiar contraseña: {str(e)}"
        print(f"[AUTH_SERVICE] ❌ {error_msg}")
        return False, error_msg