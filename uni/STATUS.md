# Status: Agent uni

## Zweck
Moodle und Unipostfach überwachen, Fristen, Zusammenfassungen, Lernsessions.

## Stand (16.10.2026)
- Uni: HNE Eberswalde (HNEE). Studiengang laut Moodle: Holzingenieurwesen M.Sc.
- Moodle: https://lms.hnee.de (Moodle 4.5). App-Login direkt mit HNEE-Nutzername/Kennwort (typeoflogin=1),
  kein SSO. Zugriff über login/token.php (service moodle_mobile_app) + webservice/rest/server.php. Getestet: geht.
  Token liegt in data/moodle_token.json (600). Jan kann ihn im Moodle-Profil unter Sicherheitsschlüssel widerrufen.
- Fristen: core_calendar_get_action_events_by_timesort lieferte 0 Einträge, obwohl eine Aufgabe fällig war.
  Fristen daher über mod_assign_get_assignments (+ mod_assign_get_submission_status) und Tests prüfen.
- Unipostfach: Exchange der HNEE, IMAP mail.hnee.de:993, Login mit Nutzername. Getestet: geht.
  Posteingang ca. 6000 Mails, über 5000 ungelesen: "ungelesen" taugt nicht als Filter.
- Zugangsdaten in uni/.env (600), Vorlage uni/.env.example. .venv angelegt, agentkit eingebunden.
- lesetest.py: liest Kurse, Termine, ungelesene Mails. Verändert nichts.
- Alle 26 Kurse gelten als wichtig (Jan).
- Gebaut und von Hand getestet (16.10.):
  - moodle.py: Anmeldung wie die App, Kurse, Fristen (Aufgaben inkl. Nachfrist und Abgabestatus, Tests).
  - fristen.py: Erinnerung 7 Tage, 2 Tage, am Tag selbst; je Frist und Stufe einmal (data/erinnert.json).
  - postfach.py: nur neue Mails seit Marke (data/postfach.json), readonly + BODY.PEEK, max. 50 pro Lauf.
  - agent.py: Freigaben (nur Typ regel), Aufträge (erledigen: protokolle/<id>.md; lernen: Sitzung in
    data/sitzungen/, Ergebnis enthält `claude --resume`), Fristen (ohne Claude), Post (Claude routine,
    nur bei neuen Mails, Antwort KEINE = nichts melden; ca. 11.000 Tokens pro Lauf).
  - Tests: `.venv/bin/python -m unittest discover -s tests -t .` (10 grün).
- Meldungen an Jan: agentkit.meldungen (shared/meldungen/), die Zentrale verschickt sie alle 30 s per
  Telegram mit Präfix [uni]. Am 16.10. auf Jans Wunsch ("alles erledigen") in diesem Chat gebaut.
- uni.service/uni.timer laufen (Kopie der Vorlagen in ~/.config/systemd/user/, Timer 8, 13, 19 Uhr).
  Logs: `journalctl --user -u uni.service` und uni/logs/.
- protokolle/ ist per uni/.gitignore vom Repo ausgeschlossen (persönliche Inhalte).
- kurse.py: spiegelt Kursmaterial nach data/kurse/<Kurs>/ (uebersicht.md + Dateien je Abschnitt), nur
  neue/geänderte Dateien (data/kurse/.stand.json). Nicht geladen: ZIP und Dateien > 100 MB.
  Stand 16.10.: 191 Dateien, 731 MB, erster Abgleich 6,5 min, danach Sekunden. Läuft in jedem agent.py-Lauf
  vor den Aufträgen; neues Material wird pro Kurs gemeldet. Gleichnamige Dateien eines Abschnitts
  bekommen die Moodle-Modul-ID angehängt.
- Textfassungen: Zu docx/pptx/xlsx legt kurse.py <datei>.txt daneben (pptx mit Foliennummern, xlsx mit
  Blattnamen). Bibliotheken python-docx, python-pptx, openpyxl in uni/.venv (Jans Okay 16.10.),
  Stand in uni/requirements.txt. Alte Formate doc/ppt/xls nicht lesbar (bräuchte LibreOffice, kein sudo).
