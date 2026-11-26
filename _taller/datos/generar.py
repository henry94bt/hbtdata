#!/usr/bin/env python3
"""Genera hbtdata.es/datos/ con los precios del día del Ministerio.

    python3 _taller/datos/generar.py                 # descarga, actualiza el histórico y rehace las páginas
    python3 _taller/datos/generar.py --si-falta      # lo mismo, pero no hace nada si ya están los precios de hoy
    python3 _taller/datos/generar.py --sin-descarga  # rehace las páginas con datos/gasolina/precios.csv
    python3 _taller/datos/generar.py --sembrar RUTA  # antes de nada, rellena el histórico con el CSV de
                                                     # canarias-gas-tracker (historico_precios.csv)
    --sin-esperas                                    # reintentos seguidos (para probar en local)

Salida: datos/index.html, datos/gasolina/index.html, datos/gasolina/<isla>/index.html,
datos/gasolina/precios.csv y datos/gasolina/historico.csv; además el bloque «datos» de sitemap.xml
y la sección «Datos de Canarias» de llms.txt. Lo lanza cada mañana .github/workflows/datos-gasolina.yml.
Solo biblioteca estándar.
"""
import re
import statistics
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fuente_gasolina as fg  # noqa: E402
from comun import (DE_ISLA, ISLAS, MESES, NOMBRE_ISLA, ahora, centimos, enumera, fecha_con_dia,  # noqa: E402
                   fecha_corta, fecha_larga, precio)
from graficos import lineas, mapa, puntos  # noqa: E402
from plantilla import (DOMINIO, MARCA, PERSONA, PERSONA_COMPLETA, barra, cabeza, e, iconos, migas,  # noqa: E402
                       pie, scripts)

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "datos"
GASOLINA = DATOS / "gasolina"
PRECIOS = GASOLINA / "precios.csv"
HISTORICO = GASOLINA / "historico.csv"
CODIGO = "https://github.com/henry94bt/hbtdata/tree/main/_taller/datos"
TRACKER = "https://henry94bt.github.io/canarias-gas-tracker/"
GEOPORTAL = "https://geoportalgasolineras.es/"
MINISTERIO = "Ministerio para la Transición Ecológica y el Reto Demográfico"
COMBUSTIBLES = [("g95", "Gasolina 95", "la gasolina 95"), ("diesel", "Diésel", "el diésel")]
FUENTE_ORIGEN = {"@type": "Dataset", "name": "Precios de carburantes en las estaciones de servicio",
                 "url": GEOPORTAL,
                 "publisher": {"@type": "GovernmentOrganization", "name": MINISTERIO}}


# ---------- textos que se repiten ----------

def fuente(fecha, extra=""):
    return (f'Fuente: <a href="{GEOPORTAL}">{MINISTERIO}</a> (Geoportal de carburantes). '
            f'Precios del {fecha:%d/%m/%Y}, {fecha:%H:%M} (hora canaria){extra}. Elaboración: hbtdata.')


def sello_fecha(fecha):
    return (f'<p class="sello-fecha mono"><span class="vivo" aria-hidden="true"></span>'
            f'<span>Precios del {fecha_con_dia(fecha)}, {fecha:%H:%M}</span><span>Se actualiza cada mañana</span></p>')


def ellos(n):
    return "la gasolinera" if n == 1 else f"las {n} gasolineras"


def donde_minimo(puestos, con_isla=False):
    primeros = [s for p, s in puestos if p == 1]
    if len(primeros) == 1:
        s = primeros[0]
        lugar = s["municipio"] + (f", {NOMBRE_ISLA[s['isla']]}" if con_isla else "")
        return f"en <strong>{e(s['rotulo'])}</strong> ({e(lugar)})"
    municipios = list(dict.fromkeys(s["municipio"] for s in primeros))
    if len(municipios) > 3:
        lugar = f"{', '.join(municipios[:2])} y otros {len(municipios) - 2} municipios"
    else:
        lugar = enumera(municipios)
    return f"en {len(primeros)} gasolineras con el mismo precio ({e(lugar)})"


def deposito(dif_litro, litros=50):
    euros = dif_litro * litros
    return f"{round(euros)} €" if euros >= 2 else centimos(euros)


def frente_a(valor, referencia, nombre="la de Canarias"):
    d = valor - referencia
    if abs(d) < 0.0005:
        return f"igual que {nombre}"
    return f"{centimos(d)} {'menos' if d < 0 else 'más'} que {nombre} ({precio(referencia)})"


def preguntas_html(extra=()):
    items = list(extra) + [
        ("¿De dónde salen los precios?",
         f'Del <a href="{GEOPORTAL}">Geoportal de carburantes</a> del {MINISTERIO}, al que las gasolineras '
         'comunican sus precios. Se descargan cada mañana de su servicio de datos abiertos, sin tocarlos.'),
        ("¿Cada cuánto se actualiza esta página?",
         "Una vez al día, por la mañana. Arriba tienes la fecha y la hora exactas de los precios. Una gasolinera "
         "puede cambiar el precio durante el día: el que manda es el del surtidor."),
        ("¿Por qué la mediana y no la media?",
         "La mediana es el precio que deja la mitad de las gasolineras por debajo y la otra mitad por encima. "
         "Una gasolinera con un precio muy raro mueve la media, pero casi no mueve la mediana."),
        ("¿Qué combustibles salen?",
         "Gasolina 95 (la E5, la de casi todos los coches de gasolina) y diésel (gasóleo A). "
         "Las gasolineras que no publican precio de uno de los dos no entran en ese ranking."),
    ]
    html = "".join(f"<details><summary>{p}</summary><p>{r}</p></details>" for p, r in items)
    jsonld = {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": p, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", r)}}
        for p, r in items]}
    return f'<div class="preguntas">{html}</div>', jsonld


