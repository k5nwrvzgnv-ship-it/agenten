# Plan: Recherche-Maske für Jan und Lia

Stand 15.11.2026, Entwurf aus dem Hauptordner-Chat. Nichts davon ist gebaut. Jans Entscheidung vom 15.11.2026:
eine Maske für beide, die Motoren bleiben vorerst getrennt (`uni/recherche.py` für Jan, `lia/recherche/` für Lia).
Offene Entscheidungen stehen am Ende (Abschnitt 9).

## 1. Bestandsaufnahme

### uni (Jan)
- Start heute: Arbeitsplatz, Art „Research-Bericht“ (`shared/arbeitsplatz/arten.toml`: Thema, Fragestellung,
  Umfang kurz/gründlich, `rueckmeldung = false`), oder als erster Schritt eines Exposés (Telegram „Exposé:“).
  Eine Rückfrage oder Erweiterung geht nicht: „neuer Auftrag“.
- Ablauf (`uni/recherche.py`, `durchfuehren`): Eckpunkte (Claude stellt Fragen, je Frage ein Suchfenster:
  literatur, methoden, daten, projekte, markt, regelwerk) -> je Fenster eine Opus-Sitzung mit zwei Durchgängen ->
  Python prüft jeden Beleg (Zitat wörtlich auf Seite/PDF, lokale Normen seitengenau, DOI gegen Crossref) -> optional
  Scopus-Fenster aus Jans Export -> Gegenprüfung „trägt das Zitat?“ -> `geprueft.json` und `Recherchebericht.md`.
- Ablage: `data/recherchen/<auftrag>/recherche/` (Bericht) bzw. `data/expose/<kette>/recherche/` (Exposé), je
  Fenster `<fenster>.json` und `-geprueft.json`, `eckpunkte.json`, `gegenpruefung.json`, `stand.json` (Kosten,
  fertige Stufen; ein neuer Anlauf setzt fort, bezahlt nichts doppelt).
- Datenformat `geprueft.json`: thema, fragen [{id, fenster, frage, anlass}], aussagen [{id, fenster, frage, art,
  text, status, fehlt, belege}], quellen [{url, titel, autoren, jahr, doi, art, fenster, zitierfaehig, pruefung}],
  luecken, widersprueche, offen, zahlen, literatursuche. Status: gesichert, teilweise, verworfen, unbelegt,
  einschaetzung.
- Kosten: Grenze 50 USD je Recherche (Exposé), Bericht kurz 15 / gründlich 50 USD (geschätzt, nicht gemessen).
  Gemessen: Exposé-Recherche mit Scopus 35,23 USD, 24 Fragen, 163 Aussagen. Kurzrecherche als normaler Auftrag
  0,88 USD; eine Antwort darauf in fortgesetzter Sitzung 1,06 USD für 3 Schritte.
- Ansicht: Arbeitsplatz zeigt Bericht und geprüfte Recherche (Reiter Aussagen mit Status- und Fragefilter,
  Quellen, Lücken und Widersprüche), nur lesend.
- Von Hand im Chat: Scopus-Dateien zuordnen, Nachträge in `geprueft.json`, Kurzrecherchen.

### lia/recherche (Lia)
- Start heute: nur von Hand im Chat. Kein Dienst, kein Timer, kein Eingang aus Lias Zentrale oder Web-App
  (Offene Punkte 5 und 6 in `lia/recherche/STATUS.md`). Lia sagt Jan, was sie braucht; der Chat schreibt eine
  Auftragsdatei und startet den Lauf, Jan sieht die Vorschau, dann `--an-lia`.
- Drei Motoren in einem Ordner:
  - Register (`agent.py`): gemeinfreie Werke aus `quellen.toml` (eigene Allowlist unter `[abruf]`), Textfassung mit
    Seiten, Kernstellen wörtlich geprüft (Kant, Liszt vom Scan, StGB, JGG). Ergebnis `data/register.json`.
  - Webauftrag (`webauftrag.py`): Auftrag als .txt in `data/web/auftraege/` (Kopfzeilen FACH, TITEL, AUFWAND,
    ANHANG). Ablage `data/web/<id>/`: auftrag.txt, ergebnis.json, geprueft.json (kern, punkte, abschnitte
    [{titel, aussagen}], luecken, rueckfragen, zahlen, traegt_zahlen, kosten_usd, an_lia), Recherche.docx, roh/.
    Belege {url, zitat} oder {register}; traegt.py urteilt ja/teilweise/nein.
  - Fallsuche (`fallsuche.py`): fünf Suchfenster, Abgleich gegen `regelwerk_reihe.md`, Dossier. Ablage
    `data/fallsuche/<id>/` (faelle.json, abgleich.json, dossier.json).
