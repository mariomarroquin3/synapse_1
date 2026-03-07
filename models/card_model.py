from config.database import get_cursor
from typing import Any, Dict, Optional

def count_cards_by_account(account_id: int) -> int:
    """Cuenta cuántas tarjetas tiene una cuenta específica."""
    query = "SELECT COUNT(*) FROM [card] WHERE [account_id] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        row = cursor.fetchone()
        # Si row existe, devolvemos el primer elemento; si no, 0.
        return int(row[0]) if row else 0

# models/card_model.py

def insert_card(account_id: int, card_type_id: int, card_number: str, pin: str, holder_name: str, exp_date: Any) -> int:
    """
    Inserta una tarjeta con número completo de 16 dígitos y PIN.
    """

    query = """
        INSERT INTO [card] (
            [account_id],
            [card_type_id],
            [card_number],
            [card_number_last4],
            [holder_name],
            [expiration_date],
            [created_at]
        ) VALUES (?, ?, ?, ?, ?, ?, Now())
    """

    with get_cursor(commit=True) as cursor:
        cursor.execute(query, (
            account_id,
            card_type_id,
            card_number,
            pin,  # aquí guardas el PIN
            holder_name,
            exp_date
        ))

        cursor.execute("SELECT @@IDENTITY")
        row = cursor.fetchone()

        if not row:
            raise Exception("Error al recuperar ID de tarjeta.")

        return int(row[0])

        if not row:
            raise Exception("Error al recuperar ID de tarjeta.")

        return int(row[0])

def get_card_by_number(card_number: str):
    """Busca una tarjeta usando su número completo de 16 dígitos."""
    query = "SELECT * FROM [card] WHERE [card_number] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (card_number,))
        return cursor.fetchone() # Devuelve la tupla completa o None
    
def get_cards_by_account(account_id: int):
    """
    Recupera todas las tarjetas asociadas a una cuenta.
    """
    query = "SELECT * FROM [card] WHERE [account_id] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        rows = cursor.fetchall()
        # Convertimos a lista de diccionarios para mayor seguridad
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

def get_card_with_user(account_id: int):
    """
    Retorna información de la tarjeta y el usuario asociado.
    """
    query = """
        SELECT 
            c.Id_card,
            c.card_number,
            c.expiration_date,
            u.full_name
        FROM ([card] AS c 
        INNER JOIN [account] AS a ON c.account_id = a.Id_account)
        INNER JOIN [user] AS u ON a.user_id = u.Id_user
        WHERE c.account_id = ?
    """
    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        row = cursor.fetchone()
        if row:
            return dict(zip([col[0] for col in cursor.description], row))
        return None
    
def update_card_status(card_id: int, is_active: bool) -> bool:
    """
    Actualiza el estado booleano de la tarjeta.
    """
    query = "UPDATE [card] SET [is_active] = ? WHERE [Id_card] = ?"
    with get_cursor(commit=True) as cursor:
        try:
            # En Access True/False se suele traducir en 1/0 o True/False nativo.
            # pyodbc suele encargarse del boolean tipo True/False.
            cursor.execute(query, (is_active, card_id))
            return True
        except Exception as e:
            raise Exception(f"Error actualizando estado de tarjeta: {str(e)}")

#SQL está usando card_number_last4, pero en el lado de la lógica de negocio, se maneja como card_number.