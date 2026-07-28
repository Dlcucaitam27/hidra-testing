# -*- coding: utf-8 -*-
"""
carga_playwright.py
====================
Prueba de SATURACIÓN / CONCURRENCIA sobre la app ya desplegada (la URL real
de Streamlit Cloud o donde la tengan corriendo). Simula N "analistas" abriendo
la página y logueándose al mismo tiempo, para ver cómo responde el servidor
bajo carga real (esto es lo único que de verdad prueba "se cae la página").

Diferencia con los otros dos scripts:
  - generador_datos.py / carga_directa_mongo.py -> prueban la BASE DE DATOS.
  - test_apptest_formulario.py                   -> prueba el FORMULARIO
    (validaciones, campos, un usuario a la vez, sin navegador).
  - carga_playwright.py (este)                   -> prueba el SERVIDOR bajo
    varios usuarios REALES simultáneos, con navegador de verdad.

Por defecto solo hace login + navega al formulario individual (no lo llena
completo, porque el formulario es enorme y cada campo que agregues aquí hace
el script más frágil). Es a propósito: esto mide "¿aguanta el servidor N
sesiones abiertas a la vez?", no "¿el formulario valida bien los campos?"
(para eso ya tienes test_apptest_formulario.py).

Requisitos:
    pip install playwright
    playwright install chromium

Uso:
    python carga_playwright.py --url https://tu-app.streamlit.app \
        --usuarios tester1,tester2,tester3 --password "Clave123!" --concurrencia 5
"""

import argparse
import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from playwright.sync_api import sync_playwright


def una_sesion(url, usuario, password, headless=True):
    t0 = time.time()
    eventos = {"usuario": usuario, "url": url}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=45000)

            # Streamlit tarda un poco en montar los widgets tras la carga inicial
            page.wait_for_selector("input", timeout=30000)

            inputs = page.locator("input[type='text'], input:not([type])")
            inputs.nth(0).fill(usuario)
            page.locator("input[type='password']").first.fill(password)
            page.get_by_text("Iniciar Sesión").click()

            # Espera a que aparezca la pantalla de selección de formulario
            page.wait_for_selector("text=SELECCIONA EL TIPO DE FORMULARIO", timeout=30000)
            eventos["login_ok"] = True

            page.get_by_text("FORMULARIO").first.click()
            page.wait_for_selector("text=DATOS DE OT/TE", timeout=30000)
            eventos["formulario_cargo"] = True

            browser.close()
        eventos["resultado"] = "OK"
    except Exception as e:
        eventos["resultado"] = f"ERROR: {e}"
    eventos["segundos"] = round(time.time() - t0, 2)
    return eventos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="URL pública de la app (Streamlit Cloud, etc.)")
    ap.add_argument("--usuarios", required=True,
                     help="lista separada por comas de usuarios de PRUEBA, ej: tester1,tester2,tester3")
    ap.add_argument("--password", required=True, help="misma contraseña para todos los usuarios de prueba")
    ap.add_argument("--concurrencia", type=int, default=5, help="cuántas sesiones simultáneas")
    ap.add_argument("--repeticiones", type=int, default=1, help="cuántas veces repetir la tanda completa")
    ap.add_argument("--headless", action="store_true", default=True)
    ap.add_argument("--con-cabeza", dest="headless", action="store_false",
                     help="mostrar el navegador (útil para depurar selectores)")
    ap.add_argument("--salida", default="resultados_playwright.csv")
    args = ap.parse_args()

    usuarios = [u.strip() for u in args.usuarios.split(",") if u.strip()]
    resultados = []

    for ronda in range(args.repeticiones):
        print(f"[INFO] Ronda {ronda + 1}/{args.repeticiones} — {args.concurrencia} sesiones simultáneas")
        with ThreadPoolExecutor(max_workers=args.concurrencia) as ex:
            futs = [
                ex.submit(una_sesion, args.url, usuarios[i % len(usuarios)], args.password, args.headless)
                for i in range(args.concurrencia)
            ]
            for fut in as_completed(futs):
                r = fut.result()
                r["ronda"] = ronda + 1
                resultados.append(r)
                print(f"   {r['usuario']} -> {r['resultado']} ({r['segundos']}s)")

    with open(args.salida, "w", newline="", encoding="utf-8") as f:
        campos = ["ronda", "usuario", "resultado", "segundos", "login_ok", "formulario_cargo", "url"]
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for r in resultados:
            w.writerow({k: r.get(k, "") for k in campos})

    ok = sum(1 for r in resultados if r["resultado"] == "OK")
    print(f"\n[RESUMEN] {ok}/{len(resultados)} sesiones exitosas. Detalle en {args.salida}")


if __name__ == "__main__":
    main()
