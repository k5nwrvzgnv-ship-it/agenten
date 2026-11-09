# Plan: Skizze „Gespräch“ ruhiger, mit Dokumentvorschau (UI-Überarbeitung über Nacht)

Stand 10.11.2026. Nur Plan, an der Skizze ist nichts geändert. Gilt für `skizzen/gespraech.html`
(veröffentlicht als https://claude.ai/artifact/FcDwRi58HWDJX2TkVu2BEC). Echte Web-App und `webapp.service` bleiben
unberührt.

Anlass, Jan 10.11.2026 (sinngemäß): „Im Prinzip okay, aber die Nutzerfreundlichkeit ist nicht gegeben. Teilweise
zu viele Informationen direkt in your face. Dokumente sollten immer als Vorschau angezeigt werden können. Modernist
ist vielleicht zu überbordend. Orientierung an Notion, mindestens bei Schriftgrößen und Informationsdichte pro
Ansicht.“

Was bleibt: Variante A (Gespräch in der Mitte), Baum links, Gespräche und Material hängen an genau einer Ebene
(Klasse/Kurs, Reihe, Stunde, „ohne Ort“), „hier“ und „darunter“, alle klickbaren Abläufe der Skizze, Lückenliste als
Teil 1, Rot nur für „wartet auf dich“. Die Testaufgaben in `STATUS.md` müssen weiter lösbar sein (siehe 4, Regel R4).

---

## 1. Befund: wo die Skizze zu dicht oder zu laut ist

Zeilen beziehen sich auf `skizzen/gespraech.html` im Stand von Commit 6ae6d22.

### Überall
- **Dicke schwarze Rahmen** trennen alles: 3 px an Leiste (Z. 32), Baum (46), Titel (72), Gesprächskopf (99),
  rechter Spalte (140), Überlagerung (157), dazu 2 px an jedem Knopf (66), Baustein (118), Eingabe (125).
  Jede Fläche ruft gleich laut.
- **Großbuchstaben mit Sperrung** an neun Stellen (Z. 48, 73, 76, 81, 84, 91, 104, 107, 116): Baumköpfe,
  Augenbrauen, Ebenenmarke, Abschnittstitel, „hier an der Reihe“, Marken in jeder Zeile, Tagestrenner, „DU · 20:14“,
  Tabellenköpfe. Das liest sich wie ständige Etiketten.
- **Schriften**: Inter Tight 800 für Titel mit 40 px (Ebene), 48 px (Lücken), 40 px (Frage-Kasten, Zahlen),
  26 px (Gesprächsname), 28 px (Überlagerung), 22 px (Baumname, rechte Spalte). 13 verschiedene Größen
  (11 bis 48), dazu die Gewichte 700 und 800.
- **Derselbe Pfad viermal** im Gespräch: Brotkrumen (Z. 357), Augenbraue „Gespräch an der Reihe · …“ (446),
  Kette „Hängt an“ rechts (476), Zeile „Kennt: …“ unter der Eingabe (432).
- **Zahlen überall**: Baum „n Gespr. · n Mat.“ an jedem Knoten (341), Abschnittszahl (406), Stundenliste mit
  denselben Zahlen (413), Kette rechts mit Zahlen (478).
- **Material ist nicht klickbar** (`zeileM`, Z. 373, ein `div`). Es gibt keine Vorschau, nur Titel und Stand.

### Ebenen-Ansicht (`ebenenAnsicht`, Z. 389–418), Beispiel Reihe Straftheorien
- Kopf mit fünf Schichten: Ebenenmarke im Kasten, Augenbraue mit Pfad und Stand, Titel 40 px, Reihenfrage,
  drei gleich starke Knöpfe („+ Gespräch“, „+ Datei ablegen“, „+ Neu aus Vorlage“).
- Darunter zwei Spalten Gespräche und Material, jede mit „hier an der Reihe“ und für jede Stunde eine eigene
  Gruppe „darunter: Stunde 2 · Kant: Vergeltung“. Bei Straftheorien sind das auf einen Blick 7 Gruppenüberschriften,
  10 Zeilen, dazu 5 Stunden mit Zahlen. Lange Stundennamen brechen in der halben Breite um.
- Jede Gesprächszeile trägt „öffnen“ als Marke (Z. 371), jede Materialzeile einen Stand in Großbuchstaben, auch
  „final“ und „deine Datei“, die nichts verlangen.
- Klasse 8 zeigt „hier“ leer und alles aus zwei Reihen und fünf Stunden darunter, also die längste Liste.

### Gespräch mit rechter Spalte (`gespraechAnsicht` Z. 444, `rechts` Z. 472)
- Unter dem Eingabefeld acht Bedienelemente auf einmal: „Foto oder Datei“, „Beispielfoto nehmen“, „gründlich“,
  „Im Netz nachsehen“, „Was haben wir bisher?“, „Daraus Auftrag machen“, „Senden“, dazu die Beschriftung
  „Nachricht“ und die Zeile „Kennt“ (Z. 457–467).
- Jede Nachricht hat ein Etikett in Großbuchstaben („DU · 20:14“, „CLAUDE · 20:15“), Tagestrenner ebenso.
- Bausteine mit 2-px-Rahmen, eigener Augenbraue und zwei Rahmenknöpfen; drei Bausteine in Gespräch g1 wirken wie
  drei Formulare im Text.
- Rechte Spalte mit sechs Blöcken untereinander: Überschrift 22 px, Kette im schwarzen Kasten mit Zahlen,
  „An andere Ebene hängen“, Reihenfrage, Gespräche hier und darunter mit Knopf, Material mit zwei Knöpfen und
  Hinweis. Die Spalte ist voller als die Mitte.
- Kopf: Augenbraue, Name 26 px, „Umbenennen“, Knopf „‹ Zur Reihe“, also zweimal Navigation (Krumen und Knopf).

### Baum (`baum`, Z. 336–355)
- Aktueller Ort schwarz gefüllt (Z. 54), Pfad mit Balken links (55): die stärkste Fläche der Seite ist die
  Navigation.
- Zahlen an jedem Knoten, Name „Lias Assistenz“ 22 px 800, Köpfe in Großbuchstaben, zwei ausgegraute
  Archiv-Einträge und zwei ausgegraute Einträge (Vorlagen, Ich) dauerhaft sichtbar.

### Heute (`heute`, Z. 499–504)
- Am ruhigsten, aber Titel 40 px für ein Wort, jede Zeile mit vollem Pfad und Stand in Großbuchstaben,
  „Weiter im Gespräch“ steht vor „Wartet auf dich“, obwohl das Rote zuerst wichtig ist.

### Lückenliste (`seiteLuecken`, Z. 536–547)
- Titel 48 px, Zahlenband mit dreimal 40 px zwischen 3-px-Linien, alle 13 Lücken mit Zahl 22 px, Text, Erklärung,
  „wo“ und Balken, am Ende der Frage-Kasten 40 px mit 3-px-Rahmen. Gleich am Anfang des Tests das Lauteste.

### Überlagerungen (`schicht`, Z. 554–588)
- Titel 28 px 800, fette Beschriftungen, 3-px-Rahmen. Inhaltlich in Ordnung, nur zu laut.

---

## 2. Gestaltungsrichtung (Orientierung an Notion bei Dichte und Typografie)

Nur die Ruhe übernehmen: Schriftgrößen, Gewichte, Abstände, graue Flächen, Hover. Keine Kopie von Notions Marke,
Logo, Symbolen oder Farben eins zu eins, keine Emoji-Symbole vor Seiten.

### Schrift
- Eine Schrift: Inter (400, 500, 600), Inter Tight entfällt. Kein Gewicht über 600, keine Großbuchstaben mit
  Sperrung mehr.
- Skala (px): **12** Metadaten (Zeit, Stand, Zahlen) · **14** Baum, Listen-Unterzeilen, Knöpfe, Tabellen ·
  **16** Fließtext, Nachrichten, Zeilentitel · **20** Abschnittstitel (600) · **32** Seitentitel (600,
  Zeilenhöhe 1.2). Schmal (≤ 760 px): Seitentitel 26. Sechs Größen statt 13.
- Zeilenhöhe 1.5, Textbreite der Mitte bis 720 px (Gespräch bis 760 px, Tabellen dürfen breiter).

### Farben (Variablen in `:root`, hell und dunkel)
- Text `#37352f`-ähnliches warmes Fast-Schwarz, leise `#787774`, sehr leise `#9b9a97`; Linien `#e9e9e7`;
  Fläche für Baum und Bausteine `#f7f7f5`; Hover `rgba(55,53,47,.06)`; ausgewählter Baumknoten
  `rgba(55,53,47,.08)` mit Text 600 (keine schwarze Füllung).
- Ein ruhiger Akzent nur für Fokusring und Hauptknopf „Senden“/„+ Gespräch“ (gedecktes Blau). Rot bleibt allein
  für „wartet auf dich“ und „hat nicht geklappt“, als Punkt plus Wort, nicht als Rahmen.
- Dunkel: gleiche Logik (Text `#e6e6e3`, Fläche `#202020`, Linien `#2f2f2f`).

### Formen und Abstände
- Linien 1 px, nur wo sie gliedern (unter dem Seitenkopf nicht, zwischen Listenzeilen nicht; Gruppen trennt
  Abstand). Ecken 6 px an Knöpfen, Bausteinen, Panels; Überlagerungen 10 px mit weichem Schatten statt Rahmen.
- Abstandsraster 4/8/12/16/24/32/48. Listenzeilen 32–36 px hoch, Abschnitte 32 px auseinander.
- Knöpfe: ein Hauptknopf je Ansicht (gefüllt, Akzent), sonst leise Textknöpfe mit Hover-Fläche. Mindestgröße
  für Finger bleibt 32 px.

### Seitenleiste (Baum)
- 240 px, Fläche `#f7f7f5`, ohne Rahmenlinie (nur Flächenwechsel). Name „Lias Assistenz“ 14 px 600.
- Köpfe „Ethik“, „Darstellendes Spiel“ 12 px leise, normale Schreibung.
- Zahlen nicht mehr dauerhaft: rechts erscheint beim Hover die Zahl, dauerhaft sichtbar nur der rote Punkt bei
  „wartet“ (an Heute und am Ort, wo etwas wartet).
- Archiv unter einem zugeklappten „Archiv“, Vorlagen und Ich unten am Rand, leise.
- Pfeil zum Auf- und Zuklappen an Klasse und Reihe (heute klappt nur die gewählte Reihe auf); Stunden 14 px leise.

### Hover statt Dauerknöpfe, Ausklappen statt Alles
- Zeilenaktionen (Vorschau, Öffnen, Umhängen) erscheinen beim Hover oder Fokus rechts in der Zeile. Auf
  Touch-Geräten (`@media (hover: none)`) bleiben sie sichtbar, sonst findet Lia sie am iPad nicht.
- Weitere Aktionen in einem Menü „···“ (Umbenennen, Was haben wir bisher?, An andere Ebene hängen,
  Neu aus Vorlage). Was eine Testaufgabe braucht, bleibt sichtbar (Regel R4 unten).
- „darunter“ ist zugeklappt mit Zahl („4 Gespräche in den Stunden darunter ▸“); offen, wenn „hier“ leer ist
  (Klasse 8, Kurs 12). Gruppen „Stunde 2 · Kant …“ erst im aufgeklappten Teil, eine Zeile je Gruppe, 14 px leise.

### Was je Ansicht standardmäßig sichtbar ist

| Ansicht | sofort sichtbar | erst auf Klick oder Hover |
|---|---|---|
| Ebene (Reihe, Stunde, Klasse, Kurs) | Krumen 14 px, Titel 32 px, Reihenfrage als graue Notiz, Hauptknopf „+ Gespräch“, leiser Knopf „Datei ablegen“; untereinander (eine Spalte): Gespräche hier, Material hier, Stunden bzw. Reihen | „darunter“ (zugeklappt mit Zahl), „Neu aus Vorlage“ im „···“, Zahlen und Aktionen je Zeile beim Hover, Stand nur bei „wartet“ und „läuft“ |
| Gespräch | Krumen, Name 20 px mit „···“ und leisem „Daraus Auftrag machen“, Nachrichten ohne Etiketten (Lias Text in grauer Blase rechts, Claude ohne Blase), Bausteine als graue Fläche mit „Kopieren“, Eingabe mit „Foto oder Datei“ und „Senden“ | „gründlich“ und „Im Netz nachsehen“ unter „Optionen“, „Beispielfoto“ im Menü von „Foto oder Datei“, „Was haben wir bisher?“ und „Umbenennen“ im „···“, „Kennt …“ als zugeklappte Zeile „Kennt Reihe Straftheorien und 3 Dateien ▸“ |
| Rechte Spalte (Gespräch) | Überschrift „An der Reihe“ 14 px 600, Reihenfrage, Material hier (klickbar, Vorschau), Gespräche hier | Gespräche darunter (zugeklappt), „An andere Ebene hängen“ im „···“; die Kette „Hängt an“ entfällt (die Krumen zeigen sie) |
| Heute | Gruß 32 px, „Wartet auf dich“ zuerst (mit Vorschau), dann „Weiter im Gespräch“ (drei) | Pfad als 12-px-Unterzeile, ältere Gespräche über „Alle Gespräche ▸“ |
| Lückenliste | Titel 32 px, ein Satz, drei Zahlen in einer ruhigen Zeile (20 px 600), die 7 Lücken „in der Skizze“, die Frage „Stimmt das? Was fehlt?“ als graue Notiz 20 px | die übrigen 6 Lücken („Weitere anzeigen ▸“), Erklärsatz je Lücke beim Aufklappen, Balken dünn und grau |
| Überlagerungen | Titel 20 px 600, Felder, ein Hauptknopf | — |

### Skizzen-Leiste oben
- Bleibt, aber leise: 40 px hoch, gelbe Fläche nur als schmaler Streifen, Reiter „1 Was fehlt“ und „2 So könnte es
  aussehen“ als Textreiter mit Unterstrich, Hinweis 12 px, „Skizze zurücksetzen“ leise rechts.

---

## 3. Dokumentvorschau

Jedes Material, jede eigene Datei und jedes Foto im Gespräch lässt sich als Vorschau öffnen.

### Zwei Stufen, wie Notions Seitenblick und die echte App
1. **Seitenpanel** (Klick auf eine Material-Zeile, egal wo: Ebene, rechte Spalte, Heute, Anhang im Gespräch):
   rechts klappt ein Panel von ca. 480 px auf (über der rechten Spalte bzw. rechts über der Mitte, mit „×“ und
   Esc). Inhalt: Titel, eine Zeile „Präsentation · 8 Seiten · Fassung 2“ und Stand (rot nur bei „wartet“),
   erste Seite groß, darunter die übrigen Seiten als kleine Bilder, „‹ ›“ zum Blättern, Seitenzahl.
   Knöpfe: Hauptknopf je nach Stand („Rückmeldung geben“ bei „wartet“, sonst „Darüber sprechen“), leise „Groß
   ansehen“, „In Word/PowerPoint öffnen“ (in der Skizze ohne Wirkung, Hinweis im Band).
2. **Groß ansehen**: Überlagerung über die ganze Seite, eine Seite so groß, wie das Fenster erlaubt, Pfeiltasten
   und Klick aufs Bild blättern, Esc schließt. Entspricht dem Seiten-Betrachter der echten App.
- Unter 760 px öffnet das Panel als ganze Seite.
- „Darüber sprechen“ öffnet ein neues Gespräch an derselben Ebene mit der Datei als Anhang (Plan
  `docs/gespraech-plan.md` 1 b).

### Gezeichnete Beispielseiten (Skizze)
- Keine echten Dateien und keine echten Inhalte. Eine Funktion zeichnet Seiten als SVG nach Art des Materials:
  - Arbeitsblatt / Reihenentwurf / Fallsammlung (Word, A4 hoch): Kopfzeile mit Titel, graue Textbalken,
    Aufgabenkästen, Tabelle beim Reihenentwurf.
  - Präsentation (PowerPoint, 16:9): Titelfolie mit echtem Material-Titel, Folien mit Überschrift und Punkten.
  - PDF-Buchseite (eigene Datei „Leben leben 2“): zwei Spalten graue Zeilen, ein Bildkasten.
  - Notentabelle / Bewertung (Excel bzw. Word): Raster ohne Namen und ohne Zahlen.
  - Foto (Planung.heic, eigenes hochgeladenes Bild): das Bild selbst.
  - Neu abgelegte Beispieldatei „Bewertungskriterien.pdf“: eine Seite mit Kriterienliste in grauen Balken.
- Jedes Material bekommt in `frische()` die Felder `art` und `seiten` (z. B. Präsentation Kant 8, Reihenentwurf 3).
  Titelzeile auf der Seite trägt den echten Material-Titel, sonst nur graue Balken: nichts wirkt wie ein fertiger
  Inhalt, den Lia für echt halten könnte.

### Bezug zur echten App
- Die Ergebnisansicht `/ergebnis/<id>` zeigt heute schon Karten mit der ersten Seite klein und „n Seiten ·
  ansehen“, der Betrachter `/ergebnis/<id>/datei/<n>/ansehen?seite=m` eine Seite groß, ohne JavaScript, aus
  `<stem>-vorschau/<stem>-seite-NN.png` des Renderers. Das Panel der Skizze nutzt dieselbe Logik (erste Seite,
  Seitenzahlen, Blättern) und dieselben Wörter.
- Lücke für später (nicht in diesem Plan, Bedarf an den Renderer-Chat bzw. Hauptordner): Eigene Dateien, die Lia
  hochlädt, haben heute keine Seitenbilder; Material aus dem Renderer schon, das Dossier-PDF der Recherche nicht.
  Für „immer eine Vorschau“ in der echten App braucht es Seitenbilder auch für hochgeladene Word/PDF/PowerPoint.
  Ein Seitenpanel in der echten App bräuchte JavaScript; heute ist der Betrachter bewusst ohne.

---

## 4. Ablauf über Nacht

### Wer macht es
**Ein Chat im Ordner `shared/webapp`, am Stück, ohne unbeaufsichtigten Lauf.** Begründung: Es ist eine einzige
Datei, die Schritte bauen aufeinander auf, das Veröffentlichen unter derselben URL geht nur über das
Artifact-Werkzeug des Chats, und ein `claude -p`-Lauf mit Schreibrechten auf Code widerspräche „Claude denkt,
Python handelt“. Geschätzt 2 bis 4 Stunden.
- Jan startet den Chat abends mit dem Auftrag „Arbeite `shared/webapp/ui-plan-notion.md` Abschnitt 4 Schritt für
  Schritt ab, ohne Rückfragen; bei einer echten Unklarheit Schritt auslassen, in STATUS notieren, weitermachen“.
- Der Rechner, auf dem die Claude-App läuft, muss wach bleiben (die App kann das Wachhalten anfordern). Läuft der
  Chat auf dem Server ohne Jans Rechner, wäre das ein unbeaufsichtigter Lauf (etwa `claude` in `tmux` oder
  `systemd-run --user`): nur mit Jans ausdrücklicher Freigabe, nicht empfohlen.

### Regeln für den Lauf
- R1 Nur `skizzen/gespraech.html`, neu `skizzen/probelauf.js` und am Ende `STATUS.md` ändern. Nichts an `app.py`,
  `vorlagen/`, `statisch/`, `webapp.service`.
- R2 Reines HTML/JS wie bisher, keine Bibliotheken; Schrift weiter von Google Fonts (nur Inter).
- R3 Nach jedem Schritt: prüfen (unten), veröffentlichen, committen. Schlägt eine Prüfung fehl, erst reparieren,
  sonst den Schritt zurücknehmen (`git checkout -- skizzen/gespraech.html`, nur diese Datei) und in STATUS notieren.
- R4 Testaufgaben 1–6 in `STATUS.md` bleiben lösbar: sichtbar bleiben „Weiter im Gespräch“ (Heute), „Als
  Reihenfrage übernehmen“ und „Kopieren“ an Bausteinen, „Foto oder Datei“, „Daraus Auftrag machen“, „+ Gespräch“,
  „Datei ablegen“, „Gespräche ohne Ort“ im Baum. Ändert sich ein Wort oder der erste Klick, wird die Tabelle in
  STATUS angepasst.
- R5 Rot nur bei „wartet“. Keine neuen Inhalte, Namen oder Zitate aus Lias Chats.
- R6 `./pruefen.sh` nie parallel; es läuft nur über den Hook von `commit.sh` (Sperre).

### Prüfung je Schritt
1. **Syntax**: Skript aus der HTML ziehen und `node --check` darauf.
2. **Probelauf ohne Browser** (`node skizzen/probelauf.js`, entsteht in Schritt 0, ohne Pakete): kleines
   Ersatz-DOM, lädt das Skript, ruft jede Ansicht auf (beide Teile, jede Ebene, jedes Gespräch, Heute, jede
   Überlagerung, ab Schritt 5 jede Vorschau mit jeder Seite) und prüft: kein Fehler, keine leere Ansicht, jede
   Testaufgabe hat ihr Bedienelement, neues Gespräch hängt an der aktuellen Ebene, Rot nur an „wartet“. Dazu eine
   **Dichte-Zählung** je Ansicht: sichtbare Bedienelemente, Zeilen, verschiedene Schriftgrößen im CSS. Schritt 0
   hält die Ausgangswerte fest; Ziel am Ende etwa die Hälfte der sofort sichtbaren Elemente je Ansicht und
   höchstens sechs Schriftgrößen.
3. **Vorschau**: auf dem Server gibt es keinen Browser. Darum nach jedem sichtbaren Schritt veröffentlichen unter
   https://claude.ai/artifact/FcDwRi58HWDJX2TkVu2BEC (bleibt privat, ältere Fassungen bleiben in der Versionsliste).
   Ist Claude in Chrome verbunden, je ein Bildschirmfoto von Ebene, Gespräch, Vorschau; sonst sieht Jan morgens nach.
4. **Commit** mit `~/agenten/commit.sh "webapp: Skizze UI Schritt n: …" shared/webapp/skizzen/gespraech.html`
   (ab Schritt 0 auch `shared/webapp/skizzen/probelauf.js`).

### Schritte

| # | Was geändert wird | Fertig, wenn |
|---|---|---|
| 0 | `skizzen/probelauf.js` anlegen, Ausgangswerte der Dichte festhalten (in die Commit-Nachricht und STATUS). Skizze unverändert. | Probelauf läuft grün auf dem heutigen Stand. |
| 1 | Grundlagen nur im CSS: Variablen (Farben hell/dunkel), Schriftskala 12/14/16/20/32, Gewichte bis 600, Inter Tight raus, Linien 1 px, Ecken, Knopfformen (Haupt, leise), Großbuchstaben-Sperrung raus, Skizzen-Leiste leise. | Keine 3-px-Linie und kein `text-transform: uppercase` mehr; Probelauf grün; veröffentlicht. |
| 2 | Seitenleiste: Flächenwechsel statt Linie, Auswahl grau statt schwarz, Zahlen nur beim Hover, roter Punkt bei „wartet“, Auf/Zu-Pfeile an Klasse und Reihe, Archiv zugeklappt, Vorlagen und Ich unten. | Baum zeigt dauerhaft keine Zahlen außer Rot; jede Ebene erreichbar. |
| 3 | Ebenen-Ansicht: eine Spalte, Kopf mit Krumen + Titel + Reihenfrage-Notiz + „+ Gespräch“ + „Datei ablegen“ + „···“; „darunter“ zugeklappt mit Zahl (offen, wenn „hier“ leer); Zeilen ohne „öffnen“-Marke, Stand nur bei wartet/läuft; Zeilenaktionen beim Hover, auf Touch sichtbar; Material-Zeilen werden Knöpfe (öffnen vorerst nur das Band „Vorschau kommt in Schritt 5“). | Straftheorien zeigt sofort höchstens 3 Abschnitte und keine Gruppenüberschrift „darunter“; Klasse 8 zeigt „darunter“ offen. |
| 4 | Gespräch und rechte Spalte: Nachrichten ohne Etiketten, Tagestrenner leise, Bausteine als graue Fläche mit leisem „Kopieren“ und „Als Reihenfrage übernehmen“; Eingabe nur „Foto oder Datei“ (Menü mit Beispielfoto) + „Optionen“ + „Senden“; Kopf mit Name, „Daraus Auftrag machen“, „···“ (Umbenennen, Was haben wir bisher?, An andere Ebene hängen); „Kennt“ zugeklappt; rechte Spalte ohne Kette, darunter zugeklappt. | Unter der Eingabe höchstens 3 Bedienelemente; Testaufgaben 1, 2, 3, 5 im Probelauf erfüllt. |
| 5 | Dokumentvorschau: `art` und `seiten` je Material, SVG-Seiten nach Art, Seitenpanel (480 px, Esc, ×), „Groß ansehen“ als Überlagerung mit Pfeiltasten, Aufruf aus Ebene, rechter Spalte, Heute, Anhängen im Gespräch und neu abgelegter Datei; „Darüber sprechen“, „Rückmeldung geben“ (nur Band). | Jedes Material und jede eigene Datei öffnet eine Vorschau mit Seitenzahl; Fokus kehrt nach dem Schließen zur Zeile zurück. |
| 6 | Heute (Wartet zuerst, mit Vorschau), Lückenliste (7 sichtbar, Rest aufklappbar, Frage als Notiz 20 px, Zahlen 20 px), Überlagerungen (20 px, Schatten, Ecken). | Lückenliste ohne Schrift über 32 px; Heute zeigt Rot nur an den drei wartenden Materialien. |
| 7 | Schmal (≤ 760 px, ≤ 1100 px) und dunkel durchgehen, Fokusreihenfolge und `:focus-visible`, Hover-Aktionen per Tastatur erreichbar; STATUS-Abschnitt „Skizze“ auf den neuen Stand (was gebaut, Dichte vorher/nachher, was nicht im Browser gesehen), Testaufgaben-Tabelle prüfen. Commit mit `skizzen/gespraech.html`, `skizzen/probelauf.js`, `STATUS.md`. | Probelauf grün, letzte Fassung veröffentlicht, STATUS committet. |

Was der Lauf nicht kann: Er sieht die Seite nicht selbst im Browser (außer über Claude in Chrome, falls verbunden).
Hover, Animation und Abstände sind deshalb morgens von Jan einmal durchzuklicken, bevor Lia sie sieht.

---

## 5. Offene Fragen an Jan

1. **Gilt die Richtung später auch für die echte Web-App?** Modernist mit drei Spalten war deine Wahl vom
   04.11., und es gibt dort einen Test, der die Schriftgrößen 12 bis 64 festhält. Vorschlag: erst nur die Skizze,
   nach Lias Test entscheiden.
2. **Rechte Spalte im Gespräch standardmäßig offen (schmal, wie geplant) oder zu, mit Knopf „An der Reihe“?**
   Vorschlag: offen, weil Testaufgabe 1 die neue Reihenfrage dort zeigt.
3. **Nachtlauf als Chat am Stück** (dein Rechner bleibt wach) **oder unbeaufsichtigt auf dem Server** (braucht
   deine Freigabe)? Vorschlag: Chat am Stück.