def selector():
    return """<div class="filtros" role="group" aria-label="Combustible">
  <div class="envuelve">
    <span class="mono">Combustible</span>
    <button class="chip" type="button" data-campo="combustible" data-valor="g95" aria-pressed="true">Gasolina 95</button>
    <button class="chip" type="button" data-campo="combustible" data-valor="diesel" aria-pressed="false">Diésel</button>
  </div>
</div>
"""


def bloque(c, html):
    return f'<div class="solo-{c}">{html}</div>'


def islas_enlaces(raiz, actual=None):
    return '<ul class="islas-enlaces">' + "".join(
        f'<li><a href="{raiz}datos/gasolina/{s}/"{" aria-current=\"page\"" if s == actual else ""}>{n}</a></li>'
        for s, n in ISLAS) + "</ul>"


def serie(historico, ambito, c):
    return [(r["fecha"], r["mediana"]) for r in historico if r["ambito"] == ambito and r["combustible"] == c]


def cambio_texto(puntos_serie, quien, nombre_comb):
    if len(puntos_serie) < 2:
        return ""
    (f0, v0), (f1, v1) = puntos_serie[0], puntos_serie[-1]
    d = v1 - v0
    verbo = "no ha cambiado" if abs(d) < 0.0005 else f"ha {'subido' if d > 0 else 'bajado'} {centimos(d)}"
    txt = (f"Desde el {fecha_larga(f0)}, la mediana de {nombre_comb} en {quien} {verbo} "
           f"(de {precio(v0)} a {precio(v1)}).")
    objetivo = (date.fromisoformat(f1) - timedelta(days=30)).isoformat()
    antes = [p for p in puntos_serie if p[0] <= objetivo]
    if antes:
        d30 = v1 - antes[-1][1]
        txt += (" En los últimos 30 días, " +
                ("sin cambios." if abs(d30) < 0.0005 else f"{'+' if d30 > 0 else '−'}{centimos(d30)}."))
    return txt


def tabla_meses(series_nombres):
    """series_nombres: [(nombre, puntos)] → tabla con la mediana de las medianas diarias de cada mes."""
    meses = defaultdict(dict)
    for nombre, pts in series_nombres:
        por_mes = defaultdict(list)
        for f, v in pts:
            por_mes[f[:7]].append(v)
        for m, vs in por_mes.items():
            meses[m][nombre] = statistics.median(vs)
    cab = "".join(f'<th class="num" scope="col">{e(n)}</th>' for n, _ in series_nombres)
    filas = ""
    for m in sorted(meses, reverse=True):
        a, mm = m.split("-")
        celdas = "".join(f'<td class="num">{precio(meses[m][n]) if n in meses[m] else "–"}</td>' for n, _ in series_nombres)
        filas += f'<tr><th scope="row">{MESES[int(mm) - 1].capitalize()} {a}</th>{celdas}</tr>'
    return (f'<details class="datos-tabla"><summary>Ver los datos por meses</summary><div class="tabla-envuelve"><table>'
            f'<caption>Mediana del mes (de las medianas de cada día)</caption>'
            f'<thead><tr><th scope="col">Mes</th>{cab}</tr></thead><tbody>{filas}</tbody></table></div></details>')


def tabla_ranking(puestos, c, nombre_comb, quien):
    filas = ""
    for p, s in puestos:
        horario = f" · {e(s['horario'])}" if s.get("horario") else ""
        mapa_url = f"https://www.google.com/maps/search/?api=1&query={s['lat']},{s['lon']}"
        filas += (f'<tr class="{"primero" if p == 1 else ""}"><td class="puesto">{p}</td>'
                  f'<td><strong>{e(s["rotulo"])}</strong><small>{e(s["direccion"])} · {e(s["municipio"])}{horario}</small></td>'
                  f'<td class="num"><strong>{precio(s[c])}</strong><small><a class="como-llegar" href="{mapa_url}">Cómo llegar</a></small></td></tr>')
    return (f'<div class="tabla-envuelve"><table><caption>{e(nombre_comb)} · las más baratas {e(quien)}</caption>'
            f'<thead><tr><th scope="col">#</th><th scope="col">Gasolinera</th><th scope="col" class="num">€/litro</th></tr></thead>'
            f'<tbody>{filas}</tbody></table></div>')


