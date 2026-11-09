# Status: Agent finance

## Zweck
Macht zu jedem Thema, das Jan schickt, eine eigene neue Recherche zur Wirtschaftlichkeit: wo in der
Wertschöpfungskette heute Gewinn anfällt, wo Angebot und Nachfrage auseinanderliegen, und höchstens drei
geprüfte Geschäftshypothesen. Erstes Thema: „Robotik und KI allgemein und in der Holzindustrie“.
Zweite Variante (Jan 09.11.2026): `/finance aktien: <Thema>` recherchiert Anlagemöglichkeiten (Firmen, ETFs,
Bewertung, höchstens drei Anlagethesen). Keine Käufe, keine Entwürfe nach außen.

## Stand (09.11.2026, abends)
- Läuft als Dienst: finance.service liegt in ~/.config/systemd/user/ (oneshot, kein Timer), Zentrale neu
  gestartet; `/finance <Thema>` wird angenommen und startet den Dienst. Probestart ohne Auftrag fehlerfrei.
- pypdf==6.21.0 in .venv und requirements.txt (Jan 09.11.); web_laden liest echte Geschäftsberichte als PDF
  (geprüft mit Hermle GB 2024, 283.000 Zeichen Text).
- Primärdaten angebunden (abrufer.py): GENESIS, Eurostat, Comtrade, TED, Jobsuche, EPO; je einmal echt geprüft
  (EPO 09.11.2026: drei Suchen, eine ohne Treffer, keine Geheimnisse in Ablage oder Cache).
- Bericht als PDF (Renderer-Art bericht) und Modell als xlsx (arbeitsmappe) entstehen ohne Claude aus den
  geprüften Schritten und gehen mit dem Ergebnis an Jan.
- 74 Tests grün, pruefen.sh testet finance mit .venv/bin/python.

## Variante aktien (gebaut 09.11.2026, Jan: "Erst Agent erweitern", "Ja, so bauen")
- Auslöser: Auftragstext beginnt mit "aktien:" (auch aktie/invest/investment/anlage), schritte.variante_aus_text.
  Ohne Präfix wie bisher MARKT. Die Zentrale bleibt unverändert.
- Schritte (schritte.SCHRITTE_AKTIEN): 1 Auswahl und Gewinnverteilung (höchstens 15 Firmen mit Yahoo-Symbol und
  ggf. SEC-CIK, höchstens 5 ETFs), dann Primärdaten OHNE Claude (ablauf.primaerdaten_aktien: je Firma Kurs, mit
  CIK SEC-Abschlüsse, je ETF Kurs, danach Eurostat-Wechselkurse ert_bil_eur_a der vorkommenden Währungen;
  Python schreibt uebersicht.json mit Werten und Quellen-IDs), 2 Kennzahlen und Bewertung (Marge, Wachstum, FCF,
  Marktkapitalisierung, KGV, FCF-Rendite als berechnet), 3 Was der Kurs einpreist (geforderte Rendite minus
  FCF-Rendite, höchstens 8 Firmen), 4 Anlagethesen (instrumente, gegenargument, risiken, rendite_pa je Szenario,
  Abbruchkriterien), 5 Gegenprüfung (Vergleich, Rückrechnung, 1 bis 3 Prognosen, keine Entwürfe).
- abrufer.py: Arten sec (data.sec.gov companyfacts, abgelegt wird ein Auszug: 11 Kennzahlen, letzte 6
  Geschäftsjahre aus 10-K/20-F/40-F, ausstehende Aktien) und kurs (Yahoo chart, 5 Jahre Monatsschluss, Auszug).
  Echt geprüft mit NVIDIA und ASML (SEC) sowie NVDA und 6954.T (Kurs). Stooq geht nicht (Browser-Prüfung).
- bericht.py: _bloecke_aktien (Rubrik Anlagemöglichkeiten, Hinweis "Keine Anlageberatung") und modell_aktien
  (Blätter Bewertung und Szenarien mit Einsatz/Ertrag).
- Offen: SEC verlangt eine Kontaktangabe im User-Agent (abrufer.SEC_AGENT hat keine); Jan hat noch keine
  genannt. Yahoo ist inoffiziell (Jan: genehmigt) und kann wegfallen.

## Erster echter Lauf (09.11.2026, Auftrag 20261109-133235-finance-4fdc5f, Thema Robotik und KI/Holzindustrie)
- Vor Abrufern und Bericht gestartet, also nur Webquellen und Annahmen. Schritte 1 bis 4 bestanden, Schritt 5
  scheiterte: Lauf erreichte die Grenze von 30 Arbeitsschritten, bevor schritt5.json geschrieben war.
