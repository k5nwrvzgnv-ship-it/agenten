# Umbauplan zum UX-Befund (Vorschlag, wartet auf Jans Freigabe)

Stand 10.11.2026. Grundlage: `befund-ux.md` (fünf Ursachen, fünf Vorschläge, Fundstellen mit Zeilen). Noch nichts
davon gebaut. Gebaut sind nur die zwei Fehler aus „Nebenbei gefunden“ (Meldung „Gespräch gelöscht.“ überall,
Regel-Folgezeilen auf „Ich“).

## Spielregeln für alle Schritte

- Ein Schritt = ein Commit über `~/agenten/commit.sh`, vorher `./pruefen.sh` mit `flock` auf `commit.sperre`.
- `oberflaeche/` und `statisch/` wirken **sofort** auf Lias Dienst (8791), Python erst nach dem Neustart. Fast alle
  Schritte sind nur Vorlagen und CSS. Nach jedem Schritt der Rundgang über alle Seiten gegen 127.0.0.1:8791 (nur
  lesend, alle 200).
- Kein neues Paket. Symbole als eigene kleine Inline-SVGs (ein Makro), kein Symbol-Font, keine Emojis; jedes
  Symbol-Knopf hat `aria-label` und `title`. Die CSP (`'self'`) bleibt.
- Alles bleibt ohne JavaScript bedienbar (Menüs sind `<details>` wie heute in `gespraech.html:18`). Wo JavaScript
  dazukommt (Schritt 7), gibt es den Weg ohne weiter.
- „Beim Überfahren“ gibt es auf dem iPad nicht: Zeilen-··· sind auf Touch-Geräten immer sichtbar
  (`@media (hover: none)`).

## Schritt 0 (empfohlen, vor allem anderen): Probe-Kopie statt live bauen

Weil Vorlagen sofort live sind, sieht Lia heute jeden Zwischenstand. Vorschlag: `app.py` liest zwei optionale
Variablen `WEBAPP_ORDNER_OBERFLAECHE` und `WEBAPP_ORDNER_STATISCH` (ohne Angabe wie heute). Gebaut wird in einer Kopie
unter `data/ux/` (nicht im Repo), die Test-Instanz 8795 zeigt die Kopie, Jan sieht sie per SSH-Tunnel. Nach Jans Okay
kommt der Schritt ins Repo und ist damit live.
- Dateien: `app.py` (Zeilen 177–178), `STATUS.md` (Startbefehl der Probe).
- Lia sieht: nichts. Der Dienst setzt die Variablen nicht; die Änderung wirkt erst beim nächsten Neustart und
  ändert auch dann nichts.
- Tests: `test_app.py` (neuer Test: Variablen gesetzt → Vorlagen und CSS aus dem anderen Ordner).
- Ohne Schritt 0: jeder Schritt direkt live, also klein halten und sofort den Rundgang machen.

## Schritt 1: Leere Abschnitte auf eine Zeile (Vorschlag 4, Ebenen)

- Dateien: `oberflaeche/_ort.html` (neues Makro für eine Abschnittszeile „Titel · Zahl +“; `:23`, `:46` ersetzt),
  `reihe.html` (`:35–42`, `:57`), `stunde.html` (`:10–18`), `klasse.html` (`:39–46`, Termine-Leerfall `:63–67`),
  `statisch/ruhig.css` (eine Klasse für die Zeile).
- Lia sieht danach: Leere Bereiche als je eine Zeile „Gespräche · 0 +“, „Material · 0 +“, „Dateien · 0 +“,
  „Stunden · 0 +“. Die abgeschlossene Reihe „Helfen“ ist vier Zeilen statt fünf Absätze. An der Stunde führt das
  „+“ bei Material direkt zu „Neu“ für diese Stunde; der Satz über den Umweg („Öffne ein Material der Reihe …“)
  entfällt. Im Archiv kein „+“. Abschnitte mit Inhalt bleiben wie heute.
- Tests: `test_app.py` prüft „Noch kein Gespräch hier.“, „Noch nichts zur ganzen Reihe.“, „Noch keine Stunden.“
  (anpassen); `test_pflege_app.py` einmal „Noch keine“; neu: leere Reihe zeigt die Zeilen mit „+“-Links, Archiv ohne.

## Schritt 2: Heute ohne leere Abschnitte (Vorschlag 4, Heute)

- Dateien: `oberflaeche/_heute.html` (`:19–23` Liste der Abschnitte, `:46–56` „Weiter im Gespräch“).
- Lia sieht danach: „Läuft gerade“ und „Weiter im Gespräch“ nur, wenn dort etwas steht. „Wartet auf dich“ ohne
  Inhalt fällt weg, die Begrüßung sagt es schon („Gerade wartet nichts auf dich.“).
- Tests: `test_app.py` („Weiter im Gespräch“, Leertexte von Heute), neu: leere Abschnitte fehlen.
- Nicht in diesem Schritt: „Fertig je Reihe zusammenfassen“. Das ist Python (`logik.heute`, `logik.py:258–313`,
  Tests in `test_logik.py`, Neustart nötig) und betrifft vor allem die drei getrennten Rollentabellen-Aufträge.
  Eigener Schritt 2b nur, wenn Jan das will.

