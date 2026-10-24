# Status: Agent recherche (Lias Instanz)

## Zweck
Baut für Lias Examensreihe (Ethik Klasse 8, Straftheorien) ein Quellenregister: gemeinfreie Texte aus
erlaubten Quellen, als Textfassung mit Seiten, mit geprüfter Gemeinfreiheit und wörtlich geprüften
Stellen. lia/examen liest das Register für die Skizzen.

## Stand (25.10.2026)
- Teil B fertig und einmal echt gelaufen (25.10., von Hand). Register data/register.json enthält:
  - stgb-46 (StGB § 46): frei (§ 5 UrhG), 1 Stelle (ganzer Paragraf), geprüft
  - jgg-2 (JGG § 2): frei (§ 5 UrhG), 1 Stelle, geprüft. Abs. 1 beginnt wie erwartet mit
    „Die Anwendung des Jugendstrafrechts soll vor allem erneuten Straftaten“.
  - kant-mds-strafrecht (AA Bd. VI, Berlin 1914, S. 331–337, Text nach korpora.org): Textfassung mit
    7 Seiten, frei und verwendbar (Kant gest. 1804, Herausgeber Paul Natorp gest. 1924). Noch keine
    Stellen (Teil C).
- Meldungen mit diesen Ergebnissen sind an Jan gegangen.
- Kein Claude-Lauf, kein Dienst, kein Timer (Teil C, Teil D).
- 37 Tests (tests/), in pruefen.sh eingetragen.

## Aufbau
- Aufruf: `AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python agent.py`
- agent.py: Lauf über alle Quellen. Fehler je Quelle: loggen, alter Registereintrag bleibt, am Ende
  eine Meldung an Jan (Jans Zentrale, wie jan_melden in lia/unterricht). Ebenso, wenn sich die
  Gemeinfreiheit einer Quelle ändert oder Stellen verworfen werden. Sonst still.
- quellen.toml: von Hand gepflegt, [abruf] allowlist (die einzige Stelle dafür) und je [[quelle]] id,
  art, werk, ausgabe, autor/todesjahr_autor, herausgeber/_todesjahr, uebersetzer/_todesjahr, urls, seiten.
- quellen.py: liest und prüft quellen.toml ohne Netz (Pflichtfelder, URLs gegen die Allowlist).
- auslesen.py: html.parser. gesetze-im-internet (nur Überschrift und Normtext), korpora.org
  (HTML-Seite = AA-Seite, Zeilennummern weg, „=“ bleibt, Leerzeichen innen an Klammern um kursive
  Wörter weg). Zeichensatz aus Content-Type, sonst aus <meta>. Parser nach Host der URL.
- gemeinfrei.py: reine Funktion pruefen(quelle, jahr) -> status frei | nicht_frei | ungeklaert,
  verwendbar, begruendung.
- register.py: Einträge bauen, laden, speichern (atomar).
- .venv: lia/recherche/.venv, agentkit per agentkit.pth, keine Pakete.
- Laufzeitdaten (nicht im Repo): data/roh/ (Cache von agentkit.abruf: nur Neues wird geladen),
  data/text/<id>.txt (Textfassung mit „--- Seite N“, lesbar mit agentkit.wortlaut.seiten),
  data/register.json. Logs: logs/recherche.log.

## Registereintrag
id, art, werk, ausgabe, autor/herausgeber/uebersetzer (falls angegeben), urls, abgerufen (frühester Abruf), roh (je URL: url, abgerufen,
sha256 des geladenen Inhalts), textfassung (Pfad relativ zum Agent-Ordner), sha256 (der Textfassung),
gemeinfreiheit {status, verwendbar, begruendung}, stellen [{seite, zitat, geprueft}].
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

## Offene Punkte
1. Nebenbei gesehen: korpora.org schreibt, das Korpus werde fortlaufend korrigiert (Textkorrekturen,
   Lesarten). Ob das für die Zitierfähigkeit „nach AA“ eine Rolle spielt, bei Gelegenheit mit Jan klären.
2. Teil C: Liszt „Der Zweckgedanke im Strafrecht“ (ZStW 3, 1883) als OCR auf archive.org finden,
   Parser dafür, Eintrag in quellen.toml (Platzhalter steht dort), Kernstellen per Claude (Opus),
   Stellen mit agentkit.wortlaut prüfen. Lia prüft Liszt-Zitate am Scan.
3. Teil D: Dienst und Timer (02:30), Grenze 8 USD pro Nacht.

## Gelernte Regeln
- (noch keine)
