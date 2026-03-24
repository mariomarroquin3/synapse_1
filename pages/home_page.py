import streamlit as st # Synapse Private Banking - UI Enhanced
import time
from datetime import datetime
import sys
import os

# --- 1. CONFIGURACIÓN DE RUTAS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 2. IMPORTACIONES LOCALES ---
from models.account_model import get_accounts_by_user, get_account_by_number, create_new_account
from models.card_model import get_cards_by_account, is_card_near_expiration, check_pending_renewal, request_card_renewal
from services.transaction_service import get_account_balance, get_all_account_history, create_transfer, process_card_payment
from services.card_service import update_card_active_status, create_card_for_account
from services.auth_service import change_password
from utils.card_generator import generate_luhn_card_number
from utils.security import validate_password
from config.database import get_connection
from utils.ui_components import apply_premium_style, render_dashboard_card
from utils.pdf_generator import generate_card_pdf
from card_print.generate_card_pdf import generate_card_pdf as generate_card_pdf2
from card_print.user_pdf import generate_account_statement_pdf
from streamlit_option_menu import option_menu

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

if user_accounts and st.session_state["active_account_id"] not in [acc["Id_account"] for acc in user_accounts]:
     st.session_state["active_account_id"] = user_accounts[0]["Id_account"]

account = {"Id_account": None, "account_number": "Sin cuenta", "currency": "USD"}

if user_accounts:
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

# --- FUNCIONES ---
def logout():
    st.session_state.logged_in = False
    st.session_state.user_data = None
    st.switch_page("pages/login_page.py")

# --- LOGICA DE NAVEGACION (Manejado en Sidebar) ---

