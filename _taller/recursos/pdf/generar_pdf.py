#!/usr/bin/env python3
"""Maqueta las guías en PDF de /recursos/ en HTML con la marca y las pasa a PDF con Playwright.

    python3 _taller/recursos/pdf/generar_pdf.py

Para cada recurso de tipo «pdf» en recursos.json genera:
  recursos/descargas/<slug>.pdf   la guía (A4)
  recursos/descargas/<slug>.png   la portada, para la ficha
y, además, assets/og-recursos.png (imagen para compartir 1200×630).
El HTML intermedio queda en _taller/recursos/pdf/salida/ para revisarlo en el navegador.
Las fuentes van en local (fuentes/, licencia OFL), así el PDF sale igual sin conexión.
Después, vuelve a ejecutar generar.py para que la ficha muestre el tamaño y la portada.
"""
import json
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
DESCARGAS = RAIZ / "recursos" / "descargas"
SALIDA = AQUI / "salida"
DOMINIO = "hbtdata.es"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
FRASE = ("Henry Barrios Thornhill (hbtdata) es analista de datos de Gran Canaria que programa con IA "
         "y autor de Abre tu sobre (abretusobre.es).")
AVISO = "Guía personal, sin relación con Anthropic. «Claude» se nombra solo para describir para qué sirve cada prompt."


def e(t):
    return escape(str(t), quote=True)


def fecha_larga(iso):
    a, m, d = (int(x) for x in iso.split("-"))
    return f"{d} de {MESES[m - 1]} de {a}"


VOLCAN = """<svg viewBox="0 0 100 100" class="volcan"><rect x="0" y="68" width="16" height="32" rx="4.5" fill="currentColor"/><rect x="21" y="38" width="16" height="62" rx="4.5" fill="currentColor"/><rect x="42" y="0" width="16" height="100" rx="4.5" fill="#F0A840"/><rect x="63" y="20" width="16" height="80" rx="4.5" fill="currentColor"/><rect x="84" y="54" width="16" height="46" rx="4.5" fill="currentColor"/></svg>"""

