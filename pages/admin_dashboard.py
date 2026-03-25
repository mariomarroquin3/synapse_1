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
from models.account_model import get_accounts_by_user, update_account_status, get_accounts_by_user_ids
from models.card_model import get_cards_by_account, update_card_status, get_cards_by_account_ids
from services.user_service import register_user_with_permissions
from services.transaction_service import review_transaction
from config.database import get_cursor
from utils.ui_components import apply_premium_style
from models.account_model import get_pending_accounts, approve_account, reject_account
from card_print.audit_pdf import generar_pdf_auditoria


# ─────────────────────────────────────────────
# VALIDACIÓN DE DUI (Formato Salvadoreño)
# ─────────────────────────────────────────────
def validate_dui(dui: str) -> bool:
    """
    Valida que el DUI tenga exactamente 9 dígitos numéricos, 
    permitiendo que el usuario ingrese o no el guion.
    """
    if not dui:
        return False
        
    # Eliminamos cualquier carácter que no sea un número (guiones, espacios, letras)
    dui_limpio = re.sub(r'\D', '', dui) 
    
    # Validamos que el resultado sean exactamente 9 números
    return len(dui_limpio) == 9


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
    total_clients, pending, staff_count = get_admin_kpis()

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
            st.metric("⏳ Aprobaciones Pendientes", f"{pending}", delta=f"{pending} TX", delta_color="inverse")
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
        with st.expander("➕ Registrar nuevo miembro del personal."):
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
                    elif not validate_dui(s_dui):
                        st.error("⚠️ DUI inválido. El formato requerido es: 00000000-0 (8 dígitos, guion, 1 dígito verificador). Solo se permiten números.")
                    else:
                        user_data = {
                            "role_id": s_role[0],
                            "email": s_email,
                            "password": s_pass,
                            "dui": s_dui.strip(),
                            "full_name": s_name,
                            "gender": s_gen[0],
                            "phone_number": f"+503 {s_phone[:4]}-{s_phone[4:]}" if len(s_phone) == 8 else s_phone
                        }

                        res = register_user_with_permissions(
                            st.session_state["user_data"]["Id_user"], 
                            user_data
                        )

                        if res["success"]:
                           
                            new_user_id = res.get("user_id", "N/A")

                          
                            log_action(
                                st.session_state["user_data"]["Id_user"],  
                                12,  
                                f"Se incorporó un {s_role[1]}: {s_name} (ID: {new_user_id})"
                            )

                            st.success(f"✅ Usuario {s_role[1]} **{s_name}** creado exitosamente.")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"Error: {res['error']}")

        # Listar Personal
        staff_users = cached_get_users(is_staff=True)
        if staff_users:
            df_staff = pd.DataFrame(staff_users)
            df_staff = df_staff[['Id_user', 'full_name', 'email', 'role_id', 'is_active']]
            role_map = {1: "Cajero", 3: "Admin", 4: "Analista", 5: "Auditor"}
            df_staff['Rol'] = df_staff['role_id'].map(role_map)
            st.dataframe(df_staff, hide_index=True, use_container_width=True)
        else:
            st.info("No hay personal registrado.")



    # --- TAB 2: GESTIÓN DE CLIENTES ---
    with tab2:
        st.header("Gestión de Usuarios")
        st.write("Gestiona el estado de los usuarios (Clientes y Personal con Cuentas).")

        tab2_clientes, tab2_personal_con_cuentas = st.tabs(["👥 Clientes", "🏢 Personal con Cuentas"])

        def render_user_list(user_list, search_query_val, is_staff_check=False):
            if search_query_val:
                user_list = [c for c in user_list if search_query_val in c['full_name'].lower() or search_query_val in c['email'].lower()]
            
            if is_staff_check:
                u_ids = [u['Id_user'] for u in user_list]
                all_staff_accs = get_accounts_by_user_ids(u_ids)
                users_with_acc_ids = {a['user_id'] for a in all_staff_accs}
                user_list = [u for u in user_list if u['Id_user'] in users_with_acc_ids]

            if not user_list:
                st.info("No se encontraron usuarios en esta categoría.")
                return

            tab_activos, tab_suspendidos = st.tabs(["✅ Activos", "🚫 Suspendidos"])
            
            def render_sub_list(sub_list):
                if not sub_list:
                    st.info("No hay usuarios aquí.")
                    return
                for usr in sub_list:
                    with st.container():
                        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                        status_text = "Activo" if usr['is_active'] else "Suspendido"
                        status_class = "status-active" if usr['is_active'] else "status-suspended"
                        c1.write(f"**{usr['full_name']}**")
                        c2.write(usr['email'])
                        c3.markdown(f"<span class='{status_class}'>{status_text}</span>", unsafe_allow_html=True)
                        btn_label = "Suspender" if usr['is_active'] else "Activar"

                        if c4.button(btn_label, key=f"user_st_{usr['Id_user']}"):
                            nuevo_estado = not usr['is_active']

                            if update_user_status(usr['Id_user'], nuevo_estado):
                                admin_id = st.session_state.get('user_data', {}).get('Id_user')

                                if admin_id:
                                    estado_anterior = "Activo" if usr['is_active'] else "Suspendido"
                                    estado_nuevo = "Activo" if nuevo_estado else "Suspendido"

                                    log_action(
                                        user_id=int(admin_id),
                                        action="3",
                                        details=f" ({usr['email']}) cambio a {estado_nuevo}"
                                    )

                                st.cache_data.clear()
                                st.success(f"Estado de {usr['full_name']} actualizado.")
                                st.rerun()

                    st.divider()

            with tab_activos:
                render_sub_list([u for u in user_list if u['is_active']])
            with tab_suspendidos:
                render_sub_list([u for u in user_list if not u['is_active']])

        with tab2_clientes:
            st.subheader("Gestión de Clientes Regulares")
            clients_all = cached_get_users(is_staff=False)
            search_q_cli = st.text_input("🔍 Buscar cliente", key="search_q_cli").lower()
            render_user_list(clients_all if clients_all else [], search_q_cli, is_staff_check=False)

        with tab2_personal_con_cuentas:
            st.subheader("Gestión de Personal con Cuentas de Banco")
            staff_all = cached_get_users(is_staff=True)
            search_q_stf = st.text_input("🔍 Buscar personal", key="search_q_stf").lower()
            render_user_list(staff_all if staff_all else [], search_q_stf, is_staff_check=True)

