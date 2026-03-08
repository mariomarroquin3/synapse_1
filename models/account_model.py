from config.database import get_cursor
from datetime import datetime
from typing import Any, Dict, Optional
import random


# ═══════════════════════════════════════════════════════════════════════════
# DICTIONARY WRAPPER - Convert pyodbc tuples to dictionaries
# ═══════════════════════════════════════════════════════════════════════════

def _row_to_dict(cursor, row: tuple) -> Optional[Dict[str, Any]]:
    """
    Converts a pyodbc row (tuple) to a dictionary using column names.
    
    Args:
        cursor: pyodbc cursor object (contains column description)
        row: tuple from fetchone() or fetchall()
        
    Returns:
        Dictionary mapping column names to values, or None if row is None
    """
    if row is None:
        return None
    
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT EXISTENCE & GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def account_number_exists(account_number: str) -> bool:
    """Verifica si un número de cuenta ya existe."""
    query = "SELECT 1 FROM [account] WHERE [account_number] = ?"

    with get_cursor() as cursor:
        cursor.execute(query, (account_number,))
        return cursor.fetchone() is not None


def generate_account_number() -> str:
    """Genera un número de cuenta único."""
    while True:
        # Format: SV_synapse + 7 random digits
        number = f"SV_synapse{random.randint(1000000, 9999999)}" 
        if not account_number_exists(number):
            return number


# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT RETRIEVAL (All return dictionaries)
# ═══════════════════════════════════════════════════════════════════════════

def get_account_by_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves the (first) account associated with a user."""
    query = "SELECT * FROM [account] WHERE [user_id] = ?"

    with get_cursor() as cursor:
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)

def get_accounts_by_user(user_id: int) -> list:
    """Retrieves all accounts associated with a user."""
    query = "SELECT * FROM [account] WHERE [user_id] = ?"

    with get_cursor() as cursor:
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        return [_row_to_dict(cursor, row) for row in rows] if rows else []


def get_account_by_number(account_number: str) -> Optional[Dict[str, Any]]:
    """Retrieves an account by its account number."""
    query = "SELECT * FROM [account] WHERE [account_number] = ?"
    
    with get_cursor() as cursor:
        cursor.execute(query, (account_number,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)


def get_account_by_id(account_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves an account by its ID."""
    query = "SELECT * FROM [account] WHERE [Id_account] = ?"
    
    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)


# ═══════════════════════════════════════════════════════════════════════════
# BALANCE CALCULATION (PURE LEDGER MODEL)
# ═══════════════════════════════════════════════════════════════════════════

def get_balance_from_ledger(account_id: int) -> float:
    """
    Calculates the account balance from the ledger using Pure Ledger Model:
    Balance = SUM(CREDITS) - SUM(DEBITS)
    
    Uses SUM with IIF to compute net balance in a single SQL query.
    
    Args:
        account_id: The account's ID
        
    Returns:
        Current balance as float (can be negative only if account is frozen/allowing debits)
    """
    query = """
        SELECT Nz(SUM(IIF([entry_type] = 'credit', [amount], -[amount])),0)
        FROM [ledger_entry]
        WHERE [account_id] = ?
    """
    
    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        result = cursor.fetchone()
        
        # If no entries exist, balance is 0
        if result is None or result[0] is None:
            return 0.0
        
        return float(result[0])


# ═══════════════════════════════════════════════════════════════════════════
# SECURE DEBIT / CREDIT OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

