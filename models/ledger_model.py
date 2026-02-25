"""
ledger_model.py
Modelo para operaciones CRUD sobre la tabla ledger_entry.
Cada registro representa un movimiento contable (débito o crédito)
asociado a una transacción y una cuenta específica.

ARQUITECTURA: Modelos NUNCA abren/cierran conexiones ni manejan transacciones.
El código de negocio (service layer) es responsable de:
  - Abrir/cerrar conexiones
  - Manejar commits/rollbacks
  - Garantizar atomicidad global
"""

from datetime import datetime
from typing import Any


# ─────────────────────────────────────────────
# Constantes contables
# ─────────────────────────────────────────────
DEBIT  = "debit"
CREDIT = "credit"


def create_ledger_entry(cursor: Any, transaction_id: int, account_id: int,
                        amount: float, entry_type: str) -> int:
    """
    Inserta un registro en ledger_entry usando un cursor existente.
    
    IMPORTANTE: Llamador es responsable de commit/rollback. Esta función
    NO abre ni cierra conexiones ni maneja transacciones.

    Args:
        cursor         : Cursor pyodbc existente (no None)
        transaction_id : FK a transaction.Id_transaction
        account_id     : FK a account.Id_account
        amount         : Monto del movimiento (siempre positivo)
        entry_type     : 'debit' o 'credit'

    Returns:
        Id del registro insertado.
        
    Raises:
        ValueError: Si entry_type o amount son inválidos.
        Exception: Si la inserción falla.
    """
    if entry_type not in (DEBIT, CREDIT):
        raise ValueError(f"entry_type debe ser '{DEBIT}' o '{CREDIT}', se recibió: '{entry_type}'")

    if amount <= 0:
        raise ValueError(f"El monto debe ser positivo, se recibió: {amount}")

    sql = """
        INSERT INTO ledger_entry (transaction_id, account_id, entry_type, amount, created_at)
        VALUES (?, ?, ?, ?, ?)
    """

    created_at = datetime.now()

    print(f"[LEDGER] Insertando entrada → tx={transaction_id}, cuenta={account_id}, "
          f"monto={amount}, tipo={entry_type}, fecha={created_at}")

    cursor.execute(sql, (transaction_id, account_id, entry_type, amount, created_at))

    # Access no soporta RETURNING; usamos @@IDENTITY para obtener el último ID generado
    cursor.execute("SELECT @@IDENTITY")
    result = cursor.fetchone()
    if result is None or result[0] is None:
        raise Exception("No se pudo obtener el ID de la entrada creada.")
    new_id = int(result[0])

    print(f"[LEDGER] ✅ Entrada creada con Id_entry={new_id}")
    return new_id


def get_ledger_entries_by_transaction(transaction_id: int) -> list[dict[str, Any]]:
    """
    Retorna todas las entradas de ledger asociadas a una transacción.
    Esta función abre su propia conexión (operación de lectura, no transaccional).

    Args:
        transaction_id: FK a transaction.Id_transaction

    Returns:
        Lista de dicts con los campos de ledger_entry.
    """
    from config.database import get_connection
    
    sql = """
        SELECT Id_entry, transaction_id, account_id, entry_type, amount, created_at
        FROM ledger_entry
        WHERE transaction_id = ?
        ORDER BY created_at ASC
    """
    print(f"[LEDGER] Consultando entradas para transaction_id={transaction_id}")

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (transaction_id,))
        rows = cursor.fetchall()

        entries = [
            {
                "Id_entry":       row[0],
                "transaction_id": row[1],
                "account_id":     row[2],
                "entry_type":     row[3],
                "amount":         row[4],
                "created_at":     row[5],
            }
            for row in rows
        ]

        print(f"[LEDGER] Se encontraron {len(entries)} entradas.")
        return entries

    except Exception as e:
        print(f"[LEDGER] ❌ Error al consultar ledger: {e}")
        return []

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_ledger_entry_by_id(entry_id: int) -> dict[str, Any] | None:
    """
    Retorna una entrada de ledger por su ID primario.
    Esta función abre su propia conexión (operación de lectura, no transaccional).
    """
    from config.database import get_connection
    
    sql = """
        SELECT Id_entry, transaction_id, account_id, entry_type, amount, created_at
        FROM ledger_entry
        WHERE Id_entry = ?
    """
    print(f"[LEDGER] Buscando Id_entry={entry_id}")

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (entry_id,))
        row = cursor.fetchone()

        if not row:
            print(f"[LEDGER] ⚠️ No se encontró Id_entry={entry_id}")
            return None

        return {
            "Id_entry":       row[0],
            "transaction_id": row[1],
            "account_id":     row[2],
            "entry_type":     row[3], 
            "amount":         row[4],
            "created_at":     row[5],
        }

    except Exception as e:
        print(f"[LEDGER] ❌ Error al buscar entrada: {e}")
        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()