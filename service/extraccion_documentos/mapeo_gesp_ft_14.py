"""
Mapeo de la estructura intermedia (ver lectores.py) al JSON del esquema
GESP-FT-14 V3 (ver esquema.py).

Principio: NO se usan posiciones fijas. Cada dato se localiza por su
ETIQUETA dentro de su SECCIÓN:
  * valor(etiqueta)        -> la siguiente celda con contenido a la derecha
  * marcada(etiqueta, lado)-> la casilla vecina (izq/der) contiene una X
  * tabla(columnas)        -> filas de datos alineadas con su encabezado
  * texto_despues(etiqueta)-> párrafos que siguen a una etiqueta
Así se toleran los cambios menores de maquetación entre Word y PDF.

Si el formato cambia de versión, normalmente basta con ajustar las etiquetas
de este archivo (y subir VERSION_ESQUEMA si cambia el JSON).
"""
import re
from datetime import date

from .esquema import documento_vacio
from .texto import es_marca, limpiar, limpiar_parrafos, norm, separar_marca, sin_tildes

# ── Registro de etiquetas conocidas ───────────────────────────────────────────
# Sirve para saber cuándo la "siguiente celda" es otra etiqueta y no un valor
# (campo vacío). Toda etiqueta usada en este módulo se registra con _E().
_ETIQUETAS: list[re.Pattern] = []


def _E(patron: str) -> re.Pattern:
    rx = re.compile(patron)
    _ETIQUETAS.append(rx)
    return rx


def _O(patron: str) -> re.Pattern:
    """Opción de casilla (SI, NO, GAO, Terceros...). NO se registra como etiqueta
    porque esos mismos textos son respuestas válidas en otros campos."""
    return re.compile(patron)


def _resto_tras_dos_puntos(original: str, t_norm: str, m: re.Match) -> str:
    """
    Si la celda es "Etiqueta: valor", devuelve "valor" (con tildes y mayúsculas
    originales). Exige los dos puntos para no confundir el final de una
    etiqueta larga ("...FARC-EP") con un valor.
    """
    plano = re.sub(r"\s+", " ", original).strip()
    if len(plano) != len(t_norm):     # la normalización no fue 1 a 1 (había una X, etc.)
        return ""
    resto = plano[m.end():]
    if t_norm[:m.end()].rstrip().endswith(":") or resto.lstrip().startswith(":"):
        return resto.strip(" :")
    return ""


def _es_etiqueta(t_norm: str) -> bool:
    for rx in _ETIQUETAS:
        m = rx.match(t_norm)
        if m and len(t_norm) - m.end() <= 3:
            return True
    return False


# ── Secciones del formato, en su orden habitual ───────────────────────────────
_SECCIONES = [
    ("informacion_general", _E(r"^(i\.\s*)?informacion general de la orden de trabajo")),
    ("datos_personales",    _E(r"^(ii\.\s*)?datos personales del evaluado")),
    ("solicitante",         _E(r"^informacion de(l)? solicitante$")),
    ("antecedentes",        _E(r"^antecedentes$")),
    ("perfil_antiguo",      _E(r"^perfil antiguo$")),
    ("perfil_actual",       _E(r"^perfil actual$")),
    ("hechos_riesgo",       _E(r"^hechos de riesgo$")),
    ("verificaciones",      _E(r"^verificaciones$")),
    ("vulnerabilidades",    _E(r"^vulnerabilidades y capacidades")),
    ("impacto",             _E(r"^impacto consecuencial$")),
    ("contexto",            _E(r"^contexto de orden publico$")),
    ("alertas",             _E(r"^alertas tempranas$")),
    ("medidas_emergencia",  _E(r"^medidas de emergencia$")),
    ("medidas_vigentes",    _E(r"^medidas de proteccion vigentes$")),
    ("nivel_riesgo",        _E(r"^nivel del riesgo$")),
    ("conclusion",          _E(r"^conclusion de la evaluacion del riesgo$")),
    ("modificaciones",      _E(r"^modificaciones solicitadas en premesa")),
    ("analista",            _E(r"^datos del servidor publico o contratista que realiza")),
    ("revision_calidad",    _E(r"^(xiv\.\s*)?informacion del servidor publico o contratista que revisa")),
    ("aval_calidad",        _E(r"^(xv\.\s*)?informacion del servidor publico o contratista que otorga")),
    ("anexos",              _E(r"^(xvi\.\s*)?anexos$")),
    ("documento_identidad", _E(r"^documento de identidad$")),
]
# A partir de aquí el formato trae el control de cambios y el instructivo: se ignora
_RX_FIN = _E(r"^(control de cambios|instrucciones de diligenciamiento|archivese en:?)$")


