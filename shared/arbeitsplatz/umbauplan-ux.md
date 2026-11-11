# Umbauplan Arbeitsplatz: ruhige Oberfläche wie in Lias App

Stand 11.11.2026. Jans Okay 11.11. mit Variante A für Schritt 4; alle fünf Schritte gebaut. Auftrag: Die Verbesserungen aus `shared/webapp` (dort
`umbauplan-ux.md`, Schritte 1–7, live seit 11.11.) kommen in den Arbeitsplatz. Jan hat vier Teile gewählt: ruhiges
Aussehen, „+“ und „···“, direkt am Ding, Dokument-Seite. Lias Fachbegriffe (Klasse, Reihe, Stunde, Gespräch, schneller
Weg) kommen nicht mit.

So sieht ein Ort danach aus (Beispiel):

```
Heute › Forschungsprojekt Fehlstellen › Exposé                [+]  [···]
Exposé                                   (anklicken = umbenennen)

Dokumente   Exposé Fehlstellen, Fassung 3        Final
            Recherche Holzfeuchte                Läuft
Unterseiten Gliederung

[+]   → Seite · Dokument … · Datei
[···] → Umbenennen · Verschieben nach … · Unterseiten ordnen (↑/↓) · Archivieren
```

## Spielregeln

- Gebaut wird nur in `shared/arbeitsplatz/`. `shared/webapp` und `uni/portal` bleiben unverändert.
- `ruhig.css`, `direkt.js` und das Stück aus `gespraech.js` werden nach `statisch/` kopiert, nicht verlinkt. Kein neues
  Paket, CSP bleibt `'self'`.
- Ein Schritt = ein Commit über `~/agenten/commit.sh` (der Hook prüft mit `pruefen.sh` unter der Sperre).
- Vorlagen und CSS wirken sofort auf den laufenden Dienst, Python erst nach Neustart (nur mit Jans Okay). Nach jedem
  Schritt ein Rundgang über alle Seiten gegen 127.0.0.1:8794, nur lesend, alle 200.
- Menüs sind `<details>`, gehen also ohne JavaScript. Wo JavaScript dazukommt, bleibt ein Weg ohne.
- Was der Unittest nicht prüfen kann (JavaScript, Aussehen), probiert Jan im Browser:
  `ssh -N -L 8794:127.0.0.1:8794 agents-user` auf dem Mac, dann http://localhost:8794.

## Schritt 1: Ruhiges Aussehen (nur Vorlagen und CSS, kein Neustart) (gebaut 11.11.2026, live)

Gebaut wie unten. Abweichungen: Die Sätze „Noch keine Orte …“ und die Leertexte des Orts fielen erst mit Schritt 2 weg.
Aufzählungen tragen wie bei Lia ein `span.nr`. Kosten auf Heute: Überschrift „Kosten · heute 0.38 USD“. Test
`test_ruhiges_aussehen`.


- Dateien: `statisch/ruhig.css` (Kopie), `statisch/arbeitsplatz.css` (Ergänzungen auf die Farben und Abstände von
  `ruhig.css` umgestellt: tiefere Baum-Ebenen, Seitenbilder, Recherche- und Prüfungsansicht), `vorlagen/basis.html`
  (Blöcke für Rahmen, Skripte, rechte Spalte, „+“ und „···“ wie in Lias `basis.html`), alle übrigen Vorlagen auf die
  Klassen von `ruhig.css`. `stil.css` fliegt raus, sobald nichts mehr darauf zeigt.
- Raster: Seitenleiste 240 px, Mitte bis 736 px (640 px Text), rechts 280 px. Rechte Spalte nur auf **Heute**: „Läuft
  gerade“ und „Kosten“ (heute und die letzten 6 Läufe). Ort, Dokument, Neu, Formular, Archiv, Meldungen sind
  einspaltig und mittig. Was gerade läuft, steht auf allen Seiten weiter im Baum neben „Heute“ („2 läuft“) und als
  Marke „Läuft“ am Dokument.
