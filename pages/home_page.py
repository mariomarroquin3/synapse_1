import streamlit as st
import time
import sys
import os

# --- 1. CONFIGURACIÓN DE RUTAS (CRÍTICO: ANTES DE LAS IMPORTACIONES LOCALES) ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 2. IMPORTACIONES LOCALES ---
from models.account_model import get_account_by_user, get_account_by_number
from models.card_model import get_cards_by_account
from services.transaction_service import get_account_balance, get_all_account_history, create_transfer
from services.card_service import update_card_active_status, create_card_for_account
from utils.card_generator import generate_luhn_card_number
from config.database import get_connection
from utils.ui_components import apply_premium_style

# --- 3. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Banca en Línea - Synapse", layout="wide")

# --- 4. DISEÑO PREMIUM ---
apply_premium_style()

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
    st.markdown(f"## Bienvenido, {user.get('full_name', 'Usuario')}")
    dui_display = user.get('DUI', user.get('dui', 'N/A'))
    st.caption(f"DUI: {dui_display} | Cuenta: {account.get('account_number', 'N/A')}")
with head_col2:
    st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
    if st.button("Cerrar Sesión", type="secondary"):
        logout()
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# Menú de Navegación
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["Resumen", "Transferencias", "Mis Tarjetas", "Historial de Movimientos", "Mi Perfil"])

# --- BOTÓN DE CAJERO ---
st.sidebar.divider()
if st.sidebar.button("🏧 CAJERO", width="stretch", type="primary"):
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
            
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            submit_transfer = st.form_submit_button("Realizar Transferencia", type="primary", width="stretch")
            st.markdown('</div>', unsafe_allow_html=True)
            
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
                                    if result.get("requires_approval"):
                                        st.info(f"⏳ Transferencia de ${amount_to_transfer:,.2f} retenida para aprobación administrativa.")
                                        st.warning("La transferencia se completará una vez sea revisada por un administrador.")
                                        time.sleep(3)
                                        st.rerun()
                                    else:
                                        st.success(f"¡Transferencia de ${amount_to_transfer:,.2f} realizada exitosamente!")
                                        st.balloons()
                                        time.sleep(1)
                                        st.rerun() # Refrescar para ver nuevo balance
                                else:
                                    st.error(f"Error al procesar la transferencia: {result.get('error')}")
                            else:
                                st.error("No se pudo identificar el ID de la cuenta destino.")

elif menu == "Historial de Movimientos":
    st.subheader("Historial de Movimientos")

    if not account["Id_account"]:
        st.warning("No tienes una cuenta bancaria asociada para ver el historial.")
    else:
        all_history = get_all_account_history(account["Id_account"])

        if all_history:

            # --- OPCIÓN DE FILTRADO ---
            st.markdown("### Opciones de Visualización")

            apply_filter = st.checkbox("Filtrar por mes y año")

            filtered_history = all_history

            if apply_filter:

                colf1, colf2 = st.columns(2)

                months = {
                    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
                }

                with colf1:
                    selected_month = st.selectbox(
                        "Seleccionar Mes",
                        options=list(months.keys()),
                        format_func=lambda x: months[x]
                    )

                with colf2:
                    years = sorted({tx["date"].year for tx in all_history}, reverse=True)
                    selected_year = st.selectbox("Seleccionar Año", options=years)

                filtered_history = [
                    tx for tx in all_history
                    if tx["date"].month == selected_month and tx["date"].year == selected_year
                ]

            st.divider()

            # Diccionario para nombres amigables
            type_names = {
                1: "Transferencia",
                2: "Retiro",
                3: "Depósito",
                4: "Pago con Tarjeta"
            }

            tab_todo, tab_trans, tab_retiro, tab_depo, tab_pago = st.tabs([
                "Todos", "Transferencias", "Retiros", "Depósitos", "Pagos"
            ])

            def render_transactions(tx_list):

                if not tx_list:
                    st.info("No hay movimientos en esta categoría.")
                    return

                for tx in tx_list:

                    with st.container(border=True):

                        col_tx1, col_tx2 = st.columns([3, 1])

                        with col_tx1:
                            st.markdown(
                                f"**Fecha:** {tx['date'].strftime('%Y-%m-%d %H:%M:%S')}"
                            )

                            st.markdown(
                                f"**Tipo:** {type_names.get(tx['type_id'], 'Otro')}"
                            )

                            st.markdown(
                                f"**Descripción:** {tx['description']}"
                            )

                        with col_tx2:

                            if tx['entry_type'] == 'debit':

                                st.markdown(
                                    f"### <span style='color:#EF4444;'>-$ {tx['amount']:,.2f}</span>",
                                    unsafe_allow_html=True
                                )

                            else:

                                st.markdown(
                                    f"### <span style='color:#10B981;'>+$ {tx['amount']:,.2f}</span>",
                                    unsafe_allow_html=True
                                )

            with tab_todo:
                render_transactions(filtered_history)

            with tab_trans:
                render_transactions(
                    [tx for tx in filtered_history if tx['type_id'] == 1]
                )

            with tab_retiro:
                render_transactions(
                    [tx for tx in filtered_history if tx['type_id'] == 2]
                )

            with tab_depo:
                render_transactions(
                    [tx for tx in filtered_history if tx['type_id'] == 3]
                )

            with tab_pago:
                render_transactions(
                    [tx for tx in filtered_history if tx['type_id'] == 4]
                )

        else:
            st.info("No tienes movimientos registrados todavía.")