def dataset(url, nombre, descripcion, lugar, historico, fecha, ambito):
    fechas = sorted({r["fecha"] for r in historico if r["ambito"] == ambito})
    return {
        "@type": "Dataset", "@id": f"{url}#datos", "name": nombre, "description": descripcion, "url": url,
        "inLanguage": "es", "creator": PERSONA, "isAccessibleForFree": True,
        "isBasedOn": FUENTE_ORIGEN,
        "spatialCoverage": {"@type": "Place", "name": lugar},
        "temporalCoverage": f"{fechas[0]}/{fechas[-1]}" if fechas else fecha.date().isoformat(),
        "dateModified": fecha.isoformat(),
        "variableMeasured": ["Precio de la gasolina 95 E5 (euros por litro)", "Precio del gasóleo A (euros por litro)"],
        "keywords": ["gasolina", "diésel", "precio", "gasolineras", lugar.split(",")[0], "Canarias"],
        "distribution": [
            {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{DOMINIO}/datos/gasolina/precios.csv",
             "name": "Precios de hoy por gasolinera"},
            {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{DOMINIO}/datos/gasolina/historico.csv",
             "name": "Mediana diaria por isla desde abril de 2026"},
        ],
    }


def como_esta_hecho(raiz):
    return f"""  <section>
    <div class="envuelve dos">
      <div class="texto">
        <p class="mono"><b>//</b> Cómo está hecho</p>
        <p>Cada mañana, un proceso en GitHub Actions descarga los precios del Ministerio, asigna cada gasolinera a su isla por el municipio, guarda la mediana del día y rehace estas páginas. Nadie toca los números a mano. El histórico empieza el 15 de abril de 2026 con los datos que ya guardaba el <a href="{TRACKER}">Canarias Gas Tracker</a>.</p>
        <p>Los datos, para que los uses: <a href="{raiz}datos/gasolina/precios.csv">precios de hoy por gasolinera</a> y <a href="{raiz}datos/gasolina/historico.csv">mediana diaria por isla</a> (CSV). El código está en <a href="{CODIGO}">GitHub</a>.</p>
      </div>
      <div class="texto">
        <p class="mono"><b>//</b> ¿Lo quieres para tu negocio?</p>
        <p>Este tipo de página (datos públicos que se actualizan solos, con gráfico, fecha y fuente) se puede hacer con los datos de cualquier sector. <a href="{raiz}webs/">Mira lo que hago para negocios</a> o escríbeme desde el <a href="{raiz}#contacto">formulario de contacto</a>.</p>
      </div>
    </div>
  </section>
"""


# ---------- página de una isla ----------

