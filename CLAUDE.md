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
- Agenten senden niemals selbst Mails oder Nachrichten und bezahlen nie selbst. Alles geht als Entwurf oder Vorschlag in die Freigabe-Warteschlange (shared/freigabe/) und wartet auf Jans Bestätigung.
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

## Struktur
- `shared/`: gemeinsamer Code (Logging, Config laden, Freigabe-Warteschlange) und `regeln.md`.
- `uni/`, `dokumente/`, `posteingang/`, `einkauf/`: je ein Agent mit eigener STATUS.md.
- Reihenfolge der Umsetzung: uni, dokumente, posteingang, einkauf.
- Pro Agent ein eigener Chat, gestartet im Agent-Ordner. Struktur und shared/ werden im Chat im Hauptordner bearbeitet.