- Weniger Text: „Noch nichts hier. „+ Neu“ legt …“, „Noch keine Orte. Links mit …“, „Neues Dokument in …“ (Neu) und
  ähnliche Sätze fallen weg.
- Jan sieht danach: dieselben Seiten in Lias ruhigem Aussehen (Inter, graue Seitenleiste, dunkler Modus), Kosten und
  „Läuft gerade“ nur noch auf Heute.
- Tests: `test_app.py` (Rahmen-Klassen, rechte Spalte nur auf Heute, `ruhig.css` statt `stil.css`).

## Schritt 2: „+“ und „···“, nur zeigen, was da ist (nur Vorlagen und CSS) (gebaut 11.11.2026, live)

Gebaut wie unten. „Unterseiten ordnen“ im „···“ erst ab zwei Unterseiten. Das „+“ der Dokument-Seite gehört zu
Schritt 5, Neu, Formular, Archiv und Meldungen haben keins. Tests `test_plus_je_seite`, `test_punkte_am_ort`,
`test_nur_zeigen_was_da_ist`.


- Dateien: neu `vorlagen/_plus.html` (Makros `plus` und `punkte`, aus Lias `_plus.html` ohne deren Ebenen-Makro),
  `basis.html` (Knopf „+ Neu“ wird das „+“), `ort.html`, `heute.html`, `archiv.html`.
- Das „+“ je Seite:

  | Seite | Im „+“ |
  |---|---|
  | Heute | Seite (oben im Baum), Dokument … |
  | Ort | Seite (Unterseite), Dokument … (Galerie mit diesem Ort), Datei (ab Schritt 4) |
  | Dokument | Dokument … am selben Ort (nicht blau, siehe Schritt 5) |
  | Archiv, archivierter Ort | kein „+“ |

  „Seite“ legt sofort eine Unterseite „Neue Seite“ an und öffnet sie (bestehende Route `/seite/neu`); den Namen
  ändert Jan dort direkt im Titel (Schritt 3). Die Maske `/seite/neu` bleibt für den Weg ohne JavaScript.
- Das „···“ am Ort: Umbenennen (Maske), Verschieben nach …, Unterseiten ordnen (je Unterseite ↑/↓), Archivieren.
  Im Archiv bleibt „Wiederherstellen“ am Hinweis „Diese Seite liegt im Archiv“. Routen bleiben alle gleich.
- Nur zeigen, was da ist: Ort ohne Dokumente ohne Abschnitt „Dokumente“, ohne Unterseiten ohne „Unterseiten“, kein
  offenes Formular „+ Seite“ mehr auf der Seite. Ist der Ort ganz leer: eine leise Zeile „Noch leer. Mit + fängst du
  an.“ Heute: „Wartet auf dich“ und „Zuletzt“ nur mit Einträgen. Im Baum fällt „+ Seite“ unter dem aktiven Ort weg
  (steht jetzt im „+“), „+ Seite“ ganz unten bleibt.
- Jan sieht danach: Kopfzeile mit Brotkrumen, „+“ und „···“, darunter nur Inhalt.
- Tests: neu `test_plus_je_seite`, `test_punkte_am_ort`, `test_nur_zeigen_was_da_ist`; angepasst die Tests, die
  „+ Neu“, „Seite bearbeiten“ und die Leertexte prüfen.

## Schritt 3: Direkt am Ding (Vorlagen und `direkt.js`, kein Neustart) (gebaut 11.11.2026, live)

Gebaut wie unten. Zusätzlich: Eine eben über „+“ angelegte „Neue Seite“ steht gleich zum Umbenennen offen
(`data-direkt-offen`, nur mit `?aktion=` nach dem Anlegen). `direkt.js` zieht Dateien allgemein in das eine Dateifeld
mit `data-ablegen` (Formular, Ort, Dokument) und behält schon gewählte. Test `test_direkt_am_ding`. Browser-Probe
steht aus.