ESTILO = """
@font-face{font-family:Poppins;font-weight:200;src:url(fuentes/poppins-latin-200-normal.woff2)}
@font-face{font-family:Poppins;font-weight:300;src:url(fuentes/poppins-latin-300-normal.woff2)}
@font-face{font-family:Poppins;font-weight:400;src:url(fuentes/poppins-latin-400-normal.woff2)}
@font-face{font-family:Poppins;font-weight:500;src:url(fuentes/poppins-latin-500-normal.woff2)}
@font-face{font-family:Poppins;font-weight:600;src:url(fuentes/poppins-latin-600-normal.woff2)}
@font-face{font-family:'JetBrains Mono';font-weight:400;src:url(fuentes/jetbrains-mono-latin-400-normal.woff2)}
@font-face{font-family:'JetBrains Mono';font-weight:500;src:url(fuentes/jetbrains-mono-latin-500-normal.woff2)}
@page{size:A4;margin:0}
:root{--osc:#0A3440;--fondo:#04161C;--claro:#F7F3EC;--ocre:#F0A840;--ocre2:#C46E14;--suave:#96D6D6;
  --mono:'JetBrains Mono',monospace;--sans:Poppins,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
html,body{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-family:var(--sans);font-weight:300;color:var(--osc);font-size:10.5pt;line-height:1.6}
.pagina{width:210mm;height:297mm;position:relative;overflow:hidden;background:var(--claro);padding:22mm 20mm 26mm;page-break-after:always;break-after:page}
.pagina:last-child{page-break-after:auto;break-after:auto}
.oscura{background:var(--osc);color:var(--claro)}
.mono{font-family:var(--mono);font-size:7.5pt;font-weight:500;letter-spacing:.14em;text-transform:uppercase}
.mono b{color:var(--ocre2);font-weight:500}
.oscura .mono b{color:var(--ocre)}
.titular{font-weight:200;text-transform:uppercase;line-height:1;letter-spacing:-.01em}
.pie{position:absolute;left:20mm;right:20mm;bottom:12mm;display:flex;justify-content:space-between;align-items:center;border-top:.5pt solid rgba(10,52,64,.25);padding-top:3.5mm;font-family:var(--mono);font-size:6.8pt;letter-spacing:.12em;text-transform:uppercase;color:rgba(10,52,64,.7)}
.oscura .pie{border-color:rgba(247,243,236,.25);color:rgba(247,243,236,.7)}
.pie b{color:var(--ocre2);font-weight:500}

/* portada */
.portada{display:flex;flex-direction:column;padding:20mm}
.portada .arriba{display:flex;justify-content:space-between;align-items:center}
.firma{display:flex;align-items:center;gap:3mm}
.volcan{width:9mm;height:9mm;color:var(--claro)}
.portada .centro{margin-top:auto}
.portada h1{font-size:46pt;margin:8mm 0 7mm;max-width:15ch}
.portada .sub{font-size:13pt;max-width:38ch;color:rgba(247,243,236,.78)}
.portada .abajo{margin-top:16mm;display:flex;justify-content:space-between;align-items:flex-end;border-top:.5pt solid rgba(247,243,236,.3);padding-top:5mm}
.portada .rejilla{position:absolute;right:-30mm;top:40mm;width:150mm;height:150mm;opacity:.5;
  background-image:radial-gradient(circle,rgba(150,214,214,.55) .6pt,transparent .9pt);background-size:5mm 5mm;
  -webkit-mask-image:radial-gradient(circle at 60% 40%,#000 20%,transparent 68%);mask-image:radial-gradient(circle at 60% 40%,#000 20%,transparent 68%)}
.sello-muestra{position:absolute;top:58mm;right:20mm;border:1pt dashed var(--ocre);color:var(--ocre);padding:2mm 4mm;border-radius:20mm}

/* índice */
.indice h2,.intro h2{font-size:30pt;margin:5mm 0 12mm}
.indice ol{list-style:none;border-top:.5pt solid rgba(10,52,64,.25)}
.indice li{display:grid;grid-template-columns:14mm 1fr auto;gap:4mm;align-items:baseline;padding:4.2mm 0;border-bottom:.5pt solid rgba(10,52,64,.25)}
.indice li .n{font-family:var(--mono);font-size:8pt;color:var(--ocre2)}
.indice li .t{font-size:12pt;font-weight:400}
.indice li .t small{display:block;font-family:var(--mono);font-size:6.8pt;letter-spacing:.12em;text-transform:uppercase;color:rgba(10,52,64,.6);font-weight:500}
.indice li .p{font-family:var(--mono);font-size:9pt}

/* introducción */
.intro p{font-size:11pt;margin-bottom:4mm;max-width:60ch}
.intro .tres{display:grid;grid-template-columns:repeat(3,1fr);gap:5mm;margin-top:10mm}
.intro .tres div{border-top:1.5pt solid var(--osc);padding-top:3mm}
.intro .tres h3{font-size:11pt;font-weight:500;margin:2mm 0 1.5mm}
.intro .tres p{font-size:9pt;color:rgba(10,52,64,.8)}

/* ficha de prompt */
.ficha h2{font-size:24pt;margin:4mm 0 4mm;max-width:20ch}
.ficha .resumen{font-size:11pt;color:rgba(10,52,64,.8);max-width:60ch;margin-bottom:6mm}
.ficha h3{font-family:var(--mono);font-size:7.5pt;font-weight:500;letter-spacing:.14em;text-transform:uppercase;margin:5mm 0 2.5mm;color:var(--ocre2)}
.ficha ul{list-style:none}
.ficha li{display:flex;gap:2.5mm;font-size:9.5pt;margin-bottom:1.2mm}
.ficha li::before{content:"";flex:none;width:1.4mm;height:1.4mm;border-radius:50%;background:var(--osc);margin-top:1.9mm}
.caja-prompt{background:var(--osc);color:var(--claro);border-radius:3mm;padding:5mm 6mm;font-family:var(--mono);font-size:8.2pt;line-height:1.65;white-space:pre-wrap}
.caja-prompt .cab{display:flex;justify-content:space-between;margin-bottom:3mm;padding-bottom:2.5mm;border-bottom:.5pt solid rgba(247,243,236,.25);font-size:6.8pt;letter-spacing:.14em;text-transform:uppercase;color:rgba(247,243,236,.7);white-space:normal}
.caja-prompt .cab b{color:var(--ocre);font-weight:500}
.caja-ejemplo{border:.5pt solid rgba(10,52,64,.3);border-radius:3mm;padding:4mm 5mm;font-size:8.6pt;line-height:1.55;white-space:pre-wrap;color:rgba(10,52,64,.85)}

/* cierre */
.cierre{display:flex;flex-direction:column}
.cierre h2{font-size:34pt;margin:6mm 0 8mm;max-width:14ch}
.cierre .url{font-family:var(--mono);font-size:15pt;color:var(--ocre);margin-bottom:10mm}
.cierre p{max-width:58ch;color:rgba(247,243,236,.8);margin-bottom:3.5mm}
.cierre .final{margin-top:auto;border-top:.5pt solid rgba(247,243,236,.3);padding-top:5mm;font-size:8.5pt}
"""


