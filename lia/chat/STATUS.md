# Status: Agent chat (Lia)

## Zweck
Beantwortet Lias Fragen in der rechten Spalte „Fragen“ der Web-App (shared/webapp), kurz und mit dem Ort als
Kontext („Ethik › 8 › Straftheorien“) oder ohne Ort, auch ganz allgemeine Fragen. Auf Lias Wunsch mit Websuche und
mit Dateien (PDF, Word, PowerPoint). Startet nie einen Auftrag und handelt nie nach außen; „Daraus Auftrag machen“
macht die Web-App. Plan: plan.md (Jans Okay 30.10.2026), Ausbau Jans Okay 02.11.2026.

## Stand (03.11.2026)
- Läuft seit 30.10. (Dienste lia-chat.path, lia-chat-aufraeumen.timer täglich 03:40). Die Web-App ist angeschlossen
  (`WEBAPP_CHAT=an`), schickt aber noch kein `netz` und keine `dateien` (Bedarf in Punkt 24 der Haupt-STATUS).
  Lia selbst hat bisher keine Frage gestellt.
- Ausbau 02.11.2026, je mit Tests und echtem Lauf (Testeinträge danach aus dem Verlauf gelöscht):
  - Allgemeine Fragen ohne Ort: kein erzwungener Schulbezug. Echt: 8 s, 0,03 USD.
  - Websuche (`netz`): WebSearch und WebFetch, WebFetch nur auf `[webfetch] recherche`. Echt (KMK und KI):
    23 s, 3 Schritte, 0,07 USD, mit Quellen als Links; kmk.org stand nicht auf der Liste (1 Aufruf abgelehnt), die
    Antwort stützte sich darum auf Berichte darüber.
  - Dateien: Text über agentkit.textfassung in den Prompt. Echt (Word, 4 Aufgaben): 10 s, 0,04 USD, Datei danach weg.
  - „Gründlich“ echt: 138 s, 0,05 USD. Brachte Überschriften und eine Tabelle; seitdem verlangt der Prompt nur
    fett, Listen und Links (schmale Spalte).
- Tests schreiben nicht mehr ins echte logs/chat.log (tests/__init__.py).
- Strukturplan Bauschritt 2 (03.11.2026, docs/struktur-pflege-plan.md): Reihen kommen über agentkit.struktur
  (altes und neues Format), erkannt nur an ihrer id. Lerngruppe im neuen Format von der Klasse
  (lia/instanz/lerngruppen.toml), Stunden aus reihe["stunden"] (nur sichtbare, Nummer zählt struktur). Eigene
  kennung, Ersatzweg über lia/unterricht/reihen.toml und Stück aus theater.toml sind weg. Kontext-Text für alle
  14 echten Reihen byte-gleich wie vorher. Kaputte reihen.toml oder lerngruppen.toml (auch Rechte nicht 600):
  StrukturFehler, Antwort ohne Reihe, Meldung an Jan (ohne Lerngruppen-Text). Kein Neustart nötig
  (lia-chat.service ist oneshot und startet je Frage neu).

## Aufbau
- Code: agent.py (Einstieg, Fehlertexte, claude_lauf, Text aus Dateien), kontext.py (Reihe über
  agentkit.struktur, Kontext-Text, Prompt; rein), chatverlauf.py (Verlauf, Aufräumen), schnittstelle.py (für die Web-App, nur
  Bordmittel), tests/.
- .venv: lia/chat/.venv, agentkit per .pth, Pakete aus requirements.txt (pypdf, python-docx, python-pptx samt
  Abhängigkeiten, Versionen wie lia/unterricht; Jan 02.11.2026). Kein openpyxl, also kein Excel.
- Dienste: Vorlagen in systemd/, installiert in ~/.config/systemd/user/, AGENTKIT_INSTANZ=lia/instanz.
- Laufzeitdaten: data/ (fragen/, antworten/, dateien/<id>/, tmp/, verlauf.jsonl), Logs: logs/ (ohne Frage- und
  Antworttext, ohne Dateinamen und Adressen).