- Office-Dateien ERSTELLEN und FORMATIEREN macht nicht uni, sondern der Agent dokumente (Jan, 16.10.).
- Erster echter Auftrag 16.10. (CASCADOS-Datei): Ergebnis gut und mit Quellen, aber 16 Schritte Opus,
  ca. 490.000 Tokens, 5h-Auslastung 43 % -> 59 %. Daraufhin:
  - WebSearch wurde in claude -p abgelehnt: in shared/agentkit/claude_lauf.py jetzt ausdrücklich erlaubt
    (nur WebSearch/WebFetch, nie Write/Edit pauschal). Getestet: geht.
  - ZIPs bis 50 MB werden geladen und sicher nach <name>_entpackt/ entpackt (Inhaltsliste <name>.zip.txt).
  - Prompt: sparsam arbeiten (uebersicht.md, Grep in .txt, PDFs seitenweise, Websuche zuletzt).
  - PDF-Textfassungen mit "--- Seite N" per pypdf (Jans Okay 16.10.). 167 PDFs, 3 Scans ohne Text,
    erste Umwandlung ca. 13 min, danach nur neue. Formelreiche PDFs: Textfassung lückenhaft.
  - Namen aus Moodle werden HTML-dekodiert (&amp; -> &).
  - Zweiter Auftrag (GEG-Frage): 10 Schritte Opus, ca. 177.000 Tokens (vorher 488.000), aber ohne Antwort,
    weil Aufgabentexte fehlten. Seitdem: data/kurse/<Kurs>/aufgaben.md (Beschreibung, Fristen, Abgabeart,
    Teamabgabe, Abgabestatus, Arbeitsanweisungen, Anhänge).
  - Vorfall 16.10.: Jans Antwort "Ja mitladen" kam als neuer Auftrag; der Agent baute daraufhin kurse.py und
    STATUS.md selbst um (ungetestet, kaputt). Zurückgenommen. Seitdem sperrt claude_lauf Schreiben auf Code,
    STATUS.md, Regeln und Einrichtung (getestet). Ursache bleibt: Rückfragen brauchen den Gesprächskanal.
- BFH Biel (16.10.): Modul "Computerbasierte Planung" der HNEE läuft an der BFH als "Fertigung im Holzbau 1"
  [BBHbf01], Prof. Stefan Jack, online per Teams. BFH-Moodle https://moodle.bfh.ch (Moodle 5.2), Kurs-ID 45291.
  Login nur per Shibboleth/SWITCH edu-ID, login/token.php geht nicht. Token einmal im Browser geholt:
  angemeldet launch.php?service=moodle_mobile_app&passport=<zahl>&urlscheme=moodlemobile aufrufen, in
  Chrome-DevTools (Network, Keep log) die Adresse moodlemobile://token=<base64> kopieren; base64 =
  md5(wwwroot+passport):::token. Liegt als BFH_MOODLE_TOKEN in uni/.env. Lesend getestet: Kursinhalt geht.
  Laufzeit des Tokens unbekannt. Eingebunden (agent.py: moodles(), _je_moodle): Kursmaterial, aufgaben.md,
  Fristen (IDs mit Präfix bfh-). Abgelaufener Schlüssel -> Meldung, HNEE läuft weiter.
  Neuer Kurs meldet beim ersten Abgleich kein Material als neu (kurse.py).
