# Status: Agent uni

## Zweck
Moodle und Unipostfach überwachen, Fristen, Zusammenfassungen, Lernsessions.

## Stand (27.10.2026)
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
    Seit 27.10. dünn: das Lesen steckt in agentkit.imap (Tests dort), postfach.py gibt nur HNEE-Zugang mit.
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
  21.10.: Seit 17.10. jede Nacht OOM-Kill an derselben 69-min-Aufnahme (DL 260914), die als älteste
  alle weiteren blockierte. Ursache gemessen: faster-whisper berechnet die Merkmale für den ganzen
  Ton auf einmal (~50 MB/min, 20 min = 1,45 GB). Seitdem Stücke von 10 min, Schnitt an der leisesten
  Stelle ±15 s, Zeitmarken mit Versatz (Kontext zwischen Stücken geht verloren, an den Schnitten
  evtl. ein Hörfehler mehr). data/transkript_versuche.json zählt Starts, nach 2 Abbrüchen ohne
  Ergebnis: Fehler-.txt und Meldung. agent.py meldet fehlgeschlagene Schritte einmal am Tag.
  Echttest 21.10. (12 min aus DL 260914, voller Ton im Speicher, MemoryMax=3G): 2 Stücke, Schnitt
  bei 9:51, Spitze 1,2 GB, 30 min Rechenzeit (Faktor 2,5 statt 1,7, lief mit nice parallel zu anderem).
  Liegt Faktor nachts auch über 2,0, FAKTOR in transkription.py anheben.
- Jans eigene Transkripte (transkripte.py, 17.10.): Auftrag "Transkript <Kurs> [TT.MM.]" mit .txt-Datei
  (Jans Format) oder Text darunter. Python legt nach data/kurse/<Kurs>/transkripte/<datum>_transkript.txt
  ab (Kurs per Namensteil, bei Mehrdeutigkeit Rückfrage mit Kandidaten), Claude (routine) meldet
  Prüfungshinweise, Fristen, Organisatorisches. KONTEXT verweist auf Transkripte. Noch nicht echt
  über Telegram getestet.
- Gruppen (17.10.): uebersicht.md zeigt Belegung jeder Gruppenwahl (mod_choicegroup_get_choicegroup_options,
  nur choicegroupid+userid, sonst "Ungültiger Parameterwert"), aufgaben.md Jans Gruppe bei Teamabgaben,
  Fristen-Erinnerung warnt bei Teamabgabe ohne Gruppe. Mitglieder anderer zeigt Moodle nicht.
- Angehängte Dateien eines Auftrags bekommen vorab eine Textfassung (kurse.textfassung).
- Links im Auftrag (termine.py, 23.10.): Python lädt bis zu 3 Links selbst (Claude hat keinen Seitenabruf),
  liest schema.org-Events aus JSON-LD (auch subEvent) und gibt Termin + Seitentext in den Prompt. Je Termin
  entsteht data/termine/<auftrag>/<datum>_<titel>.ics und hängt an der Antwort; Jan tippt sie in Telegram an.
  In Jans Kalender schreibt der Agent nicht selbst (iCloud nur lesend). Echt getestet mit webinargeek
  (Pollmeier-Webinar 17.11.2026 10:00, Termin danach in Jans Kalender). Seiten, die Termine nur per
  JavaScript nachladen und kein JSON-LD haben, liefern keinen Termin.