- Dateien: neu `vorlagen/_direkt.html` (Makro `titel` aus Lias App), `statisch/direkt.js` (Kopie; der Teil
  „Ablage“ wird in Schritt 4 auf den Arbeitsplatz zugeschnitten), `ort.html`, `formular.html`.
- Titel des Orts anklicken: Feld, Enter speichert, Esc oder „Abbrechen“ bricht ab. Das geht über die bestehende Route
  `/ort/<id>/umbenennen` (braucht nur `titel`), also ohne neues Python. Danach der Hinweis mit „Rückgängig“ wie heute.
- Formular einer Art (`/neu/<art>`): Datei auf die Seite ziehen legt sie ins Dateifeld, danach steht der Name da.
- Den Titel eines Dokuments kann man nicht umbenennen: Er kommt vom Agenten (`daten.titel`). Das wäre neues Python
  und neue Ablage, nicht Teil dieses Plans.
- Ohne JavaScript: Umbenennen über „···“, Dateifeld wie bisher.
- Jan sieht danach: Er ändert den Namen einer Seite, wo er hinschaut.
- Tests: Ort-HTML trägt `data-direkt-titel` und das Formular mit Token an `/ort/<id>/umbenennen`. Browser-Probe bei
  Jan: Anklicken, Enter, Esc, Datei ins Formular ziehen.

## Schritt 4: Datei am Ort (Python, Neustart) (Jan 11.11.: A; gebaut 11.11.2026, live seit dem Neustart 11.11. 15:42)

Gebaut wie A. Der Ordner heißt `data/eingang/gelegt-<kennung>` (Kennung aus `mkdtemp`), die Galerie zeigt dann
„Was soll daraus werden?“ und „Dabei: …“. Ist die Kennung verbraucht oder gelöscht: Hinweis in der Galerie, Fehler im
Formular. Nur am Ort, nicht auf Heute. Tests `test_datei_am_ort`, `test_datei_am_ort_grenzen`, `test_gelegt_aufraeumen`.


Lias App hat am Ort eine Ablage („Deine Dateien“, die Gespräche kennen). Der Arbeitsplatz hat keine: Jede Datei geht
heute als Material in einen Auftrag. Zwei Wege:

- **A (empfohlen): Datei wird Material für ein neues Dokument.** „Datei“ im „+“ oder eine Datei auf den Ort ziehen:
  Die Datei liegt kurz in `data/eingang/`, dann kommt die Galerie „Was soll daraus werden?“ mit den Arten, die Material
  annehmen (finance-Arten nicht). Im Formular steht die Datei schon drin, weitere kann Jan dazulegen. Liegengebliebenes
  älter als ein Tag wird beim nächsten Hochladen gelöscht.
  Python: neue Route `POST /neu/datei` (Ort, Dateien; dieselben Grenzen wie heute: 10 Dateien, je 50 MB, gleiche
  Endungen, Token, Herkunft), Galerie und Formular nehmen die Kennung `datei=` mit, `neuer_auftrag` übernimmt die
  gelegten Dateien. Tests: Hochladen, falsche Endung, fremde Kennung, Galerie ohne finance, Auftrag mit den Dateien,
  Aufräumen. Neustart mit Jans Okay.
- **B: Keine Datei am Ort.** Ziehen geht nur auf das Formular (Schritt 3) und die Dokument-Seite (Schritt 5). Kein
  neues Python, kein Neustart. Das „+“ am Ort hat dann nur Seite und Dokument …

## Schritt 5: Dokument-Seite `/dokument/<ursprung>` (Vorlagen und CSS, kein Neustart) (gebaut 11.11.2026, live)