def pagina_isla(isla, estaciones, historico, fecha):
    raiz = "../../../"
    nombre = NOMBRE_ISLA[isla]
    url = f"{DOMINIO}/datos/gasolina/{isla}/"
    propias = [s for s in estaciones if s["isla"] == isla]
    dia = fecha_con_dia(fecha)

    r = {c: fg.ranking(propias, c) for c, _, _ in COMBUSTIBLES}
    med = {c: fg.mediana(propias, c) for c, _, _ in COMBUSTIBLES}
    med_can = {c: fg.mediana(estaciones, c) for c, _, _ in COMBUSTIBLES}
    n = {c: sum(s[c] is not None for s in propias) for c, _, _ in COMBUSTIBLES}
    minimo = {c: r[c][0][1][c] for c, _, _ in COMBUSTIBLES}

    titulo = f"¿Dónde está la gasolina más barata de {nombre} hoy? · hbtdata"
    descripcion = (f"Precios del {fecha_larga(fecha)}: la gasolina 95 más barata de {nombre} está a "
                   f"{precio(minimo['g95'])} el litro y el diésel a {precio(minimo['diesel'])}. Ranking de "
                   f"gasolineras, mapa y evolución, con datos del Ministerio cada día.")
    entrada = (f"Precios del {dia}: la gasolina 95 más barata de {nombre} está a <strong>{precio(minimo['g95'])}</strong> "
               f"el litro, {donde_minimo(r['g95'])}. La mediana de {ellos(n['g95'])} de la isla es "
               f"<strong>{precio(med['g95'])}</strong>: la mitad la vende a ese precio o más barata.")

    def cifra_min(c, etiqueta, destaca):
        donde = donde_minimo(r[c])
        return (f'<div class="cifra{" destaca" if destaca else ""}"><span class="mono">{etiqueta}</span>'
                f'<span class="valor">{precio(minimo[c], "")}<small>€/l</small></span>'
                f'<p>{donde[0].upper() + donde[1:]}.</p></div>')

    cifras = (cifra_min("g95", "Gasolina 95 más barata", True)
              + cifra_min("diesel", "Diésel más barato", False)
              + f'<div class="cifra"><span class="mono">{nombre} frente a Canarias</span>'
                f'<span class="valor">{precio(med["g95"], "")}<small>€/l mediana</small></span>'
                f'<p>Gasolina 95: {frente_a(med["g95"], med_can["g95"], "la mediana de Canarias")}. '
                f'Diésel: <strong>{precio(med["diesel"])}</strong>, {frente_a(med["diesel"], med_can["diesel"], "la de Canarias")}.</p></div>')

    fu = fuente(fecha)
    ranking_html = mapa_html = municipios_html = evolucion_html = ""
    for c, nombre_c, art in COMBUSTIBLES:
        cuantas = len(r[c])
        nota = ""
        if cuantas > 10:
            nota = f'<p class="nota">Salen {cuantas} porque hay empate de precio en el último puesto.</p>'
        elif cuantas == n[c] and cuantas < 10:
            nota = f'<p class="nota">En {nombre} hay {n[c]} gasolineras con precio de {art}: salen todas.</p>'
        ranking_html += bloque(c, tabla_ranking(r[c], c, nombre_c, DE_ISLA[isla]) + nota)
        # si el ranking ya incluye todas (islas pequeñas), en el mapa se destaca solo la más barata
        destacadas, leyenda = r[c], None
        if cuantas >= n[c]:
            destacadas = [x for x in r[c] if x[0] == 1]
            leyenda = "La más barata" if len(destacadas) == 1 else f"Las {len(destacadas)} más baratas (mismo precio)"
        mapa_html += bloque(c, mapa(
            isla, propias, destacadas,
            f"Mapa de {nombre} con las gasolineras con precio de {art}; en ocre, {(leyenda or f'las {cuantas} más baratas').lower()}",
            fu, c, leyenda))

        filas = [{"etiqueta": m["municipio"], "valor": m["mediana"], "minimo": m["minimo"], "maximo": m["maximo"],
                  "nota": f'{m["n"]} gasolinera{"s" if m["n"] != 1 else ""}', "resaltar": i == 0,
                  "titulo": (f'{m["municipio"]}: mediana {precio(m["mediana"])}, de {precio(m["minimo"])} a {precio(m["maximo"])} '
                             f'({m["n"]} gasolinera{"s" if m["n"] != 1 else ""})')}
                 for i, m in enumerate(fg.por_municipio(propias, c))]
        barato = filas[0]
        texto_mun = ""
        if len(filas) > 1:
            texto_mun = (f'<p>Con {art}, el municipio con la mediana más baja es <strong>{e(barato["etiqueta"])}</strong> '
                         f'({precio(barato["valor"])}) y el de la más alta, <strong>{e(filas[-1]["etiqueta"])}</strong> '
                         f'({precio(filas[-1]["valor"])}). El punto es la mediana de cada municipio; la raya va de su gasolinera '
                         f'más barata a la más cara.</p>')
        municipios_html += bloque(c, f'<div class="cabeza-seccion"><h2>{nombre_c}: ¿en qué municipio {DE_ISLA[isla]} sale más barata?</h2>{texto_mun}</div>'
                                  + puntos(filas, f"{nombre_c}: mediana por municipio en {nombre}", fu,
                                           referencia=(med[c], f"Mediana {DE_ISLA[isla]} {precio(med[c], '')}")))

        s_isla, s_can = serie(historico, isla, c), serie(historico, "canarias", c)
        evolucion_html += bloque(c, f'<div class="cabeza-seccion"><h2>{nombre_c}: ¿ha subido o ha bajado en {nombre}?</h2>'
                                    f'<p>{cambio_texto(s_isla, nombre, art)} La línea ocre es {nombre}; la aguamarina, el conjunto de Canarias.</p></div>'
                                 + lineas([{"nombre": "Canarias", "clase": "base", "puntos": s_can},
                                           {"nombre": nombre, "clase": "acento", "puntos": s_isla}],
                                          f"{nombre_c}: mediana diaria en {nombre} y en Canarias desde el {fecha_larga(s_isla[0][0])}",
                                          fuente(fecha, f". Mediana de cada día; del 15/04 al 25/11/2026, histórico de Canarias Gas Tracker"))
                                 + tabla_meses([(nombre, s_isla), ("Canarias", s_can)]))

    faq_html, faq_ld = preguntas_html([
        (f"¿Cuál es la gasolinera más barata de {nombre} hoy?",
         f"Según los precios del {fecha_larga(fecha)}, la gasolina 95 más barata de {nombre} está a {precio(minimo['g95'])} "
         f"el litro, {re.sub(r'<[^>]+>', '', donde_minimo(r['g95']))}. El diésel más barato está a {precio(minimo['diesel'])}, "
         f"{re.sub(r'<[^>]+>', '', donde_minimo(r['diesel']))}."),
    ])
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": f"{url}#pagina", "url": url, "name": titulo, "description": descripcion,
         "inLanguage": "es", "isPartOf": {"@id": f"{DOMINIO}/#web"}, "author": PERSONA,
         "dateModified": fecha.isoformat(), "image": f"{DOMINIO}/assets/og-gasolina-{isla}.png",
         "about": {"@type": "Place", "name": f"{nombre}, Canarias, España"}, "mainEntity": {"@id": f"{url}#datos"}},
        dataset(url, f"Precios de la gasolina y el diésel en {nombre}",
                f"Precio de la gasolina 95 y del diésel en cada gasolinera de {nombre} y mediana diaria de la isla, a partir "
                f"de los datos abiertos del {MINISTERIO}. Se actualiza cada mañana.",
                f"{nombre}, Canarias, España", historico, fecha, isla),
        migas([("hbtdata", f"{DOMINIO}/"), ("Datos", f"{DOMINIO}/datos/"), ("Gasolina", f"{DOMINIO}/datos/gasolina/"),
               (nombre, url)]),
        faq_ld, PERSONA_COMPLETA,
    ]}

    return (cabeza(titulo, descripcion, url, jsonld, raiz, f"{DOMINIO}/assets/og-gasolina-{isla}.png")
            + "<body>\n" + iconos() + "\n" + barra(raiz, "datos/gasolina/") + f"""
<main id="contenido">
  <section class="cabecera">
    <div class="envuelve">
      <p class="miga mono"><a href="{raiz}datos/"><b>//</b>datos</a><span>/</span><a href="{raiz}datos/gasolina/">gasolina</a><span>/</span><span>{e(nombre.lower())}</span></p>
      <h1 class="titular">¿Dónde está la gasolina más barata {DE_ISLA[isla]}?</h1>
      <p class="entrada">{entrada}</p>
      {sello_fecha(fecha)}
      <div class="cifras">{cifras}</div>
    </div>
  </section>

{selector()}
  <section>
    <div class="envuelve">
      <div class="cabeza-seccion"><h2>Las gasolineras más baratas {DE_ISLA[isla]} hoy</h2>
        <p>Ordenadas por precio. En el mapa, en ocre; pasa por encima de un punto para ver la gasolinera y su precio.</p></div>
      <div class="dos">
        <div>{ranking_html}</div>
        <div>{mapa_html}</div>
      </div>
    </div>
  </section>

  <section class="panel">
    <div class="envuelve">{municipios_html}</div>
  </section>

  <section>
    <div class="envuelve">{evolucion_html}</div>
  </section>

  <section class="panel">
    <div class="envuelve">
      <div class="cabeza-seccion"><h2>¿Y en las otras islas?</h2>
        <p>La misma página para cada isla, y la <a href="{raiz}datos/gasolina/" style="color:var(--claro)">comparación entre islas</a>. Todas las gasolineras de Canarias en un mapa: <a href="{TRACKER}" style="color:var(--claro)">Canarias Gas Tracker</a>.</p></div>
      {islas_enlaces(raiz, isla)}
    </div>
  </section>

  <section>
    <div class="envuelve">
      <div class="cabeza-seccion"><h2>Preguntas</h2></div>
      {faq_html}
    </div>
  </section>

{como_esta_hecho(raiz)}</main>

""" + pie(raiz) + scripts(raiz))


