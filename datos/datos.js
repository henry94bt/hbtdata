/* hbtdata.es/datos/ · selector de combustible (Gasolina 95 / Diésel).
   Sin JavaScript se ven los dos bloques, uno detrás de otro. La elección se recuerda en este navegador. */
(function () {
  'use strict';
  var raiz = document.documentElement;
  raiz.classList.remove('sin-js');

  var chips = document.querySelectorAll('.filtros .chip[data-campo=combustible]');
  if (!chips.length) return;

  function guarda(v) { try { localStorage.setItem('hbt-combustible', v); } catch (e) { /* sin almacenamiento, da igual */ } }
  function lee() { try { return localStorage.getItem('hbt-combustible'); } catch (e) { return null; } }

  function pon(valor) {
    raiz.classList.toggle('ver-diesel', valor === 'diesel');
    chips.forEach(function (c) { c.setAttribute('aria-pressed', String(c.getAttribute('data-valor') === valor)); });
  }

  var pedido = new URLSearchParams(location.search).get('combustible');
  pon(pedido === 'diesel' || pedido === 'g95' ? pedido : (lee() === 'diesel' ? 'diesel' : 'g95'));

  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      var v = c.getAttribute('data-valor');
      pon(v);
      guarda(v);
    });
  });
})();
