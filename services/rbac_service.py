from config.database import get_connection
import re

def is_query_safe(query: str) -> bool:
    """
    Verifica que la consulta SQL no contenga instrucciones de modificación numéricas.
    Bloquea: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, EXEC
    """
    # Expresión regular para detectar comandos peligrosos (case-insensitive)
    peligrosos = r'\b(insert|update|delete|drop|alter|truncate|exec)\b'
    if re.search(peligrosos, query, re.IGNORECASE):
        return False
    return True

def execute_analyst_query(start_date=None, end_date=None) -> dict:
    """
    Role ID = 4 (Analista Financiero)
    Retorna métricas agregadas (flujo de caja, resúmenes por tipo).
    Validación de seguridad incluida. Filtra por fechas si se proporcionan.
    """
    from datetime import datetime, time as dtime

    # --- 1. PREPARACIÓN DE FECHAS ---
    use_dates = False
    if start_date and end_date:
        use_dates = True
        # Convertir date a datetime (inicio del día y fin del día)
        if hasattr(start_date, 'year') and not hasattr(start_date, 'hour'):
            dt_start = datetime.combine(start_date, dtime.min)
            dt_end   = datetime.combine(end_date,   dtime.max)
        else:
            dt_start = start_date
            dt_end   = end_date

    # --- 2. CONSTRUCCIÓN DE CONSULTAS (Con o sin filtro) ---
    if use_dates:
        # Hacemos JOIN con [transaction] para poder filtrar ledger_entry por fecha
        query_flujo = '''
            SELECT le.entry_type, SUM(le.amount) as monto_total
            FROM ledger_entry le
            INNER JOIN [transaction] t ON le.transaction_id = t.Id_transaction
            WHERE t.transaction_date BETWEEN ? AND ?
            GROUP BY le.entry_type
        '''
        
        query_tipos_base = '''
            SELECT tt.name, t.Id_transaction,
            (SELECT TOP 1 amount FROM ledger_entry WHERE transaction_id = t.Id_transaction) as amount
            FROM [transaction] t
            INNER JOIN transaction_type tt ON t.transaction_type_id = tt.Id_transaction_type
            WHERE t.transaction_date BETWEEN ? AND ?
        '''
    else:
        # Consultas originales (histórico completo)
        query_flujo = '''
            SELECT entry_type, SUM(amount) as monto_total
            FROM ledger_entry
            GROUP BY entry_type
        '''
        
        query_tipos_base = '''
            SELECT tt.name, t.Id_transaction,
            (SELECT TOP 1 amount FROM ledger_entry WHERE transaction_id = t.Id_transaction) as amount
            FROM [transaction] t
            INNER JOIN transaction_type tt ON t.transaction_type_id = tt.Id_transaction_type
        '''
        
    if not is_query_safe(query_flujo) or not is_query_safe(query_tipos_base):
        return {"error": "403 Acceso Denegado: Modificación no autorizada.", "status": 403, "data": None}
        
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # --- 3. EJECUCIÓN CON O SIN PARÁMETROS ---
        if use_dates:
            cursor.execute(query_flujo, (dt_start, dt_end))
            flujo_data = cursor.fetchall()
            
            cursor.execute(query_tipos_base, (dt_start, dt_end))
            tipos_raw = cursor.fetchall()
        else:
            cursor.execute(query_flujo)
            flujo_data = cursor.fetchall()
            
            cursor.execute(query_tipos_base)
            tipos_raw = cursor.fetchall()
            
        # --- 4. AGREGACIÓN EN PYTHON ---
        tipos_dict = {}
        for row in tipos_raw:
            name = row[0]
            amount = float(row[2]) if row[2] else 0.0
            if name not in tipos_dict:
                tipos_dict[name] = {"count": 1, "volumen": amount}
            else:
                tipos_dict[name]["count"] += 1
                tipos_dict[name]["volumen"] += amount
                
        tipos_list = [{"name": k, "count": v["count"], "volumen": v["volumen"]} for k, v in tipos_dict.items()]
        
        return {
            "status": 200,
            "data": {
                "flujo": [{"entry_type": row[0], "total": float(row[1]) if row[1] else 0.0} for row in flujo_data],
                "tipos": tipos_list
            }
        }
    except Exception as e:
        return {"error": str(e), "status": 500, "data": None}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


