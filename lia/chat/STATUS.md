# Status: Agent chat (Lia)

## Zweck
Gespräche für Lia in der Web-App (shared/webapp, „Gespräch in der Mitte“, Bauplan shared/webapp/bauplan-gespraech.md,
Jans Okay 10.11.2026): mehrere Gespräche, je an einer Klasse, Reihe oder Stunde oder ohne Ort, mit vollem Verlauf
über die claude-Sitzung, Fotos, Dateien, Lias Ablage am Ort, „Was haben wir bisher?“ und „Auftrag ordnen“. Daneben
läuft die alte Spalte „Fragen“ weiter, bis die Web-App umgeschaltet hat. Startet nie einen Auftrag und handelt nie
nach außen; „Daraus Auftrag machen“ macht die Web-App. Plan der Fragen: plan.md (Jan 30.10.2026).

## Stand (10.11.2026)
- Lias Wissen im Gespräch (Jan 10.11.2026, „Lias Chat soll alles wissen“, Zugang „Lia + Auswertung“): Claude darf
  mit Read in allen Ordnern unter lia/ lesen außer lia/chat (davon nur data/gespraeche, Lias Gespräche) und Ordnern
  mit Punkt (lia/.claude: Kopien des ganzen Repos). Nicht: Jans Agenten, shared/, ~/.claude; .env sperrt agentkit in
  jedem Lese-Ordner. Neue Lia-Ordner gehören von selbst dazu. Die Übersicht (wissen.karte: Grundlagen mit einem Satz,
  Zweck jedes Lia-Agenten, Katalog von lia/unterricht mit absoluten Pfaden, weitere Dateien je Ordner bis 20.000
  Zeichen, Lias andere Gespräche) geht mit der ersten Nachricht einer Sitzung mit, heute ca. 45 KB (ca. 12.000
  Tokens); fortgesetzt nur, was seit der letzten Übersicht dazukam (data/gespraeche/<id>/karte.txt). Der Prompt
  sagt: passt die Nachricht, erst lesen, dann antworten, Quelle nennen, nie „ich sehe nichts“ ohne Blick in die
  Übersicht. Mit Wissen 12 Schritte und 2 min mehr. Fortsetzen der Sitzung geht weiter: Alle Gesprächsläufe sind
  lese_ordner-Läufe im selben Arbeitsordner data/nur_lesen/, die Zahl der Lese-Ordner ändert daran nichts.
  Grenze: Ohne Glob und Grep (agentkit sperrt sie im Nur-Lesen-Lauf) findet Claude nur Dateien aus der Übersicht;
  in großen Ordnern stehen nur die 10 jüngsten Namen (Bedarf Punkt 38 der Haupt-STATUS).
- Gespräche gebaut, mit Tests ohne Netz (tests/test_gespraech.py) und echtem Lauf über den Dienst (10.11.):
  drei Nachrichten an der Reihe Straftheorien (eine mit Foto, zwei fortgesetzt), dann bisher und auftrag.
  Je 8–15 s Lauf, 0,05–0,09 USD je Nachricht (steigt mit dem Verlauf), Sonderläufe ca. 20 s, 0,07 USD; zusammen
  0,35 USD. Foto richtig gelesen, Gedächtnis über die Sitzung hielt, Bausteine und Überschriften kamen wie verlangt.
  Testgespräch, Sitzung und Antworten danach gelöscht. Die Web-App nutzt die Gespräche noch nicht.
- Read-Grenze: agentkit.claude_lauf `lese_ordner` (Hauptordner-Sitzung „agentkit: Read mit Pfadgrenze testen“).
  Im echten Lauf wollte Claude eine Datei außerhalb gar nicht erst öffnen (lehnte selbst ab); dass die Grenze
  technisch hält, belegt der agentkit-Test, nicht dieser Lauf.
- Websuche in Gesprächen (agentkit 059a9b2: lese_ordner mit WebSearch/WebFetch): lia/chat schaltet sie je Lauf
  über die eigene cfg-Kopie (ohne Häkchen nur Read, mit Häkchen dazu WebSearch und WebFetch auf [webfetch]
  recherche). Echt 10.11.: Frage zur bpb mit Netz 45 s, 5 Schritte, 0,14 USD, mit Quellen; Folgenachricht ohne
  Netz fortgesetzt, 4 s, aber 0,21 USD (die Webinhalte gehen im Verlauf mit). WebFetch auf ein PDF lieferte nur
  unlesbaren Datenstrom, Claude sagte das offen. Testgespräch danach gelöscht.

