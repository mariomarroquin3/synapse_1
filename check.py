import pyodbc
import os
from datetime import datetime
from typing import Any, Dict
from dotenv import load_dotenv
# --- EL MÉTODO A TESTEAR ---
def validate_card_for_transaction(cursor: Any, card_number: str, input_pin: str) -> Dict[str, Any]:
    # (Pegamos aquí tu lógica exacta para ver cómo reacciona)
    if not input_pin or (isinstance(input_pin, str) and input_pin.strip() == ""):
        return {"success": False, "error": "PIN de tarjeta requerido", "account_id": None, "last4": None}
    
    if len(str(input_pin).strip()) != 4:
        return {"success": False, "error": "PIN debe tener 4 dígitos", "account_id": None, "last4": None}
    
    clean_card_number = str(card_number).replace(" ", "").replace("-", "")
    last4 = clean_card_number[-4:]
    
    try:
        # ⚠️ ESTA QUERY ES LA QUE SOSPECHAMOS QUE FALLARÁ POR LOS NOMBRES
        query = """
            SELECT [Id_card], [account_id], [pin], [is_active], [expiration_date]
            FROM [card]
            WHERE [card_number] = ?
        """
        cursor.execute(query, (clean_card_number,))
        row = cursor.fetchone()
        
        if not row:
            return {"success": False, "error": "Tarjeta no encontrada", "account_id": None, "last4": last4}
        
        card_id, account_id, stored_pin, is_active, expiration_date = row
        
        if not is_active:
            return {"success": False, "error": "La tarjeta está bloqueada", "account_id": None, "last4": last4}
        
        if expiration_date < datetime.now():
            return {"success": False, "error": "Tarjeta vencida", "account_id": None, "last4": last4}
        
        if str(stored_pin).strip() != str(input_pin).strip():
            return {"success": False, "error": "PIN de tarjeta incorrecto", "account_id": None, "last4": last4}
        
        return {"success": True, "account_id": account_id, "error": None, "last4": last4}
        
    except Exception as e:
        # Retornamos el error para verlo en el test
        return {"success": False, "error": f"EXCEPCIÓN SQL: {str(e)}", "account_id": None, "last4": last4}

# --- LÓGICA DEL TEST ---
# Cargar las variables del archivo .env
load_dotenv()

# Obtener la ruta desde el .env
# Asegúrate de que en el .env la ruta NO tenga comillas, ej: DB_PATH=C:\Ruta\Base.accdb
db_path = os.getenv("ACCESS_DB_PATH") 

if not db_path:
    raise ValueError("❌ No se encontró la variable DB_PATH en el archivo .env")

# CONSTRUCCIÓN DE LA CADENA
# El prefijo 'r' es vital si la ruta tiene backslashes (\)
conn_str = (
    r"Driver={Microsoft Access Driver (*.mdb, *.accdb)};"
    f"DBQ={db_path};"
)
try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print("--- 🧪 INICIANDO TEST DE VALIDACIÓN ---")
    
    # Intentamos validar con los datos que el test anterior nos mostró (ID: 1)
    # Número: '3482', PIN: 'tok_' (o lo que tengas en la DB)
    resultado = validate_card_for_transaction(cursor, "3482", "tok_")
    
    print(f"\nResultado del Test:")
    print(f"¿Éxito?: {resultado['success']}")
    print(f"Mensaje/Error: {resultado['error']}")
    
    if "No se pudo encontrar el campo" in str(resultado['error']) or "Pocos parámetros" in str(resultado['error']):
        print("\n💡 ANÁLISIS: El test falló como esperábamos. Access no encuentra 'card_number' ni 'pin'.")

    conn.close()

except Exception as e:
    print(f"Error de conexión: {e}")