# ---------- comparación entre islas ----------

def pagina_gasolina(estaciones, historico, fecha):
    raiz = "../../"
    url = f"{DOMINIO}/datos/gasolina/"
    por_isla = {s: [x for x in estaciones if x["isla"] == s] for s, _ in ISLAS}
    med = {(s, c): fg.mediana(por_isla[s], c) for s, _ in ISLAS for c, _, _ in COMBUSTIBLES}
    med_can = {c: fg.mediana(estaciones, c) for c, _, _ in COMBUSTIBLES}
    r_can = {c: fg.ranking(estaciones, c, 1) for c, _, _ in COMBUSTIBLES}
    orden = {c: sorted((s for s, _ in ISLAS), key=lambda s: med[(s, c)]) for c, _, _ in COMBUSTIBLES}
    barata, cara = orden["g95"][0], orden["g95"][-1]
    dif = med[(cara, "g95")] - med[(barata, "g95")]
    dia = fecha_con_dia(fecha)

    titulo = "¿En qué isla está más barata la gasolina? Precios de hoy en Canarias · hbtdata"
    descripcion = (f"Precios del {fecha_larga(fecha)}: la gasolina 95 está más barata en {NOMBRE_ISLA[barata]} "
                   f"(mediana {precio(med[(barata, 'g95')])}) y más cara en {NOMBRE_ISLA[cara]} ({precio(med[(cara, 'g95')])}). "
                   f"Gasolina y diésel en las siete islas, con datos del Ministerio cada día.")
    entrada = (f"Precios del {dia}: la gasolina 95 está más barata en <strong>{NOMBRE_ISLA[barata]}</strong> "
               f"(mediana de {precio(med[(barata, 'g95')])}) y más cara en <strong>{NOMBRE_ISLA[cara]}</strong> "
               f"({precio(med[(cara, 'g95')])}): {centimos(dif)} más por litro, unos {deposito(dif)} más por un depósito de 50 litros.")

    fila_min = r_can["g95"]
    cifras = (f'<div class="cifra destaca"><span class="mono">Isla más barata · gasolina 95</span>'
              f'<span class="valor">{NOMBRE_ISLA[barata]}</span><p>Mediana de <strong>{precio(med[(barata, "g95")])}</strong>, '
              f'{frente_a(med[(barata, "g95")], med_can["g95"], "la de Canarias")}.</p></div>'
              f'<div class="cifra"><span class="mono">Isla más cara · gasolina 95</span>'
              f'<span class="valor">{NOMBRE_ISLA[cara]}</span><p>Mediana de <strong>{precio(med[(cara, "g95")])}</strong>, '
              f'{frente_a(med[(cara, "g95")], med_can["g95"], "la de Canarias")}.</p></div>'
              f'<div class="cifra"><span class="mono">La más barata de Canarias</span>'
              f'<span class="valor">{precio(fila_min[0][1]["g95"], "")}<small>€/l</small></span>'
              f'<p>Gasolina 95 {donde_minimo(fila_min, con_isla=True)}.</p></div>')

    fu = fuente(fecha)
    islas_html = evol_html = ""
    for c, nombre_c, art in COMBUSTIBLES:
        filas = []
        for s in orden[c]:
            precios = [x[c] for x in por_isla[s] if x[c] is not None]
            filas.append({"etiqueta": NOMBRE_ISLA[s], "enlace": f"{raiz}datos/gasolina/{s}/", "valor": med[(s, c)],
                          "minimo": min(precios), "maximo": max(precios), "resaltar": s == orden[c][0],
                          "nota": f"{len(precios)} gasolinera{'s' if len(precios) != 1 else ''}",
                          "titulo": f"{NOMBRE_ISLA[s]}: mediana {precio(med[(s, c)])}, de {precio(min(precios))} a {precio(max(precios))}"})
        islas_html += bloque(c, f'<div class="cabeza-seccion"><h2>{nombre_c}: ¿en qué isla está más barata?</h2>'
                                f'<p>El punto es la mediana de cada isla; la raya va de su gasolinera más barata a la más cara. '
                                f'Toca una isla para ver sus gasolineras.</p></div>'
                             + puntos(filas, f"{nombre_c}: mediana por isla", fu,
                                      referencia=(med_can[c], f"Canarias {precio(med_can[c], '')}")))
        s_can = serie(historico, "canarias", c)
        evol_html += bloque(c, f'<div class="cabeza-seccion"><h2>{nombre_c}: ¿ha subido o ha bajado en Canarias?</h2>'
                               f'<p>{cambio_texto(s_can, "Canarias", art)} Cada isla tiene su línea en su página.</p></div>'
                            + lineas([{"nombre": "Canarias", "clase": "acento", "puntos": s_can}],
                                     f"{nombre_c}: mediana diaria en Canarias desde el {fecha_larga(s_can[0][0])}",
                                     fuente(fecha, ". Mediana de cada día; del 15/04 al 25/11/2026, histórico de Canarias Gas Tracker"))
                            + tabla_meses([("Canarias", s_can)]))

    filas_tabla = ""
    for s in orden["g95"]:
        rr = fg.ranking(por_isla[s], "g95", 1)
        sitio = rr[0][1]
        empatadas = sum(1 for p, _ in rr if p == 1)
        donde = f'{e(sitio["rotulo"])} ({e(sitio["municipio"])})' if empatadas == 1 else f"{empatadas} gasolineras"
        filas_tabla += (f'<tr><th scope="row"><a href="{raiz}datos/gasolina/{s}/">{NOMBRE_ISLA[s]}</a></th>'
                        f'<td class="num">{precio(med[(s, "g95")])}</td><td class="num">{precio(med[(s, "diesel")])}</td>'
                        f'<td class="num">{precio(sitio["g95"])}<small>{donde}</small></td>'
                        f'<td class="num">{len(por_isla[s])}</td></tr>')
    tabla = (f'<div class="tabla-envuelve"><table><caption>Las siete islas · precios del {fecha:%d/%m/%Y}</caption>'
             f'<thead><tr><th scope="col">Isla</th><th scope="col" class="num">Mediana gasolina 95</th>'
             f'<th scope="col" class="num">Mediana diésel</th><th scope="col" class="num">Gasolina 95 más barata</th>'
             f'<th scope="col" class="num">Gasolineras</th></tr></thead><tbody>{filas_tabla}'
             f'<tr><th scope="row">Canarias</th><td class="num">{precio(med_can["g95"])}</td><td class="num">{precio(med_can["diesel"])}</td>'
             f'<td class="num">{precio(fila_min[0][1]["g95"])}</td><td class="num">{len(estaciones)}</td></tr>'
             f'</tbody></table></div><p class="nota">{fu}</p>')

    tarjetas = "".join(tarjeta_isla(s, por_isla[s], raiz) for s, _ in ISLAS)
    faq_html, faq_ld = preguntas_html()
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": f"{url}#pagina", "url": url, "name": titulo, "description": descripcion,
         "inLanguage": "es", "isPartOf": {"@id": f"{DOMINIO}/#web"}, "author": PERSONA,
         "dateModified": fecha.isoformat(), "image": f"{DOMINIO}/assets/og-gasolina.png",
         "about": {"@type": "Place", "name": "Canarias, España"}, "mainEntity": {"@id": f"{url}#datos"},
         "hasPart": [{"@type": "WebPage", "@id": f"{DOMINIO}/datos/gasolina/{s}/#pagina", "url": f"{DOMINIO}/datos/gasolina/{s}/",
                      "name": f"¿Dónde está la gasolina más barata {DE_ISLA[s]}?"} for s, _ in ISLAS]},
        dataset(url, "Precios de la gasolina y el diésel en Canarias por isla",
                f"Precio de la gasolina 95 y del diésel en las gasolineras de las siete islas y mediana diaria por isla, a "
                f"partir de los datos abiertos del {MINISTERIO}. Se actualiza cada mañana.",
                "Canarias, España", historico, fecha, "canarias"),
        migas([("hbtdata", f"{DOMINIO}/"), ("Datos", f"{DOMINIO}/datos/"), ("Gasolina", url)]),
        faq_ld, PERSONA_COMPLETA,
    ]}

    return (cabeza(titulo, descripcion, url, jsonld, raiz, f"{DOMINIO}/assets/og-gasolina.png")
            + "<body>\n" + iconos() + "\n" + barra(raiz, "datos/gasolina/") + f"""
<main id="contenido">
  <section class="cabecera">
    <div class="envuelve">
      <p class="miga mono"><a href="{raiz}datos/"><b>//</b>datos</a><span>/</span><span>gasolina</span></p>
      <h1 class="titular">¿En qué isla está más barata la gasolina hoy?</h1>
      <p class="entrada">{entrada}</p>
      {sello_fecha(fecha)}
      <div class="cifras">{cifras}</div>
    </div>
  </section>

{selector()}
  <section>
    <div class="envuelve">{islas_html}</div>
  </section>

  <section class="panel">
    <div class="envuelve">
      <div class="cabeza-seccion"><h2>Las siete islas, en una tabla</h2></div>
      {tabla}
    </div>
  </section>

  <section>
    <div class="envuelve">{evol_html}</div>
  </section>

  <section class="panel">
    <div class="envuelve">
      <div class="cabeza-seccion"><h2>¿Dónde está la gasolina más barata de tu isla?</h2>
        <p>Ranking de gasolineras, mapa, precio por municipio y evolución, isla por isla.</p></div>
      <ul class="rejilla-tarjetas">{tarjetas}</ul>
    </div>
  </section>

  <section>
    <div class="envuelve">
      <div class="cabeza-seccion"><h2>Preguntas</h2></div>
      {faq_html}
    </div>
  </section>

{como_esta_hecho(raiz)}</main>

""" + pie(raiz) + scripts(raiz))


