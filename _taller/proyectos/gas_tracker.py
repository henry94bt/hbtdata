"""Gráficos de hbtdata.es/proyectos/canarias-gas-tracker/ a partir del histórico del Gas Tracker.

Uso:
    python3 _taller/proyectos/gas_tracker.py RUTA/historico_precios.csv

Lee el `historico_precios.csv` del repo canarias-gas-tracker y reescribe, dentro de
proyectos/canarias-gas-tracker/index.html, lo que hay entre los marcadores:

    <!-- auto:islas --> ... <!-- /auto:islas -->   mediana por isla del último día (gráfico de puntos)
    <!-- auto:dias -->  ... <!-- /auto:dias -->    qué días guardó precios el robot

Al terminar imprime las cifras que usa el texto de la página, para comprobar que siguen
cuadrando. El texto no se reescribe solo: si cambian, hay que tocarlo a mano.

Solo necesita pandas. Medianas, eje visible y fecha y fuente, como en el resto de la marca.
"""
import html
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PAGINA = RAIZ / 'proyectos' / 'canarias-gas-tracker' / 'index.html'
G95, DIESEL = 'Precio Gasolina 95 E5', 'Precio Gasoleo A'
INICIO_REINTENTOS = date(2026, 5, 29)   # commit ad4d004: reintentos a los 5, 10 y 15 minutos
MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sept', 'oct', 'nov', 'dic']
MESES_LARGOS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
                'septiembre', 'octubre', 'noviembre', 'diciembre']


# Misma lógica que obtener_isla() de mapa_pro.py, más GÜÍMAR, que allí cae en «Otras».
def isla(municipio):
    m = str(municipio).upper()
    reglas = [
        ('Gran Canaria', ['PALMAS', 'TELDE', 'AGAETE', 'AGÜIMES', 'ARTENARA', 'ARUCAS', 'FIRGAS', 'GÁLDAR',
                          'INGENIO', 'MOGÁN', 'MOYA', 'TIRAJANA', 'BRÍGIDA', 'LUCÍA', 'GUÍA DE GRAN CANARIA',
                          'TEJEDA', 'TEROR', 'VALLESECO', 'VALSEQUILLO', 'MATEO', 'ALDEA']),
        ('Fuerteventura', ['OLIVA', 'ANTIGUA', 'BETANCURIA', 'PÁJARA', 'PUERTO DEL ROSARIO', 'TUINEJE']),
        ('Lanzarote', ['ARRECIFE', 'HARÍA', 'SAN BARTOLOMÉ', 'TEGUISE', 'TÍAS', 'TINAJO', 'YAIZA']),
        ('Tenerife', ['CRUZ DE TENERIFE', 'ADEJE', 'ARAFO', 'ARICO', 'ARONA', 'BUENAVISTA', 'CANDELARIA',
                      'FASNIA', 'GARACHICO', 'GRANADILLA', 'GUANCHA', 'ISORA', 'ICOD', 'MATANZA', 'OROTAVA',
                      'PUERTO DE LA CRUZ', 'REALEJOS', 'ROSARIO', 'LAGUNA', 'RAMBLA', 'SAN MIGUEL', 'ÚRSULA',
                      'SANTIAGO DEL TEIDE', 'SAUZAL', 'SILOS', 'TACORONTE', 'TANQUE', 'TEGUESTE', 'VICTORIA',
                      'VILAFLOR', 'GÜÍMAR']),
        ('La Palma', ['BARLOVENTO', 'BREÑA', 'FUENCALIENTE', 'GARAFÍA', 'LLANOS DE ARIDANE', 'PASO',
                      'PUNTAGORDA', 'PUNTALLANA', 'SAN ANDRÉS', 'CRUZ DE LA PALMA', 'TAZACORTE', 'TIJARAFE',
                      'MAZO']),
        ('La Gomera', ['AGULO', 'ALAJERÓ', 'HERMIGUA', 'SAN SEBASTIÁN', 'VALLE GRAN REY', 'VALLEHERMOSO']),
        ('El Hierro', ['FRONTERA', 'PINAR', 'VALVERDE']),
    ]
    for nombre, trozos in reglas:
        if any(t in m for t in trozos):
            return nombre
    return 'Otras'


def euros(x):
    return f'{x:.3f}'.replace('.', ',') + ' €'


