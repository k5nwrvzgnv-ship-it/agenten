// Direkt am Ding (umbauplan-ux.md Schritt 3; nach shared/webapp/statisch/direkt.js). Nur zusätzlich: Ohne JavaScript
// gehen dieselben Wege über „···“ und die Dateifelder. Kein fetch: Die Formulare gehen wie sonst per POST an den Server.
(function () {
  "use strict";
  document.documentElement.classList.add("mit-js");

  // --- Titel anklicken, umbenennen (Enter speichert, Esc bricht ab) ---------------------------------------------
  // _direkt.html: <h1 data-direkt-titel> gefolgt von <form class="direkt-form" hidden>. data-direkt-offen: gleich offen
  // (eine eben angelegte „Neue Seite“).
  document.querySelectorAll("[data-direkt-titel]").forEach(function (titel) {
    var form = titel.nextElementSibling;
    if (!form || !form.classList.contains("direkt-form")) { return; }
    var feld = form.querySelector(".direkt-feld");
    var anfang = feld.value;
    titel.tabIndex = 0;
    titel.setAttribute("role", "button");
    titel.title = "Zum Umbenennen anklicken";
    function oeffnen() {
      titel.hidden = true;
      form.hidden = false;
      feld.focus();
      feld.select();
    }
    function schliessen() {
      feld.value = anfang;
      form.hidden = true;
      titel.hidden = false;
      titel.focus();
    }
    titel.addEventListener("click", oeffnen);
    titel.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); oeffnen(); }
    });
    feld.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { e.preventDefault(); schliessen(); }
    });
    form.querySelector("[data-direkt-ab]").addEventListener("click", schliessen);
    // Woanders hingeklickt, ohne etwas zu ändern: wieder der Titel
    form.addEventListener("focusout", function (e) {
      if (!form.contains(e.relatedTarget) && feld.value === anfang) { schliessen(); }
    });
    if (titel.hasAttribute("data-direkt-offen")) { oeffnen(); }
  });

  // --- Datei wählen, dann Name, Regel und Knopf (form[data-datei-zeile], Dokument: eigene Fassung im „···“) ------
  document.querySelectorAll("form[data-datei-zeile]").forEach(function (form) {
    var wahl = form.querySelector("input[type=file]");
    var name = form.querySelector(".datei-zeile-name");
    function gewaehlt() {
      var namen = Array.prototype.map.call(wahl.files, function (d) { return d.name; });
      name.textContent = namen.join(", ");
      form.classList.toggle("datei-da", namen.length > 0);
      if (namen.length) { form.querySelector("button[type=submit]").focus(); }
    }
    wahl.addEventListener("change", gewaehlt);
    form.querySelector(".datei-zeile-ab").addEventListener("click", function () {
      wahl.value = "";
      gewaehlt();
    });
    gewaehlt();  // Zurück im Browser: eine gewählte Datei kann noch im Feld stehen
  });

  // --- Ablage am Ort (form.ablage-form): „Datei“ im „+“ öffnet gleich die Auswahl -------------------------------
  var ablage = document.querySelector("form.ablage-form");
  if (ablage) {
    var eingabe = ablage.querySelector("input[type=file]");
    var abschnitt = ablage.closest("section");
    var anzeige = ablage.querySelector(".ablage-gewaehlt");
    var gewaehlt = function () {
      var namen = Array.prototype.map.call(eingabe.files, function (d) { return d.name; });
      anzeige.textContent = namen.join(", ");
      ablage.classList.toggle("datei-da", namen.length > 0);
      abschnitt.classList.toggle("ablage-offen", namen.length > 0);
      if (namen.length) {
        abschnitt.scrollIntoView({ block: "nearest" });
        ablage.querySelector("button[type=submit]").focus();
      }
    };
    eingabe.addEventListener("change", gewaehlt);
    ablage.querySelector(".ablage-ab").addEventListener("click", function () {
      eingabe.value = "";
      gewaehlt();
    });
    document.querySelectorAll('a[href="#ablage"]').forEach(function (link) {
      link.addEventListener("click", function (e) {
        e.preventDefault();
        var menue = link.closest("details");
        if (menue) { menue.open = false; }
        // sichtbar machen: manche Browser öffnen die Auswahl nur für sichtbare Felder; bricht Jan ab, steht der
        // Abschnitt da wie ohne JavaScript
        abschnitt.classList.add("ablage-offen");
        eingabe.click();
      });
    });
  }

  // --- Datei auf die Seite ziehen: landet im Dateifeld mit data-ablegen (Ort: Ablage, Formular: Material, Dokument:
  // Anhang der Rückmeldung). Das Feld meldet „change“, die Seite zeigt den Namen wie nach der Auswahl. -------------
  var ziel = document.querySelector("input[type=file][data-ablegen]");
  if (!ziel) { return; }
  var tiefe = 0;
  function mitDateien(e) {
    return e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types || [], "Files") >= 0;
  }
  function markieren(an) { document.body.classList.toggle("datei-ueber", an); }
  document.addEventListener("dragenter", function (e) {
    if (!mitDateien(e)) { return; }
    tiefe += 1;
    markieren(true);
  });
  document.addEventListener("dragleave", function (e) {
    if (!mitDateien(e)) { return; }
    tiefe = Math.max(0, tiefe - 1);
    if (!tiefe) { markieren(false); }
  });
  document.addEventListener("dragover", function (e) {
    if (!mitDateien(e)) { return; }
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  });
  document.addEventListener("drop", function (e) {
    if (!mitDateien(e)) { return; }
    e.preventDefault();
    tiefe = 0;
    markieren(false);
    var neu = e.dataTransfer.files;
    if (!neu.length) { return; }
    try {
      if (ziel.multiple && ziel.files.length && window.DataTransfer) {
        // schon gewählte Dateien behalten, die gezogenen dazu
        var sammel = new DataTransfer();
        Array.prototype.forEach.call(ziel.files, function (d) { sammel.items.add(d); });
        Array.prototype.forEach.call(neu, function (d) { sammel.items.add(d); });
        ziel.files = sammel.files;
      } else if (ziel.multiple) {
        ziel.files = neu;
      } else {
        var eine = new DataTransfer();
        eine.items.add(neu[0]);
        ziel.files = eine.files;
      }
    } catch (fehler) {  // sehr alte Browser: dann wie ohne JavaScript über das Dateifeld
      ziel.focus();
      return;
    }
    ziel.dispatchEvent(new Event("change", { bubbles: true }));
  });
}());
