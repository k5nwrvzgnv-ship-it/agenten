# Status: Agent recherche (Lias Instanz)

## Zweck
Baut für Lias Examensreihe (Ethik Klasse 8, Straftheorien) ein Quellenregister: gemeinfreie Texte aus
erlaubten Quellen, als Textfassung mit Seiten, mit geprüfter Gemeinfreiheit und wörtlich geprüften
Stellen. lia/examen liest das Register für die Skizzen.

## Stand (25.10.2026)
- Teil B und Teil C fertig, echt gelaufen (25.10., von Hand). Register data/register.json enthält:
  - stgb-46 (StGB § 46): frei (§ 5 UrhG), 1 Stelle (ganzer Paragraf), geprüft
  - jgg-2 (JGG § 2): frei (§ 5 UrhG), 1 Stelle, geprüft. Abs. 1 beginnt wie erwartet mit
    „Die Anwendung des Jugendstrafrechts soll vor allem erneuten Straftaten“.
  - kant-mds-strafrecht (AA Bd. VI, Berlin 1914, S. 331–337, Text nach korpora.org): Textfassung mit
    7 Seiten, frei und verwendbar (Kant gest. 1804, Herausgeber Paul Natorp gest. 1924). 5 Kernstellen
    (Opus), alle wörtlich geprüft, keine gestrichen, 0,23 USD in 1 Lauf: S. 331 „niemals bloß als
    Mittel“, S. 331 „Er muß vorher strafbar befunden sein“, S. 332 Wiedervergeltung („Beschimpfst du
    ihn“), S. 333 Dieb und Zwangsarbeit, S. 333 Inselbeispiel.
  - liszt-zweckgedanke (ZStW Bd. 3, 1883, S. 1–47, Toronto-Scan zeitschriftgesa00berluoft): frei (Liszt gest.
    1919, kein Herausgeber, Zeitschriftenaufsatz). Textfassung = OCR (nur Orientierung). 5 Kernstellen vom
    Seitenbild, alle Prüfungen bestanden, geprueft = false, am_scan_pruefen = true, je Scan-Link:
    S. 31 „Nur die notwendige Strafe ist gerecht“, S. 36 Dreiteilung (2 von 3), S. 39 Unverbesserliche,
    S. 40/41 Anfänger der Verbrecherlaufbahn, S. 44 „weil“/„damit“. OCR-Ähnlichkeit 0,852–0,918.
    Kosten 1,28 USD (Auswahl 0,68, Abschriften 0,26/0,25/0,08). S. 39 von mir am Bild nachgeprüft: stimmt.
    Erster Durchgang verwarf S. 36 und S. 40/41 wegen zweier Fehler im Code (dritte Abschrift neu
    nummeriert; Seitengrenze mit Fußnoten); behoben, die bezahlten Abschriften wurden ohne neuen Lauf
    neu bewertet (Merkdateien von Hand angelegt, gleiche Textfassung und Stellen).
- Meldungen mit diesen Ergebnissen sind an Jan gegangen.
- Kein Dienst, kein Timer (Teil D).
- 87 Tests (tests/), in pruefen.sh eingetragen.

## Aufbau
- Aufruf: `AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python agent.py`
- agent.py: Lauf über alle Quellen. Fehler je Quelle: loggen, alter Registereintrag bleibt, am Ende
  eine Meldung an Jan (Jans Zentrale, wie jan_melden in lia/unterricht). Ebenso, wenn sich die
  Gemeinfreiheit einer Quelle ändert, Stellen verworfen werden oder Claude gelaufen ist (Stellen,
  Gestrichenes, Kosten). Sonst still.
- Kernstellen (Teil C): für jeden verwendbaren Primärtext ohne Stellen ein Claude-Lauf (claude_lauf,
  art "anspruchsvoll" = Opus, Werkzeuge "standard" ohne Bash). Prompt mit der Reihe Straftheorien aus
  lia/unterricht/reihen.toml (nur gelesen). Claude liest data/text/<id>.txt, schreibt
  data/kernstellen/<id>.json. kernstellen.py prüft: Seite vorhanden, Zitat wörtlich auf genau dieser
  Seite (wortlaut.steht_in), höchstens 700 Zeichen, keine Überschneidung. Durchgefallenes einmal zurück
  (dieselbe Sitzung), danach gestrichen. 3 bis 6 Stellen; je Textfassung (sha256) nur ein Versuch.
  Kosten je Lauf im Log, Summe je agent.py-Lauf höchstens GRENZE_USD = 8, sonst kein weiterer Lauf.
