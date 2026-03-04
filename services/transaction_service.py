"""
transaction_service.py
Servicio de negocio que orquesta transacciones y sus entradas contables.
"""

from config.database import get_connection
from models.ledger_model import create_ledger_entry, DEBIT, CREDIT
from datetime import datetime
from typing import Any

# Tipos de entrada para claridad externa
ENTRY_DEBIT  = DEBIT
ENTRY_CREDIT = CREDIT

# ─────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────

def _insert_transaction(cursor: Any, transaction_type_id: int, status_id: int,
                        description: str, created_by_user_id: int) -> int:
    """Inserta el registro principal en la tabla transaction y retorna su ID."""
    sql = """
        INSERT INTO [transaction]
            (transaction_type_id, status_id, description, created_by_user_id, transaction_date, processed_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    now = datetime.now()
    cursor.execute(sql, (transaction_type_id, status_id, description, created_by_user_id, now, now))
    
    cursor.execute("SELECT @@IDENTITY")
    result = cursor.fetchone()
    if result is None or result[0] is None:
        raise Exception("No se pudo obtener el ID de la transacción creada.")
    
    tx_id = int(result[0])
    print(f"[TX_SERVICE] Transacción insertada → Id_transaction={tx_id}")
    return tx_id

def _check_account_active(account_id: int, is_debit: bool = True) -> dict:
    """
    Verifica el estado de la cuenta con reglas granulares:
    - Débito (Salida): Solo permitido si status_id = 1 (Activo).
    - Crédito (Entrada): Permitido si es 1 (Activo) o 2 (Bloqueado).
    - Suspendido (3): Siempre denegado.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status_id FROM account WHERE Id_account = ?", (account_id,))
        row = cursor.fetchone()
        
        if not row:
            return {"success": False, "error": f"La cuenta {account_id} no existe."}
        
        status_id = row[0]
        
        # REGLA 1: Suspendida siempre bloquea todo
        if status_id == 3:
            return {"success": False, "error": "Cuenta SUSPENDIDA. Operación no permitida."}
        
        # REGLA 2: Bloqueada solo permite ENTRADAS (Créditos), no SALIDAS (Débitos)
        if is_debit and status_id == 2:
            return {"success": False, "error": "Cuenta BLOQUEADA. No se permiten retiros ni envíos de dinero."}
        
        # REGLA 3: Si no es 1, 2 o 3, por defecto bloqueamos por seguridad
        if status_id not in (1, 2):
            return {"success": False, "error": "Estado de cuenta inválido para operar."}
            
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": f"Error verificando cuenta: {str(e)}"}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ─────────────────────────────────────────────
# Consulta de Balance
# ─────────────────────────────────────────────

def get_account_balance(account_id: int) -> float:
    sql = '''
        SELECT entry_type, SUM(amount)
        FROM ledger_entry
        WHERE account_id = ?
        GROUP BY entry_type
    '''
    balance = 0.0
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (account_id,))
        rows = cursor.fetchall()
        
        for row in rows:
            entry_type = row[0]
            amount = float(row[1] or 0.0)
            if entry_type == CREDIT:
                balance += amount
            elif entry_type == DEBIT:
                balance -= amount
                
        return balance
    except Exception as e:
        print(f'[TX_SERVICE] ❌ Error calculando balance: {e}')
        return 0.0
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ─────────────────────────────────────────────
# Servicio principal - Transferencias
# ─────────────────────────────────────────────

def create_transfer(from_account_id: int, to_account_id: int,
                    amount: float, description: str,
                    created_by_user_id: int,
                    transaction_type_id: int = 1,
                    status_id: int = 1) -> dict[str, Any]:
  
    print(f"\n[TX_SERVICE] ── Iniciando transferencia GRANULAR ───────────────")

    if amount <= 0:
        return {"success": False, "error": "El monto debe ser mayor a cero."}
    if from_account_id == to_account_id:
        return {"success": False, "error": "Cuentas origen y destino iguales."}

    # ORIGEN: Debe permitir DÉBITO (Solo Activa)
    sender_status = _check_account_active(from_account_id, is_debit=True)
    if not sender_status["success"]:
        return sender_status
        
    # DESTINO: Debe permitir CRÉDITO (Activa o Bloqueada)
    receiver_status = _check_account_active(to_account_id, is_debit=False)
    if not receiver_status["success"]:
        return {"success": False, "error": f"Error en cuenta destino: {receiver_status['error']}"}

    current_balance = get_account_balance(from_account_id)
    if current_balance < amount:
        return {"success": False, "error": f"Fondos insuficientes (${current_balance})"}

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        tx_id = _insert_transaction(cursor, transaction_type_id, status_id, description, created_by_user_id)
        
        create_ledger_entry(cursor=cursor, transaction_id=tx_id, account_id=from_account_id, amount=amount, entry_type=DEBIT)
        create_ledger_entry(cursor=cursor, transaction_id=tx_id, account_id=to_account_id, amount=amount, entry_type=CREDIT)

        conn.commit()
        return {"success": True, "transaction_id": tx_id}

    except Exception as e:
        if conn: conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ─────────────────────────────────────────────
