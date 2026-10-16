# Agenten

Persönliches Agenten-System von Jan. Regeln: siehe CLAUDE.md. Aktueller Stand: siehe STATUS.md.

| Ordner | Agent | Aufgabe |
|---|---|---|
| uni/ | uni | Moodle und Unipostfach überwachen, Fristen, Zusammenfassungen, Lernsessions |
| dokumente/ | dokumente | Anträge, Berichte, PowerPoints, Tabellen erstellen |
| posteingang/ | posteingang | E-Mails lesen, sortieren, Antwortentwürfe |
| einkauf/ | einkauf | Geschenke und Bedarf recherchieren, Vorschläge mit Preisen |
| shared/ | – | agentkit (gemeinsamer Code), Telegram-Zentrale, Warteschlangen, Regeln, Einstellungen, Vorlagen |

## Bedienung über Telegram (@Agentenzentralebot)
- `/uni <Auftrag>` erledigen, `/unilern <Auftrag>` gemeinsam lernen (ebenso dokumente, posteingang, einkauf)
- `/status` Überblick, `/verbrauch` Auslastung des Claude-Kontingents, `/hilfe`
- Entwürfe kommen mit Knöpfen Freigeben / Ablehnen / Ändern. Nach Freigabe handelt der Agent selbst.

## Wichtige Dateien
- `CLAUDE.md`: Regeln für alle Chats. `STATUS.md`: Stand des Gesamtsystems.
- `shared/einstellungen.toml`: änderbare Werte (Limits, Stufen, Modelle, Werkzeuge).
- `shared/.env`: Bot-Token, Chat-ID, Kauflimit (chmod 600, nicht im Repo).
- `shared/vorlagen/`: Vorlagen für neue Agenten.

## Dienste
- `systemctl --user status agentenzentrale`, Logs: `journalctl --user -u agentenzentrale` oder shared/telegram/logs/
- Prüfen: `./pruefen.sh` (alle Tests und Linter ruff). Läuft vor jedem Commit automatisch
  (githooks/pre-commit). Nach neuem Klonen einmal: `git config core.hooksPath githooks` und
  `python3 -m venv .venv && .venv/bin/pip install -r requirements-werkzeuge.txt`.

## Arbeiten mit Claude Code
- Pro Agent ein VS-Code-Fenster im Agent-Ordner öffnen und dort den Chat führen (`/rename <agent>`).
- Struktur und shared/ im Hauptordner bearbeiten.
- Am Ende jeder Sitzung STATUS.md aktualisieren und committen lassen.
- Alte Chats: `/resume`. Neu anfangen: `/clear`. Das Wissen steht in den Dateien, nicht im Chat.
