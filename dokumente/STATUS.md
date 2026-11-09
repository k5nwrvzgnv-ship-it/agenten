# Status: Agent dokumente

## Zweck
Word-, PowerPoint- und Excel-Dateien für Jan erstellen und bearbeiten: Anträge, Berichte,
Präsentationen, Tabellen. Sauber formatiert, auf Wunsch auf Jans Vorlagen.

## Stand (09.11.2026)
- agent.py läuft als Dienst dokumente.service (oneshot, kein Timer, die Zentrale startet ihn nach jedem Auftrag).
- **Ohne `art`** (Telegram, uni): nur **Zusammenfassungen von Vorlesungen** wie bisher (Prompts byte-gleich
  zu vorher). Andere Aufträge lehnt Claude ab (NICHT_UNTERSTUETZT), der Auftrag endet als fehlgeschlagen.
  Einzige Änderung: Schickt Jan mit einer Antwort Dateien, nennt der Prompt sie jetzt.
- **Mit `art`** (Arbeitsplatz, Plan docs/arbeitsplatz-plan.md): `zusammenfassung` (wie oben), `praesentation`
  (Renderer-Art folien -> pptx + PDF, profil-praesentation.toml, HNEE-Grün) und `bericht` (Renderer-Art bericht
  -> docx + PDF, profil-zusammenfassung.toml). Andere Arten: fehlgeschlagen mit Grund. Eine Antwort ohne `art`
  erbt die Art vom Ursprung der Kette. Ergebnis zusätzlich mit `daten` = {titel, kern, punkte, pruefen}: kern
  und punkte aus kurz.json von Claude (Fallback: erste Zeile der Antwort), pruefen ergänzt Python um Zahl der
  [OFFEN: …]-Stellen, Abweichung vom Feld `Umfang` (unter 70 % / über 130 % + 1, nur Hinweis) und
  Renderer-Hinweise.
- Präsentation und Bericht: Inhalt nur aus Material (Dateien) und Feldern; was fehlt, wird [OFFEN: …] statt
  ausgedacht. Reicht nichts (nur ein Thema), antwortet Claude ZU_WENIG_MATERIAL, Auftrag fehlgeschlagen mit Grund.
  Kontrollbericht {erfunden, auftrag, darstellung}, alle leer = fertig (arten.bericht_pruefen).
  Felder, die der Agent liest: `Umfang` (Zahl darin, z. B. "10 Folien", Titelfolie zählt mit); alle übrigen
  stehen im Auftragstext und gehen so an Claude.
- Ablauf (alle Arten, zusammenfassen.erstellen mit Art-Objekt): Dateien vorbereiten (eingang.py) -> Claude
  schreibt data/ausgang/<id>/beschreibung.json im Renderer-Format (nur die nötigen Abschnitte aus
  ../shared/renderer/FORMAT.md) -> renderer.bauen() -> Claude prüft Kontrolltext und Vorschaubilder und schreibt
  kontrolle.json (und mit art kurz.json) -> Python prüft den Bericht. Fertig erst, wenn der Bericht stimmt und
  Claude die Beschreibung dabei nicht mehr geändert hat. Eine Claude-Sitzung. Grenzen: 3 Bauversuche je Bau,
  3 Kontrollen. Zusammenfassung zusätzlich gegen die Behauptungsliste (siehe unten).
- Ergebnis: data/ausgang/<id>/<titel>.pdf und .docx/.pptx, abschliessen(..., dateien=[pdf, datei], sitzung=,
  daten=). Seitenbilder in <titel>-vorschau/ (Renderer-Konvention). Antwortet Jan, setzt der Agent die Sitzung
  fort und baut neu.
- Fehler: BeschreibungUngueltig und kaputtes JSON gehen an Claude zurück. Alles andere (Claude-Lauf
  fehlgeschlagen, keine Vorschau/kein PDF, Profil, Renderer) beendet den Auftrag als fehlgeschlagen,
  die Zentrale meldet es Jan, Details in logs/dokumente.log. Limit/kein Platz: Auftrag wartet.
- Eingangsdateien (eingang.py): docx/pptx/xlsx -> <datei>.txt (agentkit.textfassung), PDF -> <datei>.txt
  (Text mit pypdfium2) und <datei>-seiten/ mit PNG je Seite. Markdown/Text liest Claude direkt.
- .venv: python-docx, python-pptx, openpyxl, Pillow, pypdfium2 (requirements.txt), agentkit und renderer
  per agentkit.pth. LibreOffice für die Vorschau aus dem System.
- Vorlagen werden benutzt, wenn sie existieren: data/vorlagen/zusammenfassung.docx, bericht.docx,
  praesentation.pptx (gibt es alle noch nicht).

