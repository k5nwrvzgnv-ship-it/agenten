# Status: Agent schnell (Lia)

## Zweck
Der schnelle Weg neben dem gründlichen (Plan docs/schnell-dokument-plan.md, Jan 10.11.2026): kleine Änderungen an
Lias Dokumenten und schnelle Dokumente, je ein claude-Lauf (Sonnet, ohne Werkzeuge) und danach der Renderer. Ziel unter
einer Minute. Was zu groß ist, geht von selbst als gründliche Nachbesserung an unterricht bzw. theater. Handelt nie
nach außen.

## Stand (10.11.2026)
- Gebaut mit Tests ohne Netz (tests/, 36 Tests, in pruefen.sh). Dienst-Vorlagen in systemd/, **noch nicht
  installiert** (wartet auf Jans Okay). Die Web-App nutzt den Agenten noch nicht (Plan Schritt 3, eigener Chat).
- Echter Lauf an Kopien (10.11., claude und Renderer echt, Kette und Agenten-Ordner als Kopie, Lias Instanz
  unberührt). Zeit = vom Lesen des Wunschs bis zur abgelegten Fassung, ohne Start des Dienstes:

  | Wunsch | Ergebnis | Zeit | davon claude | Kosten |
  |---|---|---|---|---|
  | Arbeitsblatt (echt, Spielfassung Entwurf 2, 31 KB, 12 Seiten): „B03 2 Min statt 1,5“ | genau dieser Block | 12,8 s | 5,6 s | 0,008 USD |
  | dasselbe: „Strichübersicht am Ende weglassen, mit Seitenumbruch“ | 4 Blöcke weg | 23,2 s | 7,3 s | 0,007 USD |
  | dasselbe: „Absatz unter ‚Worum es geht‘ höchstens zwei Sätze“ | genau dieser Absatz | 17,7 s | 10,4 s | 0,008 USD |
  | Folien (Beispiel aus FORMAT.md, Lias Stunde Singer/Aristoteles; echte Folien gibt es noch nicht): Satzanfang auf Folie „Unsere Leitfrage“ | Element ergänzt | 13,1 s | 6,3 s | 0,003 USD |
  | Schnelles Dokument an der Reihe Straftheorien: Handout drei Straftheorien mit Zuordnungstabelle | Arbeitsblatt, 2 Seiten, Lias Stil | 64,7 s | 59,2 s | 0,010 USD |

  Alle Änderungen minimal (übriger Inhalt wörtlich gleich), keine Korrekturrunde nötig. Renderer mit Vorschau für das
  große Blatt 4,7 s (ohne 1,1 s); der Rest der Zeit sind Start von claude und Warten auf einen Platz. Kosten weit
  unter der Schätzung (0,03–0,10 USD), vermutlich durch den Prompt-Cache. Das schnelle Dokument liegt mit 65 s knapp
  über dem Ziel (Claude schreibt das ganze Dokument). Inhaltlich brauchbar, ein Grammatikfehler („Welcher Grund
  findest du“); Claude bot wegen Lias Regel „drei Niveaus“ an, einfache und schwere Fassung nachzureichen.

## Aufbau
- Code: agent.py (Einstieg, Warteschlange, claude, Renderer, Ablage, Weitergabe), logik.py (rein: Beschreibung
  finden, Übersicht, Prompts, Antwort lesen, Änderungen anwenden), schnittstelle.py (für die Web-App, nur
  Bordmittel), tests/.
- .venv: lia/schnell/.venv, agentkit und renderer per agentkit.pth, Pakete aus requirements.txt (Versionen wie die
  .venv von lia/unterricht, Jan 10.11.2026).
- Dienste (Vorlagen in systemd/): lia-schnell.path (startet, sobald data/wuensche/ nicht leer ist),
  lia-schnell.service (oneshot, AGENTKIT_INSTANZ=lia/instanz, MemoryMax=600M, OnFailure=ausfall@). Kein Timer:
  Aufräumen am Anfang jedes Laufs (Antworten nach 30 Tagen, liegengebliebene Arbeitsordner und Uploads nach 1 Tag).
- Laufzeitdaten data/: wuensche/, antworten/, dateien/<id>/ (Uploads bis zum Lauf), arbeit/<id>/ (während des
  Laufs), tmp/, fassungen/<ursprung>/eigene-<n>/ (Beschreibung, Datei und Vorschau jeder schnell geänderten Fassung,
  Grundlage weiterer schneller Änderungen), dokumente/<auftrag>/ (schnelle Dokumente mit <Name>.json daneben),
  eingang/ (Lias Dateien zu schnellen Dokumenten, über agentkit.auftraege). Logs: logs/schnell.log (ohne Lias Texte).
