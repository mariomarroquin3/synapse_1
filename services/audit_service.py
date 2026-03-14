from config.database import get_cursor
from datetime import datetime

def log_action(user_id, action, details):
    """
    Registra una acción en la tabla audit_log.
    Se asegura de que el user_id sea válido para evitar IntegrityError.
    """
    # Validamos que el user_id no sea None o 0 antes de intentar el INSERT
    if not user_id:
        print("Error: user_id es nulo o vacío. No se puede registrar la acción.")
        return False

    query = """
    INSERT INTO audit_log (user_id, action, details, created_at)
    VALUES (?, ?, ?, ?)
    """

    try:
        with get_cursor() as cursor:
            # IMPORTANTE: Pasar los parámetros como una TUPLA (con paréntesis)
            # Esto asegura que pyodbc mapee correctamente los tipos de datos en Access
            cursor.execute(
                query,
                (int(user_id), str(action), str(details), datetime.now())
            )
            # Confirmamos la transacción
            cursor.connection.commit()
            return True
    except Exception as e:
        print(f"Error crítico en log_action: {e}")
        return False
    
from config.database import get_cursor
from datetime import datetime

def log_action(user_id, action, details):
    """
    Registra una acción en la tabla audit_log.
    Se asegura de que el user_id sea válido para evitar IntegrityError.
    """
    # Validamos que el user_id no sea None o 0 antes de intentar el INSERT
    if not user_id:
        print("Error: user_id es nulo o vacío. No se puede registrar la acción.")
        return False

    query = """
    INSERT INTO audit_log (user_id, action, details, created_at)
    VALUES (?, ?, ?, ?)
    """

    try:
        with get_cursor() as cursor:
            # IMPORTANTE: Pasar los parámetros como una TUPLA (con paréntesis)
            # Esto asegura que pyodbc mapee correctamente los tipos de datos en Access
            cursor.execute(
                query,
                (int(user_id), str(action), str(details), datetime.now())
            )
            # Confirmamos la transacción
            cursor.connection.commit()
            return True
    except Exception as e:
        print(f"Error crítico en log_action: {e}")
        return False


def get_filtered_auditor_admin_logs(filtro=None):
    """
    Obtiene el historial administrativo incluyendo el DUI del administrador.
    """
    query = """
        SELECT 
            al.Id_log, 
            u.full_name, 
            u.dui, 
            al.[action], 
            al.details, 
            al.created_at
        FROM audit_log al
        INNER JOIN [user] u ON al.user_id = u.Id_user
        ORDER BY al.created_at DESC
    """
    try:
        with get_cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()
    except Exception as e:
        print(f"Error al obtener historial administrativo: {e}")
        return []


def get_filtered_auditor_transactions(filtro=None):
    """
    Obtiene el historial de transacciones incluyendo DUI y Número de Cuenta.
    """
    query = """
        SELECT 
            t.Id_transaction, 
            t.transaction_type_id as type_id, 
            t.status_id, 
            t.description, 
            u.Id_user, 
            u.full_name, 
            u.dui, 
            a.account_number, 
            t.transaction_date as created_at, 
            t.processed_at
        FROM ([transaction] t
        INNER JOIN [user] u ON t.created_by_user_id = u.Id_user)
        LEFT JOIN account a ON u.Id_user = a.user_id
        ORDER BY t.transaction_date DESC
    """
    try:
        with get_cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()
    except Exception as e:
        print(f"🔴 ERROR SQL en transacciones: {e}")
        return []