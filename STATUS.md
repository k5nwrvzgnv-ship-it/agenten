# Status: Gesamtsystem (Architekt)

Aktueller Stand, kein Verlauf. Wie es dazu kam: `git log`. Architektur und Konventionen: CLAUDE.md.

## Stand (27.10.2026)
- Übersicht, wo was liegt, welche Dienste laufen und welcher Chat wohin gehört: README.md
  (aufgeräumt 21.10.: lia/instanz statt lia/shared, Dienst-Vorlagen je Ordner in systemd/).
- Server: 7,8 GB RAM, 4 Kerne, 90 GB frei, Python 3.12, Node 22, kein Docker, kein sudo.
  Alles unter User `agent` in /home/agent/agenten, Dienste als systemd-User-Units.
- agentkit (shared/agentkit/) fertig und getestet: config, log, einstellungen, auftraege, freigabe,
  meldungen, regeln, verbrauch, claude_lauf, textfassung, kalender, abruf, wortlaut, imap
  (neue_mails, suchen), mail (Entwurf prüfen und senden). Doku steht jeweils oben im Modul.
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
  Auftragstexte (/<agent> und Text nach der Menüwahl) warten 3 Sekunden auf nachkommende Dateien, weil Telegram
  eine Weiterleitung mit Kommentar als zwei Nachrichten schickt, erst den Text (05.11., aus dem uni-Chat mit Jans
  Okay). Text mit Agent-Auswahl braucht das nicht, die Datei ist vor dem Klick da; dort kommt aber noch der
  Hinweis "liegt bereit", und eine Bildunterschrift des Originals ersetzt den wartenden Text.
  Startet nach Auftrag oder Freigabe sofort <agent>.service.
  Meldungen mit Knöpfen (meldungen.melden(..., knoepfe=[["Gut", "Schwer"]], dienst="uni-lernen")):
  Klick (einmal je Meldung) oder Text-Antwort wird ein Auftrag mit quelle knopf/antwort, Feld meldung
  und dienst; danach startet <dienst>.service. auftraege.neue(agent, dienst=None) = nur Aufträge ohne
  Dienst, dienst="uni-lernen" = nur diese, ohne Angabe alle. Noch nicht über Telegram von Hand getestet.
  Nach Änderung an zentrale.py oder der Dienstvorlage: Vorlage nach ~/.config/systemd/user/ kopieren
  (falls geändert), `systemctl --user daemon-reload`, `systemctl --user restart agentenzentrale`.
- claude-Läufe ("Claude denkt, Python handelt"): ohne Bash und MCP, Schreiben nur im Agent-Ordner,
  Schreibschutz auf Code/STATUS.md/Regeln/Einrichtung, kein Zugriff auf .env. Alles mit echten
  Läufen getestet. Grundlast ca. 6.300 Tokens pro Lauf.
- Verbrauch: Konto aller Agenten (Jans und Lias Instanz) per [konto] quelle in shared/einstellungen.toml.
  Heute "token" (Jan 27.10. abends wieder umgestellt): eigenes Agenten-Konto, CLAUDE_CODE_OAUTH_TOKEN in
  shared/.env; ohne Token startet kein Lauf (KeinKonto). Erneuern: `~/.local/bin/claude setup-token` mit dem
  Agenten-Konto, Jan trägt ihn selbst ein.
  Alternative "login": Jans Login ~/.claude/.credentials.json (Pro), geteilt mit seinen Chats; claude_lauf
  entfernt dann ANTHROPIC_API_KEY/AUTH_TOKEN und CLAUDE_CODE_OAUTH_TOKEN für claude -p. Echt getestet 27.10.
  (Haiku): Lauf ohne Token ok. Stufen normal/sparen/nur_auftraege/limit nach 5h- und 7d-Auslastung dieses Kontos, Werte in
  shared/einstellungen.toml. Einschränkung: Auslastung wird nur bei Agenten-Läufen aktualisiert.
- Qualität: `./pruefen.sh` (Tests aller Ordner, Linter ruff aus .venv im Hauptordner, Regeln in ruff.toml).
  Git-Hook githooks/pre-commit bricht Commits ab, wenn nicht grün (core.hooksPath = githooks).
- agentkit.kalender (20.10.): termine(von, bis) aus KALENDER_ICS_URLS, nur Bordmittel (zoneinfo,
  DAILY/WEEKLY/MONTHLY/YEARLY, EXDATE, RECURRENCE-ID). Mit Jans Kalender getestet: 395 Termine,
  keine Warnung, Woche ab 19.10. stimmt. Umlaute fehlen teils schon in den iCloud-Daten ("Link ber").
- Aufträge von Agent an Agent (22.10.): `auftraege.weitergeben(von, an, text, aus_auftrag, dateien=)`.
  Nur Paare aus [weitergabe] in shared/einstellungen.toml (heute uni -> dokumente), andere Instanzen
  erben das nicht. Dateien aus dem Ordner des Absenders werden kopiert (wie Ergebnisdateien geprüft:
  nichts Verstecktes, höchstens 50 MB). Kettenschutz: Ein Auftrag mit Feld von darf nicht weitergegeben
  werden (aus_auftrag muss dafür angegeben sein). Keine Freigabe (intern, Jan 22.10.): Die Zentrale
  startet <empfänger>.service und meldet die Weitergabe nur, wenn der Empfänger keinen Dienst hat
  (Auftrag wartet). Das Ergebnis geht wie jedes direkt an Jan, nicht zurück an den Absender.
  Meldungen über Telegram getestet (22.10., Testauftrag). Mit echtem Lauf von dokumente getestet (22.10.).
- Agent uni läuft (Dienst + Timer 8/13/19 Uhr). Details: uni/STATUS.md.
- Agent dokumente läuft (Dienst dokumente, ohne Timer, eingerichtet 22.10.): Zusammenfassungen als PDF und docx
  über den Renderer, mit Selbstkontrolle gegen eine Behauptungsliste. Details: dokumente/STATUS.md.
- Lias Instanz (21.10.): eigener Ordner lia/ unter User agent, kein eigener Linux-User.
  agentkit wählt die Instanz über AGENTKIT_INSTANZ=<instanz-ordner> (ohne Variable unverändert Jans).
  lia/instanz/: .env (Token @zentraleliabot, Lias Chat-ID), Warteschlangen, regeln.md.
  Dienst lia-zentrale (shared/telegram/portal.py, Ansichten in portal_logik.py): eine Menü-Nachricht
  (Panel), die beim Tippen bearbeitet wird: Neues Material, Meine Woche, Frage stellen, Meine Anfragen,
  Hilfe, Aktualisieren, Zurück. Freitext wird eingeordnet (Material/Frage), Grüße zeigen das Menü.
  Ergebnisse mit Bezug zur Anfrage und Knopf "Menü". Keine Befehle, keine Dateien, Linkvorschau aus,
  Log ohne Inhalte. Daten und Log in lia/instanz/zentrale/.
- Menü-Nachricht auch in Jans Zentrale (21.10.): /start oder /menue zeigt das Panel (shared/telegram/
  panel.py, Ansichten in logik.py): Agent antippen (Modus umschaltbar), nächste Nachricht = Auftrag;
  Entwürfe (erneut anzeigen), Verbrauch, Status, Hilfe. /hilfe zeigt die Befehle, alle Befehle wie bisher.
  Agent-Auswahl (Panel und Text ohne Befehl) nur für Agenten mit <agent>.service, heute nur uni.
  Panel-ID liegt nur im Speicher: nach Neustart erst wieder nach /start.
  Platzhalter lia/unterricht (Dienst lia-unterricht) antwortet "kommt bald", ohne Claude.
  Ausfälle beider Dienste melden sich bei Jan (ausfall@). zentrale.py und logik.py unverändert.
- Bedienung der Zentrale (Jan 22.10.: "Backend bleibt Backend"): Nachrichten an Jan sind kurz.
  Absender fett in der ersten Zeile (keine [klammern]), danach nur das Ergebnis des Agenten (kein
  Auftragstext, keine IDs, Pfade, Kontrollrunden). Kurzer Text steht als Beschriftung unter der Datei.
  Gibt es eine gleichnamige PDF, kommt nur sie (docx bleibt auf dem Server). Stufenwechsel nur bei
  Limit ("Kontingent aufgebraucht, Aufträge warten bis ...") und wenn es wieder frei ist; Stufe sonst
  nur unter /verbrauch. Bestätigung eines Auftrags: "Uni ist dran." Technisches ins Log.
  Entwürfe ebenso: "<b>Uni</b> · Mail-Entwurf", Titel, Inhalt, Details als Zeilen. Unter Details nur, was im
  Inhalt nicht schon wörtlich (als ganzes Wort) steht (Jan 27.10.); Zahlen und Objekte immer. Nichts gekürzt.
  Typnamen: Mail-, Nachrichten-, Kauf-, Termin-Entwurf.
- Ausfallmeldung (21.10.): Jede Unit trägt OnFailure=ausfall@%n.service (Vorlage
  shared/systemd/ausfall@.service, eingerichtet). agentkit.ausfall schickt "Störung" fett, Dienst und Grund in
  Worten (oom-kill = zu wenig Arbeitsspeicher), ohne Journal-Zeilen, direkt per Telegram, sonst über
  shared/meldungen/. Höchstens eine Meldung je Unit in 6 h (shared/ausfall/stand.json). Mit
  Test-Unit geprüft: kam an. Eingerichtet für uni, uni-transkript, agentenzentrale; uni-lernen und
  dokumente haben es in der Vorlage. Grenze: agentenzentrale hat Restart=on-failure und gilt nie als
  fehlgeschlagen, solange der Neustart klappt. Nicht erkannt: Timer, die gar nicht mehr starten.
- Feedbackschleife (Jan 27.10., CLAUDE.md „Lernen aus Feedback“): Unter jedem Ergebnis in beiden Zentralen
  Knöpfe Passt / Zu lang (nur hier oder ab jetzt immer) / Falscher Fokus / Feedback schreiben (shared/telegram/
  vorlagen.py). Bei Lia ist auch eine Antwort auf ein Ergebnis Feedback, bei Jan setzt eine Antwort weiter die Sitzung
  fort. Feedback = Auftrag an „feedback“ (quelle feedback, bezug = Ergebnis); Dienste feedback und lia-feedback
  (shared/feedback/lauf.py, eingerichtet 27.10.), die Zentralen starten sie. Claude (routine, nur Read) ordnet zu:
  nachbesserung, regel, notiz oder keine; agentkit.feedback.entscheiden prüft die Nie-automatisch-Liste (heikel,
  Widerspruch, Agent ohne Dienst; nur bei Jans Agenten auch zweite Nachbesserung und Kosten über 1 USD oder
  unbekannt, Lage.grenzen, Jan 30.10.). Regel/Notiz: Zeile mit
  „(Feedback <id>)“ in <instanz>/regeln.md bzw. „Gelernte Regeln“ oder „Wünsche aus Feedback“ einer STATUS.md
  (Oberfläche: diese Datei); der Dienst committet genau diese Datei. Jan bekommt je Fall eine Meldung „Feedback“
  mit Stopp (Vorschlag: Übernehmen/Verwerfen; eigenes Feedback: Rückgängig). Klick -> feedback.service, der Fall
  wird über shared/feedback/data/meldungen.json gefunden, auch in Lias Instanz. Lia bekommt die Bestätigung als
  Ergebnis, nach Jans Entscheidung eine Meldung (Lias Zentrale zeigt jetzt Meldungen aus lia/instanz/meldungen).
- Vorlagen (27.10.): Ergebnis mit daten.kern (auftraege.abschliessen(..., daten=)) -> Kern, höchstens 3 Punkte,
  „Bitte prüfen“, höchstens 10 Belege als ausklappbares Zitat. Ohne daten wie bisher. Lia sieht bei Fehlern den
  Grund des Agenten. Kurzer Text steht mit den Knöpfen unter der Datei. Snapshot-Tests in
  shared/telegram/tests/snapshots (bei gewollter Änderung SNAPSHOTS_NEU=1, Diff ansehen, committen).
- Nachweis Feedbackschleife (27.10.): echtes Ergebnis Webauftrag V2 in einer Nachweis-Instanz (Scratch), Lias
  Zentrale mit aufgezeichneten Telegram-Aufrufen (Lia bekam nichts). „Falscher Fokus“ + Text -> Feedback-Auftrag;
  echter Zuordnungslauf (Sonnet, 0,03 USD, 8 s): Regel nur für recherche, eingetragen; Meldung an Jan um 16:19:35
  gesendet; Stopp (Auftrag wie aus dem Klick) über feedback.service: Regel entfernt, Stand gestoppt, Nachricht an
  Lia, Jans Zentrale meldete „Gestoppt“. Der Stopp-Knopf dieser Meldung antwortet jetzt „Schon entschieden“.
  Nicht echt geprüft: Commit durch den Dienst (Datei lag außerhalb des Repos, nur Unit-Test), Nachbesserung,
  Klicks in Telegram.
- Vinted-Bot Stufe 1 (27.10., Ausnahme in CLAUDE.md): llm.py protokolliert jeden claude-Lauf in
  shared/verbrauch/laeufe.jsonl (agent vinted, konto login, art foto/ranking/nachricht/antwort, ohne Auslastung,
  damit die Stufen weiter nur das Agenten-Konto sehen). Unit mit OnFailure=ausfall@%n.service und Startgrenze
  5 in 5 min (Vorlage ~/agents/vinted/systemd/), danach bleibt er aus. Testmeldung kam per Telegram raus.
  Erster echter Eintrag: Ranking mit Opus 0,13 USD. Offen: nach einigen Tagen Kosten je art auswerten,
  dann entscheiden, ob das Ranking auf Sonnet wechselt (Stufe 2: Freigabe-Warteschlange, Stufe 3: einkauf).

## Entscheidungen
- Telegram ist die Zentrale in beide Richtungen. Jan diktiert per Handy-Tastatur, nur Text.
  Sprachnachrichten (faster-whisper) eventuell später, nur nach Okay.
- Modus pro Auftrag: `erledigen` (Standard, Protokoll mit Prüfanleitung) oder `lernen` (gemeinsam,
  Telegram und PC-Chat führen dieselbe Sitzung fort). Kein automatischer Vorschlag von lernen.
- Agenten denken mit `claude -p` (~/.local/bin/claude). Laufzeit-Agenten ändern nie Code.
- Rollen für Entwicklungs-Chats nicht eigens gebaut: Plan-Modus und /code-review reichen (16.10.).
- Notion-Test (Jan 04.11.2026, Plan freigegeben, noch nichts gebaut): Notion als Arbeitsoberfläche, Agenten bleiben auf dem Server.
  Auftrag für den Hauptordner-Chat, Einrichten von Timer und Regeländerung erst nach Zusammenfassung an Jan:
  - Neuer Ordner shared/notion/, nur Bordmittel, Logik getestet, Testordner in pruefen.sh, eigener systemd-User-Timer alle 2 Minuten.
    Token einer Internal Connection (kein PAT, der hätte alle Rechte Jans) in shared/notion/.env, chmod 600, trägt Jan selbst ein.
    Die Connection sieht nur die Test-Datenbank.
  - Datenbank "Aufträge": Titel = Name, Seitentext = Auftrag, Status. Ein Notion-Button "Starten" setzt den Status (Buttons können Seiten
    bearbeiten, laut Hilfe in allen Tarifen); Datenbank-Button auf der Zeile im Test prüfen. Die Brücke fragt per Timer ab, keine Webhooks
    (Button-Webhook nur in bezahlten Tarifen, braucht öffentliche Adresse, pausiert bei Fehlern).
  - Brücke: nur Seiten von Jans Notion-Konto annehmen (created_by), auftraege.neuer_auftrag(agent "uni", quelle "notion"), danach
    <agent>.service starten (die Zentrale startet nur Weitergaben von selbst). Ergebnis, Dateien, Status zurück auf die Seite.
    Grenzen: 2000 Zeichen je Rich-Text, 100 Blöcke je Anfrage, Datei im Free-Tarif 5 MB (größere nur per Telegram, Hinweis auf der Seite).
  - Keine Doppelläufe: Seite -> Auftrag vor dem Anlegen vormerken. Abbruch dazwischen wird nicht wiederholt, sondern an Jan gemeldet.
  - Die Zentrale meldet jeden abgeschlossenen Auftrag weiter per Telegram: bleibt im Test so, zentrale.py unverändert.
  - Nur unkritische Recherchen: keine Mails, Kursunterlagen, Transkripte, kein Exposé, nichts aus Lias Instanz. Freigaben bleiben in Telegram.
  - Befristete Ausnahme in CLAUDE.md eintragen: Ergebnisse dieses Tests gehen ohne Einzelfreigabe in Jans eigenen Notion-Workspace (Jans Okay 04.11.).
  - Nicht im Test: Kommentare an den Agenten, Webhooks, weitere Agenten, Felix und Henri. Abnahme nach Jans Eindruck, keine Messung.

## Offene Punkte
1. Erledigt im uni-Chat 17.10.: agent.py setzt Antworten in der Sitzung fort, jeder Auftrag speichert
   seine Sitzung. Noch nicht getestet: echte Antwort über Telegram, interaktives `claude --resume <id>`
   am PC (Jan einmal selbst).
