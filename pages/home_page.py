import streamlit as st
import time
from datetime import datetime
import sys
import os

# --- 1. CONFIGURACIÓN DE RUTAS (CRÍTICO: ANTES DE LAS IMPORTACIONES LOCALES) ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 2. IMPORTACIONES LOCALES ---
from models.account_model import get_accounts_by_user, get_account_by_number, create_new_account
from models.card_model import get_cards_by_account, is_card_near_expiration, check_pending_renewal, request_card_renewal
from services.transaction_service import get_account_balance, get_all_account_history, create_transfer, process_card_payment
from services.card_service import update_card_active_status, create_card_for_account
from utils.card_generator import generate_luhn_card_number
from config.database import get_connection
from utils.ui_components import apply_premium_style
from utils.pdf_generator import generate_card_pdf
# IMPORT DE LA TARJETA AZUL
from card_print.generate_card_pdf import generate_card_pdf as generate_card_pdf2
# ESTADO DE CUENTA
from card_print.user_pdf import generate_account_statement_pdf

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
user_accounts = get_accounts_by_user(user["Id_user"])

if "active_account_id" not in st.session_state:
    st.session_state["active_account_id"] = user_accounts[0]["Id_account"] if user_accounts else None

# Asegurarse de que el ID activo siga existiendo (por si se eliminó una cuenta, aunque no sucede en nuestro flujo)
if user_accounts and st.session_state["active_account_id"] not in [acc["Id_account"] for acc in user_accounts]:
     st.session_state["active_account_id"] = user_accounts[0]["Id_account"]

account = {
    "Id_account": None,
    "account_number": "Sin cuenta",
    "currency": "USD"
}

if user_accounts:
    # Buscar el row de la cuenta activa
    active_row = next((acc for acc in user_accounts if acc["Id_account"] == st.session_state["active_account_id"]), user_accounts[0])
    try:
        if isinstance(active_row, (list, tuple)):
            account["Id_account"]     = active_row[0]
            account["account_number"] = active_row[2]
            account["currency"]       = active_row[3] if len(active_row) > 3 else "USD"
            account["status_id"]      = active_row[4] if len(active_row) > 4 else 1
        elif isinstance(active_row, dict):
            account["Id_account"]     = active_row.get("Id_account")
            account["account_number"] = active_row.get("account_number", "Sin cuenta")
            account["currency"]       = active_row.get("currency", "USD")
            account["status_id"]      = active_row.get("status_id", 1)
    except Exception as e:
        st.error(f"Error procesando datos de cuenta: {e}")
else:
    st.warning("⚠️ No tienes cuentas bancarias activas.")

if account.get("status_id") == 2:
    st.error("⚠️ **Cuenta Bloqueada:** Esta cuenta no admite transacciones de salida de dinero. Por favor verifique con su administrador.")
elif account.get("status_id") == 3:
    st.error("🚫 **Cuenta Suspendida:** Esta cuenta ha sido suspendida temporalmente y no puede realizar movimientos.")

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
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["Resumen", "Transferencias", "Pago de Servicios", "Mis Tarjetas", "Historial de Movimientos", "Mi Perfil"])

# --- SELECTOR DE CUENTAS ---
st.sidebar.divider()
st.sidebar.markdown("### Mis Cuentas")