## Stand der alten Spalte „Fragen“ (03.11.2026)
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
- Code: agent.py (Einstieg, Warteschlange data/fragen/, alte Fragen, Aufräumen), gespraechlauf.py (Gespräche
  beantworten, Ablage, Sonderläufe, Aufräumen der Gespräche), wissen.py (Lese-Ordner und Übersicht über Lias Wissen;
  rein, Grundlagen-Liste KERN von Hand gepflegt), gespraechablage.py (Gespräch als Datei, Sperre; nur
  Bordmittel), kontext.py (Ort über agentkit.struktur, Prompts; rein), chatverlauf.py (Verlauf der alten Spalte),
  schnittstelle.py (für die Web-App, nur Bordmittel), tests/.
- .venv: lia/chat/.venv, agentkit per .pth, Pakete aus requirements.txt (pypdf, python-docx, python-pptx samt
  Abhängigkeiten, Versionen wie lia/unterricht; Jan 02.11.2026). Kein openpyxl, also kein Excel.
- Dienste: Vorlagen in systemd/, installiert in ~/.config/systemd/user/, AGENTKIT_INSTANZ=lia/instanz. Gespräche
  laufen über dieselben Dienste (lia-chat.path auf data/fragen/), nichts an den Diensten geändert.
- Laufzeitdaten: data/ (fragen/, antworten/, gespraeche/, dateien/<id>/, nur_lesen/ (muss leer bleiben), tmp/,
  verlauf.jsonl). Logs: logs/ (ohne Nachrichtentext, Dateinamen und Adressen).
- claude-Sitzungen: alte Fragen und Sonderläufe in ~/.claude/projects/-home-agent-agenten-lia-chat/ (gleich nach dem
  Lauf gelöscht), Gespräche in ~/.claude/projects/-home-agent-agenten-lia-chat-data-nur-lesen/ (Arbeitsordner der
  lese_ordner-Läufe), gelöscht mit dem Gespräch.

## Gespräche (Schnittstelle für shared/webapp)
`sys.path` um lia/chat ergänzen, dann `import schnittstelle` (nur Bordmittel). Alle Funktionen haben `ordner=`
(Standard lia/chat/data). Ungültiges: `schnittstelle.GespraechFehler` (ValueError), Text ist ein Satz für Lia.
- `ort`: `None` (ohne Ort) oder `{"ebene": "klasse"|"reihe"|"stunde", "id": "<id aus agentkit.struktur>"}`, nur
  diese zwei Felder. Geprüft wird nur die Form; ob es die id gibt, sieht der Agent (sonst Hinweis „Ort gibt es
  nicht mehr“ an Claude). Kontext je Ebene aus lia/instanz/reihen.toml: Klasse = Fach, Klasse, Lerngruppe, Reihen
  mit Stand und Reihenfrage; Reihe = wie bisher (Reihenfrage, Lerngruppe, Notizen, Behandelt, Merksätze, Stunden);
  Stunde = Reihe plus „Gerade offen: Stunde n: Thema“.
- `gespraech_anlegen(name="", ort=None) -> id` (12 Hex). Name bis 80 Zeichen; leer = Name aus der ersten
  Nachricht (erste Zeile, bis ca. 50 Zeichen, `name_vorschlag` bleibt True, bis Lia umbenennt).
- `gespraeche(ort=None) -> list` jüngste zuerst. `ort=None`: alle; `schnittstelle.OHNE_ORT` ("ohne"): nur ohne Ort;
  ein ort-Dict: genau dort (nicht darunter, das setzt die Web-App aus der Struktur zusammen). Je Eintrag:
  `{"id", "name", "ort", "angelegt", "zuletzt", "nachrichten" (Zahl der Einträge), "laeuft" (Antwort steht aus),
  "neu" (Antwort, die Lia noch nicht gesehen hat), "vorschau" (letzter Eintrag, bis 160 Zeichen, ein Absatz)}`.
  Neue Gespräche ohne Nachricht heißen in der Liste „Neues Gespräch“.
