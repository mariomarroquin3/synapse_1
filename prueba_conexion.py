from config.database import get_connection

conn = get_connection()
print("Conexión exitosa")
conn.close()