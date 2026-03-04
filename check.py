from config.database import get_cursor

with get_cursor() as cursor:
    for table in ["card", "account"]:
        print(f"\n--- Columnas en la tabla [{table}] ---")
        # Esto extrae los nombres reales de las columnas directamente de Access
        columns = [column[3] for column in cursor.columns(table=table)]
        print(columns)