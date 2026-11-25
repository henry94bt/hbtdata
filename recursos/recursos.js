/* hbtdata.es/recursos/ · copiar, filtros y partículas. Sin librerías ni cookies. */
(function () {
  'use strict';
  document.documentElement.classList.remove('sin-js');
  var reducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---------- la barra gana fondo al bajar ----------
  var barra = document.querySelector('.barra');
  if (barra) {
    var fondo = function () { barra.classList.toggle('con-fondo', window.scrollY > 40); };
    window.addEventListener('scroll', fondo, { passive: true }); fondo();
  }

  // ---------- copiar ----------
  var aviso = document.querySelector('.estado-copia');
  function copiaTexto(texto) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(texto);
    return new Promise(function (ok, mal) {          // respaldo para http o navegadores viejos
      var t = document.createElement('textarea');
      t.value = texto; t.setAttribute('readonly', ''); t.style.position = 'fixed'; t.style.opacity = '0';
      document.body.appendChild(t); t.select();
      try { document.execCommand('copy') ? ok() : mal(); } catch (e) { mal(e); }
      document.body.removeChild(t);
    });
  }
  [].forEach.call(document.querySelectorAll('[data-copiar]'), function (b) {
    var etiqueta = b.querySelector('span'), original = etiqueta.textContent;
    b.addEventListener('click', function () {
      var fuente = b.getAttribute('data-copiar');
      var texto = fuente === 'enlace' ? location.href.split('#')[0].split('?')[0] : document.getElementById(fuente).textContent;
      copiaTexto(texto).then(function () {
        b.classList.add('hecho'); etiqueta.textContent = 'Copiado';
        if (aviso) aviso.textContent = fuente === 'enlace' ? 'Enlace copiado' : 'Prompt copiado';
        setTimeout(function () { b.classList.remove('hecho'); etiqueta.textContent = original; }, 2200);
      }, function () {
        etiqueta.textContent = 'Selecciónalo a mano';
        if (fuente !== 'enlace') {
          var r = document.createRange(); r.selectNodeContents(document.getElementById(fuente));
          var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
        }
      });
    });
  });

  // ---------- filtros de la portada (?tipo=prompt&tema=limpieza se puede enlazar) ----------
  var rejilla = document.querySelector('.rejilla');
  if (rejilla) {
    var tarjetas = [].slice.call(rejilla.children), vacio = document.querySelector('.vacio');
    var chips = [].slice.call(document.querySelectorAll('.filtros .chip'));
    var q = new URLSearchParams(location.search);
    var filtro = { tipo: q.get('tipo') || 'todo', tema: q.get('tema') || 'todo' };
    var aplica = function (enUrl) {
      var n = 0;
      tarjetas.forEach(function (t) {
        var ve = (filtro.tipo === 'todo' || t.dataset.tipo === filtro.tipo) && (filtro.tema === 'todo' || t.dataset.tema === filtro.tema);
        t.hidden = !ve; if (ve) n++;
      });
      vacio.hidden = n > 0;
      chips.forEach(function (c) { c.setAttribute('aria-pressed', filtro[c.dataset.campo] === c.dataset.valor ? 'true' : 'false'); });
      if (enUrl) {
        var p = new URLSearchParams();
        if (filtro.tipo !== 'todo') p.set('tipo', filtro.tipo);
        if (filtro.tema !== 'todo') p.set('tema', filtro.tema);
        history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p : '') + location.hash);
      }
    };
    chips.forEach(function (c) {
      c.addEventListener('click', function () { filtro[c.dataset.campo] = c.dataset.valor; aplica(true); });
    });
    aplica(false);
  }

  // ---------- partículas de la portada: un documento, un prompt y una descarga ----------
  var canvas = document.getElementById('campo');
  if (!canvas) return;
  var movil = window.matchMedia('(max-width: 900px)').matches, campo = null;
  try { campo = window.CampoParticulas && window.CampoParticulas({ canvas: canvas, particulas: movil ? 12000 : 22000, tam: movil ? 3.2 : 3.6, alfa: movil ? 0.5 : 0.42 }); } catch (e) { campo = null; }
  if (!campo) { document.documentElement.classList.add('sin-webgl'); return; }

  var raton = [9, 9], prev = null, fuerza = 0, objetivo = 0, giro = [0, 0], visible = true;
  canvas.parentNode.addEventListener('pointermove', function (e) {
    var r = canvas.getBoundingClientRect();
    var x = (e.clientX - r.left) / r.width * 2 - 1, y = -((e.clientY - r.top) / r.height * 2 - 1);
    if (prev) objetivo = Math.min(1, objetivo + Math.hypot(x - prev[0], y - prev[1]) * 5);
    prev = [x, y]; raton = [x, y];
  });
  canvas.parentNode.addEventListener('pointerleave', function () { prev = null; });
  new IntersectionObserver(function (es) { visible = es[0].isIntersecting; }).observe(canvas);
  window.addEventListener('resize', function () { campo.mide(); });

  var inicio = performance.now(), ultimo = inicio;
  function cuadro(ahora) {
    var dt = Math.min(0.05, (ahora - ultimo) / 1000); ultimo = ahora;
    if (visible) {
      var t = (ahora - inicio) / 1000, intro = reducido ? 1 : Math.min(1, t / 2.4);
      fuerza += (objetivo - fuerza) * Math.min(1, dt * 6); objetivo *= Math.pow(0.08, dt);
      var g = reducido ? [0, 0] : [Math.sin(t * 0.25) * 0.2 - 0.1 + (raton[0] < 5 ? raton[0] * 0.12 : 0), raton[1] < 5 ? raton[1] * 0.08 : 0];
      giro[0] += (g[0] - giro[0]) * Math.min(1, dt * 2); giro[1] += (g[1] - giro[1]) * Math.min(1, dt * 2);
      var asp = canvas.clientWidth / Math.max(1, canvas.clientHeight);
      campo.pinta({
        de: 'esfera', a: 'recursos', mezcla: 1 - Math.pow(1 - intro, 3), explosion: reducido ? 0 : 0.5,
        t: t, giro: giro, escala: Math.min(1.15, asp / 1.0), desplaza: [0, 0],
        raton: raton, fuerza: reducido ? 0 : fuerza, movimiento: reducido ? 0 : 1
      });
    }
    requestAnimationFrame(cuadro);
  }
  campo.precarga(['esfera', 'recursos']);
  requestAnimationFrame(cuadro);
})();
