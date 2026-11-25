# Chat de hbtdata.es (prototipo RAG, gratis con Cloudflare)

Un chat que responde **solo con lo que pone en la web**. Vive en una burbuja abajo a la derecha de `/webs/` y no guarda nada: ni cookies ni conversaciones.

```
navegador (assets/chat.js)
   │  POST /api/chat {pregunta, historial}
   ▼
Worker de Cloudflare (chat/worker)
   1. ¿origen permitido? ¿límite por IP? ¿pregunta corta? ¿tiene pinta de código?
   2. embedding de la pregunta (Workers AI, bge-m3)
   3. busca los 4 trozos más parecidos (Vectorize)
   4. si ninguno pasa el UMBRAL → texto fijo, SIN llamar al modelo
   5. si hay contexto → el modelo (Gemma 4) responde solo con eso
   6. si la respuesta trae código → se descarta
   ▼
{respuesta, fuentes}
```

Los trozos salen de las páginas de la web y de `llms.txt` con `chat/indexar.mjs`.

## Qué cuesta

Nada mientras se quede en el plan gratis de Cloudflare (sin tarjeta):

- **Workers AI**: 10.000 neuronas al día. Una pregunta con ~2.000 tokens de contexto y una respuesta corta gasta unas 25 neuronas, así que dan para **unas 300-400 preguntas al día**. Si se acaban, el chat dice que vuelvas mañana. En el plan gratis no se cobra nunca: simplemente deja de responder.
- **Vectorize**: el índice de la web son ~50 trozos; muy lejos del límite gratis.
- **Workers**: 100.000 peticiones al día.

## Ponerlo en marcha (PowerShell, una sola vez)

Hace falta Node 18 o superior y una cuenta gratis de Cloudflare.

```powershell
cd C:\dev\hbtdata\chat\worker

# 1. Iniciar sesión en Cloudflare (abre el navegador)
npx wrangler login

# 2. Crear el índice vectorial (1024 dimensiones = las de bge-m3)
npx wrangler vectorize create hbtdata-chat --dimensions=1024 --metric=cosine

# 3. Publicar el Worker. Al final sale la URL: https://hbtdata-chat.XXXX.workers.dev
npx wrangler deploy

# 4. Crear el token de administración y guardarlo como secreto
[guid]::NewGuid().ToString("N")          # copia lo que salga
npx wrangler secret put ADMIN_TOKEN      # y pégalo aquí
```

Después, desde la raíz del repo:

```powershell
cd C:\dev\hbtdata
$env:CHAT_URL   = "https://hbtdata-chat.XXXX.workers.dev"
$env:CHAT_TOKEN = "el token del paso 4"

# 5. Trocear la web y subirla (calcula los embeddings en el Worker)
node chat/indexar.mjs --subir
```

## Calibrar el umbral

El umbral decide cuándo una pregunta "es de hbtdata". Se prueba así:

```powershell
node chat/indexar.mjs --probar "¿Cuánto cuesta una web?"
node chat/indexar.mjs --probar "¿Trabajas en Lanzarote?"
node chat/indexar.mjs --probar "Hazme un script en Python que ordene una lista"
node chat/indexar.mjs --probar "Resúmeme la Segunda Guerra Mundial"
```

Cada resultado sale con su parecido (✔ = pasa el umbral). Lo ideal: las preguntas de la web por encima y las que no tienen nada que ver por debajo. Si hace falta, cambia `UMBRAL` en `worker/wrangler.toml` y vuelve a hacer `npx wrangler deploy`. Empieza en 0.55.

## Probarlo en la web

1. En `webs/index.html`, pon la URL en la etiqueta del chat (si está vacía, la burbuja no sale):
   ```html
   <script src="../assets/chat.js" data-api="https://hbtdata-chat.XXXX.workers.dev/api/chat" defer></script>
   ```
2. Desde la raíz del repo: `py -m http.server 8000` y abre `http://localhost:8000/webs/`.

Antes de pasarlo a `main`, quita `localhost` y `127.0.0.1` de `ORIGENES` en `wrangler.toml` y vuelve a publicar.

## Cuando cambie la web

```powershell
node chat/indexar.mjs --subir
```

Solo sube lo que haya cambiado y borra del índice los trozos que ya no existen (compara con `chat/trozos.json`, que se guarda en el repo). Si se añade una página nueva, va en la lista `PAGINAS` de `indexar.mjs`.

## Contra el abuso

- **Filtro por relevancia**: si la pregunta no se parece a nada de la web, no se llama al modelo. Es la defensa principal contra usarlo para programar o hacer deberes, y además ahorra cupo.
- **Límite por IP**: 8 preguntas por minuto (`[[ratelimits]]` en `wrangler.toml`).
- **Solo desde hbtdata.es**: el navegador no deja usarlo desde otras webs (CORS). Ojo: esto no frena a alguien con `curl`; para eso está el límite por IP.
- **Tamaños**: 300 caracteres por pregunta, 4 mensajes de historial y respuestas cortas.
- **Detector de código** en la pregunta y en la respuesta.
- **Prompt con reglas**: sin precios ni plazos concretos, sin política, sin inventar, ignora instrucciones metidas en la pregunta.
- **Privacidad**: el Worker no registra el texto de las preguntas; solo errores técnicos.

## Para llevarlo a clientes (La Pepa)

La pieza es la misma para cualquier web: cambias `PAGINAS` en el indexador (o le pasas PDFs, cartas o FAQ en texto), el prompt de `SISTEMA` en el Worker y los textos de `assets/chat.js`. Lo que cambia con un cliente:

- **Un índice por cliente** (o un *namespace* por cliente en el mismo índice).
- **Tráfico**: con muchas visitas el cupo gratis se queda corto. El plan de pago de Workers cuesta 5 $ al mes e incluye las mismas 10.000 neuronas diarias; lo que pase de ahí se paga por uso.
- **Datos del cliente**: explicar dónde se procesan (Cloudflare) y no indexar nada personal.
- **Medir**: contar preguntas, cuántas quedan fuera del tema y cuántas acaban en contacto (sin guardar el texto), por ejemplo con Workers Analytics Engine.

## Ideas para la siguiente versión

- Turnstile (el captcha invisible de Cloudflare) si aparece abuso con scripts. Revisar antes si deja cookies.
- Un tope diario de preguntas por IP (con KV).
- Reindexar solo con una GitHub Action en cada push a `main`.
- Llevarlo a la portada y a `/en/` (la burbuja ya traduce sus textos con `data-idioma="en"`).

## Sin comprobar todavía en Cloudflare

Se probó en local con el Worker simulado (filtros, CORS, límite, cupo agotado, lotes de indexado) y la burbuja en escritorio y móvil. En la primera puesta en marcha, mira:

- Que `bge-m3` devuelve los vectores (el código acepta `data` y `response`).
- Que Gemma 4 no gasta los tokens "pensando". Si salen respuestas vacías, cambia `MODELO` a `@cf/meta/llama-3.1-8b-instruct-fp8-fast`, que el código también entiende.
