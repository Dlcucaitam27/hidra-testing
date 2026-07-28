import streamlit as st
import hashlib
import time
import calendar
import pandas as pd
import os
import base64
from datetime import datetime, date
from zoneinfo import ZoneInfo

_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "front", "logo_hidra.png")

def _logo_b64():
    with open(_LOGO, "rb") as f:
        return base64.b64encode(f.read()).decode()

_BOGOTA = ZoneInfo("America/Bogota")
from data.diccionarios import (
    _ESTRUCTURAS, _ROLES, _LUGAR_ACREDITACION, _INSTITUCIONES, _PARTICIPACION,
    _MUNICIPIOS, _TIPOS_POBLACION, _SUBPOBLACIONES, _GENEROS, _ORIENTACIONES_SEXUALES,
    _JEFATURA_HOGAR, _SI_NO_REPORTA, _SI_NO, _DISCAPACIDAD, _ETNIA, _CUIDADOR,
    _VICTIMA_CONFLICTO_ARMADO, _LIDER_SOCIAL_DDHH, _ACTIVIDADES_ECONOMICAS_COLECTIVO,
    _FACTORES_DIFER_COL,
    # Perfil Actual
    _PA_NIVEL_EDUCATIVO, _PA_FUENTE_INGRESOS, _PA_ESTADO_PROYECTO_ARN, _PA_ACTIVIDAD_ECONOMICA,
    _PA_MACROCASOS_JEP, _PA_INSTANCIAS_PARTIDO, _PA_ROLES_PARTIDO,
    _PA_CONSEJERIA_NACIONAL, _PA_TIPO_ORG, _PA_AMBITO_ORG, _PA_ESCALA_ORG,
    _PA_CARGO_ELECCION,
    # Antecedentes
    _TIPOS_RUTA_ANTECEDENTE,
    # Hechos de Riesgo
    _TIPOS_HECHO, _TIPOS_ACTOR_GENERADOR, _MEDIOS_HECHO, _VICTIMAS_SITUACION_HECHO, _TIPOS_AMENAZA,
    # Desplazamientos
    _DESP_MOTIVOS, _DESP_MEDIOS_TRANSPORTE, _DESP_FRECUENCIAS,
    _DESP_TIPOS_VIA, _DESP_DEPARTAMENTOS,
    # Verificaciones
    _FUENTES_VERIFICACION, _VER_OPCIONES,
    # Impacto Consecuencial
    _IMPACTO_SI_NR,
)

from configuration.settings import TAB_NOMBRES
from data.mongo.usuarios_repo import actualizar_password, crear_usuario, listar_usuarios, usuario_existe, hashear_password
from data.mongo.casos_repo import conectar_sheet_casos, guardar_borrador, cargar_borrador, eliminar_borrador
from service.auth_service import verificar_credenciales, logout
from front.styles import inyectar_css_selector