- Scan-Quellen (scan_id in quellen.toml, Liszt): scan.py ordnet Druckseite -> Scan-Seite n zu
  (page_numbers.json, nur confidence 100, Lücken nur bei lückenloser Folge, sonst scan_von_hand; nichts
  geraten), holt die OCR je Druckseite (hocr_searchtext + hocr_pageindex) und baut Links
  https://archive.org/details/<id>/page/n<N>. Kernstellen vom Seitenbild (seitenbild.py, abschrift.py):
  1. Auswahl (Opus, OCR nur zur Orientierung): 3–5 Stellen mit seiten, anfang, ende, position, zweck;
     geprüfte Auswahl wird je Textfassung gespeichert und wiederverwendet.
  2. Bilder über agentkit.abruf nach data/bilder/<id>/s<seite>.jpg.
  3. Zwei Abschriften in getrennten Sitzungen, nur Bilder (buchstabengetreu, ſ als s, Trennung auflösen,
     alte Schreibung, [?] für Unleserliches). Bei Abweichung eine dritte nur für die strittigen Stellen.
  4. Prüfung: gleich nach wortlaut.normalisieren (2 von 2 oder 2 von 3), 50–900 Zeichen, unscharf zur
     OCR der Seite(n) mindestens SCHWELLE 0,75. Registerstelle: seite, seiten, zitat, position, zweck,
     geprueft = false (kein sicherer Text), am_scan_pruefen = true, scan_link {seite: link},
     pruefung {abschriften_gleich, ocr_aehnlichkeit, schwelle}. Über eine Seitengrenze: Abschrift an der
     besten Wortgrenze geteilt, Teile gegen je ihre Seite (Fußnoten und Seitenkopf liegen dazwischen).
     Bezahlte Abschriften werden je Textfassung und Stellen wiederverwendet (*_merk.json).
- quellen.toml: von Hand gepflegt, [abruf] allowlist (die einzige Stelle dafür) und je [[quelle]] id,
  art, werk, ausgabe, autor/todesjahr_autor, herausgeber/_todesjahr, uebersetzer/_todesjahr, urls, seiten.
- quellen.py: liest und prüft quellen.toml ohne Netz (Pflichtfelder, URLs gegen die Allowlist).
- auslesen.py: html.parser. gesetze-im-internet (nur Überschrift und Normtext), korpora.org
  (HTML-Seite = AA-Seite, Zeilennummern weg, „=“ bleibt, Leerzeichen innen an Klammern um kursive
  Wörter weg). Zeichensatz aus Content-Type, sonst aus <meta>. Parser nach Host der URL.
- gemeinfrei.py: reine Funktion pruefen(quelle, jahr) -> status frei | nicht_frei | ungeklaert,
  verwendbar, begruendung. <rolle>_entfaellt = "Grund" (z. B. herausgeber_entfaellt =
  "Zeitschriftenaufsatz") heißt ausdrücklich keine solche Person; ein leerer Name bleibt ungeklärt.
- register.py: Einträge bauen, laden, speichern (atomar).
- .venv: lia/recherche/.venv, agentkit per agentkit.pth, keine Pakete.
- Laufzeitdaten (nicht im Repo): data/roh/ (Cache von agentkit.abruf: nur Neues wird geladen),
  data/text/<id>.txt (Textfassung mit „--- Seite N“, lesbar mit agentkit.wortlaut.seiten),
  data/kernstellen/<id>.json (Claudes Antwort), data/register.json. Logs: logs/recherche.log.

## Registereintrag
id, art, werk, ausgabe, autor/herausgeber/uebersetzer (falls angegeben), urls, abgerufen (frühester Abruf), roh (je URL: url, abgerufen,
sha256 des geladenen Inhalts), textfassung (Pfad relativ zum Agent-Ordner), sha256 (der Textfassung),
gemeinfreiheit {status, verwendbar, begruendung}, stellen [{seite, zitat, position, zweck, geprueft,
(am_scan_pruefen, scan)}], kernstellen {sha256, datum, usd, gestrichen [{seite, grund}]} nach einem Claude-Lauf.
Gesetze: Textfassung „--- Seite 1“, darunter Überschrift und Normtext; Stelle = ganzer Normtext auf
Seite 1, geprüft mit agentkit.wortlaut.steht_in. Primärtexte: Stellen bleiben über Läufe erhalten,
solange die sha256 der Textfassung gleich bleibt, sonst werden sie verworfen und Jan erfährt es.

