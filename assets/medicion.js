/* Medición de hbtdata.es con GoatCounter. Sin cookies ni banner.
   Cuenta visitas y unos pocos eventos; nunca lo que alguien escribe en un formulario.

   Configuración: poner en CODIGO el código de la cuenta de goatcounter.com (el de CODIGO.goatcounter.com).
   Con CODIGO vacío no se carga nada. Solo cuenta en hbtdata.es (no en local ni en vistas previas).
   Para no contar tus propias visitas: abrir https://hbtdata.es/#toggle-goatcounter en cada navegador.

   GoatCounter guarda cada evento como un nombre, sin datos aparte, así que el detalle va en el nombre.
   El título del evento es la página donde pasó.
     contacto/<opción elegida>               envío del formulario
     webs-modo/<mano|ia>                     interruptor de /webs/
     webs-proceso/<proceso>                  pestaña del ejemplo de /webs/
     copiar/<prompt|enlace>/<recurso>        botones de /recursos/
     filtro/<campo>/<valor>                  filtros de /recursos/
     juego-empieza/<juego>                   botón de empezar
     juego-fin/<juego>/<resultado>           pantalla final (lo envían test.js y donde.js)
     salida/<web o correo>                   enlace a otra web
     descarga/<archivo>                      PDF
     profundidad/<página>/<25|50|75|100>     cuánto se baja */
(function () {
  'use strict';

  var CODIGO = '';            // p. ej. 'hbtdata' → https://hbtdata.goatcounter.com
  var DOMINIO = 'hbtdata.es';

  function trozo(v) {
    return String(v == null ? '' : v).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9%.]+/g, '-').replace(/^-+|-+$/g, '') || 'sin-especificar';
  }
  var pagina = location.pathname;
  var paginaCorta = trozo(pagina.replace(/^\/|\/$/g, '').replace(/\//g, '-')).replace(/^sin-especificar$/, 'portada');

  var cola = [];
  function cuenta(partes) {
    var nombre = partes.map(trozo).join('/');
    var gc = window.goatcounter;
    if (gc && typeof gc.count === 'function') {
      try { gc.count({ path: nombre, title: pagina, event: true }); } catch (e) { /* la medición nunca rompe la web */ }
    } else if (cola.length < 50) {
      cola.push(partes);
    }
  }
  // Mismo nombre que antes para que los juegos no cambien: hbtMedir('juego_fin', { juego, resultado })
  window.hbtMedir = function (nombre, datos) {
    var p = [String(nombre).replace(/_/g, '-')];
    if (datos) Object.keys(datos).forEach(function (k) { p.push(datos[k]); });
    cuenta(p);
  };

  if (!CODIGO || location.hostname !== DOMINIO) return;

  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://gc.zgo.at/count.js';
  s.setAttribute('data-goatcounter', 'https://' + CODIGO + '.goatcounter.com/count');
  s.onload = function () { cola.splice(0).forEach(cuenta); };
  document.head.appendChild(s);

  function attr(el, nombre) { return (el && el.getAttribute(nombre)) || ''; }

  // ---------- clics ----------
  document.addEventListener('click', function (ev) {
    if (!ev.isTrusted) return;                      // solo clics de verdad, no los que hace la propia página
    var t = ev.target;
    if (!t || !t.closest) return;

    var b = t.closest('.interruptor button[data-modo]');
    if (b) return cuenta(['webs-modo', attr(b, 'data-modo')]);

    b = t.closest('button[data-proceso]');
    if (b) return cuenta(['webs-proceso', attr(b, 'data-proceso')]);

    b = t.closest('[data-copiar]');
    if (b) return cuenta(['copiar', attr(b, 'data-copiar') === 'enlace' ? 'enlace' : 'prompt', paginaCorta.replace(/^recursos-/, '')]);

    b = t.closest('.filtros .chip[data-campo]');
    if (b) return cuenta(['filtro', attr(b, 'data-campo'), attr(b, 'data-valor')]);

    b = t.closest('[data-accion=empezar]');
    if (b) return cuenta(['juego-empieza', pagina.split('/').filter(Boolean).pop() || 'juegos']);

    var a = t.closest('a[href]');
    if (!a) return;
    var href = attr(a, 'href');
    if (/^mailto:/i.test(href)) return cuenta(['salida', 'correo']);
    var url;
    try { url = new URL(href, location.href); } catch (e) { return; }
    if (/\.pdf$/i.test(url.pathname)) return cuenta(['descarga', url.pathname.split('/').pop().replace(/\.pdf$/i, '')]);
    if (/^https?:$/.test(url.protocol) && url.hostname !== location.hostname) {
      cuenta(['salida', url.hostname.replace(/^www\./, '')]);
    }
  }, true);

  // ---------- formulario de contacto: solo la opción elegida, nada de lo escrito ----------
  document.addEventListener('submit', function (ev) {
    var f = ev.target;
    if (!f || !f.classList || !f.classList.contains('formulario') || !f.checkValidity()) return;
    var marcada = f.querySelector('input[name=necesito]:checked');
    cuenta(['contacto', marcada ? marcada.value : 'sin-especificar']);
  }, true);

  // ---------- profundidad de lectura ----------
  var marcas = [25, 50, 75, 100], hechas = {}, pendiente = false;
  function mide() {
    pendiente = false;
    var alto = document.documentElement.scrollHeight - window.innerHeight;
    var pct = alto > 0 ? (window.scrollY / alto) * 100 : 100;
    marcas.forEach(function (m) {
      if (!hechas[m] && pct >= m - 2) { hechas[m] = true; cuenta(['profundidad', paginaCorta, m]); }
    });
  }
  window.addEventListener('scroll', function () {
    if (!pendiente) { pendiente = true; window.requestAnimationFrame(mide); }
  }, { passive: true });
})();