- WebFetch nur auf `[webfetch] recherche` in `shared/einstellungen.toml` (eine flache Liste, Gruppen nur als
  Kommentar). Neue Seiten trägt der Chat auf Jans Wort ein (13.11. Theater, 14.11. 37 Lokalseiten).
- Kosten (gemessen): Webauftrag normal 1,90 bis 2,63 USD. AUFWAND gross 21,53 USD (Recherche 3,67, Vertiefung 1
  5,01, Vertiefung 2 6,26, Vertiefung 3 6,58 für nur 4 Schritte, weil eine fortgesetzte Sitzung ihren ganzen
  Verlauf mitschickt). Fallsuche 42,42 USD in vier Teilläufen, ein Suchfenster mit zwei Durchgängen 6,5 bis 7 USD.
  Prüflauf traegt 0,01 USD. Grenzen: Webauftrag 8 USD, gross 25 USD, Fallsuche 15 USD je Lauf.
- Was Jan heute von Hand auslöst: jeden Lauf; eine zweite Fassung als neuer Auftrag mit neuer Datei (`-v2`), der
  den ersten Lauf nicht kennt (milde Jugendtaten: zweiter Lauf nach neuen Domains, Ergebnisse liegen getrennt);
  kern von Hand kürzen (Sprachregel); `--an-lia`; neue Domains eintragen.
- Fragen zu einem Ergebnis beantwortet heute lia/chat: Es darf lesend in `lia/recherche` suchen (Glob/Grep,
  10.11.2026) und fand dort die Fälle selbst. Ohne festes Format, ohne Belegprüfung.

### Was beiden fehlt
Ein Ergebnis ist heute ein Endpunkt. Es gibt keinen Weg, (a) vor dem teuren Lauf zu sehen, was gesucht wird,
(b) eine Frage an den Bestand zu stellen, (c) gezielt zu erweitern, ohne alles neu zu suchen oder eine teure
Sitzung fortzusetzen, (d) einzelne Aussagen, Fälle oder Quellen zu verwerfen, und (e) Ergebnisse mehrerer Läufe
zusammenzusehen.

## 2. Grundidee: Recherche als Projekt

Eine Recherche ist ein Projekt mit drei Ebenen:
1. **Wissensbasis** (`wissen.json`): Fragen, Quellen, Aussagen mit Belegen und Status, Lücken, Entscheidungen.
   Sie wächst mit jedem Lauf und ist die einzige Wahrheit.
2. **Läufe**: je Lauf Art, Datum, Kosten, Modell und was neu dazukam oder sich änderte. Die Rohdateien eines
   Laufs bleiben unverändert in seinem Ordner (wie heute).
3. **Dokumente**: nur Ausgaben eines Stands (docx/PDF für Lia, Recherchebericht für Jan). Ein Dokument nennt den
   Lauf, auf dem es beruht, und wird nie zurück in die Wissensbasis gelesen.

### Ablage je Agent
`<agent>/data/projekte/<projekt-id>/`
- `wissen.json` (Wissensbasis, atomar geschrieben)
- `plan.json` (der angenommene Plan, siehe 3.1)
- `laeufe/<nr>-<art>/` (Rohdateien des Motors, wie heute `data/web/<id>/` bzw. `recherche/`)
- `dokumente/<nr>/` (Ausgaben)

Die Motoren bleiben getrennt und schreiben ihr eigenes Format wie bisher. Je Motor ein Adapter macht daraus
Einträge im gemeinsamen Format und übergibt sie an `agentkit.recherche.einarbeiten`. So ändert sich an der
Suche selbst zunächst nichts.

