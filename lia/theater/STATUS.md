# Status: Agent theater (Lias Instanz)

## Zweck
Hilft Lia in ihrem zweiten Fach Theater (Darstellendes Spiel). Erste Aufgabe: aus „Der nackte Wahnsinn“
(Michael Frayn, Noises Off) eine eigene Fassung für ihren DS-Kurs entwickeln. Lia will nicht klassisch kürzen,
sondern Spielanlässe finden, Szenen daraus entwickeln und die lustigen Textstellen behalten.

## Stand (30.10.2026)
- Dienst lia-theater eingerichtet (Jans Okay 30.10.): agent.py arbeitet Aufträge aus Lias Warteschlange selbst ab,
  vor allem Nachbesserungen aus ihrem Feedback. Erster Auftrag 20261030-111155-theater-5d88d5 (Lias Frage, wie
  lange die Fassung dauert): 2 Läufe, 0,55 USD, Antwort 38 Min, davon gut 11 Min neue Szenen, etwa 15 Min Text aus
  dem Stück und 8 Min neuer Text; von Lias Zentrale um 12:19 zugestellt. Die Nachbesserung lief wegen eines Satzes
  mit 17 Wörtern (Sprachregel), danach ging die Antwort mit Warnung im Log raus. Den Chor (gemischt) zählt Claude
  zu den neuen Teilen; die Kennzahlen von Python trennen nach Art (neu 8,5 Min, gemischt 23 Min).
- Überarbeitung mit Prüfschritt, echter Probelauf 30.10. ohne Zustellung (nachbesserung.bearbeiten direkt, Auftrag
  probe-20261030, Ordner data/runde-20261029-140740/nachbesserung-probe-20261030/, Wunsch: Kamera-Szene raus, mehr
  Publikum in Akt 2). Lias Änderung sauber (nur B12 geändert, 38 Min bleiben). Prüfung 1: 8 von 11 Kriterien unter
  „gut“ (die Runde vom 29.10. lief noch ohne Prüfschritt). Der Autor übernahm von sich aus nur Prüfer-Punkte zu
  Akt 2 („sonst nichts ändern“), seine Überarbeitung war nach der Nachbesserung 9 Zeichen zu lang, und der Lauf
  brach ab (5,44 USD). Deshalb gilt jetzt: Bricht der Prüfschritt ab, geht der letzte geprüfte Stand an Lia
  (letzter_guter_stand), Jan sieht es im Log-Hinweis. Am Probeordner nachgeprüft, die beiden docx baut der echte
  Renderer. Eine Überarbeitung, die alle Prüfrunden durchläuft, ist nur in Tests gelaufen.
- Plan und Pakete (wie lia/examen) von Jan freigegeben (29.10.). Kostengrenze seit 29.10. nachmittags aufgehoben
  (siehe Entscheidungen); der erste Lauf lief noch mit 5 USD.
- Code fertig, 55 Tests grün, in pruefen.sh eingetragen.
- An Lia geschickt (Jans Okay nach Vorschau, 29.10. 15:01, Auftrag 20261029-150107-theater-0baec0): die vier docx,
  ohne Feedback-Knöpfe, von Lias Zentrale um 15:01:33 zugestellt (4 Nachrichten). Die Zentrale warnte: Text zu lang
  und ein Satz mit 29 Wörtern (Sprachregel agentkit.sprache). Gesendet ist gesendet; nachricht_an_lia ist danach
  gekürzt und im Test gegen die Sprachregel geprüft. Lias Antwort kommt als Feedback (lia-feedback).
