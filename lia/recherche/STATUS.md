# Status: Agent recherche (Lias Instanz)

## Zweck
Baut für Lias Examensreihe (Ethik Klasse 8, Straftheorien) ein Quellenregister: gemeinfreie Texte aus
erlaubten Quellen, als Textfassung mit Seiten, mit geprüfter Gemeinfreiheit und wörtlich geprüften
Stellen. lia/examen liest das Register für die Skizzen.

## Stand (25.10.2026)
- Teil B und Teil C (ohne Liszt) fertig, echt gelaufen (25.10., von Hand). Register data/register.json enthält:
  - stgb-46 (StGB § 46): frei (§ 5 UrhG), 1 Stelle (ganzer Paragraf), geprüft
  - jgg-2 (JGG § 2): frei (§ 5 UrhG), 1 Stelle, geprüft. Abs. 1 beginnt wie erwartet mit
    „Die Anwendung des Jugendstrafrechts soll vor allem erneuten Straftaten“.
  - kant-mds-strafrecht (AA Bd. VI, Berlin 1914, S. 331–337, Text nach korpora.org): Textfassung mit
    7 Seiten, frei und verwendbar (Kant gest. 1804, Herausgeber Paul Natorp gest. 1924). 5 Kernstellen
    (Opus), alle wörtlich geprüft, keine gestrichen, 0,23 USD in 1 Lauf: S. 331 „niemals bloß als
    Mittel“, S. 331 „Er muß vorher strafbar befunden sein“, S. 332 Wiedervergeltung („Beschimpfst du
    ihn“), S. 333 Dieb und Zwangsarbeit, S. 333 Inselbeispiel.
- Liszt (ZStW Bd. 3, 1883) nicht eingetragen: OCR unbrauchbar (siehe Offene Punkte). Jan ist informiert.
- Meldungen mit diesen Ergebnissen sind an Jan gegangen.
- Kein Dienst, kein Timer (Teil D).
- 58 Tests (tests/), in pruefen.sh eingetragen.

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
  Mit scan={seite: link} bekommen Stellen am_scan_pruefen = true und den Scan-Link (für OCR-Quellen).
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
- 25.10.2026: Liszt nicht eingetragen, kein djvu-Parser gebaut. ZStW Bd. 3 liegt zweimal auf archive.org
  (zeitschriftgesa00berluoft, bub_gb_7TQwAQAAMAAJ, beide Titelblatt „Dritter Band“, 1883, Aufsatz S. 1–47),
  aber beide OCRs lesen die Fraktur als Antiqua („unb“ statt „und“). Alle Fraktur-Bände der Zeitschrift
  auf archive.org sind so; nur spätere Bände in Antiqua sind sauber. Keine Abschrift auf Wikisource.
- 25.10.2026: Zitatlänge nur über Zeichen (700) begrenzt, nicht über Sätze: Satzzählen ist bei
  „d. i.“, „u. dergl.“ und Kants Semikolons nicht sicher.

## Offene Punkte
1. Nebenbei gesehen: korpora.org schreibt, das Korpus werde fortlaufend korrigiert (Textkorrekturen,
   Lesarten). Ob das für die Zitierfähigkeit „nach AA“ eine Rolle spielt, bei Gelegenheit mit Jan klären.
2. Liszt: Jan entscheidet den Weg. Möglich: Lia schreibt 3 bis 5 Stellen am Scan ab (Python prüft
   dann nur Seite und Länge, Scan-Link je Seite: https://archive.org/details/<id>/page/n<N>), oder eine
   andere Textquelle. Eintrag dann mit autor = "Franz von Liszt", todesjahr_autor = 1919,
   herausgeber_entfaellt = "Zeitschriftenaufsatz" (Kommentar in quellen.toml).
3. Kant S. 333, Inselbeispiel: korpora.org hat „im Gefängni befindliche“ (ohne ß am Zeilenende). Das
   Zitat ist wortgetreu zur Textfassung, Lia sollte es am Druck prüfen.
4. Claude kann im Agent-Ordner mehr lesen als die Textfassung (claude_lauf beschränkt nur das
   Schreiben). Engere Leserechte bräuchten eine Änderung in agentkit (Hauptordner-Chat).
5. Teil D: Dienst und Timer (02:30), Grenze 8 USD pro Nacht.

## Gelernte Regeln
- (noch keine)
