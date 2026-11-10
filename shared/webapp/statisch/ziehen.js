// Stunden in der Reihe per Ziehen verschieben (Strukturplan 2a, Grundsatz Flexibilität). Nur zusätzlich: Das Skript
// füllt das Formular „Verschieben: … nach …“ der Seite (im „···“, id verschieben) und schickt es ab; ohne JavaScript
// geht derselbe Weg dort per Knopf. Maus: HTML-Ziehen. Finger (iPad, umbauplan-ux.md Schritt 4): kurz halten, dann
// ziehen; wer nur wischt, scrollt wie immer.
(function () {
  "use strict";
  var liste = document.querySelector(".stunden-liste");
  var form = document.getElementById("verschieben");
  if (!liste || !form) { return; }

  // Stunde „gezogen“ vor bzw. hinter li ablegen (y: Höhe des Zeigers). Bleibt sie, wo sie ist, passiert nichts.
  function ablegen(gezogen, li, y) {
    var rand = li.getBoundingClientRect();
    var davor = y < rand.top + rand.height / 2;
    var ziel = davor ? li : li.nextElementSibling;
    while (ziel && ziel.getAttribute("data-stunde") === gezogen) { ziel = ziel.nextElementSibling; }
    var wert = ziel ? "vor:" + ziel.getAttribute("data-stunde") : "ende";
    var vorher = li.parentNode.querySelector('li[data-stunde="' + gezogen + '"]');
    var nachher = vorher ? vorher.nextElementSibling : null;
    if (li.getAttribute("data-stunde") === gezogen ||
        (nachher && ziel === nachher) || (!nachher && !ziel)) { return; }  // bleibt, wo sie ist
    form.querySelector("[name=stunde]").value = gezogen;
    form.querySelector("[name=ziel]").value = wert;
    form.submit();
  }

  // --- Maus -----------------------------------------------------------------------------------------------------
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
    var id = gezogen;
    gezogen = null;
    ablegen(id, li, e.clientY);
  });

  // --- Finger ---------------------------------------------------------------------------------------------------
  var HALTEN_MS = 450;
  var WACKELN_PX = 8;
  var uhr = null;
  var finger = null;  // li, das gerade am Finger hängt
  var start = null;
  var markiert = null;

  function markieren(li, y) {
    if (markiert) { markiert.classList.remove("ziel-davor", "ziel-danach"); }
    markiert = li && li !== finger ? li : null;
    if (!markiert) { return; }
    var rand = markiert.getBoundingClientRect();
    markiert.classList.add(y < rand.top + rand.height / 2 ? "ziel-davor" : "ziel-danach");
  }
  function unterFinger(t) {
    var el = document.elementFromPoint(t.clientX, t.clientY);
    var li = el && el.closest("li[data-stunde]");
    return li && liste.contains(li) ? li : null;
  }
  function aufhoeren() {
    window.clearTimeout(uhr);
    uhr = null;
    if (finger) { finger.classList.remove("wird-gezogen"); }
    markieren(null, 0);
    liste.classList.remove("finger-zieht");
    finger = null;
  }

  liste.addEventListener("touchstart", function (e) {
    var li = e.target.closest('li[data-stunde][draggable="true"]');
    if (!li || e.touches.length !== 1) { return; }
    start = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    uhr = window.setTimeout(function () {
      finger = li;
      li.classList.add("wird-gezogen");
      liste.classList.add("finger-zieht");
      if (navigator.vibrate) { navigator.vibrate(10); }
    }, HALTEN_MS);
  }, { passive: true });

  liste.addEventListener("touchmove", function (e) {
    var t = e.touches[0];
    if (!finger) {  // vor Ablauf bewegt: Lia scrollt, kein Ziehen
      if (uhr && (Math.abs(t.clientX - start.x) > WACKELN_PX || Math.abs(t.clientY - start.y) > WACKELN_PX)) {
        window.clearTimeout(uhr);
        uhr = null;
      }
      return;
    }
    e.preventDefault();  // nicht scrollen, solange eine Stunde am Finger hängt
    markieren(unterFinger(t), t.clientY);
  }, { passive: false });

  liste.addEventListener("touchend", function (e) {
    if (!finger) { aufhoeren(); return; }
    e.preventDefault();  // kein Klick auf den Link der Stunde
    var t = e.changedTouches[0];
    var id = finger.getAttribute("data-stunde");
    var li = unterFinger(t);
    aufhoeren();
    if (li) { ablegen(id, li, t.clientY); }
  });
  liste.addEventListener("touchcancel", aufhoeren);
}());
