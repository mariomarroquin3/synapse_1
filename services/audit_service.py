from config.database import get_cursor
from datetime import datetime

def log_action(user_id, action, details):

    query = """
    INSERT INTO audit_log (user_id, action, details, created_at)
    VALUES (?, ?, ?, ?)
    """

    with get_cursor() as cursor:
        cursor.execute(
            query,
            user_id,
            action,
            details,
            datetime.now()
        )
        cursor.connection.commit()