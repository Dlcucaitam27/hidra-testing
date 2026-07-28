# -*- coding: utf-8 -*-
"""
test_apptest_formulario.py
===========================
Llena el FORMULARIO INDIVIDUAL real de Streamlit, de forma automática y sin
necesidad de abrir un navegador, usando el framework oficial de testing de
Streamlit (`streamlit.testing.v1.AppTest`). Es lo más parecido a "un robot
que llena el formulario por ti" que existe para una app Streamlit.

Qué SÍ hace:
  - Inicia sesión con un usuario de prueba real.
  - Llena la sección núcleo del formulario individual (datos de OT/TE,
    datos demográficos, ubicación, nivel de riesgo, factores diferenciales)
    para cada caso generado por `generador_datos.py`.
  - Da clic en "REGISTRAR CASO INDIVIDUAL".
  - Detecta: excepciones no controladas (la app se "cae"), mensajes de error
    de validación, y éxito de guardado.
  - Guarda todo en un CSV para tu reporte.

Qué NO hace (por el tamaño del formulario -> ver INSTRUCCIONES.md):
  - No llena las secciones opcionales de Perfiles, Antecedentes, Hechos de
    riesgo, Desplazamientos ni Verificaciones. El script está escrito para
    que copies el mismo patrón y agregues esas secciones si las necesitas
    (ver la función `rellenar_seccion_extra_EJEMPLO` al final).
  - No prueba el formulario Colectivo (la estructura es distinta). Se puede
    adaptar duplicando `rellenar_caso_individual`.

Requisitos antes de correr:
  1. Un archivo .streamlit/secrets.toml válido apuntando a tu Mongo DE PRUEBA
     (no producción).
  2. Un usuario de prueba ya creado en esa base (rol analista, sin forzar
     cambio de contraseña). Ver INSTRUCCIONES.md para crearlo.
  3. `pip install -r requirements-testing.txt`
  4. Correr este script DESDE la carpeta raíz del proyecto (donde está
     new_app_ismr_sheets.py).

Uso:
    python generador_datos.py --n-validos 20 --n-negativos 25
    python test_apptest_formulario.py --usuario tester.qa --password "Clave123!" \
        --archivo casos_generados.json --categoria validos
"""

import argparse
import csv
import json
import sys
import time
from datetime import date, datetime

sys.path.insert(0, ".")

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    print("[ERROR] Necesitas streamlit >= 1.28. Instala con: pip install -r requirements-testing.txt")
    sys.exit(1)

APP_FILE = "new_app_ismr_sheets.py"
SUBPOBLACIONES = [
    "Amnistiado/a", "Indultado/a", "Militante del Partido Comunes",
    "Dirigente del Partido Comunes", "Madre", "Padre", "Hermano/a",
    "Hijo/a", "Compañero/a permanente", "Otro familiar",
]


