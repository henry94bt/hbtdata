"""Gráficos de hbtdata.es/datos/ en HTML y SVG, sin JavaScript ni librerías.

Reglas de la marca (brief): barras desde cero; si las diferencias son de céntimos, ranking con
cifras o gráfico de puntos con el eje visible; medianas para precios; fecha y fuente en cada gráfico.
Colores: ocre #F0A840 para lo que responde a la pregunta, aguamarina #96D6D6 para el resto.

Los textos son HTML posicionado en % (se leen igual en el móvil); el SVG solo dibuja trazos.
Cada marca lleva <title> para el tooltip nativo y el dato está también en una tabla.
"""
import json
import math
from datetime import date
from html import escape
from pathlib import Path

from comun import ISLAS, MESES_CORTOS, fecha_corta, precio, precio_eje

RAIZ = Path(__file__).resolve().parents[2]


def e(t):
    return escape(str(t), quote=True)


def _paso(span, objetivo=5):
    for p in (0.01, 0.02, 0.05, 0.1, 0.2, 0.25, 0.5):
        if span / p <= objetivo:
            return p
    return 1.0


def _dominio(minimo, maximo, objetivo=5):
    span = max(maximo - minimo, 0.02)
    paso = _paso(span, objetivo)
    lo = math.floor(minimo / paso + 1e-9) * paso
    hi = math.ceil(maximo / paso - 1e-9) * paso
    if hi - lo < paso:
        hi = lo + paso
    ticks = [round(lo + i * paso, 4) for i in range(int(round((hi - lo) / paso)) + 1)]
    return lo, hi, ticks


def _pct(v, lo, hi):
    return 100 * (v - lo) / (hi - lo)


def pie_grafico(fuente_html):
    return f'<figcaption class="fuente">{fuente_html}</figcaption>'


# ---------- gráfico de puntos (dot plot) ----------

def puntos(filas, etiqueta_aria, fuente_html, referencia=None, con_rango=True, clase=""):
    """filas: dicts con etiqueta, valor, y opcionales minimo, maximo, nota, enlace, resaltar, titulo."""
    valores = [f["valor"] for f in filas]
    if con_rango:
        valores += [f.get("minimo", f["valor"]) for f in filas] + [f.get("maximo", f["valor"]) for f in filas]
    if referencia:
        valores.append(referencia[0])
    lo, hi, ticks = _dominio(min(valores), max(valores))

    rejilla = "".join(f'<i style="left:{_pct(t, lo, hi):.2f}%"></i>' for t in ticks)
    eje = "".join(f'<span style="left:{_pct(t, lo, hi):.2f}%">{precio_eje(t)}</span>' for t in ticks)
    ref = ""
    if referencia:
        x_ref = _pct(referencia[0], lo, hi)
        lado_ref = " dcha" if x_ref > 65 else (" izda" if x_ref < 35 else "")
        ref = (f'<b class="ref{lado_ref}" style="left:{x_ref:.2f}%">'
               f'<span>{e(referencia[1])}</span></b>')

    cuerpo = ""
    for f in filas:
        x = _pct(f["valor"], lo, hi)
        rango = ""
        if con_rango and "minimo" in f:
            a, b = _pct(f["minimo"], lo, hi), _pct(f["maximo"], lo, hi)
            rango = f'<s style="left:{a:.2f}%;width:{max(b - a, 0):.2f}%"></s>'
        lado = " izq" if x > 80 else ""
        etq = f'<a href="{e(f["enlace"])}">{e(f["etiqueta"])}</a>' if f.get("enlace") else e(f["etiqueta"])
        nota = f'<small>{e(f["nota"])}</small>' if f.get("nota") else ""
        titulo = e(f.get("titulo") or f'{f["etiqueta"]}: {precio(f["valor"])}')
        cuerpo += (f'<li class="{"resalta" if f.get("resaltar") else ""}">'
                   f'<span class="etq">{etq}{nota}</span>'
                   f'<span class="pista">{rango}<em style="left:{x:.2f}%" title="{titulo}"></em>'
                   f'<span class="valor{lado}" style="left:{x:.2f}%">{precio(f["valor"], "")}</span></span></li>')

    return (f'<figure class="grafico puntos {clase}">'
            f'<div class="lienzo-puntos" role="img" aria-label="{e(etiqueta_aria)}">'
            f'<div class="rejilla" aria-hidden="true">{rejilla}{ref}</div>'
            f'<ol aria-hidden="true">{cuerpo}</ol>'
            f'<div class="eje" aria-hidden="true">{eje}</div></div>'
            f'{pie_grafico(fuente_html)}</figure>')


