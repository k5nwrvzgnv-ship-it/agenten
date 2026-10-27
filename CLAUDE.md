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
- Lernen aus Feedback (Jan 27.10.2026): Feedback der Person, für die ein Agent arbeitet (Lia für lia/, Jan für
  seine Agenten), wird ohne vorherige Freigabe übernommen. agentkit.feedback ordnet es zu: Nachbesserung (neuer
  Auftrag an denselben Agenten), Regel (Zeile mit Feedback-ID und Datum in <instanz>/regeln.md oder unter
  "Gelernte Regeln" in der STATUS.md des Agenten) oder Notiz für Code/Oberfläche (STATUS.md des zuständigen
  Ordners; Agenten ändern keinen Code). Wirksam sofort; der Feedback-Dienst committet die geänderte Datei selbst.
- Vetorecht Jan: Zu jedem übernommenen Feedback bekommt Jan eine kurze Zusammenfassung mit Stopp-Knopf. Stopp
  nimmt die Übernahme zurück (Regel bzw. Notiz gelöscht, Nachbesserung zurückgezogen), die Feedbackgeberin
  erfährt es kurz.
- Nie automatisch, sondern als Vorschlag an Jan: alles, was nach außen handelt, Käufe, Limits und die Freigabe
  berührt; Schülerdaten und Datenschutz; Löschen oder Ändern bestehender Regeln (Feedback fügt nur hinzu);
  Regeln, die einer bestehenden Regel oder dieser Datei widersprechen; Lias Feedback zu Jans Agenten oder
  shared/regeln.md; mehr als eine Nachbesserung je Ergebnis oder eine, deren Lauf mehr als 1 USD kosten dürfte.
- Korrekturen an Entwürfen in der Freigabe (Ändern, Ablehnen) laufen wie bisher: Die Regel dahinter wird
  vorgeschlagen und erst nach Jans Okay eingetragen. Agenten lesen die Regeldateien bei jedem Lauf.

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
- Warteschlangen sind Ordner mit einer JSON-Datei pro Eintrag: `shared/auftraege/` (Jan -> Agent,
  Agent -> Agent nur per `auftraege.weitergeben` und nur Paare aus [weitergabe] in einstellungen.toml),
  `shared/freigabe/` (Entwurf -> Jan), `shared/meldungen/` (Agent -> Jan).
- `shared/agentkit/`: config (.env laden), log, einstellungen (einstellungen.toml), auftraege, freigabe,
  meldungen, _ablage (gemeinsame Ablage der Warteschlangen), regeln, verbrauch, claude_lauf, textfassung (Text aus pdf/docx/pptx/xlsx).
- `shared/telegram/`: Zentrale (Dienst agentenzentrale), einziger Kontakt zu Jan. zentrale.py = Telegram,
  logik.py = reine, getestete Logik.
- `shared/renderer/`: gemeinsamer Renderer für Jan und Lia (JSON-Beschreibung rein, docx/pptx/PDF raus),
  reine Bibliothek ohne Inhalte, import per agentkit.pth. Eigene STATUS.md, eigener Chat (siehe unten).
- `shared/vorlagen/`: Gerüst für neue Agenten (agent_beispiel.py, Service, Timer, STATUS.md).
- `uni/`, `dokumente/`, `lia/<agent>/` (geplant: `posteingang/`, `einkauf/`, Ordner entsteht mit dem Agenten): je ein Agent mit agent.py als Einstieg, eigener
  .venv, .env, STATUS.md, tests/. Laufzeitdaten in data/, logs/ (nicht im Repo).
- Reihenfolge der Umsetzung: uni, dokumente, posteingang, einkauf.
- Ein Chat pro Ordner, gestartet in diesem Ordner: je Agent einer (auch lia/<agent>), einer für
  shared/renderer/, einer im Hauptordner für Struktur und das übrige shared/. Ein Chat ändert nur seinen
  Ordner, Bedarf anderswo schreibt er in die STATUS.md des Hauptordners. Gedächtnis ist die STATUS.md,
  nicht der Chat: für jede neue Aufgabe darf ein frischer Chat im selben Ordner starten.

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
