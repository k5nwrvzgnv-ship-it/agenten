# Untersuchung des Agenten-Systems, November 2026

Stand: 16.11.2026, gemessen zwischen 12:42 und 12:55 Uhr auf dem Server, als User `agent`.
Zeitraum der Daten: 17.10. bis 16.11.2026 (30 Tage), soweit nicht anders genannt.
Es wurde nur gelesen und gemessen. Geändert wurde nichts außer dieser Datei.

"Beobachtet" heißt: mit Befehl oder Codestelle belegt. "Vermutet" heißt: aus dem Code geschlossen, nicht ausgeführt.
Der Bericht enthält keine Inhalte aus Mails, Schülerdaten oder Lias Texten, nur Zählungen und Pfade.

Zwei Dinge vorweg, die vom Auftrag abweichen:
- `pruefen.sh` lief einmal für die Messung (mit Sperre). Der Commit dieses Berichts über `commit.sh` startet es
  durch den Hook ein zweites Mal. Das ließ sich nicht vermeiden, ohne `--no-verify` zu nehmen.
- Screenshots waren nicht möglich (siehe Abschnitt "Nicht geprüft"). Die Oberfläche ist aus Code, CSS,
  abgerufenem HTML (nur Elemente gezählt) und den Zugriffsprotokollen bewertet.

---

## Die 10 wichtigsten Befunde

Sortiert nach Wirkung durch Aufwand. Einzelheiten und Belege stehen unter der jeweiligen Nummer weiter unten.

| Nr | Befund | Art | Schwere | Aufwand | Ordner |
|---|---|---|---|---|---|
| B1 | Schreibschutz für Claude hat eine Lücke: Vorlagen, Skripte und Pfad-Units im Agent-Ordner sind nicht geschützt. Im Ordner `uni/` liegen die Vorlagen des Uni-Portals. | vermutet | hoch | S | Hauptordner (agentkit) |
| B2 | Ein Test startet bei jeder Prüfung einen echten Claude-Lauf auf dem Agenten-Konto: 684 von 821 "uni"-Läufen sind Testläufe. | beobachtet | mittel | S | uni |
| B3 | Der Speicher ist durch offene Claude-Chats belegt (39 Prozesse, 6,8 GB). Echte Ausfälle der Zentralen und der Web-App am 01.11. und 03.11. | beobachtet | hoch | S | Jan (Bedienung), Hauptordner |
| B4 | Tests schreiben in echte Logdateien. Im Feedback-Log stammen rund 20.000 von 20.800 Zeilen aus Tests, echte Einträge rotieren heraus. | beobachtet | mittel | S | Hauptordner, je Agent |
| B5 | Offene Freigaben veralten ohne Erinnerung: 5 offen, 3 davon älter als 18 Tage. Ein später Klick würde eine wochenalte Mail senden. | beobachtet | mittel | S | Hauptordner (telegram, agentkit) |
| B6 | Das Kontingent bremst: an 20 Tagen gab es gedrosselte Läufe, seit 14.11. durchgehend Stufe "sparen". Opus macht 84 % der Kosten. | beobachtet | mittel | M | Hauptordner, uni, lia/theater, lia/recherche |
| B7 | `pruefen.sh` braucht 3:47 Minuten und läuft bei jedem Commit über alles. 261 fehlgeschlagene Test-Scopes hängen in systemd. | beobachtet | mittel | M | Hauptordner, holzbalkenscan |
| B8 | Die Sicherung umfasst nur Git. Rund 0,7 GB Arbeitsdaten von Lia, die Warteschlangen und alle `.env` liegen nur auf diesem Server. | beobachtet (dass keine zweite Sicherung existiert: vermutet) | hoch | M | Hauptordner (sicherung) |
| B9 | Drei Web-Oberflächen werden kaum genutzt: Lia-Web-App 31 Schreibaktionen in 30 Tagen und seit 11.11. kein Zugriff, Uni-Portal an einem Tag. | beobachtet | mittel | M | shared/webapp, uni, shared/arbeitsplatz |
| B10 | Lias Telegram-Menü: zwei von vier Hauptknöpfen sind seit dem 21.10. Platzhalter ("kommt bald"), dazu Auswahl- und Bestätigungsschritte gegen "Schlau statt Schalter". | beobachtet | mittel | S | Hauptordner (telegram) |

---

## Schritt 0: Maßstab

Woran "gut" gemessen wird und welche Daten das belegen.

| Größe | Was "gut" heißt | Belegt durch | Heute |
|---|---|---|---|
| Zeitersparnis | Aufträge werden ohne Nacharbeit fertig, Ergebnisse werden benutzt | Aufträge je Woche, Anteil fehlgeschlagen, Anteil mit Bezug (Nachfrage oder Korrektur), Dauer; Nutzung der Oberflächen | Jan: 92 Aufträge, 7 fehlgeschlagen (8 %), 23 mit Bezug (25 %). Lia: 33 Aufträge, 2 fehlgeschlagen, 18 mit Bezug (55 %, davon 9 Feedback). Direkt in Minuten ist die Ersparnis nicht messbar. |
| Harte Regeln | Jede Regel hat eine Stelle im Code und einen Test | Tabelle in Schritt 2 | 7 von 14 Regeln voll belegt, 7 mit Lücke |
| Ausfälle | Kein Dienst fällt aus, jeder Ausfall wird gemeldet | `journalctl --user`, `systemctl --user show`, `shared/ausfall/stand.json` | 19 Ausfälle von Diensten an 6 Tagen, alle durch Speichermangel |
| Kosten | Kontingent reicht, Agenten laufen in Stufe "normal" | `shared/verbrauch/laeufe.jsonl` | 1942 Läufe, rechnerisch 387 USD, 39 % der gezählten Läufe gedrosselt |
| Bedienaufwand | Wenige Schritte, keine Sackgassen, nichts bleibt liegen | Schritte je Aufgabe (Schritt 6), Wartezeit und Alter der Freigaben, Zugriffsprotokolle | Freigabe im Median nach 6 Minuten, aber 5 Entwürfe bleiben liegen |

---

## Schritt 1: Rohdaten

### Dienste (Journal, 30 Tage)

Befehl: `journalctl --user --since "30 days ago" -t systemd`, Zeilen zu Vinted herausgefiltert.

| Tag | Unit | Ergebnis |
|---|---|---|
| 18., 19., 20., 21.10. | uni-transkript.service | oom-kill, je einmal |
| 01.11. | agentenzentrale, lia-zentrale, webapp, lia-theater | oom-kill, je einmal |
| 03.11. | agentenzentrale (2), lia-zentrale (1), webapp (8) | oom-kill und signal |
| 07.11. | zwei holzbalkenscan-Läufe (Scope) | oom-kill an der eigenen Speichergrenze, so gewollt |

- `ausfall@` wurde am 01.11. viermal und am 03.11. elfmal gestartet. Für die vier Ausfälle von uni-transkript
  im Oktober zeigt das Journal keinen Start von `ausfall@` (vermutet: OnFailure kam erst danach).
- `NRestarts=0` bei allen Diensten, seit dem 10.11. kein Ausfall eines Dienstes.
- Die Zeilen "app.slice: A process of this unit has been killed by the OOM killer" an weiteren Tagen stehen
  jeweils direkt nach einem `daemon-reload` und sind ein wiederholter alter Zähler, kein neuer Ausfall.
- `systemd-analyze --user verify` auf alle eigenen Units: keine Ausgabe, also ohne Befund.
- Installierte Unit-Dateien und die Vorlagen im Repo sind identisch (`cmp`, keine Abweichung).

### Warteschlangen

| | Jan (`shared/`) | Lia (`lia/instanz/`) |
|---|---|---|
| Aufträge erledigt | 92 | 33 |
| davon fehlgeschlagen | 7 | 2 |
| Freigaben entschieden | 16 (9 freigegeben, 6 "ändern", 1 abgelehnt) | 0 |
| Freigaben offen | 5 (Alter 2, 12, 18, 19, 20 Tage) | 1 (seit 25.10.) |
| Meldungen gesendet | 160 | 2 |

