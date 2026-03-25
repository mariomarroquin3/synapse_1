import pyodbc
import os
import sys
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from config.database import get_connection

# Configuration: Table, Constraint Name, Column, Referenced Table(Field)
RELATIONS = [
    ("account", "account_statusesaccounts", "status_id", "account_status(Id_status)"),
    ("account", "usersaccounts", "user_id", "user(Id_user)"),
    ("audit_log", "actionsaudit_log", "action", "action(Id_action)"),
    ("audit_log", "usersaudit_log", "user_id", "user(Id_user)"),
    ("card", "accountscards", "account_id", "account(Id_account)"),
    ("card", "card_typescards", "card_type_id", "card_type(Id_type)"),
    ("card_renewals", "cardscard_renewals", "card_id", "card(Id_card)"),
    ("ledger_entry", "accountsledger_entry", "account_id", "account(Id_account)"),
    ("ledger_entry", "transactionsledger_entry", "transaction_id", "transaction(Id_transaction)"),
    ("transaction", "transaction_statusestransactions", "status_id", "transaction_status(Id_transaction_status)"),
    ("transaction", "transaction_typestransactions", "transaction_type_id", "transaction_type(Id_transaction_type)"),
    ("transaction", "userstransactions", "created_by_user_id", "user(Id_user)"),
    ("transaction_approvals", "accounttransaction_approvals", "from_account_id", "account(Id_account)"),
    ("transaction_approvals", "accounttransaction_approvals1", "to_account_id", "account(Id_account)"),
    ("transaction_approvals", "transactionstransaction_approvals", "transaction_id", "transaction(Id_transaction)"),
    ("transaction_approvals", "userstransaction_approvals", "admin_id", "user(Id_user)"),
    ("user", "rolesusers", "role_id", "rol(Id_rol)")
]

# Tables and their Primary Key columns for counter reset
TABLES_TO_RESET = {
    "account": "Id_account",
    "audit_log": "Id_log",
    "card": "Id_card",
    "card_renewals": "Id_renewal",
    "ledger_entry": "Id_entry",
    "transaction": "Id_transaction",
    "transaction_approvals": "Id_approval",
    "user": "Id_user"
}

def reset_database_counters():
    conn = get_connection()
    cursor = conn.cursor()
    
    print("--- 1. Eliminando Relaciones (Foreign Keys) ---")
    for table, constraint, col, ref in RELATIONS:
        try:
            query = f"ALTER TABLE [{table}] DROP CONSTRAINT [{constraint}]"
            cursor.execute(query)
            print(f"  OK: Relación '{constraint}' eliminada de {table}.")
        except Exception as e:
            print(f"  Aviso: No se pudo eliminar '{constraint}' de {table}. Posiblemente no existe. Error: {e}")
    conn.commit()

    print("\n--- 2. Reiniciando Contadores (AUTOINCREMENT) ---")
    for table, pk in TABLES_TO_RESET.items():
        try:
            # First, ensure table is empty (belt and suspenders)
            cursor.execute(f"DELETE FROM [{table}]")
            # Reset counter
            query = f"ALTER TABLE [{table}] ALTER COLUMN [{pk}] COUNTER(1,1)"
            cursor.execute(query)
            print(f"  OK: Contador de {table} reiniciado en 1.")
        except Exception as e:
            print(f"  ERROR: No se pudo reiniciar contador de {table}. Error: {e}")
    conn.commit()

    print("\n--- 3. Restaurando Relaciones (Foreign Keys) ---")
    for table, constraint, col, ref in RELATIONS:
        try:
            query = f"ALTER TABLE [{table}] ADD CONSTRAINT [{constraint}] FOREIGN KEY ([{col}]) REFERENCES {ref}"
            cursor.execute(query)
            print(f"  OK: Relación '{constraint}' restaurada en {table}.")
        except Exception as e:
            print(f"  ERROR Crítico: No se pudo restaurar '{constraint}' en {table}. Error: {e}")
    conn.commit()

    conn.close()
    print("\n--- ¡Proceso Completado con Éxito! ---")
    print("Todos los contadores deberían haber regresado a 1.")

if __name__ == "__main__":
    # Confirmación de seguridad
    print("ADVERTENCIA: Este script eliminará TODOS los datos de la base de datos (excepto configuración).")
    confirm = input("¿Estás seguro de que deseas continuar? (si/no): ")
    
    if confirm.lower() in ['si', 's', 'y', 'yes']:
        reset_database_counters()
    else:
        print("Operación cancelada.")
