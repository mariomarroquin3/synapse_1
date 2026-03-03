"""
account_service.py
Business Logic Layer for account operations.

Implements Pure Ledger Model with balance non-negativity enforcement
and account status controls (Traffic Light System).

Account Status Codes:
  1 (ACTIVE):  Allows both CREDIT and DEBIT operations
  2 (FROZEN):  Allows CREDIT only, blocks DEBIT operations
  3 (CLOSED):  Blocks ALL operations
"""

from models.account_model import (
    create_account,
    get_account_by_user,
    get_account_by_id,
    get_account_by_number,
    get_balance_from_ledger,
    add_ledger_entry_secure
)
from models.user_model import get_user_by_id
from datetime import datetime
from typing import Dict, Any, Optional


# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT STATUS CODES (Traffic Light System)
# ═══════════════════════════════════════════════════════════════════════════

STATUS_ACTIVE = 1
STATUS_FROZEN = 2
STATUS_CLOSED = 3

STATUS_NAMES = {
    1: "ACTIVE (allows all transactions)",
    2: "FROZEN (credit only)",
    3: "CLOSED (no transactions allowed)"
}


# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT CREATION
# ═══════════════════════════════════════════════════════════════════════════

def create_account_for_user(user_id: int, currency: str) -> Dict[str, Any]:
    """
    Creates a new account for a user.
    
    RULE: One user can only have one account.
    
    Args:
        user_id (int): ID of the account owner
        currency (str): Currency code (e.g., 'USD', 'SVC')
        
    Returns:
        dict: {
            'success': bool,
            'account_id': int (if success),
            'user_id': int,
            'user_name': str,
            'error': str (if failure)
        }
    """
    try:
        # Verify user exists
        user = get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "error": f"User with ID {user_id} does not exist."
            }

        # Verify user doesn't already have an account
        existing_account = get_account_by_user(user_id)
        if existing_account:
            return {
                "success": False,
                "error": f"User '{user['full_name']}' already has an account."
            }

        # Create the account
        account_id = create_account(user_id, currency)
        
        print(f"[ACCOUNT] ✅ Account created successfully for user {user['full_name']} (ID: {user_id})")
        
        return {
            "success": True,
            "account_id": account_id,
            "user_id": user_id,
            "user_name": user['full_name'],
            "currency": currency
        }
        
    except Exception as e:
        print(f"[ACCOUNT] ❌ Error creating account: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ═══════════════════════════════════════════════════════════════════════════
# TRANSACTION EXECUTION (Main Business Logic)
# ═══════════════════════════════════════════════════════════════════════════

def execute_transaction(account_number: str, amount: float, 
                       t_type: str, note: str) -> Dict[str, Any]:
    """
    Executes a transaction on an account with status validation.
    
    Implements the Traffic Light System:
      - ACTIVE (1):   Allows both CREDIT and DEBIT
      - FROZEN (2):   Allows CREDIT only, blocks DEBIT
      - CLOSED (3):   Blocks ALL operations
    
    Args:
        account_number (str): The account number
        amount (float): Transaction amount (must be positive)
        t_type (str): Transaction type ('credit' or 'debit')
        note (str): Transaction description/note
        
    Returns:
        Dict with keys:
            'success': bool - Operation succeeded
            'account_id': int - Account ID (if found)
            'account_number': str - Account number
            'status': int - Account status code
            'status_name': str - Human-readable status
            'previous_balance': float - Balance before transaction
            'new_balance': float - Balance after transaction (if successful)
            'entry_id': int - Ledger entry ID (if successful)
            'error': str - Error message (if failed)
            'created_at': str - Timestamp of transaction attempt
    """
    created_at = datetime.now().isoformat()
    
    # ─────────────────────────────────────────────────────────────────────
    # VALIDATION: Input parameters
    # ─────────────────────────────────────────────────────────────────────
    
    if not account_number or not isinstance(account_number, str):
        return {
            "success": False,
            "error": "Invalid account number",
            "created_at": created_at
        }
    
    if amount <= 0 or not isinstance(amount, (int, float)):
        return {
            "success": False,
            "error": "Amount must be a positive number",
            "created_at": created_at
        }
    
    if t_type not in ('credit', 'debit'):
        return {
            "success": False,
            "error": f"Transaction type must be 'credit' or 'debit', got '{t_type}'",
            "created_at": created_at
        }
    
    # ─────────────────────────────────────────────────────────────────────
    # FETCH: Account details
    # ─────────────────────────────────────────────────────────────────────
    
    account = get_account_by_number(account_number)
    
    if not account:
        return {
            "success": False,
            "account_number": account_number,
            "error": f"Account not found: {account_number}",
            "created_at": created_at
        }
    
    account_id = account.get('Id_account')
    status_id = account.get('status_id')
    
    # ─────────────────────────────────────────────────────────────────────
    # VALIDATION: Account Status (Traffic Light System)
    # ─────────────────────────────────────────────────────────────────────
    
    # CLOSED accounts block ALL operations
    if status_id == STATUS_CLOSED:
        return {
            "success": False,
            "account_id": account_id,
            "account_number": account_number,
            "status": status_id,
            "status_name": STATUS_NAMES.get(status_id, "UNKNOWN"),
            "error": f"Account is CLOSED. No transactions allowed.",
            "created_at": created_at
        }
    
    # FROZEN accounts allow CREDIT only
    if status_id == STATUS_FROZEN:
        if t_type == 'debit':
            previous_balance = get_balance_from_ledger(account_id)
            return {
                "success": False,
                "account_id": account_id,
                "account_number": account_number,
                "status": status_id,
                "status_name": STATUS_NAMES.get(status_id, "UNKNOWN"),
                "previous_balance": previous_balance,
                "error": f"Account is FROZEN. Debit operations are blocked.",
                "created_at": created_at
            }
    
    # ACTIVE accounts allow both CREDIT and DEBIT (default behavior)
    
    # ─────────────────────────────────────────────────────────────────────
    # EXECUTE: Ledger entry with balance enforcement
    # ─────────────────────────────────────────────────────────────────────
    
    previous_balance = get_balance_from_ledger(account_id)
    
    result = add_ledger_entry_secure(
        account_id=account_id,
        amount=amount,
        entry_type=t_type,
        description=note,
        transaction_id=None  # Optional: link to transaction table later
    )
    
    # ─────────────────────────────────────────────────────────────────────
    # RETURN: Result (success or failure)
    # ─────────────────────────────────────────────────────────────────────
    
    if result['success']:
        print(f"[ACCOUNT_SERVICE] ✅ Transaction executed successfully")
        return {
            "success": True,
            "account_id": account_id,
            "account_number": account_number,
            "status": status_id,
            "status_name": STATUS_NAMES.get(status_id, "UNKNOWN"),
            "previous_balance": previous_balance,
            "new_balance": result['balance'],
            "entry_id": result['entry_id'],
            "error": None,
            "created_at": created_at
        }
    else:
        print(f"[ACCOUNT_SERVICE] ❌ Transaction failed: {result['error']}")
        return {
            "success": False,
            "account_id": account_id,
            "account_number": account_number,
            "status": status_id,
            "status_name": STATUS_NAMES.get(status_id, "UNKNOWN"),
            "previous_balance": previous_balance,
            "error": result['error'],
            "created_at": created_at
        }


# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT QUERIES
# ═══════════════════════════════════════════════════════════════════════════

def get_account_info(account_number: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves account information with current balance.
    
    Args:
        account_number: The account number
        
    Returns:
        Dictionary with account details and current balance, or None if not found
    """
    account = get_account_by_number(account_number)
    
    if not account:
        return None
    
    account_id = account.get('Id_account')
    balance = get_balance_from_ledger(account_id)
    
    return {
        **account,
        'balance': balance,
        'status_name': STATUS_NAMES.get(account.get('status_id'), 'UNKNOWN')
    }


def get_account_balance(account_number: str) -> Optional[float]:
    """
    Gets the current balance for an account.
    
    Args:
        account_number: The account number
        
    Returns:
        Float balance, or None if account not found
    """
    account = get_account_by_number(account_number)
    
    if not account:
        return None
    
    account_id = account.get('Id_account')
    return get_balance_from_ledger(account_id)