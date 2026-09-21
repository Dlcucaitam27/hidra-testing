"""
Traduce el JSON extraído (esquema GESP-FT-14) a valores del formulario de
casos de HIDRA: claves de st.session_state de cada widget y registros de las
listas multiregistro (hechos, antecedentes, desplazamientos, verificaciones).

Solo se asignan valores que existen en las listas de opciones del formulario
(data/diccionarios.py). Lo que no se puede traducir con seguridad se deja
vacío y se informa en el reporte para que el analista lo complete.

Este módulo no importa Streamlit: devuelve datos y el front decide cómo aplicarlos.
"""
import re
from datetime import date

from data.diccionarios import (
    _DESP_DEPARTAMENTOS, _DESP_FRECUENCIAS, _DESP_MEDIOS_TRANSPORTE, _DESP_MOTIVOS,
    _DESP_TIPOS_VIA, _FUENTES_VERIFICACION, _MEDIOS_HECHO, _MUNICIPIOS,
    _TIPOS_ACTOR_GENERADOR, _TIPOS_AMENAZA, _TIPOS_POBLACION, _TIPOS_RUTA_ANTECEDENTE,
    _VICTIMAS_SITUACION_HECHO,
)

from .mapeo_gesp_ft_14 import _MESES
from .texto import a_entero, elegir_opcion, norm

# Estados del reporte
LLENO, REVISAR, VACIO = "✅ Llenado", "⚠️ Revisar", "— Sin dato"

# Límites de los number_input del formulario (front/pages.py)
_OT_ANIO_MIN, _OT_ANIO_MAX = 2000, 2026
_OT_NUM_MAX = 9999

_OPCIONES_SOLICITANTE = ["TERCEROS", "A NOMBRE PROPIO", "ONG",
                         "INSTITUCIÓN DEL ESTADO COLOMBIANO", "ORGANIZACIÓN INTERNACIONAL"]
_REGLAS_SOLICITANTE = [
    (r"propio|el mismo|la misma|evaluad|titular", "A NOMBRE PROPIO"),
    (r"internacional|onu|naciones unidas|mision de verificacion|mapp|cicr|acnur", "ORGANIZACIÓN INTERNACIONAL"),
    (r"\bong\b|no gubernamental|fundacion|corporacion", "ONG"),
    (r"instituci|estado|fiscal|defensor|personer|procurad|alcald|gobern|polici|ejercito|ministerio"
     r"|\barn\b|\bjep\b|\bunp\b|juzgado|tribunal|consejeria|comisionado", "INSTITUCIÓN DEL ESTADO COLOMBIANO"),
    (r"tercer", "TERCEROS"),
]

_NIVELES = ["ORDINARIO", "EXTRAORDINARIO", "EXTRAORDINARIO DE GÉNERO", "EXTREMO"]