with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 30px; margin-top: -10px;">
        <div style="background: var(--primary); width: 40px; height: 40px; border-radius: 50%; display: flex; justify-content: center; align-items: center;">
            <svg fill="white" width="20" height="20" viewBox="0 0 24 24"><path d="M4 10h3v7H4zM10.5 10h3v7h-3zM2 19h20v3H2zM17 10h3v7h-3zM12 1L2 6v2h20V6z"/></svg>
        </div>
        <div>
            <h3 style="margin: 0; font-size: 1.1rem; font-weight: 800; letter-spacing: 1px; color: white;">SYNAPSE</h3>
            <p style="margin: 0; font-size: 0.65rem; color: var(--text-secondary); letter-spacing: 1px;">PRIVATE BANKING</p>
        </div>
    </div>
    
    <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 12px 16px; display: flex; align-items: center; gap: 12px; margin-bottom: 30px;">
        <img src="https://ui-avatars.com/api/?name={av_name}&background=2D2D35&color=fff&bold=true" style="width: 40px; height: 40px; border-radius: 50%;" />
        <div style="overflow: hidden;">
            <p style="margin: 0; font-weight: 600; font-size: 0.9rem; color: white; text-overflow: ellipsis; white-space: nowrap;">{full_name}</p>
            <p style="margin: 0; font-size: 0.75rem; color: var(--text-secondary);">User</p>
        </div>
    </div>
    """.format(av_name=user.get('full_name', 'U').replace(" ", "+"), full_name=user.get('full_name', 'Usuario')), unsafe_allow_html=True)
    
    menu = option_menu(
        menu_title=None,
        options=["Resumen", "Transferencias", "Cajero Automático", "Tarjetas", "Pago de Servicios", "Historial", "Ajustes"],
        icons=["grid-fill", "send-fill", "bank2", "credit-card-fill", "wallet-fill", "clock-history", "gear-fill"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "var(--text-secondary)", "font-size": "18px"},
            "nav-link": {
                "font-size": "14px", "text-align": "left", "margin": "0px", 
                "color": "var(--text-secondary)", "padding": "12px 20px", "border-radius": "12px", "font-weight": "500"
            },
            "nav-link-selected": {
                "background-color": "rgba(37, 99, 235, 0.1)", "color": "white",
                "border": "1px solid rgba(37, 99, 235, 0.2)",
                "font-weight": "600"
            },
        }
    )
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("Cerrar Sesión", type="secondary", use_container_width=True):
        logout()

# --- SELECTOR DE CUENTAS (SIDEBAR) ---
st.sidebar.divider()
st.sidebar.markdown("### Mis Cuentas")

if user_accounts:
    status_icons = {1: "✅", 2: "🔒", 3: "⏸️", 4: "⏳", 5: "❌"}
    account_options = {
        acc["Id_account"]: f"{status_icons.get(acc.get('status_id'), '💳')} {acc.get('account_number')} ({acc.get('currency', 'USD')})" 
        for acc in user_accounts
    }
    selected_acc = st.sidebar.selectbox(
        "Cuenta Activa",
        options=list(account_options.keys()),
        format_func=lambda x: account_options[x],
        index=list(account_options.keys()).index(st.session_state["active_account_id"]) if st.session_state["active_account_id"] in account_options else 0
    )
    if selected_acc != st.session_state["active_account_id"]:
        st.session_state["active_account_id"] = selected_acc
        st.rerun()

st.sidebar.divider()
if len(user_accounts) < 5:
    if st.sidebar.button("➕ Abrir Nueva Cuenta", use_container_width=True):
        try:
            create_new_account(user["Id_user"])
            st.cache_data.clear()
            st.toast("⏳ Solicitud enviada.", icon="⏳")
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.sidebar.error(str(e))

if st.sidebar.button("🤖 Consulte a la IA", use_container_width=True):
    import webbrowser
    webbrowser.open(r"C:\Users\jonat\Documents\GitHub\synapse_1\RAG_SYNAPSE\index.html")

# ==========================================================
# --- VALIDACIÓN DE SEGURIDAD (LOGICA ACTUALIZADA) ---
# ==========================================================
estado_actual = account.get("status_id", 1)

# A. BLOQUEO TOTAL (Estados: 3, 4, 5)
# Si está SUSPENDIDA (3), ya no puede hacer nada.
if estado_actual == 3:
    st.error("🚫 **Cuenta Suspendida:** Esta cuenta ha sido inhabilitada por el administrador. No se permiten consultas ni movimientos.")
    st.stop()
elif estado_actual == 5:
    st.error("❌ **Cuenta Rechazada:** Esta solicitud no fue aprobada.")
    st.stop() 
elif estado_actual == 4:
    st.warning("⏳ **Cuenta Pendiente:** Esperando aprobación del cajero para habilitar el acceso.")
    st.stop()

# B. BLOQUEO PARCIAL (Estado: 2)
# Bloqueada permite ver saldos, pero NO sacar dinero.
if estado_actual == 2:
    st.error("⚠️ **Cuenta Bloqueada:** Solo se permiten depósitos entrantes. Las transferencias y pagos están deshabilitados.")


# --- MENU ROUTING ---
if menu == "Cajero Automático":
    st.switch_page("pages/atm_simulator.py")

elif menu == "Resumen":
    balance = get_account_balance(account["Id_account"]) if account["Id_account"] else 0.0
    st.markdown(f'<p style="color: var(--text-secondary); margin-bottom: 0;">Bienvenido de nuevo,</p><h1 style="margin-top: -10px; margin-bottom: 30px; font-weight: 800; font-size: 2.2rem; color: white;">{user.get("full_name", "Usuario")}</h1>', unsafe_allow_html=True)
    render_dashboard_card(balance, account.get("account_number", "Sin cuenta"))

elif menu == "Transferencias":
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px;">
            <div style="background: rgba(37, 99, 235, 0.15); width: 48px; height: 48px; border-radius: 14px; display: flex; justify-content: center; align-items: center; border: 1px solid rgba(37, 99, 235, 0.3);">
                <svg width="24" height="24" fill="var(--primary)" viewBox="0 0 24 24"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="var(--primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </div>
            <div>
                <h2 style="margin: 0; font-weight: 700; color: white;">Transferencias a Terceros</h2>
                <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">Envía dinero de forma rápida y segura.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    if not account["Id_account"]:
        st.warning("No tienes una cuenta bancaria asociada para hacer transferencias.")
    else:
        balance = get_account_balance(account["Id_account"])
        
        # --- CUENTA ORIGEN CARD ---
        st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; padding: 24px; position: relative; overflow: hidden; margin-bottom: 24px;">
                <!-- Decorative Arrow SVG -->
                <svg style="position: absolute; right: 20px; top: 50%; transform: translateY(-50%); width: 120px; height: 120px; opacity: 0.05; fill: white;" viewBox="0 0 24 24">
                    <path d="M13 7l5 5m0 0l-5 5m5-5H6" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <p style="color: #3B82F6; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin: 0 0 8px 0; letter-spacing: 1px;">Cuenta Origen</p>
                <h3 style="color: white; font-size: 1.5rem; font-weight: 700; margin: 0 0 4px 0; letter-spacing: 1px;">{account['account_number']}</h3>
                <p style="color: #9CA3AF; font-size: 0.9rem; margin: 0;">Disponible: <span style="color: white; font-weight: 600;">${balance:,.2f}</span></p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="transfer-container">', unsafe_allow_html=True)
        with st.form("transfer_form", border=False):
            # Input wrapper with right arrow for Cuenta Destino
            st.markdown("""
                <div style="position: relative;">
                    <p style="color: #9CA3AF; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-bottom: 8px;">Cuenta Destino</p>
                    <svg style="position: absolute; right: 12px; bottom: 10px; width: 20px; height: 20px; opacity: 0.2; fill: white;" viewBox="0 0 24 24"><path d="M13 7l5 5m0 0l-5 5m5-5H6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </div>
            """, unsafe_allow_html=True)
            dest_account_num = st.text_input("dest_account_num", label_visibility="collapsed", placeholder="Ej. 4521-XXXX...")
            
            st.markdown('<p style="color: #9CA3AF; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin: 16px 0 8px 0;">Monto (USD)</p>', unsafe_allow_html=True)
            amount_to_transfer = st.number_input("amount_to_transfer", label_visibility="collapsed", min_value=0.00, step=10.0, format="%.2f")
            
            # Input wrapper with left arrow for Concepto
            st.markdown("""
                <div style="position: relative;">
                    <p style="color: #9CA3AF; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-bottom: 8px;">Concepto (Opcional)</p>
                    <svg style="position: absolute; right: 12px; bottom: 10px; width: 20px; height: 20px; opacity: 0.2; fill: white; transform: rotate(180deg);" viewBox="0 0 24 24"><path d="M13 7l5 5m0 0l-5 5m5-5H6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </div>
            """, unsafe_allow_html=True)
            description = st.text_input("description", label_visibility="collapsed", placeholder="Ej. Pago de cena")
            
            st.markdown('<div style="margin-top: 32px;">', unsafe_allow_html=True)
            submit_transfer = st.form_submit_button("Continuar", type="primary", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
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

elif menu == "Historial":
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px;">
            <div style="background: rgba(16, 185, 129, 0.15); width: 48px; height: 48px; border-radius: 14px; display: flex; justify-content: center; align-items: center; border: 1px solid rgba(16, 185, 129, 0.3);">
                <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="#10B981"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            </div>
            <div>
                <h2 style="margin: 0; font-weight: 700; color: white;">Historial de Movimientos</h2>
                <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">Revisa tus ingresos y egresos recientes.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not account["Id_account"]:
        st.warning("No tienes una cuenta bancaria asociada para ver el historial.")
    else:
        all_history = get_all_account_history(account["Id_account"])

        if all_history:

            # --- OPCIÓN DE FILTRADO ---
            st.markdown("### 🔍 Opciones de Visualización")

            # Mejora visual 1: Usar un toggle (interruptor) en lugar de un checkbox
            apply_filter = st.toggle("Activar filtro por fechas")

            filtered_history = all_history

            if apply_filter:
                # Mejora visual 2: Un contenedor con borde sutil para agrupar el filtro
                with st.container(border=True):
                    
                    # Importamos explícitamente date y timedelta aquí para evitar errores
                    from datetime import date, timedelta
                    
                    # Definimos por defecto los últimos 30 días hasta hoy
                    today = date.today()
                    default_start = today - timedelta(days=30)

                    # Al no poner min_value ni max_value, el usuario puede elegir CUALQUIER fecha
                    date_range = st.date_input(
                        "Selecciona el rango de fechas",
                        value=(default_start, today),
                        format="DD/MM/YYYY" # Formato latino amigable
                    )

                    # Streamlit devuelve 1 fecha si el usuario está a medio click, y 2 fechas cuando ya eligió inicio y fin.
                    if len(date_range) == 2:
                        start_date, end_date = date_range
                        
                        filtered_history = [
                            tx for tx in all_history
                            if start_date <= (tx["date"].date() if hasattr(tx["date"], "date") else tx["date"]) <= end_date
                        ]
                    else:
                        st.warning("🗓️ Por favor, selecciona la fecha de fin en el calendario.")

            st.divider()

            # --- GRÁFICO DE SALDO EVOLUTIVO ---
            import altair as alt
            import pandas as pd

            st.markdown("### 📈 Evolución del Saldo")
            if all_history:
                # Calcular saldo acumulado ordenando desde el inicio para precisión
                df_ev = pd.DataFrame([
                    {"fecha": tx["date"], "monto": tx["amount"] if tx["entry_type"] == "credit" else -tx["amount"]}
                    for tx in sorted(all_history, key=lambda x: x["date"])
                ])
                df_ev["saldo"] = df_ev["monto"].cumsum()

                # Filtrar el DataFrame para la visualización si hay fechas aplicadas
                df_plot = df_ev.copy()
                if apply_filter and len(date_range) == 2:
                    start_d, end_d = date_range
                    df_plot['fecha_solo'] = pd.to_datetime(df_plot['fecha']).dt.date
                    df_plot = df_plot[(df_plot['fecha_solo'] >= start_d) & (df_plot['fecha_solo'] <= end_d)]
                
                if not df_plot.empty:
                    chart_saldo = alt.Chart(df_plot).mark_area(
                        line={'color':'#10B981'},
                        color=alt.Gradient(
                            gradient='linear',
                            stops=[alt.GradientStop(color='rgba(16, 185, 129, 0.1)', offset=0),
                                   alt.GradientStop(color='rgba(16, 185, 129, 0.7)', offset=1)],
                            x1=1, x2=1, y1=1, y2=0
                        )
                    ).encode(
                        x=alt.X("fecha:T", title="Fecha"),
                        y=alt.Y("saldo:Q", title="Saldo ($)", scale=alt.Scale(zero=False)),
                        tooltip=[
                            alt.Tooltip("fecha:T", title="Fecha", format="%d/%m/%Y %H:%M"),
                            alt.Tooltip("saldo:Q", title="Saldo Disponible", format=",.2f")
                        ]
                    ).properties(height=300).interactive()
                    
                    st.altair_chart(chart_saldo, use_container_width=True)
                else:
                    st.info("Sin registros de saldo para el periodo filtrado.")
            else:
                st.info("No hay datos suficientes para mostrar la evolución del saldo.")

            st.divider()

            # --- RENDERIZADO DE MOVIMIENTOS ---
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
                    st.info("No hay movimientos en este periodo o categoría.")
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

elif menu == "Tarjetas":
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px;">
            <div style="background: rgba(249, 115, 22, 0.15); width: 48px; height: 48px; border-radius: 14px; display: flex; justify-content: center; align-items: center; border: 1px solid rgba(249, 115, 22, 0.3);">
                <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="#F97316"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/></svg>
            </div>
            <div>
                <h2 style="margin: 0; font-weight: 700; color: white;">Gestión de Tarjetas</h2>
                <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">Administra tus tarjetas activas y solicita nuevas.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
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
                    # Estética de tarjeta "Premium" con diferenciación de color
                    if type_id == 1: # DEBITO
                        type_label = "DÉBITO"
                        bg_color = "linear-gradient(135deg, #0f172a 0%, #334155 100%)"
                        card_icon = '<svg width="32" height="32" viewBox="0 0 24 24" fill="white" style="opacity: 0.6;"><path d="M4 10h3v7H4zM10.5 10h3v7h-3zM2 19h20v3H2zM17 10h3v7h-3zM12 1L2 6v2h20V6z"/></svg>'
                    else: # VIRTUAL u otros
                        type_label = "VIRTUAL"
                        bg_color = "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)"
                        card_icon = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" style="opacity: 0.8;"><path d="M21 12V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2h7m9-7l-3-3m0 0l-3 3m3-3v10" stroke-linecap="round" stroke-linejoin="round"/></svg>'
                    
                    st.markdown(f"""
                        <div style="background: {bg_color}; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 18px; padding: 22px; position: relative; margin-bottom: 20px; color: white; min-height: 190px; box-shadow: 0 15px 30px -10px rgba(0, 0, 0, 0.3);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
                                <span style="font-size: 0.75rem; font-weight: 800; opacity: 0.9; letter-spacing: 1.5px; text-transform: uppercase;">{type_label}</span>
                                {card_icon}
                            </div>
                            <div style="font-size: 1.4rem; font-weight: 600; letter-spacing: 2px; margin-bottom: 20px;">
                                {formatted_number}
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                                <div>
                                    <p style="font-size: 0.6rem; opacity: 0.6; margin: 0; text-transform: uppercase;">Titular</p>
                                    <p style="font-size: 0.9rem; font-weight: 500; margin: 0;">{holder}</p>
                                </div>
                                <div style="text-align: right;">
                                    <p style="font-size: 0.6rem; opacity: 0.6; margin: 0; text-transform: uppercase;">Vence</p>
                                    <p style="font-size: 0.9rem; font-weight: 500; margin: 0;">{exp_date.strftime('%m/%y') if exp_date else '--/--'}</p>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    status_text = "ACTIVA" if is_active else "BLOQUEADA"
                    status_color = "#10B981" if is_active else "#EF4444"
                    st.markdown(f"**Estado:** <span style='color:{status_color}; font-weight:bold;'>{status_text}</span>", unsafe_allow_html=True)
                    
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
                    if st.button("📄 Ver / Imprimir Tarjeta (PDF)", key=f"print_card_{card_id}"):
                        st.session_state[f"show_download_{card_id}"] = True

                    if st.session_state.get(f"show_download_{card_id}"):
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
                        if st.button("Cerrar", key=f"close_print_{card_id}"):
                            st.session_state[f"show_download_{card_id}"] = False
                            st.rerun()
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
            st.info("💡 Puedes solicitar hasta 2 tarjetas por cuenta.")
            with st.form("new_card_form", border=True):
                st.markdown("#### Formulario de Solicitud")
                type_options = {1: "Débito Física", 2: "Virtual"}
                selected_type_name = st.selectbox("Tipo de Tarjeta", options=list(type_options.values()))
                selected_type_id = [k for k, v in type_options.items() if v == selected_type_name][0]
                
                holder_name = st.text_input("Nombre en la Tarjeta", value=user["full_name"])
                
                st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                submit_card = st.form_submit_button("Emitir Nueva Tarjeta", type="primary", use_container_width=True)
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

