# Datos de los juegos

Todo lo que hay en esta carpeta sale de `construir.py`. Para actualizarlo (por ejemplo, cuando el INE publique un padrón nuevo):

```
python3 juegos/datos/construir.py
```

Solo usa la biblioteca estándar de Python. Si un dato cambia de forma que rompe una respuesta fija (por ejemplo, que Artenara deje de ser el municipio menos poblado de Gran Canaria), el script se para con un `assert` en vez de generar una pregunta falsa.

| Archivo | Qué es | Fuente |
| --- | --- | --- |
| `preguntas-canarias.json` | 32 preguntas del Test de Canarias | INE (Padrón municipal, tablas 2889 y 2892), ISTAC (indicador `SUPERFICIE`), UNESCO, Gobierno de Canarias, MITECO, IGN/Grafcan |
| `sitios-canarias.json` | 34 sitios de «¿Dónde está?» | IGN: Nomenclátor Geográfico Básico de España (`ngbe_…`) y Base Topográfica Nacional (`BTN_…`), consultados con el geocodificador de CartoCiudad |
| `islas.geojson` | Contorno de las 7 islas (Lanzarote incluye La Graciosa y los islotes) | ISTAC, `VR_TERRITORIO` |

## Reglas

- Cada pregunta y cada sitio llevan su fuente y su fecha. Si un dato no se encuentra, no entra.
- Nada político ni electoral.
- Las preguntas «a mano» (parques nacionales, Patrimonio Mundial, altura del Teide) están en la función `preguntas()` con su fuente escrita.

## Reutilizar el motor (p. ej. para Historia para Gandules)

- Test: `assets/juegos/test.js` lee cualquier JSON con el mismo formato (`data-preguntas` en el HTML). Tipos: `opciones`, `isla`, `masmenos`, `ordena`. El formato está documentado al principio del archivo.
- Mapa: `assets/juegos/donde.js` lee cualquier lista de sitios (`data-sitios`) con `nombre`, `categoria`, `isla`, `lat`, `lng` y `fuente`, más el contorno (`data-islas`).