def add_ledger_entry_secure(account_id: int, amount: float, 
                            entry_type: str, description: str,
                            transaction_id: int = None) -> Dict[str, Any]:
    """
    Adds a ledger entry with automatic balance enforcement for DEBIT operations.
    
    For CREDIT: Standard INSERT (always allowed).
    For DEBIT:  Self-Defending INSERT using INSERT INTO ... SELECT.
                Only inserts if current balance >= amount.
    
    Args:
        account_id: Target account ID
        amount: Transaction amount (must be positive)
        entry_type: 'credit' or 'debit'
        description: Transaction description
        transaction_id: Optional FK to transaction table
        
    Returns:
        Dictionary with keys:
            'success': bool - Whether insert succeeded
            'entry_id': int - ID of inserted entry (if success=True)
            'balance': float - Current balance after operation
            'error': str - Error message (if success=False)
    """
    if entry_type not in ('credit', 'debit'):
        return {
            'success': False,
            'balance': get_balance_from_ledger(account_id),
            'error': f"Invalid entry_type: {entry_type}. Must be 'credit' or 'debit'."
        }
    
    if amount <= 0:
        return {
            'success': False,
            'balance': get_balance_from_ledger(account_id),
            'error': f"Amount must be positive, received: {amount}"
        }
    
    with get_cursor(commit=True) as cursor:
        try:
            # ─────────────────────────────────────────────────────────────
            # CREDIT: Standard INSERT (always allowed)
            # ─────────────────────────────────────────────────────────────
            if entry_type == 'credit':
                query = """
                    INSERT INTO [ledger_entry] 
                        ([account_id], [entry_type], [amount], [description], [transaction_id], [created_at])
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    account_id, 
                    entry_type, 
                    amount, 
                    description,
                    transaction_id,
                    datetime.now()
                ))
                
            # ─────────────────────────────────────────────────────────────
            # DEBIT: Self-Defending INSERT using INSERT INTO ... SELECT
            # ─────────────────────────────────────────────────────────────
            else:  # entry_type == 'debit'
                query = """
                    INSERT INTO [ledger_entry] 
                        ([account_id], [entry_type], [amount], [description], [transaction_id], [created_at])
                    SELECT ?, ?, ?, ?, ?, ?
                    WHERE (
                        SELECT SUM(IIF([entry_type] = 'credit', [amount], -[amount]))
                        FROM [ledger_entry]
                        WHERE [account_id] = ?
                    ) >= ?
                """
                cursor.execute(query, (
                    account_id,           # SELECT account_id
                    entry_type,           # SELECT entry_type
                    amount,               # SELECT amount
                    description,          # SELECT description
                    transaction_id,       # SELECT transaction_id
                    datetime.now(),       # SELECT created_at
                    account_id,           # WHERE condition: account_id
                    amount                # WHERE condition: amount to check against balance
                ))
            
            # Get the ID of the inserted row
            cursor.execute("SELECT @@IDENTITY")
            result = cursor.fetchone()
            
            if result is None or result[0] is None:
                # For DEBIT that failed the WHERE condition, no row is inserted
                if entry_type == 'debit':
                    balance = get_balance_from_ledger(account_id)
                    return {
                        'success': False,
                        'balance': balance,
                        'error': f"Insufficient funds. Balance: {balance}, Debit requested: {amount}"
                    }
                else:
                    raise Exception("Could not retrieve inserted entry ID")
            
            entry_id = int(result[0])
            balance = get_balance_from_ledger(account_id)
            
            print(f"[ACCOUNT] ✅ Ledger entry created → Id={entry_id}, "
                  f"account={account_id}, type={entry_type}, amount={amount}, balance={balance}")
            
            return {
                'success': True,
                'entry_id': entry_id,
                'balance': balance,
                'error': None
            }
            
        except Exception as e:
            balance = get_balance_from_ledger(account_id)
            print(f"[ACCOUNT] ❌ Error adding ledger entry: {e}")
            return {
                'success': False,
                'balance': balance,
                'error': str(e)
            }


# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT CREATION
# ═══════════════════════════════════════════════════════════════════════════

def create_account(user_id: int, currency: str) -> int:
    """
    Creates a new account for a user.
    
    Args:
        user_id: ID of the account owner
        currency: Currency code (USD, SVC, etc.)
        
    Returns:
        ID of the created account
    """
    query = """
        INSERT INTO [account] (
            [user_id],
            [account_number],
            [currency],
            [status_id],
            [created_at]
        )
        VALUES (?, ?, ?, ?, ?)
    """

    with get_cursor(commit=True) as cursor:
        cursor.execute(query, (
            user_id,                      # Account owner
            generate_account_number(),    # Unique generated number
            currency,                     # Currency
            1,                            # Status: Active (1)
            datetime.now()                # Creation timestamp
        ))
        
        # Return the ID of the newly created account
        cursor.execute("SELECT @@IDENTITY")
        result = cursor.fetchone()
        if result is None or result[0] is None:
            raise Exception("Could not retrieve account ID")
        
        return int(result[0])

def create_new_account(user_id: int, currency: str = "USD") -> int:
    """
    Creates a new account for a user, enforcing the 5-account limit.
    """
    existing_accounts = get_accounts_by_user(user_id)
    if len(existing_accounts) >= 5:
        raise ValueError("Límite alcanzado: Un usuario no puede tener más de 5 cuentas.")
    return create_account(user_id, currency)

# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def update_account_status(account_id: int, new_status_id: int) -> bool:
    """
    Updates the status of an account.
    Returns True if successful, raises Exception if an error occurs.
    
    1: Active
    2: Blocked
    3: Suspended
    """
    if new_status_id not in (1, 2, 3):
        raise ValueError("Invalid status ID. Must be 1, 2, or 3.")
        
    query = "UPDATE [account] SET status_id = ? WHERE Id_account = ?"
    with get_cursor(commit=True) as cursor:
        try:
            cursor.execute(query, (new_status_id, account_id))
            return True
        except Exception as e:
            raise Exception(f"Error updating account status: {e}")