elif menu == "Ajustes":
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px;">
            <div style="background: rgba(255, 255, 255, 0.05); width: 48px; height: 48px; border-radius: 14px; display: flex; justify-content: center; align-items: center; border: 1px solid rgba(255, 255, 255, 0.1);">
                <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="white"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
            </div>
            <div>
                <h2 style="margin: 0; font-weight: 700; color: white;">Ajustes de Cuenta</h2>
                <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">Configura tu perfil y preferencias de seguridad.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 👤 Información Personal")
    
    st.markdown(f"""
        <div style="background: rgba(22, 22, 26, 0.6); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; padding: 24px; margin-bottom: 24px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <p style="color: var(--text-secondary); font-size: 0.8rem; margin: 0; text-transform: uppercase;">Nombre Completo</p>
                    <p style="color: white; font-weight: 600; font-size: 1.1rem; margin: 5px 0 0 0;">{user['full_name']}</p>
                </div>
                <div>
                    <p style="color: var(--text-secondary); font-size: 0.8rem; margin: 0; text-transform: uppercase;">Correo Electrónico</p>
                    <p style="color: white; font-weight: 600; font-size: 1.1rem; margin: 5px 0 0 0;">{user['email']}</p>
                </div>
                <div>
                    <p style="color: var(--text-secondary); font-size: 0.8rem; margin: 0; text-transform: uppercase;">Teléfono</p>
                    <p style="color: white; font-weight: 600; font-size: 1.1rem; margin: 5px 0 0 0;">{user['phone_number']}</p>
                </div>
                <div>
                    <p style="color: var(--text-secondary); font-size: 0.8rem; margin: 0; text-transform: uppercase;">DUI</p>
                    <p style="color: white; font-weight: 600; font-size: 1.1rem; margin: 5px 0 0 0;">{user['DUI']}</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("###  Cambiar Contraseña")
    
    with st.expander("Cambiar tu contraseña de acceso", expanded=False):
        # Input fields OUTSIDE form for real-time validation
        current_pass = st.text_input("Contraseña Actual", type="password", placeholder="Ingresa tu contraseña actual", key="curr_pass")
        new_pass = st.text_input("Nueva Contraseña", type="password", placeholder="Ingresa una nueva contraseña", key="new_pass")
        confirm_pass = st.text_input("Confirmar Nueva Contraseña", type="password", placeholder="Confirma tu nueva contraseña", key="conf_pass")
        
        # Real-time validation feedback for new password (OUTSIDE form)
        if new_pass:
            is_valid, missing_reqs = validate_password(new_pass)
            if is_valid:
                st.success("✅ Contraseña cumple todos los requisitos de seguridad")
            else:
                with st.expander("📋 Requisitos faltantes:"):
                    for requirement in missing_reqs:
                        st.warning(f"❌ {requirement}")
        
        # Password confirmation check
        if new_pass and confirm_pass:
            if new_pass != confirm_pass:
                st.error("❌ Las contraseñas no coinciden")
            else:
                st.success("✅ Las contraseñas coinciden")
        elif confirm_pass and not new_pass:
            st.warning("⚠️ Ingresa la nueva contraseña primero")
        
        # Calculate button state
        password_is_valid = False
        if new_pass:
            password_is_valid, _ = validate_password(new_pass)
        
        button_disabled = not (current_pass and new_pass and confirm_pass and password_is_valid and new_pass == confirm_pass)
        
        # Submit button (OUTSIDE form for proper state handling)
        st.divider()
        if st.button(
            "🔄 Cambiar Contraseña",
            type="primary",
            use_container_width=True,
            disabled=button_disabled
        ):
            # Validation before processing
            is_valid, missing_reqs = validate_password(new_pass)
            
            if not current_pass:
                st.error("❌ Debes ingresar tu contraseña actual")
            elif not new_pass or not confirm_pass:
                st.error("❌ Debes ingresar y confirmar la nueva contraseña")
            elif new_pass != confirm_pass:
                st.error("❌ Las contraseñas no coinciden")
            elif not is_valid:
                missing_text = ", ".join(missing_reqs)
                st.error(f"❌ La nueva contraseña no cumple los requisitos: {missing_text}")
            else:
                # Process password change
                success, message = change_password(user["Id_user"], current_pass, new_pass)
                if success:
                    st.success("✅ Contraseña actualizada exitosamente")
                    st.info("Por favor, inicia sesión nuevamente con tu nueva contraseña")
                    time.sleep(2)
                    st.switch_page("pages/login_page.py")
                else:
                    st.error(f"❌ {message}")

    st.divider()
    st.markdown("### 📄 Generar Estado de Cuenta PDF")

    if account["Id_account"]:
        all_history = get_all_account_history(account["Id_account"])
        balance_actual = get_account_balance(account["Id_account"])

        if all_history:
            # --- Filtro opcional por rango de fechas ---
            use_date_filter = st.toggle("Activar filtro por fechas para el PDF", key="profile_pdf_date_filter")
            filtered_history = all_history
            
            # Variables para el PDF (puedes ajustarlas luego en tu generador de PDF)
            selected_month = None
            selected_year = None
            
            # Formateo de texto para mostrar en la interfaz
            date_range_text = "Historial Completo"

            if use_date_filter:
                with st.container(border=True):
                    from datetime import date, timedelta
                    
                    today = date.today()
                    default_start = today - timedelta(days=30)

                    date_range = st.date_input(
                        "Selecciona el periodo para el Estado de Cuenta",
                        value=(default_start, today),
                        format="DD/MM/YYYY",
                        key="pdf_date_input"
                    )

                    if len(date_range) == 2:
                        start_date, end_date = date_range
                        
                        filtered_history = [
                            tx for tx in all_history
                            if start_date <= (tx["date"].date() if hasattr(tx["date"], "date") else tx["date"]) <= end_date
                        ]
                        
                        # Guardamos el mes y año de inicio solo por si la función del PDF falla sin ellos
                        selected_month = start_date.month
                        selected_year = start_date.year
                        
                        date_range_text = f"Del {start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}"
                        
                    else:
                        st.warning("🗓️ Por favor, selecciona la fecha de fin en el calendario.")
            
            # Mostrar al usuario qué va a imprimir
            st.info(f"Se generará un PDF con: **{date_range_text}** ({len(filtered_history)} movimientos).")

            if st.button("📄 Generar Estado de Cuenta PDF"):
                
                # Prevenir la generación si el filtro está a medias
                if use_date_filter and len(date_range) < 2:
                    st.error("Debes completar la selección de fechas antes de generar el PDF.")
                elif not filtered_history:
                    st.warning("No hay movimientos en el periodo seleccionado para generar el PDF.")
                else:
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
                                "entry_type": tx["entry_type"]
                            }
                            for tx in filtered_history
                        ],
                        date_range_text=date_range_text 
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
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px;">
            <div style="background: rgba(168, 85, 247, 0.15); width: 48px; height: 48px; border-radius: 14px; display: flex; justify-content: center; align-items: center; border: 1px solid rgba(168, 85, 247, 0.3);">
                <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="#A855F7"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>
            </div>
            <div>
                <h2 style="margin: 0; font-weight: 700; color: white;">Pago de Servicios</h2>
                <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">Paga tus facturas usando tu número de tarjeta y PIN.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
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
                            if resultado.get("requires_approval"):
                                st.info(f"⏳ Pago de ${amount:,.2f} retenido para aprobación administrativa.")
                                st.warning("El pago se completará una vez sea revisado por un administrador.")
                                time.sleep(4)
                                st.rerun()
                            else:
                                st.success(f"¡Pago de ${amount:,.2f} procesado exitosamente!")
                                st.balloons()
                                time.sleep(2)
                                st.rerun()
                        else:
                            st.error(f"Error procesando pago: {resultado.get('error')}")                        