class _Documento:
    """Envoltura de la lista de bloques con las búsquedas por etiqueta."""

    def __init__(self, bloques: list[dict]):
        self.b = bloques
        # Por cada fila: [(texto_normalizado_sin_marca, tenia_marca), ...]
        self._cn = [
            [separar_marca(c) for c in bl["celdas"]] if bl["tipo"] == "fila" else None
            for bl in bloques
        ]
        self.fin = len(bloques)
        self.secciones = self._ubicar_secciones()

    # ── utilidades básicas ────────────────────────────────────────────────────
    def unico(self, i):
        """Texto normalizado si el bloque es un texto o una fila con una sola celda llena."""
        bl = self.b[i]
        if bl["tipo"] == "texto":
            return norm(bl["texto"])
        llenas = [t for t, _ in self._cn[i] if t]
        return llenas[0] if len(llenas) == 1 else None

    def titulo(self, i):
        """Como unico(), pero solo para bloques con forma de título: texto suelto o
        fila de una sola celda (PDF puede añadir una celda vacía de relleno).
        Evita confundir, p. ej., la fila 'Impacto consecuencial' de la tabla de
        categorías de una verificación con el título de la sección."""
        bl = self.b[i]
        if bl["tipo"] == "texto":
            return norm(bl["texto"])
        llenas = [t for t, _ in self._cn[i] if t]
        # En PDF un título largo puede quedar partido en dos celdas ("IMPACTO | CONSECUENCIAL")
        if len(bl["celdas"]) > 4 or not 1 <= len(llenas) <= 2:
            return None
        return " ".join(llenas)

    def _ubicar_secciones(self):
        inicios = {}
        ultima = -1   # las secciones deben aparecer en el orden del formato
        for i in range(len(self.b)):
            u = self.titulo(i)
            if u is None:
                continue
            if _RX_FIN.match(u):
                self.fin = i
                break
            for pos, (clave, rx) in enumerate(_SECCIONES):
                if pos > ultima and rx.match(u):
                    inicios[clave] = i
                    ultima = pos
                    break
        orden = sorted(inicios.items(), key=lambda kv: kv[1])
        rangos = {}
        for k, (clave, ini) in enumerate(orden):
            fin = orden[k + 1][1] if k + 1 < len(orden) else self.fin
            rangos[clave] = (ini + 1, fin)
        return rangos

    def rango(self, clave):
        return self.secciones.get(clave, (0, 0))

    def filas(self, rango):
        for i in range(*rango):
            if self.b[i]["tipo"] == "fila":
                yield i

    def buscar(self, rx, rango, desde_final=False):
        """Índices de bloques cuyo texto único coincide con rx."""
        idx = [i for i in range(*rango) if (u := self.unico(i)) is not None and rx.match(u)]
        return idx[::-1] if desde_final else idx

    def subrangos(self, rx_marcador, rango):
        """Divide `rango` en tramos que empiezan en cada bloque que coincide con rx."""
        marcas = self.buscar(rx_marcador, rango)
        return [(m, marcas[k + 1] if k + 1 < len(marcas) else rango[1]) for k, m in enumerate(marcas)]

    # ── búsquedas por etiqueta ────────────────────────────────────────────────
    def valor(self, rx, rango):
        """Valor asociado a una etiqueta. "" si la etiqueta existe pero está vacía."""
        for i in self.filas(rango):
            celdas, cn = self.b[i]["celdas"], self._cn[i]
            for j, (t, _) in enumerate(cn):
                m = rx.match(t)
                if not m:
                    continue
                # Valor escrito en la misma celda de la etiqueta ("Solicitante: ONG")
                resto = _resto_tras_dos_puntos(celdas[j], t, m)
                if resto:
                    return limpiar(resto)
                for k in range(j + 1, len(cn)):
                    tk = cn[k][0]
                    if not celdas[k].strip() or tk == t:
                        continue
                    return "" if _es_etiqueta(tk) else limpiar(celdas[k])
                return ""
        # Respaldo: la etiqueta quedó como texto suelto "Etiqueta: valor"
        for i in range(*rango):
            if self.b[i]["tipo"] != "texto":
                continue
            t = norm(self.b[i]["texto"])
            m = rx.match(t)
            if m:
                return limpiar(_resto_tras_dos_puntos(self.b[i]["texto"], t, m))
        return None

    def marcada(self, rx, rango, lado):
        """
        ¿La casilla junto a la etiqueta tiene una X? `lado` = "izq" | "der"
        indica de qué lado de la etiqueta está la casilla en el formato.
        True / False, o None si la etiqueta no aparece.
        """
        encontrada = False
        for i in self.filas(rango):
            celdas, cn = self.b[i]["celdas"], self._cn[i]
            for j, (t, tenia_marca) in enumerate(cn):
                if not rx.match(t):
                    continue
                encontrada = True
                if tenia_marca:
                    return True
                pasos = range(j - 1, -1, -1) if lado == "izq" else range(j + 1, len(cn))
                for k in pasos:
                    if not celdas[k].strip():
                        continue
                    if es_marca(celdas[k]):
                        return True
                    break
        return False if encontrada else None

    def marcadas(self, opciones, rango, lado):
        """Lista de nombres de opciones marcadas. `opciones` = [(nombre, rx), ...]."""
        return [nombre for nombre, rx in opciones if self.marcada(rx, rango, lado)]

    def texto_despues(self, rx, rango, ultima=False):
        """Texto libre que sigue a una etiqueta (misma fila y bloques siguientes)."""
        for i in self.buscar_etiqueta(rx, rango, ultima):
            partes = []
            if self.b[i]["tipo"] == "fila":
                cn = self._cn[i]
                j = next(j for j, (t, _) in enumerate(cn) if rx.match(t))
                partes += [c for c in self.b[i]["celdas"][j + 1:] if c.strip()]
            else:
                plano = re.sub(r"\s+", " ", self.b[i]["texto"]).strip()
                m = rx.match(sin_tildes(plano).lower())
                if m and plano[m.end():].strip(" :"):
                    partes.append(plano[m.end():].strip(" :"))
            for k in range(i + 1, rango[1]):
                bl = self.b[k]
                u = self.unico(k)
                if bl["tipo"] == "fila":
                    llenas = [c for c in bl["celdas"] if c.strip()]
                    if len(llenas) != 1 or (u and _es_etiqueta(u)):
                        break
                    partes.append(llenas[0])
                else:
                    if u and _es_etiqueta(u):
                        break
                    partes.append(bl["texto"])
            return limpiar_parrafos("\n".join(partes))
        return ""

    def buscar_etiqueta(self, rx, rango, ultima=False):
        idx = []
        for i in range(*rango):
            if self.b[i]["tipo"] == "fila":
                if any(rx.match(t) for t, _ in self._cn[i]):
                    idx.append(i)
            elif rx.match(norm(self.b[i]["texto"])):
                idx.append(i)
        return idx[::-1] if ultima else idx

    def texto_seccion(self, clave):
        """Todo el texto de una sección de texto libre, sin etiquetas del formato."""
        partes = []
        for i in range(*self.rango(clave)):
            bl = self.b[i]
            textos = bl["celdas"] if bl["tipo"] == "fila" else [bl["texto"]]
            for t in textos:
                if t.strip() and not _es_etiqueta(norm(t)):
                    partes.append(t)
        return limpiar_parrafos("\n".join(partes))

    # ── tablas con encabezado ─────────────────────────────────────────────────
    def tabla(self, columnas, rango, hasta=None, columna_numero=None):
        """
        Registros de una tabla. `columnas` = [(clave, "texto completo del encabezado"), ...]
        La primera columna es el ancla para ubicar la fila de encabezado.
        Los datos se asignan a cada columna por posición horizontal (cajas).
        """
        encabezados = [(clave, norm(txt)) for clave, txt in columnas]
        palabras_enc = set(" ".join(t for _, t in encabezados).split())

        def columna_de(t):
            if len(t) < 2:
                return None
            for clave, enc in encabezados:
                if enc.startswith(t) or t.startswith(enc):
                    return clave
            return None

        for i in self.filas(rango):
            cn = self._cn[i]
            asignadas = {columna_de(t) for t, _ in cn} - {None}
            if encabezados[0][0] not in asignadas or len(asignadas) < min(2, len(encabezados)):
                continue
            # Encabezado encontrado: rangos horizontales por columna
            tabla_id = self.b[i]["tabla"]
            rangos_x = {}
            filas_enc = [i]
            siguientes = [k for k in self.filas((i + 1, rango[1])) if self.b[k]["tabla"] == tabla_id]
            for k in siguientes[:2]:
                llenas = [t for t, _ in self._cn[k] if t]
                if llenas and all(set(t.split()) <= palabras_enc and len(t) > 2 for t in llenas):
                    filas_enc.append(k)
                else:
                    break
            for k in filas_enc:
                for (t, _), caja in zip(self._cn[k], self.b[k]["cajas"] or []):
                    col = columna_de(t)
                    if col:
                        x0, x1 = rangos_x.get(col, caja)
                        rangos_x[col] = (min(x0, caja[0]), max(x1, caja[1]))
            registros = []
            for k in siguientes[len(filas_enc) - 1:]:
                cn_k = self._cn[k]
                if hasta and any(hasta.match(t) for t, _ in cn_k):
                    break
                reg = {clave: [] for clave, _ in columnas}
                for celda, caja in zip(self.b[k]["celdas"], self.b[k]["cajas"] or []):
                    if not celda.strip():
                        continue
                    centro = (caja[0] + caja[1]) / 2
                    col = next((c for c, (x0, x1) in rangos_x.items() if x0 <= centro <= x1), None)
                    if col is None and rangos_x:
                        col = min(rangos_x, key=lambda c: abs((rangos_x[c][0] + rangos_x[c][1]) / 2 - centro))
                    if col:
                        reg[col].append(limpiar(celda))
                reg = {c: " ".join(v) for c, v in reg.items()}
                if any(v for c, v in reg.items() if c != columna_numero):
                    registros.append(reg)
            return registros
        return []

    def alinear_con(self, i_enc, i_fila):
        """Asigna cada celda de la fila i_fila a la celda del encabezado i_enc (por cajas)."""
        enc = [(t, caja) for (t, _), caja in zip(self._cn[i_enc], self.b[i_enc]["cajas"] or []) if t]
        salida = [[] for _ in enc]
        for celda, caja in zip(self.b[i_fila]["celdas"], self.b[i_fila]["cajas"] or []):
            if not celda.strip() or not enc:
                continue
            centro = (caja[0] + caja[1]) / 2
            dentro = [n for n, (_, c) in enumerate(enc) if c[0] <= centro <= c[1]]
            n = dentro[0] if dentro else min(range(len(enc)),
                                             key=lambda n: abs((enc[n][1][0] + enc[n][1][1]) / 2 - centro))
            salida[n].append(celda)
        return [(t, " ".join(v)) for (t, _), v in zip(enc, salida)]


