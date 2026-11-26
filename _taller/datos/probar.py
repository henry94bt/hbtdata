#!/usr/bin/env python3
"""Comprueba /datos/ en móvil y escritorio con Playwright y guarda capturas.

    python3 _taller/datos/probar.py [CARPETA_CAPTURAS]

Levanta un servidor local en la raíz del repo. Falla si hay errores de consola, desbordamiento
horizontal, JSON-LD que no se lee, enlaces internos rotos o el selector de combustible no funciona.
"""
import json
import re
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import ISLAS  # noqa: E402

PAGINAS = ["datos/", "datos/gasolina/"] + [f"datos/gasolina/{s}/" for s, _ in ISLAS]
TAMANOS = {"movil": (360, 800), "escritorio": (1366, 900)}


class Silencioso(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    capturas = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if capturas:
        capturas.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(Silencioso, directory=str(RAIZ)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}/"
    fallos = []

    with sync_playwright() as p:
        nav = p.chromium.launch()
        for nombre, (w, h) in TAMANOS.items():
            pag = nav.new_page(viewport={"width": w, "height": h})
            errores = []
            pag.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
            pag.on("pageerror", lambda ex: errores.append(str(ex)))
            for ruta in PAGINAS:
                errores.clear()
                pag.goto(base + ruta, wait_until="networkidle")
                html = pag.content()
                for bloque in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
                    try:
                        json.loads(bloque)
                    except ValueError as ex:
                        fallos.append(f"{ruta}: JSON-LD no válido ({ex})")
                for c in ("false", "true"):
                    pag.evaluate(f"document.documentElement.classList.toggle('ver-diesel', {c})")
                    ancho = pag.evaluate("document.documentElement.scrollWidth")
                    if ancho > w:
                        fallos.append(f"{nombre} {ruta}: desborda ({ancho}px > {w}px)")
                pag.evaluate("document.documentElement.classList.remove('ver-diesel')")
                if pag.locator(".filtros .chip[data-valor=diesel]").count():
                    pag.click(".filtros .chip[data-valor=diesel]")
                    if not pag.locator(".solo-diesel").first.is_visible() or pag.locator(".solo-g95").first.is_visible():
                        fallos.append(f"{nombre} {ruta}: el selector de combustible no cambia")
                    pag.click(".filtros .chip[data-valor=g95]")
                for href in set(re.findall(r'href="((?:\.\./)+[^"#?]*)"', html)):
                    destino = (RAIZ / ruta / href).resolve()
                    if destino.is_dir():
                        destino = destino / "index.html"
                    if not destino.exists():
                        fallos.append(f"{ruta}: enlace roto {href}")
                if errores:
                    fallos.append(f"{nombre} {ruta}: errores de consola {errores}")
                if capturas:
                    pag.screenshot(path=str(capturas / f"{ruta.strip('/').replace('/', '_')}_{nombre}.png"), full_page=True)
            pag.close()
        nav.close()
    srv.shutdown()

    if fallos:
        print("\n".join(fallos))
        sys.exit(1)
    print(f"OK · {len(PAGINAS)} páginas en {len(TAMANOS)} tamaños" + (f" · capturas en {capturas}" if capturas else ""))


if __name__ == "__main__":
    main()
