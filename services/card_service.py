import uuid
from datetime import datetime, timedelta
from typing import Any, Dict # Importamos para tipado explícito

from models.card_model import count_cards_by_account, insert_card
from utils.card_validator import is_luhn_valid 

def create_card_for_account(
    account_id: int, 
    card_type_id: int, 
    holder_name: str, 
    full_card_number: str
) -> Dict[str, Any]: # <--- Esto elimina el aviso de "Unknown"
    """
    Lógica de negocio para emitir una nueva tarjeta.
    """
    
    #1. REGLA DE NEGOCIO: Máximo 2 tarjetas
    try:
        current_cards = count_cards_by_account(account_id)
        if current_cards >= 2:
            return {"success": False, "error": "Límite alcanzado: 2 tarjetas máximo."}
    except Exception as e:
        return {"success": False, "error": f"Error de DB: {str(e)}"}

    # 2. VALIDACIÓN LUHN
    clean_number = full_card_number.replace(" ", "").replace("-", "")
    if not is_luhn_valid(clean_number):
        return {"success": False, "error": "Número de tarjeta inválido."}

    # 3. SEGURIDAD Y DATOS
    last4 = clean_number[-4:]
    card_token = f"tok_{uuid.uuid4().hex}" 
    
    # 4. FECHA DE EXPIRACIÓN (Para el tipo Fecha/Hora de Access)
    # Creamos un objeto datetime real (el primer día del mes en 3 años)
    exp_date = datetime.now() + timedelta(days=3*365)

    # 5. INSERCIÓN
    try:
        new_card_id = insert_card(
            account_id=account_id, 
            card_type_id=card_type_id, 
            last4=last4, 
            token=card_token, 
            holder_name=holder_name, 
            exp_date=exp_date
        )
        
        return {
            "success": True, 
            "card_id": int(new_card_id), 
            "token": str(card_token), 
            "last4": str(last4)
        }
        
    except Exception as e:
        return {"success": False, "error": f"Error al insertar: {str(e)}"}