- claude-Sitzungen: werden nach jedem Wunsch gelöscht (nur die eigenen, per Sitzungs-ID).

## Ablauf
- Änderung: Fassung finden (Datei nr von bezug, oder eigene Fassung n der Kette), Beschreibung dazu
  (logik.beschreibung_finden: `<Name>.json` daneben wie bei theater und schnell, sonst `beschreibung.json` bzw.
  `beschreibung-<zusatz>.json` wie bei unterricht; bei eigener Fassung die Kopie in data/fassungen/). Claude bekommt
  Wunsch, Beschreibung mit Übersicht der Pfade, den passenden Abschnitt aus FORMAT.md und die Gelernten Regeln von
  unterricht bzw. theater, und antwortet mit Änderungen (setzen, loeschen, einfuegen an Pfaden des Originals),
  ganzer Beschreibung oder „zu groß“ (Format: logik.py oben). Python wendet an, prüft und baut mit dem Profil des
  Agenten der Kette (`profil.toml`); ein Fehler (Antwort, Änderung, BeschreibungUngueltig) geht einmal an Claude
  zurück. Die Datei kommt mit `fassungen.eigene_dazu` als eigene Fassung in dieselbe Kette (Notiz „Schnell geändert:
  <Wunsch>“, Art fassung), die alte bleibt.
- Zu groß, keine Beschreibung (z. B. theater/rollentabelle) oder auch nach der Korrektur ungültig:
  `auftraege.weitergeben(schnell, <agent>, …, bezug=<letztes erledigtes Ergebnis>, nachbesserung=True, still=True)`,
  danach startet der Agent lia-<agent>.service selbst. War die Grundlage eine schnell geänderte Fassung, hängt sie an.
  An schnellen Dokumenten gibt es keinen gründlichen Agenten: Lia bekommt „zu groß, bitte Auftrag unter Neu“.
- Lernen: nach jeder Änderung (auch zu groß) geht der Wunsch mit `feedback_modus = nur_lernen` still an feedback,
  der Agent startet lia-feedback.service. Nur wenn [weitergabe] schnell feedback erlaubt (lia/instanz/einstellungen.toml).
- Schnelles Dokument: Auftrag des Agenten schnell (quelle schnell-dokument, ort) in Lias Warteschlange, Lias Dateien
  per agentkit.auftraege nach data/eingang/<auftrag>/. Kontext: Ort über agentkit.struktur, Text der Dateien
  (agentkit.textfassung), Fotos per Read nur in diesem Ordner (lese_ordner), Gelernte Regeln von unterricht.
  Claude wählt arbeitsblatt, folien oder arbeitsmappe. Gebaut mit dem Profil von unterricht. Der Auftrag wird
  erledigt mit der Datei, Ergebnistext mit „Schnell erstellt, ohne Quellenprüfung.“, daten {"kern", "pruefen":
  Hinweis}. Damit erscheint er wie jedes Ergebnis (Web-App, Lias Zentrale) und lässt sich schnell ändern.

## Schnittstelle (für shared/webapp)
`sys.path` um lia/schnell ergänzen, dann `import schnittstelle` (nur Bordmittel). Alle Funktionen haben `ordner=`
(Standard lia/schnell/data). Ungültiges: `schnittstelle.WunschFehler` (ValueError), Text ist ein Satz für Lia.
- `aendern(bezug, text, nr=0, eigene=None, seite=None) -> id` (12 Hex). bezug: ID eines erledigten Auftrags von
  unterricht, theater oder schnell; nr: Index der Datei in dessen `ergebnis_dateien` (wie `dnr` der Web-App).
  `eigene=n`: statt dessen die eigene Fassung n der Kette von bezug (schnell geänderte haben eine Beschreibung;
  Lias hochgeladene nicht, sie gehen gründlich). seite: 1–999, nur als Hinweis an Claude. text bis 4.000 Zeichen.
  Ohne Datei: Rückmeldungen mit Datei schickt die Web-App weiter an den Feedback-Dienst.
- `dokument(text, ort=None, dateien=None) -> id`. ort: id aus agentkit.struktur (Fach, Klasse, Reihe, Stunde).
  dateien: `[(Name wie hochgeladen, Pfad)]`, bis 5, .pdf/.docx/.pptx/.xlsx/.jpg/.jpeg/.png je bis 20 MB, werden nach
  data/dateien/<id>/ verschoben (bei WunschFehler bleibt alles liegen).
