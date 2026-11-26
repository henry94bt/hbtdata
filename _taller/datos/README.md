# _taller/datos → hbtdata.es/datos/

Sección de datos de Canarias. Cada página responde a una pregunta («¿Dónde está la gasolina más barata de Gran Canaria?»), con gráfico en la paleta de la marca, fecha y fuente debajo de cada gráfico, y los datos descargables.

## Gasolina

| Página | Qué tiene |
| --- | --- |
| `/datos/` | Portada de la sección: tarjetas con la pregunta y la cifra del día, y «Cómo leer estos datos» |
| `/datos/gasolina/` | ¿En qué isla está más barata? Gráfico de puntos por isla, tabla de las siete islas y evolución de Canarias |
| `/datos/gasolina/<isla>/` | ¿Dónde está la más barata de la isla? Ranking (con empates), mapa, mediana por municipio y evolución frente a Canarias |

Todas tienen selector Gasolina 95 / Diésel (sin JavaScript se ven los dos), preguntas frecuentes, JSON-LD (`WebPage`, `Dataset`, `BreadcrumbList`, `FAQPage` y la `#person` de la portada), `assets/medicion.js`, `assets/fuentes/fuentes.css` y «Privacidad» en el pie, como pide `brief-medicion.md`.

### Archivos

| Archivo | Qué hace |
| --- | --- |
| `generar.py` | Descarga, actualiza el histórico, rehace las páginas, el bloque `datos` de `sitemap.xml` y la sección «Datos de Canarias» de `llms.txt` |
| `fuente_gasolina.py` | API del Ministerio (con reintentos y control de respuesta parcial, como en `canarias-gas-tracker`), limpieza, isla de cada gasolinera, histórico y rankings |
| `comun.py` | Las 7 islas, los 88 municipios y los formatos (precios con coma, céntimos, fechas) |
| `graficos.py` | Gráfico de puntos, líneas y mapa de isla, en HTML y SVG sin librerías |
| `plantilla.py` | Cabecera, barra, pie y JSON-LD comunes |
| `og.py` | Imágenes para compartir (`assets/og-datos.png`, `og-gasolina.png`, `og-gasolina-<isla>.png`). Sin precios, así que no caducan |
| `probar.py` | Comprobaciones con Playwright en móvil y escritorio, con capturas |

Datos publicados: `datos/gasolina/precios.csv` (precios del día por gasolinera; la columna `fecha` es cuándo los publicó el Ministerio, en hora canaria) y `datos/gasolina/historico.csv` (mediana, mínimo y máximo diarios por isla, Canarias y combustible).

### Cómo funciona cada día

`.github/workflows/datos-gasolina.yml` lanza `generar.py` a las 07:23 UTC y, como repesca, a las 12:41 UTC con `--si-falta` (solo hace algo si por la mañana falló). Si hay cambios, los sube a `main` y Hostinger los publica. La API corta más o menos una de cada dos peticiones, así que cada una se repite hasta ocho veces con pausas cortas; si aun así falla, hay tres reintentos más (a los 5, 10 y 15 minutos). Si nada funciona, no se sube nada: la web sigue con los precios anteriores, que llevan su fecha.

```bash
python3 _taller/datos/generar.py                  # lo mismo que hace la acción
python3 _taller/datos/generar.py --sin-descarga   # rehacer las páginas tras cambiar el diseño o los textos
python3 _taller/datos/generar.py --sin-esperas    # en local, reintentos sin esperar minutos
python3 _taller/datos/og.py                       # si cambia el diseño de las imágenes para compartir
python3 _taller/datos/probar.py /tmp/capturas     # comprobar antes de subir
```

### Decisiones

- **Isla por municipio**, con la lista cerrada de los 88 municipios. Si el Ministerio escribe uno de forma nueva, se usa el contorno de las islas del ISTAC (el de `/juegos/`). Si tampoco, la gasolinera se deja fuera y se avisa en el registro.
- **Mediana** para todo lo que resume precios. Rankings con cifras y gráficos de puntos con el eje visible, porque las diferencias son de céntimos. Nada de barras.
- **Empates**: si la décima comparte precio con otras, entran todas (hasta 15) y se avisa. En las islas con menos de diez gasolineras salen todas y en el mapa se destaca solo la más barata.
- **Histórico**: del 15 de abril al 25 de noviembre de 2026 sale del `historico_precios.csv` de `canarias-gas-tracker` (`generar.py --sembrar RUTA`). Aquel CSV juntaba las gasolineras con el mismo rótulo en el mismo municipio (~430 al día en vez de ~500), así que las medianas de esos días pueden variar en una décima de céntimo. Desde el 26 de noviembre, el histórico es propio.
- **Hora**: la API da la hora peninsular; en las páginas sale la canaria (una hora menos).
- **Sin terceros**: el mapa es SVG propio (sin teselas) y «Cómo llegar» es un enlace normal a Google Maps. La única conexión externa sigue siendo GoatCounter.

### Para añadir otra página de datos

Una función `pagina_…` en `generar.py` con la misma estructura (pregunta como `h1`, entrada con la respuesta y la fecha, gráfico con `fuente`, preguntas, «Cómo está hecho»), su URL en `urls_datos()` y una tarjeta en `pagina_datos()`. Nada electoral ni que se lea como posición política.