2. dokumente: kann Zusammenfassungen (22.10.), weitere Arten im dokumente-Chat (dokumente/STATUS.md). Danach
   posteingang, einkauf (je mit STATUS.md aus shared/vorlagen/).
   posteingang (Plan Jan 27.10.): Jans privates Postfach jan@kleinke.org bei All-Inkl, IMAP
   w005718f.kasserver.com:993 (SMTP 465/587), Login direkt mit Postfach-Kennwort (kein App-Passwort bei
   All-Inkl), Kennwort trägt Jan selbst in posteingang/.env ein. Stufe 1 nur lesen und melden: Vorfilter ohne
   Claude (List-Unsubscribe, Precedence bulk, Spam, Absenderliste), dann Einordnung per claude_lauf (Frist/
   Rechnung, persönlich, Termin, Bestellung, unwichtig), Meldung [post], data/mails nach 30 Tagen löschen,
   Timer 8/13/19 Uhr. Senden erst Stufe 2 nach Freigabe. Schritt 1 erledigt 27.10.: agentkit.imap
   (aus uni/postfach.py, Zugang und Stand-Datei als Parameter), uni nutzt es. Gerüst posteingang/ angelegt 27.10.
   (ohne agent.py und Dienst). Weiter im eigenen Chat ~/agenten/posteingang, Plan in posteingang/STATUS.md.
   Ergebnisdateien an Jan: auftraege.abschliessen(..., dateien=) und meldungen.melden(..., dateien=).
3. Dateien aus Telegram: gebaut 16.10. (Zentrale nimmt Dokumente und Fotos bis 20 MB an, Ablage
   <agent>/data/eingang/<auftrag-id>/, Pfade im Feld dateien und am Ende des Auftragstexts).
   Noch offen: Handtest durch Jan (Datei mit "/uni ..." als Bildunterschrift, Album, Datei ohne Befehl).
   uni (17.10.): legt für a["dateien"] vorab <datei>.txt an (kurse.textfassung) und übernimmt
   "Transkript <Kurs>"-Aufträge als Vorlesungstranskript.
3a. Übungsaufgabe Holzschutz-Zusammenfassung (Jan, 22.10.): uni bereitet das Transkript vom 20.10. mit
   Belegen auf und gibt es per weitergeben an dokumente, das daraus ein PDF baut. Teil A (Weitergabe)
   erledigt. B (Renderer) erledigt 22.10.: Art "zusammenfassung" -> .docx, PDF aus der Vorschau
   (ergebnis.pdf). Format in shared/renderer/FORMAT.md, Profil beispiele/profil-jan-zusammenfassung.toml
   (erstellt_von trägt dokumente ein), Logo über eine Word-Vorlage mit Logo in der Kopfzeile.
   Quellen je Aussage als {"art": "transkript"|"folie"|"norm", "stelle": ...}, Kennzeichen "unsicher"/"muendlich".
   HNEE-Farben stehen im Profil. Noch offen: Logo in Grün (bisher nur weißes SVG), siehe Renderer-STATUS.
   - C dokumente: erledigt 22.10. Nimmt Aufträge an (auch von uni), Claude schreibt die Beschreibung selbst
     (eine mitgeschickte Renderer-Beschreibung ist nur Vorlage), Kontrolle gegen behauptungen.json, die Python
     nachprüft. Testauftrag uni -> dokumente lief durch, PDF und docx an Jan. Format: dokumente/STATUS.md.
   - D uni: erledigt 22.10. (nur Unit-Tests). Auftrag beginnt mit "Dokument:" -> Claude schreibt Protokoll
     (Glossar, Behauptungsliste, Abweichungen, fehlende Normen, offene Fragen), behauptungen.json und
     zusammenfassung.json in uni/data/weitergabe/<id>/; Python prüft (uni/weitergabe.py, nur Dateien aus diesem
     Ordner, kein Transkript) und gibt mit aus_auftrag=<id> an dokumente weiter, höchstens eine Nachbesserung.
     Offene Fragen nur in Protokoll und Dokument, kein Forumsbeitrag. Details und Auftragstext: uni/STATUS.md.
   Noch offen: echter Lauf IHS 20.10. (/uni Dokument: ...), dabei Verbrauch von uni und dokumente messen.
4. Optional: Token des Bots bei BotFather erneuern (/revoke), da er im Chatverlauf stand.
5. Bedarf aus uni (Lernsystem): erledigt 20.10. (kalender, Knöpfe, Start von <dienst>.service).
   Übergabe in uni/STATUS.md. Offen: Handtest der Knöpfe über Telegram, sobald uni die erste
   Meldung mit Knöpfen schickt.
6. Bedarf aus uni (20.10., vor dem Start von uni-lernen nötig): Die Zentrale meldet jeden erledigten
   Auftrag ("Auftrag erledigt (uni): ..."). Aufträge aus Klick oder Antwort auf eine Meldung (Feld
   meldung gesetzt) bitte still abschließen, sonst kommt nach jedem Knopfdruck der Lernabfrage eine
   zusätzliche Nachricht; der Agent antwortet dort selbst mit einer neuen Meldung.
   Fehlgeschlagene solche Aufträge weiter melden. uni-lernen schließt sie mit status "erledigt" ab.
6a. Bedarf an dokumente (und jeden Agenten, Jan 22.10.): Der Ergebnistext (auftraege.abschliessen) ist das,
   was Jan in Telegram liest. Höchstens 2-3 Sätze: was fertig ist, und was Jan prüfen muss. Keine Kontrollrunden,
   keine Aufzählung des Inhalts, kein "Offene Fragen: keine", keine Begründung der Seitenzahl.
   Heute in dokumente/zusammenfassen.py ergebnistext() und Claudes freie Antwort. Ein docx bekommt Jan nur
   auf Nachfrage (Antwort auf die Nachricht); der Agent muss es dann als Ergebnisdatei ohne PDF daneben schicken.
7. Server hat keinen Swap (braucht root). Nicht die Ursache des OOM bei uni-transkript, aber jeder
   Speicherengpass endet sofort im OOM-Killer. Vorschlag: 2-4 GB Swapdatei, nur nach Jans Okay.
8. Lias Agenten-Netzwerk: Architektur in docs/lia-architektur.md (Abschnitt 3 und 7 = Fahrplan).
   Entschieden 21.10.: Ordner unter agent statt User lia; vorhandener Token bleibt (stand im Chat,
   /revoke optional); agentkit als Paket erst beim Umzug zu einem User lia. Konto (seit 27.10.): Lias Agenten
   laufen über dasselbe Konto wie Jans (siehe Stand, Verbrauch, heute Jans Login); Lias eigene
   claude.ai-Chats sind davon nicht berührt. docs/lia-architektur.md Abschnitt 0 beschreibt noch den alten Stand.
   Gebaut: Lias Zentrale und Platzhalter unterricht (siehe Stand).
   Offen:
   - Handtest: Lia tippt alle Knöpfe, schickt Freitext und einen Gruß, bekommt "kommt bald".
     Jan: /start, Agent uni antippen, Auftrag schreiben, Verbrauch/Status/Entwürfe ansehen.
   - Nächste Schritte: 1. Renderer: fertig (22.10.), Arbeitsblätter und Folien in Lias Stil, Nutzung und
     Stand in shared/renderer/STATUS.md.
     2. Lias Material-Agent: gebaut 22.10. in lia/unterricht (löst den Platzhalter für quelle portal-material ab,
     Woche/Frage weiter „kommt bald“), Opus, Ethik/Frau Pohlmann. Echter Lauf: Arbeitsblatt in 90 s, 2 Läufe,
     129.430 Tokens, umgerechnet 0,61 USD. Details lia/unterricht/STATUS.md. Offen: Handtest durch Lia.
     docs/uebergabe-lia-dokumente.md ist damit erledigt.
     Bedarf aus lia/unterricht (22.10., Hauptordner- bzw. Renderer-Chat):
     - portal_logik.ergebnis_text zeigt bei fehlgeschlagen nur FEHLGESCHLAGEN, das Ergebnis des Agenten
       (z. B. „Kontingent aufgebraucht, ab 14:00 noch einmal“) kommt bei Lia nicht an.
     - claude_lauf.GESCHUETZT schützt skills/**/SKILL.md nicht: Claude könnte den Skill eines Agenten mit Write
       ändern. Vorschlag: "skills/**" ergänzen. (23.10.) Ebenso lia/unterricht/leitfaden.md (von Jan freigegeben,
       geht in jeden Lauf): Vorschlag "leitfaden.md" ergänzen.
     - Renderer: Der Vorschau-Ordner behält Bilder eines früheren Baus (4. Seite blieb nach Neubau mit 3 Seiten
       liegen). ergebnis.bilder stimmt, nur der Ordner verwirrt.
     - Antwort auf ein Ergebnis in Lias Zentrale (Änderungswunsch in derselben Sitzung) fehlt noch.
     - (23.10.) Reihenkontext: lia/unterricht liest lia/unterricht/reihen.toml (Lias laufende Reihen) bei
       jedem Lauf. Heute pflegt Jan sie von Hand. Später ein Knopf „Meine Reihen“ in Lias Zentrale
       (ansehen, Reihe anlegen, Behandeltes nachtragen); erst bauen, wenn sich der Kontext bewährt.
     Chat-Aufteilung ein Chat pro Ordner, siehe CLAUDE.md (21.10.).
   - Werkzeug lia/auswertung (23.10., Chat in lia/): Auswertung von Lias claude.ai-Chats, von Hand gestartet,
     kein Dienst. Gerüst fertig, Plan und Stand in lia/auswertung/STATUS.md. Vorschlag an den Hauptordner-Chat:
     Ordner und Chat in README.md eintragen.
     Bedarf aus lia/auswertung (23.10.) an agentkit.claude_lauf: eine Art "guenstig" (Modell aus
     [modelle] guenstig = "haiku"), unabhängig von der Stufe. Heute gibt es Haiku nur in der Stufe sparen; für das
     Einordnen von rund 1.100 Runden reicht Haiku (ca. 0,10 USD statt 1–1,50 USD mit Sonnet).
     Außerdem wünschenswert: [werkzeuge] auswertung = ["Read"] in lia/instanz/einstellungen.toml (Claude soll dort
     nichts schreiben, die Antwort kommt als Text).
     Ergebnis lia/auswertung (23.10., Details lia/auswertung/STATUS.md, UNGEPRÜFT: Lias Prüfung auf Jans Wunsch
     ausgesetzt, der unterricht-Chat legt direkt los), Vorschläge an lia/unterricht:
     - Etwa drei Viertel von Lias Aufgaben gehören zu unterricht. Größter Hebel: Fachfragen mit Belegpflicht
       (Platzhalter „Frage stellen“ ablösen) und Material mit weniger Korrekturen.
     - Reihenkontext speichern (Reihenfrage, Klasse, behandelte Positionen, Merksätze) und jedem Lauf mitgeben:
       Ursache für 57 von 284 Korrekturen.
     - Änderungswünsche zu einem Ergebnis (unterricht offener Punkt 2) sind der Normalfall (Median 3 Runden).
     - Profil für Darstellendes Spiel ergänzen (Theatermaterial, Stücke zusammenfassen).
     - Prüfsatz für Schritt 8: lia/auswertung/data/ergebnis/pruefsatz.json (22 Aufträge, anonymisiert, nur lesen).
       Optional, später (Schritt 8, Blindvergleich): P01–P17 mit material.bearbeiten laufen lassen
       (ohne Warteschlange, Lia bekommt nichts), Auftrag aus auftrag + kontext ausformulieren, Textfassung je Ergebnis
       nach lia/unterricht/data/pruefung/P01.txt usw. Kosten vorher schätzen (Material ~0,60 USD je Auftrag mit Opus,
       17 Aufträge also ~10 USD Kontingent). Danach in lia/auswertung: auswertung.py vergleichsbogen <ordner>.
     - 11 Regelvorschläge in lia/auswertung/STATUS.md, warten auf Freigabe.
     - Bewertung (Bögen, Noten, Mitarbeit) wäre ein eigener Agent, erst nach Klärung Schülerdaten (lia-architektur Abschnitt 0).
   - Bedarf an lia/theater (30.10., Jan): theater braucht einen Dienst lia-theater, der Aufträge aus
     lia/instanz/auftraege/neu abarbeitet (wie lia-unterricht), sonst bleiben Lias Nachbesserungen liegen und gehen
     als „nicht eingerichtet“ an Jan. Wartet schon: 20261030-111155-theater-5d88d5 (Lia fragt, wie viele Minuten
     die Fassung dauert; Jan hat übernommen).
   - Bedarf aus lia/ (29.10., Jan, Renderer-Chat): Excel (.xlsx) als neue Art im Renderer, damit Lias Agenten
     Tabellen ausgeben können (Anlass: Lia wünscht vom Agenten eine Notentabelle). Nötig: Spalten, Kopf, Formeln,
     Eingabeprüfung (z. B. ganze Zahlen 0-15), Zahlenformat, Druck A4 quer. xlsxwriter steht schon in
     shared/renderer/requirements.txt. Vorschau: libreoffice-calc-nogui fehlt auf dem Server (nur Writer und
     Impress), Installation braucht sudo und Jans Okay. Danach lia/unterricht die Art freischalten.
     Übergangsweise hat der lia-Chat die Notentabelle einmal von Hand als leere Vorlage gebaut (ohne Schülerdaten,
     5 Noten 0-15 -> Schnitt 2/3, LEK 0-15 1/3 -> Endnote 0-15 mit zwei Nachkommastellen).
     Erledigt 29.10. im Renderer-Chat (Plan von Jan freigegeben): Art "arbeitsmappe" -> .xlsx, Format in
     shared/renderer/FORMAT.md (Beispiel = Lias Notentabelle), Stand in shared/renderer/STATUS.md. Jan prüft die
     Notentabelle noch in Excel. Bedarf an lia/unterricht (Art freischalten): material.ARTEN um
     "arbeitsmappe": ".xlsx" ergänzen (auch die Fehlermeldung in _beschreibung_lesen), dateiname passt
     ("Arbeitsmappe <Titel>.xlsx"); xlsxwriter ist in der .venv schon da (3.3.0); Skill einzelmaterial:
     Abschnitt „Art wählen“ (Tabelle, Notentabelle, Liste zum Ausfüllen -> arbeitsmappe) und die Regel „keine
     Namen, Noten oder anderen Schülerdaten in die Beschreibung, nur leere Vorlagen“; Kontrolle: Vorschaubilder
     kommen wie bei docx (Calc ist installiert), der Kontrolltext endet mit „Probe …“-Zeilen (in Python
     nachgerechnet), die Claude gegen den Auftrag prüfen soll; scheitert die Vorschau, kommen keine Bilder
     (prompt_kontrolle darf mit leerer Bilderliste nicht scheitern). SEITEN_ENDUNGEN unverändert. Ein Test mit
     einer arbeitsmappe-Beschreibung in tests/test_material.py.
   - Erledigt 21.10. für echte Läufe in Lias Instanz: ein Kontingent für alle Instanzen
     (config.KONTINGENT_DIR: einstellungen.toml, verbrauch/, Plätze in Jans shared; /verbrauch zeigt
     lia/<agent>), eigene Werkzeuge nur über [werkzeuge] in lia/instanz/einstellungen.toml, PERSON=Lia
     in lia/instanz/.env (Grundregel und Auftragstext), portal.py schickt Ergebnisdateien.
     Bisherige Notiz: echter Agent unterricht (Schritt 1, Material auf Zuruf). Vorher klären:
     Verbrauch und Plätze gemeinsam mit Jans Instanz (gleiches Konto), "Jan" in
     claude_lauf.GRUNDREGEL und in auftraege ("Angehängte Dateien von Jan") je Instanz.
   - Dateien in Lias Zentrale: gebaut 22.10. im Chat lia/unterricht mit Jans Okay (portal.py, portal_logik.py;
     Menü- und Hilfetexte für Material angepasst). Dateien und Fotos bis 20 MB warten in
     lia/instanz/zentrale/data/eingang/, bis Lia schreibt, was damit passieren soll (Bildunterschrift oder
     nächste Nachricht), und hängen dann am Material- oder Frage-Auftrag; Abbrechen/Verwerfen löscht sie.
     Sie sind Vorlage für genau diesen Auftrag (Jan, 22.10.). Dauerhafte Schulvorlagen (dotx/potx nach
     data/vorlagen/) noch offen. Handtest über Telegram offen. Hinweis: Die Änderung an portal_logik.py steckt
     versehentlich im Commit f848330 des Hauptordner-Chats (gleichzeitig committet), portal.py in 5e8d66b.
   - Bedarf aus dem Renderer-Chat (21.10., Jan hat zugestimmt): PDFs als Bilder für Claude. Claudes Read
     öffnet PDFs nur mit poppler (pdftoppm), das fehlt auf dem Server und braucht sudo. Darum läuft der
     Hinweis in agentkit.textfassung („Das PDF selbst mit Read öffnen“) bei Scans ins Leere. Vorschlag:
     agentkit wandelt PDF-Seiten mit pypdfium2 (pip, ohne sudo) in PNG-Bilder um, Claude öffnet die
     PNGs mit Read. Lia schickt PDFs als Vorlage, der Agent muss Text und Gestaltung sehen.
   - Server (21.10.): LibreOffice 24.2 ohne Oberfläche und die Schrift Carlito sind systemweit aus apt
     installiert (/usr/bin/soffice, für die Vorschau des Renderers). Jan kommt jetzt per SSH-Schlüssel
     contabo_agents auch als root auf den Server (über Contabo „Zugangsdaten zurücksetzen“, das löste einen
     Neustart aus; alle Dienste kamen von selbst wieder). Offen: 15 normale Updates, Ubuntu 26.04 nicht
     nebenbei einspielen. 29.10.: libreoffice-calc-nogui 24.2.7 ergänzt (Jan als root, für Excel im Renderer).
     Vom Windows-Rechner kommt Jan mit C:\Users\jan\.ssh\id_ed25519_contabo als root auf den Server.
   Vorbehalt Datenschutz: Mail- und IServ-Teil erst nach Klärung mit der Schule (Abschnitt 0).
