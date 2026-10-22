# Status: Agent dokumente

## Zweck
Word-, PowerPoint- und Excel-Dateien für Jan erstellen und bearbeiten: Anträge, Berichte,
Präsentationen, Tabellen. Sauber formatiert, auf Wunsch auf Jans Vorlagen.

## Stand (22.10.2026)
- agent.py läuft als Dienst dokumente.service (oneshot, eingerichtet 22.10., kein Timer, die Zentrale
  startet ihn nach jedem Auftrag). Kann bisher nur **Zusammenfassungen von Vorlesungen** (zusammenfassen.py),
  von Jan oder von uni (auftraege.weitergeben). Andere Aufträge lehnt Claude ab (NICHT_UNTERSTUETZT),
  der Auftrag endet als fehlgeschlagen mit Grund.
- Ablauf: Dateien vorbereiten (eingang.py) -> Claude schreibt data/ausgang/<id>/beschreibung.json im
  Renderer-Format (Abschnitte Allgemein und Zusammenfassung aus ../shared/renderer/FORMAT.md stehen im
  Prompt) -> renderer.bauen() mit profil-zusammenfassung.toml -> Claude prüft Kontrolltext und
  Vorschaubilder und schreibt kontrolle.json -> Python prüft den Bericht gegen die Behauptungsliste
  (zusammenfassen.bericht_pruefen). Fertig erst, wenn jede Behauptung abgedeckt, nichts fehlt, nichts
  erfunden, keine Darstellungsfehler, und Claude die Beschreibung dabei nicht mehr geändert hat.
  Alles in einer Claude-Sitzung (sitzung_fortsetzen). Grenzen: 3 Bauversuche je Bau, 3 Kontrollen.
- Ergebnis: data/ausgang/<id>/<titel>.pdf und .docx, abschliessen(..., dateien=[pdf, docx], sitzung=).
  Antwortet Jan auf die Meldung, setzt der Agent die Sitzung fort und baut neu (Behauptungsliste aus dem
  ersten Auftrag der Kette).
- Fehler: BeschreibungUngueltig und kaputtes JSON gehen an Claude zurück. Alles andere (Claude-Lauf
  fehlgeschlagen, keine Vorschau/kein PDF, Profil, Renderer) beendet den Auftrag als fehlgeschlagen,
  die Zentrale meldet es Jan, Details in logs/dokumente.log. Limit/kein Platz: Auftrag wartet.
- Eingangsdateien (eingang.py): docx/pptx/xlsx -> <datei>.txt (agentkit.textfassung), PDF -> <datei>.txt
  (Text mit pypdfium2) und <datei>-seiten/ mit PNG je Seite (renderer.vorschau.als_bilder). So sieht
  Claude auch Folien-PDFs und Scans (Read kann hier keine PDFs, poppler fehlt).
- .venv: python-docx, python-pptx, openpyxl, Pillow, pypdfium2 (requirements.txt), agentkit und renderer
  per agentkit.pth. LibreOffice für die Vorschau aus dem System.
- Profil: profil-zusammenfassung.toml (Kopie aus renderer/beispiele/), erstellt_von leer (Jan: nicht wichtig).
  Word-Vorlage mit Logo wird benutzt, wenn data/vorlagen/zusammenfassung.docx existiert (gibt es noch nicht).

## Übergabe von uni (Format, für Teil D im uni-Chat)
- `auftraege.weitergeben("uni", "dokumente", text, aus_auftrag, dateien=[...])`. Text: worum es geht
  (Kurs, Datum, Umfang). Dateien: Transkript bzw. aufbereitete Fassung, Folien (PDF geht), und
  **behauptungen.json**: Liste aus
  `{"nr": 1, "aussage": "...", "quellen": [{"art": "transkript"|"folie"|"norm", "stelle": "4-5"}], "kennzeichnung": "unsicher"|"muendlich"}`
  (nr eindeutige ganze Zahl, aussage Pflicht, Rest optional; quellen wie in FORMAT.md: Seiten- und
  Foliennummern nur als Zahlen). Jede Behauptung muss in der Zusammenfassung vorkommen.
- Ist behauptungen.json ungültig, scheitert der Auftrag mit dem Grund (Fehler des Absenders).
- Ohne Liste prüft Claude nur gegen die Dateien.

## Aufbau
- agent.py (Einstieg, dünn), zusammenfassen.py (Ablauf und reine Logik, Claude und Renderer als
  Funktionen übergeben), eingang.py, profil-zusammenfassung.toml
- Dienst: systemd/dokumente.service, eingerichtet in ~/.config/systemd/user/. Von Hand starten:
  `systemctl --user start dokumente` (wartet, bis alle Aufträge durch sind).
- Laufzeitdaten: data/eingang/<id>/, data/ausgang/<id>/ (beschreibung.json, kontrolle.json,
  kontrolltext.txt, <titel>-vorschau/), data/vorlagen/. Logs: logs/dokumente.log, logs/renderer.log.
- Tests: `.venv/bin/python -m unittest discover -s tests -t .` (Ablauf mit falschem Claude, echte Prüfung
  des Renderers, Profil gegen den Renderer, PDF-Vorbereitung)

## Entscheidungen
- 17.10.: Beschreibung + Python statt von Claude geschriebener Skripte (Jan; "Claude denkt, Python handelt").
- 22.10.: Selbstkontrolle mit Bericht als JSON, den Python nachprüft (nicht nur Claudes "fertig").
- 22.10.: Ein Dokument an Jan zu schicken ist kein Handeln nach außen, braucht keine Freigabe.
  Weitergabe an Kommilitonen macht Jan selbst.

## Offene Punkte
1. Testauftrag 22.10. lief durch (uni -> dokumente, Gebrauchsklassen, 10 Behauptungen aus dem Transkript
   vom 20.10., Testdateien in uni/data/test-3a/): 3 Seiten, Beschreibung im 1. Versuch gültig, Kontrolle
   fand in Runde 1 einen Fehler (Deckenbalken) und korrigierte ihn, Runde 2 ok. 3 Claude-Läufe Opus,
   ca. 280.000 Tokens, 75 s. PDF kam in Telegram an, Jan: passt (22.10.).
   Schönheitsfehler: Claude hängt dieselbe Quelle an jeden Listenpunkt (Hinweis im Prompt, falls es stört).
2. Word-Vorlage mit HNEE-Logo in der Kopfzeile (data/vorlagen/zusammenfassung.docx), sobald es das Logo
   in Grün gibt (Renderer-STATUS, Offene Punkte 1).
3. Weitere Arten: Brief, Bericht, Folien, Excel (Renderer erweitern, eigener Chat). Vorlagen von Jan
   annehmen, bestehende Dateien bearbeiten (Anforderungen unten).
4. Modus lernen wird wie erledigen behandelt.
5. `ursprung()` gibt es gleich in uni/agent.py und hier: Kandidat für agentkit (Hauptordner-Chat).

## Anforderungen (Jan, 17.10.)
- Vorlagen: Jan schickt seine Vorlagen per Telegram (z. B. Datei mit "/dokumente Vorlage Briefkopf").
  Ablage unter data/vorlagen/. .dotx/.potx mit renderer.vorlage_umwandeln() in .docx/.pptx.
- Bearbeiten: Jan schickt eine bestehende Datei mit Auftrag. Das Original bleibt unverändert, das
  Ergebnis ist eine neue Datei (z. B. <name>-bearbeitet.docx).

## Gelernte Regeln
- (noch keine)