# ══════════════════════════════════════════════════════════════════════════════
# Etiquetas por sección
# ══════════════════════════════════════════════════════════════════════════════

_TIPOS_EVALUACION = [
    ("EVALUACIÓN POR PRIMERA VEZ", _E(r"^evaluacion de riesgo por primera vez")),
    ("REEVALUACIÓN POR HECHOS SOBREVINIENTES", _E(r"^reevaluacion de nivel del riesgo por hechos")),
    ("REEVALUACIÓN POR TEMPORALIDAD", _E(r"^reevaluacion de nivel del riesgo por temporalidad")),
]
_RX_N_OT = _E(r"^n\W{0,2}\s*de ot\b")
_RX_DD, _RX_MM, _RX_AAAA = _E(r"^dd$"), _E(r"^mm$"), _E(r"^aaaa$")
_E(r"^asignacion de la orden de trabajo$"); _E(r"^remision a calidad$"); _E(r"^fecha$")
_E(r"^tipo de evaluacion de riesgo$")

_RX_CEDULA = _E(r"^cedula de ciudadania$")
_RX_OTRO = _O(r"^otro$")
_RX_CUAL = _E(r"^¿?cual\s*\?$")
_DATOS_PERSONALES = {
    "numero_identificacion": _E(r"^numero de identificacion"),
    "primer_nombre": _E(r"^primer nombre$"),
    "segundo_nombre": _E(r"^segundo nombre$"),
    "primer_apellido": _E(r"^primer apellido$"),
    "segundo_apellido": _E(r"^segundo apellido$"),
    "enfoque_diferencial": _E(r"^enfoque diferencial e interseccionalidad"),
}

