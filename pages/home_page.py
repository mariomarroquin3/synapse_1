import streamlit as st
import time
from models.account_model import get_account_by_user, get_account_by_number
from services.transaction_service import get_account_balance, get_account_history_by_type, create_transfer

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Banca en Línea - Synapse", layout="wide")

# --- VERIFICACIÓN DE SESIÓN ---
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("No has iniciado sesión.")
    if st.button("Ir al Login"):
        st.switch_page("pages/login_page.py")
    st.stop()

# --- CARGA DE DATOS ---
user = st.session_state.user_data
account_row = get_account_by_user(user["Id_user"])

account = {
    "Id_account": None,
    "account_number": "Sin cuenta",
    "currency": "USD"
}

if account_row:
    try:
        # MAPEÓ UNIVERSAL (Soporta Tuplas de DB y Diccionarios)
        if isinstance(account_row, (list, tuple)):
            account["Id_account"]     = account_row[0]
            account["account_number"] = account_row[2]
            account["currency"]       = account_row[3]
        elif isinstance(account_row, dict):
            account["Id_account"]     = account_row.get("Id_account")
            account["account_number"] = account_row.get("account_number", "Sin cuenta")
            account["currency"]       = account_row.get("currency", "USD")
    except Exception as e:
        st.error(f"Error procesando datos de cuenta: {e}")
else:
    st.warning("⚠️ No se encontró una cuenta activa para este usuario.")

# --- FUNCIONES ---
def logout():
    st.session_state.logged_in = False
    st.session_state.user_data = None
    st.switch_page("pages/login_page.py")

# --- VISTA DE BANCA EN LÍNEA ---
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.markdown(f"## Bienvenido, {user['full_name']}")
    st.caption(f"DUI: {user['DUI']} | Cuenta: {account['account_number']}")
with head_col2:
    if st.button("Cerrar Sesión"):
        logout()

st.divider()

# Menú de Navegación
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["Resumen", "Transferencias", "Historial Transferencias", "Retiros", "Depósitos", "Mi Perfil"])

# --- BOTÓN DE CAJERO ---
st.sidebar.divider()
if st.sidebar.button("🏧 CAJERO", use_container_width=True):
    st.switch_page("pages/atm_simulator.py")

if menu == "Resumen":
    balance = get_account_balance(account["Id_account"]) if account["Id_account"] else 0.0
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Saldo Disponible", f"$ {balance:,.2f} {account['currency']}")
    with col2:
        st.metric("Puntos Synapse", "500 pts")

elif menu == "Transferencias":
    st.subheader("Transferencias a Terceros")
    if not account["Id_account"]:
        st.warning("No tienes una cuenta bancaria asociada para hacer transferencias.")
    else:
        balance = get_account_balance(account["Id_account"])
        st.write(f"**Saldo disponible:** $ {balance:,.2f} {account['currency']}")
        
        with st.form("transfer_form"):
            dest_account_num = st.text_input("Número de Cuenta Destino", placeholder="Ej. SV_synapse1234567")
            amount_to_transfer = st.number_input("Monto a transferir", min_value=0.01, step=10.0, format="%.2f")
            description = st.text_input("Concepto / Descripción", placeholder="Pago de servicios, almuerzo, etc.")
            
            submit_transfer = st.form_submit_button("Realizar Transferencia", type="primary", use_container_width=True)
            
            if submit_transfer:
                if not dest_account_num or amount_to_transfer <= 0 or not description:
                    st.warning("Por favor, completa todos los campos correctamente.")
                elif dest_account_num == account["account_number"]:
                    st.error("No puedes transferir dinero a tu propia cuenta.")
                elif amount_to_transfer > balance:
                    st.error("Fondos insuficientes para realizar esta transferencia.")
                else:
                    dest_account = get_account_by_number(dest_account_num)
                    if not dest_account:
                        st.error("La cuenta destino no existe o es inválida.")
                    else:
                        with st.spinner("Procesando transferencia..."):
                            time.sleep(1.0)
                            
                            # OBTENER ID DESTINO DE FORMA SEGURA
                            dest_account_id = None
                            if isinstance(dest_account, (list, tuple)):
                                dest_account_id = dest_account[0]
                            elif isinstance(dest_account, dict):
                                dest_account_id = dest_account.get("Id_account")

                            if dest_account_id:
                                result = create_transfer(
                                    from_account_id=account["Id_account"],
                                    to_account_id=dest_account_id,
                                    amount=amount_to_transfer,
                                    description=description,
                                    created_by_user_id=user["Id_user"],
                                    transaction_type_id=1 
                                )
                                
                                if result.get("success"):
                                    st.success(f"¡Transferencia de ${amount_to_transfer:,.2f} realizada exitosamente!")
                                    st.balloons()
                                    time.sleep(1)
                                    st.rerun() # Refrescar para ver nuevo balance
                                else:
                                    st.error(f"Error al procesar la transferencia: {result.get('error')}")
                            else:
                                st.error("No se pudo identificar el ID de la cuenta destino.")

