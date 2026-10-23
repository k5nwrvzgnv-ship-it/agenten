# Status: Werkzeug auswertung (Lias Instanz)

## Zweck
Aus Lias Chats in claude.ai (über Jans Konto) ableiten, welche wiederkehrenden Aufgaben sich für ihre
Agenten lohnen und wie gut die Agenten sie lösen müssen. Ergebnis: Rangliste, Beispiele, Prüfsatz und
Regelvorschläge für lia/unterricht bzw. neue Agenten. Kein Agent: Jan startet es von Hand.

## Stand (23.10.2026)
- Schritt 1 erledigt: Gerüst (.venv ohne Pakete, agentkit per .pth, ablage.py mit Tests, Eintrag in pruefen.sh).
- Noch keine Daten auf dem Server, noch keine Einwilligung von Lia.

## Aufbau
- Einstieg: auswertung.py (`.venv/bin/python auswertung.py`), legt bisher nur data/ an.
- ablage.py: data/ mit chmod 700, Dateien mit chmod 600 (atomar), lehnt ungeschützte Ordner ab.
- .venv: auswertung/.venv, keine Pakete (requirements.txt leer), agentkit per agentkit.pth.
- Kein Dienst, kein Timer, keine .env.
- Rohdaten und Ergebnisse nur in data/ (nicht im Repo, .gitignore `data/`), Logs in logs/.

## Datenschutz
- Weiter geht es erst mit Lias Einwilligung (Schritt 2). Lias Chats können Schülerdaten enthalten.
- Jans eigene Chats im Export werden nach der Auswahl (Schritt 4) nicht weiter verarbeitet.
- Löschtermin der Rohdaten: noch festzulegen (Vorschlag kommt am Ende).

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
1. Schritt 2 (Einwilligung).
2. Instanz für die claude-Läufe in Schritt 6: Vorschlag AGENTKIT_INSTANZ=lia/instanz (es sind Lias Daten).
