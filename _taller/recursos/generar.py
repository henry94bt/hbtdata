#!/usr/bin/env python3
"""Genera hbtdata.es/recursos/ a partir de recursos.json.

    python3 _taller/recursos/generar.py            # todo, borradores incluidos (con etiqueta y noindex)
    python3 _taller/recursos/generar.py --publicar # solo lo publicado; actualiza sitemap.xml y llms.txt

Salida: recursos/index.html y recursos/<slug>/index.html. Las páginas generadas
llevan la marca GENERADO y se borran y rehacen en cada ejecución: no se editan a mano.
Solo usa la biblioteca estándar de Python.
"""
import json
import re
import shutil
import sys
from datetime import date
from html import escape
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "recursos"
DOMINIO = "https://hbtdata.es"
MARCA = "<!-- GENERADO por _taller/recursos/generar.py: no editar a mano -->"
OG = f"{DOMINIO}/assets/og-recursos.png"
TIKTOK = "https://www.tiktok.com/@hbtdata"
INSTAGRAM = "https://instagram.com/hbtdata"
LINKEDIN = "https://linkedin.com/in/henry-data-analyst-"
# las tres redes por igual en todas las llamadas a la acción
REDES = [("Instagram", INSTAGRAM, "i-instagram"), ("TikTok", TIKTOK, "i-tiktok"), ("LinkedIn", LINKEDIN, "i-linkedin")]
REDES_TEXTO = (f'<a href="{INSTAGRAM}">Instagram</a>, <a href="{TIKTOK}">TikTok</a> '
               f'o <a href="{LINKEDIN}">LinkedIn</a>')
AVISO = ("Página personal, sin relación con Anthropic. «Claude» se nombra solo para describir "
         "para qué sirve cada recurso. Los conectores enlazan a su fuente oficial: aquí no se redistribuye nada ajeno.")

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_larga(iso):
    a, m, d = (int(x) for x in iso.split("-"))
    return f"{d} de {MESES[m - 1]} de {a}"


def e(texto):
    return escape(str(texto), quote=True)


# ---------- piezas comunes ----------

