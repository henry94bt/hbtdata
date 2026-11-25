#!/usr/bin/env python3
"""Genera los datos de los juegos de hbtdata.es/juegos/ a partir de fuentes oficiales.

    python3 juegos/datos/construir.py

Salida (en esta misma carpeta):
  preguntas-canarias.json  Test de Canarias (motor: assets/juegos/test.js)
  sitios-canarias.json     «¿Dónde está?» (motor: assets/juegos/donde.js)
  islas.geojson            Contorno de las islas para el mapa

Fuentes:
  INE      Cifras oficiales del Padrón municipal (API Tempus, tablas 2889 y 2892)
  ISTAC    Indicador SUPERFICIE y geometrías de las islas (API de datos.canarias.es)
  IGN      Nomenclátor Geográfico Básico de España (NGBE) y Base Topográfica Nacional (BTN),
           consultados a través del geocodificador de CartoCiudad
Los datos que no salen de una API (parques nacionales, Patrimonio Mundial, altura del Teide)
llevan su fuente escrita a mano en HECHOS. Regla: si un dato no tiene fuente, no entra.
Solo usa la biblioteca estándar de Python.
"""
import datetime
import json
import math
import os
import time
import urllib.parse
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
HOY = datetime.date.today()
CONSULTA = "consultado el " + HOY.strftime("%d/%m/%Y")

ISTAC = "https://datos.canarias.es/api/estadisticas"
CARTOCIUDAD = "https://www.cartociudad.es/geocoder/api/geocoder/candidates"


def pide(url, intentos=6):
    for k in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "hbtdata-juegos"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception:
            if k == intentos - 1:
                raise
            time.sleep(3 + 4 * k)


# ---------------------------------------------------------------- islas y municipios

ISLAS = {
    "Lanzarote": ["Arrecife", "Haría", "San Bartolomé", "Teguise", "Tías", "Tinajo", "Yaiza"],
    "Fuerteventura": ["Antigua", "Betancuria", "La Oliva", "Pájara", "Puerto del Rosario", "Tuineje"],
    "Gran Canaria": ["Agaete", "Agüimes", "La Aldea de San Nicolás", "Artenara", "Arucas", "Firgas", "Gáldar",
                     "Ingenio", "Mogán", "Moya", "Las Palmas de Gran Canaria", "San Bartolomé de Tirajana",
                     "Santa Brígida", "Santa Lucía de Tirajana", "Santa María de Guía de Gran Canaria", "Tejeda",
                     "Telde", "Teror", "Valleseco", "Valsequillo de Gran Canaria", "Vega de San Mateo"],
    "Tenerife": ["Adeje", "Arafo", "Arico", "Arona", "Buenavista del Norte", "Candelaria", "Fasnia", "Garachico",
                 "Granadilla de Abona", "La Guancha", "Guía de Isora", "Güímar", "Icod de los Vinos",
                 "La Matanza de Acentejo", "La Orotava", "Puerto de la Cruz", "Los Realejos", "El Rosario",
                 "San Cristóbal de La Laguna", "San Juan de la Rambla", "San Miguel de Abona",
                 "Santa Cruz de Tenerife", "Santa Úrsula", "Santiago del Teide", "El Sauzal", "Los Silos",
                 "Tacoronte", "El Tanque", "Tegueste", "La Victoria de Acentejo", "Vilaflor de Chasna"],
    "La Palma": ["Barlovento", "Breña Alta", "Breña Baja", "Fuencaliente de la Palma", "Garafía",
                 "Los Llanos de Aridane", "El Paso", "Puntagorda", "Puntallana", "San Andrés y Sauces",
                 "Santa Cruz de la Palma", "Tazacorte", "Tijarafe", "Villa de Mazo"],
    "La Gomera": ["Agulo", "Alajeró", "Hermigua", "San Sebastián de la Gomera", "Valle Gran Rey", "Vallehermoso"],
    "El Hierro": ["Frontera", "El Pinar de El Hierro", "Valverde"],
}
ORDEN_ISLAS = ["El Hierro", "La Palma", "La Gomera", "Tenerife", "Gran Canaria", "Fuerteventura", "Lanzarote"]
ISLA_DE = {m: i for i, ms in ISLAS.items() for m in ms}


