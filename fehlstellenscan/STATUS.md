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
- Ansatz „besser als Dataspree“ (Vorschlag, nicht entschieden): Masken statt Boxen fürs Messen (Kodytek hat
  Masken), Gesamtkarte über die ganze Länge (Kodytek-Gruppen schließen vermutlich lückenlos an), DIN 4074 als
  getestete Python-Regeln getrennt vom Modell (Sortierklasse, alle vier Seiten, Normtext vorher prüfen),
  Kennzahlen je Klasse und Messunsicherheit statt nur Konfidenz, Unsicheres an einen Menschen, Höhe messen statt
  eingeben. Gemeinsamer Kern (Erkennen, Messen, Karte), Klassen und Regelwerk je Einsatz austauschbar.
- Altholz: Kodytek deckt typische Merkmale nicht ab (Nägel, Schrauben, Farbe, Fäulnis, Insektenfraß, alte
  Verbindungen), eigene Bilder nötig; verdecktes Metall braucht vermutlich einen Metalldetektor. BSH: übersehene
  Fehler wiegen schwerer als Fehlalarme, Tempo und alle vier Seiten zählen.

## Stand (12.11.2026)
- Gerüst steht und ist committet: agent.py schließt jeden Auftrag mit dem Hinweis „noch nicht gebaut“ ab.
- datensatz.py gebaut und getestet (tests/test_datensatz.py), Aufteilung eingefroren in
  konfig/kodytek_aufteilung.json. Auf dem Server geprüft mit allen Box-Dateien und den 11 Probebildern
  (data/datensaetze/kodytek-probe/). Voller Lauf auf dem Mac 12.11.2026 fertig und geprüft (Befunde unten):
  Mac ~/fehlstellenscan/datensaetze/kodytek-1/ ist bereit fürs erste Training (imgsz 1280, Jan 12.11.2026). Ergebnisse in data/laeufe/
  (bericht.json, ueberlappung.txt, pruefung_ultralytics.txt, results.csv und args.yaml des Tests probe20).
- auswertung.py ist noch ein leerer Platz.
- Test tests/test_geruest.py: Name, Hinweis bei Aufträgen, kein Import von torch, torchvision oder ultralytics.
- .venv mit numpy 2.5.4 und Pillow 13.0.0 (Jan 11.11.2026) und agentkit per .pth; tests/test_umgebung.py
  prüft sie (auch BMP). Kein Dienst, kein Timer, keine Daten geladen.

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

## Aufbau
- Code: fehlstellenscan/agent.py (Einstieg), datensatz.py, auswertung.py, konfig/ (Einstellungen im Repo)
- .venv: fehlstellenscan/.venv, agentkit per .pth eingebunden
- Dienst: noch keiner (später oneshot auf Auftrag wie holzbalkenscan, braucht Jans Okay)
- Zugangsdaten: vorerst keine, Vorlage fehlstellenscan/.env.example
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
1. Pakete, Entscheidung Jan (Pillow und numpy auf dem Server sind installiert):
   a) Server, später für Vorhersagen: ultralytics. Zieht torch nach sich (CPU-Fassung rund 1 GB, braucht beim
      Rechnen spürbar RAM).
   b) Mac: erledigt 11.11.2026, siehe Abschnitt Mac.
2. Datensatz Kodytek vollständig auf dem Mac (12.11.2026). Bild-ZIPs (157 GB) bleiben auch nach dem Bau von
   kodytek-1 vorerst (Jan 12.11.2026). Bei Platzmangel erneut fragen; Löschen macht Jan selbst auf dem Mac,
   nur Images*.zip, die kleinen ZIPs (Boxen, Masken, Specification) bleiben.
3. Datensatz kodytek-1 auf dem Mac gebaut und geprüft, Sichtprüfung bestanden, imgsz 1280 festgelegt
   (12.11.2026). Nächster Schritt: erstes Training auf dem Mac, z. B.
   `yolo detect train data=datensaetze/kodytek-1/data.yaml model=yolo11n.pt epochs=100 imgsz=1280 batch=8
   device=mps name=kodytek1-n1280` (epochs und batch noch Vorschlag). Zurückgestellt bis nach
   dem ersten Modell (Jan 12.11.2026, Mittelweg): voller Abgleich Boxen gegen Masken, cleanlab/FiftyOne,
   Blindprüfung einer Stichprobe durch Prof. Böhme.
4. auswertung.py bauen: results.csv und args.yaml eines Laufs lesen, Läufe vergleichen, Meldung an Jan.
5. Austausch Mac und Server festlegen (z. B. rsync oder scp nur für Annotationen, Läufe und Gewichte).
6. Zentrale kennt den Agenten noch nicht (AGENTEN in shared/telegram/logik.py), Bedarf steht in der Haupt-STATUS.md
   Punkt 40. Dienst systemd/fehlstellenscan.service fehlt noch, braucht Jans Okay.
7. Gewerbliche Nutzung (Ausschreibung, Werke): Lizenz ultralytics AGPL-3.0 neu prüfen, bevor ein Prototyp
   weitergegeben wird (Enterprise-Lizenz oder z. B. YOLOX, Apache 2.0). Kodytek CC BY 4.0 gewerblich erlaubt
   mit Namensnennung. Rechte an den Ergebnissen des HNEE-Projekts für eine Bewerbung mit Prof. Böhme bzw. der
   Hochschule klären. Ausschreibungstext der TU fehlt noch (Durchsatz, Abmessungen, Merkmale, Genauigkeit).

## Gelernte Regeln
- (noch keine)