Gebaut wie unten. Abweichungen: Hat ein Dokument eine Datei mit mehr als zwei Seiten (oder mehrere Dateien mit
Seitenbildern), stehen alle Seiten in einer Klappe „Alle N Seiten“ darunter, damit nichts verloren geht. Die Knöpfe
heißen weiter „Als final markieren“ und „Nicht mehr final“. Die eigene Fassung hat nach der Wahl noch das Feld
„Notiz“. Der Hinweis „Zu dieser Art nimmt der Agent keine Rückmeldung an …“ ist weg. Der Verlauf zählt als Fassungen,
was man final markieren kann, als Rückmeldungen auch die Dateien zur Rückmeldung. Test `test_dokument_ruhig`.


- Dateien: `dokument.html`, `statisch/anhang.js` (das Stück aus Lias `gespraech.js`, das den Namen der angehängten
  Datei zeigt), `direkt.js` (Datei auf die Seite ziehen hängt sie an die Rückmeldung), `arbeitsplatz.css`.
- Reihenfolge: Kopf (Art, Titel, Marke), Dateien, das Wichtigste (Kern, Punkte, „Bitte prüfen“), das Feld für die
  Rückmeldung, die eigene Ansicht (Recherche, Prüfung, Karten) wie bisher, ganz unten der Verlauf.
- Rückmeldung als immer sichtbares Feld wie im Gespräch: Platzhalter „Was soll anders werden?“, „+ Datei anhängen“,
  „Senden“ als einziger blauer Knopf. Nur bei Arten mit `rueckmeldung`; sonst kein Feld und kein Satz dazu. Im
  Probebetrieb (`ARBEITSPLATZ_AUFTRAEGE=aus`) eine leise Zeile darunter. Route bleibt gleich.
- Je Datei ein Download-Symbol mit „PDF ansehen“ und „Original (Word)“ bzw. PowerPoint, Excel, Markdown, je nachdem,
  was da ist. Die Seitenbilder stehen klein (2 × 260 px wie bei Lia), Klick öffnet die Seite groß.
- Im „···“: Als final markieren bzw. „Final · rückgängig“ (für die Fassung oben), „Eigene Fassung hochladen …“ (erst
  nach der Wahl Name und „Hochladen“, wie bei Lia). `?offen=eigene` öffnet das „···“, Fehler stehen darin.
- Verlauf: eine geschlossene Klappe „Verlauf: N Fassungen, M Rückmeldungen“ mit den Fassungen (je mit Final-Knopf,
  Kosten, Auftrag) und den Rückmeldungen samt Antwort. Erst ab zwei Einträgen.
- Das „+“ ist hier nicht blau („Senden“ ist der Hauptknopf), mit „Dokument …“ am selben Ort.
- Jan sieht danach: Kopf, Dateien, das Wichtigste, das Feld für seine Rückmeldung, eine Zeile Verlauf.
- Tests: neu `test_dokument_ruhig` (genau ein blauer Knopf, Feld nur bei Arten mit `rueckmeldung`, Final und eigene
  Fassung im „···“, Verlauf geschlossen mit Zahlen); angepasst die Dokument-Tests („Rückmeldung geben“,
  „Fassungen“). Browser-Probe bei Jan: Datei anhängen, Datei auf die Seite ziehen, eigene Fassung im „···“.

## Abschluss

- Rundgang über alle Seiten (alle 200), Jans Instanz bleibt unverändert (nur lesend).
- Nur bei Schritt 4 A: Neustart `systemctl --user restart arbeitsplatz.service` mit Jans Okay, danach Rundgang.
- `STATUS.md` auf den Stand, dieser Plan bekommt je Schritt „gebaut“ mit Abweichungen.

## Reihenfolge

1 → 2 → 3 → 5 sind Vorlagen, CSS und Skripte und wirken sofort. 4 hängt an Jans Wahl und ist der einzige Schritt mit
Python. Eine Browser-Probe lohnt nach 3 und nach 5.
