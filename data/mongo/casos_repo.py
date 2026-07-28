import streamlit as st
from pymongo import MongoClient, ASCENDING

from configuration.settings import TAB_NOMBRES
from data.mongo.usuarios_repo import _get_client

# Cabeceras canónicas por colección — espejo de lo que crea Google Sheets
_CABECERAS_CASOS = [
    "ID_Caso", "Timestamp",
    "Tipo de Estudio", "OT-TE", "Fecha Expedicion OT",
    "Tipo de Evaluacion", "Tipo de Colectivo", "Tipo de Estructura", "Estructura Adscrita",
    "Cant Comunas", "Cant Locales", "Cant Municipales", "Cant Metropolitanas", "Cant Consejerias",
    "Tipo de Poblacion", "Subpoblacion",
    "Fecha de Nacimiento", "Sexo", "Género", "Orientación Sexual", "Jefatura del Hogar",
    "Zona Rural", "Zona de Reserva Campesina",
    "Departamento", "Municipio", "Solicitante",
    "Nivel de Riesgo", "Observaciones",
    "Num Personas Nucleo Familiar", "Companero Permanente",
    "Num Hijos Menores Edad", "Num Menores Otros", "Num Adultos Mayores", "Num Discapacidad",
    "Comp Nucleos Familiares", "Comp Num Personas", "Comp Menores Edad",
    "Comp Adultos Mayores", "Comp Discapacidad", "Comp Num Integrantes",
    "Tipo Division", "Comp Proyecto Productivo", "Comp Actividad Economica",
    "OSIEGD", "Factor Discapacidad", "Factor Etnia", "Factor Campesino",
    "Factor Cuidador", "Factor Victima Conflicto Armado", "Factor Lider Social DDHH",
    # Impacto Consecuencial - Esfera Económica
    "Imp Eco Dependencia Subsidio", "Imp Eco Perdida Iniciativas",
    "Imp Eco Acceso Empleos Formales", "Imp Eco Economia Ilicita",
    "Imp Eco Acceso Bienes",
    # Impacto Consecuencial - Esfera Social
    "Imp Soc Ruptura Tejido Social", "Imp Soc Perdida Redes Apoyo",
    "Imp Soc Traslado Violencia", "Imp Soc Confinamiento",
    "Imp Soc Restriccion Movilidad", "Imp Soc Desarraigo Cultural",
    "Imp Soc Normalizacion Violencia", "Imp Soc Libertad Seguridad",
    # Impacto Consecuencial - Esfera Político-Institucional
    "Imp Pol Restriccion Participacion", "Imp Pol Desarticulacion Liderazgos",
    "Imp Pol Oferta Institucional", "Imp Pol Derechos Politicos",
    "Imp Pol Estigmatizacion", "Imp Pol Confianza Instituciones",
    # Impacto Consecuencial - Esfera de la Salud y el Bienestar
    "Imp Sal Proyeccion Personal", "Imp Sal Cuidados Dependientes",
    "Imp Sal Desescolarizacion", "Imp Sal Abandono Menores",
    "Imp Sal Afectacion Psicosocial", "Imp Sal Discapacidad",
    "Imp Sal Dano Vida Integridad",
    "Analista", "Usuario Analista"
]
_CABECERAS_HECHOS = [
    "ID_Hecho", "ID_Caso", "OT-TE", "Tipo de Hecho",
    "Fecha del Hecho", "Departamento", "Municipio",
    "Tipo Actor Generador", "Actor Generador",
    "Medio Hecho", "Victima Situacion", "Tipo Amenaza",
    "Motivacion Amenaza", "Nexo Causal",
    "Descripcion",
    "Analista", "Usuario Analista"
]
_CABECERAS_ANTECEDENTES = [
    "ID_Antecedente", "ID_Caso", "OT-TE",
    "Registra OT Antecedentes",
    "OT-TE Antecede", "Tipo Ruta Antecedente", "Recomendacion Nivel Riesgo OT-TE Anterior",
    "Registra Resoluciones o Medidas Vigentes", "Numero Resolucion MTSP",
    "Dia Resolucion MTSP", "Mes Resolucion MTSP", "Anio Resolucion MTSP",
    "Analista", "Usuario Analista"
]
_CABECERAS_PERFILES = [
    "ID_Perfil", "ID_Caso", "OT-TE",
    "Modo de Participación", "Año Ingreso/Traslado/Captura", "Bloque de Operación",
    "Estructura", "Lugar de Acreditación", "Rol/Actividades",
    "Otro Rol", "Subpoblación Índice 1", "Meses Privado de Libertad",
    "Tipo Institución Penitenciaria", "Pabellón Alta Seguridad",
    "Analista", "Usuario Analista"
]
_CABECERAS_DESPLAZAMIENTOS = [
    "ID_Desplazamiento", "ID_Caso", "OT-TE",
    "Motivo Desplazamiento",
    "Medios de Transporte",
    "Departamento Origen", "Municipio Origen",
    "Departamento Destino", "Municipio Destino",
    "Frecuencia", "Tipo de Via",
    "Analista", "Usuario Analista"
]
_CABECERAS_VERIFICACIONES = [
    "ID_Verificacion", "ID_Caso", "OT-TE",
    "Fuente Verificacion", "Nombre Fuente",
    "V Hechos Riesgo", "V Lugar Hechos Riesgo", "V Actor Hechos Riesgo", "V Motivacion Amenaza",
    "V Perfil Antiguo", "V Modo Participacion", "V Rol Perfil Antiguo", "V Frente Columna",
    "V Perfil Actual", "V Organizacion", "V Rol Perfil Actual",
    "Criterios Verificacion",
    "Analista", "Usuario Analista"
]

