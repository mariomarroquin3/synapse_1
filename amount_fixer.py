# Suponiendo que tus funciones de transacción están en un archivo llamado transaction_service.py
from services.transaction_service import get_all_account_history, create_simple_transaction

# Suponiendo que tu conexión está en un archivo llamado db_connection.py o similar
from config.database import get_connection

# ─────────────────────────────────────────────
# CONSTANTES ACTUALIZADAS (Alineadas con entry_types)
# ─────────────────────────────────────────────
CREDIT = 1
DEBIT = 2

def arreglar_saldos_negativos_con_servicios():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Obtener todas las cuentas existentes
        cursor.execute("SELECT Id_account, user_id FROM [account]")
        cuentas = cursor.fetchall()
        
    except Exception as e:
        print(f"Error obteniendo cuentas: {e}")
        return
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    ajustes_realizados = 0

    for cuenta in cuentas:
        account_id = cuenta[0]
        user_id = cuenta[1] # Usaremos el dueño de la cuenta como creador

        # 2. Traer el historial
        historial = get_all_account_history(account_id)
        
        if not historial:
            continue

        # Invertir la lista para calcular la evolución cronológica (de más antiguo a más nuevo)
        historial.reverse()

        saldo_actual = 0
        peor_saldo = 0
        fecha_primera_transaccion = historial[0]['date']

        # 3. Calcular el punto más bajo del saldo
        for mov in historial:
            # ACTUALIZACIÓN: Ahora comparamos contra la constante numérica (1)
            if mov['entry_type'] == CREDIT:  
                saldo_actual += mov['amount']
            else: # Asumiendo que es DEBIT (2)
                saldo_actual -= mov['amount']
                
            if saldo_actual < peor_saldo:
                peor_saldo = saldo_actual

        # 4. Si hubo saldo negativo, usamos tu servicio para arreglarlo
        if peor_saldo < 0:
            monto_a_depositar = abs(peor_saldo)
            
            print(f"Cuenta {account_id} detectada con déficit de ${monto_a_depositar}. Intentando ajuste...")
            
            # Usamos TU función, pasando el entero correspondiente al crédito
            resultado = create_simple_transaction(
                account_id=account_id,
                amount=monto_a_depositar,
                entry_type=CREDIT, # ACTUALIZACIÓN: Pasamos el entero 1
                description="Ajuste de saldo inicial automático",
                created_by_user_id=user_id, 
                transaction_type_id=3, # Depósito
                created_at=fecha_primera_transaccion # Fecha retroactiva
            )
            
            if resultado['success']:
                print(f" -> Éxito. Transacción ID: {resultado['transaction_id']}")
                ajustes_realizados += 1
            else:
                print(f" -> Error al ajustar: {resultado.get('error')}")

    print(f"\nProceso finalizado. {ajustes_realizados} cuentas ajustadas.")

if __name__ == "__main__":
    arreglar_saldos_negativos_con_servicios()