def tarjeta_isla(s, propias, raiz):
    rr = fg.ranking(propias, "g95", 1)
    return (f'<li class="tarjeta"><span class="mono"><b>//</b> {NOMBRE_ISLA[s]}</span>'
            f'<h3><a href="{raiz}datos/gasolina/{s}/">¿Dónde está la gasolina más barata {DE_ISLA[s]}?</a></h3>'
            f'<p>Gasolina 95 desde <strong>{precio(rr[0][1]["g95"])}</strong> el litro, '
            f'{re.sub(r"</?strong>", "", donde_minimo(rr))}.</p>'
            f'<div class="pie"><span class="mono">Ver la isla</span><svg class="ico trazo"><use href="#i-flecha"/></svg></div></li>')


# ---------- portada de /datos/ ----------

def pagina_datos(estaciones, fecha):
    raiz = "../"
    url = f"{DOMINIO}/datos/"
    titulo = "Datos de Canarias explicados, con fuente y fecha · hbtdata"
    descripcion = ("Preguntas de Canarias respondidas con datos públicos: dónde está la gasolina más barata de cada isla, "
                   "actualizado cada día con los precios del Ministerio. Cada gráfico con su fuente y su fecha.")
    por_isla = {s: [x for x in estaciones if x["isla"] == s] for s, _ in ISLAS}
    med = {s: fg.mediana(por_isla[s], "g95") for s, _ in ISLAS}
    barata = min(med, key=med.get)
    tarjetas = (f'<li class="tarjeta grande"><span class="mono"><b>//</b> Gasolina · Canarias · se actualiza cada día</span>'
                f'<h3><a href="{raiz}datos/gasolina/">¿En qué isla está más barata la gasolina?</a></h3>'
                f'<p>Precios del {fecha_larga(fecha)}: la mediana más baja de gasolina 95 está en <strong>{NOMBRE_ISLA[barata]}</strong> '
                f'({precio(med[barata])}). Las siete islas comparadas, con su evolución desde abril.</p>'
                f'<div class="pie"><span class="mono">Ver la comparación</span><svg class="ico trazo"><use href="#i-flecha"/></svg></div></li>'
                + "".join(tarjeta_isla(s, por_isla[s], raiz) for s, _ in ISLAS))
    paginas = [("¿En qué isla está más barata la gasolina?", f"{DOMINIO}/datos/gasolina/")] + \
              [(f"¿Dónde está la gasolina más barata {DE_ISLA[s]}?", f"{DOMINIO}/datos/gasolina/{s}/") for s, _ in ISLAS]
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": f"{url}#coleccion", "url": url, "name": titulo, "description": descripcion,
         "inLanguage": "es", "isPartOf": {"@id": f"{DOMINIO}/#web"}, "author": PERSONA,
         "dateModified": fecha.isoformat(), "image": f"{DOMINIO}/assets/og-datos.png",
         "mainEntity": {"@type": "ItemList", "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "url": u, "name": n} for i, (n, u) in enumerate(paginas)]}},
        migas([("hbtdata", f"{DOMINIO}/"), ("Datos", url)]),
        PERSONA_COMPLETA,
    ]}
    return (cabeza(titulo, descripcion, url, jsonld, raiz, f"{DOMINIO}/assets/og-datos.png")
            + "<body>\n" + iconos() + "\n" + barra(raiz, "datos/") + f"""
<main id="contenido">
  <section class="cabecera">
    <div class="envuelve">
      <p class="miga mono"><b>//</b>datos</p>
      <h1 class="titular">Datos de Canarias, con su fuente y su fecha.</h1>
      <p class="entrada">Preguntas de aquí respondidas con datos públicos. Cada gráfico dice de dónde sale y de qué día es, y las páginas con precios se rehacen solas cada mañana.</p>
      {sello_fecha(fecha)}
    </div>
  </section>

  <section>
    <div class="envuelve">
      <div class="cabeza-seccion"><p class="mono"><b>//</b> Gasolina</p><h2>¿Dónde echo gasolina más barata?</h2></div>
      <ul class="rejilla-tarjetas">{tarjetas}</ul>
    </div>
  </section>

  <section class="panel">
    <div class="envuelve">
      <div class="cabeza-seccion"><p class="mono"><b>//</b> Cómo leer estos datos</p><h2>Tres reglas que se cumplen en todas las páginas.</h2></div>
      <ul class="claves">
        <li><span class="mono"><b>01</b> Fuente y fecha</span><h3>Siempre a la vista</h3><p>Debajo de cada gráfico pone de dónde sale el dato y de qué día es. Si no hay fuente, el dato no entra.</p></li>
        <li><span class="mono"><b>02</b> Mediana</span><h3>Para precios, la mediana</h3><p>Es el precio que deja la mitad por debajo y la mitad por encima. Una gasolinera con un precio raro no la mueve.</p></li>
        <li><span class="mono"><b>03</b> Céntimos</span><h3>Sin barras cortadas</h3><p>Las barras empiezan en cero. Cuando las diferencias son de céntimos, se usa un ranking con cifras o puntos con el eje visible.</p></li>
      </ul>
    </div>
  </section>

{como_esta_hecho(raiz)}</main>

""" + pie(raiz) + scripts(raiz))