def login_page():
    st.markdown(
        f'<div style="display:flex;justify-content:center;margin-bottom:16px;">'
        f'<img src="data:image/png;base64,{_logo_b64()}" width="280"></div>',
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.info("👋 Identifícate para acceder al sistema")
    with st.form("login_form"):
        username = st.text_input("Usuario", placeholder="nombre.apellido")
        password = st.text_input("Contraseña", type="password")
        submit   = st.form_submit_button("🔓 Iniciar Sesión", use_container_width=True, type="primary")
        if submit:
            if username and password:
                ok, nombre, cambiar, admin = verificar_credenciales(username, password)
                if ok:
                    st.session_state.autenticado           = True
                    st.session_state.username              = username
                    st.session_state.nombre_completo       = nombre
                    st.session_state.debe_cambiar_password = cambiar
                    st.session_state.es_admin              = admin
                    st.session_state.hechos                = []
                    st.rerun()
                else: st.error("❌ Usuario o contraseña incorrectos")
            else: st.warning("⚠️ Por favor completa todos los campos")

    # ── Link de recuperación ──────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _, col_rec = st.columns([3, 2])
    with col_rec:
        if st.button("¿Olvidaste tu contraseña?", type="secondary", use_container_width=True):
            st.session_state.vista_recovery = "solicitar"
            st.rerun()

    st.caption("🔒 Si tienes problemas, contacta al administrador")


def pantalla_cambiar_password():
    st.markdown(
        f'<div style="display:flex;justify-content:center;margin-bottom:16px;">'
        f'<img src="data:image/png;base64,{_logo_b64()}" width="220"></div>',
        unsafe_allow_html=True
    )
    st.title("🔐 Cambio de Contraseña Obligatorio")
    st.markdown("---")
    st.warning("⚠️ Debes cambiar tu contraseña antes de continuar")
    st.info(f"👤 Usuario: **{st.session_state.username}**")
    with st.form("cambiar_password_form"):
        nueva     = st.text_input("Nueva Contraseña", type="password", help="Mínimo 8 caracteres")
        confirmar = st.text_input("Confirmar Contraseña", type="password")
        st.caption("💡 Usa una contraseña segura con letras, números y símbolos")
        submit = st.form_submit_button("✅ Cambiar Contraseña", use_container_width=True, type="primary")
        if submit:
            errores = []
            if not nueva: errores.append("La contraseña no puede estar vacía")
            elif len(nueva) < 8: errores.append("La contraseña debe tener mínimo 8 caracteres")
            if nueva != confirmar: errores.append("Las contraseñas no coinciden")
            if errores:
                for e in errores: st.error(f"❌ {e}")
            else:
                nuevo_hash = hashear_password(nueva)
                if actualizar_password(st.session_state.username, nuevo_hash, False):
                    st.session_state.debe_cambiar_password = False
                    st.success("✅ ¡Contraseña actualizada!")
                    time.sleep(1); st.rerun()
                else: st.error("❌ Error al actualizar. Intenta de nuevo.")


def pantalla_selector():
    import html as _html
    inyectar_css_selector()
    nombre = st.session_state.nombre_completo or "Analista"
    nombre_corto = _html.escape(nombre.split()[0] if nombre else "Analista")
    st.markdown(f"""
    <div style="text-align:center; margin-bottom:48px; margin-top:20px;">
        <p style="font-family:'DM Sans',sans-serif; font-weight:300; font-size:13px;
                  letter-spacing:4px; text-transform:uppercase; color:#555; margin-bottom:6px;">BIENVENIDO</p>
        <p style="font-family:'Bebas Neue',sans-serif; font-size:clamp(28px,5vw,40px);
                  letter-spacing:3px; color:#F0F0F0; margin:0;">{nombre_corto}</p>
        <p style="font-size:12px; color:#444; letter-spacing:1px; margin-top:6px;">SELECCIONA EL TIPO DE FORMULARIO</p>
    </div>""", unsafe_allow_html=True)
    st.markdown(
        f'<div style="display:flex;justify-content:center;margin-bottom:32px;">'
        f'<img src="data:image/png;base64,{_logo_b64()}" width="200"></div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.markdown('<div style="text-align:center;margin-bottom:12px;"><span style="font-size:32px;">👤</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="btn-individual">', unsafe_allow_html=True)
        if st.button("FORMULARIO\nINDIVIDUAL", key="btn_individual", use_container_width=True):
            st.session_state.vista = "individual"
            st.session_state.hechos = []
            st.session_state.perfiles = []
            st.session_state.perfiles_col = []
            st.session_state.perfiles_actuales = []
            st.session_state.desplazamientos = []
            st.session_state.composiciones_col = []
            st.session_state.antecedentes = []
            st.session_state["borrador_cargado_individual"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;font-size:11px;color:#444;margin-top:10px;">Un caso por registro</p>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div style="text-align:center;margin-bottom:12px;"><span style="font-size:32px;">👥</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="btn-colectivo">', unsafe_allow_html=True)
        if st.button("FORMULARIO\nCOLECTIVO", key="btn_colectivo", use_container_width=True):
            st.session_state.vista = "colectivo"
            st.session_state.hechos = []
            st.session_state.perfiles = []
            st.session_state.perfiles_col = []
            st.session_state.perfiles_actuales = []
            st.session_state.desplazamientos = []
            st.session_state.composiciones_col = []
            st.session_state.antecedentes = []
            st.session_state["borrador_cargado_colectivo"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;font-size:11px;color:#444;margin-top:10px;">Múltiples personas afectadas</p>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, col_logout, _ = st.columns([2, 1, 2])
    with col_logout:
        if st.button("🚪 Cerrar sesión", use_container_width=True, type="secondary"): logout()


def _render_pa_form(pa, tipo, idx, es_reincorporado, es_familiar_reincorporado, es_familiar_comunes, mostrar_cargo_comunes, es_colectivo=False):
    """
    Renderiza los campos de Perfil Actual según tipo de población.

    Lógica de visibilidad:
    - REINCORPORADO/A              → es_reincorporado=True
                                     → muestra sección perfil (sin ARN ni Act.Eco.)
    - FAMILIAR DE REINCORPORADO/A  → ningún campo extra aquí
                                     (sus campos están en la subsección del formulario principal)
    - INTEGRANTE DEL PARTIDO       → mostrar_cargo_comunes=True
    - FAMILIAR DE INTEGRANTE       → es_familiar_comunes=True, mostrar_cargo_comunes=True
                                     → muestra sección perfil (sin ARN ni Act.Eco.)
    - COLECTIVO                    → es_colectivo=True
                                     → sin nivel educativo ni fuente ingresos
                                     → JEP y TOAR como conteos numéricos

    ARN y Actividad Económica se muestran en la subsección del formulario principal,
    solo cuando tipo_poblacion == FAMILIAR DE REINCORPORADO/A.
    """
    sfx = f"{tipo}_{idx}"

    def _v(campo, defecto="Seleccione..."):
        return pa.get(campo, defecto) if pa else defecto

    _opts_si_no_rep = ["Seleccione...", "SI", "NO REPORTA"]

    if not es_colectivo:
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("NIVEL DE ESCOLARIDAD", _PA_NIVEL_EDUCATIVO,
                         index=_PA_NIVEL_EDUCATIVO.index(_v("nivel_educativo"))
                               if _v("nivel_educativo") in _PA_NIVEL_EDUCATIVO else 0,
                         key=f"pa_edu_{sfx}")
        with col2:
            st.text_input("FUENTE PRINCIPAL DE INGRESOS",
                          value=_v("fuente_ingresos", ""),
                          key=f"pa_ingresos_{sfx}")

        # JEP — Comparecencia
        st.selectbox("COMPARECENCIA ANTE LA JEP", _opts_si_no_rep,
                     index=_opts_si_no_rep.index(_v("comparecencia_jep"))
                           if _v("comparecencia_jep") in _opts_si_no_rep else 0,
                     key=f"pa_jep_comp_{sfx}")
        if st.session_state.get(f"pa_jep_comp_{sfx}", "Seleccione...") == "SI":
            _mcc_prev = [m.strip() for m in _v("macrocasos_jep", "").split("|") if m.strip()] if pa else []
            st.markdown("**MACROCASO COMPARECIENTE**")
            _cols_mcc = st.columns(2)
            for _j, _mc in enumerate(_PA_MACROCASOS_JEP):
                _cols_mcc[_j % 2].checkbox(_mc, value=(_mc in _mcc_prev), key=f"pa_mcc_{_j}_{sfx}")

        # JEP — Víctima
        st.selectbox("ES VÍCTIMA ANTE LA JEP", _SI_NO_REPORTA,
                     index=_SI_NO_REPORTA.index(_v("victima_jep"))
                           if _v("victima_jep") in _SI_NO_REPORTA else 0,
                     key=f"pa_jep_vic_{sfx}")
        if st.session_state.get(f"pa_jep_vic_{sfx}", "Seleccione...") == "SI":
            _mcv_prev = [m.strip() for m in _v("macrocaso_victima", "").split("|") if m.strip()] if pa else []
            st.markdown("**MACROCASO VÍCTIMA**")
            _cols_mcv = st.columns(2)
            for _j, _mc in enumerate(_PA_MACROCASOS_JEP):
                _cols_mcv[_j % 2].checkbox(_mc, value=(_mc in _mcv_prev), key=f"pa_mcv_{_j}_{sfx}")

        # Compromisos del proceso de paz — TOAR como selectbox
        col7, col8 = st.columns(2)
        with col7:
            st.selectbox("PARTICIPA EN TRABAJOS, OBRAS Y ACTIVIDADES REPARADORAS - TOAR",
                         _SI_NO_REPORTA,
                         index=_SI_NO_REPORTA.index(_v("participacion_toar"))
                               if _v("participacion_toar") in _SI_NO_REPORTA else 0,
                         key=f"pa_toar_{sfx}")
            st.selectbox("PARTICIPA EN ACTIVIDADES DEL PROGRAMA PNIS", _SI_NO_REPORTA,
                         index=_SI_NO_REPORTA.index(_v("participacion_pnis"))
                               if _v("participacion_pnis") in _SI_NO_REPORTA else 0,
                         key=f"pa_pnis_{sfx}")
        with col8:
            st.selectbox("PARTICIPA EN ACTIVIDADES DE BÚSQUEDA DE PERSONAS DADAS POR DESAPARECIDAS",
                         _SI_NO_REPORTA,
                         index=_SI_NO_REPORTA.index(_v("busqueda_desaparecidos"))
                               if _v("busqueda_desaparecidos") in _SI_NO_REPORTA else 0,
                         key=f"pa_busq_{sfx}")
            st.selectbox("PARTICIPA EN ACTIVIDADES DE DESMINADO HUMANITARIO", _SI_NO_REPORTA,
                         index=_SI_NO_REPORTA.index(_v("desminado"))
                               if _v("desminado") in _SI_NO_REPORTA else 0,
                         key=f"pa_desminado_{sfx}")
    else:
        # ── Campos JEP / TOAR para COLECTIVO (conteos numéricos + Sí/No) ──────
        col_jc1, col_jc2, col_jc3 = st.columns(3)
        with col_jc1:
            st.number_input("CANTIDAD DE PERSONAS QUE COMPARECEN ANTE LA JEP",
                            min_value=0, step=1,
                            value=int(_v("col_jep_comp_cnt", 0) or 0),
                            key=f"pa_col_jep_comp_cnt_{sfx}")
        with col_jc2:
            st.number_input("CANTIDAD DE VÍCTIMAS ANTE LA JEP",
                            min_value=0, step=1,
                            value=int(_v("col_jep_vic_cnt", 0) or 0),
                            key=f"pa_col_jep_vic_cnt_{sfx}")
        with col_jc3:
            st.number_input("CANTIDAD DE PARTICIPANTES EN TRABAJOS, OBRAS Y ACTIVIDADES REPARADORAS (TOAR)",
                            min_value=0, step=1,
                            value=int(_v("col_toar_cnt", 0) or 0),
                            key=f"pa_col_toar_cnt_{sfx}")

        col_jp1, col_jp2, col_jp3 = st.columns(3)
        with col_jp1:
            st.number_input("CANTIDAD DE PERSONAS EN ACTIVIDADES DE BÚSQUEDA DE DESAPARECIDOS",
                            min_value=0, step=1,
                            value=int(_v("col_busq_cnt", 0) or 0),
                            key=f"pa_col_busq_cnt_{sfx}")
        with col_jp2:
            st.number_input("CANTIDAD DE PERSONAS EN ACTIVIDADES DEL PROGRAMA PNIS",
                            min_value=0, step=1,
                            value=int(_v("col_pnis_cnt", 0) or 0),
                            key=f"pa_col_pnis_cnt_{sfx}")
        with col_jp3:
            st.number_input("CANTIDAD DE PERSONAS EN ACTIVIDADES DE DESMINADO HUMANITARIO",
                            min_value=0, step=1,
                            value=int(_v("col_desminado_cnt", 0) or 0),
                            key=f"pa_col_desminado_cnt_{sfx}")

    # Otras organizaciones (multiregistro)
    st.selectbox(
        "¿PARTICIPA DE ALGÚN TIPO DE ORGANIZACIÓN SOCIAL, POLÍTICA O INSTANCIA INSTITUCIONAL DIFERENTE A COMUNES?",
        _SI_NO,
        index=_SI_NO.index(_v("participa_otras_org")) if _v("participa_otras_org") in _SI_NO else 0,
        key=f"pa_otras_org_{sfx}"
    )
    _participa_otras = st.session_state.get(f"pa_otras_org_{sfx}", "Seleccione...")
    if _participa_otras == "SI":
        _oo_key = f"otras_orgs_temp_{sfx}"
        if _oo_key not in st.session_state:
            st.session_state[_oo_key] = list(_v("otras_orgs", []) or [])

        st.markdown("**ORGANIZACIONES / INSTANCIAS REGISTRADAS**")
        for _oo_i, _oo_reg in enumerate(st.session_state[_oo_key]):
            with st.container(border=True):
                _oo_col_t, _oo_col_d = st.columns([5, 1])
                with _oo_col_t:
                    if es_colectivo:
                        st.markdown(
                            f"**Org #{_oo_i+1}:** {_oo_reg.get('tipo_org','—')}  |  "
                            f"**Personas:** {_oo_reg.get('num_personas_org', 0)}"
                        )
                        _amb_cnt_disp = ", ".join(
                            f"{k}: {v}" for k, v in _oo_reg.get("ambito_counts", {}).items() if v
                        )
                        if _amb_cnt_disp:
                            st.caption(f"Ámbitos: {_amb_cnt_disp}")
                    else:
                        st.markdown(
                            f"**Org #{_oo_i+1}:** {_oo_reg.get('nombre_org','—')}  |  "
                            f"**Tipo:** {_oo_reg.get('tipo_org','—')}  |  "
                            f"**Rol:** {_oo_reg.get('rol_org','—')}  |  "
                            f"**Ámbito:** {_oo_reg.get('ambito_org','—')}"
                        )
                with _oo_col_d:
                    if st.button("🗑️", key=f"del_oo_{sfx}_{_oo_i}", help="Eliminar esta organización"):
                        st.session_state[_oo_key].pop(_oo_i)
                        st.rerun()

        _oo_show_key = f"show_oo_form_{sfx}"
        if _oo_show_key not in st.session_state:
            st.session_state[_oo_show_key] = len(st.session_state[_oo_key]) == 0
        _oo_btn_label = "🔼 Ocultar formulario de organización" if st.session_state[_oo_show_key] else "➕ Agregar organización / instancia"
        if st.button(_oo_btn_label, key=f"toggle_oo_{sfx}", use_container_width=True, type="secondary"):
            st.session_state[_oo_show_key] = not st.session_state[_oo_show_key]
            st.rerun()

        if st.session_state[_oo_show_key]:
            with st.container(border=True):
                if es_colectivo:
                    # ── Formulario colectivo: tipo + num_personas + conteos por ámbito ─
                    st.selectbox("TIPO DE ORGANIZACIÓN", _PA_TIPO_ORG, index=0,
                                 key=f"pa_tipo_org_{sfx}_new")
                    _oo_tipo_sel = st.session_state.get(f"pa_tipo_org_{sfx}_new", "Seleccione...")
                    if _oo_tipo_sel != "Seleccione...":
                        st.number_input(
                            "NÚMERO DE PERSONAS EN ESTE TIPO DE ORGANIZACIÓN",
                            min_value=0, step=1, value=0,
                            key=f"pa_num_pers_org_{sfx}_new"
                        )
                        st.markdown("**NÚMERO DE PERSONAS POR ÁMBITO**")
                        _amb_cols_new = st.columns(4)
                        for _ai_n, _amb_n in enumerate(_PA_AMBITO_ORG):
                            with _amb_cols_new[_ai_n % 4]:
                                st.number_input(
                                    _amb_n, min_value=0, step=1, value=0,
                                    key=f"pa_amb_cnt_{_amb_n}_{sfx}_new"
                                )
                        if st.button("✅ Guardar organización", key=f"add_oo_{sfx}",
                                     use_container_width=True, type="primary"):
                            _oo_num = int(st.session_state.get(f"pa_num_pers_org_{sfx}_new") or 0)
                            _oo_amb_counts = {
                                _amb_n: int(st.session_state.get(f"pa_amb_cnt_{_amb_n}_{sfx}_new") or 0)
                                for _amb_n in _PA_AMBITO_ORG
                            }
                            st.session_state[_oo_key].append({
                                "tipo_org":         _oo_tipo_sel,
                                "num_personas_org": _oo_num,
                                "ambito_counts":    _oo_amb_counts,
                            })
                            st.session_state[_oo_show_key] = False
                            st.rerun()
                else:
                    # ── Formulario individual (original) ──────────────────────────────
                    col_ot1_n, col_ot2_n = st.columns(2)
                    with col_ot1_n:
                        st.selectbox("TIPO DE ORGANIZACIÓN", _PA_TIPO_ORG, index=0,
                                     key=f"pa_tipo_org_{sfx}_new")
                        st.text_input("NOMBRE ORGANIZACIÓN", value="", key=f"pa_nombre_org_{sfx}_new")
                    with col_ot2_n:
                        st.selectbox("ESCALA", _PA_ESCALA_ORG, index=0, key=f"pa_escala_org_{sfx}_new")
                        st.text_input("¿QUÉ ROL EJERCE EN DICHA INSTANCIA?", value="",
                                      key=f"pa_rol_org_{sfx}_new")
                    col_dep_on, col_mun_on = st.columns(2)
                    _dep_org_opts_n = ["Seleccione..."] + list(_MUNICIPIOS.keys())
                    with col_dep_on:
                        st.selectbox("DEPARTAMENTO", _dep_org_opts_n, index=0, key=f"pa_dep_org_{sfx}_new")
                    with col_mun_on:
                        _dep_sel_n  = st.session_state.get(f"pa_dep_org_{sfx}_new", "Seleccione...")
                        _mun_opts_n = _MUNICIPIOS.get(_dep_sel_n, ["Seleccione..."])
                        st.selectbox("MUNICIPIO", _mun_opts_n, index=0, key=f"pa_mun_org_{sfx}_new")
                    col_ai_n, col_af_n = st.columns(2)
                    with col_ai_n:
                        st.number_input("AÑO INICIO ACTIVIDAD", min_value=1990, max_value=2099,
                                        value=None, step=1, key=f"pa_anio_ini_org_{sfx}_new")
                    with col_af_n:
                        st.text_input(
                            "AÑO FINALIZACIÓN DE LA ACTIVIDAD (año finalizado, presente o no reporta)",
                            value="", key=f"pa_anio_fin_org_{sfx}_new")
                    _opts_amb_n = ["Seleccione..."] + _PA_AMBITO_ORG
                    st.selectbox("**ÁMBITO DE LA ORGANIZACIÓN**", _opts_amb_n, index=0,
                                 key=f"pa_amb_{sfx}_new")
                    if st.button("✅ Guardar organización", key=f"add_oo_{sfx}",
                                 use_container_width=True, type="primary"):
                        _oo_tipo   = st.session_state.get(f"pa_tipo_org_{sfx}_new", "Seleccione...")
                        _oo_nombre = st.session_state.get(f"pa_nombre_org_{sfx}_new", "")
                        _oo_escala = st.session_state.get(f"pa_escala_org_{sfx}_new", "Seleccione...")
                        _oo_rol    = st.session_state.get(f"pa_rol_org_{sfx}_new", "")
                        _oo_dep    = st.session_state.get(f"pa_dep_org_{sfx}_new", "Seleccione...")
                        _oo_mun    = st.session_state.get(f"pa_mun_org_{sfx}_new", "Seleccione...")
                        _oo_ai     = st.session_state.get(f"pa_anio_ini_org_{sfx}_new")
                        _oo_af     = st.session_state.get(f"pa_anio_fin_org_{sfx}_new", "")
                        _oo_amb    = st.session_state.get(f"pa_amb_{sfx}_new", "Seleccione...")
                        st.session_state[_oo_key].append({
                            "tipo_org":         _oo_tipo   if _oo_tipo   != "Seleccione..." else "",
                            "nombre_org":       _oo_nombre,
                            "escala_org":       _oo_escala if _oo_escala != "Seleccione..." else "",
                            "rol_org":          _oo_rol,
                            "departamento_org": _oo_dep    if _oo_dep    != "Seleccione..." else "",
                            "municipio_org":    _oo_mun    if _oo_mun    != "Seleccione..." else "",
                            "anio_inicio_org":  str(int(_oo_ai)) if _oo_ai is not None else "",
                            "anio_fin_org":     str(_oo_af),
                            "ambito_org":       _oo_amb    if _oo_amb    != "Seleccione..." else "",
                        })
                        st.session_state[_oo_show_key] = False
                        st.rerun()

    # ── Subformulario: Perfil del Reincorporado/a (FAMILIAR DE REINCORPORADO/A) ─
    if es_familiar_reincorporado:
        st.markdown("---")
        with st.container(border=True):
            st.markdown("#### 👤 PERFIL DEL REINCORPORADO/A RELACIONADO")
            st.caption("Información sobre el perfil de reincorporación del familiar")

            _opts_fr = ["Seleccione...", "SI", "NO REPORTA"]

            col_fr1, col_fr2 = st.columns(2)
            with col_fr1:
                st.selectbox("NIVEL DE ESCOLARIDAD", _PA_NIVEL_EDUCATIVO,
                             index=_PA_NIVEL_EDUCATIVO.index(_v("fr_nivel_educativo"))
                                   if _v("fr_nivel_educativo") in _PA_NIVEL_EDUCATIVO else 0,
                             key=f"fr_edu_{sfx}")
            with col_fr2:
                st.text_input("FUENTE PRINCIPAL DE INGRESOS",
                              value=_v("fr_fuente_ingresos", ""),
                              key=f"fr_ingresos_{sfx}")

            col_fr3, col_fr4 = st.columns(2)
            with col_fr3:
                st.selectbox("PROYECTO PRODUCTIVO REINCORPORACIÓN ARN", _PA_ESTADO_PROYECTO_ARN,
                             index=_PA_ESTADO_PROYECTO_ARN.index(_v("fr_estado_arn"))
                                   if _v("fr_estado_arn") in _PA_ESTADO_PROYECTO_ARN else 0,
                             key=f"fr_arn_{sfx}")
            with col_fr4:
                st.selectbox("ACTIVIDAD ECONÓMICA REINCORPORACIÓN", _PA_ACTIVIDAD_ECONOMICA,
                             index=_PA_ACTIVIDAD_ECONOMICA.index(_v("fr_actividad_economica"))
                                   if _v("fr_actividad_economica") in _PA_ACTIVIDAD_ECONOMICA else 0,
                             key=f"fr_act_eco_{sfx}")

            st.selectbox("COMPARECENCIA ANTE LA JEP", _opts_fr,
                         index=_opts_fr.index(_v("fr_comparecencia_jep"))
                               if _v("fr_comparecencia_jep") in _opts_fr else 0,
                         key=f"fr_jep_comp_{sfx}")
            if st.session_state.get(f"fr_jep_comp_{sfx}", "Seleccione...") == "SI":
                _fr_mcc_prev = [m.strip() for m in _v("fr_macrocasos_jep", "").split("|") if m.strip()] if pa else []
                st.markdown("**MACROCASO COMPARECIENTE**")
                _cols_fr_mcc = st.columns(2)
                for _j, _mc in enumerate(_PA_MACROCASOS_JEP):
                    _cols_fr_mcc[_j % 2].checkbox(_mc, value=(_mc in _fr_mcc_prev), key=f"fr_mcc_{_j}_{sfx}")

            st.selectbox("ES VÍCTIMA ANTE LA JEP", _SI_NO_REPORTA,
                         index=_SI_NO_REPORTA.index(_v("fr_victima_jep"))
                               if _v("fr_victima_jep") in _SI_NO_REPORTA else 0,
                         key=f"fr_jep_vic_{sfx}")
            if st.session_state.get(f"fr_jep_vic_{sfx}", "Seleccione...") == "SI":
                _fr_mcv_prev = [m.strip() for m in _v("fr_macrocaso_victima", "").split("|") if m.strip()] if pa else []
                st.markdown("**MACROCASO VÍCTIMA**")
                _cols_fr_mcv = st.columns(2)
                for _j, _mc in enumerate(_PA_MACROCASOS_JEP):
                    _cols_fr_mcv[_j % 2].checkbox(_mc, value=(_mc in _fr_mcv_prev), key=f"fr_mcv_{_j}_{sfx}")

            col_fr5, col_fr6 = st.columns(2)
            with col_fr5:
                st.selectbox("PARTICIPA EN TRABAJOS, OBRAS Y ACTIVIDADES REPARADORAS - TOAR",
                             _SI_NO_REPORTA,
                             index=_SI_NO_REPORTA.index(_v("fr_participacion_toar"))
                                   if _v("fr_participacion_toar") in _SI_NO_REPORTA else 0,
                             key=f"fr_toar_{sfx}")
                st.selectbox("PARTICIPA EN ACTIVIDADES DEL PROGRAMA PNIS", _SI_NO_REPORTA,
                             index=_SI_NO_REPORTA.index(_v("fr_participacion_pnis"))
                                   if _v("fr_participacion_pnis") in _SI_NO_REPORTA else 0,
                             key=f"fr_pnis_{sfx}")
            with col_fr6:
                st.selectbox("PARTICIPA EN ACTIVIDADES DE BÚSQUEDA DE PERSONAS DADAS POR DESAPARECIDAS",
                             _SI_NO_REPORTA,
                             index=_SI_NO_REPORTA.index(_v("fr_busqueda_desaparecidos"))
                                   if _v("fr_busqueda_desaparecidos") in _SI_NO_REPORTA else 0,
                             key=f"fr_busq_{sfx}")
                st.selectbox("PARTICIPA EN ACTIVIDADES DE DESMINADO HUMANITARIO", _SI_NO_REPORTA,
                             index=_SI_NO_REPORTA.index(_v("fr_desminado"))
                                   if _v("fr_desminado") in _SI_NO_REPORTA else 0,
                             key=f"fr_desminado_{sfx}")

            st.selectbox(
                "¿PARTICIPA DE ALGÚN TIPO DE ORGANIZACIÓN SOCIAL, POLÍTICA O INSTANCIA INSTITUCIONAL?",
                _SI_NO,
                index=_SI_NO.index(_v("fr_participa_otras_org"))
                      if _v("fr_participa_otras_org") in _SI_NO else 0,
                key=f"fr_otras_org_{sfx}"
            )

            st.selectbox("¿EJERCE UN CARGO DE ELECCIÓN POPULAR?", _PA_CARGO_ELECCION,
                         index=_PA_CARGO_ELECCION.index(_v("fr_cargo_eleccion"))
                               if _v("fr_cargo_eleccion") in _PA_CARGO_ELECCION else 0,
                         key=f"fr_cargo_{sfx}")

    # ── Subformulario: Perfil del Integrante de Comunes (FAMILIAR DE INTEGRANTE DEL PARTIDO COMUNES) ─
    if es_familiar_comunes:
        st.markdown("---")
        with st.container(border=True):
            st.markdown("#### 🏛️ PERFIL DEL INTEGRANTE DEL PARTIDO COMUNES RELACIONADO")
            st.caption("Información sobre el perfil del integrante de Comunes familiar")

            _opts_fc = ["Seleccione...", "SI", "NO REPORTA"]

            col_fc1, col_fc2 = st.columns(2)
            with col_fc1:
                st.selectbox("NIVEL DE ESCOLARIDAD", _PA_NIVEL_EDUCATIVO,
                             index=_PA_NIVEL_EDUCATIVO.index(_v("fc_nivel_educativo"))
                                   if _v("fc_nivel_educativo") in _PA_NIVEL_EDUCATIVO else 0,
                             key=f"fc_edu_{sfx}")
            with col_fc2:
                st.text_input("FUENTE PRINCIPAL DE INGRESOS",
                              value=_v("fc_fuente_ingresos", ""),
                              key=f"fc_ingresos_{sfx}")

            st.selectbox("COMPARECENCIA ANTE LA JEP", _opts_fc,
                         index=_opts_fc.index(_v("fc_comparecencia_jep"))
                               if _v("fc_comparecencia_jep") in _opts_fc else 0,
                         key=f"fc_jep_comp_{sfx}")
            if st.session_state.get(f"fc_jep_comp_{sfx}", "Seleccione...") == "SI":
                _fc_mcc_prev = [m.strip() for m in _v("fc_macrocasos_jep", "").split("|") if m.strip()] if pa else []
                st.markdown("**MACROCASO COMPARECIENTE**")
                _cols_fc_mcc = st.columns(2)
                for _j, _mc in enumerate(_PA_MACROCASOS_JEP):
                    _cols_fc_mcc[_j % 2].checkbox(_mc, value=(_mc in _fc_mcc_prev), key=f"fc_mcc_{_j}_{sfx}")

            st.selectbox("ES VÍCTIMA ANTE LA JEP", _SI_NO_REPORTA,
                         index=_SI_NO_REPORTA.index(_v("fc_victima_jep"))
                               if _v("fc_victima_jep") in _SI_NO_REPORTA else 0,
                         key=f"fc_jep_vic_{sfx}")
            if st.session_state.get(f"fc_jep_vic_{sfx}", "Seleccione...") == "SI":
                _fc_mcv_prev = [m.strip() for m in _v("fc_macrocaso_victima", "").split("|") if m.strip()] if pa else []
                st.markdown("**MACROCASO VÍCTIMA**")
                _cols_fc_mcv = st.columns(2)
                for _j, _mc in enumerate(_PA_MACROCASOS_JEP):
                    _cols_fc_mcv[_j % 2].checkbox(_mc, value=(_mc in _fc_mcv_prev), key=f"fc_mcv_{_j}_{sfx}")

            col_fc5, col_fc6 = st.columns(2)
            with col_fc5:
                st.selectbox("PARTICIPA EN TRABAJOS, OBRAS Y ACTIVIDADES REPARADORAS - TOAR",
                             _SI_NO_REPORTA,
                             index=_SI_NO_REPORTA.index(_v("fc_participacion_toar"))
                                   if _v("fc_participacion_toar") in _SI_NO_REPORTA else 0,
                             key=f"fc_toar_{sfx}")
                st.selectbox("PARTICIPA EN ACTIVIDADES DEL PROGRAMA PNIS", _SI_NO_REPORTA,
                             index=_SI_NO_REPORTA.index(_v("fc_participacion_pnis"))
                                   if _v("fc_participacion_pnis") in _SI_NO_REPORTA else 0,
                             key=f"fc_pnis_{sfx}")
            with col_fc6:
                st.selectbox("PARTICIPA EN ACTIVIDADES DE BÚSQUEDA DE PERSONAS DADAS POR DESAPARECIDAS",
                             _SI_NO_REPORTA,
                             index=_SI_NO_REPORTA.index(_v("fc_busqueda_desaparecidos"))
                                   if _v("fc_busqueda_desaparecidos") in _SI_NO_REPORTA else 0,
                             key=f"fc_busq_{sfx}")
                st.selectbox("PARTICIPA EN ACTIVIDADES DE DESMINADO HUMANITARIO", _SI_NO_REPORTA,
                             index=_SI_NO_REPORTA.index(_v("fc_desminado"))
                                   if _v("fc_desminado") in _SI_NO_REPORTA else 0,
                             key=f"fc_desminado_{sfx}")

            st.selectbox(
                "¿PARTICIPA DE ALGÚN TIPO DE ORGANIZACIÓN SOCIAL, POLÍTICA O INSTANCIA INSTITUCIONAL?",
                _SI_NO,
                index=_SI_NO.index(_v("fc_participa_otras_org"))
                      if _v("fc_participa_otras_org") in _SI_NO else 0,
                key=f"fc_otras_org_{sfx}"
            )

            st.selectbox("¿EJERCE UN CARGO DE ELECCIÓN POPULAR?", _PA_CARGO_ELECCION,
                         index=_PA_CARGO_ELECCION.index(_v("fc_cargo_eleccion"))
                               if _v("fc_cargo_eleccion") in _PA_CARGO_ELECCION else 0,
                         key=f"fc_cargo_{sfx}")

            # Instancias Partido Comunes del integrante relacionado
            st.markdown("---")
            st.markdown("**PARTICIPACIÓN EN INSTANCIAS POLÍTICAS, SOCIALES O INSTITUCIONALES — PARTIDO COMUNES**")
            _fc_ic_key = f"fc_instancias_comunes_temp_{sfx}"
            if _fc_ic_key not in st.session_state:
                st.session_state[_fc_ic_key] = list(_v("fc_instancias_comunes", []) or [])

            for _fc_ic_i, _fc_ic_reg in enumerate(st.session_state[_fc_ic_key]):
                with st.container(border=True):
                    _fc_ic_col_t, _fc_ic_col_d = st.columns([5, 1])
                    with _fc_ic_col_t:
                        st.markdown(
                            f"**Instancia #{_fc_ic_i+1}:** {_fc_ic_reg.get('instancias_partido','—')}  |  "
                            f"**Rol:** {_fc_ic_reg.get('roles_partido','—')}  |  "
                            f"**Consejería:** {_fc_ic_reg.get('consejeria_nacional','—')}"
                        )
                    with _fc_ic_col_d:
                        if st.button("🗑️", key=f"del_fc_ic_{sfx}_{_fc_ic_i}", help="Eliminar esta instancia"):
                            st.session_state[_fc_ic_key].pop(_fc_ic_i)
                            st.rerun()

            _fc_ic_show_key = f"fc_show_ic_form_{sfx}"
            if _fc_ic_show_key not in st.session_state:
                st.session_state[_fc_ic_show_key] = len(st.session_state[_fc_ic_key]) == 0
            _fc_ic_btn_label = "🔼 Ocultar formulario de instancia" if st.session_state[_fc_ic_show_key] else "➕ Agregar instancia en Partido Comunes"
            if st.button(_fc_ic_btn_label, key=f"toggle_fc_ic_{sfx}", use_container_width=True, type="secondary"):
                st.session_state[_fc_ic_show_key] = not st.session_state[_fc_ic_show_key]
                st.rerun()

            if st.session_state[_fc_ic_show_key]:
                with st.container(border=True):
                    _fc_idx_no_rep = len(_PA_INSTANCIAS_PARTIDO) - 2
                    st.markdown("**¿DE CUÁL INSTANCIA DE DIRECCIÓN O VIGILANCIA DEL PARTIDO COMUNES ES INTEGRANTE?**")
                    cols_fc_inst = st.columns(2)
                    for _j, _inst_n in enumerate(_PA_INSTANCIAS_PARTIDO[1:]):
                        cols_fc_inst[_j % 2].checkbox(_inst_n, value=False, key=f"fc_inst_{_j}_{sfx}_new")
                    _fc_no_rep = st.session_state.get(f"fc_inst_{_fc_idx_no_rep}_{sfx}_new", False)
                    if not _fc_no_rep:
                        st.markdown("**ROL QUE EJERCE EN DICHA INSTANCIA**")
                        cols_fc_rp = st.columns(2)
                        for _j, _rol_n in enumerate(_PA_ROLES_PARTIDO[1:]):
                            cols_fc_rp[_j % 2].checkbox(_rol_n, value=False, key=f"fc_rol_{_j}_{sfx}_new")
                    col_fc11, col_fc12 = st.columns(2)
                    with col_fc11:
                        st.selectbox("ES INTEGRANTE DE CONSEJERÍA NACIONAL", _SI_NO,
                                     index=0, key=f"fc_cons_nac_{sfx}_new")
                    _fc_tiene_cons = st.session_state.get(f"fc_cons_nac_{sfx}_new", "Seleccione...")
                    if _fc_tiene_cons == "SI":
                        with col_fc12:
                            st.selectbox("¿CUÁL CONSEJERÍA?", _PA_CONSEJERIA_NACIONAL,
                                         index=0, key=f"fc_tipo_cons_{sfx}_new")
                    if st.button("✅ Guardar instancia", key=f"add_fc_ic_{sfx}", use_container_width=True, type="primary"):
                        _fc_new_insts = " | ".join([
                            _inst_n for _j, _inst_n in enumerate(_PA_INSTANCIAS_PARTIDO[1:])
                            if st.session_state.get(f"fc_inst_{_j}_{sfx}_new", False)
                        ])
                        _fc_new_roles = " | ".join([
                            _rol_n for _j, _rol_n in enumerate(_PA_ROLES_PARTIDO[1:])
                            if st.session_state.get(f"fc_rol_{_j}_{sfx}_new", False)
                        ])
                        _fc_cons_nac  = st.session_state.get(f"fc_cons_nac_{sfx}_new", "Seleccione...")
                        _fc_tipo_cons = st.session_state.get(f"fc_tipo_cons_{sfx}_new", "") if _fc_cons_nac == "SI" else ""
                        st.session_state[_fc_ic_key].append({
                            "instancias_partido":  _fc_new_insts,
                            "roles_partido":       _fc_new_roles,
                            "consejeria_nacional": _fc_cons_nac if _fc_cons_nac != "Seleccione..." else "",
                            "tipo_consejeria":     _fc_tipo_cons if _fc_tipo_cons != "Seleccione..." else "",
                        })
                        st.session_state[_fc_ic_show_key] = False
                        st.rerun()

            st.text_input("¿A QUÉ CONSEJO LOCAL-MUNICIPAL ESTÁ VINCULADO?",
                          value=_v("fc_concejo_comunes", ""), key=f"fc_concejo_{sfx}")

            st.selectbox("¿EJERCE CARGO DE ELECCIÓN POPULAR EL INTEGRANTE?", _PA_CARGO_ELECCION,
                         index=_PA_CARGO_ELECCION.index(_v("fc_cargo_eleccion_comunes"))
                               if _v("fc_cargo_eleccion_comunes") in _PA_CARGO_ELECCION else 0,
                         key=f"fc_cargo_comunes_{sfx}")

    # ── Partido Comunes ───────────────────────────────────────────────────────
    if mostrar_cargo_comunes:
        st.markdown("---")
        st.markdown("**PARTIDO COMUNES**")
        st.text_input("¿A QUÉ CONSEJO LOCAL-MUNICIPAL ESTÁ VINCULADO?",
                      value=_v("concejo_comunes", ""), key=f"pa_concejo_{sfx}")

        # Multiregistro instancias del partido
        _ic_key = f"instancias_comunes_temp_{sfx}"
        if _ic_key not in st.session_state:
            st.session_state[_ic_key] = list(_v("instancias_comunes", []) or [])

        st.markdown("**PARTICIPACIÓN EN INSTANCIAS POLÍTICAS, SOCIALES O INSTITUCIONALES — PARTIDO COMUNES**")
        for _ic_i, _ic_reg in enumerate(st.session_state[_ic_key]):
            with st.container(border=True):
                _ic_col_t, _ic_col_d = st.columns([5, 1])
                with _ic_col_t:
                    st.markdown(
                        f"**Instancia #{_ic_i+1}:** {_ic_reg.get('instancias_partido','—')}  |  "
                        f"**Rol:** {_ic_reg.get('roles_partido','—')}  |  "
                        f"**Consejería:** {_ic_reg.get('consejeria_nacional','—')}"
                    )
                with _ic_col_d:
                    if st.button("🗑️", key=f"del_ic_{sfx}_{_ic_i}", help="Eliminar esta instancia"):
                        st.session_state[_ic_key].pop(_ic_i)
                        st.rerun()

        _ic_show_key = f"show_ic_form_{sfx}"
        if _ic_show_key not in st.session_state:
            st.session_state[_ic_show_key] = len(st.session_state[_ic_key]) == 0
        _ic_btn_label = "🔼 Ocultar formulario de instancia" if st.session_state[_ic_show_key] else "➕ Agregar instancia en Partido Comunes"
        if st.button(_ic_btn_label, key=f"toggle_ic_{sfx}", use_container_width=True, type="secondary"):
            st.session_state[_ic_show_key] = not st.session_state[_ic_show_key]
            st.rerun()

        if st.session_state[_ic_show_key]:
            with st.container(border=True):
                _idx_no_reporta_new = len(_PA_INSTANCIAS_PARTIDO) - 2
                st.markdown("**¿DE CUÁL INSTANCIA DE DIRECCIÓN O VIGILANCIA DEL PARTIDO COMUNES ES INTEGRANTE?**")
                cols_inst_new = st.columns(2)
                for _j, _inst_n in enumerate(_PA_INSTANCIAS_PARTIDO[1:]):
                    cols_inst_new[_j % 2].checkbox(_inst_n, value=False, key=f"pa_inst_{_j}_{sfx}_new")
                _no_reporta_new = st.session_state.get(f"pa_inst_{_idx_no_reporta_new}_{sfx}_new", False)
                if not _no_reporta_new:
                    st.markdown("**ROL QUE EJERCE EN DICHA INSTANCIA**")
                    cols_rp_new = st.columns(2)
                    for _j, _rol_n in enumerate(_PA_ROLES_PARTIDO[1:]):
                        cols_rp_new[_j % 2].checkbox(_rol_n, value=False, key=f"pa_rol_{_j}_{sfx}_new")
                col11_n, col12_n = st.columns(2)
                with col11_n:
                    st.selectbox("ES INTEGRANTE DE CONSEJERÍA NACIONAL", _SI_NO,
                                 index=0, key=f"pa_cons_nac_{sfx}_new")
                _tiene_cons_new = st.session_state.get(f"pa_cons_nac_{sfx}_new", "Seleccione...")
                if _tiene_cons_new == "SI":
                    with col12_n:
                        st.selectbox("¿CUÁL CONSEJERÍA?", _PA_CONSEJERIA_NACIONAL,
                                     index=0, key=f"pa_tipo_cons_{sfx}_new")
                if st.button("✅ Guardar instancia", key=f"add_ic_{sfx}", use_container_width=True, type="primary"):
                    _new_insts = " | ".join([
                        _inst_n for _j, _inst_n in enumerate(_PA_INSTANCIAS_PARTIDO[1:])
                        if st.session_state.get(f"pa_inst_{_j}_{sfx}_new", False)
                    ])
                    _new_roles = " | ".join([
                        _rol_n for _j, _rol_n in enumerate(_PA_ROLES_PARTIDO[1:])
                        if st.session_state.get(f"pa_rol_{_j}_{sfx}_new", False)
                    ])
                    _new_cons_nac  = st.session_state.get(f"pa_cons_nac_{sfx}_new", "Seleccione...")
                    _new_tipo_cons = st.session_state.get(f"pa_tipo_cons_{sfx}_new", "") if _new_cons_nac == "SI" else ""
                    st.session_state[_ic_key].append({
                        "instancias_partido":  _new_insts,
                        "roles_partido":       _new_roles,
                        "consejeria_nacional": _new_cons_nac if _new_cons_nac != "Seleccione..." else "",
                        "tipo_consejeria":     _new_tipo_cons if _new_tipo_cons != "Seleccione..." else "",
                    })
                    st.session_state[_ic_show_key] = False
                    st.rerun()

    # ── Cargo de elección popular (siempre visible) ───────────────────────────
    st.markdown("---")
    st.markdown("**Cargo de Elección Popular**")
    if es_colectivo:
        _cargo_col_val = _v("col_cargo_eleccion_sino", "Seleccione...")
        st.selectbox("¿MIEMBROS EJERCEN CARGOS DE ELECCIÓN POPULAR?", _SI_NO,
                     index=_SI_NO.index(_cargo_col_val) if _cargo_col_val in _SI_NO else 0,
                     key=f"pa_col_cargo_sino_{sfx}")
        if st.session_state.get(f"pa_col_cargo_sino_{sfx}", "") == "SI":
            st.number_input("¿CUÁNTOS MIEMBROS EJERCEN CARGOS DE ELECCIÓN POPULAR?",
                            min_value=0, step=1,
                            value=int(_v("col_cargo_eleccion_cnt", 0) or 0),
                            key=f"pa_col_cargo_cnt_{sfx}")
    else:
        st.selectbox("¿Ocupa o ha ocupado cargo de elección popular?", _PA_CARGO_ELECCION,
                     index=_PA_CARGO_ELECCION.index(_v("cargo_eleccion"))
                           if _v("cargo_eleccion") in _PA_CARGO_ELECCION else 0,
                     key=f"pa_cargo_{sfx}")


def _recoger_pa(tipo, idx, es_reincorporado, es_familiar_reincorporado,
                es_familiar_comunes, mostrar_cargo_comunes, es_colectivo=False):
    """
    Lee el estado de los widgets del Perfil Actual y retorna un dict,
    o None si hay errores de validación.
    """
    sfx = f"{tipo}_{idx}"

    if es_colectivo:
        # ── Colectivo: conteos JEP/TOAR + Sí/No para búsqueda, PNIS, desminado ─
        nivel_edu             = ""
        fuente_ingresos       = ""
        comparecencia_jep     = ""
        macrocaso_comp        = ""
        victima_jep           = ""
        macrocaso_vic         = ""
        participacion_toar    = ""
        col_jep_comp_cnt      = int(st.session_state.get(f"pa_col_jep_comp_cnt_{sfx}") or 0)
        col_jep_vic_cnt       = int(st.session_state.get(f"pa_col_jep_vic_cnt_{sfx}") or 0)
        col_toar_cnt          = int(st.session_state.get(f"pa_col_toar_cnt_{sfx}") or 0)
        col_busq_cnt          = int(st.session_state.get(f"pa_col_busq_cnt_{sfx}") or 0)
        col_pnis_cnt          = int(st.session_state.get(f"pa_col_pnis_cnt_{sfx}") or 0)
        col_desminado_cnt     = int(st.session_state.get(f"pa_col_desminado_cnt_{sfx}") or 0)
        busqueda_desaparecidos = ""
        participacion_pnis     = ""
        desminado              = ""
    else:
        # Campos del perfil — siempre se leen
        nivel_edu         = st.session_state.get(f"pa_edu_{sfx}", "Seleccione...")
        fuente_ingresos   = st.session_state.get(f"pa_ingresos_{sfx}", "Seleccione...")
        comparecencia_jep = st.session_state.get(f"pa_jep_comp_{sfx}", "Seleccione...")
        macrocaso_comp = ""
        if comparecencia_jep == "SI":
            macrocaso_comp = " | ".join([
                mc for j, mc in enumerate(_PA_MACROCASOS_JEP)
                if st.session_state.get(f"pa_mcc_{j}_{sfx}", False)
            ])
        victima_jep = st.session_state.get(f"pa_jep_vic_{sfx}", "Seleccione...")
        macrocaso_vic = ""
        if victima_jep == "SI":
            macrocaso_vic = " | ".join([
                mc for j, mc in enumerate(_PA_MACROCASOS_JEP)
                if st.session_state.get(f"pa_mcv_{j}_{sfx}", False)
            ])
        participacion_toar     = st.session_state.get(f"pa_toar_{sfx}", "Seleccione...")
        busqueda_desaparecidos = st.session_state.get(f"pa_busq_{sfx}", "Seleccione...")
        participacion_pnis     = st.session_state.get(f"pa_pnis_{sfx}", "Seleccione...")
        desminado              = st.session_state.get(f"pa_desminado_{sfx}", "Seleccione...")
        col_jep_comp_cnt = col_jep_vic_cnt = col_toar_cnt = 0
        col_busq_cnt = col_pnis_cnt = col_desminado_cnt = 0
    participa_otras        = st.session_state.get(f"pa_otras_org_{sfx}", "Seleccione...")
    otras_orgs = []
    if participa_otras == "SI":
        otras_orgs = list(st.session_state.get(f"otras_orgs_temp_{sfx}", []))

    # Subformulario del reincorporado/a (solo FAMILIAR DE REINCORPORADO/A)
    fr_nivel_edu = fr_fuente_ingresos = fr_estado_arn = fr_actividad_eco = ""
    fr_comparecencia_jep = fr_macrocasos_jep = ""
    fr_victima_jep = fr_macrocaso_victima = ""
    fr_toar = fr_busqueda = fr_pnis = fr_desminado = ""
    fr_participa_otras = fr_cargo_eleccion = ""

    if es_familiar_reincorporado:
        fr_nivel_edu         = st.session_state.get(f"fr_edu_{sfx}", "Seleccione...")
        fr_fuente_ingresos   = st.session_state.get(f"fr_ingresos_{sfx}", "Seleccione...")
        fr_estado_arn        = st.session_state.get(f"fr_arn_{sfx}", "Seleccione...")
        fr_actividad_eco     = st.session_state.get(f"fr_act_eco_{sfx}", "Seleccione...")
        fr_comparecencia_jep = st.session_state.get(f"fr_jep_comp_{sfx}", "Seleccione...")
        if fr_comparecencia_jep == "SI":
            fr_macrocasos_jep = " | ".join([
                mc for j, mc in enumerate(_PA_MACROCASOS_JEP)
                if st.session_state.get(f"fr_mcc_{j}_{sfx}", False)
            ])
        fr_victima_jep = st.session_state.get(f"fr_jep_vic_{sfx}", "Seleccione...")
        if fr_victima_jep == "SI":
            fr_macrocaso_victima = " | ".join([
                mc for j, mc in enumerate(_PA_MACROCASOS_JEP)
                if st.session_state.get(f"fr_mcv_{j}_{sfx}", False)
            ])
        fr_toar            = st.session_state.get(f"fr_toar_{sfx}", "Seleccione...")
        fr_busqueda        = st.session_state.get(f"fr_busq_{sfx}", "Seleccione...")
        fr_pnis            = st.session_state.get(f"fr_pnis_{sfx}", "Seleccione...")
        fr_desminado       = st.session_state.get(f"fr_desminado_{sfx}", "Seleccione...")
        fr_participa_otras = st.session_state.get(f"fr_otras_org_{sfx}", "Seleccione...")
        fr_cargo_eleccion  = st.session_state.get(f"fr_cargo_{sfx}", "Seleccione...")

    # Subformulario del integrante de Comunes (solo FAMILIAR DE INTEGRANTE DEL PARTIDO COMUNES)
    fc_nivel_edu = fc_fuente_ingresos = ""
    fc_comparecencia_jep = fc_macrocasos_jep = ""
    fc_victima_jep = fc_macrocaso_victima = ""
    fc_toar = fc_busqueda = fc_pnis = fc_desminado = ""
    fc_participa_otras = fc_cargo_eleccion = ""
    fc_instancias_comunes = []
    fc_concejo_comunes = fc_cargo_eleccion_comunes = ""

    if es_familiar_comunes:
        fc_nivel_edu         = st.session_state.get(f"fc_edu_{sfx}", "Seleccione...")
        fc_fuente_ingresos   = st.session_state.get(f"fc_ingresos_{sfx}", "")
        fc_comparecencia_jep = st.session_state.get(f"fc_jep_comp_{sfx}", "Seleccione...")
        if fc_comparecencia_jep == "SI":
            fc_macrocasos_jep = " | ".join([
                mc for j, mc in enumerate(_PA_MACROCASOS_JEP)
                if st.session_state.get(f"fc_mcc_{j}_{sfx}", False)
            ])
        fc_victima_jep = st.session_state.get(f"fc_jep_vic_{sfx}", "Seleccione...")
        if fc_victima_jep == "SI":
            fc_macrocaso_victima = " | ".join([
                mc for j, mc in enumerate(_PA_MACROCASOS_JEP)
                if st.session_state.get(f"fc_mcv_{j}_{sfx}", False)
            ])
        fc_toar            = st.session_state.get(f"fc_toar_{sfx}", "Seleccione...")
        fc_busqueda        = st.session_state.get(f"fc_busq_{sfx}", "Seleccione...")
        fc_pnis            = st.session_state.get(f"fc_pnis_{sfx}", "Seleccione...")
        fc_desminado       = st.session_state.get(f"fc_desminado_{sfx}", "Seleccione...")
        fc_participa_otras = st.session_state.get(f"fc_otras_org_{sfx}", "Seleccione...")
        fc_cargo_eleccion  = st.session_state.get(f"fc_cargo_{sfx}", "Seleccione...")
        fc_instancias_comunes = list(st.session_state.get(f"fc_instancias_comunes_temp_{sfx}", []))
        fc_concejo_comunes    = st.session_state.get(f"fc_concejo_{sfx}", "")
        fc_cargo_eleccion_comunes = st.session_state.get(f"fc_cargo_comunes_{sfx}", "Seleccione...")

    # Partido Comunes
    instancias_comunes = []
    concejo_comunes    = ""
    participa_comunes  = "SI" if mostrar_cargo_comunes else ""
    if mostrar_cargo_comunes:
        concejo_comunes    = st.session_state.get(f"pa_concejo_{sfx}", "")
        instancias_comunes = list(st.session_state.get(f"instancias_comunes_temp_{sfx}", []))

    _ic0 = instancias_comunes[0] if instancias_comunes else {}
    _oo0 = otras_orgs[0]         if otras_orgs         else {}

    def _c(v): return v if v and v != "Seleccione..." else ""

    return {
        # Perfil base (REINCORPORADO/A y FAMILIAR DE INTEGRANTE)
        "nivel_educativo":        nivel_edu,
        "fuente_ingresos":        _c(fuente_ingresos),
        "estado_proyecto_arn":    "",
        "actividad_economica":    "",
        "comparecencia_jep":      _c(comparecencia_jep),
        "macrocasos_jep":         macrocaso_comp,
        "victima_jep":            _c(victima_jep),
        "macrocaso_victima":      macrocaso_vic,
        "participacion_toar":     _c(participacion_toar),
        "busqueda_desaparecidos": _c(busqueda_desaparecidos),
        "participacion_pnis":     _c(participacion_pnis),
        "desminado":              _c(desminado),
        # Colectivo — conteos JEP / TOAR / búsqueda / PNIS / desminado
        "col_jep_comp_cnt":       col_jep_comp_cnt,
        "col_jep_vic_cnt":        col_jep_vic_cnt,
        "col_toar_cnt":           col_toar_cnt,
        "col_busq_cnt":           col_busq_cnt,
        "col_pnis_cnt":           col_pnis_cnt,
        "col_desminado_cnt":      col_desminado_cnt,
        "participa_otras_org":    _c(participa_otras),
        "otras_orgs":             otras_orgs,
        "tipo_org":               _oo0.get("tipo_org", ""),
        "nombre_org":             _oo0.get("nombre_org", ""),
        "ambito_org":             _oo0.get("ambito_org", ""),
        "escala_org":             _oo0.get("escala_org", ""),
        "departamento_org":       _oo0.get("departamento_org", ""),
        "municipio_org":          _oo0.get("municipio_org", ""),
        "rol_org":                _oo0.get("rol_org", ""),
        "anio_inicio_org":        _oo0.get("anio_inicio_org", ""),
        "anio_fin_org":           _oo0.get("anio_fin_org", ""),
        "cargo_eleccion":         (
            _c(st.session_state.get(f"pa_col_cargo_sino_{sfx}", "No"))
            if es_colectivo
            else _c(st.session_state.get(f"pa_cargo_{sfx}", "Seleccione..."))
        ),
        "col_cargo_eleccion_cnt": (
            int(st.session_state.get(f"pa_col_cargo_cnt_{sfx}") or 0)
            if es_colectivo and st.session_state.get(f"pa_col_cargo_sino_{sfx}") == "SI"
            else 0
        ),
        # Partido Comunes
        "participa_comunes":      participa_comunes,
        "concejo_comunes":        concejo_comunes,
        "instancias_comunes":     instancias_comunes,
        "instancias_partido":     _ic0.get("instancias_partido", ""),
        "roles_partido":          _ic0.get("roles_partido", ""),
        "consejeria_nacional":    _ic0.get("consejeria_nacional", ""),
        "tipo_consejeria":        _ic0.get("tipo_consejeria", ""),
        # Subformulario FAMILIAR DE REINCORPORADO/A
        "fr_nivel_educativo":        _c(fr_nivel_edu),
        "fr_fuente_ingresos":        _c(fr_fuente_ingresos),
        "fr_estado_arn":             _c(fr_estado_arn),
        "fr_actividad_economica":    _c(fr_actividad_eco),
        "fr_comparecencia_jep":      _c(fr_comparecencia_jep),
        "fr_macrocasos_jep":         fr_macrocasos_jep,
        "fr_victima_jep":            _c(fr_victima_jep),
        "fr_macrocaso_victima":      fr_macrocaso_victima,
        "fr_participacion_toar":     _c(fr_toar),
        "fr_busqueda_desaparecidos": _c(fr_busqueda),
        "fr_participacion_pnis":     _c(fr_pnis),
        "fr_desminado":              _c(fr_desminado),
        "fr_participa_otras_org":    _c(fr_participa_otras),
        "fr_cargo_eleccion":         _c(fr_cargo_eleccion),
        # Subformulario FAMILIAR DE INTEGRANTE DEL PARTIDO COMUNES
        "fc_nivel_educativo":           _c(fc_nivel_edu),
        "fc_fuente_ingresos":           fc_fuente_ingresos,
        "fc_comparecencia_jep":         _c(fc_comparecencia_jep),
        "fc_macrocasos_jep":            fc_macrocasos_jep,
        "fc_victima_jep":               _c(fc_victima_jep),
        "fc_macrocaso_victima":         fc_macrocaso_victima,
        "fc_participacion_toar":        _c(fc_toar),
        "fc_busqueda_desaparecidos":    _c(fc_busqueda),
        "fc_participacion_pnis":        _c(fc_pnis),
        "fc_desminado":                 _c(fc_desminado),
        "fc_participa_otras_org":       _c(fc_participa_otras),
        "fc_cargo_eleccion":            _c(fc_cargo_eleccion),
        "fc_instancias_comunes":        fc_instancias_comunes,
        "fc_concejo_comunes":           fc_concejo_comunes,
        "fc_cargo_eleccion_comunes":    _c(fc_cargo_eleccion_comunes),
    }


_DIV_OPCIONES = ["Seleccione...", "Comité", "Mesa", "Delegación", "Otro/¿Cuál?"]
_PROY_OPCIONES = ["Seleccione...", "Sí", "No"]


def _render_comp_col_form(comp, tipo_colectivo, tipo, idx):
    """Renderiza el formulario de una composición del colectivo."""
    sfx = f"{tipo}_{idx}"
    _v = lambda k, d="": (comp.get(k, d) if comp is not None else d)

    if tipo_colectivo == "Familiar":
        col_nf, col_np = st.columns(2)
        with col_nf:
            st.number_input("Número de núcleos familiares",
                            min_value=0, step=1,
                            value=int(_v("comp_nucleos_familiares", 0) or 0),
                            key=f"comp_col_nucleos_{sfx}")
        with col_np:
            st.number_input("Número de personas en el colectivo",
                            min_value=0, step=1,
                            value=int(_v("comp_num_personas", 0) or 0),
                            key=f"comp_col_num_personas_{sfx}")
        col_me, col_am = st.columns(2)
        with col_me:
            st.number_input("Número de menores de edad",
                            min_value=0, step=1,
                            value=int(_v("comp_menores", 0) or 0),
                            key=f"comp_col_menores_{sfx}")
        with col_am:
            st.number_input("Número de adultos mayores (60 años en adelante)",
                            min_value=0, step=1,
                            value=int(_v("comp_adultos_mayores", 0) or 0),
                            key=f"comp_col_adultos_mayores_{sfx}")
        st.number_input("Número de personas en situación de discapacidad",
                        min_value=0, step=1,
                        value=int(_v("comp_discapacidad", 0) or 0),
                        key=f"comp_col_discapacidad_{sfx}")
    else:
        _div_val = _v("tipo_division", "Seleccione...")
        st.selectbox("Tipo de División", _DIV_OPCIONES,
                     index=_DIV_OPCIONES.index(_div_val) if _div_val in _DIV_OPCIONES else 0,
                     key=f"comp_col_div_{sfx}")
        if st.session_state.get(f"comp_col_div_{sfx}") == "Otro/¿Cuál?":
            st.text_input("¿Cuál?", value=_v("comp_otro_cual", ""),
                          key=f"comp_col_div_otro_{sfx}")
        st.number_input("Número de integrantes",
                        min_value=0, step=1,
                        value=int(_v("comp_num_integrantes", 0) or 0),
                        key=f"comp_col_num_integrantes_{sfx}")

    # Campos comunes
    _proy_val = _v("comp_proyecto_productivo", "Seleccione...")
    st.selectbox("Tiene a cargo proyecto o iniciativa productiva", _PROY_OPCIONES,
                 index=_PROY_OPCIONES.index(_proy_val) if _proy_val in _PROY_OPCIONES else 0,
                 key=f"comp_col_proy_{sfx}")
    if st.session_state.get(f"comp_col_proy_{sfx}") == "Sí":
        st.markdown("**Actividad económica de proyecto productivo**")
        _prev_act = _v("comp_actividad_economica", [])
        _cols_ae = st.columns(2)
        for i_ae, act in enumerate(_ACTIVIDADES_ECONOMICAS_COLECTIVO):
            _cols_ae[i_ae % 2].checkbox(act, value=(act in _prev_act),
                                        key=f"comp_col_act_eco_{i_ae}_{sfx}")


def _recoger_comp_col(tipo_colectivo, tipo, idx):
    """Lee los widgets de composición del colectivo y retorna un dict."""
    sfx = f"{tipo}_{idx}"
    _c = lambda v: v if v and v != "Seleccione..." else ""

    _proy = st.session_state.get(f"comp_col_proy_{sfx}", "Seleccione...")
    _actividades = (
        [act for i_ae, act in enumerate(_ACTIVIDADES_ECONOMICAS_COLECTIVO)
         if st.session_state.get(f"comp_col_act_eco_{i_ae}_{sfx}", False)]
        if _proy == "Sí" else []
    )

    if tipo_colectivo == "Familiar":
        return {
            "comp_nucleos_familiares": int(st.session_state.get(f"comp_col_nucleos_{sfx}") or 0),
            "comp_num_personas":       int(st.session_state.get(f"comp_col_num_personas_{sfx}") or 0),
            "comp_menores":            int(st.session_state.get(f"comp_col_menores_{sfx}") or 0),
            "comp_adultos_mayores":    int(st.session_state.get(f"comp_col_adultos_mayores_{sfx}") or 0),
            "comp_discapacidad":       int(st.session_state.get(f"comp_col_discapacidad_{sfx}") or 0),
            "tipo_division":           "",
            "comp_otro_cual":          "",
            "comp_num_integrantes":    0,
            "comp_proyecto_productivo": _c(_proy),
            "comp_actividad_economica": _actividades,
        }
    else:
        _div = st.session_state.get(f"comp_col_div_{sfx}", "Seleccione...")
        _otro = (st.session_state.get(f"comp_col_div_otro_{sfx}", "")
                 if _div == "Otro/¿Cuál?" else "")
        return {
            "comp_nucleos_familiares": 0,
            "comp_num_personas":       0,
            "comp_menores":            0,
            "comp_adultos_mayores":    0,
            "comp_discapacidad":       0,
            "tipo_division":           _c(_div),
            "comp_otro_cual":          _otro,
            "comp_num_integrantes":    int(st.session_state.get(f"comp_col_num_integrantes_{sfx}") or 0),
            "comp_proyecto_productivo": _c(_proy),
            "comp_actividad_economica": _actividades,
        }


def _construir_datos_borrador(tipo):
    """Construye el dict de borrador leyendo el estado actual de todos los widgets."""
    return {
        f"caso_tipo_estudio_{tipo}":     st.session_state.get(f"caso_tipo_estudio_{tipo}", "Seleccione..."),
        f"caso_ot_anio_{tipo}":          st.session_state.get(f"caso_ot_anio_{tipo}", None),
        f"caso_ot_numero_{tipo}":        st.session_state.get(f"caso_ot_numero_{tipo}", None),
        f"caso_solicitante_{tipo}":      st.session_state.get(f"caso_solicitante_{tipo}", "Seleccione..."),
        f"caso_fecha_expedicion_{tipo}": st.session_state.get(f"caso_fecha_expedicion_{tipo}", None),
        f"caso_tipo_evaluacion_{tipo}":       st.session_state.get(f"caso_tipo_evaluacion_{tipo}", "Seleccione..."),
        f"caso_tipo_colectivo_{tipo}":          st.session_state.get(f"caso_tipo_colectivo_{tipo}", "Seleccione..."),
        f"caso_tipo_estructura_partido_{tipo}": st.session_state.get(f"caso_tipo_estructura_partido_{tipo}", "Seleccione..."),
        f"caso_estructura_adscrita_{tipo}":     st.session_state.get(f"caso_estructura_adscrita_{tipo}", "Seleccione..."),
        f"caso_cant_comunas_{tipo}":            st.session_state.get(f"caso_cant_comunas_{tipo}", 0),
        f"caso_cant_locales_{tipo}":            st.session_state.get(f"caso_cant_locales_{tipo}", 0),
        f"caso_cant_municipales_{tipo}":        st.session_state.get(f"caso_cant_municipales_{tipo}", 0),
        f"caso_cant_metropolitanas_{tipo}":     st.session_state.get(f"caso_cant_metropolitanas_{tipo}", 0),
        f"caso_cant_consejerias_{tipo}":        st.session_state.get(f"caso_cant_consejerias_{tipo}", 0),
        f"caso_familiar_parte_comunes_{tipo}": st.session_state.get(f"caso_familiar_parte_comunes_{tipo}", "Seleccione..."),
        f"caso_tipo_poblacion_{tipo}":        st.session_state.get(f"caso_tipo_poblacion_{tipo}", "Seleccione..."),
        **{f"subpob_{i}_{tipo}": st.session_state.get(f"subpob_{i}_{tipo}", False)
           for i in range(len(_SUBPOBLACIONES))},
        **{f"subpob_cnt_{i}_{tipo}": st.session_state.get(f"subpob_cnt_{i}_{tipo}", 0)
           for i in range(len(_SUBPOBLACIONES))},
        f"caso_fecha_nacimiento_{tipo}": st.session_state.get(f"caso_fecha_nacimiento_{tipo}", None),
        f"caso_sexo_{tipo}":             st.session_state.get(f"caso_sexo_{tipo}", "Seleccione..."),
        f"caso_genero_{tipo}":           st.session_state.get(f"caso_genero_{tipo}", "Seleccione..."),
        f"caso_orientacion_{tipo}":      st.session_state.get(f"caso_orientacion_{tipo}", "Seleccione..."),
        f"caso_jefatura_{tipo}":         st.session_state.get(f"caso_jefatura_{tipo}", "Seleccione..."),
        f"p_departamento_{tipo}":        st.session_state.get(f"p_departamento_{tipo}", "Seleccione..."),
        f"p_municipio_{tipo}":           st.session_state.get(f"p_municipio_{tipo}", "Seleccione..."),
        f"caso_zona_rural_{tipo}":       st.session_state.get(f"caso_zona_rural_{tipo}", "Seleccione..."),
        f"caso_zona_reserva_{tipo}":     st.session_state.get(f"caso_zona_reserva_{tipo}", "Seleccione..."),
        # Cantidades demográficas colectivo
        f"caso_cant_hombres_{tipo}":     st.session_state.get(f"caso_cant_hombres_{tipo}", 0),
        f"caso_cant_mujeres_{tipo}":     st.session_state.get(f"caso_cant_mujeres_{tipo}", 0),
        f"caso_cant_intersexual_{tipo}": st.session_state.get(f"caso_cant_intersexual_{tipo}", 0),
        f"caso_cant_femenino_{tipo}":    st.session_state.get(f"caso_cant_femenino_{tipo}", 0),
        f"caso_cant_masculino_{tipo}":   st.session_state.get(f"caso_cant_masculino_{tipo}", 0),
        f"caso_cant_transgenero_{tipo}": st.session_state.get(f"caso_cant_transgenero_{tipo}", 0),
        f"caso_cant_heterosexual_{tipo}":st.session_state.get(f"caso_cant_heterosexual_{tipo}", 0),
        f"caso_cant_homosexual_{tipo}":  st.session_state.get(f"caso_cant_homosexual_{tipo}", 0),
        f"caso_cant_bisexual_{tipo}":    st.session_state.get(f"caso_cant_bisexual_{tipo}", 0),
        f"caso_cant_zona_rural_{tipo}":  st.session_state.get(f"caso_cant_zona_rural_{tipo}", 0),
        f"caso_cant_zona_urbana_{tipo}": st.session_state.get(f"caso_cant_zona_urbana_{tipo}", 0),
        f"caso_cant_zona_reserva_{tipo}":st.session_state.get(f"caso_cant_zona_reserva_{tipo}", 0),
        f"caso_nivel_riesgo_{tipo}":     st.session_state.get(f"caso_nivel_riesgo_{tipo}", "Seleccione..."),
        f"caso_observaciones_{tipo}":    st.session_state.get(f"caso_observaciones_{tipo}", ""),
        f"caso_num_personas_{tipo}":     st.session_state.get(f"caso_num_personas_{tipo}", None),
        f"caso_companero_{tipo}":        st.session_state.get(f"caso_companero_{tipo}", "Seleccione..."),
        f"caso_hijos_menores_{tipo}":    st.session_state.get(f"caso_hijos_menores_{tipo}", None),
        f"caso_menores_otros_{tipo}":    st.session_state.get(f"caso_menores_otros_{tipo}", None),
        f"caso_adultos_mayores_{tipo}":  st.session_state.get(f"caso_adultos_mayores_{tipo}", None),
        f"caso_discapacidad_{tipo}":     st.session_state.get(f"caso_discapacidad_{tipo}", None),
        "composiciones_col": st.session_state.get("composiciones_col", []),
        f"caso_osiegd_{tipo}":              st.session_state.get(f"caso_osiegd_{tipo}", ""),
        f"caso_factor_discapacidad_{tipo}": st.session_state.get(f"caso_factor_discapacidad_{tipo}", "Seleccione..."),
        f"caso_factor_etnia_{tipo}":        st.session_state.get(f"caso_factor_etnia_{tipo}", "Seleccione..."),
        f"caso_factor_campesino_{tipo}":    st.session_state.get(f"caso_factor_campesino_{tipo}", "Seleccione..."),
        f"caso_factor_cuidador_{tipo}":     st.session_state.get(f"caso_factor_cuidador_{tipo}", "Seleccione..."),
        **{f"victima_{i}_{tipo}": st.session_state.get(f"victima_{i}_{tipo}", False)
           for i in range(len(_VICTIMA_CONFLICTO_ARMADO))},
        **{f"lider_{i}_{tipo}": st.session_state.get(f"lider_{i}_{tipo}", False)
           for i in range(len(_LIDER_SOCIAL_DDHH))},
        # Factores diferenciales colectivo
        **{f"fd_col_{gk}_{tipo}": st.session_state.get(f"fd_col_{gk}_{tipo}", 0)
           for gk, _, subs in _FACTORES_DIFER_COL if not subs},
        **{f"fd_col_{gk}_{sk}_{tipo}": st.session_state.get(f"fd_col_{gk}_{sk}_{tipo}", 0)
           for gk, _, subs in _FACTORES_DIFER_COL for sk, _ in subs},
        "hechos":            st.session_state.get("hechos", []),
        "perfiles":          st.session_state.get("perfiles", []),
        "perfiles_col":      st.session_state.get("perfiles_col", []),
        "antecedentes":      st.session_state.get("antecedentes", []),
        "perfiles_actuales": st.session_state.get("perfiles_actuales", []),
        "desplazamientos":   st.session_state.get("desplazamientos", []),
        "verificaciones":    st.session_state.get("verificaciones", []),
        f"imp_eco_dependencia_{tipo}":    st.session_state.get(f"imp_eco_dependencia_{tipo}", "Seleccione..."),
        f"imp_eco_iniciativas_{tipo}":    st.session_state.get(f"imp_eco_iniciativas_{tipo}", "Seleccione..."),
        f"imp_eco_empleos_{tipo}":        st.session_state.get(f"imp_eco_empleos_{tipo}", "Seleccione..."),
        f"imp_eco_ilicita_{tipo}":        st.session_state.get(f"imp_eco_ilicita_{tipo}", "Seleccione..."),
        f"imp_eco_bienes_{tipo}":         st.session_state.get(f"imp_eco_bienes_{tipo}", "Seleccione..."),
        f"imp_soc_tejido_{tipo}":         st.session_state.get(f"imp_soc_tejido_{tipo}", "Seleccione..."),
        f"imp_soc_redes_{tipo}":          st.session_state.get(f"imp_soc_redes_{tipo}", "Seleccione..."),
        f"imp_soc_traslado_{tipo}":       st.session_state.get(f"imp_soc_traslado_{tipo}", "Seleccione..."),
        f"imp_soc_confinamiento_{tipo}":  st.session_state.get(f"imp_soc_confinamiento_{tipo}", "Seleccione..."),
        f"imp_soc_movilidad_{tipo}":      st.session_state.get(f"imp_soc_movilidad_{tipo}", "Seleccione..."),
        f"imp_soc_desarraigo_{tipo}":     st.session_state.get(f"imp_soc_desarraigo_{tipo}", "Seleccione..."),
        f"imp_soc_normalizacion_{tipo}":  st.session_state.get(f"imp_soc_normalizacion_{tipo}", "Seleccione..."),
        f"imp_soc_libertad_{tipo}":       st.session_state.get(f"imp_soc_libertad_{tipo}", "Seleccione..."),
        f"imp_pol_participacion_{tipo}":  st.session_state.get(f"imp_pol_participacion_{tipo}", "Seleccione..."),
        f"imp_pol_liderazgos_{tipo}":     st.session_state.get(f"imp_pol_liderazgos_{tipo}", "Seleccione..."),
        f"imp_pol_oferta_{tipo}":         st.session_state.get(f"imp_pol_oferta_{tipo}", "Seleccione..."),
        f"imp_pol_derechos_{tipo}":       st.session_state.get(f"imp_pol_derechos_{tipo}", "Seleccione..."),
        f"imp_pol_estigmatizacion_{tipo}": st.session_state.get(f"imp_pol_estigmatizacion_{tipo}", "Seleccione..."),
        f"imp_pol_confianza_{tipo}":      st.session_state.get(f"imp_pol_confianza_{tipo}", "Seleccione..."),
        f"imp_sal_proyeccion_{tipo}":        st.session_state.get(f"imp_sal_proyeccion_{tipo}", "Seleccione..."),
        f"imp_sal_cuidados_{tipo}":          st.session_state.get(f"imp_sal_cuidados_{tipo}", "Seleccione..."),
        f"imp_sal_desescolarizacion_{tipo}": st.session_state.get(f"imp_sal_desescolarizacion_{tipo}", "Seleccione..."),
        f"imp_sal_abandono_{tipo}":          st.session_state.get(f"imp_sal_abandono_{tipo}", "Seleccione..."),
        f"imp_sal_psicosocial_{tipo}":       st.session_state.get(f"imp_sal_psicosocial_{tipo}", "Seleccione..."),
        f"imp_sal_discapacidad_{tipo}":      st.session_state.get(f"imp_sal_discapacidad_{tipo}", "Seleccione..."),
        f"imp_sal_dano_vida_{tipo}":         st.session_state.get(f"imp_sal_dano_vida_{tipo}", "Seleccione..."),
    }


def _btn_borrador(tipo, sufijo):
    """Botón compacto 💾 Guardar borrador alineado a la derecha, reutilizable en cualquier sección."""
    _, _col = st.columns([4, 1])
    with _col:
        if st.button("💾 Guardar borrador", key=f"borrador_{tipo}_{sufijo}",
                     use_container_width=True, type="secondary"):
            datos = _construir_datos_borrador(tipo)
            _bkey = f"borrador_cargado_{tipo}"
            if guardar_borrador(st.session_state.username, tipo, datos):
                st.session_state[_bkey] = True
                st.toast("✅ Borrador guardado", icon="💾")
            else:
                st.toast("❌ No se pudo guardar el borrador", icon="⚠️")


def formulario_casos(tipo="individual"):
    es_individual     = tipo == "individual"
    color             = "#4F8BFF" if es_individual else "#4ADE80"
    icono             = "👤"      if es_individual else "👥"
    label_badge       = "INDIVIDUAL" if es_individual else "COLECTIVO"
    titulo            = "Formulario Individual" if es_individual else "Formulario Colectivo"
    nombre_hoja_casos = TAB_NOMBRES[tipo]["casos"]

    (hoja_casos, hoja_hechos, hoja_perfiles, hoja_antecedentes,
     hoja_perfiles_actuales, hoja_desplazamientos, hoja_verificaciones,
     hoja_instancias_comunes, hoja_otras_orgs, sheet_url) = conectar_sheet_casos(tipo)
    if hoja_casos is None:
        st.error("⚠️ No se pudo conectar a Google Sheets"); return

    # ── Retomar borrador ──────────────────────────────────────────────────────
    _borrador_key = f"borrador_cargado_{tipo}"
    if not st.session_state.get(_borrador_key):
        borrador = cargar_borrador(st.session_state.username, tipo)
        if borrador is False:
            # Error de conexión: no se sabe si hay borrador, no activar autoguardado
            st.warning("⚠️ No se pudo verificar si hay un borrador guardado. Recarga la página para intentar de nuevo.")
        elif borrador is None:
            # Confirmado: sin borrador previo
            st.session_state[_borrador_key] = True
        if borrador and borrador is not False:
            st.warning(
                f"📝 Tienes un borrador guardado el **{borrador.get('_guardado_en', '—')}**. "
                "¿Deseas retomarlo?"
            )
            col_ret, col_des = st.columns(2)
            with col_ret:
                if st.button("↩️ Retomar borrador", use_container_width=True, type="primary", key=f"btn_retomar_{tipo}"):
                    _campos_fecha = {f"caso_fecha_nacimiento_{tipo}", f"caso_fecha_expedicion_{tipo}"}
                    _todos_campos = [
                        f"caso_tipo_estudio_{tipo}",
                        f"caso_ot_anio_{tipo}", f"caso_ot_numero_{tipo}",
                        f"caso_solicitante_{tipo}", f"caso_fecha_expedicion_{tipo}",
                        f"caso_tipo_evaluacion_{tipo}",
                        f"caso_tipo_colectivo_{tipo}",
                        f"caso_familiar_parte_comunes_{tipo}",
                        f"caso_tipo_poblacion_{tipo}",
                        *[f"subpob_{i}_{tipo}" for i in range(len(_SUBPOBLACIONES))],
                        *[f"subpob_cnt_{i}_{tipo}" for i in range(len(_SUBPOBLACIONES))],
                        f"caso_fecha_nacimiento_{tipo}", f"caso_sexo_{tipo}",
                        f"caso_genero_{tipo}", f"caso_orientacion_{tipo}", f"caso_jefatura_{tipo}",
                        f"p_departamento_{tipo}", f"p_municipio_{tipo}",
                        f"caso_zona_rural_{tipo}", f"caso_zona_reserva_{tipo}",
                        f"caso_cant_hombres_{tipo}", f"caso_cant_mujeres_{tipo}", f"caso_cant_intersexual_{tipo}",
                        f"caso_cant_femenino_{tipo}", f"caso_cant_masculino_{tipo}", f"caso_cant_transgenero_{tipo}",
                        f"caso_cant_heterosexual_{tipo}", f"caso_cant_homosexual_{tipo}", f"caso_cant_bisexual_{tipo}",
                        f"caso_cant_zona_rural_{tipo}", f"caso_cant_zona_urbana_{tipo}", f"caso_cant_zona_reserva_{tipo}",
                        f"caso_nivel_riesgo_{tipo}", f"caso_observaciones_{tipo}",
                        f"caso_num_personas_{tipo}", f"caso_companero_{tipo}",
                        f"caso_hijos_menores_{tipo}", f"caso_menores_otros_{tipo}",
                        f"caso_adultos_mayores_{tipo}", f"caso_discapacidad_{tipo}",
                        f"caso_osiegd_{tipo}",
                        f"caso_factor_discapacidad_{tipo}", f"caso_factor_etnia_{tipo}",
                        f"caso_factor_campesino_{tipo}", f"caso_factor_cuidador_{tipo}",
                        *[f"victima_{i}_{tipo}" for i in range(len(_VICTIMA_CONFLICTO_ARMADO))],
                        *[f"lider_{i}_{tipo}" for i in range(len(_LIDER_SOCIAL_DDHH))],
                        *[f"fd_col_{gk}_{tipo}" for gk, _, subs in _FACTORES_DIFER_COL if not subs],
                        *[f"fd_col_{gk}_{sk}_{tipo}" for gk, _, subs in _FACTORES_DIFER_COL for sk, _ in subs],
                        f"imp_eco_dependencia_{tipo}",
                        f"imp_eco_iniciativas_{tipo}",
                        f"imp_eco_empleos_{tipo}",
                        f"imp_eco_ilicita_{tipo}",
                        f"imp_eco_bienes_{tipo}",
                        f"imp_soc_tejido_{tipo}",
                        f"imp_soc_redes_{tipo}",
                        f"imp_soc_traslado_{tipo}",
                        f"imp_soc_confinamiento_{tipo}",
                        f"imp_soc_movilidad_{tipo}",
                        f"imp_soc_desarraigo_{tipo}",
                        f"imp_soc_normalizacion_{tipo}",
                        f"imp_soc_libertad_{tipo}",
                        f"imp_pol_participacion_{tipo}",
                        f"imp_pol_liderazgos_{tipo}",
                        f"imp_pol_oferta_{tipo}",
                        f"imp_pol_derechos_{tipo}",
                        f"imp_pol_estigmatizacion_{tipo}",
                        f"imp_pol_confianza_{tipo}",
                        f"imp_sal_proyeccion_{tipo}",
                        f"imp_sal_cuidados_{tipo}",
                        f"imp_sal_desescolarizacion_{tipo}",
                        f"imp_sal_abandono_{tipo}",
                        f"imp_sal_psicosocial_{tipo}",
                        f"imp_sal_discapacidad_{tipo}",
                        f"imp_sal_dano_vida_{tipo}",
                    ]
                    for campo in _todos_campos:
                        if campo in borrador:
                            valor = borrador[campo]
                            if campo in _campos_fecha and isinstance(valor, str) and valor:
                                try:
                                    valor = date.fromisoformat(valor)
                                except ValueError:
                                    valor = None
                            st.session_state[campo] = valor
                    st.session_state.hechos           = borrador.get("hechos", [])
                    st.session_state.perfiles         = borrador.get("perfiles", [])
                    st.session_state.perfiles_col     = borrador.get("perfiles_col", [])
                    st.session_state.antecedentes     = borrador.get("antecedentes", [])
                    st.session_state.perfiles_actuales = borrador.get("perfiles_actuales", [])
                    st.session_state.desplazamientos   = borrador.get("desplazamientos", [])
                    st.session_state.verificaciones    = borrador.get("verificaciones", [])
                    st.session_state.composiciones_col = borrador.get("composiciones_col", [])
                    st.session_state[_borrador_key] = True
                    st.rerun()
            with col_des:
                if st.button("🗑️ Descartar borrador", use_container_width=True, type="secondary", key=f"btn_descartar_{tipo}"):
                    eliminar_borrador(st.session_state.username, tipo)
                    for _campo in [
                        f"caso_tipo_estudio_{tipo}",
                        f"caso_ot_anio_{tipo}", f"caso_ot_numero_{tipo}",
                        f"caso_solicitante_{tipo}", f"caso_fecha_expedicion_{tipo}",
                        f"caso_tipo_poblacion_{tipo}",
                        *[f"subpob_{i}_{tipo}" for i in range(len(_SUBPOBLACIONES))],
                        *[f"subpob_cnt_{i}_{tipo}" for i in range(len(_SUBPOBLACIONES))],
                        f"caso_fecha_nacimiento_{tipo}", f"caso_sexo_{tipo}",
                        f"caso_genero_{tipo}", f"caso_orientacion_{tipo}", f"caso_jefatura_{tipo}",
                        f"p_departamento_{tipo}", f"p_municipio_{tipo}",
                        f"caso_zona_rural_{tipo}", f"caso_zona_reserva_{tipo}",
                        f"caso_cant_hombres_{tipo}", f"caso_cant_mujeres_{tipo}", f"caso_cant_intersexual_{tipo}",
                        f"caso_cant_femenino_{tipo}", f"caso_cant_masculino_{tipo}", f"caso_cant_transgenero_{tipo}",
                        f"caso_cant_heterosexual_{tipo}", f"caso_cant_homosexual_{tipo}", f"caso_cant_bisexual_{tipo}",
                        f"caso_cant_zona_rural_{tipo}", f"caso_cant_zona_urbana_{tipo}", f"caso_cant_zona_reserva_{tipo}",
                        f"caso_nivel_riesgo_{tipo}", f"caso_observaciones_{tipo}",
                        f"caso_num_personas_{tipo}", f"caso_companero_{tipo}",
                        f"caso_hijos_menores_{tipo}", f"caso_menores_otros_{tipo}",
                        f"caso_adultos_mayores_{tipo}", f"caso_discapacidad_{tipo}",
                        f"caso_osiegd_{tipo}",
                        f"caso_factor_discapacidad_{tipo}", f"caso_factor_etnia_{tipo}",
                        f"caso_factor_campesino_{tipo}", f"caso_factor_cuidador_{tipo}",
                        *[f"victima_{i}_{tipo}" for i in range(len(_VICTIMA_CONFLICTO_ARMADO))],
                        *[f"lider_{i}_{tipo}" for i in range(len(_LIDER_SOCIAL_DDHH))],
                        *[f"fd_col_{gk}_{tipo}" for gk, _, subs in _FACTORES_DIFER_COL if not subs],
                        *[f"fd_col_{gk}_{sk}_{tipo}" for gk, _, subs in _FACTORES_DIFER_COL for sk, _ in subs],
                        f"imp_eco_dependencia_{tipo}",
                        f"imp_eco_iniciativas_{tipo}",
                        f"imp_eco_empleos_{tipo}",
                        f"imp_eco_ilicita_{tipo}",
                        f"imp_eco_bienes_{tipo}",
                        f"imp_soc_tejido_{tipo}",
                        f"imp_soc_redes_{tipo}",
                        f"imp_soc_traslado_{tipo}",
                        f"imp_soc_confinamiento_{tipo}",
                        f"imp_soc_movilidad_{tipo}",
                        f"imp_soc_desarraigo_{tipo}",
                        f"imp_soc_normalizacion_{tipo}",
                        f"imp_soc_libertad_{tipo}",
                        f"imp_pol_participacion_{tipo}",
                        f"imp_pol_liderazgos_{tipo}",
                        f"imp_pol_oferta_{tipo}",
                        f"imp_pol_derechos_{tipo}",
                        f"imp_pol_estigmatizacion_{tipo}",
                        f"imp_pol_confianza_{tipo}",
                        f"imp_sal_proyeccion_{tipo}",
                        f"imp_sal_cuidados_{tipo}",
                        f"imp_sal_desescolarizacion_{tipo}",
                        f"imp_sal_abandono_{tipo}",
                        f"imp_sal_psicosocial_{tipo}",
                        f"imp_sal_discapacidad_{tipo}",
                        f"imp_sal_dano_vida_{tipo}",
                    ]:
                        st.session_state.pop(_campo, None)
                    desp_guardados = 0
                    if st.session_state.desplazamientos:
                        _start_desp = hoja_desplazamientos.count() + 1
                        _rows_desp = [
                            [
                                _start_desp + i, id_caso, ot_te.strip(),
                                desp.get("motivo", ""),
                                desp.get("medios_transporte", ""),
                                desp.get("dep_origen", ""),
                                desp.get("mun_origen", ""),
                                desp.get("dep_destino", ""),
                                desp.get("mun_destino", ""),
                                desp.get("frecuencia", ""),
                                desp.get("tipo_via", ""),
                                st.session_state.nombre_completo, st.session_state.username
                            ]
                            for i, desp in enumerate(st.session_state.desplazamientos)
                        ]
                        hoja_desplazamientos.append_many_rows(_rows_desp)
                        desp_guardados = len(_rows_desp)
                    ver_guardados = 0
                    if st.session_state.verificaciones:
                        _start_ver = hoja_verificaciones.count() + 1
                        _rows_ver = [
                            [
                                _start_ver + i, id_caso, ot_te.strip(),
                                ver.get("fuente", ""),
                                ver.get("nombre_fuente", ""),
                                ver.get("v_hechos_riesgo", ""),
                                ver.get("v_lugar_hechos", ""),
                                ver.get("v_actor_hechos", ""),
                                ver.get("v_motivacion_amenaza", ""),
                                ver.get("v_perfil_antiguo", ""),
                                ver.get("v_modo_participacion", ""),
                                ver.get("v_rol_perfil_antiguo", ""),
                                ver.get("v_frente_columna", ""),
                                ver.get("v_perfil_actual", ""),
                                ver.get("v_organizacion", ""),
                                ver.get("v_rol_perfil_actual", ""),
                                ver.get("criterios", ""),
                                st.session_state.nombre_completo, st.session_state.username
                            ]
                            for i, ver in enumerate(st.session_state.verificaciones)
                        ]
                        hoja_verificaciones.append_many_rows(_rows_ver)
                        ver_guardados = len(_rows_ver)
                    st.session_state.hechos = []
                    st.session_state.perfiles = []
                    st.session_state.antecedentes = []
                    st.session_state.perfiles_actuales = []
                    st.session_state.desplazamientos = []
                    st.session_state.verificaciones = []
                    st.session_state[_borrador_key] = True
                    st.rerun()
            st.stop()

    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("← Volver", type="secondary"):
            st.session_state.vista = None
            st.session_state.hechos = []
            st.session_state.perfiles = []
            st.session_state.perfiles_col = []
            st.session_state.perfiles_actuales = []
            st.session_state.desplazamientos = []
            st.session_state.composiciones_col = []
            st.session_state.antecedentes = []
            st.session_state[f"borrador_cargado_{tipo}"] = False
            st.rerun()
    with col_title:
        rgb = "79,139,255" if es_individual else "74,222,128"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
            <span style="font-size:22px;">{icono}</span>
            <span style="font-size:22px;font-weight:600;color:#F0F0F0;">{titulo}</span>
            <span style="background:rgba({rgb},0.1);border:1px solid rgba({rgb},0.3);
                         color:{color};font-size:10px;letter-spacing:2px;
                         padding:3px 9px;border-radius:2px;">{label_badge}</span>
        </div>
        <p style="font-size:12px;color:#555;margin:0;">
            Registrando como: <strong style="color:#888;">{st.session_state.nombre_completo}</strong></p>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📝 DATOS DE OT/TE")

    # ── Tipo de estudio (ancho completo) ─────────────────────────────────────
    tipo_estudio = st.selectbox(
        "Tipo de Estudio *",
        ["Seleccione...", "Orden de Trabajo", "Trámite de Emergencia"],
        key=f"caso_tipo_estudio_{tipo}"
    )

    es_emergencia = tipo_estudio == "Trámite de Emergencia"

    # ── Fila: Año OT | Número OT ──────────────────────────────────────────────
    col_anio, col_num = st.columns(2)
    with col_anio:
        label_anio = "Año OT" if es_emergencia else "Año OT *"
        ot_anio = st.number_input(label_anio, min_value=2000, max_value=2026, value=None,
                                  step=1, key=f"caso_ot_anio_{tipo}")
    with col_num:
        label_num = "Número OT" if es_emergencia else "Número OT *"
        ot_numero = st.number_input(label_num, min_value=0, max_value=9999, value=None,
                                    step=1, key=f"caso_ot_numero_{tipo}")

    ot_te = f"OT-{int(ot_anio)}-{str(int(ot_numero)).zfill(3)}" if (ot_anio is not None and ot_numero is not None) else ""

    # ── Fila: Entidad Solicitante | Fecha Expedición OT ──────────────────────
    _opts_solicitante = ["Seleccione...", "TERCEROS", "A NOMBRE PROPIO", "ONG",
                         "INSTITUCIÓN DEL ESTADO COLOMBIANO", "ORGANIZACIÓN INTERNACIONAL"]
    if st.session_state.get(f"caso_solicitante_{tipo}") not in _opts_solicitante:
        st.session_state[f"caso_solicitante_{tipo}"] = "Seleccione..."
    col_sol, col_fecha_ot = st.columns(2)
    with col_sol:
        solicitante = st.selectbox("Entidad Solicitante *", _opts_solicitante,
                                   key=f"caso_solicitante_{tipo}")
    with col_fecha_ot:
        fecha_expedicion_ot = st.date_input("Fecha de Expedición OT *", value=None,
                                            key=f"caso_fecha_expedicion_{tipo}")

    # ── Tipo de Evaluación (fila propia) ─────────────────────────────────────
    tipo_evaluacion = st.selectbox(
        "Tipo de Evaluación *",
        ["Seleccione...", "EVALUACIÓN POR PRIMERA VEZ",
         "REEVALUACIÓN POR HECHOS SOBREVINIENTES", "REEVALUACIÓN POR TEMPORALIDAD"],
        key=f"caso_tipo_evaluacion_{tipo}"
    )

    # ── Tipo de Colectivo (solo colectivo) ───────────────────────────────────
    if not es_individual:
        tipo_colectivo = st.selectbox(
            "Tipo de Colectivo *",
            ["Seleccione...", "Familiar", "Gremial (Asociaciones, Cooperativas, etc.)", "ETCR, NAR, ETC.", "Estructura de partido"],
            key=f"caso_tipo_colectivo_{tipo}"
        )
        if tipo_colectivo == "Estructura de partido":
            tipo_estructura_partido = st.selectbox(
                "Tipo de Estructura *",
                ["Seleccione...", "Comuna", "Local", "Municipal", "Metropolitana", "Departamental", "Nacional"],
                key=f"caso_tipo_estructura_partido_{tipo}"
            )
            _opciones_adscrita = {
                "Comuna":       ["Municipal", "Local"],
                "Local":        ["Metropolitana", "Departamental"],
                "Municipal":    ["Metropolitana", "Departamental"],
            }
            if tipo_estructura_partido == "Metropolitana":
                estructura_adscrita = "Departamental"
            elif tipo_estructura_partido in _opciones_adscrita:
                estructura_adscrita = st.selectbox(
                    "Estructura a la que está adscrita el colectivo evaluado *",
                    ["Seleccione..."] + _opciones_adscrita[tipo_estructura_partido],
                    key=f"caso_estructura_adscrita_{tipo}"
                )
            else:
                estructura_adscrita = ""
            # ── Conteos de sub-estructuras (lógica de omisión según #2) ──────
            cant_comunas      = None
            cant_locales      = None
            cant_municipales  = None
            cant_metropolitanas = None
            cant_consejerias  = None
            if tipo_estructura_partido == "Local":
                cant_comunas = st.number_input("Cantidad de Comunas", min_value=0, step=1,
                                               key=f"caso_cant_comunas_{tipo}")
            elif tipo_estructura_partido == "Municipal":
                cant_comunas = st.number_input("Cantidad de Comunas", min_value=0, step=1,
                                               key=f"caso_cant_comunas_{tipo}")
            elif tipo_estructura_partido == "Metropolitana":
                cant_locales = st.number_input("Cantidad de Locales", min_value=0, step=1,
                                               key=f"caso_cant_locales_{tipo}")
            elif tipo_estructura_partido == "Departamental":
                _cc1, _cc2 = st.columns(2)
                with _cc1:
                    cant_municipales = st.number_input("Cantidad de Municipales", min_value=0, step=1,
                                                       key=f"caso_cant_municipales_{tipo}")
                with _cc2:
                    cant_metropolitanas = st.number_input("Cantidad de Metropolitanas", min_value=0, step=1,
                                                          key=f"caso_cant_metropolitanas_{tipo}")
            elif tipo_estructura_partido == "Nacional":
                cant_consejerias = st.number_input("Cantidad de Consejerías", min_value=0, step=1,
                                                   key=f"caso_cant_consejerias_{tipo}")
        else:
            tipo_estructura_partido = ""
            estructura_adscrita = ""
            cant_comunas = cant_locales = cant_municipales = cant_metropolitanas = cant_consejerias = None
    else:
        tipo_colectivo = ""
        tipo_estructura_partido = ""
        estructura_adscrita = ""
        cant_comunas = cant_locales = cant_municipales = cant_metropolitanas = cant_consejerias = None

    # ── Tipo de Población (solo individual) ──────────────────────────────────
    if es_individual:
        tipo_poblacion = st.selectbox("Tipo de Población *", _TIPOS_POBLACION,
                                      key=f"caso_tipo_poblacion_{tipo}")
    else:
        tipo_poblacion = ""


    # ── FAMILIAR HACE PARTE DEL PARTIDO COMUNES ──────────────────────────────
    # Solo visible cuando tipo_poblacion == FAMILIAR DE REINCORPORADO/A
    if tipo_poblacion == "FAMILIAR DE REINCORPORADO/A":
        st.selectbox(
            "FAMILIAR HACE PARTE DEL PARTIDO COMUNES",
            ["Seleccione...", "SI", "NO REPORTA"],
            key=f"caso_familiar_parte_comunes_{tipo}"
        )

    # ── Subpoblación ──────────────────────────────────────────────────────────
    if es_individual:
        st.markdown("**Subpoblación \\***")
        cols_chk = st.columns(2)
        subpoblacion = [
            opcion for i, opcion in enumerate(_SUBPOBLACIONES)
            if cols_chk[i % 2].checkbox(opcion, key=f"subpob_{i}_{tipo}")
        ]
    else:
        st.markdown("**Cantidad por Subpoblación**")
        _cols_sp = st.columns(2)
        subpoblacion = [
            f"{opcion}:{_cols_sp[i % 2].number_input(f'Cantidad de {opcion}', min_value=0, step=1, key=f'subpob_cnt_{i}_{tipo}')}"
            for i, opcion in enumerate(_SUBPOBLACIONES)
        ]

    _btn_borrador(tipo, "tras_datos_ot")

    # Controla si se muestra la sección Perfil Antiguo
    _mostrar_perfil_antiguo = tipo_poblacion in ("REINCORPORADO/A", "FAMILIAR DE REINCORPORADO/A")

    st.markdown("---")
    st.subheader("👤 CARACTERÍSTICAS DEMOGRÁFICAS")

    # ── Fila: Fecha de Nacimiento | Sexo (solo individual) ───────────────────
    if es_individual:
        col_fnac, col_sexo = st.columns(2)
        with col_fnac:
            fecha_nacimiento = st.date_input("Fecha de Nacimiento *", value=None,
                                             min_value=date(1900, 1, 1),
                                             max_value=date.today(),
                                             key=f"caso_fecha_nacimiento_{tipo}")
        with col_sexo:
            sexo = st.selectbox("Sexo *", ["Seleccione...", "Hombre", "Mujer", "Intersexual"],
                                key=f"caso_sexo_{tipo}")
    else:
        # Colectivo: "Familiar" → sin fecha; los demás → "Fecha última acta de asamblea ordinaria"
        if tipo_colectivo != "Familiar":
            fecha_nacimiento = st.date_input("Fecha última acta de asamblea ordinaria", value=None,
                                             min_value=date(1900, 1, 1),
                                             max_value=date.today(),
                                             key=f"caso_fecha_nacimiento_{tipo}")
        else:
            fecha_nacimiento = None

        # ── Departamento | Municipio (colectivo) ──────────────────────────────
        _es_estructura_partido = tipo_colectivo == "Estructura de partido"
        _label_dep = "DEPARTAMENTO DE UBICACIÓN DE LA SEDE *" if _es_estructura_partido else "SELECCIONE EL DEPARTAMENTO *"
        _label_mun = "MUNICIPIO DE UBICACIÓN DE LA SEDE *"    if _es_estructura_partido else "SELECCIONE EL MUNICIPIO *"
        _col_dep, _col_mun = st.columns(2)
        with _col_dep:
            departamento = st.selectbox(_label_dep,
                                        ["Seleccione..."] + list(_MUNICIPIOS.keys()),
                                        key=f"p_departamento_{tipo}")
        with _col_mun:
            municipio = st.selectbox(_label_mun,
                                     _MUNICIPIOS.get(departamento, ["Seleccione..."]),
                                     key=f"p_municipio_{tipo}")

        # ── Cantidad por Sexo ─────────────────────────────────────────────────
        st.markdown("**Cantidad por Sexo**")
        col_sx1, col_sx2, col_sx3 = st.columns(3)
        with col_sx1:
            _cant_hombres     = st.number_input("Cantidad de Hombres", min_value=0, step=1,
                                                key=f"caso_cant_hombres_{tipo}")
        with col_sx2:
            _cant_mujeres     = st.number_input("Cantidad de Mujeres", min_value=0, step=1,
                                                key=f"caso_cant_mujeres_{tipo}")
        with col_sx3:
            _cant_intersexual = st.number_input("Cantidad de Intersexual", min_value=0, step=1,
                                                key=f"caso_cant_intersexual_{tipo}")
        sexo = f"Hombres:{_cant_hombres} | Mujeres:{_cant_mujeres} | Intersexual:{_cant_intersexual}"

        # ── Cantidad por Género ────────────────────────────────────────────────
        st.markdown("**Cantidad por Género**")
        col_gn1, col_gn2, col_gn3 = st.columns(3)
        with col_gn1:
            _cant_femenino    = st.number_input("Cantidad de Femenino", min_value=0, step=1,
                                                key=f"caso_cant_femenino_{tipo}")
        with col_gn2:
            _cant_masculino   = st.number_input("Cantidad de Masculino", min_value=0, step=1,
                                                key=f"caso_cant_masculino_{tipo}")
        with col_gn3:
            _cant_transgenero = st.number_input("Cantidad de Transgénero", min_value=0, step=1,
                                                key=f"caso_cant_transgenero_{tipo}")
        genero = f"Femenino:{_cant_femenino} | Masculino:{_cant_masculino} | Transgénero:{_cant_transgenero}"

        # ── Cantidad por Orientación Sexual ────────────────────────────────────
        st.markdown("**Cantidad por Orientación Sexual**")
        col_or1, col_or2, col_or3 = st.columns(3)
        with col_or1:
            _cant_heterosexual = st.number_input("Cantidad de Heterosexual", min_value=0, step=1,
                                                 key=f"caso_cant_heterosexual_{tipo}")
        with col_or2:
            _cant_homosexual   = st.number_input("Cantidad de Homosexual", min_value=0, step=1,
                                                 key=f"caso_cant_homosexual_{tipo}")
        with col_or3:
            _cant_bisexual     = st.number_input("Cantidad de Bisexual", min_value=0, step=1,
                                                 key=f"caso_cant_bisexual_{tipo}")
        orientacion_sexual = (f"Heterosexual:{_cant_heterosexual} | Homosexual:{_cant_homosexual} | "
                              f"Bisexual:{_cant_bisexual}")

        jefatura_hogar = None

    # ── Fila: Género | Orientación Sexual | Jefatura del Hogar (solo individual)
    if es_individual:
        col_gen, col_ori, col_jef = st.columns(3)
        with col_gen:
            genero = st.selectbox("Género *", _GENEROS, key=f"caso_genero_{tipo}")
        with col_ori:
            orientacion_sexual = st.selectbox("Orientación Sexual *", _ORIENTACIONES_SEXUALES,
                                              key=f"caso_orientacion_{tipo}")
        with col_jef:
            jefatura_hogar = st.selectbox("Jefatura del Hogar *", _JEFATURA_HOGAR,
                                          key=f"caso_jefatura_{tipo}")

    # ── Fila: Departamento | Municipio (solo individual; colectivo ya lo renderiza arriba) ──
    if es_individual:
        col_dep, col_mun = st.columns(2)
        with col_dep:
            departamento = st.selectbox("SELECCIONE EL DEPARTAMENTO *",
                                        ["Seleccione..."] + list(_MUNICIPIOS.keys()),
                                        key=f"p_departamento_{tipo}")
        with col_mun:
            municipio = st.selectbox("SELECCIONE EL MUNICIPIO *",
                                     _MUNICIPIOS.get(departamento, ["Seleccione..."]),
                                     key=f"p_municipio_{tipo}")

    # ── Fila: Zona Rural | Zona de Reserva Campesina (solo individual) ─────────
    if es_individual:
        col_rural, col_reserva = st.columns(2)
        with col_rural:
            zona_rural = st.selectbox("¿Vive en zona rural? *", _SI_NO_REPORTA,
                                      key=f"caso_zona_rural_{tipo}")
        with col_reserva:
            zona_reserva = st.selectbox("¿Vive en zona de reserva campesina? *", _SI_NO_REPORTA,
                                        key=f"caso_zona_reserva_{tipo}")
    else:
        # ── Cantidad por Zona de Residencia ───────────────────────────────────
        st.markdown("**Cantidad por Zona de Residencia**")
        col_z1, col_z2, col_z3 = st.columns(3)
        with col_z1:
            _cant_zona_rural    = st.number_input("Cantidad en zona rural", min_value=0, step=1,
                                                  key=f"caso_cant_zona_rural_{tipo}")
        with col_z2:
            _cant_zona_urbana   = st.number_input("Cantidad en zona urbana", min_value=0, step=1,
                                                  key=f"caso_cant_zona_urbana_{tipo}")
        with col_z3:
            _cant_zona_reserva  = st.number_input("Cantidad en zona de reserva campesina",
                                                  min_value=0, step=1,
                                                  key=f"caso_cant_zona_reserva_{tipo}")
        zona_rural   = f"Rural:{_cant_zona_rural} | Urbana:{_cant_zona_urbana}"
        zona_reserva = f"Reserva Campesina:{_cant_zona_reserva}"

    # ── Composición Núcleo Familiar (solo individual) ─────────────────────────
    if es_individual:
        st.markdown("---")
        st.subheader("👨‍👩‍👧‍👦 COMPOSICIÓN NÚCLEO FAMILIAR")

        col_np, col_cp = st.columns(2)
        with col_np:
            num_personas = st.number_input("Número de personas en el núcleo familiar *",
                                           min_value=0, step=1, value=None,
                                           key=f"caso_num_personas_{tipo}")
        with col_cp:
            companero = st.selectbox("¿Tiene compañero(a) permanente? *", _SI_NO,
                                     key=f"caso_companero_{tipo}")

        col_hm, col_md = st.columns(2)
        with col_hm:
            num_hijos_menores = st.number_input("Número de hijos menores de edad *",
                                                min_value=0, step=1, value=None,
                                                key=f"caso_hijos_menores_{tipo}")
        with col_md:
            num_menores_otros = st.number_input("Número de menores de edad distintos a hijos *",
                                                min_value=0, step=1, value=None,
                                                key=f"caso_menores_otros_{tipo}")

        col_am, col_di = st.columns(2)
        with col_am:
            num_adultos_mayores = st.number_input("Número de adultos mayores (60 años en adelante) *",
                                                  min_value=0, step=1, value=None,
                                                  key=f"caso_adultos_mayores_{tipo}")
        with col_di:
            num_discapacidad = st.number_input("Número de personas en situación de discapacidad *",
                                               min_value=0, step=1, value=None,
                                               key=f"caso_discapacidad_{tipo}")
        # Variables exclusivas de colectivo — no aplican para individual
        comp_nucleos_familiares  = None
        comp_num_personas        = None
        comp_menores             = None
        comp_adultos_mayores_col = None
        comp_discapacidad_col    = None
        comp_num_integrantes     = None
        tipo_division            = ""
        comp_otro_cual           = ""
        comp_proyecto_productivo = ""
        comp_actividad_economica = []
    else:
        num_personas = None
        companero = ""
        num_hijos_menores = None
        num_menores_otros = None
        num_adultos_mayores = None
        num_discapacidad = None
        # osiegd, factor_discapacidad, factor_etnia, factor_campesino,
        # factor_cuidador, victima_conflicto, lider_social
        # se asignan en la sección FACTORES DIFERENCIALES (colectivo) más abajo

        # ── Composición del Colectivo (multiregistro) ────────────────────────
        st.markdown("---")
        st.subheader("👥 COMPOSICIÓN DEL COLECTIVO")

        if "composiciones_col" not in st.session_state:
            st.session_state.composiciones_col = []

        _edit_comp_key = f"editando_comp_{tipo}"

        for _ci, _comp in enumerate(st.session_state.composiciones_col):
            with st.container(border=True):
                _cc1, _cc2, _cc3 = st.columns([4, 1, 1])
                with _cc1:
                    if tipo_colectivo == "Familiar":
                        _res = f"Composición #{_ci+1} — {_comp.get('comp_num_personas', 0)} personas"
                    else:
                        _div_r = _comp.get('tipo_division', '')
                        if _div_r == 'Otro/¿Cuál?' and _comp.get('comp_otro_cual'):
                            _div_r = _comp.get('comp_otro_cual')
                        _res = f"Composición #{_ci+1} — {_div_r} ({_comp.get('comp_num_integrantes', 0)} integrantes)"
                    st.markdown(f"**{_res}**")
                with _cc2:
                    if st.button("✏️", key=f"edit_comp_{tipo}_{_ci}", help="Editar"):
                        st.session_state[_edit_comp_key] = _ci
                        st.rerun()
                with _cc3:
                    if st.button("🗑️", key=f"del_comp_{tipo}_{_ci}", help="Eliminar"):
                        st.session_state.composiciones_col.pop(_ci)
                        if st.session_state.get(_edit_comp_key) == _ci:
                            st.session_state[_edit_comp_key] = None
                        st.rerun()

                if st.session_state.get(_edit_comp_key) == _ci:
                    st.markdown(f"**✏️ Editando Composición #{_ci+1}**")
                    _render_comp_col_form(_comp, tipo_colectivo, tipo, _ci)
                    _cs1, _cs2 = st.columns(2)
                    with _cs1:
                        if st.button("💾 Guardar cambios", key=f"save_comp_{tipo}_{_ci}",
                                     use_container_width=True, type="primary"):
                            _nuevo_comp = _recoger_comp_col(tipo_colectivo, tipo, _ci)
                            if _nuevo_comp is not None:
                                st.session_state.composiciones_col[_ci] = _nuevo_comp
                                st.session_state[_edit_comp_key] = None
                                st.rerun()
                    with _cs2:
                        if st.button("✖️ Cancelar", key=f"cancel_comp_{tipo}_{_ci}",
                                     use_container_width=True):
                            st.session_state[_edit_comp_key] = None
                            st.rerun()

        _exp_comp = len(st.session_state.composiciones_col) == 0
        with st.expander("➕ Agregar Composición", expanded=_exp_comp):
            _render_comp_col_form(None, tipo_colectivo, tipo, "new")
            if st.button("✅ Guardar Composición", key=f"btn_add_comp_{tipo}",
                         use_container_width=True, type="primary"):
                _nuevo_comp = _recoger_comp_col(tipo_colectivo, tipo, "new")
                if _nuevo_comp is not None:
                    st.session_state.composiciones_col.append(_nuevo_comp)
                    st.rerun()

        # Variables de resumen para el submit (primer registro o vacíos)
        _comp0 = st.session_state.composiciones_col[0] if st.session_state.composiciones_col else {}
        comp_nucleos_familiares  = _comp0.get("comp_nucleos_familiares", None)
        comp_num_personas        = _comp0.get("comp_num_personas", None)
        comp_menores             = _comp0.get("comp_menores", None)
        comp_adultos_mayores_col = _comp0.get("comp_adultos_mayores", None)
        comp_discapacidad_col    = _comp0.get("comp_discapacidad", None)
        comp_num_integrantes     = _comp0.get("comp_num_integrantes", None)
        tipo_division            = _comp0.get("tipo_division", "")
        comp_otro_cual           = _comp0.get("comp_otro_cual", "")
        comp_proyecto_productivo = _comp0.get("comp_proyecto_productivo", "")
        comp_actividad_economica = _comp0.get("comp_actividad_economica", [])

    # ── Factores Diferenciales ─────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🏷️ FACTORES DIFERENCIALES")

    if es_individual:
        osiegd = st.text_input(
            "F. Orientación Sexual, Identidad y Expresión de Género Diversa (OSIEGD)",
            key=f"caso_osiegd_{tipo}"
        )

        col_fd, col_fe = st.columns(2)
        with col_fd:
            factor_discapacidad = st.selectbox("F. Discapacidad *", _DISCAPACIDAD,
                                               key=f"caso_factor_discapacidad_{tipo}")
        with col_fe:
            factor_etnia = st.selectbox("F. Étnico *", _ETNIA,
                                        key=f"caso_factor_etnia_{tipo}")

        col_fc, col_fcuid = st.columns(2)
        with col_fc:
            factor_campesino = st.selectbox("F. Campesino *", _SI_NO_REPORTA,
                                            key=f"caso_factor_campesino_{tipo}")
        with col_fcuid:
            factor_cuidador = st.selectbox("F. Cuidador *", _CUIDADOR,
                                           key=f"caso_factor_cuidador_{tipo}")

        st.markdown("**F. Víctima de Conflicto Armado \\***")
        cols_vic = st.columns(2)
        victima_conflicto = [
            opcion for i, opcion in enumerate(_VICTIMA_CONFLICTO_ARMADO)
            if cols_vic[i % 2].checkbox(opcion, key=f"victima_{i}_{tipo}")
        ]

        st.markdown("**F. Líder Social y Defensor de DDHH \\***")
        cols_lid = st.columns(2)
        lider_social = [
            opcion for i, opcion in enumerate(_LIDER_SOCIAL_DDHH)
            if cols_lid[i % 2].checkbox(opcion, key=f"lider_{i}_{tipo}")
        ]

    else:
        # ── Colectivo: conteos numéricos por factor diferencial ────────────────
        _fd_osiegd_cnt = _fd_campesino_cnt = 0
        _fd_disc_parts = _fd_etnico_parts = _fd_victima_parts = []
        _fd_cuidadora_parts = _fd_lider_parts = []

        for _gk, _glabel, _subs in _FACTORES_DIFER_COL:
            st.markdown(f"**{_glabel}**")
            if not _subs:
                # Campo único
                _v_cnt = st.number_input(
                    f"Número de {_glabel}",
                    min_value=0, step=1,
                    key=f"fd_col_{_gk}_{tipo}"
                )
                if _gk == "osiegd":
                    _fd_osiegd_cnt = _v_cnt
                elif _gk == "campesino":
                    _fd_campesino_cnt = _v_cnt
            else:
                # Sub-campos en 2 columnas
                _sub_cols = st.columns(2)
                _parts = []
                for _i_s, (_sk, _slabel) in enumerate(_subs):
                    _v_sub = _sub_cols[_i_s % 2].number_input(
                        f"Número de {_slabel}",
                        min_value=0, step=1,
                        key=f"fd_col_{_gk}_{_sk}_{tipo}"
                    )
                    _parts.append((_slabel, _v_sub))
                if _gk == "discapacidad":
                    _fd_disc_parts = _parts
                elif _gk == "etnico":
                    _fd_etnico_parts = _parts
                elif _gk == "victima_ca":
                    _fd_victima_parts = _parts
                elif _gk == "cuidadora":
                    _fd_cuidadora_parts = _parts
                elif _gk == "lider_ddhh":
                    _fd_lider_parts = _parts

        # Serializar a variables del submit
        osiegd          = str(_fd_osiegd_cnt) if _fd_osiegd_cnt else ""
        factor_discapacidad = " | ".join(f"{l}:{v}" for l, v in _fd_disc_parts if v) or ""
        factor_etnia        = " | ".join(f"{l}:{v}" for l, v in _fd_etnico_parts if v) or ""
        factor_campesino    = str(_fd_campesino_cnt) if _fd_campesino_cnt else ""
        factor_cuidador     = " | ".join(f"{l}:{v}" for l, v in _fd_cuidadora_parts if v) or ""
        victima_conflicto   = [f"{l}:{v}" for l, v in _fd_victima_parts if v]
        lider_social        = [f"{l}:{v}" for l, v in _fd_lider_parts if v]

    _btn_borrador(tipo, "tras_composicion")

    # ── Antecedentes ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📁 ANTECEDENTES")
    st.caption("Opcional. Agrega uno o varios antecedentes asociados a este caso.")

    if "antecedentes" not in st.session_state:
        st.session_state.antecedentes = []

    _edit_ant_key = f"editando_antecedente_{tipo}"
    _REGISTRA_RES = ["Seleccione...", "SI", "NO", "SI MEDIDAS COLECTIVAS"]

    for i, ant in enumerate(st.session_state.antecedentes):
        with st.container(border=True):
            if st.session_state.get(_edit_ant_key) == i:
                # ── Modo edición ──────────────────────────────────────────────
                st.markdown(f"**✏️ Editando Antecedente #{i+1}**")
                _anio_val_e = int(ant.get("anio_resolucion")) if str(ant.get("anio_resolucion","")).isdigit() else None
                _mes_val_e  = int(ant.get("mes_resolucion"))  if str(ant.get("mes_resolucion","")).isdigit()  else None
                _dia_val_e  = int(ant.get("dia_resolucion"))  if str(ant.get("dia_resolucion","")).isdigit()  else None

                _reg_ot_opts = ["Seleccione...", "SI", "NO"]
                ea_reg_ot = st.selectbox(
                    "¿REGISTRA OT ANTECEDENTES? *", _reg_ot_opts,
                    index=_reg_ot_opts.index(ant.get("registra_ot","Seleccione..."))
                          if ant.get("registra_ot","") in _reg_ot_opts else 0,
                    key=f"ea_reg_ot_{tipo}_{i}"
                )

                # ── NUEVO: Campos condicionales en edición
                if ea_reg_ot == "SI":
                    col_ot_e, col_ruta_e = st.columns(2)
                    with col_ot_e:
                        ea_ot_te = st.text_input(
                            "OT - TE ANTECEDE *",
                            value=ant.get("ot_te_antecede", ""),
                            key=f"ea_ot_te_{tipo}_{i}"
                        )
                    with col_ruta_e:
                        ea_tipo_ruta = st.selectbox(
                            "TIPO DE RUTA ANTECEDENTE *",
                            _TIPOS_RUTA_ANTECEDENTE,
                            index=_TIPOS_RUTA_ANTECEDENTE.index(ant.get("tipo_ruta_antecedente", "Seleccione..."))
                            if ant.get("tipo_ruta_antecedente", "") in _TIPOS_RUTA_ANTECEDENTE else 0,
                            key=f"ea_tipo_ruta_{tipo}_{i}"
                        )
                    _opts_nra = ["Seleccione...", "ORDINARIO", "EXTRAORDINARIO", "EXTRAORDINARIO DE GÉNERO", "EXTREMO", "INACTIVACIÓN"]
                    ea_nivel_riesgo_ant = st.selectbox(
                        "RECOMENDACIÓN NIVEL DE RIESGO OT-TE ANTERIOR *",
                        _opts_nra,
                        index=_opts_nra.index(ant.get("nivel_riesgo_anterior", "Seleccione..."))
                        if ant.get("nivel_riesgo_anterior", "") in _opts_nra else 0,
                        key=f"ea_nivel_riesgo_ant_{tipo}_{i}"
                    )
                else:
                    ea_ot_te = ""
                    ea_tipo_ruta = ""
                    ea_nivel_riesgo_ant = ""

                ea_reg_res = st.selectbox(
                    "¿REGISTRA RESOLUCIONES O MEDIDAS VIGENTES? *", _REGISTRA_RES,
                    index=_REGISTRA_RES.index(ant.get("registra_resoluciones","Seleccione..."))
                          if ant.get("registra_resoluciones","") in _REGISTRA_RES else 0,
                    key=f"ea_reg_res_{tipo}_{i}"
                )
                if ea_reg_res == "SI":
                    ea_num_resolucion = st.text_input(
                        "NÚMERO DE RESOLUCIÓN MTSP",
                        value=ant.get("numero_resolucion", ""),
                        key=f"ea_num_resolucion_{tipo}_{i}"
                    )
                else:
                    ea_num_resolucion = ""
                if ea_reg_res == "SI":
                    col_a1, col_a2, col_a3 = st.columns(3)
                    with col_a1:
                        ea_anio = st.number_input(
                            "AÑO RESOLUCIÓN MTSP", min_value=2000, max_value=2099,
                            value=_anio_val_e, step=1, key=f"ea_anio_{tipo}_{i}"
                        )
                    with col_a2:
                        ea_mes = st.number_input(
                            "MES RESOLUCIÓN MTSP", min_value=1, max_value=12,
                            value=_mes_val_e, step=1, key=f"ea_mes_{tipo}_{i}"
                        )
                    _e_max_dia = 31
                    _e_dia_key = f"ea_dia_{tipo}_{i}"
                    if ea_anio is not None and ea_mes is not None:
                        try:
                            _e_max_dia = calendar.monthrange(int(ea_anio), int(ea_mes))[1]
                            _e_dia_cur = st.session_state.get(_e_dia_key)
                            if _e_dia_cur is not None and _e_dia_cur > _e_max_dia:
                                st.session_state[_e_dia_key] = _e_max_dia
                        except Exception:
                            _e_max_dia = 31
                    with col_a3:
                        ea_dia = st.number_input(
                            "DÍA RESOLUCIÓN MTSP", min_value=1, max_value=_e_max_dia,
                            value=_dia_val_e, step=1, key=f"ea_dia_{tipo}_{i}"
                        )
                else:
                    ea_anio = None
                    ea_mes  = None
                    ea_dia  = None
                col_save_a, col_cancel_a = st.columns(2)
                with col_save_a:
                    if st.button("💾 Guardar cambios", key=f"ea_save_{tipo}_{i}",
                                 type="primary", use_container_width=True):
                        err_ea = []
                        if ea_reg_ot  == "Seleccione...": err_ea.append("Debe indicar si registra OT antecedentes")
                        # ── NUEVO: Validar campos condicionales en edición
                        if ea_reg_ot == "SI":
                            if not ea_ot_te.strip():
                                err_ea.append("Debe especificar OT - TE ANTECEDE")
                            if ea_tipo_ruta == "Seleccione...":
                                err_ea.append("Debe seleccionar el tipo de ruta")
                        if ea_reg_res == "Seleccione...": err_ea.append("Debe indicar si registra resoluciones o medidas vigentes")
                        if err_ea:
                            for e in err_ea: st.error(f"• {e}")
                        else:
                            st.session_state.antecedentes[i] = {
                                "registra_ot":            ea_reg_ot,
                                # ── NUEVO: Guardar campos condicionales
                                "ot_te_antecede": ea_ot_te if ea_reg_ot == "SI" else "",
                                "tipo_ruta_antecedente": ea_tipo_ruta if ea_reg_ot == "SI" else "",
                                "nivel_riesgo_anterior": ea_nivel_riesgo_ant if ea_reg_ot == "SI" else "",
                                "registra_resoluciones":  ea_reg_res,
                                "numero_resolucion":       ea_num_resolucion if ea_reg_res == "SI" else "",
                                "anio_resolucion":        str(int(ea_anio)) if ea_anio is not None else "",
                                "mes_resolucion":         str(int(ea_mes))  if ea_mes  is not None else "",
                                "dia_resolucion":         str(int(ea_dia))  if ea_dia  is not None else "",
                            }
                            st.session_state[_edit_ant_key] = None
                            st.rerun()
                with col_cancel_a:
                    if st.button("✖ Cancelar", key=f"ea_cancel_{tipo}_{i}",
                                 type="secondary", use_container_width=True):
                        st.session_state[_edit_ant_key] = None
                        st.rerun()
            else:
                # ── Modo lectura ──────────────────────────────────────────────
                col_tit_a, col_edit_a, col_del_a = st.columns([4, 1, 1])
                with col_tit_a:
                    st.markdown(f"**Antecedente #{i+1}**")
                with col_edit_a:
                    if st.button("✏️", key=f"edit_a_{tipo}_{i}", help="Editar este antecedente"):
                        st.session_state[_edit_ant_key] = i
                        st.rerun()
                with col_del_a:
                    if st.button("🗑️", key=f"del_a_{tipo}_{i}", help="Eliminar este antecedente"):
                        st.session_state.antecedentes.pop(i)
                        st.session_state[_edit_ant_key] = None
                        st.rerun()
                ca1, ca2 = st.columns(2)
                with ca1:
                    st.write(f"📋 **¿Registra OT Antecedentes?:** {ant.get('registra_ot','')}")
                    # ── NUEVO: Mostrar campos condicionales si existen
                    if ant.get('registra_ot') == "SI":
                        st.write(f"🔖 **OT - TE ANTECEDE:** {ant.get('ot_te_antecede', '')}")
                        st.write(f"🛣️ **Tipo de Ruta:** {ant.get('tipo_ruta_antecedente', '')}")
                        st.write(f"⚠️ **Recomendación Nivel de Riesgo OT-TE Anterior:** {ant.get('nivel_riesgo_anterior', '')}")
                    st.write(f"📋 **¿Registra Resoluciones?:** {ant.get('registra_resoluciones','')}")
                    if ant.get('registra_resoluciones') == "SI":
                        st.write(f"🔢 **Número de Resolución MTSP:** {ant.get('numero_resolucion', '')}")
                with ca2:
                    _fecha_ant = " / ".join(filter(None, [
                        ant.get("dia_resolucion",""),
                        ant.get("mes_resolucion",""),
                        ant.get("anio_resolucion","")
                    ]))
                    if _fecha_ant:
                        st.write(f"📅 **Fecha Resolución MTSP (D/M/A):** {_fecha_ant}")

    with st.expander("➕ Agregar Antecedente", expanded=len(st.session_state.antecedentes) == 0):
        ant_reg_ot = st.selectbox(
            "¿REGISTRA OT ANTECEDENTES? *",
            ["Seleccione...", "SI", "NO"],
            key=f"ant_reg_ot_{tipo}"
        )

        # ── NUEVO: Campos condicionales que aparecen SOLO si es "SI"
        if ant_reg_ot == "SI":
            col_ot, col_ruta = st.columns(2)
            with col_ot:
                ant_ot_te_antecede = st.text_input(
                    "OT - TE ANTECEDE *",
                    placeholder="Ej: 2024-145",
                    key=f"ant_ot_te_{tipo}"
                )
            with col_ruta:
                ant_tipo_ruta = st.selectbox(
                    "TIPO DE RUTA ANTECEDENTE *",
                    _TIPOS_RUTA_ANTECEDENTE,
                    key=f"ant_tipo_ruta_{tipo}"
                )
            ant_nivel_riesgo_ant = st.selectbox(
                "RECOMENDACIÓN NIVEL DE RIESGO OT-TE ANTERIOR *",
                ["Seleccione...", "ORDINARIO", "EXTRAORDINARIO", "EXTRAORDINARIO DE GÉNERO", "EXTREMO", "INACTIVACIÓN"],
                key=f"ant_nivel_riesgo_ant_{tipo}"
            )
        else:
            # Si es "NO" o "Seleccione...", estos campos no existen
            ant_ot_te_antecede = ""
            ant_tipo_ruta = ""
            ant_nivel_riesgo_ant = ""

        ant_reg_res = st.selectbox(
            "¿REGISTRA RESOLUCIONES O MEDIDAS VIGENTES? *",
            _REGISTRA_RES,
            key=f"ant_reg_res_{tipo}"
        )
        if ant_reg_res == "SI":
            ant_num_resolucion = st.text_input(
                "NÚMERO DE RESOLUCIÓN MTSP",
                placeholder="Ej: 1234",
                key=f"ant_num_resolucion_{tipo}"
            )
        else:
            ant_num_resolucion = ""
        if ant_reg_res == "SI":
            col_anio_ant, col_mes_ant, col_dia_ant = st.columns(3)
            with col_anio_ant:
                ant_anio = st.number_input(
                    "AÑO RESOLUCIÓN MTSP", min_value=2000, max_value=2099,
                    value=None, step=1, key=f"ant_anio_{tipo}"
                )
            with col_mes_ant:
                ant_mes = st.number_input(
                    "MES RESOLUCIÓN MTSP", min_value=1, max_value=12,
                    value=None, step=1, key=f"ant_mes_{tipo}"
                )
            _max_dia_ant = 31
            _dia_ant_key = f"ant_dia_{tipo}"
            if ant_anio is not None and ant_mes is not None:
                try:
                    _max_dia_ant = calendar.monthrange(int(ant_anio), int(ant_mes))[1]
                    _dia_cur_ant = st.session_state.get(_dia_ant_key)
                    if _dia_cur_ant is not None and _dia_cur_ant > _max_dia_ant:
                        st.session_state[_dia_ant_key] = _max_dia_ant
                except Exception:
                    _max_dia_ant = 31
            with col_dia_ant:
                ant_dia = st.number_input(
                    "DÍA RESOLUCIÓN MTSP", min_value=1, max_value=_max_dia_ant,
                    value=None, step=1, key=f"ant_dia_{tipo}"
                )
        else:
            ant_anio = None
            ant_mes  = None
            ant_dia  = None
        st.markdown("")
        if st.button("➕ Agregar este antecedente", use_container_width=True,
                     key=f"btn_add_ant_{tipo}", type="secondary"):
            err_ant = []
            if ant_reg_ot  == "Seleccione...": err_ant.append("Debe indicar si registra OT antecedentes")
            # ── NUEVO: Validar campos condicionales
            if ant_reg_ot == "SI":
                if not ant_ot_te_antecede.strip():
                    err_ant.append("Debe especificar OT - TE ANTECEDE")
                if ant_tipo_ruta == "Seleccione...":
                    err_ant.append("Debe seleccionar el tipo de ruta")
            if ant_reg_res == "Seleccione...": err_ant.append("Debe indicar si registra resoluciones o medidas vigentes")
            if err_ant:
                for e in err_ant: st.error(f"• {e}")
            else:
                st.session_state.antecedentes.append({
                    "registra_ot":           ant_reg_ot,
                    "ot_te_antecede": ant_ot_te_antecede if ant_reg_ot == "SI" else "",
                    "tipo_ruta_antecedente": ant_tipo_ruta if ant_reg_ot == "SI" else "",
                    "nivel_riesgo_anterior": ant_nivel_riesgo_ant if ant_reg_ot == "SI" else "",
                    "registra_resoluciones": ant_reg_res,
                    "numero_resolucion":      ant_num_resolucion if ant_reg_res == "SI" else "",
                    "anio_resolucion":       str(int(ant_anio)) if ant_anio is not None else "",
                    "mes_resolucion":        str(int(ant_mes))  if ant_mes  is not None else "",
                    "dia_resolucion":        str(int(ant_dia))  if ant_dia  is not None else "",
                })
                st.success("✅ Antecedente agregado"); st.rerun()

    # ── Perfil Antiguo (solo si aplica según tipo de población) ─────────────
    if _mostrar_perfil_antiguo:
        # ── Perfil Antiguo ────────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("Perfil Antiguo")
        st.caption("Opcional. Agrega uno o varios perfiles FARC-EP asociados a este caso.")

        if "perfiles" not in st.session_state:
            st.session_state.perfiles = []

        _edit_perfil_key = f"editando_perfil_{tipo}"
        _MODOS_PART = ["Seleccione...", "Combatiente", "Miliciano/a", "Colaborador/a",
                       "Privado de la libertad", "Otro"]

        for i, perfil in enumerate(st.session_state.perfiles):
            with st.container(border=True):
                if st.session_state.get(_edit_perfil_key) == i:
                    # ── Modo edición ──────────────────────────────────────────────
                    st.markdown(f"**✏️ Editando Perfil #{i+1}**")
                    pc1, pc2 = st.columns(2)
                    with pc1:
                        ep_modo = st.selectbox("MODO DE PARTICIPACIÓN EN LAS FARC-EP *", _MODOS_PART,
                            index=_MODOS_PART.index(perfil.get("modo_participacion","Seleccione..."))
                                  if perfil.get("modo_participacion","") in _MODOS_PART else 0,
                            key=f"ep_modo_{tipo}_{i}")
                        ep_anio = st.number_input("AÑO DE INGRESO, TRASLADO O CAPTURA *",
                            min_value=1950, max_value=2026, step=1,
                            value=int(perfil["anio_ingreso"]) if str(perfil.get("anio_ingreso","")).isdigit() else 2000,
                            key=f"ep_anio_{tipo}_{i}")
                        _bloques = ["Seleccione..."] + list(_ESTRUCTURAS.keys())
                        ep_bloque = st.selectbox("SELECCIONE EL BLOQUE DE OPERACIÓN *", _bloques,
                            index=_bloques.index(perfil.get("bloque","Seleccione..."))
                                  if perfil.get("bloque","") in _bloques else 0,
                            key=f"ep_bloque_{tipo}_{i}")
                    with pc2:
                        ep_estructura = "Seleccione..."
                        if ep_bloque != "Seleccione...":
                            _ops_est = _ESTRUCTURAS[ep_bloque]
                            ep_estructura = st.selectbox("ESTRUCTURA *", _ops_est,
                                index=_ops_est.index(perfil.get("estructura",""))
                                      if perfil.get("estructura","") in _ops_est else 0,
                                key=f"ep_estructura_{tipo}_{i}")
                        ep_lugar = st.selectbox("LUGAR DE ACREDITACIÓN *", _LUGAR_ACREDITACION,
                            index=_LUGAR_ACREDITACION.index(perfil.get("lugar_acreditacion","Seleccione..."))
                                  if perfil.get("lugar_acreditacion","") in _LUGAR_ACREDITACION else 0,
                            key=f"ep_lugar_{tipo}_{i}")

                    _rol_actual = [r.strip() for r in perfil.get("rol","").split("|")
                                   if r.strip() in _ROLES[1:]]
                    st.markdown("**ROL/ACTIVIDADES P_ANTIGUO \\***")
                    cols_rol_ep = st.columns(2)
                    ep_rol = [
                        opcion for j, opcion in enumerate(_ROLES[1:])
                        if cols_rol_ep[j % 2].checkbox(opcion, value=(opcion in _rol_actual),
                                                        key=f"ep_rol_{j}_{tipo}_{i}")
                    ]

                    ep_otro_rol = ""
                    if "Otro" in ep_rol:
                        ep_otro_rol = st.text_input("¿QUÉ OTRO ROL?",
                            value=perfil.get("otro_rol",""), key=f"ep_otro_rol_{tipo}_{i}")

                    ep_mostrar_libertad = (ep_modo == "Privado de la libertad")
                    ep_meses = ""
                    ep_inst  = "Seleccione..."
                    if ep_mostrar_libertad:
                        ep_meses = st.number_input("NO. MESES PRIVADO DE LA LIBERTAD",
                            min_value=0, max_value=600, step=1,
                            value=int(perfil["meses_privado"]) if str(perfil.get("meses_privado","")).isdigit() else 0,
                            key=f"ep_meses_{tipo}_{i}")
                        ep_inst = st.selectbox("TIPO DE INSTITUCIÓN PENITENCIARIA", _INSTITUCIONES,
                            index=_INSTITUCIONES.index(perfil.get("tipo_institucion","Seleccione..."))
                                  if perfil.get("tipo_institucion","") in _INSTITUCIONES else 0,
                            key=f"ep_inst_{tipo}_{i}")

                    ep_pabellon = ""
                    if ep_mostrar_libertad and ep_inst == "CO -COMPLEJO CARCELARÍO":
                        _pab = ["Seleccione...", "Sí", "No"]
                        ep_pabellon = st.selectbox("PABELLÓN DE ALTA SEGURIDAD", _pab,
                            index=_pab.index(perfil.get("pabellon_alta_seguridad","Seleccione..."))
                                  if perfil.get("pabellon_alta_seguridad","") in _pab else 0,
                            key=f"ep_pabellon_{tipo}_{i}")

                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("💾 Guardar cambios", key=f"ep_save_{tipo}_{i}",
                                     type="primary", use_container_width=True):
                            err_ep = []
                            if ep_modo      == "Seleccione...": err_ep.append("El modo de participación es obligatorio")
                            if ep_bloque    == "Seleccione...": err_ep.append("El bloque es obligatorio")
                            if ep_estructura== "Seleccione...": err_ep.append("La estructura es obligatoria")
                            if ep_lugar     == "Seleccione...": err_ep.append("El lugar de acreditación es obligatorio")
                            if len(ep_rol)  == 0:               err_ep.append("El rol es obligatorio")
                            if "Otro" in ep_rol and not ep_otro_rol.strip(): err_ep.append("Especifica el otro rol")
                            if err_ep:
                                for e in err_ep: st.error(f"• {e}")
                            else:
                                st.session_state.perfiles[i] = {
                                    "modo_participacion": ep_modo,
                                    "anio_ingreso":       ep_anio,
                                    "bloque":             ep_bloque,
                                    "estructura":         ep_estructura,
                                    "lugar_acreditacion": ep_lugar,
                                    "rol":                " | ".join(ep_rol),
                                    "otro_rol":           ep_otro_rol.strip(),
                                    "meses_privado":      str(ep_meses) if ep_mostrar_libertad else "",
                                    "tipo_institucion":   ep_inst if ep_inst != "Seleccione..." else "",
                                    "pabellon_alta_seguridad": ep_pabellon if ep_pabellon != "Seleccione..." else "",
                                }
                                st.session_state[_edit_perfil_key] = None
                                st.rerun()
                    with col_cancel:
                        if st.button("✖ Cancelar", key=f"ep_cancel_{tipo}_{i}",
                                     type="secondary", use_container_width=True):
                            st.session_state[_edit_perfil_key] = None
                            st.rerun()
                else:
                    # ── Modo lectura ──────────────────────────────────────────────
                    col_tit, col_edit, col_del = st.columns([4, 1, 1])
                    with col_tit: st.markdown(f"**Perfil #{i+1} — {perfil.get('modo_participacion', '')}**")
                    with col_edit:
                        if st.button("✏️", key=f"edit_p_{tipo}_{i}", help="Editar este perfil"):
                            st.session_state[_edit_perfil_key] = i
                            st.rerun()
                    with col_del:
                        if st.button("🗑️", key=f"del_perfil_{tipo}_{i}", help="Eliminar este perfil"):
                            st.session_state.perfiles.pop(i)
                            st.session_state[_edit_perfil_key] = None
                            st.rerun()
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"📋 **Modo de Participación:** {perfil.get('modo_participacion','')}")
                        st.write(f"📅 **Año Ingreso/Traslado/Captura:** {perfil.get('anio_ingreso','')}")
                        st.write(f"🗺️ **Bloque:** {perfil.get('bloque','')}")
                        st.write(f"🏗️ **Estructura:** {perfil.get('estructura','')}")
                        st.write(f"📍 **Lugar de Acreditación:** {perfil.get('lugar_acreditacion','')}")
                    with c2:
                        st.write(f"🎭 **Rol/Actividades:** {perfil.get('rol','')}")
                        if perfil.get('otro_rol'): st.write(f"❓ **Otro Rol:** {perfil.get('otro_rol','')}")
                        if perfil.get('subpoblacion'): st.write(f"👥 **Subpoblación (Índice 1):** {perfil.get('subpoblacion','')}")
                        if perfil.get('meses_privado'): st.write(f"⛓️ **Meses Privado de Libertad:** {perfil.get('meses_privado','')}")
                        if perfil.get('tipo_institucion'): st.write(f"🏛️ **Tipo Institución:** {perfil.get('tipo_institucion','')}")
                        if perfil.get('pabellon_alta_seguridad'): st.write(f"🔒 **Pabellón Alta Seguridad:** {perfil.get('pabellon_alta_seguridad','')}")

        with st.expander("➕ Agregar Perfil Antiguo", expanded=len(st.session_state.perfiles) == 0):

            p_modo = st.selectbox("MODO DE PARTICIPACIÓN EN LAS FARC-EP *",
                ["Seleccione...", "Combatiente", "Miliciano/a", "Colaborador/a",
                 "Privado de la libertad", "Otro"],
                key=f"p_modo_{tipo}")

            p_anio = st.number_input(
                "AÑO DE INGRESO, TRASLADO O CAPTURA *",
                min_value=1950,
                max_value=2026,
                step=1,
                key=f"p_anio_{tipo}"
                )

            p_bloque = st.selectbox("SELECCIONE EL BLOQUE DE OPERACIÓN *",
                ["Seleccione..."] + list(_ESTRUCTURAS.keys()),
                key=f"p_bloque_{tipo}")

            p_estructura = "Seleccione..."
            if p_bloque != "Seleccione...":
                opciones_estructura = _ESTRUCTURAS[p_bloque]
                p_estructura = st.selectbox("ESTRUCTURA *", opciones_estructura,
                    key=f"p_estructura_{tipo}")

            p_lugar_acreditacion = st.selectbox("LUGAR DE ACREDITACIÓN *",
            _LUGAR_ACREDITACION,
                key=f"p_lugar_{tipo}")

            st.markdown("**ROL/ACTIVIDADES P_ANTIGUO \\***")
            cols_rol = st.columns(2)
            p_rol = [
                opcion for j, opcion in enumerate(_ROLES[1:])
                if cols_rol[j % 2].checkbox(opcion, key=f"p_rol_{j}_{tipo}")
            ]

            p_otro_rol = ""
            p_otro_rol_libre = ""
            if "Otro" in p_rol:
                p_otro_rol = st.text_input("¿QUÉ OTRO ROL?", key=f"p_otro_rol_{tipo}")
                p_otro_rol_libre = p_otro_rol

            mostrar_libertad = (p_modo == "Privado de la libertad")

            p_meses_privado    = ""
            p_tipo_institucion = "Seleccione..."
            if mostrar_libertad:
                p_meses_privado = st.number_input("NO. MESES PRIVADO DE LA LIBERTAD",
                    min_value=0, max_value=600, step=1, key=f"p_meses_{tipo}")

                p_tipo_institucion = st.selectbox("TIPO DE INSTITUCIÓN PENITENCIARIA",
                    _INSTITUCIONES, key=f"p_inst_{tipo}")

            p_pabellon = ""
            if mostrar_libertad and p_tipo_institucion == "CO -COMPLEJO CARCELARÍO":
                p_pabellon = st.selectbox("PABELLÓN DE ALTA SEGURIDAD",
                    ["Seleccione...", "Sí", "No"], key=f"p_pabellon_{tipo}")

            st.markdown("")
            if st.button("➕ Agregar este perfil", use_container_width=True,
                         key=f"btn_add_perfil_{tipo}", type="secondary"):
                err_p = []
                if p_modo        == "Seleccione...": err_p.append("El modo de participación es obligatorio")
                if not p_anio:
                    err_p.append("El año de ingreso es obligatorio")
                if p_bloque      == "Seleccione...": err_p.append("El bloque de operación es obligatorio")
                if p_estructura  == "Seleccione...": err_p.append("La estructura es obligatoria")
                if p_lugar_acreditacion == "Seleccione...": err_p.append("El lugar de acreditación es obligatorio")
                if len(p_rol) == 0:                              err_p.append("El rol es obligatorio")
                if "Otro" in p_rol and not p_otro_rol.strip():  err_p.append("Especifica el otro rol")
                if err_p:
                    for e in err_p: st.error(f"• {e}")
                else:
                    st.session_state.perfiles.append({
                        "modo_participacion":  p_modo,
                        "anio_ingreso":        p_anio,
                        "bloque":              p_bloque,
                        "estructura":          p_estructura,
                        "lugar_acreditacion":  p_lugar_acreditacion,
                        "rol":                 " | ".join(p_rol),
                        "otro_rol":            p_otro_rol.strip() if p_otro_rol else "",
                        "meses_privado":       str(p_meses_privado) if mostrar_libertad else "",
                        "tipo_institucion":    p_tipo_institucion if p_tipo_institucion != "Seleccione..." else "",
                        "pabellon_alta_seguridad": p_pabellon if p_pabellon != "Seleccione..." else "",
                    })
                    st.success("✅ Perfil Antiguo agregado"); st.rerun()

    # ── Perfil Antiguo Colectivo (solo colectivo) ─────────────────────────────
    if not es_individual:
        st.markdown("---")
        _es_familiar_col = tipo_colectivo == "Familiar"
        _label_registro  = "Representante" if _es_familiar_col else "Directivo"
        _titulo_seccion  = "PERFIL ANTIGUO DEL REPRESENTANTE" if _es_familiar_col else "PERFIL ANTIGUO DE DIRECTIVOS"
        st.subheader(_titulo_seccion)
        if _es_familiar_col:
            st.caption("Agrega uno o varios perfiles FARC-EP del colectivo familiar.")
        else:
            st.caption("Agrega uno o varios perfiles FARC-EP de los directivos del colectivo.")

        if "perfiles_col" not in st.session_state:
            st.session_state.perfiles_col = []

        _edit_pcol_key = f"editando_perfil_col_{tipo}"
        _MODOS_PART_COL = ["Seleccione...", "Combatiente", "Miliciano/a", "Colaborador/a",
                           "Privado de la libertad", "Otro"]

        for i, perfil in enumerate(st.session_state.perfiles_col):
            with st.container(border=True):
                if st.session_state.get(_edit_pcol_key) == i:
                    st.markdown(f"**✏️ Editando {_label_registro} #{i+1}**")
                    pc1, pc2 = st.columns(2)
                    with pc1:
                        epc_modo = st.selectbox("MODO DE PARTICIPACIÓN EN LAS FARC-EP *", _MODOS_PART_COL,
                            index=_MODOS_PART_COL.index(perfil.get("modo_participacion", "Seleccione..."))
                                  if perfil.get("modo_participacion", "") in _MODOS_PART_COL else 0,
                            key=f"epc_modo_{tipo}_{i}")
                        epc_anio = st.number_input("AÑO DE INGRESO, TRASLADO O CAPTURA *",
                            min_value=1950, max_value=2026, step=1,
                            value=int(perfil["anio_ingreso"]) if str(perfil.get("anio_ingreso", "")).isdigit() else 2000,
                            key=f"epc_anio_{tipo}_{i}")
                        _bloques_col = ["Seleccione..."] + list(_ESTRUCTURAS.keys())
                        epc_bloque = st.selectbox("SELECCIONE EL BLOQUE DE OPERACIÓN *", _bloques_col,
                            index=_bloques_col.index(perfil.get("bloque", "Seleccione..."))
                                  if perfil.get("bloque", "") in _bloques_col else 0,
                            key=f"epc_bloque_{tipo}_{i}")
                    with pc2:
                        epc_estructura = "Seleccione..."
                        if epc_bloque != "Seleccione...":
                            _ops_est_col = _ESTRUCTURAS[epc_bloque]
                            epc_estructura = st.selectbox("ESTRUCTURA *", _ops_est_col,
                                index=_ops_est_col.index(perfil.get("estructura", ""))
                                      if perfil.get("estructura", "") in _ops_est_col else 0,
                                key=f"epc_estructura_{tipo}_{i}")
                        epc_lugar = st.selectbox("LUGAR DE ACREDITACIÓN *", _LUGAR_ACREDITACION,
                            index=_LUGAR_ACREDITACION.index(perfil.get("lugar_acreditacion", "Seleccione..."))
                                  if perfil.get("lugar_acreditacion", "") in _LUGAR_ACREDITACION else 0,
                            key=f"epc_lugar_{tipo}_{i}")

                    st.markdown("**ROL/ACTIVIDADES P_ANTIGUO \\***")
                    _rol_actual_col = [r.strip() for r in perfil.get("rol", "").split("|") if r.strip() in _ROLES[1:]]
                    cols_rol_epc = st.columns(2)
                    epc_rol = [
                        opcion for j, opcion in enumerate(_ROLES[1:])
                        if cols_rol_epc[j % 2].checkbox(opcion, value=(opcion in _rol_actual_col),
                                                         key=f"epc_rol_{j}_{tipo}_{i}")
                    ]
                    epc_otro_rol = ""
                    if "Otro" in epc_rol:
                        epc_otro_rol = st.text_input("¿QUÉ OTRO ROL?",
                            value=perfil.get("otro_rol", ""), key=f"epc_otro_rol_{tipo}_{i}")

                    epc_mostrar_libertad = (epc_modo == "Privado de la libertad")
                    epc_meses = ""
                    epc_inst  = "Seleccione..."
                    if epc_mostrar_libertad:
                        epc_meses = st.number_input("NO. MESES PRIVADO DE LA LIBERTAD",
                            min_value=0, max_value=600, step=1,
                            value=int(perfil["meses_privado"]) if str(perfil.get("meses_privado", "")).isdigit() else 0,
                            key=f"epc_meses_{tipo}_{i}")
                        epc_inst = st.selectbox("TIPO DE INSTITUCIÓN PENITENCIARIA", _INSTITUCIONES,
                            index=_INSTITUCIONES.index(perfil.get("tipo_institucion", "Seleccione..."))
                                  if perfil.get("tipo_institucion", "") in _INSTITUCIONES else 0,
                            key=f"epc_inst_{tipo}_{i}")

                    epc_pabellon = ""
                    if epc_mostrar_libertad and epc_inst == "CO -COMPLEJO CARCELARÍO":
                        _pab_col = ["Seleccione...", "Sí", "No"]
                        epc_pabellon = st.selectbox("PABELLÓN DE ALTA SEGURIDAD", _pab_col,
                            index=_pab_col.index(perfil.get("pabellon_alta_seguridad", "Seleccione..."))
                                  if perfil.get("pabellon_alta_seguridad", "") in _pab_col else 0,
                            key=f"epc_pabellon_{tipo}_{i}")

                    col_save_col, col_cancel_col = st.columns(2)
                    with col_save_col:
                        if st.button("💾 Guardar cambios", key=f"epc_save_{tipo}_{i}",
                                     type="primary", use_container_width=True):
                            err_epc = []
                            if epc_modo      == "Seleccione...": err_epc.append("El modo de participación es obligatorio")
                            if epc_bloque    == "Seleccione...": err_epc.append("El bloque es obligatorio")
                            if epc_estructura== "Seleccione...": err_epc.append("La estructura es obligatoria")
                            if epc_lugar     == "Seleccione...": err_epc.append("El lugar de acreditación es obligatorio")
                            if len(epc_rol)  == 0:               err_epc.append("El rol es obligatorio")
                            if "Otro" in epc_rol and not epc_otro_rol.strip(): err_epc.append("Especifica el otro rol")
                            if err_epc:
                                for e in err_epc: st.error(f"• {e}")
                            else:
                                st.session_state.perfiles_col[i] = {
                                    "modo_participacion": epc_modo,
                                    "anio_ingreso":       epc_anio,
                                    "bloque":             epc_bloque,
                                    "estructura":         epc_estructura,
                                    "lugar_acreditacion": epc_lugar,
                                    "rol":                " | ".join(epc_rol),
                                    "otro_rol":           epc_otro_rol.strip(),
                                    "meses_privado":      str(epc_meses) if epc_mostrar_libertad else "",
                                    "tipo_institucion":   epc_inst if epc_inst != "Seleccione..." else "",
                                    "pabellon_alta_seguridad": epc_pabellon if epc_pabellon != "Seleccione..." else "",
                                }
                                st.session_state[_edit_pcol_key] = None
                                st.rerun()
                    with col_cancel_col:
                        if st.button("✖ Cancelar", key=f"epc_cancel_{tipo}_{i}",
                                     type="secondary", use_container_width=True):
                            st.session_state[_edit_pcol_key] = None
                            st.rerun()
                else:
                    col_tit_col, col_edit_col, col_del_col = st.columns([4, 1, 1])
                    with col_tit_col:
                        st.markdown(f"**{_label_registro} #{i+1} — {perfil.get('modo_participacion', '')}**")
                    with col_edit_col:
                        if st.button("✏️", key=f"edit_pcol_{tipo}_{i}", help="Editar"):
                            st.session_state[_edit_pcol_key] = i
                            st.rerun()
                    with col_del_col:
                        if st.button("🗑️", key=f"del_pcol_{tipo}_{i}", help="Eliminar"):
                            st.session_state.perfiles_col.pop(i)
                            st.session_state[_edit_pcol_key] = None
                            st.rerun()
                    c1_col, c2_col = st.columns(2)
                    with c1_col:
                        st.write(f"📋 **Modo de Participación:** {perfil.get('modo_participacion', '')}")
                        st.write(f"📅 **Año Ingreso/Traslado/Captura:** {perfil.get('anio_ingreso', '')}")
                        st.write(f"🗺️ **Bloque:** {perfil.get('bloque', '')}")
                        st.write(f"🏗️ **Estructura:** {perfil.get('estructura', '')}")
                        st.write(f"📍 **Lugar de Acreditación:** {perfil.get('lugar_acreditacion', '')}")
                    with c2_col:
                        st.write(f"🎭 **Rol/Actividades:** {perfil.get('rol', '')}")
                        if perfil.get('otro_rol'): st.write(f"❓ **Otro Rol:** {perfil.get('otro_rol', '')}")
                        if perfil.get('meses_privado'): st.write(f"⛓️ **Meses Privado de Libertad:** {perfil.get('meses_privado', '')}")
                        if perfil.get('tipo_institucion'): st.write(f"🏛️ **Tipo Institución:** {perfil.get('tipo_institucion', '')}")
                        if perfil.get('pabellon_alta_seguridad'): st.write(f"🔒 **Pabellón Alta Seguridad:** {perfil.get('pabellon_alta_seguridad', '')}")

        _puede_agregar = True
        if _puede_agregar:
            _label_exp = f"➕ Agregar Perfil del {_label_registro}" if _es_familiar_col else f"➕ Agregar {_label_registro}"
            with st.expander(_label_exp, expanded=len(st.session_state.perfiles_col) == 0):
                pc_modo = st.selectbox("MODO DE PARTICIPACIÓN EN LAS FARC-EP *",
                    _MODOS_PART_COL, key=f"pc_modo_{tipo}")
                pc_anio = st.number_input("AÑO DE INGRESO, TRASLADO O CAPTURA *",
                    min_value=1950, max_value=2026, step=1, key=f"pc_anio_{tipo}")
                pc_bloque = st.selectbox("SELECCIONE EL BLOQUE DE OPERACIÓN *",
                    ["Seleccione..."] + list(_ESTRUCTURAS.keys()), key=f"pc_bloque_{tipo}")
                pc_estructura = "Seleccione..."
                if pc_bloque != "Seleccione...":
                    _ops_pc = _ESTRUCTURAS[pc_bloque]
                    pc_estructura = st.selectbox("ESTRUCTURA *", _ops_pc, key=f"pc_estructura_{tipo}")
                pc_lugar = st.selectbox("LUGAR DE ACREDITACIÓN *", _LUGAR_ACREDITACION,
                    key=f"pc_lugar_{tipo}")

                st.markdown("**ROL/ACTIVIDADES P_ANTIGUO \\***")
                cols_rol_pc = st.columns(2)
                pc_rol = [
                    opcion for j, opcion in enumerate(_ROLES[1:])
                    if cols_rol_pc[j % 2].checkbox(opcion, key=f"pc_rol_{j}_{tipo}")
                ]
                pc_otro_rol = ""
                if "Otro" in pc_rol:
                    pc_otro_rol = st.text_input("¿QUÉ OTRO ROL?", key=f"pc_otro_rol_{tipo}")

                pc_mostrar_libertad = (pc_modo == "Privado de la libertad")
                pc_meses     = ""
                pc_inst      = "Seleccione..."
                pc_pabellon  = ""
                if pc_mostrar_libertad:
                    pc_meses = st.number_input("NO. MESES PRIVADO DE LA LIBERTAD",
                        min_value=0, max_value=600, step=1, key=f"pc_meses_{tipo}")
                    pc_inst = st.selectbox("TIPO DE INSTITUCIÓN PENITENCIARIA",
                        _INSTITUCIONES, key=f"pc_inst_{tipo}")
                    if pc_inst == "CO -COMPLEJO CARCELARÍO":
                        pc_pabellon = st.selectbox("PABELLÓN DE ALTA SEGURIDAD",
                            ["Seleccione...", "Sí", "No"], key=f"pc_pabellon_{tipo}")

                st.markdown("")
                if st.button(f"➕ Agregar {_label_registro}", use_container_width=True,
                             key=f"btn_add_pcol_{tipo}", type="secondary"):
                    err_pc = []
                    if pc_modo      == "Seleccione...": err_pc.append("El modo de participación es obligatorio")
                    if pc_bloque    == "Seleccione...": err_pc.append("El bloque de operación es obligatorio")
                    if pc_estructura== "Seleccione...": err_pc.append("La estructura es obligatoria")
                    if pc_lugar     == "Seleccione...": err_pc.append("El lugar de acreditación es obligatorio")
                    if len(pc_rol)  == 0:               err_pc.append("El rol es obligatorio")
                    if "Otro" in pc_rol and not pc_otro_rol.strip(): err_pc.append("Especifica el otro rol")
                    if err_pc:
                        for e in err_pc: st.error(f"• {e}")
                    else:
                        st.session_state.perfiles_col.append({
                            "modo_participacion":  pc_modo,
                            "anio_ingreso":        pc_anio,
                            "bloque":              pc_bloque,
                            "estructura":          pc_estructura,
                            "lugar_acreditacion":  pc_lugar,
                            "rol":                 " | ".join(pc_rol),
                            "otro_rol":            pc_otro_rol.strip() if pc_otro_rol else "",
                            "meses_privado":       str(pc_meses) if pc_mostrar_libertad else "",
                            "tipo_institucion":    pc_inst if pc_inst != "Seleccione..." else "",
                            "pabellon_alta_seguridad": pc_pabellon if pc_pabellon != "Seleccione..." else "",
                        })
                        st.success(f"✅ {_label_registro} agregado"); st.rerun()

    _btn_borrador(tipo, "tras_perfil_antiguo")

    # ══════════════════════════════════════════════════════════════════════════
    # 7. PERFIL ACTUAL
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("🎯 PERFIL ACTUAL")
    st.caption("Opcional. Agrega uno o varios perfiles del estado actual de reincorporación.")

    if "perfiles_actuales" not in st.session_state:
        st.session_state.perfiles_actuales = []

    # Banderas de condicionales basadas en tipo de población
    _es_reincorporado           = tipo_poblacion == "REINCORPORADO/A"
    _es_familiar_reincorporado  = tipo_poblacion == "FAMILIAR DE REINCORPORADO/A"
    _es_comunes            = tipo_poblacion in (
        "INTEGRANTE DEL PARTIDO COMUNES",
        "FAMILIAR DE INTEGRANTE DEL PARTIDO COMUNES",
    )
    _es_familiar_comunes   = tipo_poblacion == "FAMILIAR DE INTEGRANTE DEL PARTIDO COMUNES"
    _mostrar_cargo_comunes = tipo_poblacion in (
        "INTEGRANTE DEL PARTIDO COMUNES",
        "FAMILIAR DE INTEGRANTE DEL PARTIDO COMUNES",
    )

    _edit_pa_key = f"editando_pa_{tipo}"

    # ── Listado de perfiles actuales ya agregados ─────────────────────────────
    for i, pa in enumerate(st.session_state.perfiles_actuales):
        with st.container(border=True):
            col_tit_pa, col_edit_pa, col_del_pa = st.columns([4, 1, 1])
            with col_tit_pa:
                st.markdown(f"**Perfil Actual #{i+1}**")
            with col_edit_pa:
                if st.button("✏️", key=f"edit_pa_{tipo}_{i}", help="Editar"):
                    st.session_state[_edit_pa_key] = i
                    # Reset listas temporales para que se carguen desde el perfil editado
                    _sfx_edit = f"{tipo}_{i}"
                    st.session_state[f"instancias_comunes_temp_{_sfx_edit}"] = list(pa.get("instancias_comunes", []))
                    st.session_state[f"otras_orgs_temp_{_sfx_edit}"] = list(pa.get("otras_orgs", []))
                    st.rerun()
            with col_del_pa:
                if st.button("🗑️", key=f"del_pa_{tipo}_{i}", help="Eliminar"):
                    st.session_state.perfiles_actuales.pop(i)
                    st.session_state[_edit_pa_key] = None
                    st.rerun()

            if st.session_state.get(_edit_pa_key) == i:
                # ── Modo edición ──────────────────────────────────────────────
                st.markdown(f"**✏️ Editando Perfil Actual #{i+1}**")
                _render_pa_form(pa, tipo, i, _es_reincorporado, _es_familiar_reincorporado, _es_familiar_comunes, _mostrar_cargo_comunes, es_colectivo=not es_individual)
                col_sv, col_cx = st.columns(2)
                with col_sv:
                    if st.button("💾 Guardar cambios", key=f"pa_save_{tipo}_{i}",
                                 type="primary", use_container_width=True):
                        nuevo = _recoger_pa(tipo, i, _es_reincorporado, _es_familiar_reincorporado, _es_familiar_comunes, _mostrar_cargo_comunes, es_colectivo=not es_individual)
                        if nuevo is not None:
                            st.session_state.perfiles_actuales[i] = nuevo
                            st.session_state[_edit_pa_key] = None
                            st.rerun()
                with col_cx:
                    if st.button("✖ Cancelar", key=f"pa_cancel_{tipo}_{i}",
                                 type="secondary", use_container_width=True):
                        st.session_state[_edit_pa_key] = None
                        st.rerun()
            else:
                # ── Modo lectura ──────────────────────────────────────────────
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"📚 **Nivel Educativo:** {pa.get('nivel_educativo','')}")
                    st.write(f"💰 **Fuente Principal de Ingresos:** {pa.get('fuente_ingresos','')}")
                    if pa.get('estado_proyecto_arn'):
                        st.write(f"🏗️ **Estado Proyecto ARN:** {pa.get('estado_proyecto_arn','')}")
                    if pa.get('actividad_economica'):
                        st.write(f"📦 **Actividad Económica:** {pa.get('actividad_economica','')}")
                    # Instancias Comunes (multiregistro)
                    _ic_lista = pa.get('instancias_comunes', [])
                    if _ic_lista:
                        st.markdown("🏛️ **Instancias Partido Comunes:**")
                        for _ic_item in _ic_lista:
                            st.write(
                                f"  • {_ic_item.get('instancias_partido','—')} | "
                                f"Rol: {_ic_item.get('roles_partido','—')} | "
                                f"Consejería: {_ic_item.get('consejeria_nacional','—')}"
                            )
                with c2:
                    st.write(f"⚖️ **Comparecencia JEP:** {pa.get('comparecencia_jep','')}")
                    if pa.get('macrocasos_jep'):
                        st.write(f"📋 **Macrocasos JEP:** {pa.get('macrocasos_jep','')}")
                    st.write(f"🕊️ **Participación TOAR:** {pa.get('participacion_toar','')}")
                    st.write(f"🔍 **Búsqueda Personas Desaparecidas:** {pa.get('busqueda_desaparecidos','')}")
                    if pa.get('cargo_eleccion'):
                        st.write(f"🗳️ **Cargo Elección Popular:** {pa.get('cargo_eleccion','')}")
                    # Otras Organizaciones (multiregistro)
                    _oo_lista = pa.get('otras_orgs', [])
                    if _oo_lista:
                        st.markdown("🤝 **Otras Organizaciones:**")
                        for _oo_item in _oo_lista:
                            st.write(
                                f"  • {_oo_item.get('nombre_org','—')} | "
                                f"Tipo: {_oo_item.get('tipo_org','—')} | "
                                f"Rol: {_oo_item.get('rol_org','—')}"
                            )

    # ── Perfil Actual — multiregistro ────────────────────────────────────────
    _expanded_pa = len(st.session_state.perfiles_actuales) == 0
    with st.expander("➕ Agregar Perfil Actual", expanded=_expanded_pa):
        _render_pa_form(None, tipo, "new", _es_reincorporado, _es_familiar_reincorporado, _es_familiar_comunes, _mostrar_cargo_comunes, es_colectivo=not es_individual)
        st.markdown("")
        if st.button("✅ Guardar Perfil Actual", use_container_width=True,
                     key=f"btn_add_pa_{tipo}", type="primary"):
            nuevo = _recoger_pa(tipo, "new", _es_reincorporado, _es_familiar_reincorporado, _es_familiar_comunes, _mostrar_cargo_comunes, es_colectivo=not es_individual)
            if nuevo is not None:
                st.session_state.perfiles_actuales.append(nuevo)
                # Limpiar listas temporales del formulario "new"
                _sfx_new = f"{tipo}_new"
                st.session_state.pop(f"instancias_comunes_temp_{_sfx_new}", None)
                st.session_state.pop(f"otras_orgs_temp_{_sfx_new}", None)
                st.session_state.pop(f"show_ic_form_{_sfx_new}", None)
                st.session_state.pop(f"show_oo_form_{_sfx_new}", None)
                st.success("✅ Perfil Actual guardado")
                st.rerun()


    # 8. DESPLAZAMIENTOS
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("🚗 DESPLAZAMIENTOS")
    st.caption("Opcional. Agrega uno o varios desplazamientos asociados a este caso.")

    if "desplazamientos" not in st.session_state:
        st.session_state.desplazamientos = []

    def _render_desp_form(desp, tipo, idx):
        """Renderiza el formulario de un desplazamiento."""
        sfx = f"{tipo}_{idx}"
        def _dv(campo, defecto="Seleccione..."):
            return desp.get(campo, defecto) if desp else defecto

        # Motivo (siempre visible)
        motivo = st.selectbox(
            "MOTIVO DESPLAZAMIENTO *", _DESP_MOTIVOS,
            index=_DESP_MOTIVOS.index(_dv("motivo")) if _dv("motivo") in _DESP_MOTIVOS else 0,
            key=f"desp_motivo_{sfx}"
        )

        _es_no_reporta = motivo == "NO REPORTA"

        if not _es_no_reporta and motivo != "Seleccione...":
            # ── Medios de transporte (checkboxes multi) ───────────────────────
            _medios_prev = [x.strip() for x in _dv("medios_transporte", "").split("|") if x.strip()] if desp else []
            st.markdown("**MEDIO DE TRANSPORTE UTILIZADO EN LOS DESPLAZAMIENTOS**")
            cols_med = st.columns(3)
            for j, medio in enumerate(_DESP_MEDIOS_TRANSPORTE):
                cols_med[j % 3].checkbox(medio, value=(medio in _medios_prev), key=f"desp_medio_{j}_{sfx}")

            # ── Origen ────────────────────────────────────────────────────────
            col_do, col_mo = st.columns(2)
            with col_do:
                dep_origen = st.selectbox(
                    "DEPARTAMENTO ORIGEN", _DESP_DEPARTAMENTOS,
                    index=_DESP_DEPARTAMENTOS.index(_dv("dep_origen")) if _dv("dep_origen") in _DESP_DEPARTAMENTOS else 0,
                    key=f"desp_dep_origen_{sfx}"
                )
            with col_mo:
                _muns_origen = _MUNICIPIOS.get(dep_origen, ["Seleccione..."])
                if "Seleccione..." not in _muns_origen:
                    _muns_origen = ["Seleccione..."] + _muns_origen
                mun_origen_cur = _dv("mun_origen")
                st.selectbox(
                    "MUNICIPIO ORIGEN",
                    _muns_origen,
                    index=_muns_origen.index(mun_origen_cur) if mun_origen_cur in _muns_origen else 0,
                    key=f"desp_mun_origen_{sfx}"
                )

            # ── Destino ───────────────────────────────────────────────────────
            col_dd, col_md = st.columns(2)
            with col_dd:
                dep_destino = st.selectbox(
                    "DEPARTAMENTO DESTINO", _DESP_DEPARTAMENTOS,
                    index=_DESP_DEPARTAMENTOS.index(_dv("dep_destino")) if _dv("dep_destino") in _DESP_DEPARTAMENTOS else 0,
                    key=f"desp_dep_destino_{sfx}"
                )
            with col_md:
                _muns_destino = _MUNICIPIOS.get(dep_destino, ["Seleccione..."])
                if "Seleccione..." not in _muns_destino:
                    _muns_destino = ["Seleccione..."] + _muns_destino
                mun_destino_cur = _dv("mun_destino")
                st.selectbox(
                    "MUNICIPIO DESTINO",
                    _muns_destino,
                    index=_muns_destino.index(mun_destino_cur) if mun_destino_cur in _muns_destino else 0,
                    key=f"desp_mun_destino_{sfx}"
                )

            # ── Frecuencia y Tipo de vía ──────────────────────────────────────
            col_fr, col_via = st.columns(2)
            with col_fr:
                st.selectbox(
                    "FRECUENCIA DE DESPLAZAMIENTOS", _DESP_FRECUENCIAS,
                    index=_DESP_FRECUENCIAS.index(_dv("frecuencia")) if _dv("frecuencia") in _DESP_FRECUENCIAS else 0,
                    key=f"desp_frecuencia_{sfx}"
                )
            with col_via:
                st.selectbox(
                    "TIPO DE VÍA CON MAYOR DURACIÓN EN EL DESPLAZAMIENTO", _DESP_TIPOS_VIA,
                    index=_DESP_TIPOS_VIA.index(_dv("tipo_via")) if _dv("tipo_via") in _DESP_TIPOS_VIA else 0,
                    key=f"desp_tipo_via_{sfx}"
                )

    def _recoger_desp(tipo, idx):
        """Lee el estado de los widgets de Desplazamiento y retorna un dict."""
        sfx = f"{tipo}_{idx}"
        motivo = st.session_state.get(f"desp_motivo_{sfx}", "Seleccione...")
        if motivo == "Seleccione...":
            st.error("• El motivo del desplazamiento es obligatorio")
            return None

        _es_no_reporta = motivo == "NO REPORTA"

        medios = ""
        dep_origen = mun_origen = dep_destino = mun_destino = ""
        frecuencia = tipo_via = ""

        if not _es_no_reporta:
            medios = " | ".join([
                medio for j, medio in enumerate(_DESP_MEDIOS_TRANSPORTE)
                if st.session_state.get(f"desp_medio_{j}_{sfx}", False)
            ])
            dep_origen  = st.session_state.get(f"desp_dep_origen_{sfx}", "Seleccione...")
            mun_origen  = st.session_state.get(f"desp_mun_origen_{sfx}", "Seleccione...")
            dep_destino = st.session_state.get(f"desp_dep_destino_{sfx}", "Seleccione...")
            mun_destino = st.session_state.get(f"desp_mun_destino_{sfx}", "Seleccione...")
            frecuencia  = st.session_state.get(f"desp_frecuencia_{sfx}", "Seleccione...")
            tipo_via    = st.session_state.get(f"desp_tipo_via_{sfx}", "Seleccione...")

        return {
            "motivo":           motivo,
            "medios_transporte": medios,
            "dep_origen":       dep_origen  if dep_origen  != "Seleccione..." else "",
            "mun_origen":       mun_origen  if mun_origen  != "Seleccione..." else "",
            "dep_destino":      dep_destino if dep_destino != "Seleccione..." else "",
            "mun_destino":      mun_destino if mun_destino != "Seleccione..." else "",
            "frecuencia":       frecuencia  if frecuencia  != "Seleccione..." else "",
            "tipo_via":         tipo_via    if tipo_via    != "Seleccione..." else "",
        }

    _edit_desp_key = f"editando_desp_{tipo}"

    # ── Listado de desplazamientos ya agregados ───────────────────────────────
    for i, desp in enumerate(st.session_state.desplazamientos):
        with st.container(border=True):
            col_tit_d, col_edit_d, col_del_d = st.columns([4, 1, 1])
            with col_tit_d:
                st.markdown(f"**Desplazamiento #{i+1} — {desp.get('motivo','')}**")
            with col_edit_d:
                if st.button("✏️", key=f"edit_desp_{tipo}_{i}", help="Editar"):
                    st.session_state[_edit_desp_key] = i
                    st.rerun()
            with col_del_d:
                if st.button("🗑️", key=f"del_desp_{tipo}_{i}", help="Eliminar"):
                    st.session_state.desplazamientos.pop(i)
                    st.session_state[_edit_desp_key] = None
                    st.rerun()

            if st.session_state.get(_edit_desp_key) == i:
                st.markdown(f"**✏️ Editando Desplazamiento #{i+1}**")
                _render_desp_form(desp, tipo, i)
                col_sv, col_cx = st.columns(2)
                with col_sv:
                    if st.button("💾 Guardar cambios", key=f"desp_save_{tipo}_{i}",
                                 type="primary", use_container_width=True):
                        nuevo = _recoger_desp(tipo, i)
                        if nuevo is not None:
                            st.session_state.desplazamientos[i] = nuevo
                            st.session_state[_edit_desp_key] = None
                            st.rerun()
                with col_cx:
                    if st.button("✖ Cancelar", key=f"desp_cancel_{tipo}_{i}",
                                 type="secondary", use_container_width=True):
                        st.session_state[_edit_desp_key] = None
                        st.rerun()
            else:
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"🎯 **Motivo:** {desp.get('motivo','')}")
                    if desp.get('dep_origen'):
                        st.write(f"📍 **Origen:** {desp.get('mun_origen','')} — {desp.get('dep_origen','')}")
                    if desp.get('dep_destino'):
                        st.write(f"🏁 **Destino:** {desp.get('mun_destino','')} — {desp.get('dep_destino','')}")
                with c2:
                    if desp.get('medios_transporte'):
                        st.write(f"🚌 **Medios:** {desp.get('medios_transporte','')}")
                    if desp.get('frecuencia'):
                        st.write(f"🔁 **Frecuencia:** {desp.get('frecuencia','')}")
                    if desp.get('tipo_via'):
                        st.write(f"🛣️ **Tipo de Vía:** {desp.get('tipo_via','')}")

    # ── Formulario para agregar nuevo desplazamiento ──────────────────────────
    with st.expander("➕ Agregar Desplazamiento", expanded=len(st.session_state.desplazamientos) == 0):
        _render_desp_form(None, tipo, "new")
        st.markdown("")
        if st.button("➕ Agregar este Desplazamiento", use_container_width=True,
                     key=f"btn_add_desp_{tipo}", type="secondary"):
            nuevo = _recoger_desp(tipo, "new")
            if nuevo is not None:
                st.session_state.desplazamientos.append(nuevo)
                st.success("✅ Desplazamiento agregado")
                st.rerun()

    _btn_borrador(tipo, "tras_perfil_actual")

    # ── Hechos de Riesgo ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("⚠️ Hechos de Riesgo")
    st.caption("Opcional. Agrega uno o varios hechos de riesgo asociados a este caso.")

    _edit_hecho_key = f"editando_hecho_{tipo}"

    for i, hecho in enumerate(st.session_state.hechos):
        with st.container(border=True):
            if st.session_state.get(_edit_hecho_key) == i:
                # ── Modo edición ──────────────────────────────────────────────
                st.markdown(f"**✏️ Editando Hecho #{i+1}**")
                try:
                    _eh_fecha_parts = datetime.strptime(hecho["fecha"], "%Y-%m-%d")
                    _eh_anio_val = _eh_fecha_parts.year
                    _eh_mes_val  = _eh_fecha_parts.month
                    _eh_dia_val  = _eh_fecha_parts.day
                except Exception:
                    _eh_anio_val = None
                    _eh_mes_val  = None
                    _eh_dia_val  = None
                _eh_anio_key = f"eh_anio_{tipo}_{i}"
                _eh_mes_key  = f"eh_mes_{tipo}_{i}"
                _eh_dia_key  = f"eh_dia_{tipo}_{i}"
                ec_anio, ec_mes, ec_dia = st.columns(3)
                with ec_anio:
                    eh_anio = st.number_input(
                        "AÑO DEL HECHO", min_value=1900, max_value=2099,
                        value=_eh_anio_val, step=1, key=_eh_anio_key
                    )
                with ec_mes:
                    eh_mes = st.number_input(
                        "MES DEL HECHO", min_value=1, max_value=12,
                        value=_eh_mes_val, step=1, key=_eh_mes_key
                    )
                _eh_max_dia = 31
                if eh_anio is not None and eh_mes is not None:
                    try:
                        _eh_max_dia = calendar.monthrange(int(eh_anio), int(eh_mes))[1]
                        _eh_dia_cur = st.session_state.get(_eh_dia_key)
                        if _eh_dia_cur is not None and _eh_dia_cur > _eh_max_dia:
                            st.session_state[_eh_dia_key] = _eh_max_dia
                    except Exception:
                        _eh_max_dia = 31
                with ec_dia:
                    eh_dia = st.number_input(
                        "DÍA DEL HECHO", min_value=1, max_value=_eh_max_dia,
                        value=_eh_dia_val, step=1, key=_eh_dia_key
                    )
                _eh_dep_opts = ["Seleccione..."] + list(_MUNICIPIOS.keys())
                _eh_dep_val  = hecho.get("departamento", "Seleccione...")
                _eh_dep_idx  = _eh_dep_opts.index(_eh_dep_val) if _eh_dep_val in _eh_dep_opts else 0
                ec_dep, ec_mun = st.columns(2)
                with ec_dep:
                    eh_departamento = st.selectbox(
                        "DEPARTAMENTO DEL HECHO", _eh_dep_opts,
                        index=_eh_dep_idx, key=f"eh_departamento_{tipo}_{i}"
                    )
                _eh_mun_opts = _MUNICIPIOS.get(eh_departamento, ["Seleccione..."])
                _eh_mun_val  = hecho.get("municipio", "Seleccione...")
                _eh_mun_idx  = _eh_mun_opts.index(_eh_mun_val) if _eh_mun_val in _eh_mun_opts else 0
                with ec_mun:
                    eh_municipio = st.selectbox(
                        "MUNICIPIO DEL HECHO", _eh_mun_opts,
                        index=_eh_mun_idx, key=f"eh_municipio_{tipo}_{i}"
                    )
                _eh_tipo_actor_opts = ["Seleccione..."] + _TIPOS_ACTOR_GENERADOR
                _eh_tipo_actor_val  = hecho.get("tipo_actor", "Seleccione...")
                _eh_tipo_actor_idx  = _eh_tipo_actor_opts.index(_eh_tipo_actor_val) if _eh_tipo_actor_val in _eh_tipo_actor_opts else 0
                ec_tipo_actor, ec_actor_gen = st.columns(2)
                with ec_tipo_actor:
                    eh_tipo_actor = st.selectbox(
                        "TIPO ACTOR GENERADOR HECHO DE RIESGO",
                        _eh_tipo_actor_opts,
                        index=_eh_tipo_actor_idx,
                        key=f"eh_tipo_actor_{tipo}_{i}"
                    )
                with ec_actor_gen:
                    eh_actor_generador = st.text_input(
                        "ACTOR GENERADOR HECHO RIESGO",
                        value=hecho.get("actor_generador", ""),
                        key=f"eh_actor_gen_{tipo}_{i}"
                    )
                ec_medio, ec_victima, ec_amenaza = st.columns(3)
                with ec_medio:
                    _eh_medio_val = hecho.get("medio", "Seleccione...")
                    eh_medio = st.selectbox(
                        "MEDIO HECHO DE RIESGO",
                        _MEDIOS_HECHO,
                        index=_MEDIOS_HECHO.index(_eh_medio_val) if _eh_medio_val in _MEDIOS_HECHO else 0,
                        key=f"eh_medio_{tipo}_{i}"
                    )
                with ec_victima:
                    _eh_victima_val = hecho.get("victima_situacion", "Seleccione...")
                    eh_victima_situacion = st.selectbox(
                        "VÍCTIMA DE LA SITUACIÓN HECHO DE RIESGO",
                        _VICTIMAS_SITUACION_HECHO,
                        index=_VICTIMAS_SITUACION_HECHO.index(_eh_victima_val) if _eh_victima_val in _VICTIMAS_SITUACION_HECHO else 0,
                        key=f"eh_victima_{tipo}_{i}"
                    )
                with ec_amenaza:
                    pass
                if not es_individual:
                    _eh_am_dir_opts = ["Seleccione...", "Sí", "No"]
                    _eh_am_dir_val  = hecho.get("amenaza_directa_colectivo", "Seleccione...")
                    _eh_am_dir_idx  = _eh_am_dir_opts.index(_eh_am_dir_val) if _eh_am_dir_val in _eh_am_dir_opts else 0
                    col_am_dir, _ = st.columns([1, 2])
                    with col_am_dir:
                        eh_amenaza_directa_col = st.selectbox(
                            "AMENAZA DIRECTA EN CONTRA DEL COLECTIVO/ GRUPO FAMILIAR",
                            _eh_am_dir_opts,
                            index=_eh_am_dir_idx,
                            key=f"eh_amenaza_directa_col_{tipo}_{i}"
                        )
                else:
                    eh_amenaza_directa_col = ""
                _ec_amenaza_cols = st.columns(3)
                with _ec_amenaza_cols[0]:
                    _eh_amenaza_val = hecho.get("tipo_amenaza", "Seleccione...")
                    eh_tipo_amenaza = st.selectbox(
                        "TIPO DE AMENAZA",
                        _TIPOS_AMENAZA,
                        index=_TIPOS_AMENAZA.index(_eh_amenaza_val) if _eh_amenaza_val in _TIPOS_AMENAZA else 0,
                        key=f"eh_tipo_amenaza_{tipo}_{i}"
                    )
                ec_tipo, ec_motivacion = st.columns(2)
                with ec_tipo:
                    eh_tipo = st.selectbox("Tipo de Hecho *", _TIPOS_HECHO,
                        index=_TIPOS_HECHO.index(hecho["tipo"]) if hecho["tipo"] in _TIPOS_HECHO else 0,
                        key=f"eh_tipo_{tipo}_{i}")
                with ec_motivacion:
                    eh_motivacion = st.text_input(
                        "MOTIVACIÓN AMENAZA HECHO DE RIESGO",
                        value=hecho.get("motivacion_amenaza", ""),
                        placeholder="Máximo en 10 palabras",
                        key=f"eh_motivacion_{tipo}_{i}"
                    )
                ec_nexo, ec_desc = st.columns(2)
                with ec_nexo:
                    _eh_nexo_opts = ["Seleccione...", "SI", "NO"]
                    _eh_nexo_val  = hecho.get("nexo_causal", "Seleccione...")
                    _eh_nexo_idx  = _eh_nexo_opts.index(_eh_nexo_val) if _eh_nexo_val in _eh_nexo_opts else 0
                    eh_nexo_causal = st.selectbox(
                        "NEXO CAUSAL",
                        _eh_nexo_opts,
                        index=_eh_nexo_idx,
                        key=f"eh_nexo_{tipo}_{i}"
                    )
                with ec_desc:
                    eh_desc = st.text_area("Descripción", value=hecho["descripcion"], height=122, key=f"eh_desc_{tipo}_{i}")
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("💾 Guardar cambios", key=f"eh_save_{tipo}_{i}", type="primary", use_container_width=True):
                        err_e = []
                        if eh_tipo == "Seleccione...": err_e.append("Selecciona el tipo de hecho")
                        if err_e:
                            for e in err_e: st.error(f"• {e}")
                        else:
                            _fecha_eh = ""
                            if eh_anio is not None and eh_mes is not None and eh_dia is not None:
                                try:
                                    _fecha_eh = f"{int(eh_anio):04d}-{int(eh_mes):02d}-{int(eh_dia):02d}"
                                except Exception:
                                    _fecha_eh = ""
                            st.session_state.hechos[i] = {
                                "tipo": eh_tipo, "fecha": _fecha_eh,
                                "departamento": eh_departamento if eh_departamento != "Seleccione..." else "",
                                "municipio": eh_municipio if eh_municipio != "Seleccione..." else "",
                                "tipo_actor": eh_tipo_actor if eh_tipo_actor != "Seleccione..." else "",
                                "actor_generador": eh_actor_generador.strip(),
                                "medio": eh_medio if eh_medio != "Seleccione..." else "",
                                "amenaza_directa_colectivo": eh_amenaza_directa_col if eh_amenaza_directa_col != "Seleccione..." else "",
                                "victima_situacion": eh_victima_situacion if eh_victima_situacion != "Seleccione..." else "",
                                "tipo_amenaza": eh_tipo_amenaza if eh_tipo_amenaza != "Seleccione..." else "",
                                "motivacion_amenaza": eh_motivacion.strip(),
                                "nexo_causal": eh_nexo_causal if eh_nexo_causal != "Seleccione..." else "",
                                "descripcion": eh_desc.strip()
                            }
                            st.session_state[_edit_hecho_key] = None
                            st.rerun()
                with col_cancel:
                    if st.button("✖ Cancelar", key=f"eh_cancel_{tipo}_{i}", type="secondary", use_container_width=True):
                        st.session_state[_edit_hecho_key] = None
                        st.rerun()
            else:
                # ── Modo lectura ──────────────────────────────────────────────
                col_tit, col_edit, col_del = st.columns([4, 1, 1])
                with col_tit: st.markdown(f"**Hecho #{i+1} — {hecho['tipo']}**")
                with col_edit:
                    if st.button("✏️", key=f"edit_h_{tipo}_{i}", help="Editar este hecho"):
                        st.session_state[_edit_hecho_key] = i
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{tipo}_{i}", help="Eliminar este hecho"):
                        st.session_state.hechos.pop(i)
                        st.session_state[_edit_hecho_key] = None
                        st.rerun()
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"📅 **Fecha:** {hecho['fecha']}")
                    st.write(f"🗺️ **Departamento:** {hecho.get('departamento', '')}")
                    st.write(f"🏙️ **Municipio:** {hecho.get('municipio', '')}")
                    st.write(f"💬 **Motivación Amenaza:** {hecho.get('motivacion_amenaza', '')}")
                    st.write(f"🔗 **Nexo Causal:** {hecho.get('nexo_causal', '')}")
                with c2:
                    st.write(f"⚡ **Tipo Actor:** {hecho.get('tipo_actor', '')}")
                    st.write(f"🔫 **Actor Generador:** {hecho.get('actor_generador', '')}")
                    st.write(f"📡 **Medio:** {hecho.get('medio', '')}")
                    st.write(f"🎯 **Víctima Situación:** {hecho.get('victima_situacion', '')}")
                    st.write(f"⚠️ **Tipo Amenaza:** {hecho.get('tipo_amenaza', '')}")
                st.write(f"📄 **Descripción:** {hecho['descripcion']}")

    with st.expander("➕ Agregar hecho de riesgo", expanded=len(st.session_state.hechos) == 0):
        _hf_anio_key = f"hecho_anio_{tipo}"
        _hf_mes_key  = f"hecho_mes_{tipo}"
        _hf_dia_key  = f"hecho_dia_{tipo}"
        col_hf_anio, col_hf_mes, col_hf_dia = st.columns(3)
        with col_hf_anio:
            hecho_anio = st.number_input(
                "AÑO DEL HECHO", min_value=1900, max_value=2099,
                value=None, step=1, key=_hf_anio_key
            )
        with col_hf_mes:
            hecho_mes = st.number_input(
                "MES DEL HECHO", min_value=1, max_value=12,
                value=None, step=1, key=_hf_mes_key
            )
        _max_dia_hf = 31
        if hecho_anio is not None and hecho_mes is not None:
            try:
                _max_dia_hf = calendar.monthrange(int(hecho_anio), int(hecho_mes))[1]
                _dia_cur_hf = st.session_state.get(_hf_dia_key)
                if _dia_cur_hf is not None and _dia_cur_hf > _max_dia_hf:
                    st.session_state[_hf_dia_key] = _max_dia_hf
            except Exception:
                _max_dia_hf = 31
        with col_hf_dia:
            hecho_dia = st.number_input(
                "DÍA DEL HECHO", min_value=1, max_value=_max_dia_hf,
                value=None, step=1, key=_hf_dia_key
            )
        col_hf_dep, col_hf_mun = st.columns(2)
        with col_hf_dep:
            hecho_departamento = st.selectbox(
                "DEPARTAMENTO DEL HECHO",
                ["Seleccione..."] + list(_MUNICIPIOS.keys()),
                key=f"hf_departamento_{tipo}"
            )
        with col_hf_mun:
            hecho_municipio = st.selectbox(
                "MUNICIPIO DEL HECHO",
                _MUNICIPIOS.get(hecho_departamento, ["Seleccione..."]),
                key=f"hf_municipio_{tipo}"
            )
        col_hf_tipo_actor, col_hf_actor_gen = st.columns(2)
        with col_hf_tipo_actor:
            hecho_tipo_actor = st.selectbox(
                "TIPO ACTOR GENERADOR HECHO DE RIESGO",
                ["Seleccione..."] + _TIPOS_ACTOR_GENERADOR,
                key=f"hf_tipo_actor_{tipo}"
            )
        with col_hf_actor_gen:
            hecho_actor_generador = st.text_input(
                "ACTOR GENERADOR HECHO RIESGO",
                key=f"hf_actor_gen_{tipo}"
            )
        col_hf_medio, col_hf_victima, col_hf_amenaza = st.columns(3)
        with col_hf_medio:
            hecho_medio = st.selectbox(
                "MEDIO HECHO DE RIESGO",
                _MEDIOS_HECHO,
                key=f"hf_medio_{tipo}"
            )
        with col_hf_victima:
            hecho_victima_situacion = st.selectbox(
                "VÍCTIMA DE LA SITUACIÓN HECHO DE RIESGO",
                _VICTIMAS_SITUACION_HECHO,
                key=f"hf_victima_{tipo}"
            )
        with col_hf_amenaza:
            pass
        if not es_individual:
            _hf_am_dir_opts = ["Seleccione...", "Sí", "No"]
            col_hf_am_dir, _ = st.columns([1, 2])
            with col_hf_am_dir:
                hecho_amenaza_directa_col = st.selectbox(
                    "AMENAZA DIRECTA EN CONTRA DEL COLECTIVO/ GRUPO FAMILIAR",
                    _hf_am_dir_opts,
                    key=f"hf_amenaza_directa_col_{tipo}"
                )
        else:
            hecho_amenaza_directa_col = ""
        _hf_amenaza_cols = st.columns(3)
        with _hf_amenaza_cols[0]:
            hecho_tipo_amenaza = st.selectbox(
                "TIPO DE AMENAZA",
                _TIPOS_AMENAZA,
                key=f"hf_tipo_amenaza_{tipo}"
            )
        col_tipo, col_motivacion = st.columns(2)
        with col_tipo:
            tipo_hecho = st.selectbox("Tipo de Hecho *", _TIPOS_HECHO,
                key=f"hf_tipo_{tipo}")
        with col_motivacion:
            motivacion_hecho = st.text_input(
                "MOTIVACIÓN AMENAZA HECHO DE RIESGO",
                placeholder="Máximo en 10 palabras",
                key=f"hf_motivacion_{tipo}"
            )
        col_nexo, col_desc = st.columns(2)
        with col_nexo:
            nexo_causal_hecho = st.selectbox(
                "NEXO CAUSAL",
                ["Seleccione...", "SI", "NO"],
                key=f"hf_nexo_{tipo}"
            )
        with col_desc:
            descripcion_hecho = st.text_area("Descripción",
                                             placeholder="Describe brevemente el hecho...", height=122,
                                             key=f"hf_desc_{tipo}")
        st.markdown("")
        if st.button("➕ Agregar este hecho", use_container_width=True, key=f"btn_add_hecho_{tipo}", type="secondary"):
            err_h = []
            if tipo_hecho == "Seleccione...": err_h.append("Selecciona el tipo de hecho")
            if err_h:
                for e in err_h: st.error(f"• {e}")
            else:
                _fecha_hf = ""
                if hecho_anio is not None and hecho_mes is not None and hecho_dia is not None:
                    try:
                        _fecha_hf = f"{int(hecho_anio):04d}-{int(hecho_mes):02d}-{int(hecho_dia):02d}"
                    except Exception:
                        _fecha_hf = ""
                st.session_state.hechos.append({
                    "tipo": tipo_hecho, "fecha": _fecha_hf,
                    "departamento": hecho_departamento if hecho_departamento != "Seleccione..." else "",
                    "municipio": hecho_municipio if hecho_municipio != "Seleccione..." else "",
                    "tipo_actor": hecho_tipo_actor if hecho_tipo_actor != "Seleccione..." else "",
                    "actor_generador": hecho_actor_generador.strip(),
                    "medio": hecho_medio if hecho_medio != "Seleccione..." else "",
                    "amenaza_directa_colectivo": hecho_amenaza_directa_col if hecho_amenaza_directa_col != "Seleccione..." else "",
                    "victima_situacion": hecho_victima_situacion if hecho_victima_situacion != "Seleccione..." else "",
                    "tipo_amenaza": hecho_tipo_amenaza if hecho_tipo_amenaza != "Seleccione..." else "",
                    "motivacion_amenaza": motivacion_hecho.strip(),
                    "nexo_causal": nexo_causal_hecho if nexo_causal_hecho != "Seleccione..." else "",
                    "descripcion": descripcion_hecho.strip()
                })
                st.success("✅ Hecho agregado"); st.rerun()

    _btn_borrador(tipo, "tras_hechos")

    # ── Verificaciones ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("✅ Verificaciones")
    st.caption("Opcional. Agrega una o varias verificaciones asociadas a este caso.")

    _edit_ver_key = f"editando_verificacion_{tipo}"
    _CRITERIOS_VER = [
        ("Pertinencia", "Relación directa con el riesgo identificado."),
        ("Fiabilidad",  "Credibilidad de la fuente de la información."),
        ("Suficiencia", "Cantidad y calidad adecuadas para justificar el nivel de riesgo sugerido."),
        ("Veracidad",   "Verificación de la autenticidad de los datos presentados."),
        ("Necesidad",   "Implica que esta sea indispensable para esclarecer un hecho controvertido "
                        "o esencial para la toma de decisiones."),
    ]

    for i, ver in enumerate(st.session_state.verificaciones):
        with st.container(border=True):
            if st.session_state.get(_edit_ver_key) == i:
                # ── Modo edición ──────────────────────────────────────────────
                st.markdown(f"**✏️ Editando Verificación #{i+1}**")
                # Fila 1: Fuente de verificación
                _ev_fuente_val = ver.get("fuente", "Seleccione...")
                _ev_fuente_idx = _FUENTES_VERIFICACION.index(_ev_fuente_val) if _ev_fuente_val in _FUENTES_VERIFICACION else 0
                ev_fuente = st.selectbox(
                    "FUENTE DE VERIFICACIÓN",
                    _FUENTES_VERIFICACION,
                    index=_ev_fuente_idx,
                    key=f"ev_fuente_{tipo}_{i}"
                )
                # Fila 2: Nombre fuente
                ev_nombre_fuente = st.text_input(
                    "SEÑALAR NOMBRE COMPLETO FUENTE DE VERIFICACIÓN",
                    value=ver.get("nombre_fuente", ""),
                    key=f"ev_nombre_{tipo}_{i}"
                )
                # Fila 3: Verificación Hechos de Riesgo | Motivación Amenaza
                ev_col1, ev_col2 = st.columns(2)
                with ev_col1:
                    _ev_vhr_val = ver.get("v_hechos_riesgo", "Seleccione...")
                    ev_v_hechos = st.selectbox(
                        "VERIFICACIÓN HECHOS DE RIESGO",
                        _VER_OPCIONES,
                        index=_VER_OPCIONES.index(_ev_vhr_val) if _ev_vhr_val in _VER_OPCIONES else 0,
                        key=f"ev_vhr_{tipo}_{i}"
                    )
                with ev_col2:
                    _ev_vma_val = ver.get("v_motivacion_amenaza", "Seleccione...")
                    ev_v_motivacion = st.selectbox(
                        "VERIFICACIÓN MOTIVACIÓN AMENAZA",
                        _VER_OPCIONES,
                        index=_VER_OPCIONES.index(_ev_vma_val) if _ev_vma_val in _VER_OPCIONES else 0,
                        key=f"ev_vma_{tipo}_{i}"
                    )
                # Subcampos condicionales de Verificación Hechos de Riesgo
                if ev_v_hechos == "SI":
                    ev_lugar_col, ev_actor_col = st.columns(2)
                    with ev_lugar_col:
                        _ev_vlhr_val = ver.get("v_lugar_hechos", "Seleccione...")
                        ev_v_lugar = st.selectbox(
                            "V. LUGAR HECHOS DE RIESGO",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vlhr_val) if _ev_vlhr_val in _VER_OPCIONES else 0,
                            key=f"ev_vlhr_{tipo}_{i}"
                        )
                    with ev_actor_col:
                        _ev_vahr_val = ver.get("v_actor_hechos", "Seleccione...")
                        ev_v_actor = st.selectbox(
                            "V. ACTOR HECHOS DE RIESGO",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vahr_val) if _ev_vahr_val in _VER_OPCIONES else 0,
                            key=f"ev_vahr_{tipo}_{i}"
                        )
                else:
                    ev_v_lugar = ""
                    ev_v_actor = ""
                # Fila 4: Verificación Perfil Antiguo | Verificación Perfil Actual
                ev_col3, ev_col4 = st.columns(2)
                with ev_col3:
                    _ev_vpa_val = ver.get("v_perfil_antiguo", "Seleccione...")
                    ev_v_perfil_antiguo = st.selectbox(
                        "VERIFICACIÓN PERFIL ANTIGUO",
                        _VER_OPCIONES,
                        index=_VER_OPCIONES.index(_ev_vpa_val) if _ev_vpa_val in _VER_OPCIONES else 0,
                        key=f"ev_vpa_{tipo}_{i}"
                    )
                with ev_col4:
                    _ev_vpac_val = ver.get("v_perfil_actual", "Seleccione...")
                    ev_v_perfil_actual = st.selectbox(
                        "VERIFICACIÓN PERFIL ACTUAL",
                        _VER_OPCIONES,
                        index=_VER_OPCIONES.index(_ev_vpac_val) if _ev_vpac_val in _VER_OPCIONES else 0,
                        key=f"ev_vpac_{tipo}_{i}"
                    )
                # Subcampos condicionales de Verificación Perfil Antiguo
                if ev_v_perfil_antiguo == "SI":
                    ev_pa_col1, ev_pa_col2, ev_pa_col3 = st.columns(3)
                    with ev_pa_col1:
                        _ev_vmp_val = ver.get("v_modo_participacion", "Seleccione...")
                        ev_v_modo_participacion = st.selectbox(
                            "V. MODO DE PARTICIPACIÓN",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vmp_val) if _ev_vmp_val in _VER_OPCIONES else 0,
                            key=f"ev_vmp_{tipo}_{i}"
                        )
                    with ev_pa_col2:
                        _ev_vrpa_val = ver.get("v_rol_perfil_antiguo", "Seleccione...")
                        ev_v_rol_perfil_antiguo = st.selectbox(
                            "V. ROL - PERFIL ANTIGUO",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vrpa_val) if _ev_vrpa_val in _VER_OPCIONES else 0,
                            key=f"ev_vrpa_{tipo}_{i}"
                        )
                    with ev_pa_col3:
                        _ev_vfc_val = ver.get("v_frente_columna", "Seleccione...")
                        ev_v_frente_columna = st.selectbox(
                            "V. FRENTE/COMPAÑÍA/COLUMNA",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vfc_val) if _ev_vfc_val in _VER_OPCIONES else 0,
                            key=f"ev_vfc_{tipo}_{i}"
                        )
                else:
                    ev_v_modo_participacion = ""
                    ev_v_rol_perfil_antiguo = ""
                    ev_v_frente_columna = ""
                # Subcampos condicionales de Verificación Perfil Actual
                if ev_v_perfil_actual == "SI":
                    ev_pac_col1, ev_pac_col2 = st.columns(2)
                    with ev_pac_col1:
                        _ev_vorg_val = ver.get("v_organizacion", "Seleccione...")
                        ev_v_organizacion = st.selectbox(
                            "V. ORGANIZACIÓN",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vorg_val) if _ev_vorg_val in _VER_OPCIONES else 0,
                            key=f"ev_vorg_{tipo}_{i}"
                        )
                    with ev_pac_col2:
                        _ev_vrol_val = ver.get("v_rol_perfil_actual", "Seleccione...")
                        ev_v_rol_perfil_actual = st.selectbox(
                            "V. ROL",
                            _VER_OPCIONES,
                            index=_VER_OPCIONES.index(_ev_vrol_val) if _ev_vrol_val in _VER_OPCIONES else 0,
                            key=f"ev_vrol_{tipo}_{i}"
                        )
                else:
                    ev_v_organizacion = ""
                    ev_v_rol_perfil_actual = ""
                # Criterios de verificación (edición)
                st.markdown("**¿Esta verificación cumplió con alguno de los siguientes criterios?**")
                _crit_actual = [c.strip() for c in ver.get("criterios", "").split("|") if c.strip()]
                _cols_ev_crit = st.columns(len(_CRITERIOS_VER))
                ev_criterios = [
                    nombre
                    for (nombre, definicion), col in zip(_CRITERIOS_VER, _cols_ev_crit)
                    if col.checkbox(nombre, value=(nombre in _crit_actual),
                                    help=definicion, key=f"ev_crit_{nombre.lower()}_{tipo}_{i}")
                ]
                col_sv, col_cv = st.columns(2)
                with col_sv:
                    if st.button("💾 Guardar cambios", key=f"ev_save_{tipo}_{i}", type="primary", use_container_width=True):
                        st.session_state.verificaciones[i] = {
                            "fuente": ev_fuente if ev_fuente != "Seleccione..." else "",
                            "nombre_fuente": ev_nombre_fuente.strip(),
                            "v_hechos_riesgo": ev_v_hechos if ev_v_hechos != "Seleccione..." else "",
                            "v_lugar_hechos": ev_v_lugar if ev_v_lugar != "Seleccione..." else "",
                            "v_actor_hechos": ev_v_actor if ev_v_actor != "Seleccione..." else "",
                            "v_motivacion_amenaza": ev_v_motivacion if ev_v_motivacion != "Seleccione..." else "",
                            "v_perfil_antiguo": ev_v_perfil_antiguo if ev_v_perfil_antiguo != "Seleccione..." else "",
                            "v_modo_participacion": ev_v_modo_participacion if ev_v_modo_participacion != "Seleccione..." else "",
                            "v_rol_perfil_antiguo": ev_v_rol_perfil_antiguo if ev_v_rol_perfil_antiguo != "Seleccione..." else "",
                            "v_frente_columna": ev_v_frente_columna if ev_v_frente_columna != "Seleccione..." else "",
                            "v_perfil_actual": ev_v_perfil_actual if ev_v_perfil_actual != "Seleccione..." else "",
                            "v_organizacion": ev_v_organizacion if ev_v_organizacion != "Seleccione..." else "",
                            "v_rol_perfil_actual": ev_v_rol_perfil_actual if ev_v_rol_perfil_actual != "Seleccione..." else "",
                            "criterios": " | ".join(ev_criterios),
                        }
                        st.session_state[_edit_ver_key] = None
                        st.rerun()
                with col_cv:
                    if st.button("✖ Cancelar", key=f"ev_cancel_{tipo}_{i}", type="secondary", use_container_width=True):
                        st.session_state[_edit_ver_key] = None
                        st.rerun()
            else:
                # ── Modo lectura ──────────────────────────────────────────────
                col_vt, col_ve, col_vd = st.columns([4, 1, 1])
                with col_vt: st.markdown(f"**Verificación #{i+1} — {ver.get('fuente', '')}**")
                with col_ve:
                    if st.button("✏️", key=f"edit_v_{tipo}_{i}", help="Editar"):
                        st.session_state[_edit_ver_key] = i
                        st.rerun()
                with col_vd:
                    if st.button("🗑️", key=f"del_v_{tipo}_{i}", help="Eliminar"):
                        st.session_state.verificaciones.pop(i)
                        st.session_state[_edit_ver_key] = None
                        st.rerun()
                vc1, vc2 = st.columns(2)
                with vc1:
                    st.write(f"🏢 **Fuente:** {ver.get('fuente', '')}")
                    st.write(f"👤 **Nombre Fuente:** {ver.get('nombre_fuente', '')}")
                    st.write(f"⚠️ **V. Hechos Riesgo:** {ver.get('v_hechos_riesgo', '')}")
                    if ver.get("v_hechos_riesgo") == "SI":
                        st.write(f"📍 **V. Lugar Hechos Riesgo:** {ver.get('v_lugar_hechos', '')}")
                        st.write(f"🎭 **V. Actor Hechos Riesgo:** {ver.get('v_actor_hechos', '')}")
                    st.write(f"💬 **V. Motivación Amenaza:** {ver.get('v_motivacion_amenaza', '')}")
                with vc2:
                    st.write(f"📋 **V. Perfil Antiguo:** {ver.get('v_perfil_antiguo', '')}")
                    if ver.get("v_perfil_antiguo") == "SI":
                        st.write(f"🤝 **V. Modo Participación:** {ver.get('v_modo_participacion', '')}")
                        st.write(f"🏷️ **V. Rol Perfil Antiguo:** {ver.get('v_rol_perfil_antiguo', '')}")
                        st.write(f"🪖 **V. Frente/Compañía/Columna:** {ver.get('v_frente_columna', '')}")
                    st.write(f"🎯 **V. Perfil Actual:** {ver.get('v_perfil_actual', '')}")
                    if ver.get("v_perfil_actual") == "SI":
                        st.write(f"🏢 **V. Organización:** {ver.get('v_organizacion', '')}")
                        st.write(f"🏷️ **V. Rol:** {ver.get('v_rol_perfil_actual', '')}")
                if ver.get("criterios"):
                    st.write(f"✅ **Criterios:** {ver.get('criterios', '')}")

    with st.expander("➕ Agregar verificación", expanded=len(st.session_state.verificaciones) == 0):
        # Fila 1
        nv_fuente = st.selectbox(
            "FUENTE DE VERIFICACIÓN",
            _FUENTES_VERIFICACION,
            key=f"nv_fuente_{tipo}"
        )
        # Fila 2
        nv_nombre_fuente = st.text_input(
            "SEÑALAR NOMBRE COMPLETO FUENTE DE VERIFICACIÓN",
            key=f"nv_nombre_{tipo}"
        )
        # Fila 3
        nv_col1, nv_col2 = st.columns(2)
        with nv_col1:
            nv_v_hechos = st.selectbox(
                "VERIFICACIÓN HECHOS DE RIESGO",
                _VER_OPCIONES,
                key=f"nv_vhr_{tipo}"
            )
        with nv_col2:
            nv_v_motivacion = st.selectbox(
                "VERIFICACIÓN MOTIVACIÓN AMENAZA",
                _VER_OPCIONES,
                key=f"nv_vma_{tipo}"
            )
        # Subcampos condicionales de Verificación Hechos de Riesgo
        if nv_v_hechos == "SI":
            nv_lugar_col, nv_actor_col = st.columns(2)
            with nv_lugar_col:
                nv_v_lugar = st.selectbox(
                    "V. LUGAR HECHOS DE RIESGO",
                    _VER_OPCIONES,
                    key=f"nv_vlhr_{tipo}"
                )
            with nv_actor_col:
                nv_v_actor = st.selectbox(
                    "V. ACTOR HECHOS DE RIESGO",
                    _VER_OPCIONES,
                    key=f"nv_vahr_{tipo}"
                )
        else:
            nv_v_lugar = ""
            nv_v_actor = ""
        # Fila 4
        nv_col3, nv_col4 = st.columns(2)
        with nv_col3:
            nv_v_perfil_antiguo = st.selectbox(
                "VERIFICACIÓN PERFIL ANTIGUO",
                _VER_OPCIONES,
                key=f"nv_vpa_{tipo}"
            )
        with nv_col4:
            nv_v_perfil_actual = st.selectbox(
                "VERIFICACIÓN PERFIL ACTUAL",
                _VER_OPCIONES,
                key=f"nv_vpac_{tipo}"
            )
        # Subcampos condicionales de Verificación Perfil Antiguo
        if nv_v_perfil_antiguo == "SI":
            nv_pa_col1, nv_pa_col2, nv_pa_col3 = st.columns(3)
            with nv_pa_col1:
                nv_v_modo_participacion = st.selectbox(
                    "V. MODO DE PARTICIPACIÓN",
                    _VER_OPCIONES,
                    key=f"nv_vmp_{tipo}"
                )
            with nv_pa_col2:
                nv_v_rol_perfil_antiguo = st.selectbox(
                    "V. ROL - PERFIL ANTIGUO",
                    _VER_OPCIONES,
                    key=f"nv_vrpa_{tipo}"
                )
            with nv_pa_col3:
                nv_v_frente_columna = st.selectbox(
                    "V. FRENTE/COMPAÑÍA/COLUMNA",
                    _VER_OPCIONES,
                    key=f"nv_vfc_{tipo}"
                )
        else:
            nv_v_modo_participacion = ""
            nv_v_rol_perfil_antiguo = ""
            nv_v_frente_columna = ""
        # Subcampos condicionales de Verificación Perfil Actual
        if nv_v_perfil_actual == "SI":
            nv_pac_col1, nv_pac_col2 = st.columns(2)
            with nv_pac_col1:
                nv_v_organizacion = st.selectbox(
                    "V. ORGANIZACIÓN",
                    _VER_OPCIONES,
                    key=f"nv_vorg_{tipo}"
                )
            with nv_pac_col2:
                nv_v_rol_perfil_actual = st.selectbox(
                    "V. ROL",
                    _VER_OPCIONES,
                    key=f"nv_vrol_{tipo}"
                )
        else:
            nv_v_organizacion = ""
            nv_v_rol_perfil_actual = ""
        # Criterios de verificación (nuevo registro)
        st.markdown("**¿Esta verificación cumplió con alguno de los siguientes criterios?**")
        _cols_nv_crit = st.columns(len(_CRITERIOS_VER))
        nv_criterios = [
            nombre
            for (nombre, definicion), col in zip(_CRITERIOS_VER, _cols_nv_crit)
            if col.checkbox(nombre, help=definicion, key=f"nv_crit_{nombre.lower()}_{tipo}")
        ]
        st.markdown("")
        if st.button("➕ Agregar esta verificación", use_container_width=True, key=f"btn_add_ver_{tipo}", type="secondary"):
            st.session_state.verificaciones.append({
                "fuente": nv_fuente if nv_fuente != "Seleccione..." else "",
                "nombre_fuente": nv_nombre_fuente.strip(),
                "v_hechos_riesgo": nv_v_hechos if nv_v_hechos != "Seleccione..." else "",
                "v_lugar_hechos": nv_v_lugar if nv_v_lugar != "Seleccione..." else "",
                "v_actor_hechos": nv_v_actor if nv_v_actor != "Seleccione..." else "",
                "v_motivacion_amenaza": nv_v_motivacion if nv_v_motivacion != "Seleccione..." else "",
                "v_perfil_antiguo": nv_v_perfil_antiguo if nv_v_perfil_antiguo != "Seleccione..." else "",
                "v_modo_participacion": nv_v_modo_participacion if nv_v_modo_participacion != "Seleccione..." else "",
                "v_rol_perfil_antiguo": nv_v_rol_perfil_antiguo if nv_v_rol_perfil_antiguo != "Seleccione..." else "",
                "v_frente_columna": nv_v_frente_columna if nv_v_frente_columna != "Seleccione..." else "",
                "v_perfil_actual": nv_v_perfil_actual if nv_v_perfil_actual != "Seleccione..." else "",
                "v_organizacion": nv_v_organizacion if nv_v_organizacion != "Seleccione..." else "",
                "v_rol_perfil_actual": nv_v_rol_perfil_actual if nv_v_rol_perfil_actual != "Seleccione..." else "",
                "criterios": " | ".join(nv_criterios),
            })
            st.success("✅ Verificación agregada"); st.rerun()

    _btn_borrador(tipo, "tras_verificaciones")

    # ── Impacto Consecuencial ─────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Impacto Consecuencial")

    st.markdown("**IMPACTO EN LA ESFERA ECONÓMICA**")
    imp_eco_col1, imp_eco_col2 = st.columns(2)
    with imp_eco_col1:
        imp_eco_dependencia = st.selectbox(
            "DEPENDENCIA EN PROGRAMAS DE SUBSIDIO DEL ESTADO",
            _IMPACTO_SI_NR,
            key=f"imp_eco_dependencia_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_eco_dependencia_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_eco_dependencia_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_eco_empleos = st.selectbox(
            "ACCESO RESTRINGIDO A EMPLEOS FORMALES",
            _IMPACTO_SI_NR,
            key=f"imp_eco_empleos_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_eco_empleos_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_eco_empleos_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_eco_bienes = st.selectbox(
            "ACCESO A SERVICIOS Y BIENES O ENSERES DE PRIMERA NECESIDAD",
            _IMPACTO_SI_NR,
            key=f"imp_eco_bienes_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_eco_bienes_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_eco_bienes_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
    with imp_eco_col2:
        imp_eco_iniciativas = st.selectbox(
            "PÉRDIDA DE INICIATIVAS PRODUCTIVAS",
            _IMPACTO_SI_NR,
            key=f"imp_eco_iniciativas_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_eco_iniciativas_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_eco_iniciativas_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_eco_ilicita = st.selectbox(
            "INSERCIÓN EN PROCESOS DE ECONOMÍAS ILÍCITAS O EMPLEOS INFORMALES PRECARIZADOS",
            _IMPACTO_SI_NR,
            key=f"imp_eco_ilicita_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_eco_ilicita_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_eco_ilicita_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )

    st.markdown("**IMPACTO EN LA ESFERA SOCIAL**")
    imp_soc_col1, imp_soc_col2 = st.columns(2)
    with imp_soc_col1:
        imp_soc_tejido = st.selectbox(
            "RUPTURA DEL TEJIDO SOCIAL",
            _IMPACTO_SI_NR,
            key=f"imp_soc_tejido_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_tejido_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_tejido_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_soc_traslado = st.selectbox(
            "TRASLADO DE FACTORES DE VIOLENCIA DE UN TERRITORIO A OTRO",
            _IMPACTO_SI_NR,
            key=f"imp_soc_traslado_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_traslado_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_traslado_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_soc_movilidad = st.selectbox(
            "RESTRICCIÓN DE MOVILIDAD",
            _IMPACTO_SI_NR,
            key=f"imp_soc_movilidad_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_movilidad_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_movilidad_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_soc_normalizacion = st.selectbox(
            "NORMALIZACIÓN DE LA VIOLENCIA",
            _IMPACTO_SI_NR,
            key=f"imp_soc_normalizacion_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_normalizacion_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_normalizacion_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
    with imp_soc_col2:
        imp_soc_redes = st.selectbox(
            "PÉRDIDA DE REDES DE APOYO",
            _IMPACTO_SI_NR,
            key=f"imp_soc_redes_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_redes_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_redes_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_soc_confinamiento = st.selectbox(
            "CONFINAMIENTO O AUTO-CONFINAMIENTO",
            _IMPACTO_SI_NR,
            key=f"imp_soc_confinamiento_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_confinamiento_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_confinamiento_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_soc_desarraigo = st.selectbox(
            "DESARRAIGO CULTURAL Y TERRITORIAL",
            _IMPACTO_SI_NR,
            key=f"imp_soc_desarraigo_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_desarraigo_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_desarraigo_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_soc_libertad = st.selectbox(
            "AFECTACIÓN AL GOCE DEL DERECHO A LA LIBERTAD Y SEGURIDAD PERSONAL",
            _IMPACTO_SI_NR,
            key=f"imp_soc_libertad_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_soc_libertad_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_soc_libertad_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )

    st.markdown("**IMPACTO EN LA ESFERA POLÍTICO-INSTITUCIONAL**")
    imp_pol_col1, imp_pol_col2 = st.columns(2)
    with imp_pol_col1:
        imp_pol_participacion = st.selectbox(
            "RESTRICCIÓN EN LA PARTICIPACIÓN POLÍTICA",
            _IMPACTO_SI_NR,
            key=f"imp_pol_participacion_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_pol_participacion_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_pol_participacion_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_pol_oferta = st.selectbox(
            "EXPOSICIÓN POR FALENCIAS EN LA IMPLEMENTACIÓN DE LA OFERTA INSTITUCIONAL",
            _IMPACTO_SI_NR,
            key=f"imp_pol_oferta_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_pol_oferta_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_pol_oferta_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_pol_estigmatizacion = st.selectbox(
            "ESTIGMATIZACIÓN",
            _IMPACTO_SI_NR,
            key=f"imp_pol_estigmatizacion_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_pol_estigmatizacion_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_pol_estigmatizacion_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
    with imp_pol_col2:
        imp_pol_liderazgos = st.selectbox(
            "DESARTICULACIÓN EN LOS LIDERAZGOS",
            _IMPACTO_SI_NR,
            key=f"imp_pol_liderazgos_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_pol_liderazgos_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_pol_liderazgos_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_pol_derechos = st.selectbox(
            "AFECTACIÓN EN EL GOCE DE SUS DERECHOS POLÍTICOS",
            _IMPACTO_SI_NR,
            key=f"imp_pol_derechos_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_pol_derechos_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_pol_derechos_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_pol_confianza = st.selectbox(
            "PÉRDIDA DE CONFIANZA EN LAS INSTITUCIONES",
            _IMPACTO_SI_NR,
            key=f"imp_pol_confianza_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_pol_confianza_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_pol_confianza_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )

    st.markdown("**IMPACTO EN LA ESFERA DE LA SALUD Y EL BIENESTAR**")
    imp_sal_col1, imp_sal_col2 = st.columns(2)
    with imp_sal_col1:
        imp_sal_proyeccion = st.selectbox(
            "AFECTACIÓN A LA PROYECCIÓN PERSONAL O COLECTIVA",
            _IMPACTO_SI_NR,
            key=f"imp_sal_proyeccion_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_proyeccion_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_proyeccion_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_sal_desescolarizacion = st.selectbox(
            "DESESCOLARIZACIÓN",
            _IMPACTO_SI_NR,
            key=f"imp_sal_desescolarizacion_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_desescolarizacion_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_desescolarizacion_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_sal_psicosocial = st.selectbox(
            "AFECTACIÓN PSICOSOCIAL",
            _IMPACTO_SI_NR,
            key=f"imp_sal_psicosocial_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_psicosocial_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_psicosocial_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_sal_dano_vida = st.selectbox(
            "DAÑO IRREPARABLE A LA VIDA E INTEGRIDAD PERSONAL",
            _IMPACTO_SI_NR,
            key=f"imp_sal_dano_vida_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_dano_vida_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_dano_vida_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
    with imp_sal_col2:
        imp_sal_cuidados = st.selectbox(
            "IMPOSIBILIDAD DE ATENDER LOS CUIDADOS DOMÉSTICOS O DE PERSONAS DEPENDIENTES",
            _IMPACTO_SI_NR,
            key=f"imp_sal_cuidados_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_cuidados_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_cuidados_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_sal_abandono = st.selectbox(
            "PROCESOS DE ABANDONO A MENORES Y/O ADULTOS MAYORES",
            _IMPACTO_SI_NR,
            key=f"imp_sal_abandono_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_abandono_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_abandono_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )
        imp_sal_discapacidad = st.selectbox(
            "DISCAPACIDAD",
            _IMPACTO_SI_NR,
            key=f"imp_sal_discapacidad_{tipo}",
            index=_IMPACTO_SI_NR.index(st.session_state.get(f"imp_sal_discapacidad_{tipo}", "Seleccione..."))
                if st.session_state.get(f"imp_sal_discapacidad_{tipo}", "Seleccione...") in _IMPACTO_SI_NR else 0
        )

    # ── Nivel de Riesgo ───────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("⚠️ Nivel de Riesgo")
    nivel_riesgo = st.selectbox(
        "Nivel de Riesgo *",
        ["Seleccione...", "ORDINARIO","EXTRAORDINARIO", "EXTRAORDINARIO DE GÉNERO", "EXTREMO"],
        key=f"caso_nivel_riesgo_{tipo}"
    )

    # ── Observaciones ─────────────────────────────────────────────────────────
    st.markdown("---")
    observaciones = st.text_area("Observaciones (Opcional)", height=80, key=f"caso_observaciones_{tipo}")

    # ── Autoguardado con debounce (30s) + change detection ───────────────────
    if st.session_state.get(_borrador_key):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        import hashlib, json
        _tz = ZoneInfo("America/Bogota")
        _ahora = datetime.now(tz=_tz)
        _ultima_ts = st.session_state.get(f"_ultimo_autoguardado_ts_{tipo}")
        if _ultima_ts is None or (_ahora - _ultima_ts).total_seconds() >= 30:
            _datos_borrador = _construir_datos_borrador(tipo)
            _ot_actual = str(_datos_borrador.get(f"caso_ot_anio_{tipo}", "")).strip()
            if not _ot_actual:
                # Formulario reseteado (año OT vacío) → no sobreescribir borrador existente
                pass
            else:
                _hash_actual = hashlib.sha256(
                    json.dumps(_datos_borrador, sort_keys=True, default=str).encode()
                ).hexdigest()
                _hash_anterior = st.session_state.get(f"_hash_borrador_{tipo}")
                if _hash_actual != _hash_anterior:
                    _ok = guardar_borrador(st.session_state.username, tipo, _datos_borrador)
                    if _ok:
                        st.session_state[f"_hash_borrador_{tipo}"] = _hash_actual
                        st.session_state[f"_ultimo_autoguardado_{tipo}"] = f"💾 {_ahora.strftime('%H:%M:%S')}"
                        st.session_state[f"_ultimo_autoguardado_ts_{tipo}"] = _ahora
                    # Si falla, NO actualizar timestamp → reintenta en el siguiente render
                else:
                    # Sin cambios, actualizar timestamp para no re-verificar innecesariamente
                    st.session_state[f"_ultimo_autoguardado_ts_{tipo}"] = _ahora
    if st.session_state.get(f"_ultimo_autoguardado_{tipo}"):
        st.caption(f"Autoguardado: {st.session_state[f'_ultimo_autoguardado_{tipo}']}")

    # ── Guardar borrador ──────────────────────────────────────────────────────
    col_borrador, col_registrar = st.columns([1, 2])
    with col_borrador:
        if st.button("💾 Guardar borrador", use_container_width=True, type="secondary", key=f"btn_guardar_borrador_{tipo}"):
            if guardar_borrador(st.session_state.username, tipo, _construir_datos_borrador(tipo)):
                st.session_state[_borrador_key] = True
                st.success("✅ Borrador guardado. Puedes retomarlo más tarde.")
            else:
                st.error("❌ No se pudo guardar el borrador.")

    with col_registrar:
        registrar = st.button(f"✅ REGISTRAR CASO {label_badge}", use_container_width=True, type="primary", key=f"btn_registrar_{tipo}")

    if registrar:
        errores = []
        if tipo_estudio == "Seleccione...":             errores.append("Debe seleccionar el tipo de estudio")
        if not es_emergencia and ot_anio is None:       errores.append("El año de la OT es obligatorio")
        if not es_emergencia and ot_numero is None:     errores.append("El número de la OT es obligatorio")
        if es_emergencia and ot_anio is None and ot_numero is None:
            pass  # ambos opcionales en emergencia
        if fecha_expedicion_ot is None:                 errores.append("La fecha de expedición OT es obligatoria")
        if tipo_evaluacion == "Seleccione...":          errores.append("Debe seleccionar el tipo de evaluación")
        if not es_individual and tipo_colectivo == "Seleccione...": errores.append("Debe seleccionar el tipo de colectivo")
        if not es_individual and tipo_colectivo == "Estructura de partido" and tipo_estructura_partido == "Seleccione...": errores.append("Debe seleccionar el tipo de estructura")
        if not es_individual and tipo_estructura_partido in ("Comuna", "Local", "Municipal") and estructura_adscrita == "Seleccione...": errores.append("Debe seleccionar la estructura a la que está adscrita")
        if es_individual and tipo_poblacion == "Seleccione...":  errores.append("Debe seleccionar el tipo de población")
        if es_individual and len(subpoblacion) == 0:              errores.append("Debe seleccionar al menos una subpoblación")
        if es_individual and fecha_nacimiento is None:       errores.append("La fecha de nacimiento es obligatoria")
        if es_individual and fecha_nacimiento is not None:
            if fecha_nacimiento.year < 1900:                errores.append("La fecha de nacimiento no puede ser anterior a 1900")
            if fecha_nacimiento > date.today():             errores.append("La fecha de nacimiento no puede ser futura")
        if es_individual and sexo == "Seleccione...":        errores.append("Debe seleccionar un sexo")
        if es_individual and genero == "Seleccione...":             errores.append("Debe seleccionar un género")
        if es_individual and orientacion_sexual == "Seleccione...": errores.append("Debe seleccionar una orientación sexual")
        if es_individual and jefatura_hogar == "Seleccione...":     errores.append("Debe seleccionar jefatura del hogar")
        if departamento == "Seleccione...":             errores.append("Debe seleccionar un departamento")
        if es_individual and zona_rural == "Seleccione...":    errores.append("Debe indicar si vive en zona rural")
        if es_individual and zona_reserva == "Seleccione...":  errores.append("Debe indicar si vive en zona de reserva campesina")
        if municipio == "Seleccione...":                errores.append("Debe seleccionar un municipio")
        if solicitante == "Seleccione...":              errores.append("Debe seleccionar una entidad solicitante")
        if nivel_riesgo == "Seleccione...":             errores.append("Debe seleccionar un nivel de riesgo")
        if es_individual and num_personas is None:       errores.append("El número de personas en el núcleo familiar es obligatorio")
        if es_individual and companero == "Seleccione...": errores.append("Debe indicar si tiene compañero(a) permanente")
        if es_individual and num_hijos_menores is None:  errores.append("El número de hijos menores de edad es obligatorio")
        if es_individual and num_menores_otros is None:  errores.append("El número de menores de edad distintos a hijos es obligatorio")
        if es_individual and num_adultos_mayores is None: errores.append("El número de adultos mayores es obligatorio")
        if es_individual and num_discapacidad is None:   errores.append("El número de personas en situación de discapacidad es obligatorio")
        if es_individual and factor_discapacidad == "Seleccione...": errores.append("Debe seleccionar el factor de discapacidad")
        if es_individual and factor_etnia == "Seleccione...":        errores.append("Debe seleccionar el factor étnico")
        if es_individual and factor_campesino == "Seleccione...":    errores.append("Debe seleccionar el factor campesino")
        if es_individual and factor_cuidador == "Seleccione...":     errores.append("Debe seleccionar el factor cuidador")

        if errores:
            st.error("❌ Por favor corrija los siguientes errores:")
            for e in errores: st.write(f"   • {e}")
        else:
            try:
                if hoja_casos.find_one_by("OT-TE", ot_te.strip()):
                    st.error(f"❌ El caso '{ot_te}' ya existe en esta hoja")
                else:
                    timestamp = datetime.now(tz=_BOGOTA).strftime("%Y-%m-%d %H:%M:%S")
                    id_caso   = hoja_casos.count() + 1
                    hoja_casos.append_row([
                        id_caso, timestamp, tipo_estudio, ot_te.strip(),
                        str(fecha_expedicion_ot) if fecha_expedicion_ot else "",
                        tipo_evaluacion,
                        tipo_colectivo if tipo_colectivo and tipo_colectivo != "Seleccione..." else "",
                        tipo_estructura_partido if tipo_estructura_partido and tipo_estructura_partido != "Seleccione..." else "",
                        estructura_adscrita if estructura_adscrita and estructura_adscrita != "Seleccione..." else "",
                        cant_comunas      if cant_comunas      is not None else "",
                        cant_locales      if cant_locales      is not None else "",
                        cant_municipales  if cant_municipales  is not None else "",
                        cant_metropolitanas if cant_metropolitanas is not None else "",
                        cant_consejerias  if cant_consejerias  is not None else "",
                        tipo_poblacion, " | ".join(subpoblacion),
                        str(fecha_nacimiento) if fecha_nacimiento else "", sexo,
                        genero if genero and genero != "Seleccione..." else "",
                        orientacion_sexual if orientacion_sexual and orientacion_sexual != "Seleccione..." else "",
                        jefatura_hogar if jefatura_hogar and jefatura_hogar != "Seleccione..." else "",
                        zona_rural if zona_rural and zona_rural != "Seleccione..." else "",
                        zona_reserva if zona_reserva and zona_reserva != "Seleccione..." else "",
                        departamento.strip(), municipio.strip(), solicitante, nivel_riesgo,
                        observaciones.strip() if observaciones else "",
                        num_personas if num_personas is not None else "",
                        companero if companero and companero != "Seleccione..." else "",
                        num_hijos_menores if num_hijos_menores is not None else "",
                        num_menores_otros if num_menores_otros is not None else "",
                        num_adultos_mayores if num_adultos_mayores is not None else "",
                        num_discapacidad if num_discapacidad is not None else "",
                        comp_nucleos_familiares if comp_nucleos_familiares is not None else "",
                        comp_num_personas if comp_num_personas is not None else "",
                        comp_menores if comp_menores is not None else "",
                        comp_adultos_mayores_col if comp_adultos_mayores_col is not None else "",
                        comp_discapacidad_col if comp_discapacidad_col is not None else "",
                        comp_num_integrantes if comp_num_integrantes is not None else "",
                        f"{tipo_division}{': ' + comp_otro_cual if tipo_division == 'Otro/¿Cuál?' and comp_otro_cual else tipo_division}",
                        comp_proyecto_productivo if comp_proyecto_productivo != "Seleccione..." else "",
                        " | ".join(comp_actividad_economica),
                        osiegd.strip() if osiegd else "",
                        factor_discapacidad if factor_discapacidad and factor_discapacidad != "Seleccione..." else "",
                        factor_etnia if factor_etnia and factor_etnia != "Seleccione..." else "",
                        factor_campesino if factor_campesino and factor_campesino != "Seleccione..." else "",
                        factor_cuidador if factor_cuidador and factor_cuidador != "Seleccione..." else "",
                        " | ".join(victima_conflicto),
                        " | ".join(lider_social),
                        imp_eco_dependencia if imp_eco_dependencia != "Seleccione..." else "",
                        imp_eco_iniciativas if imp_eco_iniciativas != "Seleccione..." else "",
                        imp_eco_empleos if imp_eco_empleos != "Seleccione..." else "",
                        imp_eco_ilicita if imp_eco_ilicita != "Seleccione..." else "",
                        imp_eco_bienes if imp_eco_bienes != "Seleccione..." else "",
                        imp_soc_tejido if imp_soc_tejido != "Seleccione..." else "",
                        imp_soc_redes if imp_soc_redes != "Seleccione..." else "",
                        imp_soc_traslado if imp_soc_traslado != "Seleccione..." else "",
                        imp_soc_confinamiento if imp_soc_confinamiento != "Seleccione..." else "",
                        imp_soc_movilidad if imp_soc_movilidad != "Seleccione..." else "",
                        imp_soc_desarraigo if imp_soc_desarraigo != "Seleccione..." else "",
                        imp_soc_normalizacion if imp_soc_normalizacion != "Seleccione..." else "",
                        imp_soc_libertad if imp_soc_libertad != "Seleccione..." else "",
                        imp_pol_participacion if imp_pol_participacion != "Seleccione..." else "",
                        imp_pol_liderazgos if imp_pol_liderazgos != "Seleccione..." else "",
                        imp_pol_oferta if imp_pol_oferta != "Seleccione..." else "",
                        imp_pol_derechos if imp_pol_derechos != "Seleccione..." else "",
                        imp_pol_estigmatizacion if imp_pol_estigmatizacion != "Seleccione..." else "",
                        imp_pol_confianza if imp_pol_confianza != "Seleccione..." else "",
                        imp_sal_proyeccion if imp_sal_proyeccion != "Seleccione..." else "",
                        imp_sal_cuidados if imp_sal_cuidados != "Seleccione..." else "",
                        imp_sal_desescolarizacion if imp_sal_desescolarizacion != "Seleccione..." else "",
                        imp_sal_abandono if imp_sal_abandono != "Seleccione..." else "",
                        imp_sal_psicosocial if imp_sal_psicosocial != "Seleccione..." else "",
                        imp_sal_discapacidad if imp_sal_discapacidad != "Seleccione..." else "",
                        imp_sal_dano_vida if imp_sal_dano_vida != "Seleccione..." else "",
                        st.session_state.nombre_completo, st.session_state.username
                    ])
                    hechos_guardados = 0
                    if st.session_state.hechos:
                        _start_hecho = hoja_hechos.count() + 1
                        _rows_hechos = [
                            [
                                _start_hecho + i, id_caso, ot_te.strip(),
                                hecho["tipo"], hecho["fecha"],
                                hecho.get("departamento", ""), hecho.get("municipio", ""),
                                hecho.get("tipo_actor", ""), hecho.get("actor_generador", ""),
                                hecho.get("medio", ""), hecho.get("victima_situacion", ""), hecho.get("tipo_amenaza", ""),
                                hecho.get("motivacion_amenaza", ""), hecho.get("nexo_causal", ""),
                                hecho["descripcion"],
                                st.session_state.nombre_completo, st.session_state.username
                            ]
                            for i, hecho in enumerate(st.session_state.hechos)
                        ]
                        hoja_hechos.append_many_rows(_rows_hechos)
                        hechos_guardados = len(_rows_hechos)
                    perfiles_guardados = 0
                    # Perfiles individuales (perfil antiguo individual)
                    _fuente_perfiles = st.session_state.perfiles if es_individual else st.session_state.get("perfiles_col", [])
                    if _fuente_perfiles:
                        _start_perfil = hoja_perfiles.count() + 1
                        _rows_perfiles = [
                            [
                                _start_perfil + i, id_caso, ot_te.strip(),
                                perfil.get("modo_participacion", ""),
                                perfil.get("anio_ingreso", ""),
                                perfil.get("bloque", ""),
                                perfil.get("estructura", ""),
                                perfil.get("lugar_acreditacion", ""),
                                perfil.get("rol", ""),
                                perfil.get("otro_rol", ""),
                                perfil.get("subpoblacion", ""),
                                perfil.get("meses_privado", ""),
                                perfil.get("tipo_institucion", ""),
                                perfil.get("pabellon_alta_seguridad", ""),
                                st.session_state.nombre_completo, st.session_state.username
                            ]
                            for i, perfil in enumerate(_fuente_perfiles)
                        ]
                        hoja_perfiles.append_many_rows(_rows_perfiles)
                        perfiles_guardados = len(_rows_perfiles)
                    pa_guardados = 0
                    if st.session_state.perfiles_actuales:
                        _start_pa = hoja_perfiles_actuales.count() + 1
                        _start_ic = hoja_instancias_comunes.count() + 1
                        _start_oo = hoja_otras_orgs.count() + 1
                        _rows_pa, _rows_ic, _rows_oo = [], [], []
                        _ic_offset, _oo_offset = 0, 0
                        for i, pa in enumerate(st.session_state.perfiles_actuales):
                            _id_pa = _start_pa + i
                            _rows_pa.append([
                                _id_pa, id_caso, ot_te.strip(),
                                pa.get("familiar_parte_comunes", ""),
                                pa.get("nivel_educativo", ""),
                                pa.get("fuente_ingresos", ""),
                                pa.get("estado_proyecto_arn", ""),
                                pa.get("actividad_economica", ""),
                                pa.get("comparecencia_jep", ""),
                                pa.get("macrocasos_jep", ""),
                                pa.get("victima_jep", ""),
                                pa.get("macrocaso_victima", ""),
                                pa.get("participacion_toar", ""),
                                pa.get("busqueda_desaparecidos", ""),
                                pa.get("participacion_pnis", ""),
                                pa.get("desminado", ""),
                                pa.get("col_jep_comp_cnt", 0),
                                pa.get("col_jep_vic_cnt", 0),
                                pa.get("col_toar_cnt", 0),
                                pa.get("col_busq_cnt", 0),
                                pa.get("col_pnis_cnt", 0),
                                pa.get("col_desminado_cnt", 0),
                                pa.get("participa_comunes", ""),
                                pa.get("concejo_comunes", ""),
                                pa.get("instancias_partido", ""),   # compat: 1er registro
                                pa.get("roles_partido", ""),        # compat: 1er registro
                                pa.get("consejeria_nacional", ""),  # compat: 1er registro
                                pa.get("tipo_consejeria", ""),      # compat: 1er registro
                                pa.get("participa_otras_org", ""),
                                pa.get("tipo_org", ""),             # compat: 1er registro
                                pa.get("nombre_org", ""),           # compat: 1er registro
                                pa.get("ambito_org", ""),           # compat: 1er registro
                                pa.get("escala_org", ""),           # compat: 1er registro
                                pa.get("departamento_org", ""),     # compat: 1er registro
                                pa.get("municipio_org", ""),        # compat: 1er registro
                                pa.get("rol_org", ""),              # compat: 1er registro
                                pa.get("anio_inicio_org", ""),      # compat: 1er registro
                                pa.get("anio_fin_org", ""),         # compat: 1er registro
                                pa.get("cargo_eleccion", ""),
                                pa.get("col_cargo_eleccion_cnt", 0),
                                st.session_state.nombre_completo, st.session_state.username
                            ])
                            # ── Instancias Comunes (multiregistro) ───────────
                            for ic in pa.get("instancias_comunes", []):
                                _rows_ic.append([
                                    _start_ic + _ic_offset, _id_pa, id_caso, ot_te.strip(),
                                    ic.get("instancias_partido", ""),
                                    ic.get("roles_partido", ""),
                                    ic.get("consejeria_nacional", ""),
                                    ic.get("tipo_consejeria", ""),
                                    st.session_state.nombre_completo, st.session_state.username
                                ])
                                _ic_offset += 1
                            # ── Otras Organizaciones (multiregistro) ─────────
                            for oo in pa.get("otras_orgs", []):
                                _amb = oo.get("ambito_counts", {})
                                _rows_oo.append([
                                    _start_oo + _oo_offset, _id_pa, id_caso, ot_te.strip(),
                                    oo.get("tipo_org", ""),
                                    oo.get("nombre_org", ""),
                                    oo.get("ambito_org", ""),
                                    oo.get("escala_org", ""),
                                    oo.get("departamento_org", ""),
                                    oo.get("municipio_org", ""),
                                    oo.get("rol_org", ""),
                                    oo.get("anio_inicio_org", ""),
                                    oo.get("anio_fin_org", ""),
                                    oo.get("num_personas_org", 0),
                                    _amb.get("Ambiental", 0), _amb.get("Campesino", 0),
                                    _amb.get("Comunal", 0), _amb.get("Comunicaciones", 0),
                                    _amb.get("DDHH", 0), _amb.get("Discapacidad", 0),
                                    _amb.get("Educativo", 0), _amb.get("Étnico", 0),
                                    _amb.get("Género", 0), _amb.get("Juvenil", 0),
                                    _amb.get("Político", 0), _amb.get("Reincorporación", 0),
                                    _amb.get("Sector solidario", 0), _amb.get("Sindical", 0),
                                    _amb.get("Víctimas", 0), _amb.get("Otros", 0),
                                    st.session_state.nombre_completo, st.session_state.username
                                ])
                                _oo_offset += 1
                        hoja_perfiles_actuales.append_many_rows(_rows_pa)
                        hoja_instancias_comunes.append_many_rows(_rows_ic)
                        hoja_otras_orgs.append_many_rows(_rows_oo)
                        pa_guardados = len(_rows_pa)
                    antecedentes_guardados = 0
                    if st.session_state.antecedentes:
                        _start_ant = hoja_antecedentes.count() + 1
                        _rows_ant = [
                            [
                                _start_ant + i, id_caso, ot_te.strip(),
                                ant.get("registra_ot", ""),
                                ant.get("ot_te_antecede", ""),
                                ant.get("tipo_ruta_antecedente", ""),
                                ant.get("nivel_riesgo_anterior", ""),
                                ant.get("registra_resoluciones", ""),
                                ant.get("numero_resolucion", ""),
                                ant.get("dia_resolucion", ""),
                                ant.get("mes_resolucion", ""),
                                ant.get("anio_resolucion", ""),
                                st.session_state.nombre_completo, st.session_state.username
                            ]
                            for i, ant in enumerate(st.session_state.antecedentes)
                        ]
                        hoja_antecedentes.append_many_rows(_rows_ant)
                        antecedentes_guardados = len(_rows_ant)
                    desp_guardados = 0
                    if st.session_state.desplazamientos:
                        _start_desp = hoja_desplazamientos.count() + 1
                        _rows_desp = [
                            [
                                _start_desp + i, id_caso, ot_te.strip(),
                                desp.get("motivo", ""),
                                desp.get("medios_transporte", ""),
                                desp.get("dep_origen", ""),
                                desp.get("mun_origen", ""),
                                desp.get("dep_destino", ""),
                                desp.get("mun_destino", ""),
                                desp.get("frecuencia", ""),
                                desp.get("tipo_via", ""),
                                st.session_state.nombre_completo, st.session_state.username
                            ]
                            for i, desp in enumerate(st.session_state.desplazamientos)
                        ]
                        hoja_desplazamientos.append_many_rows(_rows_desp)
                        desp_guardados = len(_rows_desp)
                    ver_guardados = 0
                    if st.session_state.verificaciones:
                        _start_ver = hoja_verificaciones.count() + 1
                        _rows_ver = [
                            [
                                _start_ver + i, id_caso, ot_te.strip(),
                                ver.get("fuente", ""),
                                ver.get("nombre_fuente", ""),
                                ver.get("v_hechos_riesgo", ""),
                                ver.get("v_lugar_hechos", ""),
                                ver.get("v_actor_hechos", ""),
                                ver.get("v_motivacion_amenaza", ""),
                                ver.get("v_perfil_antiguo", ""),
                                ver.get("v_modo_participacion", ""),
                                ver.get("v_rol_perfil_antiguo", ""),
                                ver.get("v_frente_columna", ""),
                                ver.get("v_perfil_actual", ""),
                                ver.get("v_organizacion", ""),
                                ver.get("v_rol_perfil_actual", ""),
                                ver.get("criterios", ""),
                                st.session_state.nombre_completo, st.session_state.username
                            ]
                            for i, ver in enumerate(st.session_state.verificaciones)
                        ]
                        hoja_verificaciones.append_many_rows(_rows_ver)
                        ver_guardados = len(_rows_ver)
                    st.session_state.hechos = []
                    st.session_state.perfiles = []
                    st.session_state.perfiles_col = []
                    st.session_state.antecedentes = []
                    st.session_state.perfiles_actuales = []
                    st.session_state.desplazamientos = []
                    st.session_state.verificaciones = []
                    eliminar_borrador(st.session_state.username, tipo)
                    st.session_state[f"borrador_cargado_{tipo}"] = False
                    st.success(f"✅ Caso **{ot_te}** registrado en {label_badge}!")
                    if hechos_guardados        > 0: st.info(f"⚠️ {hechos_guardados} hecho(s) de riesgo registrados")
                    if perfiles_guardados      > 0: st.info(f"🧑‍🤝‍🧑 {perfiles_guardados} perfil(es) registrados")
                    if antecedentes_guardados  > 0: st.info(f"📁 {antecedentes_guardados} antecedente(s) registrados")
                    if desp_guardados          > 0: st.info(f"🚗 {desp_guardados} desplazamiento(s) registrados")
                    if ver_guardados           > 0: st.info(f"✅ {ver_guardados} verificación(es) registradas")
                    st.balloons()
                    st.info(f"""
                    **Resumen:**
                    - **ID Caso:** {id_caso}
                    - **Tipo de Estudio:** {tipo_estudio}
                    - **OT-TE:** {ot_te}
                    - **Fecha Expedición OT:** {fecha_expedicion_ot}
                    - **Tipo de Evaluación:** {tipo_evaluacion}
                    {f'- **Tipo de Colectivo:** {tipo_colectivo}' if not es_individual else ''}
                    - **Tipo de Población:** {tipo_poblacion}
                    - **Subpoblación:** {" | ".join(subpoblacion)}
                    - **Ubicación:** {municipio}, {departamento}
                    - **Nivel de Riesgo:** {nivel_riesgo}
                    - **Hechos registrados:** {hechos_guardados}
                    - **Registrado por:** {st.session_state.nombre_completo}
                    - **Fecha:** {timestamp}
                    """)
            except Exception as e:
                st.error(f"❌ Error al guardar: {str(e)}")

    st.markdown("---")
    st.caption(f"🔒 Los datos se guardan en la hoja '{nombre_hoja_casos}' de Google Sheets")


def panel_visualizacion():
    if not st.session_state.get("es_admin"):
        st.error("⛔ Acceso restringido a administradores."); return
    import io
    st.title("📊 Casos Registrados"); st.markdown("---")
    tab_ind, tab_col = st.tabs(["👤 Individual", "👥 Colectivo"])
    for tab, tipo in [(tab_ind, "individual"), (tab_col, "colectivo")]:
        with tab:
            (hoja_casos, hoja_hechos, hoja_perfiles, hoja_antecedentes_v,
             hoja_perfiles_actuales_v, hoja_desplazamientos_v, hoja_verificaciones_v,
             hoja_instancias_comunes_v, hoja_otras_orgs_v, sheet_url) = conectar_sheet_casos(tipo)
            if hoja_casos is None: st.error(f"No se pudo conectar a la hoja {tipo}"); continue

            sub1, sub2, sub3, sub4, sub5, sub6, sub7, sub8, sub9 = st.tabs(["📋 Casos", "⚠️ Hechos de Riesgo", "🧑‍🤝‍🧑 Perfil Antiguo", "📁 Antecedentes", "🎯 Perfil Actual", "🚗 Desplazamientos", "✅ Verificaciones", "🏛️ Instancias Comunes", "🤝 Otras Orgs"])

            try: datos   = hoja_casos.get_all_records()
            except: datos = []
            try: datos_h = hoja_hechos.get_all_records()
            except: datos_h = []
            try: datos_p = hoja_perfiles.get_all_records()
            except: datos_p = []
            try: datos_a = hoja_antecedentes_v.get_all_records()
            except: datos_a = []
            try: datos_pa = hoja_perfiles_actuales_v.get_all_records()
            except: datos_pa = []
            try: datos_d = hoja_desplazamientos_v.get_all_records()
            except: datos_d = []
            try: datos_ver = hoja_verificaciones_v.get_all_records()
            except: datos_ver = []
            try: datos_ic  = hoja_instancias_comunes_v.get_all_records()
            except: datos_ic = []
            try: datos_oo  = hoja_otras_orgs_v.get_all_records()
            except: datos_oo = []

            df     = pd.DataFrame(datos)     if datos     else pd.DataFrame()
            df_h   = pd.DataFrame(datos_h)   if datos_h   else pd.DataFrame()
            df_p   = pd.DataFrame(datos_p)   if datos_p   else pd.DataFrame()
            df_a   = pd.DataFrame(datos_a)   if datos_a   else pd.DataFrame()
            df_pa  = pd.DataFrame(datos_pa)  if datos_pa  else pd.DataFrame()
            df_d   = pd.DataFrame(datos_d)   if datos_d   else pd.DataFrame()
            df_ver = pd.DataFrame(datos_ver) if datos_ver else pd.DataFrame()
            df_ic  = pd.DataFrame(datos_ic)  if datos_ic  else pd.DataFrame()
            df_oo  = pd.DataFrame(datos_oo)  if datos_oo  else pd.DataFrame()

            with sub1:
                if not df.empty:
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("Total Casos",   len(df))
                    c2.metric("Departamentos", df["Departamento"].nunique() if "Departamento" in df.columns else 0)
                    c3.metric("Municipios",    df["Municipio"].nunique()    if "Municipio"    in df.columns else 0)
                    c4.metric("Riesgo Alto",   df["Nivel de Riesgo"].isin(["EXTREMO","EXTRAORDINARIO"]).sum() if "Nivel de Riesgo" in df.columns else 0)
                    col1,col2,col3 = st.columns(3)
                    with col1: depto      = st.selectbox("Departamento",    ["Todos"]+sorted(df["Departamento"].unique().tolist())   if "Departamento"  in df.columns else ["Todos"], key=f"depto_{tipo}")
                    with col2: riesgo     = st.selectbox("Nivel de Riesgo", ["Todos"]+sorted(df["Nivel de Riesgo"].unique().tolist()) if "Nivel de Riesgo" in df.columns else ["Todos"], key=f"riesgo_{tipo}")
                    with col3: analista_f = st.selectbox("Analista",        ["Todos"]+sorted(df["Analista"].unique().tolist())       if "Analista"      in df.columns else ["Todos"], key=f"analista_{tipo}")
                    df_f = df.copy()
                    if depto      != "Todos" and "Departamento"    in df.columns: df_f = df_f[df_f["Departamento"]    == depto]
                    if riesgo     != "Todos" and "Nivel de Riesgo" in df.columns: df_f = df_f[df_f["Nivel de Riesgo"] == riesgo]
                    if analista_f != "Todos" and "Analista"        in df.columns: df_f = df_f[df_f["Analista"]        == analista_f]
                    st.subheader(f"📋 Resultados ({len(df_f)} casos)")
                    st.dataframe(df_f, use_container_width=True, hide_index=True)
                else: st.info(f"📭 No hay casos {tipo}s registrados")

            with sub2:
                if not df_h.empty:
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Total Hechos",    len(df_h))
                    c2.metric("Tipos distintos",  df_h["Tipo de Hecho"].nunique() if "Tipo de Hecho" in df_h.columns else 0)
                    c3.metric("Casos con hechos", df_h["ID_Caso"].nunique()       if "ID_Caso"       in df_h.columns else 0)
                    tipo_f = st.selectbox("Filtrar por Tipo", ["Todos"]+sorted(df_h["Tipo de Hecho"].unique().tolist()) if "Tipo de Hecho" in df_h.columns else ["Todos"], key=f"tipo_hecho_{tipo}")
                    df_hf = df_h[df_h["Tipo de Hecho"] == tipo_f].copy() if tipo_f != "Todos" else df_h.copy()
                    st.dataframe(df_hf, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay hechos de riesgo registrados")

            with sub3:
                if not df_p.empty:
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Total Perfiles",    len(df_p))
                    c2.metric("Casos con perfiles", df_p["ID_Caso"].nunique() if "ID_Caso" in df_p.columns else 0)
                    st.dataframe(df_p, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay perfiles registrados")

            with sub4:
                if not df_a.empty:
                    c1,c2 = st.columns(2)
                    c1.metric("Total Antecedentes",    len(df_a))
                    c2.metric("Casos con antecedentes", df_a["ID_Caso"].nunique() if "ID_Caso" in df_a.columns else 0)
                    st.dataframe(df_a, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay antecedentes registrados")

            with sub5:
                if not df_pa.empty:
                    c1, c2 = st.columns(2)
                    c1.metric("Total Perfiles Actuales", len(df_pa))
                    c2.metric("Casos con perfil actual", df_pa["ID_Caso"].nunique() if "ID_Caso" in df_pa.columns else 0)
                    st.dataframe(df_pa, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay perfiles actuales registrados")

            with sub6:
                if not df_d.empty:
                    c1, c2 = st.columns(2)
                    c1.metric("Total Desplazamientos", len(df_d))
                    c2.metric("Casos con desplazamiento", df_d["ID_Caso"].nunique() if "ID_Caso" in df_d.columns else 0)
                    motivo_f = st.selectbox("Filtrar por Motivo", ["Todos"] + sorted(df_d["Motivo Desplazamiento"].unique().tolist()) if "Motivo Desplazamiento" in df_d.columns else ["Todos"], key=f"motivo_desp_{tipo}")
                    df_df = df_d[df_d["Motivo Desplazamiento"] == motivo_f].copy() if motivo_f != "Todos" else df_d.copy()
                    st.dataframe(df_df, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay desplazamientos registrados")

            with sub7:
                if not df_ver.empty:
                    c1, c2 = st.columns(2)
                    c1.metric("Total Verificaciones", len(df_ver))
                    c2.metric("Casos con verificación", df_ver["ID_Caso"].nunique() if "ID_Caso" in df_ver.columns else 0)
                    fuente_f = st.selectbox("Filtrar por Fuente", ["Todos"] + sorted(df_ver["Fuente Verificacion"].unique().tolist()) if "Fuente Verificacion" in df_ver.columns else ["Todos"], key=f"fuente_ver_{tipo}")
                    df_verf = df_ver[df_ver["Fuente Verificacion"] == fuente_f].copy() if fuente_f != "Todos" else df_ver.copy()
                    st.dataframe(df_verf, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay verificaciones registradas")

            with sub8:
                if not df_ic.empty:
                    c1, c2 = st.columns(2)
                    c1.metric("Total Instancias", len(df_ic))
                    c2.metric("Perfiles con instancias", df_ic["ID_Perfil_Actual"].nunique() if "ID_Perfil_Actual" in df_ic.columns else 0)
                    inst_f = st.selectbox("Filtrar por Instancia", ["Todos"] + sorted(df_ic["Instancias Partido"].dropna().unique().tolist()) if "Instancias Partido" in df_ic.columns else ["Todos"], key=f"inst_f_{tipo}")
                    df_icf = df_ic[df_ic["Instancias Partido"] == inst_f].copy() if inst_f != "Todos" else df_ic.copy()
                    st.dataframe(df_icf, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay registros de instancias en Partido Comunes")

            with sub9:
                if not df_oo.empty:
                    c1, c2 = st.columns(2)
                    c1.metric("Total Organizaciones", len(df_oo))
                    c2.metric("Perfiles con org.", df_oo["ID_Perfil_Actual"].nunique() if "ID_Perfil_Actual" in df_oo.columns else 0)
                    tipo_org_f = st.selectbox("Filtrar por Tipo", ["Todos"] + sorted(df_oo["Tipo Org"].dropna().unique().tolist()) if "Tipo Org" in df_oo.columns else ["Todos"], key=f"tipo_org_f_{tipo}")
                    df_oof = df_oo[df_oo["Tipo Org"] == tipo_org_f].copy() if tipo_org_f != "Todos" else df_oo.copy()
                    st.dataframe(df_oof, use_container_width=True, hide_index=True)
                else: st.info("📭 No hay registros de otras organizaciones")


            st.markdown("---")
            if not df.empty or not df_h.empty or not df_p.empty or not df_a.empty or not df_pa.empty or not df_d.empty or not df_ver.empty or not df_ic.empty or not df_oo.empty:
                import re as _re
                def _limpiar_excel(df_in):
                    """Elimina caracteres de control ilegales para openpyxl."""
                    _ctrl = _re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
                    return df_in.map(
                        lambda v: _ctrl.sub("", v) if isinstance(v, str) else v
                    )
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    _limpiar_excel(df_f   if not df.empty   else df).to_excel(writer, sheet_name="Casos",              index=False)
                    _limpiar_excel(df_hf  if not df_h.empty else df_h).to_excel(writer, sheet_name="Hechos de Riesgo", index=False)
                    _limpiar_excel(df_p).to_excel(writer, sheet_name="Perfiles",          index=False)
                    _limpiar_excel(df_a).to_excel(writer, sheet_name="Antecedentes",      index=False)
                    _limpiar_excel(df_pa).to_excel(writer, sheet_name="Perfiles Actuales",   index=False)
                    _limpiar_excel(df_d).to_excel(writer,  sheet_name="Desplazamientos",     index=False)
                    _limpiar_excel(df_ver).to_excel(writer, sheet_name="Verificaciones",     index=False)
                    _limpiar_excel(df_ic).to_excel(writer, sheet_name="Instancias Comunes",  index=False)
                    _limpiar_excel(df_oo).to_excel(writer, sheet_name="Otras Orgs",          index=False)
                buffer.seek(0)
                nombre_archivo = f"ISMR_{tipo}_{datetime.now(tz=_BOGOTA).strftime('%Y%m%d_%H%M')}.xlsx"
                st.download_button(
                    label="📥 Descargar reporte completo (.xlsx)",
                    data=buffer,
                    file_name=nombre_archivo,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_xlsx_{tipo}",
                    use_container_width=True,
                    type="primary"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# Panel_gestion_usuarios
# ═══════════════════════════════════════════════════════════════════════════════

def panel_gestion_usuarios():
    if not st.session_state.get("es_admin"):
        st.error("⛔ Acceso restringido a administradores."); return
    import unicodedata, io
    from data.mongo.usuarios_repo import crear_usuarios_masivo, hashear_password

    def _normalizar(texto):
        """Quita tildes y pasa a minúsculas."""
        return "".join(
            c for c in unicodedata.normalize("NFD", texto)
            if unicodedata.category(c) != "Mn"
        ).lower()

    def _generar_username(nombre_completo):
        """'Juan Carlos Pérez López' → 'juan.perez'  (primer nombre . primer apellido)"""
        partes = nombre_completo.strip().split()
        if len(partes) >= 2:
            return f"{_normalizar(partes[0])}.{_normalizar(partes[-1])}"
        return _normalizar(partes[0]) if partes else ""

    st.title("👥 Gestión de Usuarios")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "➕ Crear Usuario",
        "📤 Carga Masiva (Excel)",
        "📋 Ver Usuarios",
        "🔑 Ver Hashes",
    ])

    # ── TAB 1: Crear usuario individual (sin cambios) ───────────────────────────
    with tab1:
        st.subheader("➕ Crear Nuevo Usuario")
        with st.form("crear_usuario_form"):
            col1, col2 = st.columns(2)
            with col1:
                nuevo_username = st.text_input("Usuario *", placeholder="nombre.apellido")
                nuevo_nombre   = st.text_input("Nombre Completo *", placeholder="Juan Pérez")
            with col2:
                password_default = st.text_input("Contraseña por Defecto *", placeholder="Mínimo 8 caracteres")
                es_admin_nuevo   = st.checkbox("¿Es Administrador?", value=False)
            st.info("💡 El usuario deberá cambiar la contraseña en su primer acceso")
            if st.form_submit_button("✅ Crear Usuario", use_container_width=True, type="primary"):
                if nuevo_username and nuevo_nombre and password_default:
                    if crear_usuario(nuevo_username, password_default, nuevo_nombre, es_admin_nuevo, True):
                        st.success(f"✅ Usuario '{nuevo_username}' creado!")
                        st.info(f"Usuario: **{nuevo_username}** | Contraseña temporal: **{password_default}**")
                    else:
                        st.error("❌ El usuario ya existe o hubo un problema al crearlo")
                else:
                    st.warning("⚠️ Completa todos los campos")

    # ── TAB 2: Carga masiva desde Excel ────────────────────────────────────────
    with tab2:
        st.subheader("📤 Carga Masiva de Usuarios desde Excel")

        # Plantilla descargable
        with st.expander("📥 Descargar plantilla Excel", expanded=False):
            st.markdown(
                "El archivo debe tener **dos columnas** con los encabezados exactos:\n"
                "- `nombre_completo` — Ej: *María López Rodríguez*\n"
                "- `username` *(opcional)* — si se deja vacío se genera automáticamente "
                "como `primer_nombre.primer_apellido`"
            )
            df_plantilla = pd.DataFrame({
                "nombre_completo": ["María López Rodríguez", "Carlos Gómez Martínez"],
                "username":        ["maria.rodriguez",       ""],
            })
            buf_plantilla = io.BytesIO()
            df_plantilla.to_excel(buf_plantilla, index=False, engine="openpyxl")
            buf_plantilla.seek(0)
            st.download_button(
                "⬇️ Descargar plantilla",
                data=buf_plantilla,
                file_name="plantilla_usuarios.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.markdown("---")

        archivo = st.file_uploader(
            "Sube el Excel con los usuarios", type=["xlsx", "xls"],
            help="Columna requerida: nombre_completo. Opcional: username",
        )

        if archivo:
            try:
                df_up = pd.read_excel(archivo, dtype=str).fillna("")
            except Exception as e:
                st.error(f"❌ No se pudo leer el archivo: {e}")
                df_up = None

            if df_up is not None:
                if "nombre_completo" not in df_up.columns:
                    st.error("❌ El archivo debe tener una columna llamada **nombre_completo**.")
                else:
                    # Generar username si está vacío o la columna no existe
                    if "username" not in df_up.columns:
                        df_up["username"] = ""
                    df_up["username"] = df_up.apply(
                        lambda r: r["username"].strip() if r["username"].strip()
                        else _generar_username(r["nombre_completo"]),
                        axis=1,
                    )
                    df_up = df_up[df_up["nombre_completo"].str.strip() != ""].reset_index(drop=True)

                    st.info(f"📊 Se encontraron **{len(df_up)}** usuarios en el archivo.")
                    st.dataframe(
                        df_up[["nombre_completo", "username"]],
                        use_container_width=True,
                        hide_index=True,
                    )

                    col_pw, col_adm = st.columns(2)
                    with col_pw:
                        pwd_masiva = st.text_input(
                            "Contraseña temporal para todos",
                            key="pwd_masiva",
                            placeholder="Mínimo 8 caracteres",
                            help="Todos los usuarios deberán cambiarla al primer ingreso",
                        )
                    with col_adm:
                        admin_masivo = st.checkbox(
                            "¿Todos son administradores?", value=False, key="admin_masivo"
                        )

                    if st.button("🚀 Crear todos los usuarios", type="primary", use_container_width=True):
                        if not pwd_masiva:
                            st.warning("⚠️ Define una contraseña temporal")
                        else:
                            lista = df_up[["nombre_completo", "username"]].to_dict("records")
                            with st.spinner(f"Registrando {len(lista)} usuarios…"):
                                resultado = crear_usuarios_masivo(lista, pwd_masiva, admin_masivo)

                            creados  = resultado["creados"]
                            omitidos = resultado["omitidos"]
                            errores  = resultado["errores"]

                            if creados:
                                st.success(f"✅ **{len(creados)}** usuarios creados correctamente.")
                            if omitidos:
                                st.warning(f"⚠️ **{len(omitidos)}** ya existían y fueron omitidos: {', '.join(omitidos)}")
                            if errores:
                                st.error(f"❌ **{len(errores)}** con errores:")
                                for e in errores:
                                    st.caption(f"• `{e['username']}`: {e['error']}")

                            # Resumen descargable
                            df_res = pd.DataFrame({
                                "username": creados + omitidos + [e["username"] for e in errores],
                                "estado":   (["creado"]     * len(creados) +
                                             ["ya existía"] * len(omitidos) +
                                             ["error"]      * len(errores)),
                                "detalle":  ([""] * len(creados) +
                                             [""] * len(omitidos) +
                                             [e["error"] for e in errores]),
                            })
                            buf_res = io.BytesIO()
                            df_res.to_excel(buf_res, index=False, engine="openpyxl")
                            buf_res.seek(0)
                            st.download_button(
                                "📥 Descargar resumen de carga",
                                data=buf_res,
                                file_name="resumen_carga_usuarios.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )

    # ── TAB 3: Ver usuarios ─────────────────────────────────────────────────────
    with tab3:
        st.subheader("📋 Lista de Usuarios")
        usuarios = listar_usuarios()
        if usuarios:
            df = pd.DataFrame(usuarios)
            c1, c2, c3 = st.columns(3)
            c1.metric("Total", len(df))
            admins = df[df["es_admin"].astype(str).str.upper() == "TRUE"].shape[0] if "es_admin" in df.columns else 0
            c2.metric("Admins", admins)
            c3.metric("Analistas", len(df) - admins)
            st.dataframe(
                df[["username", "nombre_completo", "es_admin", "debe_cambiar_password"]],
                use_container_width=True,
            )
        else:
            st.info("📭 No hay usuarios")

    # ── TAB 4: Ver hashes ───────────────────────────────────────────────────────
    with tab4:
        st.subheader("🔑 Hashes de Contraseñas")
        st.warning("⚠️ Información sensible — solo visible para administradores")
        if st.checkbox("Mostrar hashes"):
            for u in listar_usuarios():
                with st.expander(f"👤 {u.get('nombre_completo','?')} (@{u.get('username','?')})"):
                    st.code(u.get('password_hash', 'N/A'), language=None)
                    st.caption(f"Debe cambiar: {u.get('debe_cambiar_password','N/A')}")


# ═════════════════════════════════════════════════════════════════════════════
# RECUPERACIÓN DE CONTRASEÑA
# ═════════════════════════════════════════════════════════════════════════════

def pantalla_recovery_solicitar():
    from service.recovery_service import enviar_codigo_recuperacion, username_a_email

    st.title("🔑 Recuperar Contraseña")
    st.markdown("---")
    st.info(
        "Ingresa tu nombre de usuario. Te enviaremos un código de verificación "
        "a tu correo institucional **@unp.gov.co**."
    )

    with st.form("recovery_solicitar_form"):
        username = st.text_input("Usuario", placeholder="nombre.apellido")
        submit   = st.form_submit_button("📨 Enviar código", use_container_width=True, type="primary")

        if submit:
            if not username.strip():
                st.warning("⚠️ Ingresa tu nombre de usuario")
            elif not usuario_existe(username.strip()):
                # Mensaje genérico para no revelar si el usuario existe
                st.warning("⚠️ Si el usuario existe, recibirás un correo en breve.")
            else:
                with st.spinner("Enviando código..."):
                    ok, resultado = enviar_codigo_recuperacion(username.strip())
                if ok:
                    email_visible = username_a_email(username.strip())
                    st.session_state["recovery_username"] = username.strip()
                    st.session_state.vista_recovery = "verificar"
                    st.success(f"✅ Código enviado a **{email_visible}**")
                    st.rerun()
                else:
                    st.error(f"❌ No se pudo enviar el correo. Contacta al administrador.\n\n`{resultado}`")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Volver al inicio de sesión", type="secondary"):
        st.session_state.vista_recovery = None
        st.rerun()


def pantalla_recovery_verificar():
    from service.recovery_service import validar_codigo, username_a_email

    username = st.session_state.get("recovery_username", "")
    email_visible = username_a_email(username) if username else "tu correo"

    st.title("🔑 Verificar Código")
    st.markdown("---")
    st.info(f"Ingresa el código de 6 dígitos enviado a **{email_visible}**. Expira en 15 minutos.")

    with st.form("recovery_verificar_form"):
        codigo = st.text_input("Código de verificación", placeholder="000000", max_chars=6)
        submit = st.form_submit_button("✅ Verificar código", use_container_width=True, type="primary")

        if submit:
            if not codigo.strip():
                st.warning("⚠️ Ingresa el código")
            elif not validar_codigo(username, codigo.strip()):
                st.error("❌ Código incorrecto o expirado. Solicita uno nuevo.")
            else:
                st.session_state["recovery_codigo_ok"] = True
                st.session_state.vista_recovery = "nueva_password"
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("← Solicitar nuevo código", use_container_width=True, type="secondary"):
            st.session_state.vista_recovery = "solicitar"
            st.rerun()
    with col_b:
        if st.button("✖ Cancelar", use_container_width=True, type="secondary"):
            st.session_state.vista_recovery = None
            st.session_state.pop("recovery_username", None)
            st.rerun()


def pantalla_recovery_nueva_password():
    from service.recovery_service import limpiar_codigo

    username = st.session_state.get("recovery_username", "")

    # Guardia: si llegaron sin pasar por verificación, redirigir
    if not st.session_state.get("recovery_codigo_ok"):
        st.session_state.vista_recovery = "solicitar"
        st.rerun()

    st.title("🔑 Nueva Contraseña")
    st.markdown("---")
    st.success(f"✅ Identidad verificada para **{username}**")

    with st.form("recovery_nueva_password_form"):
        nueva     = st.text_input("Nueva contraseña", type="password", help="Mínimo 8 caracteres")
        confirmar = st.text_input("Confirmar contraseña", type="password")
        submit    = st.form_submit_button("💾 Guardar contraseña", use_container_width=True, type="primary")

        if submit:
            errores = []
            if not nueva:          errores.append("La contraseña no puede estar vacía")
            elif len(nueva) < 8:   errores.append("Mínimo 8 caracteres")
            if nueva != confirmar: errores.append("Las contraseñas no coinciden")

            if errores:
                for e in errores: st.error(f"❌ {e}")
            else:
                nuevo_hash = hashear_password(nueva)
                if actualizar_password(username, nuevo_hash, False):
                    limpiar_codigo(username)
                    st.session_state.vista_recovery        = None
                    st.session_state["recovery_username"]  = None
                    st.session_state["recovery_codigo_ok"] = False
                    st.success("✅ ¡Contraseña actualizada! Ya puedes iniciar sesión.")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("❌ No se pudo actualizar la contraseña. Intenta de nuevo.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✖ Cancelar", type="secondary"):
        st.session_state.vista_recovery        = None
        st.session_state["recovery_username"]  = None
        st.session_state["recovery_codigo_ok"] = False
        st.rerun()
