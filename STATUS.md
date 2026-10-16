# Status: Gesamtsystem (Architekt)

## Zweck
Struktur, Regeln und gemeinsamer Code (shared/) für alle Agenten.

## Stand (14.10.2026)
- Serverprüfung erledigt: 7,8 GB RAM (6,3 GB frei), 4 Kerne, Last nahe 0, 90 GB frei. Git 2.43, Python 3.12.3, Node 22.23. Kein Docker, kein sudo.
- Entscheidung: Weg A, also alles unter User `agent` in /home/agent/agenten, Dienste als systemd-User-Units, kein eigener Linux-User.
- Entscheidung: Freigabe per Telegram, über einen neuen, eigenen Bot.
- Angelegt: Ordner, Git-Repo, .gitignore, CLAUDE.md, README.md, diese Datei.
- 16.10.: shared/ angelegt mit regeln.md, .env.example und den Ordnern freigabe/, auftraege/, agentkit/, telegram/ (Warteschlangen-Ordner sind per .gitignore ausgeschlossen).
- 16.10.: agentkit/config.py (lade_config: shared/.env, dann Agent-.env, Agent gewinnt; bricht ab, wenn eine .env nicht chmod 600 ist) und agentkit/log.py (hole_logger: <agent>/logs/<name>.log, 1 MB x 5 Dateien, plus stderr). Nur Python-Bordmittel. Tests: `cd shared && python3 -m unittest discover -s agentkit/tests -t .`
- 16.10.: agentkit/freigabe.py (neuer_entwurf, offene, erledigte, entscheide: freigegeben/abgelehnt/aendern; bei aendern Kommentar Pflicht, neuer Entwurf verweist per `vorgaenger` auf den alten) und agentkit/auftraege.py (neuer_auftrag, neue, erledigte, abschliessen: erledigt/fehlgeschlagen; `bezug` für Korrekturen zu einem Entwurf). Gemeinsame Ablage in _ablage.py: ein JSON pro Eintrag, ID-Format `JJJJMMTT-HHMMSS-agent-xxxxxx` (wird streng geprüft, da IDs später aus Telegram-Knöpfen kommen), atomares Schreiben, Abschließen geht nur einmal. 12 Tests grün.
- 16.10.: Feld `modus` in auftraege.py (erledigen/lernen, Standard erledigen). uni/STATUS.md angelegt mit den Anforderungen zu den zwei Modi. 13 Tests grün.
- 16.10.: agentkit/regeln.py: allgemeine_regeln(), agent_regeln(), regeln_als_text() (Block für den Prompt), regel_vorschlagen() (legt Entwurf Typ "regel" in die Freigabe), regel_eintragen() (nur bei Status freigegeben, kein doppelter Eintrag). 19 Tests grün.
- 16.10.: Harte Regel in CLAUDE.md geändert (Jans Entscheidung): Agenten handeln nach Freigabe selbst, genau einmal, und melden das Ergebnis. Käufe nur bis KAUF_LIMIT_EURO (shared/.env, leer = kein Kauf).
- 16.10.: freigabe.py erweitert: Fingerabdruck (sha256 über agent, typ, titel, inhalt, daten) wird beim Anlegen gespeichert. entscheide(..., "freigegeben", gesehen=<fingerabdruck>) gibt nur frei, wenn der Abdruck zur Telegram-Anzeige passt. Ausführung: zur_ausfuehrung(), ausfuehrung_beginnen() (prüft Abdruck und Kauflimit, Sperrdatei mit O_EXCL, also nur einmal), ausfuehrung_abschliessen(), unklare() (begonnen, nie abgeschlossen: wird nicht automatisch wiederholt, Jan prüft). 25 Tests grün.
- 16.10.: shared/.env angelegt (chmod 600, von Git ignoriert): Token des neuen Bots @Agentenzentralebot (per getMe geprüft), KAUF_LIMIT_EURO=1000, TELEGRAM_CHAT_ID (Jan, @jkl298) per getUpdates ermittelt und eingetragen.
- 16.10.: Telegram-Zentrale in shared/telegram/: .venv mit python-telegram-bot[job-queue] 22.8 (requirements.txt), agentkit per .pth. zentrale.py (Handler), logik.py (testbar, 4 Tests). Kann: nur Jans Chat-ID, /<agent> und /<agent>lern -> Auftrag, Text ohne Befehl -> Agent per Knopf wählen, /status, alle 30 s neue Entwürfe mit Freigeben/Ablehnen/Ändern (lange Texte aufgeteilt, nichts abgeschnitten), Meldungen zu Ausführung, unklaren Fällen und erledigten Aufträgen. Bereits Gezeigtes in data/gemeldet.json. httpx-Log auf WARNING (sonst steht der Token im Log).
- 16.10.: Handtest mit Jan bestanden: Entwurf kam an, Freigeben, /status und /uni Test funktionierten. Testdaten gelöscht. Noch kein Dienst eingerichtet.