## Schritt 3: ···-Menü und Symbole als Baustein (Vorbereitung für 4, 5, 8, 9)

- Dateien: neu `oberflaeche/_menue.html` (Makro `menue(…)` aus `gespraech.html:18–45` herausgelöst, Makro
  `symbol(name)` mit wenigen Inline-SVGs: plus, mehr, stift, verschieben, archiv, löschen, download, hochladen),
  `gespraech.html` nutzt das Makro, `ruhig.css` (`.symbol`, Menüeinträge mit Symbol).
- Lia sieht danach: Im ···-Menü des Gesprächs steht vor jedem Eintrag ein kleines Symbol; sonst nichts Neues.
- Tests: `test_app.py` (`test_gespraech`: Menütexte bleiben), neu: jeder Symbol-Knopf hat `aria-label`.

## Schritt 4: Reihe mit einem blauen Knopf und ··· (Vorschlag 2)

- Dateien: `basis.html` (`:25`: statt „+ Neu hier“ ein Block für die Kopf-Aktionen der Seite), `reihe.html`
  (`:20–28` Knopfreihe, `:70–79` Verschieben, `:81–83` Termine, `:86–93` Reihe beginnt am → ins ···), `_ort.html:56`
  („+ Gespräch“ wandert in den Kopf), `ruhig.css`.
- Lia sieht danach: Oben rechts neben dem Titel nur „+ Gespräch“ (blau) und „···“. Im ···: Bearbeiten, Termine,
  Stunden verschieben, Reihe beginnt am, In andere Klasse übernehmen, Archivieren. „+ Neu hier“ steht nicht mehr oben,
  sondern als „+“ am Abschnitt Material (aus Schritt 1). Unter den Stunden nur noch „+ Stunde“. Ziehen der Stunden
  geht weiter (`ziehen.js` füllt dasselbe Formular, das dann im Menü steht; im Browser prüfen).
- Tests: `test_app.py:863` (prüft „+ Neu hier“ als blauen Knopf), `test_pflege_app.py` (Verschieben, Bearbeiten,
  „In eine andere Klasse“, „Die Reihe beginnt“: die POST-Wege bleiben, nur HTML-Prüfungen anpassen), neu: genau ein
  `knopf-voll` auf der Reihe.
- Entscheidung für Jan: Welcher Knopf ist blau? Vorschlag „+ Gespräch“ (wie Skizze 2 und Zielbild „Gespräch in der
  Mitte“). Alternative: „+ Neu“ blau, „+ Gespräch“ als Zeile im Abschnitt Gespräche.

## Schritt 5: Stunde und Klasse genauso

- Dateien: `stunde.html` (Bearbeiten-Block `:20–61` ins ···: Thema und Marke, Verschieben, Kopieren, fällt aus,
  Ausblenden, Löschen; „Löschen geht nicht, daran hängt …“ als Satz im Menü), `klasse.html` (`:29–37`: „+ Reihe“
  ins ···, Bearbeiten ins ···; Zusatztermin-Formular `:69–81` ins ··· der Termine), `ruhig.css`.
- Lia sieht danach: Die Stunde ist Titel, Gespräche, Material, Dateien; alles Ändern hinter „···“. Die Klasse hat
  oben „+ Gespräch“ und „···“.
- Tests: `test_pflege_app.py` (Ausblenden, Verschieben aus der Stunde, Ausfall), `test_ordnung.py` nur, wenn HTML
  geprüft wird; neu: genau ein `knopf-voll` auf Stunde und Klasse.

## Schritt 6: Ein Raster mit rechter Spalte für Klasse, Reihe, Stunde (Vorschlag 1)

- Dateien: `basis.html:14` (Rahmen mit rechts auch für Ebenen), `reihe.html`, `stunde.html`, `klasse.html` (Block
  `rechts`: Reihenfrage, Schon behandelt, Dateien, Termine; wie `gespraech.html:76–106`), `ruhig.css:30–35` (Mitte
  ~640 px, rechts 280–300 px; Pflege-Seiten einspaltig und mittig, max. ~640 px), Umbruch unter 1100 px bleibt
  (`ruhig.css:322`).
- Lia sieht danach: Links was sie tut (Gespräche, Stunden bzw. Reihen, Material), rechts der Kontext. Gespräch-Seite
  und Ebenen sehen gleich aus, rechts ist nicht mehr leer. Pflege-Masken stehen mittig.
- Tests: `test_app.py` (Rahmen-Klassen, Reihenfrage auf der Reihe), `test_pflege_app.py` (Termine auf Klasse/Reihe),
  `test_schnell.py` (TestSchnellNeu prüft `ruhig.css`); neu: Ebenen haben `aside.rechts`.
- Nach 4 und 5, weil dann weniger zu verschieben ist.