_SOLICITANTE = {
    "fecha_solicitud": _E(r"^fecha de solicitud:?"),
    "solicitante": _E(r"^solicitante:?"),
    "tipo_evaluacion": _E(r"^tipo de evaluacion de riesgo:"),
}
_RX_SINOPSIS_INFO = _E(r"^sinopsis de la informacion:?$")

_COLS_ANTECEDENTES = [
    ("ot", "OT"), ("tramite_emergencia", "Tramite de Emergencia"), ("tipo_estudio", "Tipo de estudio"),
    ("nivel_riesgo", "Nivel de riesgo"), ("recomendacion_medidas", "Recomendación de medidas"),
    ("resumen", "Resumen"), ("resolucion", "Resolución"),
]

_RX_BLOQUE_FAMILIAR = _E(r"^en caso de ser familiar de una persona en proceso")
_RX_BLOQUE_PPR = _E(r"^perfil persona en proceso de reincorporacion")
_RX_BLOQUE_PRIVADO = _E(r"^en caso de ser indultado o privado de la libertad")
_FAMILIAR_PPR = {
    "nombre": _E(r"^nombre del familiar ppr"),
    "tipo_vinculo": _E(r"^tipo vinculo familiar"),
}
_PERSONA_PPR = {
    "fecha_ingreso_farc": _E(r"^fecha de ingreso a las antiguas farc"),
    "zona_operacion": _E(r"^zona de operacion"),
    "columna_frente_movil": _E(r"^columna, frente, movil"),
    "bloque": _E(r"^bloque donde estuvo"),
    "nombre_mando": _E(r"^nombre del mando"),
    "seudonimo": _E(r"^seudonimo"),
    "rol": _E(r"^rol$"),
    "actividad": _E(r"^actividad$"),
}
_COLS_PRIVACION = [
    ("establecimiento", "Nombre establecimiento de reclusión"),
    ("ubicacion", "Ubicación establecimiento de reclusión (Departamento, municipio)"),
    ("anio_captura", "Año captura"), ("anio_libertad", "Año libertad o traslado"),
]
_RX_DELITOS = _E(r"^delitos por los que fue procesado")
_COLS_DELITOS = [("delito", "Delitos por los que fue procesado"),
                 ("actividad", "Actividades humanitarias y/o políticas llevadas a cabo durante el tiempo de reclusión")]
_E(r"^actividades humanitarias y/o politicas")

_DEMOGRAFIA = {
    "edad_actual": _E(r"^edad actual"),
    "departamento_residencia": _E(r"^departamento de residencia"),
    "municipio_residencia": _E(r"^municipio de residencia"),
    "zona_rural_urbana": _E(r"^¿?vive en zona rural o urbana"),
    "zona_reserva_campesina": _E(r"^¿?vive en zona de reserva campesina"),
    "resguardo_indigena": _E(r"^¿?pertenece a un resguardo indigena"),
    "nivel_escolaridad": _E(r"^nivel de escolaridad"),
}
_E(r"^informacion demografica$")
_COLS_ENFOQUE = [("enfoque", "Enfoque Diferencial"), ("descripcion", "Breve descripción")]
_COLS_FAMILIA = [("n", "N°"), ("nombres", "Nombres completos"), ("edad", "Edad"),
                 ("vinculo", "Vínculo familiar"), ("lugar_residencia", "Lugar de residencia")]
