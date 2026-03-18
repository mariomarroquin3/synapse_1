import streamlit as st
import sys
import os
import time

# --- CONFIGURACIÓN DE RUTAS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- IMPORTACIONES DE LÓGICA ---
from models.user_model import get_user_by_email
from utils.security import verify_password
from utils.ui_components import apply_premium_style

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Synapse | Portal Empleados", page_icon="🔐", layout="centered")

# --- DISEÑO PREMIUM ---
apply_premium_style()

# CSS EXCLUSIVO (Branding de Empleados + Glassmorphism + Mesh)
st.markdown("""
<style>
    /* 1. Fondo Animado Dark Mesh (Variante Admin: Tonos más oscuros y violetas/rojos sutiles) */
    .stApp {
        background-color: #020408 !important;
        background-image: 
            radial-gradient(circle at 20% 40%, rgba(88, 28, 135, 0.35), transparent 45%), 
            radial-gradient(circle at 80% 60%, rgba(153, 27, 27, 0.20), transparent 45%), 
            radial-gradient(circle at 50% 80%, rgba(30, 58, 138, 0.3), transparent 45%) !important;
        background-size: 400% 400% !important;
        animation: meshMovement 15s ease infinite alternate !important;
    }
    
    @keyframes meshMovement {
        0% { background-position: 0% 0%; }
        50% { background-position: 50% 100%; }
        100% { background-position: 100% 50%; }
    }

    /* 2. Glassmorphism en la tarjeta de login */
    [data-testid="stVerticalBlock"] > div:has(form) {
        background: rgba(15, 15, 20, 0.7) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(239, 68, 68, 0.15) !important; /* Borde sutilmente rojizo */
        border-radius: 28px !important;
        padding: 40px 35px !important;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8) !important;
    }

    /* Limpieza de bordes nativos del form */
    [data-testid="stForm"] { 
        border: none !important; 
        padding: 0 !important; 
        background: transparent !important;
    }

    /* 3. Textos Títulos */
    .brand-title {
        color: #FFFFFF;
        text-align: center;
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
        letter-spacing: 1px;
    }
    .brand-sub {
        color: #EF4444; /* Rojo suave para indicar área restringida */
        text-align: center;
        font-size: 0.85rem;
        margin-bottom: 2.5rem;
        letter-spacing: 3px;
        font-weight: 600;
        text-transform: uppercase;
    }

    /* Ajuste de ancho de la página para centrar la tarjeta */
    .block-container { 
        padding-top: 4rem !important; 
        max-width: 450px !important; /* Un poco más estrecha que la de clientes */
    }

    /* Botón principal (Rojo/Gris oscuro para staff) */
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #374151, #1F2937) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        transition: all 0.3s ease !important;
    }
    .stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #EF4444, #DC2626) !important;
        border-color: #EF4444 !important;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CABECERA ---
st.markdown("""
    <div style="text-align: center; margin-bottom: 10px;">
        <span style="font-size: 3rem;">🛡️</span>
    </div>
    <h1 class="brand-title">SYNAPSE STAFF</h1>
    <p class="brand-sub">PORTAL DE GESTIÓN INTERNA</p>
""", unsafe_allow_html=True)

# --- FORMULARIO DE LOGIN ---
with st.form("admin_login_form"):
    st.markdown("<h5 style='text-align:center; color:#9CA3AF; margin-bottom:25px; font-weight:400;'>Ingresa tus credenciales autorizadas</h5>", unsafe_allow_html=True)
    
    a_email = st.text_input("Usuario de Empleado (Email)", placeholder="empleado@synapse.com", label_visibility="collapsed")
    st.markdown("<div style='height:5px'></div>", unsafe_allow_html=True)
    a_pass = st.text_input("Contraseña", type="password", placeholder="••••••••", label_visibility="collapsed")
    
    st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)
    submit = st.form_submit_button("INICIAR SESIÓN", use_container_width=True)

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
                            "Id_user": user.get('Id_user'), 
                            "email": user.get('email'), 
                            "full_name": user.get('full_name'),
                            "DUI": user.get('dui', user.get('DUI', 'N/A')),
                            "phone_number": user.get('phone_number', 'N/A'),
                            "role_id": user.get('role_id')
                        }
                        st.success(f"Acceso autorizado. Bienvenido, {user['full_name']}")
                        time.sleep(1)
                        st.switch_page("pages/admin_dashboard.py")
                    else:
                        st.error("❌ Cuenta suspendida. Contacte al administrador principal.")
                else:
                    st.error("Credenciales incorrectas.")
            else:
                st.error("⛔ Acceso denegado. Se requieren permisos administrativos.")

# --- ENLACE DE RETORNO ---
st.markdown("""
    <div style='text-align:center; margin-top:30px;'>
        <a href='/login_page' target='_self' style='color:#64748B; text-decoration:none; font-size: 0.9rem; transition: color 0.3s;'>
            ← Volver al Portal de Clientes
        </a>
    </div>
""", unsafe_allow_html=True)