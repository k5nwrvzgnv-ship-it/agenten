// Rückmeldung auf der Dokument-Seite (vorlagen/dokument.html, umbauplan-ux.md Schritt 5): Name der angehängten Datei
// zeigen (#anhang, #gewaehlt), Strg/Cmd+Enter sendet. Das Stück aus shared/webapp/statisch/gespraech.js.
(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    var anhang = document.getElementById('anhang');
    var gewaehlt = document.getElementById('gewaehlt');
    var text = document.getElementById('rueck-text');
    if (anhang && gewaehlt) {
      var zeigen = function () {
        var namen = Array.prototype.map.call(anhang.files, function (f) { return f.name; });
        gewaehlt.textContent = namen.length ? 'Dabei: ' + namen.join(', ') : '';
      };
      anhang.addEventListener('change', zeigen);
      zeigen();  // Zurück im Browser: eine gewählte Datei kann noch im Feld stehen
    }
    if (text) {
      text.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey) && text.form) { ev.preventDefault(); text.form.requestSubmit(); }
      });
    }
  });
})();