def pie(r, n):
    return (f'<div class="pie"><span><b>{DOMINIO}</b>/recursos · {e(r["titulo"])} · v{e(r["version"])}</span>'
            f'<span>{n:02d}</span></div>')


def html_guia(r, datos):
    prompts = [x for x in datos["recursos"] if x["tipo"] == "prompt" and x["tema"] in r.get("pdf_temas", [])]
    muestra = r["estado"] == "borrador"
    fecha = fecha_larga(r["fecha"])
    paginas = []

    paginas.append(f"""<section class="pagina oscura portada">
  <div class="rejilla"></div>
  <div class="arriba"><span class="firma">{VOLCAN}<span class="mono">hbt<b>data</b> / recursos</span></span><span class="mono">Guía en PDF · gratis</span></div>
  {'<span class="sello-muestra mono">Muestra de diseño</span>' if muestra else ''}
  <div class="centro">
    <p class="mono"><b>//</b>recursos de Claude</p>
    <h1 class="titular">{e(r['titulo'])}</h1>
    <p class="sub">{len(prompts)} prompts probados, con para qué sirve cada uno y un ejemplo de lo que sale.</p>
    <div class="abajo"><span class="mono">Henry Barrios Thornhill<br>Versión {e(r['version'])} · {fecha}</span><span class="mono"><b>{DOMINIO}</b>/recursos</span></div>
  </div>
</section>""")

    # páginas: 1 portada, 2 índice, 3 cómo usarla, 4… prompts, última cierre
    entradas = [("Cómo usar esta guía", "Antes de empezar", 3)]
    entradas += [(p["titulo"], datos["temas"][p["tema"]], 4 + i) for i, p in enumerate(prompts)]
    entradas += [("Más recursos", "Para seguir", 4 + len(prompts))]
    filas = "".join(f'<li><span class="n">{i + 1:02d}</span><span class="t"><small>{e(s)}</small>{e(t)}</span><span class="p">{p:02d}</span></li>'
                    for i, (t, s, p) in enumerate(entradas))
    paginas.append(f"""<section class="pagina indice">
  <p class="mono"><b>//</b>índice</p>
  <h2 class="titular">Qué hay dentro</h2>
  <ol>{filas}</ol>
  {pie(r, 2)}
</section>""")

    paginas.append(f"""<section class="pagina intro">
  <p class="mono"><b>//</b>antes de empezar</p>
  <h2 class="titular">Cómo usar esta guía</h2>
  <p>Cada página es un prompt que uso de verdad. Lleva para qué sirve, el texto para copiar y un ejemplo de la respuesta, para que sepas qué esperar.</p>
  <p>Los prompts funcionan en cualquier versión de Claude. Donde veas algo entre corchetes, como [canal o negocio], cámbialo por lo tuyo antes de enviarlo.</p>
  <p>Copiar desde un PDF a veces rompe los saltos de línea. Cada prompt tiene su página en {DOMINIO}/recursos con un botón de copiar.</p>
  <div class="tres">
    <div><span class="mono"><b>01</b></span><h3>Copia</h3><p>Desde la web, con un clic, o desde aquí.</p></div>
    <div><span class="mono"><b>02</b></span><h3>Adapta</h3><p>Cambia lo que va entre corchetes y añade tu contexto.</p></div>
    <div><span class="mono"><b>03</b></span><h3>Revisa</h3><p>Claude se equivoca. Comprueba las cifras antes de usarlas.</p></div>
  </div>
  {pie(r, 3)}
</section>""")

    for i, p in enumerate(prompts):
        ejemplo = (f'<h3>Un ejemplo de lo que sale</h3><div class="caja-ejemplo">{e(p["ejemplo"])}</div>'
                   if p.get("ejemplo") else "")
        paginas.append(f"""<section class="pagina ficha">
  <p class="mono"><b>{i + 1:02d}</b> / {e(datos['temas'][p['tema']])}</p>
  <h2 class="titular">{e(p['titulo'])}</h2>
  <p class="resumen">{e(p['resumen'])}</p>
  <h3>Para qué sirve</h3>
  <ul>{''.join(f'<li>{e(x)}</li>' for x in p['para_que'])}</ul>
  <h3>El prompt</h3>
  <div class="caja-prompt"><div class="cab"><span><b>&gt;_</b> prompt</span><span>{DOMINIO}/recursos/{p['slug']}</span></div>{e(p['prompt'])}</div>
  {ejemplo}
  {pie(r, 4 + i)}
</section>""")

    paginas.append(f"""<section class="pagina oscura cierre">
  <p class="mono"><b>//</b>para seguir</p>
  <h2 class="titular">Hay más en la web.</h2>
  <p class="url">{DOMINIO}/recursos</p>
  <p>Prompts, skills, conectores y otras guías, cada uno con su página y su botón de copiar. Gratis y sin registro.</p>
  <p>Si echas algo en falta, pídemelo en TikTok o Instagram: @hbtdata.</p>
  <div class="final">
    <p>{e(FRASE)}</p>
    <p>{e(AVISO)}</p>
    <p class="mono" style="margin-top:4mm">Versión {e(r['version'])} · {fecha}</p>
  </div>
  {pie(r, 4 + len(prompts))}
</section>""")

    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{e(r['titulo'])} · hbtdata</title>
