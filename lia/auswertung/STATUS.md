# Status: Werkzeug auswertung (Lias Instanz)

## Zweck
Aus Lias Chats in claude.ai (über Jans Konto) ableiten, welche wiederkehrenden Aufgaben sich für ihre
Agenten lohnen und wie gut die Agenten sie lösen müssen. Ergebnis: Rangliste, Beispiele, Prüfsatz und
Regelvorschläge für lia/unterricht bzw. neue Agenten. Kein Agent: Jan startet es von Hand.

## Stand (23.10.2026)
- Schritt 1 erledigt: Gerüst (.venv ohne Pakete, agentkit per .pth, ablage.py mit Tests, Eintrag in pruefen.sh).
- Schritt 2 erledigt: Lia hat am 23.10.2026 der Erklärung in einwilligung.md ohne Einschränkungen
  zugestimmt (mündlich an Jan, Jan hat es im Chat weitergegeben).
- Schritt 3 vorbereitet: anleitung-export.md (für Jan), Befehle entpacken und struktur. Export fehlt noch.
- Schritt 4 vorbereitet: Befehl chatliste (Vorschlag Lia/Jan/unklar nach Stichwörtern, nur Titel).
  Mit einem Kunst-Export durchgespielt. Noch keine echten Daten auf dem Server.

## Aufbau
- Einstieg: auswertung.py (`.venv/bin/python auswertung.py <befehl>`, Befehle im Kopf der Datei).
- ablage.py: data/ mit chmod 700, Dateien mit chmod 600 (atomar), lehnt ungeschützte Ordner ab.
- export.py: ZIP sicher entpacken (keine Pfade nach oben, keine Symlinks, höchstens 2 GB), Strukturbericht
  ohne Inhalte, Verzweigungen (Annahme: Feld parent_message_uuid).
- auswahl.py: Chatliste data/chatliste.tsv mit Spalte wer (Lia/Jan/unklar), bestaetigte_lia() liest sie
  zurück und bricht ab, solange etwas unklar ist. Stichwortlisten LIA/JAN oben in der Datei.
- Annahme bis zum echten Export: conversations.json mit uuid, name, created_at, chat_messages[].sender/.text.
- .venv: auswertung/.venv, keine Pakete (requirements.txt leer), agentkit per agentkit.pth.
- Kein Dienst, kein Timer, keine .env.
- Rohdaten und Ergebnisse nur in data/ (nicht im Repo, .gitignore `data/`), Logs in logs/.

## Datenschutz
- Weiter geht es erst mit Lias Einwilligung (einwilligung.md). Lias Chats können Schülerdaten enthalten.
  Ihr Okay wird hier mit Datum und Einschränkungen vermerkt. Widerruft sie, wird alles gelöscht, auch Ergebnisse.
- Jans eigene Chats im Export werden nach der Auswahl (Schritt 4) nicht weiter verarbeitet.
- Löschtermine (mit Lias Okay vom 23.10.2026 verbindlich): Jans Chats nach Schritt 4; Lias Originalchats nach
  Schritt 8, spätestens 31.12.2026; die ZIP-Datei auf Jans Rechner nach dem Hochladen. Es bleiben nur
  anonymisierte Ergebnisse, die Beispiele erst nach Lias Durchsicht.

## Plan (je Schritt erst nach Jans Okay, danach ein Commit)
1. Gerüst – erledigt.
2. Einwilligung: kurze Erklärung für Lia (was ausgewertet wird, was nicht, wo die Daten liegen, Löschung).
3. Export: Anleitung für Jan (claude.ai-Export anfordern, auf den Server laden), dann Struktur prüfen:
   Felder, verworfene Antworten, bearbeitete Prompts.
4. Lias Chats herausfiltern: Vorschlagsliste, Lia oder Jan bestätigen.
5. Anonymisieren: getestetes Skript (Namen, Schulen, Schüler, Kontaktdaten), Stichprobe für Jan.
6. Analyse: Chats in Aufgaben zerlegen, Kategorienschema an einer Stichprobe, Einordnung über
   agentkit.claude_lauf (mehrere Aufgaben je Lauf, günstiges Modell, vorher Kostenschätzung),
   je Kategorie Häufigkeit, Runden, Korrekturen, typische Eingaben; Lias Korrekturen gesondert.
7. Ergebnisse in data/ und Zusammenfassung hier: Rangliste (Häufigkeit × Aufwand × Automatisierbarkeit)
   mit Empfehlung unterricht oder neuer Agent, anonymisierte Beispiele, Prüfsatz, Regelvorschläge.
   Bedarf anderswo nur als Vorschlag in die Haupt-STATUS.md.
8. Prüfung durch Lia: 20–30 Aufgaben selbst kodieren, Übereinstimmung vergleichen; danach blinde
   Bewertung von lia/unterricht gegen ihre alten Ergebnisse (Läufe macht der unterricht-Chat).

## Offene Punkte
1. Jan fordert den Export an und lädt ihn hoch (anleitung-export.md), dann entpacken, struktur.
   Danach: Feldannahmen in export.py/auswahl.py prüfen, Verzweigungen bewerten, chatliste erzeugen.
2. Nach Bestätigung der Chatliste: Befehl zum Filtern bauen (nur Lias Chats nach data/lia/, Jans Chats
   und das Original conversations.json löschen). Noch nicht gebaut, weil er löscht.
3. Instanz für die claude-Läufe in Schritt 6: Vorschlag AGENTKIT_INSTANZ=lia/instanz (es sind Lias Daten).
