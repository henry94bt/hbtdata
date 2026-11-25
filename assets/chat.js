/* Chat de hbtdata.es — burbuja que pregunta al Worker (RAG sobre la propia web)
 *
 * Uso:
 *   <script src="../assets/chat.js" data-api="https://hbtdata-chat.XXX.workers.dev/api/chat" defer></script>
 * Opcional: data-idioma="en" (si no, se toma de <html lang>).
 *
 * Sin cookies ni almacenamiento: la conversación vive en memoria y se pierde
 * al cerrar la pestaña.
 */
(function () {
  'use strict';

  var script = document.currentScript;
  var API = script && script.dataset.api;
  if (!API) return;

  var idioma = (script.dataset.idioma || document.documentElement.lang || 'es').slice(0, 2) === 'en' ? 'en' : 'es';
  var T = {
    es: {
      abrir: 'Pregúntame',
      titulo: 'Pregunta a la web',
      subtitulo: 'Webs, procesos con IA y proyectos',
      bienvenida: 'Hola. Soy el asistente de hbtdata.es, una IA que responde con lo que pone en esta web. ¿Qué quieres saber?',
      sugerencias: ['¿Cuánto cuesta una web?', '¿Qué tareas se pueden hacer con IA?', '¿Trabajas fuera de Gran Canaria?'],
      placeholder: 'Escribe tu pregunta',
      enviar: 'Enviar',
      cerrar: 'Cerrar el chat',
      pensando: 'Buscando en la web…',
      aviso: 'Respuestas de una IA a partir de esta web: pueden fallar. Lo importante, confírmalo por correo. No se guarda la conversación.',
      fuentes: 'Más en',
      error: 'No pude conectar. Prueba otra vez o escribe a hbtdataanalyst@gmail.com.',
      tu: 'Tú',
      ia: 'hbtdata · IA',
    },
    en: {
      abrir: 'Ask me',
      titulo: 'Ask the site',
      subtitulo: 'Websites, AI processes and projects',
      bienvenida: "Hi. I'm the hbtdata.es assistant, an AI that answers with what's on this site. What would you like to know?",
      sugerencias: ['What projects has Henry built?', 'Can you build my website in English?', 'How does working together go?'],
      placeholder: 'Type your question',
      enviar: 'Send',
      cerrar: 'Close chat',
      pensando: 'Searching the site…',
      aviso: 'Answers from an AI based on this site: they can be wrong. Confirm anything important by email. Conversations are not stored.',
      fuentes: 'More at',
      error: "Couldn't connect. Try again or email hbtdataanalyst@gmail.com.",
      tu: 'You',
      ia: 'hbtdata · AI',
    },
  }[idioma];

  var MAX = 300;
  var historial = []; // { rol: 'usuario' | 'asistente', texto }
  var ocupado = false;

  // ---------------------------------------------------------------- estilos
  var css = [
    '.hbtc{--hc-fondo:#04161C;--hc-panel:#082A33;--hc-claro:#F7F3EC;--hc-tenue:rgba(247,243,236,.68);--hc-linea:rgba(247,243,236,.14);--hc-ocre:#F0A840;--hc-suave:#96D6D6;font-family:"Poppins",system-ui,sans-serif;color:var(--hc-claro)}',
    '.hbtc *{box-sizing:border-box}',
    '.hbtc [hidden]{display:none!important}',
    '.hbtc div,.hbtc p,.hbtc form{margin:0}',
    '.hbtc-boton{position:fixed;right:clamp(14px,3vw,28px);bottom:clamp(14px,3vw,28px);z-index:60;display:flex;align-items:center;gap:10px;padding:12px 18px 12px 14px;border:1px solid var(--hc-linea);border-radius:999px;background:var(--hc-panel);color:var(--hc-claro);font:500 15px/1 "Poppins",system-ui,sans-serif;cursor:pointer;box-shadow:0 10px 30px rgba(0,0,0,.35);transition:transform .2s ease,border-color .2s ease}',
    '.hbtc-boton:hover{border-color:var(--hc-ocre);transform:translateY(-2px)}',
    '.hbtc-boton:focus-visible,.hbtc button:focus-visible,.hbtc textarea:focus-visible,.hbtc a:focus-visible{outline:2px solid var(--hc-ocre);outline-offset:2px}',
    '.hbtc-icono{display:none}',
    '.hbtc-punto{width:10px;height:10px;border-radius:50%;background:var(--hc-ocre);box-shadow:0 0 0 0 rgba(240,168,64,.6);animation:hbtc-latido 2.4s infinite}',
    '@keyframes hbtc-latido{0%{box-shadow:0 0 0 0 rgba(240,168,64,.55)}70%{box-shadow:0 0 0 10px rgba(240,168,64,0)}100%{box-shadow:0 0 0 0 rgba(240,168,64,0)}}',
    '.hbtc-panel{position:fixed;right:clamp(14px,3vw,28px);bottom:clamp(14px,3vw,28px);z-index:61;width:min(400px,calc(100vw - 28px));height:min(600px,calc(100vh - 40px));display:flex;flex-direction:column;background:var(--hc-fondo);border:1px solid var(--hc-linea);border-radius:20px;box-shadow:0 24px 60px rgba(0,0,0,.5);overflow:hidden;opacity:0;transform:translateY(12px) scale(.98);transform-origin:bottom right;transition:opacity .2s ease,transform .2s ease;pointer-events:none}',
    '.hbtc-panel[data-abierto="true"]{opacity:1;transform:none;pointer-events:auto}',
    '.hbtc-cabeza{display:flex;align-items:center;gap:12px;padding:16px 16px 14px 18px;background:var(--hc-panel);border-bottom:1px solid var(--hc-linea)}',
    '.hbtc-sello{width:30px;height:30px;flex:none;color:var(--hc-claro)}',
    '.hbtc-cabeza strong{display:block;font-weight:600;font-size:15px}',
    '.hbtc-cabeza small{display:block;font:400 11px/1.4 "JetBrains Mono",ui-monospace,monospace;color:var(--hc-tenue);letter-spacing:.02em}',
    '.hbtc-cerrar{margin-left:auto;width:34px;height:34px;border:0;border-radius:50%;background:transparent;color:var(--hc-tenue);font-size:22px;line-height:1;cursor:pointer}',
    '.hbtc-cerrar:hover{color:var(--hc-claro);background:rgba(247,243,236,.08)}',
    '.hbtc-lista{flex:1;overflow-y:auto;padding:18px 16px 8px;display:flex;flex-direction:column;gap:14px;scrollbar-width:thin;scrollbar-color:var(--hc-linea) transparent}',
    '.hbtc-msj{max-width:88%;font-size:14.5px;line-height:1.55;white-space:pre-wrap;overflow-wrap:anywhere}',
    '.hbtc-msj small{display:block;margin-bottom:5px;font:500 10.5px/1 "JetBrains Mono",ui-monospace,monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--hc-tenue)}',
    '.hbtc-msj p{margin:0;padding:11px 14px;border-radius:14px}',
    '.hbtc-ia p{background:var(--hc-panel);border:1px solid var(--hc-linea);border-top-left-radius:4px}',
    '.hbtc-yo{align-self:flex-end;text-align:right}',
    '.hbtc-yo p{background:var(--hc-ocre);color:var(--hc-fondo);border-top-right-radius:4px;text-align:left}',
    '.hbtc-fuentes{margin-top:7px;font:400 12px/1.5 "JetBrains Mono",ui-monospace,monospace;color:var(--hc-tenue)}',
    '.hbtc-fuentes a{color:var(--hc-suave);text-decoration:underline;text-underline-offset:3px;margin-left:6px}',
    '.hbtc-pensando p{color:var(--hc-tenue);font-style:italic}',
    '.hbtc-sugerencias{display:flex;flex-wrap:wrap;gap:8px;padding:0 16px 12px}',
    '.hbtc-sugerencias button{padding:8px 12px;border:1px solid var(--hc-linea);border-radius:999px;background:transparent;color:var(--hc-claro);font:400 13px/1.2 "Poppins",system-ui,sans-serif;cursor:pointer;text-align:left}',
    '.hbtc-sugerencias button:hover{border-color:var(--hc-suave);color:var(--hc-suave)}',
    '.hbtc-form{display:flex;align-items:flex-end;gap:8px;margin:0 12px;padding:8px 8px 8px 14px;border:1px solid var(--hc-linea);border-radius:16px;background:var(--hc-panel)}',
    '.hbtc-form:focus-within{border-color:rgba(240,168,64,.6)}',
    '.hbtc-form textarea{flex:1;min-height:24px;max-height:110px;resize:none;border:0;background:transparent;color:var(--hc-claro);font:400 14.5px/1.5 "Poppins",system-ui,sans-serif;padding:4px 0}',
    '.hbtc-form textarea:focus{outline:none}',
    '.hbtc-form textarea::placeholder{color:var(--hc-tenue)}',
    '.hbtc-enviar{flex:none;width:38px;height:38px;border:0;border-radius:12px;background:var(--hc-ocre);color:var(--hc-fondo);cursor:pointer;display:grid;place-items:center}',
    '.hbtc-enviar:disabled{opacity:.4;cursor:default}',
    '.hbtc-pie{display:flex;justify-content:space-between;gap:10px;padding:8px 16px 14px;font:400 10.5px/1.45 "JetBrains Mono",ui-monospace,monospace;color:var(--hc-tenue)}',
    '.hbtc-pie span:last-child{flex:none}',
    '.hbtc-pie [data-lleno="true"]{color:var(--hc-ocre)}',
    '@media (max-width:520px){.hbtc-boton{width:56px;height:56px;padding:0;justify-content:center}.hbtc-boton .hbtc-texto{display:none}.hbtc-boton .hbtc-punto{display:none}.hbtc-boton .hbtc-icono{display:block;color:var(--hc-ocre)}.hbtc-panel{right:0;bottom:0;width:100vw;height:min(88vh,100dvh);border-radius:20px 20px 0 0;border-bottom:0}.hbtc-boton[data-oculto="true"]{display:none}}',
    '@media (prefers-reduced-motion:reduce){.hbtc-panel,.hbtc-boton{transition:none}.hbtc-punto{animation:none}}',
  ].join('\n');

  var estilo = document.createElement('style');
  estilo.textContent = css;
  document.head.appendChild(estilo);

  // ---------------------------------------------------------------- estructura
  var volcan =
    '<svg class="hbtc-sello" viewBox="0 0 100 100" aria-hidden="true"><rect x="0" y="68" width="16" height="32" rx="4.5" fill="currentColor"/><rect x="21" y="38" width="16" height="62" rx="4.5" fill="currentColor"/><rect x="42" y="0" width="16" height="100" rx="4.5" fill="#F0A840"/><rect x="63" y="20" width="16" height="80" rx="4.5" fill="currentColor"/><rect x="84" y="54" width="16" height="46" rx="4.5" fill="currentColor"/></svg>';

  var raiz = document.createElement('div');
  raiz.className = 'hbtc';
  raiz.innerHTML =
    '<button class="hbtc-boton" type="button" aria-haspopup="dialog" aria-expanded="false"><span class="hbtc-punto" aria-hidden="true"></span><svg class="hbtc-icono" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.9A8 8 0 1 1 21 12z"/></svg><span class="hbtc-texto"></span></button>' +
    '<div class="hbtc-panel" role="dialog" aria-modal="false" aria-labelledby="hbtc-titulo" data-abierto="false" hidden>' +
    '<div class="hbtc-cabeza">' + volcan + '<div><strong id="hbtc-titulo"></strong><small></small></div><button class="hbtc-cerrar" type="button">&times;</button></div>' +
    '<div class="hbtc-lista" aria-live="polite"></div>' +
    '<div class="hbtc-sugerencias"></div>' +
    '<form class="hbtc-form"><textarea rows="1" maxlength="' + MAX + '" required></textarea>' +
    '<button class="hbtc-enviar" type="submit"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg></button></form>' +
    '<p class="hbtc-pie"><span></span><span>0/' + MAX + '</span></p>' +
    '</div>';
  document.body.appendChild(raiz);

  var boton = raiz.querySelector('.hbtc-boton');
  var panel = raiz.querySelector('.hbtc-panel');
  var lista = raiz.querySelector('.hbtc-lista');
  var sugerencias = raiz.querySelector('.hbtc-sugerencias');
  var form = raiz.querySelector('.hbtc-form');
  var caja = form.querySelector('textarea');
  var enviar = form.querySelector('.hbtc-enviar');
  var contador = raiz.querySelector('.hbtc-pie span:last-child');

  boton.lastChild.textContent = T.abrir;
  boton.setAttribute('aria-label', T.abrir);
  raiz.querySelector('#hbtc-titulo').textContent = T.titulo;
  raiz.querySelector('.hbtc-cabeza small').textContent = T.subtitulo;
  raiz.querySelector('.hbtc-cerrar').setAttribute('aria-label', T.cerrar);
  raiz.querySelector('.hbtc-pie span').textContent = T.aviso;
  caja.placeholder = T.placeholder;
  caja.setAttribute('aria-label', T.placeholder);
  enviar.setAttribute('aria-label', T.enviar);

  T.sugerencias.forEach(function (s) {
    var b = document.createElement('button');
    b.type = 'button';
    b.textContent = s;
    b.addEventListener('click', function () { preguntar(s); });
    sugerencias.appendChild(b);
  });

  pintar('asistente', T.bienvenida);

  // ---------------------------------------------------------------- abrir / cerrar
  function abrir() {
    panel.hidden = false;
    requestAnimationFrame(function () { panel.dataset.abierto = 'true'; });
    boton.setAttribute('aria-expanded', 'true');
    boton.dataset.oculto = 'true';
    setTimeout(function () { caja.focus(); }, 60);
  }
  function cerrar() {
    panel.dataset.abierto = 'false';
    boton.setAttribute('aria-expanded', 'false');
    boton.dataset.oculto = 'false';
    setTimeout(function () { if (panel.dataset.abierto === 'false') panel.hidden = true; }, 220);
    boton.focus();
  }
  boton.addEventListener('click', function () { panel.dataset.abierto === 'true' ? cerrar() : abrir(); });
  raiz.querySelector('.hbtc-cerrar').addEventListener('click', cerrar);
  panel.addEventListener('keydown', function (e) { if (e.key === 'Escape') cerrar(); });

  // ---------------------------------------------------------------- escribir
  caja.addEventListener('input', function () {
    caja.style.height = 'auto';
    caja.style.height = Math.min(caja.scrollHeight, 110) + 'px';
    contador.textContent = caja.value.length + '/' + MAX;
    contador.dataset.lleno = String(caja.value.length >= MAX);
  });
  caja.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event('submit', { cancelable: true }));
    }
  });
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    preguntar(caja.value);
  });

  // ---------------------------------------------------------------- preguntar
  function preguntar(texto) {
    texto = String(texto || '').trim().slice(0, MAX);
    if (!texto || ocupado) return;
    ocupado = true;
    enviar.disabled = true;
    sugerencias.hidden = true;
    caja.value = '';
    caja.dispatchEvent(new Event('input'));

    pintar('usuario', texto);
    var espera = pintar('asistente', T.pensando);
    espera.classList.add('hbtc-pensando');

    fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pregunta: texto, historial: historial.slice(-4), idioma: idioma }),
    })
      .then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function (d) {
        espera.remove();
        var respuesta = d && d.respuesta ? d.respuesta : T.error;
        pintar('asistente', respuesta, d && d.fuentes);
        // Solo las respuestas de verdad entran en el historial que se reenvía.
        if (d && d.tipo === 'ok') {
          historial.push({ rol: 'usuario', texto: texto }, { rol: 'asistente', texto: respuesta });
        }
      })
      .catch(function () {
        espera.remove();
        pintar('asistente', T.error);
      })
      .then(function () {
        ocupado = false;
        enviar.disabled = false;
        if (!panel.hidden) caja.focus();
      });
  }

  // ---------------------------------------------------------------- pintar mensajes
  function pintar(rol, texto, fuentes) {
    var el = document.createElement('div');
    el.className = 'hbtc-msj ' + (rol === 'usuario' ? 'hbtc-yo' : 'hbtc-ia');
    var etiqueta = document.createElement('small');
    etiqueta.textContent = rol === 'usuario' ? T.tu : T.ia;
    var p = document.createElement('p');
    p.textContent = texto; // siempre como texto: nada de HTML de la respuesta
    el.appendChild(etiqueta);
    el.appendChild(p);

    var validas = (fuentes || []).filter(function (f) { return f && /^https:\/\/hbtdata\.es\//.test(f.url); });
    if (validas.length) {
      var pie = document.createElement('div');
      pie.className = 'hbtc-fuentes';
      pie.appendChild(document.createTextNode(T.fuentes + ':'));
      validas.forEach(function (f) {
        var a = document.createElement('a');
        a.href = f.url.replace(/^https:\/\/hbtdata\.es/, location.hostname === 'hbtdata.es' ? '' : 'https://hbtdata.es');
        a.textContent = (f.titulo || f.url).split(' · ').pop().replace(/\.$/, '');
        pie.appendChild(a);
      });
      el.appendChild(pie);
    }

    lista.appendChild(el);
    lista.scrollTop = lista.scrollHeight;
    return el;
  }
})();
