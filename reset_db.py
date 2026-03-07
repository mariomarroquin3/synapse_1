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
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        print("--- Iniciando limpieza de base de datos ---")
        
        for table in tables_to_clear:
            try:
                print(f"Limpiando tabla: {table}...")
                cursor.execute(f"DELETE FROM [{table}]")
                # Reiniciar contadores de identidad si es posible en Access
                # Nota: Access no tiene TRUNCATE, y 'DELETE' no reinicia el Autonumérico
                # Para reiniciar el ID, se suele requerir Compactar y Reparar.
            except pyodbc.Error as e:
                print(f"  Error al limpiar {table}: {e}")
        
        conn.commit()
        print("\n✅ Todos los registros operativos han sido eliminados.")
        print("⚠️  Nota: Los IDs autonuméricos no se reiniciarán hasta que se use 'Compactar y Reparar' en MS Access.")
        
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