- Ergebnis: 13 Webquellen mit wörtlichem Zitat (NVIDIA, ABB, Teradyne, Dürr, Stora Enso, West Fraser, IFR, EPO,
  BA, Holzbau-Lagebericht über Presseindex u. a.), 57 Annahmen, 5 Lücken mit Marktgröße von unten, 2 Hypothesen
  (Arbeitsvorbereitung/Abbunddaten als Dienst für Zimmereien, Sicherheit mittel; Nachrüstung und Service-Abos für
  Holzbearbeitungsmaschinen, niedrig), je mit Abbruchkriterien 2027. Bericht und Modell nachträglich gebaut:
  data/recherchen/20261109-133235-finance-4fdc5f/bericht-vorschau/bericht.pdf und modell.xlsx.
- Schwächen: keine Primärdaten; PDFs gemieden ("nicht wörtlich zitierbar"); mehrere Zweitquellen (finviz,
  inderes, Presseindex); Marktgrößen hängen je an zwei Annahmen (Anteil mit Bedarf, Preis); Jahreszahlen als
  Wort ausgeschrieben. Daraufhin geschärft (schritte.py, mit Tests): Arbeitsweise mit Grenze der
  Arbeitsschritte (Datei früh schreiben), Originalquellen vor Portalen, PDF mit kurzem Zitat, Anteil und Preis
  möglichst belegen, Schritt 5 enger (je Hypothese höchstens 2 Vergleichsfirmen, 5 neue Webseiten insgesamt),
  Jahreszahlen in Ziffern. Ein Lauf ohne Ergebnis zählt jetzt als Versuch (Nachbesserung mit Hinweis).
- Kosten (agentkit.verbrauch, rechnerisch, Jans Abo): 8 Läufe opus, 7,27 USD, 17 Minuten für 4 Schritte
  (0,22 bis 1,68 USD je Lauf; Schritt 1 brauchte 3 Läufe, Schritt 4 zwei). Schätzung für eine vollständige
  Recherche mit Primärdaten und Schritt 5: 9 bis 12 USD (zweiter Lauf: tatsächlich 5,97 USD).
  Wochenkontingent stieg in diesem Lauf von 93 auf 95 % (Stufe nur_auftraege); eine Recherche kostet also
  rund 2 % des 7-Tage-Fensters.

## Zweiter Lauf (09.11.2026, Jan: "Jetzt starten", Auftrag 20261109-142143-finance-b3c246, gleiches Thema)
- Wie /finance angelegt (quelle telegram) und über finance.service gestartet. Vollständig: alle 5 Schritte
  bestanden, jeder im ersten Versuch; Zentrale hat Text, bericht.pdf (19 Seiten Vorschau) und modell.xlsx an Jan
  geschickt (gemeldet.json).
- Primärdaten genutzt: 12 von 12 Abfragen geladen (5 Eurostat, 3 Comtrade, 2 TED, 2 Jobsuche), daraus 32
  Belege in Schritt 2 bis 4 (Schritt 2: 18 von 29 Belegen). GENESIS nicht genutzt (Claude wählte Eurostat),
  Schritt 1 und 5 nur Webquellen.
- Hypothesen: Robotik-Integration und Service für Betriebe ohne eigenes Robotik-Personal (Sicherheit mittel);
  robotergestützte Lohn-Vorfertigung für Zimmereien (niedrig). Schritt 5: je 2 Vergleichsfirmen, Rückrechnung,
  5 datierte Prognosen (Eurostat sts_inpr_a/sts_inppd_a, Jobsuche; prüfen ab 30.06. bzw. 09.11.2027),
  4 Entwürfe (nicht angelegt in der Freigabe, siehe Nächste Schritte).
- Kosten: 6 Läufe opus, 5,97 USD, 17 Minuten. Wochenkontingent 95 -> 98 % (rund 3 % je Recherche).
- Schwächen: dieselben 14 Webseiten wie im ersten Lauf, weiter Zweitquellen (finviz, inderes, Presseindex,
  Tagesspiegel, gehalt.de) und keine PDF trotz Prompt; 68 Annahmen, Marktgrößen hängen weiter an Anteil und
  Preis. Ergebnistext löste Befunde der Sprachprüfung aus (Läufe, Pfad, Hypothese(n)); gekürzt, Lesbarkeit
  bleibt wegen langer Hypothesentitel über dem Ziel.

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
Ausgabe: PDF-Bericht über den Renderer (Art bericht, ergebnis.pdf) und Modelltabelle als xlsx
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
- Bericht und Modelltabelle über shared/renderer (Art bericht -> PDF, Art arbeitsmappe -> xlsx), gebaut
  in bericht.py; Format siehe shared/renderer/FORMAT.md.