def fecha_larga(d):
    return f'{d.day} de {MESES_LARGOS[d.month - 1]} de {d.year}'


# ---------- gráfico 1: mediana por isla ----------
def grafico_islas(h):
    ultimo = h['Fecha'].max()
    dia = h[h['Fecha'] == ultimo]
    t = (dia.groupby('Isla')
            .agg(g95=(G95, 'median'), diesel=(DIESEL, 'median'), n=(G95, 'count'))
            .drop(index='Otras', errors='ignore')
            .sort_values(['g95', 'diesel']))
    lo, hi = 1.40, 2.00
    while t[['g95', 'diesel']].min().min() < lo:
        lo -= .1
    while t[['g95', 'diesel']].max().max() > hi:
        hi += .1
    pos = lambda v: f'{(v - lo) / (hi - lo) * 100:.2f}%'
    d = pd.Timestamp(ultimo).date()

    filas = []
    for nombre, r in t.iterrows():
        filas.append(
            f'      <div class="fila-p"><span class="isla">{nombre} <small>({int(r.n)})</small></span>'
            f'<span class="pista"><i class="d" style="left:{pos(r.diesel)}"></i><i class="g" style="left:{pos(r.g95)}"></i></span>'
            f'<span class="cifras"><b class="g">{euros(r.g95)[:-2]}</b> <b class="d">{euros(r.diesel)[:-2]}</b></span></div>')
    marcas = []
    v = lo
    while v <= hi + 1e-9:
        marcas.append(f'<span style="left:{pos(v)}">' + f'{v:.2f}'.replace('.', ',') + '</span>')
        v += .1
    tabla = '\n'.join(
        f'          <tr><th scope="row">{n}</th><td>{euros(r.g95)}</td><td>{euros(r.diesel)}</td><td>{int(r.n)}</td></tr>'
        for n, r in t.iterrows())
    resumen = ', '.join(f'{n} {euros(r.g95)}' for n, r in t.iterrows())

    return f'''<!-- auto:islas -->
    <figure class="grafico" aria-labelledby="t-islas">
      <h3 id="t-islas">¿Qué isla tiene la gasolina más barata?</h3>
      <p class="leyenda"><span class="g">Gasolina 95</span> <span class="d">Diésel</span> <span>· € por litro, mediana del día</span></p>
      <div class="puntos" role="img" aria-label="Mediana de la gasolina 95 por isla el {fecha_larga(d)}, de más barata a más cara: {html.escape(resumen)}.">
{chr(10).join(filas)}
      <div class="fila-p eje" aria-hidden="true"><span></span><span class="pista">{''.join(marcas)}</span><span></span></div>
      </div>
      <details>
        <summary>Ver los datos</summary>
        <table>
          <thead><tr><th scope="col">Isla</th><th scope="col">Gasolina 95</th><th scope="col">Diésel</th><th scope="col">Gasolineras</th></tr></thead>
          <tbody>
{tabla}
          </tbody>
        </table>
      </details>
      <figcaption>Mediana del precio por litro el {fecha_larga(d)}; entre paréntesis, las gasolineras con precio de gasolina 95 ese día. El eje no empieza en cero porque las diferencias son de céntimos. En El Hierro y La Gomera hay tan pocas gasolineras que un solo cambio mueve la mediana. Fuente: Ministerio para la Transición Ecológica (Geoportal de carburantes), histórico del Canarias Gas Tracker.</figcaption>
    </figure>
    <!-- /auto:islas -->'''