_ACTOR = {
    "GAO": "GAO - GRUPO ARMADO ORGANIZADO",
    "GAO-R": "GAO R - GRUPO ARMADO ORGANIZADO RESIDUAL",
    "GDO": "GDO - GRUPO DELINCUENCIAL ORGANIZADO",
    "GDCO": "GDCO - GRUPO DE DELINCUENCIA COMUN ORGANIZADA",
    "TERCERO / CIVIL": "CIVIL",
    "INSTITUCIÓN DEL ESTADO COLOMBIANO": "ESTADO COLOMBIANO",
    "NO REPORTA": "NO REPORTA",
}
_REGLAS_MEDIO = [
    (r"misiva", "MISIVA INTIMIDATORIA"), (r"llamad|telefon|celular", "LLAMADA"),
    (r"panflet", "PANFLETO"), (r"carta", "CARTAS"), (r"correo|e-?mail", "CORREO ELECTRONICO"),
    (r"whats|mensaje|sms|chat|telegram", "MENSAJE DE TEXTO - APLICACIÓN DE MENSAJERIA INSTANTANEA"),
    (r"redes|facebook|instagram|twitter|tiktok", "REDES SOCIALES"),
    (r"presencial|personalmente|directamente|cara a cara", "PRESENCIAL"),
    (r"tercer", "TERCEROS"), (r"no reporta", "NO REPORTA"),
]
_REGLAS_VICTIMA = [
    (r"evaluad|beneficiari|titular|el mismo|la misma|protegid", "EVALUADO"),
    (r"famil|hij|espos|compan|conyug|madre|padre|herman|sobrin|prim|nieto|abuel", "FAMILIAR"),
    (r"integrante|colectiv|miembro", "INTEGRANTE DE COLECTIVO"),
]
_REGLAS_MOTIVO = [
    (r"laboral|trabaj|empleo|negocio|comerci|proyecto productivo|venta", "LABORAL"),
    (r"electoral|campana|eleccion", "ACTIVIDAD ELECTORAL"),
    (r"organizaci|reunion|comunit|partido|asamblea|lider|\bjac\b|junta|\bong\b|instancia|politic",
     "ACTIVIDAD DE ORGANIZACIÓN SOCIAL, POLÍTICA, COMUNITARIA, INSTANCIA DE PARTICIPACIÓN, ONG"),
    (r"personal|famil|salud|medic|estudi|diligencia|compra|visita|tramite", "PERSONAL"),
    (r"no reporta", "NO REPORTA"),
]
_REGLAS_FRECUENCIA = [
    (r"diari|todos los dias", "Diario"),
    (r"(dos|2|tres|3|varias|algunas)\s*(o mas\s*)?veces.{0,6}semana", "Dos o más veces a la semana"),
    (r"(una|1)\s*vez.{0,6}semana|semanal", "1 vez a la semana"),
    (r"(dos|2|tres|3|varias|algunas)\s*(o mas\s*)?veces.{0,6}mes", "Dos o más veces al mes"),
    (r"(una|1)\s*vez.{0,6}mes|mensual", "1 vez al mes"),
    (r"trimestr", "1 vez al trimestre"), (r"semestr", "1 vez al semestre"),
    (r"no reporta", "No reporta"),
]
_REGLAS_VIA = [(r"primaria", "PRIMARIA"), (r"secundaria", "SECUNDARIA"),
               (r"terciaria|trocha|destapada|camino", "TERCIARIA"), (r"fluvial|rio", "FLUVIAL"),
               (r"no reporta", "NO REPORTA")]
_REGLAS_MEDIOS_TRANSPORTE = [
    (r"\ba pie\b|camin", "A PIE"), (r"avion|aere", "AVION"), (r"bicicleta", "BICICLETA"),
    (r"carro|automovil|particular", "CARRO PARTICULAR"), (r"lancha|bote|canoa|chalupa", "LANCHA"),
    (r"\bmoto", "MOTO"), (r"mula|caballo|animal|bestia|burro", "TRANSPORTE ANIMAL"),
    (r"\bbus|publico|taxi|chiva|flota|transmilenio|colectivo", "TRANSPORTE PÚBLICO"),
    (r"blindad", "VEHÍCULO BLINDADO"), (r"vehiculo convencional|camioneta", "VEHÍCULO CONVENCIONAL"),
    (r"no reporta", "NO REPORTA"),
]

# Sufijo de las claves imp_<esfera>_<item>_<tipo> del formulario
_ESFERAS_FORM = {"economica": "eco", "social": "soc", "politico_institucional": "pol", "salud_bienestar": "sal"}
_NOMBRES_ESFERA = {"economica": "Económica", "social": "Social",
                   "politico_institucional": "Político-institucional", "salud_bienestar": "Salud y bienestar"}
