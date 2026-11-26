"""Piezas comunes de hbtdata.es/datos/: islas, municipios, formatos y fechas.

Solo biblioteca estándar.
"""
import unicodedata
from datetime import date, datetime
from zoneinfo import ZoneInfo

CANARIAS = ZoneInfo("Atlantic/Canary")

# Orden fijo de las islas (de este a oeste, como en el resto de la web).
ISLAS = [
    ("lanzarote", "Lanzarote"),
    ("fuerteventura", "Fuerteventura"),
    ("gran-canaria", "Gran Canaria"),
    ("tenerife", "Tenerife"),
    ("la-gomera", "La Gomera"),
    ("la-palma", "La Palma"),
    ("el-hierro", "El Hierro"),
]
NOMBRE_ISLA = dict(ISLAS)
# «de Gran Canaria», «de La Palma», «de El Hierro»: el artículo va con mayúscula porque es parte del nombre.
DE_ISLA = {s: f"de {n}" for s, n in ISLAS}

# Los 88 municipios de Canarias. Las claves se normalizan con norma(), así que da igual
# cómo vengan escritos (tildes, mayúsculas, «Oliva (La)» o «La Oliva»).
_MUNICIPIOS = {
    "gran-canaria": [
        "Agaete", "Agüimes", "La Aldea de San Nicolás", "Artenara", "Arucas", "Firgas", "Gáldar",
        "Ingenio", "Las Palmas de Gran Canaria", "Mogán", "Moya", "San Bartolomé de Tirajana",
        "Santa Brígida", "Santa Lucía de Tirajana", "Santa María de Guía de Gran Canaria", "Tejeda",
        "Telde", "Teror", "Valleseco", "Valsequillo de Gran Canaria", "Vega de San Mateo",
    ],
    "lanzarote": ["Arrecife", "Haría", "San Bartolomé", "Teguise", "Tías", "Tinajo", "Yaiza"],
    "fuerteventura": ["Antigua", "Betancuria", "La Oliva", "Pájara", "Puerto del Rosario", "Tuineje"],
    "tenerife": [
        "Adeje", "Arafo", "Arico", "Arona", "Buenavista del Norte", "Candelaria", "Fasnia",
        "Garachico", "Granadilla de Abona", "La Guancha", "Guía de Isora", "Güímar",
        "Icod de los Vinos", "La Matanza de Acentejo", "La Orotava", "Puerto de la Cruz",
        "Los Realejos", "El Rosario", "San Cristóbal de La Laguna", "San Juan de la Rambla",
        "San Miguel de Abona", "Santa Cruz de Tenerife", "Santa Úrsula", "Santiago del Teide",
        "El Sauzal", "Los Silos", "Tacoronte", "El Tanque", "Tegueste", "La Victoria de Acentejo",
        "Vilaflor de Chasna",
    ],
    "la-palma": [
        "Barlovento", "Breña Alta", "Breña Baja", "Fuencaliente de La Palma", "Garafía",
        "Los Llanos de Aridane", "El Paso", "Puntagorda", "Puntallana", "San Andrés y Sauces",
        "Santa Cruz de La Palma", "Tazacorte", "Tijarafe", "Villa de Mazo",
    ],
    "la-gomera": ["Agulo", "Alajeró", "Hermigua", "San Sebastián de La Gomera", "Valle Gran Rey", "Vallehermoso"],
    "el-hierro": ["Frontera", "El Pinar de El Hierro", "Valverde"],
}
# Nombres que usa el Ministerio y que no coinciden con el oficial completo.
_ALIAS = {"Vilaflor": "tenerife", "El Pinar": "el-hierro"}

assert sum(len(v) for v in _MUNICIPIOS.values()) == 88, "Tienen que ser los 88 municipios"


def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def nombre_natural(municipio):
    """«Palmas de Gran Canaria (Las)» → «Las Palmas de Gran Canaria»."""
    m = " ".join(str(municipio).split())
    if m.endswith(")") and " (" in m:
        base, art = m[:-1].rsplit(" (", 1)
        if art.lower() in ("la", "las", "el", "los"):
            m = f"{art.capitalize()} {base}"
    return m


def norma(texto):
    return " ".join(sin_tildes(nombre_natural(texto)).lower().replace("-", " ").split())


_ISLA_DE = {norma(m): isla for isla, lista in _MUNICIPIOS.items() for m in lista}
_ISLA_DE.update({norma(m): isla for m, isla in _ALIAS.items()})


def isla_de_municipio(municipio):
    return _ISLA_DE.get(norma(municipio))


def slug(texto):
    t = sin_tildes(nombre_natural(texto)).lower()
    return "-".join("".join(c if c.isalnum() else " " for c in t).split())


# ---------- formatos ----------

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def precio(v, unidad=" €"):
    """1.459 → «1,459 €»."""
    return f"{v:.3f}".replace(".", ",") + unidad


def precio_eje(v):
    return f"{v:.2f}".replace(".", ",") + " €"


def centimos(diferencia):
    """0.034 → «3,4 céntimos»; 0.01 → «1 céntimo»."""
    c = round(abs(diferencia) * 100, 1)
    if c == int(c):
        n = int(c)
        return f"{n} céntimo" + ("" if n == 1 else "s")
    return f"{c:.1f}".replace(".", ",") + " céntimos"


def numero(n):
    return f"{n:,}".replace(",", ".")


def fecha_larga(d):
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_con_dia(d):
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    return f"{DIAS[d.weekday()]} {fecha_larga(d)}"


def fecha_corta(d):
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    return f"{d.day} {MESES_CORTOS[d.month - 1]}"


def ahora():
    return datetime.now(CANARIAS)


def enumera(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " y " + items[-1]
