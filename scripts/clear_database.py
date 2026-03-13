import pyodbc
import os
import sys
from dotenv import load_dotenv

# Add the project root to sys.path to import from config and utils
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from config.database import get_connection

def clear_all_tables():
    """
    Deletes all records from all tables in the database and resets autonumber IDs.
    The order of deletion is crucial to respect foreign key constraints.
    """
    # Order of deletion (child tables before parent tables)
    tables_to_clear = [
        "audit_log",
        "transaction_approvals",
        "ledger_entry",
        "transaction",
        "card_renewals",
        "card",
        "account",
        "user"
    ]

    print("--- Iniciar limpieza de base de datos ---")
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Disable some constraints if possible, but Access is strict.
        # We rely on the correct order of deletion.

        for table in tables_to_clear:
            print(f"Borrando registros de la tabla: {table}...")
            try:
                # 1. Delete all records
                cursor.execute(f"DELETE FROM [{table}]")
                
                # 2. Reset AutoNumber (Counter) in MS Access
                # This syntax works for ACE/Jet provider
                try:
                    # Alternativa para reiniciar el contador a 1 en Access
                    cursor.execute(f"ALTER TABLE [{table}] ALTER COLUMN [Id_{table}] COUNTER(1,1)")
                except pyodbc.Error as e:
                    # Some tables might have slightly different PK names or no counter
                    print(f"  Nota: No se pudo reiniciar el contador para {table} (podría no tener un campo autonumérico con el nombre estandard Id_{table}).")

                conn.commit()
                print(f"  OK: Tabla {table} vaciada.")
            except pyodbc.Error as e:
                print(f"  ERROR al vaciar {table}: {e}")
                conn.rollback()

        print("\n--- Limpieza completada con éxito ---")

    except Exception as e:
        print(f"\nERROR CRÍTICO: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Confirmación de seguridad
    print("ADVERTENCIA: Este script eliminará TODOS los datos de la base de datos.")
    confirm = input("¿Estás seguro de que deseas continuar? (si/no): ")
    
    if confirm.lower() == 'si':
        clear_all_tables()
    else:
        print("Operación cancelada.")