## Schnittstelle (für shared/webapp)
- `sys.path` um lia/chat ergänzen, dann `import schnittstelle` (nur Python-Bordmittel, Module schnittstelle und
  chatverlauf):
  - `frage_stellen(text, ort=None, gruendlich=False, ordner=ORDNER, netz=False, dateien=None) -> id` (12
    Hex-Zeichen). Ungültig: `FrageFehler` mit Satz für Lia (leer, über 4.000 Zeichen, Ort falsch, Dateien falsch).
  - `ort`: None (ohne Ort) oder `{"reihe": "<id>", "stunde_id": "<id>", "stunde": n, "chip": "Ethik › 8 ›
    Straftheorien", "stunde_thema": "…", "materialien": ["Titel", …]}`; nur `reihe` ist Pflicht. Reihe, Lerngruppe,
    Stunden usw. liest der Agent selbst über agentkit.struktur aus lia/instanz/reihen.toml. `stunde_id` (neu
    03.11.2026, freiwillig): Steht die Stunde mit dieser id in der Reihe, nimmt der Agent Nummer und Thema von dort
    (auch ausgeblendete); sonst wie bisher `stunde` mit `stunde_thema` (oder dem Thema der Stunde mit dieser
    Nummer). Die Web-App schickt heute noch keine `stunde_id`.
  - `netz=True`: Lias Häkchen „Im Netz nachsehen“. Dauert länger (ca. 20–60 s, Grenze 4 bzw. gründlich 6 min).
  - `dateien`: Liste von `(Name wie hochgeladen, Pfad der hochgeladenen Datei)`, höchstens 3, nur .pdf/.docx/.pptx,
    je bis 20 MB. Die Dateien werden nach data/dateien/<id>/ verschoben (Name bereinigt); bei `FrageFehler` bleibt
    alles, wo es war, dann räumt die Web-App ihre Uploads selbst weg.
  - `antwort_holen(id) -> dict | None` (None = noch nicht fertig, Vorschlag: alle 2 s nachfragen),
    `wartet(id) -> bool`, `verlauf() -> list` (beantwortete Fragen, älteste zuerst: id, zeit, reihe, chip,
    gruendlich, netz, frage, antwort, dateien (Namen), dateitext).
- Antwort: `{"id", "zeit", "ok", "text", "gruendlich", "netz", "reihe", "chip", "fehler", "wieder_frei"}`. `fehler`:
  None, "limit" (Kontingent voll, `wieder_frei` z. B. "31.10. 14:30"), "belegt" (alle Plätze besetzt, 1 min
  gewartet), "zeit", "technik" (Jan bekommt eine Meldung), "ungueltig". Bei Fehlern steht in `text` ein fertiger
  Satz für Lia. `text` ist Markdown: fett, Listen und mit `netz` Links `[Titel](URL)` unter „Quellen:“.
- Dateien statt Aufruf: Die Web-App schreibt nur data/fragen/<id>.json (über data/tmp, atomar); systemd startet den
  Agenten. Antwortzeit schnell ca. 10 s, gründlich (Opus) ca. 2–3 min, Zeitgrenze 2 bzw. 5 min.

## Entscheidungen
- 30.10.2026 (Jan): Plan wie plan.md, mit Ordner, .venv und Diensten. Verlauf 30 Tage, Wartegrenze auf einen Platz
  1 min (kein eigener Platz für den Chat).
- 30.10.2026: Warteschlange in Dateien statt Unix-Socket (kein Dauerdienst, Muster wie shared/auftraege).
- 30.10.2026: Claude ohne Werkzeuge (`--tools ""` über eine Kopie der Einstellungen in agent.py), höchstens 3
  Schritte. Schnell = art "routine" (Sonnet, in der Sparstufe Haiku), gründlich = "anspruchsvoll" (Opus).
- 30.10.2026: claude legt jede Sitzung unter ~/.claude/projects/-home-agent-agenten-lia-chat/ ab; der Agent löscht
  sie nach jedem Lauf, der Timer täglich alle übrigen.
- 30.10.2026: Hinweis auf „Daraus Auftrag machen“ nur, wenn Lia ausdrücklich Material will (vorher kam er bei
  jeder Antwort).
- 02.11.2026 (Jan, „Ja, so umsetzen“): Websuche nur auf Lias Häkchen, WebFetch nur auf die Domains von Lias Recherche
  (in agent.py übernommen, shared/einstellungen.toml unverändert; fehlt die Liste, nur WebSearch), höchstens 8
  Schritte. Der Text der Frage geht dabei als Suchanfrage hinaus (Hinweis „keine Namen“ macht die Web-App).
  03.11.2026 (Jan): kmk.org auf `[webfetch] recherche` (gilt auch für lia/recherche).
- 02.11.2026 (Jan): Dateien: PDF, Word, PowerPoint (Pakete wie lia/unterricht), kein Excel, keine Fotos (bräuchten
  das Werkzeug Read). Datei gleich nach der Antwort gelöscht (auch bei Fehlern, spätestens nach 24 h vom Aufräumen),
  ihr Text bleibt im Verlauf (30 Tage) und geht bei Folgefragen am selben Ort mit (jeweils der jüngste). Alle
  Dateien einer Frage zusammen höchstens 60.000 Zeichen.

## Offene Punkte
1. Web-App: `stunde_id` im Ort mitschicken, sobald ihre Stunden aus reihen.toml kommen (Strukturplan Bauschritt 5).
2. Web-App: Häkchen „Im Netz nachsehen“, Datei-Feld und Links in der Anzeige (Bedarf in Punkt 24 der Haupt-STATUS).
3. Fotos (JPG/PNG) im Chat: bräuchten Read auf data/dateien/<id>/; erst nach dem Test mit Lia und Jans Okay.
4. Sauberer als das Löschen der Sitzungen: Option `--no-session-persistence` in agentkit.claude_lauf
   (Hauptordner-Chat, kein Muss).

## Gelernte Regeln
- (noch keine)