# ---------- sitemap y llms.txt ----------

def urls_datos():
    return ["datos/", "datos/gasolina/"] + [f"datos/gasolina/{s}/" for s, _ in ISLAS]


def actualiza_sitemap(dia):
    ruta = RAIZ / "sitemap.xml"
    xml = ruta.read_text(encoding="utf-8")
    xml = re.sub(r"\s*<!-- datos -->.*?<!-- /datos -->", "", xml, flags=re.S)
    urls = "\n".join(f"  <url>\n    <loc>{DOMINIO}/{u}</loc>\n    <lastmod>{dia}</lastmod>\n  </url>" for u in urls_datos())
    bloque = f"\n  <!-- datos -->\n{urls}\n  <!-- /datos -->"
    if "<!-- recursos -->" in xml:
        xml = xml.replace("\n  <!-- recursos -->", bloque + "\n  <!-- recursos -->", 1)
    else:
        xml = xml.rstrip().removesuffix("</urlset>").rstrip() + bloque + "\n</urlset>\n"
    ruta.write_text(xml, encoding="utf-8")


def actualiza_llms():
    ruta = RAIZ / "llms.txt"
    txt = ruta.read_text(encoding="utf-8")
    txt = re.sub(r"## Datos de Canarias\n.*?(?=\n## |\Z)", "", txt, flags=re.S)
    islas = "\n".join(f"- **¿Dónde está la gasolina más barata {DE_ISLA[s]}?** {DOMINIO}/datos/gasolina/{s}/" for s, _ in ISLAS)
    bloque = (
        "## Datos de Canarias\n\n"
        f"{DOMINIO}/datos/ · Preguntas de Canarias respondidas con datos públicos, cada gráfico con su fuente y su fecha. "
        "Las páginas de gasolina se regeneran cada mañana con los precios del Geoportal de carburantes "
        f"({MINISTERIO}): ranking de gasolineras, mapa, mediana por municipio y evolución diaria desde abril de 2026.\n\n"
        f"- **¿En qué isla está más barata la gasolina?** {DOMINIO}/datos/gasolina/\n{islas}\n"
        f"- Datos abiertos (CSV): {DOMINIO}/datos/gasolina/precios.csv (precios del día por gasolinera) y "
        f"{DOMINIO}/datos/gasolina/historico.csv (mediana diaria por isla y combustible)\n"
    )
    txt = txt.replace("## Juegos", bloque + "\n## Juegos", 1) if "\n## Juegos" in txt else txt.rstrip() + "\n\n" + bloque
    ruta.write_text(re.sub(r"\n{3,}", "\n\n", txt), encoding="utf-8")