- Freigaben nur von uni (18) und posteingang (3). 37,5 % der Entscheidungen waren "ändern".
- Wartezeit bis zur Entscheidung: Median 0,1 Stunden, Maximum 67 Stunden (16 Fälle).
- Aufträge je Agent (Jan): uni 45, holzbalkenscan 20, feedback 10, posteingang 6, dokumente 4, finance 4, lia 3.
- Herkunft: Telegram 49, von Hand am Server 21 (alle 20 holzbalkenscan-Aufträge), Knopf 5, Feedback 5, Chat 4.
- Aufträge je Agent (Lia): theater 14, feedback 9, recherche 6, unterricht 4.
- Meldungen an Jan: uni 76, posteingang 25, recherche 22, holzbalkenscan 18, feedback 14. Länge im Median
  373 Zeichen, 21 über 1000 Zeichen. 24 Meldungen entstanden zwischen 0 und 6 Uhr.

### Verbrauch (`shared/verbrauch/laeufe.jsonl`, 30 Tage)

| Instanz | Agent | Läufe | USD (rechnerisch) | nicht ok | letzter Lauf |
|---|---|---|---|---|---|
| Jan | uni | 821 (davon 684 Testläufe, siehe B2) | 108,22 | 6 | 16.11. |
| Lia | theater | 57 | 91,20 | 1 | 08.11. |
| Lia | recherche | 44 | 76,63 | 3 | 14.11. |
| Jan | vinted (Konto "login") | 832 | 44,60 | 57 | 03.11. |
| Jan | finance | 30 | 26,01 | 2 | 09.11. |
| Lia | unterricht | 22 | 23,55 | 0 | 30.10. |
| Lia | auswertung | 16 | 4,88 | 0 | 09.11. |
| Jan | dokumente | 8 | 2,49 | 0 | 09.11. |
| Lia | examen | 3 | 2,47 | 0 | 25.10. |
| Lia | chat | 30 | 2,42 | 0 | 10.11. |
| Jan | posteingang | 39 | 2,31 | 0 | 16.11. |
| Jan | uniportal | 5 | 1,90 | 0 | 04.11. |
| | übrige (feedback, schnell, kleinanzeigen, Tests) | 35 | 0,33 | 0 | |

- Summe 1942 Läufe, 387,03 USD. Nach Modell: opus 326,62 USD (240 Läufe), claude-opus-5-5 44,60 (Vinted),
  sonnet 15,32, haiku 0,48.
- Je Woche: KW 43 24,81 USD, KW 44 141,55, KW 45 155,99, KW 46 64,59.
- Median je Auftrag: theater 7,44 USD (höchster 16,80), finance 6,85, unterricht 1,73.
- Stufe (nur Läufe mit Angabe, 1110): normal 679, sparen 334, nur_auftraege 97.

### Git

- 796 Commits seit 14.10., davon 727 in 30 Tagen (148 bis 210 je Woche).
- Meistgeändert: `STATUS.md` (199 Commits), `uni/STATUS.md` (91), `shared/webapp/tests/test_app.py` (66),
  `shared/webapp/STATUS.md` (66), `shared/webapp/app.py` (52), `shared/webapp/logik.py` (47), `uni/agent.py` (38).
- 25 Commits mit Wörtern wie "fix", "behoben", "repariert". Häufung bei shared/renderer (pruefung.py 4-mal),
  lia/unterricht (material.py, agent.py je 3-mal), shared/webapp und shared/telegram/logik.py (je 3-mal).
- Größte Dateien: `shared/webapp/app.py` 3128 Zeilen, `shared/webapp/logik.py` 1876, `uni/agent.py` 1513,
  `shared/agentkit/strukturpflege.py` 1350.

### Regeln

- `shared/regeln.md` und `lia/instanz/regeln.md` enthalten je eine Zeile unter "Regeln", also noch keine echte.
- Gelernte Regeln in den STATUS-Dateien: lia/unterricht 15, uni 4, lia/theater 2, alle anderen 0.
- Häufung bei lia/unterricht: 13 der 15 Regeln stammen vom 23. bis 25.10. Sie kreisen um drei Themen:
  Auswahl und Beleg von Positionen (4), Sprache und Form für die Lerngruppe (5), Fälle und Themen (3).
  Seit dem 27.10. kam keine Regel dazu, der Agent lief zuletzt am 30.10.

### Nutzung

Siehe Abschnitt "Vereinfachen oder stilllegen".

---

## Schritt 2: Harte Regeln gegen Code

| Regel aus CLAUDE.md | Stelle im Code | Test | Urteil |
|---|---|---|---|
| Nach außen nur nach Freigabe des konkreten Entwurfs | `shared/agentkit/freigabe.py:153-182`, Aufrufer `uni/agent.py:108-118`, `posteingang/agent.py:258-270` | `shared/agentkit/tests/test_warteschlangen.py:63,71,81,119`, `uni/tests/test_agent.py:374` | belegt, mit zwei Lücken: `mail.senden` (`shared/agentkit/mail.py:222`) prüft selbst keine Freigabe, und `kleinanzeigen/bot.py:231,319` sendet ohne Freigabe (siehe B12) |
| Genau dieser Entwurf, genau einmal | Fingerabdruck `freigabe.py:36-40,120,168`, Sperrdatei mit O_EXCL `freigabe.py:173-178`, Anhänge mit Prüfsumme `mail.py:183-191` | `test_warteschlangen.py:81,119`, `test_mail.py:134` | belegt |
| Anzeige in Telegram gleich Ausführung | `shared/telegram/zentrale.py:646-647,724`, `logik.py:263-291` | `shared/telegram/tests/test_logik.py` (Anzeige), kein Test für `zentrale.knopf` | Code belegt, Test für den Knopf-Weg fehlt |
| Käufe nur bis KAUF_LIMIT_EURO, ohne Wert kein Kauf | `freigabe.py:185-194` | `test_warteschlangen.py:135` | belegt. Greift nur, wenn der Agent den Entwurf als Typ "kauf" anlegt. Bisher legt kein Agent Käufe an. |
| Zugangsdaten nur in .env mit 600, nie im Repo | `shared/agentkit/config.py:42-46`, `.gitignore:2-4` | `shared/agentkit/tests/test_config_log.py:34` | belegt. Alle 9 `.env` haben 600. |
| Claude ohne Bash, Schreibschutz auf Code und Regeln | `shared/agentkit/claude_lauf.py:44-50,279-289` | `test_claude_lauf.py:83-89` | Lücke: Der Test prüft nur, dass die Muster in der Liste stehen. Ob `claude` sie durchsetzt, ist von Hand getestet (16.10., 10.11.). Die Liste selbst ist unvollständig (B1). |
| Jeder Agent isoliert (Ordner, venv, Dienst) | nur Aufbau, keine technische Grenze | keiner | Lücke: Alle Dienste laufen als User `agent`, keine Unit hat `ProtectHome`, `ReadWritePaths` oder Ähnliches. Jeder Agent-Prozess kann jede `.env` lesen (B13). |
| Keine dauerhafte Browser-Automation | kein Treffer für playwright, selenium, webdriver im Repo | keiner | erfüllt durch Abwesenheit, nicht erzwungen |
| Feedback wird übernommen, Jan hat Stopp | `shared/agentkit/feedback.py:205-216`, `shared/feedback/lauf.py` | `test_feedback.py:44,97`, `shared/feedback/tests/test_lauf.py:66,86` | belegt |
| Nie automatisch: Außenwirkung, Käufe, Limits, Datenschutz, Widerspruch | `feedback.py:90-93,181,207-210` | `test_feedback.py:32,48` | Lücke: Ob etwas "heikel" ist oder widerspricht, entscheidet das Modell in seiner JSON-Antwort. Der Code prüft nur das Feld (B11). |
| Grenzen 1 Nachbesserung und 1 USD nur für Jans Agenten | `feedback.py:39-40,214-216` | `test_feedback.py:66`, `test_lauf.py:190` | belegt |
| Feedback fügt nur hinzu | `shared/agentkit/regeln.py:147,162` (entfernt nur Zeilen mit eigener Feedback-ID) | `test_regeln.py:96,113` | belegt |
| Agent an Agent nur erlaubte Paare | `shared/agentkit/auftraege.py:150-179` | `test_warteschlangen.py:308-323,374` | belegt |
| Commit nur über commit.sh, Hook prüft | `commit.sh`, `githooks/pre-commit`, `core.hooksPath = githooks` | keiner | Lücke: `shared/feedback/lauf.py:76` ruft `git commit` direkt und ohne die Sperre auf (B14) |