## Entscheidungen
- 25.10.2026 (Jan): Teile A–D, Allowlist gesetze-im-internet.de, de.wikisource.org, zeno.org,
  korpora.org, archive.org. Meldungen an Jan, nicht an Lia.
- 25.10.2026: Gemeinfrei nur, wenn alle Beteiligten (Autor, Herausgeber, Übersetzer) Todesjahr + 70
  < aktuelles Jahr. Fehlt ein Name oder Todesjahr: ungeklärt, nicht verwenden. Gesetze: § 5 UrhG.
- 25.10.2026: Herausgeber von AA Bd. VI (Metaphysik der Sitten) ist Paul Natorp (1854–1924). Auf
  korpora.org nicht genannt; belegt durch den Band selbst (OCR archive.org kantsgesammeltes06imma,
  „Herausgeber: Paul Natorp.“, selbst nachgeprüft). Lebensdaten vom lia-Chat geprüft (Deutsche Biographie,
  DLA Marbach). Belege als Kommentar in quellen.toml.
- 25.10.2026: Liszt: Die OCR beider Scans von ZStW Bd. 3 auf archive.org liest die Fraktur als Antiqua
  („unb“ statt „und“). Keine andere Textquelle (Nachdruck 1905 nicht auf archive.org, Wikisource, DTA,
  soweit prüfbar digitale-sammlungen.de). Jan: Kernstellen vom Seitenbild, zwei Abschriften, Lia prüft am Scan.
- 25.10.2026: Toronto-Scan statt Google-Scan: 500 ppi, keine Unterstreichungen; beim Google-Scan ist
  n17 nicht S. 1 (Bildzählung passt nicht zu page_numbers.json). Zuordnung n = Blatt - 1, am Bild geprüft:
  n22 = S. 1, n23 = S. 2, n68 = S. 47; S. 1 und 2 von Hand (fehlen in page_numbers.json).
- 25.10.2026: Schwelle für den OCR-Abgleich 0,75. Bestimmt an drei selbst vom Bild gelesenen Passagen
  (S. 1, 664 Zeichen; S. 2, 390; S. 47, 227) und zwei einzelnen Sätzen (96 und 57 Zeichen): richtige Seite
  0,866–0,934, beste falsche Seite 0,366–0,592. Darum auch Mindestlänge 50 Zeichen. Grenze: Der Abgleich
  findet die Stelle, erkennt aber keine einzelnen falschen Wörter (zwei vertauschte Wörter: noch 0,87–0,90).
  Dagegen schützen nur die zwei Abschriften und Lias Prüfung am Scan.
- 25.10.2026: Zitatlänge nur über Zeichen (700) begrenzt, nicht über Sätze: Satzzählen ist bei
  „d. i.“, „u. dergl.“ und Kants Semikolons nicht sicher.

## Offene Punkte
1. Nebenbei gesehen: korpora.org schreibt, das Korpus werde fortlaufend korrigiert (Textkorrekturen,
   Lesarten). Ob das für die Zitierfähigkeit „nach AA“ eine Rolle spielt, bei Gelegenheit mit Jan klären.
2. Tests schreiben ins echte logs/recherche.log (logger an HIER), z. B. „liszt Auswahl 0.30 USD“ aus der
   Claude-Attrappe. Beim Lesen des Logs beachten; Aufräumen bei Gelegenheit.
3. Kant S. 333, Inselbeispiel: korpora.org hat „im Gefängni befindliche“ (ohne ß am Zeilenende). Das
   Zitat ist wortgetreu zur Textfassung, Lia sollte es am Druck prüfen.
4. Claude kann im Agent-Ordner mehr lesen als die Textfassung (claude_lauf beschränkt nur das
   Schreiben). Engere Leserechte bräuchten eine Änderung in agentkit (Hauptordner-Chat).
5. Teil D: Dienst und Timer (02:30), Grenze 8 USD pro Nacht.

## Gelernte Regeln
- (noch keine)
