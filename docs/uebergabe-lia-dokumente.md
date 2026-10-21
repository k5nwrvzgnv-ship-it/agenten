# Übergabe: Lias Dokument-Agent (21.10.2026)

Für einen neuen Chat. Start: `claude` im Hauptordner `~/agenten`, Arbeit auf dem Server als User agent.
Kurzauftrag: Lia fordert in ihrer Zentrale über „Neues Material“ etwas an (z. B. „Arbeitsblatt
kategorischer Imperativ, Klasse 10, 45 min“) und bekommt eine fertige Datei zurück.

## Zuerst lesen
1. `CLAUDE.md`: Regeln. Plan zeigen und auf Jans Okay warten, bevor Pakete, Dienste oder Benutzer kommen.
   Kleine Schritte, Commit je Schritt, `./pruefen.sh` grün, kcalbot und vinted-bot nicht anfassen.
2. `STATUS.md`: Stand, offener Punkt 8 (Lia).
3. `docs/lia-architektur.md`, Abschnitte 2.1, 2.5 und 7:
   - 2.1: Rolle material ist eine Renderer-Bibliothek, die auch Jans dokumente-Agent nutzt.
   - 2.5: Skills, erster Skill `einzelmaterial`.
   - 7: Schritt 1 „Material auf Zuruf“ mit Prüfkriterien.
4. `dokumente/STATUS.md`: Anforderungen an den Renderer. Claude schreibt eine JSON-Beschreibung, Python baut
   die Datei, Fehler gehen an Claude zurück. Dort stehen auch die Grenzen ohne LibreOffice.
5. Code:
   - `lia/unterricht/` (Platzhalter)
   - `shared/telegram/portal.py`, `portal_logik.py` und `panel.py` (Lias Zentrale)
   - `shared/agentkit/claude_lauf.py`, `auftraege.py` und `config.py`

## Stand
- Lias Instanz: `lia/` unter User agent, `AGENTKIT_INSTANZ=/home/agent/agenten/lia/shared`.
  Ohne die Variable verhält sich agentkit wie Jans Instanz.
- Lia nutzt Jans Pro-Abo. agentkit ist per .pth eingebunden, ein Paket kommt erst beim Umzug zu einem User lia.
- Dienst `lia-zentrale` (@zentraleliabot): Menü-Nachricht mit Knöpfen. Die Art des Auftrags steht im Feld
  `quelle` (`portal-material`, `portal-woche`, `portal-frage`, `portal-text`). Danach startet die Zentrale
  `lia-<agent>.service`.
- `lia/unterricht` (Dienst `lia-unterricht`) ist ein Platzhalter und antwortet „kommt bald“, ohne Claude.
- Jans `dokumente/` ist nur ein Gerüst (python-docx, python-pptx, openpyxl), noch kein `agent.py`.

## Mit Jan klären, nicht annehmen
- **Materialarten und Formate:** Arbeitsblatt, Folien, Raster? docx, pptx, PDF? PDF geht nur mit Typst oder
  LibreOffice. Beides braucht Jans Okay, es gibt kein sudo.
- **Zuschnitt:** Löst der Agent den Platzhalter unterricht ab (Weg „material“), oder wird er ein eigener Agent?
- **Renderer:** gemeinsam mit Jans dokumente-Agent bauen (Empfehlung der Architektur) oder vorerst nur für Lia?
- **Vorlage:** Gibt es eine Schulvorlage von Lia?

## Bekannte Lücken für einen echten Lauf
- **Einstellungen:** `lia/shared/einstellungen.toml` fehlt. `claude_lauf` liest Modelle, Plätze und Stufen
  aus `SHARED_DIR/einstellungen.toml` und würde in Lias Instanz scheitern.
- **Verbrauch:** Das Protokoll und die Plätze liegen je Instanz unter `SHARED_DIR`, obwohl beide dasselbe
  Konto nutzen. Jans Stufenberechnung sieht Lias Läufe nicht. Vorschlag: gemeinsames Protokoll und
  gemeinsame Plätze.
- **„Jan“ in den Texten:** In `claude_lauf.GRUNDREGEL` steht „Jans Agenten-System“, in `auftraege.neuer_auftrag`
  „Angehängte Dateien von Jan“. Beides sollte je Instanz kommen, für Jan unverändert.
- **Dateien:** `portal.py` schickt noch keine Ergebnisdateien (`ergebnis_dateien`), das ist Pflicht. Eingehende
  Dateien lehnt es ab, sie anzunehmen wäre gut für Vorlagen.

## Fertig heißt
- Lia tippt „Neues Material“, beschreibt ihren Wunsch und bekommt die vereinbarte Datei mit kurzem
  Begleittext in Telegram.
- Ein Fehler meldet sich verständlich bei Lia, und Jan erfährt davon.
- Jans Zentrale und seine Agenten verhalten sich unverändert.
- Es gibt Tests, `./pruefen.sh` ist grün, jeder Schritt ist committet.
- `STATUS.md` (Punkt 8) und die STATUS.md des Agenten sind aktualisiert.
- Ein echter Lauf ist einmal gemacht und die Kosten pro Auftrag sind gemessen.
- Datenschutz: Material ohne Schülerdaten ist unkritisch. Mail und IServ gehören nicht zu dieser Aufgabe.