def iconos():
    """Reutiliza el sprite de /webs/ (logo e iconos de redes) y añade los propios."""
    webs = (RAIZ / "webs" / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<svg width="0" height="0".*?</svg>', webs, re.S)
    if not m:
        sys.exit("No encuentro el sprite de iconos en webs/index.html")
    propios = (
        '  <symbol id="i-copiar" viewBox="0 0 24 24"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/></symbol>\n'
        '  <symbol id="i-descarga" viewBox="0 0 24 24"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></symbol>\n'
        '  <symbol id="i-enlace" viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></symbol>\n'
        '  <symbol id="i-flecha" viewBox="0 0 24 24"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></symbol>\n'
    )
    return m.group(0).replace("</svg>", propios + "</svg>")


FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Crect width='48' height='48' rx='10' fill='%230A3440'/%3E%3Cg fill='%23F7F3EC'%3E%3Crect x='8' y='29.8' width='5.1' height='10.2' rx='1.4'/%3E%3Crect x='14.7' y='20.2' width='5.1' height='19.8' rx='1.4'/%3E%3Crect x='21.4' y='8' width='5.1' height='32' rx='1.4' fill='%23F0A840'/%3E%3Crect x='28.2' y='14.4' width='5.1' height='25.6' rx='1.4'/%3E%3Crect x='34.9' y='25.3' width='5.1' height='14.7' rx='1.4'/%3E%3C/g%3E%3C/svg%3E")


def cabeza(titulo, descripcion, url, jsonld, raiz, noindex=False):
    robots = '<meta name="robots" content="noindex">\n' if noindex else ""
    return f"""<!doctype html>
<html lang="es" class="sin-js">
<head>
{MARCA}
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)}</title>
<meta name="description" content="{e(descripcion)}">
{robots}<link rel="canonical" href="{url}">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(descripcion)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{OG}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="es_ES">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#04161C">
<link rel="icon" href="{FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Poppins:wght@200;300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{raiz}recursos/recursos.css">
<script type="application/ld+json">
{json.dumps(jsonld, ensure_ascii=False, indent=2)}
</script>
</head>
"""


def barra(raiz, actual=None, tipos=None):
    enlaces = ""
    if tipos:
        for clave, t in tipos.items():
            marca = ' aria-current="page"' if clave == actual else ""
            enlaces += f'      <a href="{raiz}recursos/?tipo={clave}#lista"{marca}>{e(t["nombre"])}</a>\n'
    return f"""<header class="barra">
  <div class="envuelve">
    <a class="firma" href="{raiz}" aria-label="hbtdata, ir al portfolio">
      <span class="sello"><svg viewBox="0 0 100 100" style="color:var(--claro)"><use href="#volcan"/></svg></span>
      <span class="mono" style="color:var(--claro)">hbt<b>data</b><span> / Recursos</span></span>
    </a>
    <nav class="mono" aria-label="Tipos de recurso">
{enlaces}    </nav>
    <a class="pildora" href="{raiz}#contacto">Contacto</a>
  </div>
</header>
"""


def pie(raiz):
    return f"""<div class="aviso-anthropic"><div class="envuelve">{e(AVISO)}</div></div>
<footer>
  <div class="envuelve">
    <span class="mono">hbt<b>data</b> / Recursos de Claude / Las Palmas de Gran Canaria</span>
    <nav class="redes" aria-label="Redes">
      <a href="{INSTAGRAM}" aria-label="Instagram"><svg class="ico"><use href="#i-instagram"/></svg></a>
      <a href="{LINKEDIN}" aria-label="LinkedIn"><svg class="ico"><use href="#i-linkedin"/></svg></a>
      <a href="https://github.com/henry94bt" aria-label="GitHub"><svg class="ico"><use href="#i-github"/></svg></a>
      <a href="{TIKTOK}" aria-label="TikTok"><svg class="ico"><use href="#i-tiktok"/></svg></a>
    </nav>
    <a class="mono enlace" href="{raiz}">© 2026 Henry Barrios Thornhill / Volver al portfolio</a>
  </div>
</footer>
"""


def etiqueta_borrador(r):
    return '<span class="borrador">Borrador</span>' if r["estado"] == "borrador" else ""


PERSONA = {"@id": f"{DOMINIO}/#person"}


# ---------- portada ----------

def tarjeta(r, datos, raiz):
    tipo = datos["tipos"][r["tipo"]]["uno"]
    tema = datos["temas"][r["tema"]]
    accion = {"prompt": "Ver y copiar", "skill": "Ver la skill", "plugin": "Ver la lista", "pdf": "Ver la guía"}[r["tipo"]]
    return f"""        <li class="tarjeta" data-tipo="{r['tipo']}" data-tema="{r['tema']}">
          <div class="tipo"><span class="mono"><i></i>{e(tipo)} / {e(tema)}</span>{etiqueta_borrador(r)}</div>
          <h3><a href="{raiz}recursos/{r['slug']}/">{e(r['titulo'])}</a></h3>
          <p>{e(r['resumen'])}</p>
          <div class="pie"><span class="mono">{accion}</span><svg class="ico trazo"><use href="#i-flecha"/></svg></div>
        </li>
"""


def portada(datos, lista):
    raiz = "../"
    url = f"{DOMINIO}/recursos/"
    titulo = "Recursos de Claude: prompts, skills y guías gratis · hbtdata"
    descripcion = ("Los prompts, skills, conectores y guías en PDF de Claude que uso de verdad para analizar datos, "
                   "hacer informes y automatizar tareas. Gratis y sin registro.")
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": f"{url}#coleccion", "url": url, "name": titulo,
         "description": descripcion, "inLanguage": "es", "isPartOf": {"@id": f"{DOMINIO}/#web"},
         "author": PERSONA, "image": OG,
         "mainEntity": {"@type": "ItemList", "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "url": f"{url}{r['slug']}/", "name": r["titulo"]}
             for i, r in enumerate(lista)]}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "hbtdata", "item": f"{DOMINIO}/"},
            {"@type": "ListItem", "position": 2, "name": "Recursos", "item": url}]},
        {"@type": "Person", "@id": f"{DOMINIO}/#person", "name": "Henry Barrios Thornhill", "url": f"{DOMINIO}/"},
    ]}

    def chips(campo, opciones, todo):
        cuenta = {}
        for r in lista:
            cuenta[r[campo]] = cuenta.get(r[campo], 0) + 1
        h = f'<button class="chip" type="button" data-campo="{campo}" data-valor="todo" aria-pressed="true">{todo} <small>{len(lista)}</small></button>'
        for clave, nombre in opciones.items():
            if cuenta.get(clave):
                h += f'<button class="chip" type="button" data-campo="{campo}" data-valor="{clave}" aria-pressed="false">{e(nombre)} <small>{cuenta[clave]}</small></button>'
        return h

    tipos_nombres = {k: v["nombre"] for k, v in datos["tipos"].items()}
    tarjetas = "".join(tarjeta(r, datos, raiz) for r in lista)
    return (cabeza(titulo, descripcion, url, jsonld, raiz)
            + "<body>\n" + iconos() + "\n" + barra(raiz, tipos=datos["tipos"]) + f"""
<main>
  <section class="portada">
    <div class="envuelve">
      <div>
        <p class="mono"><b>//</b>recursos</p>
        <h1 class="titular">Lo que uso con Claude, para que lo uses tú.</h1>
        <p class="entrada">Prompts, skills, conectores y guías en PDF que uso de verdad para analizar datos, hacer informes y quitarme tareas de encima. Cópialos, descárgalos y adáptalos a lo tuyo.</p>
        <div class="acciones">
          <a class="pildora llena" href="#lista">Ver los recursos</a>
          <p class="pide">¿Te falta alguno? Pídemelo en {REDES_TEXTO}.</p>
        </div>
        <ul class="sellos mono"><li>Gratis</li><li>Sin registro</li><li>Probado antes de subirlo</li></ul>
      </div>
      <div class="lienzo" aria-hidden="true"><canvas id="campo"></canvas></div>
    </div>
  </section>

  <div class="filtros" role="group" aria-label="Filtrar recursos">
    <div class="envuelve">
      <div class="fila-chips"><span class="mono">Tipo</span>{chips('tipo', tipos_nombres, 'Todo')}</div>
      <div class="fila-chips"><span class="mono">Tema</span>{chips('tema', datos['temas'], 'Todos')}</div>
    </div>
  </div>

  <section id="lista" style="padding-top:44px">
    <div class="envuelve">
      <ul class="rejilla">
{tarjetas}      </ul>
      <p class="vacio" hidden>Todavía no hay nada con esa combinación. Prueba con otro tema o pídemelo en {REDES_TEXTO}.</p>
    </div>
  </section>

  <section class="panel">
    <div class="envuelve">
      <div class="cabeza">
        <p class="mono"><b>//</b> Cómo se usa</p>
        <h2 class="titular">Cuatro tipos, cero complicaciones.</h2>
        <p class="entrada">Funcionan en Claude desde el navegador, la aplicación del ordenador o el móvil. Las skills y los conectores necesitan una cuenta de pago.</p>
      </div>
      <ul class="usos">
        <li><span class="mono"><b>01</b> Prompts</span><h3>Copia, pega y cambia lo que va entre corchetes</h3><p>Cada ficha trae el texto, para qué sirve y un ejemplo de lo que sale.</p></li>
        <li><span class="mono"><b>02</b> Skills</span><h3>Descarga el ZIP y súbelo a Claude</h3><p>Una skill es un paquete de instrucciones que Claude usa cuando hace falta. Cada una trae su README.</p></li>
        <li><span class="mono"><b>03</b> Conectores</span><h3>Conecta las aplicaciones que ya usas</h3><p>Correo, Drive, Canva… Te cuento cuáles uso y para qué, con el enlace oficial.</p></li>
        <li><span class="mono"><b>04</b> Guías en PDF</span><h3>Descárgala y guárdala</h3><p>Sin formulario. Cada guía lleva la fecha de su versión para que sepas si está al día.</p></li>
      </ul>
    </div>
  </section>
</main>

""" + pie(raiz) + f"""
<script src="{raiz}assets/campo.js"></script>
<script src="{raiz}recursos/recursos.js"></script>
</body>
</html>
""")


