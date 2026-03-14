"""
seed_transactions.py
─────────────────────────────────────────────────────────────
Pobla las tablas [transaction] y [ledger_entry] con movimientos
aleatorios para las cuentas activas existentes.

FASES:
  1. Fondeo inicial: depósito (tx_type=3, CREDIT) por cada cuenta.
  2. Transacciones aleatorias: 5-10 por cuenta, eligiendo al azar
     entre los 4 tipos de transacción definidos en el sistema.

TIPOS:
  tx_type=1  Transferencia  → create_transfer()
  tx_type=2  Retiro         → create_simple_transaction() DEBIT
  tx_type=3  Depósito       → create_simple_transaction() CREDIT
  tx_type=4  Pago servicio  → create_simple_transaction() DEBIT

Los montos para débitos/transferencias siempre son < $9,999
para evitar el flujo de aprobación manual.

Uso:
    python scripts/seed_transactions.py
"""

import os
import sys
import random
import pyodbc

# ── Directorio raíz del proyecto en sys.path ──────────────────────────────
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from config.database       import get_connection
from services.transaction_service import (
    create_simple_transaction,
    create_transfer,
    get_account_balance,
    ENTRY_DEBIT,
    ENTRY_CREDIT,
)

# ─────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────

MAX_AMOUNT_AUTO   = 9_999.0   # Por debajo del límite de aprobación ($10,000)
INITIAL_DEPOSIT_MIN = 1_000.0
INITIAL_DEPOSIT_MAX = 5_000.0
TX_PER_ACCOUNT_MIN  = 5
TX_PER_ACCOUNT_MAX  = 10

DEPOSIT_DESCRIPTIONS = [
    "Depósito en efectivo", "Abono de nómina", "Transferencia recibida",
    "Pago de tercero", "Ingreso freelance", "Reembolso de compra",
]
WITHDRAWAL_DESCRIPTIONS = [
    "Retiro en cajero", "Pago de alquiler", "Gastos varios",
    "Pago de servicios", "Compra de insumos", "Retiro de emergencia",
]
PAYMENT_DESCRIPTIONS = [
    "Pago de electricidad", "Pago de agua", "Pago de internet",
    "Pago de teléfono", "Pago de suscripción", "Pago de gimnasio",
]
TRANSFER_DESCRIPTIONS = [
    "Transferencia entre cuentas", "Envío de dinero", "Apoyo familiar",
    "Pago de deuda", "Préstamo personal", "Transferencia programada",
]


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