_E(r"^grupo familiar del evaluado"); _E(r"^en caso de ser persona en proceso de reincorporacion diligencie")
_ECONOMICAS = {
    "fuente_ingresos": _E(r"^fuentes? principal(es)? de ingresos"),
    "empleado": _E(r"^¿?se encuentra empleado"),
    "persona_proteccion": _E(r"^¿?es persona de proteccion"),
    "proyecto_productivo_arn": _E(r"^nombre del proyecto productivo"),
    "proyecto_activo": _E(r"^¿?el proyecto productivo se encuentra activo"),
    "motivo_no_activo": _E(r"^en caso de no estar activo"),
    "actividad_economica_proyecto": _E(r"^¿?cual es la actividad economica del proyecto"),
    "proyecto_colectivo_individual": _E(r"^¿?el proyecto productivo es colectivo o individual"),
    "vinculado_org_gremial": _E(r"^¿?el proyecto productivo esta vinculado"),
    "nombre_org_gremial": _E(r"^nombre de la organizacion gremial"),
    "reside_lugar_proyecto": _E(r"^¿?reside en el mismo lugar"),
}
_E(r"^actividades economicas$"); _E(r"^actividades politicas y sociales$")
_POLITICAS = {
    "participa_toar_ubpd_desminado_pnis": _E(r"^¿?participa en toar"),
    "cual": _RX_CUAL,
    "comparece_jep": _E(r"^¿?comparece ante la jurisdiccion especial"),
    "victima_jep": _E(r"^¿?es victima ante la jep"),
    "macrocaso_jep": _E(r"^en caso de ser compareciente o victima"),
    "pertenece_organizacion": _E(r"^¿?pertenece a alguna organizacion social"),
    "nombre_colectividad": _E(r"^nombre de la colectividad"),
    "naturaleza_colectividad": _E(r"^naturaleza de la colectividad"),
    "rol_colectividad": _E(r"^rol que ocupa dentro de la colectividad"),
    "actividades_colectividad": _E(r"^actividades que realiza en funcion"),
    "escala_actividades": _E(r"^realiza sus actividades en una escala"),
    "cargo_eleccion_popular": _E(r"^¿?ejerce un cargo de eleccion popular"),
    "cargo_eleccion_cual": _E(r"^en caso de haber respondido afirmativamente"),
}
_E(r"^tipo de comparecencia$")
_COMPARECENCIA = [("MÁXIMO RESPONSABLE", _O(r"^maximo responsable$")),
                  ("FORZOSO", _O(r"^forzoso$")), ("VOLUNTARIO", _O(r"^voluntario$"))]
_E(r"^desplazamientos$")
_COLS_DESPLAZAMIENTOS = [
    ("origen", "Origen"), ("destino", "Destino"), ("tipo_estado_via", "Tipo y estado de la vía"),
    ("medio_transporte", "Tipo de medio de transporte"), ("horarios", "Horarios"),
    ("frecuencia", "Frecuencia"), ("motivo", "Motivo Desplazamiento"),
]

_RX_HECHO_N = _E(r"^hecho de riesgo\s*(?:#|no\.?|n°|numero)?\s*(\d+)")
_RX_OBSERVACIONES = _E(r"^obse?r?vaciones:?")
_E(r"^\*?agregar la cantidad de hechos de riesgo")
_HECHO = {
    "dia": _E(r"^dia$"), "mes": _E(r"^mes$"), "anio": _E(r"^ano$"),
    "departamento": _E(r"^departamento$"), "municipio": _E(r"^municipio$"),
    # Aceptan la etiqueta completa o cortada por un salto de página en el PDF
    # ("NOMBRE DEL ACTOR" | "... GENERADOR DEL HECHOS DE RIESGO")
    "nombre_actor": _E(r"^nombre del actor( generador( del hechos?( de riesgo)?)?)?$"),
    "victima": _E(r"^victima del( hecho( de( riesgo)?)?)?$"),
    "medio": _E(r"^medio hecho( de( riesgo)?)?$"),
    "motivacion": _E(r"^motivacion del( hecho( de( riesgo)?)?)?$"),
    "relato": _E(r"^relato abierto( del( hecho( de( riesgo)?)?)?)?$"),
}
_E(r"^lugar$"); _E(r"^tipo de actor generador"); _E(r"^tipo de hecho de riesgo$")
_E(r"^identifica nexo causal")
_TIPOS_ACTOR = [
    ("GAO", _O(r"^gao$")), ("GAO-R", _O(r"^gao\s*-?\s*r$")), ("GDO", _O(r"^gdo$")),
    ("GDCO", _O(r"^gdco$")), ("TERCERO / CIVIL", _O(r"^tercero\s*/?\s*/?\s*civil$")),
    ("INSTITUCIÓN DEL ESTADO COLOMBIANO", _O(r"^institucion del estado colombiano$")),
    ("OTRO", _RX_OTRO), ("NO REPORTA", _O(r"^no reporta$")),
]
_TIPOS_HECHO = [("DIRECTA", _O(r"^directa$")), ("POTENCIAL", _O(r"^potencial$")),
                ("DAÑO CONSUMADO", _O(r"^dano\s*/?\s*consumado$"))]
_RX_SI, _RX_NO = _O(r"^si$"), _O(r"^no$")

_RX_VERIFICACION_N = _E(r"^verificacion\s*(?:#|no\.?|n°|numero)?\s*(\d+)")
_FUENTES = [
    ("TERCEROS", _O(r"^terceros$")), ("ONG", _O(r"^ong$")),
    ("INSTITUCIÓN DEL ESTADO COLOMBIANO", _O(r"^institucion del estado colombiano$")),
    ("ORGANIZACIÓN INTERNACIONAL", _O(r"^organizacion internacional$")),
    ("NO REPORTA", _O(r"^no reporta$")),
]
_RX_NOMBRE_FUENTE = _E(r"^nombre de la fuente")
_RX_SINOPSIS_VER = _E(r"^sinopsis de la verificacion")
_E(r"^fuentes de verificacion$"); _E(r"^categorias para evaluar la informacion.*")
for _p in (r"^vector$",
           r"^perfil antiguo$", r"^perfil actual$", r"^hechos de riesgo$", r"^vulnerabilidad$",
           r"^capacidad$", r"^impacto consecuencial$", r"^contexto territorial$"):
    _E(_p)