# ---------- principal ----------

def escribe(ruta, html):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(html, encoding="utf-8")


def main():
    args = sys.argv[1:]
    GASOLINA.mkdir(parents=True, exist_ok=True)

    if "--sembrar" in args:
        origen = args[args.index("--sembrar") + 1]
        dias = fg.siembra_desde_tracker(origen, HISTORICO)
        print(f"Histórico: {dias} días añadidos desde {origen}")

    if "--si-falta" in args and PRECIOS.exists():
        _, previa = fg.lee_precios(PRECIOS)
        if previa.date() == ahora().date():
            print(f"Ya están los precios de hoy ({previa:%d/%m/%Y %H:%M}). No se hace nada.")
            return

    if "--sin-descarga" in args:
        estaciones, fecha = fg.lee_precios(PRECIOS)
    else:
        esperas = (0.05, 0.1) if "--sin-esperas" in args else (5, 10, 15)
        estaciones, fecha = fg.descarga(esperas)
        fg.guarda_precios(PRECIOS, estaciones, fecha)
    historico = fg.actualiza_historico(HISTORICO, fecha.date().isoformat(), estaciones)

    for s, _ in ISLAS:
        if not any(x["isla"] == s for x in estaciones):
            sys.exit(f"No hay gasolineras de {NOMBRE_ISLA[s]}: algo raro pasa con la fuente. No se publica.")
        escribe(GASOLINA / s / "index.html", pagina_isla(s, estaciones, historico, fecha))
    escribe(GASOLINA / "index.html", pagina_gasolina(estaciones, historico, fecha))
    escribe(DATOS / "index.html", pagina_datos(estaciones, fecha))
    actualiza_sitemap(fecha.date().isoformat())
    actualiza_llms()
    assert all(MARCA in (RAIZ / u / "index.html").read_text(encoding="utf-8") for u in urls_datos())
    print(f"{len(estaciones)} gasolineras · precios del {fecha:%d/%m/%Y %H:%M} · {len(urls_datos())} páginas")


if __name__ == "__main__":
    main()