### Gemeinsames Format (Vorschlag, angelehnt an uni `geprueft.json`)
```json
{
  "format": 1,
  "id": "20261115-lia-milde-jugendtaten",
  "titel": "Milde Jugendtaten zum Einstieg ins Thema Strafe",
  "fuer": "lia",
  "agent": "recherche",
  "ort": "<id einer Reihe oder Stunde, bzw. Ort im Arbeitsplatz>",
  "fach": "Ethik",
  "fragen": [{"id": "F1", "frage": "...", "anlass": "...", "gruppe": "nachrichten", "lauf": 1}],
  "quellen": [{"id": "Q1", "url": "https://...", "titel": "...", "autoren": [], "jahr": 2024, "doi": null,
               "art": "artikel|urteil|meldung|werk|norm|...", "register": null, "gesperrt": false, "lauf": 1}],
  "aussagen": [{
    "id": "A1", "frage": "F1", "art": "tatsache|einschaetzung|fall", "text": "...",
    "belege": [{"quelle": "Q1", "zitat": "...", "seite": null,
                "pruefung": {"status": "bestanden|durchgefallen|ungeprueft", "grund": ""}}],
    "traegt": {"urteil": "ja|teilweise|nein|offen", "fehlt": ""},
    "status": "gesichert|teilweise|verworfen|unbelegt|einschaetzung",
    "sichtung": "offen|uebernommen|verworfen",
    "fall": null,
    "lauf": 1, "geaendert_in": []
  }],
  "luecken": [{"text": "...", "lauf": 1}],
  "widersprueche": [], "rueckfragen": [],
  "entscheidungen": [{"datum": "...", "wer": "jan|lia", "was": "anfechten|verwerfen|sperren|uebernehmen",
                      "ziel": "A3", "grund": "...", "lauf": null}],
  "laeufe": [{"nr": 1, "art": "plan|suche|ausweiten|frage|nachpruefen|dokument", "datum": "...", "usd": 2.02,
              "modell": "opus", "auftrag": "<auftrags-id>", "ordner": "laeufe/1-suche",
              "neu": {"aussagen": ["A1"], "quellen": ["Q1"]}, "geaendert": [], "zusammenfassung": "..."}],
  "dokumente": [{"nr": 1, "datei": "dokumente/1/....docx", "stand_lauf": 2, "datum": "..."}]
}
```
- Status wie in uni: kein bestandener Beleg -> unbelegt (bzw. einschaetzung); bestanden, nicht gegengeprüft ->
  teilweise; traegt ja/teilweise/nein -> gesichert/teilweise/verworfen. Eine Entscheidung (verwerfen, Quelle
  gesperrt) geht über den Status des Motors.
- `fall` (nur Fallsuche): Kurzfassung, Alter, Ausgang, Abgleich je Kriterium, Gewalt-Marke. So passen Fälle ins
  selbe Format, ohne dass die Fallsuche ihr eigenes Dossier verliert.
- Register-Belege: Quelle mit `register` (id aus `register.json`), Beleg mit Seite.
- IDs sind stabil über Läufe. Neue Läufe bekommen neue IDs; dieselbe URL ist dieselbe Quelle, dieselbe Aussage
  (normalisierter Text und gleiche Quelle) wird nicht doppelt aufgenommen, sondern in `geaendert_in` vermerkt.
- `agentkit.recherche` (rein, getestet): laden, prüfen, einarbeiten (Lauf in die Basis), Status berechnen,
  `bestand_text` (kompakte Liste für Prompts), Entscheidungen anwenden, Zahlen. Kein Netz, kein Claude.

## 3. Abläufe

### 3.1 Neue Recherche: erst Plan, dann Lauf
1. Eingabe: Jan füllt Thema und Fragestellung (Arbeitsplatz), Lia schreibt in eigenen Worten (Web-App).
2. **Planlauf** (günstig): Claude ohne WebFetch, Sonnet, schlägt vor: Teilfragen, Quellengruppen aus der
   Bibliothek (Abschnitt 4), Werke aus dem Register, Kriterien zum Ein- und Ausschließen (z. B. „keine Gewalt
   gegen Menschen“ aus Lias Regeln), Aufwand (normal/groß, bei uni Fenster und Fragen). Python prüft: Gruppen und
   Werke existieren, Fragen höchstens wie heute (uni 8/24), Kriterien widersprechen keiner Regel aus
   `regeln.md`/„Gelernte Regeln“ (nur Kennungen abgleichen). Fehlt eine Seite, die nicht auf der Liste steht,
   nennt der Plan sie als Vorschlag an Jan, nicht als Teil des Laufs.
3. **Kostenschätzung von Python**, nicht von Claude: aus einer Tabelle gemessener Läufe in `agentkit.recherche`
   (heute: Lia normal 2–3 USD, groß etwa 22 USD, Fallsuche je Fenster 6,5–7 USD; uni kurz und gründlich noch
   geschätzt). Jeder echte Lauf schreibt seine Kosten in `laeufe` und verbessert die Tabelle später.
