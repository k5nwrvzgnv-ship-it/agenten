# Status: Renderer (shared/renderer)

## Zweck
Gemeinsame Bibliothek für Jan und Lia: Eine JSON-Beschreibung geht rein (von Claude geschrieben), eine
Datei kommt raus (docx, pptx, später PDF). Claude führt nie Code aus, Python baut. Nutzer sind Lias
Material-Agent (zuerst) und Jans dokumente-Agent (später). Grundlage: docs/lia-architektur.md,
Abschnitt 2.1 (Rolle material) und 7 (Schritt 1).

## Stand (21.10.2026)
- Ordner angelegt, noch kein Code. Diese Datei ist die Übergabe an den ersten Renderer-Chat.

## Zuerst lesen
1. `../../CLAUDE.md`: Regeln. Dieser Chat ändert nur shared/renderer/, Bedarf anderswo steht in
   `../../STATUS.md`.
2. `../../STATUS.md` (Punkt 8) und `../../docs/uebergabe-lia-dokumente.md` (Lias Agent, der den Renderer nutzt)
3. `../../dokumente/STATUS.md`, Abschnitt Anforderungen: Jans Wünsche (Vorlagen, Bearbeiten, Excel,
   Textfassung zur Selbstkontrolle, Fehler zurück an Claude). Gilt später, nicht für den ersten Schritt.

## Mit Jan klären, vor dem Bauen
- **Umfang des Kerns:** Vorschlag, was Lia für Arbeitsblätter und Folien braucht:
  - Titel, Überschriften, Absätze, Listen, Tabellen
  - Aufgaben mit Platz für Antworten (Linien oder Kästen)
  - Kopfzeile (Name, Klasse, Datum)
  - Folien mit Titel und Stichpunkten
- **Formate:** docx und pptx sind mit python-docx und python-pptx möglich, beide schon in `dokumente/.venv`.
  Für PDF gibt es zwei Wege, beide nur mit Jans Okay, denn es ist neue Software ohne sudo:
  - Typst als einzelne Datei in `~/.local/bin`
  - LibreOffice
- **Vorlagen:** ob es eine Schulvorlage von Lia gibt. Vorlagen liegen beim Agenten (`<agent>/data/vorlagen/`),
  nicht im Renderer.
- **Tests:** Welche .venv führt die Tests aus? Der Renderer hat als Bibliothek keine eigene. Vorschlag:
  eigene `shared/renderer/.venv` nur mit den Bibliotheken, eingetragen in `pruefen.sh`.

## Vorgaben
- Schnittstelle stabil halten: Beide Instanzen nutzen den Renderer sofort, es gibt kein versioniertes Paket.
  Das Format nur erweitern, nicht umbauen, und jede Erweiterung mit Tests.
- Eingabe streng prüfen, bevor gebaut wird (Schema). Fehlermeldungen so schreiben, dass Claude sie in derselben
  Sitzung beheben kann.
- Ausgabe zur Selbstkontrolle: eine Textfassung des fertigen Dokuments, die Claude lesen kann.
- Keine Inhalte, Zugangsdaten oder Netzzugriffe im Renderer.

## Fertig heißt (erster Schritt)
- `from renderer import ...` baut aus einer Beispielbeschreibung ein Arbeitsblatt als docx und eine kleine
  Folienreihe als pptx.
- Ungültige Beschreibungen ergeben klare Fehler.
- Es gibt Tests, `./pruefen.sh` ist grün, die Schritte sind committet, und diese STATUS.md beschreibt das Format.

## Offene Punkte
1. Die Entscheidungen oben mit Jan klären.

## Gelernte Regeln
- (noch keine)
