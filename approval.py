# Importa tus funciones desde donde las tengas (ajusta las rutas)
# from tu_modulo import get_pending_approvals, review_transaction, log_action
from services.transaction_service import review_transaction
from services.audit_service import log_action
from services.transaction_service import review_transaction

import streamlit as st

# 1. Mantenemos el truco por si audit_service lo llega a necesitar internamente
if 'user_data' not in st.session_state:
    st.session_state['user_data'] = {
        'Id_user': 31,
        'full_name': 'Administrador Principal',
        'role': '3'
    }


from config.database import get_connection # Asegúrate de que esta ruta sea la correcta a tu base de datos

# 3. Metemos la función de consulta AQUÍ MISMO para no tocar el dashboard
def get_pending_approvals_local():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT 
                t.Id_transaction, t.description, t.transaction_date, 
                a.amount, a.from_account_id, a.to_account_id,
                tt.name AS type_name, u.full_name AS requester
            FROM (([transaction] t
            INNER JOIN transaction_approvals a ON t.Id_transaction = a.transaction_id)
            INNER JOIN transaction_type tt ON t.transaction_type_id = tt.Id_transaction_type)
            INNER JOIN [user] u ON t.created_by_user_id = u.Id_user
            WHERE t.status_id = 2
        """
        cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

# 4. Ejecutamos la lógica pura
def aprobacion_masiva_ajustes(admin_id: int):
    # Usamos nuestra versión local de la función
    pendientes = get_pending_approvals_local()

    if not pendientes:
        print("No hay transacciones pendientes para aprobar.")
        return

    print(f"Se encontraron {len(pendientes)} transacciones en cola. Iniciando saneamiento...")
    aprobadas = 0

    for p in pendientes:
        tx_id, desc, date, amount, from_acc, to_acc, type_name, req = p
        
        if "Ajuste" in desc:
            nota_admin = "Aprobación automática: Saneamiento de saldo histórico."
            print(f"Procesando TX {tx_id} (Cuenta: {req}) - Monto: ${amount:,.2f}...")
            
            # Llamamos a tu servicio
            res = review_transaction(tx_id, admin_id, True, nota_admin)
            
            if res["success"]:
                log_action(
                    user_id=admin_id,
                    action="2",
                    details=f"Aprobó TX {tx_id} de {req} (${amount:,.2f}) - Ajuste Inicial"
                )
                print(" -> ✅ Aprobada con éxito.")
                aprobadas += 1
            else:
                print(f" -> ❌ Error al aprobar TX {tx_id}: {res['error']}")
        else:
            print(f"Saltando TX {tx_id} (No es un ajuste automático)")

    print(f"\n[PROCESO COMPLETADO] Se aprobaron {aprobadas} ajustes de saldo.")

# 5. Ejecutar
aprobacion_masiva_ajustes(admin_id=31)