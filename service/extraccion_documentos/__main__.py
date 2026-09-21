"""
Herramienta de línea de comandos para probar la extracción en local,
sin Streamlit ni MongoDB (útil para calibrar con documentos reales que no
pueden salir del equipo).

    python -m service.extraccion_documentos archivo.pdf
    python -m service.extraccion_documentos archivo.docx --bloques   # estructura intermedia
    python -m service.extraccion_documentos a.docx b.pdf --comparar  # diferencias Word vs PDF
"""
import argparse
import json
import sys
from pathlib import Path

from . import extraer_documento
from .lectores import leer_documento


def _aplanar(nodo, ruta=""):
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            yield from _aplanar(v, f"{ruta}.{k}" if ruta else k)
    elif isinstance(nodo, list) and nodo and isinstance(nodo[0], dict):
        for i, v in enumerate(nodo):
            yield from _aplanar(v, f"{ruta}[{i}]")
    else:
        yield ruta, nodo


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Extrae el formato GESP-FT-14 a JSON.")
    p.add_argument("archivos", nargs="+", type=Path)
    p.add_argument("--bloques", action="store_true", help="muestra la estructura intermedia")
    p.add_argument("--comparar", action="store_true", help="compara los JSON de dos archivos")
    a = p.parse_args()

    if a.bloques:
        for ruta in a.archivos:
            for i, b in enumerate(leer_documento(ruta.name, ruta.read_bytes())):
                if b["tipo"] == "texto":
                    print(f"{i:4d} T  {b['texto']}")
                else:
                    print(f"{i:4d} F{b['tabla']:<3d} " + " | ".join(c.replace("\n", " / ") for c in b["celdas"]))
        return

    resultados = [extraer_documento(r.name, r.read_bytes()) for r in a.archivos]
    if a.comparar and len(resultados) == 2:
        x, y = (dict(_aplanar({k: v for k, v in r.items() if k != "_meta"})) for r in resultados)
        difs = [(k, x.get(k), y.get(k)) for k in sorted(set(x) | set(y)) if x.get(k) != y.get(k)]
        for k, v1, v2 in difs:
            print(f"{k}\n   {a.archivos[0].name}: {v1!r}\n   {a.archivos[1].name}: {v2!r}")
        print(f"\n{len(difs)} diferencia(s).")
        return
    for r in resultados:
        print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