if user_accounts:
    # 1. Creamos las opciones del selectbox con indicadores visuales de estado
    account_options = {}
    for acc in user_accounts:
        base_text = f"{acc.get('account_number')} ({acc.get('currency', 'USD')})"
        status = acc.get("status_id")
        
        if status == 4:
            account_options[acc["Id_account"]] = f"⏳ {base_text} - Pendiente"
        elif status == 5:
            account_options[acc["Id_account"]] = f"❌ {base_text} - Rechazada"
        else:
            account_options[acc["Id_account"]] = f"✅ {base_text}"

    # Asegurarnos de que el ID activo esté en las opciones (por si es la primera vez que carga)
    current_active_id = st.session_state.get("active_account_id")
    if current_active_id not in account_options:
        current_active_id = list(account_options.keys())[0]
        st.session_state["active_account_id"] = current_active_id

    # 2. Renderizamos el selectbox
    selected_acc = st.sidebar.selectbox(
        "Cuenta Activa",
        options=list(account_options.keys()),
        format_func=lambda x: account_options[x],
        index=list(account_options.keys()).index(current_active_id)
    )
    
    if selected_acc != st.session_state.get("active_account_id"):
        st.session_state["active_account_id"] = selected_acc
        st.rerun()

    # 3. VERIFICACIÓN DE ESTADO Y BLOQUEO DE UI
    # Buscamos los datos completos de la cuenta seleccionada
    active_account_data = next((acc for acc in user_accounts if acc["Id_account"] == st.session_state["active_account_id"]), None)

    if active_account_data:
        status = active_account_data.get("status_id")
        if status == 4:
            st.warning("### ⏳ Cuenta en Revisión\nEsta cuenta está pendiente de aprobación por nuestro equipo de cajeros. Una vez aprobada, podrás realizar operaciones con ella.")
            st.stop() # Evita que se cargue el historial, saldos y botones de abajo
        elif status == 5:
            st.error("### ❌ Solicitud Rechazada\nLa solicitud para crear esta cuenta fue rechazada. Por favor, comunícate con soporte al cliente para más detalles.")
            st.stop() # Evita que se cargue el resto de la página

st.sidebar.divider()
st.sidebar.markdown("### Configuración")

