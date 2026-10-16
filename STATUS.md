# Status: Gesamtsystem (Architekt)

Aktueller Stand, kein Verlauf. Wie es dazu kam: `git log`. Architektur und Konventionen: CLAUDE.md.

## Stand (16.10.2026)
- Server: 7,8 GB RAM, 4 Kerne, 90 GB frei, Python 3.12, Node 22, kein Docker, kein sudo.
  Alles unter User `agent` in /home/agent/agenten, Dienste als systemd-User-Units.
- agentkit (shared/agentkit/) fertig und getestet: config, log, einstellungen, auftraege, freigabe,
  meldungen, regeln, verbrauch, claude_lauf. Doku steht jeweils oben im Modul.
  Einbindung per .pth in jede Agent-.venv:
  `python3 -m venv .venv && echo /home/agent/agenten/shared > .venv/lib/python3.12/site-packages/agentkit.pth`
- Freigabe: Fingerabdruck des Entwurfs muss zur Telegram-Anzeige passen, Ausführung genau einmal
  (Sperrdatei), Kauflimit KAUF_LIMIT_EURO=1000 in shared/.env. Unklare Ausführungen werden nie
  automatisch wiederholt, Jan prüft.
- Telegram-Zentrale (Bot @Agentenzentralebot, eigener Token in shared/.env, reagiert nur auf Jans
  Chat-ID) läuft als Dienst agentenzentrale. Kann: Aufträge (/<agent>, /<agent>lern, Text mit
  Agent-Auswahl), Entwürfe mit Freigeben/Ablehnen/Ändern, Meldungen, /status, /verbrauch,
  Antwort auf eine Auftragsmeldung = neuer Auftrag in derselben Claude-Sitzung, /pc und /weiter.
  Dateien und Fotos (bis 20 MB), wartende Dateien hängen am nächsten Auftrag, /verwerfen.
  Startet nach Auftrag oder Freigabe sofort <agent>.service.
  Nach Änderung an zentrale.py oder der Dienstvorlage: Vorlage nach ~/.config/systemd/user/ kopieren
  (falls geändert), `systemctl --user daemon-reload`, `systemctl --user restart agentenzentrale`.
- claude-Läufe ("Claude denkt, Python handelt"): ohne Bash und MCP, Schreiben nur im Agent-Ordner,
  Schreibschutz auf Code/STATUS.md/Regeln/Einrichtung, kein Zugriff auf .env. Alles mit echten
  Läufen getestet. Grundlast ca. 6.300 Tokens pro Lauf.
- Verbrauch: Jan hat ein Pro-Abo, Agenten teilen es mit seinen Chats. Stufen normal/sparen/
  nur_auftraege/limit nach 5h- und 7d-Auslastung, Werte in shared/einstellungen.toml.
  Einschränkung: Auslastung wird nur bei Agenten-Läufen aktualisiert.
- Qualität: `./pruefen.sh` (62 Tests, Linter ruff aus .venv im Hauptordner, Regeln in ruff.toml).
  Git-Hook githooks/pre-commit bricht Commits ab, wenn nicht grün (core.hooksPath = githooks).
- Agent uni läuft (Dienst + Timer 8/13/19 Uhr). Details: uni/STATUS.md.

## Entscheidungen
- Telegram ist die Zentrale in beide Richtungen. Jan diktiert per Handy-Tastatur, nur Text.
  Sprachnachrichten (faster-whisper) eventuell später, nur nach Okay.
- Modus pro Auftrag: `erledigen` (Standard, Protokoll mit Prüfanleitung) oder `lernen` (gemeinsam,
  Telegram und PC-Chat führen dieselbe Sitzung fort). Kein automatischer Vorschlag von lernen.
- Agenten denken mit `claude -p` (~/.local/bin/claude). Laufzeit-Agenten ändern nie Code.
- Rollen für Entwicklungs-Chats nicht eigens gebaut: Plan-Modus und /code-review reichen (16.10.).

## Offene Punkte
1. Im uni-Chat: agent.py muss Antworten fortsetzen. Dafür `claude_lauf.laufen(...,
   sitzung_fortsetzen=a["sitzung"])` wenn der Auftrag eine Sitzung hat, und
   `auftraege.abschliessen(..., sitzung=e.sitzung)` bei jedem Auftrag (nicht nur lernen).
   Der Hinweis "Weiter am PC: ..." in agent.py kann dann entfallen (die Zentrale liefert ihn bei /pc).
   Noch nicht getestet: interaktives `claude --resume <id>` am PC (Jan einmal selbst).
2. Danach: dokumente, posteingang, einkauf (je mit STATUS.md aus shared/vorlagen/).
   dokumente muss Word, PowerPoint und Excel erstellen und formatieren können (Jan, 16.10.).
3. Dateien aus Telegram: gebaut 16.10. (Zentrale nimmt Dokumente und Fotos bis 20 MB an, Ablage
   <agent>/data/eingang/<auftrag-id>/, Pfade im Feld dateien und am Ende des Auftragstexts).
   Noch offen: Handtest durch Jan (Datei mit "/uni ..." als Bildunterschrift, Album, Datei ohne Befehl).
   Für den uni-Chat: Claude liest PDF, Bilder und Text direkt, aber nicht docx/pptx/xlsx. agent.py sollte
   für a["dateien"] vor dem Lauf kurse.als_text() nutzen und <datei>.txt daneben legen.
4. Optional: Token des Bots bei BotFather erneuern (/revoke), da er im Chatverlauf stand.

## Gelernte Regeln
- (noch keine)
