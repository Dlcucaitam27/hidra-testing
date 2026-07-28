# -*- coding: utf-8 -*-
"""
generador_datos.py
===================
Genera casos de prueba sintéticos para el formulario INDIVIDUAL de HIDRA/ISMR.

No necesita Streamlit ni Mongo para correr: solo produce un archivo
`casos_generados.json` con una lista de "casos" (diccionarios) que después
consumen `test_apptest_formulario.py` y `carga_directa_mongo.py`.

Genera 4 categorías de casos, cada una con su propósito de prueba:

  - "validos"    -> deben pasar validación y guardarse sin error (regresión funcional)
  - "borde"      -> valores límite (años, edades, cantidades en el borde permitido)
  - "negativos"  -> deben SER RECHAZADOS por el formulario (campos obligatorios vacíos)
  - "inyeccion"  -> payloads de inyección NoSQL / texto malicioso en campos libres
  - "ot_te_duplicado" -> mismo OT-TE dos veces, para probar el índice único de Mongo

Uso:
    pip install faker
    python generador_datos.py --n-validos 30 --n-borde 10 --n-negativos 15 --n-inyeccion 10
"""

import argparse
import json
import random
from datetime import date, timedelta

from faker import Faker

fake = Faker("es_CO")

# ── Catálogos EXACTOS tomados de front/pages.py y data/diccionarios.py ──────
# (si el formulario cambia sus opciones, actualiza estas listas)

OPTS_TIPO_ESTUDIO = ["Orden de Trabajo", "Trámite de Emergencia"]
OPTS_SOLICITANTE = [
    "TERCEROS", "A NOMBRE PROPIO", "ONG",
    "INSTITUCIÓN DEL ESTADO COLOMBIANO", "ORGANIZACIÓN INTERNACIONAL",
]
OPTS_TIPO_EVALUACION = [
    "EVALUACIÓN POR PRIMERA VEZ",
    "REEVALUACIÓN POR HECHOS SOBREVINIENTES",
    "REEVALUACIÓN POR TEMPORALIDAD",
]
OPTS_TIPO_POBLACION = [
    "REINCORPORADO/A",
    "FAMILIAR DE REINCORPORADO/A",
    "INTEGRANTE DEL PARTIDO COMUNES",
    "FAMILIAR DE INTEGRANTE DEL PARTIDO COMUNES",
]
SUBPOBLACIONES = [
    "Amnistiado/a", "Indultado/a", "Militante del Partido Comunes",
    "Dirigente del Partido Comunes", "Madre", "Padre", "Hermano/a",
    "Hijo/a", "Compañero/a permanente", "Otro familiar",
]
OPTS_SEXO = ["Hombre", "Mujer", "Intersexual"]
OPTS_GENERO = ["FEMENINO", "MASCULINO", "TRANSGÉNERO", "NO REPORTA"]
OPTS_ORIENTACION = ["HETEROSEXUAL", "HOMOSEXUAL", "BISEXUAL", "NO REPORTA"]
OPTS_JEFATURA = ["SÍ", "NO", "NO REPORTA"]
OPTS_SI_NO_REPORTA = ["SI", "NO REPORTA"]
OPTS_SI_NO = ["SI", "NO"]
OPTS_NIVEL_RIESGO = ["ORDINARIO", "EXTRAORDINARIO", "EXTRAORDINARIO DE GÉNERO", "EXTREMO"]
OPTS_DISCAPACIDAD = [
    "D. FÍSICA", "D. INTELECTUAL", "D. MÚLTIPLE", "D. PSICOSOCIAL",
    "D. SORDOCEGUERA", "D. TALLA BAJA", "D. VISUAL", "NO REPORTA",
]
OPTS_ETNIA = ["AFROCOLOMBIANO", "GITANO", "INDÍGENA", "NO REPORTA", "PALENQUERO", "RAIZAL", "ROM"]
OPTS_CUIDADOR = ["PERSONA CUIDADORA FAMILIAR", "PERSONA CUIDADORA INFORMAL", "NO REPORTA"]

