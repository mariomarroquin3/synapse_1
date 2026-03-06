import random
from services.transaction_service import (
    create_transfer, 
    create_simple_transaction,
    ENTRY_DEBIT, 
    ENTRY_CREDIT
)
from config.database import get_cursor

def get_user_id_by_account(account_id: int):
    """
    Busca el ID del usuario dueño de una cuenta específica.
    Asegúrate de que la columna PK de 'account' se llame 'id' (o ajústalo si es distinto).
    """
    query = "SELECT [user_id] FROM [account] WHERE [Id_account] = ?"
    
    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        row = cursor.fetchone()
        
        if row:
            return row[0]
        else:
            raise Exception(f"La cuenta {account_id} no tiene un usuario asociado.")
def get_all_account_ids():
    # Eliminamos la restricción de status_id = 1 temporalmente 
    # por si tus cuentas se crearon con un estado diferente o nulo.
    query = "SELECT Id_account FROM [account]" 
    
    with get_cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        return [row[0] for row in rows]

def run_multi_type_simulation(iterations):
    print(f"🚀 Iniciando simulación de {iterations} operaciones...")
    
    account_ids = get_all_account_ids()
    if len(account_ids) < 2:
        print("❌ Error: Necesitas al menos 2 cuentas para simular.")
        return

    for i in range(iterations):
        res = {"success": False, "error": "No se ejecutó ninguna acción"}
        
        tx_type = random.choices([1, 2, 3], weights=[30, 20, 50], k=1)[0]
        amount = round(random.uniform(10.0, 150.0), 2)
        
        # 1. Elegir la cuenta origen
        acc_id = random.choice(account_ids)
        
        try:
            # 2. Obtener el DUEÑO REAL de la cuenta origen
            owner_user_id = get_user_id_by_account(acc_id)

            if tx_type == 1:
                # TRANSFERENCIA
                to_id = random.choice([id for id in account_ids if id != acc_id])
                print(f"🔄 [{i+1}] TRANSFER: Acc {acc_id} -> Acc {to_id} | ${amount}")
                # Usamos owner_user_id aquí
                res = create_transfer(acc_id, to_id, amount, "Simulación Transfer", owner_user_id)

            elif tx_type == 2:
                # RETIRO
                print(f"💸 [{i+1}] WITHDRAWAL: Acc {acc_id} | ${amount}")
                # Usamos owner_user_id aquí
                res = create_simple_transaction(acc_id, amount, ENTRY_DEBIT, "Simulación Retiro", owner_user_id)

            elif tx_type == 3:
                # DEPÓSITO
                print(f"💰 [{i+1}] DEPOSIT: Acc {acc_id} | ${amount}")
                # Usamos owner_user_id aquí
                res = create_simple_transaction(acc_id, amount, ENTRY_CREDIT, "Simulación Depósito", owner_user_id)

            # Mostrar resultado
            if res is not None and res.get("success"):
                print(f"   ✅ Éxito")
            else:
                error_msg = res.get('error') if res else "Respuesta nula"
                print(f"   ⚠️ Rechazado: {error_msg}")

        except Exception as e:
            print(f"   ❌ Error crítico en iteración {i+1}: {e}")

    print("\n--- Simulación Finalizada ---")

if __name__ == "__main__":
    run_multi_type_simulation(100)