"""Precios de carburantes de Canarias: descarga del Ministerio, limpieza, isla e histórico.

Fuente: API REST de precios de carburantes del Ministerio para la Transición Ecológica
y el Reto Demográfico (la misma del Geoportal de carburantes y de Canarias Gas Tracker).
Solo biblioteca estándar.
"""
import csv
import json
import statistics
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from comun import CANARIAS, ISLAS, isla_de_municipio, nombre_natural

URL = ("https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/"
       "EstacionesTerrestres/FiltroProvincia/{}")
PROVINCIAS = ("35", "38")          # Las Palmas y Santa Cruz de Tenerife
MINIMO_ESTACIONES = 300            # hoy son ~500; menos es una respuesta parcial y no se publica
COMBUSTIBLES = [("g95", "Gasolina 95", "Precio Gasolina 95 E5"), ("diesel", "Diésel", "Precio Gasoleo A")]
NOMBRE_COMBUSTIBLE = {c: n for c, n, _ in COMBUSTIBLES}
CAMPOS_PRECIOS = ["fecha", "id", "isla", "municipio", "localidad", "rotulo", "direccion", "cp", "horario",
                  "lat", "lon", "g95", "diesel"]
CAMPOS_HISTORICO = ["fecha", "ambito", "combustible", "gasolineras", "mediana", "minimo", "maximo"]


def _numero(texto):
    texto = (texto or "").strip().replace(",", ".")
    try:
        return float(texto) if texto else None
    except ValueError:
        return None


def _pide(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) hbtdata.es/datos (datos abiertos de carburantes)",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def _pide_insistiendo(url, veces=8):
    """La API corta a menudo la conexión (más o menos una de cada dos peticiones): se insiste un poco
    con pausas cortas antes de dar el intento por perdido."""
    for n in range(1, veces + 1):
        try:
            return _pide(url)
        except Exception as e:  # noqa: BLE001
            if n == veces:
                raise
            print(f"  {url.rsplit('/', 1)[-1]}: {e}; otra vez en {3 * n} s", file=sys.stderr)
            time.sleep(3 * n)


def descarga(esperas_minutos=(5, 10, 15)):
    """Devuelve (estaciones, fecha_ministerio). Reintenta con esperas crecientes: la API
    corta a veces las peticiones (y a ratos las de GitHub Actions). Si no hay forma, sale con error
    y no se toca nada de lo publicado."""
    intentos = len(esperas_minutos) + 1
    for n in range(1, intentos + 1):
        try:
            crudo, fecha = [], None
            for prov in PROVINCIAS:
                datos = _pide_insistiendo(URL.format(prov))
                if datos.get("ResultadoConsulta", "OK") != "OK":
                    raise ValueError(f"La API responde {datos.get('ResultadoConsulta')!r}")
                crudo += datos["ListaEESSPrecio"]
                fecha = fecha or datos.get("Fecha")
            estaciones = limpia(crudo)
            if len(estaciones) < MINIMO_ESTACIONES:
                raise ValueError(f"Solo {len(estaciones)} gasolineras: posible respuesta parcial")
            return estaciones, fecha_ministerio(fecha)
        except Exception as e:  # noqa: BLE001 — cualquier fallo de red o de formato se reintenta
            print(f"Intento {n}/{intentos} fallido: {e}", file=sys.stderr)
            if n < intentos:
                espera = esperas_minutos[n - 1]
                print(f"  Reintento en {espera} min", file=sys.stderr)
                time.sleep(espera * 60)
    sys.exit("La API del Ministerio no ha respondido. No se publica nada nuevo.")


def fecha_ministerio(texto):
    """La API da la hora peninsular («26/11/2026 14:31:28»); en Canarias es una hora menos todo el año."""
    if not texto:
        return datetime.now(CANARIAS).replace(microsecond=0)
    peninsular = datetime.strptime(texto.strip(), "%d/%m/%Y %H:%M:%S")
    return (peninsular - timedelta(hours=1)).replace(tzinfo=CANARIAS)


