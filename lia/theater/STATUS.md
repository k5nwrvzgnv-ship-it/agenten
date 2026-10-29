# Status: Agent theater (Lias Instanz)

## Zweck
Hilft Lia in ihrem zweiten Fach Theater (Darstellendes Spiel). Erste Aufgabe: aus „Der nackte Wahnsinn“
(Michael Frayn, Noises Off) eine eigene Fassung für ihren DS-Kurs entwickeln. Lia will nicht klassisch kürzen,
sondern Spielanlässe finden, Szenen daraus entwickeln und die lustigen Textstellen behalten.

## Stand (29.10.2026)
- Plan, Pakete (wie lia/examen) und Kostengrenze 5 USD je Aufruf von Jan freigegeben (29.10.).
- Code fertig, 39 Tests grün, in pruefen.sh eingetragen. Noch kein echter Lauf.
- Zerlegung am echten Text geprüft: 2253 Einheiten (Akt 1: [1]–[1113], S. 4–74; Akt 2: [1114]–[1821], S. 75–130;
  Akt 3: [1822]–[2253], S. 131–170). Sprechzeit geschätzt 68 / 40 / 29 Min. Kein Wort geht verloren (nur die
  Sprecherkennungen wandern ins Feld sprecher). Grenze: Regie ohne Klammer und ohne Namen in Großbuchstaben
  bleibt Teil der Rede davor (z. B. „Läuft eilig von der Bühne.“); der Text bleibt trotzdem wörtlich.
- Lias Material liegt in data/ (nicht im Repo, Dateien chmod 600):
  - data/eingang/: Originale von Lia (Erste_Gedanken.docx, Figuren.docx, Vom_Text_zur_Szene.pages,
    11._Klasse-25_26.zip, e-245-der-nackte-wahnsinn.pdf).
  - data/entpackt/klasse/k11/: ihre DS-Grundlagen. Den Ordner „Bewertung und Klausuren“ (Noten,
    Erwartungshorizonte mit Schülernamen) und Zwischennoten_11er.docx habe ich aus der entpackten Kopie gelöscht;
    im Original-Zip sind sie noch. Diese Daten gehen nie an Claude.
  - data/vorgaben/nachricht.md: Lias Nachricht vom 29.10. (Konzept, offene Fragen, Unsicherheit), wörtlich.
    data/vorgaben/vom_text_zur_szene.jpg: Vorschaubild ihres Schemas (die .pages selbst ist nicht lesbar).
  - data/text/: Textfassungen aller docx/pdf (agentkit.textfassung).
- Lias Konzept in Kürze: drei Akte wie im Original (Generalprobe, Premiere, Dernière), Eröffnung 3 Min, je Akt
  10 Min, 35–40 Min, 18 SuS. Heraustreten aus den Rollen, Chor über Scheitern und Angst. Muss-Liste in
  theater.toml (M0-1 bis M3-4). Offen bei Lia: Figurensplitting, Schwerpunkt Akt 2, Partitur oder Montage.
  Unsicher: wie kürzen, „zu lasch“, wie das Stück im Stück aussieht (die SuS sollen es selbst erfinden).

## Aufbau
- Aufruf von Hand: `AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python runde.py`
  Ergebnis in data/runde-<zeit>/fuer-lia/ (vier docx, je mit PDF-Vorschau), Meldung an Jan. Noch nicht an Lia.
- stueck.py: Textfassung -> nummerierte Einheiten (rede/regie/text, Sprecher, gedruckte Seite, PDF-Seite).
  Entfernt Fußzeile und Anmerkung der Ansichtssendung (auch mitten in der Zeile). Sprechzeit 130 Wörter/Min.
