import streamlit as st
import time
import sys
import os

# --- 1. CONFIGURACIÓN DE RUTAS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 2. IMPORTACIONES LOCALES ---
from models.account_model import get_accounts_by_user
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
all_accounts = get_accounts_by_user(user["Id_user"])

active_accounts = []
for acc in all_accounts:
    status = acc.get("status_id", acc[4] if isinstance(acc, tuple) else None)
    if status == 1:
        active_accounts.append(acc)

# Si no hay datos, detenemos la ejecución con un mensaje claro
if not active_accounts:
    st.error("⚠️ No se encontró una cuenta bancaria activa asociada a tu usuario.")
    if st.button("Volver al Inicio"):
        st.switch_page("pages/home_page.py")
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

# --- INITIALIZE STATE ---
if 'atm_amount' not in st.session_state:
    st.session_state.atm_amount = ""
    
# Estado para saber si estamos mostrando un recibo
if 'receipt_data' not in st.session_state:
    st.session_state.receipt_data = None

def add_digit(digit):
    st.session_state.atm_amount += str(digit)

def clear_amount():
    st.session_state.atm_amount = ""

def set_quick_amount(val):
    st.session_state.atm_amount = str(val)


# --- VISTA DE CAJERO AUTOMÁTICO ---
st.title("🏧 Synapse ATM 2.0")

# 1. SI HAY UN RECIBO EN MEMORIA, MOSTRARLO Y DETENER LA APP (Bloquea el cajero)
if st.session_state.receipt_data:
    recibo = st.session_state.receipt_data
    
    st.success("¡Transacción Exitosa!")
    st.markdown("### 📄 Tu Recibo")
    
    with st.container(border=True):
        st.markdown(f"""
            **SYNAPSE ATM RECEIPT**
            - **Fecha:** {recibo['fecha']}
            - **Operación:** {recibo['operacion']}
            - **Monto:** ${recibo['monto']:,.2f}
            - **Estado:** {recibo['estado']}
            - **Referencia:** {recibo['referencia']}
        """)
        
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            try:
                from card_print.factura_pdf import generar_recibo_pdf 
                pdf_buffer = generar_recibo_pdf(recibo)
                
                st.download_button(
                    label="📥 Descargar Factura (PDF)",
                    data=pdf_buffer,
                    file_name=f"Recibo_ATM_{recibo['referencia']}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error cargando PDF: {e}")
                
        with col2:
            if st.button("❌ Finalizar y Cerrar", type="primary", use_container_width=True):
                # Limpiamos la memoria para volver al cajero
                st.session_state.receipt_data = None
                st.rerun()
                
    # st.stop() hace que el teclado numérico no se dibuje abajo del recibo
    st.stop()


# 2. SI NO HAY RECIBO, CONTINÚA CON EL CAJERO NORMAL...
with st.container():
    st.markdown(f"#### Bienvenido, {user['full_name']}")
    
    if len(active_accounts) > 1:
        selected_idx = st.selectbox(
            "🏦 Selecciona tu cuenta a operar:",
            options=range(len(active_accounts)),
            format_func=lambda i: f"Cuenta: {active_accounts[i].get('account_number', active_accounts[i][2] if isinstance(active_accounts[i], tuple) else 'N/A')}"
        )
        account_row = active_accounts[selected_idx]
    else:
        account_row = active_accounts[0]

    account = {}
    try:
        if isinstance(account_row, (list, tuple)):
            account["Id_account"]     = account_row[0]
            account["account_number"] = account_row[2]
            account["currency"]       = account_row[3]
        elif isinstance(account_row, dict):
            account["Id_account"]     = account_row.get("Id_account")
            account["account_number"] = account_row.get("account_number")
            account["currency"]       = account_row.get("currency")
    except Exception as e:
        st.error(f"Error técnico al procesar la cuenta: {e}")
        st.stop()

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
                            st.balloons()
                            
                            # Guardamos todos los datos del recibo en sesión
                            st.session_state.receipt_data = {
                                "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "operacion": operation,
                                "monto": final_amount,
                                "estado": 'PENDIENTE DE APROBACIÓN' if result.get('requires_approval') else 'EXITOSO',
                                "referencia": result.get('transaction_id', 'REF-0000'),
                                "usuario": user['full_name'],
                                "cuenta": account['account_number']
                            }
                            
                            clear_amount()
                            st.rerun() # Recarga la app para que entre en la pantalla del recibo
                        else:
                            st.error(f"Error: {result.get('error')}")
        except ValueError:
            st.error("Monto inválido. Por favor use el teclado numérico.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
if st.button("⬅️ Volver a Inicio", use_container_width=True, type="secondary"):
    clear_amount()
    st.switch_page("pages/home_page.py")