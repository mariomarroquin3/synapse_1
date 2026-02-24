import streamlit as st
import sys
import os

# --- FIX DE RUTAS PARA DETECTAR MÓDULOS ---
# Agrega la carpeta raíz (synapse_1) al sistema de búsqueda de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.user_model import create_user, get_user_by_email
from utils.security import hash_password, verify_password

st.set_page_config(page_title="Sistema Bancario - Synapse", page_icon="🏦")

st.title("Welcome to Synapse 1.0")

# Creamos las pestañas para Login y Registro
tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])

# --- SECCIÓN DE LOGIN ---
with tab1:
    st.header("Login")
    with st.form("login_form"):
        login_email = st.text_input("Correo Electrónico")
        login_password = st.text_input("Contraseña", type="password")
        submit_login = st.form_submit_button("Entrar")

    if submit_login:
        user = get_user_by_email(login_email)
        
        if user:
            # Acceso dinámico a columnas de pyodbc Row
            db_password_hash = user.password_hash 
            db_full_name = user.full_name
            
            if verify_password(login_password, db_password_hash):
                st.success(f"Bienvenido de nuevo, {db_full_name}")
                st.session_state["logged_in"] = True
                st.session_state["user_email"] = login_email
            else:
                st.error("Contraseña incorrecta.")
        else:
            st.error("Usuario no encontrado.")

# --- SECCIÓN DE REGISTRO ---
with tab2:
    st.header("Crear Cuenta")
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Nombre Completo")
            new_email = st.text_input("Correo Electrónico")
            new_dui = st.text_input("DUI (ej: 00000000-0)")
            new_nit = st.text_input("NIT (opcional)") # CAMBIO: Añadido NIT
        with col2:
            new_phone = st.text_input("Teléfono")
            new_pass = st.text_input("Contraseña", type="password")
            confirm_pass = st.text_input("Confirmar Contraseña", type="password")
            
        submit_reg = st.form_submit_button("Registrar Usuario")

    if submit_reg:
        if new_pass != confirm_pass:
            st.warning("Las contraseñas no coinciden.")
        elif not new_email or not new_dui or not new_name:
            st.warning("Nombre, Correo y DUI son obligatorios.")
        else:
            try:
                if get_user_by_email(new_email):
                    st.error("Este correo ya está registrado.")
                else:
                    hashed = hash_password(new_pass)
                    # CAMBIO: Ahora pasamos nit e is_active (que por defecto es True)
                    create_user(
                        role_id=2, 
                        email=new_email,
                        password_hash=hashed,
                        nit=new_nit if new_nit else None, # Enviamos el NIT
                        dui=new_dui,
                        full_name=new_name,
                        phone_number=new_phone if new_phone else None
                        # is_active usa su valor por defecto True en la función
                    )
                    st.success("¡Usuario creado con éxito! Ya puedes iniciar sesión.")
            except Exception as e:
                st.error(f"Error al registrar: {e}")