- `gespraech(id) -> dict | None`: `{"id", "name", "name_vorschlag", "ort", "angelegt", "zuletzt", "gesehen" (Zahl
  gesehener Antworten), "laeuft", "eintraege": [...]}`, Einträge älteste zuerst:
  - Lia: `{"id": nachricht_id, "rolle": "lia", "zeit", "text", "fotos": [Namen], "dateien": [Namen],
    "gruendlich", "netz", "stand": "wartet"|"fertig"|"fehler", "fehler": None|Fehlerart}`
  - Claude: `{"id": nachricht_id (dieselbe wie Lias Nachricht), "rolle": "claude", "zeit", "text", "gruendlich",
    "netz"}`. Nur erfolgreiche Antworten stehen hier; Fehlertexte nur in der Antwort (antwort_holen).
  - Anhänge liegen in `data/gespraeche/<id>/<nachricht_id>/<Name>` (für Anzeige und Download der Web-App).
- `umbenennen(id, name)`, `umhaengen(id, ort)` (Claude bekommt den neuen Ort mit der nächsten Nachricht),
  `gesehen(id)` (setzt „neu“ zurück), `loeschen(id) -> bool` (Gespräch und Dateien sofort, die claude-Sitzung beim
  nächsten Aufräumen). Unbekannte id: GespraechFehler (loeschen: False).
- `nachricht(id, text, dateien=None, gruendlich=False, netz=False) -> nachricht_id`. text bis 60.000 Zeichen (leer
  nur mit Anhang). `dateien`: Liste `(Name wie hochgeladen, Pfad)`; Fotos .jpg/.jpeg/.png bis 5, .pdf/.docx/.pptx bis
  3, je bis 20 MB. HEIC/HEIF: GespraechFehler mit Satz für Lia (iPhone auf „Maximale Kompatibilität“ oder
  Bildschirmfoto). Die Dateien werden verschoben (bei Fehler bleibt alles liegen). Solange eine Antwort aussteht
  (`laeuft`), ist keine zweite Nachricht möglich (GespraechFehler). `gruendlich` = Opus (Schalter je Gespräch hält
  die Web-App und schickt ihn mit jeder Nachricht), sonst Sonnet.