def nombre_ine(n):
    """«Oliva, La» -> «La Oliva»."""
    if ", " in n:
        base, art = n.rsplit(", ", 1)
        if art in ("La", "El", "Los", "Las"):
            return art + " " + base
    return n


def poblacion():
    """Población por municipio e isla a 1 de enero (INE, Padrón)."""
    muni, anyo = {}, None
    for tabla in (2889, 2892):
        series = pide(f"https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{tabla}?nult=1")
        provincia_vista = False
        for s in series:
            if ". Total. Total habitantes" not in s["Nombre"] or not s["Data"]:
                continue
            if not provincia_vista:           # la primera serie de cada tabla es la provincia
                provincia_vista = True
                continue
            muni[nombre_ine(s["Nombre"].split(". Total.")[0])] = int(s["Data"][0]["Valor"])
            anyo = s["Data"][0]["Anyo"]
    faltan = set(ISLA_DE) - set(muni)
    assert not faltan and len(muni) == 88, ("municipios sin cuadrar", faltan, len(muni))
    islas = {i: sum(muni[m] for m in ms) for i, ms in ISLAS.items()}
    return muni, islas, anyo


def superficie():
    """Superficie en km² por municipio e isla (ISTAC; las islas incluyen sus islotes)."""
    meta = pide(f"{ISTAC}/indicators/v1.0/indicators/SUPERFICIE")
    datos = pide(f"{ISTAC}/indicators/v1.0/indicators/SUPERFICIE/data")
    titulo = {r["code"]: r["title"]["es"] for r in meta["dimension"]["GEOGRAPHICAL"]["representation"]}
    indice = datos["dimension"]["GEOGRAPHICAL"]["representation"]["index"]
    anyo = list(datos["dimension"]["TIME"]["representation"]["index"])[0]
    muni, islas = {}, {}
    for codigo, k in indice.items():
        km2 = round(float(datos["observation"][k]) / 100, 2)    # hectáreas -> km²
        t = titulo[codigo]
        if t.endswith(" (Isla)"):
            islas[t[:-7]] = km2
        elif codigo.isdigit():
            muni[t] = km2
    return muni, islas, anyo


# ---------------------------------------------------------------- formato

def miles(n):
    return f"{n:,}".replace(",", ".")


def km2(x):
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " km²"


def pct(x):
    return f"{x:.1f}".replace(".", ",") + " %"


# ---------------------------------------------------------------- preguntas