## Zugänge und Schnittstellen
- EPO OPS (09.11.2026): Abfrage-Art epo mit begriffe (Titel/Kurzfassung), anmelder, cpc, land, von_jahr,
  bis_jahr. agent.epo_token holt den Token (Basic-Auth Key:Secret, nur Wegwerf-Cache, 15 Min. im Speicher),
  Suche über published-data/search/biblio, abgelegt wird ein Auszug (Trefferzahl, erste 25 mit Titel,
  Anmelder, CPC, Familie). Keine Treffer = HTTP 404, wird als Quelle mit 0 Treffern abgelegt. Höchstens
  4 EPO-Abfragen je Liste (OPS drosselt die Suche, Header x-throttling-control: search=green:5).
  Trefferzahl zählt Veröffentlichungen, nicht Erfindungen (eine Familie kann viele Länder haben).
- `finance/.env` (chmod 600): GENESIS_TOKEN, GENESIS_BENUTZER, GENESIS_PASSWORT, COMTRADE_KEY, EPO_OPS_KEY,
  EPO_OPS_SECRET. EPO-Werte eingetragen 09.11.2026, Test ok (Token über
  `POST https://ops.epo.org/3.2/auth/accesstoken`, Basic-Auth Key:Secret, grant_type=client_credentials, gilt
  20 Min.; Suche `GET /3.2/rest-services/published-data/search?q=...` liefert XML, Header x-throttling-control beachten).
- GENESIS: `POST https://genesis.destatis.de/genesisWS/rest/2020/data/tablefile`, Header `username` = Token,
  `password` leer, Formular name/startyear/endyear/format=ffcsv; Antwort ZIP mit CSV, Fehler als JSON
  (Status.Code, z. B. 104 = keine Objekte). Höchstens 3 parallele Anfragen, über 15 Minuten wird beendet.
  Tabellensuche ginge über `find/find` (term, category=tables), ist nicht angebunden.
- UN Comtrade: `GET https://comtradeapi.un.org/data/v1/get/C/A/HS?...`, Header `Ocp-Apim-Subscription-Key`.
  Mit partner2Code=0, customsCode=C00, motCode=0 genau eine Zeile (sonst eine je Zollverfahren/Transportart).
- Eurostat (ohne Konto): `GET https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<datensatz>?...`
- TED (ohne Konto): `POST https://api.ted.europa.eu/v3/notices/search`, JSON {query, fields, limit}; Gesamtzahl in
  totalNoticeCount. Jede Meldung trägt Links in 24 Sprachen, daher limit 10.
- Jobsuche BA (ohne Konto): `GET https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs`, Header
  `X-API-Key: jobboerse-jobsuche` (öffentlich), Gesamtzahl maxErgebnisse.
- Dienst: systemd/finance.service (Vorlage) = ~/.config/systemd/user/finance.service. Nach Änderung der Vorlage:
  kopieren, `systemctl --user daemon-reload`. Neue Pakete nur nach Jans Okay.

## Aufbau (gebaut 09.11.2026)
- agent.py: je Auftrag (Text = Thema) eine Recherche in data/recherchen/<auftrag-id>/; LimitErreicht,
  KeinPlatz, LaeuftSchon -> Auftrag wartet, fertige Schritte bleiben liegen und werden beim nächsten Lauf nur
  neu geprüft. web_laden: agentkit.abruf (GET, Allowlist = Host der URL, Cache data/cache), HTML als Text,
  PDF über agentkit.textfassung (braucht pypdf, fehlt -> WebFehler, siehe Offene Punkte 5).
  ausfuehren() für Freigaben: noch NotImplementedError, finance legt noch keine Entwürfe an.
- ablauf.py (ohne agentkit): fünf Schritte nacheinander, je Schritt ein claude-Lauf (art anspruchsvoll),
  dann Webquellen auflösen, Pflichtfelder und Zahlen prüfen; bei Fehlern (auch Lauf ohne Ergebnis) bis zu zwei
  Nachbesserungen mit der Fehlerliste im Prompt, sonst Abbruch der Recherche. Zwischen Schritt 1 und 2 Phase
  Primärdaten (Ergebnis nr 0): Claude schreibt abfragen.json (6 bis 12, höchstens 15), Python führt aus, ein
  Nachbesserungslauf für fehlgeschlagene; Ergebnis in abfragen_ergebnis.json (liegt sie vor, wird die Phase
  übersprungen); bricht nie ab. bericht_text = Kurztext an Jan.
- abrufer.py (ohne Netz): Abfrage-Formate je Art (Docstring), strenge Prüfung (nur Codes, Ziffern, Datum),
  Anfrage bauen, Antwort prüfen (GENESIS: ZIP -> CSV, Fehler-JSON; Comtrade mit partner2Code/customsCode/motCode
  = genau eine Zeile; TED limit 10, Gesamtzahl totalNoticeCount; Jobsuche maxErgebnisse).
