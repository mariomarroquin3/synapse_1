from models.account_model import (
    create_account,
    get_account_by_user
)
from models.user_model import get_user_by_id


def create_account_for_user(user_id: int, currency: str):

    # Busca el usuario por ID
    user = get_user_by_id(user_id)

    # Si no existe, lanza error
    if not user:
        raise Exception("El usuario no existe.")

    # Verifica si ya tiene una cuenta creada
    if get_account_by_user(user_id):
        raise Exception("El usuario ya tiene una cuenta.")

    # Si pasa las validaciones, crea la cuenta
    create_account(user_id, currency)