from config.database import get_cursor
from typing import Any, Dict, Optional
import datetime
import streamlit as st

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
    
@st.cache_data(ttl=60)
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

# --- FLUJO DE RENOVACIÓN DE TARJETAS ---

def is_card_near_expiration(expiration_date) -> bool:
    """Retorna True si la tarjeta vence en 30 días o menos, o si ya venció."""
    if not expiration_date:
        return False
    # Asume expiration_date como datetime.date o datetime.datetime
    # MS Access puede devolver un datetime.datetime
    now = datetime.datetime.now()
    if isinstance(expiration_date, datetime.date) and not isinstance(expiration_date, datetime.datetime):
        exp_dt = datetime.datetime.combine(expiration_date, datetime.time.min)
    else:
        exp_dt = expiration_date
    delta = exp_dt - now
    return delta.days <= 30

def check_pending_renewal(card_id: int) -> bool:
    """Retorna True si ya existe una solicitud de renovación sin procesar."""
    query = "SELECT COUNT(*) FROM [card_renewals] WHERE [card_id] = ? AND [processed] = False"
    with get_cursor() as cursor:
        cursor.execute(query, (card_id,))
        count = cursor.fetchone()[0]
        return count > 0

def request_card_renewal(card_id: int, account_id: int, user_id: int) -> Dict[str, Any]:
    """Solicita la renovación: cobra $5, marca inactiva e inserta en la tabla auxiliar."""
    # Evitar doble solicitud
    if check_pending_renewal(card_id):
        return {"success": False, "error": "Ya existe una renovación en proceso."}
    
    # Aquí debemos cobrar los $5. Para evitar dependencias circulares complejas, 
    # instanciamos un entry directo o llamamos al transaction engine asegurando importe
    from services.transaction_service import create_simple_transaction
    
    pay_res = create_simple_transaction(
        account_id=account_id,
        amount=5.00,
        entry_type="debit",
        description=f"Pago por comisión de renovación (Tarjeta #{card_id})",
        created_by_user_id=user_id,
        transaction_type_id=4, # Pago
        status_id=3 
    )
    
    if not pay_res.get("success"):
        return {"success": False, "error": f"Fondos insuficientes o error facturando: {pay_res.get('error')}"}
    
    # Cobro exitoso, proceder
    try:
        update_card_status(card_id, False) # Apagamos la tarjeta
        # Insertamos el ticket
        q_insert = "INSERT INTO [card_renewals] ([card_id], [requested_at], [processed]) VALUES (?, Now(), False)"
        with get_cursor(commit=True) as cursor:
            cursor.execute(q_insert, (card_id,))
            
        from services.audit_service import log_action
        log_action(user_id, "SOLICITUD_RENOVACION_TARJETA", f"Cliente solicitó renovación de la tarjeta ID {card_id}")
            
        return {"success": True, "message": "Solicitud completada y cobro efectuado."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_pending_renewals():
    """Recupera los tickets de renovación listos para atención por cajero."""
    query = """
        SELECT 
            cr.Id_renewal,
            cr.card_id,
            cr.requested_at,
            c.card_number_last4,
            a.account_number,
            u.full_name,
            u.DUI
        FROM (([card_renewals] cr
        INNER JOIN [card] c ON cr.card_id = c.Id_card)
        INNER JOIN [account] a ON c.account_id = a.Id_account)
        INNER JOIN [user] u ON a.user_id = u.Id_user
        WHERE cr.processed = False
        ORDER BY cr.requested_at ASC
    """
    with get_cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        if not rows: return []
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in rows]

def finalize_card_renewal(renewal_id: int, card_id: int, admin_id: int) -> bool:
    """Agrega 3 años a la tarjeta, la reactiva y marca el ticket como procesado."""
    try:
        # 1. Obtener la expiración actual desde la tabla base
        q_exp = "SELECT [expiration_date], [card_number_last4] FROM [card] WHERE [Id_card] = ?"
        with get_cursor() as cursor:
            cursor.execute(q_exp, (card_id,))
            row = cursor.fetchone()
            if not row:
                raise Exception("Tarjeta no encontrada para renovación.")
            current_exp = row[0]
            last4 = row[1]
        
        # 2. Agregar 3 años a esa fecha
        from dateutil.relativedelta import relativedelta
        new_exp = current_exp + relativedelta(years=3)
        
        # 3. Guardar todo
        q_update_card = "UPDATE [card] SET [expiration_date] = ?, [is_active] = True WHERE [Id_card] = ?"
        q_update_ticket = "UPDATE [card_renewals] SET [processed] = True WHERE [Id_renewal] = ?"
        
        with get_cursor(commit=True) as cursor:
            cursor.execute(q_update_card, (new_exp, card_id))
            cursor.execute(q_update_ticket, (renewal_id,))
            
        from services.audit_service import log_action
        log_action(admin_id, "FINALIZO_RENOVACION_TARJETA", f"Cajero entregó y reactivó tarjeta ****{last4}. Nueva expiración: {new_exp.strftime('%m/%y')}")
        
        return True
    except Exception as e:
        raise Exception(f"Error procesando renovación final: {str(e)}")