- bericht.py (ohne Netz, ohne Claude): Beschreibung Art bericht (Abschnitte je Schritt, Zahlen als Tabellen-
  zellen mit Quellen-ID oder [Annahme], Quellen-IDs aus Fließtext entfernt, Quellenverzeichnis aus data/quellen,
  offene_punkte aus Schritt 1 als offene Fragen, Hinweis bei Abbruch) und Art arbeitsmappe (Blatt Marktgröße:
  bis 4 Faktoren, Excel multipliziert; Blatt Szenarien mit Marge).
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
- Tests: test_quellen_pruefung, test_ablauf, test_abrufer, test_bericht (ohne Netz), test_agent (mit agentkit,
  falsches Laden), test_geruest.

## Dritter Lauf (09.11.2026, Variante aktien, Auftrag 20261109-162430-finance-fa0f3f)
- Thema "Robotik und KI – Unternehmen und Investmentmöglichkeiten". Alle 5 Schritte bestanden. Nach Schritt 3
  pausiert (5h-Kontingent 101 %), um 18:02 von Hand neu gestartet, um 18:10 fertig. Die Zentrale hat das Ergebnis
  gemeldet (bericht.pdf mit 21 Seiten Vorschau, modell.xlsx).
- Primärdaten: 33 von 33 Abfragen geladen (15 Firmen, 5 ETFs, 4 Wechselkurse); 40 Quellen, davon 33 aus
  Abschlüssen und Kursen; 57 Annahmen. In Schritt 2 bewertet: NVIDIA, TSMC, ASML, Teradyne, Cognex, Intuitive,
  Alphabet, Rockwell.
- Thesen: Korb aus Intuitive Surgical und ASML (fair bewertet, Basis rund 9,3 % pro Jahr, Sicherheit mittel);
  Robotik-ETF 2B76.DE (Sicherheit niedrig; TER und Zusammensetzung ungeprüft); Cognex abwarten (teuer).
  Gegenprüfung: Rückrechnung ab Ende 2021 bestätigt den Korb knapp (1,59 statt 1,56 erwartet; ASML über,
  Intuitive unter der Erwartung). Für den ETF zeigt BOTZ eine Auswahl im Nachhinein (31,8 statt 49,2).
- Kosten: 9 Läufe, 6,85 USD, darunter ein abgewiesener Lauf.
- Schwächen: Firmen ohne SEC-Meldung (Fanuc, Yaskawa, Keyence, Harmonic Drive, Siemens, ABB) fielen heraus,
  das Ergebnis ist deshalb US-lastig. Bei NVIDIA, Intuitive und Rockwell fehlen die Investitionen der letzten Jahre im
  SEC-Auszug, also auch der FCF (vermutlich fehlen Konzepte wie PaymentsToAcquireProductiveAssets in
  abrufer.SEC_KONZEPTE). Die Marktkapitalisierung beruht teils auf verwässerten Aktien. ETF-Kosten hat der Lauf nicht geladen
  (Anbieterseite gesperrt).

## Nächste Schritte hier
1. Kosten je vollständiger Recherche: rund 6 USD, 6 Läufe, 17 Minuten, etwa 3 % des Wochenkontingents.
   Neue Läufe nur per /finance von Jan.
2. Vorschlag an Jan (nicht umgesetzt): Zweitquellen hart begrenzen, z. B. Python lehnt Webquellen von
   Sammel- und Nachrichtenseiten ab, wenn die Originalseite des Herausgebers erreichbar wäre, oder eine Liste
   gesperrter Domains. Der Prompt allein hat nicht gewirkt.
3. GENESIS gezielter nutzen: Tabellensuche (find/find) als eigene Abfrage-Art, damit Claude Codes nicht raten muss.
4. Prognosen aus Schritt 5 nach data/prognosen.json und monatlicher Timer (eigene Unit, nur nach Jans Okay).
5. Entwürfe aus Schritt 5 über shared/freigabe/ anlegen und ausfuehren() bauen.
6. EPO in einem echten /finance-Lauf beobachten: nutzt Claude die Patentsuche sinnvoll, reichen 4 Abfragen?
7. Marge im Modell zeigt #DIV/0!, wenn ein Szenario Umsatz 0 hat (Excel). Bei Bedarf Formel ändern.
8. aktien: weitere SEC-Konzepte für Investitionen ergänzen (FCF fehlt sonst); Firmen ohne SEC über
   Geschäftsberichte (PDF der Investorenseite) als eigene Abfrage-Art; ETF-Factsheets (TER, Positionen).

## Gelernte Regeln
- (noch keine)
