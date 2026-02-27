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

# --- DISEÑO LIMPIO Y PROFESIONAL (AZUL Y BLANCO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@300;400;600;700&display=swap');
    html, body, [class*="st-"] { font-family: 'Segoe UI', sans-serif; }
    .stApp { background-color: #fcfcfc; }
    .hero-title { color: #0047AB; font-weight: 700; font-size: 3rem; text-align: center; margin-bottom: 0px; }
    .hero-subtitle { color: #6c757d; text-align: center; font-size: 1.1rem; margin-bottom: 2.5rem; }
    .custom-card { background-color: #ffffff; border: 1px solid #e9ecef; padding: 35px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); margin-bottom: 20px; }
    .stButton>button { background-color: #0047AB !important; color: white !important; border-radius: 8px; font-weight: 600; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background-color: #003380 !important; }
    .footer-text { text-align: center; color: #adb5bd; font-size: 0.8rem; margin-top: 4rem; padding-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE LIMPIEZA ---
def clean_numeric_input(key):
    value = st.session_state[key]
    clean_value = "".join(filter(str.isdigit, value))
    if value != clean_value:
        st.session_state[key] = clean_value

def clean_name_input(key):
    value = st.session_state[key]
    clean_value = "".join(re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', value))
    if value != clean_value:
        st.session_state[key] = clean_value

# --- CABECERA ---
st.markdown('<h1 class="hero-title">Synapse 1.0</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Banca Digital de El Salvador</p>', unsafe_allow_html=True)

tab_acceso, tab_registro = st.tabs(["🔐 Iniciar Sesión", "📝 Crear Cuenta"])

# --- SECCIÓN: LOGIN ---
with tab_acceso:
    col_a, col_b, col_c = st.columns([0.15, 0.7, 0.15])
    with col_b:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        with st.form("form_login"):
            st.markdown("#### Bienvenid@")
            l_email = st.text_input("Correo electrónico", placeholder="usuario@correo.com")
            l_pass = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submit_l = st.form_submit_button("INGRESAR")

            if submit_l:
                if not l_email or not l_pass:
                    st.warning("Por favor, complete todos los campos.")
                else:
                    user = get_user_by_email(l_email)
                    # user[3] es el password_hash (columnas: Id_user, role_id, email, password_hash, ...)
                    if user and verify_password(l_pass, user[3]):
                        st.session_state["logged_in"] = True
                        st.session_state["user_data"] = {
                            "Id_user": user[0],
                            "email": user[2],
                            "full_name": user[6],
                            "DUI": user[5],
                            "phone_number": user[7]
                        }
                        st.toast(f"¡Bienvenido, {user[6]}!", icon='✅')
                        time.sleep(1)
                        st.switch_page("pages/home_page.py")
                    else:
                        st.error("Credenciales incorrectas.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- SECCIÓN: REGISTRO ---
with tab_registro:
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown("#### Formulario de Registro")
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        reg_name = st.text_input("Nombre Completo", key="r_name", on_change=clean_name_input, args=("r_name",))
        reg_email = st.text_input("Correo Electrónico", key="r_email_field")
        raw_dui = st.text_input("Número de DUI", max_chars=9, key="r_dui", on_change=clean_numeric_input, args=("r_dui",))
        dui_f = f"{raw_dui[:8]}-{raw_dui[8:]}" if len(raw_dui) == 9 else ""
        if dui_f: st.caption(f"DUI: :blue[{dui_f}]")
    with r_col2:
        raw_tel = st.text_input("Teléfono", max_chars=8, key="r_phone", on_change=clean_numeric_input, args=("r_phone",))
        tel_f = f"+503 {raw_tel[:4]}-{raw_tel[4:]}" if len(raw_tel) == 8 else ""
        if tel_f: st.caption(f"Tel: :blue[{tel_f}]")
        reg_pass = st.text_input("Contraseña", type="password", key="r_pass_field")
        reg_conf = st.text_input("Confirmar Contraseña", type="password", key="r_conf_field")
    
    gen = st.selectbox("Género", ["Masculino", "Femenino", "Otro"], key="r_gender")
    
    if st.button("REGISTRAR CUENTA"):
        if reg_pass != reg_conf: st.warning("Las contraseñas no coinciden.")
        elif not reg_name or not reg_email: st.warning("Faltan datos obligatorios.")
        else:
            try:
                if get_user_by_email(reg_email): st.error("Email ya registrado.")
                else:
                    h = hash_password(reg_pass)
                    u_id = create_user(2, reg_email, h, None, dui_f, reg_name, gen[0], tel_f)
                    create_account_for_user(u_id, "USD")
                    st.success("✅ ¡Cuenta abierta con éxito!")
                    st.balloons()
            except Exception as e: st.error(f"Error: {e}")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="footer-text">© 2026 Synapse El Salvador.</div>', unsafe_allow_html=True)