import streamlit as st
import gspread
from google.oauth2.service_account import Credentials


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
