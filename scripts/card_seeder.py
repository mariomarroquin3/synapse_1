import os
import sys
import random
from datetime import datetime, timedelta

# Configuración de rutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from config.database import get_connection

def generate_card_number():
    """Genera el número de tarjeta principal de 16 dígitos."""
    return "".join([str(random.randint(0, 9)) for _ in range(16)])

def generate_validation_pin():
    """Genera el PIN de validación de 4 dígitos (card_number_last4)."""
    return "".join([str(random.randint(0, 9)) for _ in range(4)])

def get_owner_name(cursor, user_id):
    cursor.execute("SELECT full_name FROM [user] WHERE Id_user = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else "Tarjetahabiente"

def seed_cards():
    conn = get_connection()
    cursor = conn.cursor()
    
    print("── Seed: Generando Tarjetas (PIN de Validación + 16 Dígitos) ──")
    
    cursor.execute("SELECT Id_account, user_id FROM [account] WHERE status_id = 1")
    accounts = cursor.fetchall()
    
    expiry_date = (datetime.now() + timedelta(days=365*4))
    cards_created = 0

    for acc in accounts:
        acc_id = acc[0]
        user_id = acc[1]
        
        cursor.execute("SELECT COUNT(*) FROM [card] WHERE account_id = ?", (acc_id,))
        if cursor.fetchone()[0] == 0:
            full_num = generate_card_number()
            # Ahora card_number_last4 es el PIN de validación independiente
            val_pin = generate_validation_pin() 
            holder = get_owner_name(cursor, user_id)
            
            # Asignación aleatoria: 1 (Débito) o 2 (Virtual)
            card_type = random.choice([1, 2])
            
            cursor.execute("""
                INSERT INTO [card] (
                    account_id, 
                    card_type_id, 
                    card_number, 
                    card_number_last4, 
                    holder_name, 
                    expiration_date, 
                    created_at, 
                    is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                acc_id, 
                card_type,
                full_num, 
                val_pin,    # Aquí va el PIN de 4 dígitos
                holder, 
                expiry_date, 
                datetime.now(), 
                True
            ))
            cards_created += 1

    conn.commit()
    conn.close()
    print(f"✅ Seed exitoso. {cards_created} tarjetas (Débito/Virtual) con PIN de validación creado.")

if __name__ == "__main__":
    seed_cards()