4. Annehmen startet den Lauf: uni nimmt die Teilfragen des Plans statt eigener Eckpunkte; lia/recherche baut aus
   dem Plan die Auftragsdatei (wie heute, mit FACH, TITEL, AUFWAND). Danach Adapter -> `wissen.json`.
5. Wer den Plan ändern will, schreibt es hin; das gibt einen neuen Planlauf (nicht die alte Sitzung fortsetzen).

### 3.2 Fragen an den Bestand
- Antwort nur aus `wissen.json`, ohne Web. Claude bekommt die Basis als Datei (Read im Projektordner, Sonnet),
  schreibt `{antwort, stuetzt: [Aussage-IDs], fehlt}`. Python prüft: jede ID existiert und ist nicht verworfen,
  Zitate im Antworttext stehen wörtlich in einem bestandenen Beleg. Die Ansicht zeigt die Antwort mit den
  Aussagen und ihren Belegen darunter.
- Weiß der Bestand es nicht, sagt die Antwort das und nennt, was eine Erweiterung suchen müsste; daraus wird auf
  Wunsch ein Ausweiten-Plan (3.3). Eine Frage löst nie selbst eine Websuche aus.
- Kosten: Lauf `frage`, erwartet wenige Cent (lia/chat mit Netz 0,14 USD; ohne Netz weniger, noch nicht gemessen).
- Für Lia kann das lia/chat übernehmen, sobald es `wissen.json` statt verstreuter Dateien liest (Abschnitt 8,
  Schritt 10).

### 3.3 Ausweiten
- Ein neuer Lauf mit neuer Sitzung, nie eine Fortsetzung der alten. Begründung: Fortsetzungen schicken den ganzen
  Verlauf mit; Vertiefung 3 der Theater-Recherche kostete 6,58 USD für 4 Schritte, eine Antwort in fortgesetzter
  uni-Sitzung 1,06 USD für 3 Schritte.
- Der Prompt bekommt `bestand_text`: Fragen, URLs der vorhandenen Quellen, Aussagen kurz mit Status, verworfene
  Fälle und gesperrte Quellen ausdrücklich als „nicht wieder vorschlagen“, dazu das Ziel der Erweiterung (neue
  Teilfrage, mehr Fälle, andere Gruppe, neue Seiten nach Jans Eintrag).
- Vor dem Lauf ein kurzer Plan wie in 3.1 (Ziel, Gruppen, Kostenschätzung). Python arbeitet das Ergebnis ein und
  markiert Neues mit der Laufnummer; Doppeltes fällt weg und wird im Lauf gezählt.
- Abgrenzung: Die drei Vertiefungsrunden innerhalb eines Laufs mit `AUFWAND: gross` bleiben, wie Jan am 14.11.2026
  entschieden hat. Dieser Plan ändert nur, wie ein späteres Ausweiten läuft.

### 3.4 Nachprüfen
- **Aussage anfechten** (mit Grund): ein kleiner Prüflauf nur für diese Aussage (traegt mit dem Grund im Prompt,
  neue Sitzung, Sonnet). Ergebnis ändert Status und landet in `entscheidungen`. Gegenbelege suchen wäre Ausweiten.
- **Fall bzw. Aussage verwerfen**: ohne Claude, Status verworfen, Grund in `entscheidungen`, rückgängig machbar.
- **Quelle sperren**: ohne Claude; im Projekt gesperrt, Aussagen, die nur an dieser Quelle hängen, werden
  unbelegt, Ausweiten schlägt sie nicht wieder vor. Eine Sperre für alle Projekte ist eine Regel und geht über den
  Feedback-Weg (Abschnitt 6). Aus der Allowlist entfernt sie nichts.

### 3.5 Sichten und Dokument
- Neues aus einem Lauf hat `sichtung: offen`. Gesichertes gilt als übernommen, sobald man nichts dagegen sagt;
  verworfen wird per Text oder im „···“ (Abschnitt 5). Keine Häkchenliste.
- Ein Dokument entsteht nur aus Übernommenem und hält den Stand fest (`stand_lauf`). Für Lia: siehe Abschnitt 5.
- Dokumente baut Python wie heute (Renderer bzw. Recherchebericht), nicht Claude; nur kern/punkte für Lia kommen
  von Claude und werden gegen die Sprachregel geprüft (heute von Hand gekürzt, siehe Offener Punkt 10 in
  `lia/recherche/STATUS.md`).