# ---------- fichas ----------

def lista_html(items):
    return '<ul class="lista">' + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>"


def cuerpo_prompt(r):
    h = f"""      <div class="bloque">
        <h2>Para qué sirve</h2>
        {lista_html(r['para_que'])}
      </div>
      <div class="bloque">
        <h2>El prompt</h2>
        <div class="codigo">
          <header><span class="mono"><b>&gt;_</b> prompt</span><button class="copiar" type="button" data-copiar="texto-prompt"><svg class="ico trazo"><use href="#i-copiar"/></svg><span>Copiar</span></button></header>
          <pre id="texto-prompt">{e(r['prompt'])}</pre>
        </div>
      </div>
"""
    if r.get("ejemplo"):
        h += f"""      <div class="bloque">
        <h2>Un ejemplo de lo que sale</h2>
        <div class="codigo resultado">
          <header><span class="mono">Respuesta de ejemplo</span></header>
          <pre>{e(r['ejemplo'])}</pre>
        </div>
      </div>
"""
    if r.get("consejos"):
        h += f"""      <div class="bloque">
        <h2>Consejos</h2>
        {lista_html(r['consejos'])}
      </div>
"""
    return h


def cuerpo_skill(r, raiz):
    if r.get("descarga"):
        boton = f'<a class="pildora llena" href="{raiz}recursos/{r["descarga"]}" download><svg class="ico trazo"><use href="#i-descarga"/></svg>Descargar la skill</a>'
    else:
        boton = '<span class="pildora" aria-disabled="true"><svg class="ico trazo"><use href="#i-descarga"/></svg>Descarga pronto</span>'
    h = f"""      <div class="bloque">
        <h2>Para qué sirve</h2>
        {lista_html(r['para_que'])}
      </div>
      <div class="bloque">
        <div class="descarga"><div class="texto"><span class="mono">ZIP con SKILL.md y README</span>{boton}</div></div>
      </div>
      <div class="bloque">
        <h2>Cómo instalarla</h2>
        <ol class="pasos">{''.join(f'<li>{e(p)}</li>' for p in r['instalar'])}</ol>
      </div>
"""
    if r.get("pendiente") and r["estado"] == "borrador":
        h += f'      <div class="bloque"><p class="pendiente">Pendiente: {e(r["pendiente"])}</p></div>\n'
    return h


