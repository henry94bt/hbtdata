/* Formulario de contacto sin servidor: con lo que rellena la persona prepara un correo
   y abre su programa de correo con el mensaje ya escrito.
   Uso: <form class="formulario" data-correo="..." data-asunto="hbtdata.es" data-idioma="es|en"> */
(function () {
  'use strict';
  var TEXTOS = {
    es: {
      saludo: 'Hola, Henry:', vacio: '(Sin mensaje)', sin: 'Sin especificar',
      que: 'Qué necesito: ', nombre: 'Nombre: ', contacto: 'Cómo contactarme: ', negocio: 'Negocio o empresa: ',
      estado: 'Si se abrió tu programa de correo con el mensaje escrito, solo falta pulsar «Enviar». Si no se abrió, escríbeme directamente a '
    },
    en: {
      saludo: 'Hi Henry,', vacio: '(No message)', sin: 'Not specified',
      que: 'What I need: ', nombre: 'Name: ', contacto: 'How to reach me: ', negocio: 'Company: ',
      estado: 'If your email app opened with the message ready, just press "Send". If it did not open, write to me directly at '
    }
  };
  document.querySelectorAll('form.formulario').forEach(function (form) {
    var T = TEXTOS[form.dataset.idioma] || TEXTOS.es;
    var estado = form.querySelector('.estado');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!form.reportValidity()) return;
      var d = new FormData(form);
      var que = d.get('necesito') || T.sin;
      var nombre = (d.get('nombre') || '').trim();
      var contacto = (d.get('contacto') || '').trim();
      var negocio = (d.get('negocio') || '').trim();
      var mensaje = (d.get('mensaje') || '').trim();
      var asunto = que + ' – ' + (negocio || nombre) + ' (' + (form.dataset.asunto || 'hbtdata.es') + ')';
      var cuerpo = [
        T.saludo, '', mensaje || T.vacio, '', '—',
        T.que + que, T.nombre + nombre, T.contacto + contacto,
        negocio ? T.negocio + negocio : null
      ].filter(function (l) { return l !== null; }).join('\n');
      var url = 'mailto:' + form.dataset.correo + '?subject=' + encodeURIComponent(asunto) + '&body=' + encodeURIComponent(cuerpo);
      (window.hbtAbrirCorreo || function (u) { window.location.href = u; })(url);   // el hueco sirve para probarlo
      if (estado) {
        estado.hidden = false;
        estado.innerHTML = T.estado + '<a href="mailto:' + form.dataset.correo + '">' + form.dataset.correo + '</a>.';
      }
    });
  });
})();