_CABECERAS_PERFILES_ACTUALES = [
    "ID_Perfil_Actual", "ID_Caso", "OT-TE",
    "Familiar Parte Comunes",
    "Nivel Educativo", "Fuente Principal de Ingresos",
    "Estado Proyecto ARN", "Actividad Economica",
    "Comparecencia JEP", "Macrocasos JEP",
    "Victima JEP", "Macrocaso Victima",
    "Participacion TOAR", "Busqueda Desaparecidos",
    "Participacion PNIS", "Desminado",
    "Col JEP Comparecencia", "Col JEP Victima",
    "Col TOAR", "Col Busqueda Desaparecidos",
    "Col PNIS", "Col Desminado",
    "Participa Comunes", "Concejo Comunes",
    "Instancias Partido", "Roles Partido",
    "Consejeria Nacional", "Tipo Consejeria",
    "Participa Otras Org", "Tipo Org",
    "Nombre Org", "Ambito Org", "Escala Org",
    "Departamento Org", "Municipio Org", "Rol Org",
    "Anio Inicio Org", "Anio Fin Org",
    "Cargo Eleccion", "Col Cargo Eleccion Cnt",
    "Analista", "Usuario Analista"
]


_CABECERAS_INSTANCIAS_COMUNES = [
    "ID_Instancia_Comunes", "ID_Perfil_Actual", "ID_Caso", "OT-TE",
    "Instancias Partido",
    "Roles Partido",
    "Consejeria Nacional", "Tipo Consejeria",
    "Analista", "Usuario Analista"
]

_CABECERAS_OTRAS_ORGS = [
    "ID_Otra_Org", "ID_Perfil_Actual", "ID_Caso", "OT-TE",
    "Tipo Org", "Nombre Org",
    "Ambito Org", "Escala Org",
    "Departamento Org", "Municipio Org",
    "Rol Org",
    "Anio Inicio Org", "Anio Fin Org",
    "Num Personas Org",
    "Ambito Ambiental", "Ambito Campesino", "Ambito Comunal", "Ambito Comunicaciones",
    "Ambito DDHH", "Ambito Discapacidad", "Ambito Educativo", "Ambito Etnico",
    "Ambito Genero", "Ambito Juvenil", "Ambito Politico", "Ambito Reincorporacion",
    "Ambito Sector solidario", "Ambito Sindical", "Ambito Victimas", "Ambito Otros",
    "Analista", "Usuario Analista"
]