- Mails senden (mail.py, 24.10., Plan von Jan freigegeben): Claude schreibt Entwürfe nach
  data/entwuerfe/<schluessel>/mail_<n>.json (an, cc, betreff, text, antwort_auf_uid, begruendung): in
  erledigen-Aufträgen (Schlüssel = Auftrags-ID), in post_pruefen (post-<zeit>, nur wenn Jan offensichtlich
  antworten muss) und bei neuem Material (material-<zeit>-<kurs>). Python prüft (Adressen, höchstens 5
  Empfänger, Betreff/Text), Gesprächsbezug (In-Reply-To/References) kommt aus data/mails/<uid>.json, nie von
  Claude. Dann freigabe.neuer_entwurf(typ "mail"), Datei wird .eingereicht bzw. .ungueltig. Nach Freigabe:
  ausfuehren() -> mail.senden: SMTP mail.hnee.de:587 STARTTLS mit HNEE-Login (AUTH LOGIN), Absender
  MAIL_ABSENDER=jkl298@hnee.de, MAIL_NAME in uni/.env, Kopie per IMAP APPEND nach "Gesendete Elemente".
  Ändern in Telegram -> Auftrag quelle "telegram-aendern", bezug = Entwurf: aenderung_bearbeiten (routine)
  schreibt neuen Entwurf (vorgaenger, alter Gesprächsbezug bleibt) und optional regel.json ->
  regeln.regel_vorschlagen. Ablehnen ohne Kommentar: kein Regelvorschlag (Zentrale fragt keinen Grund ab).
  post_pruefen legt jede gelesene Mail in data/mails/<uid>.json ab. Lernmodus bekommt keinen Mail-Hinweis.
  Echttest 24.10. erfolgreich: Entwurf an jkl298@hnee.de per Telegram freigegeben, 5 s später gesendet,
  genau einmal im Posteingang und in Gesendete Elemente (gleiche Message-ID). Ändern noch nicht echt getestet.
- Termin-Vorschläge (27.10., Jans Wunsch: Agent entscheidet, was in den Kalender kommt, Jan bestätigt kurz):
  ENTWURF_HINWEIS (Aufträge erledigen, post_pruefen, Material, Ändern) lässt Claude je Termin
  data/entwuerfe/<schluessel>/termin_<n>.json schreiben (titel, beginn, ende, ort, notiz, erinnerungen_min,
  quelle, begruendung; Zeit ohne Zone = deutsche Zeit, nur Datum = ganztägig). termine.entwurf_pruefen prüft
  (nicht vergangen, höchstens 24 h bzw. 14 Tage, höchstens 3 Erinnerungen), Standard-Erinnerungen 1 Tag und 2 Std.
  vorher, ganztägig Vortag 9 Uhr. agent.termine_einreichen gleicht mit agentkit.kalender ab (gleicher Beginn ±15 min
  und ein Titel im anderen enthalten = steht schon drin), schlägt jede UID nur einmal vor
  (data/termine/vorgeschlagen.json), legt data/termine/<schluessel>/<datei>.ics ab und hängt sie an die Meldung
  bzw. das Auftragsergebnis. Jan tippt die .ics an. Kalender nicht lesbar: Vorschlag ohne Abgleich.
  Nur Unit-Tests, erster echter Lauf ab Timer 27.10. 13 Uhr steht aus.
  Direkt eintragen (Freigeben = Termin in iCloud) wartet auf ../STATUS.md Punkt 9 (CalDAV, App-spezifisches
  Passwort von Jan). Dann Entwurfstyp "termin" in die Freigabe und ausfuehren() -> kalender.eintragen.
- Mail-Entwürfe als Einzelnachrichten (27.10., Jan): entwuerfe_einreichen schickt vor jedem Entwurf eine Meldung
  mit dem Wortlaut der Originalmail (mail.wortlaut: Von, Datum, Betreff, Anhänge, Text; nicht bei Überarbeitung)
  und eine mit dem reinen Entwurfstext (zum Kopieren/Weiterleiten), wartet bis die Zentrale beide verschickt hat
  (bis_gesendet, max. 120 s, sonst trotzdem weiter; die Zentrale zeigt Entwürfe vor Meldungen), dann erst die
  Freigabe. post_pruefen meldet die Übersicht zuerst. postfach.py speichert dafür "wortlaut" (Absätze erhalten,
  zitierter Verlauf ab "Von:/Gesendet:", "Am ... schrieb", "Ursprüngliche Nachricht" abgeschnitten, max. 20.000
  Zeichen). Mails vor dem 27.10. haben nur den zusammengezogenen text. Die Freigabe-Nachricht der Zentrale zeigt
  den Text weiterhin noch einmal mit Kopf.