# --- TAB 3: CONTROL DE CUENTAS Y TARJETAS ---
    with tab3:
        st.header("Control de Cuentas y Tarjetas")
        st.write("Gestiona el estado operativo (Activa, Bloqueada, Suspendida, Pendiente, Rechazada) de las cuentas y tarjetas.")

        tab3_clientes, tab3_personal = st.tabs(["👥 Cuentas de Clientes", "🏢 Cuentas de Personal"])

        def render_account_controls(user_list, search_query_val, is_staff_control=False, estado_filtro="Todas"):
            # 1. Filtrado por búsqueda de texto
            if search_query_val:
                user_list = [
                    c for c in user_list
                    if search_query_val in c['full_name'].lower()
                    or search_query_val in c['email'].lower()
                ]
                
            if not user_list:
                st.info("No hay usuarios en esta categoría.")
                return 

            # 2. Obtener TODAS las cuentas de estos usuarios para las métricas
            u_ids = [u['Id_user'] for u in user_list]
            all_accounts = get_accounts_by_user_ids(u_ids)
            
            if not all_accounts:
                st.info("No hay cuentas registradas.")
                return

            # --- MÉTRICAS (Siempre visibles con los 5 estados) ---
            t_act = sum(1 for acc in all_accounts if acc.get("status_id") == 1)
            t_blo = sum(1 for acc in all_accounts if acc.get("status_id") == 2)
            t_sus = sum(1 for acc in all_accounts if acc.get("status_id") == 3)
            t_pen = sum(1 for acc in all_accounts if acc.get("status_id") == 4)
            t_rec = sum(1 for acc in all_accounts if acc.get("status_id") == 5)
            
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("✅ Activas", t_act)
            m2.metric("⚠️ Bloqueadas", t_blo)
            m3.metric("🚫 Suspendidas", t_sus)
            m4.metric("⏳ Pendientes", t_pen)
            m5.metric("❌ Rechazadas", t_rec)
            st.divider()

            # 3. Filtrar cuentas según el selector de estado
            accounts_to_show = all_accounts
            if estado_filtro != "Todas":
                status_map = {
                    "Activas": 1, "Bloqueadas": 2, "Suspendidas": 3, 
                    "Pendientes": 4, "Rechazadas": 5
                }
                target_id = status_map.get(estado_filtro)
                accounts_to_show = [a for a in all_accounts if a.get("status_id") == target_id]

            if not accounts_to_show:
                st.warning(f"No hay cuentas con estado: {estado_filtro}")
                return

            # 4. Agrupar datos para la interfaz
            accs_by_user = {}
            for acc in accounts_to_show:
                accs_by_user.setdefault(acc['user_id'], []).append(acc)

            # Obtener tarjetas de las cuentas filtradas
            acc_ids = [acc['Id_account'] for acc in accounts_to_show]
            all_cards = get_cards_by_account_ids(acc_ids) if acc_ids else []
            cards_by_acc = {}
            for card in all_cards:
                cards_by_acc.setdefault(card['account_id'], []).append(card)

            prefix = "stf" if is_staff_control else "cli"

            # 5. Renderizado de Usuarios y sus Cuentas
            status_options = [1, 2, 3, 4, 5]
            status_names = {
                1: "✅ Activa",
                2: "⚠️ Bloqueada",
                3: "🚫 Suspendida",
                4: "⏳ Pendiente",
                5: "❌ Rechazada"
            }

            for user in user_list:
                if user["Id_user"] not in accs_by_user:
                    continue
                
                with st.expander(f"👤 {user['full_name']} | {user['email']}"):
                    for account in accs_by_user[user["Id_user"]]:
                        ac_id = account['Id_account']
                        ac_num = account.get("account_number", "N/A")
                        ac_status = account.get("status_id", 1)
                        
                        # Colores de estado (Añadido azul para pendiente y gris para rechazada)
                        colors = {
                            1: ("Activa", "#16a34a"), 
                            2: ("Bloqueada", "#f59e0b"), 
                            3: ("Suspendida", "#ef4444"),
                            4: ("Pendiente", "#3b82f6"),
                            5: ("Rechazada", "#6b7280")
                        }
                        s_name, s_col = colors.get(ac_status, ("Desconocido", "gray"))

                        c_top1, c_top2 = st.columns([2, 1])
                        with c_top1:
                            st.write(f"**Cuenta:** `{ac_num}`")
                            st.markdown(f"<span style='color:{s_col}; font-weight:bold;'>{s_name}</span>", unsafe_allow_html=True)

                        # --- Dentro de render_account_controls en admin_dashboard.py ---

                        with c_top2:
                            if ac_status in [4, 5]:
                                st.selectbox(
                                    "Cambiar", options=[ac_status], 
                                    format_func=lambda x: status_names.get(x), 
                                    key=f"sel_{prefix}_acc_{ac_id}_disabled", # Clave más específica
                                    disabled=True
                                      )
                                
                            else:
                                
                            
                                new_st = st.selectbox(
                                    "Cambiar", options=[1, 2, 3], 
                                    index=[1, 2, 3].index(ac_status),
                                    format_func=lambda x: status_names.get(x),
                                    key=f"sel_{prefix}_acc_{ac_id}"
                                )
                                if new_st != ac_status:
                                    if update_account_status(ac_id, new_st):
                                        # 🛡️ USAMOS TU CLAVE 
                                        admin_id = st.session_state.get('user_data', {}).get('Id_user')
                                        
                                        if admin_id:
                                            # Buscamos el nombre del estado (Activa, Bloqueada, etc.)
                                            nombre_estado = status_names.get(new_st, "Desconocido")
                                            
                                            # 🚀 Lanzamos el log
                                            log_action(
                                                user_id=int(admin_id),
                                                action="4",
                                                details=f"Admin cambió estado de la cuenta {ac_num} a {nombre_estado}"
                                            )
                                        
                                        st.cache_data.clear() 
                                        st.success(f"Estado de cuenta {ac_num} actualizado")
                                        st.rerun()

                        # --- SECCIÓN DE TARJETAS (Aplicando la misma lógica) ---
                        st.write("💳 **Tarjetas:**")
                        u_cards = cards_by_acc.get(ac_id, [])
                        if u_cards:
                            for card in u_cards:
                                with st.container(border=True):
                                    tc1, tc2 = st.columns([3, 1])
                                    with tc1:
                                        full_card = str(card["card_number"])
                                        st.write(f"{full_card}")
                                    with tc2:
                                        # Usamos un nombre de variable único para evitar la línea amarilla
                                        nuevo_estado_card = st.toggle(
                                            "On", 
                                            value=bool(card["is_active"]), 
                                            key=f"tgl_{prefix}_acc_{ac_id}_card_{card['Id_card']}"
                                        )
                                        
                                        if nuevo_estado_card != bool(card["is_active"]):
                                            if update_card_status(card["Id_card"], nuevo_estado_card):
                                                # 🛡️ Obtención segura del ID del administrador
                                                admin_data = st.session_state.get('user_data', {})
                                                admin_id = admin_data.get('Id_user')
                                                
                                                if admin_id:
                                                    # Definimos la acción según el toggle
                                                    accion_txt = "10" if nuevo_estado_card else "11"
                                                    
                                                    log_action(
                                                        user_id=int(admin_id),
                                                        action=accion_txt,
                                                        details=f"Admin cambió estado de la tarjeta {full_card} de la cuenta {ac_num}"
                                                    )
                                                
                                                st.cache_data.clear()
                                                st.rerun()
        with tab3_clientes:
            st.subheader("Control de Cuentas de Clientes Regulares")
            
            estado_filtro_cli = st.selectbox(
                "Filtrar por estado de cuenta",
                ["Todas", "Activas", "Bloqueadas", "Suspendidas", "Pendientes", "Rechazadas"], # Añadidos nuevos estados
                key="filter_estado_cli"
                )
            
            clients_for_control = cached_get_users(is_staff=False)
            search_control_cli = st.text_input("🔍 Buscar cliente por nombre o correo", key="search_ctrl_cli").lower()
            render_account_controls(
                clients_for_control if clients_for_control else [],
                search_control_cli,
                is_staff_control=False,
                estado_filtro=estado_filtro_cli
                )

        with tab3_personal:
            st.subheader("Control de Cuentas del Personal")
            
            estado_filtro_stf = st.selectbox(
                "Filtrar por estado de cuenta",
                ["Todas", "Activas", "Bloqueadas", "Suspendidas", "Pendientes", "Rechazadas"], # Añadidos nuevos estados
                key="filter_estado_stf"
                )
                
            staff_for_control = cached_get_users(is_staff=True)
            search_control_stf = st.text_input("🔍 Buscar personal por nombre o correo", key="search_ctrl_stf").lower()
            
            render_account_controls(
                staff_for_control if staff_for_control else [],
                search_control_stf,
                is_staff_control=True,
                estado_filtro=estado_filtro_stf
                )

    def get_pending_approvals():
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
            return cursor.fetchall()