def preguntas(pob, sup):
    muni, islas_p, anyo_p = pob
    smuni, islas_s, anyo_s = sup
    total = sum(muni.values())

    F_INE = {"nombre": "INE · Cifras oficiales del Padrón municipal",
             "url": "https://www.ine.es/dynt3/inebase/index.htm?padre=517",
             "fecha": f"1 de enero de {anyo_p}"}
    F_INE_ISLA = dict(F_INE, nombre="INE · Padrón municipal (suma de los municipios de cada isla)")
    F_SUP = {"nombre": "ISTAC · Superficie (las islas incluyen sus islotes)",
             "url": f"{ISTAC}/indicators/v1.0/indicators/SUPERFICIE", "fecha": str(anyo_s)}
    F_PN = {"nombre": "Gobierno de Canarias · Parques Nacionales de Canarias",
            "url": "https://www.gobiernodecanarias.org/parquesnacionales/", "fecha": CONSULTA}
    F_PM = {"nombre": "UNESCO · Lista del Patrimonio Mundial (España)",
            "url": "https://whc.unesco.org/es/list/?iso=es", "fecha": CONSULTA}
    F_OAPN = {"nombre": "MITECO · Red de Parques Nacionales (fechas de declaración)",
              "url": "https://www.miteco.gob.es/content/dam/miteco/es/ceneam/quienes-somos/dossier_parques_2015_tcm30-165584.pdf",
              "fecha": "dossier de 2015"}
    F_TEIDE = {"nombre": "IGN y Grafcan · altitud oficial del Teide",
               "url": "https://pre-web.grafcan.es/files/2019/11/20191022_Medicion_Teide_ElDia.pdf",
               "fecha": "medición del IGN (1983), confirmada por Grafcan (2011)"}

    def isla_mas(d, mayor=True):
        return sorted(d.items(), key=lambda x: -x[1] if mayor else x[1])

    def p_isla(id_, enunciado, correcta, dato, fuente):
        return {"id": id_, "tipo": "isla", "enunciado": enunciado, "opciones": ORDEN_ISLAS,
                "correcta": correcta, "dato": dato, "fuente": fuente}

    def p_masmenos(id_, a, b, medida):
        if medida == "habitantes":
            va, vb, fmt, f = muni.get(a, islas_p.get(a)), muni.get(b, islas_p.get(b)), lambda v: miles(v) + " hab.", F_INE
            if a in islas_p:
                f = F_INE_ISLA
            pregunta = f"¿{a} tiene más o menos habitantes que {b}?"
        else:
            va, vb, fmt, f = smuni.get(a, islas_s.get(a)), smuni.get(b, islas_s.get(b)), km2, F_SUP
            pregunta = f"¿{a} tiene más o menos superficie que {b}?"
        assert va is not None and vb is not None and va != vb, (a, b)
        return {"id": id_, "tipo": "masmenos", "enunciado": pregunta,
                "a": {"nombre": a, "valor": va, "texto": fmt(va)},
                "b": {"nombre": b, "valor": vb, "texto": fmt(vb)},
                "correcta": "mas" if va > vb else "menos",
                "dato": f"{a}: {fmt(va)} · {b}: {fmt(vb)}", "fuente": f}

    def p_ordena(id_, enunciado, nombres, valores, fmt, fuente, orden="desc"):
        el = [{"nombre": n, "valor": v, "texto": fmt(v)} for n, v in zip(nombres, valores)]
        return {"id": id_, "tipo": "ordena", "enunciado": enunciado, "orden": orden, "elementos": el, "fuente": fuente}

    def p_opciones(id_, enunciado, opciones, correcta, dato, fuente):
        assert correcta in opciones
        return {"id": id_, "tipo": "opciones", "enunciado": enunciado, "opciones": opciones,
                "correcta": correcta, "dato": dato, "fuente": fuente}

    mas_pob, menos_pob = isla_mas(islas_p)[0], isla_mas(islas_p, False)[0]
    sup_orden = isla_mas(islas_s)
    mun_ext = isla_mas(smuni)[0]
    mun_pob = isla_mas(muni)
    mun_menos = isla_mas(muni, False)[0]
    gc_menos = min(ISLAS["Gran Canaria"], key=lambda m: muni[m])
    dos_grandes = (islas_p["Gran Canaria"] + islas_p["Tenerife"]) / total * 100
    assert sup_orden[0][0] == "Tenerife" and sup_orden[1][0] == "Fuerteventura"
    assert mun_ext[0] == "Pájara" and mun_menos[0] == "Betancuria" and gc_menos == "Artenara"
    assert mun_pob[1][0] == "Santa Cruz de Tenerife"

    q = [
        p_isla("pn-garajonay", "¿En qué isla está el Parque Nacional de Garajonay?", "La Gomera",
               "Garajonay está en La Gomera. Es parque nacional desde 1981 y Patrimonio Mundial desde 1986.", [F_PN, F_OAPN, F_PM]),
        p_isla("pn-timanfaya", "¿En qué isla está el Parque Nacional de Timanfaya?", "Lanzarote",
               "Timanfaya está en Lanzarote. Es uno de los cuatro parques nacionales de Canarias.", F_PN),
        p_isla("pn-taburiente", "¿En qué isla está el Parque Nacional de la Caldera de Taburiente?", "La Palma",
               "La Caldera de Taburiente está en La Palma. Es parque nacional desde 1954.", [F_PN, F_OAPN]),
        p_isla("isla-mas-grande", "¿Qué isla tiene más superficie?", sup_orden[0][0],
               f"{sup_orden[0][0]}, con {km2(sup_orden[0][1])}.", F_SUP),
        p_isla("isla-segunda", "¿Cuál es la segunda isla más grande de Canarias?", sup_orden[1][0],
               f"{sup_orden[1][0]} ({km2(sup_orden[1][1])}), por delante de Gran Canaria ({km2(islas_s['Gran Canaria'])}).", F_SUP),
        p_isla("isla-mas-gente", "¿Qué isla tiene más habitantes?", mas_pob[0],
               f"{mas_pob[0]}, con {miles(mas_pob[1])} habitantes. Gran Canaria tiene {miles(islas_p['Gran Canaria'])}.", F_INE_ISLA),
        p_isla("isla-menos-gente", "De las siete islas mayores, ¿cuál tiene menos habitantes?", menos_pob[0],
               f"{menos_pob[0]}, con {miles(menos_pob[1])} habitantes.", F_INE_ISLA),
        p_isla("pm-risco", "¿En qué isla está Risco Caído, Patrimonio Mundial desde 2019?", "Gran Canaria",
               "El Paisaje cultural del Risco Caído y las montañas sagradas está en Gran Canaria.", F_PM),
        p_isla("pm-laguna", "¿En qué isla está San Cristóbal de La Laguna, Patrimonio Mundial desde 1999?", "Tenerife",
               "La Laguna está en Tenerife.", F_PM),
        p_isla("mun-extenso", "¿En qué isla está el municipio más extenso de Canarias?", ISLA_DE[mun_ext[0]],
               f"Es {mun_ext[0]}, en {ISLA_DE[mun_ext[0]]}, con {km2(mun_ext[1])}.", F_SUP),

        p_masmenos("mm-tejeda", "Tejeda", "Betancuria", "habitantes"),
        p_masmenos("mm-arona", "Arona", "Telde", "habitantes"),
        p_masmenos("mm-santalucia", "Santa Lucía de Tirajana", "Arrecife", "habitantes"),
        p_masmenos("mm-artenara", "Artenara", "Agulo", "habitantes"),
        p_masmenos("mm-adeje", "Adeje", "Puerto del Rosario", "habitantes"),
        p_masmenos("mm-sanbartolome", "San Bartolomé de Tirajana", "Arrecife", "habitantes"),
        p_masmenos("mm-laguna", "San Cristóbal de La Laguna", "Santa Cruz de Tenerife", "habitantes"),
        p_masmenos("mm-lanzarote", "Lanzarote", "La Palma", "habitantes"),
        p_masmenos("mm-orotava", "La Orotava", "Mogán", "superficie"),
        p_masmenos("mm-pajara", "Pájara", "La Gomera", "superficie"),

        p_ordena("or-islas-gente", "Ordena estas islas de más a menos habitantes",
                 ["Gran Canaria", "Lanzarote", "Fuerteventura", "La Palma"],
                 [islas_p[i] for i in ["Gran Canaria", "Lanzarote", "Fuerteventura", "La Palma"]],
                 lambda v: miles(v) + " hab.", F_INE_ISLA),
        p_ordena("or-islas-sup", "Ordena estas islas de más a menos superficie",
                 ["Lanzarote", "La Palma", "La Gomera", "El Hierro"],
                 [islas_s[i] for i in ["Lanzarote", "La Palma", "La Gomera", "El Hierro"]], km2, F_SUP),
        p_ordena("or-mun-gente", "Ordena estos municipios de más a menos habitantes",
                 ["Las Palmas de Gran Canaria", "San Cristóbal de La Laguna", "Telde", "Arona"],
                 [muni[m] for m in ["Las Palmas de Gran Canaria", "San Cristóbal de La Laguna", "Telde", "Arona"]],
                 lambda v: miles(v) + " hab.", F_INE),
        p_ordena("or-mun-sup", "Ordena estos municipios de más a menos superficie",
                 ["Pájara", "San Bartolomé de Tirajana", "La Orotava", "Mogán"],
                 [smuni[m] for m in ["Pájara", "San Bartolomé de Tirajana", "La Orotava", "Mogán"]], km2, F_SUP),
        p_ordena("or-patrimonio", "Ordena del más antiguo al más reciente como Patrimonio Mundial",
                 ["Parque Nacional de Garajonay", "San Cristóbal de La Laguna", "Parque Nacional del Teide",
                  "Risco Caído y montañas sagradas"], [1986, 1999, 2007, 2019], lambda v: str(v), F_PM, orden="asc"),

        p_opciones("op-municipios", "¿Cuántos municipios tiene Canarias?", ["82", "88", "94", "101"], str(len(muni)),
                   f"Canarias tiene {len(muni)} municipios: 34 en la provincia de Las Palmas y 54 en la de Santa Cruz de Tenerife.", F_INE),
        p_opciones("op-menos-gente", "¿Cuál es el municipio con menos habitantes de Canarias?",
                   ["Betancuria", "Artenara", "Agulo", "Tejeda"], mun_menos[0],
                   f"{mun_menos[0]}, con {miles(mun_menos[1])} habitantes.", F_INE),
        p_opciones("op-dos-grandes", "¿Qué parte de la población canaria vive en Gran Canaria o en Tenerife?",
                   ["Unos 2 de cada 3", "Unos 3 de cada 4", "Unos 4 de cada 5", "Unos 9 de cada 10"],
                   "Unos 4 de cada 5",
                   f"El {pct(dos_grandes)}: {miles(islas_p['Gran Canaria'] + islas_p['Tenerife'])} de {miles(total)} habitantes.", F_INE_ISLA),
        p_opciones("op-total", "¿Cuántos habitantes tiene Canarias, más o menos?",
                   ["1,8 millones", "2,25 millones", "2,7 millones", "3,1 millones"], "2,25 millones",
                   f"{miles(total)} habitantes.", F_INE),
        p_opciones("op-teide", "¿Cuánto mide el Teide?", ["3.555 m", "3.715 m", "3.718 m", "3.812 m"], "3.715 m",
                   "La altitud oficial es 3.715 m. La cifra de 3.718 m sigue apareciendo en muchos sitios, pero no es la oficial.", F_TEIDE),
        p_opciones("op-segundo", "Después de Las Palmas de Gran Canaria, ¿cuál es el municipio con más habitantes?",
                   ["Santa Cruz de Tenerife", "San Cristóbal de La Laguna", "Telde", "Arona"], mun_pob[1][0],
                   f"{mun_pob[1][0]}, con {miles(mun_pob[1][1])} habitantes.", F_INE),
        p_opciones("op-gc-menos", "¿Qué municipio de Gran Canaria tiene menos habitantes?",
                   ["Artenara", "Tejeda", "Valleseco", "Agaete"], gc_menos,
                   f"{gc_menos}, con {miles(muni[gc_menos])} habitantes. Tejeda tiene {miles(muni['Tejeda'])}.", F_INE),
    ]
    # comprobaciones de las respuestas fijas
    assert len(muni) == 88
    assert 78 < dos_grandes < 85
    assert 2.15e6 < total < 2.35e6
    return q