_NOMBRES_ITEM = {
    "dependencia": "Dependencia de subsidios", "iniciativas": "Pérdida de iniciativas productivas",
    "despojo_tierras": "Despojo o abandono de tierras", "empleos": "Acceso restringido a empleos formales",
    "ilicita": "Economías ilícitas / empleo precarizado", "bienes": "Acceso a servicios y bienes",
    "tejido": "Ruptura del tejido social", "redes": "Pérdida de redes de apoyo",
    "traslado": "Traslado de factores de violencia", "confinamiento": "Confinamiento",
    "movilidad": "Restricción de movilidad", "desarraigo": "Desarraigo territorial y cultural",
    "normalizacion": "Normalización de la violencia", "libertad": "Libertad y seguridad personal",
    "participacion": "Restricción en la participación política", "liderazgos": "Desarticulación de liderazgos",
    "oferta": "Falencias en la oferta institucional", "derechos": "Derechos políticos",
    "estigmatizacion": "Estigmatización", "confianza": "Pérdida de confianza en las instituciones",
    "proyeccion": "Proyección personal o colectiva", "cuidados": "Cuidados domésticos / dependientes",
    "desescolarizacion": "Desescolarización", "abandono": "Abandono de menores / adultos mayores",
    "psicosocial": "Afectación psicosocial", "discapacidad": "Discapacidad",
    "dano_vida": "Daño irreparable a la vida e integridad",
}
_ITEMS_SIN_CAMPO = {"despojo_tierras"}   # existe en el formato pero no en el formulario


class _Reporte:
    def __init__(self):
        self.filas = []

    def agregar(self, seccion, campo, valor, estado, nota=""):
        if isinstance(valor, date):
            valor = valor.strftime("%d/%m/%Y")
        self.filas.append({"Sección": seccion, "Campo del formulario": campo,
                           "Valor": "" if valor is None else str(valor), "Estado": estado, "Nota": nota})


# ══════════════════════════════════════════════════════════════════════════════
# Utilidades de traducción
# ══════════════════════════════════════════════════════════════════════════════

def _departamento(texto, opciones=None):
    reglas = [(r"bogota", "BOGOTÁ D.C."),
              (r"san andres|providencia", "ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA"),
              (r"san andres|providencia", "SAN ANDRÉS Y PROVIDENCIA"),
              (r"^valle", "VALLE DEL CAUCA"), (r"guajira", "LA GUAJIRA"),
              (r"^(norte|n\.|nte\.?) (de )?santander", "NORTE DE SANTANDER")]
    return elegir_opcion(texto, opciones or list(_MUNICIPIOS.keys()), reglas)


def _municipio(texto, departamento):
    if not departamento or departamento not in _MUNICIPIOS:
        return None
    return elegir_opcion(texto, _MUNICIPIOS[departamento], [(r"bogota", "BOGOTÁ D.C.")])


def _lugar(texto, deps_opciones=None):
    """'Planadas, Tolima' / 'Tolima - Planadas' / 'Planadas' -> (departamento, municipio)."""
    partes = [p.strip() for p in re.split(r"[,/\-–()]| - ", texto or "") if p.strip()]
    for i, p in enumerate(partes):
        dep = _departamento(p, deps_opciones)
        if dep:
            dep_mun = dep if dep in _MUNICIPIOS else _departamento(p)
            for q in partes[:i] + partes[i + 1:]:
                mun = _municipio(q, dep_mun)
                if mun:
                    return dep, mun
            return dep, None
    # Solo el municipio: se acepta si su nombre es único en el país
    for p in partes:
        hallados = [(d, m) for d in _MUNICIPIOS for m in [_municipio(p, d)] if m]
        if len(hallados) == 1:
            d, m = hallados[0]
            if deps_opciones and d not in deps_opciones:
                d = _departamento(d, deps_opciones)
            return d, m
    return None, None


def _nivel_riesgo(texto, opciones=_NIVELES):
    t = norm(texto)
    hallados = []
    if "extraordinario de genero" in t:
        hallados.append("EXTRAORDINARIO DE GÉNERO")
        t = t.replace("extraordinario de genero", " ")
    for patron, nivel in ((r"\bextremo\b", "EXTREMO"), (r"\bextraordinario\b", "EXTRAORDINARIO"),
                          (r"\bordinario\b", "ORDINARIO"), (r"inactiv", "INACTIVACIÓN")):
        if re.search(patron, t) and nivel in opciones:
            hallados.append(nivel)
    return hallados[0] if len(hallados) == 1 else None


