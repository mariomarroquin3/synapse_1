import streamlit as st
import time
from models.account_model import get_account_by_user
from services.transaction_service import create_simple_transaction, ENTRY_CREDIT

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="ATM Simulator - Synapse", page_icon="🏧", layout="centered")

# --- VERIFICACIÓN DE SESIÓN ---
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("No has iniciado sesión.")
    if st.button("Ir al Login"):
        st.switch_page("pages/login_page.py")
    st.stop()

# --- CARGA DE DATOS ---
user = st.session_state.user_data
account_row = get_account_by_user(user["Id_user"])

if not account_row:
    st.error("No se encontró una cuenta bancaria asociada a tu usuario.")
    if st.button("Volver al Inicio"):
        st.switch_page("pages/home_page.py")
    st.stop()

account = {
    "Id_account": account_row[0],
    "account_number": account_row[2],
    "currency": account_row[3]
}

# --- VISTA DE CAJERO AUTOMÁTICO ---
st.title("🏧 Cajero Automático")
st.markdown("---")

st.markdown(f"**Cliente:** {user['full_name']}")
st.markdown(f"**Cuenta Destino:** {account['account_number']} ({account['currency']})")

st.markdown("### Seleccione o ingrese el monto a depositar")

# Variable para almacenar el monto a depositar si se usan botones rápidos
if 'quick_amount' not in st.session_state:
    st.session_state.quick_amount = 0.0

def set_amount(val):
    st.session_state.quick_amount = val

# Opciones rápidas
col1, col2, col3, col4 = st.columns(4)
col1.button("$20", use_container_width=True, on_click=set_amount, args=(20.0,))
col2.button("$50", use_container_width=True, on_click=set_amount, args=(50.0,))
col3.button("$100", use_container_width=True, on_click=set_amount, args=(100.0,))
col4.button("$500", use_container_width=True, on_click=set_amount, args=(500.0,))

amount_to_deposit = st.number_input(
    "Monto a depositar", 
    min_value=0.0, 
    value=st.session_state.quick_amount, 
    step=10.0, 
    format="%.2f",
    help="Ingrese el monto exacto que desea depositar en su cuenta."
)

st.markdown("<br>", unsafe_allow_html=True)

if st.button("💰 Depositar Dinero", type="primary", use_container_width=True):
    if amount_to_deposit <= 0:
        st.warning("El monto a depositar debe ser mayor a $0.00.")
    else:
        with st.spinner("Procesando los billetes ingresados..."):
            time.sleep(1.5) # Simular procesamiento del cajero
            
            result = create_simple_transaction(
                account_id=account["Id_account"],
                amount=amount_to_deposit,
                entry_type=ENTRY_CREDIT,
                description=f"Depósito cajero automático ({account['currency']})",
                created_by_user_id=user["Id_user"],
                transaction_type_id=2, # 2 = depósito/retiro
                status_id=1            # Se asume 1=Completada según los servicios
            )
            
            if result.get("success"):
                st.success(f"¡Depósito de ${amount_to_deposit:,.2f} procesado exitosamente!")
                st.balloons()
                st.session_state.quick_amount = 0.0 # Reiniciar monto
            else:
                st.error(f"Error al procesar el depósito: {result.get('error')}")

st.markdown("---")
if st.button("⬅️ Volver a Inicio", use_container_width=True):
    st.session_state.quick_amount = 0.0 # Reiniciar al salir
    st.switch_page("pages/home_page.py")
