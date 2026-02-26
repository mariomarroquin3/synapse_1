from config.database import get_cursor
from datetime import datetime
import random


def get_account_by_user(user_id: int):
    # Consulta para obtener la cuenta asociada al usuario
    query = "SELECT * FROM [account] WHERE [user_id] = ?"

    # Abre conexión a la base de datos
    with get_cursor() as cursor:
        # Ejecuta la consulta enviando el user_id
        cursor.execute(query, (user_id,))
        
        # Devuelve la primera cuenta encontrada
        return cursor.fetchone()


def account_number_exists(account_number: str):
    # Consulta para verificar si el número ya existe
    query = "SELECT 1 FROM [account] WHERE [account_number] = ?"

    # Abre conexión a la base de datos
    with get_cursor() as cursor:
        # Ejecuta la consulta con el número de cuenta
        cursor.execute(query, (account_number,))
        
        # Retorna True si existe, False si no
        return cursor.fetchone() is not None


def generate_account_number():
    while True:
        # Example: SV_synapse (Bank Code) + random digits
        number = f"SV_synapse{random.randint(1000000, 9999999)}" 
        if not account_number_exists(number):
            return number

def create_account(user_id: int, currency: str):

    # Consulta para insertar nueva cuenta
    query = """
        INSERT INTO [account] (
            [user_id],
            [account_number],
            [currency],
            [status_id],
            [created_at]
        )
        VALUES (?, ?, ?, ?, ?)
    """

    # Abre conexión con commit automático
    with get_cursor(commit=True) as cursor:
        cursor.execute(
            query,
            (
                user_id,                      # ID del usuario dueño
                generate_account_number(),    # Número único generado
                currency,                     # Moneda de la cuenta
                1,                            # Estado activo por defecto
                datetime.now()                # Fecha de creación
            )
        )