## 4. Quellenbibliothek
- **Gruppen**: `[webfetch]` bekommt benannte Gruppen je Agent, z. B. `[webfetch.recherche]` mit `nachrichten`,
  `justiz`, `bildung`, `mediatheken`, `theater`, `lokal`, `nachschlagen`; `[webfetch.uni]` mit `literatur`,
  `verlage`, `daten`, `foerderung`, `hersteller`. `einstellungen.webfetch_domains(agent)` liefert weiter die
  Vereinigung, die Allowlist ändert sich also nicht. Die heutigen Kommentare werden die Gruppennamen.
- **Werke**: `lia/recherche/data/register.json` (gemeinfreie Werke mit Kernstellen), bei uni die lokalen Normen
  (`data/normen/uebersicht.md`) und ein Scopus-Export. Der Plan wählt daraus; die Bibliothek zeigt sie nur.
- **Sicherheitsgrenze**: Die Allowlist bleibt die Grenze für WebFetch und `agentkit.abruf`. Die Auswahl im Plan
  steuert, wo zuerst gesucht wird (Prompt), sie erweitert nie. Neue Seiten trägt nur Jan ein. Pläne und Läufe
  sammeln Seiten, die gefehlt haben (heute steht das in den Lücken), in einer Vorschlagsliste für Jan.
- `[abruf] allowlist` in `lia/recherche/quellen.toml` bleibt getrennt (Register-Abruf), wird aber in der
  Bibliothek mit angezeigt.

## 5. Zwei Gesichter derselben Seite

### Lia (Web-App, Regel „Schlau statt Schalter“, Jan 10.11.2026)
- Kein Knopf für Fragen, Ausweiten oder Nachprüfen, keine Auswahl von Gruppen oder Aufwand.
- Neue Recherche: Lia schreibt, was sie braucht. Der Plan kommt als zwei, drei Sätze („Ich suche echte Fälle mit
  12- bis 17-Jährigen, ohne Gewalt, vor allem in Polizeimeldungen und Lokalnachrichten. Dauert etwa 20 Minuten.“)
  und einem Knopf „Los“.
- Danach schreibt sie in eigenen Worten an die Recherche („Gibt es auch einen aus Berlin?“, „Fall 3 ist zu hart“,
  „Such noch nach Schulfällen“). Ein kleiner Lauf (Haiku oder Sonnet, ohne Web) erkennt die Absicht:
  `frage | ausweiten | nachpruefen | plan_aendern | dokument | regel`. Python prüft das Ergebnis (bekannte
  Absicht, IDs existieren). Bei Unklarheit stellt das System eine kurze Rückfrage statt zu raten.
- Alles, was Geld kostet (neue Recherche, Ausweiten), kommt vorher als Plan in Sätzen mit „Los“; Fragen und
  Verwerfen laufen sofort. So bleibt es ohne Schalter, und ein Missverständnis kostet keinen großen Lauf.
- Sichten: Lia sieht die Ergebnisse wie heute als Dokument mit „Auf einen Blick“. Gesichertes gilt als
  übernommen; was sie ablehnt, sagt sie, und es fällt aus der nächsten Fassung. Kosten sieht sie nicht, nur die
  Dauer.

### Jan (Arbeitsplatz)
Jan 15.11.2026: Auch Jans Seite kommt mit wenigen Knöpfen aus. Ein Knopf steht nur sichtbar da, wenn er wirklich
sinnvoll ist, sonst liegt er versteckt im „···“-Menü.
- Dieselbe Seite wie Lias: das Textfeld mit derselben Absichtserkennung ist der Hauptweg (fragen, ausweiten,
  verwerfen, Plan ändern), dazu die Wissensbasis (Aussagen mit Status- und Fragefilter wie die heutige Ansicht),
  Läufe, Dokumente.
- Sichtbare Knöpfe nur zwei: „Los“ unter einem Plan (vor jedem bezahlten Lauf) und „Senden“ am Textfeld.
- Plan: kommt als kurze Liste (Teilfragen, Gruppen, Werke, Aufwand, geschätzte Kosten). Ändern per Text oder direkt
  am Eintrag (anklicken, wie Titel im Arbeitsplatz), keine Formularmaske.
