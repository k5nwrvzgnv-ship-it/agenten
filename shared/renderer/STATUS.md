# Status: Renderer (shared/renderer)

## Zweck
Gemeinsame Bibliothek für Jan und Lia: Eine JSON-Beschreibung geht rein (von Claude geschrieben), eine
Datei kommt raus (docx, pptx, später PDF). Claude führt nie Code aus, Python baut. Nutzer sind Lias
Material-Agent (zuerst) und Jans dokumente-Agent (später). Grundlage: docs/lia-architektur.md,
Abschnitt 2.1 (Rolle material) und 7 (Schritt 1).

## Stand (21.10.2026)
- Entscheidungen geklärt (siehe unten), Plan von Jan freigegeben (6 Schritte, siehe Offene Punkte).
- Schritt 1 fertig: `.venv` (Versionen wie in `dokumente/`, Pillow bewusst auf 12.3.0), `agentkit.pth`,
  `requirements.txt`, leeres Paket, `tests/test_umgebung.py`, Eintrag in `pruefen.sh`.
- Neu aufsetzen: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, dann
  `echo /home/agent/agenten/shared > .venv/lib/python3.12/site-packages/agentkit.pth`.

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
Freigegebener Plan (21.10.), je Schritt ein Commit. Schnittstelle: `pruefen(beschreibung)` -> Fehlerliste,
`bauen(beschreibung, ziel, vorlage=None)` -> Ergebnis(pfad, textfassung), `vorlage_umwandeln(quelle, ziel)`,
`BeschreibungUngueltig`. Vorlage ist ein Parameter des Agenten, nicht Teil von Claudes JSON.
Module: pruefung.py, arbeitsblatt.py, folien.py, vorlagen.py, FORMAT.md, beispiele/.
1. (erledigt) .venv, requirements.txt, pruefen.sh, leeres Paket mit Test
2. pruefung.py mit Tests, FORMAT.md (art arbeitsblatt: titel, kopfzeile, bloecke ueberschrift/absatz/liste/
   tabelle/aufgabe mit antwort linien|kasten; art folien: titel, untertitel, folien mit titel/punkte).
   Streng: unbekannte Felder sind Fehler, alle Fehler auf einmal mit Pfad (`bloecke[4].antwort.anzahl: ...`).
3. Arbeitsblatt als docx mit Tests (Linien/Kästen per XML, Kopfzeile auf jeder Seite, A4)
4. Folien als pptx mit Tests (Layouts nach Platzhaltertyp suchen, nicht nach Namen)
5. Vorlagen: Umwandlung .dotx/.potx und Parameter `vorlage`, mit Tests
6. Beispiele, Textfassung über agentkit.textfassung im Ergebnis, Format hier in STATUS.md

## Gelernte Regeln
- (noch keine)
