import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import hashlib
import time
import os

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "front", "logo_hidra.png")

st.set_page_config(page_title="HIDRA", page_icon="💧", layout="centered")

defaults = {
    "autenticado": False, "username": None, "nombre_completo": None,
    "debe_cambiar_password": False, "es_admin": False, "vista": None, "hechos": []
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

TAB_NOMBRES = {
    "individual": {"casos": "Individual",  "hechos": "Hechos_Individual"},
    "colectivo":  {"casos": "Colectivo",   "hechos": "Hechos_Colectivo"},
}

def inyectar_css_selector():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');
        .stApp { background: #0A0A0F; }
        #MainMenu, footer, header { visibility: hidden; }
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
    </style>
    """, unsafe_allow_html=True)

# ── Usuarios ──────────────────────────────────────────────────────────────────

def conectar_sheet_usuarios():
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        sheet_name = st.secrets.get("sheet_usuarios", "ISMR_Usuarios")
        try:
            spreadsheet = client.open(sheet_name)
        except:
            spreadsheet = client.create(sheet_name)
            spreadsheet.share(credentials_dict["client_email"], perm_type='user', role='writer')
        worksheet = spreadsheet.sheet1
        if not worksheet.row_values(1):
            worksheet.append_row(["username","password_hash","nombre_completo","es_admin","debe_cambiar_password"])
        return worksheet
    except Exception as e:
        st.error(f"Error al conectar sheet de usuarios: {str(e)}")
        return None

def obtener_usuario(username):
    worksheet = conectar_sheet_usuarios()
    if not worksheet: return None
    try:
        for u in worksheet.get_all_records():
            if u.get('username') == username: return u
        return None
    except: return None

def actualizar_password(username, nuevo_hash, debe_cambiar=False):
    worksheet = conectar_sheet_usuarios()
    if not worksheet: return False
    try:
        datos = worksheet.get_all_values()
        for idx, fila in enumerate(datos[1:], start=2):
            if fila[0] == username:
                worksheet.update_cell(idx, 2, nuevo_hash)
                worksheet.update_cell(idx, 5, str(debe_cambiar).upper())
                return True
        return False
    except Exception as e:
        st.error(f"Error al actualizar contraseña: {str(e)}")
        return False

def crear_usuario(username, password_hash, nombre_completo, es_admin=False, debe_cambiar=True):
    worksheet = conectar_sheet_usuarios()
    if not worksheet: return False
    try:
        if obtener_usuario(username): return False
        worksheet.append_row([username, password_hash, nombre_completo,
                               str(es_admin).upper(), str(debe_cambiar).upper()])
        return True
    except Exception as e:
        st.error(f"Error al crear usuario: {str(e)}")
        return False

def listar_usuarios():
    worksheet = conectar_sheet_usuarios()
    if not worksheet: return []
    try: return worksheet.get_all_records()
    except: return []

# ── Casos y Hechos ────────────────────────────────────────────────────────────

def conectar_sheet_casos(tipo="individual"):
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        spreadsheet = client.open(st.secrets.get("sheet_name", "ISMR_Casos"))

        tab_casos  = TAB_NOMBRES[tipo]["casos"]
        tab_hechos = TAB_NOMBRES[tipo]["hechos"]

        try: hoja_casos = spreadsheet.worksheet(tab_casos)
        except: hoja_casos = spreadsheet.add_worksheet(title=tab_casos, rows="1000", cols="20")
        if not hoja_casos.get_all_values():
            hoja_casos.append_row(["ID_Caso","Timestamp","OT-TE","Edad","Sexo",
                                   "Departamento","Municipio","Solicitante",
                                   "Nivel de Riesgo","Observaciones","Analista","Usuario Analista"])

        try: hoja_hechos = spreadsheet.worksheet(tab_hechos)
        except: hoja_hechos = spreadsheet.add_worksheet(title=tab_hechos, rows="1000", cols="20")
        if not hoja_hechos.get_all_values():
            hoja_hechos.append_row(["ID_Hecho","ID_Caso","OT-TE","Tipo de Hecho",
                                    "Fecha del Hecho","Lugar","Autor","Descripcion",
                                    "Analista","Usuario Analista"])

        return hoja_casos, hoja_hechos, spreadsheet.url
    except Exception as e:
        st.error(f"Error al conectar Google Sheets ({tipo}): {str(e)}")
        return None, None, None

def obtener_siguiente_id(hoja):
    return max(len(hoja.get_all_values()), 1)

# ── Auth ──────────────────────────────────────────────────────────────────────

def verificar_credenciales(username, password):
    usuario = obtener_usuario(username)
    if not usuario: return False, None, False, False
    try:
        if 'password_hash' not in usuario:
            st.error("La hoja de usuarios no tiene el formato correcto.")
            return False, None, False, False
        phash = hashlib.sha256(password.encode()).hexdigest()
        if phash == usuario['password_hash']:
            debe_cambiar = str(usuario.get('debe_cambiar_password','FALSE')).upper() == 'TRUE'
            es_admin     = str(usuario.get('es_admin','FALSE')).upper() == 'TRUE'
            return True, usuario.get('nombre_completo', username), debe_cambiar, es_admin
        return False, None, False, False
    except Exception as e:
        st.error(f"Error en verificación: {str(e)}")
        return False, None, False, False

def logout():
    for key in defaults: st.session_state[key] = defaults[key]
    st.rerun()

# ── Pantallas ─────────────────────────────────────────────────────────────────

def login_page():
    st.image(LOGO_PATH, width=280)
    st.markdown("---")
    st.info("👋 Identifícate para acceder al sistema")
    with st.form("login_form"):
        username = st.text_input("Usuario", placeholder="tu.usuario")
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
    st.markdown("---")
    st.caption("🔒 Si tienes problemas, contacta al administrador")

def pantalla_cambiar_password():
    st.image(LOGO_PATH, width=220)
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
                nuevo_hash = hashlib.sha256(nueva.encode()).hexdigest()
                if actualizar_password(st.session_state.username, nuevo_hash, False):
                    st.session_state.debe_cambiar_password = False
                    st.success("✅ ¡Contraseña actualizada!")
                    time.sleep(1); st.rerun()
                else: st.error("❌ Error al actualizar. Intenta de nuevo.")

def pantalla_selector():
    inyectar_css_selector()
    nombre = st.session_state.nombre_completo or "Analista"
    nombre_corto = nombre.split()[0] if nombre else "Analista"
    st.markdown(f"""
    <div style="text-align:center; margin-bottom:48px; margin-top:20px;">
        <p style="font-family:'DM Sans',sans-serif; font-weight:300; font-size:13px;
                  letter-spacing:4px; text-transform:uppercase; color:#555; margin-bottom:6px;">BIENVENIDO</p>
        <p style="font-family:'Bebas Neue',sans-serif; font-size:clamp(28px,5vw,40px);
                  letter-spacing:3px; color:#F0F0F0; margin:0;">{nombre_corto}</p>
        <p style="font-size:12px; color:#444; letter-spacing:1px; margin-top:6px;">SELECCIONA EL TIPO DE FORMULARIO</p>
    </div>""", unsafe_allow_html=True)
    col_logo, _, _ = st.columns([1, 2, 1])
    with col_logo:
        st.image(LOGO_PATH, width=160)

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.markdown('<div style="text-align:center;margin-bottom:12px;"><span style="font-size:32px;">👤</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="btn-individual">', unsafe_allow_html=True)
        if st.button("FORMULARIO\nINDIVIDUAL", key="btn_individual", use_container_width=True):
            st.session_state.vista = "individual"; st.session_state.hechos = []; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;font-size:11px;color:#444;margin-top:10px;">Un caso por registro</p>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div style="text-align:center;margin-bottom:12px;"><span style="font-size:32px;">👥</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="btn-colectivo">', unsafe_allow_html=True)
        if st.button("FORMULARIO\nCOLECTIVO", key="btn_colectivo", use_container_width=True):
            st.session_state.vista = "colectivo"; st.session_state.hechos = []; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;font-size:11px;color:#444;margin-top:10px;">Múltiples personas afectadas</p>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, col_logout, _ = st.columns([2, 1, 2])
    with col_logout:
        if st.button("🚪 Cerrar sesión", use_container_width=True, type="secondary"): logout()

# ── Formulario ────────────────────────────────────────────────────────────────

def formulario_casos(tipo="individual"):
    es_individual     = tipo == "individual"
    color             = "#4F8BFF" if es_individual else "#4ADE80"
    icono             = "👤"      if es_individual else "👥"
    label_badge       = "INDIVIDUAL" if es_individual else "COLECTIVO"
    titulo            = "Formulario Individual" if es_individual else "Formulario Colectivo"
    nombre_hoja_casos = TAB_NOMBRES[tipo]["casos"]   # FIX: accesible en todo el scope

    hoja_casos, hoja_hechos, sheet_url = conectar_sheet_casos(tipo)
    if hoja_casos is None:
        st.error("⚠️ No se pudo conectar a Google Sheets"); return

    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("← Volver", type="secondary"):
            st.session_state.vista = None; st.session_state.hechos = []; st.rerun()
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
    st.subheader("📝 Información del Caso")
    ot_te = st.text_input("OT-TE *", placeholder="Ejemplo: OT-2024-001")
    col1, col2 = st.columns(2)
    with col1:
        edad         = st.number_input("Edad *", min_value=0, max_value=120, value=None)
        sexo         = st.selectbox("Sexo *", ["Seleccione...", "Hombre", "Mujer", "Otro", "No Reporta"])
        departamento = st.text_input("Departamento *", placeholder="Ejemplo: Antioquia")
    with col2:
        municipio    = st.text_input("Municipio *", placeholder="Ejemplo: Medellín")
        solicitante  = st.selectbox("Entidad Solicitante *", ["Seleccione...", "ARN", "SESP", "OTRO"])
        nivel_riesgo = st.selectbox("Nivel de Riesgo *", ["Seleccione...", "EXTRAORDINARIO", "EXTREMO", "ORDINARIO"])
    observaciones = st.text_area("Observaciones (Opcional)", height=80)

    # ── Hechos de Riesgo ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("⚠️ Hechos de Riesgo")
    st.caption("Opcional. Agrega uno o varios hechos de riesgo asociados a este caso.")

    for i, hecho in enumerate(st.session_state.hechos):
        with st.container(border=True):
            col_tit, col_del = st.columns([5, 1])
            with col_tit: st.markdown(f"**Hecho #{i+1} — {hecho['tipo']}**")
            with col_del:
                if st.button("🗑️", key=f"del_{tipo}_{i}"):
                    st.session_state.hechos.pop(i); st.rerun()
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"📅 **Fecha:** {hecho['fecha']}")
                st.write(f"📍 **Lugar:** {hecho['lugar']}")
            with c2:
                st.write(f"👤 **Autor:** {hecho['autor']}")
            st.write(f"📄 **Descripción:** {hecho['descripcion']}")

    with st.expander("➕ Agregar hecho de riesgo", expanded=len(st.session_state.hechos) == 0):
        with st.form(f"form_hecho_{tipo}", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                tipo_hecho  = st.selectbox("Tipo de Hecho *", [
                    "Seleccione...", "Amenaza", "Atentado", "Desplazamiento forzado",
                    "Homicidio", "Secuestro", "Extorsión", "Reclutamiento forzado",
                    "Violencia sexual", "Confinamiento", "Otro"])
                fecha_hecho = st.date_input("Fecha del Hecho *")
                lugar_hecho = st.text_input("Lugar donde ocurrió *", placeholder="Municipio, vereda, barrio...")
            with c2:
                autor_hecho       = st.text_input("Autor *", placeholder="Grupo armado, persona, etc.")
                descripcion_hecho = st.text_area("Descripción *",
                                                 placeholder="Describe brevemente el hecho...", height=122)
            if st.form_submit_button("➕ Agregar este hecho", use_container_width=True):
                err_h = []
                if tipo_hecho == "Seleccione...": err_h.append("Selecciona el tipo de hecho")
                if not lugar_hecho.strip():        err_h.append("El lugar es obligatorio")
                if not autor_hecho.strip():        err_h.append("El autor es obligatorio")
                if not descripcion_hecho.strip():  err_h.append("La descripción es obligatoria")
                if err_h:
                    for e in err_h: st.error(f"• {e}")
                else:
                    st.session_state.hechos.append({
                        "tipo": tipo_hecho, "fecha": str(fecha_hecho),
                        "lugar": lugar_hecho.strip(), "autor": autor_hecho.strip(),
                        "descripcion": descripcion_hecho.strip()
                    })
                    st.success("✅ Hecho agregado"); st.rerun()

    # ── Botón Registrar ───────────────────────────────────────────────────────
    st.markdown("---")
    if st.button(f"✅ REGISTRAR CASO {label_badge}", use_container_width=True, type="primary"):
        errores = []
        if not ot_te or ot_te.strip() == "":            errores.append("El campo OT-TE es obligatorio")
        if edad is None or edad == 0:                   errores.append("La edad es obligatoria")
        if sexo == "Seleccione...":                     errores.append("Debe seleccionar un sexo")
        if not departamento or departamento.strip() == "": errores.append("El departamento es obligatorio")
        if not municipio or municipio.strip() == "":    errores.append("El municipio es obligatorio")
        if solicitante == "Seleccione...":              errores.append("Debe seleccionar una entidad solicitante")
        if nivel_riesgo == "Seleccione...":             errores.append("Debe seleccionar un nivel de riesgo")

        if errores:
            st.error("❌ Por favor corrija los siguientes errores:")
            for e in errores: st.write(f"   • {e}")
        else:
            try:
                todas_filas   = hoja_casos.get_all_values()
                ot_existentes = [fila[2] for fila in todas_filas[1:]]
                if ot_te.strip() in ot_existentes:
                    st.error(f"❌ El caso '{ot_te}' ya existe en esta hoja")
                else:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    id_caso   = obtener_siguiente_id(hoja_casos)
                    hoja_casos.append_row([
                        id_caso, timestamp, ot_te.strip(), edad, sexo,
                        departamento.strip(), municipio.strip(), solicitante, nivel_riesgo,
                        observaciones.strip() if observaciones else "",
                        st.session_state.nombre_completo, st.session_state.username
                    ])
                    hechos_guardados = 0
                    for hecho in st.session_state.hechos:
                        id_hecho = obtener_siguiente_id(hoja_hechos)
                        hoja_hechos.append_row([
                            id_hecho, id_caso, ot_te.strip(),
                            hecho["tipo"], hecho["fecha"], hecho["lugar"],
                            hecho["autor"], hecho["descripcion"],
                            st.session_state.nombre_completo, st.session_state.username
                        ])
                        hechos_guardados += 1
                    st.session_state.hechos = []
                    st.success(f"✅ Caso **{ot_te}** registrado en {label_badge}!")
                    if hechos_guardados > 0: st.info(f"⚠️ {hechos_guardados} hecho(s) de riesgo registrados")
                    st.balloons()
                    st.info(f"""
                    **Resumen:**
                    - **ID Caso:** {id_caso}
                    - **OT-TE:** {ot_te}
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

# ── Panel Visualización ───────────────────────────────────────────────────────

def panel_visualizacion():
    st.title("📊 Casos Registrados"); st.markdown("---")
    tab_ind, tab_col = st.tabs(["👤 Individual", "👥 Colectivo"])
    for tab, tipo in [(tab_ind, "individual"), (tab_col, "colectivo")]:
        with tab:
            hoja_casos, hoja_hechos, sheet_url = conectar_sheet_casos(tipo)
            if hoja_casos is None: st.error(f"No se pudo conectar a la hoja {tipo}"); continue
            if sheet_url: st.markdown(f"[📝 Abrir en Google Sheets]({sheet_url})")
            sub1, sub2 = st.tabs(["📋 Casos", "⚠️ Hechos de Riesgo"])
            with sub1:
                try:
                    datos = hoja_casos.get_all_records()
                    if datos:
                        df = pd.DataFrame(datos)
                        c1,c2,c3,c4 = st.columns(4)
                        c1.metric("Total Casos",   len(df))
                        c2.metric("Departamentos", df["Departamento"].nunique() if "Departamento" in df.columns else 0)
                        c3.metric("Municipios",    df["Municipio"].nunique()    if "Municipio"    in df.columns else 0)
                        c4.metric("Riesgo Alto",   df["Nivel de Riesgo"].isin(["EXTREMO","EXTRAORDINARIO"]).sum() if "Nivel de Riesgo" in df.columns else 0)
                        col1,col2,col3 = st.columns(3)
                        with col1: depto      = st.selectbox("Departamento",  ["Todos"]+sorted(df["Departamento"].unique().tolist())  if "Departamento"  in df.columns else ["Todos"], key=f"depto_{tipo}")
                        with col2: riesgo     = st.selectbox("Nivel de Riesgo",["Todos"]+sorted(df["Nivel de Riesgo"].unique().tolist()) if "Nivel de Riesgo" in df.columns else ["Todos"], key=f"riesgo_{tipo}")
                        with col3: analista_f = st.selectbox("Analista",       ["Todos"]+sorted(df["Analista"].unique().tolist())      if "Analista"      in df.columns else ["Todos"], key=f"analista_{tipo}")
                        df_f = df.copy()
                        if depto      != "Todos" and "Departamento"    in df.columns: df_f = df_f[df_f["Departamento"]    == depto]
                        if riesgo     != "Todos" and "Nivel de Riesgo" in df.columns: df_f = df_f[df_f["Nivel de Riesgo"] == riesgo]
                        if analista_f != "Todos" and "Analista"        in df.columns: df_f = df_f[df_f["Analista"]        == analista_f]
                        st.subheader(f"📋 Resultados ({len(df_f)} casos)")
                        st.dataframe(df_f, use_container_width=True, hide_index=True)
                        csv = df_f.to_csv(index=False, encoding="utf-8-sig")
                        st.download_button(f"📥 Descargar CSV", csv, f"casos_{tipo}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key=f"dl_casos_{tipo}")
                    else: st.info(f"📭 No hay casos {tipo}s registrados")
                except Exception as e: st.error(f"Error al cargar casos: {str(e)}")
            with sub2:
                try:
                    datos_h = hoja_hechos.get_all_records()
                    if datos_h:
                        df_h = pd.DataFrame(datos_h)
                        c1,c2,c3 = st.columns(3)
                        c1.metric("Total Hechos",    len(df_h))
                        c2.metric("Tipos distintos",  df_h["Tipo de Hecho"].nunique() if "Tipo de Hecho" in df_h.columns else 0)
                        c3.metric("Casos con hechos", df_h["ID_Caso"].nunique()       if "ID_Caso"       in df_h.columns else 0)
                        tipo_f = st.selectbox("Filtrar por Tipo", ["Todos"]+sorted(df_h["Tipo de Hecho"].unique().tolist()) if "Tipo de Hecho" in df_h.columns else ["Todos"], key=f"tipo_hecho_{tipo}")
                        df_hf = df_h[df_h["Tipo de Hecho"] == tipo_f].copy() if tipo_f != "Todos" else df_h.copy()
                        st.dataframe(df_hf, use_container_width=True, hide_index=True)
                        csv_h = df_hf.to_csv(index=False, encoding="utf-8-sig")
                        st.download_button(f"📥 Descargar CSV Hechos", csv_h, f"hechos_{tipo}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key=f"dl_hechos_{tipo}")
                    else: st.info("📭 No hay hechos de riesgo registrados")
                except Exception as e: st.error(f"Error al cargar hechos: {str(e)}")

# ── Panel Usuarios ────────────────────────────────────────────────────────────

def panel_gestion_usuarios():
    st.title("👥 Gestión de Usuarios"); st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["➕ Crear Usuario", "📋 Ver Usuarios", "🔑 Ver Hashes"])
    with tab1:
        st.subheader("➕ Crear Nuevo Usuario")
        with st.form("crear_usuario_form"):
            col1, col2 = st.columns(2)
            with col1:
                nuevo_username = st.text_input("Usuario *", placeholder="nombre.apellido")
                nuevo_nombre   = st.text_input("Nombre Completo *", placeholder="Juan Pérez")
            with col2:
                password_default = st.text_input("Contraseña por Defecto *", value="ISMR2024")
                es_admin_nuevo   = st.checkbox("¿Es Administrador?", value=False)
            st.info("💡 El usuario deberá cambiar la contraseña en su primer acceso")
            if st.form_submit_button("✅ Crear Usuario", use_container_width=True, type="primary"):
                if nuevo_username and nuevo_nombre and password_default:
                    phash = hashlib.sha256(password_default.encode()).hexdigest()
                    if crear_usuario(nuevo_username, phash, nuevo_nombre, es_admin_nuevo, True):
                        st.success(f"✅ Usuario '{nuevo_username}' creado!")
                        st.info(f"Usuario: **{nuevo_username}** | Contraseña temporal: **{password_default}**")
                    else: st.error("❌ El usuario ya existe o hubo un problema al crearlo")
                else: st.warning("⚠️ Completa todos los campos")
    with tab2:
        st.subheader("📋 Lista de Usuarios")
        usuarios = listar_usuarios()
        if usuarios:
            df = pd.DataFrame(usuarios)
            c1,c2,c3 = st.columns(3)
            c1.metric("Total", len(df))
            admins = df[df["es_admin"].astype(str).str.upper() == "TRUE"].shape[0] if "es_admin" in df.columns else 0
            c2.metric("Admins", admins); c3.metric("Analistas", len(df)-admins)
            st.dataframe(df[["username","nombre_completo","es_admin","debe_cambiar_password"]], use_container_width=True)
        else: st.info("📭 No hay usuarios")
    with tab3:
        st.subheader("🔑 Hashes de Contraseñas")
        st.warning("⚠️ Información sensible — solo visible para administradores")
        if st.checkbox("Mostrar hashes"):
            for u in listar_usuarios():
                with st.expander(f"👤 {u.get('nombre_completo','?')} (@{u.get('username','?')})"):
                    st.code(u.get('password_hash','N/A'), language=None)
                    st.caption(f"Debe cambiar: {u.get('debe_cambiar_password','N/A')}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not st.session_state.autenticado:
        login_page(); return
    if st.session_state.debe_cambiar_password:
        pantalla_cambiar_password(); return
    if st.session_state.es_admin:
        st.sidebar.image(LOGO_PATH, use_container_width=True)
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
