# Status: Agent finance

## Zweck
Macht zu jedem Thema, das Jan schickt, eine eigene neue Recherche zur Wirtschaftlichkeit: wo in der
Wertschöpfungskette heute Gewinn anfällt, wo Angebot und Nachfrage auseinanderliegen, und höchstens drei
geprüfte Geschäftshypothesen. Erstes Thema: „Robotik und KI allgemein und in der Holzindustrie“.

## Stand (09.11.2026)
- Recherche-Ablauf gebaut und getestet (32 Tests grün, mit falschem Claude), aber noch NIE echt gelaufen:
  kein Dienst installiert, `/finance` kommt in der Zentrale noch nicht an.
- Zugänge: GENESIS und Comtrade in .env und getestet, EPO wartet auf Bestätigung (siehe Offene Punkte 1).
- .venv steht. pruefen.sh testet finance noch mit System-python3 (Umstellung beim Hauptordner-Chat), deshalb
  importieren ablauf.py, schritte.py, pruefung.py, quellen.py kein agentkit; agent.py schon (nur von Hand mit
  .venv geprüft: Import und echter Webabruf ok).
- Außerhalb des Ordners eingerichtet (Hauptordner-Chat): pruefen.sh `finance|python3|tests`;
  shared/einstellungen.toml [werkzeuge] finance = Read, Write, Edit, Glob, Grep, WebSearch, WebFetch (ohne
  [webfetch]-Liste, ohne [weitergabe]); "finance" in AGENTEN (shared/telegram/logik.py), wirkt erst mit
  installiertem finance.service und Neustart der Zentrale.

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
   - Ohne Konto geprüft (09.11.2026, je eine Testabfrage HTTP 200):
     Eurostat `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<datensatz>?...`;
     TED `POST https://api.ted.europa.eu/v3/notices/search` (JSON query, z. B. classification-cpv=42997300
     Industrieroboter: 2739 Treffer); Jobsuche BA `https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs`
     mit öffentlichem Header `X-API-Key: jobboerse-jobsuche` (v4 liefert 403; Treffer in `ergebnisliste`,
     Gesamtzahl `maxErgebnisse`).
   - Offen: EPO OPS (Jan trägt EPO_OPS_KEY und EPO_OPS_SECRET ein, danach Test).
2. .venv steht (09.11.2026): Pakete laut requirements.txt (= shared/renderer/requirements.txt), agentkit per
   .pth, Tests damit grün. Weitere Pakete nur nach Jans Okay. Offen: pruefen.sh noch auf `python3`, Umstellung
   auf `.venv/bin/python` ist in ../STATUS.md (Punkt 32) an den Hauptordner-Chat gemeldet. Danach einen Test
   für agent.py mit agentkit ergänzen (Warten bei LimitErreicht, Abschluss des Auftrags).
3. Dienst einrichten (nach Jans Okay): systemd/finance.service nach ~/.config/systemd/user/ kopieren,
   `systemctl --user daemon-reload`, dann die Zentrale neu starten, damit `/finance` erscheint.
   Monatlicher Prognose-Timer ebenso erst nach Jans Okay.
4. Kosten je Recherche nach dem ersten echten Lauf beziffern (agentkit.verbrauch).
5. pypdf für Geschäftsberichte als PDF: Paket fehlt in finance/.venv (uni hat pypdf==6.21.0). Nur nach Jans
   Okay installieren und in requirements.txt eintragen; bis dahin werden PDF-Webquellen abgelehnt.
6. `.env.example` (nur Namen) fehlt noch.

## Aufbau (gebaut 09.11.2026)
- agent.py: je Auftrag (Text = Thema) eine Recherche in data/recherchen/<auftrag-id>/; LimitErreicht,
  KeinPlatz, LaeuftSchon -> Auftrag wartet, fertige Schritte bleiben liegen und werden beim nächsten Lauf nur
  neu geprüft. web_laden: agentkit.abruf (GET, Allowlist = Host der URL, Cache data/cache), HTML als Text,
  PDF über agentkit.textfassung (braucht pypdf, fehlt -> WebFehler, siehe Offene Punkte 5).
  ausfuehren() für Freigaben: noch NotImplementedError, finance legt noch keine Entwürfe an.