- Transkription (transkription.py, faster-whisper 1.2.1, Modell small int8, Jans Okay 16.10.):
  Ton/Video bis 300 MB lädt kurse.py, nachts entsteht <datei>.txt mit Zeitmarken. Faktor ~1,7
  (90 min Vorlesung ~2,5 h). Keine Datei, die nicht vor 7 Uhr fertig wird. Modell in data/modelle/.
  Ton liest av selbst (faster-whisper 1.2.1 passt nicht zu av 19). Qualität: gut lesbar, Hörfehler
  bei Fachbegriffen (Schweizer Färbung). Speicher ~1 GB pro 42 min Aufnahme.
  Dienst/Timer uni-transkript (1 Uhr), Vorlage in uni/systemd/, von Jan am 17.10. eingerichtet
  (Claude darf keine Dienste anlegen und keine Pakete installieren: Sicherheitsprüfung, Jan per `!`-Befehl).
  Erster Lauf 17.10. 1 Uhr noch nicht geprüft: `journalctl --user -u uni-transkript -n 30`.
- Jans eigene Transkripte (transkripte.py, 17.10.): Auftrag "Transkript <Kurs> [TT.MM.]" mit .txt-Datei
  (Jans Format) oder Text darunter. Python legt nach data/kurse/<Kurs>/transkripte/<datum>_transkript.txt
  ab (Kurs per Namensteil, bei Mehrdeutigkeit Rückfrage mit Kandidaten), Claude (routine) meldet
  Prüfungshinweise, Fristen, Organisatorisches. KONTEXT verweist auf Transkripte. Noch nicht echt
  über Telegram getestet.
- Gruppen (17.10.): uebersicht.md zeigt Belegung jeder Gruppenwahl (mod_choicegroup_get_choicegroup_options,
  nur choicegroupid+userid, sonst "Ungültiger Parameterwert"), aufgaben.md Jans Gruppe bei Teamabgaben,
  Fristen-Erinnerung warnt bei Teamabgabe ohne Gruppe. Mitglieder anderer zeigt Moodle nicht.
- Angehängte Dateien eines Auftrags bekommen vorab eine Textfassung (kurse.textfassung).
- BFH-Postfach (jan.kleinke@students.bfh.ch): Weiterleitung ins HNEE-Postfach am 17.10. von Jan
  eingerichtet, Ankunft noch nicht geprüft (Testmail an die BFH-Adresse, dann im HNEE-Postfach suchen).
- Zurückgestellt: myCampus-App HNEE (Stundenplan, Noten, Prüfungen). Datenquelle dahinter noch unbekannt.
- Lernsystem (Umbau ab 20.10., Pilot Modul Holzschutz und Sanierung = IHS Lautner + SHB Jahreis):
  Ziel: Prüfung mit wenig Aufwand bestehen; Maßstab Prüfungssimulation, nicht Informiertheit.
  Prüfung: Vortrag mit mündlicher Prüfung aus beiden Teilen, Januar 2027. Jan war bis 20.10. bei keinem Termin.
  - Prüfungsplan (Schritt 1, fertig): data/lernen/holzschutz/pruefungsplan.json (Quelle) und .md (lesbar),
    Themen mit Score 1-5, Signalen, Lernzielen, Aufgabentyp, Quellen; Liste "fehlt". Nicht im Repo
    (Inhalte aus Skripten). Häufigkeiten unbekannt, keine Prüfungsprotokolle.
  - Infokarten Pilze (6) und Insekten (6) sind Scans mit je 4 Fotos + Merkmalen: Grundlage für Bildkarten.
  - Kalender: Jans Apple-Kalender, KALENDER_ICS_URLS in shared/.env, Termine heißen wie der Kurs,
    Raum in LOCATION. Kalendermodul kommt nach agentkit (Bedarf in ../STATUS.md).
  - fsrs 6.3.2 in .venv (Jans Okay 20.10.). Tägliche Abfrage 18 Uhr, Selbstbewertung mit 4 Knöpfen,
    Claude bewertet nur in der Simulation. Dienst uni-lernen (Timer 15 min) genehmigt, Jan richtet ein.
  - Nächste Schritte: Karten + Lernermodell (FSRS) + tägliche Abfrage, Nachholwege für verpasste
    Termine, Sonntagsbericht, Simulation alle 4 Wochen, zuletzt Trigger vor der Vorlesung.

