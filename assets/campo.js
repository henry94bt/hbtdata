/* Campo de partículas de la portada de hbtdata.
   Un solo sistema de partículas (WebGL2, sin librerías) que cambia de forma con el scroll:
   el logo, las islas, las gasolineras reales, un campo de fútbol, las historias de
   Historia para Gandules, un 1 X 2, los carruseles, los picos de las islas y el logo otra vez.
   Las formas salen de las escenas de la página: <article class="escena" data-forma="...">. */
(function () {
  'use strict';

  var DATOS = window.CAMPO_DATOS || {};
  var CLARO = [0.97, 0.95, 0.92];
  var OCRE = [0.94, 0.62, 0.20];
  var SUAVE = [0.50, 0.82, 0.82];

  // ---------- utilidades ----------

  function azar(semilla) {                       // mulberry32: mismas formas en cada visita
    var a = semilla >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function gauss(R) {
    var u = R() || 1e-6, v = R();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }
  function mezcla(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; }
  function escala(c, k) { return [c[0] * k, c[1] * k, c[2] * k]; }
  function elige(acum, x) {                      // índice según pesos acumulados
    var lo = 0, hi = acum.length - 1;
    while (lo < hi) { var m = (lo + hi) >> 1; if (acum[m] < x) lo = m + 1; else hi = m; }
    return lo;
  }
  function acumula(pesos) {
    var s = 0, out = pesos.map(function (p) { s += p; return s; });
    return out.map(function (v) { return v / s; });
  }

  function Forma(N) {
    this.N = N; this.p = new Float32Array(N * 3); this.c = new Float32Array(N * 3); this.i = 0;
  }
  Forma.prototype.pon = function (x, y, z, col) {
    var k = this.i++ * 3;
    if (this.i > this.N) return;
    this.p[k] = x; this.p[k + 1] = y; this.p[k + 2] = z;
    this.c[k] = col[0]; this.c[k + 1] = col[1]; this.c[k + 2] = col[2];
  };
  Forma.prototype.inclina = function (ang) {     // gira alrededor del eje X (mapa «tumbado»)
    var s = Math.sin(ang), co = Math.cos(ang), p = this.p;
    for (var k = 0; k < p.length; k += 3) {
      var y = p[k + 1], z = p[k + 2];
      p[k + 1] = y * co - z * s; p[k + 2] = y * s + z * co;
    }
    return this;
  };

  // ---------- geometría de Canarias ----------

  var K = 2.55 / (4.9 * 0.879);
  function proy(lon, lat) { return [(lon + 15.74) * 0.879 * K, (lat - 28.52) * K]; }

  var ANILLOS = (DATOS.islas || []).map(function (r) { return r.map(function (q) { return proy(q[0], q[1]); }); });
  var INFO = ANILLOS.map(function (r) {
    var a = 0, per = 0, x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9, segs = [];
    for (var i = 0; i < r.length; i++) {
      var p = r[i], q = r[(i + 1) % r.length];
      a += p[0] * q[1] - q[0] * p[1];
      var l = Math.hypot(q[0] - p[0], q[1] - p[1]); per += l; segs.push(per);
      x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]);
    }
    return { area: Math.abs(a) / 2, per: per, segs: segs, caja: [x0, x1, y0, y1] };
  });
  var POR_AREA = acumula(INFO.map(function (f) { return f.area; }));
  var POR_COSTA = acumula(INFO.map(function (f) { return f.per; }));

  function dentro(r, x, y) {
    var d = false;
    for (var i = 0, j = r.length - 1; i < r.length; j = i++) {
      var a = r[i], b = r[j];
      if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) d = !d;
    }
    return d;
  }
  function puntoIsla(R) {
    var k = elige(POR_AREA, R()), c = INFO[k].caja;
    for (var t = 0; t < 200; t++) {
      var x = c[0] + R() * (c[1] - c[0]), y = c[2] + R() * (c[3] - c[2]);
      if (dentro(ANILLOS[k], x, y)) return [x, y];
    }
    return ANILLOS[k][0];
  }
  function puntoCosta(R) {
    var k = elige(POR_COSTA, R()), f = INFO[k], r = ANILLOS[k];
    var d = R() * f.per, i = 0;
    while (f.segs[i] < d) i++;
    var a = r[i], b = r[(i + 1) % r.length], l0 = i ? f.segs[i - 1] : 0, t = (d - l0) / ((f.segs[i] - l0) || 1);
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  }

  // ---------- las formas ----------

  var FORMAS = {
    esfera: function (N, R) {
      var f = new Forma(N);
      for (var i = 0; i < N; i++) {
        var x = gauss(R), y = gauss(R), z = gauss(R), r = 1.05 * Math.cbrt(R()) / (Math.hypot(x, y, z) || 1);
        f.pon(x * r, y * r, z * r, mezcla(CLARO, SUAVE, R() * 0.5));
      }
      return f;
    },

    logo: function (N, R) {                     // las cinco barras con forma de volcán
      var f = new Forma(N), H = [0.32, 0.62, 1, 0.8, 0.46], s = 1.75, gap = s * 0.05;
      var bw = (s - 4 * gap) / 5, rad = bw * 0.28, acum = acumula(H);
      for (var i = 0; i < N; i++) {
        var b = elige(acum, R()), x0 = -s / 2 + b * (bw + gap), y0 = -s / 2, h = H[b] * s, x, y;
        for (var t = 0; t < 20; t++) {
          x = R() * bw; y = R() * h;
          var dx = Math.min(x, bw - x), dy = Math.min(y, h - y);
          if (!(dx < rad && dy < rad && Math.hypot(rad - dx, rad - dy) > rad)) break;
        }
        var z = gauss(R) * (R() < 0.25 ? 0.16 : 0.05);
        f.pon(x0 + x, y0 + y, z, b === 2 ? mezcla(OCRE, CLARO, R() * 0.12) : escala(CLARO, 0.8 + R() * 0.2));
      }
      return f;
    },

    islas: function (N, R) {
      var f = new Forma(N);
      for (var i = 0; i < N; i++) {
        var costa = R() < 0.3, q = costa ? puntoCosta(R) : puntoIsla(R);
        f.pon(q[0] + gauss(R) * 0.004, q[1] + gauss(R) * 0.004, gauss(R) * 0.03,
          costa ? CLARO : escala(mezcla(SUAVE, CLARO, R() * 0.3), 0.75));
      }
      return f;
    },

    gasolineras: function (N, R) {               // cada grupito, una gasolinera; color por precio
      var f = new Forma(N), G = (DATOS.gasolineras || []).map(function (g) {
        var q = proy(g[0], g[1]), t = Math.max(0, Math.min(1, (g[2] - 1.42) / 0.26));
        return [q[0], q[1], t < 0.5 ? mezcla(SUAVE, CLARO, t * 2) : mezcla(CLARO, OCRE, (t - 0.5) * 2)];
      });
      for (var i = 0; i < N; i++) {
        if (R() < 0.16 || !G.length) {
          var q = puntoCosta(R);
          f.pon(q[0], q[1], gauss(R) * 0.01, [0.10, 0.24, 0.26]);
        } else {
          var g = G[Math.floor(R() * G.length)];
          f.pon(g[0] + gauss(R) * 0.0075, g[1] + gauss(R) * 0.0075, gauss(R) * 0.012, g[2]);
        }
      }
      return f;
    },

    campo: function (N, R) {                     // un campo de fútbol visto en perspectiva
      var f = new Forma(N), k = 2.05 / 105, L = [];
      function seg(x0, y0, x1, y1) { L.push([x0, y0, x1, y1]); }
      function arco(cx, cy, r, a0, a1) {
        var n = 40;
        for (var i = 0; i < n; i++) {
          var a = a0 + (a1 - a0) * i / n, b = a0 + (a1 - a0) * (i + 1) / n;
          seg(cx + r * Math.cos(a), cy + r * Math.sin(a), cx + r * Math.cos(b), cy + r * Math.sin(b));
        }
      }
      var X = 52.5, Y = 34;
      seg(-X, -Y, X, -Y); seg(X, -Y, X, Y); seg(X, Y, -X, Y); seg(-X, Y, -X, -Y); seg(0, -Y, 0, Y);
      arco(0, 0, 9.15, 0, 2 * Math.PI);
      [-1, 1].forEach(function (s) {
        var a = s * X;
        seg(a, -20.16, a - s * 16.5, -20.16); seg(a - s * 16.5, -20.16, a - s * 16.5, 20.16); seg(a - s * 16.5, 20.16, a, 20.16);
        seg(a, -9.16, a - s * 5.5, -9.16); seg(a - s * 5.5, -9.16, a - s * 5.5, 9.16); seg(a - s * 5.5, 9.16, a, 9.16);
        var ang = Math.acos(5.5 / 9.15);
        if (s > 0) arco(a - 11, 0, 9.15, Math.PI - ang, Math.PI + ang); else arco(a + 11, 0, 9.15, -ang, ang);
        seg(a, -3.66, a + s * 2, -3.66); seg(a + s * 2, -3.66, a + s * 2, 3.66); seg(a + s * 2, 3.66, a, 3.66);
      });
      var largos = L.map(function (s) { return Math.hypot(s[2] - s[0], s[3] - s[1]); }), acum = acumula(largos);
      for (var i = 0; i < N; i++) {
        if (R() < 0.68) {
          var s = L[elige(acum, R())], t = R();
          f.pon((s[0] + (s[2] - s[0]) * t) * k + gauss(R) * 0.004, (s[1] + (s[3] - s[1]) * t) * k + gauss(R) * 0.004,
            gauss(R) * 0.004, escala(CLARO, 0.85 + R() * 0.15));
        } else if (R() < 0.04) {
          f.pon(gauss(R) * 0.02, gauss(R) * 0.02, 0.05 + gauss(R) * 0.02, OCRE);   // el balón
        } else {                                  // el césped, a franjas
          var fx = (R() * 2 - 1) * (X + 3), fy = (R() * 2 - 1) * (Y + 3);
          f.pon(fx * k, fy * k, gauss(R) * 0.01,
            (Math.floor((fx + X + 3) / 9.25) % 2) ? [0.10, 0.27, 0.24] : [0.06, 0.18, 0.17]);
        }
      }
      return f.inclina(-1.02);
    },

    historias: function (N, R) {                 // las historias de @historiaparagandules como chinchetas
      var f = new Forma(N), Z = 1.12, P = (DATOS.historias || []).map(function (h) { var q = proy(h[0], h[1]); return [q[0] * Z, q[1] * Z]; });
      for (var i = 0; i < N; i++) {
        var r = R();
        if (r < 0.30 || !P.length) {
          var q = puntoIsla(R);
          f.pon(q[0] * Z, q[1] * Z, gauss(R) * 0.008, escala(SUAVE, 0.38));
        } else if (r < 0.42) {
          var c = puntoCosta(R);
          f.pon(c[0] * Z, c[1] * Z, 0, escala(CLARO, 0.55));
        } else {
          var p = P[Math.floor(R() * P.length)], h = 0.15;
          if (R() < 0.45) {
            var x = gauss(R), y = gauss(R), z = gauss(R), n = Math.hypot(x, y, z) || 1, rr = 0.013 * Math.cbrt(R());
            f.pon(p[0] + x / n * rr, p[1] + y / n * rr, h + z / n * rr, escala(mezcla(OCRE, CLARO, R() * 0.2), 0.8));
          } else {
            f.pon(p[0] + gauss(R) * 0.002, p[1] + gauss(R) * 0.002, R() * h, escala(CLARO, 0.45));
          }
        }
      }
      return f.inclina(-0.95);
    },

    unoequisdos: function (N, R) {               // 1 X 2, dibujado con la propia fuente de la web
      var f = new Forma(N), cv = document.createElement('canvas'), W = 900, H = 320;
      cv.width = W; cv.height = H;
      var g = cv.getContext('2d');
      g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.font = '600 250px Poppins, system-ui, sans-serif';
      var ts = ['1', 'X', '2'];
      ts.forEach(function (t, i) { g.fillText(t, W / 2 + (i - 1) * 300, H / 2 + 10); });
      var d = g.getImageData(0, 0, W, H).data, pts = [];
      for (var y = 0; y < H; y += 2) for (var x = 0; x < W; x += 2) if (d[(y * W + x) * 4 + 3] > 140) pts.push(x, y);
      var n = pts.length / 2;
      for (var i = 0; i < N; i++) {
        var k = Math.floor(R() * n) * 2, px = pts[k] + R() * 2, py = pts[k + 1] + R() * 2;
        var x = (px - W / 2) / W * 2.2, y = -(py - H / 2) / W * 2.2;
        f.pon(x + gauss(R) * 0.004, y + gauss(R) * 0.004, gauss(R) * 0.06,
          Math.abs(x) < 0.37 ? mezcla(OCRE, CLARO, R() * 0.12) : escala(CLARO, 0.8 + R() * 0.2));
      }
      return f;
    },

    carruseles: function (N, R) {                // cinco diapositivas 4:5 en abanico
      var f = new Forma(N), w = 0.52, h = 0.65, piv = -1.45;
      for (var i = 0; i < N; i++) {
        var c = Math.floor(R() * 5), a = (c - 2) * 0.24, borde = R() < 0.35, x, y;
        if (borde) {
          var t = R() * 2 * (w + h);
          if (t < w) { x = t; y = 0; } else if (t < w + h) { x = w; y = t - w; }
          else if (t < 2 * w + h) { x = 2 * w + h - t; y = h; } else { x = 0; y = 2 * (w + h) - t; }
        } else { x = R() * w; y = R() * h; }
        x -= w / 2; y += -0.42;
        var yy = y - piv, xr = x * Math.cos(a) + yy * Math.sin(a), yr = -x * Math.sin(a) + yy * Math.cos(a) + piv;
        var col = c === 2 ? OCRE : escala(CLARO, 0.55 + 0.15 * (2 - Math.abs(c - 2)));
        f.pon(xr, yr + 0.25, (c - 2) * 0.03 + gauss(R) * 0.012, borde ? col : escala(col, 0.55));
      }
      return f;
    },

    picos: function (N, R) {                     // la cumbre más alta de cada isla, desde el nivel del mar
      var f = new Forma(N), P = DATOS.picos || [1501, 2426, 1487, 3715, 1949, 807, 670];
      var n = P.length, ancho = 2.3, gap = 0.09, bw = (ancho - gap * (n - 1)) / n, base = -0.78;
      var acum = acumula(P);
      for (var i = 0; i < N; i++) {
        if (R() < 0.16) {
          var x = (R() * 2 - 1) * 1.25;
          f.pon(x, base - 0.03 + 0.018 * Math.sin(x * 11) + gauss(R) * 0.012, gauss(R) * 0.05, mezcla(SUAVE, CLARO, R() * 0.2));
        } else {
          var b = elige(acum, R()), h = P[b] / 3715 * 1.55;
          f.pon(-ancho / 2 + b * (bw + gap) + R() * bw, base + R() * h, gauss(R) * 0.05,
            b === 3 ? mezcla(OCRE, CLARO, R() * 0.12) : escala(CLARO, 0.8 + R() * 0.2));
        }
      }
      return f;
    }
  };

  // ---------- WebGL ----------

  var VS = [
    '#version 300 es',
    'in vec3 aA; in vec3 aB; in vec3 aCA; in vec3 aCB; in vec4 aR;',
    'uniform mat4 uMVP; uniform float uMix, uTime, uBurst, uMotion, uPx, uAspect, uAlpha;',
    'uniform vec2 uOffset, uMouse; uniform float uMouseOn;',
    'out vec3 vC; out float vA;',
    'void main(){',
    '  float m = clamp((uMix - aR.x*0.35)/0.65, 0.0, 1.0); m = m*m*(3.0-2.0*m);',
    '  vec3 p = mix(aA, aB, m);',
    '  vec3 dir = normalize(vec3(sin(aR.z*61.0+1.3), cos(aR.w*47.0), sin(aR.z*29.0+aR.w*13.0)));',
    '  p += dir * sin(3.14159*m) * uBurst * (0.18 + 0.42*aR.w);',
    '  p += uMotion * 0.011 * vec3(sin(uTime*0.7+aR.z*40.0), cos(uTime*0.6+aR.w*30.0), sin(uTime*0.5+aR.x*20.0));',
    '  vec4 c = uMVP * vec4(p, 1.0);',
    '  vec2 ndc = c.xy / c.w + uOffset;',
    '  vec2 d = ndc - uMouse; d.x *= uAspect;',
    '  float r2 = dot(d, d);',
    '  vec2 empuje = (d / (sqrt(r2) + 1e-4)) * uMouseOn * 0.11 * exp(-r2 / 0.03) * (0.6 + 0.8*aR.y);',
    '  empuje.x /= uAspect;',
    '  ndc += empuje;',
    '  gl_Position = vec4(ndc * c.w, c.z, c.w);',
    '  gl_PointSize = uPx * (0.55 + aR.y) * (4.2 / c.w);',
    '  vC = mix(aCA, aCB, m);',
    '  vA = uAlpha * (0.55 + 0.45*aR.w);',
    '}'
  ].join('\n');
  var FS = [
    '#version 300 es',
    'precision mediump float;',
    'in vec3 vC; in float vA; out vec4 o;',
    'void main(){',
    '  float d = length(gl_PointCoord - 0.5);',
    '  float a = (exp(-d*d*42.0) + 0.22*exp(-d*d*9.0)) * vA;',
    '  o = vec4(vC * a, a);',
    '}'
  ].join('\n');

  function sombreador(gl, tipo, src) {
    var s = gl.createShader(tipo);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }

  function perspectiva(fov, asp, n, f) {
    var t = 1 / Math.tan(fov / 2), nf = 1 / (n - f);
    return [t / asp, 0, 0, 0, 0, t, 0, 0, 0, 0, (f + n) * nf, -1, 0, 0, 2 * f * n * nf, 0];
  }
  function mult(a, b) {
    var o = new Array(16);
    for (var i = 0; i < 4; i++) for (var j = 0; j < 4; j++) {
      var s = 0;
      for (var k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k];
      o[i * 4 + j] = s;
    }
    return o;
  }
  function modelo(ry, rx, esc, z) {
    var cy = Math.cos(ry), sy = Math.sin(ry), cx = Math.cos(rx), sx = Math.sin(rx);
    // traslación * rotY * rotX * escala
    return [
      cy * esc, 0, -sy * esc, 0,
      sy * sx * esc, cx * esc, cy * sx * esc, 0,
      sy * cx * esc, -sx * esc, cy * cx * esc, 0,
      0, 0, -z, 1
    ];
  }

  // ---------- arranque ----------

  window.CampoParticulas = function (opciones) {
    var canvas = opciones.canvas;
    var gl = canvas.getContext('webgl2', { antialias: false, alpha: true, premultipliedAlpha: true, powerPreference: 'high-performance' });
    if (!gl) return null;
    var prog = gl.createProgram();
    gl.attachShader(prog, sombreador(gl, gl.VERTEX_SHADER, VS));
    gl.attachShader(prog, sombreador(gl, gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return null;
    gl.useProgram(prog);

    var N = opciones.particulas;
    var R = azar(94);
    var rnd = new Float32Array(N * 4);
    for (var i = 0; i < rnd.length; i++) rnd[i] = R();

    function buf(data) { var b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW); return b; }
    var loc = {}, U = {};
    ['aA', 'aB', 'aCA', 'aCB', 'aR'].forEach(function (n) { loc[n] = gl.getAttribLocation(prog, n); gl.enableVertexAttribArray(loc[n]); });
    ['uMVP', 'uMix', 'uTime', 'uBurst', 'uMotion', 'uPx', 'uAspect', 'uAlpha', 'uOffset', 'uMouse', 'uMouseOn'].forEach(function (n) { U[n] = gl.getUniformLocation(prog, n); });
    var bR = buf(rnd);

    var cache = {};
    function forma(nombre) {
      if (!cache[nombre]) {
        var f = (FORMAS[nombre] || FORMAS.esfera)(N, azar(nombre.length * 7919 + 13));
        cache[nombre] = { p: buf(f.p), c: buf(f.c) };
      }
      return cache[nombre];
    }
    function ata(l, b, n) { gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.vertexAttribPointer(l, n, gl.FLOAT, false, 0, 0); }

    gl.disable(gl.DEPTH_TEST);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE);
    gl.clearColor(0, 0, 0, 0);

    var dpr = 1, ancho = 0, alto = 0;
    function mide() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      ancho = canvas.clientWidth; alto = canvas.clientHeight;
      canvas.width = Math.round(ancho * dpr); canvas.height = Math.round(alto * dpr);
      gl.viewport(0, 0, canvas.width, canvas.height);
    }
    mide();

    return {
      mide: mide,
      precarga: function (nombres) { nombres.forEach(forma); },
      // estado = { de, a, mezcla, explosion, t, giro:[y,x], escala, desplaza:[x,y], raton:[x,y], fuerza, movimiento }
      pinta: function (e) {
        var A = forma(e.de), B = forma(e.a);
        ata(loc.aA, A.p, 3); ata(loc.aCA, A.c, 3); ata(loc.aB, B.p, 3); ata(loc.aCB, B.c, 3); ata(loc.aR, bR, 4);
        var asp = ancho / Math.max(1, alto);
        var mvp = mult(perspectiva(0.62, asp, 0.1, 20), modelo(e.giro[0], e.giro[1], e.escala, 4.2));
        gl.uniformMatrix4fv(U.uMVP, false, new Float32Array(mvp));
        gl.uniform1f(U.uMix, e.mezcla);
        gl.uniform1f(U.uTime, e.t);
        gl.uniform1f(U.uBurst, e.explosion);
        gl.uniform1f(U.uMotion, e.movimiento);
        gl.uniform1f(U.uPx, opciones.tam * dpr);
        gl.uniform1f(U.uAspect, asp);
        gl.uniform1f(U.uAlpha, opciones.alfa);
        gl.uniform2f(U.uOffset, e.desplaza[0], e.desplaza[1]);
        gl.uniform2f(U.uMouse, e.raton[0], e.raton[1]);
        gl.uniform1f(U.uMouseOn, e.fuerza);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawArrays(gl.POINTS, 0, N);
      }
    };
  };
})();
