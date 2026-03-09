from config.database import get_cursor
try:
    with get_cursor(commit=True) as cursor:
        cursor.execute("CREATE TABLE card_renewals (Id_renewal AUTOINCREMENT PRIMARY KEY, card_id INT, requested_at DATETIME, processed BIT)")
    print("Table created.")
except Exception as e:
    print(f"Error: {e}")
