# Persönliches Agenten-System – Regeln für alle Chats

Jan baut hier ein System aus Agenten, die seinen Alltag vereinfachen. Diese Regeln gelten für jeden Chat in diesem Ordner und allen Unterordnern.

## Arbeitsweise mit Jan
- Deutsch, kurz, klar, ehrlich. Keine Emojis, keine Schönfärberei.
- Jan ist Einsteiger bei Git und Linux-Administration: Befehle vor dem Ausführen kurz erklären.
- Vor dem Anlegen von Benutzern, Installieren von Software oder Einrichten von Diensten: Plan zusammenfassen und auf Jans Okay warten.
- Kleine Schritte. Nach jedem Schritt ein Git-Commit mit verständlicher deutscher Nachricht.
- Nichts erfinden. Bei Unklarheit nachfragen.
- Am Ende einer Arbeitssitzung die STATUS.md des Agenten aktualisieren und committen. Sie ist die Übergabe an den nächsten Chat.

## Harte Regeln
- Agenten handeln nach außen (Mails, Nachrichten, Abgaben, Käufe usw.) nur nach Jans Freigabe des konkreten Entwurfs über die Freigabe-Warteschlange (shared/freigabe/). Nach der Freigabe führt der Agent genau diesen Entwurf einmal aus und meldet das Ergebnis.
- Käufe zusätzlich nur bis zur Obergrenze KAUF_LIMIT_EURO aus shared/.env. Ist kein Wert eingetragen, wird nicht gekauft.
- Zugangsdaten nur in .env-Dateien mit chmod 600, nie im Repo. Neue Geheimnisse vorher gegen .gitignore prüfen.
- Jeder Agent läuft isoliert: eigener Ordner, eigene virtuelle Umgebung (.venv im Agent-Ordner), eigener systemd-User-Dienst oder -Timer.
- Keine dauerhaft laufende Browser-Automation. Browser nur zeitgesteuert und kurz.
- Lernen nur nach Bestätigung: Korrigiert oder lehnt Jan einen Entwurf ab, wird die Regel dahinter vorgeschlagen und erst nach seinem Okay in shared/regeln.md (allgemein) oder in die STATUS.md des Agenten (agentenspezifisch) geschrieben. Agenten lesen beide Dateien bei jedem Lauf.

## Server und Tabus
- Ubuntu-Server (Contabo), 4 Kerne, 7,8 GB RAM, kein Swap. Gearbeitet wird als User `agent` ohne sudo.
- Dienste laufen als systemd-User-Units (`systemctl --user`), Linger ist aktiv.
- Nicht anfassen (Ordner, Dienste, Ports, Zugangsdaten):
  - kcalbot: Systemdienst `kcalbot.service`, User `bot`, /opt/kcalbot, vermutlich Port 8787
  - Vinted-Bot: User-Dienst `vinted-bot.service`, /home/agent/agents/vinted, Port 9222 (lokal)
- Jeder Agent bekommt eigene Zugangsdaten, auch einen eigenen Telegram-Bot-Token. Die Tokens der bestehenden Bots werden nicht wiederverwendet.

## Architektur
- Grundsatz: Claude denkt, Python handelt. Agenten rufen Claude nur über `agentkit.claude_lauf` auf
  (`claude -p`, ohne Bash, Schreibschutz auf Code und Regeln). Nach außen handelt nur Python-Code.
- Warteschlangen sind Ordner mit einer JSON-Datei pro Eintrag: `shared/auftraege/` (Jan -> Agent),
  `shared/freigabe/` (Entwurf -> Jan), `shared/meldungen/` (Agent -> Jan).
- `shared/agentkit/`: config (.env laden), log, einstellungen (einstellungen.toml), auftraege, freigabe,
  meldungen, _ablage (gemeinsame Ablage der Warteschlangen), regeln, verbrauch, claude_lauf.
- `shared/telegram/`: Zentrale (Dienst agentenzentrale), einziger Kontakt zu Jan. zentrale.py = Telegram,
  logik.py = reine, getestete Logik.
- `shared/vorlagen/`: Gerüst für neue Agenten (agent_beispiel.py, Service, Timer, STATUS.md).
- `uni/`, `dokumente/`, `posteingang/`, `einkauf/`: je ein Agent mit agent.py als Einstieg, eigener
  .venv, .env, STATUS.md, tests/. Laufzeitdaten in data/, logs/ (nicht im Repo).
- Reihenfolge der Umsetzung: uni, dokumente, posteingang, einkauf.
- Pro Agent ein eigener Chat, gestartet im Agent-Ordner. Struktur und shared/ werden im Chat im
  Hauptordner bearbeitet. Ein Agent-Chat ändert shared/ nicht, er schreibt den Bedarf in ../STATUS.md.

## Konventionen
- Namen und Kommentare deutsch, ohne Umlaute in Bezeichnern (`pruefen`, nicht `prüfen`).
- Erst agentkit nutzen, nichts davon nachbauen. Fehlt dort etwas, im Hauptordner-Chat ergänzen.
- Möglichst Python-Bordmittel. Neue Pakete nur nach Jans Okay, dann in requirements.txt.
- Logik ohne Netz in eigene, getestete Funktionen (wie fristen.py, logik.py). Netz und Telegram dünn halten.
- Fehler nie still verschlucken: loggen, und wenn Jan es wissen muss, eine Meldung.
- Nur ändern, was zum Auftrag gehört. Aufräumen nebenbei vorher vorschlagen.

## Fertig heißt
- `./pruefen.sh` zeigt ALLES GRÜN (Tests aller Ordner, Linter). Der Git-Hook githooks/pre-commit
  bricht sonst jeden Commit ab. `--no-verify` nur mit Jans Okay.
- Neue Logik hat Tests. Neue Testordner werden in pruefen.sh eingetragen.
- STATUS.md beschreibt den aktuellen Stand, keinen Verlauf (der steht in Git).
