"""
test_historical_dates.py
Script de prueba para verificar que la inyección de fechas históricas funciona correctamente.
"""

from datetime import datetime, timedelta
from services.transaction_service import create_transfer, create_simple_transaction, ENTRY_DEBIT, ENTRY_CREDIT
from config.database import get_connection

# ─────────────────────────────────────────────
# TEST 1: Transferencia con fecha histórica
# ─────────────────────────────────────────────
def test_transfer_with_historical_date():
    print("\n" + "="*80)
    print("TEST 1: Transferencia con fecha histórica")
    print("="*80)
    
    # Crear una fecha de hace 7 días
    historical_date = datetime.now() - timedelta(days=7)
    
    result = create_transfer(
        from_account_id=1,
        to_account_id=2,
        amount=500.0,
        description="Transferencia histórica de prueba",
        created_by_user_id=1,
        transaction_type_id=1,
        created_at=historical_date
    )
    
    print(f"\nResultado: {result}")
    if result["success"]:
        print(f"✅ Transferencia creada con éxito: TX ID {result['transaction_id']}")
        print(f"   Fecha histórica inyectada: {historical_date}")
        return result["transaction_id"]
    else:
        print(f"❌ Error: {result['error']}")
        return None

# ─────────────────────────────────────────────
# TEST 2: Transacción simple con fecha histórica
# ─────────────────────────────────────────────
def test_simple_transaction_with_historical_date():
    print("\n" + "="*80)
    print("TEST 2: Transacción simple (depósito) con fecha histórica")
    print("="*80)
    
    # Crear una fecha de hace 14 días
    historical_date = datetime.now() - timedelta(days=14)
    
    result = create_simple_transaction(
        account_id=1,
        amount=1000.0,
        entry_type=ENTRY_CREDIT,
        description="Depósito histórico de prueba",
        created_by_user_id=1,
        transaction_type_id=2,
        created_at=historical_date
    )
    
    print(f"\nResultado: {result}")
    if result["success"]:
        print(f"✅ Transacción creada con éxito: TX ID {result['transaction_id']}")
        print(f"   Fecha histórica inyectada: {historical_date}")
        return result["transaction_id"]
    else:
        print(f"❌ Error: {result['error']}")
        return None

# ─────────────────────────────────────────────
# TEST 3: Verificar que las fechas se guardaron correctamente
# ─────────────────────────────────────────────
def verify_historical_dates(tx_id_1, tx_id_2):
    print("\n" + "="*80)
    print("TEST 3: Verificar que las fechas se guardaron correctamente")
    print("="*80)
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if tx_id_1:
            cursor.execute("SELECT transaction_date FROM [transaction] WHERE Id_transaction = ?", (tx_id_1,))
            row = cursor.fetchone()
            if row:
                print(f"\n✅ Transferencia (TX {tx_id_1}): transaction_date = {row[0]}")
        
        if tx_id_2:
            cursor.execute("SELECT transaction_date FROM [transaction] WHERE Id_transaction = ?", (tx_id_2,))
            row = cursor.fetchone()
            if row:
                print(f"✅ Depósito (TX {tx_id_2}): transaction_date = {row[0]}")
    
    except Exception as e:
        print(f"❌ Error verificando fechas: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ─────────────────────────────────────────────
# TEST 4: Transacción sin fecha (debe usar ahora)
# ─────────────────────────────────────────────
def test_transaction_without_date():
    print("\n" + "="*80)
    print("TEST 4: Transacción SIN fecha histórica (debe usar ahora)")
    print("="*80)
    
    result = create_transfer(
        from_account_id=1,
        to_account_id=2,
        amount=300.0,
        description="Transferencia sin fecha especificada",
        created_by_user_id=1,
        transaction_type_id=1
        # NOTA: No se pasa created_at
    )
    
    print(f"\nResultado: {result}")
    if result["success"]:
        print(f"✅ Transferencia creada con éxito: TX ID {result['transaction_id']}")
        print(f"   Fecha (automática): {datetime.now()}")
        return result["transaction_id"]
    else:
        print(f"❌ Error: {result['error']}")
        return None

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTS DE INYECCIÓN DE FECHAS HISTÓRICAS")
    print("="*80)
    
    try:
        tx_id_1 = test_transfer_with_historical_date()
        tx_id_2 = test_simple_transaction_with_historical_date()
        tx_id_3 = test_transaction_without_date()
        
        verify_historical_dates(tx_id_1, tx_id_2)
        
        print("\n" + "="*80)
        print("✅ TESTS COMPLETADOS")
        print("="*80)
    except Exception as e:
        print(f"\n❌ Error durante los tests: {e}")
        import traceback
        traceback.print_exc()