def _get_active_accounts() -> list[dict]:
    """Retorna todas las cuentas con status_id=1 (ACTIVO)."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Id_account, user_id FROM [account] WHERE status_id = 1"
        )
        rows = cursor.fetchall()
        return [{"Id_account": r[0], "user_id": r[1]} for r in rows]
    except Exception as e:
        print(f"  ❌ Error obteniendo cuentas: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def _rand_amount(min_: float, max_: float) -> float:
    """Monto aleatorio redondeado a 2 decimales."""
    return round(random.uniform(min_, max_), 2)


def _safe_debit_amount(account_id: int, cap: float = MAX_AMOUNT_AUTO) -> float | None:
    """
    Calcula un monto de débito seguro:
    - Máximo el 80% del balance actual (para no dejarlo en $0).
    - Nunca mayor a `cap`.
    Retorna None si el balance es insuficiente (< $1).
    """
    balance = get_account_balance(account_id)
    if balance < 1.0:
        return None
    usable = min(balance * 0.8, cap)
    return _rand_amount(1.0, usable)


# ─────────────────────────────────────────────────────────────────────────
# Fondeo inicial
# ─────────────────────────────────────────────────────────────────────────

def phase_initial_funding(accounts: list[dict], actor_id: int) -> None:
    """Deposita un monto inicial en cada cuenta para garantizar fondos."""
    print("\n── Fase 1: Fondeo inicial ──────────────────────────────")
    for acc in accounts:
        acc_id = acc["Id_account"]
        amount = _rand_amount(INITIAL_DEPOSIT_MIN, INITIAL_DEPOSIT_MAX)
        desc   = random.choice(DEPOSIT_DESCRIPTIONS)

        result = create_simple_transaction(
            account_id=acc_id,
            amount=amount,
            entry_type=ENTRY_CREDIT,
            description=f"[Fondeo inicial] {desc}",
            created_by_user_id=actor_id,
            transaction_type_id=3,   # Depósito
        )
        if result["success"]:
            print(f"  ✅ Cuenta {acc_id} fondada con ${amount:,.2f}")
        else:
            print(f"  ❌ Cuenta {acc_id} — error: {result.get('error')}")


# ─────────────────────────────────────────────────────────────────────────
# Transacciones aleatorias
# ─────────────────────────────────────────────────────────────────────────

def _do_transfer(from_id: int, all_ids: list[int], actor_id: int) -> dict:
    """Crea una transferencia a una cuenta aleatoria distinta."""
    candidates = [i for i in all_ids if i != from_id]
    if not candidates:
        return {"success": False, "error": "No hay cuentas destino disponibles."}

    to_id  = random.choice(candidates)
    amount = _safe_debit_amount(from_id)
    if amount is None:
        return {"success": False, "error": "Fondos insuficientes para transferencia."}

    return create_transfer(
        from_account_id=from_id,
        to_account_id=to_id,
        amount=amount,
        description=random.choice(TRANSFER_DESCRIPTIONS),
        created_by_user_id=actor_id,
        transaction_type_id=1,
    )


def _do_withdrawal(acc_id: int, actor_id: int) -> dict:
    """Crea un retiro (DEBIT, tx_type=2)."""
    amount = _safe_debit_amount(acc_id)
    if amount is None:
        return {"success": False, "error": "Fondos insuficientes para retiro."}

    return create_simple_transaction(
        account_id=acc_id,
        amount=amount,
        entry_type=ENTRY_DEBIT,
        description=random.choice(WITHDRAWAL_DESCRIPTIONS),
        created_by_user_id=actor_id,
        transaction_type_id=2,
    )


def _do_deposit(acc_id: int, actor_id: int) -> dict:
    """Crea un depósito (CREDIT, tx_type=3)."""
    amount = _rand_amount(10.0, MAX_AMOUNT_AUTO)
    return create_simple_transaction(
        account_id=acc_id,
        amount=amount,
        entry_type=ENTRY_CREDIT,
        description=random.choice(DEPOSIT_DESCRIPTIONS),
        created_by_user_id=actor_id,
        transaction_type_id=3,
    )


def _do_payment(acc_id: int, actor_id: int) -> dict:
    """Crea un pago de servicio (DEBIT, tx_type=4)."""
    amount = _safe_debit_amount(acc_id, cap=500.0)   # Pagos más pequeños
    if amount is None:
        return {"success": False, "error": "Fondos insuficientes para pago."}

    return create_simple_transaction(
        account_id=acc_id,
        amount=amount,
        entry_type=ENTRY_DEBIT,
        description=random.choice(PAYMENT_DESCRIPTIONS),
        created_by_user_id=actor_id,
        transaction_type_id=4,
    )


def phase_random_transactions(accounts: list[dict], actor_id: int) -> None:
    """Genera transacciones aleatorias para cada cuenta."""
    print("\n── Fase 2: Transacciones aleatorias ────────────────────")
    all_ids  = [a["Id_account"] for a in accounts]
    tx_types = [1, 2, 3, 4]   # Los 4 tipos disponibles

    total_ok  = 0
    total_err = 0

    for acc in accounts:
        acc_id = acc["Id_account"]
        n_tx   = random.randint(TX_PER_ACCOUNT_MIN, TX_PER_ACCOUNT_MAX)
        print(f"\n  Cuenta {acc_id}: {n_tx} transacciones")

        for _ in range(n_tx):
            tx_type = random.choice(tx_types)

            if tx_type == 1:
                result = _do_transfer(acc_id, all_ids, actor_id)
            elif tx_type == 2:
                result = _do_withdrawal(acc_id, actor_id)
            elif tx_type == 3:
                result = _do_deposit(acc_id, actor_id)
            else:  # tx_type == 4
                result = _do_payment(acc_id, actor_id)

            type_labels = {1: "Transferencia", 2: "Retiro", 3: "Depósito", 4: "Pago"}
            label = type_labels[tx_type]

            if result["success"]:
                tx_id = result.get("transaction_id", "?")
                print(f"    ✅ [{label}] TX-{tx_id}")
                total_ok += 1
            else:
                err = result.get("error", "desconocido")
                print(f"    ⚠️  [{label}] {err}")
                total_err += 1

    print(f"\n  Total OK: {total_ok} | Total errores/omitidos: {total_err}")


# ─────────────────────────────────────────────────────────────────────────
# Punto de entrada
# ─────────────────────────────────────────────────────────────────────────

def _get_actor_id() -> int:
    """Obtiene el ID del admin para usarlo como created_by_user_id."""
    from models.user_model import get_user_by_email
    user = get_user_by_email("admin@synapse.com")
    if user:
        return int(user["Id_user"])
    # Fallback: primer usuario disponible
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 1 Id_user FROM [user] ORDER BY Id_user")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return int(row[0]) if row else 1


if __name__ == "__main__":
    print("=" * 55)
    print("  SEED — Tablas [transaction] + [ledger_entry]")
    print("=" * 55)

    actor_id = _get_actor_id()
    print(f"\n  Actor (created_by_user_id): {actor_id}")

    accounts = _get_active_accounts()
    if not accounts:
        print("\n  ⚠️  No se encontraron cuentas activas.")
        print("  Ejecuta primero: seed_users.py → seed_accounts.py")
        sys.exit(1)

    print(f"  Cuentas activas encontradas: {len(accounts)}")

    phase_initial_funding(accounts, actor_id)
    phase_random_transactions(accounts, actor_id)

    print("\n" + "=" * 55)
    print("  Seed de transacciones finalizado.")
    print("=" * 55)
