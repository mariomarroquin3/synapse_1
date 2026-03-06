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

# --- ESTILOS CSS ADICIONALES PARA ATM ---
st.markdown("""
    <style>
    .atm-container {
        background-color: #1e1e1e;
        border-radius: 15px;
        padding: 30px;
        border: 2px solid #333;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .atm-screen {
        background-color: #0c1c0c;
        border: 5px solid #444;
        border-radius: 10px;
        padding: 20px;
        font-family: 'Courier New', Courier, monospace;
        color: #00ff00;
        margin-bottom: 20px;
        box-shadow: inset 0 0 10px #000;
    }
    .keypad-button {
        height: 60px !important;
        font-size: 20px !important;
        font-weight: bold !important;
    }
    .amount-display {
        font-size: 36px;
        text-align: center;
        background: #000;
        color: #00ff00;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- VISTA DE CAJERO AUTOMÁTICO ---
st.title("🏧 Synapse ATM 2.0")

# --- INITIALIZE STATE ---
if 'atm_amount' not in st.session_state:
    st.session_state.atm_amount = ""

def add_digit(digit):
    st.session_state.atm_amount += str(digit)

def clear_amount():
    st.session_state.atm_amount = ""

def set_quick_amount(val):
    st.session_state.atm_amount = str(val)

# --- ATM CONTAINER ---
with st.container():
    st.markdown(f"#### Bienvenido, {user['full_name']}")
    
    col_main1, col_main2 = st.columns([1.5, 1])

    with col_main1:
        st.markdown('<div class="atm-screen">', unsafe_allow_html=True)
        st.write("SYNAPSE BANKING NETWORK")
        st.write(f"CUENTA: {account['account_number']}")
        
        balance = get_account_balance(account["Id_account"])
        st.write(f"SALDO DISPONIBLE: $ {balance:,.2f} {account['currency']}")
        
        st.markdown("---")
        
        # Display current amount being entered
        display_val = st.session_state.atm_amount if st.session_state.atm_amount else "0"
        st.markdown(f'<div class="amount-display">$ {display_val}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Action selection
        operation = st.selectbox("Seleccione Operación", ["Retiro", "Depósito"], index=0)

    with col_main2:
        # Numeric Keypad
        st.markdown("##### Teclado Numérico")
        k_col1, k_col2, k_col3 = st.columns(3)
        
        for i in range(1, 10):
            col = [k_col1, k_col2, k_col3][(i-1)%3]
            if col.button(str(i), key=f"btn_{i}", use_container_width=True):
                add_digit(i)
                st.rerun()
        
        if k_col1.button(".", key="btn_dot", use_container_width=True):
            if "." not in st.session_state.atm_amount:
                add_digit(".")
                st.rerun()
        if k_col2.button("0", key="btn_0", use_container_width=True):
            add_digit(0)
            st.rerun()
        if k_col3.button("C", key="btn_clear", use_container_width=True, type="secondary"):
            clear_amount()
            st.rerun()

        st.markdown("##### Montos Rápidos")
        q_col1, q_col2 = st.columns(2)
        if q_col1.button("$20", key="q_20", use_container_width=True): set_quick_amount(20); st.rerun()
        if q_col2.button("$50", key="q_50", use_container_width=True): set_quick_amount(50); st.rerun()
        if q_col1.button("$100", key="q_100", use_container_width=True): set_quick_amount(100); st.rerun()
        if q_col2.button("$500", key="q_500", use_container_width=True): set_quick_amount(500); st.rerun()

    st.divider()
    
    # Process Button
    btn_label = "Confirmar Retiro" if operation == "Retiro" else "Confirmar Depósito"
    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
    if st.button(btn_label, type="primary", use_container_width=True):
        try:
            final_amount = float(st.session_state.atm_amount) if st.session_state.atm_amount else 0.0
            
            if final_amount <= 0:
                st.warning("Ingrese un monto válido mayor a $0.00")
            else:
                with st.spinner("Procesando transacción..."):
                    time.sleep(2)
                    
                    entry_type = ENTRY_DEBIT if operation == "Retiro" else ENTRY_CREDIT
                    type_id = 2 if operation == "Retiro" else 3
                    desc = f"{operation} ATM - {account['account_number']}"
                    
                    if operation == "Retiro" and balance < final_amount:
                        st.error("❌ Fondos insuficientes para este retiro.")
                    else:
                        result = create_simple_transaction(
                            account_id=account["Id_account"],
                            amount=final_amount,
                            entry_type=entry_type,
                            description=desc,
                            created_by_user_id=user["Id_user"],
                            transaction_type_id=type_id
                        )
                        
                        if result.get("success"):
                            st.success(f"✅ {operation} de ${final_amount:,.2f} procesado con éxito.")
                            st.balloons()
                            
                            # Mostrar "Recibo"
                            with st.expander("📄 Ver Recibo de Transacción", expanded=True):
                                st.markdown(f"""
                                    **SYNAPSE ATM RECEIPT**
                                    - **Fecha:** {time.strftime("%Y-%m-%d %H:%M:%S")}
                                    - **Operación:** {operation}
                                    - **Monto:** ${final_amount:,.2f}
                                    - **Estado:** {'PENDIENTE DE APROBACIÓN' if result.get('requires_approval') else 'EXITOSO'}
                                    - **Referencia:** {result.get('transaction_id')}
                                """)
                            
                            clear_amount()
                            time.sleep(3)
                            st.rerun()
                        else:
                            st.error(f"Error: {result.get('error')}")
        except ValueError:
            st.error("Monto inválido. Por favor use el teclado numérico.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
if st.button("⬅️ Volver a Inicio", use_container_width=True, type="secondary"):
    clear_amount()
    st.switch_page("pages/home_page.py")