---

## Befunde im Einzelnen

### B1 Schreibschutz hat eine Lücke bei Vorlagen und Skripten

- **Was:** Claude darf im Agent-Ordner schreiben (`--permission-mode acceptEdits`). Verboten sind nur die Muster
  in `GESCHUETZT`: `*.py`, `*.pth`, `*.sh`, `*.toml`, `*.service`, `*.timer`, STATUS.md, CLAUDE.md, regeln.md
  und einige mehr. Nicht geschützt sind `*.html`, `*.js`, `*.css`, `*.path`, `*.json` und alle übrigen `.md`.
  Im Ordner `uni/` liegt das Uni-Portal: 11 Jinja-Vorlagen, htmx, CSS, zwei Pfad-Units. Der Portal-Dienst lädt
  Vorlagen aus `uni/portal/vorlagen` (`uni/portal/app.py:78`). Jinja-Vorlagen sind ausführbarer Code im
  Portal-Prozess. Der Agent uni liest fremden Text (Mails, Moodle, Webseiten) und hat dabei Edit und Write.
  Kette: fremder Text bringt Claude dazu, eine Vorlage zu ändern, der Portal-Dienst führt sie beim nächsten
  Seitenaufruf aus und kann als User `agent` alle `.env` lesen.
- **Beleg:** `shared/agentkit/claude_lauf.py:48-50`. Zählung der verfolgten, ungeschützten Dateien:
  `git ls-files uni | grep -vE '\.(py|pth|sh|toml|service|timer)$|...'` ergibt für uni 11 html, 1 js, 1 css,
  2 path, 3 json, 8 md, dazu Schriften und Prüfsummen. Bei kleinanzeigen 1 html (Testdaten), bei lia/chat und lia/schnell je 1 path.
- **Art:** vermutet. Die Kette wurde nicht ausgeführt. Dass Claude solche Dateien wirklich schreiben darf, folgt
  aus acceptEdits und der Liste; ein eigener Rechtetest scheiterte am abgelaufenen Login (siehe "Nicht geprüft").
- **Schwere:** hoch. **Aufwand:** S.
- **Vorschlag:** Die Liste umdrehen. Schreiben nur in `data/**` und ausdrücklich genannten Ausgabeordnern
  erlauben, alles andere im Agent-Ordner verbieten. Als Sofortmaßnahme `*.html`, `*.js`, `*.css`, `*.path`,
  `*.json` außerhalb von `data/` in `GESCHUETZT` aufnehmen.
- **Ordner:** Hauptordner (shared/agentkit).
- **Messgröße:** Ein Test geht alle von Git verfolgten Dateien jedes Agent-Ordners durch und verlangt, dass
  jede unter ein Verbotsmuster fällt. Ziel: 0 ungeschützte verfolgte Dateien (heute uni 32).

### B2 Ein Test startet echte Claude-Läufe

- **Was:** Bei jedem Lauf von `pruefen.sh` entsteht ein echter Eintrag im Verbrauchsprotokoll: Agent uni,
  Auftrag "a3", Modell haiku oder sonnet, rund 9000 Tokens, 1 Schritt. "a3" ist eine Test-Kennung aus
  `uni/tests/test_agent.py:124-131`. Der Test ersetzt `agent.claude_lauf.laufen`, aber mehrere Funktionen in
  `uni/agent.py` haben `laufen=claude_lauf.laufen` als Vorgabewert (z. B. Zeilen 253, 411, 472, 727, 749).
  Vorgabewerte werden beim Laden gebunden und vom Ersetzen nicht erfasst (Ursache vermutet, Wirkung beobachtet).
- **Beleg:** Während meines Prüflaufs entstand um 12:50:56 der Eintrag
  `{'agent': 'uni', 'auftrag': 'a3', 'modell': 'haiku', 'tokens': 8979, 'dauer_s': 5.0, 'stufe': 'sparen'}`.
  Zählung über 30 Tage: 684 Einträge mit Auftrag "a3", 5,63 Mio. Tokens, 6,63 USD. Je Tag so viele wie
  Prüfläufe (09.11. und 10.11. je 59).
- **Art:** beobachtet.
- **Schwere:** mittel. Folgen: Das Agenten-Konto zahlt für Tests (7-Tage-Fenster steht bei 80 %), die Statistik
  von uni ist zu 83 % Testrauschen, Tests brauchen Netz und Konto, und der Testlauf hält die Sperre
  `uni/data/lauf.lock`, kann also einen echten Lauf um 8, 13 oder 19 Uhr verdrängen (Letzteres vermutet).
- **Aufwand:** S.
- **Vorschlag:** Im Test die Funktion am Ziel ersetzen oder `laufen` ausdrücklich übergeben. Zusätzlich in
  `pruefen.sh` `AGENTKIT_CLAUDE_BIN=/bin/false` setzen (die Variable gibt es schon, `claude_lauf.py:38`), dann
  fällt jeder künftige Ausrutscher sofort auf.
- **Ordner:** uni, Hauptordner (pruefen.sh).
- **Messgröße:** 0 neue Einträge in `laeufe.jsonl` während `pruefen.sh`.

### B3 Speicher: offene Claude-Chats verdrängen die Dienste

- **Was:** Von 7,9 GB sind 6,5 GB belegt, verfügbar 1,3 GB. 39 Claude-Prozesse (Chats über die Desktop-App)
  belegen zusammen 6,8 GB RSS, 19 davon laufen länger als 24 Stunden (3,2 GB). Alle eigenen Dienste zusammen
  brauchen rund 0,3 GB. Die echten Ausfälle am 01.11. und 03.11. trafen die kleinen Dauerdienste
  (agentenzentrale 46 MB, lia-zentrale 40 MB, webapp), weil der Kernel beim Speichermangel sie auswählte.
- **Beleg:** `ps -eo rss,etimes,args | grep ccd-cli` (39 Prozesse, 6834 MB; älter als 24 h: 19, 3157 MB),
  `free -m` (available 1373), Journal siehe Schritt 1. Summe aller `MemoryMax` der Units: 15,3 GB bei 7,9 GB RAM.
  Keine Unit hat `OOMScoreAdjust` oder `MemoryHigh`. `lia-chat-aufraeumen.service` hat keine Grenze.
- **Art:** beobachtet.
- **Schwere:** hoch (einziger Ausfallgrund im Zeitraum). **Aufwand:** S.
- **Vorschlag:** (1) Alte Chats schließen oder in der App automatisch archivieren lassen; als Regel in
  CLAUDE.md: höchstens so viele offene Chats, dass 2,5 GB frei bleiben. (2) Den Dauerdiensten
  `OOMScoreAdjust=-500` geben, damit bei Mangel zuerst Läufe und Chats sterben, nicht die Zentrale.
  (3) Swap wäre die robusteste Lösung, braucht aber root.
- **Ordner:** Jan (Bedienung), Hauptordner (Units).
- **Messgröße:** `free -m` available über 2500 MB im Tagesmittel; 0 Zeilen "oom-kill" für Dienste in 30 Tagen.

### B4 Tests schreiben in echte Logs

- **Was:** `agentkit.log.hole_logger` schreibt immer nach `<agent>/logs/`. Tests, die Agentencode laden, schreiben
  dorthin. Die Logs rotieren bei 1 MB mit 5 alten Dateien, echte Einträge verschwinden dadurch schnell.
- **Beleg:** Vorher-Nachher-Vergleich aller Laufzeitdateien um meinen Prüflauf: geändert wurden
  `shared/feedback/logs/feedback.log` (35 Zeilen), `posteingang/logs/posteingang.log` (21),
  `lia/unterricht/logs/unterricht.log` (12), `lia/recherche/logs/recherche.log` (299, davon 37 ERROR/WARNING).
  Im Feedback-Log liegen 20.025 von 20.811 Zeilen in Sekunden mit fünf oder mehr Zeilen (Testmuster), darunter
  rund 1700 ERROR/WARNING.
