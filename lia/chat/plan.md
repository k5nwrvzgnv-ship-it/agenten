# Plan: Chat-Agent lia/chat (Spalte „Fragen“ der Web-App), 30.10.2026

Grundlage: `docs/webapp-aufbau.md` 3.1, Punkt 24 der Haupt-STATUS (Bedarf c), `shared/webapp/board-plan.md` (9).
Gebaut wird erst nach Jans Okay.

## 1. Was der Agent tut
Lia stellt rechts in der Web-App eine Frage. Der Agent antwortet kurz, mit dem Ort als Kontext
(„Ethik › 8 › Straftheorien“) oder „ohne Ort“. Er startet nie einen Auftrag und handelt nie nach außen.
„Daraus Auftrag machen“ macht die Web-App allein (Galerie mit Text und Ort vorbelegt), der Agent liefert nur Text.

## 2. Schnittstelle zur Web-App: Warteschlange in Dateien (Empfehlung)
Ordner `lia/chat/data/` (Laufzeitdaten, nicht im Repo):
- `fragen/<id>.json` schreibt die Web-App:
  `{"id", "zeit", "text", "gruendlich": false, "ort": null | {"reihe": "<kennung>", "stunde": 3 | null,
  "chip": "Ethik › 8 › Straftheorien", "stunde_thema": "…", "materialien": ["Titel", …]}}`
  (`stunde_thema` und `materialien` liefert die Web-App, solange Stunden und Material-Titel nur bei ihr liegen.)
- `antworten/<id>.json` schreibt der Agent:
  `{"id", "zeit", "ok", "text", "gruendlich", "chip", "fehler": null | "limit" | "belegt" | "technik",
  "wieder_frei": "14:30" | null}`. Bei Fehlern steht ein fertiger Satz für Lia in `text`.
- Start: systemd-Pfad-Unit `lia-chat.path` (DirectoryNotEmpty auf `fragen/`) startet `lia-chat.service`
  (oneshot). Der arbeitet alle Fragen der Reihe nach ab und beendet sich. Die Web-App ruft nichts auf, sie schreibt
  nur die Datei und fragt per htmx alle 2 s nach `antworten/<id>.json` („denkt nach …“).
- Für die Web-App gibt es `lia/chat/schnittstelle.py` (nur Python-Bordmittel): `frage_stellen(...) -> id`,
  `antwort_holen(id) -> dict | None`, `verlauf() -> list`. Sie kann es importieren oder das Format selbst schreiben.

Warum nicht Unix-Socket: Das bräuchte einen dauernd laufenden Server (RAM, kein Swap) und die Web-App müsste
30 s an einer Verbindung hängen. Die Dateien passen zum bestehenden Muster (`shared/auftraege`), sind testbar und
überstehen Neustarts.

Antwortzeit (Schätzung, wird im Test gemessen): schnell 10–30 s (Start von claude ca. 5 s), gründlich 30–90 s.
Zeitlimit: schnell 2 min, gründlich 5 min.

## 3. Ablauf je Frage (Python)
1. Frage lesen und prüfen (Text bis 4.000 Zeichen, Ort bekannt oder null).
2. Kontext bauen, nur aus Dateien, kein Modell: Reihe aus `lia/instanz/reihen.toml` (bis zum Umzug durch
   lia/unterricht: `lia/unterricht/reihen.toml`, Kennung wie in der Web-App): Fach, Klasse, Titel, Reihenfrage,
   Lerngruppe, schon behandelt, Notizen, Stunden (`[[reihe.stunde]]`, sonst `stunde_thema` aus der Frage),
   Material-Titel aus der Frage. Lias Regeln kommen über `agentkit.claude_lauf` automatisch mit
   (`lia/instanz/regeln.md` und „Gelernte Regeln“ dieser STATUS). Kein Inhalt aus Schülerdateien.
