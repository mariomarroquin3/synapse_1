import streamlit as st
import time
from models.account_model import get_account_by_user
from services.transaction_service import get_account_balance, get_account_history_by_type

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
    "Id_account": account_row[0] if account_row else None,
    "account_number": account_row[2] if account_row else "Sin cuenta",
    "currency": account_row[3] if account_row else "USD"
}

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
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["Resumen", "Transferencias", "Retiros", "Depósitos", "Mi Perfil"])

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

elif menu == "Retiros":
    st.subheader("Historial de Retiros")
    if account["Id_account"]:
        history = get_account_history_by_type(account["Id_account"], 2) # 2 = retiro cajero automático
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
        history = get_account_history_by_type(account["Id_account"], 3) # 3 = depósito cajero automático
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