- Lernblätter als PDF (lernblatt.py, 27.10., Plan von Jan freigegeben): Vorher schrieb Claude Lernblätter als .md
  nach data/kurse/<Kurs>/transkripte/ und Jan bekam nur den Pfad. Jetzt sagt LERNBLATT_HINWEIS (Aufträge erledigen
  und Antworten darauf): Lernblatt als Renderer-Beschreibung (Art zusammenfassung) nach
  data/lernblaetter/<erster Auftrag der Kette>/blatt_<n>.json, Änderungen per Antwort in derselben Datei. Das Format
  legt Python vor jedem Lauf als data/lernblaetter/FORMAT.md ab (Abschnitte Allgemein und Zusammenfassung aus
  shared/renderer/FORMAT.md), damit es nicht in jedem Prompt steht. agent.lernblaetter_bauen baut nach dem Lauf
  jedes neue oder geänderte Blatt (Prüfsumme in <ordner>/.gebaut.json) nach blatt_<n>/<Titel>.docx und .pdf
  (renderer.bauen ohne Bildvorschau + vorschau.als_pdf, also ohne pypdfium2; LibreOffice ~3 s, ~220 MB) und hängt
  das PDF an das Ergebnis. Ungültige Beschreibung: eine Nachbesserung in derselben Sitzung, bleibt sie ungültig,
  stehen die Fehler im Ergebnis. PDF-Fehler (LibreOffice) stehen im Ergebnis und im Log, nächster Lauf versucht
  es neu. Profil: uni/profil-lernblatt.toml (Kopie von Jans Zusammenfassungs-Profil, HNEE-Farben).
  Abgrenzung: "Dokument:"-Aufträge (zum Weitergeben, mit Belegprüfung in dokumente) bleiben wie sie sind.
  Nur Unit-Tests und ein Probebau mit LibreOffice; echter Lauf steht aus (Offene Punkte 7).
- Tests mit Meldungen: von OhneTelegram (tests/test_agent.py) erben, sonst landen sie echt in Telegram
  (passiert am 27.10. mit zwei Testnachrichten).