def _dentro(lon, lat, anillo):
    dentro = False
    j = len(anillo) - 1
    for i in range(len(anillo)):
        xi, yi = anillo[i]
        xj, yj = anillo[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


_CONTORNOS = None


def isla_por_coordenadas(lat, lon):
    """Plan B por si el Ministerio escribe un municipio de forma nueva: la isla cuyo contorno
    (ISTAC, el mismo de /juegos/) contiene la gasolinera, o la más cercana a menos de 3 km."""
    global _CONTORNOS
    if _CONTORNOS is None:
        ruta = Path(__file__).resolve().parents[2] / "juegos" / "datos" / "islas.geojson"
        geo = json.loads(ruta.read_text(encoding="utf-8"))
        nombre_a_slug = {n: s for s, n in ISLAS}
        _CONTORNOS = []
        for f in geo["features"]:
            g = f["geometry"]
            poligonos = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            _CONTORNOS.append((nombre_a_slug[f["properties"]["isla"]], [p[0] for p in poligonos]))
    for isla, anillos in _CONTORNOS:
        if any(_dentro(lon, lat, a) for a in anillos):
            return isla
    mejor, dist = None, 0.03  # ~3 km en grados
    for isla, anillos in _CONTORNOS:
        for a in anillos:
            for x, y in a:
                d = ((x - lon) ** 2 + (y - lat) ** 2) ** 0.5
                if d < dist:
                    mejor, dist = isla, d
    return mejor


def limpia(crudo):
    estaciones = []
    for x in crudo:
        if x.get("IDProvincia") not in PROVINCIAS:
            continue
        lat, lon = _numero(x.get("Latitud")), _numero(x.get("Longitud (WGS84)"))
        if lat is None or lon is None:
            continue
        g95, diesel = _numero(x.get("Precio Gasolina 95 E5")), _numero(x.get("Precio Gasoleo A"))
        if g95 is None and diesel is None:
            continue
        isla = isla_de_municipio(x.get("Municipio", "")) or isla_por_coordenadas(lat, lon)
        if not isla:
            print(f"Sin isla, se deja fuera: {x.get('Rótulo')} ({x.get('Municipio')})", file=sys.stderr)
            continue
        estaciones.append({
            "id": x.get("IDEESS", "").strip(),
            "isla": isla,
            "municipio": nombre_natural(x.get("Municipio", "")),
            "localidad": " ".join(x.get("Localidad", "").split()),
            "rotulo": " ".join(x.get("Rótulo", "").split()) or "Sin nombre",
            "direccion": " ".join(x.get("Dirección", "").split()),
            "cp": x.get("C.P.", "").strip(),
            "horario": " ".join(x.get("Horario", "").split()),
            "lat": round(lat, 6), "lon": round(lon, 6),
            "g95": g95, "diesel": diesel,
        })
    return estaciones


# ---------- archivos ----------

def guarda_precios(ruta, estaciones, fecha):
    """Un CSV limpio: la primera columna es la fecha y hora (canaria) en que el Ministerio publicó los precios."""
    marca = fecha.strftime("%Y-%m-%dT%H:%M")
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_PRECIOS)
        w.writeheader()
        for e in sorted(estaciones, key=lambda e: (e["isla"], e["municipio"], e["rotulo"], e["id"])):
            fila = {"fecha": marca, **e}
            for c in ("g95", "diesel"):
                fila[c] = "" if e[c] is None else f"{e[c]:.3f}"
            w.writerow(fila)


def lee_precios(ruta):
    with open(ruta, encoding="utf-8") as f:
        estaciones = list(csv.DictReader(f))
    if not estaciones:
        raise ValueError(f"{ruta} está vacío")
    fecha = datetime.strptime(estaciones[0]["fecha"], "%Y-%m-%dT%H:%M").replace(tzinfo=CANARIAS)
    for e in estaciones:
        del e["fecha"]
        e["lat"], e["lon"] = float(e["lat"]), float(e["lon"])
        for c in ("g95", "diesel"):
            e[c] = float(e[c]) if e[c] else None
    return estaciones, fecha