if len(user_accounts) < 5:
    st.sidebar.markdown('<div class="btn-success">', unsafe_allow_html=True)
    if st.sidebar.button("➕ Abrir Nueva Cuenta", use_container_width=True):
        try:
            # Llama a la función para crear la cuenta
            create_new_account(user["Id_user"])
            
            # Mensajes de retroalimentación actualizados
            st.toast("⏳ Solicitud enviada al cajero para aprobación.", icon="⏳")
            st.sidebar.success("Tu solicitud de cuenta ha sido enviada y está en revisión.")
            
            time.sleep(2) 
            st.rerun()
        except Exception as e:
            st.sidebar.error(str(e))
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
else:
    st.sidebar.info("Límite de 5 cuentas alcanzado.")

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
                full_number = card.get("card_number") # Ahora es el de 16 dígitos
                holder = card.get("holder_name")
                exp_date = card.get("expiration_date")
                is_active = card.get("is_active")
                
                # Para la visualización premium, mostramos el número completo formateado
                display_number = str(full_number) if full_number else "0" * 16
                formatted_number = " ".join([display_number[i:i+4] for i in range(0, 16, 4)])
                
                with cols[idx % 2]:
                    with st.container(border=True):
                        # Estética de tarjeta "Premium"
                        type_label = "DÉBITO" if type_id == 1 else "VIRTUAL"
                        st.caption(f"TARJETA {type_label}")
                        st.markdown(f"#### {formatted_number}")
                        
                        subcol1, subcol2 = st.columns(2)
                        with subcol1:
                            st.write(f"**Titular:**\n{holder}")
                        with subcol2:
                            exp_str = exp_date.strftime("%m/%y") if exp_date else "--/--"
                            st.write(f"**Vence:**\n{exp_str}")
                        
                        status_text = "ACTIVA" if is_active else "BLOQUEADA"
                        status_color = "#10B981" if is_active else "#EF4444"
                        st.markdown(f"Estado: <span style='color:{status_color}; font-weight:bold;'>{status_text}</span>", unsafe_allow_html=True)
                        
                        # --- FLUJO DE RENOVACIÓN DE TARJETAS ---
                        is_renewing = check_pending_renewal(card_id)
                        
                        if is_renewing:
                            st.info("⏳ Renovación en curso. Acérquese a una sucursal para retirar su nueva tarjeta.", icon="⏳")
                        elif is_card_near_expiration(exp_date):
                            st.warning("⚠️ Su tarjeta expirará pronto.")
                            if st.button("🔄 Renovar Tarjeta ($5.00)", key=f"btn_renew_card_{card_id}"):
                                with st.spinner("Procesando pago de renovación..."):
                                    res = request_card_renewal(card_id, account["Id_account"], user["Id_user"])
                                    if res.get("success"):
                                        st.success("¡Pago exitoso! Acuda a una sucursal para finalizar.")
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.error(f"Error en renovación: {res.get('error')}")
                        else:
                            st.info("La gestión de estado (bloqueo) está temporalmente deshabilitada.")
                        # BOTÓN GENERAR Y DESCARGAR TARJETA
                        if st.button("🖨️ Generar tarjeta", key=f"print_card_{card_id}"):
                            card_data_pdf = {
                                "card_number": full_number,
                                "expiration_date": exp_date,
                                "full_name": holder
                                }
                            pdf_buffer = generate_card_pdf2(card_data_pdf, account["Id_account"])
                            # limpiar espacios del nombre para el archivo
                            safe_name = holder.replace(" ", "_")
                            st.download_button(
                                 label="📥 Descargar tarjeta PDF",
                                   data=pdf_buffer,
                                   file_name=f"Tarjeta_de_{safe_name}.pdf",
                                   mime="application/pdf",
                                   key=f"download_card_{card_id}"
                                   )
        else:
            st.info("No tienes tarjetas vinculadas a esta cuenta.")

        st.divider()

        # 2. SOLICITUD DE NUEVA TARJETA
        st.markdown("### Solicitar Nueva Tarjeta")
        
        # Inicializar estado para nueva tarjeta
        if "new_card_data" not in st.session_state:
            st.session_state.new_card_data = None

        # Contar tarjetas actuales
        num_cards = len(cards)

        if num_cards >= 2:
            st.warning("Has alcanzado el límite máximo de 2 tarjetas por cuenta.")
            # Si hay datos de una tarjeta recién creada, los mostramos igual
        
        # Mostrar datos de la tarjeta recién creada (si existen)
        if st.session_state.new_card_data:
            data = st.session_state.new_card_data
            st.success(f"¡Tarjeta emitida con éxito!")
            st.markdown("### 📄 Datos de tu nueva tarjeta")
            
            # Formatear número para mostrar
            f_num = data['full_number']
            display_f_num = " ".join([f_num[i:i+4] for i in range(0, 16, 4)])
            
            st.info(f"**Número:** `{display_f_num}`")
            st.warning(f"**PIN:** `{data['pin']}` - **¡IMPORTANTE!** Memoriza este PIN ahora.")
            
            # Generación de PDF
            exp_date_str = (datetime.now().replace(year=datetime.now().year + 4)).strftime("%m/%y")
            pdf_buffer = generate_card_pdf(
                holder_name=data['holder_name'],
                card_number=data['full_number'],
                pin=data['pin'],
                exp_date_str=exp_date_str,
                card_type=data['type_name']
            )
            
            st.download_button(
                label="📥 Descargar información en PDF",
                data=pdf_buffer,
                file_name=f"datos_tarjeta_{data['last4']}.pdf",
                mime="application/pdf",
                key=f"download_btn_{data['last4']}" # Key única para evitar conflictos
            )
            
            st.balloons()
            
            if st.button("Finalizar y ocultar datos", key="btn_finish_new_card"):
                st.session_state.new_card_data = None
                st.rerun()

            st.info("Esta información permanecerá visible para que puedas copiarla. Haz clic en 'Finalizar' cuando hayas terminado.")
        
        # Mostrar el formulario SOLO si no se ha alcanzado el límite Y no hay una tarjeta recién creada mostrándose
        elif num_cards < 2:
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
                                    st.session_state.new_card_data = {
                                        "full_number": full_number,
                                        "pin": result["pin"],
                                        "last4": result["last4"],
                                        "holder_name": holder_name,
                                        "type_name": selected_type_name
                                    }
                                    st.rerun()
                                else:
                                    st.error(f"Error: {result.get('error')}")

