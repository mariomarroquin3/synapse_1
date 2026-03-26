from config.database import get_cursor
from datetime import datetime
from typing import Any, Dict, Optional
import random

# ─────────────────────────────────────────────
# CONSTANTES ACTUALIZADAS
# ─────────────────────────────────────────────
CREDIT = 1
DEBIT = 2

# ═══════════════════════════════════════════════════════════════════════════
# DICTIONARY WRAPPER
# ═══════════════════════════════════════════════════════════════════════════

def _row_to_dict(cursor, row: tuple) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))

# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT NUMBER GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def account_number_exists(account_number: str) -> bool:
    query = "SELECT 1 FROM [account] WHERE [account_number] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (account_number,))
        return cursor.fetchone() is not None

def generate_account_number() -> str:
    while True:
        number = f"SV_synapse{random.randint(1000000, 9999999)}"
        if not account_number_exists(number):
            return number

# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT RETRIEVAL
# ═══════════════════════════════════════════════════════════════════════════

def get_account_by_user(user_id: int) -> Optional[Dict[str, Any]]:
    query = "SELECT * FROM [account] WHERE [user_id] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)

def get_accounts_by_user(user_id: int) -> list:
    query = "SELECT * FROM [account] WHERE [user_id] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        return [_row_to_dict(cursor, row) for row in rows] if rows else []

def get_account_by_number(account_number: str) -> Optional[Dict[str, Any]]:
    query = "SELECT * FROM [account] WHERE [account_number] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (account_number,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)

def get_account_by_id(account_id: int) -> Optional[Dict[str, Any]]:
    query = "SELECT * FROM [account] WHERE [Id_account] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)

# ═══════════════════════════════════════════════════════════════════════════
# GET PENDING ACCOUNTS (for admin approval)
# ═══════════════════════════════════════════════════════════════════════════

def get_pending_accounts() -> list:
    query = """
    SELECT *
    FROM [account]
    WHERE [status_id] = 4
    """
    with get_cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        return [_row_to_dict(cursor, row) for row in rows] if rows else []

# ═══════════════════════════════════════════════════════════════════════════
# PURE LEDGER BALANCE
# ═══════════════════════════════════════════════════════════════════════════

def get_balance_from_ledger(account_id: int) -> float:
    # ACTUALIZACIÓN: Evaluamos contra 1 (CREDIT) en lugar de 'credit'
    query = f"""
        SELECT Nz(SUM(IIF([entry_type] = {CREDIT}, [amount], -[amount])),0)
        FROM [ledger_entry]
        WHERE [account_id] = ?
    """
    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        result = cursor.fetchone()
        if result is None or result[0] is None:
            return 0.0
        return float(result[0])

# ═══════════════════════════════════════════════════════════════════════════
# SECURE LEDGER ENTRY
# ═══════════════════════════════════════════════════════════════════════════

def add_ledger_entry_secure(account_id: int, amount: float,
                            entry_type: int, description: str, # ACTUALIZACIÓN: entry_type ahora es int
                            transaction_id: int = None) -> Dict[str, Any]:

    # ACTUALIZACIÓN: Verificamos contra constantes enteras
    if entry_type not in (CREDIT, DEBIT):
        return {
            "success": False,
            "balance": get_balance_from_ledger(account_id),
            "error": "Invalid entry type"
        }

    if amount <= 0:
        return {
            "success": False,
            "balance": get_balance_from_ledger(account_id),
            "error": "Amount must be positive"
        }

    with get_cursor(commit=True) as cursor:
        try:
            # ACTUALIZACIÓN: Comparamos con la constante CREDIT
            if entry_type == CREDIT:
                query = """
                INSERT INTO [ledger_entry]
                ([account_id],[entry_type],[amount],[description],[transaction_id],[created_at])
                VALUES (?,?,?,?,?,?)
                """
                cursor.execute(query, (
                    account_id,
                    entry_type,
                    amount,
                    description,
                    transaction_id,
                    datetime.now()
                ))

            else:
                # ACTUALIZACIÓN: En el SELECT condicional, evaluamos contra el valor int (1)
                query = f"""
                INSERT INTO [ledger_entry]
                ([account_id],[entry_type],[amount],[description],[transaction_id],[created_at])
                SELECT ?,?,?,?,?,?
                WHERE (
                    SELECT SUM(IIF([entry_type]={CREDIT},[amount],-[amount]))
                    FROM [ledger_entry]
                    WHERE [account_id]=?
                ) >= ?
                """
                cursor.execute(query, (
                    account_id,
                    entry_type,
                    amount,
                    description,
                    transaction_id,
                    datetime.now(),
                    account_id,
                    amount
                ))

            cursor.execute("SELECT @@IDENTITY")
            result = cursor.fetchone()

            if result is None or result[0] is None:
                balance = get_balance_from_ledger(account_id)
                return {
                    "success": False,
                    "balance": balance,
                    "error": "Insufficient funds"
                }

            entry_id = int(result[0])
            balance = get_balance_from_ledger(account_id)

            return {
                "success": True,
                "entry_id": entry_id,
                "balance": balance
            }

        except Exception as e:
            balance = get_balance_from_ledger(account_id)
            return {
                "success": False,
                "balance": balance,
                "error": str(e)
            }

# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT CREATION
# ═══════════════════════════════════════════════════════════════════════════

def create_account(user_id: int, currency: int) -> int:
    query = """
    INSERT INTO [account]
    ([user_id],[account_number],[currency],[status_id],[created_at])
    VALUES (?,?,?,?,?)
    """
    with get_cursor(commit=True) as cursor:
        cursor.execute(query, (
            user_id,
            generate_account_number(),
            currency,
            4,  # PENDING APPROVAL
            datetime.now()
        ))
        cursor.execute("SELECT @@IDENTITY")
        result = cursor.fetchone()
        if result is None or result[0] is None:
            raise Exception("Could not retrieve account ID")
        return int(result[0])

def create_new_account(user_id: int, currency: int = 1) -> int:
    existing_accounts = get_accounts_by_user(user_id)
    if len(existing_accounts) >= 5:
        raise ValueError("Limit reached: user cannot have more than 5 accounts.")
    return create_account(user_id, currency)

# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT STATUS MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def update_account_status(account_id: int, new_status_id: int) -> bool:
    if new_status_id not in (1, 2, 3, 4, 5):
        raise ValueError("Invalid status id")
    query = """
    UPDATE [account]
    SET [status_id] = ?
    WHERE [Id_account] = ?
    """
    with get_cursor(commit=True) as cursor:
        cursor.execute(query, new_status_id, account_id)
        return True

# ═══════════════════════════════════════════════════════════════════════════
# ADMIN APPROVAL ACTIONS
# ═══════════════════════════════════════════════════════════════════════════

def approve_account(account_id: int) -> bool:
    return update_account_status(account_id, 1)

def reject_account(account_id: int) -> bool:
    return update_account_status(account_id, 5)

def get_accounts_by_user_ids(user_ids: list) -> list:
    if not user_ids: return []
    placeholders = ','.join(['?'] * len(user_ids))
    query = f'SELECT * FROM [account] WHERE [user_id] IN ({placeholders})'
    with get_cursor() as cursor:
        cursor.execute(query, tuple(user_ids))
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in rows] if rows else []

def get_all_accounts_global() -> list:
    """
    Obtiene TODAS las cuentas de la tabla [account] sin filtros.
    Utilizado para calcular KPIs globales en el dashboard del admin.
    Retorna lista de diccionarios con todas las columnas de la tabla.
    """
    query = 'SELECT * FROM [account]'
    with get_cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in rows] if rows else []