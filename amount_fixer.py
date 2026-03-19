# Suponiendo que tus funciones de transacción están en un archivo llamado transaction_service.py
from services.transaction_service import get_all_account_history, create_simple_transaction

# Suponiendo que tu conexión está en un archivo llamado db_connection.py o similar
from config.database import get_connection
# CREDIT = 'CREDIT'  # o como lo tengas definido
# DEBIT = 'DEBIT'

def arreglar_saldos_negativos_con_servicios():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Obtener todas las cuentas existentes (único paso que requiere SQL directo aquí)
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
        user_id = cuenta[1] # Usaremos el dueño de la cuenta como creador, o puedes poner el ID de un Admin (ej: 1)

        # 2. Reutilizamos tu función para traer el historial
        historial = get_all_account_history(account_id)
        
        if not historial:
            continue

        # OJO: Tu función get_all_account_history ordena "DESC" (del más nuevo al más viejo).
        # Para calcular cómo evolucionó el saldo en el tiempo, debemos invertir la lista (ASC).
        historial.reverse()

        saldo_actual = 0
        peor_saldo = 0
        fecha_primera_transaccion = historial[0]['date']

        # 3. Calcular el punto más bajo del saldo
        for mov in historial:
            # Tu sistema usa entry_type para saber si suma o resta
            if mov['entry_type'] == 'CREDIT':  
                saldo_actual += mov['amount']
            else: # Asumiendo que es DEBIT
                saldo_actual -= mov['amount']
                
            if saldo_actual < peor_saldo:
                peor_saldo = saldo_actual

        # 4. Si hubo saldo negativo, usamos tu servicio para arreglarlo
        if peor_saldo < 0:
            monto_a_depositar = abs(peor_saldo)
            
            print(f"Cuenta {account_id} detectada con déficit de ${monto_a_depositar}. Intentando ajuste...")
            
            # Usamos TU función, respetando TODA tu lógica de negocio
            resultado = create_simple_transaction(
                account_id=account_id,
                amount=monto_a_depositar,
                entry_type='credit', # Asumiendo que 'CREDIT' es tu constante de entrada
                description="Ajuste de saldo inicial automático",
                created_by_user_id=user_id, # O el ID del administrador
                transaction_type_id=3, # Depósito
                created_at=fecha_primera_transaccion # Le pasamos la fecha antigua
            )
            
            if resultado['success']:
                print(f" -> Éxito. Transacción ID: {resultado['transaction_id']}")
                ajustes_realizados += 1
            else:
                print(f" -> Error al ajustar: {resultado.get('error')}")

    print(f"\nProceso finalizado. {ajustes_realizados} cuentas ajustadas.")

arreglar_saldos_negativos_con_servicios()