## Übergabe aus dem Hauptordner (20.10.2026): Kalender und Knöpfe fertig
- agentkit.kalender.termine(von, bis) -> Liste Termin(beginn, ende, titel, ort, ganztags, uid), Zeiten mit
  Zone Europe/Berlin, nach Beginn sortiert. Fehler beim Abruf: KalenderFehler (nennt nur "Kalender N").
- meldungen.melden(AGENT, text, knoepfe=[["Gut", "Schwer"]], dienst="uni-lernen"): Klick oder Text-Antwort
  wird Auftrag (quelle "knopf"/"antwort", text = Beschriftung bzw. Antwort, Felder meldung und dienst),
  die Zentrale startet danach uni-lernen.service. Pro Meldung zählt nur ein Klick.
- Erledigt 20.10.: agent.py holt auftraege.neue(AGENT, dienst=None) (Test in tests/test_agent.py).
  uni-lernen muss auftraege.neue(AGENT, dienst="uni-lernen") holen.
- Ohne uni-lernen.service warten die Klick-Aufträge in shared/auftraege/neu/ (Zentrale loggt das).

## Start im neuen Chat (Übergabe aus dem Hauptordner, 16.10.2026)
Fertig und getestet in shared/ (nicht hier ändern, Änderungen an shared/ im Chat im Hauptordner):
- agentkit: config, log, freigabe (inkl. Ausführung nach Freigabe), auftraege (inkl. modus), regeln,
  einstellungen, verbrauch, claude_lauf. Doku steht jeweils oben im Modul.
- Telegram-Zentrale läuft als Dienst agentenzentrale. Sie legt bei /uni bzw. /unilern Aufträge an und
  startet danach uni.service (falls vorhanden). Ebenso nach Freigabe eines uni-Entwurfs.
- Vorlagen in shared/vorlagen/: STATUS-agent.md, agent.service, agent.timer, agent_beispiel.py (Gerüst).
- Werkzeuge für Claude beim Agenten uni (einstellungen.toml): Read, Write, Edit, Glob, Grep, WebSearch.

Erste Schritte (jeweils mit Jans Okay, siehe CLAUDE.md):
1. Mit Jan klären: Welche Uni, Moodle-Adresse, Login-Art (eigenes Konto oder Single Sign-on)?
   Gibt es Moodle-Webservice-Tokens (/login/token.php, wie die Moodle-App), dann ohne Browser.
   Unipostfach: IMAP/SMTP oder Exchange? Welche Kurse, welche Fristen sind wichtig?
2. .venv anlegen und agentkit einbinden:
   `python3 -m venv .venv && echo /home/agent/agenten/shared > .venv/lib/python3.12/site-packages/agentkit.pth`
3. .env.example und .env (chmod 600) mit Uni-Zugangsdaten.
4. agent.py nach shared/vorlagen/agent_beispiel.py: Aufträge abarbeiten (erledigen mit Protokoll, lernen
   mit Sitzung), Fristen-Prüfung zeitgesteuert.
5. Lernmodus über Telegram: Rückfragen und Antworten laufen über die Zentrale. Dafür braucht die Zentrale
   noch einen Gesprächskanal Agent <-> Jan sowie /pc und /weiter. Das wird im Hauptordner-Chat gebaut,
   wenn uni so weit ist.
6. uni.service und uni.timer aus den Vorlagen, erst nach Jans Okay einrichten.

## Anforderungen (von Jan, 16.10.2026)
Zwei Arbeitsmodi. Jan wählt je nach Zeitdruck; ohne Angabe gilt "erledigen".
- Modus erledigen: Der Agent arbeitet allein und liefert danach ein verständliches Protokoll:
  - was er Schritt für Schritt gemacht hat,
  - welche Quellen er genutzt hat, mit genauer Stelle (Kurs, Datei, Seite/Folie),
  - wo er unsicher ist,
  - wie Jan das Ergebnis selbst nachprüfen kann (konkrete Prüfschritte).
  Kurzfassung per Telegram, volles Protokoll als Datei in uni/protokolle/.