- Erster echter Lauf 29.10. (data/runde-20261029-140740/), an der Kostengrenze abgebrochen:
  - Szenenkarte 2,18 USD (398 s, 868k Tokens): 44 Spielanlässe (21/15/8), beim ersten Versuch geprüft, ohne
    Nachbesserung. M0-1, M3-3, M3-4 unter nicht_gefunden (Lias eigene Ideen, mit Anknüpfungspunkt). 16 Hinweise,
    fachlich genau (z. B. Lloyd spricht schon im Original aus dem Zuschauerraum; im Original springt Tim für
    Selsdon ein, nicht das Publikum; Meditation nur zweimal kurz erwähnt; Druckfehler BROOKE statt POPPY bei 1277).
  - Ablauf 3,27 USD (333 s, 659k Tokens, Fortsetzung derselben Sitzung schickt das ganze Stück noch einmal mit):
    19 Bausteine, 38 Min, beim ersten Versuch geprüft. Vom Original bleiben 240 von 2253 Einheiten, etwa 15 Min
    Sprechzeit. Empfehlungen: Montage aus Originalpointen; Akt 2 Schwerpunkt Publikumsaktion. Vorschläge gegen
    „zu lasch“: Countdown je Akt, Kostümteil als Zeichen für Rolle/Ich, wachsender Chor aus Splittern, anonyme
    Angst-Sätze der SuS für Heraustreten und Chor.
  - Summe 5,45 USD, Szenenaufgabe deshalb nicht gelaufen. Meldung an Jan ging raus.
  - Fortsetzung 29.10. 14:50 (Jans Okay, mit Lias Fachbuch): Szenenkarte und Ablauf übernommen, Szenenaufgabe in
    eigener Sitzung 1,39 USD (117 s, 575k Tokens; Schätzung „unter 1 USD“ lag daneben, das Buch kostet mit).
    Ergebnis 3 Seiten: 8 feste Bausteine (Türen, Sardinenteller, wiederkehrender Satz, Selsdons Stichwort,
    Schlusssatz auf „Sardinen“), 5 Arbeitsschritte = 60 Min, Planungstabelle. Quellen Kündiger S. 285, 296,
    314–315 von mir im Auszug nachgeprüft: stimmen. Schönheitsfehler: Seite 2 halb leer (Claude setzt vor die
    Tabelle einen Seitenwechsel).
  - Runde gesamt 6,84 USD. Alle vier Dokumente in data/runde-20261029-140740/fuer-lia/ (docx und PDF-Vorschau).
    Erst Jan zur Vorschau, dann an Lia (siehe oben).
- Umbau nach dem Lauf: runde.py <ordner> setzt eine Runde fort (geprüfte Antworten werden übernommen); die
  Szenenaufgabe bekommt den Ablauf zusätzlich als Kurzfassung. (Die eigene Sitzung für die Szenenaufgabe, nur der
  Kosten wegen, ist wieder zurückgenommen: sie läuft in der Hauptsitzung, siehe Entscheidungen.)
  Ablauftabelle mit drei Spalten, Seiten zusammengefasst, Optionen als Überschriften.
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
  - data/eingang/Praxis Schultheater.pdf (Lia über Jan, 29.10.): Scan mit Texterkennung, 259 MB, 384 Seiten.
    Sabine Kündiger, Praxis Schultheater. Reihen und Modelle für die Sekundarstufe I und II, Klett/Kallmeyer,
    3. Aufl. 2022. Textfassung 760.000 Zeichen (OCR mit Leerzeichenfehlern, Abbildungen teils als Zeichensalat).
    Als Kontext eingebunden (Jan 29.10.): S. 123–136 und 267–336 (theater.toml [buch], buch.py), 172.000 Zeichen
    in 5 Teilen, Zeichensalat-Zeilen gefiltert. Szenenkarte und Szenenaufgabe lesen es.
- Lias Konzept in Kürze: drei Akte wie im Original (Generalprobe, Premiere, Dernière), Eröffnung 3 Min, je Akt
  10 Min, 35–40 Min, 18 SuS. Heraustreten aus den Rollen, Chor über Scheitern und Angst. Muss-Liste in
  theater.toml (M0-1 bis M3-4). Offen bei Lia: Figurensplitting, Schwerpunkt Akt 2, Partitur oder Montage.
  Unsicher: wie kürzen, „zu lasch“, wie das Stück im Stück aussieht (die SuS sollen es selbst erfinden).

## Aufbau
- Dienst: lia-theater.service (Vorlage systemd/lia-theater.service, in ~/.config/systemd/user/), oneshot,
  OnFailure=ausfall@%n.service. Lias Zentrale und lia-feedback starten ihn nach jedem neuen Auftrag.
- agent.py: holt auftraege.neue("theater"), je Auftrag nachbesserung.bearbeiten. Fehler: Lia bekommt eine kurze
  Nachricht, Jan die Ursache; Kontingent voll: Lia erfährt, ab wann.
