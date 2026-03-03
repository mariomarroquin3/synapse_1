import streamlit as st
import sys
import os
import re
import time
import pandas as pd

# --- CONFIGURACIÓN DE RUTAS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- IMPORTACIONES ---
from models.user_model import get_users_by_role_category, update_user_status
from services.user_service import register_user_with_permissions

# --- SEGURIDAD DE PÁGINA ---
if "user_data" not in st.session_state or st.session_state["user_data"]["role_id"] != 3:
    st.error("Acceso denegado. Se requieren privilegios de Administrador.")
    if st.button("Ir al Login"):
        st.switch_page("pages/admin_login.py")
    st.stop()

st.set_page_config(page_title="Synapse | Admin Dashboard", page_icon="📈", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    .main { background-color: #F8FAFC; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0; }
    .status-active { color: #10B981; font-weight: 700; }
    .status-suspended { color: #EF4444; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Panel de Control Administrativo")
st.write(f"Bienvenido, **{st.session_state['user_data']['full_name']}**")

tab1, tab2, tab3 = st.tabs(["👥 Gestión de Personal", "💳 Gestión de Clientes", "⚙️ Configuración"])

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
        st.dataframe(df_staff, use_container_width=True)
    else:
        st.info("No hay personal registrado.")

# --- TAB 2: GESTIÓN DE CLIENTES ---
with tab2:
    st.header("Gestión de Cuentas de Clientes")
    st.info("Nota: Los administradores pueden gestionar clientes existentes pero no crearlos.")
    
    clients = get_users_by_role_category(is_staff=False)
    if clients:
        for client in clients:
            with st.container():
                c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                status_text = "Activo" if client['is_active'] else "Suspendido"
                status_class = "status-active" if client['is_active'] else "status-suspended"
                
                c1.write(f"**{client['full_name']}**")
                c2.write(client['email'])
                c3.markdown(f"<span class='{status_class}'>{status_text}</span>", unsafe_allow_html=True)
                
                btn_label = "Suspender" if client['is_active'] else "Activar"
                if c4.button(btn_label, key=f"btn_{client['Id_user']}"):
                    update_user_status(client['Id_user'], not client['is_active'])
                    st.success(f"Estado de {client['full_name']} actualizado.")
                    time.sleep(1)
                    st.rerun()
            st.divider()
    else:
        st.info("No hay clientes registrados en el sistema.")

# --- TAB 3: CONFIGURACIÓN ---
with tab3:
    st.header("Funciones Avanzadas")
    st.write("Configuraciones del sistema y registros de auditoría (Próximamente).")
    if st.button("Cerrar Sesión Administrativa"):
        st.session_state.clear()
        st.switch_page("pages/login_page.py")