- runde.py: bereitet data/runde-<zeit>/kontext/ vor (Stück in 6 nummerierten Teilen, vorgaben.md aus theater.toml
  und Lias Texten, grundlagen.md aus 12 ausgewählten Infoblättern und Aufgaben), dann drei Claude-Läufe (Opus) in
  einer Sitzung, je höchstens eine Nachbesserung, Kostengrenze 5 USD (Jan 29.10.2026).
  1. karte.py: szenenkarte.json (8–45 Spielanlässe mit Nummernbereich, Figuren, worum, Komik, Muss-Punkte,
     Pointen). Python prüft Akt, Nummern, Überschneidungen, Muss-Liste (Punkte, die nicht im Original stehen,
     unter nicht_gefunden mit Grund).
  2. fassung.py: ablauf.json (Bausteine original/neu/gemischt, Originaltext nur als Nummern mit Strichen, neuer
     Text ausgeschrieben; Varianten zu splitting, akt2, partitur mit Empfehlung; 3–6 Vorschläge gegen „zu lasch“).
     Python prüft: Summe 35–40 Min, jeder Teil höchstens 3 Min neben Lias Plan, jede Nummer nur einmal, Sprechzeit
     des Originals unter der Spielzeit des Bausteins, jeder Muss-Punkt genau einmal.
  3. aufgabe.py: Szenenaufgabe „Stück im Stück“ als Renderer-Beschreibung (FORMAT.md-Abschnitte im Prompt, weil
     Claude nur im Agent-Ordner liest), geprüft mit renderer.pruefen.
- Dokumente: 1 Szenenkarte, 2 Ablauf und Varianten, 3 Spielfassung (Originaltext wörtlich von Python, [S. n],
  [Strich: n Einheiten], neuer Text in grünen Kästen, am Ende Strichübersicht je Akt), 4 Szenenaufgabe.
  Dazu spielfassung.txt. Profil profil.toml (wie lia/examen, Fach Darstellendes Spiel).
- theater.toml: Stück, Rahmen, Muss-Liste, Kontextdateien (Teil des Dateinamens in data/text/, genau ein Treffer).
  Bewusst nicht als Kontext: Bewertung und Klausuren, Planungen (enthalten Namen), Chortexte der SuS.
- Instanz: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz. Meldungen gehen in Jans Zentrale.
- .venv: Pakete aus requirements.txt (gleich lia/examen), agentkit und renderer per agentkit.pth.
- Laufzeitdaten: lia/theater/data/, Logs: lia/theater/logs/ (beide nicht im Repo)

## Rechte
- Die PDF ist eine Ansichtssendung des Deutschen Theaterverlags; laut Vermerk sind Kopien für Einstudierung,
  Aufführung oder Unterricht ohne Vertrag verboten.
- Jan 29.10.2026: Lia hat alles mit dem Verlag geklärt (Bearbeitung und Ausgabe des Textes). Der Agent darf
  deshalb Stücktext ausgeben, auch Strich- und Spielfassungen. Den Vertrag selbst habe ich nicht gesehen.
- Originaltext tippt Claude nicht ab: Claude wählt Stellen über Nummern aus, Python übernimmt sie wörtlich aus
  der Textfassung. Neue Texte (Chortext, Einstieg, Heraustreten) sind als neu gekennzeichnet.

## Entscheidungen
- 29.10.2026: eigener Ordner lia/theater statt Teil von lia/unterricht (Jan: zweites Fach, eigener Agent).
- 29.10.2026: Bewertungsdaten aus Lias Zip werden nicht verwendet (Schülerdaten).
- 29.10.2026: Seiten in den Dokumenten = gedruckte Seiten der Ansichtssendung (E 245). Ob die gekauften
  Textbücher gleich umbrochen sind, ist nicht geprüft.

## Offene Punkte
1. Erster echter Lauf, Ergebnis an Jan zur Vorschau, danach an Lia (Weg wie lia/recherche, über Auftrag an
   Lias Zentrale).
2. Fragen an Lia (über Jan):
   - Frederick (Philip/Scheich) fehlt in Figuren.docx. Fällt die Figur weg, oder ist sie nur vergessen?
   - Termin der Aufführung und bis wann sie den Ablaufvorschlag braucht.
3. Folgerunden aus Lias Feedback: heute startet runde.py immer von vorn. Eine Runde, die auf einem bestehenden
   Ablauf weiterarbeitet, fehlt noch.

## Gelernte Regeln
- (noch keine)