9. Termine in Jans iCloud-Kalender SCHREIBEN (Bedarf uni, Plan von Jan 24.10.): agentkit-Teil erledigt 27.10.
   - `kalender.eintragen(titel, beginn, ende, *, agent, ort="", notiz="", uid=None, ganztags=False,
     erinnerungen=(), config=None) -> uid`. Nur neue Termine: CalDAV (principal -> calendar-home-set ->
     Kalender per Anzeigename, nur Kalender mit VEVENT) -> PUT <uid>.ics mit If-None-Match: *, ohne METHOD,
     Erinnerungen als VALARM. Notiz endet mit "angelegt vom Uni-Agenten" (aus agent). Ohne uid: feste_uid(titel,
     beginn) = sha1(titel|beginn.isoformat())[:16] + "@agenten" (gleiche Formel wie termine.uid in uni, das
     seine eigene uid mitgeben kann). Ganztags: ende = letzter Tag, einschließlich (wie uni).
   - Fehler: KalenderFehler (fehlende Werte in .env, Termin unplausibel, Kalendername passt auf keinen oder
     mehrere, Anmeldung abgelehnt, Netz, HTTP-Fehler); TerminSchonDa (Unterklasse) bei HTTP 412 = UID steht
     schon im Kalender, nichts überschrieben. Zugangsdaten gehen nur per https an *.icloud.com, jede
     Weiterleitung geprüft.
   - `kalender.ics(titel, beginn, ende, uid, ort, beschreibung, ganztags, erinnerungen, link, methode, jetzt)`:
     inhaltsgleich mit uni/termine.ics (PRODID agentkit). methode=None für CalDAV.
   - Geprüft: Unit-Tests mit nachgebautem Server; echte Anfrage an caldav.icloud.com mit falschem Zugang
     ergibt die erwartete Ablehnung (Netzweg ok). Noch kein echter Termin eingetragen.
   - Offen Jan: in shared/.env eintragen ICLOUD_APPLE_ID, ICLOUD_APP_PASSWORT (App-spezifisches Passwort,
     appleid.apple.com) und ICLOUD_KALENDER (Anzeigename des Hauptkalenders). Danach einmal echt testen
     (Testtermin, dann von Hand löschen).
   - Offen uni-Chat: Entwurfstyp "termin" (Freigabe, dann kalender.eintragen in ausfuehren(), TerminSchonDa
     als "stand schon im Kalender" melden); termine.ics/_falten auf agentkit.kalender umstellen und die eigene
     Kopie löschen. Die Zentrale zeigt typ "termin" als "Termin-Entwurf".
10. Bedarf aus lia/examen (25.10., Plan Examensreihe von Jan freigegeben, Punkte 1–6, Prüfung in ca. 4 Wochen):
   - Lias Zentrale: Bewertungsbogen je Runde ENTFÄLLT (Jan/Lia 27.10., Auftrag „Neuausrichtung der Recherche“):
     Lia liest Ergebnisse und spricht ihr Feedback als Text ein (bis auf Weiteres über Jan).
   - Erledigt 25.10. (Teil A lia/recherche): agentkit.abruf, nur Bordmittel (urllib). Allowlist von Jan
     freigegeben: gesetze-im-internet.de, de.wikisource.org, zeno.org, korpora.org, archive.org (gibt der Aufrufer an).
     `abruf.laden(url, allowlist, cache_dir, neu=False, zeitlimit=60, max_bytes=30 MB)` -> Ergebnis mit
     inhalt (bytes), meta (url, endgueltige_url, abgerufen, status, content_type, sha256, groesse), aus_cache,
     text(). Erlaubt: Host gleich Domain oder endet auf ".domain"; nur https; jede Weiterleitung geprüft;
     2 s Pause je Host (im Prozess). Cache <sha256 der URL>.bin/.json, Treffer ohne Netz, neu=True lädt neu.
     Zeichensatz aus Content-Type (auch "charset=Charset=ISO-8859-1"), sonst UTF-8: abruf.als_text(bytes, ct).
     Fehler: AbrufFehler (Domain nicht erlaubt, Weiterleitung abgelehnt, nur https, HTTP-Fehler, zu groß,
     Zeitüberschreitung, Netzfehler, Zeichensatz, Cache beschädigt). Nur Unit-Tests, noch kein echter Abruf.
   - Erledigt 25.10.: agentkit.wortlaut (normalisieren, steht_in, seiten), inhaltsgleich mit lia/examen/wortlaut.py.
     Offen im lia-Chat: lia/examen auf agentkit.wortlaut umstellen, dann lia/examen/wortlaut.py löschen.
   - Erledigt 25.10. (Plan „Webrecherche“, Teil A): WebFetch je Agent nur auf freigegebene Domains.
     shared/einstellungen.toml: [werkzeuge] recherche (mit WebSearch, WebFetch) und [webfetch] recherche = Jans Liste
     (19 Domains). Lias Instanz hat keine eigene einstellungen.toml und erbt beides; eine Instanzdatei darf
     [webfetch] ebenfalls setzen. einstellungen.webfetch_domains(cfg, agent) -> Liste oder None (nur reine
     Domainnamen, sonst ValueError), dieselbe Liste dient als Allowlist für abruf.laden.
     claude_lauf: Mit Liste wird WebFetch nur als WebFetch(domain:d) und WebFetch(domain:*.d) erlaubt, ohne Liste
     (uni, einkauf) unverändert. Echte Läufe 25.10. (claude 2.1.304, haiku, Stufe sparen, zusammen 0,004 USD):
     www.gesetze-im-internet.de und korpora.org ok; example.com, evilarchive.org, archive.org.example.com
     abgelehnt (permission_denials). www.bpb.de war erlaubt, der Server brach aber ab (ECONNRESET).
     abruf.html_zu_text(html) bzw. Ergebnis.text_ohne_html(): reiner Text ohne script/style/noscript/svg, eine
     Zeile je Block, oben Titel, og:title, og:description, description (doppelte nur einmal).
   - Freigabe-Einträge ohne Ausführung durch einen Agenten (Typ "entwurf", Lia setzt selbst ein): Nach der
     Freigabe bleiben sie in „Warten auf Ausführung“. Vorschlag: Typ "entwurf" in der Zentrale nach Freigabe
     direkt als ausgeführt vermerken („setzt Lia selbst ein“). Bis dahin schließt der examen-Chat sie von Hand ab.
11. Erledigt 25.10.: Status "allowed_warning" sperrte alle Läufe (verbrauch.stufe und Prüfung am Ende von
   claude_lauf.laufen werteten jeden Status außer "allowed" als Limit). Jetzt verbrauch.gesperrt(status):
   None, "allowed" und "allowed_warning" sind frei, die Stufen sparen/nur_auftraege kommen aus 5h/7d. Mit Tests.
12. Sicherung (Jan 27.10.2026, Plan freigegeben): Repo gespiegelt nach privatem GitHub-Repo
   k5nwrvzgnv-ship-it/agenten (Remote „sicherung“, main verfolgt sicherung/main). Zugang nur über Deploy-Key
   ~/.ssh/github_sicherung (Host-Alias github-sicherung in ~/.ssh/config, Schreibrecht nur auf dieses Repo).
   Erster Push 27.10. (Stand 89be3a1). data/ und .env sind nicht im Repo und damit nicht auf GitHub.
   Nächtlicher Push (Jan 27.10.): shared/sicherung/sicherung.py (push main, danach Abgleich per ls-remote;
   bei Fehler Meldung an Jan, Agent „sicherung“), Dienst sicherung.service + sicherung.timer (03:30,
   Persistent), Vorlagen in shared/sicherung/systemd/, eingerichtet und einmal von Hand erfolgreich gelaufen
   (27.10. 09:34, Stand b49bbb2). Log: shared/sicherung/logs/. Fehlerweg nur mit Tests geprüft, nicht echt.
   Offen: Sicherung von Lias Daten (data/, ca. 330 MB, persönlich, nicht auf GitHub) per rsync auf Jans Mac
   (Entscheidung Jan).
   Achtung: Weil main jetzt sicherung/main verfolgt, schiebt ein einfaches `git push` nach GitHub. Chats pushen
   weiter nur auf Jans Anweisung.
13. Erledigt 27.10.: Agenten laufen über ein eigenes Claude-Konto (siehe Stand, Verbrauch). Testlauf als Agent
   „kontotest“ im Verbrauchsprotokoll (Haiku, 0,0007 USD); er hat den alten Stand von Jans Konto (7d 94 %,
   Stufe nur_auftraege) überschrieben, Stufe jetzt normal.

14. Feedbackschleife, offen:
   - Fortschritt per bearbeiteter Nachricht (z. B. auftraege.fortschritt(id, text), Zentralen bearbeiten eine
     Statusnachricht) noch nicht gebaut; die Agenten müssten Zwischenstände melden.
   - Grenze: Der Commit des Dienstes nimmt die ganze Datei mit, also auch unfertige Änderungen eines Chats an
     derselben STATUS.md. Ist pruefen.sh rot, bleibt die Zeile uncommittet und Jan bekommt eine Meldung.
   - Stopp einer Nachbesserung greift nur, solange der Agent sie noch nicht bearbeitet; sonst scheitert sein
     abschliessen (Log), und das Ergebnis ist schon zugestellt.
   - Bedarf an Agenten: recherche und unterricht (in deren STATUS.md). uni setzt Nachbesserungen schon in der
     Sitzung fort (bezug, sitzung); daten.kern ist für alle Agenten optional.
   - lia/recherche/faelle.py und lia/examen lesen Lias Regeln nur aus lia/unterricht/STATUS.md; Regeln aus Feedback
     in lia/instanz/regeln.md oder einer anderen STATUS.md erreichen sie nur über claude_lauf (Systemprompt).

15. Bedarf aus lia/recherche (27.10.): agentkit.abruf.laden scheitert an URLs mit Umlauten im Pfad (z. B.
   de.wikipedia.org/wiki/Antonio_Rüdiger) mit UnicodeEncodeError statt AbrufFehler; das beendete einen bezahlten
   Lauf. In lia/recherche umgangen (webauftrag.adresse kodiert die URL, faelle.belege_pruefen fängt den Fehler).
   Vorschlag: abruf.laden kodiert Pfad und Query selbst (IRI -> URI) und meldet alles andere als AbrufFehler.
   Zweiter Bedarf erledigt 27.10.: daten.knoepfe = "nur_antwort" (vorlagen.NUR_ANTWORT) wählt die Feedback-Knöpfe
   je Ergebnis ab. Lia sieht nur „Menü“, ihre Antwort bleibt Feedback; Jan sieht keine Knöpfe, seine Antwort setzt
   das Gespräch fort. Beide Zentralen damit neu gestartet. lia/recherche kann das Dossier (fallsuche --an-lia)
   jetzt an Lia schicken; noch nicht echt über Telegram geprüft.

16. Sprache der Zentralen (Jan 27.10.: Nachrichten für Laien, Technik bleibt im Backend, keine neuen Funktionen).
   Erledigt: 1 Inventur docs/sprache/inventur.md; 2 Sprachregel docs/sprache/sprachregel.md (angenommen 27.10., alle
   5 Punkte wie vorgeschlagen); 3 agentkit.sprache (Jargon-Prüfer, 1. Wiener Sachtextformel, Grenzen je Person) mit
   Tests; Snapshots aller Nachrichtenarten, die schon reine Funktionen sind (shared/telegram/tests/test_nachrichten.py,
   lia_* / jan_*), geprüft in test_sprache_snapshots.py; Laufzeitprüfung in beiden Zentralen (sprachpruefung.py als
   rate_limiter, Warnung „Sprache <Endpunkt> (<Absender>): …“ ohne Inhalt im Log), Ausfallmeldung ins Journal.
   Schritt 4 (umschreiben) weitgehend erledigt: Lias Zentrale (Menü, Hilfe, Hinweise, Ergebniskopf), Jans Zentrale
   (Menü, Hilfe, Status, Verbrauch, Freigabe, Fehler; Texte aus zentrale.py jetzt in logik.py mit Snapshots) und
   Feedback (agentkit.feedback, feedback/lauf.py): Jans Zusammenfassung kommt von „Zentrale“ (logik.SYSTEM), ohne
   Pfade und „Art:“, Ablageort steht nur im Log des Feedback-Dienstes; Gründe für Vorschläge in Alltagsworten.
   Beide Zentralen am 27.10. 17:40 mit allen Änderungen neu gestartet; noch keine echte Nachricht seitdem geprüft.
   Altlasten: shared/telegram/tests/sprache_altlasten.json (noch 7 Befunde in 3 Snapshots) darf nur kürzer werden
   (SPRACHE_ALTLASTEN_KUERZEN=1 streicht Behobenes). Nachweis = Datei leer, dann löschen. Rest: jan_fehler_mit_grund
   (Fehlertext und Pfad, die der Agent selbst ins Ergebnis schreibt), lia_fehler („Kontingent“ im Ergebnistext von
   unterricht), lia_recherche (langer Satz im Kern von recherche). Alle drei kommen aus den Agenten, nicht aus der
   Zentrale: gehören zum Ergebnistext-Vertrag.
   Offen: Ergebnistext-Vertrag in agentkit, Bedarf an die Agenten in deren STATUS.md; 5 Handy-Bilder vorher/nachher
   (380 px); danach eine Woche Auswertung (Treffer im Log, Passt/Zu lang/Falscher Fokus, Rückfragen, Wünsche).
17. Bedarf aus uni (27.10.): Nach dem Wechsel [konto] quelle auf "login" sperrt claude_lauf weiter bis 20:10.
   Grund: verbrauch.letzter_stand nimmt die letzte Auslastung aus laeufe.jsonl egal von welchem Konto; letzter
   Eintrag ist der abgewiesene uni-Lauf 17:15 auf dem Agenten-Konto (status rejected, 5h 1,02). Der Haiku-Test
   über den Login steht nicht im Protokoll. Vorschlag: Einträge mit Feld "konto" (quelle) schreiben und
   letzter_stand nur Einträge des eingestellten Kontos lesen lassen (alte ohne Feld = "token").
18. Bedarf aus posteingang (27.10.): agentkit.imap.zerlege soll zusätzlich "kopf" liefern, ein dict mit
   klein geschriebenen Namen: list-unsubscribe, list-id, precedence, auto-submitted, x-spam-flag (fehlende
   weglassen). posteingang/vorfilter.py liest daraus Newsletter, Massenmails und Spam. Ohne "kopf" prüft der
   Vorfilter nur gesperrte Absender. uni ist nicht betroffen (zusätzliches Feld).
19. Erledigt 27.10.: imap.suchen und mail wie unten beschrieben, Tests in agentkit/tests (test_imap,
   test_mail). Lesender Echttest von imap.suchen gegen jan@kleinke.org: INBOX/Sent/Archive, seit, zwei
   Umlaut-Kriterien zugleich (LITERAL+), unbekannter Ordner -> leere Liste. Senden nicht echt getestet (macht
   posteingang nach Jans Freigabe). Abweichung: ohne GESENDET_ORDNER keine Kopie in Gesendet (steht im Ergebnis).
   "an" in zerlege ist eine Liste. uni-Umstellung als Bedarf in uni/STATUS.md eingetragen.
   Ursprünglicher Bedarf aus posteingang (27.10., Plan Mail-Aufträge von Jan freigegeben): Jan gibt per /posteingang einen
   Auftrag ("Termin bei Frau X absagen"), posteingang sucht Kontext und Schreibstil im Postfach und legt einen
   Mail-Entwurf in die Freigabe, nach Freigabe Senden von jan@kleinke.org. posteingang-Teil wird gegen diese
   Schnittstellen gebaut (Funktionen werden übergeben, Tests ohne agentkit-Teil):
   a) agentkit.imap.suchen(host, port, nutzer, kennwort, ordner, *, von=None, an=None, text=None, seit=None,
      max_mails=20) -> list[dict]: nur lesend (readonly, BODY.PEEK) wie neue_mails, ohne Stand-Datei, neueste
      zuerst, jede Mail wie zerlege plus Feld "ordner". Kriterien per UND (IMAP SEARCH FROM/TO/TEXT/SINCE),
      Umlaute per CHARSET UTF-8. Ordner, den es nicht gibt: leere Liste und Log, kein Fehler.
      Dazu in zerlege das Feld "an" (To und Cc), damit gesendete Mails ihren Empfänger zeigen.
   b) agentkit.mail aus uni/mail.py verallgemeinert: pruefen(entwurf, original=None) (Original als dict statt
      UID-Ablage, weil UIDs je Ordner doppelt sind), anzeige, wortlaut, bauen, senden(cfg, daten) mit
      SMTP_SSL bei SMTP_PORT 465, sonst STARTTLS; Login aus MAIL_NUTZER/MAIL_KENNWORT (Standard IMAP_NUTZER/
      IMAP_KENNWORT), Kopie in GESENDET_ORDNER. uni stellt danach darauf um (uni-Chat).
