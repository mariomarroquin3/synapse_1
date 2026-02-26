import streamlit as st
import sys
import os
import re
import time

# --- FIX DE RUTAS ---
# Asegura que el sistema encuentre los módulos en la carpeta raíz del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- IMPORTACIONES DE SERVICIOS Y MODELOS ---
from models.user_model import (
    create_user, 
    get_user_by_email, 
    get_user_by_dui, 
    get_user_by_phone
)
from services.account_service import create_account_for_user # Integrado desde lógica de test
from utils.security import hash_password, verify_password

st.set_page_config(page_title="Synapse 1.0 - Banking System", page_icon="🏦", layout="centered")

# --- FUNCIONES DE LIMPIEZA Y VALIDACIÓN (TIEMPO REAL) ---
def clean_numeric_input(key):
    """Elimina cualquier carácter no numérico en tiempo real."""
    value = st.session_state[key]
    clean_value = "".join(filter(str.isdigit, value))
    if value != clean_value:
        st.session_state[key] = clean_value

def clean_name_input(key):
    """Elimina números y símbolos del nombre en tiempo real."""
    value = st.session_state[key]
    clean_value = "".join(re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', value))
    if value != clean_value:
        st.session_state[key] = clean_value

st.title("Welcome to Synapse 1.0")

# Pestañas principales
tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])

# --- SECCIÓN DE LOGIN ---
with tab1:
    st.header("Login")
    with st.form("login_form"):
        login_email = st.text_input("Correo Electrónico")
        login_password = st.text_input("Contraseña", type="password")
        submit_login = st.form_submit_button("Entrar", use_container_width=True)

    if submit_login:
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_regex, login_email):
            st.error("❌ Por favor, ingresa un correo electrónico válido.")
        else:
            user = get_user_by_email(login_email)
            
            if not user:
                st.error("❌ El correo electrónico no está registrado.")
            else:
                if verify_password(login_password, user.password_hash):
                    st.success(f"¡Bienvenido de nuevo, {user.full_name}!")
                    st.session_state["logged_in"] = True
                else:
                    st.error("❌ Contraseña inválida.")
                    
# --- SECCIÓN DE REGISTRO ---
with tab2:
    st.header("Crear Cuenta")
    col1, col2 = st.columns(2)
    
    with col1:
        new_name = st.text_input("Nombre Completo", key="reg_name", on_change=clean_name_input, args=("reg_name",))
        new_email = st.text_input("Correo Electrónico", key="reg_email")
        
        raw_dui = st.text_input("DUI (solo números)", max_chars=9, key="reg_dui", on_change=clean_numeric_input, args=("reg_dui",))
        dui_ready = f"{raw_dui[:8]}-{raw_dui[8:]}" if len(raw_dui) == 9 else ""
        if dui_ready: st.caption(f"✅ Formato: {dui_ready}")

    with col2:
        raw_phone = st.text_input("Teléfono (solo números)", max_chars=8, key="reg_phone", on_change=clean_numeric_input, args=("reg_phone",))
        phone_ready = f"{raw_phone[:4]}-{raw_phone[4:]}" if len(raw_phone) == 8 else ""
        if phone_ready: st.caption(f"✅ Formato: {phone_ready}")

        new_pass = st.text_input("Contraseña", type="password", key="reg_pass")
        confirm_pass = st.text_input("Confirmar Contraseña", type="password", key="reg_confirm")

    selected_gender = st.selectbox("Género", ["Masculino", "Femenino"], key="reg_gender")
    gender_letter = "M" if selected_gender == "Masculino" else "F"

    if st.button("Registrar Usuario", use_container_width=True):
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_regex, new_email):
            st.error("❌ Por favor, ingresa un correo electrónico válido.")
        elif len(raw_dui) != 9 or len(raw_phone) != 8:
            st.error("❌ El DUI o el Teléfono están incompletos.")
        elif not new_name:
            st.error("❌ El nombre completo es obligatorio.")
        elif new_pass != confirm_pass:
            st.warning("⚠️ Las contraseñas no coinciden.")
        elif len(new_pass) < 6:
            st.warning("⚠️ La contraseña debe tener al menos 6 caracteres.")
        else:
            try:
                # Validaciones de duplicados
                if get_user_by_email(new_email):
                    st.error(f"❌ El correo '{new_email}' ya está registrado.")
                elif get_user_by_dui(dui_ready):
                    st.error(f"❌ El DUI '{dui_ready}' ya está registrado.")
                elif get_user_by_phone(phone_ready):
                    st.error(f"❌ El número de teléfono '{phone_ready}' ya está registrado.")
                else:
                    # Lógica integrada del test_create_user
                    hashed = hash_password(new_pass)
                    
                    # 1. Crear usuario y obtener ID
                    new_user_id = create_user(
                        role_id=2, 
                        email=new_email, 
                        password_hash=hashed,
                        nit=None, 
                        dui=dui_ready, 
                        full_name=new_name,
                        gender=gender_letter, 
                        phone_number=phone_ready
                    )
                    
                    # 2. Crear cuenta bancaria asociada
                    create_account_for_user(new_user_id, "USD")

                    st.success(f"✅ ¡Registro exitoso! Usuario creado con ID: {new_user_id} y cuenta USD activa.")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Error inesperado: {e}")
                #nahum test