def _parsear_ot(numero_ot, anio_respaldo=None):
    """'OT-2026-0457' -> (2026, 457). Devuelve (anio|None, numero|None)."""
    nums = re.findall(r"\d+", numero_ot or "")
    anio = numero = None
    for k, n in enumerate(nums):
        if len(n) == 4 and 2000 <= int(n) <= 2099:
            anio = int(n)
            resto = nums[:k] + nums[k + 1:]
            numero = int(resto[0]) if resto else None
            break
    else:
        if nums:
            numero = int(nums[-1])
        anio = anio_respaldo
    return anio, numero


def _mes(texto):
    t = norm(texto)
    if t in _MESES:
        return _MESES[t]
    return a_entero(t)


def _fecha_hecho(dia, mes, anio):
    """Fecha parcial igual que el formulario: 'AAAA', 'AAAA-MM' o 'AAAA-MM-DD'."""
    a = a_entero(anio)
    if a is None:
        return ""
    if a < 100:
        a += 2000
    m = _mes(mes)
    if not m or not 1 <= m <= 12:
        return f"{a:04d}"
    d = a_entero(dia)
    try:
        date(a, m, d or 1)
    except ValueError:
        d = None
    return f"{a:04d}-{m:02d}-{d:02d}" if d else f"{a:04d}-{m:02d}"


# ══════════════════════════════════════════════════════════════════════════════
# Prellenado
# ══════════════════════════════════════════════════════════════════════════════

