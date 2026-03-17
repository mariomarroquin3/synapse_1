import streamlit as st

def apply_premium_style():
    """
    Inyecta un sistema de diseño premium (CSS) en la aplicación Streamlit.
    Adaptado para imitar la UI de Synapse Private Banking.
    """
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        :root {
            --primary: #2563EB;
            --secondary: #3B82F6;
            --bg-main: #0F0F13;
            --bg-card: rgba(22, 22, 26, 0.6);
            --text-primary: #FFFFFF;
            --text-secondary: #9CA3AF;
            --border-color: rgba(255, 255, 255, 0.08);
            --glass: rgba(255, 255, 255, 0.03);
            --glass-border: rgba(255, 255, 255, 0.1);
        }

        /* Tipografía Global - Más específica para evitar romper iconos */
        html, body, .stApp {
            font-family: 'Inter', sans-serif !important;
            background-color: var(--bg-main) !important;
        }

        /* Header default y footers out */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            border: none !important;
            display: none !important;
        }
        footer {display: none !important;}

        /* App Background gradients */
        .stApp {
            background: radial-gradient(circle at 15% 50%, rgba(37, 99, 235, 0.05), transparent 25%),
                        radial-gradient(circle at 85% 30%, rgba(255, 255, 255, 0.02), transparent 25%),
                        #0F0F13 !important;
        }

        /* Sidebar Moderno */
        section[data-testid="stSidebar"] {
            background-color: #0A0A0E !important;
            border-right: 1px solid var(--border-color);
            width: 280px !important;
            min-width: 280px !important;
        }
        
        /* Ocultar navegación por defecto */
        [data-testid="stSidebarNav"] {
            display: none !important;
        }
        
        /* Remover el padding superior innecesario en la página principal */
        .block-container {
            padding-top: 2rem !important;
            max-width: 1200px !important;
        }

        /* Botones Base */
        .stButton > button {
            border-radius: 12px !important;
            padding: 10px 24px !important;
            font-weight: 600 !important;
            letter-spacing: 0.3px !important;
            transition: all 0.2s ease !important;
            border: 1px solid var(--border-color) !important;
            position: relative;
            overflow: hidden;
        }

        /* Botón Primario */
        .stButton > button[kind="primary"] {
            background: var(--primary) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3) !important;
        }
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5) !important;
            background: var(--secondary) !important;
        }

        /* Botón Secundario - Cerrar Sesión en Sidebar */
        .stButton > button[kind="secondary"] {
            background: transparent !important;
            border: none !important;
            color: var(--text-secondary) !important;
            font-weight: 500 !important;
            justify-content: flex-start !important;
            padding: 0 !important;
        }
        .stButton > button[kind="secondary"]:hover {
            color: white !important;
            background: transparent !important;
        }
        .stButton > button[kind="secondary"]::before {
            content: '\\e908'; /* Un icono simple o similar si quieres font icons, ideal SVG en HTML */
        }

        /* Formularios y Cajas de Texto */
        div[data-testid="stForm"] {
            background: var(--bg-card) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 20px !important;
            padding: 24px !important;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
        }

        /* Input Fields */
        .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"] {
            background-color: rgba(0, 0, 0, 0.3) !important;
            border-radius: 10px !important;
            border: 1px solid var(--border-color) !important;
            color: var(--text-primary) !important;
            padding: 10px 16px !important;
        }

        .stTextInput input:focus {
            border-color: var(--primary) !important;
            outline: none !important;
            box-shadow: 0 0 0 1px var(--primary) !important;
        }

        /* Divider elegante */
        .stDivider hr {
            border-top: 1px solid var(--border-color) !important;
            margin: 1.5rem 0 !important;
        }
        
        /* Metric custom hiding default */
        div[data-testid="stMetric"] {
            display: none !important;
        }

        /* Scrollbar Personalizada */
        ::-webkit-scrollbar {
            width: 6px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: #2D2D35;
            border-radius: 10px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #4A4A57;
        }
        </style>
    """, unsafe_allow_html=True)

def render_dashboard_card(balance, account_number):
    """
    Renderiza la tarjeta de balance principal con el estilo glassmorphism.
    """
    card_html_content = f"""
    <div style="background: rgba(22, 22, 26, 0.95); border-radius: 20px; padding: 28px 32px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); position: relative; overflow: hidden; margin-bottom: 20px; max-width: 580px;">
        <!-- Watermark Bank Icon SVG -->
        <svg style="position: absolute; right: -20px; bottom: 10px; width: 250px; height: 250px; opacity: 0.03; fill: white;" viewBox="0 0 24 24">
            <path d="M4 10h3v7H4zM10.5 10h3v7h-3zM2 19h20v3H2zM17 10h3v7h-3zM12 1L2 6v2h20V6z"/>
        </svg>
        <p style="color: #8B8B9B; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; font-weight: 500;">Balance Disponible</p>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <p style="color: #9CA3AF; font-size: 0.95rem; margin: 0; font-family: monospace;">{account_number} &bull; Corriente</p>
            <span style="background: rgba(255, 255, 255, 0.1); padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; color: #D1D5DB;">USD</span>
        </div>
        <h1 style="color: #FFFFFF; font-size: 4.8rem; font-weight: 800; margin: 0; margin-top: -10px; letter-spacing: -2px;">
            ${balance:,.2f}
        </h1>
        <!-- Action Buttons Container (visual only, actual clicks will be Streamlit columns under it) -->
        <div style="display: flex; gap: 40px; margin-top: 36px; padding-left: 10px;">
            <!-- Transferir -->
            <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                <div style="width: 64px; height: 64px; border-radius: 18px; background: rgba(37, 99, 235, 0.1); display: flex; align-items: center; justify-content: center; border: 1px solid rgba(37, 99, 235, 0.15);">
                    <div style="background: #2563EB; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                        <svg width="18" height="18" fill="white" viewBox="0 0 24 24"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </div>
                </div>
                <span style="color: #9CA3AF; font-size: 0.75rem; font-weight: 500;">Transferir</span>
            </div>
            <!-- Cajero ATM -->
            <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                <div style="width: 64px; height: 64px; border-radius: 18px; background: rgba(168, 85, 247, 0.1); display: flex; align-items: center; justify-content: center; border: 1px solid rgba(168, 85, 247, 0.15);">
                    <div style="background: #9333EA; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                        <svg width="18" height="18" fill="white" viewBox="0 0 24 24"><path d="M4 10h3v7H4zM10.5 10h3v7h-3zM2 19h20v3H2zM17 10h3v7h-3zM12 1L2 6v2h20V6z"/></svg>
                    </div>
                </div>
                <span style="color: #9CA3AF; font-size: 0.75rem; font-weight: 500; text-align: center;">Cajero<br>ATM</span>
            </div>
            <!-- Pagar -->
            <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                <div style="width: 64px; height: 64px; border-radius: 18px; background: rgba(16, 185, 129, 0.1); display: flex; align-items: center; justify-content: center; border: 1px solid rgba(16, 185, 129, 0.15);">
                    <div style="background: #059669; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                        <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="white"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/></svg>
                    </div>
                </div>
                <span style="color: #9CA3AF; font-size: 0.75rem; font-weight: 500;">Pagar</span>
            </div>
            <!-- Tarjetas -->
            <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                <div style="width: 64px; height: 64px; border-radius: 18px; background: rgba(249, 115, 22, 0.1); display: flex; align-items: center; justify-content: center; border: 1px solid rgba(249, 115, 22, 0.15);">
                    <div style="background: #E85D04; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                        <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="white"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/></svg>
                    </div>
                </div>
                <span style="color: #9CA3AF; font-size: 0.75rem; font-weight: 500;">Tarjetas</span>
            </div>
        </div>
    </div>
    """
    card_html_content = "".join([line.strip() for line in card_html_content.split('\n')])
    st.markdown(card_html_content, unsafe_allow_html=True)


