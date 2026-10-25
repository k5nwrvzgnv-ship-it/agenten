# Status: Agent examen (Lias Instanz)

## Zweck
Automatisiert die Planung von Unterrichtsreihen für Lia: Grobskizzen (Varianten), Kritik (Prüfer-Lauf gegen
die Rubrik, Kolloquiumsfragen), Quellen aus lia/recherche. Erster Bestand ist ihre Examensreihe Ethik Klasse 8,
Straftheorien (Berlin, Prüfung ca. Ende November 2026). Lia wählt die Richtung und bewertet jede Runde.

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
- Quellen: Register von lia/recherche fertig (StGB § 46, JGG § 2, Kant 5 Stellen, Liszt 5 Stellen vom Scan).
- Runde 1 echt gelaufen (25.10., von Hand, Version b9090a0 in data/reihe/): 2,47 USD (Skizzen 0,62 + Kürzung
  0,94, Prüfer 0,91). Erster Skizzen-Lauf zu lang (4200–4500 statt 3000 Zeichen), nach einer Nachbesserung
  gültig. Skizzen: A „Klassischer Weg: erst Kant, dann von Liszt“ (10 von 15 Kriterien unter „gut“),
  B „Provokation zuerst: von Liszt vor Kant“ (8), C „Gefängnis von innen“ (11). Keine Stufe „nicht erkennbar“.
  Prüfer-Kritik fachlich treffend (z. B. B führt Liszt als „überhaupt strafen?“ statt als Zweckstrafe ein).
  Annahmen der Skizzen: 8 Stunden, ISS grundlegendes Niveau (Stufen D–E), Liszt auf Besserung reduziert,
  Ankerfall „Jonas“ (Einbrüche, keine Gewalt), Kants Hinrichtungsbeispiel nicht verwendet.
  Dateien: data/reihe/runde-1/ (skizze-A/B/C.md, bericht.md, skizzen.json, pruefung.json).
- Für Lia (25.10., kurzfassung.py, ohne Claude, über shared/renderer mit profil.toml): data/reihe/runde-1/fuer-lia/
  „Runde 1 - drei Grobskizzen.docx“ (4 Seiten: Annahmen je erster Satz, je Skizze eine Seite mit Prüfer-Kernsatz
  oben) und „Runde 1 - Bewertungsbogen.docx“ (je Skizze Note 1–5, was stört, was übernehmen; Wahl A/B/C/Mischung;
  Annahmen; Regelwunsch; Tabelle der offenen Angaben aus examen.toml). Vorschau als PNG/PDF daneben, von Claude
  angesehen. Version ed060d3. Jan schickt beides an Lia; ihre Antworten trägt Jan hier ein.
- Tests: 32, grün. Kein Dienst, kein Timer.

## Aufbau
- Instanz: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz
- Code: grundlagen.py (Rubrik, RLP-Auszug, examen.toml laden und prüfen; `.venv/bin/python grundlagen.py`).
  Wörtlicher Vergleich über agentkit.wortlaut (seit 25.10. dort, vorher lia/examen/wortlaut.py).
- Runde 1: `AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python runde.py`
  runde.py (Ablauf, Kostengrenze 8 USD, Meldung an Jan), skizzen.py (Kontext, Prompt, Prüfung: genau A/B/C,
  2–4 RLP-ids, Quellen nur als Verweis <quelle>:<seite> ins Register, Stundenzahl aus examen.toml sonst 8–10,
  alle drei Perspektiven, genau eine Prüfungsstunde, höchstens 3000 Zeichen je Skizze), pruefer.py (neue
  Sitzung, jedes Kriterium genau einmal mit Stufe und Beleg, fünf Kolloquiumsfragen), versionen.py (data/reihe/
  als lokales Git-Repo, Autor „Agent examen“, ohne geerbte GIT_*-Variablen). Je Lauf eine Nachbesserung in
  derselben Sitzung, danach Abbruch mit Meldung. Welche Reihe: examen.toml [reihe] titel_in_reihen_toml.
- Kontext jedes Laufs: Reihe aus lia/unterricht/reihen.toml, Lias Gelernte Regeln aus lia/unterricht/STATUS.md,
  lia/unterricht/leitfaden.md, Register lia/recherche/data/register.json (alles nur gelesen).
- Daten im Repo (keine Schülerdaten): rubrik.toml, rlp_auszug.toml, examen.toml, impuls.md.
- data/vorgaben/RLP_Ethik_Sek_I.pdf: Kopie aus lia/unterricht/data/wissen/eingang/Vorgaben/ (nicht im Repo).
- .venv: pypdf und die Pakete des Renderers (Versionen wie shared/renderer/requirements.txt), agentkit und
  renderer per agentkit.pth.
- kurzfassung.py: `.venv/bin/python kurzfassung.py` baut Kurzfassung und Bogen für Runde 1 aus skizzen.json und
  pruefung.json und sichert eine neue Version. profil.toml: Kopie von lia/unterricht/profil.toml.
- Reihenkontext (Lerngruppe, Vorwissen, Kant dann von Liszt) steht in lia/unterricht/reihen.toml, nicht doppelt.

## Entscheidungen
- 25.10.2026 (Jan): Bundesland Berlin, Seminar egal, Prüfung in etwa einem Monat. KI-Regeln des Seminars
  spielen für die Planung keine Rolle (Jan); Hinweis an Lia: selbst prüfen, falls sie eine Erklärung
  über die selbstständige Anfertigung unterschreibt.
- 25.10.2026 (Jan): Freigegeben: zwei Agenten mit Timern (lia-recherche, lia-examen), Allowlist, 8 USD je Nacht,
  Zentrale-Bogen und agentkit-Abruf (Hauptordner-Chat), Impuls über die Freigabe, eigenes lokales Repo der Reihe.

- 25.10.2026 (Jan): Plan lia/recherche freigegeben, Teile A–D: A agentkit.abruf (Allowlist, Cache) und
  wortlaut nach agentkit (Hauptordner-Chat); B quellen.toml, Parser, Register, Gemeinfreiheit für StGB § 46,
  JGG § 2, Kant AA 6:331–337 ohne Claude; C Liszt „Zweckgedanke“ (ZStW 3, 1883; Band unter den Google-Scans auf
  archive.org per Textsuche finden) und Kernstellen per Claude; D Timer 02:30. Auswahl der Kernstellen mit Opus,
  Meldungen nach jedem Lauf an Jan (nicht Lia), Lia prüft jedes verwendete Liszt-Zitat am Scan (OCR).

## Offene Punkte
1. Lia: offene Angaben in examen.toml liefern, Rubrik-Entwurf durchsehen, Bewertungsbogen schicken.
2. Impuls freigeben (Lias Zentrale) und einsetzen, Ergebnis in examen.toml [impuls].
3. Schritt 5: Lia bewertet Runde 1 mit dem Bogen (docx, über Jan). Danach: Antworten eintragen, offene Angaben
   nach examen.toml, Regelvorschläge aus „was stört“ und dem Regelwunsch (erst nach Lias Okay eintragen).
   Der Bogen in ihrer Zentrale fehlt weiter (Haupt-STATUS Punkt 10).
4. Verbesserungen am Ablauf vor Runde 2: annahmen sind nicht begrenzt (Runde 1: ca. 5000 Zeichen, mehr als
   eine Skizze), Grenze und Pflichtfelder einführen; impuls.md in den Kontext (Claude kannte den echten Impuls
   nicht und nahm einen anderen an).
5. Danach Folgerunden (Schritt 6) nur für die gewählte Richtung.

## Gelernte Regeln
- (noch keine)