def construir_prellenado(datos: dict, tipo: str = "individual") -> dict:
    """
    Devuelve:
        {"valores": {clave_session_state: valor},
         "listas":  {"hechos": [...], "antecedentes": [...], "desplazamientos": [...], "verificaciones": [...]},
         "reporte": [ {Sección, Campo del formulario, Valor, Estado, Nota}, ... ]}
    """
    v, rep = {}, _Reporte()
    ig, dp, so = datos["informacion_general"], datos["datos_personales"], datos["solicitante"]
    pc, pa = datos["perfil_actual"], datos["perfil_antiguo"]

    def poner(clave, valor, seccion, campo, estado=LLENO, nota=""):
        if valor is None or valor == "":
            rep.agregar(seccion, campo, "", VACIO, nota)
            return
        v[f"{clave}_{tipo}"] = valor
        rep.agregar(seccion, campo, valor, estado, nota)

    # ── Datos OT/TE ───────────────────────────────────────────────────────────
    s = "Datos OT/TE"
    f_asig = date.fromisoformat(ig["fecha_asignacion_ot"]) if ig["fecha_asignacion_ot"] else None
    anio, numero = _parsear_ot(ig["numero_ot"], f_asig.year if f_asig else None)
    nota_ot = f"Leído del documento: '{ig['numero_ot']}'" if ig["numero_ot"] else ""
    if ig["numero_ot"]:
        poner("caso_tipo_estudio", "Orden de Trabajo", s, "Tipo de Estudio", REVISAR,
              "Inferido: el documento trae N° de OT")
    else:
        rep.agregar(s, "Tipo de Estudio", "", VACIO)
    if anio is not None and not _OT_ANIO_MIN <= anio <= _OT_ANIO_MAX:
        rep.agregar(s, "Año OT", anio, REVISAR, f"Fuera del rango permitido por el formulario "
                                               f"({_OT_ANIO_MIN}-{_OT_ANIO_MAX}); no se aplicó")
    else:
        poner("caso_ot_anio", anio, s, "Año OT", nota=nota_ot)
    if numero is not None and not 0 <= numero <= _OT_NUM_MAX:
        rep.agregar(s, "Número OT", numero, REVISAR, "Fuera de rango; no se aplicó")
    else:
        poner("caso_ot_numero", numero, s, "Número OT", nota=nota_ot)

    sol = elegir_opcion(so["solicitante"], _OPCIONES_SOLICITANTE, _REGLAS_SOLICITANTE)
    poner("caso_solicitante", sol, s, "Entidad Solicitante", REVISAR if sol else VACIO,
          f"Texto del documento: '{so['solicitante']}'" if so["solicitante"] else "")
    poner("caso_fecha_expedicion", f_asig, s, "Fecha de Expedición OT", REVISAR,
          "Tomada de la fecha de asignación de la OT" if f_asig else "")
    poner("caso_tipo_evaluacion", ig["tipo_evaluacion"] or elegir_opcion(
        so["tipo_evaluacion"], ["EVALUACIÓN POR PRIMERA VEZ", "REEVALUACIÓN POR HECHOS SOBREVINIENTES",
                                "REEVALUACIÓN POR TEMPORALIDAD"],
        [(r"primera", "EVALUACIÓN POR PRIMERA VEZ"), (r"sobrevinient", "REEVALUACIÓN POR HECHOS SOBREVINIENTES"),
         (r"temporalidad", "REEVALUACIÓN POR TEMPORALIDAD")]), s, "Tipo de Evaluación")

    ppr = pa["persona_reincorporacion"]
    if any(ppr.values()):
        poblacion, nota = "REINCORPORADO/A", "Inferido: el documento diligencia el perfil de persona en reincorporación"
    elif pa["familiar_ppr"]["nombre"]:
        poblacion, nota = "FAMILIAR DE REINCORPORADO/A", "Inferido: el documento diligencia el familiar PPR"
    else:
        poblacion, nota = None, "El formato no trae este dato directamente"
    poner("caso_tipo_poblacion", poblacion if poblacion in _TIPOS_POBLACION else None, s,
          "Tipo de Población", REVISAR, nota)

    # ── Características demográficas ──────────────────────────────────────────
    s = "Características demográficas"
    demo = pc["demografia"]
    dep = _departamento(demo["departamento_residencia"])
    mun = _municipio(demo["municipio_residencia"], dep)
    if not dep and demo["municipio_residencia"]:
        dep, mun = _lugar(demo["municipio_residencia"])
    poner("p_departamento", dep, s, "Departamento",
          nota="" if dep else f"No se reconoció '{demo['departamento_residencia']}'")
    poner("p_municipio", mun, s, "Municipio",
          nota="" if mun else f"No se reconoció '{demo['municipio_residencia']}'")
    zona = norm(demo["zona_rural_urbana"])
    if "rural" in zona:
        poner("caso_zona_rural", "SI", s, "¿Vive en zona rural?")
    else:
        rep.agregar(s, "¿Vive en zona rural?", "", VACIO if not zona else REVISAR,
                    f"Documento: '{demo['zona_rural_urbana']}' (el formulario solo admite SI / NO REPORTA)" if zona else "")
    reserva = norm(demo["zona_reserva_campesina"])
    if reserva.startswith("si"):
        poner("caso_zona_reserva", "SI", s, "¿Vive en zona de reserva campesina?")
    else:
        rep.agregar(s, "¿Vive en zona de reserva campesina?", "", VACIO if not reserva else REVISAR,
                    f"Documento: '{demo['zona_reserva_campesina']}' (el formulario solo admite SI / NO REPORTA)"
                    if reserva else "")
    for campo in ("Fecha de Nacimiento", "Sexo", "Género", "Orientación Sexual", "Jefatura del Hogar"):
        rep.agregar(s, campo, "", VACIO, "El formato GESP-FT-14 no trae este dato"
                    + (f" (edad actual: {demo['edad_actual']})" if campo == "Fecha de Nacimiento"
                       and demo["edad_actual"] else ""))

    # ── Composición núcleo familiar (desde el grupo familiar) ─────────────────
    s = "Núcleo familiar"
    familia = [m for m in pc["grupo_familiar"] if m["nombres"] or m["vinculo"]]
    if familia:
        edades = [a_entero(m["edad"]) for m in familia]
        sin_edad = sum(1 for e in edades if e is None)
        nota_edad = f"{sin_edad} integrante(s) sin edad: conteo parcial" if sin_edad else ""
        es_hijo = [bool(re.search(r"\bhij", norm(m["vinculo"]))) for m in familia]
        pareja = any(re.search(r"compan|conyug|espos|pareja|novi", norm(m["vinculo"])) for m in familia)
        poner("caso_num_personas", len(familia), s, "Número de personas en el núcleo familiar", REVISAR,
              "Cuenta los integrantes listados en el grupo familiar (sin incluir al evaluado)")
        poner("caso_companero", "SI" if pareja else "NO", s, "¿Tiene compañero(a) permanente?", REVISAR,
              "Inferido del vínculo familiar")
        poner("caso_hijos_menores", sum(1 for e, h in zip(edades, es_hijo) if h and e is not None and e < 18),
              s, "Número de hijos menores de edad", REVISAR, nota_edad)
        poner("caso_menores_otros", sum(1 for e, h in zip(edades, es_hijo) if not h and e is not None and e < 18),
              s, "Número de menores distintos a hijos", REVISAR, nota_edad)
        poner("caso_adultos_mayores", sum(1 for e in edades if e is not None and e >= 60),
              s, "Número de adultos mayores", REVISAR, nota_edad)
    else:
        rep.agregar(s, "Grupo familiar", "", VACIO, "El documento no lista integrantes")
    rep.agregar(s, "Número de personas en situación de discapacidad", "", VACIO, "El formato no trae este dato")

    # ── Impacto consecuencial ─────────────────────────────────────────────────
    s = "Impacto consecuencial"
    for esfera, abbr in _ESFERAS_FORM.items():
        for item, valor in datos["impacto_consecuencial"][esfera]["items"].items():
            campo = f"{_NOMBRES_ESFERA[esfera]} · {_NOMBRES_ITEM.get(item, item)}"
            if item in _ITEMS_SIN_CAMPO:
                if valor:
                    rep.agregar(s, campo, valor, REVISAR, "El formulario no tiene este ítem")
                continue
            if valor == "SI":
                poner(f"imp_{abbr}_{item}", "SI", s, campo)
            elif valor == "NO":
                poner(f"imp_{abbr}_{item}", "NO REPORTA", s, campo, REVISAR,
                      "Marcado 'no' en el documento; el formulario solo admite SI / NO REPORTA")
            else:
                rep.agregar(s, campo, "", VACIO)

    # ── Nivel de riesgo ───────────────────────────────────────────────────────
    s = "Nivel de riesgo"
    nivel = _nivel_riesgo(datos["nivel_riesgo"])
    poner("caso_nivel_riesgo", nivel, s, "Nivel de Riesgo", REVISAR if nivel else VACIO,
          f"Texto del documento: '{datos['nivel_riesgo'][:80]}'" if datos["nivel_riesgo"] else "")

    # ── Listas multiregistro ──────────────────────────────────────────────────
    listas = {
        "antecedentes": _antecedentes(datos, rep),
        "desplazamientos": _desplazamientos(datos, rep),
        "hechos": _hechos(datos, rep),
        "verificaciones": _verificaciones(datos, rep),
    }
    return {"valores": v, "listas": listas, "reporte": rep.filas}


