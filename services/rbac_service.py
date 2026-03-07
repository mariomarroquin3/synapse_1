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

def execute_analyst_query() -> dict:
    """
    Role ID = 4 (Analista Financiero)
    Retorna métricas agregadas (flujo de caja, resúmenes por tipo).
    Validación de seguridad incluida.
    """
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
        
        cursor.execute(query_flujo)
        flujo_data = cursor.fetchall()
        
        cursor.execute(query_tipos_base)
        tipos_raw = cursor.fetchall()
        
        # Agregación en Python para evadir limitaciones de MS Access con subconsultas
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

def execute_auditor_query() -> dict:
    """
    Role ID = 5 (Auditor)
    Retorna detalle histórico de transacciones (solo lectura).
    Validación de seguridad incluida.
    """
    # Consulta detallada sin agregaciones destructivas
    query = '''
        SELECT
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
            data.append({
                "transaction_date": row[0],
                "amount": float(row[1]) if row[1] else 0.0,
                "description": row[2] or "",
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
