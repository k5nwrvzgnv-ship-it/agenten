# Status: Renderer (shared/renderer)

## Zweck
Gemeinsame Bibliothek für Jan und Lia: Eine JSON-Beschreibung geht rein (von Claude geschrieben), eine
Datei kommt raus (docx, pptx, später PDF). Claude führt nie Code aus, Python baut. Nutzer sind Lias
Material-Agent (zuerst) und Jans dokumente-Agent (später). Grundlage: docs/lia-architektur.md,
Abschnitt 2.1 (Rolle material) und 7 (Schritt 1).

## Stand (21.10.2026)
- Ordner angelegt, noch kein Code. Die Entscheidungen vor dem Bauen sind geklärt (siehe unten).

## Zuerst lesen
1. `../../CLAUDE.md`: Regeln. Dieser Chat ändert nur shared/renderer/, Bedarf anderswo steht in
   `../../STATUS.md`.
2. `../../STATUS.md` (Punkt 8) und `../../docs/uebergabe-lia-dokumente.md` (Lias Agent, der den Renderer nutzt)
3. `../../dokumente/STATUS.md`, Abschnitt Anforderungen: Jans Wünsche (Vorlagen, Bearbeiten, Excel,
   Textfassung zur Selbstkontrolle, Fehler zurück an Claude). Gilt später, nicht für den ersten Schritt.

## Entscheidungen (Jan, 21.10.)
- **Umfang des Kerns:** alle vier Bausteine:
  - Titel, Überschriften, Absätze, Listen, Tabellen
  - Aufgaben mit Platz für Antworten (Linien oder Kästen)
  - Kopfzeile (Name, Klasse, Datum)
  - Folien mit Titel und Stichpunkten
- **Formate:** zuerst nur docx und pptx (python-docx, python-pptx). PDF später, wenn Bedarf da ist. Typst oder
  LibreOffice nur nach erneutem Okay von Jan.
- **Vorlagen:** sollen über die Bedienoberfläche (Telegram) vorgegeben werden können. Aufteilung:
  - Renderer: optionales Feld für eine Vorlage (docx/pptx). Mit Vorlage baut er auf deren Stilen bzw.
    Folienmastern auf, ohne Vorlage auf schlichten Standardstilen. Dazu eine Hilfsfunktion, die .dotx/.potx in
    .docx/.pptx umwandelt.
  - Agent: legt die Vorlagen unter `<agent>/data/vorlagen/` ab, nicht im Renderer.
  - Zentrale: Lias `portal.py` muss Dateien annehmen. Das macht der Hauptordner-Chat (steht in `../../STATUS.md`,
    Punkt 8).
  - Ob Lia eine Schulvorlage hat, ist noch offen. Für den Kern ist das egal.
- **Tests:** eigene `shared/renderer/.venv` mit python-docx 1.2.0 und python-pptx 1.0.2 (gleiche Versionen wie
  in `dokumente/`). Dazu kommt ein Eintrag in `pruefen.sh`.
- **Laufzeit:** Die Agenten importieren den Renderer über agentkit.pth in ihrer eigenen .venv. Darum brauchen
  sie dort python-docx bzw. python-pptx. Die .venv des Renderers ist nur für die Tests da.

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
1. Plan für den Kern zeigen (Format der Beschreibung, Module, .venv anlegen) und auf Jans Okay warten.
2. Kern bauen wie unter „Fertig heißt“, inklusive Vorlagenfeld und Umwandlung .dotx/.potx.

## Gelernte Regeln
- (noch keine)
