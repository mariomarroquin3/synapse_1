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


# ─────────────────────────────────────────────
# Validación y gestión de estado de tarjetas
# ─────────────────────────────────────────────

def validate_card_for_transaction(cursor: Any, card_number: str, input_token: str) -> Dict[str, Any]:
    """
    Valida una tarjeta para ser utilizada en una transacción.
    
    Validaciones:
    1. La tarjeta existe en la tabla [card] usando card_number_last4
    2. is_active es True
    3. expiration_date > fecha actual
    4. card_token coincide con input_token
    5. Token debe ser proporcionado explícitamente
    
    Args:
        cursor: Cursor pyodbc activo (no abre conexión)
        card_number: Número de tarjeta a validar (puede ser 4 o 16 dígitos)
        input_token: Token proporcionado para validación (REQUERIDO)
        
    Returns:
        dict: {
            'success': bool,
            'account_id': int | None,
            'error': str | None
        }
    
    Raises:
        Exception: Si hay error en la base de datos
    """
    
    # ─────────────────────────────────────────────────────────────────────
    # VALIDACIÓN ESTRICTA: Token debe ser requerido
    # ─────────────────────────────────────────────────────────────────────
    if not input_token or (isinstance(input_token, str) and input_token.strip() == ""):
        print(f"[CARD_SERVICE] ❌ Token requerido para validación")
        return {"success": False, "error": "Token de tarjeta requerido", "account_id": None}
    
    # ─────────────────────────────────────────────────────────────────────
    # ENTRADA: Slice automático si tiene 16 dígitos
    # ─────────────────────────────────────────────────────────────────────
    search_number = card_number
    if len(str(card_number).replace(" ", "").replace("-", "")) == 16:
        # Si tiene 16 dígitos, extraer últimos 4
        search_number = str(card_number).replace(" ", "").replace("-", "")[-4:]
    
    print(f"[CARD_SERVICE] Validando tarjeta: {search_number}...")
    
    try:
        # Búsqueda 1: Encontrar tarjeta por card_number_last4
        query = """
            SELECT [Id_card], [account_id], [card_token], [is_active], [expiration_date]
            FROM [card]
            WHERE [card_number_last4] = ?
        """
        cursor.execute(query, (search_number,))
        row = cursor.fetchone()
        
        # Validación 1: Tarjeta existe
        if not row:
            print(f"[CARD_SERVICE] ❌ Tarjeta no encontrada")
            return {"success": False, "error": "Tarjeta no encontrada", "account_id": None}
        
        card_id, account_id, stored_token, is_active, expiration_date = row
        
        # Validación 2: Tarjeta está activa
        if not is_active:
            print(f"[CARD_SERVICE] ❌ Tarjeta bloqueada")
            return {"success": False, "error": "La tarjeta está bloqueada", "account_id": None}
        
        # Validación 3: Fecha de expiración válida
        if expiration_date < datetime.now():
            print(f"[CARD_SERVICE] ❌ Tarjeta vencida")
            return {"success": False, "error": "Tarjeta vencida", "account_id": None}
        
        # Validación 4: Token coincide
        if stored_token != input_token:
            print(f"[CARD_SERVICE] ❌ Token inválido")
            return {"success": False, "error": "Token de tarjeta inválido", "account_id": None}
        
        print(f"[CARD_SERVICE] ✅ Tarjeta validada correctamente (Cuenta: {account_id})")
        return {"success": True, "account_id": account_id, "error": None}
        
    except Exception as e:
        print(f"[CARD_SERVICE] ❌ Error en validación: {str(e)}")
        raise Exception(f"Error validando tarjeta: {str(e)}")


def update_card_active_status(cursor: Any, card_id: int, status: bool) -> None:
    """
    Actualiza el estado activo/inactivo de una tarjeta.
    
    IMPORTANTE: Esta función NO hace commit. El llamador es responsable
    de hacer commit o rollback dentro de su transacción.
    
    Args:
        cursor: Cursor pyodbc activo en una conexión abierta
        card_id: ID de la tarjeta a actualizar
        status: True para activar, False para bloquear
        
    Raises:
        Exception: Si hay error en la base de datos
    """
    print(f"[CARD_SERVICE] Actualizando tarjeta {card_id} → is_active={status}")
    
    try:
        query = """
            UPDATE [card]
            SET [is_active] = ?
            WHERE [Id_card] = ?
        """
        cursor.execute(query, (status, card_id))
        print(f"[CARD_SERVICE] ✅ Estado de tarjeta actualizado")
        
    except Exception as e:
        print(f"[CARD_SERVICE] ❌ Error al actualizar tarjeta: {str(e)}")
        raise Exception(f"Error al actualizar estado de tarjeta: {str(e)}")