20. Erledigt 28.10. (Bedarf aus uni, Plan von Jan freigegeben: Mail-Ablauf von posteingang auch für uni):
   a) agentkit.imap.suchen geht jetzt auch am HNEE-Exchange. Antwortet der Server auf SEARCH CHARSET UTF-8
      mit [BADCHARSET], wird ohne CHARSET erneut gesucht, Umlaute umgeschrieben (umschreiben: ö -> oe,
      ß -> ss, Akzente weg). an= geht dort nicht an den Server (TO findet nichts, TEXT nur den Mailtext,
      UID 739 an Böhme fehlte damit): Python holt To/Cc der übrigen Treffer in Blöcken
      (BODY.PEEK[HEADER.FIELDS (TO CC)], höchstens MAX_PRUEFEN = 1000 neueste) und vergleicht als Teilstring
      (Groß-/Kleinschreibung und Umlaute egal). Andere Ablehnung von SEARCH: imaplib.IMAP4.error statt
      ValueError. Server mit CHARSET (jan@kleinke.org) unverändert. Lesender Echttest 28.10.: HNEE "Gesendete
      Elemente" an="Boehme" und an="Böhme" je 45 Mails (mit UID 739; TEXT "Boehme" allein fand nur 17),
      INBOX von="Böhme" 20; kleinke.org INBOX text="für" und Sent an= gehen weiter.
   b) agentkit.mailauftrag = allgemeiner Teil von posteingang/auftrag.py, Tests in test_mailauftrag:
      Postfach(agent, beschreibung, eingang, gesendet, max_tage_zurueck, unterschrift) – Standard STANDARD
      = posteingang (jan@kleinke.org, INBOX/Archive, Sent, 730 Tage, Unterschrift wie in Jans Mails).
      prompt_suche(text, heute, postfach), suche_lesen(antwort, postfach), kontext_sammeln(suche, suchen,
      termine, heute, postfach) (termine=None: ohne Kalender), kontext_als_text(kontext),
      prompt_entwurf(text, kontext, heute, postfach), prompt_aendern(kommentar, alt, text, kontext, heute,
      postfach), antwort_lesen(antwort, kontext) -> ("entwurf", roh, original) | ("rueckfrage", text, None);
      Fehler: AuftragFehler. Ist unterschrift gesetzt, verlangt der Prompt sie wörtlich.
      Umstellung von posteingang als Bedarf in posteingang/STATUS.md, Aufruf für uni in uni/STATUS.md (Punkt 9).
      Hinweis: CLAUDE.md (Architektur, agentkit-Liste) nennt mailauftrag und mail noch nicht.

21. Freigabe-Ansicht neu (28.10., Jan: "überladen"; Entscheidungen Jan 28.10.: nichts Ausklappbares, also
   weder Begründung noch technische Kopfzeilen in Telegram; Ergebnisse, die nur auf einen Entwurf verweisen,
   kommen nicht). Gebaut in shared/telegram/logik.py: entwurf_als_text = Gerüst für alle Typen: Kopf (Mail:
   **An Name** (Adresse), Betreff wie gesendet, kursiver Bezug "Antwort auf die Mail [von X] vom TT.MM.JJJJ",
   Präfix-Wurm zusammengefasst über betreff_kurz), Inhalt im blockquote, "Bitte prüfen:" fett sichtbar.
   Begründung, In-Reply-To und References stehen weiter im Entwurf (inhalt, daten). Mails werden aus daten gezeigt (genau das geht raus), andere
   Typen aus inhalt plus Feldern, die dort nicht wörtlich stehen. html_aufteilen schließt offene Tags am
   Schnitt und öffnet sie neu, nichts geht verloren. Knöpfe Freigeben / Ändern / Ablehnen, ohne Link-Vorschau.
   nur_freigabe_verweis: Ergebnis "Entwurf an ... liegt zur Freigabe" (oder daten.nur_freigabe) wird nicht
   gesendet, Feedback läuft über Ändern/Ablehnen. agentkit.mail.pruefen nimmt optional "pruefen" (Prüffrage
   an Jan, bis 500 Zeichen) und legt antwort_auf_von/antwort_auf_datum für die Anzeige ab. Fehlt "pruefen",
   zieht die Ansicht einen Satz "Bitte prüf..." aus der Begründung.
   Offen (Bedarf):
   - mailauftrag (anderer Chat, noch uncommittet), posteingang, uni: Im Entwurfs-Prompt das Feld "pruefen"
     anbieten ("eine offene Frage an Jan, sonst weglassen"; nicht "rueckfrage", das ist schon die Rückfrage
     statt Entwurf) und in antwort_lesen durchreichen.
   - posteingang/agent.py entwurf_einreichen und uni/agent.py: beim Ändern zusätzlich antwort_auf_von und
     antwort_auf_datum vom Vorgänger übernehmen (sonst fehlen Name und Datum in der Bezugszeile).
   - posteingang und uni: bei reinen Entwurfs-Ergebnissen daten.nur_freigabe = True setzen, statt sich auf
     den Text "liegt zur Freigabe" zu verlassen.

22. Leitstand (Frontend zur Steuerung, Plan 28.10.): docs/leitstand-plan.md mit Eingriffspunkten, Ereignis-Schema,
   Schnittstelle, Variantenvergleich (Empfehlung: eigenes Dashboard, Python-Bordmittel, nur per SSH-Tunnel) und
   Messgrößen. Klickbarer Entwurf: https://claude.ai/artifact/6DVm6MiPQHtjiMbjb6buzT.
   Stufe 1 gebaut 28.10. (Plan von Jan freigegeben):
   - agentkit.ereignis: KONTINGENT_DIR/ereignisse/<JJJJ-MM-TT>.jsonl, nur anhängen, id = "<tag>:<byte>", lesen(seit=),
     aufraeumen(30 Tage). Nur IDs, Arten, Zahlen, Werkzeugnamen; Texte in daten auf 100 Zeichen gekürzt; schreiben()
     wirft nie. AGENTKIT_EREIGNIS_DIR lenkt um (pruefen.sh setzt einen Temp-Ordner, Tests schreiben nie echt).
   - claude_lauf.laufen: Popen in eigener Prozessgruppe, Ausgabe zeilenweise, Zeitlimit beendet auch Kindprozesse
     (Vorbereitung Abbruch Stufe 2). Ereignisse lauf.gestartet (mit pid), werkzeug (live), lauf.beendet, lauf.fehler
     (limit, pausiert, zeit, laeuft_schon, kein_platz, konto, technik). Ergebnis.lauf = Lauf-ID. Echter Haiku-Lauf
     28.10.: ok, 0,0009 USD, Ereignisse wie erwartet.
   - auftraege/freigabe: auftrag.angelegt/.abgeschlossen, freigabe.wartet/.entschieden/.ausfuehrung_begonnen/
     .ausgefuehrt. Mit eigener basis (Tests) unter <basis>/ereignisse.
   - shared/leitstand/: logik.py (getestet), server.py (nur GET, Unix-Socket data/leitstand.sock, Ordner 700),
     index.html (Netz, Läufe, fragt alle 2 s nach neuen Ereignissen, Stand im Adress-Anker, übersteht Neuladen).
     Lias Läufe ohne Auftrags- und Ergebnistext. Von Hand gegen echte Daten geprüft (Scratch-Socket), Dienste und
     offene Freigaben stimmten. Dienst leitstand eingerichtet 28.10. 22:56 (Jans Okay, enable --now, Vorlage
     systemd/leitstand.service, OnFailure=ausfall@, MemoryMax 150M). Beide Zentralen zugleich neu gestartet
     (schreiben jetzt auftrag.angelegt; Panel erst wieder nach /start).
   Zugriff vom Mac: ssh -N -L 8790:/home/agent/agenten/shared/leitstand/data/leitstand.sock agent@<server>, dann
   http://localhost:8790. Noch nicht von Jan im Browser geprüft.
   Offen:
   - Bedarf an alle Agenten: auftrag_id an claude_lauf.laufen mitgeben (heute u. a. uni/karten, recherche, examen,
     unterricht/leitfaden nicht), sonst „Lauf ohne Auftrag“. Die Agent-Chats übernehmen das aus diesem Punkt.
   - Stufe 2 (Freigabe, Abbruch), Stufe 3 (Einstellungen) laut Plan, je nach Okay.
23. Bedarf aus der Leitstand-Prüfung gegen echte Nutzung (lia-Chat, 28.10.2026, Rohdaten 16.–28.10.). Prototyp mit
   geschwärzten Daten und allen Tabellen (Eingriffe, Aufgaben Jan/Lia, Zielwerte, Aufgabentest) nur im Scratchpad
   dieses Chats (/tmp/claude-1002/-home-agent-agenten-lia/91021f8b-bf4d-4aa2-b56c-5ff60187dab6/scratchpad/proto/,
   flüchtig); bei Bedarf nach docs/ übernehmen. Nichts davon ist gebaut.
   - Sicherheit, vor Stufe 2: Überholte Entwürfe bleiben in freigabe/offen freigebbar. Am 28.10. lagen zwei: der
     Böhme-Entwurf vom 27.10. (anderer Inhalt, kein vorgaenger-Link zur Fassung vom 28.10.) und die alte
     Absage an die Beratung (die Nachbesserung ging schon raus). Vorschlag: freigabe.entscheide lehnt "freigegeben"
     ab, wenn es im selben Strang (Agent, Empfänger, Betreff ohne Re/AW) einen jüngeren Entwurf gibt;
     neuer_entwurf mit vorgaenger zieht den Vorgänger zurück. Gilt dann für Telegram und Leitstand.
   - Fehlklick am Handy: Feld "nicht vor" (z. B. 10 s nach Freigabe), damit Rückgängig möglich ist, bevor
     ausfuehrung_beginnen greift.
   - Ereignisse: auftrag.angelegt landet in shared/auftraege/ereignisse/ (nicht in Git, nicht in .gitignore) statt
     in shared/ereignisse/. Vermutung: die Zentrale übergibt basis, und auftraege schreibt dann unter
     <basis>/ereignisse. Nicht geprüft.
   - Feedback-Tests schreiben ins echte shared/feedback/logs/feedback.log (2531 Zeilen, fast alles Tests).
   - laeufe.jsonl: kein Fehlerfeld (3 recherche-Läufe am 27.10. nach ca. 540 s ok = false ohne Ursache), Konto
     nur beim Vinted-Bot. Für Messungen beides mitschreiben.
   - Lias Entwurf examen-0c44bf ("Lia setzt selbst ein") offen seit 25.10.; Lia braucht einen Weg, ihn
     abzuschließen. Zugang Lias zu einer Web-Ansicht ist offen (SSH-Tunnel nicht zumutbar), Entscheidung Jan.
   - Zur Messung der Handeingriffe fehlen Zeitstempel in der Bash-History (HISTTIMEFORMAT in ~/.bashrc, nur mit
     Jans Okay).

