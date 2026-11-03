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
  (Lia): Termin, Abgabe Entwurf, Stundenzahl, Stundenlänge, Schulform (bestimmt die Niveaustufe),
  Bewertungsbogen, Reihenfrage, Seminarvorgaben zur Reihenfrage. Welche Reihe und die Stelle der Prüfungsstunde
  stehen seit 03.11. nur in lia/instanz/reihen.toml (siehe Aufbau). Verordnung vermutlich VSLVO
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
  angesehen. Jan schickt beides an Lia; ihre Antworten trägt Jan hier ein.
- Lesehilfe (25.10., Jan verstand die Skizzen nicht: „Wer ist Jonas? Was ist Audio?“): Runde 1 erklärte ihre
  Fälle nur in den Annahmen und schrieb fehlendes Material (Audio, Video, Doku, vereinfachte Texte) so, als gäbe
  es es. Nachtrag data/reihe/runde-1/lesehilfe.json (im Chat aus skizzen.json zusammengestellt, ohne Claude-Lauf):
  Fälle Jonas und Selin, fehlendes Material je Skizze. Kurzfassung jetzt 5 Seiten: Seite 1 Fälle und Abkürzungen,
  je Skizze eine Seite mit Kasten „Gibt es noch nicht“, Annahmen am Ende. Version 9e9e121.
- Ab Runde 2 (skizzen.py): Pflichtfelder fall und abschlussfall (je höchstens 600 Zeichen, jede Person dort
  eingeführt), material_fehlt (Liste mit Stunde), Abkürzungen nur aus GLOSSAR (AFB, BBB, LEK, RLP, StGB, JGG,
  ISS, UB, OCR, Doku), andere Großbuchstaben-Kürzel lehnt die Prüfung ab. annahmen im Prompt auf je ein bis
  zwei Sätze begrenzt (noch nicht von Python geprüft).
- Lias eigener Auftrag (25.10., gesprochen, über Jan): Reihenfragen, reale Fälle, Norwegen, Liszts Tätertypen.
  Im lia-Chat von Hand recherchiert (nicht über die Agenten), Ergebnis data/reihe/recherche-1/
  „Recherche Reihe Strafe.docx“ (4 Seiten, mit Quellen; Erzeugung erzeugen.py daneben), Version e1b145d.
  Kernbefunde: (1) Liszt (ZStW 3, S. 39–42, OCR, am Scan prüfen) sieht für alle drei Tätertypen Freiheitsentzug
  vor, für Unverbesserliche (rückfällige Eigentumstäter) Einschließung auf unbestimmte Zeit; „Liszt = mild“ ist
  falsch. Der Liszt-Merksatz aus Runde 1 (Jonas: Bewährung) ist damit fachlich falsch. (2) Reale Fälle: Ingrid M.
  (85, Memmingen, 17,63 Euro, 4 Monate Haft, LG Memmingen 09.04.2019) empfohlen, Containern Olching (AG
  Fürstenfeldbruck 30.01.2019, BVerfG 18.08.2020), Schul-Einbrüche Bergisch Gladbach (Dez. 2019).
  (3) Empfehlung Struktur: ein Fall, neue Täterinfos in der Examensstunde. (4) Norwegen: kein frei abrufbares
  Video verifiziert, nur Spuren (arte „Kathedralen der Kultur“ Halden, 26 Min., 2016). Nussbaum nicht empfohlen.
  examen.toml: Schulform Gemeinschaftsschule Neukölln (Niveau offen), Prüfungsstunde = Anwendungsstunde zu Liszt.
- Beispiele des Fachseminars (25.10., Jan per scp, zwei Scans, Originale data/vorgaben/seminar/, keine
  Schülerdaten): Reihenplanung Klasse 8 „Geschlecht – angeboren oder anerzogen?“ und Material „Dürfen wir Tiere
  essen?“. Abschriften in lia/unterricht/data/wissen/eingang/Seminar/ (Katalog aktualisiert). Daraus
  seminar_vorbild.md (Beobachtungen, keine Regeln; Lia bestätigt): eine Problemfrage mit zwei Polen, Tabelle
  Problemfrage/Inhalt/Perspektive/Kompetenz/Material, Verlauf eigenes Urteil → Klärung → realer Fall →
  Positionen → Debatte → schriftliches Urteil mit Checkliste. Geht in Skizzen- und Prüfer-Lauf (runde.py
  Pfade.vorbild). Skizzen brauchen ab Runde 2 je Stunde einen RLP-Kompetenzbereich; alle vier müssen vorkommen.
- Strukturplan Bauschritt 2 (03.11.2026, docs/struktur-pflege-plan.md, Jan F14 „Examen ist eine Stunde“):
  examen liest die Reihe nur noch über agentkit.struktur. titel_in_reihen_toml und pruefungsstunde_in_reihe sind
  aus examen.toml, skizzen.py, kurzfassung.py raus. reihe_text stürzt mit Stunden nicht mehr ab (vorher TypeError
  bei "; ".join über die Stunden-Tabellen). Bis zur Migration (Bauschritt 3) hat keine Reihe Stunden: examen
  läuft dann nicht, gewollt. Kein echter Lauf in diesem Schritt (kommt mit der Abnahme, Plan Abschnitt 12).