# Pares Departamento/Municipio válidos conocidos (amplía si quieres más variedad;
# deben existir tal cual en data/diccionarios.py -> _MUNICIPIOS)
DEP_MUN_VALIDOS = [
    ("ANTIOQUIA", "MEDELLÍN"),
    ("BOGOTÁ D.C.", "BOGOTÁ D.C."),
    ("VALLE DEL CAUCA", "SANTIAGO DE CALI"),
    ("ATLÁNTICO", "SOLEDAD"),
]
# Estos 4 pares ya se verificaron contra data/diccionarios.py (_MUNICIPIOS).
# Si el diccionario del proyecto cambia, vuelve a validarlos antes de correr
# las pruebas "en serio" (basta con que el nombre exista tal cual, con tildes).

PAYLOADS_INYECCION = [
    '{"$ne": null}',
    '{"$gt": ""}',
    "'; DROP TABLE casos; --",
    "<script>alert(1)</script>",
    "a" * 5000,                       # texto extremadamente largo
    "😀🔥💀" * 200,                    # unicode/emoji en volumen
    "OT-TE\x00con\x00nulos",       # bytes nulos
    "   ",                             # solo espacios (parece vacío pero no lo es)
]


def _caso_base(ot_anio, ot_numero, id_extra=""):
    dep, mun = random.choice(DEP_MUN_VALIDOS)
    return {
        "tipo": "individual",
        "caso_tipo_estudio": random.choice(OPTS_TIPO_ESTUDIO[:1]),  # "Orden de Trabajo" por defecto
        "caso_ot_anio": ot_anio,
        "caso_ot_numero": ot_numero,
        "caso_solicitante": random.choice(OPTS_SOLICITANTE),
        "caso_fecha_expedicion": str(fake.date_between(start_date="-2y", end_date="today")),
        "caso_tipo_evaluacion": random.choice(OPTS_TIPO_EVALUACION),
        "caso_tipo_poblacion": random.choice(OPTS_TIPO_POBLACION),
        "subpoblaciones": random.sample(SUBPOBLACIONES, k=random.randint(1, 3)),
        "caso_fecha_nacimiento": str(fake.date_of_birth(minimum_age=18, maximum_age=85)),
        "caso_sexo": random.choice(OPTS_SEXO),
        "caso_genero": random.choice(OPTS_GENERO),
        "caso_orientacion": random.choice(OPTS_ORIENTACION),
        "caso_jefatura": random.choice(OPTS_JEFATURA),
        "p_departamento": dep,
        "p_municipio": mun,
        "caso_zona_rural": random.choice(OPTS_SI_NO_REPORTA),
        "caso_zona_reserva": random.choice(OPTS_SI_NO_REPORTA),
        "caso_nivel_riesgo": random.choice(OPTS_NIVEL_RIESGO),
        "caso_observaciones": fake.sentence(nb_words=10),
        "caso_num_personas": random.randint(1, 8),
        "caso_companero": random.choice(OPTS_SI_NO),
        "caso_hijos_menores": random.randint(0, 4),
        "caso_menores_otros": random.randint(0, 3),
        "caso_adultos_mayores": random.randint(0, 2),
        "caso_discapacidad": random.randint(0, 2),
        "caso_osiegd": fake.sentence(nb_words=6),
        "caso_factor_discapacidad": random.choice(OPTS_DISCAPACIDAD),
        "caso_factor_etnia": random.choice(OPTS_ETNIA),
        "caso_factor_campesino": random.choice(OPTS_SI_NO_REPORTA),
        "caso_factor_cuidador": random.choice(OPTS_CUIDADOR),
        "_categoria": "valido",
        "_id_extra": id_extra,
    }


def generar_validos(n, ot_anio_inicio=2024, ot_numero_inicio=1):
    """Casos 100% válidos. OT-TE únicos y crecientes para no chocar con el índice único."""
    casos = []
    for i in range(n):
        c = _caso_base(ot_anio_inicio, ot_numero_inicio + i, id_extra=f"valido_{i}")
        casos.append(c)
    return casos


def generar_borde(n, ot_numero_inicio=5000):
    """Valores en el límite de lo permitido por los widgets (min/max de number_input, fechas)."""
    casos = []
    extremos_numericos = [0, 1, 120, 9999]
    for i in range(n):
        c = _caso_base(2000 if i % 2 == 0 else 2026, ot_numero_inicio + i, id_extra=f"borde_{i}")
        c["_categoria"] = "borde"
        c["caso_num_personas"] = random.choice(extremos_numericos[:3])
        c["caso_hijos_menores"] = random.choice([0, 999])
        c["caso_fecha_nacimiento"] = random.choice([
            str(date(1900, 1, 1)),           # límite inferior permitido por el formulario
            str(date.today()),               # hoy (borde válido)
            str(date.today() + timedelta(days=1)),  # futuro -> debe rechazarse
        ])
        casos.append(c)
    return casos