# ---------- líneas en el tiempo ----------

def lineas(series, etiqueta_aria, fuente_html, hueco_dias=6, clase=""):
    """series: dicts con nombre, clase ('acento' o 'base') y puntos [(fecha_iso, valor)], en orden de dibujo
    (la base primero, el acento encima)."""
    todas = [p for s in series for p in s["puntos"]]
    if not todas:
        return ""
    fechas = sorted({f for f, _ in todas})
    d0, d1 = date.fromisoformat(fechas[0]), date.fromisoformat(fechas[-1])
    dias = max((d1 - d0).days, 1)
    lo, hi, ticks = _dominio(min(v for _, v in todas), max(v for _, v in todas), objetivo=4)
    W, H = 1000, 300

    def xy(f, v):
        return (date.fromisoformat(f) - d0).days / dias * W, H - (v - lo) / (hi - lo) * H

    trazos = "".join(f'<line x1="0" x2="{W}" y1="{xy(fechas[0], t)[1]:.1f}" y2="{xy(fechas[0], t)[1]:.1f}"/>' for t in ticks)
    caminos = ""
    finales = ""
    for s in series:
        d, previo = "", None
        for f, v in s["puntos"]:
            x, y = xy(f, v)
            salto = previo is None or (date.fromisoformat(f) - date.fromisoformat(previo)).days > hueco_dias
            d += f'{"M" if salto else "L"}{x:.1f},{y:.1f}'
            previo = f
        caminos += f'<path class="{s["clase"]}" d="{d}"/>'
        f, v = s["puntos"][-1]
        x, y = xy(f, v)
        finales += f'<span class="punto-final {s["clase"]}" style="left:{x / W * 100:.2f}%;top:{y / H * 100:.2f}%"></span>'

    # bandas invisibles con el tooltip de cada día
    por_fecha = {f: {} for f in fechas}
    for s in series:
        for f, v in s["puntos"]:
            por_fecha[f][s["nombre"]] = v
    ancho = W / max(len(fechas), 1) * 1.6
    bandas = ""
    for f in fechas:
        x, _ = xy(f, lo)
        txt = f"{fecha_corta(f)} · " + " · ".join(f"{n}: {precio(v)}" for n, v in por_fecha[f].items())
        bandas += f'<rect x="{x - ancho / 2:.1f}" y="0" width="{ancho:.1f}" height="{H}"><title>{e(txt)}</title></rect>'

    eje_y = "".join(f'<span style="top:{xy(fechas[0], t)[1] / H * 100:.2f}%">{precio_eje(t)}</span>' for t in ticks)
    meses, m = "", (d0.year, d0.month)
    while True:
        primero = date(m[0], m[1], 1)
        if primero > d1:
            break
        if primero >= d0:
            x = (primero - d0).days / dias * 100
            if x < 94:
                meses += f'<span style="left:{x:.2f}%">{MESES_CORTOS[primero.month - 1]}</span>'
        m = (m[0] + (m[1] == 12), m[1] % 12 + 1)

    # el último valor va en la leyenda: si las dos líneas acaban juntas, las etiquetas no se pisan
    leyenda = "".join(f'<li class="{s["clase"]}"><i></i>{e(s["nombre"])} <b>{precio(s["puntos"][-1][1])}</b>'
                      f'<small>{fecha_corta(s["puntos"][-1][0])}</small></li>' for s in reversed(series))
    return (f'<figure class="grafico lineas {clase}">'
            f'<ul class="leyenda">{leyenda}</ul>'
            f'<div class="lienzo-lineas" role="img" aria-label="{e(etiqueta_aria)}">'
            f'<div class="eje-y" aria-hidden="true">{eje_y}</div>'
            f'<div class="area">'
            f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" aria-hidden="true">'
            f'<g class="rejilla">{trazos}</g>{caminos}<g class="bandas">{bandas}</g></svg>'
            f'{finales}</div>'
            f'<div class="eje-x" aria-hidden="true">{meses}</div></div>'
            f'{pie_grafico(fuente_html)}</figure>')


