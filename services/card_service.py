import uuid
import random
from datetime import datetime, timedelta
from typing import Any, Dict # Importamos para tipado explícito

from models.card_model import count_cards_by_account, insert_card
from utils.card_validator import is_luhn_valid 

def create_card_for_account(
    account_id: int, 
    card_type_id: int, 
    holder_name: str, 
    full_card_number: str
) -> Dict[str, Any]:
    """
    Lógica de negocio para emitir una nueva tarjeta.
    
    Genera un PIN de 4 dígitos aleatorio y valida el número con Luhn.
    
    Args:
        account_id: ID de la cuenta propietaria
        card_type_id: Tipo de tarjeta
        holder_name: Nombre del titular
        full_card_number: Número completo de 16 dígitos
        
    Returns:
        dict: {'success': bool, 'card_id': int, 'pin': str, 'last4': str, 'error': str}
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

    # 3. GENERAR PIN DE 4 DÍGITOS
    pin = f"{random.randint(1000, 9999)}"
    last4 = clean_number[-4:]
    
    # 4. FECHA DE EXPIRACIÓN
    exp_date = datetime.now() + timedelta(days=3*365)

    # 5. INSERCIÓN
    try:
        new_card_id = insert_card(
            account_id=account_id, 
            card_type_id=card_type_id, 
            card_number=clean_number,
            pin=pin,
            holder_name=holder_name, 
            exp_date=exp_date
        )
        
        return {
            "success": True, 
            "card_id": int(new_card_id), 
            "pin": str(pin), 
            "last4": str(last4)
        }
        
    except Exception as e:
        return {"success": False, "error": f"Error al insertar: {str(e)}"}


# ─────────────────────────────────────────────
# Validación y gestión de estado de tarjetas
# ─────────────────────────────────────────────

def validate_card_for_transaction(cursor: Any, card_number: str, input_pin: str) -> Dict[str, Any]:
    """
    Valida una tarjeta para ser utilizada en una transacción.
    
    Validaciones:
    1. La tarjeta existe en la tabla [card] usando el número completo (16 dígitos)
    2. is_active es True
    3. expiration_date > fecha actual
    4. PIN proporcionado coincide con el almacenado (4 dígitos)
    
    Args:
        cursor: Cursor pyodbc activo (no abre conexión)
        card_number: Número completo de 16 dígitos
        input_pin: PIN de 4 dígitos proporcionado para validación
        
    Returns:
        dict: {
            'success': bool,
            'account_id': int | None,
            'error': str | None,
            'last4': str | None  # Últimos 4 dígitos
        }
    
    Raises:
        Exception: Si hay error en la base de datos
    """
    
    # ─────────────────────────────────────────────────────────────────────
    # VALIDACIÓN ESTRICTA: PIN debe ser requerido
    # ─────────────────────────────────────────────────────────────────────
    if not input_pin or (isinstance(input_pin, str) and input_pin.strip() == ""):
        print(f"[CARD_SERVICE] ❌ PIN requerido para validación")
        return {"success": False, "error": "PIN de tarjeta requerido", "account_id": None, "last4": None}
    
    if len(str(input_pin).strip()) != 4:
        print(f"[CARD_SERVICE] ❌ PIN debe tener exactamente 4 dígitos")
        return {"success": False, "error": "PIN debe tener 4 dígitos", "account_id": None, "last4": None}
    
    # ─────────────────────────────────────────────────────────────────────
    # LIMPIAR NÚMERO DE TARJETA
    # ─────────────────────────────────────────────────────────────────────
    clean_card_number = str(card_number).replace(" ", "").replace("-", "")
    last4 = clean_card_number[-4:]
    
    print(f"[CARD_SERVICE] Validando tarjeta: {last4}...")
    
    try:
        # Búsqueda: Encontrar tarjeta por número completo
        query = """
            SELECT [Id_card], [account_id], [card_token], [is_active], [expiration_date]
            FROM [card]
            WHERE [card_number_last4] = ?
        """
        cursor.execute(query, (clean_card_number,))
        row = cursor.fetchone()
        
        # Validación 1: Tarjeta existe
        if not row:
            print(f"[CARD_SERVICE] ❌ Tarjeta no encontrada")
            return {"success": False, "error": "Tarjeta no encontrada", "account_id": None, "last4": None}
        
        card_id, account_id, stored_pin, is_active, expiration_date = row
        
        # Validación 2: Tarjeta está activa
        if not is_active:
            print(f"[CARD_SERVICE] ❌ Tarjeta bloqueada")
            return {"success": False, "error": "La tarjeta está bloqueada", "account_id": None, "last4": None}
        
        # Validación 3: Fecha de expiración válida
        if expiration_date < datetime.now():
            print(f"[CARD_SERVICE] ❌ Tarjeta vencida")
            return {"success": False, "error": "Tarjeta vencida", "account_id": None, "last4": None}
        
        # Validación 4: PIN coincide
        if str(stored_pin).strip() != str(input_pin).strip():
            print(f"[CARD_SERVICE] ❌ PIN inválido")
            return {"success": False, "error": "PIN de tarjeta incorrecto", "account_id": None, "last4": None}
        
        print(f"[CARD_SERVICE] ✅ Tarjeta validada correctamente (Cuenta: {account_id})")
        return {"success": True, "card_id": card_id, "account_id": account_id, "error": None, "last4": last4}
        
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
