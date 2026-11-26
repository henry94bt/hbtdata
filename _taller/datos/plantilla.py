"""Cabecera, barra y pie comunes de hbtdata.es/datos/ (mismo esqueleto que /recursos/)."""
import json
import re
import sys
from html import escape
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DOMINIO = "https://hbtdata.es"
MARCA = "<!-- GENERADO por _taller/datos/generar.py: no editar a mano -->"
INSTAGRAM = "https://instagram.com/hbtdata"
LINKEDIN = "https://linkedin.com/in/henry-data-analyst-"
TIKTOK = "https://www.tiktok.com/@hbtdata"
PERSONA = {"@id": f"{DOMINIO}/#person"}
PERSONA_COMPLETA = {"@type": "Person", "@id": f"{DOMINIO}/#person", "name": "Henry Barrios Thornhill", "url": f"{DOMINIO}/"}
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Crect width='48' height='48' rx='10' fill='%230A3440'/%3E%3Cg fill='%23F7F3EC'%3E%3Crect x='8' y='29.8' width='5.1' height='10.2' rx='1.4'/%3E%3Crect x='14.7' y='20.2' width='5.1' height='19.8' rx='1.4'/%3E%3Crect x='21.4' y='8' width='5.1' height='32' rx='1.4' fill='%23F0A840'/%3E%3Crect x='28.2' y='14.4' width='5.1' height='25.6' rx='1.4'/%3E%3Crect x='34.9' y='25.3' width='5.1' height='14.7' rx='1.4'/%3E%3C/g%3E%3C/svg%3E")


def e(t):
    return escape(str(t), quote=True)


def iconos():
    """El sprite de /webs/ (logo y redes) más las flechas propias."""
    webs = (RAIZ / "webs" / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<svg width="0" height="0".*?</svg>', webs, re.S)
    if not m:
        sys.exit("No encuentro el sprite de iconos en webs/index.html")
    propios = (
        '  <symbol id="i-flecha" viewBox="0 0 24 24"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></symbol>\n'
        '  <symbol id="i-descarga" viewBox="0 0 24 24"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></symbol>\n'
    )
    return m.group(0).replace("</svg>", propios + "</svg>")


def cabeza(titulo, descripcion, url, jsonld, raiz, imagen):
    return f"""<!doctype html>
<html lang="es" class="sin-js">
<head>
{MARCA}
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)}</title>
<meta name="description" content="{e(descripcion)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(descripcion)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{imagen}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="es_ES">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#04161C">
<link rel="icon" href="{FAVICON}">
<link rel="stylesheet" href="{raiz}assets/fuentes/fuentes.css">
<link rel="stylesheet" href="{raiz}datos/datos.css">
<script type="application/ld+json">
{json.dumps(jsonld, ensure_ascii=False, indent=2)}
</script>
</head>
"""


def barra(raiz, actual=""):
    enlaces = [("datos/", "Datos"), ("datos/gasolina/", "Gasolina"), ("juegos/", "Juegos"),
               ("recursos/", "Recursos"), ("webs/", "Para negocios")]
    nav = "".join(f'<a href="{raiz}{h}"{" aria-current=\"page\"" if h == actual else ""}>{t}</a>' for h, t in enlaces)
    return f"""<a class="saltar" href="#contenido">Saltar al contenido</a>
<header class="barra">
  <div class="envuelve">
    <a class="firma" href="{raiz}" aria-label="hbtdata, ir al portfolio">
      <span class="sello"><svg viewBox="0 0 100 100" style="color:var(--claro)"><use href="#volcan"/></svg></span>
      <span class="mono" style="color:var(--claro)">hbt<b>data</b><span> / Datos</span></span>
    </a>
    <nav class="mono" aria-label="Secciones">{nav}</nav>
    <a class="pildora" href="{raiz}#contacto">Contacto</a>
  </div>
</header>
"""


def pie(raiz):
    return f"""<footer>
  <div class="envuelve">
    <span class="mono">hbt<b>data</b> / Datos de Canarias / Las Palmas de Gran Canaria</span>
    <nav class="redes" aria-label="Redes">
      <a href="{INSTAGRAM}" aria-label="Instagram"><svg class="ico"><use href="#i-instagram"/></svg></a>
      <a href="{LINKEDIN}" aria-label="LinkedIn"><svg class="ico"><use href="#i-linkedin"/></svg></a>
      <a href="https://github.com/henry94bt" aria-label="GitHub"><svg class="ico"><use href="#i-github"/></svg></a>
      <a href="{TIKTOK}" aria-label="TikTok"><svg class="ico"><use href="#i-tiktok"/></svg></a>
    </nav>
    <span class="mono"><a class="enlace" href="{raiz}">© 2026 Henry Barrios Thornhill / Volver al portfolio</a> / <a class="enlace" href="{raiz}privacidad/">Privacidad</a></span>
  </div>
</footer>
"""


def scripts(raiz):
    return f"""<script src="{raiz}datos/datos.js"></script>
<script defer src="{raiz}assets/medicion.js"></script>
</body>
</html>
"""


def migas(lista):
    """lista de (nombre, url) → BreadcrumbList."""
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(lista)]}
