/* Motor del test de hbtdata.es/juegos/test/.
   Lee las preguntas de un JSON (data-preguntas) y no sabe nada de Canarias: para otro quiz
   (por ejemplo, el de Historia para Gandules) basta con otro JSON con el mismo formato.

   Formato del JSON:
   { "titulo", "url", "partida": 10, "niveles": [{ "desde", "titulo", "texto" }],
     "preguntas": [ { "id", "tipo", "enunciado", "fuente": {nombre, url, fecha} | [ … ], "dato", … } ] }
   Tipos:
     opciones  "opciones": [texto…], "correcta": texto
     isla      igual que opciones; si hay data-islas (GeoJSON con properties.isla) se dibuja un mapa pinchable
     masmenos  "a": {nombre, valor, texto}, "b": {…}, "correcta": "mas" | "menos"  (¿A tiene más o menos que B?)
     ordena    "elementos": [{nombre, valor, texto}…], "orden": "desc" | "asc"  (barras desde cero solo con "desc")
*/
(function () {
  'use strict';
  var J = window.Juegos;
  var raiz = document.getElementById('test');
  if (!raiz || !J) return;

  var $ = function (s, n) { return (n || raiz).querySelector(s); };
  var P = {
    inicio: $('[data-pantalla=inicio]'), pregunta: $('[data-pantalla=pregunta]'), final: $('[data-pantalla=final]')
  };
  var el = {
    progreso: $('.progreso'), tipo: $('[data-tipo]'), contador: $('[data-contador]'), enunciado: $('[data-enunciado]'),
    zona: $('[data-zona]'), respuesta: $('.respuesta'), titRes: $('.respuesta h3'), dato: $('.respuesta p'), fuente: $('.respuesta .fuente'),
    comprobar: $('[data-accion=comprobar]'), siguiente: $('[data-accion=siguiente]'), empezar: $('[data-accion=empezar]'),
    otra: $('[data-accion=otra]'), marcador: $('[data-marcador]'), nivel: $('[data-nivel]'), textoNivel: $('[data-texto-nivel]'),
    repaso: $('[data-repaso]'), compartir: $('.compartir')
  };
  var ETIQUETA = { opciones: '//curiosidad', isla: '//¿qué isla?', masmenos: '//¿más o menos?', ordena: '//ordena' };
  var BIEN = ['¡Eso es!', 'Bien visto.', 'Correcto.', 'Exacto.'];
  var MAL = ['Pues no.', 'Casi.', 'Esta no era.', 'Uy, no.'];
  var reducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var datos = null, islas = null, partida = [], k = 0, aciertos = [], estado = null;

  // ---------- carga ----------
  fetch(raiz.dataset.preguntas).then(function (r) { return r.json(); }).then(function (d) {
    datos = d; el.empezar.disabled = false;
  }).catch(function () {
    el.empezar.textContent = 'No se pudieron cargar las preguntas';
  });
  if (raiz.dataset.islas) {
    fetch(raiz.dataset.islas).then(function (r) { return r.json(); }).then(function (g) { islas = g; }).catch(function () { islas = null; });
  }

  // Elige N preguntas repartiendo los tipos y las baraja.
  function eligePartida() {
    var porTipo = {};
    datos.preguntas.forEach(function (q) { (porTipo[q.tipo] = porTipo[q.tipo] || []).push(q); });
    var montones = J.baraja(Object.keys(porTipo)).map(function (t) { return J.baraja(porTipo[t]); });
    var n = Math.min(datos.partida || 10, datos.preguntas.length), out = [];
    while (out.length < n) montones.forEach(function (m) { if (out.length < n && m.length) out.push(m.pop()); });
    return J.baraja(out);
  }

  function muestra(nombre) {
    Object.keys(P).forEach(function (p) { P[p].hidden = p !== nombre; });
    window.scrollTo({ top: 0, behavior: reducido ? 'auto' : 'smooth' });
  }

  function empieza() {
    partida = eligePartida(); k = 0; aciertos = [];
    el.progreso.innerHTML = partida.map(function () { return '<i></i>'; }).join('');
    muestra('pregunta');
    pregunta();
  }

  // ---------- una pregunta ----------
  function pregunta() {
    var q = partida[k];
    estado = { q: q, respondida: false, orden: [] };
    [].forEach.call(el.progreso.children, function (i, n) { i.className = n < k ? (aciertos[n] ? 'bien' : 'mal') : (n === k ? 'ahora' : ''); });
    el.contador.textContent = (k + 1) + ' de ' + partida.length;
    el.tipo.textContent = ETIQUETA[q.tipo] || '//pregunta';
    el.enunciado.textContent = q.enunciado;
    el.respuesta.hidden = true;
    el.siguiente.hidden = true;
    el.comprobar.hidden = q.tipo !== 'ordena';
    el.comprobar.disabled = true;
    el.zona.innerHTML = '';
    el.zona.className = 'zona zona-' + q.tipo;
    ({ opciones: pintaOpciones, isla: pintaIsla, masmenos: pintaMasMenos, ordena: pintaOrdena })[q.tipo](q);
    el.enunciado.focus({ preventScroll: true });
  }

  function boton(texto, clase) {
    var b = document.createElement('button');
    b.type = 'button'; b.className = clase || 'opcion';
    b.innerHTML = '<span></span><span class="marca"></span>';
    b.firstChild.textContent = texto;
    return b;
  }

  function pintaOpciones(q) {
    var lista = document.createElement('div'); lista.className = 'lista';
    J.baraja(q.opciones).forEach(function (o) {
      var b = boton(o); b.dataset.valor = o;
      b.addEventListener('click', function () { responde(o === q.correcta, b, q.correcta); });
      lista.appendChild(b);
    });
    el.zona.appendChild(lista);
  }

  function pintaIsla(q) {
    if (islas) el.zona.appendChild(mapaIslas(q));
    var lista = document.createElement('div'); lista.className = 'lista islas';
    q.opciones.forEach(function (o) {
      var b = boton(o); b.dataset.valor = o;
      b.addEventListener('click', function () { responde(o === q.correcta, b, q.correcta); });
      lista.appendChild(b);
    });
    el.zona.appendChild(lista);
  }

  // Mapa SVG de las islas, pinchable. Proyección equirectangular corregida por la latitud.
  function mapaIslas(q) {
    var feats = islas.features.filter(function (f) { return q.opciones.indexOf(f.properties.isla) >= 0; });
    var x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9, cos = Math.cos(28.3 * Math.PI / 180);
    var P2 = function (c) { return [c[0] * cos, -c[1]]; };
    feats.forEach(function (f) { f.geometry.coordinates.forEach(function (pol) { pol[0].forEach(function (c) { var p = P2(c); x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }); }); });
    var W = 1000, esc = W / (x1 - x0), H = Math.round((y1 - y0) * esc), pad = 14;
    var svg = '<svg viewBox="' + (-pad) + ' ' + (-pad) + ' ' + (W + 2 * pad) + ' ' + (H + 2 * pad) + '" role="group" aria-label="Mapa de las islas">';
    feats.forEach(function (f) {
      var d = f.geometry.coordinates.map(function (pol) {
        return pol.map(function (anillo) {
          return 'M' + anillo.map(function (c) { var p = P2(c); return ((p[0] - x0) * esc).toFixed(1) + ',' + ((p[1] - y0) * esc).toFixed(1); }).join('L') + 'Z';
        }).join('');
      }).join('');
      svg += '<path class="isla" data-valor="' + f.properties.isla + '" d="' + d + '"><title>' + f.properties.isla + '</title></path>';
    });
    svg += '</svg>';
    var caja = document.createElement('div'); caja.className = 'mapa-islas'; caja.innerHTML = svg;
    caja.addEventListener('click', function (e) {
      var p = e.target.closest('path.isla');
      if (!p || estado.respondida) return;
      var b = el.zona.querySelector('.opcion[data-valor="' + p.dataset.valor + '"]');
      if (b) b.click();
    });
    caja.setAttribute('aria-hidden', 'true');             // los botones de debajo hacen lo mismo y se leen mejor
    return caja;
  }

  function pintaMasMenos(q) {
    var caja = document.createElement('div'); caja.className = 'duelo';
    caja.innerHTML = '<div class="carta a"><span class="mono">¿Cuánto?</span><strong></strong><em>?</em></div>' +
      '<div class="frente mono">frente a</div>' +
      '<div class="carta b"><span class="mono">Dato</span><strong></strong><em></em></div>';
    $('.a strong', caja).textContent = q.a.nombre;
    $('.b strong', caja).textContent = q.b.nombre;
    $('.b em', caja).textContent = q.b.texto;
    var botones = document.createElement('div'); botones.className = 'masmenos';
    [['mas', 'Más'], ['menos', 'Menos']].forEach(function (o) {
      var b = boton(o[1]); b.dataset.valor = o[0];
      b.addEventListener('click', function () { responde(o[0] === q.correcta, b, q.correcta); });
      botones.appendChild(b);
    });
    el.zona.appendChild(caja); el.zona.appendChild(botones);
  }

  function pintaOrdena(q) {
    var lista = document.createElement('div'); lista.className = 'lista ordena';
    var ayuda = document.createElement('p'); ayuda.className = 'ayuda';
    ayuda.textContent = q.orden === 'asc' ? 'Toca en orden, del primero al último. Vuelve a tocar para quitar.' : 'Toca en orden, del mayor al menor. Vuelve a tocar para quitar.';
    J.baraja(q.elementos).forEach(function (e) {
      var b = boton(e.nombre, 'opcion paso'); b.dataset.valor = e.nombre;
      b.setAttribute('aria-pressed', 'false');
      b.addEventListener('click', function () {
        if (estado.respondida) return;
        var i = estado.orden.indexOf(e.nombre);
        if (i >= 0) estado.orden.splice(i, 1); else estado.orden.push(e.nombre);
        numera();
      });
      lista.appendChild(b);
    });
    function numera() {
      [].forEach.call(lista.children, function (b) {
        var i = estado.orden.indexOf(b.dataset.valor);
        b.querySelector('.marca').textContent = i >= 0 ? String(i + 1) : '';
        b.classList.toggle('puesto', i >= 0);
        b.setAttribute('aria-pressed', i >= 0 ? 'true' : 'false');
      });
      el.comprobar.disabled = estado.orden.length !== q.elementos.length;
    }
    el.zona.appendChild(ayuda); el.zona.appendChild(lista);
  }

  el.comprobar.addEventListener('click', function () {
    var q = estado.q;
    var bien = q.elementos.slice().sort(function (a, b) { return q.orden === 'asc' ? a.valor - b.valor : b.valor - a.valor; });
    var ok = bien.every(function (e, i) { return estado.orden[i] === e.nombre; });
    responde(ok, null, null, bien);
  });

  // ---------- corregir ----------
  function responde(ok, elegido, correcta, ordenBueno) {
    if (estado.respondida) return;
    estado.respondida = true;
    var q = estado.q;
    aciertos[k] = ok;
    [].forEach.call(el.zona.querySelectorAll('.opcion'), function (b) {
      b.disabled = true;
      if (correcta != null && b.dataset.valor === correcta) { b.classList.add('correcta'); b.querySelector('.marca').textContent = 'Correcta'; }
    });
    if (elegido) { elegido.classList.add('elegida'); if (!ok) { elegido.classList.add('fallo'); elegido.querySelector('.marca').textContent = 'Tu respuesta'; } }
    [].forEach.call(el.zona.querySelectorAll('path.isla'), function (p) {
      if (p.dataset.valor === correcta) p.classList.add('correcta');
      else if (elegido && p.dataset.valor === elegido.dataset.valor) p.classList.add('fallo');
    });

    if (q.tipo === 'masmenos') revelaDuelo(q);
    if (q.tipo === 'ordena') revelaOrden(q, ordenBueno);

    el.titRes.textContent = (ok ? BIEN : MAL)[Math.floor(Math.random() * 4)];
    var dato = q.dato || '';
    if (!ok && q.tipo !== 'ordena' && q.tipo !== 'masmenos') dato = 'Era «' + correcta + '». ' + dato;
    if (!ok && q.tipo === 'masmenos') dato = 'Era «' + (q.correcta === 'mas' ? 'más' : 'menos') + '». ' + dato;
    el.dato.textContent = dato;
    el.dato.hidden = !dato;
    J.pintaFuente(el.fuente, q.fuente);
    el.respuesta.classList.toggle('bien', ok);
    el.respuesta.hidden = false;
    el.comprobar.hidden = true;
    el.siguiente.hidden = false;
    el.siguiente.textContent = k === partida.length - 1 ? 'Ver resultado' : 'Siguiente';
    el.progreso.children[k].className = ok ? 'bien' : 'mal';
    el.siguiente.focus({ preventScroll: true });
    if (!reducido) el.respuesta.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  function barras(elementos) {
    var max = Math.max.apply(null, elementos.map(function (e) { return e.valor; }));
    var caja = document.createElement('div'); caja.className = 'barras';
    elementos.forEach(function (e) {
      var fila = document.createElement('div'); fila.className = 'fila';
      fila.innerHTML = '<span class="nombre"></span><span class="pista"><i></i></span><span class="valor"></span>';
      fila.querySelector('.nombre').textContent = e.nombre;
      fila.querySelector('.valor').textContent = e.texto;
      fila.querySelector('i').style.width = (e.valor / max * 100).toFixed(1) + '%';   // barras desde cero
      caja.appendChild(fila);
    });
    return caja;
  }

  function revelaDuelo(q) {
    $('.a em', el.zona).textContent = q.a.texto;
    el.zona.appendChild(barras([q.a, q.b]));
  }

  function revelaOrden(q, bien) {
    var lista = el.zona.querySelector('.ordena');
    [].forEach.call(lista.children, function (b) {
      var mio = estado.orden.indexOf(b.dataset.valor), real = bien.findIndex(function (e) { return e.nombre === b.dataset.valor; });
      b.classList.remove('puesto');
      b.classList.add(mio === real ? 'correcta' : 'fallo', 'elegida');
      b.querySelector('.marca').textContent = mio === real ? (real + 1) + ' ✓' : (mio + 1) + ' → ' + (real + 1);
    });
    var titulo = document.createElement('p'); titulo.className = 'mono solucion'; titulo.textContent = 'El orden bueno';
    el.zona.appendChild(titulo);
    if (q.orden !== 'asc') el.zona.appendChild(barras(bien));
    else {
      var ol = document.createElement('ol'); ol.className = 'orden-bueno';
      bien.forEach(function (e) { var li = document.createElement('li'); li.innerHTML = '<span></span><span class="valor"></span>'; li.firstChild.textContent = e.nombre; li.lastChild.textContent = e.texto; ol.appendChild(li); });
      el.zona.appendChild(ol);
    }
  }

  el.siguiente.addEventListener('click', function () {
    k++;
    if (k < partida.length) pregunta(); else final();
  });

  // ---------- resultado ----------
  function final() {
    var n = aciertos.filter(Boolean).length, total = partida.length;
    var niveles = (datos.niveles || []).slice().sort(function (a, b) { return a.desde - b.desde; });
    var nivel = niveles.filter(function (v) { return n >= v.desde; }).pop() || { titulo: '', texto: '' };
    el.marcador.innerHTML = '<b></b><span></span>';
    el.marcador.firstChild.textContent = n; el.marcador.lastChild.textContent = '/' + total;
    el.nivel.textContent = nivel.titulo;
    el.textoNivel.textContent = nivel.texto;
    el.repaso.innerHTML = '';
    partida.forEach(function (q, i) {
      var li = document.createElement('li'); li.className = aciertos[i] ? 'bien' : 'mal';
      li.innerHTML = '<span class="marca"></span><span></span>';
      li.firstChild.textContent = aciertos[i] ? 'Bien' : 'Fallo';
      li.lastChild.textContent = q.enunciado;
      el.repaso.appendChild(li);
    });
    muestra('final');
    var casillas = aciertos.map(Boolean);
    var texto = datos.titulo + ': ' + n + '/' + total + ' · ' + nivel.titulo + '\n' + casillas.map(function (c) { return c ? '🟧' : '⬛'; }).join('') + '\n¿Y tú cuánto sabes?';
    J.fuentesListas().then(function () {
      var cv = J.tarjeta({ juego: datos.titulo, marcador: String(n), de: '/' + total, nivel: nivel.titulo, casillas: casillas, url: datos.url, dibujo: islas ? dibujaIslas : null });
      J.compartir({ lienzo: cv, texto: texto, url: datos.url, archivo: 'test-de-canarias-' + n + '-de-' + total + '.png', nodo: el.compartir });
    });
    el.marcador.focus({ preventScroll: true });
  }

  // Silueta de las islas en la tarjeta.
  function dibujaIslas(ctx, caja) {
    var cos = Math.cos(28.3 * Math.PI / 180), x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    islas.features.forEach(function (f) { f.geometry.coordinates.forEach(function (pol) { pol[0].forEach(function (c) { x0 = Math.min(x0, c[0] * cos); x1 = Math.max(x1, c[0] * cos); y0 = Math.min(y0, -c[1]); y1 = Math.max(y1, -c[1]); }); }); });
    var esc = Math.min(caja.w / (x1 - x0), caja.h / (y1 - y0)), ox = caja.x, oy = caja.y + (caja.h - (y1 - y0) * esc) / 2;
    ctx.fillStyle = 'rgba(150,214,214,.22)'; ctx.strokeStyle = 'rgba(150,214,214,.7)'; ctx.lineWidth = 2;
    islas.features.forEach(function (f) {
      ctx.beginPath();
      f.geometry.coordinates.forEach(function (pol) { pol.forEach(function (an) { an.forEach(function (c, i) { var x = ox + (c[0] * cos - x0) * esc, y = oy + (-c[1] - y0) * esc; if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); }); ctx.closePath(); }); });
      ctx.fill('evenodd'); ctx.stroke();
    });
  }

  el.empezar.addEventListener('click', empieza);
  el.otra.addEventListener('click', empieza);
  J.cabecera();
})();