- Im „···“ einer Aussage, eines Falls oder einer Quelle: Anfechten, Verwerfen, Sperren, Rückgängig. Im „···“ des
  Projekts: Ausweiten, Dokument bauen, Quellenbibliothek.
- Sichten wie bei Lia: Gesichertes gilt als übernommen, Jan nimmt nur heraus, was nicht passt (Text oder „···“).
- Kosten je Lauf mit Modell und Schritten in einer geschlossenen Klappe „Läufe“, nicht dauerhaft sichtbar.
- Quellenbibliothek als eigene Seite (über „···“), mit Vorschlagsliste und Pflege der Gruppen.
- Jan sieht auch Lias Projekte, mit denselben Wegen, weil er heute ihre Läufe startet und prüft.

### Recherche am Ort (Jan 15.11.2026)
Jan: Eine Recherche findet an einem Ort im Baum statt, auf jeder Ebene (z. B. Forschungsprojekt Fehlstellen,
Holzbiologie, ein Kapitel unter „Schriftlicher Teil“). So ist sie örtlich leicht zu finden, der Kontext stimmt, und
beim Schreiben der Arbeit kann sie im richtigen Kapitel stattfinden. Skizze: `docs/recherche-entwurf.html`.
- Eine Recherche ist ein Eintrag im Baum, wie eine Unterseite: Sie steht unter der Seite, an der sie gestartet
  wurde, auf jeder Ebene. Die Recherche trägt `ort` (Feld steht schon im Format, die Adapter setzen es noch nicht).
- Eine eigene Seite „Recherchen“ als Ablage gibt es nicht; `/recherchen` und der Baum-Eintrag darauf entfallen.
  Was läuft oder fertig ist, steht wie bei Dokumenten auf „Heute“.
- Jede Seite hat das Textfeld „Was willst du hier wissen?“. Soll die Recherche tiefer hin, schreibt Jan es dazu
  („für Kapitel 2“); Verschieben im „···“ der Recherche wie bei Seiten.
- Kontext für Plan und Lauf: Titel der Ebenen darüber, Dateien und Dokumente am Ort und darüber, dazu als Bestand
  die Recherchen am Ort und darüber (`bestand_text`, wie beim Ausweiten: nicht noch einmal suchen, nur ergänzen).
- Schreiben (später, uni): Ein Auftrag am Kapitel nimmt die Recherchen dieses Orts und darüber als Quellen.
- Lia: `ort` ist dort Reihe oder Stunde; Verhalten gleich, ihre Seite folgt in Schritt 11.
- Gebaut (15.11.2026, lesend): Recherchen im Baum an ihrem Ort, Übersicht nach Skizze, `/recherchen` weg (siehe
  `shared/arbeitsplatz/STATUS.md`). Exposé-Recherche über `orte-zuordnung.json` unter „Exposé“. Lias drei Projekte
  stehen ohne Ort auf Heute. Gebaut 17.11.2026: „+ → Recherche …“ an jeder Seite und auf Heute, Plan ohne Claude
  (Thema, Ort, Umfang, Kosten) mit „Los“, Auftrag an uni mit `ort`. Offen: Plan mit Claude (6a, 7), `ort` aus den
  Adaptern (6b, uni zuerst).

## 6. Harte Regeln aus CLAUDE.md
- **Nach außen**: Recherche liest nur (WebSearch, WebFetch auf der Allowlist). Ein Dokument an Lia ist Zustellung
  über ihre Warteschlange wie heute, keine Handlung nach außen. Mails oder Nachrichten an Dritte gibt es nicht.
- **Claude denkt, Python handelt**: Claude schreibt nur JSON (Plan, Lauf, Antwort, Absicht) über
  `agentkit.claude_lauf`; Python prüft und schreibt `wissen.json`. Absichtserkennung handelt nie selbst.
- **Feedback und Vetorecht**: Fragen, Ausweiten, Nachprüfen und Sichten sind Aufträge bzw. Arbeit an den Daten des
  Projekts, kein Feedback. Sagt Lia etwas Allgemeines („nie Gewalt“, „keine Fälle über 18“), erkennt die
  Absichtserkennung `regel` und gibt es an den Feedback-Dienst (`agentkit.feedback`): Regel mit Feedback-ID in
  „Gelernte Regeln“ von `lia/recherche/STATUS.md`, Jan bekommt die Zusammenfassung mit Stopp-Knopf. Regeln nur
  hinzufügen; Löschen, Ändern und Widersprüche gehen als Vorschlag an Jan.