- **Art:** beobachtet.
- **Schwere:** mittel (Fehlersuche wird unzuverlässig, echte Fehler gehen unter). **Aufwand:** S.
- **Vorschlag:** Wie bei den Ereignissen eine Umgebungsvariable (`AGENTKIT_LOG_DIR`) in `log.py` beachten und in
  `pruefen.sh` auf einen Wegwerf-Ordner setzen.
- **Ordner:** Hauptordner (agentkit, pruefen.sh).
- **Messgröße:** Keine Datei unter `*/logs/` ändert sich während `pruefen.sh`.

### B5 Offene Freigaben veralten

- **Was:** Die Zentrale zeigt jeden Entwurf genau einmal (`zentrale.py:731`). Danach erinnert nichts mehr, und
  es gibt kein Verfallsdatum. Die Knöpfe unter der alten Nachricht bleiben gültig.
- **Beleg:** `shared/freigabe/offen/`: 5 Einträge, erstellt am 27.10. (uni, Mail), 28.10. (posteingang, Mail),
  28.10. (uni, Regel), 04.11. (uni, Mail), 13.11. (posteingang, Mail). Lia: 1 Entwurf von examen seit 25.10.
  Erneut ansehen kostet drei Schritte (/start, "Entwürfe (5)", "Alle mit Knöpfen anzeigen") und sendet dann
  alle fünf auf einmal.
- **Art:** beobachtet.
- **Schwere:** mittel. **Aufwand:** S.
- **Vorschlag:** Entwürfe nach einer festen Frist (z. B. 7 Tage) selbst als "abgelaufen" abschließen und das
  kurz melden. Einmal täglich eine Zeile, wenn etwas älter als 24 Stunden offen ist. Im Menü jeden Entwurf
  einzeln antippbar machen.
- **Ordner:** Hauptordner (shared/telegram, shared/agentkit).
- **Messgröße:** Ältester offener Entwurf jünger als 7 Tage; Zahl offener Entwürfe am Wochenende 0.

### B6 Kontingent bremst den Betrieb

- **Was:** Das Agenten-Konto steht im 7-Tage-Fenster bei 80 % (Stufe "sparen" ab 70 %). An 20 Tagen gab es
  gedrosselte Läufe, seit dem 14.11. liefen alle 74 Läufe in Stufe "sparen". Opus verursacht 326,62 von
  387,03 USD. Am 15.11. kam kleinanzeigen dazu (alle 5 Minuten, laut eigener STATUS rund 75 USD im Monat).
- **Beleg:** `laeufe.jsonl`: Stufen normal 679, sparen 334, nur_auftraege 97. Letzter Stand
  `{'5h': 0.01, '7d': 0.8}`. Teuerste Einzelläufe: uni 10,38 USD, 7,49, 7,36; recherche 6,58.
- **Art:** beobachtet.
- **Schwere:** mittel. **Aufwand:** M.
- **Vorschlag:** Kosten je Auftrag im Ergebnis vermerken und wöchentlich je Agent zusammenzählen (B18).
  Für teure Schritte prüfen, ob Sonnet reicht (heute entscheidet nur "routine" oder "anspruchsvoll" je Aufruf).
  Den Takt von kleinanzeigen an die Stufe koppeln (in "sparen" 15 statt 5 Minuten).
- **Ordner:** Hauptordner, uni, lia/theater, lia/recherche, kleinanzeigen.
- **Messgröße:** Anteil der Läufe in Stufe "normal" über 90 % je Woche; USD je Auftrag (Median) je Agent.

### B7 Prüfung ist langsam und hinterlässt Reste

- **Was:** `pruefen.sh` lief 3:47 Minuten (2679 Tests in 25 Ordnern, dazu ruff), alles grün. Der Hook startet
  das bei jedem Commit vollständig. Bei 727 Commits in 30 Tagen sind das rechnerisch rund 46 Stunden Prüfzeit,
  jeweils seriell hinter der Sperre. Ein Test von holzbalkenscan lässt absichtlich einen Prozess an einer
  Speichergrenze sterben; jeder solche Scope bleibt als "failed" in systemd stehen.
- **Beleg:** `/usr/bin/time -v`: Elapsed 3:47.10. `systemctl --user list-units --all | grep -c holzbalkenscan-test`:
  261 (vor meinem Lauf 260). Im Journal 260 Zeilen "holzbalkenscan-test-…scope: Failed with result 'oom-kill'"
  in 9 Tagen.
- **Art:** beobachtet.
- **Schwere:** mittel (Wartezeit je Commit, Rauschen im Journal und in der Unit-Liste). **Aufwand:** M.
- **Vorschlag:** Im Hook nur die Ordner testen, die der Commit berührt, plus agentkit, wenn `shared/agentkit`
  betroffen ist. Den vollen Lauf nachts per Timer mit Meldung bei Rot. Den Speichergrenzen-Test mit
  `systemd-run --collect` starten oder als langsamen Test nur im Nachtlauf.
- **Ordner:** Hauptordner, holzbalkenscan.
- **Messgröße:** Dauer des Hooks im Median unter 60 Sekunden; `systemctl --user list-units --state=failed` leer.

### B8 Sicherung umfasst nur Git

- **Was:** `sicherung.service` schiebt jede Nacht den Zweig main nach GitHub (21-mal ok, 0-mal Fehler seit
  27.10.). Alles, was `.gitignore` ausschließt, liegt nur auf diesem Server.
- **Beleg:** `du -sh`: lia/theater/data 313 MB, lia/unterricht/data 221 MB, lia/examen/data 91 MB, finance/data
  63 MB, lia/recherche/data 45 MB, dazu Warteschlangen, `lia/instanz/`, `kleinanzeigen.db`, 9 `.env`.
  (uni/data 2,3 GB besteht großteils aus einem ladbaren Sprachmodell.)
- **Art:** beobachtet. Dass es keine zweite Sicherung gibt (z. B. Snapshots bei Contabo), ist vermutet.
- **Schwere:** hoch (Lias Arbeitsergebnisse, bei einem Plattenfehler weg). **Aufwand:** M.
- **Vorschlag:** Nächtliches verschlüsseltes Archiv von `*/data` (ohne Modelle), `lia/instanz` und den
  Warteschlangen an einen zweiten Ort. Die `.env` getrennt und von Hand sichern. Einmal im Quartal eine
  Rückspielprobe.
- **Ordner:** Hauptordner (shared/sicherung).
- **Messgröße:** Alter der jüngsten Datensicherung unter 26 Stunden, als Zeile in /status.

### B9 Web-Oberflächen werden kaum genutzt

- **Was:** Gemessen am Zugriffsprotokoll im Journal (ohne statische Dateien).
- **Beleg:**
  - Lia-Web-App: 31 schreibende Zugriffe in 30 Tagen, davon 16 Rückmeldungen zu Ergebnissen, 1 neuer Auftrag
    über `/neu`. Letzter Zugriff am 11.11., seitdem fünf Tage keiner. Aufwand im Repo: 5997 Zeilen Code,
    4814 Zeilen Tests, 130 Commits, meistgeänderter Bereich nach den STATUS-Dateien.
  - Uni-Portal: Zugriffe nur am 04.11. (94 lesend, 16 schreibend).
  - Arbeitsplatz: Zugriffe an 4 Tagen, 5 schreibende.
  - In der Web-App liegen zwei Garnituren Vorlagen: `vorlagen/` (28 Dateien) mit `stil.css` (571 Zeilen) für
    die alte Oberfläche und `oberflaeche/` (38 Dateien) für die neue. Der Dienst läuft mit
    `WEBAPP_OBERFLAECHE=neu`, die alte wird vom laufenden Dienst nicht benutzt, aber mitgepflegt.
  - `ruhig.css` liegt identisch in shared/webapp und shared/arbeitsplatz (je 426 Zeilen).
- **Art:** beobachtet.
- **Schwere:** mittel (viel Pflege für wenig Nutzung). **Aufwand:** M.
- **Vorschlag:** Mit Lia klären, warum sie seit dem 11.11. nicht mehr hineingeht, bevor weiter gebaut wird.
  Alte Garnitur und `stil.css` löschen. Beim Uni-Portal entscheiden: nutzen oder Dienst anhalten.
