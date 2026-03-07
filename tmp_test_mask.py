import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from config.database import get_connection

def test_regex():
    from services.rbac_service import execute_auditor_query
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Insert dummy data with a 16-digit number to check masking
    print("Pre-test inserting a manual card payment record...")
    try:
        cursor.execute("INSERT INTO [transaction] (transaction_type_id, status_id, description, created_by_user_id, transaction_date, processed_at) VALUES (4, 1, 'Fake Payment - Tarjeta: 1234567890123456', 2, Now(), Now())")
        conn.commit()
    except Exception as e:
        print("Failed manual insert", e)
    
    # 2. Check the output
    print("Checking Auditor view...")
    response = execute_auditor_query()
    if response['status'] == 200:
        data = response['data']
        # Print top 5 newest lines
        for d in data[:5]:
            print(d['description'])
    else:
        print("Error in query:", response)
    
    print("\nPre-test Cleanup...")
    try:
        cursor.execute("DELETE FROM [transaction] WHERE description LIKE 'Fake Payment - Tarjeta%'")
        conn.commit()
    except Exception as e:
        pass
        
    cursor.close()
    conn.close()

if __name__ == "__main__":
    test_regex()
