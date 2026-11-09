# Status: Agent finance

## Zweck
Macht zu jedem Thema, das Jan schickt, eine eigene neue Recherche zur Wirtschaftlichkeit: wo in der
Wertschöpfungskette heute Gewinn anfällt, wo Angebot und Nachfrage auseinanderliegen, und höchstens drei
geprüfte Geschäftshypothesen. Erstes Thema: „Robotik und KI allgemein und in der Holzindustrie“.

## Stand (07.11.2026)
- Gerüst aus shared/vorlagen/ angelegt (Hauptordner-Chat): agent.py (Beispielgerüst: Freigaben ausführen,
  Aufträge abarbeiten, Recherche fehlt noch), systemd/finance.service (Vorlage, nicht installiert),
  tests/test_geruest.py.
- Noch nicht da: .venv, .env, data/, Dienst, Timer, eigentliche Recherche.
- Schon eingerichtet außerhalb des Ordners:
  - pruefen.sh: Eintrag `finance|python3|tests` (System-python3, weil es noch keine .venv gibt).
  - shared/einstellungen.toml: [werkzeuge] finance = Read, Write, Edit, Glob, Grep, WebSearch, WebFetch.
    Kein Eintrag unter [webfetch] (WebFetch damit ohne Domaingrenze), keine [weitergabe]-Paare.
  - shared/telegram/logik.py: "finance" in AGENTEN. Die Zentrale nimmt `/finance <Thema>` erst an, wenn
    finance.service in ~/.config/systemd/user/ liegt und die Zentrale neu gestartet ist.
- Bau in diesem Chat (`/home/agent/agenten/finance`), Hauptordner-Chat hat nur vorbereitet.

## Auftrag (Jan 07.11.2026, gekürzt)
Je Thema eine eigene, neue Recherche in fünf Schritten:
1. Wertschöpfungskette zerlegen: wo heute Gewinn anfällt, Marge und Kapitalrendite aus echten Abschlüssen.
2. Lücken zwischen Angebot und Nachfrage aus Primärdaten belegen: Destatis GENESIS (Produktion,
   Kostenstruktur, Erzeugerpreise), Eurostat Prodcom und Comext, UN Comtrade, Thünen-Holzmarktbericht,
   IFR-Roboterdichte, dazu Ausschreibungen, Stellenanzeigen, Patente.
3. Je Lücke begründen, warum sie besteht und ob sie bleibt (Engpass, Five Forces, Zyklus); Marktgröße
   von unten rechnen.
4. Höchstens drei Hypothesen mit Zahlen, Annahmen samt Quelle, Szenarien, Sicherheitsgrad und vorher
   festgelegten Abbruchkriterien.
5. Externe Prüfung je Hypothese: Vergleichsfirmen, Rückrechnung an einem bekannten Fall, datierte Prognosen
   (werden später automatisch gegen die Statistik geprüft), Entwürfe für Kundengespräche und
   Angebotsanfragen über die Freigabe (shared/freigabe/).
Ausgabe: PDF-Bericht über den Renderer (Art zusammenfassung, ergebnis.pdf) und Modelltabelle als xlsx
(Art arbeitsmappe). Ohne Quelle keine Zahl; nicht Belegbares als Annahme markieren.

## Entscheidungen
- 07.11.2026: Ordnername bleibt `finance` (Jan).
- 07.11.2026: IFR nur mit frei zugänglichen Zahlen (Pressemitteilungen), alles andere als Annahme (Jan).
- 07.11.2026: Bundesanzeiger vorerst nicht nutzen (keine API, Abfrage gegen Automaten). Stattdessen
  Geschäftsberichte als PDF und Unternehmensregister; was so nicht belegbar ist, bleibt Lücke bzw. Annahme (Jan).
- 07.11.2026: Bau in eigenen Chats: der Hauptordner-Chat bereitet vor, dieser Chat baut (Jan).
- 07.11.2026: WebFetch ohne Domainliste, weil Geschäftsberichte auf beliebigen Firmenseiten liegen
  (Hauptordner-Chat; eine Liste unter [webfetch] finance kann Jan jederzeit verlangen).

## Geplanter Aufbau (Claude denkt, Python handelt)
- Auftrag per Telegram `/finance <Thema>`, eigener Dienst finance.service (oneshot, startet nach jedem
  Auftrag). Kein Timer für die Recherche.