- **Ordner:** shared/webapp, uni, shared/arbeitsplatz.
- **Messgröße:** Schreibende Zugriffe je Woche und Tage mit Zugriff je Woche, je Oberfläche.

### B10 Lias Telegram-Menü hat Sackgassen und Schalter

- **Was:** Die Startansicht zeigt vier Hauptknöpfe. "Meine Woche" und "Frage stellen" führen seit dem 21.10. zu
  einer festen Antwort "kommt bald" (`lia/unterricht/agent.py:33-36`). Der Hinweis dazu steht dauerhaft im Menü
  (`shared/telegram/portal_logik.py:52,103`). Freier Text löst die Frage "Als Materialwunsch / Als Frage" aus
  (`portal_logik.py:128-134`), danach folgt "Soll ich das so abschicken?" (`portal_logik.py:121-126`). Dazu ein
  Knopf "Aktualisieren".
- **Beleg:** Codestellen oben. In 30 Tagen kam über das Menü kein Auftrag der Arten Woche oder Frage an
  (Herkunft der 33 Aufträge: theater 13, feedback 9, webauftrag 5, portal-material 4, weitere 2).
- **Art:** beobachtet.
- **Schwere:** mittel. **Aufwand:** S.
- **Vorschlag:** Die zwei Platzhalter-Knöpfe und den Hinweis entfernen, bis es die Funktion gibt. Freien Text
  direkt als Auftrag annehmen und selbst einordnen, mit "Zurückziehen" unter der Bestätigung statt einer
  Rückfrage davor. "Aktualisieren" ins Menü hinter "···" oder weglassen.
- **Ordner:** Hauptordner (shared/telegram).
- **Messgröße:** Schritte für "Material anfordern" von 3 auf 1; Knöpfe der Startansicht von 6 auf höchstens 3.

### B11 "Nie automatisch" beim Feedback entscheidet das Modell

- **Was:** Ob ein Feedback Außenwirkung, Käufe, Limits oder Datenschutz berührt oder einer Regel widerspricht,
  steht als Feld `heikel` und `widerspricht` in Claudes Antwort. Der Code prüft nur diese Felder.
- **Beleg:** `shared/agentkit/feedback.py:90-93` (Anweisung im Prompt), `:181` (Feld lesen), `:207-210`.
- **Art:** beobachtet (Aufbau), ein Fehlurteil wurde nicht beobachtet.
- **Schwere:** mittel (Jan hat den Stopp-Knopf als zweite Sicherung). **Aufwand:** S.
- **Vorschlag:** Zusätzlich eine feste Wortliste im Code (z. B. senden, Mail, kaufen, Euro, Limit, Freigabe,
  Schüler, Namen), die jeden Treffer zum Vorschlag macht, unabhängig von Claudes Antwort.
- **Ordner:** Hauptordner (shared/agentkit).
- **Messgröße:** Test mit zehn heiklen Beispielsätzen, bei denen `heikel=false` gesetzt ist: alle werden Vorschlag.

### B12 kleinanzeigen weicht von CLAUDE.md ab

- **Was:** Der Agent hat einen eigenen Telegram-Bot und sendet Treffer direkt an freigeschaltete Chats, künftig
  auch an eine zweite Person. CLAUDE.md nennt die Zentrale als einzigen Kontakt und verlangt für Nachrichten
  nach außen die Freigabe. Der Agent steht nicht im Abschnitt "Architektur". Claude bewertet fremde
  Anzeigentexte und hat dabei die Standardwerkzeuge samt Write und Edit, obwohl nur eine JSON-Antwort gebraucht
  wird.
- **Beleg:** `kleinanzeigen/bot.py:73,231,319`, `shared/einstellungen.toml` (kein Eintrag unter [werkzeuge], also
  "standard"), `kleinanzeigen/STATUS.md` (Entscheidungen vom 15.11.).
- **Art:** beobachtet. Jans Entscheidung vom 15.11. deckt den eigenen Bot, CLAUDE.md wurde nicht angepasst.
- **Schwere:** niedrig bis mittel. **Aufwand:** S.
- **Vorschlag:** Ausnahme in CLAUDE.md festhalten (Trefferlinks an freigeschaltete Chats sind keine Handlung nach
  außen im Sinne der Freigabe). Bewertung als Nur-Lesen-Lauf ohne Werkzeuge fahren (`lese_ordner` gibt es schon).
- **Ordner:** Hauptordner (CLAUDE.md, einstellungen.toml), kleinanzeigen.
- **Messgröße:** kleinanzeigen-Läufe mit 0 erlaubten Schreibwerkzeugen.

### B13 Werkzeuge und Isolation sind gröber als nötig

- **Was:** Werkzeuge gelten je Agent, nicht je Aufgabe. uni hat WebSearch und WebFetch auch in dem Lauf, der
  neue Mails liest (`uni/agent.py:1445`). finance und der geplante einkauf haben WebFetch ohne Domainliste.
  Technisch trennt nichts die Agenten: gleicher Linux-User, keine Härtung in den Units.
- **Beleg:** `shared/einstellungen.toml` ([werkzeuge], [webfetch]), `claude_lauf.py:274`, Unit-Dateien (kein
  `ProtectHome`, `ReadWritePaths`, `NoNewPrivileges`).
- **Art:** beobachtet (Aufbau). Ein Abfluss von Daten wurde nicht beobachtet.
- **Schwere:** mittel. **Aufwand:** M.
- **Vorschlag:** `laufen(..., werkzeuge=[...])` je Aufruf erlauben und Mail-Läufe ohne Netz fahren. In den Units
  `ReadWritePaths=` auf den eigenen Ordner und die Warteschlangen setzen, `InaccessiblePaths=` für fremde `.env`.
- **Ordner:** Hauptordner.
- **Messgröße:** Zahl der Läufe, in denen fremder Text und Netzwerkzeug zusammentreffen: 0.

### B14 Zwei Sperrdateien, ein Commit-Weg ohne Sperre

- **Was:** `commit.sh` sperrt `.git/commit.sperre`. Im Hauptordner liegt zusätzlich eine unverfolgte, leere
  `commit.sperre` vom 07.11. Wer nach der Kurzformel "flock auf commit.sperre" die falsche Datei nimmt, sperrt
  nichts. Der Feedback-Dienst committet mit `git commit` direkt, also mit Hook, aber ohne Sperre. Sein
  Prüflauf kann parallel zu einem Chat laufen, genau das Muster des Ausfalls vom 03.11.
- **Beleg:** `ls -la commit.sperre .git/commit.sperre`, `commit.sh` (Zeile mit `exec 9>`),
  `shared/feedback/lauf.py:70-83`. Bisher 1 Commit des Dienstes (08.11., 1 min 55 s CPU).
- **Art:** beobachtet (Aufbau), Zusammenstoß vermutet.
- **Schwere:** niedrig bis mittel. **Aufwand:** S.
- **Vorschlag:** Die Datei im Hauptordner löschen. Den Feedback-Dienst `commit.sh` aufrufen lassen.
- **Ordner:** Hauptordner, shared/feedback.
- **Messgröße:** `grep -rn '"commit"' --include=*.py` findet keinen direkten Aufruf mehr.

### B15 Liegengebliebene Worktrees mit Kopie einer .env

- **Was:** Unter `lia/.claude/worktrees/` liegen zwei Git-Worktrees (14 MB, je eine volle Kopie des Repos). Einer
  enthält `uni/.env` (Rechte 600). ruff und die Größenlisten laufen über diese Kopien mit.
- **Beleg:** `git worktree list` (zwei Einträge mit Zweigen `claude/…`), `find . -name ".env*"`.
- **Art:** beobachtet. **Schwere:** niedrig. **Aufwand:** S.
- **Vorschlag:** Prüfen, ob die Zweige noch gebraucht werden, sonst `git worktree remove`. `.claude/` in
  `.gitignore` und in `ruff.toml` ausschließen. Ebenso fehlt `shared/auftraege/ereignisse/` in `.gitignore`
  (`git status` zeigt `shared/auftraege/` als unverfolgt); ein `git add` auf `shared` nähme es mit.
- **Ordner:** Hauptordner. **Messgröße:** `git worktree list` zeigt nur den Hauptordner.