# --- TAB 4: APROBACIONES ($10K+) ---
    with tab4:
        st.header("Transacciones Pendientes de Aprobación")
        st.write("Cualquier movimiento mayor o igual a $10,000 requiere autorización manual.")

        pendientes = get_pending_approvals()

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
                        note = st.text_input("Nota (Obligatoria)", key=f"note_{tx_id}", placeholder="Escriba el motivo...")
                        col_b1, col_b2 = st.columns(2)

                        if col_b1.button("✅ Aprobar", key=f"app_{tx_id}", type="primary", use_container_width=True):
                            if not note or note.strip() == "":
                                st.warning("⚠️ Debe ingresar una nota.")
                            else:
                                res = review_transaction(tx_id, st.session_state['user_data']['Id_user'], True, note)
                                if res.get("success"):
                                    admin_id = st.session_state.get('user_data', {}).get('Id_user')
                                    if admin_id:
                                        log_action(user_id=int(admin_id), action="2", details=f"Aprobó TX {tx_id} de {req} (${amt_display:,.2f})")
                                    st.success("Aprobada")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(res.get("error", "Error desconocido"))

                        if col_b2.button("❌ Rechazar", key=f"rej_{tx_id}", type="secondary", use_container_width=True):
                            if not note or note.strip() == "":
                                st.warning("⚠️ Debe ingresar una nota.")
                            else:
                                res = review_transaction(tx_id, st.session_state['user_data']['Id_user'], False, note)
                                if res.get("success"):
                                    admin_id = st.session_state.get('user_data', {}).get('Id_user')
                                    if admin_id:
                                        log_action(user_id=int(admin_id), action="5", details=f"Rechazó TX {tx_id} de {req} (${amt_display:,.2f})")
                                    st.warning("Rechazada")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(res.get("error", "Error desconocido"))
        else:
            st.info("✅ No hay transacciones pendientes de revisión por el momento.")

 # --- TAB 5: HISTORIAL DE APROBACIONES ---
    with tab5:
        st.header("Historial de Revisiones")
        st.write("Registro de transacciones que ya han sido procesadas por el equipo administrativo.")

        import datetime

        # 🔹 FILTRO POR FECHA (OPCIONAL)
        with st.container(border=True):
            st.markdown("#### 🔍 Filtro por Fecha")

            default_end = datetime.date.today()
            default_start = default_end - datetime.timedelta(days=30)

            date_range = st.date_input(
                "📅 Rango de Fechas",
                value=(default_start, default_end),
                key="date_tab5_simple"
            )

        start_date, end_date = None, None
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range

        st.divider()

        # 🔹 CONTROL DE MOSTRAR TODO / 50
        if "show_all_approvals" not in st.session_state:
            st.session_state.show_all_approvals = False

        limit_app = None if st.session_state.show_all_approvals else 50

        # 🔹 CONSULTA (NO SE TOCA)
        try:
            if limit_app is None:
                with st.spinner("Cargando historial completo de aprobaciones..."):
                    movimientos = get_filtered_approval_history(limit_app)
            else:
                movimientos = get_filtered_approval_history(limit_app)
        except Exception as e:
            st.error(f"Error cargando aprobaciones: {e}")
            movimientos = []

        # 🔹 FILTRO EN MEMORIA (NO TOCA BD)
        if movimientos and start_date and end_date:
            movimientos = [
                m for m in movimientos
                if m[2] and start_date <= m[2].date() <= end_date
            ]

        # 🔹 UI
        if movimientos:
            for m in movimientos:
                tx_id, desc, date, amount, rev_date, notes, t_name, req, admin, s_name, s_id = m

                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1.5, 1])

                    with c1:
                        st.markdown(f"**ID:** {tx_id} | **Tipo:** {t_name}")
                        st.markdown(f"**Cliente:** {req}")
                        st.markdown(f"**Monto:** `${float(amount or 0):,.2f}`")
                        st.caption(
                            f"Fecha Solicitud: {date.strftime('%d/%m/%Y %H:%M') if date else 'N/A'}"
                        )

                    with c2:
                        status_color = "#10B981" if s_id == 3 else "#EF4444"
                        st.markdown(
                            f"**Estado:** <span style='color:{status_color}; font-weight:bold;'>{s_name.upper()}</span>",
                            unsafe_allow_html=True
                        )
                        st.markdown(f"**Revisado por:** {admin if admin else 'Sistema'}")
                        st.caption(
                            f"Fecha Revisión: {rev_date.strftime('%d/%m/%Y %H:%M') if rev_date else 'N/A'}"
                        )

                    with c3:
                        st.markdown("**Notas de Revisión:**")
                        st.info(notes if notes else "Sin observaciones.")

            st.divider()

            # 🔹 BOTONES
            if limit_app == 50 and len(movimientos) == 50:
                if st.button("📂 Mostrar todo el historial de Aprobaciones", key="btn_show_all_approvals"):
                    st.session_state.show_all_approvals = True
                    st.rerun()

            elif limit_app is None:
                if st.button("🔽 Volver a los 50 más recientes", key="btn_show_last_approvals"):
                    st.session_state.show_all_approvals = False
                    st.rerun()

        else:
            st.info("No hay historial de revisiones disponible con los filtros seleccionados.")


