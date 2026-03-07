from config.database import get_cursor

def check_schema():
    try:
        with get_cursor() as cursor:
            cursor.execute("SELECT TOP 1 * FROM [card]")
            columns = [col[0] for col in cursor.description]
            print(f"Columns in [card] table: {columns}")
    except Exception as e:
        print(f"Error checking schema: {e}")

if __name__ == "__main__":
    check_schema()
