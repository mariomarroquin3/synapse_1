import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from config.database import get_connection

def test_queries():
    conn = get_connection()
    cursor = conn.cursor()
    
    query1 = '''
        SELECT
            t.transaction_date,
            (SELECT TOP 1 amount FROM ledger_entry WHERE transaction_id = t.Id_transaction) as amount,
            t.description,
            u.email as created_by
        FROM [transaction] t
        LEFT JOIN [user] u ON t.created_by_user_id = u.Id_user
        ORDER BY t.transaction_date DESC
    '''
    
    try:
        cursor.execute(query1)
        r = cursor.fetchone()
        print("Query 1 (Auditor) OK")
    except Exception as e:
        print("Query 1 Failed:", e)

    query2 = '''
        SELECT tt.name, COUNT(t.Id_transaction) as total_tx, 
        SUM((SELECT TOP 1 amount FROM ledger_entry WHERE transaction_id = t.Id_transaction)) as volumen
        FROM [transaction] t
        INNER JOIN transaction_type tt ON t.transaction_type_id = tt.Id_transaction_type
        GROUP BY tt.name
    '''
    
    try:
        cursor.execute(query2)
        r = cursor.fetchone()
        print("Query 2 (Analyst) OK")
    except Exception as e:
        print("Query 2 Failed:", e)
        
    cursor.close()
    conn.close()

if __name__ == "__main__":
    test_queries()