# --- TAB 6: CONFIGURACIÓN ---
    with tab6:
        st.header("⚙️ Configuración")
        st.subheader("📜 Historial de Tus Acciones Administrativas")

        import datetime
        from card_print.audit_pdf import generar_pdf_auditoria

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
                action_filter = st.selectbox(
                    "⚙️ Tipo de acción",
                    acciones,
                    key="filter_tab6_final"
                )
            
            with col_f2:
                default_end = datetime.date.today()
                default_start = default_end - datetime.timedelta(days=30)

                date_range = st.date_input(
                    "📅 Rango de Fechas",
                    value=(default_start, default_end),
                    key="date_tab6"
                )
                
        start_date, end_date = None, None
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            
        st.divider()

        if "show_all_logs" not in st.session_state:
            st.session_state.show_all_logs = False

        if "pdf_logs_buffer" not in st.session_state:
            st.session_state.pdf_logs_buffer = None

        limit = None if st.session_state.show_all_logs else 50
        
        try:
            if limit is None:
                with st.spinner("Cargando historial completo..."):
                    logs_validados = get_filtered_audit_logs(
                        u_id, limit, start_date, end_date, action_filter
                    )
            else:
                logs_validados = get_filtered_audit_logs(
                    u_id, limit, start_date, end_date, action_filter
                )

            if logs_validados:
                df_logs = pd.DataFrame(
                    logs_validados,
                    columns=["ID", "Acción", "Detalles", "Fecha"]
                )

                df_logs["Fecha"] = pd.to_datetime(df_logs["Fecha"])

                # 🔹 ORDENAR
                df_logs_sorted = df_logs.sort_values(by="Fecha", ascending=False)

                # 🔹 TABLA
                st.dataframe(
                    df_logs_sorted,
                    height=450,
                    hide_index=True,
                    use_container_width=True
                )

                st.caption(f"Mostrando {len(df_logs_sorted)} acciones registradas.")

                # 🔹 GENERAR PDF
                rango_enviar_logs = date_range if isinstance(date_range, tuple) else None

                if st.button("📄 Generar PDF", key="btn_generar_pdf_logs"):
                    with st.spinner("Generando PDF..."):
                        st.session_state.pdf_logs_buffer = generar_pdf_auditoria(
                            df_logs_sorted,
                            "Reporte de Acciones Administrativas",
                            rango_enviar_logs
                        )

                # 🔹 DESCARGAR PDF
                if st.session_state.pdf_logs_buffer:
                    st.download_button(
                        label="⬇️ Descargar PDF",
                        data=st.session_state.pdf_logs_buffer,
                        file_name=f"Auditoria_Logs_{datetime.date.today()}.pdf",
                        mime="application/pdf",
                        key="btn_pdf_logs"
                    )

                # 🔹 BOTONES MOSTRAR MÁS
                if limit == 50 and len(df_logs_sorted) == 50:
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
    
    from models.user_model import get_user_by_id

    from services.transaction_service import create_simple_transaction, create_transfer
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
                # --- Obtenemos nombre para el log ---
                cliente = get_user_by_id(acc['user_id'])
                nombre_cliente = cliente['full_name'] if cliente else f"Usuario ID {acc['user_id']}"

                approve_account(acc['Id_account'])

                log_action(
                    st.session_state['user_data']['Id_user'],
                    "1",
                    f"Aprobación automática de cuenta {acc['account_number']} para: {nombre_cliente}"
                )
            
            # --- FIX CACHÉ ---
            st.cache_data.clear()
            st.success(f"{len(pending_accounts)} cuentas aprobadas automáticamente.")
            time.sleep(1)
            st.rerun()

    pending_accounts = get_pending_accounts()

    if not pending_accounts:
        st.info("No hay solicitudes pendientes.")
    else:
        for acc in pending_accounts:
            # --- Obtenemos el cliente para mostrar su nombre en la interfaz ---
            cliente = get_user_by_id(acc['user_id'])
            nombre_cliente = cliente['full_name'] if cliente else f"Usuario ID {acc['user_id']}"

            with st.container(border=True):

                c1, c2, c3 = st.columns([2,2,1])

                with c1:
                    st.markdown(f"**Cuenta:** {acc['account_number']}")
                    st.caption(f"ID Cuenta: {acc['Id_account']}")

                with c2:
                    # --- Mostramos el nombre real del cliente ---
                    st.markdown(f"**Cliente:** {nombre_cliente}")
                    st.caption(f"Usuario ID: {acc['user_id']} | Estado: Pendiente")

                with c3:

                    if st.button("✅ Aprobar", key=f"approve_{acc['Id_account']}"):
                        approve_account(acc['Id_account'])
                        log_action(
                            st.session_state['user_data']['Id_user'],
                            "1",
                            f"Cajero aprobó la cuenta {acc['account_number']} de {nombre_cliente}"
                        )
                        # --- FIX CACHÉ ---
                        st.cache_data.clear()
                        st.success("Cuenta aprobada")
                        time.sleep(1)
                        st.rerun()

                    if st.button("❌ Rechazar", key=f"reject_{acc['Id_account']}"):
                        reject_account(acc['Id_account'])
                        log_action(
                            st.session_state['user_data']['Id_user'],
                            "6",
                            f"Cajero rechazó la cuenta {acc['account_number']} de {nombre_cliente}"
                        )
                        # --- FIX CACHÉ ---
                        st.cache_data.clear()
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
                                "9",
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
                    st.markdown(f"**Tarjeta ({r['card_number']})**")
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


                                st.success("¡Tarjeta renovada y activada exitosamente!")

                                time.sleep(2)

                                st.rerun()

                        except Exception as e:
                            st.error(f"Error en entrega: {e}")

                    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # -------------------------------------------------
    # TRANSFERENCIAS GLOBALES (CAJERO)
    # -------------------------------------------------
    st.subheader("💸 Transferencias Globales")
    st.write("Realiza transferencias entre cualquier par de cuentas del banco.")

    with st.form("cajero_transfer_form"):
        col_tf1, col_tf2 = st.columns(2)
        with col_tf1:
            tf_origen  = st.text_input("Cuenta Origen",  placeholder="Ej. SV_synapse1234567")
            tf_monto   = st.number_input("Monto ($)", min_value=0.01, step=10.0, format="%.2f")
        with col_tf2:
            tf_destino = st.text_input("Cuenta Destino", placeholder="Ej. SV_synapse7654321")
            tf_desc    = st.text_input("Descripción",    placeholder="Ej. Transferencia por cajero")

        sub_tf = st.form_submit_button("⚡ Ejecutar Transferencia", type="primary", use_container_width=True)

        if sub_tf:
            if not tf_origen or not tf_destino or not tf_desc or tf_monto <= 0:
                st.warning("Complete todos los campos correctamente.")
            elif tf_origen.strip() == tf_destino.strip():
                st.error("❌ Las cuentas origen y destino no pueden ser la misma.")
            else:
                acc_orig = get_account_by_number(tf_origen.strip())
                acc_dest = get_account_by_number(tf_destino.strip())

                if not acc_orig:
                    st.error("❌ Cuenta origen no encontrada.")
                elif not acc_dest:
                    st.error("❌ Cuenta destino no encontrada.")
                else:
                    # Obtener IDs de forma segura (dict o tuple)
                    orig_id = acc_orig.get('Id_account') if isinstance(acc_orig, dict) else acc_orig[0]
                    dest_id = acc_dest.get('Id_account') if isinstance(acc_dest, dict) else acc_dest[0]

                    try:
                        res_tf = create_transfer(
                            from_account_id=orig_id,
                            to_account_id=dest_id,
                            amount=tf_monto,
                            description=tf_desc,
                            created_by_user_id=st.session_state['user_data']['Id_user'],
                            transaction_type_id=1
                        )

                        if res_tf.get('success'):
                            log_action(
                                st.session_state['user_data']['Id_user'],
                                "7",
                                f"Cajero realizó transferencia de ${tf_monto:,.2f} de {tf_origen} a {tf_destino}: {tf_desc}"
                            )
                            if res_tf.get('requires_approval'):
                                st.warning(f"⏳ Transferencia de ${tf_monto:,.2f} retenida para aprobación (monto >= $10,000).")
                            else:
                                st.success(f"✅ Transferencia de ${tf_monto:,.2f} realizada exitosamente.")
                        else:
                            st.error(f"❌ Error: {res_tf.get('error')}")
                    except Exception as e:
                        st.error(f"❌ Error de base de datos: {str(e)}")