elif menu == "Historial Transferencias":
    st.subheader("Historial de Transferencias")
    if not account["Id_account"]:
        st.warning("No tienes una cuenta bancaria asociada para ver el historial.")
    else:
        tx_history = get_account_history_by_type(account["Id_account"], 1) # 1 = Transferencia
        if tx_history:
            for tx in tx_history:
                with st.container(border=True):
                    st.markdown(f"**Fecha:** {tx['date'].strftime('%Y-%m-%d %H:%M:%S')}")
                    st.markdown(f"**Descripción:** {tx['description']}")
                    
                    if tx['entry_type'] == 'debit':
                        st.markdown(f"**Monto:** <span style='color:red;'>-$ {tx['amount']:,.2f}</span> (Enviado)", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**Monto:** <span style='color:green;'>+$ {tx['amount']:,.2f}</span> (Recibido)", unsafe_allow_html=True)
        else:
            st.info("No tienes transferencias registradas todavía.")

elif menu == "Retiros":
    st.subheader("Historial de Retiros")
    if account["Id_account"]:
        history = get_account_history_by_type(account["Id_account"], 2) # 2 = retiro
        if history:
            for tx in history:
                with st.container(border=True):
                    st.markdown(f"**Fecha:** {tx['date'].strftime('%Y-%m-%d %H:%M:%S')}")
                    st.markdown(f"**Descripción:** {tx['description']}")
                    st.markdown(f"**Monto:** <span style='color:red;'>-$ {tx['amount']:,.2f}</span>", unsafe_allow_html=True)
        else:
            st.info("No tienes retiros registrados todavía.")
    else:
        st.warning("No tienes una cuenta bancaria asociada.")

elif menu == "Depósitos":
    st.subheader("Historial de Depósitos")
    if account["Id_account"]:
        history = get_account_history_by_type(account["Id_account"], 3) # 3 = depósito
        if history:
            for tx in history:
                with st.container(border=True):
                    st.markdown(f"**Fecha:** {tx['date'].strftime('%Y-%m-%d %H:%M:%S')}")
                    st.markdown(f"**Descripción:** {tx['description']}")
                    st.markdown(f"**Monto:** <span style='color:green;'>+$ {tx['amount']:,.2f}</span>", unsafe_allow_html=True)
        else:
            st.info("No tienes depósitos registrados todavía.")
    else:
        st.warning("No tienes una cuenta bancaria asociada.")

elif menu == "Mi Perfil":
    st.subheader("Información Personal")
    st.write(f"**Nombre:** {user['full_name']}")
    st.write(f"**Email:** {user['email']}")
    st.write(f"**Teléfono:** {user['phone_number']}")
    st.write(f"**DUI:** {user['DUI']}")