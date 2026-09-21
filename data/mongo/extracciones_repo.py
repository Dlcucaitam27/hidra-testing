import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
from pymongo import ASCENDING, DESCENDING

from data.mongo.casos_repo import _conectar_db, _serializar

# Colección con el JSON extraído de cada formato GESP-FT-14 cargado (Word/PDF).
# El archivo original NO se guarda: solo su hash SHA-256 para trazabilidad.
_COLECCION = "extracciones_documentos"


@st.cache_resource
def _indices_extracciones():
    """Bandera compartida por worker para crear los índices una sola vez."""
    return {"creados": False}


def _coleccion():
    db = _conectar_db()
    if db is None:
        return None
    col = db[_COLECCION]
    bandera = _indices_extracciones()
    if not bandera["creados"]:
        col.create_index([("sha256", ASCENDING)], background=True)
        col.create_index([("usuario", ASCENDING), ("guardado_en", DESCENDING)], background=True)
        bandera["creados"] = True
    return col


def guardar_extraccion(datos: dict, username: str, tipo: str) -> str | None:
    """
    Inserta el JSON extraído junto con quién lo cargó y cuándo.
    Devuelve el id insertado (str) o None si falló.
    """
    col = _coleccion()
    if col is None:
        return None
    try:
        meta = datos.get("_meta", {})
        doc = {
            "usuario": username,
            "tipo_formulario": tipo,
            "archivo": meta.get("archivo", ""),
            "sha256": meta.get("sha256", ""),
            "formato": meta.get("formato", ""),
            "version_esquema": meta.get("version_esquema", ""),
            "numero_ot": datos.get("informacion_general", {}).get("numero_ot", ""),
            "guardado_en": datetime.now(tz=ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M:%S"),
            "datos": _serializar(datos),
        }
        return str(col.insert_one(doc).inserted_id)
    except Exception as e:
        st.error(f"Error al guardar la extracción del documento: {str(e)}")
        return None


def buscar_extraccion_por_hash(sha256: str) -> dict | None:
    """Última extracción guardada del mismo archivo (para avisar de cargas repetidas)."""
    col = _coleccion()
    if col is None:
        return None
    try:
        return col.find_one({"sha256": sha256}, {"_id": 0, "usuario": 1, "guardado_en": 1},
                            sort=[("guardado_en", DESCENDING)])
    except Exception:
        return None
