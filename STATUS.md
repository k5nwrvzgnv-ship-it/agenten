# Status: Gesamtsystem (Architekt)

## Zweck
Struktur, Regeln und gemeinsamer Code (shared/) für alle Agenten.

## Stand (14.10.2026)
- Serverprüfung erledigt: 7,8 GB RAM (6,3 GB frei), 4 Kerne, Last nahe 0, 90 GB frei. Git 2.43, Python 3.12.3, Node 22.23. Kein Docker, kein sudo.
- Entscheidung: Weg A, also alles unter User `agent` in /home/agent/agenten, Dienste als systemd-User-Units, kein eigener Linux-User.
- Entscheidung: Freigabe per Telegram, über einen neuen, eigenen Bot.
- Angelegt: Ordner, Git-Repo, .gitignore, CLAUDE.md, README.md, diese Datei.

## Offene Punkte (nächste Schritte)
1. shared/ anlegen: Logging, Config laden (.env), Freigabe-Warteschlange (Datei-basiert, ein JSON pro Entwurf, Zustände offen/freigegeben/abgelehnt), shared/regeln.md.
2. Telegram-Freigabe-Bot: Jan legt bei BotFather einen neuen Bot an und trägt den Token in shared/.env ein (chmod 600).
3. Je Agent eine STATUS.md-Vorlage.
4. Danach: Agent uni im eigenen Chat im Ordner uni/.

## Gelernte Regeln
- (noch keine)