- Python holt Primärdaten (GENESIS, Eurostat, UN Comtrade, TED, Jobsuche der Bundesagentur, EPO OPS) und
  speichert jede Abfrage mit Abrufdatum und URL in `data/quellen/` unter einer Quellen-ID.
  Für Webabrufe agentkit.abruf nutzen, nichts nachbauen.
- Claude recherchiert in mehreren Läufen über agentkit.claude_lauf, einer je Schritt (ein Lauf mit
  30 Schritten/15 Minuten aus [lauf] reicht nicht für alles), und schreibt je Schritt JSON. Jede Zahl trägt
  eine Quellen-ID oder die Markierung Annahme.
- Python prüft (getestete Funktionen ohne Netz):
  - Zahl ohne Quelle und ohne Annahme -> Ablehnung, Nachbesserung im selben Schritt.
  - Abgleich der Zahlen mit den gespeicherten Rohdaten.
  - Marktgröße nachrechnen (von unten).
  - Höchstens drei Hypothesen, jede mit Abbruchkriterien.
- Datierte Prognosen in `data/prognosen.json`; ein monatlicher Timer (eigene Unit) prüft sie gegen die
  Statistik und meldet das Ergebnis an Jan (agentkit.meldungen).
- Entwürfe für Kundengespräche und Angebotsanfragen nur über shared/freigabe/ (agentkit.freigabe),
  ausgeführt genau einmal nach Jans Freigabe.
- Bericht und Modelltabelle über shared/renderer (Art zusammenfassung -> PDF, Art arbeitsmappe -> xlsx),
  Format siehe shared/renderer/FORMAT.md.

## Offene Punkte
1. Konten und Schlüssel legt Jan selbst an und trägt sie in `finance/.env` ein (chmod 600, Vorlage
   `.env.example` im Repo, nur Namen ohne Werte): Destatis GENESIS, UN Comtrade, EPO OPS. Eurostat, TED und
   die Jobsuche der Bundesagentur prüfen, ob sie ohne Konto gehen.
   - `finance/.env` existiert (chmod 600) mit GENESIS_TOKEN, GENESIS_BENUTZER, GENESIS_PASSWORT,
     COMTRADE_KEY, EPO_OPS_KEY, EPO_OPS_SECRET. `.env.example` fehlt noch.
   - GENESIS fertig (09.11.2026): GENESIS_TOKEN eingetragen, Login-Check erfolgreich. Adresse jetzt
     `https://genesis.destatis.de/genesisWS/rest/2020/` (die alte www-genesis... leitet per 307 um).
     Anmeldung per POST mit Headern `username` = Token, `password` leer. Höchstens 3 parallele Anfragen,
     Anfragen über 15 Minuten werden sonst beendet.
   - UN Comtrade fertig (09.11.2026): COMTRADE_KEY eingetragen, Testabfrage erfolgreich
     (`https://comtradeapi.un.org/data/v1/get/C/A/HS?...`, Header `Ocp-Apim-Subscription-Key`).
     Achtung: die Abfrage DE/2023/HS 8479/Export/Welt lieferte 38 Zeilen statt einer (vermutlich Aufteilung
     nach Zollverfahren/Transportart, Beschreibungsfelder leer ohne includeDesc) - beim Bau klären.
   - Offen: EPO OPS (Jan), Prüfung Eurostat/TED/Jobsuche ohne Konto.
2. .venv anlegen: `python3 -m venv .venv`, agentkit per .pth (siehe ../STATUS.md, Stand), Pakete des
   Renderers laut shared/renderer/requirements.txt. Weitere Pakete nur nach Jans Okay, dann in
   requirements.txt. Danach in pruefen.sh `finance|python3|tests` auf `finance|.venv/bin/python|tests`
   umstellen (Bedarf an den Hauptordner-Chat, in ../STATUS.md eintragen) und tests/test_geruest.py ersetzen.
3. Dienst einrichten (nach Jans Okay): systemd/finance.service nach ~/.config/systemd/user/ kopieren,
   `systemctl --user daemon-reload`, dann die Zentrale neu starten, damit `/finance` erscheint.
   Monatlicher Prognose-Timer ebenso erst nach Jans Okay.
4. Kosten je Recherche nach dem ersten echten Lauf beziffern (agentkit.verbrauch).

## Gelernte Regeln
- (noch keine)