<style>{ESTILO}</style></head><body>
{''.join(paginas)}
</body></html>"""


def html_og():
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{ESTILO}
body{{width:1200px;height:630px;background:#04161C;color:var(--claro);overflow:hidden;position:relative;font-size:16px}}
.rejilla{{position:absolute;right:-80px;top:-60px;width:760px;height:760px;
  background-image:radial-gradient(circle,rgba(150,214,214,.55) 1.6px,transparent 2.4px);background-size:20px 20px;
  -webkit-mask-image:radial-gradient(circle at 55% 50%,#000 18%,transparent 62%)}}
.caja{{position:absolute;left:80px;top:78px;right:80px;bottom:70px;display:flex;flex-direction:column}}
.firma .volcan{{width:44px;height:44px}}
.mono{{font-size:15px}}
h1{{font-size:84px;margin:26px 0 22px;max-width:12ch}}
p.s{{font-size:26px;color:rgba(247,243,236,.75);max-width:30ch}}
.abajo{{margin-top:auto;display:flex;justify-content:space-between}}
</style></head><body><div class="rejilla"></div><div class="caja">
<span class="firma">{VOLCAN}<span class="mono">hbt<b>data</b> / recursos</span></span>
<h1 class="titular">Recursos de Claude</h1>
<p class="s">Prompts, skills, conectores y guías en PDF que uso de verdad. Gratis.</p>
<div class="abajo"><span class="mono">Henry Barrios Thornhill</span><span class="mono"><b>hbtdata.es</b>/recursos</span></div>
</div></body></html>"""


def main():
    datos = json.loads((AQUI.parent / "recursos.json").read_text(encoding="utf-8"))
    DESCARGAS.mkdir(parents=True, exist_ok=True)
    SALIDA.mkdir(exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        pag = nav.new_page()
        for r in (x for x in datos["recursos"] if x["tipo"] == "pdf"):
            html = AQUI / f"{r['slug']}.html"            # junto a fuentes/ para que carguen
            html.write_text(html_guia(r, datos), encoding="utf-8")
            pag.goto(html.as_uri(), wait_until="load")
            pag.evaluate("document.fonts.ready")
            destino = RAIZ / "recursos" / r["descarga"]
            pag.pdf(path=str(destino), format="A4", print_background=True, prefer_css_page_size=True)
            # portada en PNG para la ficha
            pag.set_viewport_size({"width": 794, "height": 1123})
            png = destino.with_suffix(".png")
            pag.locator(".portada").screenshot(path=str(png))
            try:                                         # se muestra a 150 px: basta con 300 de ancho
                from PIL import Image
                im = Image.open(png); im.thumbnail((300, 425)); im.save(png, optimize=True)
            except ImportError:
                pass
            (SALIDA / html.name).write_text(html.read_text(encoding="utf-8"), encoding="utf-8")
            html.unlink()
            print(f"{destino.relative_to(RAIZ)} ({destino.stat().st_size // 1024} KB)")
        og = AQUI / "og.html"
        og.write_text(html_og(), encoding="utf-8")
        pag.set_viewport_size({"width": 1200, "height": 630})
        pag.goto(og.as_uri(), wait_until="load")
        pag.evaluate("document.fonts.ready")
        pag.screenshot(path=str(RAIZ / "assets" / "og-recursos.png"))
        og.unlink()
        print("assets/og-recursos.png")
        nav.close()


if __name__ == "__main__":
    main()
