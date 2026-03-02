import random
from typing import List, Dict, Any, Optional
from config.database import get_cursor

# Importar tus servicios
from services.transaction_service import (
    create_transfer, 
    create_simple_transaction,
    ENTRY_DEBIT, 
    ENTRY_CREDIT
)
from services.card_service import create_card_for_account
from services.bill_payment_service import pay_bill_with_card

# --- 1. HELPERS DE BASE DE DATOS ---
def get_all_account_ids() -> List[int]:
    query = "SELECT [Id_account] FROM [account]"
    with get_cursor() as cursor:
        cursor.execute(query)
        return [int(row[0]) for row in cursor.fetchall()]

def get_user_id_by_account(account_id: int) -> int:
    query = "SELECT [user_id] FROM [account] WHERE [id] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        row = cursor.fetchone()
        if row: 
            return int(row[0])
        else: 
            raise Exception(f"La cuenta {account_id} no tiene usuario.")

def get_card_tokens_for_account(account_id: int) -> List[str]:
    query = "SELECT [card_token] FROM [card] WHERE [account_id] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        return [str(row[0]) for row in cursor.fetchall()]

# --- 2. GENERADOR DE NÚMEROS LUHN (Para Testing) ---
def generate_valid_luhn_number(prefix: str = "4532") -> str: # <-- Tipo añadido
    """Genera un número de tarjeta de 16 dígitos que pasa la validación Luhn."""
    number = [int(x) for x in prefix]
    while len(number) < 15:
        number.append(random.randint(0, 9))
    
    calc_digits = number.copy()
    calc_digits.reverse()
    for i in range(len(calc_digits)):
        if i % 2 == 0:
            calc_digits[i] *= 2
            if calc_digits[i] > 9:
                calc_digits[i] -= 9
                
    check_digit = (10 - (sum(calc_digits) % 10)) % 10
    number.append(check_digit)
    
    return "".join(map(str, number))

# --- 3. FASE 1: SEMBRADO DE TARJETAS ---
def seed_cards_for_accounts(account_ids: List[int]) -> None: # <-- Tipos añadidos
    print("\n--- FASE 1: Generando Tarjetas ---")
    for acc_id in account_ids:
        for _ in range(2): 
            luhn_number = generate_valid_luhn_number()
            holder_name = f"Test User Acc {acc_id}"
            card_type_id = random.choice([1, 2])
            
            res = create_card_for_account(acc_id, card_type_id, holder_name, luhn_number)
            if res.get("success"):
                print(f"💳 Tarjeta creada para Cuenta {acc_id} | Últimos 4: {res.get('last4')}")
            else:
                pass
    print("✅ Fase de tarjetas completada.")

# --- 4. FASE 2: SIMULACIÓN DE TRANSACCIONES Y PAGOS ---
def run_multi_type_simulation(iterations: int = 15) -> None: # <-- Tipos añadidos
    print(f"\n🚀 FASE 2: Iniciando {iterations} operaciones...")
    
    account_ids = get_all_account_ids()
    if len(account_ids) < 2:
        print("❌ Error: Necesitas al menos 2 cuentas para simular.")
        return
        
    seed_cards_for_accounts(account_ids)

    for i in range(iterations):
        # Explicitamente declaramos que res es un diccionario
        res: Dict[str, Any] = {"success": False, "error": "No ejecutado"}
        
        tx_type = random.choices([1, 2, 3, 4], weights=[20, 10, 45, 25], k=1)[0]
        amount = round(random.uniform(10.0, 150.0), 2)
        acc_id = random.choice(account_ids)
        
        try:
            owner_user_id = get_user_id_by_account(acc_id)

            if tx_type == 1:
                to_id = random.choice([id for id in account_ids if id != acc_id])
                print(f"🔄 [{i+1}] TRANSFER: {acc_id} -> {to_id} | ${amount}")
                res = create_transfer(acc_id, to_id, amount, "Sim. Transfer", owner_user_id)

            elif tx_type == 2:
                print(f"💸 [{i+1}] WITHDRAWAL: {acc_id} | ${amount}")
                res = create_simple_transaction(acc_id, amount, ENTRY_DEBIT, "Sim. Retiro", owner_user_id)

            elif tx_type == 3:
                print(f"💰 [{i+1}] DEPOSIT: {acc_id} | ${amount}")
                res = create_simple_transaction(acc_id, amount, ENTRY_CREDIT, "Sim. Depósito", owner_user_id)
                
            elif tx_type == 4:
                tokens = get_card_tokens_for_account(acc_id)
                if not tokens:
                    print(f"🛒 [{i+1}] PAYMENT: Saltado. Cuenta {acc_id} no tiene tarjetas.")
                    continue
                    
                token = random.choice(tokens)
                bill_name = random.choice(["Netflix", "Spotify", "Luz Eléctrica", "Amazon AWS", "Agua"])
                print(f"🛒 [{i+1}] PAYMENT: {acc_id} pagando {bill_name} | ${amount}")
                
                res = pay_bill_with_card(token, amount, bill_name, owner_user_id)

            # Ya no verificamos 'if res is not None' porque garantizamos que es un Dict
            if res.get("success"):
                print(f"   ✅ Éxito")
            else:
                print(f"   ⚠️ Rechazado: {res.get('error', 'Nulo')}")

        except Exception as e:
            print(f"   ❌ Error crítico: {e}")

    print("\n--- Simulación Finalizada ---")

if __name__ == "__main__":
    run_multi_type_simulation(20)