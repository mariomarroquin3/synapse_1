from config.database import get_cursor
from typing import Any

def count_cards_by_account(account_id: int) -> int:
    """Cuenta cuántas tarjetas tiene una cuenta específica."""
    query = "SELECT COUNT(*) FROM [card] WHERE [account_id] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        row = cursor.fetchone()
        # Si row existe, devolvemos el primer elemento; si no, 0.
        return int(row[0]) if row else 0

# models/card_model.py

def insert_card(account_id: int, card_type_id: int, last4: str, token: str, holder_name: str, exp_date: Any) -> int:
    """
    Inserta la tarjeta. exp_date ahora acepta un objeto datetime 
    para ser compatible con el tipo Fecha/Hora de Access.
    """
    query = """
        INSERT INTO [card] (
            [account_id], [card_type_id], [card_number_last4], 
            [card_token], [holder_name], [expiration_date], [created_at]
        ) VALUES (?, ?, ?, ?, ?, ?, Now())
    """
    with get_cursor(commit=True) as cursor:
        cursor.execute(query, (account_id, card_type_id, last4, token, holder_name, exp_date))
        
        cursor.execute("SELECT @@IDENTITY")
        row = cursor.fetchone()
        if not row:
            raise Exception("Error al recuperar ID de tarjeta.")
        return int(row[0])

def get_card_by_token(card_token: str):
    """Busca una tarjeta usando su token de seguridad."""
    query = "SELECT * FROM [card] WHERE [card_token] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (card_token,))
        return cursor.fetchone() # Aquí devolvemos la tupla completa o None
    
def get_cards_by_account(account_id: int):
    """
    Recupera todas las tarjetas asociadas a una cuenta.
    """
    query = """
        SELECT [Id_card], [account_id], [card_type_id], 
               [card_number_last4], [card_token], [holder_name], 
               [expiration_date], [created_at]
        FROM [card] 
        WHERE [account_id] = ?
    """
    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        # fetchall() devuelve una lista de tuplas
        return cursor.fetchall()
    # Tarjetas 8-2
def get_card_with_user(account_id: int):
    """
    Obtiene la tarjeta junto con el nombre real del usuario
    compatible con Microsoft Access.
    """

    query = """
        SELECT 
            c.Id_card,
            c.card_number_last4,
            c.expiration_date,
            u.full_name
        FROM 
            ([card] AS c 
            INNER JOIN [account] AS a 
                ON c.account_id = a.id_account)
        INNER JOIN [user] AS u 
            ON a.user_id = u.id_user
        WHERE 
            c.account_id = ?
    """

    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        return cursor.fetchone()