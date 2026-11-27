# Status: Agent fehlstellenscan (Fehlstellen-Scan)

## Zweck
Arbeit mit YOLO für Jans Forschungsprojekt zur Fehlstellenerkennung an Holzlamellen (HNEE, Betreuung
Prof. Böhme): Datensätze bauen und prüfen, Trainingsläufe auswerten und vergleichen, später Vorhersagen auf
neuen Bildern. Getrennt von uni/ (Moodle, Post) und holzbalkenscan/ (Prüfstand für Felix' Streifenbilder;
die können später als Dateien Eingabe werden).

## Ziele und Wettbewerb (Jan 12.11.2026)
- Ziele: (1) Forschungsprojekt HNEE. (2) Mit Prototyp und Projekt auf die Ausschreibung der TU für einen
  Altholz-Scanner bewerben. (3) BSH-Werken einen Scanner vor dem Kappen zur Endloslamelle vorschlagen.
- Wettbewerb: Dataspree (Proof of Concept „Oberflächeninspektion“, gezeigt 12.11.2026). Stand laut ihren Folien:
  eine Sichtseite, eine Kamera (5.472 px, 0,035 mm/px, also rund 19 cm je Bild), Balkenhöhe muss eingegeben
  werden, Kalibrierung vor Ort nötig, Toleranz der Vermessung nicht genannt, erkannt vor allem Bohrlöcher und
  Äste; Tracking über Bildgrenzen, weitere Defekttypen und Laborintegration erst im Ausblick. Ihr Berichtsentwurf
  (Balkenkarte, Merkmalsliste, Grenzwerte, Balken-ID) ist ein Demo-Bild mit widersprüchlichen Maßen und bewertet
  OK/nicht OK nach Fläche, nicht nach Sortierklasse. Für BSH-Kapplinien gibt es nach Claudes Wissen (ungeprüft)
  eingeführte Anbieter (Microtec Goldeneye, WEINIG CombiScan); vor einem Vorschlag an Werke Markt recherchieren.
- Marktrecherche Kappscanner (12.11.2026): docs/markt-kappscanner.md (Anbieter, Preise, Zielgruppe, Lücke, Fragen
  an die zwei Werke). Befunde: (1) MiCROTEC und WEINIG decken den Markt ab, vier Seiten, Laser plus Farbe,
  Röntgen optional, 2,5 bis 20 m/s; WEINIG hat eigene Einstiegsgeräte (SOLID SCAN 1000, EasyScan Smart C).
  (2) Neupreise nirgends öffentlich; verbreitete Alternative ist Kreidemarkierung von Hand plus optimierende
  Kappsäge. (3) Normweg für Kamera plus YOLO ist apparativ unterstützte visuelle Sortierung (DIN 4074-3:2025-06),
  nicht maschinelle Festigkeitssortierung nach EN 14081. Kostenschwelle nur über die zwei Werke klärbar.
- Recherche Hardware und Training (20.11.2026): docs/recherche-hardware-training.md (Notizen daneben). Befunde:
  (1) 5-10k reicht für einen Demonstrator (zwei Farbzeilen- oder Flächenkameras oben/unten, Hand-Durchschub mit
  Messrad-Encoder, Lichttunnel, Laserlinie Eigenbau Klasse 2, Jetson), nicht für Industrie (45-140k geschätzt).
  (2) Engpass ist die Annotation, nicht Rechenzeit; eigener Kodytek-Lauf liegt auf dem Niveau publizierter
  Arbeiten mit 3.500 Bildern. (3) Verdeckte Nägel, innere Fäule, A-Kategorien sieht keine Kamera. (4) WIn-Altholz
  (FNR, HNEE-koordiniert, NIR-Handscanner) ist Anknüpfungspunkt für die Bewerbung.
- Entwurf Aufnahme-Apparatur für den Termin bei Felix am 27.11.2026 (22.11.2026, nicht entschieden):
  docs/entwurf-aufnahme-apparatur.md und unterlagen/apparatur-skizze.svg. Jans Vorgaben: Licht und Abstand fest,
  wenig Aufwand, smart mit Metadaten. Vorschlag: fertige LED-Fotobox mit Schlitzen als Reiter auf dem Balken,
  Jans Fund Somikon 40 cm (h 250 mm, rund 22 Px/mm, Flächen bis 23 cm, laut Jan meist so), Kamera-App mit festen Werten, Balkendaten per iPhone-Kurzbefehl, Zuordnung der Fotos
  per EXIF-Zeit mit Skript `aufnahme.py ordnen` (noch nicht gebaut, wartet auf Jans Okay).
- Vorschlag erster Altholz-Test (20.11.2026, nicht entschieden): docs/plan-erster-test-altholz.md (iPhone-Fotos bei
  Felix, selbst labeln, Training auf dem Mac). Für die Gruppe gedacht, Rüdiger liest ihn über docs/.
- Mögliche Umstrukturierung (Jan 22.11.2026, nicht entschieden): Die TU bietet an, wir machen die Software, sie
  stellt Ausrüstung und Material; Fokus wäre der Altholz-Scanner mit Ausblick BSH/KVH. Erst Machbarkeitstest
  (Fotos bei Felix 27.11., labeln, trainieren), dann Zusage an die TU oder weiter wie im Exposé. Vorbereitung für
  Henri und Prof. Böhme (23.11., erstes Gespräch) mit Pitch und Grundlagen: docs/vorbereitung-boehme-23-11.md.
- Plan Werkbank (Jan 23.11.2026): docs/plan-trainingswerkzeug.md. Oberfläche für die Schleife Daten ansehen,
  Fehler finden, labeln, nachtrainieren, gegen Messlatte prüfen; Maskenstil einstellbar und in seinen Folgen
  sichtbar. Reihenfolge von Jan bestätigt. Phase 0 gebaut (23.11.): docs/messprotokoll-27-11.md (Messschieber bei
  Felix, Äste nummerieren, 5 Äste doppelt messen; diese Balken nur Test), docs/labelrichtlinie.md (Entwurf,
  Henri und Felix lesen gegen), auswertung.py. Henri und Felix haben Windows und Mac (X-AnyLabeling passt).
  Phase 1: läuft seit 23.11.2026 auf Jans Mac (Abschnitt Werkbank). Offen: Freigabe X-AnyLabeling (Phase 2);
  Normfrage, was zum Ast zählt.
- Werkbank als Web-App (Jan 24.11.2026, Entwurf, nicht entschieden): docs/bauplan-werkbank-web.md, klickbarer Entwurf
  unterlagen/werkbank-entwurf/. Jan hat ein KI-Rechenzentrum zugesagt bekommen (GPU und Datenregeln offen).
  Sechs Looks auf der neuen Bedienung mit Bedienfeld: unterlagen/werkbank-looks/ (befund.md). Seit 25.11.2026 gegen UI/UX-Regeln überarbeitet.
  Jan hat Nachtschicht mit Figtree gewählt (24.11.2026, „passt erstmal“), weiter am 25.11.
  Test 25.11.2026: unterlagen/werkbank-skill-pur/ zeigt, was UI/UX Pro Max ohne Jans Einstellungen baut (befund.md, vergleich.jpg).
  Jan 25.11.: in vielem besser. Weiter in unterlagen/werkbank-regler/ (Bedienfeld, weniger Knöpfe), Jans Werte sind Startfassung, Umrisse dünner.
- Fotobox-Aufnahme (Jan 25.11.2026, gebaut, am iPhone noch nicht erprobt): aufnahme/ (Abschnitt Fotobox-Aufnahme).
- Ansatz „besser als Dataspree“ (Vorschlag, nicht entschieden): Masken statt Boxen fürs Messen (Kodytek hat
  Masken), Gesamtkarte über die ganze Länge (Kodytek-Gruppen schließen vermutlich lückenlos an), DIN 4074 als
  getestete Python-Regeln getrennt vom Modell (Sortierklasse, alle vier Seiten, Normtext vorher prüfen),
  Kennzahlen je Klasse und Messunsicherheit statt nur Konfidenz, Unsicheres an einen Menschen, Höhe messen statt
  eingeben. Gemeinsamer Kern (Erkennen, Messen, Karte), Klassen und Regelwerk je Einsatz austauschbar.
- Altholz: Kodytek deckt typische Merkmale nicht ab (Nägel, Schrauben, Farbe, Fäulnis, Insektenfraß, alte
  Verbindungen), eigene Bilder nötig; verdecktes Metall braucht vermutlich einen Metalldetektor. BSH: übersehene
  Fehler wiegen schwerer als Fehlalarme, Tempo und alle vier Seiten zählen.

## Ideen, Ausblick (Jan 12.11.2026, nicht entschieden)
- Recherche 12.11.2026: docs/recherche-zwilling-flicken.md. Befunde: (1) Äste aus Oberfläche ist etabliert
  (TU Wien: 3D-Äste aus Faserwinkeln per Laser, nicht aus Farbbild; Rundholz mit Deep Learning, Engpass
  CT-Paare, daher künstliche Daten). (2) Zwilling aus Lamellenscans gibt es als Forschungsaufbau (TU Wien 2018,
  50 BSH-Träger), nicht als Industrielösung. (3) Flickautomaten (Wintersteiger TRC Woodpatch) nur für dünne
  Decklagen 10-20 mm. Studie Poznań 2022: ausgefräste Randäste in 40-mm-Kiefernlamellen, BSH-Träger über
  40 N/mm² im Mittel, nicht zugelassen. Schiffchen in Sichtqualität laut Verband zulässig, ein Hersteller
  widerspricht. EN 14080 selbst nicht eingesehen.
- Tracheideneffekt (Jan 12.11.2026, Abschnitt 4 der Recherche): Laserpunkt wird auf Holz zur Ellipse in
  Faserrichtung, auf Ästen rund. Liefert Faserwinkel, die Grundlage für 3D-Äste (TU Wien). Für Fichte reicht
  roter Laser um 650 nm und CMOS-Kamera (Rotkanal); Laubholz braucht Nahinfrarot. Idee erster Versuch:
  Punktraster-Modul, Kamera, gehobeltes Fichtenbrett, Ellipsen mit numpy/OpenCV. Laserschutz, Kosten und
  Leistung vorher klären; Pakete (OpenCV) nur nach Jans Okay.
- Inneres aus der Oberfläche: Modell, trainiert mit Paaren aus Oberflächenscan und CT, schätzt die 3D-Lage von
  Fehlstellen. Tragfähig nur für Merkmale mit Spur an der Oberfläche, vor allem Äste (Kegel vom Mark nach außen,
  auf mehreren Seiten sichtbar). Fäulnis, Hohlräume, innere Risse, Metall nicht ableitbar (Modell würde raten);
  für Altholz daher kein Ersatz für CT, Ultraschall oder Metalldetektor. Ausgabe mit Unsicherheit. Einstieg ohne
  CT: Äste auf allen vier Seiten erkennen, einander zuordnen, Kegel anpassen (Geometrie, testbar).
- Digitaler Zwilling BSH: aus den Vierseiten-Scans jeder Lamelle vor dem Verkleben zusammensetzen. Lamellen sind
  dünn (etwa 40 mm), Äste meist auf beiden Breitseiten sichtbar, Schätzung des Inneren daher leichter als beim
  ganzen Träger. Nutzen: Lage jeder Fehlstelle im Träger bekannt, je Fehlstelle entscheiden (dulden, flicken,
  kappen) nach Beanspruchung an der Stelle, Lamellen gezielt anordnen, Festigkeit rechnen.
- Ausfräsen und Schiffchen statt Kappen: spart Länge und Keilzinkung. Fehlerfreie Festigkeit wird nicht
  erreicht (Kerbwirkung, Faserlage), BSH mit geflickten inneren Lamellen war in einer Studie aber tragfähig
  (siehe Recherche). Tragend nur mit Prüfungen und Zulassung. Offen: Normtext EN 14080, Frage an die zwei Werke.

## Stand (15.11.2026)
- Gerüst steht und ist committet: agent.py schließt jeden Auftrag mit dem Hinweis „noch nicht gebaut“ ab.
- datensatz.py gebaut und getestet (tests/test_datensatz.py), Aufteilung eingefroren in
  konfig/kodytek_aufteilung.json. Auf dem Server geprüft mit allen Box-Dateien und den 11 Probebildern
  (data/datensaetze/kodytek-probe/). Voller Lauf auf dem Mac 12.11.2026 fertig und geprüft (Befunde unten):
  Mac ~/fehlstellenscan/datensaetze/kodytek-1/ fertig; erstes Training kodytek1-n1280 fertig 15.11.2026 (offener Punkt 3). Ergebnisse in data/laeufe/
  (bericht.json, ueberlappung.txt, pruefung_ultralytics.txt, results.csv und args.yaml des Tests probe20).
- auswertung.py gebaut (23.11.2026, tests/test_auswertung.py), siehe Abschnitt Auswertung.
- Test tests/test_geruest.py: Name, Hinweis bei Aufträgen, kein Import von torch, torchvision oder ultralytics.
- .venv mit numpy 2.5.4 und Pillow 13.0.0 (Jan 11.11.2026) und agentkit per .pth; tests/test_umgebung.py
  prüft sie (auch BMP). Kein Dienst, kein Timer, keine Daten geladen.

## Gruppen-Bot Rüdiger (Jan 19.11.2026)
- Telegram-Bot @nichtsotiefruedigerbot („Rüdiger“, eigener Token, Privacy mode an) für die Gruppe des
  Forschungsprojekts. Jan, Henri und Felix fragen mit /frage <Text> oder per Antwort auf Rüdiger. Code: gruppe.py
  (Telegram per urllib, Long-Polling, kein neues Paket), gruppe_logik.py (rein, tests/test_gruppe_logik.py).
- Dienst fehlstellenscan-gruppe.service (Vorlage systemd/, dauerhaft, MemoryMax 1G, OnFailure=ausfall@).
- Zugang (.env): GRUPPE_BOT_TOKEN, GRUPPE_CHAT_ID (-1004382420400, „Forschungsprojekt: Lamellen-Scan“),
  GRUPPE_NUTZER_IDS (Jan 486792619). Henri und Felix: Spricht jemand Rüdiger in dieser Gruppe an, der nicht
  eingetragen ist, bekommt Jan eine Meldung mit „Freischalten“ / „Nicht freischalten“ (einmal je Person), die Gruppe
  „Jan schaltet dich frei“. Der Klick kommt als Auftrag (Feld meldung) zurück, gruppe.py trägt die Person in
  data/gruppe/stand.json (freigeschaltet) ein. Andere Chats: nur Log und data/gruppe/unbekannt.jsonl.
- Stil (Jan 19.11.2026): wie die Gruppe, Du, locker, kurz, ohne Floskeln, fachlich genau. Stilproben sind die
  letzten eigenen Nachrichten der Gruppe aus dem Verlauf (nicht Rüdigers Antworten).
- Fragen: claude_lauf mit lese_ordner, suchen=True, ohne_projekt=True (läuft in ~/.cache/agentkit/nur_lesen/,
  keine CLAUDE.md), Modell anspruchsvoll, Werkzeuge Read/Glob/Grep/WebSearch/WebFetch ([werkzeuge] fehlstellenscan,
  WebFetch ohne Domainliste, Jan „full power“). Lesen darf Rüdiger (gruppe_logik.lese_ordner_karte): Spiegel
  data/gruppe/spiegel/ (STATUS.md und Code, vor jedem Lauf frisch kopiert), unterlagen/ (Kodytek-Paper PDF und
  Text), docs/, konfig/, data/{laeufe,annotationen,rohbilder,pruefung,datensaetze,modelle,gruppe/dateien},
  holzbalkenscan/. Nie: andere Agenten, .env, data/gruppe/mails/ (Postfach-Kontext). Henri und Felix dürfen alles
  zum Projekt sehen, auch Wettbewerb und Markt (Jan 19.11.2026). Echter Lauf 19.11.: keine CLAUDE.md im Kontext,
  uni/STATUS.md abgelehnt, Paper richtig gelesen.