# ---------------------------------------------------------------- sitios del mapa

# (nombre que se enseña, búsqueda, id en CartoCiudad, categoría, isla si no sale del municipio)
SITIOS = [
    ("Roque Nublo", "Roque Nublo", "ngbe_2627492", "montanas", None),
    ("Roque Bentayga", "Roque Bentayga", "ngbe_2627472", "montanas", None),
    ("Dunas de Maspalomas", "Dunas de Maspalomas", "BTN_341", "playas", None),
    ("Playa de Las Canteras", "Playa de Las Canteras", "ngbe_2627087", "playas", None),
    ("Teror", "Teror", "BTN_539653", "pueblos", None),
    ("Cueva Pintada de Gáldar", "Cueva Pintada", "BTN_486868", "lugares", None),
    ("Pico del Teide", "Pico del Teide", "ngbe_2637213", "montanas", None),
    ("Roques de García", "Roques de García", "ngbe_2637882", "montanas", None),
    ("Garachico", "Garachico", "BTN_542203", "pueblos", None),
    ("Playa de Las Teresitas", "Las Teresitas", "ngbe_2637314", "playas", None),
    ("Basílica de Candelaria", "Basilica de Candelaria", "BTN_428246", "lugares", None),
    ("Barranco de Masca", "Barranco de Masca", "ngbe_2632712", "lugares", None),
    ("Montañas del Fuego", "Montañas del Fuego", "ngbe_2629895", "montanas", None),
    ("Jameos del Agua", "Jameos del Agua", "ngbe_2629328", "lugares", None),
    ("Mirador del Río", "Mirador del Río", "BTN_513322", "lugares", None),
    ("Teguise", "Teguise", "ngbe_2863833", "pueblos", None),
    ("Punta del Papagayo", "Papagayo", "ngbe_2638598", "playas", None),
    ("Playa de Famara", "Playa de Famara", "ngbe_2630069", "playas", None),
    ("Caleta de Sebo", "Caleta de Sebo", "BTN_4338721", "pueblos", "La Graciosa"),
    ("Betancuria", "Betancuria", "BTN_540606", "pueblos", None),
    ("Playa de Cofete", "Playa de Cofete", "ngbe_2622973", "playas", None),
    ("Montaña de Tindaya", "Montaña de Tindaya", "ngbe_2622468", "montanas", None),
    ("Playa de Sotavento de Jandía", "Playa de Sotavento", "ngbe_2623016", "playas", None),
    ("Roque de los Muchachos", "Roque de los Muchachos", "ngbe_3300894", "montanas", None),
    ("Playa de Nogales", "Playa de Nogales", "ngbe_2631850", "playas", None),
    ("Bosque de Los Tilos", "Bosque de Los Tilos", "ngbe_2630588", "lugares", None),
    ("Faro de Fuencaliente", "Faro de Fuencaliente", "BTN_377809", "lugares", None),
    ("Roque de Agando", "Roque de Agando", "ngbe_2628629", "montanas", None),
    ("Alto de Garajonay", "Garajonay", "ngbe_2638528", "montanas", None),
    ("Agulo", "Agulo", "BTN_542185", "pueblos", None),
    ("Playa de Valle Gran Rey", "Valle Gran Rey", "ngbe_2628515", "playas", None),
    ("Roque de la Bonanza", "Roque de la Bonanza", "ngbe_2619941", "montanas", None),
    ("Faro de Orchilla", "Faro de Orchilla", "BTN_377812", "lugares", None),
    ("La Restinga", "Puerto de La Restinga", "BTN_4338709", "pueblos", None),
]
CATEGORIAS = [
    {"id": "pueblos", "nombre": "Pueblos"},
    {"id": "montanas", "nombre": "Roques y montañas"},
    {"id": "playas", "nombre": "Playas y costa"},
    {"id": "lugares", "nombre": "Monumentos y lugares"},
]
FUENTE_ID = {"ngbe": "IGN · Nomenclátor Geográfico Básico de España", "BTN": "IGN · Base Topográfica Nacional"}


