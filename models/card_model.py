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

def insert_card(account_id: int, card_type_id: int, card_number: str, pin: str, holder_name: str, exp_date: Any) -> int:
    """
    Inserta una tarjeta con número completo (16 dígitos) y PIN de 4 dígitos.
    
    Args:
        account_id: ID de la cuenta propietaria
        card_type_id: Tipo de tarjeta (1=Débito, 2=Virtual, etc.)
        card_number: Número completo de 16 dígitos
        pin: PIN de 4 dígitos para validación
        holder_name: Nombre del titular
        exp_date: Fecha de expiración (datetime)
        
    Returns:
        int: ID de la tarjeta insertada
    """
    query = """
        INSERT INTO [card] (
            [account_id], [card_type_id], [card_number], 
            [pin], [holder_name], [expiration_date], [created_at]
        ) VALUES (?, ?, ?, ?, ?, ?, Now())
    """
    with get_cursor(commit=True) as cursor:
        cursor.execute(query, (account_id, card_type_id, card_number, pin, holder_name, exp_date))
        
        cursor.execute("SELECT @@IDENTITY")
        row = cursor.fetchone()
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
    
    Returns:
        list: Lista de tuplas con (Id_card, account_id, card_type_id, card_number, pin, holder_name, expiration_date, is_active, created_at)
    """
    query = """
        SELECT [Id_card], [account_id], [card_type_id], 
               [card_number], [pin], [holder_name], 
               [expiration_date], [is_active], [created_at]
        FROM [card] 
        WHERE [account_id] = ?
    """
    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        return cursor.fetchall()
    # Tarjetas 8-2
def get_card_with_user(account_id: int):
    """
    
    Returns:
        tuple: (Id_card, card_number, expiration_date, full_name) o None
    """

    query = """
        SELECT 
            c.Id_card,
            c.card_number,
            c.expiration_date,
            u.full_name
        FROM 
            ([card] AS c 
            INNER JOIN [account] AS a 
                ON c.account_id = a.Id_account)
        INNER JOIN [user] AS u 
            ON a.user_id = u.Id = a.id_account)
        INNER JOIN [user] AS u 
            ON a.user_id = u.id_user
        WHERE 
            c.account_id = ?
    """

    with get_cursor() as cursor:
        cursor.execute(query, (account_id,))
        return cursor.fetchone()