- Gespräch: Antwort auf eine Rüdiger-Nachricht setzt dessen Sitzung fort; sonst stehen die letzten 12 Wechsel
  (data/gruppe/verlauf.jsonl) im Prompt. Fotos und Dateien (auch zitierte) landen in data/gruppe/dateien/<id>/.
  Höchstens 40 Anfragen je Person und Tag. Antworten als Klartext, geteilt ab 4000 Zeichen.
- Geprüft 19.11.2026 (offline simuliert): Freischalt-Klick trägt die Person ein; Henris Klick auf Freigeben wird
  abgewiesen, seine Antwort auf den Entwurf ergibt einen neuen, Jans Klick gibt frei, Mail geht genau einmal raus,
  Ergebnis einmal in die Gruppe. Echt: Henri am 19.11. per Knopf freigeschaltet. Offen: Felix (ID 2036658844)
  hat Rüdiger noch nicht angesprochen (Rüdiger ist kein Admin, Datenschutzmodus an: Telegram
  stellt nur /frage und Antworten auf ihn zu, @-Erwähnungen nicht; Jan 19.11.). Echter Mail-Test mit dem neuen Ablauf steht aus; Jans Testmail an Henri (20261119-140812-...-d37e77)
  entstand noch mit der alten Fassung und liegt nur in der Zentrale.
- Mails: Claude antwortet {"mail_auftrag": ...}; dann agentkit.mailauftrag mit Jans HNEE-Postfach (Login aus
  uni/.env kopiert, Jan 19.11.2026), Läufe ohne Netz. Entwurf in die Freigabe (typ mail) und in die Gruppe,
  genau wie in der Zentrale (telegram.logik.entwurf_als_text, Jan 19.11.2026), mit Knöpfen Freigeben/Ablehnen.
  Die Knöpfe wirken nur für Jan (GRUPPE_JAN_ID in .env, Telegram-ID im Klick), Freigabe mit dem Fingerabdruck des
  in der Gruppe gezeigten Entwurfs. Entwürfe tragen anzeige=gruppe und erscheinen nicht in der Zentrale (Jan
  19.11.: „der entwurf soll in der gruppe landen“). Antwortet jemand aus der Gruppe auf den Entwurf, ist
  das ein Änderungswunsch: alter Entwurf wird „aendern“, neuer Entwurf (überarbeitet) kommt in Gruppe und Freigabe.
  Zuordnung Nachricht -> Entwurf in stand.json (entwuerfe).
  Nach Freigabe sendet gruppe.py genau einmal (SMTP HNEE, Kopie in
  „Gesendete Elemente“) und meldet der Gruppe das Ergebnis, ebenso Ablehnen, Ablauf, Ändern. „Ändern“ kommt als
  Auftrag quelle telegram-aendern; agent.py lässt diese liegen, gruppe.py überarbeitet sie.

## Mac (Training, von Hand)
- Ordner ~/fehlstellenscan mit .venv aus Python 3.14.5 von python.org
  (/Library/Frameworks/Python.framework/Versions/3.14/bin/python3), nicht aus Anaconda.
- Versionen (11.11.2026): torch 2.15.0, torchvision 0.29.2, ultralytics 8.4.210, numpy 2.5.4, Pillow 13.0.0,
  opencv-python 5.0.0.93, pip 26.3. macOS 26.6.2, M4 Pro, 14 Kerne, 24 GB RAM.
- ultralytics-Einstellungen in ~/Library/Application Support/Ultralytics/settings.json: sync=False (keine
  Statistik an ultralytics), datasets_dir ~/datasets (nur für Beispieldaten wie coco8), Läufe landen in
  ~/fehlstellenscan/runs/detect/<name>/ (results.csv, args.yaml, weights/best.pt).
- Probelauf 11.11.2026: coco8, yolo11n.pt, 1 Epoche, device=mps lief auf der GPU (GPU_mem 1,14 GB, mAP50 0,944).
  `yolo checks` zeigt „CPU“ und „GPU None“, das betrifft nur CUDA; mps nutzt das Training mit device=mps.
- Harmlose Meldungen: „fc-list: major issue … MiKTeX“ (Schriftsuche von MiKTeX), UserWarning „does not have a
  deterministic implementation“ (mps), „Cache entry deserialization failed“ (pip).
- Neues Terminal-Fenster, dann (Anaconda aus, Umgebung an):

      conda deactivate
      cd ~/fehlstellenscan && source .venv/bin/activate
      yolo detect train data=<data.yaml> model=yolo11n.pt epochs=<n> imgsz=640 device=mps

- Neu aufsetzen: .venv löschen, mit dem python.org-Python neu bauen, dann
  `python -m pip install --upgrade pip`, `python -m pip install torch torchvision ultralytics`,
  `yolo settings sync=False`.

## Datensatz bauen (datensatz.py)
- Befehle: `statistik`, `aufteilung`, `bauen`, `ueberlappung` (je `--help`). Nur Bordmittel und Pillow,
  numpy nur für `ueberlappung`, kein agentkit: läuft so auch in der Mac-.venv.
- Klassen fest 0-9 in der Reihenfolge der Specification: live_knot, dead_knot, knot_missing, knot_with_crack,
  crack, quartzity, resin, marrow, blue_stain, overgrown. Namen der Box-Dateien ohne Groß-/Kleinschreibung,
  unbekannter Name bricht ab.
- Boxen unter 2 px in einer Richtung (echte Bildbreite) werden aussortiert und in bericht.json einzeln gelistet.
  Bilder, die dadurch alle Boxen verlieren, fallen ganz weg (nicht „ohne Fehler“). Dezimalkomma wird zu Punkt.
  Bilder ohne Fehlstelle bleiben mit leerer .txt.
- Aufteilung 80/10/10 nach Gruppen (Bildnummer ohne die letzten 5 Ziffern, 407 Gruppen mit 1-74 Bildern,
  vermutlich je ein Brett), seltene Klassen zuerst verteilt, Seed 20261112. Eingefroren (Stand min_px 2):
  train 16.074 / val 2.026 / test 2.176 Bilder; blue_stain 75/12/9; overgrown 5/0/0. Ein Test prüft, dass die
  Datei zu den Box-Dateien passt. Test-Teil nicht mehr ändern, sonst sind Läufe nicht vergleichbar.
- Ausgabe <ziel>/: images/{train,val,test}/ (Hardlinks auf die BMPs, `--kopieren` für Kopien),
  labels/{train,val,test}/, data.yaml, bericht.json (Zählungen je Teil und Klasse, aussortierte Boxen),
  manifest.json (md5 je Bild, Git-Stand, Aufteilung), DATENKARTE.md. Ein vorhandenes Ziel wird nie überschrieben.
- `--probe N`: Überanpassungstest mit N Bildern mit Boxen, train = val.
- Befunde 12.11.2026:
  - Box-Größen (kürzere Seite, nach Aussortieren): Median live_knot 72 px, dead_knot 65, crack 66,
    resin 72, marrow 122, quartzity 145, blue_stain 181. Bei imgsz 640 (Faktor 0,23) liegen rund die Hälfte der
    Äste, Risse und Harzgallen unter 16 px, bei imgsz 1280 nur 2-6 %. Unter 8 px (kleinste YOLO-Stufe) bei 640:
    2-7 %, bei 1280: unter 2 % (außer quartzity und knot_with_crack 4-7 %, auch bei voller Auflösung).
    Vorschlag: imgsz=1280 statt 640; Kacheln bringen laut Statistik kaum mehr. Klären vor dem ersten Training.
  - overgrown: nach Aussortieren 5 Boxen, Median 5 px, alle in train. Praktisch nicht lernbar, in der Auswertung
    weglassen.
  - Überlappung: Nachbarbilder 100000005/06, 00/02, 61/62 nach Herausrechnen der Maserung ohne gemeinsame Zeilen
    (beste Korrelation 0,2-0,43, fremdes Paar 0,26-0,29, echte Überlappung wäre nahe 1). Das spricht gegen
    überlappende Aufnahmen; die Gruppen-Aufteilung bleibt trotzdem (gleiches Brett, gleiche Äste über die Naht).
- Befunde voller Lauf Mac 12.11.2026 (Dateien in data/laeufe/):
  - kodytek-1: train 16.073 / val 2.026 / test 2.176 Bilder (davon ohne Fehler 1.578 / 175 / 239). Boxen je Teil
    und Klasse stimmen genau mit konfig/kodytek_aufteilung.json überein. 434 Boxen aussortiert, 1 Bild weggelassen
    (150400014, train), fehlend 0, Dezimalkomma 132. Die früher genannten 524 Boxen unter 2 px waren ohne die
    Rundung in filtern() gezählt; 90 Boxen mit genau 2 px bleiben (gewollt). Kein Fehler in der Umwandlung.
  - ultralytics 8.4.210 liest alle drei Teile (check_det_dataset und YOLODataset je Teil): gleiche Bildzahlen,
    0 corrupt, keine Warnungen.
  - Überlappung (30 Gruppen): beste Korrelation Nachbarn im Mittel 0,40 (0,23-0,77), fremdes Bild 0,29
    (0,20-0,46), also deutlich unter 1: keine überlappenden Aufnahmen. In 6 Paaren passt das Bildende am besten
    auf Zeile 0 des nächsten Bilds (höchster Wert 0,77): Bilder schließen vermutlich lückenlos an. Gruppen-Aufteilung bleibt richtig.
  - Überanpassungstest probe20 (20 Bilder aus Gruppe 1000, 54 Boxen, 5 Klassen, yolo11n, imgsz 1280, 150 Epochen,
    6,5 min, GPU 5,3 GB): mAP50 0,971 (bester 0,972), P 0,94, R 0,93, mAP50-95 0,68-0,71. Bestanden; der Rest bis 1
    kommt von Augmentierung und kleinem Modell, falsche Boxen ergäben Werte nahe 0. Sichtprüfung
    train_batch0.jpg 12.11.2026: Jan hat Ausschnitte gezeigt (100000000, 03, 12, 19), Boxen sitzen auf den
    Fehlstellen (live_knot auf kleinen Ästen, dead_knot auf dunklem Ast, quartzity auf dunklen Streifen).
  - Literatur (Suche 12.11.2026): keine offizielle Aufteilung. CFIS-YOLO (arXiv 2504.11305) nutzt einen Teil
    (3.465 Bilder, 3 seltene Klassen weggelassen) mit eigener 8:1:1-Aufteilung, also nicht vergleichbar.

## Mac: Datensatz bauen und prüfen (von Hand)
Alles im Mac-Terminal (Anaconda aus, Umgebung an wie im Abschnitt Mac). Hardlinks gehen nur auf demselben
Laufwerk, ~/fehlstellenscan/daten und ~/fehlstellenscan/datensaetze liegen beide im Benutzerordner.

1. Skript und Aufteilung vom Server holen:

       mkdir -p ~/fehlstellenscan/konfig
       scp agents-user:agenten/fehlstellenscan/datensatz.py ~/fehlstellenscan/
       scp agents-user:agenten/fehlstellenscan/konfig/kodytek_aufteilung.json ~/fehlstellenscan/konfig/

2. Überlappungs-Stichprobe (30 Gruppen, je ein Nachbarpaar und ein fremdes Bild, einige Minuten):

       python datensatz.py ueberlappung --bilder daten/kodytek/bilder --anzahl 30 | tee ueberlappung.txt

   Werte „Nachbarn“ nahe 1 hießen echte Überlappung; erwartet sind ähnliche Werte wie beim fremden Bild.
3. Überanpassungstest (20 Bilder, train = val; mAP50 muss gegen 1 gehen, sonst stimmt die Umwandlung nicht):

       python datensatz.py bauen --boxen daten/kodytek/boxen --bilder daten/kodytek/bilder --ziel datensaetze/kodytek-probe20 --aufteilung konfig/kodytek_aufteilung.json --probe 20 --ohne-md5
       yolo detect train data=datensaetze/kodytek-probe20/data.yaml model=yolo11n.pt epochs=150 imgsz=1280 batch=4 mosaic=0 device=mps name=probe20

   Danach ansehen: runs/detect/probe20/labels.jpg (Boxen an plausibler Stelle und Größe) und train_batch0.jpg
   (Boxen auf den Fehlstellen), mAP50 in der letzten Zeile von results.csv.
4. Vollen Datensatz bauen (md5 über rund 174 GB dauert eine Weile, braucht keinen zusätzlichen Platz):

       python datensatz.py bauen --boxen daten/kodytek/boxen --bilder daten/kodytek/bilder --ziel datensaetze/kodytek-1 --aufteilung konfig/kodytek_aufteilung.json

   Erwartet (Lauf 12.11.2026): train 16.073 / val 2.026 / test 2.176 Bilder, 434 aussortierte Boxen,
   1 weggelassenes Bild, Dezimalkomma 132 Dateien, fehlend 0.
5. ultralytics liest den Datensatz (fremde Gegenprobe, Warnungen zu Labels notieren):

       python -c "from ultralytics.data.utils import check_det_dataset; print(check_det_dataset('datensaetze/kodytek-1/data.yaml'))"

6. Ergebnisse zum Server (Ordner data/laeufe/ gibt es dort):

       scp ueberlappung.txt datensaetze/kodytek-1/bericht.json runs/detect/probe20/results.csv agents-user:agenten/fehlstellenscan/data/laeufe/

- Hinweis Hardlinks: Die Bilder belegen den Platz nur einmal. Platz wird erst frei, wenn Original und
  datensaetze/ gelöscht sind. Die ZIPs sind davon unabhängig.

## Segmentierung: Masken zu Polygonen (masken.py)
Ziel (Jan 19.11.2026): yolo11n-seg auf Kodytek, Fehlstellen als Umriss statt Box. Grund: Die Norm misst Äste
am kleinsten Durchmesser (Henri), dafür braucht es den Umriss (daraus später gekippte Box, Ellipse, kleinster
Durchmesser in Python).
- Befehle `ansehen`, `bauen`, `gegenprobe`, `zeichnen`, `gruppenbilder` (je `--help`). numpy, Pillow, opencv, importiert
  datensatz.py aus demselben Ordner. Masken aus `Semantic Maps.zip` (jede einzeln im Speicher) oder einem Ordner.
- Bilder für Menschen (Gruppe, Folien): `gruppenbilder` macht je Bild drei JPGs, nur Masken, keine Boxen (Jan
  21.11.2026), deutsche Klassennamen, 1600 px breit: `_vergleich` (Markierung über Modell, Flächen), `_umriss`
  (Modell, nur Umriss), `_masse` (Modell, bei Ästen angepasste Ellipse mit Achsen und Länge × Breite in mm).
  mm aus dem Kodytek-Paper: quer 16,66 px/mm, längs 6,67 px/mm (Pixel nicht quadratisch, erst in mm umrechnen).
  Neonfarben je Klasse (Äste türkis/pink), Namensfelder weichen einander aus. Maße beruhen auf den großzügigen
  Pinsel-Masken, also eher zu groß. Kein ultralytics im Code: das Modell läuft
  auf dem Mac per `yolo segment predict`, gezeichnet wird auf dem Server. Mac (Umgebung an, ~/fehlstellenscan):

      mkdir -p gruppe/bilder gruppe/markierung
      for n in 153200022 153200004 153200015; do cp datensaetze/kodytek-seg-1/images/val/$n.bmp gruppe/bilder/; cp datensaetze/kodytek-seg-1/labels/val/$n.txt gruppe/markierung/; done
      yolo segment predict model=runs/segment/kodytek-seg1-n1280/weights/best.pt source=gruppe/bilder imgsz=1280 retina_masks=True save_txt=True save_conf=True save=False project=gruppe name=vorhersage exist_ok=True
      scp -r gruppe agents-user:agenten/fehlstellenscan/data/laeufe/kodytek-seg-1/
      scp -r runs/segment/gruppe/vorhersage agents-user:agenten/fehlstellenscan/data/laeufe/kodytek-seg-1/gruppe/

  (ultralytics legt `project=gruppe` unter runs/segment/ ab, Ausgabe „Results saved to“ zeigt den Pfad.)

  Server: `.venv/bin/python masken.py gruppenbilder --bilder data/laeufe/kodytek-seg-1/gruppe/bilder
  --markierung data/laeufe/kodytek-seg-1/gruppe/markierung --vorhersage data/laeufe/kodytek-seg-1/gruppe/vorhersage/labels
  --ausgabe data/laeufe/kodytek-seg-1/gruppe/fertig 153200022 153200004 153200015`.