def sitios():
    out = []
    for nombre, busca, id_, cat, isla in SITIOS:
        url = CARTOCIUDAD + "?" + urllib.parse.urlencode({"q": busca, "limit": 10, "no_process": "callejero,carretera,portal,codpost,expendeduria,refcatastral,punto_recarga_electrica"})
        candidatos = pide(url)
        c = next((x for x in candidatos if x["id"] == id_), None)
        assert c, ("sin resultado", nombre, id_)
        muni = c["muni"]
        isla = isla or ISLA_DE[muni]
        out.append({
            "id": id_, "nombre": nombre, "categoria": cat, "isla": isla, "municipio": muni,
            "lat": round(c["lat"], 5), "lng": round(c["lng"], 5),
            "fuente": {"nombre": FUENTE_ID[id_.split("_")[0]] + " (vía CartoCiudad)", "url": url, "fecha": CONSULTA,
                       "registro": c["address"]},
        })
        time.sleep(1.5)
    return out


def islas_geojson():
    feats = []
    base = f"{ISTAC}/structural-resources/v1.0/variables/VR_TERRITORIO/variableelements"
    nombres = {"ISLA_LANZAROTE": "Lanzarote", "ISLA_FUERTEVENTURA": "Fuerteventura", "ISLA_GRAN_CANARIA": "Gran Canaria",
               "ISLA_TENERIFE": "Tenerife", "ISLA_LA_PALMA": "La Palma", "ISLA_GOMERA": "La Gomera", "ISLA_HIERRO": "El Hierro"}
    for codigo, nombre in nombres.items():           # Lanzarote incluye La Graciosa y los islotes del norte
        d = pide(f"{base}/{codigo}/geoinfo")
        g = d["features"][0]["geometry"]
        feats.append({"type": "Feature", "properties": {"isla": nombre}, "geometry": g})
        time.sleep(0.4)
    return {"type": "FeatureCollection",
            "fuente": f"ISTAC · geometrías de las islas (VR_TERRITORIO), {CONSULTA}",
            "features": feats}