def _antecedentes(datos, rep):
    salida = []
    opts_nivel = _NIVELES + ["INACTIVACIÓN"]
    for k, a in enumerate(datos["antecedentes"]["registros"], start=1):
        ruta = elegir_opcion(a["tipo_estudio"], _TIPOS_RUTA_ANTECEDENTE,
                             [(r"colectiv", "COLECTIVA"), (r"individual", "INDIVIDUAL")])
        m_anio = re.search(r"\b(19|20)\d{2}\b", a["resolucion"])
        salida.append({
            "registra_ot": "SI" if a["ot"] else "NO",
            "ot_te_antecede": a["ot"],
            "tipo_ruta_antecedente": ruta or "",
            "nivel_riesgo_anterior": _nivel_riesgo(a["nivel_riesgo"], opts_nivel) or "",
            "registra_resoluciones": "SI" if a["resolucion"] else "",
            "numero_resolucion": a["resolucion"],
            "anio_resolucion": m_anio.group() if m_anio else "",
            "mes_resolucion": "",
            "dia_resolucion": "",
        })
        rep.agregar("Antecedentes", f"Antecedente #{k}", a["ot"] or a["resolucion"], REVISAR,
                    "Verifique tipo de ruta, nivel y fecha de la resolución")
    return salida


def _desplazamientos(datos, rep):
    salida = []
    for k, d in enumerate(datos["perfil_actual"]["desplazamientos"], start=1):
        dep_o, mun_o = _lugar(d["origen"], _DESP_DEPARTAMENTOS)
        dep_d, mun_d = _lugar(d["destino"], _DESP_DEPARTAMENTOS)
        medios = [op for patron, op in _REGLAS_MEDIOS_TRANSPORTE
                  if re.search(patron, norm(d["medio_transporte"])) and op in _DESP_MEDIOS_TRANSPORTE]
        motivo = elegir_opcion(d["motivo"], _DESP_MOTIVOS, _REGLAS_MOTIVO)
        salida.append({
            "motivo": motivo or "",
            "medios_transporte": " | ".join(dict.fromkeys(medios)),
            "dep_origen": dep_o or "", "mun_origen": mun_o or "",
            "dep_destino": dep_d or "", "mun_destino": mun_d or "",
            "frecuencia": elegir_opcion(d["frecuencia"], _DESP_FRECUENCIAS, _REGLAS_FRECUENCIA) or "",
            "tipo_via": elegir_opcion(d["tipo_estado_via"], _DESP_TIPOS_VIA, _REGLAS_VIA) or "",
        })
        rep.agregar("Desplazamientos", f"Desplazamiento #{k}", f"{d['origen']} → {d['destino']}",
                    REVISAR if motivo else VACIO,
                    "" if motivo else f"Motivo obligatorio no reconocido ('{d['motivo']}'): edítelo")
    return salida