- Tests: 46, grün (davon LeserTest = Testregel 22 auf den eingefrorenen Daten von agentkit). Kein Dienst, kein
  Timer.

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
  derselben Sitzung, danach Abbruch mit Meldung.
- Welche Reihe (grundlagen.pruefungsreihe): struktur.laden() (lia/instanz), dann s.pruefungsreihen() (nicht
  archivierte Reihen mit sichtbarer Stunde Marke „Prüfung“) und s.pruefungsstunde(id). Die Nummer dieser Stunde
  ist die Prüfungsstunde der Skizzen (skizzen.prompt/pruefen, Parameter ps). Keine oder mehrere Reihen bzw.
  Prüfungsstunden, oder reihen.toml kaputt: runde.ReiheFehlt, kein Claude-Lauf, Meldung an Jan mit dem, was Lia
  eintragen muss, aber nur, wenn sich der Text seit der letzten Meldung geändert hat (data/zustand.json, Feld
  reihe; eine eindeutige Reihe setzt es auf ""). Gilt für den späteren Timer genauso. grundlagen.py zeigt den
  Zustand als „ok“ oder „offen“. kurzfassung.py nimmt den Titel der gefundenen Reihe.
- Kontext jedes Laufs: Reihe aus lia/instanz/reihen.toml über agentkit.struktur (runde.reihe_text: Felder der
  Reihe ohne ids, Zeile „Prüfungsstunde: Stunde n von m“, alle sichtbaren Stunden mit Nummer, Prüfungsstunde als
  [PRÜFUNGSSTUNDE], UB als [UB]), Lias Gelernte Regeln aus lia/unterricht/STATUS.md, lia/unterricht/leitfaden.md,
  Register lia/recherche/data/register.json (alles nur gelesen).
- Daten im Repo (keine Schülerdaten): rubrik.toml, rlp_auszug.toml, examen.toml, impuls.md.
- data/vorgaben/RLP_Ethik_Sek_I.pdf: Kopie aus lia/unterricht/data/wissen/eingang/Vorgaben/ (nicht im Repo).
- .venv: pypdf und die Pakete des Renderers (Versionen wie shared/renderer/requirements.txt), agentkit und
  renderer per agentkit.pth.
- kurzfassung.py: `.venv/bin/python kurzfassung.py` baut Kurzfassung und Bogen für Runde 1 aus skizzen.json und
  pruefung.json und sichert eine neue Version. profil.toml: Kopie von lia/unterricht/profil.toml.
- Reihenkontext (Lerngruppe, Vorwissen, Kant dann von Liszt) steht in lia/instanz/reihen.toml (Lerngruppe nach
  der Migration in lia/instanz/lerngruppen.toml), nicht doppelt.
- Tests: tests/test_runde.py LeserTest nutzt shared/agentkit/tests/daten/reihen_alt.toml (eingefrorene echte
  Datei) und reihen_neu.toml (neues Format mit Stunden), nur gelesen.

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
4. Verbesserungen am Ablauf vor Runde 2: Länge der annahmen in Python begrenzen (Runde 1: ca. 5000 Zeichen);
   impuls.md in den Kontext (Claude kannte den echten Impuls nicht und nahm einen anderen an).
5. Danach Folgerunden (Schritt 6) nur für die gewählte Richtung.
6. Vor Runde 2: Kontext der Skizzen um Lias Vorgaben aus ihrem Auftrag ergänzen (reale Fälle mit Quelle statt
   erfundener, Examensstunde = Liszt-Anwendung, didaktischer Bogen: erst passt eine Strafe spontan, mit mehr
   Kontext eine andere) und das Ergebnis der Webrecherche V2 als Anhang/Kontext mitgeben
   (lia/recherche/data/web/20261025-211917-lia-reihe-strafe-v2/). Liszts Tätertypen stehen seit 25.10. als
   7 geprüfte Stellen im Register (erledigt); der Liszt-Merksatz aus Runde 1 („Bewährung“ für Jonas) ist falsch
   und darf nicht wieder auftauchen. Regelvorschlag an Lia: „Fälle nur real und mit Quelle“ (erst nach Okay).
7. Webrecherche durch die Agenten: erledigt 25.10. (lia/recherche, webauftrag.py, Domains in
   shared/einstellungen.toml [webfetch]). Offen dort: Lias Zentrale als Eingang, Teilläufe für gründliche
   Aufträge, Prüflauf „trägt das Zitat?“ mit haiku nur Vorsortierung (siehe lia/recherche/STATUS.md).
8. Lia soll seminar_vorbild.md lesen und bestätigen, was davon Regel werden soll.
9. Strukturplan: Nach der Migration (Bauschritt 3) muss Lia die Stunden der Straftheorien eintragen und die
   Prüfungsstunde markieren, sonst läuft examen nicht. Abnahme (Plan Abschnitt 12): Prüfungsstunde in der App
   verschieben, dann echte Runde 1; Kontext muss Reihe und neue Stelle nennen.
10. Frage an Jan (nicht entschieden): stundenzahl bleibt in examen.toml. Sobald Lia alle Stunden einträgt,
   könnte die Zahl ihrer Stunden die Vorgabe für die Skizzen sein; heute gilt sonst 8 bis 10.

## Gelernte Regeln
- (noch keine)