def guarda(nombre, obj):
    with open(os.path.join(AQUI, nombre), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":") if nombre.endswith("geojson") else None,
                  indent=None if nombre.endswith("geojson") else 1)
        f.write("\n")
    print("ok", nombre)


if __name__ == "__main__":
    pob, sup = poblacion(), superficie()
    guarda("preguntas-canarias.json", {
        "titulo": "Test de Canarias",
        "url": "https://hbtdata.es/juegos/test/",
        "partida": 10,
        "actualizado": HOY.isoformat(),
        "niveles": [
            {"desde": 0, "titulo": "Recién llegado", "texto": "Hay mucha isla por descubrir. Repite y verás."},
            {"desde": 4, "titulo": "De guagua y paseo", "texto": "Te mueves bien, pero alguna isla se te escapa."},
            {"desde": 7, "titulo": "Canario de manual", "texto": "Te sabes las islas de punta a punta."},
            {"desde": 10, "titulo": "Enciclopedia isleña", "texto": "Ni un fallo. Esto ya es de ISTAC."},
        ],
        "preguntas": preguntas(pob, sup),
    })
    guarda("sitios-canarias.json", {
        "titulo": "¿Dónde está?",
        "url": "https://hbtdata.es/juegos/donde-esta/",
        "categorias": CATEGORIAS,
        "filtros_isla": [
            {"id": "lanzarote", "nombre": "Lanzarote y La Graciosa", "islas": ["Lanzarote", "La Graciosa"]},
            {"id": "fuerteventura", "nombre": "Fuerteventura", "islas": ["Fuerteventura"]},
            {"id": "gran-canaria", "nombre": "Gran Canaria", "islas": ["Gran Canaria"]},
            {"id": "tenerife", "nombre": "Tenerife", "islas": ["Tenerife"]},
            {"id": "la-gomera", "nombre": "La Gomera", "islas": ["La Gomera"]},
            {"id": "la-palma", "nombre": "La Palma", "islas": ["La Palma"]},
            {"id": "el-hierro", "nombre": "El Hierro", "islas": ["El Hierro"]},
        ],
        "actualizado": HOY.isoformat(),
        "sitios": sitios(),
    })
    guarda("islas.geojson", islas_geojson())