_ESFERAS = {
    "economica": _E(r"^impacto en la esfera economica"),
    "social": _E(r"^impacto en la esfera social"),
    "politico_institucional": _E(r"^impacto en la esfera politico"),
    "salud_bienestar": _E(r"^impacto en la esfera de la salud"),
}
# clave del ítem -> etiqueta. Las claves coinciden con el sufijo de los campos
# imp_* del formulario (ver prellenado.py).
_ITEMS_IMPACTO = {
    "economica": {
        "dependencia": _O(r"^dependencia de subsidios"),
        "iniciativas": _O(r"^perdida de iniciativas productivas"),
        "despojo_tierras": _O(r"^despojo o abandono de tierras"),
        "empleos": _O(r"^acceso restringido a empleos formales"),
        "ilicita": _O(r"^insercion en procesos de economias ilicitas"),
        "bienes": _O(r"^dificultad en el acceso a servicios y bienes"),
    },
    "social": {
        "tejido": _O(r"^ruptura del tejido social"),
        "redes": _O(r"^perdida de redes de apoyo"),
        "traslado": _O(r"^traslado de factores de violencia"),
        "confinamiento": _O(r"^confinamiento o auto ?confinamiento"),
        "movilidad": _O(r"^restriccion de movilidad"),
        "desarraigo": _O(r"^desarraigo territorial"),
        "normalizacion": _O(r"^normalizacion de la violencia"),
        "libertad": _O(r"^afectacion al goce al? derecho de la libertad"),
    },
    "politico_institucional": {
        "participacion": _O(r"^restriccion en la participacion politica"),
        "liderazgos": _O(r"^desarticulacion en los liderazgos"),
        "oferta": _O(r"^exposicion por falencias"),
        "derechos": _O(r"^afectacion en el goce de sus derechos politicos"),
        "estigmatizacion": _O(r"^estigmatizacion$"),
        "confianza": _O(r"^perdida de confianza en las instituciones"),
    },
    "salud_bienestar": {
        "proyeccion": _O(r"^afectacion a la proyeccion personal"),
        "cuidados": _O(r"^imposibilidad de atender los cuidados"),
        "desescolarizacion": _O(r"^desescolarizacion$"),
        "abandono": _O(r"^procesos de abandono a menores"),
        "psicosocial": _O(r"^afectacion psicosocial$"),
        "discapacidad": _O(r"^discapacidad$"),
        "dano_vida": _O(r"^dano irreparable a la vida"),
    },
}
_RX_DESCRIPCION = _E(r"^descripcion$")
_RX_OTRO_CUAL = _E(r"^otro,?\s*¿?cual\??$")
_RX_SINOPSIS = _E(r"^sinopsis$")

_ANALISTA = {
    "nombres_apellidos": _E(r"^nombres y apellidos$"),
    "documento": _E(r"^documento de identidad"),
    "cargo": _E(r"^cargo o rol$"),
    "correo": _E(r"^correo electronico institucional$"),
}
_E(r"^firma del analista:?$")

# Textos guía propios del formato que no son datos
for _p in (r"^insertar imagen\.?$", r"^(\d\.)$"):
    _E(_p)


# ══════════════════════════════════════════════════════════════════════════════
# Mapeo principal
# ══════════════════════════════════════════════════════════════════════════════

def _valores(doc, etiquetas: dict, rango, destino: dict):
    for campo, rx in etiquetas.items():
        v = doc.valor(rx, rango)
        if v:
            destino[campo] = v


_MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], start=1)}
_MESES["setiembre"] = 9


def fecha_iso(dia, mes, anio):
    """Arma una fecha ISO a partir de sus partes; None si no es una fecha válida."""
    try:
        d, m, a = int(dia), int(mes), int(anio)
        if a < 100:
            a += 2000
        return date(a, m, d).isoformat()
    except (TypeError, ValueError):
        return None


def parsear_fecha(texto):
    """'10/01/2026', '10-01-2026', '2026-01-10', '10 de enero de 2026' -> '2026-01-10'."""
    t = norm(texto)
    if not t:
        return None
    m = re.search(r"\b(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})\b", t)
    if m:
        return fecha_iso(m.group(3), m.group(2), m.group(1))
    m = re.search(r"\b(\d{1,2})[/.\- ]+(\d{1,2})[/.\- ]+(\d{2,4})\b", t)
    if m:
        return fecha_iso(m.group(1), m.group(2), m.group(3))
    m = re.search(r"\b(\d{1,2})\s*(?:de\s+)?([a-z]+)\s*(?:de\s+|del\s+)?(\d{4})\b", t)
    if m and m.group(2) in _MESES:
        return fecha_iso(m.group(1), _MESES[m.group(2)], m.group(3))
    return None


