import streamlit as st
import sys
import os
import re
import time
import pandas as pd
from services.audit_service import log_action

# --- 1. CONFIGURACIÓN DE RUTAS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 2. IMPORTACIONES LOCALES ---
from models.user_model import get_users_by_role_category, update_user_status
from models.account_model import get_accounts_by_user, update_account_status
from models.card_model import get_cards_by_account, update_card_status
from services.user_service import register_user_with_permissions
from services.transaction_service import review_transaction
from config.database import get_cursor
from utils.ui_components import apply_premium_style

# --- SEGURIDAD DE PÁGINA ---
if "user_data" not in st.session_state or st.session_state["user_data"]["role_id"] not in [1, 3, 4, 5]:
    st.error("Acceso denegado. Se requieren privilegios de Personal Interno.")
    if st.button("Ir al Login"):
        st.switch_page("pages/admin_login.py")
    st.stop()

role_id = st.session_state["user_data"]["role_id"]

st.set_page_config(page_title="Synapse | Admin Dashboard", page_icon="📈", layout="wide")

# --- DISEÑO PREMIUM ---
apply_premium_style()

# CSS ADICIONAL (Específico de Dashboard)
st.markdown("""
<style>
    .status-active { color: #10B981; font-weight: 700; }
    .status-suspended { color: #EF4444; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# --- CÁLCULO DE MÉTRICAS (KPIs) ---
if role_id == 3:
    with get_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM [user] WHERE role_id = 2")
        total_clients = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM [transaction] WHERE status_id = 2")
        pending_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM [user] WHERE role_id IN (1, 3, 4, 5)") # Staff roles
        staff_count = cursor.fetchone()[0]

# --- CABECERA Y MÉTRICAS ---
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    role_names = {1: "Cajero", 3: "Administrador", 4: "Analista Financiero", 5: "Auditor"}
    st.title(f"🛡️ Panel de Control - {role_names.get(role_id, 'Personal')}")
    st.write(f"Conectado como: **{st.session_state['user_data']['full_name']}**")
with col_h2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Cerrar Sesión", type="secondary", use_container_width=True):
        st.session_state.clear()
        st.switch_page("pages/login_page.py")

st.divider()

# Dashboard Metrics
if role_id == 3:
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Clientes Totales", f"{total_clients}", help="Usuarios registrados con rol de Cliente")
    col_m2.metric("Aprobaciones Pendientes", f"{pending_count}", delta=f"{pending_count} TX", delta_color="inverse")
    col_m3.metric("Personal Synapse", f"{staff_count}")
    st.divider()

if role_id == 3:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "👥 Gestión de Personal", 
        "💳 Gestión de Clientes", 
        "🔒 Control de Cuentas y Tarjetas",
        "💸 Aprobaciones", 
        "📜 Historial de Aprobaciones",
        "⚙️ Configuración"
    ])

    # --- TAB 1: GESTIÓN DE PERSONAL ---
    with tab1:
        st.header("Gestión de Personal Interno")

        # Crear nuevo personal
        with st.expander("➕ Registrar nuevo miembro del personal"):
            with st.form("create_staff_form"):
                col1, col2 = st.columns(2)
                with col1:
                    s_name = st.text_input("Nombre Completo")
                    s_email = st.text_input("Correo Electrónico")
                    s_pass = st.text_input("Contraseña Temporal", type="password")
                    s_role = st.selectbox("Rol", [
                        (1, "Cajero"),
                        (3, "Administrador"),
                        (4, "Analista Financiero"),
                        (5, "Auditor")
                    ], format_func=lambda x: x[1])
                with col2:
                    s_dui = st.text_input("DUI", max_chars=9)
                    s_phone = st.text_input("Teléfono", max_chars=8)
                    s_gen = st.selectbox("Género", ["Masculino", "Femenino", "Otro"])

                submit_staff = st.form_submit_button("Crear Usuario Staff")

                if submit_staff:
                    if not s_name or not s_email or not s_pass or not s_dui:
                        st.warning("Complete los campos obligatorios.")
                    else:
                        user_data = {
                            "role_id": s_role[0],
                            "email": s_email,
                            "password": s_pass,
                            "dui": f"{s_dui[:8]}-{s_dui[8:]}" if len(s_dui) == 9 else s_dui,
                            "full_name": s_name,
                            "gender": s_gen[0],
                            "phone_number": f"+503 {s_phone[:4]}-{s_phone[4:]}" if len(s_phone) == 8 else s_phone
                        }
                        res = register_user_with_permissions(st.session_state["user_data"]["Id_user"], user_data)
                        if res["success"]:
                            st.success(f"Usuario {s_role[1]} creado exitosamente.")
                            st.rerun()
                        else:
                            st.error(f"Error: {res['error']}")

        # Listar Personal
        staff_users = get_users_by_role_category(is_staff=True)
        if staff_users:
            df_staff = pd.DataFrame(staff_users)
            df_staff = df_staff[['Id_user', 'full_name', 'email', 'role_id', 'is_active']]
            # Map roles
            role_map = {1: "Cajero", 3: "Admin", 4: "Analista", 5: "Auditor"}
            df_staff['Rol'] = df_staff['role_id'].map(role_map)
            st.dataframe(df_staff, width="stretch")
        else:
            st.info("No hay personal registrado.")

    # --- TAB 2: GESTIÓN DE CLIENTES ---
    with tab2:
        st.header("Gestión de Cuentas de Clientes")
        st.info("Nota: Los administradores pueden gestionar clientes existentes pero no crearlos.")

        clients = get_users_by_role_category(is_staff=False)
        if clients:
            # 1. Buscador
            search_query = st.text_input("🔍 Buscar cliente por nombre o correo", placeholder="Ej: Juan Pérez o juan@example.com").lower()

            # Filtrar clientes por búsqueda
            if search_query:
                clients = [c for c in clients if search_query in c['full_name'].lower() or search_query in c['email'].lower()]

            # 2. Separación por Estados
            tab_activos, tab_suspendidos = st.tabs(["✅ Activos", "🚫 Suspendidos"])

            def render_client_list(client_list):
                if not client_list:
                    st.info("No se encontraron clientes en esta categoría.")
                    return

                for client in client_list:
                    with st.container():
                        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                        status_text = "Activo" if client['is_active'] else "Suspendido"
                        status_class = "status-active" if client['is_active'] else "status-suspended"

                        c1.write(f"**{client['full_name']}**")
                        c2.write(client['email'])
                        c3.markdown(f"<span class='{status_class}'>{status_text}</span>", unsafe_allow_html=True)

                        btn_label = "Suspender" if client['is_active'] else "Activar"
                        if c4.button(btn_label, key=f"btn_{client['Id_user']}"):
                            nuevo_estado = not client['is_active']
                            update_user_status(client['Id_user'], nuevo_estado)
                            accion = "SUSPENDER_USUARIO" if client['is_active'] else "ACTIVAR_USUARIO"
                            log_action(
                                st.session_state["user_data"]["Id_user"],
                                  accion,
                                  f"Admin cambió estado del usuario {client['full_name']} ({client['email']})"
                                  )
                            st.success(f"Estado de {client['full_name']} actualizado.")
                            time.sleep(1)
                            st.rerun()
                    st.divider()

            with tab_activos:
                active_clients = [c for c in clients if c['is_active']]
                render_client_list(active_clients)

            with tab_suspendidos:
                suspended_clients = [c for c in clients if not c['is_active']]
                render_client_list(suspended_clients)
        else:
            st.info("No hay clientes registrados en el sistema.")

    # --- TAB 3: CONTROL DE CUENTAS Y TARJETAS ---
    with tab3:
        st.header("Control de Cuentas y Tarjetas de Clientes")
        st.write("Gestiona el estado operativo (Activa, Bloqueada, Suspendida) de las cuentas y tarjetas.")

        # Obtener todos los clientes
        clients_for_control = get_users_by_role_category(is_staff=False)
        
        if clients_for_control:
            search_control = st.text_input("🔍 Buscar cliente por nombre o correo", key="search_ctrl").lower()
            if search_control:
                clients_for_control = [c for c in clients_for_control if search_control in c['full_name'].lower() or search_control in c['email'].lower()]
            
            for client in clients_for_control:
                with st.expander(f"👤 {client['full_name']} | ✉️ {client['email']}"):
                    # 1. Obtener y renderizar la Cuenta
                    accounts = get_accounts_by_user(client["Id_user"])
                    
                    if not accounts:
                         st.info("Este cliente aún no tiene cuentas bancarias.")
                         continue
                         
                    st.markdown("#### 🏦 Cuentas Bancarias")
                    for acc_idx, account in enumerate(accounts):
                        ac_id = account.get("Id_account", account[0] if isinstance(account, tuple) else None)
                        if not ac_id: continue
                        
                        ac_num = account.get("account_number", account[2] if isinstance(account, tuple) else "N/A")
                        ac_status = account.get("status_id", account[4] if isinstance(account, tuple) else 1)
                        
                        col_acc1, col_acc2 = st.columns([2, 1])
                        with col_acc1:
                            st.write(f"**Número de Cuenta:** `{ac_num}`")
                            st.write(f"**Saldo Actual:** Pendiente a cargar en módulo") # Podriamos cargar el get_balance_from_ledger pero evitamos llamadas excesivas en un loop
                        
                        with col_acc2:
                            new_ac_status = st.selectbox(
                                "Estado de la Cuenta",
                                options=[1, 2, 3],
                                format_func=lambda x: "✅ Activa" if x == 1 else ("⚠️ Bloqueada" if x == 2 else "🚫 Suspendida"),
                                index=[1, 2, 3].index(ac_status) if ac_status in [1,2,3] else 0,
                                key=f"acc_status_{ac_id}"
                            )
                            
                            if new_ac_status != ac_status:
                                try:
                                     update_account_status(ac_id, new_ac_status)
                                     log_action(
                                          st.session_state["user_data"]["Id_user"],
                                          "CAMBIO_ESTADO_CUENTA",
                                          f"Admin cambió estado de la cuenta {ac_num} a {new_ac_status}"
                                          )
                                     st.success(f"Estado de cuenta {ac_num} actualizado correctamente.")
                                     time.sleep(1)
                                     st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                                    
                        # 2. Obtener y renderizar las Tarjetas de esta cuenta
                        st.markdown(f"**💳 Tarjetas Vinculadas a {ac_num}**")
                        cards = get_cards_by_account(ac_id)
                        if cards:
                            for card in cards:
                                with st.container(border=True):
                                    c1, c2 = st.columns([3, 1])
                                    with c1:
                                        # Mostrar últimos 4 dígitos reales del card_number de 16, no la de PIN
                                        last4 = str(card["card_number"])[-4:]
                                        st.write(f"**Tarjeta:** `**** **** **** {last4}`")
                                        exp = card["expiration_date"].strftime("%m/%y") if card["expiration_date"] else "N/A"
                                        st.caption(f"Vence: {exp}")
                                    
                                    with c2:
                                        # Status Toggle
                                        toggle_label = "Activa" if card["is_active"] else "Inactiva"
                                        is_active_new = st.toggle(
                                            toggle_label,
                                            value=bool(card["is_active"]),
                                            key=f"card_toggle_{card['Id_card']}"
                                        )
                                        
                                        if is_active_new != bool(card["is_active"]):
                                            try:
                                                update_card_status(card["Id_card"], is_active_new)
                                                log_action(
                                                    st.session_state["user_data"]["Id_user"],
                                                    "CAMBIO_ESTADO_TARJETA",
                                                    f"Admin cambió estado de la tarjeta ****{last4} a {'Activa' if is_active_new else 'Inactiva'}"
                                                    )
                                                st.toast(f"Estado de la tarjeta ...{last4} cambiado a {'Activa' if is_active_new else 'Inactiva'}", icon="✅")
                                                time.sleep(1)
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"Error: {str(e)}")
                        else:
                            st.info("No hay tarjetas vinculadas a esta cuenta.")
                        
                        if acc_idx < len(accounts) - 1:
                            st.divider()
        else:
            st.info("No hay clientes registrados en el sistema.")

    # --- TAB 4: APROBACIONES ($10K+) ---
    with tab4:
        st.header("Transacciones Pendientes de Aprobación")
        st.write("Cualquier movimiento mayor o igual a $10,000 requiere autorización manual.")

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

        with get_cursor() as cursor:
            cursor.execute(query)
            pendientes = cursor.fetchall()

        if pendientes:
            for p in pendientes:
                tx_id, desc, date, amount, from_acc, to_acc, type_name, req = p
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1:
                        st.markdown(f"**ID:** {tx_id} | **Tipo:** {type_name}")
                        st.markdown(f"**Solicitante:** {req}")
                        amt_display = float(amount or 0)
                        st.markdown(f"**Monto:** `${amt_display:,.2f}`")
                        date_str = date.strftime('%d/%m/%Y %H:%M') if date else "N/A"
                        st.caption(f"Fecha: {date_str}")

                    with c2:
                        st.info(f"De: {from_acc if from_acc else 'N/A'}\nA: {to_acc if to_acc else 'N/A'}")

                    with c3:
                        note = st.text_input("Nota (opcional)", key=f"note_{tx_id}")
                        col_b1, col_b2 = st.columns(2)
                        st.markdown('<div class="btn-success">', unsafe_allow_html=True)
                        if col_b1.button("✅ Aprobar", key=f"app_{tx_id}", width="stretch", type="primary"):
                            res = review_transaction(tx_id, st.session_state["user_data"]["Id_user"], True, note)
                            if res["success"]:
                                st.success("Aprobada")
                                st.rerun()
                            else: st.error(res["error"])
                        st.markdown('</div>', unsafe_allow_html=True)
                        st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                        if col_b2.button("❌ Rechazar", key=f"rej_{tx_id}", width="stretch", type="secondary"):
                            res = review_transaction(tx_id, st.session_state["user_data"]["Id_user"], False, note)
                            if res["success"]:
                                st.warning("Rechazada")
                                st.rerun()
                            else: st.error(res["error"])
                        st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No hay transacciones pendientes de revisión.")

    # --- TAB 5: HISTORIAL DE APROBACIONES ---
    with tab5:
        st.header("Historial de Revisiones")
        st.write("Registro de transacciones que ya han sido procesadas por el equipo administrativo.")

        history_query = """
            SELECT 
                t.Id_transaction, t.description, t.transaction_date, 
                a.amount, a.reviewed_at, a.review_notes,
                tt.name AS type_name, u_req.full_name AS requester,
                u_adm.full_name AS reviewer, ts.name AS status_name,
                t.status_id
            FROM (((([transaction] t
            INNER JOIN transaction_approvals a ON t.Id_transaction = a.transaction_id)
            INNER JOIN transaction_type tt ON t.transaction_type_id = tt.Id_transaction_type)
            INNER JOIN [user] u_req ON t.created_by_user_id = u_req.Id_user)
            LEFT JOIN [user] u_adm ON a.admin_id = u_adm.Id_user)
            INNER JOIN transaction_status ts ON t.status_id = ts.Id_transaction_status
            WHERE t.status_id IN (3, 5)
            ORDER BY a.reviewed_at DESC
        """

        with get_cursor() as cursor:
            cursor.execute(history_query)
            movimientos = cursor.fetchall()

        if movimientos:
            for m in movimientos:
                tx_id, desc, date, amount, rev_date, notes, t_name, req, admin, s_name, s_id = m
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1.5, 1])
                    with c1:
                        st.markdown(f"**ID:** {tx_id} | **Tipo:** {t_name}")
                        st.markdown(f"**Cliente:** {req}")
                        st.markdown(f"**Monto:** `${float(amount or 0):,.2f}`")
                        st.caption(f"Fecha Solicitud: {date.strftime('%d/%m/%Y %H:%M') if date else 'N/A'}")

                    with c2:
                        status_color = "#10B981" if s_id == 3 else "#EF4444"
                        st.markdown(f"**Estado:** <span style='color:{status_color}; font-weight:bold;'>{s_name.upper()}</span>", unsafe_allow_html=True)
                        st.markdown(f"**Revisado por:** {admin if admin else 'Sistema'}")
                        st.caption(f"Fecha Revisión: {rev_date.strftime('%d/%m/%Y %H:%M') if rev_date else 'N/A'}")

                    with c3:
                        st.markdown("**Notas de Revisión:**")
                        st.info(notes if notes else "Sin observaciones.")
        else:
            st.info("No hay historial de revisiones disponible.")


    # --- TAB 6: CONFIGURACIÓN (DENTRO DEL IF ROLE_ID == 3) ---
        with tab6:
            st.header("⚙️ Configuración")
            st.subheader("📜 Historial de Tus Acciones Administrativas")

            # Esta consulta devuelve exactamente 4 columnas
            query_audit = """
                SELECT l.Id_log, l.action, l.details, l.created_at
                FROM audit_log l
                WHERE l.user_id = ?
                ORDER BY l.created_at DESC
            """
            u_id = st.session_state['user_data']['Id_user']

            with get_cursor() as cursor:
                cursor.execute(query_audit, (u_id,))
                logs = cursor.fetchall()

            # Validación de seguridad: Nos aseguramos de que cada fila tenga 4 elementos
            logs_validados = [list(row) for row in logs if row is not None and len(row) == 4]

            if logs_validados:
                # Ahora las columnas coinciden perfectamente con los datos (4 = 4)
                df_logs = pd.DataFrame(logs_validados, columns=["ID", "Acción", "Detalles", "Fecha"])
                df_logs["Fecha"] = pd.to_datetime(df_logs["Fecha"])

                # Filtros
                col1, col2 = st.columns(2)
                with col1:
                    acciones = ["Todas"] + sorted(df_logs["Acción"].unique())
                    action_filter = st.selectbox("⚙️ Tipo de acción", acciones, key="filter_tab6_final")

                if action_filter != "Todas":
                    df_logs = df_logs[df_logs["Acción"] == action_filter]

                st.dataframe(df_logs.sort_values(by="Fecha", ascending=False), use_container_width=True)
            else:
                st.info("No has realizado acciones todavía.")
#--------------------------------------------------
# PANEL CAJERO 
# -------------------------------------------------
elif role_id == 1:
    st.header("Panel Operativo - Cajero")
    st.info("Buscador de Cuentas y Procesamiento de Transacciones rápidos.")
    
    # Buscador de cuenta visual para el cajero
    from models.account_model import get_account_by_number
    from services.transaction_service import create_simple_transaction
    
    search_acc = st.text_input("🔍 Buscar Cuenta por Número (Ej. SV_synapse...)")
    
    if search_acc:
        acc_data = get_account_by_number(search_acc)

        if acc_data:
            acc_id = acc_data[0] if isinstance(acc_data, (list, tuple)) else acc_data.get('Id_account')
            st.success(f"Cuenta encontrada: ID {acc_id}")

            with st.form("cajero_tx_form"):
                tx_type = st.selectbox("Tipo de Operación", ["Depósito", "Retiro"])
                tx_amount = st.number_input("Monto", min_value=0.01, step=10.0)
                tx_desc = st.text_input("Descripción")

                sub_tx = st.form_submit_button("Procesar Operación", type="primary")

                if sub_tx:
                    if not tx_desc or tx_amount <= 0:
                        st.warning("Complete todos los campos de la operación.")
                    else:

                        # 2 Retiro / 3 Depósito
                        t_id = 2 if tx_type == "Retiro" else 3
                        entry = "debit" if t_id == 2 else "credit"

                        res = create_simple_transaction(
                            account_id=acc_id,
                            amount=tx_amount,
                            entry_type=entry,
                            description=tx_desc,
                            created_by_user_id=st.session_state['user_data']['Id_user'],
                            transaction_type_id=t_id
                        )

                        if res.get('success'):
                            msg = res.get('message', 'Operación ejecutada con éxito.')
                            st.success(msg)
                        else:
                            st.error(res.get('error'))

        else:
            st.error("Cuenta no encontrada.")
            
elif role_id == 4:
    st.header("Panel de Métricas - Analista Financiero")
    st.write("Vista de solo lectura (Resumen global).")

    from services.rbac_service import execute_analyst_query
    import pandas as pd

    res = execute_analyst_query()

    if res.get('status') == 200:
        data = res['data']

        col_a1, col_a2 = st.columns(2)

        with col_a1:
            st.subheader("Flujo de Caja Global")

            if data['flujo']:
                df_flujo = pd.DataFrame(data['flujo'])

                st.bar_chart(
                    df_flujo,
                    x='entry_type',
                    y='total'
                )
            else:
                st.info("Sin datos en contabilidad.")

        with col_a2:
            st.subheader("Volumen de Transacciones")

            if data['tipos']:
                df_tipos = pd.DataFrame(data['tipos'])

                st.bar_chart(
                    df_tipos,
                    x='name',
                    y='count'
                )
            else:
                st.info("Sin datos por tipo.")

        st.divider()

        st.subheader("Detalle de Volúmenes por Tipo")

        if data['tipos']:
            st.dataframe(
                df_tipos,
                use_container_width=True
            )

    else:
        st.error(res.get('error'))


elif role_id == 5:
    st.header("Control de Riesgos - Auditor")
    st.write("Historial Detallado de operaciones del Sistema. (Solo Lectura)")

    # IMPORTANTE: Todo el código de abajo ahora tiene 4 espacios de sangría
    import pandas as pd
    import datetime
    from services.rbac_service import execute_auditor_query

    # ------------------ HISTORIAL GENERAL ------------------
    res = execute_auditor_query()

    if res.get('status') == 200:
        history = res['data']

        if history:
            df_history = pd.DataFrame(history)

            # Filtro por usuario/Email
            filter_user = st.text_input("🔎 Filtrar historial por 'created_by' (Usuario/Email)")
            if filter_user:
                df_history = df_history[
                    df_history['created_by'].astype(str).str.contains(filter_user, case=False, na=False)
                ]

            st.subheader("📋 Historial de Operaciones")
            st.dataframe(df_history, use_container_width=True)
        else:
            st.info("El libro mayor está vacío.")
    else:
        st.error(res.get('error'))

    # ------------------ HISTORIAL DE ACCIONES ADMINISTRATIVAS ------------------
    st.divider()
    st.subheader("📜 Historial de Acciones Administrativas")

    query = """
        SELECT 
            l.Id_log,
            u.full_name,
            l.action,
            l.details,
            l.created_at
        FROM audit_log l
        INNER JOIN [user] u ON l.user_id = u.Id_user
        ORDER BY l.created_at DESC
    """

    with get_cursor() as cursor:
        cursor.execute(query)
        logs = cursor.fetchall()

    # --- PROTECCIÓN: solo filas con 5 elementos ---
    logs = [list(row) for row in logs if row is not None and len(row) == 5]

    if logs:
        df_logs = pd.DataFrame(logs, columns=[
            "ID", "Administrador", "Acción", "Detalles", "Fecha"
        ])
        df_logs["Fecha"] = pd.to_datetime(df_logs["Fecha"])

        # ---------------- FILTROS ----------------
        col1, col2, col3 = st.columns([2, 2, 2])

        with col1:
            search_admin = st.text_input("🔎 Filtrar por administrador", key="audit_search")

        with col2:
            action_filter = st.selectbox(
                "⚙️ Filtrar por tipo de acción",
                ["Todas"] + sorted(df_logs["Acción"].unique()),
                key="audit_action"
            )

        with col3:
            filter_by_date = st.checkbox("Filtrar por mes y año")
            if filter_by_date:
                months = list(range(1, 13))
                years = list(range(2020, datetime.datetime.now().year + 1))
                selected_month = st.selectbox("Mes", months, index=datetime.datetime.now().month-1, key="month_select")
                selected_year = st.selectbox("Año", years, index=len(years)-1, key="year_select")

        # Aplicar filtros
        if search_admin:
            df_logs = df_logs[df_logs["Administrador"].str.contains(search_admin, case=False)]

        if action_filter != "Todas":
            df_logs = df_logs[df_logs["Acción"] == action_filter]

        if filter_by_date and 'selected_month' in locals():
            df_logs = df_logs[
                (df_logs["Fecha"].dt.month == selected_month) &
                (df_logs["Fecha"].dt.year == selected_year)
            ]

        st.dataframe(df_logs.sort_values(by="Fecha", ascending=False), use_container_width=True)
    else:
        st.info("No hay acciones administrativas registradas todavía.")