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
            [account_id], [card_type_id], [card_number_last4], 
            [card_token], [holder_name], [expiration_date], [created_at]
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
    query = "SELECT * FROM [card] WHERE [card_number_last4] = ?"
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
            c.card_number_last4,
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
    
    
def get_card_by_token(input_pin: str) -> Optional[Dict[str, Any]]:
    """
    Busca por la columna card_token (que es el PIN).
    Mantiene el nombre de las llaves igual que la DB para no romper el código externo.
    """
    query = "SELECT * FROM [card] WHERE [card_token] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (input_pin,))
        row = cursor.fetchone()
        if row:
            # Esto genera automáticamente las llaves con los nombres de Access
            columns = [col[0] for col in cursor.description] 
            return dict(zip(columns, row))
        return None

#SQL está usando card_number_last4, pero en el lado de la lógica de negocio, se maneja como card_number.