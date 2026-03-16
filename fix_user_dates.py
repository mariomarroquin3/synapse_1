import os
import sys
from config.database import get_connection

def sync_dates_final_fix():
    conn = get_connection()
    cursor = conn.cursor()
    
    print("── Sincronizando fechas (Estrategia de Compatibilidad Total) ──")
    
    try:
        # 1. Obtenemos la fecha más antigua de transacción por cada cuenta
        # Usamos una consulta simple que Access entiende perfecto
        cursor.execute("SELECT account_id, MIN(created_at) FROM [ledger_entry] GROUP BY account_id")
        tx_data = cursor.fetchall()
        
        accounts_updated = 0
        users_updated = 0

        for account_id, first_tx in tx_data:
            if not account_id or not first_tx:
                continue

            # 2. Actualizamos la Cuenta (Account)
            # Solo si la fecha de la cuenta es posterior a la transacción
            cursor.execute("UPDATE [account] SET created_at = ? WHERE Id_account = ? AND created_at > ?", 
                           (first_tx, account_id, first_tx))
            accounts_updated += cursor.rowcount

            # 3. Buscamos el ID del usuario dueño de esa cuenta
            cursor.execute("SELECT user_id FROM [account] WHERE Id_account = ?", (account_id,))
            user_row = cursor.fetchone()
            
            if user_row:
                user_id = user_row[0]
                # 4. Actualizamos el Usuario (User)
                # Solo si su fecha de creación es posterior a la transacción
                cursor.execute("UPDATE [user] SET created_at = ? WHERE Id_user = ? AND created_at > ?", 
                               (first_tx, user_id, first_tx))
                users_updated += cursor.rowcount

        conn.commit()
        print(f"  ✅ ¡Éxito! La línea de tiempo ha sido reparada.")
        print(f"  📊 Cuentas ajustadas: {accounts_updated}")
        print(f"  📊 Usuarios ajustados: {users_updated}")

    except Exception as e:
        if conn: conn.rollback()
        print(f"  ❌ Error inesperado: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    sync_dates_final_fix()