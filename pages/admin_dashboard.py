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
from models.account_model import get_pending_accounts, approve_account, reject_account


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
@st.cache_data(ttl=600, max_entries=10)
def get_admin_kpis():
    with get_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM [user] WHERE role_id = 2")
        total_clients = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM [transaction] WHERE status_id = 2")
        pending = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM [user] WHERE role_id IN (1, 3, 4, 5)")
        staff = cursor.fetchone()[0]
        return total_clients, pending, staff

@st.cache_data(ttl=600, max_entries=10)
def cached_get_users(is_staff: bool):
    return get_users_by_role_category(is_staff=is_staff)

@st.cache_data(ttl=300, max_entries=10)
def get_user_actions(user_id: int):
    query = "SELECT DISTINCT [action] FROM [audit_log] WHERE [user_id] = ?"
    with get_cursor() as cursor:
        cursor.execute(query, (user_id,))
        return [row[0] for row in cursor.fetchall() if row[0]]

def _fetch_audit_logs(user_id: int, limit, start_date, end_date, action_type: str):
    top_clause = f"TOP {limit}" if limit else ""
    query = f"SELECT {top_clause} l.[Id_log], l.[action], l.[details], l.[created_at] FROM [audit_log] l WHERE l.[user_id] = ?"
    params = [user_id]
    
    if start_date and end_date:
        query += " AND l.[created_at] BETWEEN ? AND ?"
        import datetime
        dt_start = datetime.datetime.combine(start_date, datetime.time.min)
        dt_end = datetime.datetime.combine(end_date, datetime.time.max)
        params.extend([dt_start, dt_end])
        
    if action_type != "Todas":
        query += " AND l.[action] = ?"
        params.append(action_type)
        
    query += " ORDER BY l.[created_at] DESC"
    
    with get_cursor() as cursor:
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [list(row) for row in rows if row is not None and len(row) == 4]

@st.cache_data(ttl=300, max_entries=20)
def _cached_fetch_audit_logs(user_id: int, start_date, end_date, action_type: str):
    return _fetch_audit_logs(user_id, 50, start_date, end_date, action_type)

def get_filtered_audit_logs(user_id: int, limit, start_date, end_date, action_type: str):
    if limit == 50:
        return _cached_fetch_audit_logs(user_id, start_date, end_date, action_type)
    return _fetch_audit_logs(user_id, limit, start_date, end_date, action_type)

# --- GLOBAL PAGINATORS FOR ADMIN & AUDITOR TABS ---

