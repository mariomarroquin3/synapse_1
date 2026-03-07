"""
test_card_validation.py
Ejemplos prácticos de uso del sistema de validación de tarjetas.
"""

from datetime import datetime, timedelta
from config.database import get_connection
from services.card_service import validate_card_for_transaction, update_card_active_status
from services.transaction_service import create_simple_transaction, ENTRY_DEBIT, ENTRY_CREDIT


def demo_card_validation():
    """
    Demostración de validación de tarjetas usando cursor compartido.
    
    NOTA: Este es un ejemplo educacional que muestra cómo funciona
    el sistema. Para ejecutar contra una base de datos real:
    1. Inserta datos de prueba en las tablas [card] y [account]
    2. Ajusta los valores de card_number y account_id
    """
    
    print("\n" + "="*70)
    print("TEST PRUEBA DE VALIDACION DE TARJETAS - SYNAPSE BANKING SYSTEM")
    print("="*70)
    
    # ──────────────────────────────────────────────────────────────
    # Test 1: Validación de Tarjeta Válida
    # ──────────────────────────────────────────────────────────────
    print("\n[TEST 1] Validación de Tarjeta Activa y No Expirada")
    print("-" * 70)
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Buscar una tarjeta válida en la base de datos
        cursor.execute("""
            SELECT TOP 1 [card_number], [card_number_last4], [is_active], [expiration_date]
            FROM [card]
            WHERE [is_active] = True
            AND [expiration_date] > ?
        """, (datetime.now(),))
        
        row = cursor.fetchone()
        
        if row:
            card_num, card_tok, is_active, exp_date = row
            print(f"OK Tarjeta encontrada: {card_num[-4:]}****")
            print(f"  - Activa: {is_active}")
            print(f"  - Vence el: {exp_date}")
            
            # Validar usando el cursor compartido
            result = validate_card_for_transaction(cursor, card_num, card_tok)
            print(f"  - Validacion: {'OK EXITOSA' if result['success'] else 'FAIL FALLIDA'}")
            if result['success']:
                print(f"  - Cuenta asociada: {result['account_id']}")
            else:
                print(f"  - Error: {result['error']}")
        else:
            print("⚠️ No se encontraron tarjetas válidas en la BD para prueba")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    
    # ──────────────────────────────────────────────────────────────
    # Test 2: Validación de Tarjeta Bloqueada
    # ──────────────────────────────────────────────────────────────
    print("\n[TEST 2] Validación de Tarjeta Bloqueada (is_active=False)")
    print("-" * 70)
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Buscar una tarjeta bloqueada
        cursor.execute("""
            SELECT TOP 1 [card_number], [card_number_last4], [is_active]
            FROM [card]
            WHERE [is_active] = False
        """)
        
        row = cursor.fetchone()
        
        if row:
            card_num, card_tok, is_active = row
            print(f"OK Tarjeta bloqueada encontrada: {card_num[-4:]}****")
            print(f"  - Estado: {'Inactiva FAIL' if not is_active else 'Activa OK'}")
            
            # Intentar validar (debería fallar)
            result = validate_card_for_transaction(cursor, card_num, card_tok)
            print(f"  - Validación: {'✅ EXITOSA' if result['success'] else '❌ FALLIDA (ESPERADO)'}")
            if not result['success']:
                print(f"  - Error esperado: {result['error']}")
        else:
            print("WARN No se encontraron tarjetas bloqueadas en la BD para prueba")
            
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    
    # ──────────────────────────────────────────────────────────────
    # Test 3: Validación de Tarjeta Vencida
    # ──────────────────────────────────────────────────────────────
    print("\n[TEST 3] Validación de Tarjeta Expirada")
    print("-" * 70)
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Buscar una tarjeta vencida
        cursor.execute("""
            SELECT TOP 1 [card_number], [card_number_last4], [is_active], [expiration_date]
            FROM [card]
            WHERE [expiration_date] < ?
        """, (datetime.now(),))
        
        row = cursor.fetchone()
        
        if row:
            card_num, card_tok, is_active, exp_date = row
            print(f"OK Tarjeta expirada encontrada: {card_num[-4:]}****")
            print(f"  - Fecha de vencimiento: {exp_date}")
            print(f"  - Fecha actual: {datetime.now()}")
            
            # Intentar validar (debería fallar)
            result = validate_card_for_transaction(cursor, card_num, card_tok)
            print(f"  - Validación: {'✅ EXITOSA' if result['success'] else '❌ FALLIDA (ESPERADO)'}")
            if not result['success']:
                print(f"  - Error esperado: {result['error']}")
        else:
            print("WARN No se encontraron tarjetas vencidas en la BD para prueba")
            
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    
    # ──────────────────────────────────────────────────────────────
    # Test 4: Token Inválido
    # ──────────────────────────────────────────────────────────────
    print("\n[TEST 4] Validación con Token Incorrecto")
    print("-" * 70)
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Buscar una tarjeta válida
        cursor.execute("""
            SELECT TOP 1 [card_number], [card_number_last4], [is_active], [expiration_date]
            FROM [card]
            WHERE [is_active] = True
            AND [expiration_date] > ?
        """, (datetime.now(),))
        
        row = cursor.fetchone()
        
        if row:
            card_num, card_tok, is_active, exp_date = row
            print(f"OK Tarjeta valida encontrada: {card_num[-4:]}****")
            
            # Intentar validar con token INCORRECTO
            invalid_token = "tok_invalid_token_xyz"
            print(f"  - Token correcto: {card_tok[:10]}...")
            print(f"  - Token proporcionado: {invalid_token}")
            
            result = validate_card_for_transaction(cursor, card_num, invalid_token)
            print(f"  - Validacion: {'OK EXITOSA' if result['success'] else 'OK FALLIDA (ESPERADO)'}")
            if not result['success']:
                print(f"  - Error esperado: {result['error']}")
        else:
            print("WARN No se encontraron tarjetas validas en la BD para prueba")
            
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    
    # ──────────────────────────────────────────────────────────────
    # Test 5: Actualizar Estado de Tarjeta (Bloquear/Desbloquear)
    # ──────────────────────────────────────────────────────────────
    print("\n[TEST 5] Actualizar Estado de Tarjeta (Bloquear Temporalmente)")
    print("-" * 70)
    
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Obtener ID de una tarjeta activa
        cursor.execute("""
            SELECT TOP 1 [Id_card], [card_number], [is_active]
            FROM [card]
            WHERE [is_active] = True
        """)
        
        row = cursor.fetchone()
        
        if row:
            card_id, card_num, curr_status = row
            print(f"OK Tarjeta seleccionada: {card_num[-4:]}**** (ID: {card_id})")
            print(f"  - Estado actual: {'Activa OK' if curr_status else 'Bloqueada FAIL'}")
            
            try:
                # BLOQUEAR la tarjeta
                print(f"\n  -> Ejecutando: update_card_active_status(cursor, {card_id}, False)")
                update_card_active_status(cursor, card_id, False)
                conn.commit()
                print(f"  OK Tarjeta bloqueada exitosamente")
                
                # DESBLOQUEAR la tarjeta
                print(f"\n  -> Ejecutando: update_card_active_status(cursor, {card_id}, True)")
                cursor = conn.cursor()  # New cursor after commit
                update_card_active_status(cursor, card_id, True)
                conn.commit()
                print(f"  OK Tarjeta desbloqueada exitosamente")
                
            except Exception as e:
                conn.rollback()
                print(f"  ERROR durante la actualizacion: {e}")
        else:
            print("WARN No se encontraron tarjetas activas para la prueba")
            
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    
    # ──────────────────────────────────────────────────────────────
    # Test 6: Transacción con Validación de Tarjeta
    # ──────────────────────────────────────────────────────────────
    print("\n[TEST 6] Crear Transacción CON Validación de Tarjeta")
    print("-" * 70)
    
    try:
        # Obtener datos de una tarjeta válida
        conn = None
        cursor = None
        card_num = None
        card_tok = None
        account_id = None
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT TOP 1 [card_number], [card_number_last4], [account_id]
                FROM [card]
                WHERE [is_active] = True
                AND [expiration_date] > ?
            """, (datetime.now(),))
            
            row = cursor.fetchone()
            if row:
                card_num, card_tok, account_id = row
                print(f"OK Datos de prueba obtenidos:")
                print(f"  - Tarjeta: {card_num[-4:]}****")
                print(f"  - Cuenta: {account_id}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
        
        if card_num and account_id:
            # Intentar realizar transacción CON validación de tarjeta
            print(f"\n-> Ejecutando: create_simple_transaction() CON card_number y pin")
            result = create_simple_transaction(
                account_id=account_id,
                amount=10.00,
                entry_type=ENTRY_DEBIT,
                description="Pago con validacion de tarjeta - TEST",
                created_by_user_id=1,
                transaction_type_id=4,  # Bill Payment
                card_number=card_num,
                pin=card_tok
            )
            
            if result['success']:
                print(f"\nOK TRANSACCION EXITOSA")
                print(f"  - ID Transacción: {result['transaction_id']}")
                print(f"  - ID Ledger: {result['ledger_entry_id']}")
            else:
                print(f"\nERROR TRANSACCION FALLIDA")
                print(f"  - Error: {result['error']}")
        else:
            print("WARN No se pudieron obtener datos de prueba de la BD")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    # ──────────────────────────────────────────────────────────────
    # Test 7: Transacción SIN Validación de Tarjeta (Backward Compatibility)
    # ──────────────────────────────────────────────────────────────
    print("\n[TEST 7] Crear Transacción SIN Validación (Compatibilidad Anterior)")
    print("-" * 70)
    
    try:
        # Obtener una cuenta válida
        conn = None
        cursor = None
        account_id = None
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT TOP 1 [Id_account] FROM [account] WHERE [status_id] = 1")
            row = cursor.fetchone()
            if row:
                account_id = row[0]
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
        
        if account_id:
            # Intentar transacción SIN tarjeta (comportamiento original)
            print(f"OK Cuenta seleccionada: {account_id}")
            print(f"\n-> Ejecutando: create_simple_transaction() sin card_number")
            result = create_simple_transaction(
                account_id=account_id,
                amount=5.00,
                entry_type=ENTRY_CREDIT,  # Depósito
                description="Depósito sin tarjeta - TEST",
                created_by_user_id=1,
                transaction_type_id=3  # Deposit
                # NO se proporciona card_number ni pin
            )
            
            if result['success']:
                print(f"\nOK TRANSACCION EXITOSA (Sin validacion de tarjeta)")
                print(f"  - ID Transacción: {result['transaction_id']}")
                print(f"  - ID Ledger: {result['ledger_entry_id']}")
            else:
                print(f"\nERROR TRANSACCION FALLIDA")
                print(f"  - Error: {result['error']}")
        else:
            print("WARN No se encontraron cuentas activas para la prueba")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    print("\n" + "="*70)
    print("OK PRUEBAS COMPLETADAS")
    print("="*70 + "\n")


if __name__ == "__main__":
    demo_card_validation()
