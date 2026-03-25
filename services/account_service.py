"""
account_service.py
Business Logic Layer for account operations.

Implements Pure Ledger Model with balance non-negativity enforcement
and account status controls (Traffic Light System + Approval System)

Account Status Codes:
  1 (ACTIVE):   Allows both CREDIT and DEBIT
  2 (FROZEN):   Allows CREDIT only
  3 (CLOSED):   Blocks ALL operations
  4 (PENDING):  Waiting for admin approval
  5 (REJECTED): Account creation denied
"""

from models.account_model import (
    create_account,
    get_account_by_user,
    get_account_by_id,
    get_account_by_number,
    get_balance_from_ledger,
    add_ledger_entry_secure,
    update_account_status
)

from models.user_model import get_user_by_id

from datetime import datetime
from typing import Dict, Any, Optional


# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT STATUS CODES
# ═══════════════════════════════════════════════════════════════════════════

STATUS_ACTIVE = 1
STATUS_FROZEN = 2
STATUS_CLOSED = 3
STATUS_PENDING = 4
STATUS_REJECTED = 5

STATUS_NAMES = {
    1: "ACTIVE (allows all transactions)",
    2: "FROZEN (credit only)",
    3: "CLOSED (no transactions allowed)",
    4: "PENDING (awaiting admin approval)",
    5: "REJECTED (account denied)"
}


# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT CREATION
# ═══════════════════════════════════════════════════════════════════════════

def create_account_for_user(user_id: int, currency: int) -> Dict[str, Any]:

    try:

        user = get_user_by_id(user_id)

        if not user:
            return {
                "success": False,
                "error": f"User with ID {user_id} does not exist."
            }

        existing_account = get_account_by_user(user_id)

        if existing_account:
            return {
                "success": False,
                "error": f"User '{user['full_name']}' already has an account."
            }

        # create account (should default to status 4 = PENDING)
        account_id = create_account(user_id, currency)

        print(f"[ACCOUNT] Account created in PENDING status for {user['full_name']}")

        return {
            "success": True,
            "account_id": account_id,
            "user_id": user_id,
            "user_name": user['full_name'],
            "currency": currency,
            "status": STATUS_PENDING
        }

    except Exception as e:

        print(f"[ACCOUNT] Error creating account: {e}")

        return {
            "success": False,
            "error": str(e)
        }


# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT APPROVAL SYSTEM
# ═══════════════════════════════════════════════════════════════════════════

def approve_account(account_id: int) -> Dict[str, Any]:

    try:

        account = get_account_by_id(account_id)

        if not account:
            return {
                "success": False,
                "error": "Account not found"
            }

        update_account_status(account_id, STATUS_ACTIVE)

        return {
            "success": True,
            "account_id": account_id,
            "new_status": STATUS_ACTIVE,
            "status_name": STATUS_NAMES[STATUS_ACTIVE]
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


def reject_account(account_id: int) -> Dict[str, Any]:

    try:

        account = get_account_by_id(account_id)

        if not account:
            return {
                "success": False,
                "error": "Account not found"
            }

        update_account_status(account_id, STATUS_REJECTED)

        return {
            "success": True,
            "account_id": account_id,
            "new_status": STATUS_REJECTED,
            "status_name": STATUS_NAMES[STATUS_REJECTED]
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ═══════════════════════════════════════════════════════════════════════════
# TRANSACTION EXECUTION
# ═══════════════════════════════════════════════════════════════════════════

def execute_transaction(account_number: str, amount: float,
                       t_type: str, note: str) -> Dict[str, Any]:

    created_at = datetime.now().isoformat()

    if not account_number:
        return {
            "success": False,
            "error": "Invalid account number",
            "created_at": created_at
        }

    if amount <= 0:
        return {
            "success": False,
            "error": "Amount must be positive",
            "created_at": created_at
        }

    if t_type not in ("credit", "debit"):
        return {
            "success": False,
            "error": "Invalid transaction type",
            "created_at": created_at
        }

    account = get_account_by_number(account_number)

    if not account:
        return {
            "success": False,
            "error": "Account not found",
            "created_at": created_at
        }

    account_id = account.get("Id_account")
    status_id = account.get("status_id")

    # ───────── STATUS VALIDATIONS ─────────

    if status_id == STATUS_PENDING:

        return {
            "success": False,
            "account_id": account_id,
            "status": status_id,
            "status_name": STATUS_NAMES[status_id],
            "error": "Account pending approval",
            "created_at": created_at
        }

    if status_id == STATUS_REJECTED:

        return {
            "success": False,
            "account_id": account_id,
            "status": status_id,
            "status_name": STATUS_NAMES[status_id],
            "error": "Account was rejected",
            "created_at": created_at
        }

    if status_id == STATUS_CLOSED:

        return {
            "success": False,
            "account_id": account_id,
            "status": status_id,
            "status_name": STATUS_NAMES[status_id],
            "error": "Account is closed",
            "created_at": created_at
        }

    if status_id == STATUS_FROZEN and t_type == "debit":

        return {
            "success": False,
            "account_id": account_id,
            "status": status_id,
            "status_name": STATUS_NAMES[status_id],
            "error": "Account frozen: debit blocked",
            "created_at": created_at
        }

    # ───────── EXECUTE LEDGER ENTRY ─────────

    previous_balance = get_balance_from_ledger(account_id)

    result = add_ledger_entry_secure(
        account_id=account_id,
        amount=amount,
        entry_type=t_type,
        description=note,
        transaction_id=None
    )

    if result["success"]:

        return {
            "success": True,
            "account_id": account_id,
            "previous_balance": previous_balance,
            "new_balance": result["balance"],
            "entry_id": result["entry_id"],
            "status": status_id,
            "status_name": STATUS_NAMES[status_id],
            "created_at": created_at
        }

    else:

        return {
            "success": False,
            "account_id": account_id,
            "previous_balance": previous_balance,
            "error": result["error"],
            "created_at": created_at
        }


# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT INFO
# ═══════════════════════════════════════════════════════════════════════════

def get_account_info(account_number: str) -> Optional[Dict[str, Any]]:

    account = get_account_by_number(account_number)

    if not account:
        return None

    account_id = account.get("Id_account")

    balance = get_balance_from_ledger(account_id)

    return {
        **account,
        "balance": balance,
        "status_name": STATUS_NAMES.get(account.get("status_id"), "UNKNOWN")
    }


def get_account_balance(account_number: str) -> Optional[float]:

    account = get_account_by_number(account_number)

    if not account:
        return None

    account_id = account.get("Id_account")

    return get_balance_from_ledger(account_id)