def _parse_fecha(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


def iniciar_sesion(at, usuario, password):
    at.text_input[0].set_value(usuario)
    at.text_input[1].set_value(password)
    at.form_submit_button[0].click()
    at.run()
    if at.exception:
        raise RuntimeError(f"Excepción al hacer login: {at.exception}")
    if any("incorrectos" in e.value for e in at.error):
        raise RuntimeError("Usuario o contraseña incorrectos. Revisa --usuario/--password.")
    return at


def ir_a_formulario_individual(at):
    at.button(key="btn_individual").click()
    at.run()
    return at


def _set_selectbox(at, key, valor, avisos):
    try:
        at.selectbox(key=key).select(valor).run()
    except Exception as e:
        avisos.append(f"No se pudo fijar selectbox '{key}'={valor!r}: {e}")


def _set_text(at, key, valor, avisos):
    try:
        at.text_input(key=key).set_value(valor or "")
    except Exception as e:
        avisos.append(f"No se pudo fijar text_input '{key}': {e}")


def _set_text_area(at, key, valor, avisos):
    try:
        at.text_area(key=key).set_value(valor or "")
    except Exception as e:
        avisos.append(f"No se pudo fijar text_area '{key}': {e}")


def _set_number(at, key, valor, avisos):
    try:
        if valor is not None:
            at.number_input(key=key).set_value(valor)
    except Exception as e:
        avisos.append(f"No se pudo fijar number_input '{key}': {e}")


def _set_date(at, key, valor, avisos):
    try:
        if valor:
            at.date_input(key=key).set_value(_parse_fecha(valor))
    except Exception as e:
        avisos.append(f"No se pudo fijar date_input '{key}': {e}")


def rellenar_caso_individual(at, caso, avisos):
    """Llena la sección núcleo del formulario INDIVIDUAL con los datos de `caso`
    (diccionario producido por generador_datos.py). Cada bloque hace .run()
    porque varios campos son dependientes (p.ej. municipio depende de
    departamento) y Streamlit necesita re-ejecutar el script para mostrar
    las opciones correctas."""

    _set_selectbox(at, "caso_tipo_estudio_individual", caso.get("caso_tipo_estudio"), avisos)
    at.run()

    _set_number(at, "caso_ot_anio_individual", caso.get("caso_ot_anio"), avisos)
    _set_number(at, "caso_ot_numero_individual", caso.get("caso_ot_numero"), avisos)
    _set_selectbox(at, "caso_solicitante_individual", caso.get("caso_solicitante"), avisos)
    _set_date(at, "caso_fecha_expedicion_individual", caso.get("caso_fecha_expedicion"), avisos)
    _set_selectbox(at, "caso_tipo_evaluacion_individual", caso.get("caso_tipo_evaluacion"), avisos)
    at.run()

    _set_selectbox(at, "caso_tipo_poblacion_individual", caso.get("caso_tipo_poblacion"), avisos)
    at.run()

    seleccionadas = set(caso.get("subpoblaciones") or [])
    for i, nombre in enumerate(SUBPOBLACIONES):
        key = f"subpob_{i}_individual"
        try:
            cb = at.checkbox(key=key)
            if nombre in seleccionadas:
                cb.check()
            else:
                cb.uncheck()
        except Exception as e:
            avisos.append(f"No se pudo fijar checkbox '{key}': {e}")
    at.run()

    _set_date(at, "caso_fecha_nacimiento_individual", caso.get("caso_fecha_nacimiento"), avisos)
    _set_selectbox(at, "caso_sexo_individual", caso.get("caso_sexo"), avisos)
    _set_selectbox(at, "caso_genero_individual", caso.get("caso_genero"), avisos)
    _set_selectbox(at, "caso_orientacion_individual", caso.get("caso_orientacion"), avisos)
    _set_selectbox(at, "caso_jefatura_individual", caso.get("caso_jefatura"), avisos)
    at.run()

    if caso.get("p_departamento"):
        _set_selectbox(at, "p_departamento_individual", caso["p_departamento"], avisos)
        at.run()   # el rerun refresca la lista de municipios de ese departamento
    if caso.get("p_municipio"):
        _set_selectbox(at, "p_municipio_individual", caso["p_municipio"], avisos)
        at.run()

    _set_selectbox(at, "caso_zona_rural_individual", caso.get("caso_zona_rural"), avisos)
    _set_selectbox(at, "caso_zona_reserva_individual", caso.get("caso_zona_reserva"), avisos)
    at.run()

    _set_selectbox(at, "caso_nivel_riesgo_individual", caso.get("caso_nivel_riesgo"), avisos)
    _set_text_area(at, "caso_observaciones_individual", caso.get("caso_observaciones"), avisos)

    _set_number(at, "caso_num_personas_individual", caso.get("caso_num_personas"), avisos)
    _set_selectbox(at, "caso_companero_individual", caso.get("caso_companero"), avisos)
    _set_number(at, "caso_hijos_menores_individual", caso.get("caso_hijos_menores"), avisos)
    _set_number(at, "caso_menores_otros_individual", caso.get("caso_menores_otros"), avisos)
    _set_number(at, "caso_adultos_mayores_individual", caso.get("caso_adultos_mayores"), avisos)
    _set_number(at, "caso_discapacidad_individual", caso.get("caso_discapacidad"), avisos)

    _set_text_area(at, "caso_osiegd_individual", caso.get("caso_osiegd"), avisos)
    _set_selectbox(at, "caso_factor_discapacidad_individual", caso.get("caso_factor_discapacidad"), avisos)
    _set_selectbox(at, "caso_factor_etnia_individual", caso.get("caso_factor_etnia"), avisos)
    _set_selectbox(at, "caso_factor_campesino_individual", caso.get("caso_factor_campesino"), avisos)
    _set_selectbox(at, "caso_factor_cuidador_individual", caso.get("caso_factor_cuidador"), avisos)
    at.run()


def rellenar_seccion_extra_EJEMPLO(at, avisos):
    """
    PLANTILLA para que agregues las secciones que este script no cubre
    (Perfiles, Antecedentes, Hechos, Desplazamientos, Verificaciones).

    Pasos para extenderlo tú mismo:
      1. Abre front/pages.py y busca la sección que quieras (Ctrl+F).
      2. Anota el `key=f"..."` exacto de cada widget dentro de esa sección.
      3. Repite el patrón de arriba: selectbox -> _set_selectbox,
         text_input -> _set_text, number_input -> _set_number, etc.
      4. Si un campo aparece solo bajo cierta condición (p.ej. "si tipo_colectivo
         == Estructura de partido"), primero fija el campo que dispara la
         condición y haz at.run() ANTES de intentar fijar el campo condicional.
    """
    pass


def enviar_caso(at):
    at.button(key="btn_registrar_individual").click()
    at.run()


def evaluar_resultado(at):
    if at.exception:
        return "CRASH", "; ".join(str(e) for e in at.exception)
    errores_validacion = [e.value for e in at.error]
    if errores_validacion:
        return "RECHAZADO_VALIDACION", " | ".join(errores_validacion)
    exitos = [s.value for s in at.success]
    if exitos:
        return "OK", " | ".join(exitos)
    return "INDETERMINADO", "No hubo excepción, error ni mensaje de éxito visible."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--usuario", required=True, help="usuario analista de PRUEBA (no producción)")
    ap.add_argument("--password", required=True)
    ap.add_argument("--archivo", default="casos_generados.json")
    ap.add_argument("--categoria", default="validos",
                     choices=["validos", "borde", "negativos", "inyeccion", "duplicados_ot_te"])
    ap.add_argument("--limite", type=int, default=None)
    ap.add_argument("--salida", default=None)
    args = ap.parse_args()

    with open(args.archivo, encoding="utf-8") as f:
        casos = json.load(f)[args.categoria]
    if args.limite:
        casos = casos[: args.limite]

    salida = args.salida or f"reporte_apptest_{args.categoria}.csv"
    filas = []
    print(f"[INFO] {len(casos)} casos de la categoría '{args.categoria}' por probar.")

    for i, caso in enumerate(casos):
        t0 = time.time()
        avisos = []
        try:
            at = AppTest.from_file(APP_FILE, default_timeout=60)
            at.run()
            iniciar_sesion(at, args.usuario, args.password)
            ir_a_formulario_individual(at)
            rellenar_caso_individual(at, caso, avisos)
            enviar_caso(at)
            resultado, detalle = evaluar_resultado(at)
        except Exception as e:
            resultado, detalle = "ERROR_SCRIPT", str(e)

        fila = {
            "n": i + 1,
            "id_extra": caso.get("_id_extra", ""),
            "categoria_esperada": caso.get("_categoria", args.categoria),
            "campo_vaciado": caso.get("_campo_vaciado", ""),
            "resultado": resultado,
            "detalle": detalle[:500],
            "avisos_llenado": "; ".join(avisos)[:500],
            "segundos": round(time.time() - t0, 2),
        }
        filas.append(fila)
        print(f"  [{i+1}/{len(casos)}] {fila['id_extra'] or '(sin id)'} -> {resultado}  ({fila['segundos']}s)")

    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()) if filas else [])
        w.writeheader()
        w.writerows(filas)

    print(f"\n[OK] Reporte guardado en {salida}")
    resumen = {}
    for fila in filas:
        resumen[fila["resultado"]] = resumen.get(fila["resultado"], 0) + 1
    print("[RESUMEN]", resumen)


if __name__ == "__main__":
    main()
