import hashlib
import streamlit as st
import bcrypt
from pymongo import MongoClient


@st.cache_resource
def _get_client():
    uri = st.secrets["mongodb"]["uri"].split("?")[0]
    return MongoClient(
        uri,
        tls=True,
        tlsAllowInvalidCertificates=False,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
        retryWrites=True,
        appName="ISMR",
    )


def _conectar_coleccion_usuarios():
    try:
        db_name = st.secrets["mongodb"].get("db_name", "ismr")
        db = _get_client()[db_name]
        coleccion = db["usuarios"]
        coleccion.create_index("username", unique=True, background=True)
        return coleccion
    except Exception as e:
        st.error(f"Error al conectar MongoDB (usuarios): {str(e)}")
        return None


def conectar_sheet_usuarios():
    return _conectar_coleccion_usuarios()


def obtener_usuario(username):
    coleccion = _conectar_coleccion_usuarios()
    if coleccion is None:
        return None
    try:
        doc = coleccion.find_one({"username": username}, {"_id": 0})
        if not doc:
            return None
        return _normalizar_usuario(doc)
    except Exception:
        return None


def hashear_password(password: str) -> str:
    """
    Genera un hash bcrypt de la contraseña.
    Retorna el hash como string (bcrypt ya incluye la sal internamente).
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verificar_password(password: str, hash_guardado: str) -> bool:
    """
    Verifica una contraseña contra su hash.
    Soporta tanto bcrypt (nuevo) como SHA-256 (legado) para migración automática.
    Retorna (es_valida, es_sha256_legado).
    """
    if hash_guardado.startswith("$2b$") or hash_guardado.startswith("$2a$"):
        try:
            es_valida = bcrypt.checkpw(password.encode(), hash_guardado.encode())
            return es_valida, False
        except Exception:
            return False, False
    else:
        sha_hash = hashlib.sha256(password.encode()).hexdigest()
        return sha_hash == hash_guardado, True


def actualizar_password(username, nuevo_hash, debe_cambiar=False):
    coleccion = _conectar_coleccion_usuarios()
    if coleccion is None:
        return False
    try:
        resultado = coleccion.update_one(
            {"username": username},
            {"$set": {
                "password_hash": nuevo_hash,
                "debe_cambiar_password": "FALSE"
            }}
        )
        return resultado.matched_count > 0
    except Exception as e:
        st.error(f"Error al actualizar contraseña: {str(e)}")
        return False


def _migrar_a_bcrypt(username: str, password: str) -> None:
    """
    Migra silenciosamente un hash SHA-256 a bcrypt al momento del login.
    """
    try:
        nuevo_hash = hashear_password(password)
        coleccion = _conectar_coleccion_usuarios()
        if coleccion:
            coleccion.update_one(
                {"username": username},
                {"$set": {"password_hash": nuevo_hash}}
            )
    except Exception:
        pass


def crear_usuario(username, password_plano, nombre_completo, es_admin=False, debe_cambiar=True, email=None):
    """
    Inserta un nuevo usuario hasheando la contraseña con bcrypt.
    """
    coleccion = _conectar_coleccion_usuarios()
    if coleccion is None:
        return False
    try:
        if obtener_usuario(username):
            return False
        email_final = email or f"{username.strip().lower()}@unp.gov.co"
        hash_bcrypt = hashear_password(password_plano)
        coleccion.insert_one({
            "username": username,
            "password_hash": hash_bcrypt,
            "nombre_completo": nombre_completo,
            "es_admin": "TRUE" if es_admin else "FALSE",
            "debe_cambiar_password": "TRUE" if debe_cambiar else "FALSE",
            "email": email_final,
        })
        return True
    except Exception as e:
        st.error(f"Error al crear usuario: {str(e)}")
        return False


def listar_usuarios():
    coleccion = _conectar_coleccion_usuarios()
    if coleccion is None:
        return []
    try:
        return [_normalizar_usuario(doc) for doc in coleccion.find({}, {"_id": 0})]
    except Exception:
        return []


def usuario_existe(username: str) -> bool:
    return obtener_usuario(username) is not None


def crear_usuarios_masivo(lista_usuarios, password_plano, es_admin=False):
    """
    Crea múltiples usuarios de una vez a partir de una lista de dicts:
      [{"nombre_completo": "Juan Pérez", "username": "juan.perez"}, ...]

    - Hashea la contraseña una sola vez y la reutiliza para todos.
    - Usa insert_many() para una sola llamada a MongoDB.
    - Omite usernames que ya existen (gracias al índice único).

    Retorna un dict con:
      - creados:  lista de usernames insertados
      - omitidos: lista de usernames que ya existían
      - errores:  lista de dicts {"username": ..., "error": ...}
    """
    coleccion = _conectar_coleccion_usuarios()
    if coleccion is None:
        return {"creados": [], "omitidos": [], "errores": [
            {"username": "—", "error": "No se pudo conectar a MongoDB"}
        ]}

    # Cargar usernames existentes de una sola vez
    try:
        existentes = {
            doc["username"]
            for doc in coleccion.find({}, {"username": 1, "_id": 0})
        }
    except Exception as e:
        return {"creados": [], "omitidos": [], "errores": [{"username": "—", "error": str(e)}]}

    # Hashear la contraseña una sola vez para todos
    hash_bcrypt = hashear_password(password_plano)

    documentos, creados, omitidos, errores = [], [], [], []
    usernames_en_lote = set()

    for usuario in lista_usuarios:
        username        = usuario.get("username", "").strip()
        nombre_completo = usuario.get("nombre_completo", "").strip()

        if not username or not nombre_completo:
            errores.append({"username": username or "(vacío)", "error": "Username o nombre vacío"})
            continue

        if username in existentes or username in usernames_en_lote:
            omitidos.append(username)
            continue

        documentos.append({
            "username":              username,
            "password_hash":         hash_bcrypt,
            "nombre_completo":       nombre_completo,
            "es_admin":              "TRUE" if es_admin else "FALSE",
            "debe_cambiar_password": "TRUE",
            "email":                 f"{username.lower()}@unp.gov.co",
        })
        usernames_en_lote.add(username)
        creados.append(username)

    # Insertar todos de una sola vez
    if documentos:
        try:
            coleccion.insert_many(documentos, ordered=False)
        except Exception as e:
            # insert_many con ordered=False inserta los que puede y reporta los que fallan
            errores.append({"username": "lote", "error": str(e)})

    return {"creados": creados, "omitidos": omitidos, "errores": errores}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalizar_usuario(doc):
    for campo in ("es_admin", "debe_cambiar_password"):
        valor = doc.get(campo, False)
        if isinstance(valor, bool):
            doc[campo] = "TRUE" if valor else "FALSE"
        elif isinstance(valor, str):
            doc[campo] = "TRUE" if valor.strip().upper() == "TRUE" else "FALSE"
        else:
            doc[campo] = "FALSE"
    if "email" not in doc or not doc["email"]:
        doc["email"] = f"{doc.get('username','').strip().lower()}@unp.gov.co"
    return doc
