# -*- coding: utf-8 -*-
"""
carga_directa_mongo.py
=======================
Prueba de CAPACIDAD del backend, sin pasar por la interfaz de Streamlit.

Qué hace: llama directamente a las mismas funciones que usa `front/pages.py`
para guardar un caso (`conectar_sheet_casos` -> `proxy_casos.append_row(...)`),
usando exactamente el mismo orden de columnas que el formulario real
(copiado de `front/pages.py`, líneas ~4012-4082, sección "individual").

Para qué sirve:
  - Medir cuántos casos por segundo aguanta Mongo/Atlas con inserciones reales.
  - Probar el índice único de OT-TE (duplicados deben fallar, no tumbar el proceso).
  - Detectar errores de conexión/timeouts bajo volumen, sin gastar tiempo
    llenando formularios a mano ni abriendo navegadores.

IMPORTANTE: esto SOLO prueba la capa de datos (Mongo), NO prueba la interfaz
web ni las validaciones de campos del formulario (eso lo hace
`test_apptest_formulario.py`). Son pruebas complementarias, no sustitutas.

Uso:
    python generador_datos.py --n-validos 200
    python carga_directa_mongo.py --archivo casos_generados.json --categoria validos
"""

import argparse
import json
import sys
import time
from datetime import datetime, date

# Debes correr este script DESDE la carpeta raíz del proyecto (donde está
# new_app_ismr_sheets.py), o ajustar el sys.path abajo, para que encuentre
# los módulos "data", "configuration", etc.
sys.path.insert(0, ".")

import streamlit as st  # noqa: E402  (necesario para que st.secrets funcione)

try:
    from data.mongo.casos_repo import conectar_sheet_casos
except ImportError as e:
    print("[ERROR] No se pudo importar data.mongo.casos_repo.")
    print("        Corre este script desde la carpeta raíz del proyecto HIDRA")
    print(f"        (donde está new_app_ismr_sheets.py). Detalle: {e}")
    sys.exit(1)


def _fila_individual(caso: dict, id_caso: int, tz_offset_str="-05:00"):
    """Arma la fila EXACTAMENTE en el mismo orden que usa front/pages.py
    al guardar un caso individual. Si el formulario cambia de orden de
    columnas, actualiza esta función para que siga calzando."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ot_te = f"OT-{caso['caso_ot_anio']}-{str(caso['caso_ot_numero']).zfill(3)}"

    return ot_te, [
        id_caso, timestamp, caso.get("caso_tipo_estudio", ""), ot_te,
        caso.get("caso_fecha_expedicion", ""),
        caso.get("caso_tipo_evaluacion", ""),
        "", "", "", "", "", "", "",  # campos exclusivos de colectivo (vacíos en individual)
        caso.get("caso_tipo_poblacion", ""),
        " | ".join(caso.get("subpoblaciones", []) or []),
        caso.get("caso_fecha_nacimiento", ""), caso.get("caso_sexo", ""),
        caso.get("caso_genero", ""), caso.get("caso_orientacion", ""),
        caso.get("caso_jefatura", ""),
        caso.get("caso_zona_rural", ""), caso.get("caso_zona_reserva", ""),
        (caso.get("p_departamento") or "").strip(), (caso.get("p_municipio") or "").strip(),
        caso.get("caso_solicitante", ""), caso.get("caso_nivel_riesgo", ""),
        (caso.get("caso_observaciones") or "").strip(),
        caso.get("caso_num_personas", ""), caso.get("caso_companero", ""),
        caso.get("caso_hijos_menores", ""), caso.get("caso_menores_otros", ""),
        caso.get("caso_adultos_mayores", ""), caso.get("caso_discapacidad", ""),
        "", "", "", "", "", "", "", "", "",  # campos exclusivos de colectivo (composición)
        (caso.get("caso_osiegd") or "").strip(),
        caso.get("caso_factor_discapacidad", ""), caso.get("caso_factor_etnia", ""),
        caso.get("caso_factor_campesino", ""), caso.get("caso_factor_cuidador", ""),
        "", "",  # victima_conflicto, lider_social (opcionales, no cubiertos por el generador)
        "", "", "", "", "",             # impacto económico (opcional)
        "", "", "", "", "", "", "", "",  # impacto social (opcional)
        "", "", "", "", "", "",          # impacto político (opcional)
        "", "", "", "", "", "", "",      # impacto en salud (opcional)
        "TESTER_AUTOMATIZADO", "tester.qa",
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archivo", default="casos_generados.json")
    ap.add_argument("--categoria", default="validos",
                     choices=["validos", "borde", "negativos", "inyeccion", "duplicados_ot_te"])
    ap.add_argument("--limite", type=int, default=None, help="probar solo los primeros N casos")
    args = ap.parse_args()

    with open(args.archivo, encoding="utf-8") as f:
        datos = json.load(f)
    casos = datos[args.categoria]
    if args.limite:
        casos = casos[: args.limite]

    print(f"[INFO] Conectando a Mongo (colección 'individual')...")
    (hoja_casos, *_resto) = conectar_sheet_casos("individual")
    if hoja_casos is None:
        print("[ERROR] No se pudo conectar. Revisa .streamlit/secrets.toml -> [mongodb] uri")
        sys.exit(1)

    resultados = []
    t0 = time.time()
    for i, caso in enumerate(casos):
        ot_te, fila = _fila_individual(caso, id_caso=hoja_casos.count() + 1)
        t_ini = time.time()
        try:
            existe = hoja_casos.find_one_by("OT-TE", ot_te)
            if existe:
                resultados.append({"ot_te": ot_te, "resultado": "RECHAZADO_DUPLICADO",
                                    "ms": round((time.time() - t_ini) * 1000, 1)})
                continue
            hoja_casos.append_row(fila)
            resultados.append({"ot_te": ot_te, "resultado": "OK",
                                "ms": round((time.time() - t_ini) * 1000, 1)})
        except Exception as e:
            resultados.append({"ot_te": ot_te, "resultado": f"ERROR: {e}",
                                "ms": round((time.time() - t_ini) * 1000, 1)})
        if (i + 1) % 25 == 0:
            print(f"  ... {i + 1}/{len(casos)} procesados")

    total_s = round(time.time() - t0, 2)
    ok = sum(1 for r in resultados if r["resultado"] == "OK")
    dup = sum(1 for r in resultados if r["resultado"] == "RECHAZADO_DUPLICADO")
    err = sum(1 for r in resultados if r["resultado"].startswith("ERROR"))

    print(f"\n[RESUMEN] {len(resultados)} casos en {total_s}s "
          f"({round(len(resultados) / total_s, 2)} casos/seg)")
    print(f"   OK: {ok}   Duplicados rechazados: {dup}   Errores: {err}")

    salida = f"resultados_carga_mongo_{args.categoria}.json"
    with open(salida, "w", encoding="utf-8") as f:
        json.dump({"resumen": {"total": len(resultados), "ok": ok, "duplicados": dup,
                                "errores": err, "segundos": total_s},
                   "detalle": resultados}, f, ensure_ascii=False, indent=2)
    print(f"[OK] Detalle guardado en {salida}")


if __name__ == "__main__":
    main()
