// Indexador del chat de hbtdata.es
//
// Trocea las páginas de la web y llms.txt en trozos con su título y URL,
// los guarda en chat/trozos.json y, con --subir, los manda al Worker, que
// calcula los embeddings y los guarda en Vectorize.
//
// Uso (desde la raíz del repo, Node 18 o superior, sin dependencias):
//   node chat/indexar.mjs                  -> solo genera chat/trozos.json
//   node chat/indexar.mjs --subir          -> genera y sube (borra los trozos que ya no existen)
//   node chat/indexar.mjs --probar "¿Cuánto cuesta una web?"   -> parecido de cada trozo
//
// Para --subir y --probar hacen falta dos variables de entorno:
//   CHAT_URL   = https://hbtdata-chat.<tu-subdominio>.workers.dev
//   CHAT_TOKEN = el ADMIN_TOKEN que se guardó con `wrangler secret put`

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const SALIDA = join(RAIZ, 'chat', 'trozos.json');
const WEB = 'https://hbtdata.es';
const MAX = 1000; // caracteres por trozo (aprox.)
const MIN = 80; // trozos más cortos no aportan nada (solo un título suelto)
// Textos de botones y enlaces que no dicen nada fuera de la página
const BOTONES = /^(entrar|abrir( la web| el mapa)?|código|ver( ejemplos| procesos con ia| mi portfolio de datos)?|pedir una propuesta|hablemos|cuéntame tu negocio|jugar|open( the site| the map)?|code|let's talk)$/i;

// Páginas que entran en el chat. Si se añade una sección nueva a la web, va aquí.
const PAGINAS = [
  { archivo: 'index.html', url: `${WEB}/`, nombre: 'Portfolio', idioma: 'es' },
  { archivo: 'webs/index.html', url: `${WEB}/webs/`, nombre: 'Webs para negocios', idioma: 'es' },
  { archivo: 'juegos/index.html', url: `${WEB}/juegos/`, nombre: 'Juegos', idioma: 'es' },
  { archivo: 'juegos/test/index.html', url: `${WEB}/juegos/test/`, nombre: 'Test de Canarias', idioma: 'es' },
  { archivo: 'juegos/donde-esta/index.html', url: `${WEB}/juegos/donde-esta/`, nombre: '¿Dónde está?', idioma: 'es' },
  { archivo: 'en/index.html', url: `${WEB}/en/`, nombre: 'Portfolio (English)', idioma: 'en' },
];

// ---------------------------------------------------------------------------

function main() {
  const args = process.argv.slice(2);
  if (args[0] === '--probar') return probar(args.slice(1).join(' '));

  const trozos = [];
  for (const p of PAGINAS) {
    const ruta = join(RAIZ, p.archivo);
    if (!existsSync(ruta)) {
      console.warn(`(se salta ${p.archivo}: no existe en esta rama)`);
      continue;
    }
    trozos.push(...trocearHtml(readFileSync(ruta, 'utf8'), p));
  }
  trozos.push(...trocearLlms(readFileSync(join(RAIZ, 'llms.txt'), 'utf8')));

  // Ids estables: si el texto de un trozo no cambia, su id tampoco.
  const vistos = new Set();
  for (const t of trozos) {
    let id = hash(`${t.url}|${t.titulo}|${t.texto}`);
    while (vistos.has(id)) id = hash(id);
    vistos.add(id);
    t.id = id;
  }

  const anteriores = existsSync(SALIDA) ? JSON.parse(readFileSync(SALIDA, 'utf8')).trozos.map((t) => t.id) : [];
  const borrar = anteriores.filter((id) => !vistos.has(id));

  writeFileSync(SALIDA, JSON.stringify({ generado: new Date().toISOString(), trozos }, null, 2) + '\n');
  const caracteres = trozos.reduce((s, t) => s + t.texto.length, 0);
  console.log(`${trozos.length} trozos (${caracteres} caracteres) en chat/trozos.json`);
  for (const t of trozos) console.log(`  ${String(t.texto.length).padStart(4)}  ${t.titulo}`);

  if (args[0] === '--subir') return subir(trozos, borrar);
}

// ---------------------------------------------------------------------------
// HTML -> trozos

function trocearHtml(html, pagina) {
  let cuerpo = (html.match(/<main\b[^>]*>([\s\S]*?)<\/main>/i) || html.match(/<body\b[^>]*>([\s\S]*?)<\/body>/i) || [, html])[1];
  cuerpo = cuerpo
    .replace(/<(script|style|svg|noscript|template|form|canvas)\b[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<ul\b[^>]*aria-hidden="true"[^>]*>[\s\S]*?<\/ul>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ');

  const trozos = [];
  const secciones = [...cuerpo.matchAll(/<section\b([^>]*)>([\s\S]*?)<\/section>/gi)];

  for (const [, attrs, contenido] of secciones) {
    const id = (attrs.match(/\bid="([^"]+)"/) || [])[1];
    const url = id ? `${pagina.url}#${id}` : pagina.url;
    const encabezado = (contenido.match(/<h[12]\b[^>]*>([\s\S]*?)<\/h[12]>/i) || contenido.match(/<h3\b[^>]*>([\s\S]*?)<\/h3>/i) || [])[1];
    const titulo = `${pagina.nombre} · ${encabezado ? aTexto(encabezado).replace(/\n/g, ' ') : id || 'Inicio'}`;

    // Cada pregunta frecuente (<details>) va en su propio trozo.
    let resto = contenido;
    for (const [bloque, interior] of contenido.matchAll(/<details\b[^>]*>([\s\S]*?)<\/details>/gi)) {
      const pregunta = aTexto((interior.match(/<summary\b[^>]*>([\s\S]*?)<\/summary>/i) || [])[1] || '');
      const respuesta = aTexto(interior.replace(/<summary\b[\s\S]*?<\/summary>/i, ''));
      if (pregunta && respuesta) {
        trozos.push({ url, titulo: `${pagina.nombre} · ${pregunta}`, texto: `${pregunta}\n${respuesta}`, idioma: pagina.idioma });
      }
      resto = resto.replace(bloque, ' ');
    }

    for (const texto of empaquetar(aTexto(resto))) trozos.push({ url, titulo, texto, idioma: pagina.idioma });
  }

  // Lo que queda fuera de las secciones (p. ej., la cinta de sectores de /webs/)
  const fuera = aTexto(cuerpo.replace(/<section\b[\s\S]*?<\/section>/gi, ' '));
  if (fuera.length > 60) {
    for (const texto of empaquetar(fuera)) trozos.push({ url: pagina.url, titulo: `${pagina.nombre} · Otros`, texto, idioma: pagina.idioma });
  }
  return trozos;
}

function aTexto(html) {
  const lineas = decodificar(
    html
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/(p|li|h[1-6]|div|summary|tr|dt|dd|figcaption|blockquote|header|footer|ol|ul)>/gi, '\n')
      .replace(/<li\b[^>]*>/gi, '\n')
      .replace(/<[^>]+>/g, ' ')
  )
    .split('\n')
    .map((l) => l.replace(/[ \t ]+/g, ' ').trim())
    .filter((l) => l && !/^\/\/$/.test(l) && !BOTONES.test(l));
  // Quita líneas repetidas seguidas
  return lineas.filter((l, i) => l !== lineas[i - 1]).join('\n');
}

function decodificar(s) {
  const nombres = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', laquo: '«', raquo: '»', middot: '·', mdash: '—', ndash: '–', hellip: '…', euro: '€', copy: '©', iexcl: '¡', iquest: '¿' };
  return s
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(Number(d)))
    .replace(/&([a-z]+);/gi, (m, n) => nombres[n.toLowerCase()] ?? m);
}

// Junta líneas en trozos de hasta MAX caracteres sin partir frases.
function empaquetar(texto) {
  const trozos = [];
  let actual = '';
  for (const linea of texto.split('\n')) {
    if (actual && actual.length + linea.length + 1 > MAX) {
      trozos.push(actual);
      actual = '';
    }
    actual = actual ? `${actual}\n${linea}` : linea.slice(0, MAX * 2);
  }
  if (actual.length >= MIN) trozos.push(actual);
  return trozos;
}

// ---------------------------------------------------------------------------
// llms.txt -> un trozo por apartado "## "

function trocearLlms(texto) {
  const trozos = [];
  const partes = texto.split(/^## /m);
  const cabecera = partes.shift().trim();
  if (cabecera) trozos.push({ url: `${WEB}/`, titulo: 'Resumen · hbtdata', texto: cabecera.replace(/^# .*\n/, '').trim(), idioma: 'es' });

  for (const parte of partes) {
    const [primera, ...resto] = parte.split('\n');
    const cuerpo = resto.join('\n').trim();
    const ingles = /^english/i.test(primera.trim());
    const enlace = (cuerpo.match(/https:\/\/hbtdata\.es\/[\w\-/]*/) || [])[0];
    const url = ingles ? `${WEB}/en/` : enlace || `${WEB}/`;
    for (const t of empaquetar(cuerpo)) {
      trozos.push({ url, titulo: `Resumen · ${primera.trim()}`, texto: t, idioma: ingles ? 'en' : 'es' });
    }
  }
  return trozos;
}

// ---------------------------------------------------------------------------
// Worker

function credenciales() {
  const url = (process.env.CHAT_URL || '').replace(/\/+$/, '');
  const token = process.env.CHAT_TOKEN || '';
  if (!url || !token) {
    console.error('Faltan CHAT_URL y CHAT_TOKEN. En PowerShell:\n  $env:CHAT_URL="https://hbtdata-chat.TU-SUBDOMINIO.workers.dev"\n  $env:CHAT_TOKEN="tu token"');
    process.exit(1);
  }
  return { url, token };
}

async function subir(trozos, borrar) {
  const { url, token } = credenciales();
  const res = await fetch(`${url}/admin/indexar`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${token}` },
    body: JSON.stringify({ trozos, borrar }),
  });
  console.log(res.status, await res.text());
  if (!res.ok) process.exit(1);
}

async function probar(pregunta) {
  if (!pregunta) {
    console.error('Uso: node chat/indexar.mjs --probar "tu pregunta"');
    process.exit(1);
  }
  const { url, token } = credenciales();
  const res = await fetch(`${url}/admin/buscar?q=${encodeURIComponent(pregunta)}`, { headers: { authorization: `Bearer ${token}` } });
  const datos = await res.json();
  if (!res.ok) return console.error(res.status, datos);
  console.log(`Umbral actual: ${datos.umbral}`);
  for (const r of datos.resultados) console.log(`  ${r.score >= datos.umbral ? '✔' : '·'} ${r.score.toFixed(3)}  ${r.titulo}`);
}

function hash(s) {
  return createHash('sha1').update(s).digest('hex').slice(0, 20);
}

main();