- Umwandlung: je Klassenfarbe eine Binärmaske, `cv2.findContours`, jeder Fleck ein Objekt, Polygon durch die
  Mitten der Randpixel, normiert auf die echte Bildgröße. Weggelassen und in bericht.json einzeln gelistet:
  Flecken unter 2 px Breite oder Höhe (`klein`), Flecken ohne Fläche wie 1 px breite schräge Linien (`linie`).
  Unbekannte Farben werden gezählt, nicht umgewandelt. Löcher werden ausgemalt und gezählt. Maske mit anderer
  Größe als das Bild: Bild fällt weg, steht in `groesse_abweichend`.
- `bauen` übernimmt Bilder (Hardlinks) und Aufteilung aus einem Box-Datensatz (kodytek-1), also genau die
  eingefrorene Aufteilung. `--probe N`: die ersten N train-Bilder mit Objekten, train = val.
- Befunde an den 3 Masken auf dem Server (19.11.2026): Hintergrund 000000, nur Farben der Spezifikation, keine
  Mischfarben an den Rändern. Flecken gleich Boxen (8 von 8, dazu ein 1-px-Klickfehler aussortiert), jedes
  Polygon füllt seine Box. Die Masken sind mit dem Pinsel gemalt: Umrisse großzügig, deutlich größer als der
  dunkle Ast oder Streifen (quartzity mit Wellenrand). Für Maße wie den kleinsten Astdurchmesser heißt das:
  Kodytek-Masken messen eher zu groß. Vor Aussagen in mm an eigenen, enger gezeichneten Masken prüfen.

### Mac: Seg-Datensatz bauen und trainieren (von Hand)
Mac-Terminal, Umgebung an wie im Abschnitt Mac. Erwartet wird kodytek-1 aus dem Abschnitt davor.
Alles am Stück: seg_nacht.sh (Schritte 2-6, volles Training nur bei Probe-Mask-mAP50 ab 0,9, sonst Abbruch;
batch=4 als Ersatz, wenn batch=8 abbricht). Start: `caffeinate -i bash seg_nacht.sh 2>&1 | tee seg_nacht.log`.
Gestartet von Jan am 19.11.2026 abends. Probe bestanden (20 Bilder, 54 Objekte wie die Box-Probe, 9 min,
GPU 6,3 GB): Mask-mAP50 0,970, Mask-mAP50-95 0,675 (Box 0,970 / 0,718). Voller Lauf fertig 21.11.2026 09:42.

1. Skripte holen (datensatz.py wird von masken.py gebraucht):

       scp agents-user:agenten/fehlstellenscan/masken.py ~/fehlstellenscan/
       scp agents-user:agenten/fehlstellenscan/datensatz.py ~/fehlstellenscan/

2. Fünf Masken ansehen (Hintergrund, Farben, UNBEKANNT bei fremden Farben):

       python masken.py ansehen --masken "daten/kodytek/zip/Semantic Maps.zip" --anzahl 5

3. Vollen Seg-Datensatz bauen (liest alle 20.276 Masken einzeln, Dauer noch nicht gemessen):

       python masken.py bauen --vorlage datensaetze/kodytek-1 --masken "daten/kodytek/zip/Semantic Maps.zip" --ziel datensaetze/kodytek-seg-1

   Erwartet: dieselben Bildzahlen wie kodytek-1 (16.073 / 2.026 / 2.176), keine unbekannten Farben, Größe
   abweichend 0, fehlende Masken 0.
4. Gegenprobe, Bilder zum Draufschauen, ultralytics liest den Datensatz:

       python masken.py gegenprobe --seg datensaetze/kodytek-seg-1 --boxen datensaetze/kodytek-1 --ausgabe gegenprobe-seg.json
       python masken.py zeichnen --seg datensaetze/kodytek-seg-1 --ausgabe seg-bilder 100000000 100000061 100000062
       python -c "from ultralytics.data.utils import check_det_dataset; print(check_det_dataset('datensaetze/kodytek-seg-1/data.yaml'))"

   Abweichungen Flecken gegen Boxen sind zu erwarten (ein Riss in mehreren Stücken, zwei berührende Äste
   derselben Klasse als ein Fleck). Fehler wären große Abweichungen in einer ganzen Klasse.
5. Überanpassungstest (Mask-mAP50 muss gegen 1 gehen, sonst stimmt die Umwandlung nicht):

       python masken.py bauen --vorlage datensaetze/kodytek-1 --masken "daten/kodytek/zip/Semantic Maps.zip" --ziel datensaetze/kodytek-seg-probe20 --probe 20
       yolo segment train data=datensaetze/kodytek-seg-probe20/data.yaml model=yolo11n-seg.pt epochs=150 imgsz=1280 batch=4 mosaic=0 device=mps name=seg-probe20

6. Erst wenn 5 passt, volles Training (Speicher reicht nicht: batch=4). Nur val auswerten, test nicht anfassen:

       yolo segment train data=datensaetze/kodytek-seg-1/data.yaml model=yolo11n-seg.pt epochs=60 imgsz=1280 batch=8 device=mps name=kodytek-seg1-n1280

   Läufe landen in runs/segment/<name>/. Rechnung: Box-Modell 21 min je Epoche, Seg langsamer, also über 21 h.
