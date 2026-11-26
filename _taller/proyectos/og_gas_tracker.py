"""Imagen para compartir de /proyectos/canarias-gas-tracker/ (assets/og-gas-tracker.png, 1200×630).

Uso: python3 _taller/proyectos/og_gas_tracker.py
Dibuja las gasolineras de assets/campo-datos.js (precios del 13/10/2026) coloreadas de turquesa
(más barata) a ocre (más cara) y la pasa a PNG con Playwright.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / 'assets' / 'og-gas-tracker.png'

HTML = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="assets/fuentes/fuentes.css">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1200px;height:630px;overflow:hidden;font-family:Poppins,sans-serif;color:#F7F3EC;
 background:radial-gradient(circle at 78% 55%,rgba(10,52,64,.95),transparent 60%),radial-gradient(circle at 15% 100%,rgba(10,52,64,.8),transparent 55%),#04161C}
.texto{position:absolute;left:60px;top:118px;width:560px}
.mono{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:500;letter-spacing:.2em;text-transform:uppercase;color:rgba(247,243,236,.7)}
.mono b{color:#F0A840;font-weight:500}
h1{font-weight:200;text-transform:uppercase;font-size:66px;line-height:1.02;margin:22px 0 26px;letter-spacing:-.01em}
p{font-weight:300;font-size:21px;line-height:1.55;color:rgba(247,243,236,.75)}
canvas{position:absolute;right:24px;top:96px}
.pie{position:absolute;right:60px;bottom:34px;font-size:11px}
</style></head><body>
<div class="texto"><p class="mono"><b>//Proyecto</b>&nbsp; Canarias Gas Tracker</p>
<h1>La gasolina más barata de las islas.</h1>
<p>Un mapa que se actualiza solo cada mañana con datos abiertos del Ministerio. Cómo está hecho y lo que aprendí.</p></div>
<canvas id="c" width="1080" height="840" style="width:540px;height:420px"></canvas>
<p class="mono pie">Gasolina 95 · 13 oct. 2026 · Ministerio</p>
<script src="assets/campo-datos.js"></script>
<script>
const D=window.CAMPO_DATOS, c=document.getElementById('c'), x=c.getContext('2d');
const lon0=-18.25,lon1=-13.3,lat0=27.55,lat1=29.5, W=c.width,H=c.height;
const k=Math.min(W/(lon1-lon0)/Math.cos(28.5*Math.PI/180), H/(lat1-lat0));
const ox=(W-(lon1-lon0)*Math.cos(28.5*Math.PI/180)*k)/2, oy=(H-(lat1-lat0)*k)/2;
const P=(lo,la)=>[ox+(lo-lon0)*Math.cos(28.5*Math.PI/180)*k, oy+(lat1-la)*k];
x.strokeStyle='rgba(247,243,236,.22)';x.lineWidth=2;
D.islas.forEach(r=>{x.beginPath();r.forEach((p,i)=>{const q=P(p[0],p[1]);i?x.lineTo(...q):x.moveTo(...q)});x.closePath();x.stroke()});
const ps=D.gasolineras.map(g=>g[2]).filter(Boolean).sort((a,b)=>a-b);
const q=f=>ps[Math.floor(f*(ps.length-1))], lo=q(.05), hi=q(.95);
const A=[150,214,214], B=[240,168,64];
D.gasolineras.forEach(g=>{const t=Math.max(0,Math.min(1,(g[2]-lo)/(hi-lo)));const col=A.map((a,i)=>Math.round(a+(B[i]-a)*t));
 const [px,py]=P(g[0],g[1]);x.fillStyle=`rgba(${col},.9)`;x.beginPath();x.arc(px,py,7,0,7);x.fill()});
</script></body></html>"""

tmp = RAIZ / '_og_tmp.html'
tmp.write_text(HTML, encoding='utf-8')
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome')
        pg = b.new_page(viewport={'width': 1200, 'height': 630})
        pg.goto(tmp.as_uri())
        pg.wait_for_timeout(600)
        pg.screenshot(path=str(SALIDA))
        b.close()
finally:
    tmp.unlink()
print('Escrito', SALIDA.relative_to(RAIZ))
