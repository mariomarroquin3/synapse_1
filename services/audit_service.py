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