- Tests schreiben nicht ins echte logs/*.log: tests/__init__.py richtet die Logger uni, uni-lernen und
  uni-transkript vorab ohne Datei ein (hole_logger hängt dann nichts mehr an). Neuer Logger-Name: dort ergänzen.
- Aufträge während eines Laufs (23.10.): systemctl start auf einen laufenden uni.service startet keinen zweiten
  Lauf. auftraege_abarbeiten holt deshalb so lange nach, bis nichts Neues kommt, und läuft am Ende des Laufs
  noch einmal. Kommt ein Auftrag erst in den letzten Millisekunden, wartet er bis zum nächsten Timer.
- Neues Material wird eingeordnet (agent.material_meldung, 23.10.): je Kurs ein Claude-Lauf (routine,
  zeitgesteuert): Einstufung HANDELN/LESEN/NUR ABLEGEN, was tun bis wann, was nötig (Software, Remote),
  gilt es für HNEE (Terminplan und Intro, Grep nach hnee/Eberswalde/Biel). Ohne Claude (Kontingent, Fehler)
  kommt die Dateiliste mit Hinweis. Echttest LIGNOCAM-Material: 9 Schritte, ca. 83.000 Tokens, 0,13 USD, 26 s.
- BFH: Abgabe "Vortrag (Eberswalde)" steht in Moodle mit Frist 03.02.2026 (vergangen), vermutlich 2027 gemeint.
  Prüfung laut Intro-Folie 15: Vortrag (Eberswalde) 20 %, Vorbereitungsübung CAD 10 % und Bericht ImW5.2 nur Biel.
- Normen (normen.py, 23.10.): Jan legt PDFs aus Nautos (HNEE-VPN) nach data/normen/ (Unterordner erlaubt,
  nicht im Repo). Jeder agent.py-Lauf (Schritt normen_aufbereiten nach kurse_spiegeln) schreibt zu neuen
  Dateien die Textfassung und data/normen/uebersicht.md (Kennung und Ausgabe von Seite 1, Seiten, Datei;
  unlesbare PDFs als KEIN TEXT) und meldet neue Normen. KONTEXT, PROMPT_DOKUMENT und karten.py verweisen
  darauf. Nautos-PDFs sind ungeschützt und gut lesbar (getestet 23.10. mit DIN 68800-1:2019-06, 34 Seiten;
  nur das Deckblatt hat Tabs statt Leerzeichen; jede Seite trägt einen Ausdruckvermerk mit Datum).
  Kennung und Ausgabe kommen aus dem Nautos-Dateinamen (<Kennung>_<JJJJ-MM>-00_DE_<Nr>.pdf, -NA/-A2 werden
  /NA, /A2), das Deckblatt nur als Ersatz. Doppelte Downloads haben dieselbe Nautos-Nr. (Endung " (1)").
  Liegen vor (24.10., 48 Dateien, Text aus allen, Doppel gelöscht): holzschutz/ (DIN 68800-1 bis -4, DIN EN 335, 350 mit
  Berichtigung 1, 351-1/-2, 460, 599-1), eurocode5/ (DIN EN 1995-1-1 2010-12 + A2 2014-07 + NA 2013-08 und
  2026-09; DIN EN 1995-1-2 2010-12 + NA 2010-12 und 2026-10), bauphysik_lca/ (DIN 4108-2, 4108-3, 276, 277,
  DIN EN 15804, 15978 2012 und 2026, DIN EN ISO 14040, 14044), fertigung_bfh/ (DIN 199-1, 6763, 66025-1),
  eurocode_grundlagen/ (DIN EN 1990/NA + NA/A1 – Grundnorm DIN EN 1990 selbst FEHLT; DIN EN 1991-1-1 bis -4
  2010-12 mit NA, Änderungen, Berichtigung), eurocode5/ zusätzlich DIN EN 1995-2 + NA, material/ (DIN EN 338
  2016-07, DIN 4074-1 2026-05, DIN 4074-5 2026-11). Noch FEHLT: DIN EN 17121 (Modulhandbuch SHB).
  Jan lädt aus Nautos in den Hauptordner data/normen/, dabei entstehen Doppel (gleiche Nautos-Nr., Endung
  " (1)"). aus_dateiname macht aus -NA-A1 "/NA/A1".
  Eurocode 5: Die Kurse (SHB 02) nutzen die 1. Generation (2010-12, 8.2 = Abscheren). In 2026-09 ist 8.2 der
  Knicknachweis, Verbindungen in Kap. 11; alte Fassung wird bis April 2028 zurückgezogen, NA zu 2026 fehlt.
  KONTEXT: bei mehreren Ausgaben die nehmen, auf die das Kursmaterial verweist. Skript SHB 01 S. 5
  "DIN EN 399-1" ist ein Tippfehler für DIN EN 599-1. Holzschutz-Prüfungsplan: Fundstellen eingetragen.
  Liste der Normen für dieses Semester an Jan gegeben (aus Kurs-Textfassungen gezählt und Normen.xlsx in
  Lifecycle-orientierte Bilanzierung/09 Normen).
- Literatur (literatur.py, 24.10.): PDFs in data/literatur/<herkunft>/ (nicht im Repo). Jeder agent.py-Lauf
  (Schritt literatur_aufbereiten nach normen_aufbereiten) schreibt Textfassungen und data/literatur/uebersicht.md
  (Herkunft, Titel aus Dateiname, Seiten) und meldet Neues. Gemeinsame Schleife mit Normen:
  normen.ablage_aufbereiten. KONTEXT, PROMPT_DOKUMENT und karten.py verweisen darauf (ergänzend zu Kurs und Normen).
  Liegen vor: informationsdienst_holz/ (holzbau handbuch R05 T01 F01, R05 T02 F01, R05 T02 F02 Holzschutz bauliche
  Maßnahmen, IDH spezial serielles Sanieren, StGHlb Merkblatt und Muster-Ausschreibung Sanierung BSH),
  kit/ (Blaß/Sandhaas, Ingenieurholzbau, 658 S.; Textfassung oft ohne Leerzeichen, Grep nach Einzelwörtern).
  Gewünscht, nur als E-Book-PDF sinnvoll (Scans ohne Textebene nützen nichts, kein OCR): Scheiding u. a.
  Holzschutz (Hanser), Huckfeldt/Schmidt Hausfäule- und Bauholzpilze, Werner/Zimmer Holzbau 1+2.
- BFH-Postfach (jan.kleinke@students.bfh.ch): Weiterleitung ins HNEE-Postfach am 17.10. von Jan
  eingerichtet, Ankunft noch nicht geprüft (Testmail an die BFH-Adresse, dann im HNEE-Postfach suchen).
- Zurückgestellt: myCampus-App HNEE (Stundenplan, Noten, Prüfungen). Datenquelle dahinter noch unbekannt.
- emma (HNEE-Campusportal, CampusNet von Datenlotsen, 24.10. einmal von Hand gelesen, nicht im Agenten):
  Anmeldung nur über SSO dsf.hnee.de (IdentityServer, Formular Username/Password + __RequestVerificationToken),
  geht mit HNEE_NUTZER/HNEE_KENNWORT aus uni/.env; CampusNet leitet danach per Refresh-Header weiter.
  Menü: MYEXAMS, EXAMREGISTRATION (Prüfungen mit Termin und Anmeldestatus), MYREGISTRATIONS, MYMODULES, EXAMRESULTS.
- Prüfungen WS 26/27 (emma + Modulhandbuch-Msc_aktualisiert.pdf, 24.10.), Lernstrategie für alle geplant:
  - Fachplanung im Hochbau 2 / HSS (M.03.R.2515.W, IHS + SHB): Vortrag mit mündlicher Prüfung. Pilot Lernsystem.
  - Computerbasierte Planung (M.03.R.2513.W): Teile BFH "Fertigung im Holzbau 1" und CAM (keine eigene Prüfung).
    Widerspruch offen: HNEE-Modulhandbuch/emma Vortrag mit mündlicher Prüfung 100 %, BFH-Intro Folie 15
    Modulprüfung 75 min 80 % + Vortrag Eberswalde 20 %.
  - Nachhaltigkeit im Holzingenieurwesen (emma: Sustainability in wood engineering, M.03.R.2505.P): LCA +
    Eilbacher, Vortrag mit mündlicher Prüfung, beide Teilleistungen nötig. Offen: ob die LCA-Teamabgabe GEG
    (fällig 16.10., nicht abgegeben) eine Teilleistung ist.
  - Research project 2, Practical module: Prüfungsform laut emma, Zuordnung der Kurse noch nicht geklärt.
  - Bio-based materials (mündlich 12.11.2026): Jan lässt es wegen Workload aus (24.10.).
  - Für keine Prüfung außer Research project 1 ist Jan in emma angemeldet, Termine meist offen.
  - Mails an Dozenten zu den offenen Punkten: Jan will vorerst keine (24.10.).
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
  - lernmodell.py: Karten (karten.json), FSRS-Stand (zustand.json), Verlauf (verlauf.jsonl) je Modul;
    Planung in Tagen, Auswahl höchstens 13 Karten (~10 min), höchstens 8 neue pro Tag, fällige zuerst,
    reihum über Themen, neue nach Score und schwacher Trefferquote; Status nicht gesehen/wackelig/sitzt.
  - karten.py <modul> [min_score]: schneidet Bildkarten aus den Infokarten (Fotos ohne Beschriftung),
    Claude schreibt karten_entwurf.json, Python prüft und übernimmt (ID aus Thema, Frage und Bild).
    Erster Lauf 20.10.: 61 Karten (Score 4-5, davon 12 Bildkarten), Opus, 29 von 30 Schritten,
    ca. 820.000 Tokens, 7 min; 7-Tage-Auslastung danach 71 % (Stufe sparen). Weitere Läufe kleiner
    halten (ein Thema oder wenige Themen pro Lauf).
  - lernen.py (Dienst uni-lernen, Vorlage systemd/uni-lernen.*, Timer alle 15 min): ab 18 Uhr, wenn kein
    Kalendertermin läuft, Frage mit [Antwort zeigen] [Später], dann Antwort + Quelle mit
    [Nochmal] [Schwer] [Gut] [Leicht]; Nochmal kommt am Ende einmal neu; Später = 1 h, bis 22 Uhr.
    Zustand data/lernen/sitzung.json. Noch NICHT eingerichtet: wartet auf Punkt 6 in ../STATUS.md
    (Zentrale soll Klick-Aufträge still abschließen), dann richtet Jan den Dienst ein.
  - Nächste Schritte: Dienst einrichten und über Telegram testen, Nachholwege für verpasste Termine,
    Sonntagsbericht, Simulation alle 4 Wochen, zuletzt Trigger vor der Vorlesung.

- Dokument-Aufträge an dokumente (Teil D von Punkt 3a im Hauptordner, gebaut 22.10., nur Unit-Tests):
  - Auslöser: Auftrag beginnt mit "Dokument:" (weitergabe.ist_dokumentauftrag), nur im ersten Lauf, nicht bei
    Antworten darauf. Ohne Auslöser nie Weitergabe.
  - agent.dokument_auftrag: Claude (PROMPT_DOKUMENT, Format-Abschnitt aus shared/renderer/FORMAT.md im Prompt)
    schreibt protokolle/<id>.md (Glossar, Behauptungsliste mit Transkript/Folie/Norm/Status, Abweichungen,
    fehlende Normen, offene Fragen), data/weitergabe/<id>/behauptungen.json (Format von dokumente),
    data/weitergabe/<id>/zusammenfassung.json (Renderer-Beschreibung) und data/weitergabe/<id>.json
    {"text", "dateien"}. Python prüft (weitergabe.uebergabe_pruefen: nur Dateien aus data/weitergabe/<id>/,
    höchstens 5, behauptungen.json und eine Beschreibung Pflicht, beide mit den Renderer-Regeln), bei Fehlern
    eine Nachbesserung in derselben Sitzung, sonst fehlgeschlagen mit den Fehlern. Dann
    auftraege.weitergeben("uni", "dokumente", ..., aus_auftrag=<id>), Merkdatei data/weitergabe/<id>.erledigt.
    Liegt schon eine gültige Übergabe vor (Abbruch nach dem Lauf), wird ohne neuen Claude-Lauf weitergegeben.
  - dokumente (Teil C) schreibt die Zusammenfassung mit eigenem Claude-Lauf neu und prüft sie gegen
    behauptungen.json; zusammenfassung.json dient dort als aufbereitete Fassung. Der ursprüngliche Plan
    (dokumente baut nur) gilt damit nicht. Folien gehen nicht mit, dokumente kann Folienangaben also nicht
    selbst nachprüfen.
  - Offene Fragen an den Dozenten nur in Protokoll und Dokument, kein Forumsbeitrag (bräuchte Freigabe).
  - Quellenlage IHS 20.10.: DIN 68800-1 und EN 350 fehlen, von DIN 68800-4 nur Bild von 4.6
    (data/lernen/holzschutz/quellen/). Folie 81 ist ein Reflexionsauftrag ohne Zahlen: das Beispiel ist
    ein eigenes und wird so gekennzeichnet.
  - Echter Lauf steht aus. Vorschlag für den Auftrag (per /uni):
    "Dokument: Zusammenfassung Integrierter Holzschutz 20.10. für Kommilitonen, Vorbereitung Exkursion 27.10.
    und Prüfung. Quelle: data/eingang/20261022-082205-uni-f0e6f1/Transkribt_20-10-26.pdf (.txt), Folien und
    Infokarten in data/kurse/Integrierter Holzschutz/ (u. a. Folie 65 und 81). Gliederung: Organisatorisches
    mit Exkursion, Prüfungsrelevantes (Abstände, Rückschnitte), Tabelle Gebrauchsklasse -> Dauerhaftigkeitsklasse,
    Übung Folie 81 durchgespielt, Hintergrund, 5-10 Selbsttest-Fragen, offene Fragen an den Dozenten."
    Danach Tokens messen (Schätzung 100.000-200.000 für uni, dazu der Lauf von dokumente).

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
3. Echter Lauf Dokument-Auftrag IHS 20.10. (siehe Stand), dabei Verbrauch messen.
5. Weitere Normen von Jan: je Lieferung Verzeichnis prüfen und im Holzschutz-Prüfungsplan (json und md)
   "fehlt" und Quellen nachziehen. Kernliste des Semesters liegt vollständig vor (24.10.). Nicht in Nautos:
   WTA-Merkblätter (Transkript IHS 20.10. S. 22, Regelsanierung).
7. Lernblatt-PDF: Echttest 27.10. geklappt (Auftrag 20261027-204849-uni-827139, Antwort auf a4ca81, im Chat
   wie eine Telegram-Antwort angelegt, gleiche Sitzung): blatt_1.json gültig im ersten Anlauf, PDF 6 Seiten hing
   am Ergebnis. Verbrauch: Opus, 4 Schritte, ca. 370.000 Tokens, 1,29 USD, 82 s. Offen: derselbe Weg direkt
   über eine Telegram-Antwort, und das Blatt vom 20.10. (2026-10-20_Transkript_Nr1_Zusammenfassung.md).
4. Zu prüfen: Lauf uni-transkript in der Nacht zum 22.10. (DL 260914 sollte fertig werden, danach die
   übrigen Aufnahmen), Weiterleitung BFH-Postfach.
8. Bedarf (Hauptordner-Chat, 27.10.): agentkit.mail gibt es jetzt (verallgemeinert aus uni/mail.py).
   uni/mail.py darauf umstellen: pruefen(entwurf, original) nimmt die Originalmail als dict (mail_holen
   vorher selbst aufrufen), senden(cfg, daten) loggt mit MAIL_NUTZER/MAIL_KENNWORT ein (ersatzweise
   IMAP_NUTZER/IMAP_KENNWORT, nicht HNEE_NUTZER) und legt eine Kopie nur ab, wenn GESENDET_ORDNER gesetzt ist.
   Also in uni/.env MAIL_NUTZER, MAIL_KENNWORT und GESENDET_ORDNER="Gesendete Elemente" eintragen.
   SMTP_PORT 587 bleibt STARTTLS. mail_merken und mail_holen bleiben in uni.

## Gelernte Regeln
- Gruppenarbeiten und Gruppenwahlen (Jan, 17.10.2026): Jan bildet Gruppen mit seinen Freunden. Erste Wahl: Henri von Mulert, Julius von Boehmer, Lennart Blümel; wenn noch Platz ist: Felix Frankowiak. Melde früh, dass eine Gruppenwahl offen ist, nenne die Belegung (aus uebersicht.md bzw. aufgaben.md), empfiehl eine Gruppe mit genug freien Plätzen für alle und erinnere Jan, sich mit ihnen abzusprechen. Trage Jan nie selbst ein.
- Aufnahmen (Jan, 20.10.2026): Jan nimmt Vorlesungen auch auf, wenn der Kurs es verbietet. Weise ihn nicht auf Aufnahmeverbote hin.
