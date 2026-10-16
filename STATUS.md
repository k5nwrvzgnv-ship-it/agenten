# Status: Gesamtsystem (Architekt)

## Zweck
Struktur, Regeln und gemeinsamer Code (shared/) für alle Agenten.

## Stand (14.10.2026)
- Serverprüfung erledigt: 7,8 GB RAM (6,3 GB frei), 4 Kerne, Last nahe 0, 90 GB frei. Git 2.43, Python 3.12.3, Node 22.23. Kein Docker, kein sudo.
- Entscheidung: Weg A, also alles unter User `agent` in /home/agent/agenten, Dienste als systemd-User-Units, kein eigener Linux-User.
- Entscheidung: Freigabe per Telegram, über einen neuen, eigenen Bot.
- Angelegt: Ordner, Git-Repo, .gitignore, CLAUDE.md, README.md, diese Datei.
- 16.10.: shared/ angelegt mit regeln.md, .env.example und den Ordnern freigabe/, auftraege/, agentkit/, telegram/ (Warteschlangen-Ordner sind per .gitignore ausgeschlossen).

## Entscheidungen (16.10.2026)
- Telegram ist die Zentrale in beide Richtungen, nicht nur für Freigaben:
  - Raus: Entwürfe mit Knöpfen Freigeben/Ablehnen/Ändern, Rückfragen, Meldungen.
  - Rein: Aufträge und Korrekturen von Jan als Text (auf dem Handy diktiert oder getippt).
  - Der Bot reagiert nur auf Jans Chat-ID.
- Die Agenten "denken" mit Claude Code im Headless-Modus (`claude -p`, installiert: /home/agent/.local/bin/claude, Version 2.1.301).
- Sprache: Jan diktiert über die Handy-Tastatur, der Bot verarbeitet nur Text. Echte Sprachnachrichten (lokales faster-whisper) eventuell später, nur nach Okay.
- Routing zu den Agenten anfangs per Befehl (`/uni …`, `/einkauf …`). Ohne Befehl fragt der Bot mit Knöpfen nach.
- Aufträge: Warteschlange shared/auftraege/ (neu/, erledigt/), ein JSON pro Auftrag. Der Bot startet danach den passenden Agenten-Dienst sofort.

## Geplante Struktur shared/
- regeln.md, .env.example (im Repo), .env (chmod 600, nicht im Repo)
- agentkit/ (Python-Paket, per `pip install -e` in jede Agent-.venv): config.py, log.py, freigabe.py, auftraege.py, regeln.py
- freigabe/ (offen/, erledigt/), auftraege/ (neu/, erledigt/)
- telegram/: Telegram-Zentrale als eigener User-Dienst mit eigener .venv

## Offene Punkte (nächste Schritte)
1. agentkit: config.py und log.py, danach freigabe.py und auftraege.py mit Tests.
2. Je Agent eine STATUS.md-Vorlage.
3. Telegram-Zentrale: Jan legt bei BotFather einen neuen Bot an und trägt den Token in shared/.env ein (chmod 600). Installation und Dienst nur nach Jans Okay.
4. Klären: Wie laufen mehrere `claude -p`-Aufrufe parallel (Nutzungslimits, Sperre gegen gleichzeitige Läufe), und welche Werkzeuge darf jeder Agent nutzen?
5. Danach: Agent uni im eigenen Chat im Ordner uni/.

## Gelernte Regeln
- (noch keine)