- **Lias Aufträge laufen ohne Jans Okay** (Jan 30.10.2026), auch Ausweiten und Nachbesserungen, egal wie oft und
  wie teuer. Für Jans Projekte gelten die Grenzen aus CLAUDE.md (mehr als eine Nachbesserung je Ergebnis oder über
  1 USD als Vorschlag an Jan). Die Kostengrenzen je Lauf im Code (8/25/15/50 USD) bleiben als technische Sicherung;
  ändern nur mit Jans Okay.
- **Limits und Käufe**: keine Käufe. Allowlist und Gruppen ändert nur Jan.
- **Schülerdaten**: Lias Lerngruppe steht heute im Prompt (Reihenkontext). Daran ändert der Plan nichts; Suchtexte
  enthalten keine Namen (gilt schon).
- **Isolation**: Jeder Motor bleibt in seinem Ordner mit eigener .venv. Gemeinsam ist nur `agentkit.recherche`.

## 7. Was nicht in diesem Plan steht
- Zusammenlegen der Motoren (ausdrücklich später).
- Scopus über die Maske (bleibt Jans Handarbeit, wie in `uni/STATUS.md`).
- Register-Pflege über die Maske (neue Werke in `quellen.toml` bleiben Handarbeit im lia/recherche-Chat).
- Automatische Läufe ohne Eingabe (Timer, Teil D von lia/recherche).

## 8. Bauschritte
Je Schritt der zuständige Chat (CLAUDE.md: ein Chat ändert nur seinen Ordner), mit Tests, eingetragen in
`pruefen.sh` wo neu. Nach jedem Schritt Commit und STATUS.

| Nr | Chat | Schritt | Tests |
|---|---|---|---|
| 1 | Hauptordner | `agentkit/recherche.py`: Format, prüfen, einarbeiten (IDs, Doppelte), Status, Entscheidungen, `bestand_text`, Kostentabelle. Kein Netz. | Unit-Tests mit kleinen Basen, Doppelte, Sperre macht Aussagen unbelegt, Rückgängig |
| 2 | lia/recherche | Adapter Webauftrag -> `wissen.json`; vorhandene sechs Läufe als drei Projekte mit je zwei Läufen einlesen (reihe-strafe, theater, milde Jugendtaten). Kein Claude-Lauf. | Adapter gegen Kopien echter `geprueft.json` |
| 3 | uni | Adapter `geprueft.json` -> `wissen.json`, Exposé-Recherche als Projekt einlesen. | wie 2 |
| 4 | Hauptordner (Arbeitsplatz) | Lesende Projektseite: Wissensbasis, Läufe, Dokumente, für uni und Lias Projekte. Ersetzt die heutige Ansicht recherche. | App-Tests über Unix-Socket |
| 5 | Hauptordner, dann uni und lia/recherche | Fragen an den Bestand: Prompt und Prüfung in agentkit, Aufruf je Motor, Feld auf der Seite. Erster echter Lauf misst die Kosten. | Prüfung der Antwort (unbekannte ID, erfundenes Zitat) |
| 6 | Hauptordner | Nachprüfen und Sichten ohne Claude (verwerfen, sperren, rückgängig) im „···“ der Einträge; anfechten als Prüflauf je Motor. | Logik in agentkit, App |
| 6a | Hauptordner | Absichtserkennung für Jans Textfeld (dieselbe wie Schritt 10, hier zuerst gebaut), damit Jans Seite ohne weitere Knöpfe auskommt. | Absicht prüfen (unbekannt, mehrdeutig) |
| 6b | Hauptordner, uni, lia/recherche | Recherche am Ort (Abschnitt 5): Adapter setzen `ort`, `agentkit.recherche` sammelt Recherchen am Ort und darüber (Bestand) und den Ortskontext; Arbeitsplatz zeigt Recherchen im Baum an ihrem Ort, Textfeld an jeder Seite, `/recherchen` entfällt. | Bestand über Ebenen, Ort fehlt oder archiviert |
| 7 | Hauptordner, uni, lia/recherche | Planlauf und Start aus dem Plan: Planformat in agentkit, uni nimmt Teilfragen statt Eckpunkten, lia/recherche baut die Auftragsdatei aus dem Plan. Arbeitsplatz-Art recherche auf Plan umstellen. | Planprüfung, Auftragsdatei aus Plan |
| 8 | uni, lia/recherche | Ausweiten: neue Sitzung mit `bestand_text`, Einarbeiten, Zählung Doppelter. Erster echter Lauf auf „milde Jugendtaten“ (Ziel: Berliner Fälle). | Prompt enthält Sperren und Verworfenes; Einarbeiten |
| 9 | Hauptordner | Quellenbibliothek: Gruppen in `einstellungen.toml` (Vereinigung bleibt gleich, Test vergleicht vorher/nachher), Seite im Arbeitsplatz lesend mit Vorschlagsliste. | `test_einstellungen`, Arbeitsplatz |
| 10 | lia/recherche, Hauptordner | Eingang für Lia: Dienst `lia-recherche` (Installation nur mit Jans Okay), Aufträge aus Lias Instanz, Absichtserkennung aus 6a auch für Lia; lia/chat liest `wissen.json`. | Absicht prüfen (unbekannt, mehrdeutig, regel) |
| 11 | shared/webapp | Recherche-Seite für Lia: Plan in Sätzen mit „Los“, ein Textfeld, Dokument wie heute. | App-Tests, Rundgang gegen 127.0.0.1:8791 |
| 12 | alle | Probe: je eine echte Recherche für Jan und Lia von Anfang bis Dokument, Abnahme nach Jans Eindruck. | |

