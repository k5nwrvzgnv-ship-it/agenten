// Gespräch (oberflaeche/gespraech.html): Bausteine kopieren, Eingabefeld wächst mit, gewählte Anhänge zeigen,
// Strg/Cmd+Enter sendet, nach dem Laden ans Ende scrollen. Ohne dieses Skript geht alles außer Kopieren.
(function () {
  'use strict';

  function kopieren(knopf) {
    var text = knopf.getAttribute('data-kopie') || '';
    var fertig = function () {
      var alt = knopf.textContent;
      knopf.textContent = 'Kopiert';
      setTimeout(function () { knopf.textContent = alt; }, 1500);
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(fertig, function () { knopf.textContent = 'Kopieren ging nicht'; });
      return;
    }
    var feld = document.createElement('textarea');  // Ersatz ohne HTTPS
    feld.value = text;
    feld.setAttribute('readonly', '');
    feld.style.position = 'absolute';
    feld.style.left = '-9999px';
    document.body.appendChild(feld);
    feld.select();
    try { document.execCommand('copy'); fertig(); } catch (e) { knopf.textContent = 'Kopieren ging nicht'; }
    document.body.removeChild(feld);
  }

  document.addEventListener('click', function (ev) {
    var knopf = ev.target.closest('[data-kopie]');
    if (knopf) { ev.preventDefault(); kopieren(knopf); }
  });

  function wachsen(feld) {
    feld.style.height = 'auto';
    feld.style.height = Math.min(feld.scrollHeight + 2, window.innerHeight * 0.6) + 'px';
  }

  document.addEventListener('DOMContentLoaded', function () {
    var text = document.getElementById('text');
    var anhang = document.getElementById('anhang');
    var gewaehlt = document.getElementById('gewaehlt');
    if (text) {
      text.addEventListener('input', function () { wachsen(text); });
      text.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey) && text.form) { ev.preventDefault(); text.form.requestSubmit(); }
      });
    }
    if (anhang && gewaehlt) {
      anhang.addEventListener('change', function () {
        var namen = Array.prototype.map.call(anhang.files, function (f) { return f.name; });
        gewaehlt.textContent = namen.length ? 'Dabei: ' + namen.join(', ') : '';
      });
    }
    // Antwort da (Verlauf ohne hx-get): Eingabe wieder frei, ans Ende
    document.body.addEventListener('htmx:afterSwap', function () {
      var v = document.getElementById('verlauf');
      if (v && !v.hasAttribute('hx-get')) {
        document.querySelectorAll('#eingabe [disabled]').forEach(function (el) { el.disabled = false; });
        var e = document.getElementById('ende');
        if (e) e.scrollIntoView({ block: 'end' });
      }
    });
    var ende = document.getElementById('ende');
    if (ende && !location.hash.match(/fehler|sonder/)) ende.scrollIntoView({ block: 'end' });
  });
})();