elif menu == "Mis Tarjetas":
    st.subheader("Gestión de Tarjetas")
    if not account["Id_account"]:
        st.warning("No tienes una cuenta bancaria asociada.")
    else:
        # 1. VISUALIZACIÓN DE TARJETAS
        st.markdown("### Mis Tarjetas Activas")
        cards = get_cards_by_account(account["Id_account"])
        
        if cards:
            cols = st.columns(2)
            for idx, card in enumerate(cards):
                # card es ahora un diccionario
                card_id = card.get("Id_card")
                type_id = card.get("card_type_id")
                card_number = card.get("card_number_last4")
                holder = card.get("holder_name")
                exp_date = card.get("expiration_date")
                is_active = card.get("is_active")
                
                last4 = str(card_number) if card_number else "****"
                
                with cols[idx % 2]:
                    with st.container(border=True):
                        # Estética de tarjeta "Premium"
                        type_label = "DÉBITO" if type_id == 1 else "VIRTUAL"
                        st.caption(f"TARJETA {type_label}")
                        st.markdown(f"#### **** **** **** {last4}")
                        
                        subcol1, subcol2 = st.columns(2)
                        with subcol1:
                            st.write(f"**Titular:**\n{holder}")
                        with subcol2:
                            exp_str = exp_date.strftime("%m/%y") if exp_date else "--/--"
                            st.write(f"**Vence:**\n{exp_str}")
                        
                        status_text = "ACTIVA" if is_active else "BLOQUEADA"
                        status_color = "#10B981" if is_active else "#EF4444"
                        st.markdown(f"Estado: <span style='color:{status_color}; font-weight:bold;'>{status_text}</span>", unsafe_allow_html=True)
                        
                        st.info("La gestión de estado (bloqueo) está temporalmente deshabilitada.")
        else:
            st.info("No tienes tarjetas vinculadas a esta cuenta.")

        st.divider()

        # 2. SOLICITUD DE NUEVA TARJETA
        st.markdown("### Solicitar Nueva Tarjeta")
        if len(cards) >= 2:
            st.warning("Has alcanzado el límite máximo de 2 tarjetas por cuenta.")
        else:
            with st.expander("Abrir formulario de solicitud"):
                with st.form("new_card_form"):
                    type_options = {1: "Débito Física", 2: "Virtual"}
                    selected_type_name = st.selectbox("Tipo de Tarjeta", options=list(type_options.values()))
                    selected_type_id = [k for k, v in type_options.items() if v == selected_type_name][0]
                    
                    holder_name = st.text_input("Nombre en la Tarjeta", value=user["full_name"])
                    
                    st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                    submit_card = st.form_submit_button("Emitir Tarjeta Ahora", type="primary")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    if submit_card:
                        if not holder_name:
                            st.error("El nombre del titular es requerido.")
                        else:
                            with st.spinner("Generando nueva tarjeta..."):
                                full_number = generate_luhn_card_number()
                                result = create_card_for_account(
                                    account_id=account["Id_account"],
                                    card_type_id=selected_type_id,
                                    holder_name=holder_name,
                                    full_card_number=full_number
                                )
                                
                                if result.get("success"):
                                    st.success(f"¡Tarjeta emitida con éxito!")
                                    st.info(f"**Número:** {full_number}")
                                    st.warning(f"**PIN:** {result['pin']} - Guardar en lugar seguro")
                                    st.info(f"**Últimos 4 dígitos:** {result['last4']}")
                                    st.balloons()
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error(f"Error: {result.get('error')}")

elif menu == "Mi Perfil":
    st.subheader("Información Personal")
    st.write(f"**Nombre:** {user['full_name']}")
    st.write(f"**Email:** {user['email']}")
    st.write(f"**Teléfono:** {user['phone_number']}")
    st.write(f"**DUI:** {user['DUI']}")