elif role_id == 4:
    st.header("📊 Panel de Métricas - Analista Financiero")
    st.write("Vista de solo lectura orientada a la toma de decisiones estratégicas.")

    from services.rbac_service import execute_analyst_query, get_daily_transaction_counts
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

    res = execute_analyst_query(start_date, end_date)

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
            st.subheader("🕒 Evolución Temporal de Transacciones")

            try:
                hist_res = get_daily_transaction_counts(start_date, end_date)

                if hist_res.get('status') == 200 and hist_res.get('data'):
                    df_hist = pd.DataFrame(hist_res['data'])
                    df_hist['fecha'] = pd.to_datetime(df_hist['fecha'])

                    chart_evolucion = alt.Chart(df_hist).mark_area(
                        line={'color': '#FF9800'},
                        color=alt.Gradient(
                            gradient='linear',
                            stops=[alt.GradientStop(color='rgba(255,152,0,0.1)', offset=0),
                                   alt.GradientStop(color='rgba(255,152,0,0.7)', offset=1)],
                            x1=1, x2=1, y1=1, y2=0
                        )
                    ).encode(
                        x=alt.X('fecha:T', title="Línea de Tiempo",
                                axis=alt.Axis(format='%d/%m', labelAngle=-30)),
                        y=alt.Y('cantidad:Q', title="N° de Operaciones",
                                scale=alt.Scale(zero=True)),
                        tooltip=[
                            alt.Tooltip('fecha:T', title='Fecha', format='%d/%m/%Y'),
                            alt.Tooltip('cantidad:Q', title='Transacciones')
                        ]
                    ).properties(height=300).interactive()

                    st.altair_chart(chart_evolucion, use_container_width=True)
                    st.caption(f"Datos reales: {len(df_hist)} días con actividad en el rango seleccionado.")

                elif hist_res.get('status') != 200:
                    st.error(f"Error al consultar datos: {hist_res.get('error')}")
                else:
                    st.info("💤 No hay transacciones registradas en el rango de fechas seleccionado.")

            except Exception as e:
                st.error(f"Error de base de datos en evolución temporal: {str(e)}")

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
import datetime
from services.audit_service import log_action, get_filtered_auditor_admin_logs, get_filtered_auditor_transactions # Asegúrate de importar tus funciones
from config.database import get_cursor
from card_print.audit_pdf import generar_pdf_auditoria

