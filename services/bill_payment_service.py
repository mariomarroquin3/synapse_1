from datetime import datetime
from typing import Any, Dict
from models.card_model import get_card_by_token
from services.transaction_service import create_simple_transaction, ENTRY_DEBIT

# Definimos tu nuevo tipo de transacción
TX_TYPE_PAYMENT = 4 

# Índices corregidos basados en tu estructura de tabla
IDX_CARD_ACCOUNT_ID = 1
IDX_CARD_EXP_DATE = 6  # Cambiado de 5 a 6 (el 5 es holder_name)

def pay_bill_with_card(
    card_token: str, 
    amount: float, 
    bill_description: str, 
    user_id: int
) -> Dict[str, Any]: # <-- Esto elimina el aviso de "Unknown"
    """
    Procesa el pago de un servicio usando el token de la tarjeta.
    """
    # 1. Buscar la tarjeta
    card = get_card_by_token(card_token)
    if not card:
        return {"success": False, "error": "Tarjeta no encontrada o token inválido."}

    # Extraer datos de la tupla
    account_id = int(card[IDX_CARD_ACCOUNT_ID])
    exp_date = card[IDX_CARD_EXP_DATE] # Esto es un objeto datetime desde Access

    # 2. Validar expiración (¡Ahora sí la usamos!)
    # Si la fecha de hoy es mayor a la de la tarjeta, está vencida
    if exp_date and exp_date < datetime.now():
        print(f"[DEBUG] Intento de pago con tarjeta vencida: {exp_date}")
        return {"success": False, "error": "La tarjeta ha expirado."}

    # 3. Procesar el pago
    print(f"[DEBUG] Iniciando pago de {bill_description} por ${amount} desde cuenta {account_id}")
    
    # Ejecutamos la transacción
    raw_result = create_simple_transaction(
        account_id=account_id,
        amount=amount,
        entry_type=ENTRY_DEBIT, 
        description=f"Pago Tarjeta: {bill_description}",
        created_by_user_id=user_id
    )
    
    # Forzamos el tipado para que el IDE deje de marcar "Unknown"
    result: Dict[str, Any] = dict(raw_result) if raw_result else {"success": False, "error": "Error interno"}

    return result