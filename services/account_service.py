from models.account_model import (
    create_account,
    get_account_by_user
)
from models.user_model import get_user_by_id


def create_account_for_user(user_id: int, currency: str):
    """
    Crea una nueva cuenta para un usuario.
    
    REGLA: Un usuario solo puede tener una cuenta.
    
    Args:
        user_id (int): ID del usuario propietario
        currency (str): Moneda de la cuenta (e.g., 'USD', 'SVC')
        
    Returns:
        dict: Resultado de la operación {'success': bool, 'account_id': int, 'error': str}
        
    Raises:
        Exception: Si el usuario no existe o ya tiene cuenta
    """

    # Busca el usuario por ID (ahora retorna diccionario)
    user = get_user_by_id(user_id)

    # Si no existe, lanza error
    if not user:
        raise Exception(f"El usuario con ID {user_id} no existe.")

    # Verifica si ya tiene una cuenta creada
    existing_account = get_account_by_user(user_id)
    if existing_account:
        raise Exception(f"El usuario '{user['full_name']}' ya tiene una cuenta asociada.")

    # Si pasa las validaciones, crea la cuenta
    account_id = create_account(user_id, currency)
    
    print(f"[ACCOUNT] ✅ Cuenta creada exitosamente para usuario {user['full_name']} (ID: {user_id})")
    return {
        "success": True,
        "account_id": account_id,
        "user_id": user_id,
        "user_name": user['full_name']
    }