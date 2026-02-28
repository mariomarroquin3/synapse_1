import streamlit as st
import sys
import os
import re
import time

# --- CONFIGURACIÓN DE RUTAS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- IMPORTACIONES DE LÓGICA ---
from models.user_model import (
    create_user, 
    get_user_by_email, 
    get_user_by_dui,
    get_user_by_phone
)
from services.account_service import create_account_for_user
from utils.security import hash_password, verify_password

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Synapse | Banca Digital", page_icon="🏦", layout="centered")

# --- CSS AVANZADO: ELIMINACIÓN DE BLOQUES VACÍOS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    /* 1. Reset de márgenes y eliminación de espacios en blanco del sistema */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        max-width: 500px !important;
    }
    
    /* Ocultar elementos de UI de Streamlit */
    header, footer, [data-testid="stHeader"] {
        visibility: hidden !important;
        height: 0px !important;
        display: none !important;
    }
    
    /* 2. ATAQUE AL ESPACIO EN BLANCO: Ocultar contenedores vacíos */
    div[data-testid="stElementContainer"]:empty,
    div.stMarkdown:empty,
    div.element-container:has(.auth-card:empty) {
        display: none !important;
        height: 0px !important;
        margin: 0px !important;
        padding: 0px !important;
    }

    /* Reducir el gap vertical de Streamlit */
    div.stVerticalBlock {
        gap: 0rem !important;
    }

    /* Variables de Estilo */
    :root {
        --primary: #0047AB;
        --secondary: #00B4D8;
    }

    html, body, [class*="st-"] { 
        font-family: 'Plus Jakarta Sans', sans-serif; 
    }
    
    .stApp { 
        background-color: #F8FAFC;
    }

    /* Hero Section */
    .hero-section {
        text-align: center;
        margin-bottom: 2rem;
    }
    .brand-title {
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.2rem;
        font-weight: 800;
        margin-bottom: -5px;
        letter-spacing: -1.5px;
    }
    .brand-sub {
        color: #64748B;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }

    /* Estilo de Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        justify-content: center;
        margin-bottom: -1px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 12px 12px 0 0;
        padding: 10px 20px;
        color: #94A3B8;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--primary) !important;
        font-weight: 700 !important;
        background-color: white !important;
    }

    /* Formulario como Card */
    div[data-testid="stForm"] {
        background: white !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 0px 0px 20px 20px !important;
        padding: 2.5rem !important;
        box-shadow: 0 15px 25px -5px rgba(0, 0, 0, 0.05) !important;
        margin-top: 0px !important;
    }

    /* Estilo de Inputs */
    .stTextInput input {
        border-radius: 10px !important;
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
    }
    .stTextInput input:focus {
        border-color: var(--primary) !important;
    }

    /* Botón */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, var(--primary), #003380) !important;
        color: white !important;
        border-radius: 10px !important;
        padding: 12px !important;
        font-weight: 700 !important;
        border: none !important;
        margin-top: 15px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE LIMPIEZA MANUAL (SIN CALLBACKS) ---
def get_clean_numeric(text):
    return "".join(filter(str.isdigit, text))

def get_clean_name(text):
    return "".join(re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', text))

# --- RENDERIZADO DE UI ---
st.markdown('<div class="hero-section">', unsafe_allow_html=True)
st.markdown('<h1 class="brand-title">Synapse</h1>', unsafe_allow_html=True)
st.markdown('<p class="brand-sub">Banca Digital • El Salvador</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

tab_login, tab_reg = st.tabs(["🔐 ACCESO", "📝 REGISTRO"])

with tab_login:
    with st.form("login_form_final"):
        st.markdown("<h4 style='text-align:center; margin-bottom:25px; color:#0F172A;'>Inicia Sesión</h4>", unsafe_allow_html=True)
        l_email = st.text_input("Correo electrónico", placeholder="usuario@correo.com")
        l_pass = st.text_input("Contraseña", type="password", placeholder="••••••••")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        submit = st.form_submit_button("ENTRAR AL PORTAL")

        if submit:
            if not l_email or not l_pass:
                st.warning("Por favor completa tus datos.")
            else:
                user = get_user_by_email(l_email)
                if user and verify_password(l_pass, user[3]):
                    st.session_state["logged_in"] = True
                    st.session_state["user_data"] = {
                        "Id_user": user[0], "email": user[2], "full_name": user[6],
                        "DUI": user[5], "phone_number": user[7]
                    }
                    st.success("Acceso concedido.")
                    time.sleep(0.5)
                    st.switch_page("pages/home_page.py")
                else:
                    st.error("Credenciales no válidas.")

with tab_reg:
    with st.form("reg_form_final"):
        st.markdown("<h4 style='margin-bottom:25px; color:#0F172A;'>Crea tu cuenta</h4>", unsafe_allow_html=True)
        r_col1, r_col2 = st.columns(2)
        with r_col1:
            r_name_raw = st.text_input("Nombre", placeholder="Tu nombre completo")
            r_email = st.text_input("Email", placeholder="tu@correo.com")
            r_dui_raw = st.text_input("DUI", max_chars=9, placeholder="000000000")
        with r_col2:
            r_tel_raw = st.text_input("Teléfono", max_chars=8, placeholder="70000000")
            r_pass = st.text_input("Clave", type="password", placeholder="Clave segura")
            r_conf = st.text_input("Confirmar", type="password", placeholder="Repite tu clave")
        
        r_gen = st.selectbox("Género", ["Masculino", "Femenino", "Otro"])
        
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        btn_reg = st.form_submit_button("REGISTRARME AHORA")

        if btn_reg:
            # Limpieza manual post-submit (Evita errores de Streamlit Form)
            clean_name = get_clean_name(r_name_raw)
            clean_dui = get_clean_numeric(r_dui_raw)
            clean_tel = get_clean_numeric(r_tel_raw)
            
            if r_pass != r_conf: 
                st.error("Las contraseñas no coinciden.")
            elif not clean_name or not r_email or not clean_dui: 
                st.warning("Faltan datos requeridos o formato inválido.")
            else:
                try:
                    if get_user_by_email(r_email): 
                        st.error("Email ya registrado.")
                    else:
                        # Aplicar formato a DUI y Teléfono
                        dui_f = f"{clean_dui[:8]}-{clean_dui[8:]}" if len(clean_dui) == 9 else clean_dui
                        tel_f = f"+503 {clean_tel[:4]}-{clean_tel[4:]}" if len(clean_tel) == 8 else clean_tel
                        
                        h = hash_password(r_pass)
                        u_id = create_user(2, r_email, h, None, dui_f, clean_name, r_gen[0], tel_f)
                        create_account_for_user(u_id, "USD")
                        st.success("¡Bienvenido a Synapse!")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                except Exception as e: 
                    st.error(f"Error en el servidor: {e}")

st.markdown("""
    <p style='text-align:center; color:#94A3B8; font-size:0.7rem; margin-top:2rem;'>
        © 2026 Synapse Digital Bank S.A. de C.V.<br>
        Seguridad Bancaria de El Salvador.
    </p>
""", unsafe_allow_html=True)