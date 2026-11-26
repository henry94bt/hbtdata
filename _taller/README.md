# _taller

Herramientas para generar partes de hbtdata.es. No se publica: `.htaccess` devuelve 404 para `/_taller/`.

## recursos/ → hbtdata.es/recursos/

| Archivo | Qué hace |
| --- | --- |
| `recursos.json` | Fuente de todos los recursos. Para añadir uno, una entrada nueva |
| `generar.py` | Genera `recursos/index.html` y `recursos/<slug>/index.html` |
| `pdf/generar_pdf.py` | Maqueta las guías en HTML y las pasa a PDF con Playwright; también `assets/og-recursos.png` |
| `probar.py` | Pruebas con Playwright en escritorio y móvil, con capturas |

Flujo:

```bash
python3 _taller/recursos/pdf/generar_pdf.py   # si cambia algún PDF
python3 _taller/recursos/generar.py           # todo, borradores incluidos (con etiqueta y noindex)
python3 _taller/recursos/probar.py /tmp/capturas
```

Para publicar: poner `"estado": "publicado"` en lo que esté revisado y ejecutar
`python3 _taller/recursos/generar.py --publicar`, que deja fuera los borradores y
añade `/recursos/` a `sitemap.xml` y `llms.txt`. Subir a `main` solo con el sí de Henry
(se despliega solo en hbtdata.es), y nunca antes del 29N.

## proyectos/ → hbtdata.es/proyectos/

| Archivo | Qué hace |
| --- | --- |
| `gas_tracker.py` | Regenera los dos gráficos de `/proyectos/canarias-gas-tracker/` (mediana por isla y días con datos) desde el `historico_precios.csv` del repo canarias-gas-tracker, e imprime las cifras que usa el texto |
| `og_gas_tracker.py` | `assets/og-gas-tracker.png` con Playwright |

```bash
python3 _taller/proyectos/gas_tracker.py ../canarias-gas-tracker/historico_precios.csv
```

El texto de la página no se reescribe solo: si cambian las cifras que imprime el script, hay que tocarlo a mano.
Cada página de proyecto carga `assets/medicion.js` y `assets/fuentes/fuentes.css` y lleva «Privacidad» en el pie.

Reglas: solo material propio y probado; nada de La Pepa Studio ni de clientes; los
conectores enlazan a su fuente oficial; sin logo de Anthropic; textos en español de Canarias.
