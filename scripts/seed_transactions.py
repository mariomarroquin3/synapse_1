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
TX_PER_ACCOUNT_MIN  = 1
TX_PER_ACCOUNT_MAX  = 2

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
def _get_masked_card_for_description(account_id: int) -> str | None:
    """Extrae los últimos 4 dígitos del número de tarjeta para el log."""
    conn = get_connection()
    cursor = conn.cursor()
    # Obtenemos el card_number de 16 dígitos
    cursor.execute("SELECT card_number FROM [card] WHERE account_id = ? AND is_active = True", (account_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        full_number = row[0]
        return full_number[-4:] # Extraemos los últimos 4 del número real
    return None

from datetime import datetime, timedelta

def _get_random_past_date(days_back: int = 90) -> datetime:
    """Genera una fecha aleatoria entre hoy y N días atrás."""
    random_days = random.randint(0, days_back)
    random_hours = random.randint(0, 23)
    random_minutes = random.randint(0, 59)
    
    past_date = datetime.now() - timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
    return past_date

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
# Transacciones aleatorias (CORREGIDO: Ahora recibe el owner_id)
# ─────────────────────────────────────────────────────────────────────────

def _do_transfer(from_id: int, owner_id: int, all_ids: list[int]) -> dict:
    """Crea una transferencia siendo el dueño de la cuenta quien la ejecuta."""
    candidates = [i for i in all_ids if i != from_id]
    if not candidates:
        return {"success": False, "error": "No hay cuentas destino disponibles."}

    to_id  = random.choice(candidates)
    amount = _safe_debit_amount(from_id)
    if amount is None:
        return {"success": False, "error": "Fondos insuficientes."}

    return create_transfer(
        from_account_id=from_id,
        to_account_id=to_id,
        amount=amount,
        description=random.choice(TRANSFER_DESCRIPTIONS),
        created_by_user_id=owner_id, # <--- CAMBIO: El usuario dueño transacciona
        transaction_type_id=1,
    )

def _do_withdrawal(acc_id: int, owner_id: int) -> dict:
    """Cajero Automático: El dueño retira su dinero."""
    amount = _safe_debit_amount(acc_id)
    if amount is None: return {"success": False, "error": "Fondos insuficientes."}

    return create_simple_transaction(
        account_id=acc_id,
        amount=amount,
        entry_type=ENTRY_DEBIT,
        description=random.choice(WITHDRAWAL_DESCRIPTIONS),
        created_by_user_id=owner_id, # <--- CAMBIO
        transaction_type_id=2,
    )

def _do_deposit(acc_id: int, owner_id: int) -> dict:
    amount = _rand_amount(10.0, MAX_AMOUNT_AUTO)
    return create_simple_transaction(
        account_id=acc_id,
        amount=amount,
        entry_type=ENTRY_CREDIT,
        description=random.choice(DEPOSIT_DESCRIPTIONS),
        created_by_user_id=owner_id, # <--- CAMBIO
        transaction_type_id=3,
    )

def _do_payment(acc_id: int, owner_id: int) -> dict:
    """
    Simula un pago de servicio utilizando la tarjeta vinculada a la cuenta.
    """
    # 1. Intentamos obtener la tarjeta (necesaria para el realismo del log)
    card_info = _get_masked_card_for_description(acc_id)
    
    # 2. Si por alguna razón la cuenta no tiene tarjeta, fallamos la TX
    # Esto ayuda a validar que el seed_cards corrió bien
    if not card_info:
        return {"success": False, "error": f"Cuenta {acc_id} no tiene tarjeta activa para pagos."}

    # 3. Calculamos un monto lógico para servicios (capado a $500 para realismo)
    amount = _safe_debit_amount(acc_id, cap=500.0)
    if amount is None: 
        return {"success": False, "error": "Fondos insuficientes para cubrir el recibo."}

    # 4. Construimos una descripción detallada
    # Ejemplo: "Pago de electricidad (Visa: ****1234)"
    service_name = random.choice(PAYMENT_DESCRIPTIONS)
    full_description = f"{service_name} (Tarj: ****{card_info})"

    # 5. Ejecutamos la transacción
    return create_simple_transaction(
        account_id=acc_id,
        amount=amount,
        entry_type=ENTRY_DEBIT,
        description=full_description,
        created_by_user_id=owner_id,
        transaction_type_id=4,   # Tipo: Pago de Servicio
    )

# ─────────────────────────────────────────────────────────────────────────
# Fases de ejecución actualizadas
# ─────────────────────────────────────────────────────────────────────────

def phase_initial_funding(accounts: list[dict], fallback_actor_id: int) -> None:
    """Fondeo inicial: Aquí sí puede ser el Admin o el propio usuario."""
    print("\n── Fase 1: Fondeo inicial ──────────────────────────────")
    for acc in accounts:
        acc_id = acc["Id_account"]
        owner_id = acc["user_id"] # Usamos el dueño de la cuenta
        amount = _rand_amount(INITIAL_DEPOSIT_MIN, INITIAL_DEPOSIT_MAX)
        
        create_simple_transaction(
            account_id=acc_id,
            amount=amount,
            entry_type=ENTRY_CREDIT,
            description="[Fondeo inicial] Depósito de apertura",
            created_by_user_id=owner_id, # El usuario 'abre' su cuenta
            transaction_type_id=3,
        )
    print(f"  ✅ {len(accounts)} cuentas fondeadas.")

def phase_random_transactions(accounts: list[dict]) -> None:
    """Genera transacciones distribuidas por usuario."""
    print("\n── Fase 2: Transacciones aleatorias ────────────────────")
    all_ids  = [a["Id_account"] for a in accounts]
    total_ok = 0

    for acc in accounts:
        acc_id = acc["Id_account"]
        owner_id = acc["user_id"] # <--- IMPORTANTE: Recuperamos el dueño real
        n_tx = random.randint(TX_PER_ACCOUNT_MIN, TX_PER_ACCOUNT_MAX)

        for _ in range(n_tx):
            tx_type = random.choice([1, 2, 3, 4])
            if tx_type == 1:   res = _do_transfer(acc_id, owner_id, all_ids)
            elif tx_type == 2: res = _do_withdrawal(acc_id, owner_id)
            elif tx_type == 3: res = _do_deposit(acc_id, owner_id)
            else:              res = _do_payment(acc_id, owner_id)

            if res["success"]: total_ok += 1

    print(f"  ✅ Seed finalizado: {total_ok} transacciones reales creadas.")

if __name__ == "__main__":
    # 1. Obtener cuentas (ya traen el user_id)
    accounts = _get_active_accounts()
    
    # 2. Ejecutar fases sin forzar un único actor global
    phase_initial_funding(accounts, 1) 
    phase_random_transactions(accounts)