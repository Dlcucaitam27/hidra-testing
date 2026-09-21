"""
Lectores de documentos: convierten un .docx o un .pdf en una ESTRUCTURA
INTERMEDIA COMÚN, independiente del formato de archivo.

La estructura intermedia es una lista de bloques en orden de lectura:

    {"tipo": "texto", "texto": "Sinopsis de la información:"}
    {"tipo": "fila",  "celdas": ["Primer Nombre", "PEDRO", ...],
                      "cajas": [(x0, x1), ...],  # extensión horizontal de cada celda
                      "tabla": 7}                # id de la tabla de origen

"cajas" está en puntos para PDF y en columnas de la cuadrícula para Word; solo
se compara dentro de una misma tabla, así que la unidad no importa.

El mapeo al JSON final (mapeo_gesp_ft_14.py) trabaja únicamente sobre esta
estructura, así que las diferencias entre Word y PDF quedan aisladas aquí.
No se usa OCR: ambos formatos traen capa de texto nativa.
"""
import io
import itertools
import re

from .texto import norm


class ErrorLectura(Exception):
    """El archivo no se pudo leer (dañado, protegido, formato no soportado)."""


EXTENSIONES_SOPORTADAS = (".docx", ".pdf")


def leer_documento(nombre_archivo: str, contenido: bytes) -> list[dict]:
    """Detecta la extensión y enruta al lector correspondiente."""
    ext = ("." + nombre_archivo.rsplit(".", 1)[-1].lower()) if "." in nombre_archivo else ""
    if ext == ".docx":
        return leer_docx(contenido)
    if ext == ".pdf":
        return leer_pdf(contenido)
    raise ErrorLectura(f"Extensión no soportada: '{ext or nombre_archivo}'. Use .docx o .pdf.")


# ══════════════════════════════════════════════════════════════════════════════
# WORD (.docx)
# ══════════════════════════════════════════════════════════════════════════════

def leer_docx(contenido: bytes) -> list[dict]:
    try:
        import docx
        from docx.oxml.ns import qn
    except ImportError as e:  # pragma: no cover
        raise ErrorLectura("Falta la librería 'python-docx' (pip install python-docx).") from e

    try:
        documento = docx.Document(io.BytesIO(contenido))
    except Exception as e:
        raise ErrorLectura(f"No se pudo abrir el archivo Word: {e}") from e

    W_P, W_TBL, W_TR, W_TC, W_SDT = qn("w:p"), qn("w:tbl"), qn("w:tr"), qn("w:tc"), qn("w:sdt")
    W_SDT_CONTENT, W_T, W_TAB, W_BR, W_SYM = (qn("w:sdtContent"), qn("w:t"), qn("w:tab"),
                                              qn("w:br"), qn("w:sym"))
    W_TCPR, W_VMERGE, W_VAL = qn("w:tcPr"), qn("w:vMerge"), qn("w:val")

    bloques: list[dict] = []
    ids_tabla = itertools.count()

    def texto_parrafo(p) -> str:
        partes = []
        for el in p.iter():
            if el.tag == W_T:
                partes.append(el.text or "")
            elif el.tag == W_TAB:
                partes.append(" ")
            elif el.tag == W_BR:
                partes.append("\n")
            elif el.tag == W_SYM:
                # Símbolo de fuente (Wingdings, etc.): en un formato casi siempre es una casilla marcada
                partes.append("☒")
        return "".join(partes)

    def hijos(el):
        """Hijos directos, desenvolviendo controles de contenido (w:sdt)."""
        for h in el.iterchildren():
            if h.tag == W_SDT:
                contenido_sdt = h.find(W_SDT_CONTENT)
                if contenido_sdt is not None:
                    yield from hijos(contenido_sdt)
            else:
                yield h

    def es_continuacion_vertical(tc) -> bool:
        tcpr = tc.find(W_TCPR)
        if tcpr is None:
            return False
        vm = tcpr.find(W_VMERGE)
        return vm is not None and vm.get(W_VAL) in (None, "continue")

    def texto_celda(tc) -> str:
        return "\n".join(texto_parrafo(p) for p in hijos(tc) if p.tag == W_P).strip()

    def recorrer_contenedor(el):
        for h in hijos(el):
            if h.tag == W_P:
                t = texto_parrafo(h).strip()
                if t:
                    bloques.append({"tipo": "texto", "texto": t})
            elif h.tag == W_TBL:
                recorrer_tabla(h)

    def recorrer_tabla(tbl):
        tid = next(ids_tabla)
        for tr in (h for h in hijos(tbl) if h.tag == W_TR):
            tcs = [h for h in hijos(tr) if h.tag == W_TC]
            if any(any(x.tag == W_TBL for x in hijos(tc)) for tc in tcs):
                # Celda contenedora: sus párrafos y tablas internas se emiten en orden
                for tc in tcs:
                    recorrer_contenedor(tc)
                continue
            celdas = ["" if es_continuacion_vertical(tc) else texto_celda(tc) for tc in tcs]
            # "Cajas" en unidades de columna de la cuadrícula, para alinear datos con encabezados
            cajas, col = [], _grid_before(tr)
            for tc in tcs:
                ancho = _grid_span(tc)
                cajas.append((col, col + ancho))
                col += ancho
            if any(celdas):
                bloques.append({"tipo": "fila", "celdas": celdas, "cajas": cajas, "tabla": tid})

    def _entero_attr(padre, *ruta):
        el = padre
        for tag in ruta:
            el = el.find(qn(tag)) if el is not None else None
        try:
            return int(el.get(W_VAL)) if el is not None else None
        except (TypeError, ValueError):
            return None

    def _grid_span(tc):
        return _entero_attr(tc, "w:tcPr", "w:gridSpan") or 1

    def _grid_before(tr):
        return _entero_attr(tr, "w:trPr", "w:gridBefore") or 0

    recorrer_contenedor(documento.element.body)
    return bloques