def generar_negativos(n, ot_numero_inicio=6000):
    """Casos que DEBEN fallar la validación: se vacía un campo obligatorio distinto en cada uno."""
    campos_obligatorios = [
        "caso_tipo_estudio", "caso_fecha_expedicion", "caso_tipo_evaluacion",
        "caso_tipo_poblacion", "subpoblaciones", "caso_fecha_nacimiento", "caso_sexo",
        "caso_genero", "caso_orientacion", "caso_jefatura", "p_departamento",
        "caso_zona_rural", "caso_zona_reserva", "p_municipio", "caso_solicitante",
        "caso_nivel_riesgo", "caso_num_personas", "caso_companero",
        "caso_hijos_menores", "caso_menores_otros", "caso_adultos_mayores",
        "caso_discapacidad", "caso_factor_discapacidad", "caso_factor_etnia",
        "caso_factor_campesino", "caso_factor_cuidador",
    ]
    casos = []
    for i in range(n):
        campo_a_vaciar = campos_obligatorios[i % len(campos_obligatorios)]
        c = _caso_base(2025, ot_numero_inicio + i, id_extra=f"negativo_{i}__falta_{campo_a_vaciar}")
        c["_categoria"] = "negativo"
        c["_campo_vaciado"] = campo_a_vaciar
        if campo_a_vaciar == "subpoblaciones":
            c[campo_a_vaciar] = []
        else:
            c[campo_a_vaciar] = None
        casos.append(c)
    return casos


def generar_inyeccion(n, ot_numero_inicio=7000):
    """Payloads maliciosos / raros en campos de texto libre (observaciones, osiegd)."""
    casos = []
    for i in range(n):
        c = _caso_base(2025, ot_numero_inicio + i, id_extra=f"inyeccion_{i}")
        c["_categoria"] = "inyeccion"
        payload = PAYLOADS_INYECCION[i % len(PAYLOADS_INYECCION)]
        c["caso_observaciones"] = payload
        c["caso_osiegd"] = payload
        casos.append(c)
    return casos


def generar_duplicados_ot_te(ot_anio=2025, ot_numero=9999):
    """Dos casos con el MISMO OT-TE: el segundo debe ser rechazado por el índice único."""
    c1 = _caso_base(ot_anio, ot_numero, id_extra="dup_1")
    c2 = _caso_base(ot_anio, ot_numero, id_extra="dup_2")
    c1["_categoria"] = c2["_categoria"] = "duplicado_ot_te"
    return [c1, c2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-validos", type=int, default=20)
    ap.add_argument("--n-borde", type=int, default=8)
    ap.add_argument("--n-negativos", type=int, default=len([
        "caso_tipo_estudio", "caso_fecha_expedicion", "caso_tipo_evaluacion",
        "caso_tipo_poblacion", "subpoblaciones", "caso_fecha_nacimiento", "caso_sexo",
        "caso_genero", "caso_orientacion", "caso_jefatura", "p_departamento",
        "caso_zona_rural", "caso_zona_reserva", "p_municipio", "caso_solicitante",
        "caso_nivel_riesgo", "caso_num_personas", "caso_companero",
        "caso_hijos_menores", "caso_menores_otros", "caso_adultos_mayores",
        "caso_discapacidad", "caso_factor_discapacidad", "caso_factor_etnia",
        "caso_factor_campesino", "caso_factor_cuidador",
    ]))
    ap.add_argument("--n-inyeccion", type=int, default=len(PAYLOADS_INYECCION))
    ap.add_argument("--salida", default="casos_generados.json")
    args = ap.parse_args()

    datos = {
        "validos": generar_validos(args.n_validos),
        "borde": generar_borde(args.n_borde),
        "negativos": generar_negativos(args.n_negativos),
        "inyeccion": generar_inyeccion(args.n_inyeccion),
        "duplicados_ot_te": generar_duplicados_ot_te(),
    }

    with open(args.salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in datos.values())
    print(f"[OK] {total} casos generados -> {args.salida}")
    for k, v in datos.items():
        print(f"   - {k}: {len(v)}")


if __name__ == "__main__":
    main()
