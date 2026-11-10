# Plan: Schnelle Dokumente und kleine Änderungen (Lia)

Stand 10.11.2026. Nur Plan, nichts gebaut. Jans Entscheidungen 10.11.2026: alle sechs Empfehlungen aus Abschnitt 6
angenommen.

## 1. Anlass
Lia (über Jan, 10.11.2026): In claude.ai ist sie schneller, auch wenn sie 100 Prompts braucht, weil **kleine
Änderungen an Dokumenten** in der Web-App ewig dauern. Außerdem braucht sie **mal schnell ein Dokument**, das kein
Arbeitsblatt und keine Präsentation ist; das muss flexibler sein.
Jan: Recherchen zu Reihen und daraus abgeleitete Präsentationen und Arbeitsblätter sind komplexe Aufgaben, die Zeit
brauchen dürfen, damit die Qualität stimmt. Kleine Änderungen und schnelle Dokumente sollen nicht jedes Mal den ganzen
Lauf gehen.

Damit ruht `docs/gespraech-flexibel-plan.md` (Gespräch wie eine Claude-Code-Sitzung). Er bleibt als Vorrat.

## 2. Befund
- Lias erledigte Aufträge (lia/instanz/auftraege/erledigt, 27 Stück): Nachbesserungen beim Theater-Agenten dauerten
  7 bis 67 Minuten, meist 15 bis 20; neues Material bei unterricht 6 bis 7 Minuten.
- Grund: Jede Rückmeldung läuft durch die ganze Kette. Der Feedback-Dienst ordnet zu, dann entsteht ein neuer
  Auftrag, der Agent läuft mit allen Schritten und Prüfrunden, zuletzt baut der Renderer neu.
- Der letzte Schritt ist billig: Zu jedem Dokument liegt die Beschreibung, aus der der Renderer baut
  (unterricht: `data/arbeit/<auftrag>/beschreibung.json`, theater: `<Name>.json` neben der .docx). Gemessen 10.11. an
  einem echten Arbeitsblatt: neu bauen 0,6 s, mit Vorschaubildern 4,2 s, Speicher bis 220 MB.

## 3. Idee: ein schneller Weg neben dem gründlichen
Neuer Agent **`lia/schnell`** (eigener Ordner, .venv, Dienst, wie jeder Agent). Ein claude-Lauf, keine Prüfrunden,
dann Renderer. Ziel: unter einer Minute vom Absenden bis zur neuen Fassung. Zwei Arten:

**a) Kleine Änderung an einem Dokument**
- Lia schreibt am Dokument, was anders sein soll („Aufgabe 2 einfacher“, „Merksatz kürzer“, „Folie 4 weg“).
- Python holt die Beschreibung des Dokuments und gibt sie Claude mit dem Wunsch und Lias Regeln. Claude schreibt die
  geänderte Beschreibung, sonst nichts.
- Python prüft sie mit dem Renderer (`BeschreibungUngueltig` geht einmal an Claude zurück), baut das Dokument und legt
  es als neue Fassung derselben Kette ab (agentkit.fassungen). Die alte Fassung bleibt.
- Ist der Wunsch zu groß für den schnellen Weg (neue Inhalte, die Recherche brauchen, ganz neuer Aufbau), sagt Claude
  das mit einem Satz. Python gibt dann den Wunsch als normale Nachbesserung an den zuständigen Agenten weiter
  (`auftraege.weitergeben`), und Lia sieht: „Das ist größer, läuft gründlich, dauert länger.“ Kein zusätzlicher Knopf.
- Lernen bleibt: Der Wunsch geht danach zusätzlich an den Feedback-Dienst, aber nur zum Lernen von Regeln (keine
  zweite Nachbesserung). Läuft im Hintergrund, Lia wartet nicht darauf.

**b) Schnelles Dokument, frei**
- Lia schreibt, was sie braucht („Checkliste für den Wandertag“, „Handout mit den drei Straftheorien“, „Tabelle zum
  Ausfüllen für die Gruppenarbeit“), am Ort oder ohne Ort, gern mit angehängter Datei.
- Claude wählt die passende Form aus dem Renderer: Dokument im Stil von Lias Arbeitsblättern (docx), Folien (pptx)
  oder Tabelle (xlsx), und schreibt die Beschreibung. Python baut wie oben.
- Kontext: Ort mit Reihe, Reihenfrage und Lerngruppe (agentkit.struktur), Lias Regeln, angehängte Dateien
  (agentkit.textfassung). Keine Recherche, keine Prüfrunden. Das Ergebnis trägt einen kleinen Hinweis „schnell
  erstellt, ohne Quellenprüfung“ (Entscheidung 6.3). Für Belastbares bleibt der gründliche Weg.
- Danach geht a) genauso: kleine Änderungen am schnellen Dokument.

