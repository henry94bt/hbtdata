/* Medición de hbtdata.es con Umami instalado en un servidor propio. Sin cookies ni banner.
   Cuenta visitas y unos pocos eventos; nunca lo que alguien escribe en un formulario.

   Configuración: rellenar SERVIDOR y WEB_ID cuando el Umami esté en marcha.
   Con WEB_ID vacío no se carga nada. Solo cuenta en hbtdata.es (no en local ni en vistas previas).
   Para no contar tus propias visitas, en la consola del navegador: localStorage.setItem('umami.disabled', '1')

   Eventos:
     contacto        envío del formulario       { necesito, pagina }
     webs_modo       interruptor de /webs/      { modo: mano | ia }
     webs_proceso    pestaña del ejemplo        { proceso }
     copiar          botones de /recursos/      { que: prompt | enlace, recurso }
     filtro          filtros de /recursos/      { campo, valor }
     juego_empieza   botón de empezar           { juego }
     juego_fin       pantalla final             { juego, resultado }  (lo envían test.js y donde.js)
     salida          enlace a otra web o correo { destino, pagina }
     descarga        PDF                        { archivo }
     profundidad     cuánto se baja en la página { pct: 25 | 50 | 75 | 100 } */
(function () {
  'use strict';

  var SERVIDOR = '';          // p. ej. 'https://umami-hbtdata.vercel.app' (sin barra final)
  var SCRIPT = 'script.js';   // si en Vercel se pone TRACKER_SCRIPT_NAME, el mismo nombre aquí
  var WEB_ID = '';            // el «Website ID» que da Umami al dar de alta hbtdata.es
  var DOMINIO = 'hbtdata.es';

  var cola = [];
  function envia(nombre, datos) {
    if (window.umami && typeof window.umami.track === 'function') {
      try { window.umami.track(nombre, datos); } catch (e) { /* la medición nunca rompe la web */ }
    } else if (cola.length < 50) {
      cola.push([nombre, datos]);
    }
  }
  window.hbtMedir = envia;

  if (!SERVIDOR || !WEB_ID || location.hostname !== DOMINIO) return;

  var s = document.createElement('script');
  s.defer = true;
  s.src = SERVIDOR + '/' + SCRIPT;
  s.setAttribute('data-website-id', WEB_ID);
  s.setAttribute('data-domains', DOMINIO);
  s.onload = function () { cola.splice(0).forEach(function (e) { envia(e[0], e[1]); }); };
  document.head.appendChild(s);

  var pagina = location.pathname;
  function attr(el, nombre) { return (el && el.getAttribute(nombre)) || ''; }

  // ---------- clics ----------
  document.addEventListener('click', function (ev) {
    if (!ev.isTrusted) return;                      // solo clics de verdad, no los que hace la propia página
    var t = ev.target;
    if (!t || !t.closest) return;

    var b = t.closest('.interruptor button[data-modo]');
    if (b) return envia('webs_modo', { modo: attr(b, 'data-modo') });

    b = t.closest('button[data-proceso]');
    if (b) return envia('webs_proceso', { proceso: attr(b, 'data-proceso') });

    b = t.closest('[data-copiar]');
    if (b) return envia('copiar', { que: attr(b, 'data-copiar') === 'enlace' ? 'enlace' : 'prompt', recurso: pagina });

    b = t.closest('.filtros .chip[data-campo]');
    if (b) return envia('filtro', { campo: attr(b, 'data-campo'), valor: attr(b, 'data-valor') });

    b = t.closest('[data-accion=empezar]');
    if (b) return envia('juego_empieza', { juego: pagina.split('/').filter(Boolean).pop() || 'juegos' });

    var a = t.closest('a[href]');
    if (!a) return;
    var href = attr(a, 'href');
    if (/^mailto:/i.test(href)) return envia('salida', { destino: 'correo', pagina: pagina });
    var url;
    try { url = new URL(href, location.href); } catch (e) { return; }
    if (/\.pdf$/i.test(url.pathname)) return envia('descarga', { archivo: url.pathname.split('/').pop() });
    if (/^https?:$/.test(url.protocol) && url.hostname !== location.hostname) {
      envia('salida', { destino: url.hostname.replace(/^www\./, ''), pagina: pagina });
    }
  }, true);

  // ---------- formulario de contacto: solo la opción elegida, nada de lo escrito ----------
  document.addEventListener('submit', function (ev) {
    var f = ev.target;
    if (!f || !f.classList || !f.classList.contains('formulario') || !f.checkValidity()) return;
    var marcada = f.querySelector('input[name=necesito]:checked');
    envia('contacto', { necesito: marcada ? marcada.value : 'Sin especificar', pagina: pagina });
  }, true);

  // ---------- profundidad de lectura ----------
  var marcas = [25, 50, 75, 100], hechas = {}, pendiente = false;
  function mide() {
    pendiente = false;
    var alto = document.documentElement.scrollHeight - window.innerHeight;
    var pct = alto > 0 ? (window.scrollY / alto) * 100 : 100;
    marcas.forEach(function (m) {
      if (!hechas[m] && pct >= m - 2) { hechas[m] = true; envia('profundidad', { pct: m }); }
    });
  }
  window.addEventListener('scroll', function () {
    if (!pendiente) { pendiente = true; window.requestAnimationFrame(mide); }
  }, { passive: true });
})();
