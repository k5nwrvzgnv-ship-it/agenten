// Stunden in der Reihe per Ziehen verschieben (Strukturplan 2a, Grundsatz Flexibilität). Nur zusätzlich: Das Skript
// füllt das Formular „Verschieben: … nach …“ der Seite und schickt es ab; ohne JavaScript geht derselbe Weg per Knopf.
(function () {
  "use strict";
  var liste = document.querySelector(".stunden-liste");
  var form = document.getElementById("verschieben");
  if (!liste || !form) { return; }
  var gezogen = null;
  liste.addEventListener("dragstart", function (e) {
    var li = e.target.closest("li[data-stunde]");
    if (!li) { return; }
    gezogen = li.getAttribute("data-stunde");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", gezogen);
    li.classList.add("wird-gezogen");
  });
  liste.addEventListener("dragend", function (e) {
    var li = e.target.closest("li[data-stunde]");
    if (li) { li.classList.remove("wird-gezogen"); }
  });
  liste.addEventListener("dragover", function (e) {
    if (gezogen && e.target.closest("li[data-stunde]")) { e.preventDefault(); }
  });
  liste.addEventListener("drop", function (e) {
    var li = e.target.closest("li[data-stunde]");
    if (!gezogen || !li) { return; }
    e.preventDefault();
    var rand = li.getBoundingClientRect();
    var davor = e.clientY < rand.top + rand.height / 2;
    var ziel = davor ? li : li.nextElementSibling;
    while (ziel && ziel.getAttribute("data-stunde") === gezogen) { ziel = ziel.nextElementSibling; }
    var wert = ziel ? "vor:" + ziel.getAttribute("data-stunde") : "ende";
    var vorher = li.parentNode.querySelector('li[data-stunde="' + gezogen + '"]');
    var nachher = vorher ? vorher.nextElementSibling : null;
    if (li.getAttribute("data-stunde") === gezogen ||
        (nachher && ziel === nachher) || (!nachher && !ziel)) { gezogen = null; return; }  // bleibt, wo sie ist
    form.querySelector("[name=stunde]").value = gezogen;
    form.querySelector("[name=ziel]").value = wert;
    form.submit();
  });
})();