def _conectar_db():
    """Retorna la base de datos MongoDB usando el cliente singleton.
    Si la conexión falla, limpia el cache para forzar un nuevo cliente en el siguiente intento.
    """
    try:
        db_name = st.secrets["mongodb"].get("db_name", "ismr")
        client = _get_client()
        return client[db_name]
    except Exception as e:
        # Limpiar cache para que el siguiente intento cree un cliente fresco
        try:
            _get_client.clear()
        except Exception:
            pass
        st.error(f"Error al conectar MongoDB: {str(e)}")
        return None


# ── Borradores ────────────────────────────────────────────────────────────────

def _serializar(obj):
    """Convierte tipos no serializables por BSON (datetime.date, datetime.datetime) a string ISO."""
    import datetime
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serializar(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serializar(i) for i in obj]
    return obj


def guardar_borrador(username: str, tipo: str, datos: dict) -> bool:
    """
    Upsert de un borrador asociado a username + tipo de formulario.
    Sobreescribe el borrador anterior si existe.
    """
    db = _conectar_db()
    if db is None:
        return False
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        datos_serializados = _serializar(datos)
        datos_serializados["_guardado_en"] = datetime.now(tz=ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M:%S")
        db["borradores"].update_one(
            {"_username": username, "_tipo": tipo},
            {"$set": {**datos_serializados, "_username": username, "_tipo": tipo}},
            upsert=True,
        )
        return True
    except Exception as e:
        # Si falla la operación, el cliente podría tener conexión rota — limpiar cache
        try:
            _get_client.clear()
        except Exception:
            pass
        st.error(f"Error al guardar borrador: {str(e)}")
        return False


def cargar_borrador(username: str, tipo: str):
    """
    Devuelve el borrador del usuario para el tipo dado.
    - dict  → borrador encontrado
    - None  → no existe borrador (confirmado)
    - False → error de conexión/consulta (no se sabe si hay borrador)
    """
    db = _conectar_db()
    if db is None:
        return False
    try:
        doc = db["borradores"].find_one(
            {"_username": username, "_tipo": tipo}, {"_id": 0}
        )
        return doc or None
    except Exception as e:
        st.error(f"Error al cargar borrador: {str(e)}")
        return False


def eliminar_borrador(username: str, tipo: str) -> None:
    """
    Elimina el borrador del usuario tras un envío definitivo exitoso.
    """
    db = _conectar_db()
    if db is None:
        return
    try:
        db["borradores"].delete_one({"_username": username, "_tipo": tipo})
    except Exception as e:
        st.error(f"Error al eliminar borrador: {str(e)}")


@st.cache_resource
def _indices_inicializados():
    """Conjunto mutable compartido por todas las sesiones del mismo worker.
    Registra qué tipos ya tienen sus índices creados, para no repetirlos."""
    return set()


def _crear_indices(tipo: str, col_casos, col_hechos, col_perfiles, col_antecedentes,
                   col_perfiles_actuales, col_desplazamientos, col_verificaciones,
                   col_instancias_comunes, col_otras_orgs):
    """Crea los índices necesarios una sola vez por tipo y worker."""
    creados = _indices_inicializados()
    if tipo in creados:
        return
    col_casos.create_index([("OT-TE", ASCENDING)], unique=True, background=True)
    col_hechos.create_index([("ID_Caso", ASCENDING)], background=True)
    col_perfiles.create_index([("ID_Caso", ASCENDING)], background=True)
    col_antecedentes.create_index([("ID_Caso", ASCENDING)], background=True)
    col_perfiles_actuales.create_index([("ID_Caso", ASCENDING)], background=True)
    col_desplazamientos.create_index([("ID_Caso", ASCENDING)], background=True)
    col_verificaciones.create_index([("ID_Caso", ASCENDING)], background=True)
    col_instancias_comunes.create_index([("ID_Perfil_Actual", ASCENDING)], background=True)
    col_otras_orgs.create_index([("ID_Perfil_Actual", ASCENDING)], background=True)
    creados.add(tipo)


def conectar_sheet_casos(tipo="individual"):
    """
    Equivalente a conectar_sheet_casos() de Google Sheets.
    Retorna (proxy_casos, proxy_hechos, db_url) donde los proxies
    implementan la misma interfaz que un gspread Worksheet:
      - get_all_values() -> list[list]
      - get_all_records() -> list[dict]
      - append_row(values: list) -> None
      - append_many_rows(rows: list[list]) -> None
      - count() -> int
      - find_one_by(field, value) -> dict | None
    Crea índices la primera vez por tipo (cacheado por worker).
    """
    db = _conectar_db()
    if db is None:
        return None, None, None, None, None, None, None, None, None, None

    try:
        tab_casos              = TAB_NOMBRES[tipo]["casos"]
        tab_hechos             = TAB_NOMBRES[tipo]["hechos"]
        tab_perfiles           = TAB_NOMBRES[tipo]["perfiles"]
        tab_antecedentes       = TAB_NOMBRES[tipo]["antecedentes"]
        tab_perfiles_actuales  = TAB_NOMBRES[tipo]["perfiles_actuales"]
        tab_desplazamientos    = TAB_NOMBRES[tipo].get("desplazamientos", f"desplazamientos_{tipo}")
        tab_verificaciones     = TAB_NOMBRES[tipo]["verificaciones"]

        nombre_col_casos              = f"casos_{tab_casos.lower()}"
        nombre_col_hechos             = f"hechos_{tab_hechos.lower()}"
        nombre_col_perfiles           = f"perfiles_{tab_perfiles.lower()}"
        nombre_col_antecedentes       = f"antecedentes_{tab_antecedentes.lower()}"
        nombre_col_perfiles_actuales  = f"perfiles_actuales_{tab_perfiles_actuales.lower()}"
        nombre_col_desplazamientos    = f"desplazamientos_{tab_desplazamientos.lower()}"
        nombre_col_verificaciones     = f"verificaciones_{tab_verificaciones.lower()}"

        col_casos             = db[nombre_col_casos]
        col_hechos            = db[nombre_col_hechos]
        col_perfiles          = db[nombre_col_perfiles]
        col_antecedentes      = db[nombre_col_antecedentes]
        col_perfiles_actuales = db[nombre_col_perfiles_actuales]
        col_desplazamientos   = db[nombre_col_desplazamientos]
        col_verificaciones    = db[nombre_col_verificaciones]

        tab_instancias_comunes = TAB_NOMBRES[tipo].get("instancias_comunes", f"instancias_comunes_{tipo}")
        tab_otras_orgs         = TAB_NOMBRES[tipo].get("otras_orgs",         f"otras_orgs_{tipo}")

        nombre_col_instancias_comunes = f"instancias_comunes_{tab_instancias_comunes.lower()}"
        nombre_col_otras_orgs         = f"otras_orgs_{tab_otras_orgs.lower()}"

        col_instancias_comunes = db[nombre_col_instancias_comunes]
        col_otras_orgs         = db[nombre_col_otras_orgs]

        # Índices — solo la primera vez por tipo en este worker process
        _crear_indices(tipo, col_casos, col_hechos, col_perfiles, col_antecedentes,
                       col_perfiles_actuales, col_desplazamientos, col_verificaciones,
                       col_instancias_comunes, col_otras_orgs)

        proxy_casos               = WorksheetProxy(col_casos,               _CABECERAS_CASOS)
        proxy_hechos              = WorksheetProxy(col_hechos,              _CABECERAS_HECHOS)
        proxy_perfiles            = WorksheetProxy(col_perfiles,            _CABECERAS_PERFILES)
        proxy_antecedentes        = WorksheetProxy(col_antecedentes,        _CABECERAS_ANTECEDENTES)
        proxy_perfiles_actuales   = WorksheetProxy(col_perfiles_actuales,   _CABECERAS_PERFILES_ACTUALES)
        proxy_desplazamientos     = WorksheetProxy(col_desplazamientos,     _CABECERAS_DESPLAZAMIENTOS)
        proxy_verificaciones      = WorksheetProxy(col_verificaciones,      _CABECERAS_VERIFICACIONES)
        proxy_instancias_comunes  = WorksheetProxy(col_instancias_comunes,  _CABECERAS_INSTANCIAS_COMUNES)
        proxy_otras_orgs          = WorksheetProxy(col_otras_orgs,          _CABECERAS_OTRAS_ORGS)

        uri = st.secrets["mongodb"]["uri"]
        db_url = uri.split("@")[-1] if "@" in uri else uri  # oculta credenciales

        return (proxy_casos, proxy_hechos, proxy_perfiles, proxy_antecedentes,
                proxy_perfiles_actuales, proxy_desplazamientos, proxy_verificaciones,
                proxy_instancias_comunes, proxy_otras_orgs, db_url)
    except Exception as e:
        st.error(f"Error al conectar colecciones MongoDB ({tipo}): {str(e)}")
        return None, None, None, None, None, None, None, None, None, None


# ── Proxy de Worksheet ────────────────────────────────────────────────────────

class WorksheetProxy:
    """
    Emula la interfaz de gspread.Worksheet que usa la capa de servicio y UI:
      - get_all_values()  -> list[list]   (primera fila = cabeceras)
      - get_all_records() -> list[dict]
      - append_row(values: list) -> None

    Internamente mapea cada fila a un documento MongoDB usando las
    cabeceras como nombres de campo.
    """

    def __init__(self, coleccion, cabeceras: list):
        self._col = coleccion
        self._cabeceras = cabeceras

    # ── Lectura ───────────────────────────────────────────────────────────────

    def get_all_records(self) -> list:
        """
        Retorna todos los documentos como lista de dicts,
        con las mismas keys que cabeceras, sin el campo _id de MongoDB.
        """
        try:
            docs = list(self._col.find({}, {"_id": 0}))
            return [self._completar_cabeceras(d) for d in docs]
        except Exception as e:
            st.error(f"Error al leer registros: {str(e)}")
            return []

    def get_all_values(self) -> list:
        """
        Retorna los datos como lista de listas, incluyendo la fila de
        cabeceras como primera fila (igual que gspread).
        """
        records = self.get_all_records()
        if not records:
            return [self._cabeceras]
        filas = [self._cabeceras]
        for rec in records:
            filas.append([str(rec.get(c, "")) for c in self._cabeceras])
        return filas

    # ── Escritura ─────────────────────────────────────────────────────────────

    def append_row(self, values: list) -> None:
        """
        Inserta un documento mapeando la lista de valores a las cabeceras
        en el mismo orden que Google Sheets.
        """
        from pymongo.errors import DuplicateKeyError
        if len(values) != len(self._cabeceras):
            raise ValueError(
                f"Se esperaban {len(self._cabeceras)} valores, "
                f"se recibieron {len(values)}"
            )
        doc = dict(zip(self._cabeceras, values))
        try:
            self._col.insert_one(doc)
        except DuplicateKeyError:
            ot_val = doc.get("OT-TE", "")
            st.error(f"❌ El caso '{ot_val}' ya existe en la base de datos.")
        except Exception as e:
            st.error(f"Error al insertar registro: {str(e)}")

    def append_many_rows(self, rows: list) -> None:
        """Inserta múltiples filas en una sola operación bulk (insert_many)."""
        if not rows:
            return
        from pymongo.errors import BulkWriteError
        docs = []
        for values in rows:
            if len(values) != len(self._cabeceras):
                raise ValueError(
                    f"Se esperaban {len(self._cabeceras)} valores, "
                    f"se recibieron {len(values)}"
                )
            docs.append(dict(zip(self._cabeceras, values)))
        try:
            self._col.insert_many(docs, ordered=True)
        except BulkWriteError as bwe:
            st.error(f"Error en inserción masiva: {bwe.details}")
        except Exception as e:
            st.error(f"Error al insertar registros: {str(e)}")

    def count(self) -> int:
        """Retorna el número de documentos en la colección (O(1), sin descargar datos)."""
        try:
            return self._col.estimated_document_count()
        except Exception as e:
            st.error(f"Error al contar registros: {str(e)}")
            return 0

    def find_one_by(self, field: str, value) -> dict | None:
        """Busca un documento por campo/valor usando índice. Evita cargar toda la colección."""
        try:
            return self._col.find_one({field: value}, {"_id": 0})
        except Exception as e:
            st.error(f"Error al buscar registro: {str(e)}")
            return None

    # ── Helper ────────────────────────────────────────────────────────────────

    def _completar_cabeceras(self, doc: dict) -> dict:
        """Garantiza que el dict tenga todas las cabeceras esperadas."""
        return {c: doc.get(c, "") for c in self._cabeceras}
