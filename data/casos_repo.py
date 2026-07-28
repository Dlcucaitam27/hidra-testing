import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from configuration.settings import TAB_NOMBRES


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