- `bisher(id) -> nachricht_id` („Was haben wir bisher?“: ### Entschieden, ### Verworfen, ### Offen, Bausteine) und
  `auftrag_ordnen(id) -> nachricht_id` (Auftragstext in Lias Ich-Form, schlichter Text bis ca. 3.000 Zeichen, ohne
  Tabellen und Codeblöcke: Wunsch, entschieden, verworfen, offen; für das Feld in „Neu“). Laufen ohne Sitzung über
  den Verlauf als Text, ihre Antwort kommt nicht ins Gespräch. Gespräch ohne Antwort: GespraechFehler.
- `antwort_holen(nachricht_id) -> dict | None` (None = noch nicht fertig; Vorschlag: alle 2 s):
  `{"id", "gespraech", "art": "nachricht"|"bisher"|"auftrag", "zeit", "ok", "text", "fehler", "wieder_frei",
  "chip" ("Ethik › 8 › Straftheorien › Stunde 2"), "gruendlich", "netz"}`. `fehler`: None, "limit" (`wieder_frei`
  z. B. "31.10. 14:30"), "belegt", "zeit", "technik" (Jan hat eine Meldung), "ungueltig" (Gespräch gelöscht). Bei
  Fehlern steht in `text` ein Satz für Lia, Lias Eintrag hat dann `stand` "fehler" und sie kann neu schicken.
- Antworttext ist Markdown: Überschriften (##, ###), Listen, Tabellen, **fett**, Links, mit Netz „Quellen:“ als
  `[Titel](URL)`. Bausteine als Codeblock mit Sprache `baustein <art>`, art aus reihenfrage, merksatz,
  arbeitsauftrag, fall, text; im Block nur der Text (Absätze, Listen). Bausteine können eingerückt in Listen stehen.
- Zeiten: schnell meist 10–20 s (mit Lesen in Lias Wissen länger), Grenze 6 min (gründlich 10 min, mit Netz je
  2 min mehr), plus bis 1 min Warten auf einen Platz.
- Ablage am Ort: Dateien direkt in `lia/instanz/ablage/<id>/` für den Ort und die Ebenen darüber (Fach, Klasse,
  Reihe, Stunde) gehen mit: PDF/Word/PowerPoint als Text (zusammen bis 40.000 Zeichen), JPG/PNG als Foto (bis 5 je
  Lauf, die jüngsten; in den Gesprächsordner kopiert, weil Read nur dort darf), Excel nur mit Hinweis (kein
  openpyxl). Jede Datei geht einmal je Gespräch mit (geänderte erneut); eine abgelegte Datei, die später dazukommt,
  mit der nächsten Nachricht.
- Aufbewahrung (Jan 09.11.2026): 30 Tage ab der letzten Nachricht, dann Gespräch, Dateien und Sitzung weg (täglich
  03:40, lia-chat-aufraeumen.timer).

## Alte Spalte „Fragen“ (Schnittstelle bis zum Umschalten)
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
- 10.11.2026 (Jan): „Lias Chat soll alles wissen“, Zugang „Lia + Auswertung“: alle Lia-Ordner samt UBs+Feedback
  (Namen von Erwachsenen) und lia/auswertung (claude.ai-Export, kann auch Chats von Jan enthalten); nicht der ganze
  Server (Jans Mails, Uni, Zugänge). Schülernamen gibt Claude nie wieder (Prompt).
- 09./10.11.2026 (Jan, gespraech-plan 3 und Bauplan): Sitzung fortsetzen statt letzter 6 Fragen, Read für Fotos
  mit Pfadgrenze, Sonnet Standard und gründlich (Opus) je Gespräch, Kosten auf Lias Kontingent, 30 Tage ab
  letzter Nachricht. HEIC vorerst abgelehnt (bräuchte ein Paket).
- 10.11.2026: Gespräche laufen über dieselbe Warteschlange data/fragen/ (Eintrag mit "art"), also ohne neuen Dienst.
  Eine Nachricht nach der anderen je Gespräch (eine Sitzung verträgt keine zwei Läufe zugleich).
- 10.11.2026: Sonderläufe ohne Sitzung über den Verlauf als Text (bis 90.000 Zeichen, älteste zuerst weg), damit
  sie nicht im Gespräch landen. Geht eine Sitzung verloren oder liefert Fortsetzen nichts, startet der Agent
  einmal neu mit dem Verlauf als Text. Prompt höchstens 120 KB (claude -p: 128 KB), gekürzt wird zuerst Verlauf,
  dann Ablage, dann Dateien, nie Lias Nachricht.
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
0. Glob und Grep im Nur-Lesen-Lauf (agentkit, Punkt 38 der Haupt-STATUS, Jan entscheidet): Dann sucht Claude in
   Lias Ordnern selbst, die Übersicht kann kleiner werden (Grundlagen, Agenten, Katalog). Kosten der Übersicht
   (ca. 12.000 Tokens je neue Sitzung) nach zwei Wochen ansehen.
1. Kosten: Nachrichten nach einer Websuche sind teurer (Webinhalte im Verlauf). Nach zwei Wochen ansehen.
2. Web-App: auf die Gespräche umschalten (Bauplan Schritt 6). Danach als Vorschlag an Jan: frage_stellen,
   chatverlauf, data/verlauf.jsonl und die alten Punkte (stunde_id, Häkchen und Datei-Feld der alten Spalte,
   Punkt 24 der Haupt-STATUS) wegräumen.
3. Echt noch nicht gesehen: lange Gespräche (Kontextgrenze, Kosten nach zwei Wochen ansehen, gespraech-plan 3.4),
   Ablage am Ort mit echten Dateien (die Web-App schreibt sie noch nicht), gründlich (Opus) im Gespräch.
4. Aufräumen löscht in ~/.claude/projects/-home-agent-agenten-lia-chat/ jede Sitzung ohne Gespräch, die älter als
   1 h ist, also auch Sitzungen eines Entwickler-Chats, der in lia/chat gestartet wurde (vorher: alle, täglich).
   Sauberer: `--no-session-persistence` in agentkit.claude_lauf für Läufe ohne Fortsetzen (Hauptordner-Chat).

## Gelernte Regeln
- (noch keine)