7. Ergebnisse zum Server (Ordner gibt es dort):

       scp datensaetze/kodytek-seg-1/bericht.json gegenprobe-seg.json seg-bilder/*.png agents-user:agenten/fehlstellenscan/data/laeufe/kodytek-seg-1/
       scp runs/segment/seg-probe20/results.csv agents-user:agenten/fehlstellenscan/data/laeufe/seg-probe20/
       scp -r runs/segment/kodytek-seg1-n1280 agents-user:agenten/fehlstellenscan/data/laeufe/

- Hinweis Maskenauflösung: YOLO-seg lernt Masken in einem Viertel der Eingabegröße. Bei imgsz 1280 ist ein
  Maskenpunkt rund 9 Originalpixel; dünne Risse leiden zuerst (crack je Klasse ansehen). Abhilfe wäre
  `mask_ratio=2` (mehr Speicher), erst nach dem ersten Lauf entscheiden.

### Erstes Seg-Modell kodytek-seg1-n1280 (fertig 21.11.2026)
Dateien auf dem Server: data/laeufe/kodytek-seg1-n1280/ (results.csv, args.yaml, Kurven, Matrizen, val_batch0-2,
best.pt, last.pt), data/laeufe/kodytek-seg-1/ (bericht.json, gegenprobe-seg.json, 3 Kontrollbilder,
seg_nacht.log), data/laeufe/seg-probe20/results.csv.
- Datensatz kodytek-seg-1: train 16.068 / val 2.026 / test 2.176 Bilder. Keine unbekannten Farben, keine fehlende
  Maske. 5 Masken breiter als ihr Bild (z. B. 100000023: Bild 2777, Maske 2800; dazu 100000024, 104700046,
  104700048, 115100056, alle train): Bilder weggelassen, daher train 5 weniger als kodytek-1. Weggelassen 372
  kleine Flecken (Boxen: 434) und 58 Linien ohne Fläche. 1.307 Löcher ausgemalt (live_knot 459, knot_with_crack
  307, dead_knot 263), Art der Löcher nicht angesehen (Masken liegen nur auf dem Mac).
- Gegenprobe: Flecken je Teil und Klasse weichen höchstens um 4 von den Boxen ab, nur 67 von 20.270 Bildern
  haben eine Abweichung (meist ein Fleck mehr oder weniger). Masken und Boxen beschreiben dieselben Objekte.
  Kontrollbilder vom Mac 100000000/61/62 gleich wie die Server-Probe.
- Lauf: yolo11n-seg, imgsz 1280, batch 8, MuSGD (optimizer auto), mask_ratio 4, 60 Epochen. Rund 28 min je
  Epoche mit Prüfung (Epoche 1: 1.721 s); die 33,5 h enthalten eine Pause von rund 5,7 h zwischen Epoche 20 und
  25. GPU-Speicher laut Log bis 16,4 GB (meist 13-15 GB) von 24 GB.
- Verlauf: bester Stand Epoche 37 (best.pt). Danach sinkt der train-seg-Verlust weiter, val-seg-Verlust steigt
  (1,733 bei Epoche 35 auf 1,769 bei 60), Mask-mAP50-95 fällt von 0,413 auf 0,396. Leichte Überanpassung wie
  beim Box-Modell; 35-40 Epochen reichen.
- best.pt auf val (2.026 Bilder, 4.465 Objekte): Box P 0,753, R 0,672, mAP50 0,748, mAP50-95 0,457; Mask P
  0,753, R 0,669, mAP50 0,746, mAP50-95 0,413. Box-Modell kodytek1-n1280 zum Vergleich: mAP50 0,751, mAP50-95 0,460.
- Je Klasse Mask mAP50 / mAP50-95 (Box in Klammern): live_knot 0,868 / 0,420 (0,867 / 0,442); dead_knot
  0,851 / 0,449 (0,860 / 0,487); knot_missing 0,829 / 0,420 (0,829 / 0,470); knot_with_crack 0,845 / 0,580
  (0,845 / 0,591); crack 0,739 / 0,377 (0,749 / 0,462); quartzity 0,643 / 0,363 (0,634 / 0,421); resin
  0,768 / 0,348 (0,783 / 0,402); marrow 0,880 / 0,605 (0,869 / 0,637); blue_stain 0,293 / 0,151 (12 Objekte).
- Sichtprüfung val_batch0: Masken sitzen auf den Fehlstellen wie die Labels. Fehler wie beim Box-Modell: kleine
  Äste live/dead vertauscht (4 von 16 Bildern), Harz am rechten Brettrand (153200015) fehlt.
- Schluss: Erkennen gleich gut wie das Box-Modell, Masken kosten nichts. Die genaue Form (Mask-mAP50-95) liegt
  unter der Box, am deutlichsten bei crack, resin, quartzity: dünne oder unscharf gemalte Formen, passt zur
  Maskenauflösung (1/4) und zu den Pinsel-Masken. Inferenz 0,5 ms, Nachbearbeitung der Masken 6,5 ms je Bild.

## Auswertung (auswertung.py, ab 23.11.2026)
Gegenprobe ohne ultralytics: was das Modell je Objekt richtig und falsch macht, und wie genau es in mm misst.
- `fehler`: Markierung (YOLO-seg) gegen Vorhersage (`yolo segment predict save_txt save_conf`) je Bild. Zuordnung
  nach Konfidenz absteigend, IoU der Masken ab 0,5, erst gleiche Klasse (Treffer), dann über Klassen (vertauscht),
  Rest übersehen bzw. Fehlalarm. Konfidenzschwelle `--konf` (Vorgabe 0,25). Ausgabe bericht.json (je Klasse R, P,
  95-%-Intervall per Bootstrap über Bilder, R je Größenklasse <5/5-10/10-20/20-40/>=40 mm kurze Achse,
  Verwechslungen, bei Ast-Treffern Vorhersage minus Markierung in mm) und fehler.csv (eine Zeile je Objekt).
  Auch Person gegen Person (zweite Markierung als --vorhersage). Ohne `--bilder` gilt 2800 x 1024; schmalere
  Kodytek-Bilder (z. B. 2777) verschieben die mm dann um rund 1 %, die IoU kaum.
- `messung`: messung.csv aus dem Messprotokoll gegen funde.json von `balken.py karte`. Zuordnung nach Lage
  (Mitte, höchstens 20 mm), nur Ast-Klassen; `--laenge-spiegeln` / `--hoehe-spiegeln`, wenn Ende A oder Kante K
  im Streifenbild auf der anderen Seite liegt. Ergebnis: Modell minus Messschieber (Ellipse kurz gegen d_min, lang
  gegen d_max, Bland-Altman), Äste ohne Fund, Abweichung zwischen zwei Messenden.
- Geprüft 23.11.2026 an den 3 Gruppenbildern (data/laeufe/kodytek-seg-1/auswertung-gruppe/): 8 markiert, 7
  Treffer, Harz in 153200015 übersehen (wie in der Sichtprüfung), in 153200004 ein Ast doppelt vorhergesagt (tot
  0,56 Treffer, lebend 0,66 Fehlalarm, im Vergleichsbild nachgesehen). Äste: Vorhersage im Mittel 0,8 mm breiter
  als die Markierung (n=6).
- val komplett (23.11.2026, Vorhersage conf 0.05 auf dem Mac, Auswertung ab 0,25): data/laeufe/kodytek-seg1-n1280/
  val-auswertung/ (markierung, vorhersage, ergebnis/bericht.json, fehler.csv). 4.465 markiert: 3.628 Treffer,
  316 Klasse vertauscht, 521 übersehen, 693 Fehlalarme. R / P je Klasse: live_knot 0,846 / 0,812, dead_knot
  0,799 / 0,814, knot_missing 0,812 / 0,812, knot_with_crack 0,851 / 0,708, crack 0,753 / 0,658, quartzity
  0,591 / 0,573, resin 0,730 / 0,756, marrow 0,889 / 0,712, blue_stain 0,250 / 0,231 (12 Objekte).
- Kleine Äste fallen ab: R unter 5 mm kurze Achse live 0,72, dead 0,65, knot_missing 0,68, knot_with_crack 0/20;
  ab 5 mm 0,85-0,91. Verwechslungen vor allem dead -> live (136) und live -> dead (89), quartzity -> marrow (22).
  Äste: Vorhersage im Mittel 0,87 mm breiter als die Markierung (sd 2,2 mm, n=3.027).
- Gegenprobe mit der Werkbank (FiftyOne evaluate_detections, Masken-IoU 0,5, gleiche Vorhersagen, ab 0,25): R und
  P je Klasse auf zwei Stellen gleich wie auswertung.py. Die Zuordnung in auswertung.py ist damit bestätigt.
- Mit ultralytics (Mask P 0,753 R 0,669, mAP50-95 0,413) nicht direkt vergleichbar: ultralytics wählt die Schwelle
  nach bestem F1 und mittelt je Klasse (Mittel der Klassen hier: P 0,68 R 0,72). FiftyOne-mAP (COCO, Masken)
  0,374, niedriger, weil nur Vorhersagen ab 0,25 eingehen. Für Vergleiche zwischen Modellen: auswertung.py oder
  ultralytics, aber immer dasselbe.
- Neu rechnen (Server): `systemd-run --user --scope -q -p MemoryMax=1500M .venv/bin/python auswertung.py fehler
  --markierung data/laeufe/kodytek-seg1-n1280/val-auswertung/markierung --vorhersage
  data/laeufe/kodytek-seg1-n1280/val-auswertung/vorhersage --ausgabe data/laeufe/kodytek-seg1-n1280/val-auswertung/ergebnis`
  (16 s). Markierung und Vorhersage lädt mac/werkbank_val.sh hoch.

## Fotobox-Aufnahme (Mac, ab 25.11.2026)
- Box 60 x 60 x 60 cm, Handy mittig an der Klappe oben, schwarz, zwei Wände offen, vier Rollenböcke (Jan). Ersetzt den
  Reiter-Entwurf der 40er Box.
- aufnahme/logik.py (Rechnung), server.py (nur Bordmittel), seite/ (Oberfläche, Optik „Jans Wahl 25.11.“),
  tests/test_aufnahme.py. Läuft von Hand auf dem Mac, Fotos in ~/fehlstellenscan/aufnahmen/<Balken-ID>/ (balken.json).
- Start (Mac-Terminal): `scp -r agents-user:agenten/fehlstellenscan/aufnahme ~/fehlstellenscan/`, dann
  `python3 ~/fehlstellenscan/aufnahme/server.py`, Seite http://localhost:8765. Die Oberfläche antwortet nur dem Mac
  selbst, das iPhone nur unter /h/<code>/ (Code in einstellungen.json). Port 8765 ist im WLAN unverschlüsselt offen.
- Kurzbefehl: Wiederholen { GET warten; Foto aufnehmen; POST foto }, Schritte und Adressen unter ···. „warten“ endet
  erst beim Auslösen.
- Abstand = Linse bis Rolle (Start 60 cm, ungemessen) minus Balkenhöhe in dieser Lage. Seiten 1/3 breit, 2/4 schmal.
  Bildwinkel Start 24 mm, „Messen“ (Als Maßstab) setzt ihn neu und rechnet die schon gemachten Fotos dieses
  Balkens mit um (Lage der Abschnitte bleibt, nur mm ändern sich; andere Balken nicht). Vorschub automatisch (25 % Überlappung, höchstens 50 cm).
  Mit dem ersten Foto einer Seite ist deren Plan eingefroren, neue Messwerte gelten nur für Seiten ohne Fotos.
- Richtung (Jan 27.11.2026 „selber einstellen“): Einrichtung (···) Balken waagerecht (Vorgabe) oder senkrecht im Bild,
  gilt für Seiten ohne Fotos. Plan: laengs_mm/quer_mm bleiben lange/kurze Bildseite, feld_mm ist das Bildfeld in
  Schieberichtung (Vorschub, Abschnitte, Lücke). Offen: Körper und Streifenbild nehmen weiter die lange Seite als
  Längsrichtung an, für senkrecht noch nicht angepasst. px/mm stehen je Foto nur auf dem Mac (sips).
- In der Halle 27.11.2026 (Jan, nur auf dem Server im Browser geprüft, am Mac nicht): Zuschnitt von Hand (Rahmen bleibt
  beim Öffnen, Kanten/Ecken ziehen, innen verschieben, Maß in cm), Bildfeld anklickbar wie L × B × H (Seiten ohne
  Fotos, Mitte bleibt). Zollstock rastet bis 6 Grad ein (Alt frei), feiner, neu setzbar, echtes Maß auch im Livebild
  (Server nimmt den Maßstab jetzt auch ohne Foto; Annahme: Livebild zeigt denselben Ausschnitt wie das Foto).
  Vorschub (V): zwei Linien quer zur Schieberichtung im Abstand des Vorschubs zum gemeinten Abschnitt.
  Offen: Maßstab rückgängig gibt es nicht (Jan fragte nach „zurücksetzbar“, gebaut ist Zollstock neu setzen).
- Geprüft auf dem Server mit simuliertem iPhone im Browser. Offen, nur am Gerät klärbar: Kurzbefehl, Auflösung und
  Linse von „Foto aufnehmen“ (Makro?), Schärfe, sips mit HEIC, Dauer bis zum Bild. Keine feste Belichtung, kein
  Live-Bild. Rückfall: Foto per AirDrop, dann ··· „Foto vom Mac“.
- Erster Test am iPhone (Jan 25.11.2026): Auslösen und Übertragen per Kurzbefehl klappt, Foto stark überbelichtet
  (Automatik, schwarzer Grund). Darum iPhone-App (Jan 25.11. „Ja, App bauen“): aufnahme/app/ (Swift, Xcode-Projekt,
  iOS 17+), auf dem Server nicht übersetzbar, 25.11. auf Jans Mac in Xcode fehlerfrei gebaut (Simulator), am iPhone noch nie, noch nicht im Repo (Muster für *.swift, *.plist, *.pbxproj, Assets.xcassets fehlt in claude_lauf.GESCHUETZT,
  Bedarf steht in der STATUS.md des Hauptordners). Belichtung und Weißabgleich gesperrt, Fokus je Seite,
  Live-Bild, Bedienung am Mac (dunkler, heller, einmessen, 12/48). Laut Apple-Forum hält iOS feste Werte nur bei
  12 MP ein, bei 48 MP weichen sie ab: je Foto stehen ISO und Zeit in balken.json (kamera), Wahl nach Jans Test.
- Test am iPhone 16 (25.11.2026, je zwei Fotos, gleiche Stelle, eingestellt 1/41 s ISO 33): 12 MP zweimal 1/41 s ISO 32;
  48 MP (8064 x 6048, um 8,5 MB) 1/73 und 1/65 s bei ISO 50, schwankt also um etwa 12 %. Belichtung nach dem Einmessen
  gut. Die Fassung mit selbst nachregelndem Einmessen ist noch nicht auf dem iPhone. px_je_mm noch falsch: Bildwinkel
  ungemessen, Balkenlage im Test vermutlich nicht die gewählte Seite, Balken lag quer zur langen Bildseite.
- Zuschnitt: Rahmen am Bild, Anteile in den Einstellungen, eingefroren im Plan der Seite (zuschnitt). Originale
  bleiben ganz, bilder.py wendet plan.zuschnitt an. mitte_mm ist
  die Mitte des Zuschnitts, px_je_mm gilt fürs ganze Bild. Neben jedem Zuschnitt-JPG liegt <Foto>.zuschnitt (mit
  welchem Zuschnitt es entstand); weicht der Plan ab, entsteht es neu (nur wenn das Original da ist).
- Rand gegen die Alustangen der Fotobox (Jan 27.11.2026, Fotos von B004-B007 oben und unten zu wenig beschnitten):
  POST /api/rand {"oben": 0.03, "unten": 0.07} (Anteile des ganzen Bildes, gemessen: Stange oben bis 1 %, unten bis
  5,5 %) klemmt die Zuschnitte aller Seiten, Einzelfotos und der Einstellungen (logik.rand_klemmen/plan_rand,
  zweimal = einmal), rechnet Labels um (kette.label_umrechnen, Objekte am Rand abgeschnitten, ganz draußen weg).
  kette.label rechnet jedes Label mit anderem Zuschnitt beim Lesen um (auch vom Server geholte). quer_mm und
  feld_mm werden 10 % kleiner: B004 S1 hat jetzt eine Lücke zwischen den Fotos (Vorschub 300 mm, Feld 283 mm).
  Geprüft: Tests, Kopie der echten Balken (16 Seiten, 282 Fotos, ohne Originale). Offen bei Jan (Mac, lokal):
  neurolign_einrichten.sh, dann /api/rand per curl, dann neurolign_abgleich.sh hoch.
- Kette Aufnahme > Labeln > Training in einer Anwendung (Jan 25.11.2026 „alles nur in eine anwdnung“), Navigation oben:
  aufnahme/kette.py (Ablage, Aufteilung, Lauf; Bordmittel), bilder.py (Zuschnitt, Kacheln 1280 px; läuft in der
  Trainings-.venv), seite/labeln.* (Werkbank nach unterlagen/werkbank-regler, Jans Wahl, 18 Klassen der
  Labelrichtlinie), seite/training.*, tests/test_kette.py. Keine neuen Pakete.
  Zuschnitt: aufnahmen/<ID>/zuschnitt/, Original bleibt ganz. Labels: aufnahmen/<ID>/labels/<Foto>.json in Anteilen des
  Zuschnitts; ein gespeichertes Foto ohne Objekte zählt als fehlerfrei. Gekachelt wird erst beim Bau nach
  datensaetze/altholz-N; Lauf in runs/segment/altholz-N, Log aufnahmen/altholz-N.log, 60 Epochen, imgsz 1280, batch 2,
  Start vom Kodytek-Modell, wenn vorhanden. mm im Labeln nur bei gemessenem Bildwinkel, sonst Pixel.
  Aufteilung nach Balken (aufnahmen/teile.json), Vorschlag jeder fünfte Prüfung, änderbar bis zum ersten echten Training;
  Messbalken vom 27.11. vorher auf „Nur Test“ stellen. Geprüft wird nie auf Trainingsbildern (Jan 26.11.2026,
  kette.pruefung): mit Trainings- und Prüfbalken nach Balken (nur dann wird die Aufteilung fest); sonst wird eine
  ganze Seite zurückgehalten (mit Objekten, Training behält Objekte, Fotozahl nahe einem Fünftel); bei nur einer
  Seite die letzten Fotos (ein Fünftel, Nachbarn überlappen um 25 %, also geschönt). Ein einziges Foto: kein Start.
  Altholz wird so auch zusammen mit Kodytek immer mitgeprüft. Die Seite nennt die Art der Prüfung.
  Geprüft auf dem Server im Browser mit yolo-Attrappe. Nicht geprüft: echtes yolo auf dem Mac, HEIC, Durchlauf eines
  ganzen Balkens, Prüfer in frischem Kontext. Nach Neustart des Programms ist die Anzeige
  des Laufs weg, der Lauf selbst geht weiter.
- Ergebnis nach dem Training (Jan 25.11.2026): Seite Training zeigt unter dem Start „Ergebnis altholz-N“, auch nach
  Neustart (letzter altholz-Lauf mit Abschlusstabelle). Quelle nur, was ultralytics und bilder.py schreiben
  (kette.ergebnis_gelesen): Abschlusstabelle im Log (best.pt, je Klasse Box und Maske P, R, mAP50, mAP50-95),
  results.csv (beste Epoche nach Fitness 0,1 mAP50 + 0,9 mAP50-95 für Box und Maske, an kodytek-seg1-n1280 geprüft;
  Dauer = Spalte time), args.yaml (Startmodell, imgsz, batch, Epochen), datensaetze/altholz-N/bericht.json (Kacheln
  train/val, Art der Prüfung; alte Läufe mit probe = train als Prüfung bekommen einen Warnhinweis), aufnahmen/altholz-N.json (Datensätze). Groß die
  Masken-Werte, Boxen in einer Zeile, Klassen mit deutschen Namen. Geprüft mit yolo-Attrappe und gerendert mit den
  echten Dateien von kodytek-seg1-n1280; nicht geprüft mit einem echten altholz-Lauf auf dem Mac.
- Datensätze im Training (Jan 25.11.2026): Häkchen Altholz, Kodytek-Auswahl und jeder Satz in datensaetze/, der Umrisse und
  dieselbe Klassenzählung hat (Box-Sätze wie kodytek-1 und altholz-N fehlen absichtlich). aufnahme/saetze.py (Bordmittel).
  Kodytek-Auswahl: 400 Trainings- und 100 Prüfbilder aus kodytek-seg-1, seltene Klassen zuerst, einmal gezogen und fest
  (aufnahmen/kodytek/auswahl.json), Test nie. Im Labeln über die Auswahl im Kopf („Kodytek-Auswahl“) mit Originalumrissen
  als Vorlage; erst wenn alle Objekte geprüft und gespeichert sind, gilt die Korrektur, sonst das Original. Originale
  bleiben unverändert (Hardlinks, Korrekturen in aufnahmen/kodytek/labels/). Maße dort in Pixeln, weil längs und quer
  verschieden aufgelöst. Ganze Sätze gehen per train.txt ein, Auswahlbilder nicht doppelt. Ganzer Kodytek-Satz: um
  21 min je Epoche auf dem Mac (gemessen am Box-Modell). Mit Kodytek oder anderen Sätzen dabei mischt die Prüfzahl von ultralytics Altholz und Kodytek. Darum (Jan 26.11.2026)
  schreibt bilder.py dann val_altholz.txt und altholz.yaml (nur Altholz-Prüfkacheln), kette.py prüft nach dem Training
  best.pt damit (`yolo segment val`, Zustand „pruefen“, Log aufnahmen/altholz-N-altholz.log, Ausgabe
  runs/segment/altholz-N/pruefung-altholz). Die Seite zeigt groß die Altholz-Zahlen, darunter klein alle Sätze zusammen.
  Scheitert diese Prüfung, bleibt das Training gültig, die Seite meldet den Fehler. Nur mit yolo-Attrappe geprüft.
  Geprüft auf dem Server mit drei echten Kodytek-Bildern und yolo-Attrappe, nicht auf dem Mac.
- Klassen im Labeln (Jan 25.11.2026 „vereinfachen, für die Übersichtlichkeit der Farben“): sechs Farbgruppen (Ast, Riss, Loch,
  Fuge, Metall, Weitere eingeklappt), innerhalb der Gruppe Strichmuster. Nur Anzeige, Zifferntasten 1-9 folgen der
  neuen Reihenfolge. Klassennummern und Training unverändert 18 Klassen; ob fürs Training zusammengelegt wird, ist offen.
- Klassen als Datei (Jan 26.11.2026 „flexibel: umbenennen, löschen, neu, Farbe“): aufnahme/klassen.py (rein,
  tests/test_klassen.py), Ablage aufnahmen/klassen.json (fehlt sie, gilt die Startfassung = die 18 von oben). Jede
  Klasse: feste ID (nie neu vergeben, Labels tragen sie), fester Schlüssel fürs Training (0-9 Kodytek), Name, Gruppe,
  Muster, Farbe (leer = Farbe der Gruppe). Labeln > Bearbeiten > Stift neben „Klasse“ öffnet das Fenster Klassen:
  Name, Farbe, Gruppe je Zeile, Gruppenname änderbar, + je Gruppe und + für eine neue Gruppe, Mülleimer. Löschen mit
  Objekten = zusammenlegen in eine gewählte Klasse (Objekte merken die alte in kv), Rückgängig unten im Fenster.
  Gilt sofort für alle (/api/klassen, Recht labeln). Training: YOLO-Nummer = ID, gelöschte IDs bleiben leer in
  data.yaml. neurolign_abgleich.sh runter holt klassen.json mit. Offene Browser anderer merken eine Änderung erst nach
  Neuladen (Speichern mit gelöschter Klasse wird mit Hinweis abgelehnt).
- Gespeichert werden jetzt je Objekt auch Konfidenz c und Quelle q (Vorlabel, vorher beim Speichern verloren), kv und m.
- Am Holz gemessen (Jan 26.11.2026, für Prüfbalken): Bearbeiten > „Am Holz gemessen“, kleinster und größter
  Durchmesser in mm je Person (m: von, min, max; auf dem Mac „mac“), daneben Bild minus Holz (hervorgehoben ab 1 mm
  und 10 %). Ersetzt die Zuordnung per Lage aus docs/messprotokoll-27-11.md, wenn die Äste im Foto gelabelt sind;
  Astnummern auf dem Holz helfen beim Finden. Auswertung über alle Messungen fehlt noch (auswertung.py liest nur CSV).
- Streifenbild als Balken (aufnahme/streifen.py, tests/test_streifen.py): schneidet ein holzbalkenscan-Streifenbild
  in gleiche Stücke um 1 m (Seite 1, hochgeladen, px/mm aus kacheln.json, Maße in mm) und speichert die Funde aus
  balken.py karte als offene Vorlabel mit Konfidenz und Modellname. Felix' Testbalken 261019 A (ISO 800,
  kodytek-seg1-n1280, 7 Stücke, 287 Vorlabel) liegt seit 26.11.2026 auf dem Server als B501 „Felix 261019 A“. Zweites
  Querschnittsmaß unbekannt, eingetragen 230 mm als Platzhalter. Training nimmt nur fertig geprüfte Fotos; welcher
  Teil (Training/Prüfung/Nur Test) B501 bekommt, legt Jan in der Galerie auf dem Mac fest.
- Durchlauf (Jan 25.11.2026): Handy nicht drehen, den Balken im Kasten drehen (Länge an der langen Bildseite).
- Raster (Jan 25.11.2026 „dezenter und mehr neopunk“, Kreuzpunkte cyan, Ziel und Ecken magenta; von Jan 25.11. „passt erstmal“): am Mac im Live-Bild, beim Messen und beim Zuschnitt, an der Bildmitte, Weite aus dem Plan (cm
  steht unter dem Bild); auf fertigen Fotos keins. Messlinie rastet bis 6 Grad waagerecht/senkrecht ein, Fadenkreuz am
  Zeiger. iPhone-App (Jan 26.11.2026 „raster wie in webapp“): gleiches Muster und gleiche Weite wie am Mac, Text „Raster 10 cm“
  unter dem Bild. Der Browser hängt die Weite an /live.jpg (r = Anteil der langen Bildseite am ganzen Bild, w mm, g),
  server.py gibt sie per logik.raster_fuers_handy mit jeder Live-Antwort an die App. Ohne Plan oder mit altem
  Mac-Programm: 1/12 der langen Seite ohne Maß. Die App zeigt das ganze Bild, nicht den Zuschnitt. Am 26.11.2026 in
  Xcode gebaut und auf Jans iPhone gespielt, läuft laut Jan. Team-Kennung (DEVELOPMENT_TEAM, Jans Personal Team) steht
  im Projekt, damit scp sie nicht mehr überschreibt; kostenlose Signierung, App läuft 7 Tage, dann in Xcode neu Run.
- App-Icon und Name (Jan 26.11.2026 „app logo neuro lign“): Logo der Web-App (N mit vier Punkten, weiß auf schwarz) als
  Assets.xcassets/AppIcon (1024 px, mit Pillow aus den SVG-Maßen gezeichnet), Name auf dem Home-Bildschirm „Neurolign“.
- Testdurchlauf B002 (Kästchen 29,5 x 13,5 x 20 cm, Jan 25.11.2026, von Claude per Chrome bedient): Aufnahme, Labeln,
  Training laufen auf dem Mac durch. Vier Seiten je ein Foto, 12 MP: 4032 x 3024 px, 2,2-2,8 MB, 1/46 s ISO 32
  (eingestellt 1/46 s ISO 33), Auslösen bis Bild 1,2-1,4 s, HEIC-Zuschnitt per sips klappt. Linse bis Rolle 59 cm
  (eingetragen, nicht nachgeprüft), Zuschnitt [0,098 0,031 0,722 0,937] ohne die Folienwand. Bildwinkel an Seite 2 mit
  29,5 cm gemessen: Faktor 0,749 (etwa 26 mm KB, passt zur Hauptkamera iPhone 16), 7,74 px/mm bei 39 cm.
  Maßhaltigkeit offen: Seite 3 im Bild etwa 4 % zu groß, Seite 1 etwa 2 % (Höhe der Fläche über der Rolle ungemessen).
  Der erste Maßstab war falsch (an der breiten Fläche gemessen, mit dem Abstand der schmalen gerechnet).
  Labels: Seite 2 und 4 als Entwurf von Claude, von Jan bestätigt (8 Objekte); Seite 1 und 3 ungelabelt (Öffnung,
  Etikett). B001 Seite 2 ist leer gespeichert (ein Enter zu viel, siehe Fehler unten), B001 steht auf „Nur Test“.
  Ablaufprobe altholz-1 (nur Altholz, B002 allein, noch mit train = val, alte Fassung, nichts festgelegt): fehlerfrei, 60 Epochen in knapp
  7 min, 4-7 s je Epoche. Für Freitag reicht so ein Kurzlauf als Kettenprobe.
  Belichtung (Helligkeit 0-255, gedimmte Lampe): Holz Median 175-204, oberstes 1 % 216-227, nichts ausgebrannt. Grund
  an den Seiten 30-50 % heller als in der Mitte (Folienwand). Lampenstufe nebensächlich, wichtiger: feste markierte
  Stufe, matte Wände. Leisten (je 15 cm von der Außenwand): grob gerechnet wären 10 cm gleichmäßiger (87 -> 95 %).
  Auflösung (Jan 25.11.2026 „das passt so“): ab jetzt 48 MP aufnehmen; 12 MP bei Bedarf beim Bau durch 2x2-Mitteln
  rechnen (noch nicht gebaut).
- Maßhaltigkeit (26.11.2026): Rechnung ist das Lochkameramodell, richtig. Ein falscher Abstand Linse-Rolle erklärt
  die 4 % an B002 nicht (1 cm Fehler = 0,36 % zwischen Seite 2 und 3, für 4 % wären 14 cm nötig); Seite 1 und 3
  haben denselben Abstand und weichen trotzdem 2 % voneinander ab. Vermutlich Kästchen (Rand, Deckel, Lage) und
  Messpunkte. Beim echten Balken wiegt die eingetragene Höhe je Lage am meisten (5 mm = 1,2 %). Feineres Raster
  bringt nichts (nur Anzeige). Gegenprobe B002 Seite 4 (an Seite 2 geeicht): Ast B 16,3 x 16,8 mm im Foto, Jan
  „scheint genau genug“. Zollstock-Test am ersten echten Balken Fr 27.11. mit „Messen“.
- Messen (26.11.2026, Jan „elegant, nicht sloppy“): zwei Punkte, Länge steht sofort an der Linie (unter 10 cm in
  mm). Zollstockmaß eingeben, Abweichung live; „Prüfung speichern“ legt sie in balken.json (kontrollen) ab,
  Maßstab bleibt, Rückgängig direkt danach. Mittel steht rechts als „Maßprüfung“. Solange der Bildwinkel nur
  angenommen ist, ist „Als Maßstab übernehmen“ der Hauptknopf. Labeln zeigt weiter den Kreisdurchmesser (gleiche
  Fläche), nicht längs x quer.
- Ablauf (26.11.2026, Jan: nur Symbole, keine Wörter an Knöpfen, auch nicht am Hauptknopf): Seiten als Balken im
  Schrägbild, gemeinte Seite schraffiert, verdeckte Kanten gestrichelt (balken3d in app.js), darunter Fotos/Plan.
  Schritt als Symbol plus Zahl, Rollen als Balken > 90° > Balken, Hauptknopf Kamera (auch beim Weiterrollen), am Ende Etikett zum Labeln.
  Seitenbild mit Kamera bleibt. Einrichtung ohne Kurzbefehl. Geprüft auf dem Server mit Playwright und
  künstlichem Foto, nicht auf dem Mac.
- Fehler, offen: Im Labeln springt Enter nach dem letzten bestätigten Objekt zum nächsten offenen Foto, ein weiteres
  Enter speichert es leer als fehlerfrei.
- Papierkorb (oder Entf) legt ein Foto nach <Balken-ID>/verworfen/, direkt danach zurückholbar (Knopf, Cmd+Z).
- Auswahl fürs Labeln (Jan 27.11.2026: Serien zeigen Fehlstellen doppelt, manche Fotos nur Grund): koerper.py legt je
  Seite in koerper.json `auswahl` ab (je Foto Name, Lage a_mm..b_mm, Schärfe, Wahl drin/doppelt/leer), Logik in
  aufnahme/auswahl.py (tests/test_auswahl.py). So wenige Fotos, dass sie die Seite abdecken und Nachbarn sich um
  mindestens 80 mm überlappen (Jan: 8 cm, etwa die größte Fehlstelle längs); bei fast gleicher Reichweite (30 mm)
  das schärfere (Laplace). Unsichere Lage (Serienschritt ohne Stütze) und unplausible Seiten (grund): alle bleiben.
  Leer: weniger als 15 % Holz oder Fläche dunkel und nicht rot (ist_holz: Helligkeit unter 100, Rot minus Blau unter
  40; vorher galt ein Foto nur mit Grund als Holz übers ganze Bild). Keine Hintergrundbilder als Negativbeispiele (Jan).
  Nichts wird gelöscht: kette.gezeigt blendet leere und doppelte in Labeln, Vorlabeln, Training (Zählung) und Galerie
  (fotos, ausgeblendet im Tooltip) aus; ein Foto mit menschlichem Label (nicht nur Vorlabel) bleibt sichtbar.
  Berechnet wird die Auswahl mit dem Körper (Galerie rechnet veraltete Körper selbst, Vorlabeln am Mac rechnet ihn
  vorher). Server: Vorlabeln schickt die Auswahl mit, der Server legt sie in <Balken>/auswahl.json ab (gilt, wenn
  neuer als koerper.json). Offen: Tauschen einzelner Fotos von Hand (Oberfläche fehlt), Labels der Auswahl per Lage
  auf die ausgeblendeten Fotos übertragen (nach dem ersten Training). Am Mac noch nicht gelaufen.
- Bilderleiste im Labeln (Jan 26.11.2026): gruppiert Balken > Seite S1-S4 > Foto. Der aktuelle Balken ist offen, die
  anderen zu (Kopf: Pfeil, ID, Name, fertig/alle mit kleinem Balken; fertig = gespeichert, nichts offen, nichts
  ungespeichert). Zustand je Foto als Zeichen in der Bildecke: gestrichelter grauer Ring = leer, gelber Ring mit
  blauem Tortenstück = offen (Anteil geprüft), blauer Haken = geprüft, weißer Punkt = geändert. Zugeklappte Balken
  zeichnen keine Bilder, neu gebaut wird nur bei Wechsel, Auf/Zu und Verwerfen (163 Fotos in 41 Balken: 8 ms).
  /labeln?balken=<ID> öffnet den Balken aufgeklappt. Am Handy springt der Reiter Bilder zum aktuellen Foto.
  Balken wählen im Kopf (Jan 27.11.2026): Knopf mit ID, Name, fertig/alle öffnet die Liste aller Balken (Popover,
  Pfeile, Esc, Taste W); Wahl springt zum ersten offenen Foto. Kopf zeigt das Foto ohne Balken-ID und „n von N“ im Balken.
  Geprüft mit Playwright auf einer Kopie (4 Balken), 1440 und 390 px, axe ohne Befunde; nicht auf der Domain.
  Verwerfen: Symbol (Bild mit Kreuz) neben dem aktuellen Foto oder Entf, wenn ein Foto der Leiste den Fokus hat.
  Mac-Modus /api/loeschen und /api/zurueck (jetzt auch für hochgeladene Seiten), Servermodus /api/foto-weg und
  /api/foto-zurueck (neu, Werk.foto_zurueck, nur hochgeladene Seiten; Fotobox-Fotos zeigen dort kein Symbol).
  Rückgängig unten rechts (Pfeil mit Miniatur des Fotos) und Strg/Cmd+Z, mehrfach hintereinander; nach einer
  Objektänderung gehört Strg+Z wieder dem Objekt, der Knopf bleibt. Labels und ungespeicherte Änderungen kommen
  mit zurück. Geprüft mit Playwright auf Kopien (B002 als B002-B040, B501) im Mac- und im Servermodus, 1440 und
  390 px, axe ohne Befund, frischer Prüfer (übernommen: Sprung am Handy, deutlichere Zeichen, eigenes Symbol
  statt zweitem Mülleimer, Rückgängig verdeckt die Leiste nicht). Offen aus der Prüfung: Suche bzw. Sprung zu
  einem Balken bei 50 und mehr Balken. Am Mac nicht geprüft.
- Körper (26.11.2026, Ideen in docs/ideen-galerie-3d-und-aufteilung.md): aufnahme/koerper.py (numpy, Pillow,
  tests/test_koerper.py) findet je Zuschnitt die Holzfläche (Rot minus Blau, Otsu), dreht sie gerade, schneidet quer
  auf ihre Kanten, legt mehrere Fotos einer Seite nach mitte_mm überblendet aneinander (Vorschubrichtung aus dem
  Balkenende im ersten Foto, nie gespiegelt) und streckt auf die eingetragenen Maße. Ausgabe <ID>/koerper/S1-S4.jpg
  (4 px/mm, längs höchstens 8000 px) und koerper.json mit gemessenen Maßen und Abweichung in %. Fehlt px_je_mm (nur
  sips misst ihn), gilt Bildbreite / voll_mm. Kette.koerper rechnet in der Trainings-.venv neu, wenn balken.json oder
  ein Zuschnitt neuer ist. Seite /koerper?id=<ID> (nur Mac-Modus, ohne ID der letzte Balken mit Fotos): Quader mit
  CSS 3D, Seite i liegt bei rotateX(90°·i), Stirnseiten grau, ziehen/Pfeiltasten drehen, Rad/+/- zoomen, Tasten 1-4
  und Knöpfe drehen die Seite nach vorn, Knopf zeigt die größere Abweichung (gelb ab 2 %).
  Lage der Seiten: Beim Weiterrollen stößt die nächste Seite an die obere Bildkante (an B002 an den Zapfen des Bodens
  gesehen). Rollt jemand andersherum, liegen 2 und 4 vertauscht: nicht automatisch erkannt.
  B002 (Kopie in data/proben/B002): S1 +1,6 %, S2 ±0,0, S3 +3,3 längs / +3,7 quer (gleichmäßig, Fläche lag etwa
  15 mm näher an der Linse als eingetragen), S4 −0,7 %. Geprüft auf dem Server (Playwright, axe), nicht auf dem Mac.
  Nicht geprüft: echter Balken mit mehreren Fotos je Seite (nur künstlich), Feinabgleich am Bildinhalt fehlt (Lage
  längs nur aus mitte_mm). Kleine Seitenbilder S1_k.jpg bis S4_k.jpg (480 px breit) für die Galerie.
- Galerie (Jan 26.11.2026, „gleichzeitig Gruppen fürs Training zuordnen, per Drag and Drop“): /galerie (nur Mac-Modus,
  in der Navigation nach Aufnahme), Kette.galerie, /api/galerie. Drei Spalten Training / Prüfung / Nur Test (teile.json,
  wie die Trainingsseite), neueste Balken zuerst. Ziehen oder Pfeil links/rechts auf der Karte setzt den Teil
  (/api/teil), gesperrte Balken (schon trainiert) tragen ein Schloss und lassen sich nicht ziehen. Karte: abgewickelter
  Mantel (unten Seite 1, darüber 2 bis 4, je Streifen auf gleiche Höhe gestreckt), ohne Körper ein Zuschnitt, ID,
  Maße in cm, vier Striche = Seiten mit Fotos, gelber Punkt = Maßabweichung über 2 %, grüne Linie = Labelstand.
  Klick öffnet /koerper. Die Seite rechnet fehlende oder veraltete Körper selbst nach (kette.koerper_veraltet: fehlt,
  keine kleinen Bilder, balken.json oder ein Zuschnitt neuer oder fehlend), einer nach dem anderen, neueste zuerst.
  Geprüft auf dem Server mit 13 Kopien von B002 (Playwright: Ziehen, Sperre, Tasten, Neuladen; axe). Am Mac
  (26.11.2026, per Chrome): Galerie, Ziehen mit der Maus (gespeichert, zurückgezogen), Körper B002 in der
  Trainings-.venv gerechnet, gleiche Abweichungen wie auf dem Server, Drehen klappt. B001 Seite 3 brach mit
  KeyError 'zuschnitt' ab (Plan aus älterer Fassung ohne Zuschnitt, auch Ursache von „Vorschaubild B001 Seite 3
  fehlt“): behoben, fehlt der Zuschnitt, gilt das ganze Bild (Zuschnitt und Label speichern). /api/koerper meldet
  jede andere Ausnahme als 500 mit Text statt abgebrochener Verbindung. Am Mac nach dem Fix noch nicht geprüft.
  Neuer Balken bleibt wie bisher: „+“ in der Aufnahme, der alte steht danach in der Galerie.
- Balken verwalten (Jan 26.11.2026, für die 50 Balken bei Felix am 27.11.): Balkenwahl, „+“ und ··· stehen oben in
  der Seitenleiste der Aufnahme (nicht mehr in der Kopfzeile). ··· = Bearbeiten (Stift: Maße, Holzart, Name in einem
  Formular, auch Umbenennen), Löschen (Mülleimer); in der Galerie dasselbe am ··· jeder Karte, dazu Aufnahme (Kamera) und Labeln. /?balken=<ID> öffnet
  einen Balken in der Aufnahme; eine Karte ohne Fotos führt dorthin statt in den Körper. 3D-Ansicht: Pfeil zur Galerie
  (kommt man von dort, wie Zurück im Browser). Alle Knöpfe nur Symbol, auch Anlegen (+) und Speichern (Haken).
  Maße direkt rechts (Jan 26.11.2026): Klick auf die Zahlen L × B × H macht drei Felder daraus (Fokus auf der
  angeklickten Zahl), Enter oder Wegklicken speichert, Esc bricht ab, Fehler lässt die Felder offen. Wechsel des Balkens
  beim Ändern speichert erst. Die Zeile steht auch, wenn die Seite keinen Plan hat.
  - Name: feste ID bleibt (steckt in Fotonamen, Labelpfaden, teile.json, gebauten Datensätzen), dazu Feld "name" in
    balken.json (bis 40 Zeichen, leer = keiner), angezeigt als „B003 Name“. Vorschlag, Jan noch nicht vorgelegt.
  - Maße ändern geht auch mit Fotos (Werk.masse_aendern, logik.plan_anpassen), nichts wird verworfen: Abschnitte bis
    zum letzten Foto bleiben, wo sie sind; Abstand und Bildfeld folgen der neuen Höhe dieser Lage (Kamera, Bildwinkel,
    Zuschnitt, Vorschub wie beim ersten Foto); länger gibt neue Abschnitte am Ende, kürzer streicht nur leere am Ende.
    Mit angepasst: px/mm je Foto, Prüfmessungen der Seite, Plan im Foto-Papierkorb. Labels (Anteile) bleiben gültig,
    der Körper rechnet neu. Passt eine Seite nicht mehr in die Box, bleibt alles. Hochgeladene Seiten (frei) bleiben.
    Regel vorgeschlagen, von Jan noch nicht bestätigt.
  - Löschen: aufnahmen/<ID>/ wandert ganz nach aufnahmen/papierkorb/<ID>/ (Fotos, Zuschnitte, Labels, Körper), Eintrag
    in teile.json bleibt (Zurückholen kommt in dieselbe Gruppe). Rückgängig-Knopf „↶ ID“ unten rechts (Aufnahme und
    Galerie), auch Strg/Cmd+Z, solange die Seite offen ist; später nur von Hand zurückschieben. Nicht während Auslösen
    oder Training. Papierkorb wird nie geleert. Nur Mac-Modus (/api/balken-weg, /api/balken-zurueck).
  - Geprüft auf dem Server mit Playwright (Probedaten B002 und drei leeren Balken): Menü, Umbenennen, Löschen mit Strg+Z,
    Galerie-Dialog, Löschen und Zurück, Pfeil aus dem Körper; 1440 und 390 px, axe ohne Befund. Frischer Prüfer: übernommen ein Stift statt Stift und Tt,
    Rückgängig in der Ecke mit ID, größeres ··· am Handy. Offen aus der Prüfung: kein schneller Schritt zum nächsten
    Balken (nur Auswahlliste), drei ähnliche Kreispfeile (Rückgängig, Nochmal, Ansicht zurück). Am Mac nicht geprüft.

- Gruppiert annehmen (Jan 26.11.2026 „vorlabels sollte man auch gruppiert akzeptieren können“): in Labeln
  Mehrfachauswahl in Liste und Bild: Strg/Cmd-Klick einzeln, Umschalt-Klick Bereich (Liste nach Konfidenz sortiert),
  Klick aufs Klassenmuster einer Zeile = alle offenen dieser Klasse (Taste K), Klick auf die Konfidenz = alle offenen
  ab diesem Wert (G), Strg+A = alle offenen, Esc hebt auf. Dann Hauptknopf (Haken mit Zahl, Enter) bestätigt,
  Mülleimer (Entf) verwirft, Klasse im Bereich Bearbeiten (oder Ziffer) klassifiziert alle um. Knopf „Balken mit
  Haken“ im Kopf der aktuellen Balken-Gruppe (B) dehnt die Regel auf alle Fotos des Balkens aus (Zahl am Knopf); das
  wird sofort gespeichert, Rückgängig (Knopf in der Meldung, Strg/Cmd+Z) speichert den alten Stand zurück. Auf einem
  Foto wirkt es wie jede Änderung (Speichern mit Enter). Geprüft mit Playwright auf einer Kopie von B501: 32 Risse
  zu Fuge, 110 Risse auf dem Balken verworfen und zurück (Platte geprüft), 1440 und 390 px.
- Vorlabeln per Modell (Jan 26.11.2026, docs/plan-vorlabeln.md): aufnahme/vorlabeln.py (rein, Bordmittel,
  tests/test_vorlabeln.py), Kette.vorlabeln_* (Mac), bilder.py kacheln, seite/vorlabeln.js und .css (Labeln und
  Galerie). Gerechnet auf dem Mac: Lauf holt im Hintergrund mit neurolign_abgleich.sh runter die Fotos, schneidet zu,
  kachelt wie das Training (1280 px, 256 Überlappung, Objekt zählt im Kern seiner Kachel), `yolo segment predict`
  (imgsz 1280, retina_masks, save_txt, save_conf, device mps) als eigener Prozess in der Trainings-.venv. Server holt
  fertige Balken über den Tunnel ab (GET /api/vorlabeln, Abholer alle 3 s solange ein Lauf läuft) und fügt sie in seine
  Labels ein, dann vergisst der Mac sie (/api/vorlabeln-ab). Im Mac-Modus gehen sie direkt in die Labels auf dem Mac.
  Ein Lauf auf einmal, nicht neben einem Training.
  Regeln: bestätigte und von Hand gezeichnete offene Objekte bleiben, alte offene Vorlabel (mit q) werden ersetzt, neue,
  die ein bleibendes Objekt zur Hälfte überdecken, fallen weg; neu je Objekt k, p, c, q (Modellname), ok false; von
  „vorlabel“. Prüfung und Nur Test (teile.json des Macs) bleiben gesperrt (Schloss), einmal mit einbeziehen nur über ···.
  Modell: bestes altholz-N nach Altholz-Prüfzahl (Masken-mAP50-95; alte Läufe mit Prüfung auf Trainingsbildern zählen
  nicht), bei Gleichstand das neuere, sonst kodytek-seg1-n1280; Name klein als Etikett, anderes nur über ···.
  Klassen über den Schlüssel (Namen aus aufnahmen/altholz-N.json bzw. der data.yaml aus args.yaml) auf die feste ID.
  Bedienung: Labeln: Zauberstab im Kopf jeder Balken-Gruppe (ganzer Balken) und neben dem aktuellen Foto, Etikett und
  ··· vorn in der Bilderleiste. Galerie (Mac): Karten mit Strg/Cmd/Umschalt-Klick oder Leertaste wählen, unten Leiste
  mit Zahl, Zauberstab, Etikett, ···; dazu im ··· jeder Karte. Fortschritt je Balken als Zeichnung (gestrichelter Ring
  wartet, Tortenring Kacheln, Haken fertig, Dreieck Fehler, Schloss gesperrt), durchgestrichenes Notebook ohne Mac.
  Fertige Balken lädt Labeln neu, Fotos mit ungespeicherten Änderungen bleiben (ihr Speichern meldet den Konflikt).
  Geprüft: Tests mit yolo-Attrappe (Kacheln, Überlappung, Regeln, Sperre, Fehler, Server -> Tunnel -> Mac -> Labels
  des Servers, Mac aus); Galerie und Labeln mit Playwright auf Kopien (B002, B501) und yolo-Attrappe, 1440 und 390 px.
  Nicht geprüft: echtes yolo und Mac (Dauer, Speicher bei 48-MP-Zuschnitten, ob retina_masks-Umrisse gut aussehen),
  Abgleich runter vor dem Vorlabeln holt alle Balken (wie beim Training).
  Offen: Mac-Modus-Vorlabel eines Balkens, den der Server schon labelt, überschreibt das nächste `abgleich runter`.
  Körper für hochgeladene Balken (B501) bricht in der Galerie ab (KeyError flaeche_mm, freier Plan), schon vorher so.
- Mac einrichten für Vorlabeln (offen bei Jan, Mac-Terminal, lokal): `scp agents-user:agenten/fehlstellenscan/mac/neurolign_einrichten.sh ~/fehlstellenscan/mac/`
  und `bash ~/fehlstellenscan/mac/neurolign_einrichten.sh` (holt den neuen Code, startet launchd neu). Auf dem Mac
  müssen runs/segment/kodytek-seg1-n1280/weights/best.pt und datensaetze/kodytek-seg-1/data.yaml liegen. Achtung:
  Vorlabeln auf B501 ersetzt Felix' offene Vorlabel aus balken.py (bestätigte bleiben).
- Frischer Prüfer (26.11.): übernommen Balkenebene nur per Klick (Enter/Entf wirken dort nicht), Balkensymbol mit
  Fotozahl an Haken und Mülleimer, Rückgängig bleibt stehen, Schloss nur im Kopf, Zauberstab ohne Haken als Auslöser,
  deutlichere Auswahl. Offen aus der Prüfung: Konfidenz in der Liste nur als Warnzeichen sichtbar (Optik-Einstellung),
  doppelter Balken-Knopf (Kopf und Bearbeiten), Etikett-Platz in der Leiste.
- Raster und Zollstock in Labeln (Jan 26.11.2026 „Cm raster einstellbar, Digitalen Zollstock einblendbar
  (einmessbar)“), seite/massstab.js: Werkzeugleiste rechts neben Zoom. Raster (R) ab der linken oberen Bildecke,
  Weite 1/2/5/10 cm (am Handy nur die gewählte, Tipp schaltet weiter), jede fünfte Linie kräftiger; Raster und Weite
  merkt sich der Browser. Ohne Maßstab ist der Raster-Knopf gestrichelt und startet den Zollstock. Zollstock (L): zwei
  Klicks setzen ihn, Enden ziehen dreht und verlängert (Umschalt rastet 15°), Band ziehen verschiebt, Esc beim Setzen
  bricht ab. Mit Maßstab gelbes Band mit mm/cm-Teilung und Länge, ohne nur Linie mit px. Einmessen: echte Länge ins
  Feld neben dem Zollstock, Enter oder Haken; gespeichert je Foto als mm je Pixel des Zuschnitts in
  aufnahmen/<Balken>/einmessung.json (POST /api/foto-massstab, Mac und Server, Recht labeln; Abgleich runter holt sie
  mit). Gilt vor Plan- und Streifenbild-Maßstab; Labels bleiben unverändert (Anteile). Rückgängig in der Meldung.
  Geprüft: Tests, Playwright auf Kopien von B501 im Mac- und Servermodus, 1440 und 390 px, axe ohne Befund.
  Offen aus der Prüfung: Maßstab gilt nur je Foto (nicht für die ganze Seite übernehmbar), Einmessen auf einem Foto
  mit Maßstab ersetzt ihn ohne eigenes Zeichen (nur Rückgängig), Zollstock nicht per Tastatur setzbar.
- Raster und Zollstock in der Aufnahme (Jan 26.11.2026 „vor allem fürs Aufnehmen“, „überall die Möglichkeit, ein
  Raster einzuschalten, mit verschiedener Größe, auch den Zollstock“), app.js, Leiste unter dem Bild rechts (#massw):
  Raster-Knopf (R) schaltet die Kreuze im Livebild, beim Messen und Zuschnitt und jetzt auch auf Fotos; Mitte und
  Ecken bleiben im Livebild immer. Weite 1/2/5/10 cm statt nur automatisch (am Handy schaltet die gewählte weiter),
  das iPhone folgt der Weite, Raster aus schickt dem iPhone kein Maß. Zollstock (L, Gliedermaßstab-Symbol, Messen
  behält das Lineal): zwei Klicks, Enden ziehen, Band ziehen; Teilung aus dem Plan der Seite, „≈“ solange der
  Bildwinkel nur angenommen ist. Auf einem Foto: echte Länge in cm, Enter oder Haken übernimmt sie als Maßstab
  (/api/massstab wie Messen, gilt für den Balken). Im Livebild nur Anzeige. Geprüft mit Playwright auf einer Kopie
  (Testbalken mit Foto vom Mac), 1440 und 390 px, axe ohne Befund; Livebild mit iPhone nicht geprüft. Servermodus hat
  keine große Bildansicht (Hochladen nur Vorschaubilder), dort gibt es Raster und Zollstock nur in Labeln.

## Neurolign-Server (ab 26.11.2026)
- Jans Wahl 26.11.2026 nachts: Neurolign läuft zusätzlich auf dem Server, immer an, für Henri und Felix; Server ist
  Hauptablage für Fotos und Labels, Training bleibt auf dem Mac. Adresse https://neurolign.meldro.de, Passwort je Person
  (Caddy basicauth jan, henri, felix). Plan: docs/plan-neurolign-server.md, Jans Schritte: docs/neurolign-einrichten.md.
- Stand 26.11.2026 morgens: Dienst fehlstellenscan-neurolign läuft (Vorlage systemd/, 127.0.0.1:8796, MemoryMax 768M,
  OnFailure=ausfall@), Ablage data/neurolign/aufnahmen. Passwörter in .env (NEUROLIGN_PASSWORT_JAN/_HENRI/_FELIX),
  Caddy-Block data/caddy-neurolign.txt (Hashes). DNS und Caddy eingerichtet (26.11.), https://neurolign.meldro.de
  antwortet 401 ohne Passwort, Jan ist angemeldet. Passwörter an Henri und Felix gibt Jan selbst weiter.
- Oberfläche = Klon der Mac-Oberfläche (Jan 26.11.2026 abends „einfach ein clon“): dieselben Seiten Aufnahme,
  Galerie, Körper, Labeln, Training, dieselben Wege (server.mac_wege), /api/stand im Mac-Format ohne iPhone-Adressen.
  Auslösen und Kamera melden auf dem Server „iPhone nicht verbunden“ (iPhone-Wege /h/ und /live.jpg gibt es dort
  nicht); Fotos kommen über „Foto vom Mac“ (···) in einen Abschnitt. Teil in der Galerie: gilt auf dem Mac (Tunnel)
  und wird bei Erfolg auch auf dem Server gesetzt. Die frühere Seite Hochladen ist entfernt (/api/hochladen bleibt).
  Jan 26.11.2026 nachts: Aufnahme mit dem iPhone nur am Mac, die Domain dient zum Labeln. iPhone über die Domain
  ginge nur mit drei Änderungen (App nimmt nur http, Caddy-basicauth auch auf /h/, Server sperrt /h/), verworfen.
  Galerie auf dem Server versucht für rein hochgeladene Balken (B501) einen Körper; koerper.py scheitert dort an
  fehlendem flaeche_mm (nur Logeintrag, Vorschlag: vorher abfangen, nicht umgesetzt).
  Offen: Balken löschen auf dem Server löscht nicht auf dem Mac (Abgleich lässt fremde gleicher ID stehen); Körper
  auf dem Server rechnet in der Grenze von 768 MB, mit großen Fotos ungeprüft; Seiten im Browser auf der Domain nicht
  angesehen (nur Auslieferung und Tests geprüft).
- Code: server.py --server (gleiches Programm wie auf dem Mac, Mac-Modus unverändert), zugang.py (Rechte, rein,
  tests/test_neurolign_server.py). Nutzer kommt aus X-Nutzer, die Caddy setzt; geglaubt nur von
  127.0.0.1 mit Host neurolign.meldro.de. POST nur mit Origin https://neurolign.meldro.de und X-Aufnahme. Henri und
  Felix dürfen alles wie Jan (vollwertige Kollegen, Jan 26.11.2026): anlegen, hochladen, labeln, Fotos verwerfen,
  Maße ändern, Training starten. iPhone-Wege und Kodytek-Auswahl gibt es im Servermodus nicht.
- Training vom Server, gerechnet auf Jans Mac (Jan 26.11.2026 „so bauen“): tunnel.py. Der Mac hält per launchd
  (de.meldro.neurolign, mac/neurolign_dienst.sh, eingerichtet mit mac/neurolign_einrichten.sh) Neurolign mit
  --tunnel-port 8766 (zweiter Eingang nur 127.0.0.1, nur GET/POST /api/training, /api/abbrechen, /api/teil, nur mit
  Kopfzeile X-Tunnel = NEUROLIGN_TUNNEL_SCHLUESSEL aus .env beider Seiten) und ssh -R 127.0.0.1:8797 zum Server offen,
  dazu caffeinate -s (wach nur am Netzteil). Der Server reicht diese Wege an 127.0.0.1:8797 weiter (--mac-port,
  --env); Mac nicht da: 503 mit mac:false, die Seite zeigt ein durchgestrichenes Notebook und sperrt den Start.
  Vor jedem Start (auch lokal am Mac) holt Neurolign mit --abgleich die Labels vom Server (neurolign_abgleich.sh
  runter); scheitert das, startet kein Training. Ergebnis und Läufe bleiben auf dem Mac.
  Geprüft: Tests mit Mac, Eingang und Server in einem Prozess; Seite gerendert mit und ohne Mac, axe ohne Befunde.
  Nicht geprüft: echter Mac, launchd, ob sshd auf dem Server -R erlaubt (zeigt neurolign_einrichten.sh am Ende),
  ssh unter launchd ohne Passwortabfrage. neurolign_einrichten.sh lief am 27.11.2026 auf dem Mac durch (Tunnel steht);
  Neurolign läuft dort jetzt als Dienst, neuer Code: rsync aufnahme/ (ohne app/), dann launchctl kickstart -k gui/$(id -u)/de.meldro.neurolign.
- Hochladen: Seite auf dem Balkenbild wählen, Fotos einzeln hoch (je höchstens 40 MB, Caddy 50 MB). Hochgeladene Seiten
  haben einen freien Plan (frei, ohne Abschnitte, ohne Zuschnitt, Maße in Pixeln); Fotobox-Seiten nimmt der Server
  nicht an, der Mac zeigt freie Seiten ohne Plan und fotografiert dort nicht. JPEG und PNG; HEIC abgelehnt (kein Paket
  dafür auf dem Server). Server vergibt Balken ab B501 (Mac ab B001).
- Labels tragen von (Name). Speichern schickt den geladenen Stand mit; hat inzwischen jemand anderes gespeichert, kommt
  ein Fehler mit Namen statt stillem Überschreiben (auch im Mac-Modus).
- Kodytek-Auswahl auf dem Server (Jan 26.11.2026 „immer die Randfälle Kodytek auf der Domain“): abgleich hoch schickt
  die ausgewählten Bilder mit Originalumrissen nach aufnahmen/kodytek/quelle/{images,labels}/<teil>/, Korrekturen
  und einmessung.json mit --ignore-existing, auswahl.json zuletzt; runter holt kodytek/labels und einmessung.json.
  kette.kodytek_bild nimmt den Mac-Pfad aus auswahl.json oder die Kopie in quelle/. Lokal mit nachgestelltem ssh
  durchgespielt, mit dem echten Mac noch nicht. Offen bei Jan: neues Skript auf den Mac holen und hoch laufen lassen.
- Abgleich: mac/neurolign_abgleich.sh hoch (neue Fotobox-Balken auf den Server; lässt Balken mit Labels auf dem Server
  und fremde gleicher ID aus) und runter (alle Balken vom Server auf den Mac, ohne zuschnitt/, einstellungen.json und
  teile.json; fremde gleicher ID bleiben auf dem Mac). Lokal mit nachgestelltem ssh durchgespielt, nicht mit dem echten Mac.
- Geprüft: Tests; Dienst lokal (403 ohne Nutzer); Probe-Caddy ohne root auf Port 18950 mit dem echten Block (401 ohne und
  mit falschem Passwort, Henri bleibt Henri trotz eigener X-Nutzer-Kopfzeile); Seiten gerendert 1440 und 390 px als henri
  und jan, axe ohne Befunde. Nicht geprüft: echtes HTTPS und Zertifikat (erst nach DNS), Hochladen vom iPhone (HEIC?),
  Fotobox-Balken vom Mac auf dem Server (Fotos der iPhone-App als HEIC wären dort nicht zuschneidbar).
- Offen: Datenschutz: Fotos liegen bei
  Contabo, Henri und Felix sehen alle Balken.

## Werkbank (Mac, FiftyOne, ab 23.11.2026)
FiftyOne zeigt Bilder mit Markierung und Vorhersage im Browser, wertet je Objekt aus und speichert Ansichten.
Freigabe Jan 23.11.2026: Python 3.13 von python.org und fiftyone (mac/requirements-werkbank.txt) in eigener
~/fehlstellenscan/.venv-werkbank. FiftyOne kann laut Doku und PyPI (1.22.1) kein Python 3.14, darum nicht in der
Trainings-.venv. Nicht auf dem Server (eigene MongoDB, zu wenig Speicher).
- Code: werkbank.py (reine Umwandlung YOLO-seg -> Rechteck plus Maske, mm wie auswertung.py, getestet) und
  mac/werkbank_laden.py (importiert fiftyone, nur Mac, vom Gerüst-Test ausgenommen, weil im Unterordner).
- Beim Laden: Auswertung je Objekt (Masken-IoU 0,5, Konfidenz ab 0,25; Felder eval und eval_frei ohne
  Klassenzwang), Bericht je Klasse, mAP, verdächtige Labels (compute_mistakenness). Gespeicherte Ansichten:
  übersehen, Fehlalarme, kleine Äste übersehen (unter 10 mm), Klasse vertauscht, verdächtige Labels zuerst.
- Läuft seit 23.11.2026 (fiftyone 1.22.1, Python 3.13.17, M4 Pro). save_view mit overwrite und Auswertung auf der
  gefilterten Ansicht funktionieren; Laden und Auswerten von val rund 1-2 min. Bericht: data/laeufe/kodytek-seg1-n1280/
  werkbank-val.txt, Vergleich mit auswertung.py im Abschnitt Auswertung. Die Vorhersage lief auf der CPU.
- Ähnlichkeitskarte und Einzigartigkeit (compute_visualization, compute_uniqueness) brauchen ein Bildmodell,
  vermutlich torch in .venv-werkbank: erst nach Jans Okay.
- Plan Werkbank für Henri und Felix (Jan 23.11.2026 „merken, erstmal lassen“, nichts eingerichtet): Subdomain
  werkbank.meldro.de (Name noch offen). Jan bei INWX: A 84.247.188.205, AAAA 2a02:c207:3020:9076::1. Jan als root:
  Caddy-Block wie lia.meldro.de (basicauth je ein Benutzer für Henri und Felix, Hash per `caddy hash-password`,
  HSTS) mit reverse_proxy 127.0.0.1:5151. Claude: mac/werkbank_teilen.sh startet Oberfläche plus `ssh -N -R
  127.0.0.1:5151:127.0.0.1:5151 agents-user` und `caffeinate`, ctrl-c beendet beides. Erreichbar nur, solange das
  Skript läuft (FiftyOne und Bilder bleiben auf dem Mac). Henri und Felix können Tags und Ansichten ändern (nur
  Datenbank, werkbank_val.sh baut neu). Port 5151 auf dem Server frei; ob sshd Weiterleitung erlaubt, ungeprüft
  (50-cloud-init.conf nur für root lesbar).
- Datenschutz: FiftyOne sendet laut eigener Angabe Nutzungsstatistik, abschalten wie unten (wie sync=False bei
  ultralytics). Mit `fiftyone config do_not_track` prüfen.

Einrichten (einmal, Mac-Terminal; erneut starten schadet nicht, holt auch neue Skripte):

    mkdir -p ~/fehlstellenscan/mac && scp agents-user:agenten/fehlstellenscan/mac/werkbank_einrichten.sh ~/fehlstellenscan/mac/
    bash ~/fehlstellenscan/mac/werkbank_einrichten.sh

Das Skript prüft Python 3.13 (sonst öffnet es python.org: neueste 3.13 mit Mac-Installer, am 23.11. 3.13.17), holt
die Skripte, baut .venv-werkbank, installiert fiftyone und schaltet die Statistik ab (`do_not_track: true`).

Benutzen (Mac-Terminal):
- val komplett: `bash ~/fehlstellenscan/mac/werkbank_val.sh`. Vorhersage mit der Trainings-.venv (conf 0.05,
  löscht vorher alte Vorhersagen, weil yolo anhängt; Ausgabe landet in runs/segment/val-vorhersage/seg1),
  Markierung und Vorhersage zum Server, Laden mit Auswertung (--ersetzen --nur-laden), Bericht werkbank-val.txt
  zum Server, dann Oberfläche http://localhost:5151 (Beenden mit ctrl-c).
- Nur ansehen: `.venv-werkbank/bin/python mac/werkbank_laden.py zeigen --name kodytek-seg1-val`.
- Felix' Balken: `.venv-werkbank/bin/python mac/werkbank_laden.py kacheln --kacheln balken-felix/kacheln
  --vorhersage runs/segment/balken-felix/vorhersage/labels --name balken-felix-iso800`.

## Seg-Modell auf Felix' Balken (balken.py, ab 21.11.2026)
Ziel (Jan 21.11.2026): kodytek-seg1-n1280 auf einem ganzen Balken ausprobieren. Quelle: Streifenbild aus
holzbalkenscan, Reihe ISO 800 (Testbalken 261019 Seite A, BSH mit 7 Lamellen, 6485 x 230 mm, 6 Px/mm), Lauf
20261107-010055 (Felix' Code unverändert). Balkenfeld im Streifen ab Pixel (204, 205), am Bild nachgemessen.
- `balken.py kacheln` schneidet den Streifen in Kacheln wie Kodytek-Bilder: 2800 x 1024, transponiert (Faser
  senkrecht wie bei Kodytek), je Richtung auf 16,66 Px/mm quer und 6,67 Px/mm längs gestreckt, also 168 mm quer x
  153,5 mm längs je Kachel. Ergebnis: 114 Kacheln (57 längs x 2 quer, Überlappung mind. 40 mm), 65 MB, in
  data/laeufe/balken-felix-iso800/kacheln/ mit kacheln.json (Lage jeder Kachel in mm). Sichtprüfung l010: sieht
  aus wie ein Kodytek-Bild, Ast quer gestreckt wie im Training.
- `balken.py karte` legt die Vorhersagen zurück auf den Balken (l längs ab Balkenanfang, q quer ab Oberkante, mm),
  verwirft Doppelte aus Überlappungen (Fund zählt nur in der Kachel, in deren Kern sein Schwerpunkt liegt) und
  schreibt funde.json, funde.csv (Semikolon) und je Meter ein Kartenbild (3 Px/mm) mit Umriss, Name, Konfidenz
  und bei Ästen Ellipse lang x kurz in mm.
- Grenzen: Das Streifenbild ist ein Handy-Mosaik (JPG, 6 Px/mm), für Kodytek-Maßstab quer 2,8-fach hochgerechnet;
  feiner als 6 Px/mm wird nichts. Holz gealtert, verschmutzt, BSH-Fugen: alles anders als Kodytek-Schnittholz.
  Ergebnis ist ein Eindruck, kein Messwert. Eine Markierung zum Vergleich gibt es nicht.
- Mac (Umgebung an, ~/fehlstellenscan):

      mkdir -p balken-felix && scp -r agents-user:agenten/fehlstellenscan/data/laeufe/balken-felix-iso800/kacheln balken-felix/
      yolo segment predict model=runs/segment/kodytek-seg1-n1280/weights/best.pt source=balken-felix/kacheln imgsz=1280 retina_masks=True save_txt=True save_conf=True save=False project=balken-felix name=vorhersage exist_ok=True
      scp -r runs/segment/balken-felix/vorhersage/labels agents-user:agenten/fehlstellenscan/data/laeufe/balken-felix-iso800/

  (Pfad der Labels steht in der Ausgabe „Results saved to“; Kacheln ohne Fund haben keine .txt.)
- Server: `systemd-run --user --scope -q -p MemoryMax=1500M .venv/bin/python balken.py karte --kacheln
  data/laeufe/balken-felix-iso800/kacheln --vorhersage data/laeufe/balken-felix-iso800/labels --ausgabe
  data/laeufe/balken-felix-iso800/karte`. Kacheln schneiden brauchte 17 s und 630 MB.
- Ergebnis 21.11.2026 (Vorhersage auf dem Mac, conf 0,25 Vorgabe; 113 von 114 Kacheln mit Fund): 267 Funde
  nach 271 verworfenen Doppelten. Riss 196 (61 ab 0,5), Ast tot 33 (15), Ast mit Riss 13 (11), Harz 14 (1),
  Ast lebend 10 (4), Mark 1. Karte: data/laeufe/balken-felix-iso800/karte/ (karte_00m..06m.jpg, funde.csv).
- Sichtprüfung Meter 1 bis 2 und Auszählung: 137 der 196 Risse sind flache Linien genau auf den Klebefugen der
  Lamellen (quer bei 35, 70, 105, 140, 175, 210 mm), zusammen 16,8 m. Das Modell hält BSH-Fugen für Risse; Kodytek
  kennt keine Fugen. Einzelne Risse innerhalb einer Lamelle sehen echt aus (Schwindrisse), nicht gezählt.
- Äste: Die gefundenen sitzen auf echten Ästen, Maße plausibel (7 bis 21 mm). Es fehlen aber deutlich sichtbare
  Äste (Meter 1 bis 2 etwa 4 übersehen bei 6 gefunden, grob geschätzt) und ein dunkles Ausbruchloch bei
  l 1710 mm. Konfidenzen niedrig (Median 0,44 bei Ast tot). Gealtertes, dunkles Holz und Handy-Mosaik sind fürs
  Modell fremd.
- Schluss: Fürs Erkennen von Ästen auf Altholz taugt das Kodytek-Modell als Startpunkt, nicht als Ergebnis.
  Fugen als eigene Klasse oder Maske (Lage aus der Lamellenteilung) und eigene Altholz-Labels sind nötig (passt
  zu docs/plan-erster-test-altholz.md). Ohne Markierung gibt es keine Zahl für Trefferquote.

## Aufbau
- Code: fehlstellenscan/agent.py (Einstieg), datensatz.py, masken.py, balken.py, auswertung.py, konfig/ (Einstellungen im Repo)
- .venv: fehlstellenscan/.venv, agentkit per .pth eingebunden
- Dienst: fehlstellenscan-gruppe.service (Gruppen-Bot). Für agent.py noch keiner (später oneshot auf Auftrag).
- Zugangsdaten: fehlstellenscan/.env (Bot-Token, Gruppe, HNEE-Login), Vorlage .env.example
- Laufzeitdaten: fehlstellenscan/data/ (nicht im Repo) mit rohbilder/, annotationen/,
  datensaetze/<name>-<version>/, laeufe/<zeitstempel>/, modelle/. Logs: fehlstellenscan/logs/
- Auftrag von Hand anlegen, solange die Zentrale den Agenten nicht kennt:

      cd ~/agenten/fehlstellenscan
      .venv/bin/python -c "from agentkit import auftraege; print(auftraege.neuer_auftrag('fehlstellenscan', 'TEXT', quelle='hand'))"
      .venv/bin/python agent.py

## Entscheidungen
- 11.11.2026 (Jan): Eigener Agent, nicht in uni/ oder holzbalkenscan/.
- 11.11.2026 (Jan): Training von Hand auf Jans Mac (M4 Pro, PyTorch mit device="mps", 640 GB frei). Die Rohbilder
  liegen auf dem Mac. Der Server (keine GPU, 7,8 GB RAM ohne Swap, 70 GB frei) baut und prüft Datensätze nur in
  kleinem Umfang, wertet Läufe aus und macht später Vorhersagen. Nie den ganzen Datensatz auf den Server.
- 11.11.2026 (Jan): Lizenz ultralytics AGPL-3.0 vorerst angenommen, weil nur Jan es nutzt. Bei Weitergabe oder
  Zugang anderer (z. B. Portal) neu prüfen; Alternative YOLOX (Apache 2.0).
- 12.11.2026 (Jan): datensatz.py im Mittelweg: 10 Klassen (overgrown bleibt, in der Auswertung weglassen),
  Mindestgröße 2 px, Gruppen-Aufteilung 80/10/10 eingefroren, Manifest, Prüfung mit ultralytics und
  Überanpassungstest auf dem Mac.
- 12.11.2026 (Jan): Erstes Training auf kodytek-1 mit imgsz=1280 (nicht 640), Gründe siehe Befunde 12.11.2026.
- 12.11.2026 (Jan): Bild-ZIPs (157 GB) auf dem Mac auch nach dem Bau von kodytek-1 vorerst behalten (238 GB frei).
- 11.11.2026: Läufe nur auf Auftrag, ohne Claude, Rechenschritte später in systemd-run --scope mit MemoryMax wie
  holzbalkenscan. Tests importieren kein PyTorch (Test prüft das).

## Datensatz 1: Kodytek et al.
- Kodytek, Bodzas, Bilik: „A large-scale image dataset of wood surface defects for automated vision-based quality
  control processes“, F1000Research 10:581 (v2 2022). Daten: Zenodo 10.5281/zenodo.4694695, CC BY 4.0
  (Namensnennung nötig).
- 20.275 Farbbilder BMP 2800 x 1024, Schnittholz aus einer Sägewerkslinie (Zeilenkamera, Holzart nicht genannt),
  1.992 ohne Fehler. 10 Klassen mit Box und Maske, stark ungleich (Live_knot rund 42.000 Objekte, overgrown 10,
  blue_stain 192).
- Rund 155 GB in 10 ZIPs je etwa 15 GB: Download auf den Mac, nicht auf den Server.
- Ob alle sichtbaren Fehler markiert sind, sagt das Paper nicht. Kaggle-Spiegel (nomihsa965) nicht nutzen (ohne
  Login nicht lesbar, Lizenz und Inhalt unbekannt), Original von Zenodo nehmen.
- Zenodo (nur eine Version, 15.04.2021): 13 Dateien, 156,6 GB. Bouding_Boxes.zip (so geschrieben, 5,0 MB, md5
  9b9e9745bc220188faeb4065e4bcd101), Semantic Maps.zip (207 MB, md5 b06ab6c11b82eb906f64e8bc032cbc66, entpackt
  174 GB, nie ganz entpacken), Semantic Map Specification.txt (430 Byte, md5 045123a74ed25224737ec165328c5bb6),
  Images1–10.zip je 15,3–17,6 GB (Images1 md5 cba808d221d78c46e79958efd4785bca; alle md5 in der Zenodo-API
  https://zenodo.org/api/records/4694695). Bilder entpackt ebenfalls rund 174 GB (BMP 8,6 MB je Bild).
- Zenodo liefert nur etwa 300–400 KB/s und bricht ab: ein Bild-ZIP rund 13 Stunden, alles rund 5 Tage. Download mit
  Wiederholschleife (curl -C -, siehe Download-Stand).

### Box-Format (geprüft 11.11.2026 an allen 20.276 Dateien und der Maske zu 100000000)
- Je Bild <nummer>_anno.txt, je Fehlstelle eine Zeile: Klasse TAB x1 TAB y1 TAB x2 TAB y2, Windows-Zeilenende.
  Werte 0..1 = Pixel geteilt durch Breite 2800 bzw. Höhe 1024; (x1, y1) links oben, (x2, y2) rechts unten
  ausschließlich (Maske 100000000 deckt sich pixelgenau: Box 1231..1412 x 304..1024, Maske 1231–1411 x 304–1023).
- 1.992 leere Dateien (Bilder ohne Fehler), 43.974 Boxen, keine Werte außerhalb 0..1, keine vertauschten Ecken.
- 132 Dateien mit Dezimalkomma (0,902500) statt Punkt: beim Einlesen Komma durch Punkt ersetzen.
- Nicht alle Bilder sind 2800 breit: 155 Dateien passen zu Breiten 2709–2799 (z. B. 100000061: 2799,
  100000062: 2780). Die Masken haben genau diese Breite, und die Boxen sind auf die echte Breite bezogen (an beiden
  Masken pixelgenau geprüft). Für YOLO also unkritisch, die Breite immer aus dem Bild lesen, nie 2800 annehmen.
- 524 Boxen sind in einer Richtung unter 2 px (757 unter 5 px, 926 unter 10 px), z. B. 1 x 1 px; vermutlich
  Klickfehler beim Annotieren. Darunter 6 der 10 overgrown-Boxen. datensatz.py sortiert unter 2 px aus (Jan 12.11.).
- Klassennamen in den Dateien (Boxen / Bilder): Live_Knot 21.224 / 11.912, Dead_Knot 11.985 / 8.350,
  resin 3.455 / 2.624, knot_with_crack 2.276 / 1.835, Crack 2.169 / 1.578, Marrow 1.181 / 1.061,
  Quartzity 1.075 / 847, Knot_missing 503 / 478, Blue_Stain 96 / 77, overgrown 10 / 6. Schreibweise weicht von der
  Specification ab (dort Live_knot, Death_know, Blue_stain, Nummern 1–8, 10, 11 mit Maskenfarben).
- 20.276 Bilder, Box-Dateien und Masken, jede Nummer passt zu genau einem Bild (die 20.275 im Paper sind falsch gezählt).
- Sichtprüfung 12.11.2026 an 11 Bildern aus Images1 (data/rohbilder/, Boxen eingezeichnet in data/pruefung/,
  Skript noch nicht im Repo): Alle Boxen sitzen auf den Fehlstellen, auch bei schmalen Bildern (2799, 2780) und
  Dezimalkomma. Auffällig: schwarzer Hintergrund links und rechts neben dem Brett; senkrechte Nahtstellen mit
  Helligkeitssprung in manchen Bildern (Zeilenkamera); 100000022 („ohne Fehler“) zeigt einen dunklen Streifen
  ähnlich Quartzity ohne Box, also sind wohl nicht alle sichtbaren Merkmale markiert.

### Download-Stand (12.11.2026): vollständig
- Mac: ~/fehlstellenscan/daten/kodytek/ mit zip/ (alle 13 Dateien von Zenodo, 157 GB, alle md5 geprüft),
  bilder/Images1/ bis bilder/Images10/ (20.276 BMP, jedes mit Box-Datei und umgekehrt, abgeglichen mit comm),
  boxen/ (alle Box-Dateien), masken/ (nur 100000000, 100000061, 100000062). Danach 238 GB frei.
  Images1 enthält die Nummern 100–105, 106 zum Teil, 991, 993, 999 (ohne Blue_Stain und overgrown).
- Laden mit Neustart langsamer Verbindungen (im Ordner zip/, je Fenster eine Liste von ZIPs):

      for z in 3 4 5 6; do for i in {1..1000}; do curl -L --fail -C - --speed-limit 1000000 --speed-time 60 -o Images$z.zip "https://zenodo.org/api/records/4694695/files/Images$z.zip/content" && break; sleep 20; done; done

- Tempo: Zenodo begrenzt je Verbindung. Vom Server 2,1 MB/s je Verbindung, 4 gleichzeitig zusammen fast 10 MB/s.
  Auf dem Mac je Verbindung oft nur 0,25–0,35 MB/s, nach einem Neustart der Verbindung (Nacht 12.11.) aber
  3–7 MB/s: langsame Verbindungen früh abbrechen und neu ansetzen lohnt sich. Nicht über den Server umleiten (69 GB frei, Regel: nie den ganzen Datensatz dort).
- Spiegel: Hugging Face iluvvatar/wood_surface_defects (2023, Privatperson, CC BY 4.0), 2,2 GB Parquet, aber Bilder
  als JPEG Qualität 50 neu gespeichert und Boxen selbst ins YOLO-Format umgerechnet (README behauptet „alle
  2800 x 1024“, stimmt nicht). Höchstens für schnelle Vorversuche, nicht als Grundlage.
- Server: data/annotationen/ mit Bouding_Boxes.zip, Specification, Masken 100000000, 100000061, 100000062 (per scp, Jans Okay
  11.11.2026), entpackt nach data/annotationen/boxen/. data/rohbilder/: 11 Probebilder (Jans Okay 12.11.2026):
  100000000, 100000002, 100000005, 100000006, 100000022, 100000033, 100000061, 100000062, 100000069, 100100027,
  99100031 (je Klasse aus Images1 eins, ohne Fehler, schmal, Dezimalkomma).

## Offene Punkte
1. Pakete, Entscheidung Jan (Pillow, numpy und opencv-python-headless auf dem Server sind installiert):
   a) Server, später für Vorhersagen: ultralytics. Zieht torch nach sich (CPU-Fassung rund 1 GB, braucht beim
      Rechnen spürbar RAM).
   b) Mac: erledigt 11.11.2026, siehe Abschnitt Mac.
2. Datensatz Kodytek vollständig auf dem Mac (12.11.2026). Bild-ZIPs (157 GB) bleiben auch nach dem Bau von
   kodytek-1 vorerst (Jan 12.11.2026). Bei Platzmangel erneut fragen; Löschen macht Jan selbst auf dem Mac,
   nur Images*.zip, die kleinen ZIPs (Boxen, Masken, Specification) bleiben.
3. Erstes Training fertig (15.11.2026): Mac ~/fehlstellenscan,
   `yolo detect train data=datensaetze/kodytek-1/data.yaml model=yolo11n.pt epochs=100 imgsz=1280 batch=8
   device=mps name=kodytek1-n1280`, nach Pause bei Epoche 90 per resume fortgesetzt (letzte 10 Epochen
   3,6 h, rund 21 min je Epoche, GPU 9,4 GB). Gewichte Mac runs/detect/kodytek1-n1280/weights/ (best.pt 5,5 MB).
   - Epoche 100 (val): P 0,697, R 0,729, mAP50 0,749, mAP50-95 0,453. Ohne Mosaik kein Sprung mehr
     (Epoche 90: 0,749 / 0,455). Seit Epoche 40 praktisch Plateau: yolo11n ist an seiner Grenze.
   - best.pt auf val: P 0,726, R 0,690, mAP50 0,751, mAP50-95 0,460. Je Klasse (Bilder/Boxen, P, R, mAP50,
     mAP50-95): live_knot 1277/2204 0,83 0,82 0,874 0,45; dead_knot 812/1147 0,84 0,76 0,864 0,49;
     knot_missing 47/48 0,89 0,67 0,854 0,49; knot_with_crack 187/242 0,70 0,84 0,840 0,59; crack 162/215
     0,66 0,71 0,730 0,44; quartzity 110/127 0,64 0,51 0,630 0,40; resin 283/352 0,80 0,71 0,782 0,41;
     marrow 110/117 0,74 0,88 0,874 0,65; blue_stain 5/12 0,43 0,32 0,314 0,22 (nur 12 Boxen, Zufall groß).
     overgrown fehlt in val (gewollt). Inferenz 0,4 ms je Bild auf mps (ohne Nachbearbeitung 4,7 ms).
   - Test-Teil noch unberührt; erst am Ende für das gewählte Modell auswerten.
   - Dateien auf dem Server: data/laeufe/kodytek1-n1280/ (results.csv, args.yaml, Kurven, Matrizen,
     val_batch0-2 labels/pred, best.pt). Optimierer laut args.yaml MuSGD, lr0 0,01, Mosaik 1,0.
   - Verlauf (results.csv): beste Epoche 74 (mAP50 0,752, mAP50-95 0,460). Ab etwa Epoche 40 sinken die
     train-Verluste weiter, val box_loss und cls_loss steigen leicht (1,497 -> 1,537): leichte Überanpassung,
     bei gleichbleibendem mAP. 50-60 Epochen hätten gereicht.
   - Verwechslungsmatrix (Spalten = wahr, Anteil richtig): live_knot 0,91, dead_knot 0,80, knot_missing 0,75,
     knot_with_crack 0,81, crack 0,95, quartzity 0,72, resin 0,87, marrow 0,93, blue_stain 0,92 (11 von 12).
     Hauptverwechslungen: dead_knot als live_knot 16 % (188), live_knot als dead_knot 5 % (120),
     knot_missing als dead_knot 21 % (10), knot_with_crack als live_knot 10 % (25), quartzity als marrow
     20 % (26). Übersehen (Zeile background) nur 1-8 %. Die Hintergrundspalte (z. B. 10.726 live_knot ohne
     Label) ist vermutlich mit sehr niedriger Konfidenzschwelle gezählt (conf in args.yaml leer), also keine
     echte Fehlalarmrate. Das ist nicht geprüft. Der Recall in der Matrix liegt deshalb höher als R 0,69.
   - Sichtprüfung val_batch0 und 1 (32 Bilder, Schwelle der Bilder 0,25): Boxen sitzen fast immer richtig.
     Fehler sind meist live/dead an kleinen Ästen (wenige Pixel, auch am Label schwer zu entscheiden)
     und knot_with_crack auf Ästen, die als live_knot markiert sind, aber einen Riss zeigen könnten. Echte
     Aussetzer sind selten: ein winziger Ast (153200021) und Harz am rechten Brettrand (val_batch0, Zeile 3 rechts) fehlen.
     Schluss: Ein großer Teil der Fehler liegt an der Grenze der Klassen und an Labels, nicht an
     fehlender Erkennung. live/dead bleibt die wichtigste Schwäche (ob die
     Sortierung das braucht, hängt vom Normtext ab, noch nicht geprüft). val_batch2 noch nicht angesehen.
   Nächstes: über größere Modelle entscheiden (yolo11s etwa 3-fach, yolo11m etwa 10-fach Rechenaufwand; Mac oder gemietete
   GPU, Jans Entscheidung).
   Zurückgestellt bis nach
   dem ersten Modell (Jan 12.11.2026, Mittelweg): voller Abgleich Boxen gegen Masken, cleanlab/FiftyOne,
   Blindprüfung einer Stichprobe durch Prof. Böhme.
4. Läufe vergleichen (results.csv und args.yaml lesen) fehlt in auswertung.py noch; gehört zu Phase 3 der Werkbank
   (docs/plan-trainingswerkzeug.md). Fehler je Objekt und Messung am Holz sind gebaut (Abschnitt Auswertung).
5. Austausch Mac und Server festlegen (z. B. rsync oder scp nur für Annotationen, Läufe und Gewichte).
6. Zentrale kennt den Agenten noch nicht (AGENTEN in shared/telegram/logik.py), Bedarf steht in der Haupt-STATUS.md
   Punkt 40. Dienst systemd/fehlstellenscan.service fehlt noch, braucht Jans Okay.
7. Gewerbliche Nutzung (Ausschreibung, Werke): Lizenz ultralytics AGPL-3.0 neu prüfen, bevor ein Prototyp
   weitergegeben wird (Enterprise-Lizenz oder z. B. YOLOX, Apache 2.0). Kodytek CC BY 4.0 gewerblich erlaubt
   mit Namensnennung. Rechte an den Ergebnissen des HNEE-Projekts für eine Bewerbung mit Prof. Böhme bzw. der
   Hochschule klären. Ausschreibungstext der TU fehlt noch (Durchsatz, Abmessungen, Merkmale, Genauigkeit).
8. Segmentierung (Jan 19.11.2026): erstes Seg-Modell fertig und ausgewertet (21.11.2026, Abschnitt „Erstes
   Seg-Modell“). Nächstes: Maße aus den Umrissen (gekippte Box, Ellipse, kleinster Durchmesser) als getestete
   Funktion. Test-Teil weiter unberührt.

## Gelernte Regeln
- 19.11.2026: Rüdiger schreibt in der Gruppe im Stil der Gruppe: Du, locker, kurz, ohne Floskeln, fachlich genau (Anlass: Jan „so wie wir im Stil“).
- 19.11.2026: Mail-Entwürfe aus der Gruppe zeigt Rüdiger dort genau wie in der Zentrale; alle in der Gruppe können per Antwort ändern, freigeben nur Jan, auch per Knopf in der Gruppe (Anlass: Jan „mail entwurf soll aber in der gruppe sein“, „so dass andere änderungen machen können. freigeben nur ich“).
- 21.11.2026: Rüdiger hält Gruppen-Texte wirklich kurz, lieber Bilder als lange Erklärung (Anlass: Jan „der letzte text war aber zu lang von ihm“).
- 21.11.2026: Beispielbilder des Modells für die Gruppe nur mit Masken, keine Bounding Boxen (Anlass: Jan „die bounding boxes wollen wir nicht mehr sehen. nur die masken“).
- 19.11.2026: Rüdiger bleibt bei der Frage: keine ungefragten Verweise auf andere Verfahren, Teilprojekte oder Personen, keine internen Ordner- oder Dateinamen (Anlass: Jan „der Verweis zu Felix müsste nicht sein“).
- 24.11.2026: Jan will die Materie beim Arbeiten verstehen (5-6 h je Woche, kaum Python): Bei jedem Schritt an Daten und Training kurz erklären, was er da tut und warum (Anlass: Jan „bei jedem schritt auch nochmal besser zu verstehen was ich da überhaupt mache“).
