import streamlit as st

# Redirect to login page
st.set_page_config(
    page_title="Synapse 1.0 - El Salvador",
    page_icon="🏦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# If user is not logged in, show login page
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.switch_page("pages/login_page.py")
else:
    # If user is logged in, show home page
    st.switch_page("pages/home_page.py")