# ══════════════════════════════════════════════════════════════════════════════
# PDF
# ══════════════════════════════════════════════════════════════════════════════

# Encabezado y pie de página repetidos en cada hoja del formato: se descartan
_RX_ENCABEZADO = re.compile(
    r"^(evaluacion de riesgo .{0,3} ruta individual|para la mesa tecnica de seguridad"
    r"|gestion especializada de seguridad y proteccion|unidad nacional de proteccion|interior)"
)
_RX_PIE = re.compile(r"^(etiquetado:?.*|gesp-ft-\d+.*|oficializacion:.*|pagina \d+ de \d+"
                     r"|comentado \[.*)$")   # globos de comentarios si el PDF se exportó con marcas


def _es_contenedora(celda, centros) -> bool:
    """True si la celda abarca el centro de al menos otras dos celdas de la página."""
    x0, top, x1, bottom = celda
    propio = ((x0 + x1) / 2, (top + bottom) / 2)
    dentro = sum(1 for cx, cy in centros
                 if (cx, cy) != propio and x0 < cx < x1 and top < cy < bottom)
    return dentro >= 2


def leer_pdf(contenido: bytes) -> list[dict]:
    try:
        import pdfplumber
    except ImportError as e:  # pragma: no cover
        raise ErrorLectura("Falta la librería 'pdfplumber' (pip install pdfplumber).") from e

    bloques: list[dict] = []
    ids_tabla = itertools.count()
    try:
        pdf = pdfplumber.open(io.BytesIO(contenido))
    except Exception as e:
        raise ErrorLectura(f"No se pudo abrir el PDF: {e}") from e

    with pdf:
        hay_texto = False
        for pagina in pdf.pages:
            items = []           # (top, x0, bloque)
            ocupadas = []        # cajas de celdas ya emitidas como filas
            tablas = pagina.find_tables()
            # Centros de todas las celdas de la página, para detectar celdas "contenedoras"
            # (el recuadro de una sección que envuelve una tabla interna). pdfplumber a veces
            # las entrega como tabla aparte y a veces mezcladas en la misma tabla.
            centros = [((c[0] + c[2]) / 2, (c[1] + c[3]) / 2)
                       for t in tablas for f in t.rows for c in f.cells if c is not None]
            for tabla in tablas:
                tid = next(ids_tabla)
                for fila, textos in zip(tabla.rows, tabla.extract()):
                    # pdfplumber devuelve None en las posiciones cubiertas por celdas combinadas
                    pares = [(c, t) for c, t in zip(fila.cells, textos) if c is not None]
                    if not pares:
                        continue
                    # Las celdas contenedoras se vacían: su contenido ya sale de las filas
                    # internas, y su texto suelto se recupera abajo como bloques de texto
                    contenedoras = {id(c) for c, _ in pares if _es_contenedora(c, centros)}
                    pares = [(c, "" if id(c) in contenedoras else t) for c, t in pares]
                    celdas = [(t or "").strip() for _, t in pares]
                    no_vacias = [norm(t) for t in celdas if t.strip()]
                    ocupadas.extend(c for c, _ in pares if id(c) not in contenedoras)
                    if no_vacias and all(_RX_ENCABEZADO.match(t) for t in no_vacias):
                        continue
                    if no_vacias:
                        items.append((fila.bbox[1], fila.bbox[0], {
                            "tipo": "fila", "celdas": celdas,
                            "cajas": [(round(c[0], 1), round(c[2], 1)) for c, _ in pares],
                            "tabla": tid,
                        }))

            # Texto fuera de las celdas emitidas (párrafos dentro de cajas contenedoras)
            palabras = [w for w in pagina.extract_words(keep_blank_chars=False)
                        if not any(c[0] - 1 <= (w["x0"] + w["x1"]) / 2 <= c[2] + 1
                                   and c[1] - 1 <= (w["top"] + w["bottom"]) / 2 <= c[3] + 1
                                   for c in ocupadas)]
            for top, x0, linea in _agrupar_lineas(palabras):
                n = norm(linea)
                if _RX_PIE.match(n) or _RX_ENCABEZADO.match(n):
                    continue
                items.append((top, x0, {"tipo": "texto", "texto": linea}))

            items.sort(key=lambda it: (round(it[0]), it[1]))
            bloques.extend(b for _, _, b in items)
            hay_texto = hay_texto or bool(items)

    if not hay_texto:
        raise ErrorLectura("El PDF no tiene capa de texto (¿es un escaneo?). Este lector no aplica OCR.")
    return bloques


def _agrupar_lineas(palabras, tolerancia=3.0):
    """Agrupa palabras sueltas en líneas según su posición vertical."""
    lineas = []
    for w in sorted(palabras, key=lambda w: (w["top"], w["x0"])):
        if lineas and abs(lineas[-1]["top"] - w["top"]) <= tolerancia:
            lineas[-1]["palabras"].append(w)
        else:
            lineas.append({"top": w["top"], "palabras": [w]})
    salida = []
    for l in lineas:
        ws = sorted(l["palabras"], key=lambda w: w["x0"])
        salida.append((l["top"], ws[0]["x0"], " ".join(w["text"] for w in ws)))
    return salida