def get_daily_transaction_counts(start_date, end_date) -> dict:
    """
    Role ID = 4 (Analista Financiero)
    Retorna el conteo real de transacciones agrupadas por dia dentro del rango dado.
    Compatible con MS Access usando Format() para agrupar por fecha.
    Args:
        start_date: datetime.date o datetime.datetime inicio
        end_date:   datetime.date o datetime.datetime fin
    Returns:
        dict: {"status": 200, "data": [{"fecha": "YYYY-MM-DD", "cantidad": int}, ...]}
    """
    from datetime import datetime, time as dtime

    # Convertir date a datetime si es necesario
    if hasattr(start_date, 'year') and not hasattr(start_date, 'hour'):
        dt_start = datetime.combine(start_date, dtime.min)
        dt_end   = datetime.combine(end_date,   dtime.max)
    else:
        dt_start = start_date
        dt_end   = end_date

    # MS Access usa Format() para agrupar por fecha — no soporta DATE() ni CAST
    query = """
        SELECT Format(transaction_date, 'yyyy-mm-dd') AS fecha, COUNT(*) AS cantidad
        FROM [transaction]
        WHERE transaction_date BETWEEN ? AND ?
        GROUP BY Format(transaction_date, 'yyyy-mm-dd')
        ORDER BY Format(transaction_date, 'yyyy-mm-dd')
    """

    if not is_query_safe(query):
        return {"error": "403 Acceso Denegado.", "status": 403, "data": None}

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, (dt_start, dt_end))
        rows = cursor.fetchall()
        data = [{"fecha": row[0], "cantidad": int(row[1])} for row in rows if row[0]]
        return {"status": 200, "data": data}
    except Exception as e:
        return {"error": str(e), "status": 500, "data": None}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()



def execute_auditor_query() -> dict:
    """
    Role ID = 5 (Auditor)
    Retorna detalle histórico de transacciones (solo lectura).
    Validación de seguridad incluida.
    """
    # Consulta detallada sin agregaciones destructivas
    # Consulta detallada sin agregaciones destructivas. Limitado a TOP 50 por memoria.
    query = '''
        SELECT TOP 50
            t.transaction_date,
            (SELECT TOP 1 amount FROM ledger_entry WHERE transaction_id = t.Id_transaction) as amount,
            t.description,
            u.email as created_by
        FROM [transaction] t
        LEFT JOIN [user] u ON t.created_by_user_id = u.Id_user
        ORDER BY t.transaction_date DESC
    '''
    
    if not is_query_safe(query):
        return {"error": "403 Acceso Denegado: Modificación no autorizada.", "status": 403, "data": None}
        
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        
        data = []
        for row in rows:
            desc = row[2] or ""
            # Enmascarar números de tarjeta de 16 dígitos en la descripción
            # Busca exactamente 16 dígitos consecutivos
            desc = re.sub(
                r'\b(\d{12})(\d{4})\b', 
                r'**** **** **** \2', 
                desc
            )
            
            data.append({
                "transaction_date": row[0],
                "amount": float(row[1]) if row[1] else 0.0,
                "description": desc,
                "created_by": row[3] or "Sistema"
            })
            
        return {"status": 200, "data": data}
    except Exception as e:
        return {"error": str(e), "status": 500, "data": None}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def execute_custom_query(query: str, role_id: int) -> dict:
    """
    Función genérica para ejecutar consultas personalizadas con validación restrictiva.
    """
    if role_id in (4, 5):
        if not is_query_safe(query):
            return {"error": "403 Acceso Denegado: Modificación no autorizada para tu Rol.", "status": 403}
            
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        # Si es un SELECT, devolver datos. Si no, hacer commit para admin
        if query.strip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            return {"status": 200, "data": rows}
        else:
            if role_id not in (1, 3):
                raise Exception("Role no autorizado para modificaciones")
            conn.commit()
            return {"status": 200, "message": "Operación exitosa"}
    except Exception as e:
        if conn: conn.rollback()
        return {"error": str(e), "status": 500}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
