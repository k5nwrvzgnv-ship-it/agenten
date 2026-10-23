# Status: Gesamtsystem (Architekt)

Aktueller Stand, kein Verlauf. Wie es dazu kam: `git log`. Architektur und Konventionen: CLAUDE.md.

## Stand (22.10.2026)
- Übersicht, wo was liegt, welche Dienste laufen und welcher Chat wohin gehört: README.md
  (aufgeräumt 21.10.: lia/instanz statt lia/shared, Dienst-Vorlagen je Ordner in systemd/).
- Server: 7,8 GB RAM, 4 Kerne, 90 GB frei, Python 3.12, Node 22, kein Docker, kein sudo.
  Alles unter User `agent` in /home/agent/agenten, Dienste als systemd-User-Units.
- agentkit (shared/agentkit/) fertig und getestet: config, log, einstellungen, auftraege, freigabe,
  meldungen, regeln, verbrauch, claude_lauf, textfassung, kalender. Doku steht jeweils oben im Modul.
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
- Verbrauch: Jan hat ein Pro-Abo, Agenten teilen es mit seinen Chats. Stufen normal/sparen/
  nur_auftraege/limit nach 5h- und 7d-Auslastung, Werte in shared/einstellungen.toml.
  Einschränkung: Auslastung wird nur bei Agenten-Läufen aktualisiert.
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
  Entwürfe ebenso: "<b>Uni</b> · Mail-Entwurf", Titel, Inhalt, Details als Zeilen (nichts gekürzt).
- Ausfallmeldung (21.10.): Jede Unit trägt OnFailure=ausfall@%n.service (Vorlage
  shared/systemd/ausfall@.service, eingerichtet). agentkit.ausfall schickt "Störung" fett, Dienst und Grund in
  Worten (oom-kill = zu wenig Arbeitsspeicher), ohne Journal-Zeilen, direkt per Telegram, sonst über
  shared/meldungen/. Höchstens eine Meldung je Unit in 6 h (shared/ausfall/stand.json). Mit
  Test-Unit geprüft: kam an. Eingerichtet für uni, uni-transkript, agentenzentrale; uni-lernen und
  dokumente haben es in der Vorlage. Grenze: agentenzentrale hat Restart=on-failure und gilt nie als
  fehlgeschlagen, solange der Neustart klappt. Nicht erkannt: Timer, die gar nicht mehr starten.

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
   /revoke optional); Lia nutzt Jans Pro-Abo (teilt das Kontingent, Schuldaten liefen über Jans
   Konto, siehe Abschnitt 0); agentkit als Paket erst beim Umzug zu einem User lia.
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
     nebenbei einspielen.
   Vorbehalt Datenschutz: Mail- und IServ-Teil erst nach Klärung mit der Schule (Abschnitt 0).

## Gelernte Regeln
- (noch keine)
