// Dokument auf einen Ordner ziehen (Jan 19.11.2026): Zeilen mit data-dokument lassen sich auf Ziele mit data-ordner
// ablegen (Ordner im Baum, Unterordner auf der Seite). Abgelegt schickt die Seite ein normales Formular an
// /dokument/<id>/ort (mit Token aus <meta name="formular-token">); der Server leitet zurück, mit Hinweis und
// Rückgängig. Ohne JavaScript geht dasselbe über „Verschieben nach“ im „···“ des Dokuments.
(function () {
  "use strict";
  var ART = "application/x-arbeitsplatz-dokument";
  var token = document.querySelector('meta[name="formular-token"]');
  if (!token) { return; }
  var gezogen = null;  // manche Browser verraten die Daten erst beim Ablegen, daher hier gemerkt

  function istDokument(e) {
    return gezogen !== null || (e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types || [], ART) >= 0);
  }
  function ziel(e) { return e.target.closest ? e.target.closest("[data-ordner]") : null; }

  document.addEventListener("dragstart", function (e) {
    var zeile = e.target.closest && e.target.closest("[data-dokument]");
    if (!zeile) { return; }
    gezogen = zeile.getAttribute("data-dokument");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData(ART, gezogen);
    document.body.classList.add("dokument-zieht");
    zeile.classList.add("wird-gezogen");
  });
  document.addEventListener("dragend", function () {
    gezogen = null;
    document.body.classList.remove("dokument-zieht");
    Array.prototype.forEach.call(document.querySelectorAll(".wird-gezogen, .ablage-ziel"), function (x) {
      x.classList.remove("wird-gezogen", "ablage-ziel");
    });
  });
  document.addEventListener("dragover", function (e) {
    var z = ziel(e);
    if (!z || !istDokument(e)) { return; }
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    z.classList.add("ablage-ziel");
  });
  document.addEventListener("dragleave", function (e) {
    var z = ziel(e);
    if (z && !z.contains(e.relatedTarget)) { z.classList.remove("ablage-ziel"); }
  });
  document.addEventListener("drop", function (e) {
    var z = ziel(e);
    if (!z || !istDokument(e)) { return; }
    e.preventDefault();
    var id = gezogen || e.dataTransfer.getData(ART);
    if (!id) { return; }
    var form = document.createElement("form");
    form.method = "post";
    form.action = "/dokument/" + encodeURIComponent(id) + "/ort";
    [["token", token.content], ["ort", z.getAttribute("data-ordner")], ["zurueck", location.pathname]]
      .forEach(function (paar) {
        var feld = document.createElement("input");
        feld.type = "hidden";
        feld.name = paar[0];
        feld.value = paar[1];
        form.appendChild(feld);
      });
    document.body.appendChild(form);
    form.submit();
  });
}());
