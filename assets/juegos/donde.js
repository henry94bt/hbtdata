/* Motor de «¿Dónde está?» (hbtdata.es/juegos/donde-esta/).
   Mapa con Leaflet sin teselas: solo el contorno de las islas (GeoJSON propio), así no hay
   peticiones a terceros, ni cookies, ni nombres en el mapa que chiven la respuesta.

   Datos (data-sitios): { titulo, url, categorias: [{id, nombre}], filtros_isla: [{id, nombre, islas: []}],
                          sitios: [{ id, nombre, categoria, isla, municipio, lat, lng, fuente }] }
   Contorno (data-islas): GeoJSON con properties.isla.
   Puntuación: 1000 puntos si se pincha a menos de 0,5 km; después baja con la distancia
   (1000 · e^(−(d − 0,5) / 25)): a 10 km, unos 680; a 25 km, unos 370; a 75 km, unos 50. */
(function () {
  'use strict';
  var J = window.Juegos, L = window.L;
  var raiz = document.getElementById('donde');
  if (!raiz || !J || !L) return;

  var $ = function (s, n) { return (n || raiz).querySelector(s); };
  var P = { inicio: $('[data-pantalla=inicio]'), juego: $('[data-pantalla=juego]'), final: $('[data-pantalla=final]') };
  var el = {
    islas: $('[data-filtro=isla]'), cats: $('[data-filtro=categoria]'), largo: $('[data-filtro=largo]'), cuantos: $('[data-cuantos]'),
    empezar: $('[data-accion=empezar]'), contador: $('[data-contador]'), categoria: $('[data-categoria]'), nombre: $('[data-nombre]'),
    instruccion: $('[data-instruccion]'), confirmar: $('[data-accion=confirmar]'), centro: $('[data-accion=centro]'),
    siguiente: $('[data-accion=siguiente]'), resultado: $('[data-resultado]'), km: $('[data-km]'), puntos: $('[data-puntos]'),
    donde: $('[data-donde]'), fuente: $('[data-fuente]'), total: $('[data-total]'), nivel: $('[data-nivel]'),
    lista: $('[data-lista]'), otra: $('[data-accion=otra]'), compartir: $('.compartir'), progreso: $('.progreso'), marcador: $('[data-marcador-vivo]')
  };
  var reducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var movil = function () { return window.matchMedia('(max-width: 760px)').matches; };

  var datos = null, contorno = null, capaIslas = null, ronda = [], k = 0, jugadas = [], intento = null, capaRonda = L.layerGroup(), filtro = { isla: 'todas', categoria: 'todas', largo: 10 };

  // ---------- mapa ----------
  var mapa = L.map('mapa', { zoomSnap: 0.25, zoomDelta: 0.5, minZoom: 5.5, maxZoom: 14, attributionControl: true, zoomControl: false, keyboard: true });
  L.control.zoom({ position: 'bottomright', zoomInTitle: 'Acercar', zoomOutTitle: 'Alejar' }).addTo(mapa);
  mapa.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
  mapa.attributionControl.addAttribution('Islas: <a href="https://www.gobiernodecanarias.org/istac/">ISTAC</a> · Sitios: <a href="https://www.ign.es/">IGN</a>');
  mapa.setView([28.35, -15.9], 7.25);
  capaRonda.addTo(mapa);

  // Deja hueco para el panel (a la izquierda en escritorio, abajo en el móvil).
  function hueco() {
    var r = P[estadoPantalla()] && P[estadoPantalla()].getBoundingClientRect();
    if (!r) return { paddingTopLeft: [30, 30], paddingBottomRight: [30, 30] };
    return movil() ? { paddingTopLeft: [24, 24], paddingBottomRight: [24, Math.min(window.innerHeight * 0.6, r.height + 24)] }
                   : { paddingTopLeft: [r.right + 30, 30], paddingBottomRight: [60, 30] };
  }
  function estadoPantalla() { return Object.keys(P).filter(function (p) { return !P[p].hidden; })[0]; }

  function encuadra(limites, max) {
    var o = hueco(); o.maxZoom = max || 11; o.animate = !reducido;
    mapa.fitBounds(limites, o);
  }
  function limitesFiltro() {
    if (!capaIslas) return L.latLngBounds([27.6, -18.2], [29.45, -13.3]);
    var f = filtroIsla(), b = L.latLngBounds([]);
    capaIslas.eachLayer(function (l) { if (!f || f.islas.indexOf(l.feature.properties.isla) >= 0 || (f.islas.indexOf('La Graciosa') >= 0 && l.feature.properties.isla === 'Lanzarote')) b.extend(l.getBounds()); });
    return b.isValid() ? b : L.latLngBounds([27.6, -18.2], [29.45, -13.3]);
  }

  // ---------- carga ----------
  Promise.all([
    fetch(raiz.dataset.sitios).then(function (r) { return r.json(); }),
    fetch(raiz.dataset.islas).then(function (r) { return r.json(); })
  ]).then(function (res) {
    datos = res[0]; contorno = res[1];
    capaIslas = L.geoJSON(contorno, { interactive: false, style: { color: '#96D6D6', weight: 1.1, opacity: 0.6, fillColor: '#0A3440', fillOpacity: 1 } }).addTo(mapa);
    capaIslas.eachLayer(function (l) {                // nombre de cada isla, discreto
      L.marker(l.getBounds().getCenter(), { interactive: false, keyboard: false, icon: L.divIcon({ className: 'rotulo-isla', html: '<span>' + l.feature.properties.isla + '</span>', iconSize: null }) }).addTo(mapa);
    });
    mapa.setMaxBounds(L.latLngBounds([17, -29], [39, -3]));   // holgado: con el panel encima, el encuadre necesita margen
    pintaFiltros();
    encuadra(limitesFiltro(), 9);
  }).catch(function () {
    el.cuantos.textContent = 'No se pudieron cargar los datos del juego.';
  });

  function chip(nombre, grupo, valor, marcado) {
    var l = document.createElement('label'); l.className = 'chip';
    l.innerHTML = '<input type="radio"><span></span>';
    var i = l.firstChild; i.name = grupo; i.value = valor; i.checked = !!marcado;
    l.lastChild.textContent = nombre;
    return l;
  }
  function pintaFiltros() {
    el.islas.appendChild(chip('Todas', 'isla', 'todas', true));
    datos.filtros_isla.forEach(function (f) { el.islas.appendChild(chip(f.nombre, 'isla', f.id)); });
    el.cats.appendChild(chip('Todo', 'categoria', 'todas', true));
    datos.categorias.forEach(function (c) { el.cats.appendChild(chip(c.nombre, 'categoria', c.id)); });
    raiz.addEventListener('change', function (e) {
      if (e.target.name === 'isla') { filtro.isla = e.target.value; encuadra(limitesFiltro(), 10); }
      if (e.target.name === 'categoria') filtro.categoria = e.target.value;
      if (e.target.name === 'largo') filtro.largo = +e.target.value;
      cuenta();
    });
    cuenta();
  }
  function filtroIsla() { return datos.filtros_isla.filter(function (f) { return f.id === filtro.isla; })[0] || null; }
  function candidatos() {
    var f = filtroIsla();
    return datos.sitios.filter(function (s) {
      return (!f || f.islas.indexOf(s.isla) >= 0) && (filtro.categoria === 'todas' || s.categoria === filtro.categoria);
    });
  }
  function cuenta() {
    var n = candidatos().length, jugar = Math.min(n, filtro.largo);
    el.cuantos.textContent = n === 0 ? 'No hay sitios con esos filtros. Prueba con otros.'
      : (n < filtro.largo ? 'Con estos filtros hay ' + n + ' sitio' + (n > 1 ? 's' : '') + ': jugarás ' + jugar + '.' : 'Partida de ' + jugar + ' sitios, elegidos al azar entre ' + n + '.');
    el.empezar.disabled = n === 0;
  }

  function muestra(nombre) { Object.keys(P).forEach(function (p) { P[p].hidden = p !== nombre; }); raiz.dataset.estado = nombre; }

  // ---------- partida ----------
  function empieza() {
    ronda = J.baraja(candidatos()).slice(0, filtro.largo); k = 0; jugadas = [];
    el.progreso.innerHTML = ronda.map(function () { return '<i></i>'; }).join('');
    capaRonda.clearLayers();
    muestra('juego');
    turno();
  }

  function turno() {
    var s = ronda[k];
    intento = null;
    capaRonda.clearLayers();
    [].forEach.call(el.progreso.children, function (i, n) { i.className = n < k ? (jugadas[n].puntos >= 500 ? 'bien' : 'mal') : (n === k ? 'ahora' : ''); });
    el.contador.textContent = 'Sitio ' + (k + 1) + ' de ' + ronda.length;
    el.categoria.textContent = '//' + nombreCategoria(s.categoria).toLowerCase() + (filtro.isla === 'todas' ? '' : ' · ' + s.isla);
    el.nombre.textContent = s.nombre;
    el.instruccion.textContent = movil() ? 'Toca el mapa donde creas que está.' : 'Pincha en el mapa donde creas que está.';
    el.instruccion.hidden = false;
    el.resultado.hidden = true;
    el.confirmar.hidden = false; el.confirmar.disabled = true;
    el.centro.hidden = false;
    el.siguiente.hidden = true;
    el.marcador.textContent = J.miles(jugadas.reduce(function (a, j) { return a + j.puntos; }, 0)) + ' puntos';
    encuadra(limitesFiltro(), 10);
    el.nombre.focus({ preventScroll: true });
  }
  function nombreCategoria(id) { var c = datos.categorias.filter(function (c) { return c.id === id; })[0]; return c ? c.nombre : ''; }

  function marca(latlng) {
    if (!ronda[k] || !el.resultado.hidden || estadoPantalla() !== 'juego') return;
    intento = latlng;
    capaRonda.clearLayers();
    L.circleMarker(latlng, { radius: 9, color: '#04161C', weight: 2, fillColor: '#F0A840', fillOpacity: 1 }).addTo(capaRonda);
    el.confirmar.disabled = false;
    el.instruccion.textContent = 'Si no te convence, vuelve a pinchar. Cuando lo tengas, confirma.';
  }
  mapa.on('click', function (e) { marca(e.latlng); });
  el.centro.addEventListener('click', function () { marca(mapa.getCenter()); });

  function puntua(d) { return d <= 0.5 ? 1000 : Math.round(1000 * Math.exp(-(d - 0.5) / 25)); }

  el.confirmar.addEventListener('click', function () {
    if (!intento) return;
    var s = ronda[k], real = L.latLng(s.lat, s.lng);
    var d = J.km([intento.lat, intento.lng], [s.lat, s.lng]), pts = puntua(d);
    jugadas[k] = { sitio: s, intento: intento, km: d, puntos: pts };
    L.polyline([intento, real], { color: '#F0A840', weight: 2, dashArray: '6 7', interactive: false }).addTo(capaRonda);
    L.circleMarker(real, { radius: 13, color: '#96D6D6', weight: 2, fill: false, interactive: false }).addTo(capaRonda);
    L.circleMarker(real, { radius: 6, color: '#04161C', weight: 2, fillColor: '#96D6D6', fillOpacity: 1, interactive: false }).addTo(capaRonda);
    el.km.textContent = d < 1 ? 'A ' + Math.round(d * 1000) + ' m' : 'A ' + J.decimal(d, d < 10 ? 1 : 0) + ' km';
    el.puntos.textContent = J.miles(pts) + ' puntos';
    el.donde.textContent = s.nombre === s.municipio ? s.nombre + ' es un municipio de ' + s.isla + '.'
      : s.nombre + ' está en ' + s.municipio + ' (' + s.isla + ').';
    el.instruccion.hidden = true;
    J.pintaFuente(el.fuente, s.fuente);
    el.resultado.hidden = false;
    el.confirmar.hidden = true; el.centro.hidden = true;
    el.siguiente.hidden = false;
    el.siguiente.textContent = k === ronda.length - 1 ? 'Ver resultado' : 'Siguiente sitio';
    el.progreso.children[k].className = pts >= 500 ? 'bien' : 'mal';
    el.marcador.textContent = J.miles(jugadas.reduce(function (a, j) { return a + j.puntos; }, 0)) + ' puntos';
    encuadra(L.latLngBounds([intento, real]).pad(0.25), 12);
    el.siguiente.focus({ preventScroll: true });
  });

  el.siguiente.addEventListener('click', function () { k++; if (k < ronda.length) turno(); else final(); });

  // ---------- resultado ----------
  function final() {
    var total = jugadas.reduce(function (a, j) { return a + j.puntos; }, 0), max = jugadas.length * 1000, pc = total / max;
    if (window.hbtMedir) window.hbtMedir('juego_fin', { juego: 'donde-esta', resultado: Math.round(pc * 10) * 10 + '%' });
    var nivel = pc >= 0.85 ? 'Te lo sabes de memoria' : pc >= 0.6 ? 'Buen ojo' : pc >= 0.35 ? 'Vas bien encaminado' : 'Toca darse un paseo por las islas';
    capaRonda.clearLayers();
    var b = L.latLngBounds([]);
    jugadas.forEach(function (j) {
      var real = L.latLng(j.sitio.lat, j.sitio.lng);
      L.polyline([j.intento, real], { color: '#F0A840', weight: 1.5, dashArray: '5 6', opacity: 0.8, interactive: false }).addTo(capaRonda);
      L.circleMarker(j.intento, { radius: 5, color: '#04161C', weight: 1.5, fillColor: '#F0A840', fillOpacity: 1, interactive: false }).addTo(capaRonda);
      L.circleMarker(real, { radius: 5, color: '#04161C', weight: 1.5, fillColor: '#96D6D6', fillOpacity: 1, interactive: false }).addTo(capaRonda);
      b.extend(real); b.extend(j.intento);
    });
    el.total.innerHTML = '<b></b><span></span>';
    el.total.firstChild.textContent = J.miles(total); el.total.lastChild.textContent = ' / ' + J.miles(max);
    el.nivel.textContent = nivel;
    el.lista.innerHTML = '';
    jugadas.forEach(function (j) {
      var li = document.createElement('li');
      li.innerHTML = '<span class="n"></span><span class="km"></span><span class="pts"></span>';
      li.children[0].textContent = j.sitio.nombre;
      li.children[1].textContent = j.km < 1 ? Math.round(j.km * 1000) + ' m' : J.decimal(j.km, j.km < 10 ? 1 : 0) + ' km';
      li.children[2].textContent = J.miles(j.puntos);
      el.lista.appendChild(li);
    });
    muestra('final');
    setTimeout(function () { encuadra(b.pad(0.1), 10); }, 30);
    var texto = datos.titulo + ' en Canarias: ' + J.miles(total) + ' de ' + J.miles(max) + ' puntos · ' + nivel + '\n' +
      jugadas.map(function (j) { return j.puntos >= 800 ? '🟧' : j.puntos >= 400 ? '🟫' : '⬛'; }).join('') + '\n¿Tú lo harías mejor?';
    J.fuentesListas().then(function () {
      var cv = J.tarjeta({ juego: datos.titulo, marcador: J.miles(total), de: 'puntos', nivel: nivel, barras: jugadas.map(function (j) { return j.puntos / 1000; }),
        url: datos.url, frase: '¿Tú lo harías mejor?', dibujo: dibujo });
      J.compartir({ lienzo: cv, texto: texto, url: datos.url, archivo: 'donde-esta-' + total + '-puntos.png', nodo: el.compartir });
    });
    el.total.focus({ preventScroll: true });
  }

  // Islas, intentos (ocre) y sitios reales (turquesa) en la tarjeta.
  function dibujo(ctx, caja) {
    var cos = Math.cos(28.3 * Math.PI / 180), x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    contorno.features.forEach(function (f) { f.geometry.coordinates.forEach(function (pol) { pol[0].forEach(function (c) { x0 = Math.min(x0, c[0] * cos); x1 = Math.max(x1, c[0] * cos); y0 = Math.min(y0, -c[1]); y1 = Math.max(y1, -c[1]); }); }); });
    var esc = Math.min(caja.w / (x1 - x0), caja.h / (y1 - y0)), ox = caja.x, oy = caja.y + (caja.h - (y1 - y0) * esc) / 2;
    var xy = function (lng, lat) { return [ox + (lng * cos - x0) * esc, oy + (-lat - y0) * esc]; };
    ctx.save(); ctx.beginPath(); ctx.rect(caja.x - 20, caja.y - 10, caja.w + 40, caja.h + 20); ctx.clip();
    ctx.fillStyle = 'rgba(150,214,214,.16)'; ctx.strokeStyle = 'rgba(150,214,214,.55)'; ctx.lineWidth = 2;
    contorno.features.forEach(function (f) {
      ctx.beginPath();
      f.geometry.coordinates.forEach(function (pol) { pol.forEach(function (an) { an.forEach(function (c, i) { var p = xy(c[0], c[1]); if (i) ctx.lineTo(p[0], p[1]); else ctx.moveTo(p[0], p[1]); }); ctx.closePath(); }); });
      ctx.fill('evenodd'); ctx.stroke();
    });
    jugadas.forEach(function (j) {
      var a = xy(j.intento.lng, j.intento.lat), r = xy(j.sitio.lng, j.sitio.lat);
      ctx.setLineDash([8, 8]); ctx.strokeStyle = 'rgba(240,168,64,.85)'; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(r[0], r[1]); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = '#96D6D6'; ctx.beginPath(); ctx.arc(r[0], r[1], 9, 0, 7); ctx.fill();
      ctx.fillStyle = '#F0A840'; ctx.beginPath(); ctx.arc(a[0], a[1], 9, 0, 7); ctx.fill();
    });
    ctx.restore();
  }

  el.empezar.addEventListener('click', empieza);
  el.otra.addEventListener('click', function () { muestra('inicio'); capaRonda.clearLayers(); encuadra(limitesFiltro(), 10); });
  window.addEventListener('resize', function () { mapa.invalidateSize(); });
})();
