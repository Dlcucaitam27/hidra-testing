"""
Extracción de datos del formato GESP-FT-14 (Word o PDF) a JSON.

Flujo:
    archivo (.docx | .pdf)
        └─ lectores.leer_documento()      -> estructura intermedia común (bloques)
            └─ mapeo_gesp_ft_14.mapear()  -> JSON según esquema.ESQUEMA
                └─ prellenado.construir_prellenado() -> valores para el formulario HIDRA

Uso típico:
    from service.extraccion_documentos import extraer_documento
    resultado = extraer_documento("evaluacion.pdf", contenido_bytes)
"""
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

from .esquema import FORMATO, VERSION_ESQUEMA, VERSION_FORMATO, validar
from .lectores import EXTENSIONES_SOPORTADAS, ErrorLectura, leer_documento
from .mapeo_gesp_ft_14 import mapear

__all__ = ["extraer_documento", "ErrorLectura", "EXTENSIONES_SOPORTADAS"]


def extraer_documento(nombre_archivo: str, contenido: bytes) -> dict:
    """
    Lee el archivo y devuelve el JSON del esquema con un bloque "_meta":
        _meta.advertencias -> problemas detectados (no bloquean)
    Lanza ErrorLectura si el archivo no se puede leer.
    """
    bloques = leer_documento(nombre_archivo, contenido)
    datos, advertencias = mapear(bloques)
    advertencias += validar(datos)
    datos["_meta"] = {
        "formato": FORMATO,
        "version_formato": VERSION_FORMATO,
        "version_esquema": VERSION_ESQUEMA,
        "archivo": nombre_archivo,
        "extension": nombre_archivo.rsplit(".", 1)[-1].lower(),
        "sha256": hashlib.sha256(contenido).hexdigest(),
        "extraido_en": datetime.now(tz=ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M:%S"),
        "advertencias": advertencias,
    }
    return datos