# ---------- gráfico 2: días con datos ----------
def grafico_dias(h):
    con = {pd.Timestamp(f).date() for f in h['Fecha'].unique()}
    ini, fin = min(con), max(con)
    lunes = ini - timedelta(days=ini.weekday())
    domingo = fin + timedelta(days=6 - fin.weekday())
    semanas = ((domingo - lunes).days + 1) // 7

    celdas = []
    d = lunes
    while d <= domingo:
        if d < ini or d > fin:
            celdas.append('<i class="fuera"></i>')
        else:
            clase = 'si' if d in con else 'no'
            celdas.append(f'<i class="{clase}" title="{d.day} {MESES[d.month - 1]}: {"con datos" if clase == "si" else "sin datos"}"></i>')
        d += timedelta(days=1)

    meses = []
    for s in range(semanas):
        inicio_semana = lunes + timedelta(weeks=s)
        dias = [inicio_semana + timedelta(days=k) for k in range(7)]
        primero = next((x for x in dias if x.day == 1 and ini <= x <= fin), None)
        if s == 0:
            meses.append(f'<span style="grid-column:{s + 1}">{MESES[ini.month - 1]}</span>')
        elif primero:
            meses.append(f'<span style="grid-column:{s + 1}">{MESES[primero.month - 1]}</span>')
    col_reintentos = (INICIO_REINTENTOS - lunes).days // 7

    def tramo(a, b):
        dias = [a + timedelta(days=k) for k in range((b - a).days + 1)]
        return sum(x in con for x in dias), len(dias)

    antes = tramo(ini, INICIO_REINTENTOS - timedelta(days=1))
    despues = tramo(INICIO_REINTENTOS, fin)
    pct = round(despues[0] / despues[1] * 100)

    bloque = f'''<!-- auto:dias -->
    <figure class="grafico" aria-labelledby="t-dias">
      <h3 id="t-dias">¿Qué días guardó precios el robot?</h3>
      <p class="leyenda"><span class="si">Con datos</span> <span class="no">Sin datos</span></p>
      <div class="dias" role="img" aria-label="Del {fecha_larga(ini)} al {fecha_larga(fin)}: antes de los reintentos hubo datos {antes[0]} de {antes[1]} días; desde el {fecha_larga(INICIO_REINTENTOS)}, {despues[0]} de {despues[1]}.">
        <div class="meses" style="--semanas:{semanas}" aria-hidden="true">{''.join(meses)}</div>
        <div class="rejilla" style="--semanas:{semanas}">{''.join(celdas)}<span class="corte" style="left:calc({col_reintentos} / {semanas} * 100%)"><b>{INICIO_REINTENTOS.day} may · reintentos</b></span></div>
      </div>
      <p class="cifras-dias"><span>Antes: <b>{antes[0]} de {antes[1]}</b> días</span> <span>Después: <b>{despues[0]} de {despues[1]}</b> días ({pct}&nbsp;%)</span></p>
      <figcaption>Cada cuadro es un día, del {fecha_larga(ini)} al {fecha_larga(fin)}; cada columna, una semana de lunes a domingo. La línea marca el {fecha_larga(INICIO_REINTENTOS)}, cuando entraron los reintentos. Fuente: historico_precios.csv del Canarias Gas Tracker.</figcaption>
    </figure>
    <!-- /auto:dias -->'''
    return bloque, antes, despues, pct


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    h = pd.read_csv(sys.argv[1])
    h['Isla'] = h['Municipio'].fillna(h.get('Localidad')).apply(isla)

    islas = grafico_islas(h)
    dias, antes, despues, pct = grafico_dias(h)

    texto = PAGINA.read_text(encoding='utf-8')
    for nombre, nuevo in (('islas', islas), ('dias', dias)):
        patron = re.compile(rf'<!-- auto:{nombre} -->.*?<!-- /auto:{nombre} -->', re.S)
        if not patron.search(texto):
            sys.exit(f'No encuentro los marcadores auto:{nombre} en {PAGINA}')
        texto = patron.sub(lambda _: nuevo, texto)
    PAGINA.write_text(texto, encoding='utf-8')

    # Cifras que usa el texto, para revisarlas
    ultimo = h['Fecha'].max()
    dia = h[h['Fecha'] == ultimo]
    gc = dia[dia['Isla'] == 'Gran Canaria'][G95]
    mes = h.assign(m=pd.to_datetime(h['Fecha']).dt.to_period('M')).groupby('m')[G95].median()
    print(f'Último día: {ultimo} · gasolineras: {len(dia)} · días en el histórico: {h["Fecha"].nunique()} · filas: {len(h)}')
    print(f'Gran Canaria, gasolina 95: de {euros(gc.min())} a {euros(gc.max())} '
          f'({(gc.max() - gc.min()) * 100:.0f} céntimos; {(gc.max() - gc.min()) * 50:.1f} € en 50 litros)')
    print('Mediana mensual de la gasolina 95 en Canarias:', ', '.join(f'{p}: {euros(v)}' for p, v in mes.items()))
    print(f'Días con datos: antes {antes[0]}/{antes[1]}, después {despues[0]}/{despues[1]} ({pct} %)')
    print(f'Escrito: {PAGINA.relative_to(RAIZ)}')


if __name__ == '__main__':
    main()
