# Status: Agent kleinanzeigen

## Zweck
Wie der alte Vinted-Bot (~/agents/vinted), nur für Kleinanzeigen und zum Schnappen guter Angebote:
Jan (und ein Kumpel) beschreibt oder fotografiert im eigenen Telegram-Bot, was er sucht. Der Bot prüft
laufend die neuesten Anzeigen und meldet gute Angebote sofort mit Link. Schreiben an Verkäufer macht der
Nutzer selbst, der Agent hat kein Kleinanzeigen-Konto und handelt nicht nach außen.

## Aus der Untersuchung 11/2026 (16.11.2026, Hauptordner-Chat mit Jans Okay)
- Die Bewertung läuft ohne Werkzeuge (bot.py, _lauf_cfg). Ein Test in tests/test_logik.py sichert das ab.
- Offen bei Jan: Ausnahme in CLAUDE.md für den eigenen Bot und Treffer ohne Freigabe.

## Stand (15.11.2026)
- Läuft als Dauerdienst kleinanzeigen.service (systemd-User, enabled), Bot @klnanzgnbot. Erste echte Suche von
  Jan hat einen Treffer geliefert.
- .venv mit httpx und python-telegram-bot[job-queue] (Versionen wie die Zentrale), agentkit per .pth.
- .env (chmod 600): Token eingetragen, ERLAUBTE_CHAT_IDS = nur Jan. Der Kumpel fehlt noch.
- Tests in pruefen.sh eingetragen (Jan 15.11.2026).

## Aufbau
- bot.py: Telegram (Dauerdienst), Takt, Claude-Aufrufe über agentkit.claude_lauf (art routine = Sonnet,
  in Stufe sparen Haiku). Dünn, ohne eigene Logik.
- abruf.py: httpx, nur lesend, mind. 3-5 s Pause zwischen Abrufen.
- seite.py: Suchseite lesen (Anzeigen stehen als Astro-JSON im props-Attribut des ImpressionTracker), URL bauen.
- vorfilter.py: schon gesehen, Gesuche, alte Top-Anzeigen, Preis, Ausschlusswörter; Marktpreis (Median).
- bewertung.py: Prompts (Suche anlegen, Anzeigen bewerten) und strenge Prüfung der JSON-Antwort.
- pruefung.py: ein Durchgang je Suche (Anzeigen rein, Telegram-Texte raus), eingabe.py, texte.py, db.py (SQLite).
- Tests: tests/test_logik.py mit tests/daten/suchseite.html (gekürzte echte Seite).
- Laufzeit: data/kleinanzeigen.db, data/fotos/ (nach der Analyse gelöscht), logs/kleinanzeigen.log.

## Ablauf
1. Text oder Foto -> Claude macht Titel, 1-2 kurze Suchbegriffe, Ausschlusswörter, Marktwert (1 Lauf).
2. Antwort mit Preisgrenze/Ort ("80 € 30 km 34128", "80 €", "egal") -> Suche aktiv, erster Durchgang sofort.
3. Alle TAKT_MIN (5) min, außer Nachtruhe 1-6 Uhr: je Suchbegriff eine Seite, neueste zuerst, mit Preis und
   Umkreis in der URL. Nur neue Kandidaten gehen gebündelt an Claude (max. 25 je Lauf), Meldung ab 70 Punkten.
4. Tagesgrenze 100 Läufe (beide Nutzer): danach und wenn Claude pausiert ist (Stufe nur_auftraege, Limit) nur
   Anzeigen <= 60 % des Marktwerts, ohne Bewertung. In Stufe sparen entfällt jeder zweite Lauf, die Kandidaten
   bleiben offen und kommen im nächsten Takt dran.
5. /suchen: je Suche Pausieren/Fortsetzen und Löschen. Fremde Chats bekommen auf /start nur ihre Chat-ID.

## Wissen über Kleinanzeigen (15.11.2026)
- URL: /s-<plz>/sortierung:neuste/preis::<max>/<begriff>/k0l<ort_id>r<km>. Reihenfolge ist fest, sonst kommt
  eine Seite ohne Liste. "neuste" ohne e. Orts-ID: /s-ort-empfehlungen.json?query=<plz> -> {"_4927": "34128 Kassel"}.
- Mit Datumssortierung zeigt die Seite bei zu engen Begriffen "Es wurden keine Ergebnisse ..." statt Ersatztreffern.
  Darum soll Claude breite Begriffe wählen, die Feinheiten prüft die Bewertung.
- Abrufe vom Server ohne Captcha; Drosselung bei Dauerbetrieb noch nicht beobachtet (Störung wird einmal gemeldet).

## Entscheidungen
- 15.11.2026 (Jan): Kein Kleinanzeigen-Konto, nur scannen und Link schicken.
- 15.11.2026 (Jan): Sonnet bewertet (ca. 75 USD/Monat API-Gegenwert). Teilagent des geplanten Agenten einkauf.
- 15.11.2026 (Jan): Eigener Telegram-Bot, weil ein Kumpel mitnutzt. Token nur aus kleinanzeigen/.env, nie aus
  shared/.env (dort steht der Token der Zentrale unter demselben Namen).
- 15.11.2026 (Jan): Zum Schnappen guter Angebote. Daher Takt 5 statt 15 min, neueste zuerst, Schwelle 70.

## Offene Punkte
1. Kumpel: schickt @klnanzgnbot /start, seine ID steht dann im Log ("Unbekannter Chat ...") und in der DB
   (werte: fremd_<id>). Mit Komma an ERLAUBTE_CHAT_IDS anhängen, dann systemctl --user restart kleinanzeigen.
2. Nach ein paar Tagen Betrieb: Kosten (shared/verbrauch) und Meldungsqualität prüfen, ggf. Schwelle/Takt anpassen.
3. Ordner: als Teilagent von einkauf später ggf. nach einkauf/kleinanzeigen verschieben.

## Betrieb
- systemctl --user status kleinanzeigen / journalctl --user -u kleinanzeigen -f / logs/kleinanzeigen.log
- Nach Änderungen an .env oder Python-Code: systemctl --user restart kleinanzeigen.

## Gelernte Regeln
- (noch keine)