def mapear(bloques: list[dict]) -> tuple[dict, list[str]]:
    """Convierte la estructura intermedia en el JSON del esquema. Devuelve (json, advertencias)."""
    doc = _Documento(bloques)
    r = documento_vacio()
    adv = []

    faltantes = [c for c, _ in _SECCIONES[:17] if c not in doc.secciones]
    if len(faltantes) > 12:
        adv.append("El documento no parece ser el formato GESP-FT-14: casi ninguna sección fue reconocida.")
    elif faltantes:
        adv.append("Secciones no encontradas: " + ", ".join(faltantes))

    # ── I. Información general ────────────────────────────────────────────────
    rg = doc.rango("informacion_general")
    ig = r["informacion_general"]
    ig["numero_ot"] = doc.valor(_RX_N_OT, rg) or ""
    tipos = doc.marcadas(_TIPOS_EVALUACION, rg, "izq")
    if len(tipos) == 1:
        ig["tipo_evaluacion"] = tipos[0]
    elif len(tipos) > 1:
        adv.append("Tipo de evaluación: hay más de una casilla marcada.")
    fechas = _fechas_dd_mm_aaaa(doc, rg)
    if fechas:
        ig["fecha_asignacion_ot"] = fechas[0]
        if len(fechas) > 1:
            ig["fecha_remision_calidad"] = fechas[1]

    # ── II. Datos personales ──────────────────────────────────────────────────
    rg = doc.rango("datos_personales")
    dp = r["datos_personales"]
    cc, otro = doc.marcada(_RX_CEDULA, rg, "der"), doc.marcada(_RX_OTRO, rg, "der")
    dp["tipo_documento"] = "CÉDULA DE CIUDADANÍA" if cc else ("OTRO" if otro else "")
    dp["tipo_documento_cual"] = doc.valor(_RX_CUAL, rg) or ""
    _valores(doc, _DATOS_PERSONALES, rg, dp)

    # ── Solicitante ───────────────────────────────────────────────────────────
    rg = doc.rango("solicitante")
    so = r["solicitante"]
    so["fecha_solicitud"] = parsear_fecha(doc.valor(_SOLICITANTE["fecha_solicitud"], rg))
    so["solicitante"] = doc.valor(_SOLICITANTE["solicitante"], rg) or ""
    so["tipo_evaluacion"] = doc.valor(_SOLICITANTE["tipo_evaluacion"], rg) or ""
    so["sinopsis"] = doc.texto_despues(_RX_SINOPSIS_INFO, rg)

    # ── Antecedentes ──────────────────────────────────────────────────────────
    rg = doc.rango("antecedentes")
    r["antecedentes"]["registros"] = doc.tabla(_COLS_ANTECEDENTES, rg)
    r["antecedentes"]["sinopsis"] = doc.texto_despues(_RX_SINOPSIS_INFO, rg)

    # ── Perfil antiguo ────────────────────────────────────────────────────────
    rg = doc.rango("perfil_antiguo")
    pa = r["perfil_antiguo"]
    sub = {rx.pattern: s for rx in (_RX_BLOQUE_FAMILIAR, _RX_BLOQUE_PPR, _RX_BLOQUE_PRIVADO)
           for s in doc.subrangos(rx, rg)[:1]}
    r_fam = sub.get(_RX_BLOQUE_FAMILIAR.pattern, rg)
    r_ppr = sub.get(_RX_BLOQUE_PPR.pattern, rg)
    r_priv = sub.get(_RX_BLOQUE_PRIVADO.pattern, rg)
    # Los subrangos se solapan con el siguiente bloque: se recortan en el orden del formato
    if _RX_BLOQUE_PPR.pattern in sub:
        r_fam = (r_fam[0], min(r_fam[1], r_ppr[0]))
    if _RX_BLOQUE_PRIVADO.pattern in sub:
        r_ppr = (r_ppr[0], min(r_ppr[1], r_priv[0]))
    _valores(doc, _FAMILIAR_PPR, r_fam, pa["familiar_ppr"])
    pa["familiar_ppr"]["sinopsis"] = doc.texto_despues(_RX_SINOPSIS_INFO, r_fam)
    _valores(doc, _PERSONA_PPR, r_ppr, pa["persona_reincorporacion"])
    pa["privacion_libertad"] = doc.tabla(_COLS_PRIVACION, r_priv, hasta=_RX_DELITOS)
    pa["delitos_y_actividades"] = doc.tabla(_COLS_DELITOS, r_priv)
    pa["sinopsis"] = doc.texto_despues(_RX_SINOPSIS_INFO, r_priv, ultima=True)

    # ── Perfil actual ─────────────────────────────────────────────────────────
    rg = doc.rango("perfil_actual")
    pc = r["perfil_actual"]
    _valores(doc, _DEMOGRAFIA, rg, pc["demografia"])
    pc["enfoque_diferencial"] = doc.tabla(_COLS_ENFOQUE, rg)
    pc["grupo_familiar"] = [
        {k: v for k, v in reg.items() if k != "n"}
        for reg in doc.tabla(_COLS_FAMILIA, rg, columna_numero="n")
    ]
    _valores(doc, _ECONOMICAS, rg, pc["actividades_economicas"])
    _valores(doc, _POLITICAS, rg, pc["actividades_politicas_sociales"])
    pc["actividades_politicas_sociales"]["tipo_comparecencia"] = doc.marcadas(_COMPARECENCIA, rg, "der")
    pc["desplazamientos"] = doc.tabla(_COLS_DESPLAZAMIENTOS, rg)

    # ── Hechos de riesgo ──────────────────────────────────────────────────────
    rg = doc.rango("hechos_riesgo")
    i_obs = doc.buscar_etiqueta(_RX_OBSERVACIONES, rg, ultima=True)
    fin_hechos = i_obs[0] if i_obs else rg[1]
    for ini, fin in doc.subrangos(_RX_HECHO_N, (rg[0], fin_hechos)):
        h = {"numero": _RX_HECHO_N.match(doc.unico(ini)).group(1)}
        sr = (ini + 1, fin)
        for campo, rx in _HECHO.items():
            h[campo] = doc.valor(rx, sr) or ""
        h["tipo_actor"] = doc.marcadas(_TIPOS_ACTOR, sr, "izq")
        h["tipo_hecho"] = doc.marcadas(_TIPOS_HECHO, sr, "izq")
        si, no = doc.marcada(_RX_SI, sr, "izq"), doc.marcada(_RX_NO, sr, "izq")
        h["nexo_causal"] = "SI" if si and not no else ("NO" if no and not si else None)
        if si and no:
            adv.append(f"Hecho #{h['numero']}: nexo causal marcado como SI y NO a la vez.")
        claves = ["numero", "dia", "mes", "anio", "departamento", "municipio", "tipo_actor",
                  "nombre_actor", "victima", "medio", "tipo_hecho", "motivacion", "relato", "nexo_causal"]
        h = {k: h.get(k, "") for k in claves}
        if any(h[k] for k in claves if k != "numero"):
            r["hechos_riesgo"]["registros"].append(h)
    if i_obs:
        r["hechos_riesgo"]["observaciones"] = doc.texto_despues(_RX_OBSERVACIONES, (i_obs[0], rg[1]))

    # ── Verificaciones ────────────────────────────────────────────────────────
    rg = doc.rango("verificaciones")
    for ini, fin in doc.subrangos(_RX_VERIFICACION_N, rg):
        sr = (ini + 1, fin)
        v = {
            "numero": _RX_VERIFICACION_N.match(doc.unico(ini)).group(1),
            "fuentes": doc.marcadas(_FUENTES, sr, "der"),
            "nombre_fuente": doc.valor(_RX_NOMBRE_FUENTE, sr) or "",
            "sinopsis": doc.texto_despues(_RX_SINOPSIS_VER, sr),
        }
        if v["fuentes"] or v["nombre_fuente"] or v["sinopsis"]:
            r["verificaciones"].append(v)

    # ── Impacto consecuencial ─────────────────────────────────────────────────
    rg = doc.rango("impacto")
    marcadores = sorted((i, esfera) for esfera, rx in _ESFERAS.items() for i in doc.buscar(rx, rg)[:1])
    for k, (ini, esfera) in enumerate(marcadores):
        sr = (ini + 1, marcadores[k + 1][0] if k + 1 < len(marcadores) else rg[1])
        destino = r["impacto_consecuencial"][esfera]
        destino["items"] = _impacto_esfera(doc, sr, _ITEMS_IMPACTO[esfera], adv, esfera)
        destino["otro_cual"] = doc.valor(_RX_OTRO_CUAL, sr) or ""
        destino["sinopsis"] = doc.texto_despues(_RX_SINOPSIS, sr)

    # ── Secciones de texto libre ──────────────────────────────────────────────
    r["vulnerabilidades_capacidades"] = doc.texto_seccion("vulnerabilidades")
    r["contexto_orden_publico"] = doc.texto_seccion("contexto")
    r["alertas_tempranas"] = doc.texto_seccion("alertas")
    r["medidas_emergencia"] = doc.texto_seccion("medidas_emergencia")
    r["medidas_proteccion_vigentes"] = doc.texto_seccion("medidas_vigentes")
    r["nivel_riesgo"] = doc.texto_seccion("nivel_riesgo")
    r["conclusion"] = doc.texto_seccion("conclusion")
    r["modificaciones_premesa"] = doc.texto_seccion("modificaciones")

    # ── Analista ──────────────────────────────────────────────────────────────
    _valores(doc, _ANALISTA, doc.rango("analista"), r["analista"])

    return r, adv


