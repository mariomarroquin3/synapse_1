import streamlit as st
import sys
import os
import time

# --- CONFIGURACIÓN DE RUTAS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- IMPORTACIONES DE LÓGICA ---
from models.user_model import get_user_by_email
from utils.security import verify_password

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Synapse | Admin Portal", page_icon="🔐", layout="centered")

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    
    :root {
        --primary: #3B82F6;
        --secondary: #60A5FA;
        --bg-main: #000000;
        --bg-card: #111111;
        --text-primary: #FFFFFF;
        --text-secondary: #94A3B8;
        --border-color: #222222;
    }

    .stApp { background-color: var(--bg-main); color: var(--text-primary); }
    .brand-title {
        color: var(--text-primary);
        text-align: center;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .brand-sub {
        color: var(--text-secondary);
        text-align: center;
        font-size: 0.9rem;
        margin-bottom: 2rem;
        letter-spacing: 2px;
    }
    div[data-testid="stForm"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 20px !important;
        padding: 2.5rem !important;
    }
    .stTextInput label, .stTextInput input {
        color: var(--text-primary) !important;
    }
    .stTextInput input {
        background-color: var(--bg-main) !important;
        border: 1px solid var(--border-color) !important;
    }
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, var(--primary), #1E40AF) !important;
        color: white !important;
        border-radius: 10px !important;
        padding: 12px !important;
        font-weight: 700 !important;
        border: none !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="brand-title">Synapse Admin</h1>', unsafe_allow_html=True)
st.markdown('<p class="brand-sub">PORTAL DE GESTIÓN INTERNA</p>', unsafe_allow_html=True)

with st.form("admin_login_form"):
    st.markdown("<h4 style='text-align:center; color:white; margin-bottom:20px;'>Acceso Restringido</h4>", unsafe_allow_html=True)
    a_email = st.text_input("Usuario Administrativo (Email)", placeholder="admin@synapse.com")
    a_pass = st.text_input("Contraseña", type="password", placeholder="••••••••")
    submit = st.form_submit_button("INICIAR SESIÓN")

    if submit:
        if not a_email or not a_pass:
            st.warning("Ingrese sus credenciales.")
        else:
            user = get_user_by_email(a_email)
            # Solo permitir roles Staff (1=Cajero, 3=Admin, 4=Analista, 5=Auditor)
            if user and user['role_id'] in [1, 3, 4, 5]:
                if verify_password(a_pass, user['password_hash']):
                    if user['is_active']:
                        st.session_state["logged_in"] = True
                        st.session_state["is_admin"] = (user['role_id'] == 3)
                        st.session_state["user_data"] = {
                            "Id_user": user['Id_user'], 
                            "email": user['email'], 
                            "full_name": user['full_name'],
                            "role_id": user['role_id']
                        }
                        st.success(f"Bienvenido, {user['full_name']}")
                        time.sleep(1)
                        st.switch_page("pages/admin_dashboard.py")
                    else:
                        st.error("Cuenta suspendida. Contacte al administrador principal.")
                else:
                    st.error("Contraseña incorrecta.")
            else:
                st.error("Acceso denegado. Se requieren permisos administrativos.")

st.markdown("<p style='text-align:center; margin-top:20px;'><a href='/login_page' target='_self' style='color:#94A3B8; text-decoration:none;'>← Volver al Portal de Clientes</a></p>", unsafe_allow_html=True)