3. Verlauf: die letzten Wechsel (höchstens 6, gekürzt) seit dem letzten Ortswechsel gehen mit in den Prompt.
4. `claude_lauf.laufen(AGENT, …)`: schnell = art „routine“ (Sonnet, in der Sparstufe Haiku), gründlich nur auf
   Lias Klick = art „anspruchsvoll“ (Opus). Ohne Werkzeuge (`--tools ""`, über eine Kopie der Einstellungen im
   Code, keine Änderung an `shared/einstellungen.toml`), höchstens 3 Schritte. Kein Lesen, kein Schreiben.
5. Antwort schreiben, Verlauf ergänzen, Frage-Datei löschen.
6. Fehler: Kontingent voll -> „Gerade ist das Kontingent voll, wieder frei ab 14:30.“; alle Plätze belegt
   (nach 1 min Warten) -> „Gerade laufen zwei Aufträge, frag in ein paar Minuten noch mal.“; sonst Technik-Satz,
   Log und Meldung an Jan. Nie still.

Prompt-Regeln (fest im Code): kurz antworten (Standard 2–6 Sätze, länger nur bei „gründlich“), Deutsch, keine
Schülernamen wiederholen oder erfinden, wenn welche in der Frage stehen: kurz darauf hinweisen. Keine Aufträge
versprechen, stattdessen auf „Daraus Auftrag machen“ verweisen.

## 4. Datenschutz und Aufbewahrung
- Fester Hinweis unter dem Eingabefeld („Bitte keine Namen von Schüler*innen“) macht die Web-App.
  Eine verlässliche Namenserkennung gibt es nicht, also baue ich keine.
- Verlauf in `data/verlauf.jsonl`, Einträge älter als 30 Tage werden bei jedem Lauf und einmal täglich
  (`lia-chat-aufraeumen.timer`) gelöscht, ebenso alte Antwort-Dateien.
- claude speichert jede Sitzung zusätzlich unter `~/.claude/projects/-home-agent-agenten-lia-chat/`. Der Agent
  löscht diese Dateien gleich nach jedem Lauf (nur diesen einen Ordner). Sauberer wäre die Option
  `--no-session-persistence` in `agentkit.claude_lauf` (Bedarf an den Hauptordner-Chat, kein Muss).
- Logs ohne Frage- und Antworttext (nur ID, Länge, Dauer, Modell). Keine Übernahme von Chat-Inhalten in Regeln.

## 5. Was entsteht
- `lia/chat/`: `agent.py` (Einstieg), `kontext.py` (Ort -> Text, rein), `verlauf.py` (Speichern, Aufräumen, rein),
  `schnittstelle.py`, `tests/`, `systemd/` (Vorlagen für `lia-chat.service`, `lia-chat.path`,
  `lia-chat-aufraeumen.service` und `.timer`), `STATUS.md`, `requirements.txt` (leer: keine neuen Pakete).
- `.venv` in `lia/chat/` mit agentkit per .pth, wie die anderen Lia-Agenten.
- Dienst mit `AGENTKIT_INSTANZ=lia/instanz`, `OnFailure=ausfall@%n.service`, MemoryMax 500M.
- Eintrag des Testordners in `pruefen.sh` (Hauptordner-Datei, nur diese eine Zeile).
- Punkt 24 der Haupt-STATUS: Schnittstelle für den shared/webapp-Chat.

## 6. Test
Tests ohne Netz für Kontext, Verlauf, Aufräumen, Fehlertexte und Schnittstelle (claude_lauf ersetzt).
Echter Lauf: zwei Fragen (eine mit Ort Ethik 8, eine ohne Ort) über die Warteschlange, Antwortzeit messen.
Kostet zwei kurze Sonnet-Läufe auf dem Agenten-Konto.

## 7. Fragen an Jan
1. Okay für Ordner, .venv und die Dienste aus 5 (Pfad-Unit plus täglicher Aufräum-Timer)?
2. 30 Tage Aufbewahrung des Verlaufs?
3. Plätze: Der Chat teilt sich die 2 gleichzeitigen Läufe mit allen Agenten. Laufen zwei Material-Aufträge,
   wartet eine Frage höchstens 1 min und bekommt dann den Hinweis. Reicht das, oder soll der Hauptordner-Chat
   dem Chat einen eigenen Platz geben?