24. Web-App für Lia und weitere Lehrerinnen (Entwurf 29.10.2026, gebaut ab 30.10., neuer Aufbau Bauschritt 1 30.10.): docs/webapp-plan.md, Prototyp
   docs/webapp-prototyp.html (Beispieldaten, Seitenvorschau mit Anmerkungen, Feedback mit Geltungsbereich, Vorlagen,
   Testleitung für 7 Aufgaben), privat veröffentlicht unter
   https://claude.ai/artifact/JMoaDZKoS59tpG35fbxZDs (für Lia erst nach „Teilen“ durch Jan).
   - Befund: Lia hat über Telegram in 8 Tagen 1 Auftrag geschickt (wegen Kontingent fehlgeschlagen), kein Feedback;
     fast alles läuft mündlich über Jan. portal.py kennt keine Freigaben (examen-0c44bf offen seit 25.10.).
   - Entschieden (Jan 30.10.): Die Web-App wird für Lia nutzbar gemacht, Gestaltung „Modernist“ (Boards
     ModHeute/ModNeu/ModErgebnis im Canvas https://claude.ai/artifact/F8ysVSyr8TjGhFDcyNnejU). Adresse
     lia.meldro.de (Subdomain, nichts zu kaufen; neutrale Domain erst mit einer zweiten Lehrerin). Gebaut wird in
     shared/webapp/ vom Hauptordner-Chat.
   - Auftrag an den Hauptordner-Chat (aus dem lia/-Chat, 30.10.): Lia braucht einen Überblick, was gerade läuft.
     Nur echte Daten aus lia/instanz, keine Beispielinhalte. Erste Stufe:
     1. Heute: wartet auf Lia (offene Entwürfe, neue Ergebnisse), läuft gerade (auftraege/neu), fertig und
        fehlgeschlagen (auftraege/erledigt), Begriffe aus Lias Sicht, keine Agentennamen und IDs.
     2. Ergebnis: Kern bzw. Antworttext, Seitenvorschau aus dem Renderer (`<stem>-vorschau/`), Downloads der
        ergebnis_dateien (PDF, Word, PowerPoint, Excel), Pfade gegen den Agent-Ordner geprüft.
     3. Feedback-Knöpfe wie in Telegram, über agentkit.feedback, mit Rückmeldung, was daraus wurde.
     4. Entwurf: Setze ich selbst ein / Ändern / Ablehnen (für examen-0c44bf, Typ entwurf).
     5. Neuer Auftrag nur für Arten, die laufen: Material (unterricht, auch Arbeitsmappe), Theater.
     Weggelassen, weil es das noch nicht gibt: Mail-Entwürfe, „Text prüfen“, Frage und Woche (Platzhalter in
     unterricht), Fortschrittsbalken, Anmerkung an einer Stelle, Reihen und Vorlagen pflegen. Telegram bleibt
     für Hinweise.
   - Pakete freigegeben (Jan 30.10.): fastapi, uvicorn, jinja2, python-multipart, webauthn, htmx-Datei, nur in
     shared/webapp/.venv und dessen requirements.txt. Anmeldung per Passkey mit Einladungslink.
   - Offen, Jan als root: DNS lia.meldro.de bei INWX (A/AAAA wie
     kcal) und zweiter Caddy-Block (Vorschlag in docs/webapp-plan.md 1.3), kcal-Block danach prüfen. Klärungen
     K1 (Schule/Datenschutz) und K3 (Abo oder API) sind nicht erledigt; Jan entscheidet, ob Lia vorher startet.
     Bis dahin läuft die App lokal (Unix-Socket wie der Leitstand). Bauplan in Abschnitt 7 des Plans.
   - Stand 30.10.: Bauschritt 1 fertig (shared/webapp/, eigene STATUS.md): Seite „Heute“ nur lesend aus
     lia/instanz (wartet auf Lia, läuft, fertig, hat nicht geklappt), Unix-Socket data/webapp.sock, Zugriff per
     SSH-Tunnel, von Hand gestartet, kein Dienst, keine Anmeldung. Echter Lauf zeigt die 7 Aufträge und
     examen-0c44bf. Dazu (Jan 30.10. vorgezogen): Ergebnis- und Entwurf-Ansicht nur lesend, per Klick aus
     „Heute“ (Punkte 2 und 4 oben ohne Knöpfe): Kern, Punkte, Bitte prüfen, Seitenvorschau, Downloads mit
     Pfadprüfung, Grund bei Fehlschlag; Entwurf ganz mit Einsatz. Nach Jans Anmerkung 30.10.: Auftrag mit
     Feedback-Schleife ist ein Auftrag (Kette über bezug), eine Zeile in „Heute“, Ergebnis mit neuester Fassung
     und Verlauf (Fassungen, Lias Rückmeldungen). „Neuer Auftrag“ (Jans Okay 30.10.): nur Material, gebaut,
     standardmäßig aus, im Testbetrieb gegen shared/webapp/data/test/instanz (kein Agentenstart), Schutz über
     Origin und Token. Echt auf lia/instanz erst mit Bauschritt 2 und Jans Okay (Ergebnisse gingen auch per
     Telegram an Lia). Theater erst, wenn lia/theater neue Aufträge annimmt (bisher nur Nachbesserungen).
     agentkit.auftraege.neuer_auftrag hat dafür den Parameter absender. Nächster Schritt: Bauschritt 2 (Konten,
     Einladung, Passkey).
     Dienst webapp.service: Okay Jan.
   - Ordnung nach Fach, Klasse und Reihe (Jans Okay 30.10.): Zuordnung nur über das optionale Feld reihe in
     agentkit.auftraege.neuer_auftrag oder den Agenten (theater -> Darstellendes Spiel Kurs 12 „Der nackte
     Wahnsinn“, examen -> Ethik 8 Straftheorien), sonst ohne Reihe. Auswahl der Reihe beim Neuen Auftrag
     (Testbetrieb). Reihen pflegt vorerst Jan; Lia pflegt sie selbst, sobald gebaut, auch ohne Konten (Jan 03.11.).
   - Bedarf an den lia/unterricht-Chat (Jan 30.10.): EINE Datei lia/instanz/reihen.toml für App und Agenten. Bitte
     lia/unterricht/reihen.toml dorthin verschieben, reihen.py und lia/examen (titel_in_reihen_toml) umstellen,
     Felder id, stand (laufend/abgeschlossen) und agenten erlauben und den Kurs eintragen (fach „Darstellendes
     Spiel“, klasse „Kurs 12“, titel „Der nackte Wahnsinn“, agenten ["theater"]); Format in
     shared/webapp/ordnung.py. Bis dahin setzt die App die Reihen aus unterricht/examen/theater zusammen.
     Später: Feld reihe des Auftrags bevorzugt nutzen, statt selbst eine Reihe zu wählen (heute steht sie als
     Zeile „Reihe: …“ am Ende des Auftragstexts).
   - Neuer Aufbau Desktop zuerst (Plan docs/webapp-aufbau.md, Boards „Desktop“ und „Handy-Prüfung“ im Canvas;
     Lias Test 30.10.: gefällt, Ebene Stunde gewünscht). Geklärt (Jan 30.10.): Fach „Darstellendes Spiel“,
     Stück gehört zu Kurs 12, Notentabelle zu Ethik 8, Lia nutzt Word, Pages/Keynote und eine Schulplattform.
     Stand 30.10.: Bauschritt 1 gebaut (Jans Okay 30.10.): drei Spalten Baum | Inhalt mit Brotkrumen | „Fragen“
     (nur Platzhalter „Kommt bald“), Baum aus den Reihen (Heute mit Zahl, je Fach Klassen/Kurse und Reihen),
     Reihen-Ansicht /reihe/<kennung> (nur lesend), „Heute“ ohne Chips mit Ort je Zeile, /unterricht leitet auf /
     um. Fach und Kurs im Code umgestellt. Ergebnis, Entwurf, Neuer Auftrag unverändert im Rahmen.
     Seitengalerie (Jans Wunsch 30.10.): je Dokument eine Karte mit kleiner erster Seite, Klick öffnet einen
     Seiten-Betrachter mit Vor/Zurück (ohne JavaScript), auch im Verlauf. Fehlende Optionen am Dokument (Feedback-
     Knöpfe, final, eigene Fassung, Rückmeldung mit Datei, Nochmal, Entwurf-Knöpfe) als Liste an Jan; er legt die
     Reihenfolge fest (shared/webapp/STATUS.md, Offene Punkte 4). Jan 30.10.: Material-Ansicht genau wie das Board
     „Desktop“ ausprobieren: gebaut (Knopf-Spalte, Fassungen-Liste, final, eigene Fassung, Rückmeldung). Final und
     eigene Fassungen speichert die Web-App vorerst selbst in shared/webapp/data/ (nicht in Lias Instanz, Agenten
     sehen sie nicht: Bedarf b und d bleiben); Rückmeldung nur im Testbetrieb, echt erst mit Jans Okay.
     Board komplett (Jan 30.10. abends: „alle Funktionen aus dem Board zum Laufen bekommen“, Plan
     shared/webapp/board-plan.md, Chats lia/unterricht, lia/theater, lia/chat, Hauptordner): In der Web-App gebaut
     und committet: Klasse, Fach, Reihe mit Material-Stand, Stunden (aus reihen.toml oder in der App), Archiv
     (schuljahr), Galerie (Arbeitsblatt, Präsentation, Tabelle, Reihenentwurf, LEK; Spielfassung, Szenenaufgabe)
     mit Ort, Auch als (einfach, Hilfekarten, Level) im selben Lauf, Varianten nachträglich, Rückmeldung je
     Datei/Seite, final und eigene Fassung über agentkit.fassungen, Entwurf selbst einsetzen, Nochmal,
     Zurückziehen, Vorlagen und Ich (lesend), Spalte „Fragen“ an lia/chat (nur mit WEBAPP_CHAT=an). Einzelheiten
     shared/webapp/STATUS.md „Board komplett“. Jan 30.10.: „Ja, echt“ und „Weg 2“: Dienst webapp.service läuft (127.0.0.1:8791, echt auf
     lia/instanz, Fragen an); für Lia https://lia.meldro.de mit Passwort über Caddy, eingerichtet und von außen geprüft
     30.10. abends (401 ohne, 200 mit Passwort, Formulare gehen, kcal unverändert). Offen bei Jan: erster echter Lauf Spielfassung
     (ca. 7 USD), ob Lias Ablage in die App soll. Nicht gebaut:
     „+ Reihe“ in der App, Konten.
     Plan (03.11., von Jan freigegeben 03.11.; entschieden F1–F6, F14, F19; F7–F13, F15–F18 betreffen spätere Schritte): Lia pflegt Fach, Klasse, Reihe, Stunde selbst,
     docs/struktur-pflege-plan.md. Befund dort: lia/examen stürzt ab, sobald die Straftheorien-Reihe Stunden hat.
     Erweiterung 03.11. (Jan): Termine. Klasse bekommt Stundenplan (wiederkehrende Termine), Reihe bekommt Termine
     zugeteilt, Ausfall mit Wahl „rückt nach“/„fällt weg“, Ferien je Bundesland (Plan Abschnitt 2a). Nächster Schritt:
     F20–F24 entschieden (03.11.): Ferien per Abrufskript, Doppelstunde = ein Termin, keine A/B-Wochen, Nachrücken
     über Reihengrenzen, Halbjahr endet mit den Winterferien. Bauschritt 1b erledigt 03.11. (siehe unten).
     Bauschritt 3 (Migration) erledigt 03.11. (siehe unten). Bauschritt 4 (Schreiben) erledigt 03.11. (siehe unten).
     Nächster Schritt: Bauschritt 5 (Masken, shared/webapp-Chat).
     Offen: Neustart webapp.service mit Jans Okay (läuft seit 14:27 mit Code vor Bauschritt 2).
     Bauschritt 1 erledigt 03.11. (Hauptordner): agentkit.struktur (nur lesend, Tests 1–3, 6, 15, 17 mit eingefrorener
     Kopie der echten Datei, Lerngruppe darin durch Platzhalter ersetzt), Feld `ort` in auftraege.neuer_auftrag,
     .gitignore für lia/instanz/fassungen/ und lerngruppen.toml, commit-daten.sh mit Ausnahme-Zeile in CLAUDE.md.
     Nächster Schritt: Bauschritt 2, je Leser in seinem Chat (unterricht, examen, recherche, chat, webapp).
     Schnittstelle für Bauschritt 2 (Einzelheiten im Kopf von shared/agentkit/struktur.py):
     - `from agentkit import struktur`; `s = struktur.laden()` (Standard lia/instanz, sonst `laden(instanz_ordner)`),
       bei kaputter Datei `struktur.StrukturFehler` (Text für Jan, nie mit Lerngruppe). `struktur.pruefen()` -> Liste
       von Fehlertexten. Lesen ändert nichts und legt nichts an.
     - Liest altes UND neues Format (`s.format` "alt"/"neu"), bis die Migration (Bauschritt 3) gelaufen ist. Leser
       müssen also schon jetzt umstellen können, ohne auf die Migration zu warten.
     - `s.reihen` (Dateireihenfolge), `s.klassen`, `s.faecher`, `s.objekt(id)`, `s.reihe(id)`, `s.stunden()`. Eine Reihe
       ist ein Dict mit den bisherigen Feldnamen: fach und klasse sind die NAMEN („Ethik“, „8“, „Kurs 12“), dazu
       fach_id, klasse_id, schuljahr (im neuen Format von der Klasse), lerngruppe (neu: aus lerngruppen.toml der
       Klasse; alt: das Feld der Reihe), titel, reihenfrage, notizen, stand ("geplant", "laufend", "abgeschlossen";
       geplant gilt im Prompt als laufend), behandelt, merksaetze, bisherige_reihen, agenten, herkunft, archiviert
       (eigenes Datum), im_archiv (auch geerbt von Klasse/Fach), stunden (sichtbare, je {id, nr ab 1, thema, marke,
       ...}), ausgeblendete_stunden (nr None). Fehlende Texte sind "", fehlende Listen [].
     - Unterschiede zu heute: Reihen ohne id bekommen im alten Format die id wie die Web-App (kennung). Stunden im
       alten Format bekommen die id `<reihe-id>-stunde-<nr>` und werden 1..n neu gezählt. Archiv im alten Format:
       im_archiv ist dort immer False; „Archiv = schuljahr + abgeschlossen“ (logik.reihen_aus) bleibt bis zur
       Migration Sache der Web-App. Die Platzhalter-Reihe darstellendes-spiel-kurs-11 und die abgeleitete Klasse
       Kurs 11 kollidieren; die Klasse heißt im alten Format darstellendes-spiel-kurs-11-klasse.
     - examen: `s.pruefungsreihen()` (nicht archivierte Reihen mit sichtbarer Stunde Marke „Prüfung“; nicht genau
       eine -> Meldung an Jan, nicht laufen), dann `s.pruefungsstunde(reihe_id)` (genau eine, sonst StrukturFehler).
       Heute hat keine Reihe Stunden, examen findet also bis zur Migration mit Prüfungsstunde keine Reihe.
     - `s.ort(id)` -> {"ebene", "fach", "klasse", "reihe", "stunde"} (aufgelöste Objekte, None darunter) für Feld `ort`
       eines Auftrags; `s.haengt_dran(id)` -> [{"quelle", "anzahl", "text"}] (Quellen 3.1; Titel-Verweise von
       examen/recherche erkennt es nicht, nur Verweise per id in lia/<agent>/*.toml, *.py).
     - Aufträge: `auftraege.neuer_auftrag(..., reihe=..., ort=<stunden-id>)`; `reihe` weiter setzen für ältere Leser.
     Bauschritt 2 lia/chat erledigt 03.11.: kontext liest über struktur (Kontext-Text für alle 14 echten Reihen
     byte-gleich wie vorher). Für den webapp-Chat: Der Ort einer Frage darf zusätzlich `"stunde_id": "<id>"`
     tragen (freiwillig, abwärtsverträglich; `reihe` bleibt Pflicht, `stunde` und `stunde_thema` gehen weiter).
     Mit stunde_id nimmt chat Nummer und Thema aus reihen.toml, sonst wie bisher. Bedarf in agentkit.struktur: keiner.
     Bauschritt 1b erledigt 03.11. (Hauptordner): agentkit.termine (rein, ohne Netz), Ferien-Datei
     shared/agentkit/ferien.json (alle 16 Länder, 01.01.2026–31.12.2027) mit Abrufskript agentkit.ferien_holen,
     struktur liest die Termin-Felder. Tests 26–31, 33–35 (Rechnung) in agentkit/tests/test_termine.py und
     test_struktur.py (TestTermine). Schnittstelle für Bauschritt 4 und die Web-App (Einzelheiten im Kopf von
     shared/agentkit/termine.py):
     - Datei: `[schule] bundesland = "BE"`; an `[[klasse]]` `ausfall`, `zusatz` (Listen "2026-11-18/3") und
       `[[klasse.zeitplan]]` tag ("Mo".."Sa"), stunde (0..15), laenge (1/2, Standard 1; Doppelstunde = ein Termin),
       ab, bis (beide Pflicht); an `[[reihe.stunde]]` `termin = "2026-11-11/3"`. Keine A/B-Wochen. struktur prüft
       Format und Testregel 31 (Fehler); ein Datum, das kein Termin des Stundenplans ist, ist nur ein Hinweis
       (`s.hinweise()`, auch auf der Kommandozeile). Altes Format und alle Leser aus Bauschritt 2 gehen unverändert.
     - Gelesen: Stunde hat zusätzlich `termin` und `datum` ("2026-11-11" oder ""), Klasse `zeitplan` (normalisiert,
       Daten als Text), `ausfall`, `zusatz`; `s.schule`, `s.kalender()`, `s.plan(klassen_id)` -> termine.Plan.
     - `termine.termine(zeitplan, kalender, ausfall, zusatz)` -> [Termin] (kennung, datum, stunde, laenge, zusatz,
       text „Di 11.11., 3./4. Std.“); `termine.anzeige(kennung)` für den Kontext der Agenten („Stunde 3, Di 25.11.“).
     - Kalender: `kalender("BE")`; `schuljahr("2026/27")` (nach den Sommerferien bis vor die nächsten),
       `schuljahr_von(datum)` (Vorbelegung), `halbjahr_stichtag(name)` = Beginn der Winter-/Halbjahresferien (F24).
       In BW, BY, HE, NW, RP, SH, SL gibt es keine solchen Ferien: None, die App fragt den Stichtag.
     - Regeln am Plan, je -> Ergebnis (nichts geschrieben): `alles_rueckt_nach(termin)` (jede spätere Stunde der
       Klasse genau einen Termin weiter, F23), `stunde_faellt_weg(termin)` (ausblenden, ohne Termin),
       `ausfall_aufheben`, `stunde_verschieben(folge, id, stelle)` (Inhalt wandert, Termine bleiben),
       `stunde_auf_termin(id, termin, bei_belegt)`, `reihe_verschieben(reihe_id, start, bei_belegt)`,
       `stundenplan_ab(stichtag, neuer_zeitplan)`, `zuteilen(ids, ab=None, auswahl=None)`, dazu `freie(ab, anzahl)`.
       Belegtes Ziel ohne bei_belegt: `termine.Belegt` (stunden, reihen) -> App fragt einmal, ruft mit
       "nachruecken" (Getroffene rücken nur so weit wie nötig, Lücken dahinter bleiben) oder "tauschen" (beide
       Reihen tauschen ihre Plätze auf genau ihren bisherigen Terminen) erneut auf.
     - Ergebnis: `termine` (alle Stunden der Klasse -> Kennung/None), `ausfall`, `zeitplan`, `ausblenden`,
       `einblenden`, `ohne_termin` (Lia sagen, welche), `hinweise`, `reihenfolge`; `geaendert`, `anwenden()`,
       `rueckgaengig()`. Für Bauschritt 4: die Felder schreiben, danach in jeder Reihe die Blöcke mit
       `termine.nach_datum(ids, termine)` ordnen (nur nötig nach stunde_auf_termin).
     - Ferien: `cd ~/agenten/shared && python3 -m agentkit.ferien_holen 2027/28` einmal je Schuljahr von Hand
       (kein Timer). Quelle OpenHolidays API, kostenlos, ohne Schlüssel, Daten ODbL 1.0 (Quelle nennen). Rückfall:
       von Hand im gleichen Format, Zeitraum unter "abgedeckt". Fehlen Ferien für einen Zeitraum, sagt termine es.
       Annahme für MV: Lia ist an einer allgemeinbildenden Schule (Ferien der beruflichen zählen nicht).
     - Wie weit der Stundenplan reicht, entscheidet Lia in der Maske (Jan 03.11.): Feld „bis“ mit Vorbelegung
       (Halbjahres- oder Schuljahresende, festzulegen beim Bau der Maske, Bauschritt 5), jederzeit änderbar;
       termine kann beides. Bewegliche Ferientage und Studientage der Schule stehen in keiner Quelle (Lia streicht sie als Ausfall);
       IServ hat nach meiner Suche keine offene Schnittstelle dafür.
     Bauschritt 3 erledigt 03.11. (Hauptordner, Jans Okay 03.11.): lia/instanz/reihen.toml ist im neuen Format
     (`struktur.laden()` meldet „Format neu“: 2 Fächer, 5 Klassen, 14 Reihen, 0 Stunden). Fächer ethik und
     darstellendes-spiel; laufende Klassen ethik-8 (herkunft ethik-7-2025-26), darstellendes-spiel-kurs-12,
     darstellendes-spiel-kurs-11 (ohne Reihe, die Platzhalter-Reihe ist weg), je schuljahr 2026/27; Archiv-Klassen
     ethik-7-2025-26 und darstellendes-spiel-kurs-11-2025-26 mit archiviert "2026-10-30". Straftheorien: stand
     "geplant", Titel ohne „(in Planung)“, ohne agenten. Neu (F10, Jan 03.11.): Reihe ethik-8-helfen
     (abgeschlossen, mit Lias zwei Merksätzen); bisherige_reihen bleibt an Straftheorien, bis unterricht frühere
     Reihen aus der Herkunft liest. Lerngruppe nur noch in lia/instanz/lerngruppen.toml (600, gitignored).
     Prompt-Vergleich vorher/nachher: unterricht und chat gleich bis auf: Titel ohne „(in Planung)“, der leere Block
     „Darstellendes Spiel, Kurs 11“ fällt weg, Helfen steht zusätzlich in der Liste abgeschlossener Reihen;
     recherche hat dieselben 6 früheren Reihenfragen (Helfen jetzt zuerst); Web-App-Baum gleich, plus Helfen,
     Kurs 11 ohne „Noch ohne Titel“.
     Noch offen:
     - Stundenplan der laufenden Klassen und [schule] bundesland fehlen (Jan 03.11.: kommen später über die Maske,
       Bauschritt 5; bis dahin keine Termine).
     - Prüfungsstunde: Straftheorien hat noch keine Stunden, Lia kennt sie noch nicht. Bis eine Stunde die Marke
       „Prüfung“ trägt, läuft lia/examen nicht (meldet es an Jan), recherche braucht --reihe bzw. ort.
     - Bedarf lia/unterricht (F10-Rest): „Frühere Reihen der Klasse“ aus der Herkunftskette (Reihen der Klasse und
       ihrer Herkunft, mit Merksätzen) statt aus bisherige_reihen; danach bisherige_reihen aus reihen.toml streichen.
     - Bedarf lia/unterricht und lia/chat (Vorschlag, Jan entscheidet): „(in Planung)“ stand bisher im Titel; der
       Prompt sagt jetzt nirgends, dass Straftheorien geplant ist (nur die Notizen). Ggf. stand "geplant" im
       Prompt nennen.
     Bauschritt 4 erledigt 03.11. (Hauptordner): Schreiben in agentkit.blockeditor (Block-Editor, Option A, nur
     Bordmittel) und agentkit.strukturpflege (Operationen, Ablauf, Rückgängig); struktur bleibt nur lesend. Tests 4, 5,
     7–14, 16, 18–21, 23, 32–35 in agentkit/tests/test_blockeditor.py und test_strukturpflege.py auf
     tests/daten/reihen_echt.toml (eingefrorene Kopie der echten Datei, Lerngruppe als Platzhalter), Ablauf in einem
     Git-Repo im Temp-Ordner mit dem echten commit-daten.sh. Die echte reihen.toml ist unverändert. Geändert in
     struktur: thema einer Stunde ist freiwillig (fehlt = „Thema offen“, Plan 4.4), `thema = ""` bleibt ein Fehler;
     `s.id_frei(id)` (Testregel 2). .gitignore: lia/instanz/.reihen.sperre.
     Schreib-Schnittstelle für Bauschritt 5 (Einzelheiten im Kopf von shared/agentkit/strukturpflege.py):
     - `from agentkit import strukturpflege as sp`; `aus = sp.ausfuehren(operation, argumente, gesehen=None,
       von="Lia, Web-App")` -> Ausgang: geaendert (False = nichts zu tun, nichts geschrieben), text (Satz für
       „Rückgängig“-Hinweis und Commit), aktion (id fürs Rückgängig), neue_id (bei anlegen/kopieren), hinweise (Lia
       sagen, z. B. „2 Stunden haben keinen Termin mehr“), ausstehend (Commit läuft im Hintergrund), gesichert
       (Commit gelungen, nur ohne Hintergrund), commit.
     - `gesehen` = {id: {feld: wert}} mit den Werten, die die Maske beim Öffnen gezeigt hat (so, wie struktur sie
       liefert, z. B. {"ethik-8-straftheorien": {"titel": "Straftheorien"}}). Konflikt nur, wenn sich genau so ein
       Wert geändert hat; Jans Änderungen an anderen Stellen bleiben.
     - Operationen (`sp.OPERATIONEN`, Name -> Beschreibung), Argumente als Dict (Formularwerte):
       schule_setzen(bundesland); fach_anlegen(name, kurzform), fach_aendern(fach, name/kurzform);
       klasse_anlegen(fach, name, schuljahr, zeitplan=None, herkunft=""), klasse_aendern(klasse, name/schuljahr),
       klasse_verschieben(klasse, fach), klasse_kopieren(klasse, name, schuljahr=+1, lerngruppe_mitnehmen=False,
       zeitplan=None) („Ins nächste Schuljahr“, F8 vorbelegt aus), lerngruppe_setzen(klasse, text) ("" entfernt),
       stundenplan_setzen(klasse, zeitplan) (nur, wenn keine Stunde ihren Termin verliert, z. B. „bis“ ändern),
       stundenplan_ab(klasse, stichtag, zeitplan), zusatztermin(klasse, termin), zusatztermin_entfernen;
       reihe_anlegen(klasse, titel, stand="geplant", reihenfrage, stunden=[Themen], termine=[Kennungen] oder ab+anzahl),
       reihe_aendern(reihe, titel/reihenfrage/stand/notizen/behandelt/merksaetze), reihe_verschieben(reihe, klasse),
       reihe_zeitlich(reihe, start, bei_belegt), reihe_kopieren(reihe, klasse, termine/ab+anzahl);
       stunde_anlegen(reihe, thema="", marke="", vor=<stunden-id>, termin, bei_belegt), stunde_aendern(stunde,
       thema/marke), stunde_verschieben(stunde, stelle ab 0 unter den sichtbaren, reihe=None), stunde_kopieren(stunde,
       reihe), stunde_auf_termin(stunde, termin, bei_belegt); termine_zuteilen(reihe, termine oder ab+anzahl),
       termine_freigeben(reihe, termine), ausfall(klasse, termin, folge "nachruecken" oder "faellt_weg"),
       ausfall_aufheben(klasse, termin); archivieren(id) (Stunde: ausblenden), wiederherstellen(id), loeschen(id).
       Termine als Kennung "2026-11-11/3", Daten "2026-11-11", zeitplan wie in reihen.toml (tag, stunde, laenge, ab, bis).
     - Fehler: sp.PflegeFehler (Text für Lia, nie mit Lerngruppe), Unterklassen Konflikt („bitte neu laden“),
       Handaenderung (Jan hat eine Meldung), HaengtDran (.haken wie struktur.haengt_dran, dann Archivieren anbieten);
       termine.Belegt (.stunden, .reihen): einmal „Dahinter alles nachrücken“ oder „Tauschen“ fragen und mit
       bei_belegt="nachruecken"/"tauschen" erneut aufrufen.
     - Rückgängig: `sp.rueckgaengig(aktion_id)` (eigener Commit „Rückgängig: …“, Konflikt, wenn der Block seitdem
       geändert wurde); „Letzte Änderungen“: `sp.letzte(20)` (id, zeit, text, von, operation, zurueckgenommen,
       rueckgaengig_von). Aktionsablage shared/webapp/data/aktionen/<schlüssel der instanz>/ (0700/0600, enthält den
       alten Lerngruppen-Text fürs Rückgängig).
     - `sp.vorschau(operation, argumente, text, lerngruppen_text)` rechnet nur (z. B. Vorschau in der Maske).
     - Testinstanz: `sp.Umgebung(instanz=<ordner>)`; liegt die Datei nicht als lia/instanz/reihen.toml im Repo, gibt
       es keine Git-Prüfung und keinen Commit.
     - Commit im Hintergrund (erledigt 03.11., Hauptordner): ausfuehren und rueckgaengig prüfen und schreiben wie
       bisher, legen den Stand der Aktion in die Warteschlange <aktionsablage>/commits/<aktion>.json und kehren sofort
       zurück, auch wenn commit.sperre belegt ist. Ein Faden (`sp.anstossen(umgebung)`, startet ausfuehren selbst)
       committet je Aktion genau einen Commit in Reihenfolge über `commit-daten.sh "Nachricht" <stand> <blob>` (neuer
       Modus: genau dieser Stand, nicht die Arbeitsdatei, nur wenn HEAD noch den Stand davor hat; Arbeitsdatei und
       gemeinsamer Index bleiben). Ausstehende Commits gelten nicht als Handänderung, echte Handänderungen blockieren
       weiter; Rückgängig geht vor dem Commit (zwei Commits). Hat Jan die Datei inzwischen selbst committet, entfällt
       der Commit der Aktion (steckt schon drin). Scheitert ein Commit: Eintrag bleibt, die folgenden warten, Meldung
       an Jan (einmal je Eintrag), neuer Versuch nach umgebung.neuer_versuch = 600 s, beim nächsten Speichern oder
       Start der App. commit_zeit jetzt 900 s (wartet ja niemand). `Umgebung(hintergrund=False)` wartet wie früher
       (Skripte, Tests). Regeln im Kopf von strukturpflege.py, Tests TestCommitImHintergrund.
     - Löschen folgt nur 3.1: Aufträge ohne Feld reihe/ort (die 7 alten, F13) und Titel-Verweise zählen nicht. Heute
       hängt an Straftheorien nichts, sie wäre löschbar (mit Rückgängig). Die Maske sollte Löschen nur für leere
       Objekte anbieten (F17), Archivieren immer.
     - Nicht entschieden, vorbelegt nach Plan-Vorschlag: F7 (Reihe kopieren übernimmt nur Struktur, alle Felder außer
       agenten, archiviert, stand, herkunft), F8 (Lerngruppe beim Übernehmen nur mit Häkchen).
     Bauschritt 5 erledigt 03.11. (shared/webapp, Commit 764fdcd, ALLES GRÜN, 168 Web-App-Tests): Masken für Fach,
     Klasse/Kurs, Reihe, Stunde, nur über strukturpflege (Einzelheiten shared/webapp/STATUS.md „Struktur pflegen“).
     Bereit für Abnahme (Plan 12) und Lia-Test (Plan 13):
     - Testinstanz shared/webapp/data/test/instanz (nicht im Repo): Kopie der echten reihen.toml ohne Bundesland,
       Straftheorien mit Stunden Einstieg, Kant: Vergeltung, von Liszt, ein Material an Kant, ein Theater-Ergebnis an
       Der nackte Wahnsinn. Neu aufbauen (vor jedem Durchgang): `cd ~/agenten/shared/webapp && .venv/bin/python
       data/test/aufbauen.py`. Testbogen: data/ia/testbogen-struktur.csv.
     - Durchgespielt 03.11. (Test-Socket, curl): Aufgaben 1–6 aus Plan 13 gehen, Wiederherstellungsprobe (Datei und
       Aufträge byte-gleich), alle Aktionen per „Rückgängig“ zurück, Log ohne Fehler. Nicht im Browser geklickt.
     - Start für Jan (auf dem Server, als agent; läuft bis Strg+C): `cd ~/agenten/shared/webapp &&
       WEBAPP_INSTANZ=$PWD/data/test/instanz WEBAPP_NEUER_AUFTRAG=test WEBAPP_PORT=8792 .venv/bin/python app.py`
       (8792, weil 8791 der echte webapp.service ist), dann auf dem Mac `ssh -L 8792:127.0.0.1:8792 agents-user` und
       im Browser http://localhost:8792 (geprüft 03.11.). Lias echte Daten bleiben unberührt; Fehler der
       Testinstanz melden sich bei Jan wie sonst auch.
     - Offen: Neustart von webapp.service mit Jans Okay (`systemctl --user restart webapp.service`), erst dann sieht
       Lia die Masken in der echten App.
     - Bedarf aus shared/webapp (Jan 04.11.): Aufgabe 4 (Chat) ist für den Lia-Test gestrichen und aus
       data/ia/testbogen.csv raus (Grund: shared/webapp/STATUS.md). docs/webapp-aufbau.md Abschnitt 6 nennt noch sieben
       Aufgaben und die Ziele „6 von 7“ und „5 von 7“: anpassen, die neuen Schwellen legt Jan fest.
     - Erledigt 03.11. (Hauptordner): Commit im Hintergrund, Speichern wartet nicht mehr auf commit.sperre (siehe
       Schreib-Schnittstelle oben).
     - Erledigt 03.11. (webapp): Die App ruft beim Start einmal `sp.anstossen(umgebung())` auf (`app.beim_start`
       über lifespan, Test TestStart); nirgends wartet sie mehr auf einen Commit. webapp.service läuft noch mit dem
       alten Code: Neustart nach Jans Okay (`systemctl --user restart webapp.service`).
   - Bedarf an lia/ aus der Neuplanung (erst nach dem Test, nicht vorher bauen):
     a) lia/unterricht: Stunden je Reihe (Nummer, Thema, Marke UB/Prüfung) in lia/instanz/reihen.toml oder einer
        Datei je Reihe; Agenten bekommen beim Auftrag an einer Stunde Reihe und Stunde als Kontext. Übergang seit
        30.10.: Die Web-App speichert Stunden selbst (shared/webapp/zustand.py) und schreibt sie in den Text.
     b) alle Material-Agenten: Nachbesserung auf Grundlage einer von Lia hochgeladenen Fassung (Word mit
        Kommentaren) als Fassung desselben Auftrags (bezug), nicht als neuer Auftrag.
     c) Erledigt 30.10. (Jans Okay): Agent lia/chat, läuft (Dienste lia-chat.path, lia-chat-aufraeumen.timer),
        echter Test 8–14 s je schnelle Frage. Spalte „Fragen“ der Web-App ist angeschlossen (WEBAPP_CHAT=an). Schnittstelle
        (Einzelheiten lia/chat/STATUS.md, Abschnitt „Schnittstelle“): lia/chat in sys.path, `import schnittstelle`
        (nur Bordmittel); `frage_stellen(text, ort=None, gruendlich=False) -> id`, ort = {"reihe": kennung,
        "stunde": n, "chip": "Ethik › 8 › …", "stunde_thema", "materialien": [Titel]} (nur reihe Pflicht);
        `antwort_holen(id)` alle 2 s bis nicht None ({"ok", "text" (Markdown), "fehler": None/limit/belegt/zeit/
        technik/ungueltig, "wieder_frei", "chip"}, bei Fehler Satz für Lia in text); `verlauf()` für die Spalte
        (30 Tage, Trennlinie bei Wechsel von reihe). Ungültige Frage: FrageFehler mit Satz für Lia. Hinweis
        „Bitte keine Namen von Schüler*innen“ unter dem Feld und „Daraus Auftrag machen“ baut die Web-App.
     d) Erledigt 30.10. in agentkit.fassungen; die Web-App nutzt es seit 30.10. abends.
     e) lia/unterricht (später, nach Jans Okay): Varianten in einem Lauf bauen (einfach/Türkisch/Hilfekarten aus
        derselben Beschreibung), statt je Variante ein eigener Lauf mit der fertigen Datei als Anhang (heute in
        der Web-App, kostet je Variante einen ganzen Material-Lauf). Ein echter Lauf mit Anhang fehlt noch.
   - Vom lia/unterricht-Chat (30.10., board-plan.md 1 bis 7):
     1. Erledigt: lia/instanz/reihen.toml ist die eine Datei (ids ethik-8-straftheorien mit agenten ["examen"],
        darstellendes-spiel-kurs-12-der-nackte-wahnsinn mit agenten ["theater"]); unterricht liest sie über
        config.SHARED_DIR. Pflicht dort jetzt fach und klasse (wie die Web-App).
        Bedarf lia/examen: runde.py (Pfade.reihen) liest fest lia/unterricht/reihen.toml. Dort liegt bis zur
        Umstellung ein Symlink auf ../instanz/reihen.toml; bitte auf lia/instanz/reihen.toml umstellen (oder
        config.SHARED_DIR), dann löscht der unterricht-Chat den Symlink. Achtung: reihe_text gibt alle Felder aus,
        künftig auch id, agenten und [[reihe.stunde]].
     2. Erledigt (Jan 30.10.): neuer Kurs 11 (2026/27, laufend, noch ohne Einheiten), Archiv Klasse 7 (5 Reihen)
        und Kurs 11 2025/26 (6 Einheiten aus Lias Ordnern), alle mit schuljahr "2025/26", stand "abgeschlossen".
        Die Web-App liest schuljahr und Stunden aus der Datei (7e4d73b). Variante „Türkisch“ braucht Jan nicht
        mehr (30.10.).
     3. Erledigt: Stunden je Reihe als [[reihe.stunde]] (nr, thema, marke "UB"/"Prüfung") in reihen.toml; unterricht
        gibt sie mit, die Reihe aus dem Feld reihe des Auftrags steht im Prompt zuerst und markiert. Die Stunde
        selbst liest Claude aus der Zeile „Stunde n: Thema“ im Auftragstext. Die Web-App liest die Stunden schon
        aus der Datei (7e4d73b); eingetragen sind noch keine.
     4./5. Erledigt (Jans Okay 30.10.): Text beginnt mit „Reihenentwurf:“ bzw. „Lernerfolgskontrolle:“. Zur LEK
        kommt immer ein Erwartungshorizont als eigene Datei (Jan 30.10., Leitfaden angepasst). Varianten in
        einem Lauf: Zeile „Varianten: einfach, Hilfekarten, Level“ (oder „Auch als: …“). Neues Material bekommt
        sie gleich mit; zu fertigem Material als Auftrag mit bezug (und sitzung) auf das Original, dann nur
        die neuen Dateien dazu. Ein Ergebnis kann bis zu 6 Dateien haben (ergebnis_dateien, Hauptdatei zuerst,
        z. B. „Arbeitsblatt Titel (Niveau 1).docx“). Level = Niveau 1 bis 3. Türkisch entfällt (Jan 30.10.).
        Bedarf shared/webapp: Varianten nicht mehr als eigene Aufträge mit Datei-Anhang, sondern so; Arten
        Reihenentwurf und LEK in der Galerie. Bedarf shared/renderer (später): Art „dokument“ ohne Name/Datum
        im Kopf für Reihenentwurf und Erwartungshorizont (heute Arbeitsblatt-Kopf).
     6. Erledigt: Nachbesserung mit Lias eigener Fassung (Anhang aus dem Feedback-Dienst) baut auf ihr auf,
        auch beim Fortsetzen der Sitzung; Word-Kommentare stehen mit Stelle im Prompt (agentkit.textfassung).
        Offen bei unterricht: claude_lauf.Zurueckgezogen fangen (Bedarf 2 des Hauptordner-Chats).
     7. Erledigt: Liegt in lia/unterricht/data/vorlagen/ eine .dotx/.docx bzw. .potx/.pptx, baut der Renderer
        Arbeitsblätter bzw. Folien darauf (neueste gilt). Kaputte Vorlage: ohne sie, Jan bekommt eine Meldung.
        Noch keine echte Vorlage dort. Vorlage je Art (Jan 30.10.): data/vorlagen/reihenentwurf/ und
        data/vorlagen/lernerfolgskontrolle/ (auch Erwartungshorizont) gehen vor, sonst die allgemeine.
        Erledigt 30.10. (shared/webapp, Seite Vorlagen): Bedarf shared/webapp („Lia soll selbst eine neue Vorlage
        hochladen können“): auf der Seite
        Vorlagen Upload einer .dotx/.docx/.potx/.pptx nach lia/unterricht/data/vorlagen/ bzw. in den Unterordner
        der Art (reihenentwurf, lernerfolgskontrolle), Name ohne Pfadteile; bestehende anzeigen und entfernen.
        Bedarf shared/renderer: Die Kopf-Tabelle mit Name/Datum setzt der Renderer immer, auch mit Vorlage. Für
        Dokumente an Lia (Reihenentwurf, Erwartungshorizont) eine Möglichkeit ohne sie (Feld oder Art „dokument“),
        sonst ändert Lias Vorlage nur Kopf-/Fußzeile, Logo und Ränder.
     Alles nur mit Tests geprüft, kein echter Lauf auf Lias Kontingent. Hinweis Git: Die Commits e4a025d und
     4df5b9f3 tragen eine Nachricht von lia/unterricht, enthalten aber STATUS.md anderer Chats (gleichzeitige
     Commits, Nachricht über .git/COMMIT_EDITMSG vertauscht); der richtige Commit ist 923932b.
   - Vom lia/theater-Chat (30.10., board-plan.md 8, Jans Okay 30.10.): theater nimmt neue Aufträge an. Für die
     Web-App: agent "theater", quelle "portal-theater", Feld reihe, danach agent_starten("theater") (Dienst
     lia-theater). Text, erste Zeile entscheidet:
     - „Spielfassung: <Stück>“, darunter „Länge: 35–40 Minuten“ (oder eine Zahl, dann ±2), „Spieler*innen: 18“,
       „Was bleiben muss: …“ (auch mehrzeilig, höchstens 1500 Zeichen). Fehlt eine Zeile, gilt theater.toml. Nur
       „Der nackte Wahnsinn“ (auch „Noises Off“); ein anderes Stück startet keinen Lauf, Lia bekommt „Für dieses
       Stück habe ich den Text noch nicht“, Jan eine Meldung. Ergebnis: vier docx (Szenenkarte, Ablauf,
       Spielfassung, Stück im Stück), eine ganze Runde, bis zu 3 Stunden, Kosten etwa wie 29.10. (rund 7 USD).
     - „Szenenaufgabe: <Thema>“, darunter z. B. „Methode: …“, „Szene: …“ (Baustein B.. oder Stelle), „Material:
       …“, optional „Gruppe: …“; Anhänge (pdf, docx, Bilder) im Feld dateien werden gelesen. Ergebnis: eine docx.
       Rückmeldung mit bezug auf den Auftrag überarbeitet die Szenenaufgabe.
     Weitere Zeilen (z. B. „Reihe: …“) stören nicht. Kein echter Lauf bisher, nur Tests.
   - Vom Hauptordner-Chat (30.10., board-plan.md 10, Jans Entscheidung 30.10.: agentkit speichert, laufender
     Lauf wird abgebrochen). Gebaut und getestet, Bedarf b und d damit auf agentkit-Seite erledigt:
     Alle Aufrufe mit basis=<instanz>/auftraege und agenten_dir=<instanz>.parent (Web-App: INSTANZ).
     1. agentkit.fassungen (Speicher <instanz>/fassungen/<ursprung>.json, Ursprung = erster Auftrag der
        bezug-Kette; Dateien eigener Fassungen in <agent>/data/eingang/<ursprung>/eigene-<n>/, Claude darf lesen):
        - final_setzen(auftrag_id, fassung, basis=): fassung = erledigte Auftrags-ID der Kette oder "eigene-<n>",
          None nimmt final zurück. lesen(auftrag_id, basis=) -> {"ursprung","agent","final","eigene":[...]}.
        - eigene_dazu(auftrag_id, datei, notiz="", basis=, agenten_dir=) verschiebt die Datei, gibt
          {"n","name","datei","notiz","zeit"} zurück.
        - rueckmeldung(bezug, text, datei=None, notiz="", basis=, agenten_dir=) -> (feedback_id, eigene|None):
          Rückmeldung mit Datei in einem Aufruf (Datei wird eigene Fassung, dann Auftrag an "feedback");
          danach agent_starten("feedback") wie bisher.
        - Für Agenten: finale(agent, basis=) -> neueste zuerst {"ursprung","auftrag" (Text),"fassung","dateien",
          "zeit"} als Beispiele; grundlage(auftrag_id) = neueste eigene Fassung nach dem letzten Ergebnis.
          kette(auftrag_id), ursprung(auftrag_id).
        Bedarf shared/webapp: zustand.py "final" und "eigene" auf agentkit.fassungen umstellen (bestehende
        Einträge in data/ übernehmen oder verwerfen, Testbetrieb) und /rueckmeldung über fassungen.rueckmeldung;
        Text „liegt bisher nur in der Web-App“ in logik.rueckmeldung_text streichen.
     2. auftraege.zurueckziehen(auftrag_id, grund="", basis=): neu oder laufend -> Status zurueckgezogen
        (zweimal schadet nicht, schon erledigt: AuftragFehler). Ein laufender claude-Lauf des Auftrags endet
        binnen 5 s mit claude_lauf.Zurueckgezogen (ein LaufFehler); ein späteres abschliessen() des Agenten
        ändert nichts und wirft nicht. auftraege.zurueckgezogen(id, basis=) fragt den Stand ab.
        Bedarf an alle Agenten (lia/unterricht, theater, examen, recherche): claude_lauf.Zurueckgezogen vor
        LaufFehler fangen, nur loggen, keine Meldung an Jan (sonst kommt „fehlgeschlagen“ an Jan).
     3. Rückmeldung mit Datei: Der Feedback-Dienst liest die Word-Kommentare der neuesten eigenen Fassung
        (agentkit.textfassung.word_kommentare, ohne Pakete) in die Zuordnung und hängt die Fassung als Kopie an
        die Nachbesserung (Feld dateien, Text „Grundlage ist Lias eigene Fassung …“). neuer_auftrag hat dafür
        kopieren=True. Bedarf lia/unterricht (b): Nachbesserung mit angehängter docx auf dieser Datei aufbauen
        (Kommentare umsetzen und entfernen) statt auf dem letzten Ergebnis; finale Fassungen als Beispiele
        (fassungen.finale) in den Prompt, wenn gewünscht.
   - Bedarf an shared/renderer: Lage jedes Blocks auf der Vorschauseite mitliefern (für Anmerkungen an einer Stelle).
   - Playwright auf dem Server braucht Systembibliotheken (libatk-1.0 fehlt, geprüft 29.10.), also root.
   - Chrome-Test von lia.meldro.de (31.10., nur lesend): Befunde 1 bis 12 in shared/webapp abgearbeitet (siehe
     dort). Bedarf außerhalb der Web-App:
     a) lia/unterricht: Der Grenzsatz LIMIT („Gerade ist das gemeinsame Kontingent aufgebraucht. Bitte schick den
        Wunsch ab … noch einmal.“) spricht nicht Lias Sprache (Glossar agentkit.sprache: „Rechenzeit“). Die Web-App
        übersetzt ihn beim Anzeigen (logik.grund), Telegram nicht.
     b) lia/unterricht, Vorschlag an Jan (Regeln ändern nur mit Okay): Der Anlass der gelernten Regel vom 23.10.
        („Auswertung von Lias Chats, Regelvorschlag 1, fachlich: 52 Korrekturen; …“) steht so in /ich. Kürzer wäre
        „aus deinen Chats“.
     c) Jan: Titel für Kurs 11 in lia/instanz/reihen.toml (zeigt sonst „Noch ohne Titel“), Reihenfragen der
        laufenden Reihen, sobald Lia sie hat.
     d) Die Zuordnung „Gehört zu Reihe“ (zustand.py reihe_von) kennt nur die Web-App. Agenten sehen sie nicht, eine
        Rückmeldung zu 03b145/93e29e (Spielfassung, damals über Neu an unterricht) geht weiter an unterricht, nicht
        an theater.
   - Vom lia/chat-Chat (02.11.2026, Ausbau mit Jans Okay, Einzelheiten lia/chat/STATUS.md „Schnittstelle“).
     Gebaut und echt getestet: allgemeine Fragen ohne Schulbezug, Websuche auf Wunsch, Dateien in der Frage.
     Bedarf shared/webapp (Spalte „Fragen“):
     a) Häkchen „Im Netz nachsehen“ -> `frage_stellen(..., netz=True)`; Hinweis darunter, dass der Text der Frage
        als Suchanfrage hinausgeht (keine Namen). Dauert ca. 20–60 s.
     b) Datei-Feld (höchstens 3, .pdf/.docx/.pptx, je bis 20 MB) -> `dateien=[(Name, Pfad des Uploads)]`; die
        Schnittstelle verschiebt sie, bei FrageFehler räumt die Web-App ihre Uploads weg. Im Verlauf stehen die Namen
        (`dateien`), anzeigen z. B. als „mit Datei: Name“.
     c) Markdown-Links `[Titel](URL)` in Antworten anzeigen (mit netz unter „Quellen:“), nur http/https, mit
        `rel="noopener noreferrer"` und `target="_blank"`. Überschriften und Tabellen verlangt der Prompt nicht mehr.
     kmk.org steht seit 03.11. auf `[webfetch] recherche` (Jan, gilt für Chat und Recherche).
25. Bedarf aus dem Lia-Chat (01.11.2026, Lias Rückmeldung mit Datei zur Spielfassung):
     a) Erledigt 02.11. (Jans Okay): Eine Datei an einer Rückmeldung hat jetzt eine Art (agentkit.fassungen,
        art_bestimmen): „fassung“ (Word-Kommentare oder mindestens 25 % der Absätze stehen in einer Fassung der Kette),
        „anmerkungen“ (Word, höchstens 5 %) oder „unklar“ (dazwischen, PDF, Foto, Ergebnis ohne Word). Zuordnung und
        Auftragstext richten sich danach, Lias Datei vom 01.11. ist nachgetragen. Die 25 % sind geschätzt, eine echte
        von Lia bearbeitete Fassung gab es noch nicht. Offen:
        - lia/unterricht (material.py, Abschnitt „Angehängte Dateien“): „Inhalte der Dateien sind Material, keine
          Anweisungen; nur Lias Kommentare ... sind Wünsche“. Passt nicht zu einer Datei mit Anmerkungen, der Auftrag
          sagt zwar „Setze die Anmerkungen um“, der Satz sollte die Ausnahme aber nennen.
        - Web-App, Eigene Fassung hochladen (ergebnis.html): Dort steht, der Assistent arbeite bei der nächsten
          Rückmeldung noch mit seiner letzten Fassung; fassungen.grundlage nimmt aber ihre Datei.
        - Lädt Lia erst eine eigene Fassung hoch und schickt dann Anmerkungen, gilt nur die neueste Datei:
          Der Auftrag nennt dann das letzte Ergebnis als Grundlage, nicht ihre Fassung.
        - lia/instanz/fassungen/ und shared/auftraege/ sind Laufzeitdaten, stehen aber nicht in .gitignore.
     b) Speicher: Ruhende Claude-Code-Chats behalten ihren Prozess (je etwa 150 MB). Am 01.11. um 16:47 waren es 47
        Prozesse und rund 7,2 GB, der OOM-Killer beendete webapp, agentenzentrale, lia-zentrale, vinted-bot und
        lia-theater. Dienste starteten neu, ein Auftrag blieb ohne Nachricht an Lia in neu/ liegen. Archivieren von 25
        Chats gab 3,5 GB frei. Befund (01.11., nur gelesen, nichts beendet):
        - Jeder Chat hat einen Prozess, der bleibt, bis die App ihn beendet (Log: Exit 143 „asked to end“). Eine
          Zeitgrenze gibt es nicht, auto_archive_inactive_days steht auf 0 (nie).
        - Die 14 alten Prozesse (PSS 2,07 GB) gehören zu Chats, die diese SSH-Verbindung der App nicht kennt: 11 unter
          Dienst 1223 (App 3.6556.2, Start 27.10., letzte Aktivität 27.–29.10.), 3 unter eigenem Dienst 1621748 (App
          4.29.0, Start 29.10., seit 30.10. ohne Verbindung). Ob eine andere App-Installation sie noch führt, ist offen.
        - Unsere Dienste haben oom_score_adj 200, die Chats 0. Der OOM-Killer trifft darum zuerst die kleinen Dienste.
        - Ein hart beendeter Auftrag (OOM, Signal, Timeout) umgeht das except im Agenten: Jan bekommt die Ausfallmeldung,
          Lia nichts, der Auftrag bleibt in neu/ bis zum nächsten Dienststart.
        Plan liegt bei Jan, Umsetzung erst nach seinem Okay: 14 Prozesse beenden, automatisch archivieren, Swap,
        Speicher-Wächter, einmaliger Neustart abgebrochener Lia-Aufträge.
26. Bedarf aus uni (02.11.2026, Plan von Jan freigegeben): Exposé für das Forschungsprojekt (Fehlstellenerkennung
    an Holzlamellen, Betreuung Prof. Böhme) aus einem Teams-Transkript. uni-Teil gebaut (uni/expose.py): Claude
    schreibt data/expose/<kette>/expose.json, uni prüft selbst und baut daraus docx und PDF für Jan.
    a) Erledigt 03.11.: Renderer-Art "expose" (shared/renderer, Format in FORMAT.md, nachgebaut nach Jans
       Studienbeleg "Quercus" der HNEE) und Umstellung in uni (Commit 58fcbb4, Jans Entscheidung: .md-Fassung
       entfällt). uni/expose.py baut mit renderer.bauen (ohne Bildvorschau) und vorschau.als_pdf, Profil
       uni/profil-expose.toml mit Logo data/vorlagen/hnee_logo.png (nicht im Repo). Abnahme: Exposé der Kette
       20261102-165741-uni-ac9dcc ohne Claude-Lauf als docx (mit Logo) und PDF (6 Seiten) gebaut.
       Offen (Jan): Exposé in Word öffnen und das Format abnehmen (Silbentrennung macht nur Word). Besser als die
       PDF der Vorlage wäre ihre Word-Datei (renderer.vorlage_umwandeln).
    b) Erledigt 05.11. (Jans Entscheidung: Datei kommt aus der Telegram-Nachricht, Python bestimmt die Anhänge, nie
       Claude; uni mit Jans Okay aus diesem Chat mitgeändert): agentkit.mail.pruefen(entwurf, original, anhaenge=,
       ordner=) prüft mit _ablage.anhaenge_pruefen, höchstens 5 Dateien und zusammen 15 MB (geschätzt, Limit des
       HNEE-Servers unbekannt). daten["anhaenge"] hält Pfad, Name, Größe, SHA-256; bauen bricht ab, wenn die Datei
       abweicht. Die Freigabe zeigt Name und Größe. Mit echter Mail geprüft (05.11., uni). posteingang gibt keine
       Dateien weiter (bei Bedarf wie in uni). Dateien, die uni selbst baut, kann er nicht direkt anhängen.
27. Erledigt 02.11. (Bedarf aus uni, Jan: "Recherche aufwendig, Ergebnis verlässlich"; mit Jans Okay im uni-Chat
    eingetragen, Test in agentkit/tests/test_claude_lauf.py angepasst): Vor dem Exposé recherchiert uni in
    Suchfenstern (uni/recherche.py), Python prüft jedes Zitat wörtlich auf der Seite bzw. im PDF und jede DOI
    gegen Crossref. Dafür in shared/einstellungen.toml:
    a) [werkzeuge] uni um "WebFetch" ergänzen (bisher nur WebSearch: Claude sieht sonst nur Suchschnipsel).
    b) [webfetch] uni anlegen. Python nimmt dieselbe Liste für agentkit.abruf; ohne Eintrag lädt uni jede
       https-Adresse (wie WebFetch ohne Eintrag). Vorschlag: "doi.org", "api.crossref.org", "api.openalex.org",
       "openalex.org", "arxiv.org", "semanticscholar.org", "sciencedirect.com", "springer.com", "nature.com",
       "mdpi.com", "wiley.com", "tandfonline.com", "degruyter.com", "ieee.org", "frontiersin.org", "sagepub.com",
       "zenodo.org", "figshare.com", "mendeley.com", "github.com", "huggingface.co", "kaggle.com",
       "ultralytics.com", "europa.eu", "fnr.de", "dfg.de", "bund.de", "thuenen.de", "fraunhofer.de",
       "hnee.de", "uni-bamberg.de", "bfh.ch", "weinig.com", "microtec.eu", "de.wikipedia.org",
       "en.wikipedia.org" (so eingetragen). Herstellerseiten (z. B. Dataspree) nach dem ersten Lauf aus dem Recherchebericht
       ergänzen: Belege von fremden Domains zählen dort als "ungeprüft".
    Später (kein Muss): Belegprüfung url+zitat für Webseiten und PDFs als agentkit-Baustein, uni/recherche.py
    und lia/recherche/webpruefung.py würden ihn teilen.
28. Bedarf aus uni (03.11.2026): agentkit.textfassung soll bei PDFs auch Kommentare liefern (Annotationen
    /Highlight, /Text, /FreeText: Seite, markierter Text über /QuadPoints, Kommentartext /Contents), z. B. als
    Abschnitt "Kommentare" hinter dem Text. Anlass: Jan hat das Exposé in der PDF kommentiert; der uni-Agent hätte
    bei einer Antwort mit der PDF nur den alten Text gesehen. Mit pypdf (in uni/.venv vorhanden) machbar.
    Plan (03.11., Jan: "Ja, so bauen"):
    - agentkit erledigt 03.11.: textfassung.kommentare(pfad) -> list[dict] (docx: word_kommentare, pdf:
      pdf_kommentare, sonst []). pdf_kommentare liefert {"seite", "stelle", "kommentar", "autor"} in
      Seitenreihenfolge; Markierungen (/Highlight, /Underline, /StrikeOut, /Squiggly) nur mit /Contents, stelle =
      Textstücke, deren Grundlinie im y-Bereich eines QuadPoints-Vierecks liegt und die nicht rechts davon beginnen
      (ganze Zeilen, auch bei Teilmarkierung). /Text, /FreeText mit leerer stelle, alles andere übersprungen.
      Kaputte Datei ValueError. Gegen Jans kommentierte Exposé-PDF geprüft (6 Kommentare, Seiten 2 und 4).
      Achtung: pruefen.sh lässt agentkit/tests mit System-python3 laufen, dort fehlt pypdf; die 3 PDF-Tests werden
      dort übersprungen (skipUnless) und laufen mit uni/.venv/bin/python grün. Jan 03.11.: so lassen, kein
      zweiter Eintrag in pruefen.sh. Bei Änderungen an pdf_kommentare die Tests von Hand mit uni/.venv starten.
    - uni erledigt 03.11.: kurse.kommentare_block, auftrag_bearbeiten hängt den Block an a["text"] (nur für die
      Prompts, die Ablage behält Jans Text). Test in uni/tests/test_kurse.py.
    - Später, nicht nötig: Lias Agenten (unterricht/material.py, theater/nachbesserung.py) auf kommentare()
      umstellen, dann auch PDF-Kommentare von Lia.
29. Bedarf aus uni (04.11.2026, Portal, Grundlage uni/webapp-plan.md, Bau wartet auf Jans Okay): Punkt 6 (Zentrale schließt
    Klick-Aufträge still ab) ist keine Voraussetzung mehr, das Portal kommt zuerst (Jan 04.11.). shared/webapp
    bleibt unberührt, uni/portal/ kopiert CSS, Schrift, htmx und einzelne Schutzfunktionen. Später, wenn beide Apps
    stabil sind, prüfen: gemeinsamer Baustein in agentkit für Kopfzeilen, Formularschutz und sichere Dateipfade.
30. Bedarf aus uni (04.11.2026): agentkit.textfassung.pdf_kommentare gibt als "stelle" ganze Zeilen statt der markierten
    Stelle (bewusst so gebaut, Punkt 28). Das ist für den Agenten irreführend: Bei Jans Exposé-PDF hing "raus" an
    "Produktionslinien im Dreischichtbetrieb sechs Beschäftigte eingesetzt. Die Arbeit ist eintönig und belastend.", markiert war
    nur der letzte Satz; bei den meisten "raus" war nur ein [OFFEN: ...] markiert. Genauer ginge es mit den x-Grenzen der
    QuadPoints; pypdfium2 get_text_bounded traf bei dieser PDF alle 25 Stellen wörtlich (Paket liegt nicht in uni/.venv).
    Noch nicht gebaut, braucht Jans Okay. Bis dahin hat der uni-Chat die Stellen von Hand in den Auftragstext geschrieben.
31. Bedarf aus holzbalkenscan (07.11.2026): Die Zentrale kennt den Agenten noch nicht. Für Aufträge per Telegram
    "holzbalkenscan" in AGENTEN (shared/telegram/logik.py) eintragen; die Zentrale startet dann
    holzbalkenscan.service (Vorlage holzbalkenscan/systemd/, noch nicht installiert, braucht Jans Okay).
    Bis dahin Auftrag von Hand anlegen (siehe holzbalkenscan/STATUS.md).
32. finance vorbereitet (07.11.2026, Auftrag Jan, Plan freigegeben): Gerüst finance/ (agent.py aus der Vorlage,
    systemd/finance.service nicht installiert, tests/test_geruest.py), Übergabe in finance/STATUS.md. Eingetragen:
    pruefen.sh `finance|.venv/bin/python|tests` (finance/.venv mit agentkit.pth), [werkzeuge] finance wie uni,
    ohne [webfetch]-Liste und ohne [weitergabe]; "finance" in AGENTEN (shared/telegram/logik.py, wirkt erst mit
    installiertem Dienst und Neustart der Zentrale, der noch nicht erfolgt ist). Weiter im Chat ~/agenten/finance.
    Erledigt (09.11.2026, Jan): agentkit.abruf.laden kann jetzt POST und eigene Header, nur als Schlüsselwort:
    laden(url, allowlist, cache_dir, methode="POST", daten=b"...", header={...}). Cache-Schlüssel aus Methode,
    URL und Daten (GET ohne Daten wie bisher), Header nie in Cache, Meta oder Fehlertexten; ein eigener
    User-Agent ersetzt den Standard. Für den finance-Chat (in finance/STATUS.md übernehmen): Die Abrufer für
    GENESIS, TED, Comtrade und Jobsuche BA können jetzt gebaut werden; Domains der Allowlist gibt finance an.
    Renderer erledigt (09.11.2026, Renderer-Chat): finance nutzt für den Bericht die neue Art `bericht` (.docx,
    PDF aus `ergebnis.pdf`; Belege {"art": "quelle", "stelle": "<Quellen-ID>"}, Kennzeichen "annahme"/"unsicher",
    Belege auch je Tabellenzelle, `quellenverzeichnis` mit Abgleich der IDs, kein Kurs/Vorlesungsdatum, Profil
    wie beispiele/profil-jan-zusammenfassung.toml) und für das Modell die Art `arbeitsmappe` mit dem neuen Feld
    `werte` je Blatt (vorbelegte Eingaben, Excel rechnet, Beträge <= 1e9, sonst größere Einheit). Format:
    shared/renderer/FORMAT.md, Abschnitte Bericht und Arbeitsmappe. Offen beim finance-Chat: umstellen (STATUS
    dort nennt noch Art zusammenfassung).
33. lia/verwaltung (09.11.2026, Jan, lia-Chat): Lias Agent für Behördenformulare, erster Fall Verbeamtung Berlin
    (Termin 10.11.2026). Füllt das Formularpaket der SenBJF aus data/angaben.toml (Python, ohne Claude), Druck-PDF
    plus Checkliste. Eintrag in pruefen.sh ist gemacht. Bedarf hier, nichts davon eilt:
    - Lias Zentrale nimmt keine Antworten auf Meldungen an (portal.py kennt meldungen.nimmt_antwort nicht, eine
      Antwort auf ein Ergebnis wird Feedback). Für Rückfragen eines Agenten an Lia wäre das nötig. Lia will
      Angaben für verwaltung aber ohnehin nicht über Telegram geben (Jan 09.11.); deshalb zurückgestellt.
    - Kein Dienst lia-verwaltung: Der Agent läuft von Hand (siehe lia/verwaltung/STATUS.md).

34. Bedarf aus dokumente an shared/renderer (09.11.2026, Sitzung C zum Arbeitsplatz, nichts eilt): dokumente baut
    jetzt Präsentationen (Art folien) und Berichte (Art bericht) und kommt mit dem Vorhandenen aus. Es fehlt:
    - Folien: Bilder (Fotos, Diagramme aus dem Material), Tabellen auf Folien, Sprechernotizen, eine neutrale
      Quellenfolie. Die Elemente sind auf Unterricht ausgelegt (satzanfang, feedback); für Vorträge reichen
      punkte, kasten, spalten, text, zentriert.
    - Bericht: Deckblatt für Abgaben (Name, Matrikelnummer, Betrieb, Zeitraum, Betreuung), Inhaltsverzeichnis,
      Bilder mit Bildunterschrift; "Stand <Datum>" steht immer im Kopf (für eine Abgabe abschaltbar machen).
    Details und Probeläufe: dokumente/STATUS.md.
35. Bedarf aus lia/auswertung an agentkit.claude_lauf (09.11.2026, nichts eilt): Der Prompt geht als Argument an
    claude -p. Linux erlaubt je Argument höchstens 128 KB (MAX_ARG_STRLEN), darüber bricht Popen mit „Argument list
    too long“ ab, bevor ein Lauf startet. Vorschlag: Prompt über stdin übergeben. Bis dahin teilt auswertung in
    Pakete unter 100 KB (luecken.pakete).
36. Bedarf aus lia/auswertung an shared/webapp und lia/chat (09.11.2026, Jan entscheidet die Reihenfolge): Lias
    claude.ai-Chats seit 24.10. (9 Chats, 188 Runden) zeigen, warum sie dort statt in der Web-App arbeitet. Größte
    Lücken nach Runden: langes Gespräch mit vollem Verlauf (99; heute 6 Fragen, Ortswechsel setzt zurück), lange
    Antworten mit Tabellen in breiter Ansicht (59), Fotos und Screenshots (39), Textbausteine im Chat verfeinern
    ohne Auftrag (39), Dateien dauerhaft an Reihe/Stunde (26), eigene Texte prüfen (22), mehrere Gespräche auch ohne
    Ort (19), Reihen selbst anlegen (19). Liste mit allen Lücken: lia/auswertung/STATUS.md, Belege nur auf dem Server
    (lia/auswertung/data/luecken/bericht.md). Ungeprüft durch Lia.
    Plan: docs/gespraech-plan.md (Gespräch in die Mitte der Web-App). Jans Entscheidungen 09.11.2026 (alle wie
    empfohlen): Gedächtnis über claude_lauf sitzung_fortsetzen, Read für Fotos mit Pfadgrenze, drei Spalten mit dem
    Gespräch in der Mitte, Kosten auf Lias Kontingent (Sonnet, gründlich je Gespräch), Aufbewahrung 30 Tage ab letzter
    Nachricht. Als Nächstes entsteht im shared/webapp-Chat die Klick-Attrappe für Lia; gebaut wird erst nach Lias Okay.
    Bedarf an agentkit (Plan Schritt 4.3.2): Read mit Pfadgrenze ist gebaut (unten); offen bleibt nur, falls nötig,
    Art "Projekt" in agentkit.struktur/strukturpflege.
    Jan 10.11.2026: Die echte Web-App wird jetzt umgebaut und echt getestet, ohne vorher Lias Okay (hebt 4.3 und
    „Modernist bis nach Lias Test“ auf). Bauplan: shared/webapp/bauplan-gespraech.md (Jans Okay 10.11.). Bedarf daraus,
    je im eigenen Chat (Jans Okay 10.11.): (a) Hauptordner/agentkit: Read mit Pfadgrenze, erledigt (unten); (b) lia/chat:
    Gespräch als Objekt mit Ebene (Klasse/Reihe/Stunde/ohne Ort), Sitzung fortsetzen, Fotos über Read, Ablage
    `lia/instanz/ablage/<ort-id>/` als Kontext, Bausteine im Prompt, „Was haben wir bisher?“, „Auftrag ordnen“.
    Schnittstelle siehe Bauplan Abschnitt 1.
    Read mit Pfadgrenze (10.11.2026, claude 2.1.304): `claude_lauf.laufen(..., lese_ordner=[ordner, ...])`. Dann hat
    Claude nur Read, Modus dontAsk, allow nur `Read(//<ordner>/**)`, deny Bash/Edit/Write/Grep/Glob/NotebookEdit
    und `.env`/`.env.*` je Ordner; Antwort nur als Text. WebSearch/WebFetch kommen dazu, wenn sie für den Agenten
    unter [werkzeuge] stehen (WebFetch weiter nur auf [webfetch]); sonst sind auch sie gesperrt (Bedarf lia/chat:
    alle Gesprächsläufe mit lese_ordner, Häkchen „Im Netz nachsehen“ bleibt). claude läuft dabei im leeren Ordner
    `<agent>/data/nur_lesen/` (Lesen im Arbeitsordner erlaubt claude -p sonst immer von selbst, auch in dontAsk;
    Probe: geheim.txt im Agent-Ordner war mit cwd = Agent-Ordner lesbar). Python prüft die Ordner vorher
    (`lese_ordner_pruefen`: absolut, vorhanden, aufgelöst, nicht `/`, keine Musterzeichen, enthält nicht den
    Agent-Ordner) und startet nicht, wenn in nur_lesen/ etwas liegt. Sitzungen führt claude je Arbeitsordner: Fortsetzen
    geht nur zwischen Läufen mit lese_ordner (geprüft: Sitzung angelegt, fortgesetzt, Antwort aus dem Verlauf).
    Echter Lauf im Scratchpad (Probe-Agent, Konto token, sonnet, 0,02 USD), Aufruf
    `laufen("probe", <probe>, prompt, lese_ordner=[<probe>/data/gespraeche/g1, <ablage>/ort-1])`, Ausgabe gekürzt:
    bild.png (64x64, roter Kreis, blaues Quadrat) „Lesen ging, roter Kreis links neben blauem Quadrat“;
    ablage/ort-1/notiz.txt gelesen; verweigert (permission_denials): probe/geheim.txt (Agent-Ordner), g1/link.txt
    (Symlink im erlaubten Ordner auf geheim.txt), g1/.env, g1/.env.lokal. Befund dabei: `Read(**/.env)` aus VERBOTEN
    greift nur unterhalb des Arbeitsordners; im ersten Lauf ohne eigene Sperre war g1/.env lesbar, darum die
    absolute Sperre je Ordner. Zweiter echter Lauf mit [werkzeuge] Read/WebSearch/WebFetch und [webfetch] bpb.de
    (0,05 USD): Bild beschrieben, bpb.de abgerufen, WebSearch ging; verweigert: WebFetch example.com, Read
    probe/geheim.txt. Tests ohne Netz: agentkit/tests/test_claude_lauf.py (test_nur_lesen_*).
37. Bedarf aus der Probe der Web-App (10.11.2026, Jan, Test-Instanz, Bauplan-Schritt 7 abgebrochen): Das Gespräch
    in der Mitte ist zu starr und überfordernd. Jan: Es soll sein wie eine Claude-Code-Sitzung. Befund: Claude bekommt
    je Nachricht nur einen Ortstext (Fach, Klasse, Reihe, Lerngruppe, Notizen), liest keine Dateien (nur Fotos und auf
    Wunsch das Netz), kann nichts tun außer Text, kennt die Agenten nicht; „Daraus Auftrag machen“ füllt nur das
    Formular der festen Auftragsarten. Jans Zielbild:
    - Kennt alles, was zum Ort gehört: liest und sucht in Lias Instanz (reihen.toml, Entwürfe, Fassungen, Ablage,
      Regeln) und in den Ergebnissen der Agenten. Antwortet aus dem Ort heraus, z. B. „laut Reihenentwurf ist für
      diese Stunde … angedacht“ oder „diese Stunde hängt an keiner Reihe: an Straftheorien hängen oder gleich eine
      neue Reihe mit Stunden entwerfen?“.
    - Handelt im Gespräch, nicht über Knöpfe (Jan: „willst du 1000 Knöpfe entwickeln“, auch „Als Reihenfrage
      übernehmen“ ist schon zu starr): Lia sagt es, Claude macht es. Mit „Claude denkt, Python handelt“ vereinbar über
      wenige allgemeine Werkzeuge, die Python bereitstellt und prüft (Idee, ungeprüft: eigener MCP-Server in
      agentkit), etwa Struktur ändern über strukturpflege mit Rückgängig, Datei ablegen, Auftrag an einen Agenten
      geben. Nach außen weiter nur über die Freigabe.
    - Flexible Agenten statt fester Auftragsarten: Agenten beschreiben ihre Fähigkeiten, Claude prüft im Gespräch, ob
      ein Auftrag damit geht. Fehlt etwas, sagt er es und macht daraus einen kleinen Ausbau-Auftrag an eine
      Claude-Code-Sitzung im zuständigen Ordner, mit Jans Zustimmung.
    - Lernt von Lia und verbessert sich selbst (aufbauend auf agentkit.feedback), zunehmend automatisierter Betrieb.
    Berührt CLAUDE.md (Architektur, „Agenten ändern keinen Code“), agentkit.claude_lauf (Werkzeuge über Read hinaus),
    lia/chat und shared/webapp. Plan: docs/gespraech-flexibel-plan.md (10.11.2026, Entscheidungen bei Jan, Abschnitt
    8). Jans Antworten 10.11.: überfordernd war alles (Länge, Gliederung, Oberfläche ringsum, dass Claude nichts tun
    kann); unintuitiv sind alle Bearbeiten-Flächen (Stunden, Reihen und Klassen, Ablage, Masken), Wunsch Drag and
    Drop. Probe 10.11. (claude 2.1.304): Grep/Glob halten die Read-Pfadgrenze, eigener MCP-Server mit Bordmitteln
    geht mit claude -p (allow/deny je Werkzeug). Dieser Plan ruht: Lia (über Jan, 10.11.) störte vor allem, dass
    kleine Änderungen an Dokumenten ewig dauern (Nachbesserungen 7–67 min) und dass schnelle Dokumente anderer Art
    fehlen. Neuer Plan dafür: docs/schnell-dokument-plan.md (Agent lia/schnell, Entscheidungen bei Jan, Abschnitt 6).
    Stand Web-App: Umbau gebaut, nicht umgeschaltet, webapp.service zeigt
    weiter die alte Oberfläche; Bau dort ruht bis zum Plan. Testhinweis: Die Test-Instanz der Web-App hat eine eigene
    reihen.toml, lia/chat liest immer lia/instanz; neu angelegte Test-Orte kennt Claude darum nicht.

## Gelernte Regeln
- (noch keine)