def cuerpo_plugin(r):
    items = "".join(
        f'<li><a href="{e(x["enlace"])}" rel="noopener"><strong>{e(x["nombre"])}</strong><p>{e(x["uso"])}</p>'
        f'<svg class="ico trazo"><use href="#i-fuera"/></svg></a></li>' for x in r["elementos"])
    fuente = r.get("fuente")
    return f"""      <div class="bloque">
        <h2>Para qué sirve esta lista</h2>
        {lista_html(r['para_que'])}
      </div>
      <div class="bloque">
        <h2>Lo que tengo conectado</h2>
        <ul class="conectores">{items}</ul>
      </div>
""" + (f"""      <div class="bloque">
        <p class="pendiente">Todos se activan desde la configuración de Claude. <a href="{e(fuente['enlace'])}">{e(fuente['texto'])}</a>.</p>
      </div>
""" if fuente else "")


def cuerpo_pdf(r, raiz):
    archivo = SALIDA / r["descarga"]
    portada_img = r["descarga"].replace(".pdf", ".png")
    hay = archivo.exists()
    boton = (f'<a class="pildora llena" href="{raiz}recursos/{r["descarga"]}" download><svg class="ico trazo"><use href="#i-descarga"/></svg>Descargar el PDF</a>'
             if hay else '<span class="pildora" aria-disabled="true">PDF en preparación</span>')
    img = (f'<img src="{raiz}recursos/{portada_img}" alt="Portada de la guía «{e(r["titulo"])}»" width="150" height="212" loading="lazy">'
           if (SALIDA / portada_img).exists() else "")
    paginas = ""
    if hay:
        kb = archivo.stat().st_size // 1024
        paginas = f" · {kb} KB"
    return f"""      <div class="bloque">
        <h2>Qué trae</h2>
        {lista_html(r['para_que'])}
      </div>
      <div class="bloque">
        <div class="descarga">{img}<div class="texto"><span class="mono">PDF · versión {e(r['version'])} · {fecha_larga(r['fecha'])}{paginas}</span>{boton}<p class="mono" style="text-transform:none;letter-spacing:.04em">Descarga directa, sin formulario.</p></div></div>
      </div>
"""


