import random
from typing import List, Dict, Any
from config.database import get_cursor

# Importamos todos tus servicios y constantes
from services.transaction_service import (
    create_simple_transaction,
    create_transfer,
    ENTRY_DEBIT,
    ENTRY_CREDIT
)

# --- 1. HELPERS DE BASE DE DATOS ---
def get_all_accounts() -> List[Dict[str, Any]]:
    """Obtiene todas las cuentas con su user_id asociado."""
    query = """
        SELECT [Id_account], [user_id] 
        FROM [account]
    """
    with get_cursor() as cursor:
        cursor.execute(query)
        return [
            {
                'account_id': int(row[0]),
                'user_id': int(row[1])
            } 
            for row in cursor.fetchall()
        ]


def get_all_cards_info() -> List[Dict[str, Any]]:
    """Obtiene las tarjetas disponibles usando los nombres reales de las columnas."""
    # Columnas confirmadas:
    # En [card]: account_id, card_number_last4, card_token
    # En [account]: Id_account, user_id
    query = """
        SELECT c.[account_id], a.[user_id], c.[card_number_last4], c.[card_token] 
        FROM [card] c
        INNER JOIN [account] a ON c.[account_id] = a.[Id_account]
    """
    with get_cursor() as cursor:
        cursor.execute(query)
        return [
            {
                "account_id": row[0], 
                "user_id": int(row[1]), 
                "card_number": str(row[2]),  # Mapeamos card_number_last4 (ya es 4 dígitos)
                "card_token": str(row[3])
            } 
            for row in cursor.fetchall()
        ]


# --- 2. SIMULACIÓN COMPLETA ---
def run_full_simulation(iterations: int = 15) -> None:
    print(f"\n🚀 INICIANDO SIMULACIÓN MIXTA: {iterations} operaciones...")
    
    accounts_data = get_all_accounts()
    cards_data = get_all_cards_info()
    
    if len(accounts_data) < 2:
        print("❌ Error: Necesitas al menos 2 cuentas para simular.")
        return
        
    print(f"✅ Cuentas: {len(accounts_data)} | Tarjetas: {len(cards_data)}\n")

    for i in range(iterations):
        res: Dict[str, Any] = {"success": False, "error": "No ejecutado"}
        
        # Opciones: 1=Transferencia, 2=Retiro Normal, 3=Depósito, 4=Pago con Tarjeta
        tx_type = random.choices([1, 2, 3, 4], weights=[20, 20, 30, 30], k=1)[0]
        amount = round(random.uniform(5.0, 150.0), 2)
        
        try:
            if tx_type == 1:
                # TRANSFERENCIA (Sin tarjeta)
                # Obtener dos cuentas diferentes
                from_acc_data = random.choice(accounts_data)
                to_acc_data = random.choice([a for a in accounts_data if a['account_id'] != from_acc_data['account_id']])
                
                from_account_id = from_acc_data['account_id']
                from_user_id = from_acc_data['user_id']
                to_account_id = to_acc_data['account_id']
                
                print(f"🔄 [{i+1}] TRANSFERENCIA: Cuenta {from_account_id} -> {to_account_id} | ${amount}")
                res = create_transfer(from_account_id, to_account_id, amount, "Transferencia de prueba", from_user_id)

            elif tx_type == 2:
                # RETIRO EN SUCURSAL/ATM (Sin tarjeta requerida para este test)
                acc_data = random.choice(accounts_data)
                account_id = acc_data['account_id']
                user_id = acc_data['user_id']
                
                print(f"💸 [{i+1}] RETIRO: Cuenta {account_id} | ${amount}")
                res = create_simple_transaction(
                    account_id=account_id, 
                    amount=amount, 
                    entry_type=ENTRY_DEBIT, 
                    description="Retiro en sucursal", 
                    created_by_user_id=user_id,  # Usar user_id real
                    transaction_type_id=2
                )

            elif tx_type == 3:
                # DEPÓSITO (Usa ENTRY_CREDIT)
                acc_data = random.choice(accounts_data)
                account_id = acc_data['account_id']
                user_id = acc_data['user_id']
                
                print(f"💰 [{i+1}] DEPÓSITO: Cuenta {account_id} | ${amount}")
                res = create_simple_transaction(
                    account_id=account_id, 
                    amount=amount, 
                    entry_type=ENTRY_CREDIT, 
                    description="Depósito en ventanilla", 
                    created_by_user_id=user_id,  # Usar user_id real
                    transaction_type_id=3
                )
                
            elif tx_type == 4:
                # PAGO CON TARJETA (Usa ENTRY_DEBIT + card_number + card_token)
                if not cards_data:
                    print(f"🛒 [{i+1}] PAGO TARJETA: Saltado (No hay tarjetas)")
                    continue
                    
                card_info = random.choice(cards_data)
                account_id = card_info["account_id"]
                user_id = card_info["user_id"]
                card_number = card_info["card_number"]
                card_token = card_info["card_token"]
                merchant = random.choice(["Netflix", "Amazon", "Supermercado", "Gasolinera"])
                
                print(f"💳 [{i+1}] PAGO TARJETA: Cuenta {account_id} | Tarjeta {card_number[-4:]} | {merchant} | ${amount}")
                res = create_simple_transaction(
                    account_id=account_id, 
                    amount=amount, 
                    entry_type=ENTRY_DEBIT, 
                    description=f"Compra en {merchant}", 
                    created_by_user_id=user_id,  # Usar user_id real de la tarjeta
                    transaction_type_id=4,
                    card_number=card_number,      # 4 dígitos finales
                    card_token=card_token          # Token actual de la BD
                )

            # Resultados
            if res.get("success"):
                print(f"   ✅ OK")
            else:
                print(f"   ⚠️ Falló: {res.get('error')}")

        except Exception as e:
            print(f"   ❌ Error en iteración {i+1}: {e}")

    print("\n--- Simulación Finalizada ---")

if __name__ == "__main__":
    run_full_simulation(20)