- Modus lernen: Der Agent nimmt Jan an die Hand und arbeitet den Auftrag gemeinsam mit ihm durch
  (erklären, Fragen stellen, auf Antwort warten, Rückmeldung geben). Nicht alles vorlösen.
  Läuft sowohl über Telegram (unterwegs, kurze Nachrichten) als auch im Claude-Code-Chat am PC.
  Technisch: mehrere Runden, Sitzung fortsetzen mit `claude -p --resume`; der Agent merkt sich die Sitzung pro Auftrag.
- Entscheidung 16.10.: Kein automatischer Vorschlag von Modus lernen bei benoteten Abgaben. Jan wählt selbst.
- Der Modus steht im Auftrag (Feld `modus` in agentkit/auftraege.py, Werte `erledigen`/`lernen`).

## Übergabe Telegram <-> PC (Entscheidung 16.10.2026)
- Telegram und PC führen dieselbe Claude-Sitzung fort.
- Pro Lern-Auftrag eine Sitzung; Sitzungs-ID in uni/data/sitzungen/<auftrag-id>.json (nicht im Repo).
- Telegram -> PC: Jan schreibt `/pc`, Bot schickt den Befehl `cd ~/agenten/uni && claude --resume <sitzungs-id>`.
- PC -> Telegram: Jan beendet den PC-Chat und schreibt `/weiter`.
- Sperre: Solange die Sitzung am PC liegt, schreibt der Bot nicht hinein und meldet das.
- Absicherung: Nach jeder Runde schreibt der Agent uni/protokolle/<auftrag-id>-lernstand.md (durchgenommen, gut gekonnt, wo es hakte, nächster Schritt). Lässt sich eine Sitzung nicht fortsetzen, startet er neu mit diesem Lernstand.
- Beide Seiten sollen im Ordner uni/ laufen, damit dieselben Regeln (CLAUDE.md, Rechte) gelten.
- Test 16.10. (Claude Code 2.1.301): Sitzung mit `claude -p --output-format json` gestartet (liefert `session_id`), mit `claude -p --resume <id>` fortgesetzt: Sie erinnerte sich korrekt. Klappte sogar aus einem anderen Ordner. Die Sitzung liegt als .jsonl unter ~/.claude/projects/<ordner>/. Noch nicht getestet: interaktives `claude --resume <id>` am PC (muss Jan einmal selbst ausprobieren).

## Offene Punkte
1. Erledigt 16.10.: uni.service und uni.timer eingerichtet (Jan hat es ausdrücklich angewiesen), Timer 8/13/19 Uhr, Handstart erfolgreich.
2. Gesprächskanal: agent.py setzt seit 17.10. die Sitzung fort (Auftrag mit Feld sitzung): Modus und
   Protokoll-ID vom Ursprung der Antwortkette (ursprung()), Antwort-Prompts kurz, jeder Auftrag
   speichert seine Sitzung. Nur Unit-Tests: echter Test über Telegram steht aus (auf eine neue
   Antwort des Agenten antworten; Aufträge von vor dem 17.10. haben keine Sitzung).
3. Zu prüfen: erster Lauf uni-transkript (17.10. 1 Uhr), Weiterleitung BFH-Postfach.

## Gelernte Regeln
- Gruppenarbeiten und Gruppenwahlen (Jan, 17.10.2026): Jan bildet Gruppen mit seinen Freunden. Erste Wahl: Henri von Mulert, Julius von Boehmer, Lennart Blümel; wenn noch Platz ist: Felix Frankowiak. Melde früh, dass eine Gruppenwahl offen ist, nenne die Belegung (aus uebersicht.md bzw. aufgaben.md), empfiehl eine Gruppe mit genug freien Plätzen für alle und erinnere Jan, sich mit ihnen abzusprechen. Trage Jan nie selbst ein.
- Aufnahmen (Jan, 20.10.2026): Jan nimmt Vorlesungen auch auf, wenn der Kurs es verbietet. Weise ihn nicht auf Aufnahmeverbote hin.
