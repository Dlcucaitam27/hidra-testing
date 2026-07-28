import streamlit as st
import os

_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "front", "logo_hidra.png")

from configuration.settings import defaults
from service.auth_service import logout
from front.pages import (
    login_page,
    pantalla_cambiar_password,
    pantalla_selector,
    formulario_casos,
    panel_visualizacion,
    panel_gestion_usuarios,
    pantalla_recovery_solicitar,
    pantalla_recovery_verificar,
    pantalla_recovery_nueva_password,
)

st.set_page_config(page_title="HIDRA", page_icon="💧", layout="centered")

from front.styles import inyectar_css_selector
inyectar_css_selector()

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# Inicializar estado de recuperación si no existe
if "vista_recovery" not in st.session_state:
    st.session_state.vista_recovery = None
if "recovery_username" not in st.session_state:
    st.session_state.recovery_username = None
if "recovery_codigo_ok" not in st.session_state:
    st.session_state.recovery_codigo_ok = False


def main():
    # ── Flujo de recuperación (tiene prioridad sobre login) ───────────────────
    vista_rec = st.session_state.get("vista_recovery")
    if vista_rec == "solicitar":
        pantalla_recovery_solicitar(); return
    if vista_rec == "verificar":
        pantalla_recovery_verificar(); return
    if vista_rec == "nueva_password":
        pantalla_recovery_nueva_password(); return

    # ── Flujo normal ──────────────────────────────────────────────────────────
    if not st.session_state.autenticado:
        login_page(); return

    if st.session_state.debe_cambiar_password:
        pantalla_cambiar_password(); return

    if st.session_state.es_admin:
        st.sidebar.image(_LOGO, width=200)
        st.sidebar.success(f"👤 {st.session_state.nombre_completo}")
        st.sidebar.markdown("---")
        opcion = st.sidebar.radio("Menú", ["🏠 Inicio", "📊 Ver Datos", "👥 Gestionar Usuarios"])
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True): logout()
        vista = st.session_state.get("vista")
        if   vista == "individual":          formulario_casos("individual")
        elif vista == "colectivo":           formulario_casos("colectivo")
        elif opcion == "🏠 Inicio":          pantalla_selector()
        elif opcion == "📊 Ver Datos":       panel_visualizacion()
        else:                                panel_gestion_usuarios()
        return

    vista = st.session_state.vista
    if   vista is None:         pantalla_selector()
    elif vista == "individual": formulario_casos("individual")
    elif vista == "colectivo":  formulario_casos("colectivo")


if __name__ == "__main__":
    main()
