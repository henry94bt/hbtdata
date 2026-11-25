/* Utilidades comunes de los juegos de hbtdata.es: formato, azar, tarjeta de resultado y compartir.
   Sin librerías ni servidor. Expone window.Juegos. */
(function () {
  'use strict';

  var C = { fondo: '#04161C', petroleo: '#0A3440', claro: '#F7F3EC', tenue: 'rgba(247,243,236,.62)', linea: 'rgba(247,243,236,.16)', ocre: '#F0A840', suave: '#96D6D6' };

  function miles(n) { return Math.round(n).toLocaleString('es-ES'); }
  function decimal(n, d) { return n.toLocaleString('es-ES', { minimumFractionDigits: d, maximumFractionDigits: d }); }

  function baraja(lista) {
    var a = lista.slice();
    for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; }
    return a;
  }

  // Distancia en km entre dos puntos [lat, lng] (fórmula del haversine, radio medio de la Tierra).
  function km(a, b) {
    var R = 6371.0088, r = Math.PI / 180;
    var dLat = (b[0] - a[0]) * r, dLng = (b[1] - a[1]) * r;
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
  }

  // La fuente de un dato puede ser un objeto o una lista de objetos {nombre, url, fecha}.
  function pintaFuente(nodo, fuente) {
    nodo.textContent = '';
    var lista = Array.isArray(fuente) ? fuente : (fuente ? [fuente] : []);
    lista.forEach(function (f, k) {
      var p = document.createElement('span');
      p.appendChild(document.createTextNode(k ? '' : 'Fuente: '));
      var a = document.createElement(f.url ? 'a' : 'span');
      if (f.url) { a.href = f.url; a.target = '_blank'; a.rel = 'noopener'; }
      a.textContent = f.nombre;
      p.appendChild(a);
      if (f.fecha) p.appendChild(document.createTextNode(' (' + f.fecha + ')'));
      nodo.appendChild(p);
    });
  }

  // La cabecera gana fondo al bajar.
  function cabecera() {
    var barra = document.querySelector('.barra');
    if (!barra || barra.classList.contains('fija')) return;
    function f() { barra.classList.toggle('con-fondo', window.scrollY > 30); }
    window.addEventListener('scroll', f, { passive: true }); f();
  }

  // ---------- tarjeta de resultado (PNG 1080×1350, 4:5) ----------

  function volcan(ctx, x, y, alto, color) {         // el logo de 5 barras
    var barras = [[0, 68, 32], [21, 38, 62], [42, 0, 100], [63, 20, 80], [84, 54, 46]], k = alto / 100;
    barras.forEach(function (b, i) {
      ctx.fillStyle = i === 2 ? C.ocre : color;
      redondo(ctx, x + b[0] * k, y + b[1] * k, 16 * k, b[2] * k, 4.5 * k); ctx.fill();
    });
  }
  function redondo(ctx, x, y, w, h, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }
  function ajusta(ctx, texto, max, tam, peso) {
    var t = tam;
    do { ctx.font = peso + ' ' + t + 'px Poppins, system-ui, sans-serif'; t -= 4; } while (ctx.measureText(texto).width > max && t > 20);
  }

  // o = { juego, marcador, de, nivel, frase, casillas: [true/false…] | barras: [0..1…], url, dibujo: fn(ctx, caja) }
  function tarjeta(o) {
    var W = 1080, H = 1350, cv = document.createElement('canvas');
    cv.width = W; cv.height = H;
    var ctx = cv.getContext('2d');
    ctx.fillStyle = C.fondo; ctx.fillRect(0, 0, W, H);
    var g = ctx.createRadialGradient(W * 0.78, H * 0.3, 10, W * 0.78, H * 0.3, W * 0.7);
    g.addColorStop(0, 'rgba(240,168,64,.20)'); g.addColorStop(1, 'rgba(240,168,64,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    var g2 = ctx.createRadialGradient(W * 0.5, H * 1.15, 10, W * 0.5, H * 1.15, W * 0.9);
    g2.addColorStop(0, 'rgba(10,52,64,.95)'); g2.addColorStop(1, 'rgba(10,52,64,0)');
    ctx.fillStyle = g2; ctx.fillRect(0, 0, W, H);

    var M = 90;
    ctx.textBaseline = 'alphabetic';
    ctx.fillStyle = C.tenue; ctx.font = '500 26px "JetBrains Mono", ui-monospace, monospace';
    ctx.fillText('//JUEGOS · HBTDATA.ES', M, 140);

    ctx.fillStyle = C.claro; ajusta(ctx, o.juego.toUpperCase(), W - 2 * M, 92, '200');
    ctx.fillText(o.juego.toUpperCase(), M, 260);

    if (o.dibujo) o.dibujo(ctx, { x: M, y: 320, w: W - 2 * M, h: 360 });

    ctx.fillStyle = C.ocre; ajusta(ctx, o.marcador, W - 2 * M - 260, 230, '300');
    ctx.fillText(o.marcador, M, 900);
    var ancho = ctx.measureText(o.marcador).width;
    if (o.de) { ctx.fillStyle = C.tenue; ctx.font = '300 54px Poppins, system-ui, sans-serif'; ctx.fillText(o.de, M + ancho + 18, 900); }

    if (o.nivel) { ctx.fillStyle = C.claro; ajusta(ctx, o.nivel, W - 2 * M, 60, '400'); ctx.fillText(o.nivel, M, 990); }

    var y = 1050;
    if (o.casillas) {
      var n = o.casillas.length, gap = 14, lado = Math.min(64, (W - 2 * M - gap * (n - 1)) / n);
      o.casillas.forEach(function (ok, i) {
        var x = M + i * (lado + gap);
        redondo(ctx, x, y, lado, lado, 12);
        if (ok) { ctx.fillStyle = C.ocre; ctx.fill(); }
        else { ctx.strokeStyle = 'rgba(247,243,236,.45)'; ctx.lineWidth = 3; ctx.stroke(); }
      });
    }
    if (o.barras) {
      var nb = o.barras.length, gb = 10, wb = (W - 2 * M - gb * (nb - 1)) / nb, hb = 90;
      o.barras.forEach(function (v, i) {
        var x = M + i * (wb + gb);
        ctx.fillStyle = 'rgba(247,243,236,.12)'; redondo(ctx, x, y, wb, hb, 8); ctx.fill();
        var h = Math.max(4, hb * v);
        ctx.fillStyle = C.ocre; redondo(ctx, x, y + hb - h, wb, h, 8); ctx.fill();
      });
    }

    ctx.strokeStyle = C.linea; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(M, H - 150); ctx.lineTo(W - M, H - 150); ctx.stroke();
    ctx.fillStyle = C.claro; ctx.font = '400 38px Poppins, system-ui, sans-serif';
    ctx.fillText(o.frase || '¿Y tú cuánto sabes?', M, H - 82);
    ctx.fillStyle = C.ocre; ctx.font = '500 26px "JetBrains Mono", ui-monospace, monospace';
    ctx.fillText(o.url.replace(/^https?:\/\//, ''), M, H - 40);
    volcan(ctx, W - M - 74, H - 118, 74, C.claro);
    return cv;
  }

  function aBlob(cv) {
    return new Promise(function (ok) { cv.toBlob(function (b) { ok(b); }, 'image/png'); });
  }

  // Monta los botones de compartir. o = { lienzo, texto, url, archivo, nodo }
  function compartir(o) {
    var nodo = o.nodo, img = nodo.querySelector('img'), aviso = nodo.querySelector('.aviso-copia');
    var b = { comparte: nodo.querySelector('[data-accion=compartir]'), baja: nodo.querySelector('[data-accion=descargar]'), copia: nodo.querySelector('[data-accion=copiar]') };
    var blobP = aBlob(o.lienzo), url = null;
    blobP.then(function (blob) { url = URL.createObjectURL(blob); img.src = url; });
    var mensaje = o.texto + '\n' + o.url;
    function dice(t) { aviso.textContent = t; setTimeout(function () { if (aviso.textContent === t) aviso.textContent = ''; }, 4000); }

    b.comparte.onclick = function () {
      blobP.then(function (blob) {
        var file = null;
        try { file = new File([blob], o.archivo, { type: 'image/png' }); } catch (e) { file = null; }
        if (file && navigator.canShare && navigator.canShare({ files: [file] })) {
          return navigator.share({ files: [file], text: mensaje }).catch(function () {});
        }
        if (navigator.share) return navigator.share({ text: o.texto, url: o.url }).catch(function () {});
        b.copia.onclick();
      });
    };
    b.baja.onclick = function () {
      blobP.then(function () {
        var a = document.createElement('a'); a.href = url; a.download = o.archivo; document.body.appendChild(a); a.click(); a.remove();
      });
    };
    b.copia.onclick = function () {
      var hecho = function () { dice('Copiado. Pégalo en WhatsApp o donde quieras.'); };
      if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(mensaje).then(hecho, function () { manual(); });
      else manual();
      function manual() {
        var t = document.createElement('textarea'); t.value = mensaje; t.setAttribute('readonly', ''); t.style.position = 'fixed'; t.style.opacity = '0';
        document.body.appendChild(t); t.select();
        try { document.execCommand('copy'); hecho(); } catch (e) { dice('No se pudo copiar.'); }
        t.remove();
      }
    };
  }

  // Espera a que Poppins y JetBrains Mono estén listas antes de dibujar en el lienzo.
  function fuentesListas() {
    if (!document.fonts || !document.fonts.load) return Promise.resolve();
    return Promise.all([
      document.fonts.load('200 92px Poppins'), document.fonts.load('300 92px Poppins'), document.fonts.load('400 40px Poppins'),
      document.fonts.load('500 26px "JetBrains Mono"')
    ]).catch(function () {});
  }

  window.Juegos = { C: C, miles: miles, decimal: decimal, baraja: baraja, km: km, pintaFuente: pintaFuente, cabecera: cabecera, tarjeta: tarjeta, compartir: compartir, fuentesListas: fuentesListas, redondo: redondo };
})();
