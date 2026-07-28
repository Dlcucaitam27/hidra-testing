import streamlit as st
from data.mongo.usuarios_repo import (
    obtener_usuario,
    verificar_password,
    hashear_password,
    actualizar_password,
    _migrar_a_bcrypt,
)
from configuration.settings import defaults


def obtener_siguiente_id(hoja):
    return hoja.count() + 1


def verificar_credenciales(username, password):
    """
    Verifica las credenciales del usuario.
    Si el hash guardado es SHA-256 (legado), lo migra automáticamente a bcrypt.
    """
    usuario = obtener_usuario(username)
    if not usuario:
        return False, None, False, False
    try:
        if "password_hash" not in usuario:
            st.error("La colección de usuarios no tiene el formato correcto.")
            return False, None, False, False

        es_valida, es_legado = verificar_password(password, usuario["password_hash"])

        if es_valida:
            # Migración silenciosa SHA-256 → bcrypt al primer login
            if es_legado:
                _migrar_a_bcrypt(username, password)

            debe_cambiar = str(usuario.get("debe_cambiar_password", "FALSE")).upper() == "TRUE"
            es_admin     = str(usuario.get("es_admin", "FALSE")).upper() == "TRUE"
            return True, usuario.get("nombre_completo", username), debe_cambiar, es_admin

        return False, None, False, False

    except Exception as e:
        st.error(f"Error en verificación: {str(e)}")
        return False, None, False, False


def logout():
    for key in defaults:
        st.session_state[key] = defaults[key]
    st.rerun()
