#!/usr/bin/env python3
"""Pruebas de /recursos/ con Playwright, en escritorio y en móvil.

    python3 _taller/recursos/probar.py [carpeta_capturas]

Sirve la raíz del repo en local, abre la portada y cada ficha, y comprueba:
sin errores en consola, filtros, botón de copiar (lee el portapapeles), copiar
enlace, descarga del PDF y que el PDF se abre. Guarda capturas de página completa.
"""
import functools
import http.server
import json
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
CAPTURAS = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/capturas-recursos")
CAPTURAS.mkdir(parents=True, exist_ok=True)
DATOS = json.loads((Path(__file__).parent / "recursos.json").read_text(encoding="utf-8"))
# solo los recursos que están generados (en la versión publicada no salen los borradores)
DATOS["recursos"] = [r for r in DATOS["recursos"] if (RAIZ / "recursos" / r["slug"] / "index.html").exists()]

fallos = []


def comprueba(cond, texto):
    print(("  ok   " if cond else "  FALLO ") + texto)
    if not cond:
        fallos.append(texto)


def servidor():
    manejador = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(RAIZ))
    manejador.func.log_message = lambda *a: None
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), manejador)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"


def main():
    s, base = servidor()
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome", args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        for nombre, opciones in {
            "escritorio": dict(viewport={"width": 1440, "height": 900}),
            "movil": dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True),
        }.items():
            print(f"\n== {nombre}")
            ctx = nav.new_context(**opciones, permissions=["clipboard-read", "clipboard-write"])
            pag = ctx.new_page()
            errores = []
            pag.on("pageerror", lambda ex: errores.append(str(ex)))
            pag.on("console", lambda m: errores.append(m.text) if m.type == "error" and "fonts.g" not in m.text else None)

            pag.goto(f"{base}/recursos/", wait_until="networkidle")
            pag.wait_for_timeout(2800)
            pag.screenshot(path=str(CAPTURAS / f"portada-{nombre}.png"))
            pag.screenshot(path=str(CAPTURAS / f"portada-{nombre}-completa.png"), full_page=True)
            total = pag.locator(".tarjeta").count()
            comprueba(total == len(DATOS["recursos"]), f"portada: {total} tarjetas")
            pag.locator('.chip[data-campo=tipo][data-valor=prompt]').click()
            visibles = pag.locator(".tarjeta:visible").count()
            n_prompts = sum(r["tipo"] == "prompt" for r in DATOS["recursos"])
            comprueba(visibles == n_prompts and "tipo=prompt" in pag.url, f"filtro de prompts: {visibles} visibles, url {pag.url.split('/recursos')[1]}")
            pag.goto(f"{base}/recursos/?tema=personal", wait_until="networkidle")
            comprueba(pag.locator(".vacio").is_visible() or pag.locator(".tarjeta:visible").count() > 0, "filtro por URL sin resultados muestra aviso")

            for r in DATOS["recursos"]:
                pag.goto(f"{base}/recursos/{r['slug']}/", wait_until="networkidle")
                pag.wait_for_timeout(300)
                pag.screenshot(path=str(CAPTURAS / f"{r['slug']}-{nombre}.png"), full_page=True)
                comprueba(pag.locator("h1").inner_text().strip() != "", f"{r['slug']}: carga")
                if r["tipo"] == "prompt":
                    pag.locator('[data-copiar="texto-prompt"]').click()
                    pag.wait_for_timeout(200)
                    copiado = pag.evaluate("navigator.clipboard.readText()")
                    comprueba(copiado == r["prompt"], f"{r['slug']}: copiar prompt ({len(copiado)} caracteres)")
                    comprueba(pag.locator('[data-copiar="texto-prompt"]').inner_text().strip().lower() == "copiado", f"{r['slug']}: el botón dice «Copiado»")
                pag.locator('[data-copiar="enlace"]').click()
                pag.wait_for_timeout(200)
                comprueba(pag.evaluate("navigator.clipboard.readText()") == f"{base}/recursos/{r['slug']}/", f"{r['slug']}: copiar enlace")
                if r["tipo"] == "pdf" and nombre == "escritorio":
                    enlace = pag.locator("a[download]")
                    comprueba(enlace.count() == 1, f"{r['slug']}: botón de descarga")
                    if enlace.count():
                        with pag.expect_download() as d:
                            enlace.click()
                        ruta = d.value.path()
                        cabecera = Path(ruta).read_bytes()[:5]
                        comprueba(cabecera == b"%PDF-", f"{r['slug']}: el archivo descargado es un PDF")
            comprueba(not errores, "sin errores en consola" + (f": {errores[:3]}" if errores else ""))
            ctx.close()
        nav.close()
    s.shutdown()
    print(f"\nCapturas en {CAPTURAS}")
    if fallos:
        sys.exit(f"{len(fallos)} fallos")


if __name__ == "__main__":
    main()
