import pyodbc
from config.database import get_connection

def clear_database():
    """
    Elimina todos los registros de las tablas operativas de la base de datos.
    Mantiene las tablas de catálogo (roles, estados, tipos).
    """
    
    # Orden de eliminación para respetar llaves foráneas
    tables_to_clear = [
        "audit_log",
        "transaction_approvals",
        "ledger_entry",
        "transaction",
        "card",
        "account",
        "user"
    ]
    
    # Mapeo de tablas y sus columnas Autonuméricas (Identity)
    # Se obtuvieron de los modelos y metadata del sistema
    table_identity_cols = {
        "user": "Id_user",
        "account": "Id_account",
        "card": "Id_card",
        "transaction": "Id_transaction",
        "ledger_entry": "Id_entry",
        "transaction_approvals": "Id_approval", 
        "audit_log": "Id_log"
    }

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        print("--- Iniciando limpieza y reset de base de datos ---")
        
        # 1. Eliminar datos en orden reverso de FKs
        for table in tables_to_clear:
            try:
                print(f"Limpiando datos de la tabla: {table}...")
                cursor.execute(f"DELETE FROM [{table}]")
            except pyodbc.Error as e:
                print(f"  Error al limpiar {table}: {e}")
        
        # 2. Resetear contadores Autonuméricos (COUNTER(1,1))
        # Esto hace que el siguiente registro empiece en 1
        print("\n--- Reseteando contadores de ID ---")
        for table, identity_col in table_identity_cols.items():
            try:
                print(f"Reseteando ID en {table} ([{identity_col}])...")
                # MS Access SQL: ALTER TABLE [tab] ALTER COLUMN [col] COUNTER(1,1)
                cursor.execute(f"ALTER TABLE [{table}] ALTER COLUMN [{identity_col}] COUNTER(1,1)")
            except pyodbc.Error as e:
                # Si la columna no es autonumérica o el nombre no coincide, saltamos sin error fatal
                print(f"  Aviso: No se pudo resetear ID en {table}: {e}")
        
        conn.commit()
        print("\n✅ Limpieza y reset de IDs completado exitosamente.")
        print("El próximo registro insertado comenzará con el ID 1.")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n❌ Error general: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    confirm = input("¿Estás seguro de que deseas eliminar TODOS los registros operativos? (s/n): ")
    if confirm.lower() == 's':
        clear_database()
    else:
        print("Operación cancelada.")
