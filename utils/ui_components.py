import streamlit as st

def apply_premium_style():
    """
    Inyecta un sistema de diseño premium (CSS) en la aplicación Streamlit.
    """
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        
        :root {
            --primary: #3B82F6;
            --secondary: #60A5FA;
            --bg-main: #000000;
            --bg-card: #111111;
            --text-primary: #FFFFFF;
            --text-secondary: #94A3B8;
            --border-color: #222222;
            --accent: #10B981;
            --glass: rgba(255, 255, 255, 0.03);
            --glass-border: rgba(255, 255, 255, 0.1);
        }

        /* Tipografía Global - Más específica para evitar romper iconos */
        html, body, .stApp {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        /* Estilo general de la App */
        .stApp {
            background-color: var(--bg-main);
            color: var(--text-primary);
        }

        /* Sidebar Moderno */
        [data-testid="stSidebar"] {
            background-color: var(--bg-card) !important;
            border-right: 1px solid var(--border-color);
        }
        
        /* Ocultar navegación por defecto */
        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* Botones 'Premium' Base */
        .stButton > button {
            border-radius: 12px !important;
            padding: 10px 24px !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            border: 1px solid transparent !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 8px !important;
        }

        /* Botón Primario (Bootstrap-like Primary) */
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #3B82F6 0%, #1E40AF 100%) !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
        }
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 20px rgba(59, 130, 246, 0.5) !important;
            background: linear-gradient(135deg, #60A5FA 0%, #3B82F6 100%) !important;
        }

        /* Botón Secundario (Bootstrap-like Secondary) */
        .stButton > button[kind="secondary"] {
            background: var(--bg-card) !important;
            border: 1px solid var(--border-color) !important;
            color: var(--text-primary) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
        }
        .stButton > button[kind="secondary"]:hover {
            background: #1A1A1A !important;
            border-color: var(--text-secondary) !important;
            transform: translateY(-2px) !important;
        }

        /* Botón de Éxito (Success) */
        .btn-success .stButton > button {
            background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
        }
        .btn-success .stButton > button:hover {
            box-shadow: 0 8px 20px rgba(16, 185, 129, 0.5) !important;
            background: linear-gradient(135deg, #34D399 0%, #10B981 100%) !important;
        }

        /* Botón de Peligro (Danger) */
        .btn-danger .stButton > button {
            background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%) !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3) !important;
        }
        .btn-danger .stButton > button:hover {
            box-shadow: 0 8px 20px rgba(239, 68, 68, 0.5) !important;
            background: linear-gradient(135deg, #F87171 0%, #EF4444 100%) !important;
        }
        
        .stButton > button:active {
            transform: scale(0.98) !important;
        }

        /* Tarjetas (Cards) de Información */
        div[data-testid="stMetric"], div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--bg-card) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 20px !important;
            padding: 20px !important;
            transition: border-color 0.3s ease;
        }

        div[data-testid="stMetric"]:hover {
            border-color: var(--primary) !important;
        }

        /* Formularios */
        div[data-testid="stForm"] {
            background: var(--bg-card) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 24px !important;
            padding: 2rem !important;
        }

        /* Input Fields */
        .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"] {
            background-color: #0A0A0A !important;
            border-radius: 12px !important;
            border: 1px solid var(--border-color) !important;
            color: var(--text-primary) !important;
            padding: 8px 12px !important;
        }

        .stTextInput input:focus {
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            margin-bottom: 2rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px !important;
            padding: 10px 20px !important;
            background-color: transparent !important;
            color: var(--text-secondary) !important;
            border: 1px solid transparent !important;
        }

        .stTabs [aria-selected="true"] {
            background-color: var(--glass) !important;
            color: var(--primary) !important;
            border: 1px solid var(--glass-border) !important;
            font-weight: 700 !important;
        }

        /* Divider */
        .stDivider {
            border-color: var(--border-color) !important;
            margin: 2rem 0 !important;
        }

        /* Scrollbar Personalizada */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: var(--bg-main);
        }
        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 10px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #333;
        }
        </style>
    """, unsafe_allow_html=True)

def card_html(title, content, subtext="", color="var(--primary)"):
    """
    Retorna un componente HTML para una tarjeta personalizada.
    """
    st.markdown(f"""
        <div style="
            background: var(--bg-card);
            border-left: 4px solid {color};
            padding: 20px;
            border-radius: 12px;
            border-top-right-radius: 20px;
            border-bottom-right-radius: 20px;
            border: 1px solid var(--border-color);
            margin-bottom: 15px;
        ">
            <p style="color: var(--text-secondary); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;">{title}</p>
            <h2 style="color: var(--text-primary); margin: 0; font-weight: 800;">{content}</h2>
            <p style="color: #6B7280; font-size: 0.75rem; margin-top: 5px;">{subtext}</p>
        </div>
    """, unsafe_allow_html=True)