### B16 STATUS-Dateien sind zu groß und enthalten Verlauf und Personenbezug

- **Was:** `STATUS.md` im Hauptordner hat 1200 Zeilen (122 KB) und 199 Commits, uni 673, shared/webapp 677. Der
  Kopf sagt "kein Verlauf", der Text ist nach Datum gegliedert. Jeder neue Chat liest das als Übergabe.
  `uni/STATUS.md` nennt unter "Gelernte Regeln" Namen Dritter, `lia/unterricht/STATUS.md` beschreibt eine
  Lerngruppe. Beide Dateien gehen nachts nach GitHub. `lerngruppen.toml` ist aus genau diesem Grund nicht im Repo.
- **Beleg:** `wc -l`, `git log --name-only`, `.gitignore` (Kommentar zu lerngruppen.toml, F6).
- **Art:** beobachtet. **Schwere:** mittel (Datenschutz), niedrig (Größe). **Aufwand:** M.
- **Vorschlag:** Je STATUS höchstens 150 Zeilen: Stand, offene Punkte, Betrieb. Entscheidungen mit Datum in eine
  eigene Datei. Regeln mit Personenbezug in eine Datei außerhalb von Git (wie lerngruppen.toml) auslagern,
  `regeln_als_text` liest sie mit.
- **Ordner:** alle, Hauptordner zuerst. **Messgröße:** Zeilen je STATUS.md; Treffer für Personennamen im Repo 0.

### B17 Ausfälle werden nur erkannt, wenn systemd sie sieht

- **Was:** `ausfall@` meldet eine fehlgeschlagene Unit. Nicht erkannt werden: ein hängender Dauerdienst, ein
  Timer, der nicht mehr feuert, ein Lauf, der mit Code 0 endet und nichts getan hat, und der Ausfall des ganzen
  Servers. Die Meldung nennt nur "Bitte sieh am PC nach".
- **Beleg:** `shared/agentkit/ausfall.py` (Kopfkommentar "Grenze"), keine Watchdog- oder Lebenszeichen-Stelle im
  Repo (`grep -ri "watchdog\|lebenszeichen"` findet nur den Fehlertext).
- **Art:** beobachtet (Aufbau). **Schwere:** mittel. **Aufwand:** S bis M.
- **Vorschlag:** Die Zentrale prüft stündlich, ob jeder Timer-Dienst in seinem Takt zuletzt erfolgreich lief,
  und meldet Abweichungen. Für den Serverausfall ein Lebenszeichen an einen kostenlosen Dienst von außen.
- **Ordner:** Hauptordner. **Messgröße:** Zeit vom Stillstand eines Timers bis zur Meldung unter 2 Stunden.

### B18 Kosten der Woche sind nirgends zu sehen

- **Was:** `/verbrauch` zeigt Prozent des Kontingents und die Läufe von heute, ohne Geldwert. Der Leitstand
  zeigt drei Tage (`shared/leitstand/server.py`, `TAGE = 3`). Die Wochensumme je Agent gibt es nur per Skript.
- **Beleg:** `shared/telegram/logik.py:368-387`. **Art:** beobachtet. **Schwere:** niedrig. **Aufwand:** S.
- **Vorschlag:** In `/verbrauch` eine Zeile je Agent für die letzten 7 Tage (Läufe, USD rechnerisch).
- **Ordner:** Hauptordner. **Messgröße:** Aufgabe "Kosten der Woche" in einem Schritt lösbar.

### B19 Web-App: Kontrast, Trefferflächen, Navigation am Handy

- **Was und Beleg (berechnet aus `shared/webapp/statisch/ruhig.css`):**
  - Farbe `--sehrleise` #8c8b87 auf Weiß hat Kontrast 3,41, `--leise` #787774 hat 4,48. Für Text von 12 bis
    14 px verlangt WCAG AA 4,5. `--sehrleise` wird an 17 Stellen verwendet, 12 px an 19 Stellen.
  - Knöpfe sind 28 bis 32 px hoch (`.knopf` 32, `.knopf-leise` 28, Baumeinträge 30). Für Finger sind 44 px
    üblich. Unter 760 px Breite wird nichts vergrößert.
  - Unter 760 px rutscht der Navigationsbaum unter den gesamten Inhalt (`grid-template-areas: "inhalt" "rechts"
    "baum"`). Ein Sprung dorthin fehlt.
  - Leitstand und Uni-Portal liegen über 6,0 und sind unauffällig.
- **Art:** beobachtet (gerechnet), nicht am Gerät gesehen. **Schwere:** niedrig bis mittel. **Aufwand:** S.
- **Vorschlag:** `--sehrleise` auf mindestens #737270 abdunkeln, 12 px nur für Nebensachen. Bei
  `pointer: coarse` Mindesthöhe 44 px. Am Handy oben ein Knopf "Fächer", der zum Baum springt.
- **Ordner:** shared/webapp, shared/arbeitsplatz. **Messgröße:** Kleinster Textkontrast über 4,5.

### B20 Meldungen: nachts, mit Technik, lange Sätze

- **Was:** 24 von 160 Meldungen an Jan entstanden zwischen 0 und 6 Uhr und wurden im Median 17 Sekunden später
  zugestellt. Die Sprachprüfung der Zentrale hat 155 Befunde protokolliert (IDs und Hashes in Meldungen von
  holzbalkenscan 36-mal, kleingeschriebene Agentennamen, Dateinamen, zu lange Sätze). Sie warnt nur.
- **Beleg:** `shared/meldungen/gesendet/` (Stunde aus `erstellt`), `shared/telegram/logs/zentrale.log`
  (`grep "Sprache sendMessage"`).
- **Art:** beobachtet. **Schwere:** niedrig. **Aufwand:** S.
- **Vorschlag:** Meldungen ohne Eile zwischen 22 und 7 Uhr sammeln und morgens als eine Nachricht senden.
  Befunde der Sprachprüfung je Agent wöchentlich in die STATUS des Agenten schreiben, damit sie behoben werden.
- **Ordner:** Hauptordner, holzbalkenscan. **Messgröße:** Meldungen zwischen 22 und 7 Uhr: 0; Befunde je Woche.

### B21 Eine kaputte Datei kann eine Warteschlange blockieren

- **Was:** `_ablage.liste` liest jede JSON-Datei des Ordners und bricht beim ersten Lesefehler ab. Die Zentrale
  ruft das in jeder Prüfrunde auf. Eine einzige unlesbare Datei würde alle Ausgaben an Jan anhalten.
- **Beleg:** `shared/agentkit/_ablage.py` (Funktion `liste`), kein Test mit kaputter Datei in
  `test_warteschlangen.py`. Geschrieben wird atomar (tmp und `os.replace`), das Risiko ist daher klein.
- **Art:** vermutet. **Schwere:** niedrig. **Aufwand:** S.
- **Vorschlag:** Unlesbare Datei überspringen, nach `kaputt/` verschieben, einmal melden.
- **Ordner:** Hauptordner. **Messgröße:** Test mit kaputter Datei: übrige Einträge kommen an.

### B22 Bedienung der Zentrale für Jan

- **Was und Beleg:**
  - `AGENTEN` in `shared/telegram/logik.py:15` nennt uni, dokumente, posteingang, einkauf, finance. einkauf gibt es
    nicht. holzbalkenscan und fehlstellenscan fehlen, alle 20 holzbalkenscan-Aufträge kamen "von Hand" am Server.
  - "Modus wechseln: lernen" ist ein Schalter (`logik.py:629-633`), "Status" wiederholt großteils die
    Startansicht, "Aktualisieren" ist ein eigener Knopf.
  - Das Log der Zentrale enthält 203 Netzfehler mit vollem Traceback (4600 der Zeilen). Die Bibliothek
    wiederholt selbst, die Einträge überdecken echte Fehler.
- **Art:** beobachtet. **Schwere:** niedrig. **Aufwand:** S.
- **Vorschlag:** Die Agentenliste aus den vorhandenen Diensten ableiten. Den Modus aus dem Text erkennen
  (oder "lernen" als eigener Befehl, den es schon gibt). Netzfehler als eine Zeile loggen.
- **Ordner:** Hauptordner. **Messgröße:** Anteil der Aufträge "von Hand" unter 5 %.