def resumen_dia(fecha_iso, estaciones):
    """Filas del histórico de un día: una por ámbito (cada isla y Canarias) y combustible."""
    filas = []
    ambitos = [(s, [e for e in estaciones if e["isla"] == s]) for s, _ in ISLAS] + [("canarias", estaciones)]
    for ambito, lista in ambitos:
        for c, _, _ in COMBUSTIBLES:
            precios = [e[c] for e in lista if e[c] is not None]
            if not precios:
                continue
            filas.append({"fecha": fecha_iso, "ambito": ambito, "combustible": c, "gasolineras": len(precios),
                          "mediana": round(statistics.median(precios), 4),
                          "minimo": min(precios), "maximo": max(precios)})
    return filas


def lee_historico(ruta):
    if not Path(ruta).exists():
        return []
    with open(ruta, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    for r in filas:
        r["gasolineras"] = int(r["gasolineras"])
        for c in ("mediana", "minimo", "maximo"):
            r[c] = float(r[c])
    return filas


def guarda_historico(ruta, filas):
    orden = {s: i for i, (s, _) in enumerate(ISLAS)}
    orden["canarias"] = len(orden)
    filas = sorted(filas, key=lambda r: (r["fecha"], orden.get(r["ambito"], 99), r["combustible"]))
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_HISTORICO)
        w.writeheader()
        for r in filas:
            w.writerow({**r, "mediana": f"{r['mediana']:.4f}".rstrip("0").rstrip("."),
                        "minimo": f"{r['minimo']:.3f}", "maximo": f"{r['maximo']:.3f}"})


def actualiza_historico(ruta, fecha_iso, estaciones):
    filas = [r for r in lee_historico(ruta) if r["fecha"] != fecha_iso] + resumen_dia(fecha_iso, estaciones)
    guarda_historico(ruta, filas)
    return lee_historico(ruta)


def siembra_desde_tracker(ruta_csv, ruta_historico):
    """Rellena el histórico con lo que ya guardó Canarias Gas Tracker (desde el 15 de abril de 2026).
    Ojo: aquel CSV juntaba en una sola fila las gasolineras con el mismo rótulo en el mismo municipio,
    así que cada día tiene ~430 gasolineras en vez de ~500. Las medianas apenas cambian."""
    por_dia = defaultdict(list)
    with open(ruta_csv, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("Municipio"):
                continue  # el primer día no guardaba el municipio
            isla = isla_de_municipio(r["Municipio"])
            if not isla:
                continue
            por_dia[r["Fecha"]].append({"isla": isla, "g95": _numero(r["Precio Gasolina 95 E5"]),
                                        "diesel": _numero(r["Precio Gasoleo A"])})
    existentes = lee_historico(ruta_historico)
    hechos = {r["fecha"] for r in existentes}
    nuevas = []
    for dia, lista in sorted(por_dia.items()):
        if dia not in hechos and len(lista) >= MINIMO_ESTACIONES:
            nuevas += resumen_dia(dia, lista)
    guarda_historico(ruta_historico, existentes + nuevas)
    return len({r["fecha"] for r in nuevas})


# ---------- cálculos para las páginas ----------

def ranking(estaciones, combustible, cuantas=10):
    """Las más baratas, con empates: si la décima comparte precio con otras, entran todas (hasta 15)."""
    con = sorted((e for e in estaciones if e[combustible] is not None),
                 key=lambda e: (e[combustible], e["municipio"], e["rotulo"]))
    if len(con) <= cuantas:
        corte = con
    else:
        limite = con[cuantas - 1][combustible]
        corte = [e for e in con if e[combustible] <= limite][:15]
    puestos, anterior, puesto = [], None, 0
    for i, e in enumerate(corte, 1):
        if e[combustible] != anterior:
            puesto, anterior = i, e[combustible]
        puestos.append((puesto, e))
    return puestos


def mediana(estaciones, combustible):
    precios = [e[combustible] for e in estaciones if e[combustible] is not None]
    return statistics.median(precios) if precios else None


def por_municipio(estaciones, combustible):
    grupos = defaultdict(list)
    for e in estaciones:
        if e[combustible] is not None:
            grupos[e["municipio"]].append(e[combustible])
    filas = [{"municipio": m, "mediana": statistics.median(v), "minimo": min(v), "maximo": max(v), "n": len(v)}
             for m, v in grupos.items()]
    return sorted(filas, key=lambda r: (r["mediana"], r["municipio"]))