elif menu == "Mi Perfil":
    st.subheader("Información Personal")
    st.write(f"**Nombre:** {user['full_name']}")
    st.write(f"**Email:** {user['email']}")
    st.write(f"**Teléfono:** {user['phone_number']}")
    st.write(f"**DUI:** {user['DUI']}")

    st.divider()
    st.markdown("### 📄 Generar Estado de Cuenta PDF")

    if account["Id_account"]:
        all_history = get_all_account_history(account["Id_account"])
        balance_actual = get_account_balance(account["Id_account"])

        if all_history:
            # --- Filtro opcional por mes y año ---
            use_date_filter = st.checkbox("Filtrar por mes y año", key="profile_pdf_date_filter")
            filtered_history = all_history
            selected_month = None
            selected_year = None

            if use_date_filter:
                months = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                          5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                          9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
                col1, col2 = st.columns(2)
                with col1:
                    selected_month = st.selectbox(
                        "Mes",
                        options=list(months.keys()),
                        format_func=lambda x: months[x]
                    )
                with col2:
                    years = sorted({tx["date"].year for tx in all_history}, reverse=True)
                    selected_year = st.selectbox("Año", options=years)

                filtered_history = [
                    tx for tx in all_history
                    if tx["date"].month == selected_month and tx["date"].year == selected_year
                ]

            if st.button("📄 Generar Estado de Cuenta PDF"):
                from card_print.user_pdf import generate_account_statement_pdf

                pdf_buffer = generate_account_statement_pdf(
                    user_name=user['full_name'],
                    account_number=account['account_number'],
                    balance=balance_actual,
                    transactions=[
                        {
                            "date": tx["date"],
                            "type": {1:"Transferencia",2:"Retiro",3:"Depósito",4:"Pago"}.get(tx["type_id"], "Otro"),
                            "description": tx["description"],
                            "amount": tx["amount"],
                            "entry_type": tx["entry_type"]  # 'credit' o 'debit'
                        }
                        for tx in filtered_history
                    ],
                    month=selected_month,
                    year=selected_year
                )
                st.download_button(
                    label="📥 Descargar PDF",
                    data=pdf_buffer,
                    file_name=f"EstadoCuenta_{user['full_name'].replace(' ','_')}.pdf",
                    mime="application/pdf"
                )
        else:
            st.info("No hay movimientos registrados para esta cuenta.")
    else:
        st.warning("No tienes una cuenta asociada para generar el estado de cuenta.")                                  

elif menu == "Pago de Servicios":
    st.subheader("Pago de Servicios con Tarjeta")
    if not account["Id_account"]:
        st.warning("No tienes una cuenta bancaria asociada.")
    else:
        st.write("Realiza pagos en línea de forma rápida y segura utilizando el número de tarjeta y tu PIN.")
        
        with st.form("card_payment_form"):
            card_number = st.text_input("Número de Tarjeta (16 dígitos)", max_chars=16, placeholder="1234567812345678")
            pin = st.text_input("PIN de la Tarjeta", type="password", max_chars=4, placeholder="****")
            amount = st.number_input("Monto a Pagar ($)", min_value=0.01, step=10.0, format="%.2f")
            description = st.text_input("Descripción del Servicio", placeholder="Ej: Recibo de Luz, Pago por compras en línea, etc.")
            
            st.markdown('<div class="btn-success">', unsafe_allow_html=True)
            submit_payment = st.form_submit_button("Realizar Pago Ahora", type="primary", width="stretch")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if submit_payment:
                if not card_number or len(card_number) != 16 or not card_number.isdigit():
                    st.error("Por favor ingresa un número de tarjeta válido.")
                elif not pin or len(pin) != 4 or not pin.isdigit():
                    st.error("Por favor ingresa un PIN válido de 4 dígitos.")
                elif amount <= 0:
                    st.error("El monto debe ser mayor a cero.")
                elif not description.strip():
                    st.error("Ingresa la descripción del pago.")
                else:
                    with st.spinner("Procesando pago..."):
                        time.sleep(1.5)
                        
                        resultado = process_card_payment(
                            card_number=card_number,
                            pin=pin,
                            amount=amount,
                            description=description,
                            created_by_user_id=user["Id_user"]
                        )
                        
                        if resultado.get("success"):
                            st.success(f"¡Pago de ${amount:,.2f} procesado exitosamente!")
                            st.balloons()
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Error procesando pago: {resultado.get('error')}")                        