## Entscheidungen (16.10.2026)
- Telegram ist die Zentrale in beide Richtungen, nicht nur für Freigaben:
  - Raus: Entwürfe mit Knöpfen Freigeben/Ablehnen/Ändern, Rückfragen, Meldungen.
  - Rein: Aufträge und Korrekturen von Jan als Text (auf dem Handy diktiert oder getippt).
  - Der Bot reagiert nur auf Jans Chat-ID.
- Die Agenten "denken" mit Claude Code im Headless-Modus (`claude -p`, installiert: /home/agent/.local/bin/claude, Version 2.1.301).
- Sprache: Jan diktiert über die Handy-Tastatur, der Bot verarbeitet nur Text. Echte Sprachnachrichten (lokales faster-whisper) eventuell später, nur nach Okay.
- Routing zu den Agenten anfangs per Befehl (`/uni …`, `/einkauf …`). Ohne Befehl fragt der Bot mit Knöpfen nach.
- Modus pro Auftrag (allgemein, für alle Agenten): `erledigen` (Standard; allein arbeiten, danach Protokoll mit Prüfanleitung) oder `lernen` (gemeinsam Schritt für Schritt, per Telegram und im PC-Chat). Telegram: `/uni …` = erledigen, `/unilern …` = lernen (Befehlsnamen vorläufig). Details: uni/STATUS.md.
- Aufträge: Warteschlange shared/auftraege/ (neu/, erledigt/), ein JSON pro Auftrag. Der Bot startet danach den passenden Agenten-Dienst sofort.

## Entscheidung agentkit-Einbindung (16.10.2026)
- agentkit wird nicht installiert, sondern per .pth-Datei in jede Agent-.venv eingebunden:
  `python3 -m venv .venv && echo /home/agent/agenten/shared > .venv/lib/python3.12/site-packages/agentkit.pth`
  Danach funktioniert `from agentkit import config, log, freigabe, auftraege, regeln` in der .venv.

## Geplante Struktur shared/
- regeln.md, .env.example (im Repo), .env (chmod 600, nicht im Repo)
- agentkit/ (Python-Paket, per .pth-Datei in jede Agent-.venv): config.py, log.py, freigabe.py, auftraege.py, regeln.py
- freigabe/ (offen/, erledigt/), auftraege/ (neu/, erledigt/)
- telegram/: Telegram-Zentrale als eigener User-Dienst mit eigener .venv

## Offene Punkte (nächste Schritte)
1. (erledigt, siehe Entscheidung agentkit-Einbindung)
2. Je Agent eine STATUS.md-Vorlage.
2a. (erledigt: Der Agent führt nach Freigabe selbst aus, siehe freigabe.py.) Die Telegram-Zentrale muss beim Freigeben den Fingerabdruck des angezeigten Entwurfs mitgeben und unklare() regelmäßig melden.
3. Telegram-Zentrale als systemd-User-Dienst agentenzentrale.service einrichten (nach Jans Okay). Später: Agenten-Dienst nach neuem Auftrag sofort starten.
4. Klären: Wie laufen mehrere `claude -p`-Aufrufe parallel (Nutzungslimits, Sperre gegen gleichzeitige Läufe), und welche Werkzeuge darf jeder Agent nutzen?
5. Danach: Agent uni im eigenen Chat im Ordner uni/.

## Gelernte Regeln
- (noch keine)
