# -*- coding: utf-8 -*-
"""
clonar_datos_mongo.py
======================
OPCIONAL. Copia las colecciones de tu Mongo de PRODUCCIÓN hacia tu Mongo de
PRUEBAS, para que el entorno de testing tenga datos realistas en vez de
empezar vacío.

Solo tiene sentido correrlo UNA VEZ, justo después de crear la base de
pruebas (ver INSTRUCCIONES_CLON_ENTORNO.md, Paso 3). No lo vuelvas a correr
después de empezar a generar casos falsos con generador_datos.py, o vas a
mezclar datos reales con datos de prueba en la misma base.

Requiere permisos de LECTURA en producción y de ESCRITURA en pruebas.
Si no tienes URI de producción a mano, no pasa nada: usa la base de pruebas
vacía y ya (los otros scripts del kit generan sus propios datos).

Uso:
    pip install pymongo
    python clonar_datos_mongo.py --uri-origen "mongodb+srv://.../ismr" \
        --uri-destino "mongodb+srv://.../ismr_pruebas" --confirmar
"""

import argparse
import sys

from pymongo import MongoClient


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri-origen", required=True, help="URI de Mongo de PRODUCCIÓN (solo lectura)")
    ap.add_argument("--uri-destino", required=True, help="URI de Mongo de PRUEBAS (destino)")
    ap.add_argument("--confirmar", action="store_true",
                     help="obligatorio: confirma que sabes que vas a escribir en --uri-destino")
    args = ap.parse_args()

    if not args.confirmar:
        print("[STOP] Vuelve a correr agregando --confirmar cuando estés seguro de la URI de destino.")
        print("       Este script ESCRIBE datos en --uri-destino. Revisa dos veces que NO sea producción.")
        sys.exit(1)

    if args.uri_origen.strip() == args.uri_destino.strip():
        print("[ERROR] El origen y el destino son la MISMA URI. Esto borraría/duplicaría producción. Abortado.")
        sys.exit(1)

    cli_origen = MongoClient(args.uri_origen)
    cli_destino = MongoClient(args.uri_destino)

    db_origen = cli_origen.get_default_database()
    db_destino = cli_destino.get_default_database()

    print(f"[INFO] Origen:  base '{db_origen.name}'")
    print(f"[INFO] Destino: base '{db_destino.name}'")
    respuesta = input(f"¿Confirmas copiar TODAS las colecciones de '{db_origen.name}' a '{db_destino.name}'? (escribe SI): ")
    if respuesta.strip().upper() != "SI":
        print("Cancelado.")
        sys.exit(0)

    for nombre_col in db_origen.list_collection_names():
        docs = list(db_origen[nombre_col].find({}))
        if not docs:
            print(f"  - {nombre_col}: vacía, se omite")
            continue
        for d in docs:
            d.pop("_id", None)  # deja que Mongo genere IDs nuevos en destino
        db_destino[nombre_col].delete_many({})
        db_destino[nombre_col].insert_many(docs)
        print(f"  - {nombre_col}: {len(docs)} documentos copiados")

    print("[OK] Clonado completo.")


if __name__ == "__main__":
    main()