# Servicio principal - Transacciones simples
# ─────────────────────────────────────────────

def create_simple_transaction(account_id: int, amount: float,
                               entry_type: str, description: str,
                               created_by_user_id: int,
                               transaction_type_id: int, 
                               status_id: int = 1,
                               card_number: str | None = None,
                               card_token: str | None = None) -> dict[str, Any]:
    """
    Crea una transacción simple (depósito, retiro, etc).
    
    Si card_number se proporciona, valida la tarjeta antes de procesar.
    
    Args:
        account_id: Cuenta a afectar
        amount: Monto de la transacción
        entry_type: DEBIT o CREDIT
        description: Descripción del movimiento
        created_by_user_id: Usuario que crea la transacción
        transaction_type_id: Tipo de transacción (2=Retiro, 3=Depósito, 4=Pago)
        status_id: Estado de la transacción (default=1=Pending)
        card_number: Número de tarjeta (opcional, para transacciones con tarjeta)
        card_token: Token de tarjeta (requerido si card_number se proporciona)
        
    Returns:
        dict: {'success': bool, 'transaction_id': int | None, 'ledger_entry_id': int | None}
    """
    
    if amount <= 0:
        return {"success": False, "error": "El monto debe ser mayor a cero."}

    # Verificar estado basándose en si es salida (DEBIT) o entrada (CREDIT)
    is_debit = (entry_type == DEBIT)
    acc_status = _check_account_active(account_id, is_debit=is_debit)
    if not acc_status["success"]:
        return acc_status

    if is_debit:
        current_balance = get_account_balance(account_id)
        if current_balance < amount:
            return {"success": False, "error": f"Fondos insuficientes (${current_balance})"}

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # VALIDACIÓN OPCIONAL: Si se proporciona card_number, validar tarjeta
        if card_number is not None:
            print(f"[TX_SERVICE] Validando tarjeta para transacción...")
            if card_token is None:
                return {"success": False, "error": "card_token es requerido cuando se proporciona card_number"}
            
            # Importar aquí para evitar dependencias circulares
            from services.card_service import validate_card_for_transaction
            
            card_validation = validate_card_for_transaction(cursor, card_number, card_token)
            if not card_validation["success"]:
                return {
                    "success": False, 
                    "error": card_validation["error"]
                }
            
            # Verificar que la tarjeta pertenece a la cuenta correcta
            card_account_id = card_validation["account_id"]
            if card_account_id != account_id:
                return {
                    "success": False,
                    "error": f"La tarjeta no pertenece a esta cuenta (Tarjeta: {card_account_id}, Cuenta: {account_id})"
                }
            
            print(f"[TX_SERVICE] ✅ Tarjeta validada correctamente")

        tx_id = _insert_transaction(cursor, transaction_type_id, status_id, description, created_by_user_id)
        ledger_id = create_ledger_entry(cursor=cursor, transaction_id=tx_id, account_id=account_id, amount=amount, entry_type=entry_type)

        conn.commit()
        return {"success": True, "transaction_id": tx_id, "ledger_entry_id": ledger_id}

    except Exception as e:
        if conn: conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_account_history_by_type(account_id: int, transaction_type_id: int) -> list:
    sql = '''
        SELECT t.transaction_date, t.description, l.amount, l.entry_type
        FROM (ledger_entry l
        INNER JOIN [transaction] t ON l.transaction_id = t.Id_transaction)
        WHERE l.account_id = ? AND t.transaction_type_id = ?
        ORDER BY t.transaction_date DESC
    '''
    history = []
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (account_id, transaction_type_id))
        rows = cursor.fetchall()
        for row in rows:
            history.append({"date": row[0], "description": row[1], "amount": float(row[2]), "entry_type": row[3]})
        return history
    except Exception:
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()