### B23 Am Rand: Zugang von außen und fremde Dienste (nur benannt)

- Caddy schützt `lia.meldro.de` und `uni.meldro.de` mit Basic Auth und HSTS. Eine Bremse gegen Durchprobieren
  ist in der Konfiguration nicht zu sehen. `/etc/caddy/Caddyfile` ist für alle Benutzer lesbar, samt
  Kennwort-Hashes. Das ist Sache von root.
- Jans Login für `claude` auf dem Server ist abgelaufen (mein Rechtetest: "OAuth session expired"). Die Agenten
  nutzen das eigene Konto und sind nicht betroffen. Der Vinted-Bot rechnet laut Protokoll über "login" ab
  (letzter Eintrag 03.11.). Falls er wieder angeschaltet wird, dürfte seine Bewertung scheitern (vermutet).
- Port 8787 lauscht auf allen Adressen (laut CLAUDE.md kcalbot). Nicht untersucht.
- `shared/webapp/data/webapp.sock` hat Rechte 666. `/home/agent` hat 750, andere Benutzer kommen nicht heran.

---

## Schritt 3: Sicherheit, Wege von fremdem Text

| Eingang | Weg in den Claude-Lauf | Was Python danach nach außen tut | Kann fremder Text die Sperren umgehen? |
|---|---|---|---|
| Mails (uni, posteingang) | `agentkit.imap` (nur lesend) in den Prompt | Entwurf über `mail.pruefen` in die Freigabe, Versand nur nach Klick | Freigabe und Einmal-Ausführung: nein (Fingerabdruck, Sperrdatei, Anhänge mit Prüfsumme, Empfänger werden vollständig gezeigt). Ein untergeschobener Entwurf erscheint aber als normaler Entwurf; die Sicherung ist Jans Lesen. Schreibschutz: siehe B1. |
| Webseiten (uni, finance, recherche) | WebSearch und WebFetch im Lauf | nichts direkt | Abfluss über WebFetch: bei uni und recherche durch die Domainliste begrenzt, bei finance offen (B13). WebSearch ist überall frei. |
| Kleinanzeigen | Anzeigentext in den Prompt, Antwort als JSON, streng geprüft | Telegram-Nachricht an freigeschaltete Chats, als HTML | Freigabe gibt es hier nicht (B12). Schreibwerkzeuge unnötig vorhanden. |
| Dokumente (dokumente, Lias Agenten) | `agentkit.textfassung`, Dateien im Agent-Ordner | Datei an Jan oder Lia über die Zentrale (`anhaenge_pruefen`: nur eigener Ordner, nichts Verstecktes) | nein |
| Telegram | nur Jans Chat-ID (`zentrale.py:615,808-820`), nur freigeschaltete Chats (`kleinanzeigen/bot.py:82`) | Auftrag in die Warteschlange | Fremde Chats werden abgewiesen. Ein Test dafür fehlt (zentrale.py ist nur für die Wartezeit getestet). |
| Feedback (Text, Word-Kommentare) | Prompt des Feedback-Dienstes, Werkzeug nur Read | Regelzeile in STATUS.md oder regeln.md, Commit | Regeln wirken in jedem späteren Lauf. Schutz: Modellurteil plus Jans Stopp (B11). |

- Kauflimit: Es gibt keinen Code, der kauft. Die Prüfung steht bereit und ist getestet.
- `.env`: alle 9 Dateien 600, keine verfolgt. Suche nach Token-Mustern (Telegram, sk-ant, ghp, private Schlüssel)
  in Arbeitsbaum, ganzer Git-Historie, eigenen Logs und Journal: 0 Treffer.
- Leitstand: Socket `shared/leitstand/data/leitstand.sock` mit 700 in einem Ordner mit 700, nur GET. Unauffällig.

---

## Schritt 4: Betrieb

| Fall | Verhalten | Beleg | Urteil |
|---|---|---|---|
| Netzfehler | Zentrale loggt und macht weiter (203 Fälle, kein Absturz). Agenten melden einen fehlgeschlagenen Schritt höchstens einmal am Tag. Meldungen gelten erst nach erfolgreichem Senden als gesendet. | `zentrale.log`, `posteingang/agent.py:273`, `zentrale.py` (pruefen) | gut |
| Leere oder kaputte Claude-Antwort | `auswerten` liefert `ok=False`, 69 solche Läufe im Protokoll (57 davon Vinted) | `claude_lauf.py:309-310` | gut |
| Zeitlimit | Prozessgruppe wird nach 15 Minuten beendet, kein Lauf erreichte die Grenze (Maximum 679 s) | `claude_lauf.py:388`, `laeufe.jsonl` | gut |
| Voller Speicher | Jede Unit außer `lia-chat-aufraeumen` hat `MemoryMax`. Die Summe (15,3 GB) übersteigt den RAM, kein Schutz der Dauerdienste. | Unit-Dateien | Lücke (B3) |
| Doppelter Start | Sperre je Agent (`data/lauf.lock`), Timer-Dienste sind oneshot, Platzvergabe über Sperrdateien | `claude_lauf.py:488-489` | gut |
| Absturz mitten im Senden | Wird nie wiederholt, Jan bekommt "unklar" | `freigabe.py:145-150`, `zentrale.py` | gut |
| Kontingent leer | Stufen, zeitgesteuerte Läufe pausieren, Aufträge warten | `claude_lauf.py:467-473` | gut, aber häufig aktiv (B6) |
| Hängender Dienst, toter Timer, Server weg | nichts | B17 | Lücke |

---

## Schritt 5: Code

- **ruff:** grün. Geprüft werden nur Fehlerregeln (E4, E7, E9, F, B). Ausgenommen ist `holzbalkenscan/verfahren`.
  `holzbalkenscan/verfahren_neu` (2508 und 1495 Zeilen, fast gleich mit `verfahren/`) ist nicht ausgenommen und
  besteht trotzdem.
- **Tests:** 2679 Tests, alle grün. Verhältnis Test- zu Codezeilen: agentkit 6234 zu 9227, uni 6114 zu 8160,
  webapp 4814 zu 5997. Schwach: kleinanzeigen 258 zu 1168, holzbalkenscan 684 zu 5260 (eigener Code ohne
  `verfahren`), lia/verwaltung 342 zu 893.
- **Logik mit Außenwirkung:** Freigabe, Mail, Anhänge, Kauflimit und Weitergabe sind getestet. Ohne Test:
  `zentrale.knopf` (der Klick, der freigibt), die Abweisung fremder Chats, `kleinanzeigen/bot.py` (nur die Logik
  dahinter ist getestet).
- **Doppelter Code:** `ruhig.css` zweimal identisch; zwei Vorlagen-Garnituren in der Web-App;
  `holzbalkenscan/verfahren` und `verfahren_neu`; die Schleife "freigegebene ausführen" steht fast gleich in
  uni, posteingang, finance und der Vorlage (je 10 Zeilen) und gehört nach agentkit.
- **Verschluckte Fehler:** kein blankes `except:`. 69-mal `except Exception`, soweit gelesen mit Log oder Meldung.
  76 Stellen fangen einen engen Fehler und gehen ohne Log weiter; auffällig nur `lia/chat/wissen.py:69,83,99`
  (OSError wird zu leerem Text).
- **Große Dateien:** `shared/webapp/app.py` mit 3128 Zeilen und über 70 Routen in einer Datei ist der Ort mit
  den meisten Änderungen und Fix-Commits.

---

## Schritt 6: Oberfläche, je fünf Aufgaben

Schritte sind Tipp- oder Schreibvorgänge ab geöffnetem Telegram oder geöffneter Seite, aus dem Code gezählt.

### Jan

