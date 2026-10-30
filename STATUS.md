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

24. Web-App für Lia und weitere Lehrerinnen (Entwurf 29.10.2026, Bauschritt 1 und Ansichten gebaut 30.10.): docs/webapp-plan.md, Prototyp
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
   - Ordnung nach Fach, Klasse und Reihe (Jans Wunsch und Okay 30.10., gebaut): „Heute“ mit Chips Alle, Ethik,
     Theater, Ohne Reihe; Ansicht /unterricht (Fach, Klasse oder Kurs, Reihe mit Entwürfen und Aufträgen);
     Auswahl der Reihe beim Neuen Auftrag (Testbetrieb). Zuordnung nur über das neue optionale Feld reihe in
     agentkit.auftraege.neuer_auftrag oder den Agenten (theater -> Theater Kurs 11, examen -> Ethik 8
     Straftheorien), sonst „ohne Reihe“. Entschieden: Fach heißt „Theater“, Theater-Reihe „Der nackte Wahnsinn“,
     Kurs 11; Reihen pflegt vorerst Jan, Lia erst mit Konten.
   - Bedarf an den lia/unterricht-Chat (Jan 30.10.): EINE Datei lia/instanz/reihen.toml für App und Agenten. Bitte
     lia/unterricht/reihen.toml dorthin verschieben, reihen.py und lia/examen (titel_in_reihen_toml) umstellen,
     Felder id, stand (laufend/abgeschlossen) und agenten erlauben und den Theater-Kurs eintragen
     (fach "Theater", klasse "Kurs 11", titel "Der nackte Wahnsinn", agenten ["theater"]); Format in
     shared/webapp/ordnung.py. Bis dahin setzt die App die Reihen aus unterricht/examen/theater zusammen.
     Später: Feld reihe des Auftrags bevorzugt nutzen, statt selbst eine Reihe zu wählen (heute steht sie als
     Zeile „Reihe: …“ am Ende des Auftragstexts).
   - Neuplanung Desktop zuerst (Jan 30.10., nur Plan): docs/webapp-aufbau.md, klickbares Board „Desktop“ und
     „Handy-Prüfung“ im Canvas. Drei Spalten Baum | Inhalt | Fragen (Chat), Vorlagengalerie am Ort, final setzt
     Lia, eigene Fassung hochladen. Chips und /unterricht sollen entfallen. Gebaut wird erst nach Lias Test
     (7 Aufgaben, Ziel 6 von 7 ohne Hilfe, Jan leitet) und Jans Okay. Jan klärt vorher: Fachname „Darstellendes
     Spiel“ statt „Theater“? Welche Programme nutzt Lia am PC? Gibt es Kurs 12, für welche Klasse ist die
     Notentabelle?
   - Bedarf an lia/ aus der Neuplanung (erst nach dem Test, nicht vorher bauen):
     a) lia/unterricht: Stunden je Reihe (Nummer, Thema, Marke UB/Prüfung) in lia/instanz/reihen.toml oder einer
        Datei je Reihe; Agenten bekommen beim Auftrag an einer Stunde Reihe und Stunde als Kontext.
     b) alle Material-Agenten: Nachbesserung auf Grundlage einer von Lia hochgeladenen Fassung (Word mit
        Kommentaren) als Fassung desselben Auftrags (bezug), nicht als neuer Auftrag.
     c) Chat-Agent für Lia (eigener Ordner lia/chat/ oder Teil von unterricht): kurze Antworten über
        agentkit.claude_lauf, Kontext des Orts aus Dateien (Fach, Klasse mit Lerngruppe, Reihe, Stunden, Regeln),
        kleines Modell für schnelle Fragen, kein Starten von Aufträgen, keine Schülernamen, Verlauf befristet.
     d) agentkit: Zustand „final“ einer Fassung und „eigene Fassung“ (oder die Web-App speichert es selbst nach
        den Konten), Entscheidung im Hauptordner-Chat.
   - Bedarf an shared/renderer: Lage jedes Blocks auf der Vorschauseite mitliefern (für Anmerkungen an einer Stelle).
   - Playwright auf dem Server braucht Systembibliotheken (libatk-1.0 fehlt, geprüft 29.10.), also root.

## Gelernte Regeln
- (noch keine)
