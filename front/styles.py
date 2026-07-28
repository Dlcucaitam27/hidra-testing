import streamlit as st
def inyectar_css_selector():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');
        .stApp { background: #0F0A1F; }
        #MainMenu, footer, header { visibility: hidden; }
        ._terminalButton_rix23_138,
        button[data-testid="manage-app-button"] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            position: absolute !important;
            pointer-events: none !important;
        }
        .btn-individual > button, .btn-colectivo > button {
            width: 100% !important; min-height: 340px !important;
            border-radius: 4px !important; border: 1px solid !important;
            transition: all 0.3s ease !important;
            font-family: 'Bebas Neue', sans-serif !important;
            letter-spacing: 3px !important; font-size: 28px !important;
        }
        .btn-individual > button {
            background: linear-gradient(145deg, #1A1A2E 0%, #16213E 50%, #0F3460 100%) !important;
            border-color: rgba(79, 139, 255, 0.3) !important; color: #E8EEFF !important;
        }
        .btn-individual > button:hover {
            border-color: rgba(79, 139, 255, 0.7) !important;
            box-shadow: 0 20px 60px rgba(79, 139, 255, 0.2) !important;
        }
        .btn-colectivo > button {
            background: linear-gradient(145deg, #1A1A1A 0%, #1E2A1E 50%, #0A3D0A 100%) !important;
            border-color: rgba(74, 222, 128, 0.25) !important; color: #E8FFE8 !important;
        }
        .btn-colectivo > button:hover {
            border-color: rgba(74, 222, 128, 0.6) !important;
            box-shadow: 0 20px 60px rgba(74, 222, 128, 0.15) !important;
        }
        .stButton > button[kind="secondary"] {
            background: transparent !important; border: 1px solid #333 !important; color: #666 !important;
        }
        .block-container {
            padding-top: 15px !important;
            padding-bottom: 15px !important;
        }
        /* Labels de widgets (selectbox, number_input, text_area, date, multiselect, etc.) */
        div[data-testid="stWidgetLabel"] p,
        div[data-testid="stWidgetLabel"] label,
        .stTextInput label, .stSelectbox label,
        .stNumberInput label, .stTextArea label,
        .stDateInput label, .stMultiSelect label,
        .stRadio label, .stCheckbox label {
            color: #D4D4D4 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("""
        <script>
            const observer = new MutationObserver(() => {
                const btn = document.querySelector('[data-testid="manage-app-button"]');
                if (btn) btn.style.display = 'none';
            });
            observer.observe(document.body, { childList: true, subtree: true });
        </script>
    """, unsafe_allow_html=True)
