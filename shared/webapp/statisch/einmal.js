// Formular mit data-einmal: Knopf nach dem ersten Absenden sperren (Doppelklick, Befund 03.11. Punkt 1). Nur zusätzlich:
// Ohne JavaScript verwirft der Server die zweite gleiche Anfrage.
(function () {
  "use strict";
  function knoepfe(form) {
    return form.querySelectorAll("button[type=submit]");
  }
  document.addEventListener("submit", function (e) {
    if (!e.target.hasAttribute("data-einmal")) { return; }
    knoepfe(e.target).forEach(function (k) { k.disabled = true; });
  });
  // Zurück im Browser zeigt die Seite evtl. aus dem Speicher: Knopf wieder frei, sonst bleibt er tot
  window.addEventListener("pageshow", function () {
    document.querySelectorAll("form[data-einmal]").forEach(function (f) {
      knoepfe(f).forEach(function (k) { k.disabled = false; });
    });
  });
}());