## Schritt 7: Datei ablegen als ein Vorgang, Regeln im Moment (Vorschlag 3, Dateien)

- Dateien: `_ort.html:25–31`, neu `statisch/ablage.js` (eigener Code: nach der Auswahl Name, Regeln „PDF, Word …
  bis 20 MB. Keine Schülerdaten.“ und Knopf „Ablegen“ zeigen; Ziehen auf die Fläche), `ruhig.css`.
- Lia sieht danach: „+“ bei Dateien öffnet die Auswahl, danach eine Zeile mit Dateiname, Regeln und „Ablegen“. Der
  Regeltext steht nicht mehr dauerhaft da. Ohne JavaScript: wie heute.
- Tests: `test_app.py` (Ablage-POST unverändert; HTML: Regeltext steht im Formular, nicht als dauerhafte Zeile).
  Im Browser prüfen (Auswahl, Ziehen, iPad).

## Schritt 8: Erklärtexte kürzen (Vorschlag 3, Rest)

- Dateien: `_verlauf.html:27` („Frag einfach los …“ in den Platzhalter der Eingabe, `gespraech.html:58`),
  `gespraech.html:70–73` (bleibt als einzige Angabe, was das Gespräch kennt), `gespraeche.html:21` und
  `gespraech.html:72` (30 Tage: einmal, im `details`), `neu.html:25` (Satz weg), `vorlagen.html:48–49` (in ein
  `details` „Was kommt aus der Vorlage?“), `ich.html:14–15` (ein kurzer Satz unter der Überschrift),
  `pflege_reihe_neu.html:18–21` (Zahlenfeld beschriftet, Erklärsatz kürzer). Das Formular in Neu (`neu.html:42`,
  `:89`, `:95–99`) auf zwei Sätze.
- Lia sieht danach: weniger Text; was sie braucht, steht im Feld oder ist aufklappbar. „Beim ersten Besuch“ bauen
  wir nicht (bräuchte gespeicherten Zustand je Seite).
- Tests: `test_app.py` („Frag einfach los“), Neu-Tests in `test_app.py` (TestNeuerAuftrag) bei geänderten Sätzen.

## Schritt 9: Ergebnis-Seite (Vorschlag 5)

- Dateien: `ergebnis.html` (`:163–179` rechte Leiste: nur „Rückmeldung geben“ blau, dazu ··· mit Eigene Fassung
  hochladen und Als final markieren; `:50–57` je Datei ein Download-Symbol mit Auswahl PDF/Word und „Rückmeldung zu
  dieser Datei“ im selben Menü; `:258–295` Fassungen in einer geschlossenen Klappe „Verlauf: n Fassungen,
  m Rückmeldungen“, `:290` Final-Knopf je Fassung ins Zeilen-···), `ruhig.css`.
- Lia sieht danach: Kopf, Dateien, „Das Wichtigste“, eine Zeile Verlauf. Die Seite ist etwa eine Bildschirmhöhe
  statt 4059 px. Rückmeldung bleibt ein Klick.
- Tests: `test_app.py` (TestMaterial: „Als final markieren“, „Rückmeldung geben“, „Fassungen“, `test_rote_marken`
  erwartet genau einen blauen Knopf „Rückmeldung geben“, bleibt so), `test_schnell.py` (TestSchnellNeu: „Fassungen“,
  schnelle Fassung oben).

## Später, nur wenn Jan will

- **10. Zeilen-···** an Gespräch-, Stunden- und Fassungszeilen (Umbenennen, Löschen, Verschieben, Ausblenden direkt
  an der Zeile). Dateien `_ort.html:34–40`, `reihe.html:47–55`, `ruhig.css`. Tests neu.
- **11. Wörter**: „Neu“ statt „Neuer Auftrag +“ und „Daraus Auftrag machen“, Plus immer vorn (`_heute.html:11`,
  `gespraech.html:16`); Stand der Reihe als Kennzeichen statt „(in Planung)“ im Namen (`logik.py:1036`, `:1340`,
  Python: 13 Prüfungen in `test_logik.py`, 8 in `test_ordnung.py`, Neustart); Stunde im Baum „1 · Thema offen“
  (`logik.py:1344`); „Ich“ umbenennen (`logik.py:1358`, `app.py:2164`; Name entscheidet Jan oder Lia).
- **2b. Fertig je Reihe zusammenfassen** (siehe Schritt 2).

## Reihenfolge und Aufwand

0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9. Schritte 1, 2 und 8 sind je eine kurze Sitzung, 3 bis 6 und 9 je eine
längere, 7 braucht eine Browserprobe. Nach Schritt 6 lohnt eine Probe mit Lia, bevor 7 bis 9 folgen.

## Was Jan entscheidet

1. Plan so freigeben (ganz oder bis zu einem Schritt)?
2. Schritt 0 (Probe-Kopie, eine kleine Python-Änderung) ja oder nein?
3. Blauer Knopf an Reihe, Stunde, Klasse: „+ Gespräch“ (Vorschlag) oder „+ Neu“?