- `antwort_holen(id) -> dict | None` (None = noch nicht fertig; Vorschlag: alle 2 s), `wartet(id) -> bool`.
  Antwort: `{"id", "art": "aenderung"|"dokument", "zeit", "ok", "stand", "text", "fehler", "wieder_frei",
  "fassung", "auftrag", "sekunden", "usd"}`.
  - `stand`: "fertig" (neue Fassung bzw. Dokument da), "gruendlich" (läuft als Nachbesserung, `auftrag` = deren ID,
    `text` = „Das ist eine größere Änderung. Sie läuft jetzt gründlich und dauert länger.“), "zu_gross" (schnelles
    Dokument, nichts weitergegeben), "fehler".
  - `fehler`: None, "limit" (`wieder_frei` z. B. "31.10. 14:30"), "belegt", "zeit", "technik" (Jan hat eine
    Meldung), "ungueltig" (Dokument oder Wunsch unbekannt). Bei Fehlern steht in `text` ein Satz für Lia.
  - `fassung` (bei fertig): `{"agent" (der Kette), "bezug", "ursprung", "eigene" (n der neuen eigenen Fassung, bei
    schnellen Dokumenten None), "name", "datei" (relativ zum Ordner von agent), "vorschau" (Ordner mit PNG je Seite
    und PDF, relativ zu lia/schnell, oder None)}`. Schnelles Dokument: `auftrag` = ID des erledigten Auftrags.
  - `text`: Claudes Satz, was geändert ist (bzw. was das Dokument enthält, mit dem Hinweis am Ende).
- Zeiten: Änderung meist 13–25 s, schnelles Dokument um 1 min; Grenze je Lauf 4 min, höchstens 2 Läufe, plus bis
  1 min Warten auf einen Platz.

## Entscheidungen
- 10.11.2026 (Jan, Plan Abschnitt 6): eigener Agent, Rückmeldung am Dokument zuerst schnell, groß geht von selbst
  gründlich, schnelle Dokumente ohne Recherche mit Hinweis, Sonnet (`art="routine"`, in der Sparstufe Haiku),
  Pakete wie lia/unterricht.
- 10.11.2026: Claude schreibt Änderungen an Pfaden statt der ganzen Beschreibung (die ganze bleibt erlaubt). Grund:
  Lias Beschreibungen sind bis 38 KB; sie ganz neu ausgeben dauerte Minuten. Pfade beziehen sich auf das Original,
  damit die Reihenfolge gleichgültig ist.
- 10.11.2026: Eigene Warteschlange data/wuensche/ mit Pfad-Unit wie lia/chat (Start in Sekunden, die Web-App muss
  keinen Dienst starten). Neue Fassungen als eigene Fassung der Kette (agentkit.fassungen kennt nur Aufträge
  desselben Agenten in einer Kette); die gründliche Nachbesserung findet sie über fassungen.grundlage.
- 10.11.2026: Der Hinweis „schnell erstellt, ohne Quellenprüfung“ steht im Ergebnistext, nicht im Dokument (das
  Blatt geht an Schüler*innen). Auf Wunsch leicht änderbar.
- 10.11.2026: Auch nach der Korrektur ungültige Änderungen gehen gründlich statt als Fehler (Lias Wunsch geht nicht
  verloren).

## Offene Punkte
1. Dienste installieren (Jans Okay ausstehend), vorher Neustart der Zentralen (Haupt-STATUS Punkt 37). Danach ein
   Lauf über den Dienst: Zeit mit Start und Speicher-Spitze messen.
2. Web-App (Plan Schritt 3): Anbinden. Schnell geänderte Fassungen zeigt sie heute als eigene Fassung „von dir“; die
   Notiz beginnt mit „Schnell geändert:“.
3. Gründliche Nachbesserung nach schnellen Änderungen: unterricht kopiert die Beschreibung des letzten eigenen
   Ergebnisses, theater baut aus seinem Ablauf neu. Schnelle Änderungen kommen dort nur über die angehängte Datei
   (fassungen.grundlage bzw. Anhang) an und können verloren gehen. Bedarf in Haupt-STATUS Punkt 37.
4. Schnelle Dokumente gehen als erledigter Auftrag auch an Lias Zentrale (Telegram). Eine Antwort dort würde ein
   Auftrag an schnell, den dieser Agent nicht abarbeitet (er liest nur data/wuensche/). Bedarf in Punkt 37.
5. Lias Formatvorlage (lia/unterricht/data/vorlagen/, formatvorlage.py) nutzt schnell nicht; heute gibt es keine.
6. Nach der Probe mit Lia: schnelles Dokument über 1 min (Sonnet schreibt alles), Haiku in der Sparstufe, wie oft
   „zu groß“ falsch eingeschätzt wird.

## Gelernte Regeln
- (noch keine)