| Aufgabe | Weg | Schritte | Wo man hängen bleibt |
|---|---|---|---|
| Entwurf freigeben | Nachricht mit Knöpfen kommt von selbst, "Freigeben" | 1 | Gut. Alte Entwürfe: 3 Schritte und alle auf einmal (B5). |
| Entwurf ändern lassen | "Ändern", Text schreiben | 2 | Gut. 6 von 16 Entscheidungen waren "ändern", der Weg wird gebraucht. |
| Agentenausfall erkennen | Meldung "Zentrale · Störung" kommt von selbst | 0 | Die Meldung nennt keinen nächsten Schritt außer "am PC nachsehen". Im Menü und in /status steht kein Zustand der Dienste. Der Leitstand zeigt ihn, braucht aber Terminal, SSH-Tunnel und Browser (3 Schritte, nur am PC). Stille Ausfälle bleiben unsichtbar (B17). |
| Kosten der Woche sehen | geht nicht | - | /verbrauch zeigt heute und Prozent, der Leitstand 3 Tage (B18). |
| Auftrag an uni mit Datei | Datei mit "/uni Text" als Bildunterschrift | 1 | Gut. Für holzbalkenscan gibt es keinen Weg über Telegram (B22). |

### Lia

| Aufgabe | Weg | Schritte | Wo man hängen bleibt |
|---|---|---|---|
| Material anfordern (Telegram) | "Neues Material", Text, "Abschicken" | 3 | Die Bestätigung ist ein Schritt zu viel (B10). |
| Einfach losschreiben (Telegram) | Text, "Als Materialwunsch", "Abschicken" | 3 | Zwei Rückfragen für eine Nachricht. |
| "Meine Woche" oder Frage stellen | Knopf, ggf. Text | 1 bis 2 | Sackgasse seit 21.10. ("kommt bald"). |
| Auftrag in der Web-App | Ort im Baum, "+", Vorlage, Formular mit 2 bis 4 Feldern, "Abschicken" | 5 und mehr | In 30 Tagen einmal benutzt. Am Handy liegt der Baum unter dem Inhalt (B19). |
| Ergebnis korrigieren | Telegram: Knopf unter dem Ergebnis (fertige Antwort oder freier Text). Web-App: Rückmeldung am Ergebnis. | 1 bis 2 | Funktioniert und wird genutzt (9 Feedback-Aufträge, 16 Rückmeldungen in der Web-App). Das ist der meistgenutzte Teil der Web-App. |

### Nach Nielsens Heuristiken, kurz

- Sichtbarkeit des Zustands: gut bei laufenden Aufträgen, schwach bei Diensten und offenen Entwürfen.
- Übereinstimmung mit der Welt: Texte sind klar und ohne Technik (Sprachregel greift), Ausnahme holzbalkenscan.
- Kontrolle und Freiheit: "Zurückziehen" und "Rückgängig" gibt es, gut.
- Fehlervermeidung: Fingerabdruck und Einmal-Ausführung vorbildlich. Schwach: veraltete Knöpfe bleiben scharf.
- Erkennen statt erinnern: Befehle wie /uni, /unilern, /pc, /weiter, /verwerfen muss man wissen.
- Schlichtheit: Platzhalter, "Aktualisieren", "Status" neben der Startansicht.
- Hilfe bei Fehlern: "Einzelheiten stehen am PC" ist ehrlich, hilft unterwegs aber nicht.

### "Schlau statt Schalter"

Verstöße: "Modus wechseln" (Jan), "Als Materialwunsch / Als Frage" (Lia), "Soll ich das so abschicken?" (Lia),
"Aktualisieren" (beide), Auswahl der Vorlage vor dem Formular in der Web-App.

---

## Agenten, die man vereinfachen oder stilllegen sollte

| Agent oder Teil | Nutzung in 30 Tagen | Umfang | Vorschlag |
|---|---|---|---|
| lia/examen | 3 Läufe, letzter am 25.10., 1 Entwurf seit 25.10. offen | 1059 Zeilen | Mit Lia klären, ob noch gebraucht. Sonst ruhen lassen und aus `pruefen.sh` nehmen (nur Nachtlauf). |
| lia/verwaltung | kein Claude-Lauf, kein Auftrag, 6 geänderte Dateien | 893 Zeilen | Wie examen. |
| lia/unterricht | 4 Aufträge, letzter Lauf 30.10., trägt die Platzhalter im Menü | 1312 Zeilen, 15 Regeln | Platzhalter entfernen (B10). Nachfragen, warum seit dem 30.10. nichts kam. |
| lia/auswertung | 16 Läufe, letzter 09.11., kein Auftrag in der Warteschlange | 1598 Zeilen | Vermutlich Einmal-Werkzeug. Als Skript behalten, nicht als Agent pflegen. |
| lia/vabali | 409 Durchgänge (alle 15 Minuten), 1 Meldung | 196 Zeilen | Klein und billig. Takt auf 30 oder 60 Minuten, wenn Lia das reicht. |
| lia/schnell, lia/chat | 7 und 30 Läufe, letzter 10.11. | 1040 und 1694 Zeilen | Hängen an der Web-App. Entscheidung folgt aus B9. |
| Uni-Portal (uni/portal) | Zugriffe an einem Tag | Dauerdienst, 11 Vorlagen | Nutzen oder Dienst anhalten. Verringert auch B1. |
| Arbeitsplatz | 5 Schreibaktionen | 2281 Zeilen, Dauerdienst | Abwarten bis Ende November, dann entscheiden. |
| dokumente | 4 Aufträge (2 von uni, 2 vom Arbeitsplatz), keiner direkt von Jan | 745 Zeilen | Als Baustein behalten, kein eigener Befehl nötig. |
| posteingang | 6 Aufträge, 28 Timer-Läufe, 3 Entwürfe (1 gesendet, 2 offen) | 675 Zeilen | Behalten. Nutzen hängt an B5. |
| holzbalkenscan | 20 Aufträge bis 07.11., seitdem keiner | 5260 Zeilen | `verfahren_neu` und `verfahren` zusammenführen. Speichergrenzen-Test aus dem Hook nehmen (B7). |
| Web-App, alte Oberfläche | vom laufenden Dienst nicht benutzt | 28 Vorlagen, stil.css | Löschen. |
| einkauf | geplant, in AGENTEN und einstellungen.toml schon eingetragen | - | Einträge entfernen, bis es den Agenten gibt. kleinanzeigen deckt den Bedarf vorerst. |

Klar genutzt und ihren Aufwand wert: uni (45 Aufträge, 18 Freigaben), lia/theater (14 Aufträge), lia/recherche
(6 Aufträge, zuletzt 14.11.), finance (4 Aufträge), Feedback-Dienst (19 Aufträge).

---

## Was ich nicht prüfen konnte und warum

- **Screenshots bei 375 px:** Der vorhandene Headless-Browser startet nicht (`libatk-1.0.so.0` fehlt). Neue
  Pakete waren ausgeschlossen. Layout, Umbrüche und Trefferflächen sind deshalb aus dem CSS abgeleitet, nicht
  gesehen.
- **Ob `claude` den Schreibschutz und die .env-Sperre wirklich durchsetzt:** Ein einzelner Testlauf in einem
  Wegwerf-Ordner mit Jans Login scheiterte ("OAuth session expired"). Den Token der Agenten habe ich dafür
  nicht benutzt. Installiert ist Version 2.1.304, dieselbe wie beim Handtest vom 10.11.
- **Telegram am Gerät:** Nachrichtenlänge und Knöpfe sind aus Code und gespeicherten Meldungen bewertet (Länge,
  Zahl der Knöpfe), nicht in der App gesehen.
- **Leitstand im Browser:** nur `index.html` und Server gelesen, kein Aufruf über den Socket.
- **kcalbot und Vinted-Bot:** nicht angefasst, keine Logs gelesen. Benannt ist nur, was aus eigenen Daten
  hervorgeht (Verbrauchsprotokoll, Port, Login).
- **Zeitersparnis in Minuten:** dafür gibt es keine Daten. Ersatzgrößen stehen im Maßstab.
- **Andere Sicherungen:** Snapshots beim Anbieter oder Sicherungen durch root kann User `agent` nicht sehen.
- **Kernel-Log:** nicht lesbar für `agent`. Die OOM-Ereignisse stammen aus dem systemd-Journal des Users.
- **Genaue Stelle hinter B2:** Welcher Aufruf im Test den echten Lauf auslöst, habe ich nicht einzeln
  nachverfolgt. Die Wirkung ist belegt, die Ursache (Vorgabewert) ist vermutet.
- **Zugriffe auf die Web-App vor dem 30.10.:** Das Journal enthält Zugriffszeilen erst ab dann.