## Probeläufe Arbeitsplatz (09.11.2026, Agenten-Konto, kleines Testmaterial)
- praesentation (20261109-211357-dokumente-a51635): Notizen-docx Holzfeuchte, "5 Folien". 5 Folien, nichts
  erfunden, 1 [OFFEN] (fehlende Messwerte), 2 Kontrollen (Claude korrigierte Spalten), 3 Läufe, 0,93 USD, 2 min.
- bericht (20261109-211605-dokumente-c7647f): Praktikumsnotizen (md, fiktiv), Gliederungswunsch mit 6 Kapiteln,
  "2 Seiten". 2 Seiten, Gliederung eingehalten, 10 [OFFEN] (Zeitraum, Reflexion, Fazit ...), keine erfundenen
  Eindrücke, 1 Kontrolle, 2 Läufe, 0,46 USD, 1 min.
- Beide Ergebnisse gingen wie jedes erledigte Ergebnis über die Zentrale an Jan (Telegram).

## Vorschlag Felder für shared/arbeitsplatz/arten.toml
- praesentation: Thema (zeile, Pflicht), Zielgruppe (zeile), Umfang (auswahl: 5 / 10 / 15 / 20 Folien),
  Stichpunkte (text), Hinweise (text); Material als Dateien. ausgabe ["pptx", "pdf"].
- bericht: Art des Berichts (auswahl: Praktikumsbericht, Projektbericht, Laborbericht, Exkursionsbericht,
  Sonstiger), Thema (zeile, Pflicht), Gliederungswunsch (text), Umfang (auswahl: 2 / 5 / 10 / 15 Seiten),
  Angaben (text: Betrieb, Zeitraum, Betreuung), Stichpunkte (text); Material als Dateien. ausgabe ["docx", "pdf"].
- Nur der Name `Umfang` ist für Python wichtig, sonst frei.

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
- agent.py (Einstieg, dünn, Art wählen, Profil je Renderer-Art), zusammenfassen.py (Ablauf für alle Arten und
  reine Logik, Claude und Renderer als Funktionen übergeben, Art-Objekt ZUSAMMENFASSUNG), arten.py (Prompts und
  Kontrollbericht für praesentation und bericht, ARTEN), eingang.py, profil-zusammenfassung.toml,
  profil-praesentation.toml
- Dienst: systemd/dokumente.service, eingerichtet in ~/.config/systemd/user/. Von Hand starten:
  `systemctl --user start dokumente` (wartet, bis alle Aufträge durch sind).
- Laufzeitdaten: data/eingang/<id>/, data/ausgang/<id>/ (beschreibung.json, kontrolle.json,
  kontrolltext.txt, <titel>-vorschau/), data/vorlagen/. Logs: logs/dokumente.log, logs/renderer.log.
- Tests: `.venv/bin/python -m unittest discover -s tests -t .` (Ablauf mit falschem Claude, echte Prüfung
  des Renderers, Profile gegen den Renderer, PDF-Vorbereitung; Beispiele in tests/daten/)

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
3. Weitere Arten: Brief, Excel. Vorlagen von Jan annehmen, bestehende Dateien bearbeiten (Anforderungen unten).
   Grenzen der neuen Arten durch den Renderer (Bedarf in ../STATUS.md Punkt 34): Folien ohne Bilder, Tabellen,
   Sprechernotizen; Bericht ohne Deckblatt, Inhaltsverzeichnis und Bilder, "Stand <heute>" steht immer im Kopf.
   Bilder aus dem Material (Fotos, Diagramme) kommen deshalb nicht ins Ergebnis.
4. Modus lernen wird wie erledigen behandelt.
5. `ursprung()` gibt es gleich in uni/agent.py und hier: Kandidat für agentkit (Hauptordner-Chat).
6. Jan sieht die beiden Probeergebnisse an (Telegram bzw. data/ausgang/<id>/), dann in arten.toml aktiv = true.
7. Über Telegram gibt es Präsentation und Bericht nicht (ohne art nur Zusammenfassung). Falls gewünscht: art aus
   dem Text erkennen oder /dokumente-Unterbefehle, braucht Jans Okay.

## Anforderungen (Jan, 17.10.)
- Vorlagen: Jan schickt seine Vorlagen per Telegram (z. B. Datei mit "/dokumente Vorlage Briefkopf").
  Ablage unter data/vorlagen/. .dotx/.potx mit renderer.vorlage_umwandeln() in .docx/.pptx.
- Bearbeiten: Jan schickt eine bestehende Datei mit Auftrag. Das Original bleibt unverändert, das
  Ergebnis ist eine neue Datei (z. B. <name>-bearbeitet.docx).

## Gelernte Regeln
- (noch keine)
