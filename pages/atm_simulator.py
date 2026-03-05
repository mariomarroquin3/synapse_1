import streamlit as st
import time
import sys
import os

# --- 1. CONFIGURACIÓN DE RUTAS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 2. IMPORTACIONES LOCALES ---
from models.account_model import get_account_by_user
from services.transaction_service import create_simple_transaction, ENTRY_CREDIT, ENTRY_DEBIT, get_account_balance
from utils.ui_components import apply_premium_style

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="ATM Simulator - Synapse", page_icon="🏧", layout="centered")

# --- VERIFICACIÓN DE SESIÓN ---
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("No has iniciado sesión.")
    if st.button("Ir al Login"):
        st.switch_page("pages/login_page.py")
    st.stop()

# --- DISEÑO PREMIUM ---
apply_premium_style()

# --- CARGA DE DATOS ---
user = st.session_state.user_data
account_row = get_account_by_user(user["Id_user"])

# Si no hay datos, detenemos la ejecución con un mensaje claro
if not account_row:
    st.error("⚠️ No se encontró una cuenta bancaria activa asociada a tu usuario.")
    if st.button("Volver al Inicio"):
        st.switch_page("pages/home_page.py")
    st.stop()

# Mapeo universal (Soporta Tuplas/Listas y Diccionarios)
account = {}

try:
    if isinstance(account_row, (list, tuple)):
        # Acceso por índice (Legacy/Tuple)
        account["Id_account"]     = account_row[0]
        account["account_number"] = account_row[2]
        account["currency"]       = account_row[3]
    elif isinstance(account_row, dict):
        # Acceso por nombre (Modern/Dict)
        account["Id_account"]     = account_row.get("Id_account")
        account["account_number"] = account_row.get("account_number")
        account["currency"]       = account_row.get("currency")
except Exception as e:
    st.error(f"Error técnico al procesar la cuenta: {e}")
    st.stop()

# --- VISTA DE CAJERO AUTOMÁTICO ---
st.title("🏧 Cajero Automático")
st.markdown("---")

st.markdown(f"**Cliente:** {user['full_name']}")
st.markdown(f"**Cuenta Destino:** {account['account_number']} ({account['currency']})")

tab_dep, tab_ret = st.tabs(["💰 Depositar", "💵 Retirar"])

with tab_dep:
    st.markdown("### Seleccione o ingrese el monto a depositar")
    
    # Variable para almacenar el monto a depositar si se usan botones rápidos
    if 'quick_amount_dep' not in st.session_state:
        st.session_state.quick_amount_dep = 0.0
    
    def set_amount_dep(val):
        st.session_state.quick_amount_dep = val
    
    # Opciones rápidas
    col1, col2, col3, col4 = st.columns(4)
    col1.button("$20", key="dep_20", width="stretch", on_click=set_amount_dep, args=(20.0,), type="secondary")
    col2.button("$50", key="dep_50", width="stretch", on_click=set_amount_dep, args=(50.0,), type="secondary")
    col3.button("$100", key="dep_100", width="stretch", on_click=set_amount_dep, args=(100.0,), type="secondary")
    col4.button("$500", key="dep_500", width="stretch", on_click=set_amount_dep, args=(500.0,), type="secondary")
    
    amount_to_deposit = st.number_input(
        "Monto a depositar", 
        min_value=0.0, 
        value=st.session_state.quick_amount_dep, 
        step=10.0, 
        format="%.2f",
        help="Ingrese el monto exacto que desea depositar en su cuenta.",
        key="amount_deposit"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
    if st.button("💰 Depositar Dinero", type="primary", width="stretch"):
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
                    transaction_type_id=3, # 3 = depósito cajero automático
                    status_id=1            # Se asume 1=Completada según los servicios
                )
                
                if result.get("success"):
                    if result.get("requires_approval"):
                        st.info(f"⏳ Depósito de ${amount_to_deposit:,.2f} retenido para aprobación administrativa.")
                        st.warning("El dinero no se reflejará hasta que un administrador lo apruebe.")
                    else:
                        st.success(f"¡Depósito de ${amount_to_deposit:,.2f} procesado exitosamente!")
                        st.balloons()
                    st.session_state.quick_amount_dep = 0.0 # Reiniciar monto
                else:
                    st.error(f"Error al procesar el depósito: {result.get('error')}")
    st.markdown('</div>', unsafe_allow_html=True)

with tab_ret:
    st.markdown("### Seleccione o ingrese el monto a retirar")
    
    # Variable para almacenar el monto a retirar si se usan botones rápidos
    if 'quick_amount_ret' not in st.session_state:
        st.session_state.quick_amount_ret = 0.0
    
    def set_amount_ret(val):
        st.session_state.quick_amount_ret = val
    
    # Opciones rápidas
    col1, col2, col3, col4 = st.columns(4)
    col1.button("$20", key="ret_20", width="stretch", on_click=set_amount_ret, args=(20.0,), type="secondary")
    col2.button("$50", key="ret_50", width="stretch", on_click=set_amount_ret, args=(50.0,), type="secondary")
    col3.button("$100", key="ret_100", width="stretch", on_click=set_amount_ret, args=(100.0,), type="secondary")
    col4.button("$500", key="ret_500", width="stretch", on_click=set_amount_ret, args=(500.0,), type="secondary")
    
    amount_to_withdraw = st.number_input(
        "Monto a retirar", 
        min_value=0.0, 
        value=st.session_state.quick_amount_ret, 
        step=10.0, 
        format="%.2f",
        help="Ingrese el monto exacto que desea retirar de su cuenta.",
        key="amount_withdraw"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("💵 Retirar Dinero", type="primary", width="stretch"):
        if amount_to_withdraw <= 0:
            st.warning("El monto a retirar debe ser mayor a $0.00.")
        else:
            with st.spinner("Procesando retiro..."):
                time.sleep(1.5) # Simular procesamiento del cajero
                
                balance = get_account_balance(account["Id_account"])
                if balance < amount_to_withdraw:
                    st.error("Fondos insuficientes.")
                else:
                    result = create_simple_transaction(
                        account_id=account["Id_account"],
                        amount=amount_to_withdraw,
                        entry_type=ENTRY_DEBIT,
                        description=f"Retiro cajero automático ({account['currency']})",
                        created_by_user_id=user["Id_user"],
                        transaction_type_id=2, # 2 = retiro cajero automático
                        status_id=1            # Se asume 1=Completada según los servicios
                    )
                    
                    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                    if result.get("success"):
                        if result.get("requires_approval"):
                            st.info(f"⏳ Retiro de ${amount_to_withdraw:,.2f} retenido para aprobación administrativa.")
                            st.warning("La transacción será procesada una vez sea aprobada por un administrador.")
                        else:
                            st.success(f"¡Retiro de ${amount_to_withdraw:,.2f} procesado exitosamente!")
                            st.balloons()
                        st.session_state.quick_amount_ret = 0.0 # Reiniciar monto
                    else:
                        st.error(f"Error al procesar el retiro: {result.get('error')}")
                    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
if st.button("⬅️ Volver a Inicio", width="stretch", type="secondary"):
    st.session_state.quick_amount_dep = 0.0 # Reiniciar al salir
    st.session_state.quick_amount_ret = 0.0 # Reiniciar al salir
    st.switch_page("pages/home_page.py")