def _fetch_approval_history(limit):
    top_clause = f"TOP {limit}" if limit else ""
    query = f"""
        SELECT {top_clause}
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
        cursor.execute(query)
        rows = cursor.fetchall()
        return [list(row) for row in rows if row is not None and len(row) == 11]

@st.cache_data(ttl=300, max_entries=1)
def _cached_fetch_approval_history():
    return _fetch_approval_history(50)
    
def get_filtered_approval_history(limit):
    if limit == 50:
        return _cached_fetch_approval_history()
    return _fetch_approval_history(limit)


def _fetch_auditor_admin_logs(limit):
    top_clause = f"TOP {limit}" if limit else ""
    query = f"""
        SELECT {top_clause}
            l.[Id_log],
            u.[full_name],
            l.[action],
            l.[details],
            l.[created_at]
        FROM [audit_log] l
        INNER JOIN [user] u ON l.user_id = u.Id_user
        ORDER BY l.[created_at] DESC
    """
    with get_cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        return [list(row) for row in rows if row is not None and len(row) == 5]

@st.cache_data(ttl=300, max_entries=1)
def _cached_fetch_auditor_admin_logs():
    return _fetch_auditor_admin_logs(50)

def get_filtered_auditor_admin_logs(limit):
    if limit == 50:
        return _cached_fetch_auditor_admin_logs()
    return _fetch_auditor_admin_logs(limit)


def _fetch_auditor_transactions(limit):
    top_clause = f"TOP {limit}" if limit else ""
    query = f"""
        SELECT {top_clause}
            t.[Id_transaction],
            t.[transaction_type_id],
            t.[status_id],
            t.[description],
            t.[created_by_user_id],
            u.[full_name],
            t.[transaction_date],
            t.[processed_at]
        FROM [transaction] t
        INNER JOIN [user] u ON t.created_by_user_id = u.Id_user
        ORDER BY t.[transaction_date] DESC
    """
    with get_cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        return [list(row) for row in rows if row is not None and len(row) == 8]
        
@st.cache_data(ttl=300, max_entries=1)
def _cached_fetch_auditor_transactions():
    return _fetch_auditor_transactions(50)

def get_filtered_auditor_transactions(limit):
    if limit == 50:
        return _cached_fetch_auditor_transactions()
    return _fetch_auditor_transactions(limit)

if role_id == 3:
    total_clients, pending_count, staff_count = get_admin_kpis()

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
    with col_m1:
        with st.container(border=True):
            st.metric("👥 Clientes Totales", f"{total_clients}", help="Usuarios registrados con rol de Cliente")
    with col_m2:
        with st.container(border=True):
            st.metric("⏳ Aprobaciones Pendientes", f"{pending_count}", delta=f"{pending_count} TX", delta_color="inverse")
    with col_m3:
        with st.container(border=True):
            st.metric("🏢 Personal Synapse", f"{staff_count}")
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
        staff_users = cached_get_users(is_staff=True)
        if staff_users:
            df_staff = pd.DataFrame(staff_users)
            df_staff = df_staff[['Id_user', 'full_name', 'email', 'role_id', 'is_active']]
            # Map roles
            role_map = {1: "Cajero", 3: "Admin", 4: "Analista", 5: "Auditor"}
            df_staff['Rol'] = df_staff['role_id'].map(role_map)
            st.dataframe(df_staff, hide_index=True, use_container_width=True)
        else:
            st.info("No hay personal registrado.")

    # --- TAB 2: GESTIÓN DE CLIENTES ---
    with tab2:
        st.header("Gestión de Cuentas de Clientes")
        st.info("Nota: Los administradores pueden gestionar clientes existentes pero no crearlos.")

        clients = cached_get_users(is_staff=False)
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
        clients_for_control = cached_get_users(is_staff=False)
        
        if clients_for_control:
            search_control = st.text_input("🔍 Buscar cliente por nombre o correo", key="search_ctrl").lower()
            if search_control:
                clients_for_control = [c for c in clients_for_control if search_control in c['full_name'].lower() or search_control in c['email'].lower()]
            
            for client in clients_for_control:
                with st.expander(f"👤 {client['full_name']} | ✉️ {client['email']}"):
                    # 1. Obtener y renderizar la Cuenta
                    accounts = get_accounts_by_user(client["Id_user"])
                    accounts = [
                        acc for acc in accounts
                        if (acc.get("status_id", acc[4] if isinstance(acc, tuple) else None)) in [1,2,3]
                        ]

                    
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

        if "show_all_approvals" not in st.session_state:
            st.session_state.show_all_approvals = False

        limit_app = None if st.session_state.show_all_approvals else 50

        try:
            if limit_app is None:
                with st.spinner("Cargando historial completo de aprobaciones..."):
                    movimientos = get_filtered_approval_history(limit_app)
            else:
                movimientos = get_filtered_approval_history(limit_app)
        except Exception as e:
            st.error(f"Error cargando aprobaciones: {e}")
            movimientos = []

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
            
            st.divider()
            if limit_app == 50 and len(movimientos) == 50:
                if st.button("📂 Mostrar todo el historial de Aprobaciones", key="btn_show_all_approvals"):
                    st.session_state.show_all_approvals = True
                    st.rerun()
            elif limit_app is None:
                if st.button("🔽 Volver a los 50 más recientes", key="btn_show_last_approvals"):
                    st.session_state.show_all_approvals = False
                    st.rerun()
        else:
            st.info("No hay historial de revisiones disponible.")


    # --- TAB 6: CONFIGURACIÓN ---
        with tab6:
            st.header("⚙️ Configuración")
            st.subheader("📜 Historial de Tus Acciones Administrativas")

            import datetime
            u_id = int(st.session_state['user_data']['Id_user'])
            
            with st.container(border=True):
                st.markdown("#### 🔍 Filtros de Búsqueda")
                col_f1, col_f2 = st.columns(2)
                
                try:
                    acciones_unicas = get_user_actions(u_id)
                except Exception:
                    acciones_unicas = []
                acciones = ["Todas"] + sorted(acciones_unicas)
                
                with col_f1:
                    action_filter = st.selectbox("⚙️ Tipo de acción", acciones, key="filter_tab6_final")
                
                with col_f2:
                    default_end = datetime.date.today()
                    default_start = default_end - datetime.timedelta(days=30)
                    date_range = st.date_input("📅 Rango de Fechas", value=(default_start, default_end), key="date_tab6")
                    
            start_date, end_date = None, None
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
                
            st.divider()

            if "show_all_logs" not in st.session_state:
                st.session_state.show_all_logs = False

            limit = None if st.session_state.show_all_logs else 50
            
            try:
                if limit is None:
                    with st.spinner("Cargando historial completo..."):
                        logs_validados = get_filtered_audit_logs(u_id, limit, start_date, end_date, action_filter)
                else:
                    logs_validados = get_filtered_audit_logs(u_id, limit, start_date, end_date, action_filter)

                if logs_validados:
                    df_logs = pd.DataFrame(logs_validados, columns=["ID", "Acción", "Detalles", "Fecha"])
                    df_logs["Fecha"] = pd.to_datetime(df_logs["Fecha"])

                    st.dataframe(
                        df_logs.sort_values(by="Fecha", ascending=False),
                        height=450,
                        hide_index=True,
                        use_container_width=True
                    )
                    st.caption(f"Mostrando {len(df_logs)} acciones registradas.")
                    
                    if limit == 50 and len(df_logs) == 50:
                        if st.button("📂 Mostrar todos los registros de esta búsqueda"):
                            st.session_state.show_all_logs = True
                            st.rerun()
                    elif limit is None:
                        if st.button("🔽 Volver a los 50 más recientes"):
                            st.session_state.show_all_logs = False
                            st.rerun()
                else:
                    st.info("No se encontraron registros con los filtros seleccionados.")
                    
            except Exception as e:
                st.error(f"Error de base de datos: {str(e)}")
                
#--------------------------------------------------
# PANEL CAJERO 
# -------------------------------------------------
elif role_id == 1:
    st.header("Panel Operativo - Cajero")
    st.info("Buscador de Cuentas y Procesamiento de Transacciones rápidos.")

    # -------------------------------------------------
    # SOLICITUDES DE APERTURA DE CUENTA
    # -------------------------------------------------

    from models.account_model import (
        get_pending_accounts,
        approve_account,
        reject_account,
        get_account_by_number
    )

    from services.transaction_service import create_simple_transaction
    from models.card_model import get_pending_renewals, finalize_card_renewal
    from services.audit_service import log_action

    st.subheader("📋 Solicitudes de Apertura de Cuenta")

    # BOTÓN PARA APROBAR TODAS
    if st.button("⚡ Aprobar todas las solicitudes pendientes"):

        pending_accounts = get_pending_accounts()

        if not pending_accounts:
            st.info("No hay cuentas pendientes para aprobar.")

        else:
            for acc in pending_accounts:

                approve_account(acc['Id_account'])

                log_action(
                    st.session_state['user_data']['Id_user'],
                    "APROBAR_CUENTA",
                    f"Aprobación automática de cuenta {acc['account_number']}"
                )

            st.success(f"{len(pending_accounts)} cuentas aprobadas automáticamente.")

            time.sleep(1)

            st.rerun()

    pending_accounts = get_pending_accounts()

    if not pending_accounts:
        st.info("No hay solicitudes pendientes.")

    else:
        for acc in pending_accounts:

            with st.container(border=True):

                c1, c2, c3 = st.columns([2,2,1])

                with c1:
                    st.markdown(f"**Cuenta:** {acc['account_number']}")
                    st.caption(f"ID Cuenta: {acc['Id_account']}")

                with c2:
                    st.markdown(f"**Usuario ID:** {acc['user_id']}")
                    st.caption("Estado: Pendiente de aprobación")

                with c3:

                    if st.button("✅ Aprobar", key=f"approve_{acc['Id_account']}"):

                        log_action(
                            st.session_state['user_data']['Id_user'],
                            "APROBAR_CUENTA",
                            f"Cajero aprobó la cuenta {acc['account_number']}"
                        )
                        
                        approve_account(acc['Id_account'])

                        st.success("Cuenta aprobada")

                        time.sleep(1)

                        st.rerun()

                    if st.button("❌ Rechazar", key=f"reject_{acc['Id_account']}"):

                        reject_account(acc['Id_account'])

                        log_action(
                            st.session_state['user_data']['Id_user'],
                            "RECHAZAR_CUENTA",
                            f"Cajero rechazó la cuenta {acc['account_number']}"
                        )

                        st.error("Cuenta rechazada")

                        time.sleep(1)

                        st.rerun()

    st.divider()


    # -------------------------------------------------
    # BUSCADOR DE CUENTAS
    # -------------------------------------------------

    search_acc = st.text_input("🔍 Buscar Cuenta por Número (Ej. SV_synapse...)")
    
    if search_acc:
        acc_data = get_account_by_number(search_acc)

        if acc_data:
            acc_id = acc_data[0] if isinstance(acc_data, (list, tuple)) else acc_data.get('Id_account')
            acc_status = acc_data[4] if isinstance(acc_data, (list, tuple)) else acc_data.get("status_id")
            if acc_status != 1:
                st.error("⚠️ Esta cuenta no está activa. No se pueden realizar operaciones.")
                st.stop()

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

                            log_action(
                                st.session_state['user_data']['Id_user'],
                                "TRANSACCION",
                                f"{tx_type} de ${tx_amount} en cuenta {search_acc}"
                            )

                            st.success(msg)

                        else:
                            st.error(res.get('error'))

        else:
            st.error("Cuenta no encontrada.")
            
    st.divider()

    # -------------------------------------------------
    # ENTREGA DE TARJETAS RENOVADAS
    # -------------------------------------------------

    st.subheader("💳 Entrega de Renovaciones de Tarjeta")
    
    renewals = get_pending_renewals()

    if not renewals:
        st.info("No hay tarjetas pendientes de entrega por renovación.")

    else:
        for r in renewals:

            with st.container(border=True):

                c1, c2, c3 = st.columns([1.5, 2, 1])

                with c1:
                    st.markdown(f"**Cliente:** {r['full_name']}")
                    st.caption(f"DUI: {r['DUI']}")

                with c2:
                    st.markdown(f"**Tarjeta (****{r['card_number_last4']})**")
                    st.caption(
                        f"Cuenta: {r['account_number']} | "
                        f"Solicitado: {r['requested_at'].strftime('%d/%m/%Y %H:%M') if r['requested_at'] else 'N/A'}"
                    )

                with c3:
                    st.markdown('<div class="btn-success">', unsafe_allow_html=True)

                    if st.button(
                        "Confirmar Identidad y Entregar",
                        key=f"btn_delivery_{r['Id_renewal']}",
                        type="primary"
                    ):

                        try:

                            if finalize_card_renewal(
                                r['Id_renewal'],
                                r['card_id'],
                                st.session_state['user_data']['Id_user']
                            ):

                                log_action(
                                    st.session_state['user_data']['Id_user'],
                                    "ENTREGA_TARJETA",
                                    f"Entrega de tarjeta terminada ****{r['card_number_last4']}"
                                )

                                st.success("¡Tarjeta renovada y activada exitosamente!")

                                time.sleep(2)

                                st.rerun()

                        except Exception as e:
                            st.error(f"Error en entrega: {e}")

                    st.markdown('</div>', unsafe_allow_html=True)

elif role_id == 4:
    st.header("📊 Panel de Métricas - Analista Financiero")
    st.write("Vista de solo lectura orientada a la toma de decisiones estratégicas.")

    from services.rbac_service import execute_analyst_query
    import pandas as pd
    import altair as alt
    from datetime import datetime, timedelta

    # --- INICIALIZACIÓN DE VARIABLES (Evita errores si no hay datos) ---
    df_flujo = pd.DataFrame()
    df_tipos = pd.DataFrame()
    df_hist = pd.DataFrame()

    # --- SECCIÓN DE FILTROS ---
    with st.container():
        st.subheader("📅 Filtros de Consulta")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            start_date = st.date_input("Fecha Inicio", datetime.now() - timedelta(days=30))
        with col_f2:
            end_date = st.date_input("Fecha Fin", datetime.now())

    res = execute_analyst_query()

    if res.get('status') == 200:
        data = res.get('data', {}) # Usamos .get() para evitar KeyError
        
        # --- 1. PROCESAMIENTO DE DATOS ---
        if data.get('flujo'):
            df_flujo = pd.DataFrame(data['flujo'])
            
        if data.get('tipos'):
            df_tipos = pd.DataFrame(data['tipos'])

        # --- 2. KPIs DE CABECERA ---
        if not df_flujo.empty:
            total_credit = df_flujo[df_flujo['entry_type'] == 'credit']['total'].sum()
            total_debit = df_flujo[df_flujo['entry_type'] == 'debit']['total'].sum()
            balance = total_credit - total_debit

            st.caption(f"Resumen del periodo: {start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}")
            m1, m2, m3 = st.columns(3)
            m1.metric("Ingresos Globales", f"${total_credit:,.2f}")
            m2.metric("Egresos Globales", f"${total_debit:,.2f}")
            m3.metric("Balance Neto", f"${balance:,.2f}", delta=f"{balance:,.2f}")
        
        st.divider()

        # --- 3. FILA 1: GRÁFICOS DE BARRAS ---
        col_a1, col_a2 = st.columns([1.2, 1])

        with col_a1:
            st.subheader("💰 Flujo de Caja")
            if not df_flujo.empty:
                chart_flujo = alt.Chart(df_flujo).mark_bar(cornerRadiusTopLeft=10).encode(
                    x=alt.X('entry_type:N', title="Tipo"),
                    y=alt.Y('total:Q', title="Monto ($)"),
                    color=alt.Color('entry_type:N', scale=alt.Scale(range=['#1E88E5', '#E53935']), legend=None)
                ).properties(height=300)
                st.altair_chart(chart_flujo, use_container_width=True)
            else:
                st.info("No hay datos de flujo para mostrar.")

        with col_a2:
            st.subheader("📈 Cantidad por Operación")
            if not df_tipos.empty:
                chart_tipos = alt.Chart(df_tipos).mark_bar(color='#26A69A').encode(
                    x=alt.X('count:Q', title="Cantidad"),
                    y=alt.Y('name:N', title="Operación", sort='-x')
                ).properties(height=300)
                st.altair_chart(chart_tipos, use_container_width=True)
            else:
                st.info("No hay datos de operaciones.")

        st.divider()

        # --- 4. FILA 2: TENDENCIA Y COMPOSICIÓN ---
        col_b1, col_b2 = st.columns(2)


        with col_b2:
            st.subheader("🍩 Mix de Productos")
            if not df_tipos.empty:
                chart_donut = alt.Chart(df_tipos).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta(field="count", type="quantitative"),
                    color=alt.Color(field="name", type="nominal", title="Producto"),
                ).properties(height=300)
                st.altair_chart(chart_donut, use_container_width=True)

        with col_b1:
            st.subheader("🕒 Evolución Temporal")
            
            historico = data.get('historico')
            
            if historico:
                # Si el backend ya tiene los datos, los usamos
                df_hist = pd.DataFrame(historico)
            else:
                # SIMULACIÓN PROFESIONAL: Si no hay datos, creamos una serie temporal de prueba
                # Esto sirve para mostrar la funcionalidad en la etapa de planificación
                date_range = pd.date_range(start=start_date, end=end_date)
                import numpy as np
                df_hist = pd.DataFrame({
                    'fecha': date_range,
                    'cantidad': np.random.randint(5, 50, size=len(date_range)) # Genera números aleatorios entre 5 y 50
                })
                st.caption("⚠️ Nota: Visualizando datos simulados (Tendencia proyectada).")

            # Gráfico de Líneas con Área (se ve más profesional)
            chart_evolucion = alt.Chart(df_hist).mark_area(
                line={'color':'#FF9800'},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='white', offset=0),
                           alt.GradientStop(color='#FF9800', offset=1)],
                    x1=1, x2=1, y1=1, y2=0
                )
            ).encode(
                x=alt.X('fecha:T', title="Línea de Tiempo"),
                y=alt.Y('cantidad:Q', title="N° de Operaciones"),
                tooltip=[alt.Tooltip('fecha:T', title='Fecha'), alt.Tooltip('cantidad:Q', title='Transacciones')]
            ).properties(height=300).interactive()
            
            st.altair_chart(chart_evolucion, use_container_width=True)

        # --- 5. DETALLE TABULAR (SEGURO) ---
        with st.expander("📂 Explorar registros detallados"):
            if not df_tipos.empty:
                st.dataframe(df_tipos, hide_index=True, use_container_width=True)
            else:
                st.write("No hay registros para mostrar en la tabla.")

    else:
        st.error(f"Error de conexión: {res.get('error', 'No se pudo obtener respuesta del servidor.')}")

import streamlit as st
import pandas as pd
from services.audit_service import log_action
from config.database import get_cursor
import datetime

if role_id == 5:
    st.header("Control de Riesgos - Auditor")
    st.write("Historial Detallado de Operaciones del Sistema. (Solo Lectura)")

    tab_admin, tab_ops = st.tabs(["Historial Administrativo", "Historial de Transacciones"])

    # --- TAB 1: Historial Administrativo ---
    with tab_admin:
        st.subheader("📜 Acciones de Personal y Configuración")

        if "show_all_audit_admin" not in st.session_state:
            st.session_state.show_all_audit_admin = False

        limit_admin = None if st.session_state.show_all_audit_admin else 50

        try:
            if limit_admin is None:
                with st.spinner("Cargando historial administrativo completo..."):
                    rows = get_filtered_auditor_admin_logs(limit_admin)
            else:
                rows = get_filtered_auditor_admin_logs(limit_admin)
                
            if rows:
                    # Crear DataFrame seguro
                    df_admin = pd.DataFrame.from_records(
                        rows,
                        columns=["ID", "Administrador", "Acción", "Detalles", "Fecha"]
                    )
                    df_admin['Fecha'] = pd.to_datetime(df_admin['Fecha'])

                    # --- FILTRO POR ACCIÓN (con "Todos") ---
                    acciones_unicas = sorted(df_admin['Acción'].dropna().unique().tolist())
                    selected_accion = st.selectbox(
                        "Filtrado por acción",
                        ["Todos"] + acciones_unicas,
                        key="filter_accion_admin"
                    )
                    if selected_accion != "Todos":
                        df_admin = df_admin[df_admin['Acción'] == selected_accion]

                    # --- FILTRO POR ADMINISTRADOR ---
                    search_admin = st.text_input(
                        "🔎 Filtrado por Administrador",
                        key="search_admin_audit"
                    )
                    if search_admin:
                        df_admin = df_admin[
                            df_admin['Administrador'].str.contains(search_admin, case=False, na=False)
                        ]

                    # --- FILTRO OPCIONAL POR MES Y AÑO ---
                    use_date_filter = st.checkbox(
                        "Activar filtro por mes y año",
                        key="enable_date_filter_admin"
                    )
                    if use_date_filter:
                        months = list(range(1, 13))
                        years = list(range(df_admin['Fecha'].dt.year.min(), df_admin['Fecha'].dt.year.max() + 1))
                        col1, col2 = st.columns(2)
                        with col1:
                            selected_month = st.selectbox(
                                "📅 Mes", months, index=datetime.datetime.now().month - 1, key="month_admin"
                            )
                        with col2:
                            selected_year = st.selectbox(
                                "📅 Año", years, index=len(years) - 1, key="year_admin"
                            )
                        df_admin = df_admin[
                            (df_admin['Fecha'].dt.month == selected_month) &
                            (df_admin['Fecha'].dt.year == selected_year)
                        ]

                    st.dataframe(df_admin, height=450, hide_index=True, use_container_width=True)
                    st.caption(f"Mostrando {len(df_admin)} registros del historial administrativo.")
                    
                    if limit_admin == 50 and len(df_admin) == 50:
                        if st.button("📂 Mostrar todos los registros administrativos", key="btn_show_all_audit_admin"):
                            st.session_state.show_all_audit_admin = True
                            st.rerun()
                    elif limit_admin is None:
                        if st.button("🔽 Volver a los 50 más recientes", key="btn_show_last_audit_admin"):
                            st.session_state.show_all_audit_admin = False
                            st.rerun()
            else:
                st.info("No hay registros en el registro de auditoría.")
        except Exception as e:
            st.error(f"Error al cargar historial administrativo: {e}")

    # --- TAB 2: Historial de Transacciones ---
    with tab_ops:
        st.subheader("📜 Movimientos y Transacciones")

        if "show_all_audit_trans" not in st.session_state:
            st.session_state.show_all_audit_trans = False

        limit_trans = None if st.session_state.show_all_audit_trans else 50

        try:
            if limit_trans is None:
                with st.spinner("Cargando transacciones completas..."):
                    rows = get_filtered_auditor_transactions(limit_trans)
            else:
                rows = get_filtered_auditor_transactions(limit_trans)

            if rows:
                    columns = [
                        "ID Transacción", "Tipo_ID", "Status_ID", "Descripción",
                        "ID Usuario", "Usuario", "Fecha Creación", "Procesado En"
                    ]
                    df_trans = pd.DataFrame.from_records(rows, columns=columns)
                    df_trans['Fecha Creación'] = pd.to_datetime(df_trans['Fecha Creación'])
                    df_trans['Procesado En'] = pd.to_datetime(df_trans['Procesado En'])

                    # --- MAPEO TIPO DE TRANSACCIÓN ---
                    tipo_dict = {1: "Transferencia", 2: "Retiro", 3: "Depósito", 4: "Pago"}
                    df_trans['Tipo Nombre'] = df_trans['Tipo_ID'].map(tipo_dict).fillna("Desconocido")

                    # --- FILTROS ---
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        search_user = st.text_input("🔎 Filtrar por Usuario", key="search_user_trans")
                    with col_f2:
                        tipo_options = ["Todos"] + list(tipo_dict.values())
                        selected_tipo = st.selectbox("Filtrar por tipo de transacción", tipo_options, key="filter_tipo_trans")

                    # Filtro opcional por Mes y Año
                    use_date_filter = st.checkbox("📅 Activar filtro por mes y año", key="enable_date_filter_trans")

                    df_filtered = df_trans.copy()
                    if search_user:
                        df_filtered = df_filtered[df_filtered['Usuario'].str.contains(search_user, case=False, na=False)]
                    if selected_tipo != "Todos":
                        df_filtered = df_filtered[df_filtered['Tipo Nombre'] == selected_tipo]
                    if use_date_filter:
                        available_years = sorted(df_filtered['Fecha Creación'].dt.year.unique().tolist(), reverse=True)
                        if not available_years:
                            available_years = [datetime.datetime.now().year]
                        c1, c2 = st.columns(2)
                        with c1:
                            sel_month = st.selectbox("Mes", list(range(1, 13)), index=datetime.datetime.now().month - 1, key="m_trans")
                        with c2:
                            sel_year = st.selectbox("Año", available_years, key="y_trans")
                        df_filtered = df_filtered[
                            (df_filtered['Fecha Creación'].dt.month == sel_month) &
                            (df_filtered['Fecha Creación'].dt.year == sel_year)
                        ]

                    display_cols = [
                        "ID Transacción", "Usuario", "Tipo Nombre", "Descripción",
                        "Fecha Creación", "Procesado En", "Status_ID"
                    ]
                    st.dataframe(df_filtered[display_cols], height=450, hide_index=True, use_container_width=True)
                    st.caption(f"Mostrando {len(df_filtered)} transacciones encontradas.")
                    
                    if limit_trans == 50 and len(df_filtered) == 50:
                        if st.button("📂 Mostrar todas las transacciones", key="btn_show_all_audit_trans"):
                            st.session_state.show_all_audit_trans = True
                            st.rerun()
                    elif limit_trans is None:
                        if st.button("🔽 Volver a los 50 más recientes", key="btn_show_last_audit_trans"):
                            st.session_state.show_all_audit_trans = False
                            st.rerun()
            else:
                st.info("No se encontraron registros de transacciones.")
        except Exception as e:
            st.error(f"Error crítico al cargar historial de transacciones: {e}")

            