# ---------- mapa de una isla ----------

_CONTORNO = {}


def _simplifica(puntos, tol):
    """Douglas-Peucker."""
    if len(puntos) < 3:
        return puntos
    (x1, y1), (x2, y2) = puntos[0], puntos[-1]
    dx, dy = x2 - x1, y2 - y1
    largo = math.hypot(dx, dy) or 1e-12
    peor, idx = 0, 0
    for i in range(1, len(puntos) - 1):
        x, y = puntos[i]
        d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / largo
        if d > peor:
            peor, idx = d, i
    if peor <= tol:
        return [puntos[0], puntos[-1]]
    return _simplifica(puntos[:idx + 1], tol)[:-1] + _simplifica(puntos[idx:], tol)


COS = math.cos(math.radians(28.3))


def _proyecta(lon, lat):
    return lon * COS, -lat


def contorno(isla):
    if not _CONTORNO:
        geo = json.loads((RAIZ / "juegos" / "datos" / "islas.geojson").read_text(encoding="utf-8"))
        a_slug = {n: s for s, n in ISLAS}
        for f in geo["features"]:
            g = f["geometry"]
            polis = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            _CONTORNO[a_slug[f["properties"]["isla"]]] = [[_proyecta(x, y) for x, y in p[0]] for p in polis]
    return _CONTORNO[isla]


def mapa(isla, estaciones, destacadas, etiqueta_aria, fuente_html, combustible, leyenda_destacadas=None):
    anillos = contorno(isla)
    xs = [x for a in anillos for x, _ in a] + [_proyecta(s["lon"], s["lat"])[0] for s in estaciones]
    ys = [y for a in anillos for _, y in a] + [_proyecta(s["lon"], s["lat"])[1] for s in estaciones]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    lado = max(x1 - x0, y1 - y0)
    margen = lado * 0.06
    W = 1000
    escala = W / (x1 - x0 + 2 * margen)
    H = (y1 - y0 + 2 * margen) * escala

    def p(x, y):
        return (x - x0 + margen) * escala, (y - y0 + margen) * escala

    tol = lado * 0.0015
    caminos = ""
    for a in anillos:
        if len(a) < 4:
            continue
        # un anillo cerrado empieza y acaba en el mismo punto: se parte por el punto más lejano
        lejos = max(range(len(a)), key=lambda i: (a[i][0] - a[0][0]) ** 2 + (a[i][1] - a[0][1]) ** 2)
        s = _simplifica(a[:lejos + 1], tol)[:-1] + _simplifica(a[lejos:], tol)
        # islotes diminutos fuera
        ax = [q[0] for q in s]
        ay = [q[1] for q in s]
        if (max(ax) - min(ax)) < lado * 0.004 and (max(ay) - min(ay)) < lado * 0.004:
            continue
        caminos += "M" + "L".join(f"{p(x, y)[0]:.1f},{p(x, y)[1]:.1f}" for x, y in s) + "Z"

    r_base, r_top = 12, 19
    ids = {id(s) for _, s in destacadas}
    base = ""
    for s in sorted(estaciones, key=lambda s: -s["lat"]):
        if id(s) in ids or s[combustible] is None:
            continue
        x, y = p(*_proyecta(s["lon"], s["lat"]))
        base += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r_base}"><title>{e(s["rotulo"])} · {e(s["municipio"])}: '
                 f'{precio(s[combustible])}</title></circle>')
    top = ""
    for puesto, s in reversed(destacadas):
        x, y = p(*_proyecta(s["lon"], s["lat"]))
        top += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r_top}"><title>{puesto}.º {e(s["rotulo"])} · '
                f'{e(s["municipio"])}: {precio(s[combustible])}</title></circle>')

    return (f'<figure class="grafico mapa">'
            f'<ul class="leyenda"><li class="acento"><i class="redondo"></i>{e(leyenda_destacadas or f"Las {len(destacadas)} más baratas")}</li>'
            f'<li class="base"><i class="redondo"></i>El resto</li></ul>'
            f'<svg viewBox="0 0 {W} {H:.0f}" role="img" aria-label="{e(etiqueta_aria)}">'
            f'<path class="tierra" d="{caminos}"/><g class="base">{base}</g><g class="acento">{top}</g></svg>'
            f'{pie_grafico(fuente_html)}</figure>')
