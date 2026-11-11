// Direkt am Ding (umbauplan-ux.md Schritt 4). Nur zusätzlich: Ohne JavaScript gehen dieselben Wege über „···“, die
// Masken und den Abschnitt „Deine Dateien“. Kein fetch: Die Formulare gehen wie sonst per POST an den Server.
(function () {
  "use strict";
  document.documentElement.classList.add("mit-js");

  // --- Titel anklicken, umbenennen (Enter speichert, Esc bricht ab) ---------------------------------------------
  // _direkt.html: <h1 data-direkt-titel> gefolgt von <form class="direkt-form" hidden>.
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
  });

  // --- Datei wählen, dann Name, Regel und Knopf (form[data-datei-zeile], Ergebnis: eigene Fassung im „···“) ------
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

  // --- Datei ablegen: „Datei“ im „+“ oder Datei auf die Seite ziehen ---------------------------------------------
  var ablage = document.querySelector("form.ablage-form");
  if (!ablage) { return; }
  var eingabe = ablage.querySelector("input[type=file]");
  var abschnitt = ablage.closest("section");
  var anzeige = ablage.querySelector(".ablage-gewaehlt");
  function gewaehlt() {
    var namen = Array.prototype.map.call(eingabe.files, function (d) { return d.name; });
    anzeige.textContent = namen.join(", ");
    ablage.classList.toggle("datei-da", namen.length > 0);
    abschnitt.classList.toggle("ablage-offen", namen.length > 0);
    if (namen.length) {
      abschnitt.scrollIntoView({ block: "nearest" });
      ablage.querySelector("button[type=submit]").focus();
    }
  }
  eingabe.addEventListener("change", gewaehlt);
  ablage.querySelector(".ablage-ab").addEventListener("click", function () {
    eingabe.value = "";
    gewaehlt();
  });
  // „Datei“ im „+“: gleich die Auswahl öffnen statt zum Abschnitt springen
  document.querySelectorAll('a[href="#ablage"]').forEach(function (link) {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      var menue = link.closest("details");
      if (menue) { menue.open = false; }
      // sichtbar machen: manche Browser öffnen die Auswahl nur für sichtbare Felder; bricht Lia ab, steht der
      // Abschnitt da wie ohne JavaScript
      abschnitt.classList.add("ablage-offen");
      eingabe.click();
    });
  });
  // Datei auf die Seite ziehen. Nur Dateien: Das Ziehen von Stunden (ziehen.js) bleibt unberührt.
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
    if (!e.dataTransfer.files.length) { return; }
    try {
      eingabe.files = e.dataTransfer.files;
    } catch (fehler) {  // sehr alte Browser: dann wie ohne JavaScript über „+ Datei ablegen“
      abschnitt.classList.add("ablage-offen");
      return;
    }
    gewaehlt();
  });
}());