if role_id == 5:
    st.header("Control de Riesgos - Auditor")
    st.write("Historial Detallado de Operaciones del Sistema. (Solo Lectura)")

    from services.transaction_service import get_all_account_history
    import altair as alt

    tab_admin, tab_ops, tab_acc = st.tabs(["Historial Administrativo", "Historial de Transacciones", "📊 Auditoría de Cuentas"])

    # --- TAB 1: Historial Administrativo ---
    with tab_admin:
        st.subheader("📜 Acciones de Personal y Configuración")

        if "show_all_audit_admin" not in st.session_state:
            st.session_state.show_all_audit_admin = False

        try:
            with st.spinner("Cargando historial administrativo..."):
                # Llamada al backend (Asegúrate de que el SQL devuelva la columna DUI)
                rows = get_filtered_auditor_admin_logs(None)
                
            if rows:
                # 1. Agregamos "DUI" a las columnas esperadas
                df_admin = pd.DataFrame.from_records(
                    rows,
                    columns=["ID", "Administrador", "DUI", "Acción", "Detalles", "Fecha"]
                )
                df_admin['Fecha'] = pd.to_datetime(df_admin['Fecha'])

                # --- FILTROS ---
                col_a1, col_a2, col_a3 = st.columns(3)
                
                with col_a1:
                    acciones_unicas = sorted(df_admin['Acción'].dropna().unique().tolist())
                    selected_accion = st.selectbox(
                        "📌 Filtrado por acción",
                        ["Todos"] + acciones_unicas,
                        key="filter_accion_admin"
                    )
                with col_a2:
                    search_admin = st.text_input("🔎 Filtrar Administrador", key="search_admin_audit")
                with col_a3:
                    search_dui_admin = st.text_input("💳 Filtrar por DUI", key="search_dui_admin_audit")

                # Aplicar filtros de texto y selectbox
                if selected_accion != "Todos":
                    df_admin = df_admin[df_admin['Acción'] == selected_accion]
                if search_admin:
                    df_admin = df_admin[df_admin['Administrador'].str.contains(search_admin, case=False, na=False)]
                if search_dui_admin:
                    # astype(str) previene errores si la BD lo envía como número
                    df_admin = df_admin[df_admin['DUI'].astype(str).str.contains(search_dui_admin, case=False, na=False)]

                # --- FILTRO POR RANGO DE FECHAS ---
                use_date_filter = st.checkbox("📅 Activar filtro por fechas", key="enable_date_filter_admin")
                date_range = None
                
                if use_date_filter:
                    today = datetime.date.today()
                    if not df_admin.empty:
                        default_start = df_admin['Fecha'].dt.date.min()
                        default_end = df_admin['Fecha'].dt.date.max()
                    else:
                        default_start, default_end = today, today
                        
                    date_range = st.date_input(
                        "Seleccione el rango",
                        value=(default_start, default_end),
                        key="date_range_admin"
                    )
                    
                    if not df_admin.empty:
                        if len(date_range) == 2:
                            start_date, end_date = date_range
                            df_admin = df_admin[(df_admin['Fecha'].dt.date >= start_date) & (df_admin['Fecha'].dt.date <= end_date)]
                        elif len(date_range) == 1:
                            start_date = date_range[0]
                            df_admin = df_admin[df_admin['Fecha'].dt.date == start_date]

                # --- VISUALIZACIÓN EN PANTALLA ---
                if not st.session_state.show_all_audit_admin and len(df_admin) > 50:
                    df_mostrar = df_admin.head(50)
                    st.caption(f"Mostrando 50 de {len(df_admin)} registros. Utiliza la descarga PDF para obtener el informe completo.")
                else:
                    df_mostrar = df_admin
                    st.caption(f"Mostrando los {len(df_admin)} registros.")

                st.dataframe(df_mostrar, height=450, hide_index=True, use_container_width=True)
                
                # --- BOTÓN DE DESCARGA PDF ---
                if not df_admin.empty:
                    rango_enviar = date_range if use_date_filter else None
                    pdf_buffer_admin = generar_pdf_auditoria(df_admin, "Reporte de Acciones Administrativas", rango_enviar)
                    
                    st.download_button(
                        label="📄 Descargar Reporte Completo en PDF",
                        data=pdf_buffer_admin,
                        file_name=f"Auditoria_Admin_{datetime.date.today()}.pdf",
                        mime="application/pdf",
                        key="btn_pdf_admin"
                    )
                
                # --- CONTROLES DE VISTA ---
                if len(df_admin) > 50:
                    if not st.session_state.show_all_audit_admin:
                        if st.button("📂 Mostrar todos los registros", key="btn_show_all_audit_admin"):
                            st.session_state.show_all_audit_admin = True
                            st.rerun()
                    else:
                        if st.button("🔽 Volver a los 50 más recientes", key="btn_show_last_audit_admin"):
                            st.session_state.show_all_audit_admin = False
                            st.rerun()
            else:
                st.info("No hay registros en el registro de auditoría administrativo.")
        except Exception as e:
            st.error(f"Error al cargar historial administrativo: {e}")

    # --- TAB 2: Historial de Transacciones ---
    with tab_ops:
        st.subheader("📜 Movimientos y Transacciones")

        if "show_all_audit_trans" not in st.session_state:
            st.session_state.show_all_audit_trans = False

        try:
            with st.spinner("Cargando transacciones completas..."):
                # Llamada al backend (Asegúrate de que el SQL devuelva DUI y Numero Cuenta)
                rows = get_filtered_auditor_transactions(None)

            if rows:
                # 1. Agregamos DUI y Numero Cuenta a las columnas
                columns = [
                    "ID Transacción", "Tipo_ID", "Status_ID", "Descripción",
                    "ID Usuario", "Usuario", "DUI", "Numero Cuenta", "Fecha Creación", "Procesado En"
                ]
                df_trans = pd.DataFrame.from_records(rows, columns=columns)
                df_trans['Fecha Creación'] = pd.to_datetime(df_trans['Fecha Creación'])
                df_trans['Procesado En'] = pd.to_datetime(df_trans['Procesado En'])

                tipo_dict = {1: "Transferencia", 2: "Retiro", 3: "Depósito", 4: "Pago"}
                df_trans['Tipo Nombre'] = df_trans['Tipo_ID'].map(tipo_dict).fillna("Desconocido")

                # --- NUEVOS FILTROS ---
                col_t1, col_t2, col_t3, col_t4 = st.columns(4)
                with col_t1:
                    search_user = st.text_input("🔎 Filtrar Usuario", key="search_user_trans")
                with col_t2:
                    search_dui = st.text_input("💳 Filtrar DUI", key="search_dui_trans")
                with col_t3:
                    search_account = st.text_input("🏦 Filtrar Cuenta", key="search_account_trans")
                with col_t4:
                    tipo_options = ["Todos"] + list(tipo_dict.values())
                    selected_tipo = st.selectbox("Tipo transacción", tipo_options, key="filter_tipo_trans")

                df_filtered = df_trans.copy()
                
                # Aplicar filtros en cascada
                if search_user:
                    df_filtered = df_filtered[df_filtered['Usuario'].str.contains(search_user, case=False, na=False)]
                if search_dui:
                    df_filtered = df_filtered[df_filtered['DUI'].astype(str).str.contains(search_dui, case=False, na=False)]
                if search_account:
                    df_filtered = df_filtered[df_filtered['Numero Cuenta'].astype(str).str.contains(search_account, case=False, na=False)]
                if selected_tipo != "Todos":
                    df_filtered = df_filtered[df_filtered['Tipo Nombre'] == selected_tipo]

                # --- FILTRO POR RANGO DE FECHAS ---
                use_date_filter_trans = st.checkbox("📅 Activar filtro por fechas", key="enable_date_filter_trans")
                date_range_t = None
                
                if use_date_filter_trans:
                    today = datetime.date.today()
                    if not df_filtered.empty:
                        default_start_t = df_filtered['Fecha Creación'].dt.date.min()
                        default_end_t = df_filtered['Fecha Creación'].dt.date.max()
                    else:
                        default_start_t, default_end_t = today, today
                        
                    date_range_t = st.date_input(
                        "Seleccione el rango",
                        value=(default_start_t, default_end_t),
                        key="date_range_trans"
                    )
                    
                    if not df_filtered.empty:
                        if len(date_range_t) == 2:
                            start_date_t, end_date_t = date_range_t
                            df_filtered = df_filtered[(df_filtered['Fecha Creación'].dt.date >= start_date_t) & (df_filtered['Fecha Creación'].dt.date <= end_date_t)]
                        elif len(date_range_t) == 1:
                            start_date_t = date_range_t[0]
                            df_filtered = df_filtered[df_filtered['Fecha Creación'].dt.date == start_date_t]

                # 2. Columnas a mostrar en la tabla y en el PDF
                display_cols = [
                    "ID Transacción", "Usuario", "DUI", "Numero Cuenta", "Tipo Nombre", "Descripción",
                    "Fecha Creación", "Procesado En", "Status_ID"
                ]
                
                # --- VISUALIZACIÓN EN PANTALLA ---
                if not st.session_state.show_all_audit_trans and len(df_filtered) > 50:
                    df_mostrar_trans = df_filtered.head(50)
                    st.caption(f"Mostrando 50 de {len(df_filtered)} transacciones. Descarga el PDF para obtener todas.")
                else:
                    df_mostrar_trans = df_filtered
                    st.caption(f"Mostrando {len(df_filtered)} transacciones encontradas.")

                st.dataframe(df_mostrar_trans[display_cols], height=450, hide_index=True, use_container_width=True)
                
                # --- BOTÓN DE DESCARGA PDF ---
                if not df_filtered.empty:
                    rango_enviar_trans = date_range_t if use_date_filter_trans else None
                    pdf_buffer_trans = generar_pdf_auditoria(df_filtered[display_cols], "Reporte de Transacciones", rango_enviar_trans)
                    
                    st.download_button(
                        label="📄 Descargar Reporte Completo en PDF",
                        data=pdf_buffer_trans,
                        file_name=f"Auditoria_Transacciones_{datetime.date.today()}.pdf",
                        mime="application/pdf",
                        key="btn_pdf_trans"
                    )
                
                # --- CONTROLES DE VISTA ---
                if len(df_filtered) > 50:
                    if not st.session_state.show_all_audit_trans:
                        if st.button("📂 Mostrar todas las transacciones", key="btn_show_all_audit_trans"):
                            st.session_state.show_all_audit_trans = True
                            st.rerun()
                    else:
                        if st.button("🔽 Volver a los 50 más recientes", key="btn_show_last_audit_trans"):
                            st.session_state.show_all_audit_trans = False
                            st.rerun()
            else:
                st.info("No se encontraron registros de transacciones.")
        except Exception as e:
            st.error(f"Error crítico al cargar historial de transacciones: {e}")

    # --- TAB 3: Auditoría de Cuentas ---
    with tab_acc:
        st.subheader("Auditoría de Cuentas")
        st.write("Consulta la evolución del saldo de cualquier cuenta del sistema.")
        
        @st.cache_data(ttl=60)
        def _get_all_accounts_for_auditor():
            with get_cursor() as cursor:
                # Obtenemos id, número de cuenta y el nombre descriptivo del usuario para el selectbox
                cursor.execute("SELECT a.Id_account, a.account_number, u.full_name FROM account a INNER JOIN [user] u ON a.user_id = u.Id_user ORDER BY u.full_name")
                rows = cursor.fetchall()
                return [{"id": r[0], "num": r[1], "name": r[2]} for r in rows] if rows else []
        
        all_accounts = _get_all_accounts_for_auditor()
        
        if not all_accounts:
            st.info("No hay cuentas registradas en el sistema.")
        else:
            # Diccionario para el Selectbox: {ID: "Nombre - Número de cuenta"}
            acc_opts = {a["id"]: f"{a['name']} - {a['num']}" for a in all_accounts}
            selected_acc_id = st.selectbox(
                "Seleccione una cuenta para auditar",
                options=list(acc_opts.keys()),
                format_func=lambda x: acc_opts[x],
                index=0
            )
            
            if selected_acc_id:
                st.divider()
                st.markdown("### 📈 Evolución del Saldo General")
                
                history = get_all_account_history(selected_acc_id)
                
                if history:
                    # Calcular el saldo acumulado (running total)
                    df_ev = pd.DataFrame([
                        {"fecha": tx["date"], "monto": tx["amount"] if tx["entry_type"] == "credit" else -tx["amount"]}
                        for tx in sorted(history, key=lambda x: x["date"])
                    ])
                    df_ev["saldo"] = df_ev["monto"].cumsum()
                    
                    # Gráfico de Área igual al del Usuario
                    chart_saldo_aud = alt.Chart(df_ev).mark_area(
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
                    ).properties(height=350).interactive()
                    
                    st.altair_chart(chart_saldo_aud, use_container_width=True)
                else:
                    st.info("Esta cuenta no tiene ninguna transacción o movimiento registrado aún.")