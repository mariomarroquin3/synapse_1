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
    get_user_by_phone,
    get_user_by_nit
)
from services.account_service import create_account_for_user
from utils.security import hash_password, verify_password, validate_password
from utils.ui_components import apply_premium_style
from models.account_model import get_account_by_user

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Synapse | Banca Digital", page_icon="🏦", layout="centered")

# --- APLICAR TU DISEÑO PREMIUM BASE ---
apply_premium_style()

# --- CSS MINIMALISTA EXCLUSIVO PARA CENTRAR EL LOGIN Y FONDO ---
st.markdown("""
<style>
/* Fondo Animado Dark Mesh */
    .stApp {
        background-color: #05070A !important;
        background-image: 
            radial-gradient(circle at 15% 50%, rgba(30, 58, 138, 0.35), transparent 50%), 
            radial-gradient(circle at 85% 30%, rgba(49, 46, 129, 0.35), transparent 50%), 
            radial-gradient(circle at 50% 80%, rgba(120, 53, 15, 0.25), transparent 50%) !important;
        background-size: 200% 200% !important;
        animation: meshGradient 2s ease infinite !important;
        background-attachment: fixed !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    @keyframes meshGradient {
        0% { background-position: 0% 0%; }
        50% { background-position: 100% 100%; }
        100% { background-position: 0% 0%; }
    }

/* TARJETA GLASSMORPHISM (Atrapada en la columna central exacta) */
    div[data-testid="column"]:nth-of-type(2) {
        background: rgba(15, 15, 20, 0.65) !important;
        backdrop-filter: blur(25px) !important;
        -webkit-backdrop-filter: blur(25px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 24px !important;
        padding: 45px 40px !important;
        box-shadow: 0 25px 60px rgba(0, 0, 0, 0.6) !important;
        margin-top: 8vh !important;
    }
    /* Quitar bordes por defecto del form de Streamlit para no duplicar */
    [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }

    /* 2. FORZAR TAMAÑO DEL LOGO - PASO 2: CSS de Imagen */
    .logo-container img {
        width: 900px !important;
        max-width: none !important;
        display: block;
        margin: 0 auto !important;
    }

    /* 3. CSS de Contenedor: Asegurar alineación y eliminar padding excesivo */
    [data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }
    /* Eliminar padding excesivo en columnas */
    div[data-testid="column"] {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    /* Ajuste específico para la columna central */
    div[data-testid="column"]:nth-of-type(2) {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }

    /* Ajustes de Layout */
    .block-container { 
        padding-top: 3rem !important; 
        max-width: 500px !important; 
    }
    
    .stTabs [data-baseweb="tab-list"] { 
        justify-content: center; 
        background-color: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 5px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE LIMPIEZA MANUAL ---
def get_clean_numeric(text):
    return "".join(filter(str.isdigit, text))

def get_clean_name(text):
    return "".join(re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', text))

# --- RENDERIZADO DEL LOGO ---
logo_path = "img/Synapsebank.png" 

# Proporción ajustada para hacer el logo más grande
col_izq, col_centro, col_der = st.columns([1, 1, 1])
with col_centro:
    # Contenedor HTML: Envuelve la llamada de st.image dentro de un st.markdown con un div que tenga la clase logo-container
    if os.path.exists(logo_path):
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image(logo_path, use_container_width=False)
        st.markdown('</div>', unsafe_allow_html=True)
    elif os.path.exists("img/Synapsebank.jpg"):
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image("img/Synapsebank.jpg", use_container_width=False)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Fallback visual elegante si no encuentra la imagen
        st.markdown("""
        <div class="logo-container" style='background: linear-gradient(135deg, #2563EB, #3B82F6); width: 80px; height: 80px; border-radius: 16px; margin: 0 auto; display: flex; align-items: center; justify-content: center; box-shadow: 0 10px 20px rgba(37,99,235,0.3);'>
            <span style='color: white; font-size: 36px; font-weight: bold;'>S</span>
        </div>
        """, unsafe_allow_html=True)

# Espacio extra tras eliminar el texto para que no quede muy pegado a las pestañas
st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

# --- TABS DE NAVEGACIÓN ---
tab_login, tab_reg = st.tabs(["🔐 ACCESO", "📝 REGISTRO"])

with tab_login:
    with st.form("login_form_final"):
        st.markdown("<h4 style='text-align:center; margin-bottom:25px; color:var(--text-primary); font-weight:600;'>Inicia Sesión</h4>", unsafe_allow_html=True)

        l_email = st.text_input("Correo electrónico", placeholder="usuario@correo.com")
        l_pass = st.text_input("Contraseña", type="password", placeholder="••••••••")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        submit = st.form_submit_button("ENTRAR AL PORTAL", type="primary", use_container_width=True)

        if submit:
            if not l_email or not l_pass:
                st.warning("Por favor completa tus datos.")
            else:
                user = get_user_by_email(l_email)

                if user and verify_password(l_pass, user['password_hash']):
                    # 🔒 VERIFICAR SI LA CUENTA ESTÁ ACTIVA
                    if not user.get('is_active', True):
                        st.error("❌ Tu cuenta ha sido desactivada o bloqueada. Contacta al banco.")
                        time.sleep(2)
                        st.stop()

                    # 🔎 BUSCAR CUENTA DEL USUARIO
                    account = get_account_by_user(user['Id_user'])

                    if account:
                        status = account["status_id"]
                        # ⏳ CUENTA PENDIENTE
                        if status == 4:
                            st.warning("⏳ Tu cuenta está pendiente de aprobación por el banco.")
                            st.stop()
                        # ❌ CUENTA RECHAZADA
                        if status == 5:
                            st.error("❌ Tu solicitud de cuenta fue rechazada. Contacta al banco.")
                            st.stop()

                    # ✅ LOGIN PERMITIDO
                    st.session_state["logged_in"] = True
                    st.session_state["user_data"] = {
                        "Id_user": user['Id_user'], 
                        "email": user['email'], 
                        "full_name": user['full_name'],
                        "DUI": user.get('dui', user.get('DUI', 'N/A')), 
                        "phone_number": user['phone_number'],
                        "role_id": user['role_id']
                    }

                    st.success("Acceso concedido.")
                    time.sleep(0.5)
                    st.switch_page("pages/home_page.py")
                else:
                    st.error("Credenciales no válidas.")


with tab_reg:
    with st.form("reg_form_final"):
        st.markdown("<h4 style='text-align:center; margin-bottom:25px; color:var(--text-primary); font-weight:600;'>Crea tu cuenta</h4>", unsafe_allow_html=True)
        
        r_col1, r_col2 = st.columns(2)
        with r_col1:
            r_name_raw = st.text_input("Nombre", placeholder="Tu nombre completo")
            r_email = st.text_input("Email", placeholder="tu@correo.com")
            r_dui_raw = st.text_input("DUI", max_chars=9, placeholder="000000000")
            r_nit_raw = st.text_input("NIT para empresas (Opcional)", max_chars=14, placeholder="00000000-0")
        with r_col2:
            r_tel_raw = st.text_input("Teléfono", max_chars=8, placeholder="70000000")
            r_pass = st.text_input("Clave", type="password", placeholder="Clave segura")
            r_conf = st.text_input("Confirmar", type="password", placeholder="Repite tu clave")
            r_gen = st.selectbox("Género", ["Masculino", "Femenino"])
        
        # Validación de contraseña en tiempo real
        if r_pass:
            is_valid, missing_reqs = validate_password(r_pass)
            
            if is_valid:
                st.success("✅ Contraseña cumple todos los requisitos")
            else:
                with st.expander("📋 Requisitos de seguridad", expanded=not is_valid):
                    for requirement in missing_reqs:
                        st.warning(f"❌ {requirement}")
                    
                    st.markdown("**Requisitos cumplidos:**")
                    all_reqs = [
                        ("Mínimo 8 caracteres", len(r_pass) >= 8),
                        ("Al menos una MAYÚSCULA", bool(re.search(r'[A-Z]', r_pass))),
                        ("Al menos una minúscula", bool(re.search(r'[a-z]', r_pass))),
                        ("Al menos un número", bool(re.search(r'[0-9]', r_pass))),
                        ("Carácter especial (!@#$%^&*)", bool(re.search(r'[!@#$%^&*]', r_pass)))
                    ]
                    
                    for req_text, is_met in all_reqs:
                        if is_met:
                            st.write(f"✅ {req_text}")
        
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        
        password_is_valid = False
        if r_pass and r_conf:
            password_is_valid, _ = validate_password(r_pass)
        
        btn_reg = st.form_submit_button(
            "REGISTRARME AHORA", 
            type="primary",
            use_container_width=True,
            disabled=not password_is_valid and len(r_pass) > 0
        )

        if btn_reg:
            clean_name = get_clean_name(r_name_raw)
            clean_dui = get_clean_numeric(r_dui_raw)
            clean_tel = get_clean_numeric(r_tel_raw)
            clean_nit = get_clean_numeric(r_nit_raw) if r_nit_raw else None
            
            if r_pass != r_conf: 
                st.error("Las contraseñas no coinciden.")
            elif not clean_name or not r_email or not clean_dui: 
                st.warning("Faltan datos requeridos o formato inválido.")
            else:
                try:
                    is_valid, missing = validate_password(r_pass)
                    if not is_valid:
                        st.error("❌ La contraseña no cumple los requisitos de seguridad.")
                        st.stop()
                    
                    dui_f = f"{clean_dui[:8]}-{clean_dui[8:]}" if len(clean_dui) == 9 else clean_dui
                    tel_f = f"+503 {clean_tel[:4]}-{clean_tel[4:]}" if len(clean_tel) == 8 else clean_tel
                    nit_f = f"{clean_nit[:8]}-{clean_nit[8:]}" if clean_nit and len(clean_nit) == 9 else (r_nit_raw if r_nit_raw else None)
                    
                    if get_user_by_email(r_email): 
                        st.error("Email ya registrado.")
                    elif get_user_by_phone(tel_f):
                        st.error("Número de teléfono ya registrado.")
                    elif get_user_by_dui(dui_f):
                        st.error("DUI ya registrado.")
                    elif nit_f and get_user_by_nit(nit_f):
                        st.error("NIT ya registrado.")
                    else:
                        h = hash_password(r_pass)
                        u_id = create_user(2, r_email, h, nit_f, dui_f, clean_name, r_gen[0], tel_f)
                        create_account_for_user(u_id, "USD")
                        st.success("¡Bienvenido a Synapse!")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                except Exception as e: 
                    st.error(f"Error en el servidor: {e}")

# --- FOOTER ---
st.markdown("""
    <p style='text-align:center; color:#94A3B8; font-size:0.75rem; margin-top:3rem;'>
        © 2026 Synapse Digital Bank S.A. de C.V.<br>
        Seguridad Bancaria de El Salvador.<br>
        <a href="/admin_login" target="_self" style="color: #64748B; text-decoration: none; font-weight: 600; margin-top: 15px; display: inline-block;">
            🔐 Inicio de sesión de empleados
        </a>
    </p>
""", unsafe_allow_html=True)