def ficha(r, datos, lista):
    raiz = "../../"
    url = f"{DOMINIO}/recursos/{r['slug']}/"
    tipo = datos["tipos"][r["tipo"]]
    tema = datos["temas"][r["tema"]]
    titulo = f"{r['titulo']} · {tipo['uno']} de Claude · hbtdata"
    esquema = {"prompt": "CreativeWork", "skill": "SoftwareSourceCode", "plugin": "Article", "pdf": "DigitalDocument"}[r["tipo"]]
    obra = {"@type": esquema, "@id": f"{url}#recurso", "name": r["titulo"], "description": r["resumen"], "url": url,
            "inLanguage": "es", "datePublished": r["fecha"], "dateModified": r["fecha"], "author": PERSONA,
            "isAccessibleForFree": True, "isPartOf": {"@id": f"{DOMINIO}/recursos/#coleccion"}, "about": tema}
    if r["tipo"] == "prompt":
        obra["genre"] = "Prompt"
        obra["text"] = r["prompt"]
    if r["tipo"] == "pdf":
        obra["encodingFormat"] = "application/pdf"
        obra["contentUrl"] = f"{DOMINIO}/recursos/{r['descarga']}"
        obra["version"] = r["version"]
    if r["tipo"] == "plugin":
        obra["headline"] = r["titulo"]
    jsonld = {"@context": "https://schema.org", "@graph": [
        obra,
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "hbtdata", "item": f"{DOMINIO}/"},
            {"@type": "ListItem", "position": 2, "name": "Recursos", "item": f"{DOMINIO}/recursos/"},
            {"@type": "ListItem", "position": 3, "name": r["titulo"], "item": url}]},
        {"@type": "Person", "@id": f"{DOMINIO}/#person", "name": "Henry Barrios Thornhill", "url": f"{DOMINIO}/"},
    ]}
    cuerpo = {"prompt": lambda: cuerpo_prompt(r), "skill": lambda: cuerpo_skill(r, raiz),
              "plugin": lambda: cuerpo_plugin(r), "pdf": lambda: cuerpo_pdf(r, raiz)}[r["tipo"]]()

    parecidos = [x for x in lista if x is not r and x["tema"] == r["tema"]] + \
                [x for x in lista if x is not r and x["tema"] != r["tema"]]
    mas = "".join(f'<li><a href="{raiz}recursos/{x["slug"]}/"><small>{e(datos["tipos"][x["tipo"]]["uno"])}</small>{e(x["titulo"])}</a></li>'
                  for x in parecidos[:4])

    return (cabeza(titulo, r["resumen"], url, jsonld, raiz, noindex=r["estado"] == "borrador")
            + '<body class="ficha-pagina">\n' + iconos() + "\n" + barra(raiz, actual=r["tipo"], tipos=datos["tipos"]) + f"""
<main>
  <section class="ficha-cabeza">
    <div class="envuelve">
      <p class="miga mono"><a href="{raiz}recursos/"><b>//</b>recursos</a><span>/</span><a href="{raiz}recursos/?tipo={r['tipo']}#lista">{e(tipo['nombre'])}</a><span>/</span><a href="{raiz}recursos/?tema={r['tema']}#lista">{e(tema)}</a></p>
      <h1 class="titular">{e(r['titulo'])}</h1>
      <p class="entrada">{e(r['resumen'])}</p>
      <div class="datos-ficha"><span class="mono">Actualizado el {fecha_larga(r['fecha'])}</span>{etiqueta_borrador(r)}</div>
    </div>
  </section>

  <div class="envuelve cuerpo">
    <article>
{cuerpo}    </article>
    <aside class="lateral">
      <div class="caja">
        <span class="mono">Compartir</span>
        <p>Este recurso tiene su propio enlace. Pásaselo a quien le pueda servir.</p>
        <button class="copiar grande" type="button" data-copiar="enlace"><svg class="ico trazo"><use href="#i-enlace"/></svg><span>Copiar enlace</span></button>
      </div>
      <div class="caja">
        <span class="mono">Más recursos</span>
        <ul class="mas">{mas}</ul>
        <a class="enlace" href="{raiz}recursos/">Ver todos</a>
      </div>
      <div class="caja">
        <span class="mono">¿Te ha servido?</span>
        <p>Cuento cómo lo uso y qué subo nuevo en mis redes.</p>
        <div class="redes-botones">{"".join(f'<a class="pildora" href="{u}"><svg class="ico"><use href="#{i}"/></svg>{n}</a>' for n, u, i in REDES)}</div>
      </div>
    </aside>
  </div>
  <p class="estado-copia" role="status" aria-live="polite"></p>
</main>

""" + pie(raiz) + f"""
<script src="{raiz}recursos/recursos.js"></script>
</body>
</html>
""")


