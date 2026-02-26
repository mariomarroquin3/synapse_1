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
    """
    Inserta el registro principal en la tabla transaction y retorna su ID.
    
    IMPORTANTE: Usa el cursor existente. El llamador gestiona commit/rollback.
    No llama a commit (lo gestiona el llamador).

    Args:
        cursor             : pyodbc cursor existente
        transaction_type_id: FK a transaction_type
        status_id          : FK a transaction_status
        description        : Descripción de la operación
        created_by_user_id : Usuario que ejecuta la operación

    Returns:
        ID de la transacción creada.
    """
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

    # Validaciones previas
    if amount <= 0:
        return {"success": False, "error": "El monto debe ser mayor a cero."}

    if from_account_id == to_account_id:
        return {"success": False, "error": "Las cuentas de origen y destino no pueden ser iguales."}

    conn = None
    cursor = None

    try:
        # PASO 1: Obtener conexión única para toda la transacción
        conn = get_connection()
        cursor = conn.cursor()

        # PASO 2: Insertar transacción principal
        tx_id = _insert_transaction(
            cursor, transaction_type_id, status_id,
            description, created_by_user_id
        )

        # PASO 3: Insertar entrada de DÉBITO (sale de cuenta origen)
        debit_entry_id = create_ledger_entry(
            cursor=cursor,
            transaction_id=tx_id,
            account_id=from_account_id,
            amount=amount,
            entry_type=DEBIT
        )

        # PASO 4: Insertar entrada de CRÉDITO (entra a cuenta destino)
        credit_entry_id = create_ledger_entry(
            cursor=cursor,
            transaction_id=tx_id,
            account_id=to_account_id,
            amount=amount,
            entry_type=CREDIT
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
        # ROLLBACK de toda la transacción en caso de error
        if conn:
            try:
                conn.rollback()
                print(f"[TX_SERVICE] ✅ Rollback exitoso - ningún cambio fue persistido")
            except Exception as rb_err:
                print(f"[TX_SERVICE] ❌ Error en rollback: {rb_err}")
        return {"success": False, "error": str(e)}

    finally:
        # CLEANUP: Cerrar cursor y conexión
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print(f"[TX_SERVICE] ── Fin de transferencia ───────────────────────────\n")


# ─────────────────────────────────────────────
# Servicio principal - Transacciones simples
# ─────────────────────────────────────────────

def create_simple_transaction(account_id: int, amount: float,
                               entry_type: str, description: str,
                               created_by_user_id: int,
                               transaction_type_id: int = 2,
                               status_id: int = 1) -> dict[str, Any]:
    """
    Crea una transacción simple con UNA sola entrada en ledger_entry.
    Total atomicidad: transacción + ledger en un único commit.
    
    Útil para depósitos (CREDIT) o retiros/cargos (DEBIT).

    Args:
        account_id          : Cuenta afectada
        amount              : Monto (positivo)
        entry_type          : 'debit' o 'credit'
        description         : Descripción de la operación
        created_by_user_id  : Usuario que ejecuta la operación
        transaction_type_id : FK a transaction_type (default 2 = depósito/retiro)
        status_id           : FK a transaction_status

    Returns:
        dict con 'success', 'transaction_id', 'ledger_entry_id' o 'error'.
    """
    print(f"\n[TX_SERVICE] ── Iniciando tx simple ({entry_type}) ATÓMICA ──────")
    print(f"[TX_SERVICE] Cuenta={account_id}, monto={amount}")

    # Validaciones previas
    if amount <= 0:
        return {"success": False, "error": "El monto debe ser mayor a cero."}

    if entry_type not in (DEBIT, CREDIT):
        return {"success": False, "error": f"entry_type inválido: '{entry_type}'."}

    conn = None
    cursor = None

    try:
        # PASO 1: Obtener conexión única para toda la transacción
        conn = get_connection()
        cursor = conn.cursor()

        # PASO 2: Insertar transacción principal
        tx_id = _insert_transaction(
            cursor, transaction_type_id, status_id,
            description, created_by_user_id
        )

        # PASO 3: Insertar entrada de ledger
        ledger_id = create_ledger_entry(
            cursor=cursor,
            transaction_id=tx_id,
            account_id=account_id,
            amount=amount,
            entry_type=entry_type
        )

        # PASO 4: COMMIT ÚNICO - Todo fue exitoso
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
        # ROLLBACK de toda la transacción en caso de error
        if conn:
            try:
                conn.rollback()
                print(f"[TX_SERVICE] ✅ Rollback exitoso - ningún cambio fue persistido")
            except Exception as rb_err:
                print(f"[TX_SERVICE] ❌ Error en rollback: {rb_err}")
        return {"success": False, "error": str(e)}

    finally:
        # CLEANUP: Cerrar cursor y conexión
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print(f"[TX_SERVICE] ── Fin de tx simple ──────────────────────────────\n")