- nachbesserung.py: Runde finden (bezug auf einen früheren Auftrag, auf an_lia.json, sonst Rundenname im Text),
  gültigen Ablauf finden (stand.json des Bezugs, sonst ergebnis.json bzw. ablauf.json der Runde). Ordner
  data/<runde>/nachbesserung-<auftrag>/: kennzahlen.md (Python rechnet Spielzeit, Sprechzeit, Wörter je Baustein),
  spielfassung-vorher.txt, antwort.json, bei Überarbeitung ablauf.json, spielfassung.txt und fuer-lia/ (Ablauf und
  Spielfassung als docx), stand.json (welcher Ablauf danach gilt). Ein Claude-Lauf (Opus, neue Sitzung) wählt
  "antwort" oder "ueberarbeitung"; Python prüft antwort.json, den neuen Ablauf wie fassung.pruefen plus aenderungen
  und die Sprachregel für Lia. Eine Nachbesserung; harte Fehler danach brechen ab, Sprachregel nur Warnung.
  Bei Überarbeitung danach runde.pruefschleife (Prüfer gegen die Rubrik, Autor überarbeitet höchstens zweimal);
  bricht sie ab, gilt der letzte Stand, der Pythons Prüfung besteht. Ablauf-Dokument: Lias Änderungen, Prüfung.
  Lias Antworttext entsteht vor dem Prüfschritt; spätere Änderungen stehen nur im Dokument.
- Neue Runde von Hand: `AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python runde.py`
  Ergebnis in data/runde-<zeit>/fuer-lia/ (vier docx, je mit PDF-Vorschau), Meldung an Jan. Noch nicht an Lia.
  `runde.py <ordner>` setzt eine abgebrochene Runde fort. `runde.py --an-lia <ordner>` (nur in Lias Instanz, nach
  Jans Durchsicht): legt einen Auftrag für theater an und schließt ihn sofort mit den vier docx ab (daten: kern,
  3 Punkte, pruefen, knoepfe = "nur_antwort"); Lias Zentrale stellt zu. Nur einmal je Runde (an_lia.json).
- stueck.py: Textfassung -> nummerierte Einheiten (rede/regie/text, Sprecher, gedruckte Seite, PDF-Seite).
  Entfernt Fußzeile und Anmerkung der Ansichtssendung (auch mitten in der Zeile). Sprechzeit 130 Wörter/Min.
- runde.py: bereitet data/runde-<zeit>/kontext/ vor (Stück in 6 nummerierten Teilen, vorgaben.md aus theater.toml
  und Lias Texten, grundlagen.md aus 12 ausgewählten Infoblättern und Aufgaben), dann drei Claude-Läufe (Opus) in
  einer Sitzung (fortgesetzte Runde ohne Sitzung: neue), je höchstens eine Nachbesserung, keine Kostengrenze
  (GRENZE_USD = None; runde(grenze=...) nur noch für Tests). Kosten stehen im Log und in der Meldung an Jan.
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
- 29.10.2026 (Jan): Kosten spielen keine Rolle, die Qualität des Ergebnisses entscheidet. Deshalb keine
  Kostengrenze mehr, und die Szenenaufgabe läuft wieder in der Sitzung, die das Stück kennt. Weiter gilt die
  Grenze des Kontingents (5-Stunden-Fenster): ist es voll, bricht ein Lauf mit LimitErreicht ab und lässt sich mit
  runde.py <ordner> fortsetzen. Künftige Abwägungen im Agenten nach Qualität, nicht nach Preis.

## Offene Punkte
1. Lias Feedback: Regeln landen unter „Gelernte Regeln“ hier, Nachbesserungen bearbeitet der Dienst selbst.
2. Fragen an Lia (über Jan):
   - Frederick (Philip/Scheich) fehlt in Figuren.docx. Fällt die Figur weg, oder ist sie nur vergessen?
   - Termin der Aufführung und bis wann sie den Ablaufvorschlag braucht.
3. Überarbeitung baut nur Ablauf und Spielfassung neu (keine neue Szenenkarte oder Szenenaufgabe). Ob der Autor
   im Prüfschritt Lias „nur das ändern“ immer einhält, steht nicht im Prompt (kritik.ueberarbeitung_prompt gilt auch
   für runde.py); im Probelauf tat er es aus der Sitzung heraus.

## Gelernte Regeln
- (noch keine)
