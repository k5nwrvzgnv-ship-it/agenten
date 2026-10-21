# Status: Agent unterricht (Lias Instanz)

## Zweck
Später: Unterrichtsmaterial, Wochenüberblick und Fragen für Lia (docs/lia-architektur.md, Schritt 1).
Heute Platzhalter: bestätigt jeden Auftrag mit "kommt bald", ruft Claude nicht auf.

## Stand (21.10.2026)
- agent.py schließt alle neuen Aufträge mit einer Antwort je Art (Feld quelle) ab. Tests in tests/.

## Aufbau
- Instanz: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz (Warteschlangen, Regeln, .env dort)
- Code: lia/unterricht/agent.py
- .venv: lia/unterricht/.venv, agentkit per .pth eingebunden
- Dienst: lia-unterricht.service (oneshot, Vorlage systemd/), gestartet von Lias Zentrale
- Laufzeitdaten: lia/unterricht/data/, Logs: lia/unterricht/logs/ (beide nicht im Repo)

## Entscheidungen
- 21.10.2026: Platzhalter ohne Claude, bis Lias Material-Workflow gebaut wird.

## Offene Punkte
1. Echten Agenten bauen (Schritt 1 der Architektur). Dann Verbrauch: Lia nutzt Jans Pro-Abo.

## Gelernte Regeln
- (noch keine)