Was nicht schnell wird: Reihenentwurf, Recherche, Material aus der Reihe, Spielfassung. Die bleiben gründlich.

Grenzen der Formen: Der Renderer kennt für Lia Arbeitsblatt, Folien und Arbeitsmappe. Ein Brief (Elternbrief mit
Anschrift und Unterschrift) sähe als Arbeitsblatt-Layout behelfsmäßig aus. Braucht Lia das oft, ist eine Art „Brief“
ein Bedarf an shared/renderer (später, eigener Chat).

## 4. Schritte und Zuständigkeit
Je Schritt ein Commit über commit.sh, `./pruefen.sh` grün (nur mit Sperre), Tests ohne Netz.

1. **Hauptordner**: dieser Plan, STATUS. Dazu `[weitergabe] schnell = ["unterricht", "theater"]` in
   einstellungen.toml (für die Übergabe großer Wünsche), feedback mit Modus „nur lernen“ (keine Nachbesserung).
2. **lia/schnell** (eigener Chat): Agent aus der Vorlage, .venv mit denselben Paketen wie lia/unterricht (python-docx,
   python-pptx, xlsxwriter, Pillow, pypdfium2; Jans Okay), Dienst wie lia-chat (Warteschlange, oneshot,
   `MemoryMax` um 600M: claude rund 250 MB, danach Renderer bis 220 MB). Logik rein und getestet: Beschreibung zum
   Bezug finden, Antwort lesen (Beschreibung oder „zu groß“), Fassung ablegen. Echter Lauf an Kopien: drei kleine
   Änderungen an einem echten Arbeitsblatt, eine an einer Folie, ein schnelles Dokument; Zeit und Kosten messen.
3. **shared/webapp** (eigener Chat): Rückmeldung am Dokument geht an `lia/schnell` statt an den Feedback-Dienst; in
   „Neu“ eine Karte „Anderes Dokument“ (ein Textfeld, Dateien). Antwort per Abfrage wie heute, Anzeige „wird
   geändert …“. Achtung: `app.py` lädt schon die neue, nicht freigegebene Oberfläche (`oberflaeche/`); ein Neustart
   würde sie Lia zeigen. Darum zuerst ein Schalter für die alte Oberfläche (Entscheidung 6.5). Neustart nur mit
   Jans Okay.
4. **Probe mit Lia**: drei echte kleine Änderungen und ein schnelles Dokument, Zeit stoppen. Danach zwei Wochen
   Betrieb, dann Zeiten, Kosten und „zu groß“-Fälle ansehen.

## 5. Kosten, Zeit, Risiken
- Zeit (Schätzung): claude-Lauf mit Sonnet 10–30 s (Gesprächsläufe brauchten am 10.11. 8–15 s), Renderer mit
  Vorschau 4 s (gemessen), Start des Dienstes und Abfrage der Web-App wenige Sekunden. Gemessen wird in Schritt 2.
- Kosten (Schätzung): ähnlich einer Gesprächsnachricht, 0,03–0,10 USD je Änderung mit Sonnet. Auf Lias Kontingent.
- Speicher: claude und Renderer laufen nacheinander, nicht gleichzeitig; höchstens zwei claude-Läufe zugleich wie
  heute (`[parallel]`).
- Qualität: Der schnelle Weg ändert nur, was Lia sagt, und erfindet keine Quellen (Prompt). Der Renderer prüft die
  Form streng. Inhaltlich prüft niemand nach; darum der Hinweis bei schnellen Dokumenten und die Übergabe großer
  Wünsche an den gründlichen Weg.
- Claude könnte einen großen Wunsch für klein halten (oder umgekehrt). Probe und die zwei Wochen zeigen, wie oft.

## 6. Entscheidungen (Jan 10.11.2026: alle wie empfohlen)
1. **Eigener Agent `lia/schnell`** statt eines Modus in lia/unterricht und lia/theater? Ein Ort für alles Schnelle,
   die gründlichen Agenten bleiben unverändert. **Empfehlung: ja.**
2. **Rückmeldung am Dokument geht immer zuerst an den schnellen Weg**, Claude entscheidet klein oder groß, groß
   geht von selbst an die gründliche Nachbesserung? **Empfehlung: ja.**
3. **Schnelle Dokumente ohne Recherche und Prüfrunden**, mit kleinem Hinweis „schnell erstellt, ohne
   Quellenprüfung“? **Empfehlung: ja.**
4. **Modell Sonnet** für den schnellen Weg (Opus ist langsamer)? **Empfehlung: ja, nach der Probe ansehen.**
5. **Web-App:** Schalter für die alte Oberfläche, damit der schnelle Weg bald live gehen kann, ohne die neue,
   nicht freigegebene Oberfläche umzuschalten? **Empfehlung: ja.**
6. **Pakete** für die .venv von lia/schnell (dieselben wie lia/unterricht) installieren? **Empfehlung: ja.**