- ablauf.py (ohne agentkit): fünf Schritte nacheinander, je Schritt ein claude-Lauf (art anspruchsvoll),
  dann Webquellen auflösen, Pflichtfelder und Zahlen prüfen; bei Fehlern bis zu zwei Nachbesserungen mit der
  Fehlerliste im Prompt, sonst Abbruch der Recherche. bericht_text = Kurztext an Jan (statt PDF, bis Renderer).
- schritte.py: Aufgaben, Gerüste und Prompt je Schritt, ZAHL_REGELN für Claude, Pflichtfelder je Schritt
  (2: je Lücke zwei Belege; 3: marktgroesse als berechnet/produkt; 5: Prognosen mit Zahl und Datum in der
  Zukunft, Entwürfe mit art/an/betreff/text). Webquelle = {"url", "zitat", "beschreibung"} statt Quellen-ID:
  Python lädt, prüft Zitat wörtlich (agentkit.wortlaut.steht_in) und Zahl im Zitat, legt als "web" ab und
  ersetzt durch die ID.
- pruefung.py: Zahl-Objekte {wert, einheit, quelle | annahme | berechnet}; nackte Zahlen sind Fehler (außer
  jahr, von_jahr, bis_jahr, nr); Abgleich mit Rohdaten (auch Tsd/Mio/Mrd, 0,5 %), Webquellen nur Hinweis;
  berechnet (produkt, quotient, summe, differenz) nachgerechnet (1 %); Hypothesen 1 bis 3 mit sicherheit,
  drei Szenarien, Abbruchkriterien mit Datum in der Zukunft.
- quellen.py: data/quellen/<ID>.json (Meta), <ID>.roh.<endung> (Rohinhalt), maßgeblich index.toml (art, endung,
  sha256; *.toml darf Claude nicht schreiben, so fällt Umdeklarieren oder Ändern auf).
  ID Q-<JJJJMMTT>-<art>-<6 hex>, Arten genesis, eurostat, comtrade, ted, jobsuche, epo, web.
- Tests: tests/test_quellen_pruefung.py, tests/test_ablauf.py (ohne Netz, ohne agentkit).

## Blockiert (Bedarf in ../STATUS.md, Punkt 32)
- Abrufer der Primärdaten (GENESIS, Comtrade, TED, Jobsuche): agentkit.abruf kann nur GET ohne Header.
  Nicht selbst nachbauen, Erweiterung im Hauptordner-Chat. Bis dahin liegen keine Primärdaten in data/quellen,
  Claude arbeitet mit Webquellen und Annahmen (Eurostat-API ginge per GET, ist aber noch nicht angebunden).
- PDF-Bericht und xlsx-Modell: Renderer-Arten passen nicht (zusammenfassung = Vorlesung, arbeitsmappe ohne
  Werte). Erweiterung im Renderer-Chat. Bis dahin nur bericht_text und die Schritt-JSONs.

## Nächste Schritte hier
1. Erster echter Probelauf von Hand, nur nach Jans Okay (5 bis 15 Läufe "anspruchsvoll"): Auftrag anlegen
   (agentkit.auftraege.neuer_auftrag("finance", "<Thema>", quelle="hand")), dann `.venv/bin/python agent.py`.
   Danach Prompts nach dem Ergebnis schärfen und Kosten beziffern (Offene Punkte 4).
2. Danach Dienst (Offene Punkte 3), Prognosen in data/prognosen.json und Timer, Entwürfe über die Freigabe.
3. Abrufer für Primärdaten, sobald agentkit.abruf POST/Header kann; Bericht, sobald der Renderer es kann.

## Gelernte Regeln
- (noch keine)