Schritte 1 bis 4 kosten nichts (kein Claude-Lauf) und machen schon sichtbar, ob das Format trägt. Fallsuche als
dritter Adapter erst nach Schritt 8, wenn das Format für Webaufträge steht.

## 9. Entscheidungen für Jan
Entschieden (Jan 15.11.2026): Auch Jans Seite mit wenigen Knöpfen, der Rest im „···“ (Abschnitt 5). Alle neun
Punkte unten wie empfohlen (Jan 15.11.2026: „Ja, alle so“). Bau beginnt mit Schritt 1 im Hauptordner-Chat.

1. **Gemeinsames Format** in `agentkit.recherche`, Motoren bleiben und schreiben es über Adapter, Ablage
   `data/projekte/<id>/` je Agent. **Empfehlung: ja.**
2. **Alte Läufe** als Projekte einlesen (Lias v1 und v2 je als zwei Läufe eines Projekts). **Empfehlung: ja**,
   die alten Ordner bleiben unverändert liegen.
3. **Planlauf**: Sonnet ohne Web, Kosten schätzt Python aus gemessenen Läufen. Oder mit wenigen Websuchen, damit
   der Plan sieht, was es gibt (teurer, aber besserer Plan)? **Empfehlung: ohne Web**, Lücken zeigt erst der Lauf.
4. **Gruppen im Plan** steuern nur, wo zuerst gesucht wird, oder sperren WebFetch für den Lauf auf die gewählten
   Gruppen? **Empfehlung: nur steuern**; enger würde Läufe wie „milde Jugendtaten“ wieder dünn machen.
5. **Neue Seiten**: Bibliothek zuerst nur lesend mit Vorschlagsliste, Eintrag weiter über den Hauptordner-Chat;
   ein Knopf „Aufnehmen“ für dich bräuchte eine Ausnahme wie `commit-daten.sh` für `einstellungen.toml`.
   **Empfehlung: erst lesend.**
6. **Lias Ergebnisse ohne deine Vorschau**: Startet Lia selbst, geht das Dokument direkt an sie (Python prüft die
   Sprachregel); du siehst alles im Arbeitsplatz. Startest du für sie, bleibt die Vorschau. **Empfehlung: so.**
7. **Lias Verwerfen und Sperren im Projekt** ohne Stopp-Knopf für dich (rückgängig bleibt), nur allgemeine Regeln
   über den Feedback-Weg mit Stopp. **Empfehlung: so.**
8. **Kostengrenzen je Lauf** bleiben wie im Code (Lia 8/25, Fallsuche 15, uni 15/50 USD), Ausweiten bekommt dieselbe
   Grenze wie ein neuer Lauf gleichen Aufwands, Fragen 0,50 USD. **Empfehlung: so.**
9. **Reihenfolge**: Schritte 1 bis 4 zuerst (ohne Kosten), danach Fragen, Nachprüfen, Plan, Ausweiten, zum Schluss
   Lias Eingang und Seite. **Empfehlung: ja.**