def _hechos(datos, rep):
    salida = []
    for h in datos["hechos_riesgo"]["registros"]:
        dep = _departamento(h["departamento"])
        mun = _municipio(h["municipio"], dep)
        actores = [_ACTOR[a] for a in h["tipo_actor"] if a in _ACTOR and _ACTOR[a] in _TIPOS_ACTOR_GENERADOR]
        amenazas = [t for t in h["tipo_hecho"] if t in _TIPOS_AMENAZA]
        notas = ["Seleccione el 'Tipo de Hecho' (el formato no lo trae)"]
        if "OTRO" in h["tipo_actor"]:
            notas.append("actor marcado como 'OTRO'")
        if len(actores) > 1 or len(amenazas) > 1:
            notas.append("varias casillas marcadas: se tomó la primera")
        salida.append({
            "tipo": "",
            "fecha": _fecha_hecho(h["dia"], h["mes"], h["anio"]),
            "departamento": dep or "", "municipio": mun or "",
            "tipo_actor": actores[0] if actores else "",
            "actor_generador": h["nombre_actor"],
            "medio": elegir_opcion(h["medio"], _MEDIOS_HECHO, _REGLAS_MEDIO) or "",
            "amenaza_directa_colectivo": "",
            "victima_situacion": elegir_opcion(h["victima"], _VICTIMAS_SITUACION_HECHO, _REGLAS_VICTIMA) or "",
            "tipo_amenaza": amenazas[0] if amenazas else "",
            "motivacion_amenaza": h["motivacion"],
            "nexo_causal": h["nexo_causal"] or "",
            "descripcion": h["relato"],
        })
        rep.agregar("Hechos de riesgo", f"Hecho #{h['numero']}", salida[-1]["fecha"], REVISAR, "; ".join(notas))
    return salida


def _verificaciones(datos, rep):
    salida = []
    for ver in datos["verificaciones"]:
        fuentes = [f for f in (elegir_opcion(x, _FUENTES_VERIFICACION) for x in ver["fuentes"]) if f]
        salida.append({
            "fuente": fuentes[0] if fuentes else "",
            "nombre_fuente": ver["nombre_fuente"],
            "v_hechos_riesgo": "", "v_lugar_hechos": "", "v_actor_hechos": "",
            "v_motivacion_amenaza": "", "v_perfil_antiguo": "", "v_modo_participacion": "",
            "v_rol_perfil_antiguo": "", "v_frente_columna": "", "v_perfil_actual": "",
            "v_organizacion": "", "v_rol_perfil_actual": "", "criterios": "",
        })
        rep.agregar("Verificaciones", f"Verificación #{ver['numero']}", ver["nombre_fuente"], REVISAR,
                    "Complete los campos de verificación (V. hechos, V. perfil...); la sinopsis queda en el JSON")
    return salida
