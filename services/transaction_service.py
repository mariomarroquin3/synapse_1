"""
transaction_service.py
Servicio de negocio que orquesta transacciones y sus entradas contables.

ARQUITECTURA DE ATOMICIDAD:
  - Una única conexión para toda la operación
  - Una única transacción que abarca:
    * inserción en [transaction]
    * inserción de TODOS los ledger_entry asociados
  - Un único commit() al final si todo es exitoso
  - rollback() si algo falla
  - Los modelos NUNCA abren/cierran conexiones

Modelo ledger doble:
  - Transferencia entre cuentas → 2 entradas (débito origen, crédito destino)
  - Depósito / operación simple → 1 entrada (crédito destino)
  - Retiro / cargo simple       → 1 entrada (débito origen)
"""

from config.database import get_connection
from models.ledger_model import create_ledger_entry, DEBIT, CREDIT
from datetime import datetime
from typing import Any

# ─────────────────────────────────────────────
# Tipos de entrada para claridad externa
# ─────────────────────────────────────────────
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

def _check_account_active(account_id: int) -> dict:
    """
    Verifica si una cuenta existe y está ACTIVA (status_id = 1).
    Retorna un dict con success y error_message.
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
        if status_id == 2:
            return {"success": False, "error": f"La cuenta {account_id} está BLOQUEADA."}
        elif status_id == 3:
            return {"success": False, "error": f"La cuenta {account_id} está SUSPENDIDA."}
        elif status_id != 1:
            return {"success": False, "error": f"La cuenta {account_id} no está activa."}
            
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": f"Error verificando cuenta: {str(e)}"}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ─────────────────────────────────────────────
# Consulta de Balance (Movido arriba para poder usarlo en transferencias)
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
  
    print(f"\n[TX_SERVICE] ── Iniciando transferencia (ATÓMICA) ───────────────")
    print(f"[TX_SERVICE] De cuenta={from_account_id} → A cuenta={to_account_id}, monto={amount}")

    # 1. Validaciones básicas de negocio
    if amount <= 0:
        return {"success": False, "error": "El monto debe ser mayor a cero."}
    if from_account_id == to_account_id:
        return {"success": False, "error": "Las cuentas de origen y destino no pueden ser iguales."}

    # 2. Verificar estado de cuentas (Semáforo)
    sender_status = _check_account_active(from_account_id)
    if not sender_status["success"]:
        return sender_status
        
    receiver_status = _check_account_active(to_account_id)
    if not receiver_status["success"]:
        return {"success": False, "error": f"Error en cuenta destino: {receiver_status['error']}"}

    # 3. Verificar fondos de la cuenta origen
    current_balance = get_account_balance(from_account_id)
    if current_balance < amount:
        return {"success": False, "error": f"Fondos insuficientes. Balance actual: ${current_balance}"}

    conn = None
    cursor = None

    try:
        # PASO 1: Obtener conexión única
        conn = get_connection()
        cursor = conn.cursor()

        # PASO 2: Insertar transacción principal
        tx_id = _insert_transaction(
            cursor, transaction_type_id, status_id,
            description, created_by_user_id
        )

        # PASO 3: Insertar entrada de DÉBITO (sale de cuenta origen)
        debit_entry_id = create_ledger_entry(
            cursor=cursor, transaction_id=tx_id, account_id=from_account_id,
            amount=amount, entry_type=DEBIT
        )

        # PASO 4: Insertar entrada de CRÉDITO (entra a cuenta destino)
        credit_entry_id = create_ledger_entry(
            cursor=cursor, transaction_id=tx_id, account_id=to_account_id,
            amount=amount, entry_type=CREDIT
        )

        # PASO 5: COMMIT ÚNICO - Todo fue exitoso
        conn.commit()
        
        print(f"[TX_SERVICE] ✅ Transferencia ATÓMICA completada → tx={tx_id}, "
              f"ledger_debit={debit_entry_id}, ledger_credit={credit_entry_id}")

        return {
            "success": True,
            "transaction_id": tx_id,
            "ledger_entries": {
                "debit":  {"id": debit_entry_id,  "account_id": from_account_id, "type": DEBIT},
                "credit": {"id": credit_entry_id, "account_id": to_account_id,  "type": CREDIT},
            }
        }

    except Exception as e:
        print(f"[TX_SERVICE] ❌ Error en transferencia: {e}")
        if conn:
            try:
                conn.rollback()
                print(f"[TX_SERVICE] ✅ Rollback exitoso - ningún cambio fue persistido")
            except Exception as rb_err:
                print(f"[TX_SERVICE] ❌ Error en rollback: {rb_err}")
        return {"success": False, "error": str(e)}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        print(f"[TX_SERVICE] ── Fin de transferencia ───────────────────────────\n")

# ─────────────────────────────────────────────
# Servicio principal - Transacciones simples
# ─────────────────────────────────────────────

def create_simple_transaction(account_id: int, amount: float,
                               entry_type: str, description: str,
                               created_by_user_id: int,
                               transaction_type_id: int, 
                               status_id: int = 1) -> dict[str, Any]:
    
    print(f"\n[TX_SERVICE] ── Iniciando tx simple ({entry_type}) ATÓMICA ──────")
    print(f"[TX_SERVICE] Cuenta={account_id}, monto={amount}")

    # 1. Validaciones previas
    if amount <= 0:
        return {"success": False, "error": "El monto debe ser mayor a cero."}
    if entry_type not in (DEBIT, CREDIT):
        return {"success": False, "error": f"entry_type inválido: '{entry_type}'."}

    # 2. Verificar estado de la cuenta
    acc_status = _check_account_active(account_id)
    if not acc_status["success"]:
        return acc_status

    # 3. Si es retiro (Débito), verificar fondos
    if entry_type == DEBIT:
        current_balance = get_account_balance(account_id)
        if current_balance < amount:
            return {"success": False, "error": f"Fondos insuficientes. Balance actual: ${current_balance}"}

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        tx_id = _insert_transaction(
            cursor, transaction_type_id, status_id,
            description, created_by_user_id
        )

        ledger_id = create_ledger_entry(
            cursor=cursor, transaction_id=tx_id, account_id=account_id,
            amount=amount, entry_type=entry_type
        )

        conn.commit()
        print(f"[TX_SERVICE] ✅ Tx simple ATÓMICA completada → tx={tx_id}, ledger={ledger_id}")

        return {
            "success": True,
            "transaction_id": tx_id,
            "ledger_entry_id": ledger_id,
            "entry_type": entry_type,
        }

    except Exception as e:
        print(f"[TX_SERVICE] ❌ Error en tx simple: {e}")
        if conn:
            try:
                conn.rollback()
                print(f"[TX_SERVICE] ✅ Rollback exitoso - ningún cambio fue persistido")
            except Exception as rb_err:
                print(f"[TX_SERVICE] ❌ Error en rollback: {rb_err}")
        return {"success": False, "error": str(e)}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        print(f"[TX_SERVICE] ── Fin de tx simple ──────────────────────────────\n")

def get_account_history_by_type(account_id: int, transaction_type_id: int) -> list:
    from config.database import get_connection
    
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
            history.append({
                "date": row[0],
                "description": row[1],
                "amount": float(row[2]),
                "entry_type": row[3]
            })
            
        return history
    except Exception as e:
        print(f'[TX_SERVICE] ❌ Error consultando historial de tipo {transaction_type_id}: {e}')
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()