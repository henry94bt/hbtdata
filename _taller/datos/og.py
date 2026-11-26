#!/usr/bin/env python3
"""Imágenes para compartir (1200×630) de /datos/: assets/og-datos.png, og-gasolina.png y og-gasolina-<isla>.png.

    python3 _taller/datos/og.py

No llevan precios (se harían viejas): solo la pregunta y la isla. Se rehacen a mano si cambia el diseño.
Necesita Playwright con Chromium.
"""
import sys
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from comun import DE_ISLA, ISLAS  # noqa: E402
from graficos import _proyecta, _simplifica, contorno  # noqa: E402

RAIZ = AQUI.parents[1]
VOLCAN = ('<svg viewBox="0 0 100 100" class="volcan"><rect x="0" y="68" width="16" height="32" rx="4.5" fill="currentColor"/>'
          '<rect x="21" y="38" width="16" height="62" rx="4.5" fill="currentColor"/><rect x="42" y="0" width="16" height="100" rx="4.5" fill="#F0A840"/>'
          '<rect x="63" y="20" width="16" height="80" rx="4.5" fill="currentColor"/><rect x="84" y="54" width="16" height="46" rx="4.5" fill="currentColor"/></svg>')


def silueta(islas, resaltar=None):
    """SVG con el contorno de las islas pedidas; la resaltada en ocre."""
    trazos = []
    for s, _ in ISLAS:
        if s not in islas:
            continue
        for a in contorno(s):
            lejos = max(range(len(a)), key=lambda i: (a[i][0] - a[0][0]) ** 2 + (a[i][1] - a[0][1]) ** 2)
            trazos.append((s, _simplifica(a[:lejos + 1], 0.0015)[:-1] + _simplifica(a[lejos:], 0.0015)))
    xs = [x for _, a in trazos for x, _ in a]
    ys = [y for _, a in trazos for _, y in a]
    x0, y0 = min(xs), min(ys)
    w, h = max(xs) - x0, max(ys) - y0
    caminos = "".join(
        f'<path class="{"si" if s == resaltar or resaltar is None else "no"}" d="M'
        + "L".join(f"{x - x0:.4f},{y - y0:.4f}" for x, y in a) + 'Z"/>' for s, a in trazos)
    return f'<svg viewBox="0 0 {w:.4f} {h:.4f}" class="islas">{caminos}</svg>'


def html(titulo, subtitulo, ruta, islas, resaltar=None):
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<link rel="stylesheet" href="../../assets/fuentes/fuentes.css"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1200px;height:630px;background:#04161C;color:#F7F3EC;overflow:hidden;position:relative;font-family:Poppins,sans-serif;font-weight:300}}
.mono{{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:500;letter-spacing:.14em;text-transform:uppercase;color:rgba(247,243,236,.75)}}
.mono b{{color:#F0A840;font-weight:500}}
.halo{{position:absolute;right:-120px;top:-80px;width:820px;height:820px;background:radial-gradient(circle,rgba(240,168,64,.13),transparent 60%)}}
.islas{{position:absolute;right:70px;top:60px;width:440px;height:440px}}
.islas path{{fill:#0B3A47;stroke:#96D6D6;stroke-width:1.5px;vector-effect:non-scaling-stroke;stroke-opacity:.6}}
.islas path.si{{fill:#0E4654;stroke:#F0A840;stroke-opacity:1}}
.caja{{position:absolute;left:80px;top:78px;width:600px;bottom:70px;display:flex;flex-direction:column}}
.firma{{display:flex;align-items:center;gap:14px}}
.volcan{{width:44px;height:44px;color:#F7F3EC}}
h1{{font-weight:200;font-size:56px;line-height:1.08;margin:28px 0 20px;letter-spacing:-.01em}}
p.s{{font-size:23px;color:rgba(247,243,236,.75);max-width:30ch;line-height:1.4}}
.abajo{{margin-top:auto;display:flex;justify-content:space-between;width:1040px}}
</style></head><body><div class="halo"></div>{silueta(islas, resaltar)}<div class="caja">
<span class="firma">{VOLCAN}<span class="mono">hbt<b>data</b> / datos</span></span>
<h1>{escape(titulo)}</h1>
<p class="s">{escape(subtitulo)}</p>
<div class="abajo"><span class="mono">Datos del Ministerio · cada día</span><span class="mono"><b>hbtdata.es</b>/{escape(ruta)}</span></div>
</div></body></html>"""


def main():
    todas = [s for s, _ in ISLAS]
    piezas = [
        ("og-datos.png", html("Datos de Canarias, con su fuente y su fecha", "Preguntas de aquí respondidas con datos públicos.",
                              "datos", todas)),
        ("og-gasolina.png", html("¿En qué isla está más barata la gasolina?", "Gasolina y diésel en las siete islas, actualizado cada mañana.",
                                 "datos/gasolina", todas)),
    ] + [(f"og-gasolina-{s}.png", html(f"¿Dónde está la gasolina más barata {DE_ISLA[s]}?",
                                       "Ranking de gasolineras, mapa y evolución, actualizado cada mañana.",
                                       f"datos/gasolina/{s}", [s], s)) for s, _ in ISLAS]
    tmp = AQUI / "og-tmp.html"
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pag = nav.new_page(viewport={"width": 1200, "height": 630})
        for nombre, contenido in piezas:
            tmp.write_text(contenido, encoding="utf-8")
            pag.goto(tmp.as_uri(), wait_until="load")
            pag.evaluate("document.fonts.ready")
            destino = RAIZ / "assets" / nombre
            pag.screenshot(path=str(destino))
            try:
                from PIL import Image
                im = Image.open(destino).convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
                im.save(destino, optimize=True)
            except ImportError:
                pass
            print(f"assets/{nombre} ({destino.stat().st_size // 1024} KB)")
        nav.close()
    tmp.unlink()


if __name__ == "__main__":
    main()