def _fechas_dd_mm_aaaa(doc, rango):
    """Fechas en cuadrículas DD | MM | AAAA (asignación y remisión de la OT), en orden."""
    for i in doc.filas(rango):
        cn = doc._cn[i]
        if sum(1 for t, _ in cn if _RX_DD.match(t) or _RX_MM.match(t) or _RX_AAAA.match(t)) < 3:
            continue
        siguientes = [k for k in doc.filas((i + 1, rango[1])) if doc.b[k]["tabla"] == doc.b[i]["tabla"]]
        if not siguientes:
            return []
        alineado = doc.alinear_con(i, siguientes[0])
        fechas, actual = [], {}
        for enc, val in alineado:
            actual[enc] = val
            if enc == "aaaa":
                completa = parsear_fecha(val) or fecha_iso(actual.get("dd"), actual.get("mm"), val)
                if completa or any(actual.values()):
                    fechas.append(completa)
                actual = {}
        return fechas
    return []


def _impacto_esfera(doc, rango, items, adv, esfera):
    """{clave_item: "SI" | "NO" | None} leyendo las columnas Si / no de la esfera."""
    salida = {clave: None for clave in items}
    i_enc = next((i for i in doc.filas(rango) if any(_RX_DESCRIPCION.match(t) for t, _ in doc._cn[i])), None)
    for clave, rx in items.items():
        for i in doc.filas(rango):
            cn = doc._cn[i]
            if not cn or not rx.match(cn[0][0] or next((t for t, _ in cn if t), "")):
                continue
            if i_enc is not None:
                columnas = dict(doc.alinear_con(i_enc, i))
                si, no = columnas.get("si", ""), columnas.get("no", "")
            else:
                resto = doc.b[i]["celdas"][1:]
                si, no = (resto + ["", ""])[:2]
            marca_si = es_marca(si) or norm(si) == "si"
            marca_no = es_marca(no) or norm(no) == "no"
            if marca_si and marca_no:
                adv.append(f"Impacto ({esfera}): '{clave}' marcado como Si y No a la vez.")
            elif marca_si:
                salida[clave] = "SI"
            elif marca_no:
                salida[clave] = "NO"
            break
    return salida
