"""
Utilidades de texto compartidas por lectores, mapeo y prellenado.

Toda comparación de etiquetas se hace sobre texto normalizado (sin tildes,
en minúsculas y con espacios colapsados) para tolerar las pequeñas
diferencias que aparecen entre la versión Word y la versión PDF del formato.
"""
import re
import unicodedata

# Símbolos que un analista usa para "marcar" una casilla
_MARCAS = "x✓✔☒☑■●"
RX_MARCA = re.compile(rf"^[{_MARCAS}]$")
_RX_MARCA_BORDE = re.compile(rf"^(?:[{_MARCAS}]\s+)?(.*?)(?:\s+[{_MARCAS}])?$", re.S)


def sin_tildes(texto: str) -> str:
    """Quita tildes conservando la longitud del texto (un carácter por carácter)."""
    return "".join(unicodedata.normalize("NFKD", ch)[0] if ch.strip() else ch for ch in texto)


def norm(texto) -> str:
    """Minúsculas, sin tildes y con espacios colapsados."""
    if texto is None:
        return ""
    t = sin_tildes(str(texto)).lower()
    return re.sub(r"\s+", " ", t).strip()


def limpiar(texto) -> str:
    """Texto de una sola línea: une saltos de línea y colapsa espacios.
    Une sin espacio las palabras cortadas con guion al final de línea (PDF)."""
    if not texto:
        return ""
    t = re.sub(r"-\s*\n\s*", "-", str(texto))
    return re.sub(r"\s+", " ", t).strip()


def limpiar_parrafos(texto) -> str:
    """Conserva los saltos de línea (texto libre largo) pero limpia cada línea."""
    if not texto:
        return ""
    lineas = [re.sub(r"[ \t]+", " ", l).strip() for l in str(texto).splitlines()]
    return "\n".join(l for l in lineas if l)


def es_marca(texto) -> bool:
    return bool(RX_MARCA.match(norm(texto)))


def separar_marca(texto) -> tuple[str, bool]:
    """'X GAO-R' -> ('gao-r', True). Devuelve el texto normalizado sin la marca."""
    n = norm(texto)
    m = _RX_MARCA_BORDE.match(n)
    resto = m.group(1) if m else n
    return resto, resto != n


def a_entero(texto):
    m = re.search(r"\d+", str(texto or ""))
    return int(m.group()) if m else None


def elegir_opcion(valor, opciones, reglas=None):
    """
    Busca en `opciones` (lista del formulario) la que corresponde a `valor`.
      1. Coincidencia exacta normalizada.
      2. `reglas`: lista de (regex_sobre_valor_normalizado, opcion).
      3. Única opción que contiene al valor como palabra completa (o viceversa).
    Devuelve la opción tal como está escrita en el formulario, o None.
    """
    v = norm(valor)
    if not v:
        return None
    validas = [o for o in opciones if o != "Seleccione..."]
    for o in validas:
        if norm(o) == v:
            return o
    for patron, opcion in (reglas or []):
        if re.search(patron, v) and opcion in validas:
            return opcion
    candidatas = [o for o in validas
                  if re.search(rf"\b{re.escape(v)}\b", norm(o)) or re.search(rf"\b{re.escape(norm(o))}\b", v)]
    return candidatas[0] if len(candidatas) == 1 else None
