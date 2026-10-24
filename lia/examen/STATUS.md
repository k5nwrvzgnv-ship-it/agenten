# Status: Agent examen (Lias Instanz)

## Zweck
Unterstützt Lia bei ihrer Examensreihe Ethik Klasse 8, Straftheorien (Berlin, Prüfung ca. Ende November 2026).
Die Reihe bleibt Lias Leistung: Der Agent liefert Varianten (Grobskizzen), Kritik (Prüfer-Lauf gegen die Rubrik,
Kolloquiumsfragen) und arbeitet mit Quellen aus lia/recherche. Lia entscheidet und schreibt ihren Entwurf selbst.

## Plan (Jan 25.10.2026, Punkte 1–6 freigegeben)
1. Grundlagen: Rubrik, RLP-Wortlaut, Prüfungsangaben, anonymer Vorab-Impuls. ERLEDIGT bis auf Lias Angaben.
2. lia/recherche (eigener Agent, Timer nachts): gemeinfreie Primärtexte (Platon, Kant, Beccaria, Bentham, Hegel,
   Feuerbach, Liszt, Nietzsche) und StGB § 46, JGG § 2, nur von der Allowlist; Quellenregister mit Fundstelle und
   Gemeinfreiheit (bei Übersetzungen auch Übersetzer); Python prüft jedes Zitat wörtlich. Klein anfangen
   (Gesetze, Wikisource).
3. Runde 1 (eine Nacht): drei Grobskizzen je eine Seite, verschiedene didaktische Grundentscheidung, rückwärts ab
   Abschlussaufgabe, je mit Reihenfrage und RLP-Bezug (ids aus rlp_auszug.toml).
4. Prüfer-Lauf: jede Skizze gegen rubrik.toml (Stufe + Beleg je Kriterium), fünf Kolloquiumsfragen je Skizze.
5. Lias Bewertung über ihre Zentrale (Bedarf in Haupt-STATUS, Punkt 10), daraus Regelvorschläge nach Lias Okay.
6. Folgerunden nur für die gewählte Richtung; jede Runde ein Commit im eigenen Repo data/reihe/ (nicht pushen).
7. Ende: alle Kriterien mindestens „gut“, Lia begründet jede Entscheidung selbst, Fachseminarleitung hat die
   Grobskizze gesehen. Obergrenze 8 USD Kontingent je Nacht (Jan), danach Abbruch mit Meldung.

## Stand (25.10.2026)
- rubrik.toml: ENTWURF, 15 Kriterien (12 wörtlich aus Lias Fachseminar „Kriterien gute Unterrichtseinheit“,
  dazu Differenzierung, fachliche Richtigkeit, Begründbarkeit im Reflexionsgespräch), Stufen nicht erkennbar /
  ansatzweise / gut / sehr gut, Schwelle „gut“. Prüffragen und „gut“-Beschreibungen sind Claudes Auslegung,
  Lia hat sie noch nicht gesehen. Lias offizieller Bewertungsbogen fehlt; im Netz nicht gefunden (berlin.de
  sperrt automatische Abrufe, Handbuch Vorbereitungsdienst 2017 hat keinen Bogen für die Prüfungsstunde).
- rlp_auszug.toml: 23 Stellen aus dem RLP Ethik Sek I (Themenfeld 3.3 Strafe, verbindliche Vorgaben,
  Niveaustufen ISS/Gymnasium/Förderbedarf Lernen, Standards 2.3 D–F, drei weitere mit unsicherer Stufe).
  Alle 23 wörtlich auf ihrer Seite im PDF belegt (grundlagen.py).
- examen.toml: Prüfungsangaben und Reihenfrage-Kandidaten, Anregungen aus „Tipps Max Examens.docx“. Offen
  (Lia): Termin, Abgabe Entwurf, Stundenzahl, Position der Prüfungsstunde, Stundenlänge, Schulform (bestimmt
  die Niveaustufe), Bewertungsbogen, Reihenfrage, Seminarvorgaben zur Reihenfrage. Verordnung vermutlich VSLVO
  2014 (Beginn vor 02.02.2026), von Lia zu bestätigen.
- Vorab-Impuls: impuls.md (5 Fragen, anonym, Papier, ca. 5 min, mit Hinweisen für Lia). Liegt in Lias
  Freigabe-Warteschlange: 20261025-003745-examen-0c44bf. Nach Lias Freigabe von Hand als ausgeführt vermerken
  (freigabe.ausfuehrung_beginnen/abschliessen, „Lia setzt selbst ein“), bis die Zentrale das kann.
- Tests: 14, grün. Noch kein Claude-Lauf, kein Dienst, keine Kosten.

## Aufbau
- Instanz: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz
- Code: grundlagen.py (Rubrik, RLP-Auszug, examen.toml laden und prüfen; `.venv/bin/python grundlagen.py`),
  wortlaut.py (wörtlicher Vergleich ohne Leerraum und Silbentrennung, Seiten aus der Textfassung).
- Daten im Repo (keine Schülerdaten): rubrik.toml, rlp_auszug.toml, examen.toml, impuls.md.
- data/vorgaben/RLP_Ethik_Sek_I.pdf: Kopie aus lia/unterricht/data/wissen/eingang/Vorgaben/ (nicht im Repo).
- .venv: pypdf (Version wie lia/unterricht), agentkit per agentkit.pth.
- Reihenkontext (Lerngruppe, Vorwissen, Kant dann von Liszt) steht in lia/unterricht/reihen.toml, nicht doppelt.

## Entscheidungen
- 25.10.2026 (Jan): Bundesland Berlin, Seminar egal, Prüfung in etwa einem Monat. KI-Regeln des Seminars
  spielen für die Planung keine Rolle (Jan); Hinweis an Lia: selbst prüfen, falls sie eine Erklärung
  über die selbstständige Anfertigung unterschreibt.
- 25.10.2026 (Jan): Freigegeben: zwei Agenten mit Timern (lia-recherche, lia-examen), Allowlist, 8 USD je Nacht,
  Zentrale-Bogen und agentkit-Abruf (Hauptordner-Chat), Impuls über die Freigabe, eigenes lokales Repo der Reihe.

## Offene Punkte
1. Lia: offene Angaben in examen.toml liefern, Rubrik-Entwurf durchsehen, Bewertungsbogen schicken.
2. Impuls freigeben (Lias Zentrale) und einsetzen, Ergebnis in examen.toml [impuls].
3. Nächster Schritt: lia/recherche (eigener Chat in lia/recherche/), zuerst StGB § 46, JGG § 2, Kant und Liszt.
4. Danach Runde 1 (examen.py mit claude_lauf, Prüfer), zur Not von Hand ausgelöst, bevor der Timer steht.

## Gelernte Regeln
- (noch keine)