# ---------- sitemap y llms.txt (solo al publicar) ----------

def actualiza_sitemap(lista):
    ruta = RAIZ / "sitemap.xml"
    xml = ruta.read_text(encoding="utf-8")
    xml = re.sub(r"\s*<!-- recursos -->.*?<!-- /recursos -->", "", xml, flags=re.S)
    hoy = date.today().isoformat()
    urls = [f"  <url>\n    <loc>{DOMINIO}/recursos/</loc>\n    <lastmod>{hoy}</lastmod>\n  </url>"]
    urls += [f"  <url>\n    <loc>{DOMINIO}/recursos/{r['slug']}/</loc>\n    <lastmod>{r['fecha']}</lastmod>\n  </url>" for r in lista]
    bloque = "\n  <!-- recursos -->\n" + "\n".join(urls) + "\n  <!-- /recursos -->\n"
    ruta.write_text(xml.rstrip().removesuffix("</urlset>").rstrip() + bloque + "</urlset>\n", encoding="utf-8")


def actualiza_llms(lista, datos):
    ruta = RAIZ / "llms.txt"
    txt = ruta.read_text(encoding="utf-8")
    txt = re.sub(r"\n## Recursos de Claude\n.*?(?=\n## |\Z)", "\n", txt, flags=re.S)
    lineas = [f"- **{r['titulo']}** ({datos['tipos'][r['tipo']]['uno'].lower()}): {r['resumen']} {DOMINIO}/recursos/{r['slug']}/" for r in lista]
    bloque = ("\n## Recursos de Claude\n\n"
              f"{DOMINIO}/recursos/ · Prompts, skills, conectores y guías en PDF de Claude que usa Henry Barrios Thornhill. "
              "Gratis, sin registro. Página personal sin relación con Anthropic.\n\n" + "\n".join(lineas) + "\n")
    txt = txt.replace("\n## Cómo trabajo", bloque + "\n## Cómo trabajo", 1)
    ruta.write_text(txt, encoding="utf-8")


# ---------- principal ----------

def main():
    publicar = "--publicar" in sys.argv
    datos = json.loads((Path(__file__).parent / "recursos.json").read_text(encoding="utf-8"))
    lista = [r for r in datos["recursos"] if not publicar or r["estado"] == "publicado"]

    slugs = [r["slug"] for r in datos["recursos"]]
    if len(slugs) != len(set(slugs)):
        sys.exit("Hay slugs repetidos en recursos.json")
    for r in datos["recursos"]:
        if r["tipo"] not in datos["tipos"] or r["tema"] not in datos["temas"]:
            sys.exit(f"Tipo o tema desconocido en «{r['slug']}»")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", r["slug"]) or r["slug"] == "descargas":
            sys.exit(f"Slug no válido: «{r['slug']}»")

    # borra lo generado antes (solo carpetas con la marca)
    for d in SALIDA.iterdir():
        indice = d / "index.html"
        if d.is_dir() and indice.exists() and MARCA in indice.read_text(encoding="utf-8"):
            shutil.rmtree(d)

    (SALIDA / "index.html").write_text(portada(datos, lista), encoding="utf-8")
    for r in lista:
        carpeta = SALIDA / r["slug"]
        carpeta.mkdir(exist_ok=True)
        (carpeta / "index.html").write_text(ficha(r, datos, lista), encoding="utf-8")

    if publicar:
        actualiza_sitemap(lista)
        actualiza_llms(lista, datos)
    borradores = sum(r["estado"] == "borrador" for r in lista)
    print(f"{len(lista)} recursos generados ({borradores} borradores)" + (" · sitemap.xml y llms.txt actualizados" if publicar else ""))


if __name__ == "__main__":
    main()
