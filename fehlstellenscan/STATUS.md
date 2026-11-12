# Status: Agent fehlstellenscan (Fehlstellen-Scan)

## Zweck
Arbeit mit YOLO für Jans Forschungsprojekt zur Fehlstellenerkennung an Holzlamellen (HNEE, Betreuung
Prof. Böhme): Datensätze bauen und prüfen, Trainingsläufe auswerten und vergleichen, später Vorhersagen auf
neuen Bildern. Getrennt von uni/ (Moodle, Post) und holzbalkenscan/ (Prüfstand für Felix' Streifenbilder;
die können später als Dateien Eingabe werden).

## Stand (11.11.2026)
- Gerüst steht und ist committet: agent.py schließt jeden Auftrag mit dem Hinweis „noch nicht gebaut“ ab.
- datensatz.py, auswertung.py und konfig/ sind leere Plätze mit Beschreibung, was dort hineinkommt.
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
  Klickfehler beim Annotieren. Darunter 6 der 10 overgrown-Boxen. In datensatz.py mit Mindestgröße aussortieren
  (Grenze mit Jan festlegen) und melden.
- Klassennamen in den Dateien (Boxen / Bilder): Live_Knot 21.224 / 11.912, Dead_Knot 11.985 / 8.350,
  resin 3.455 / 2.624, knot_with_crack 2.276 / 1.835, Crack 2.169 / 1.578, Marrow 1.181 / 1.061,
  Quartzity 1.075 / 847, Knot_missing 503 / 478, Blue_Stain 96 / 77, overgrown 10 / 6. Schreibweise weicht von der
  Specification ab (dort Live_knot, Death_know, Blue_stain, Nummern 1–8, 10, 11 mit Maskenfarben).
- 20.276 Box-Dateien und 20.276 Masken, das Paper nennt 20.275 Bilder: eine Nummer zu viel, offen.
- Sichtprüfung 12.11.2026 an 11 Bildern aus Images1 (data/rohbilder/, Boxen eingezeichnet in data/pruefung/,
  Skript noch nicht im Repo): Alle Boxen sitzen auf den Fehlstellen, auch bei schmalen Bildern (2799, 2780) und
  Dezimalkomma. Auffällig: schwarzer Hintergrund links und rechts neben dem Brett; senkrechte Nahtstellen mit
  Helligkeitssprung in manchen Bildern (Zeilenkamera); 100000022 („ohne Fehler“) zeigt einen dunklen Streifen
  ähnlich Quartzity ohne Box, also sind wohl nicht alle sichtbaren Merkmale markiert.

### Download-Stand (11.11.2026)
- Mac: ~/fehlstellenscan/daten/kodytek/zip/ mit Bouding_Boxes.zip, Semantic Maps.zip, Specification (md5 stimmen),
  Images1.zip und Images2.zip vollständig (12.11.2026, md5 stimmen). Images1 enthält 2.000 BMP im Unterordner
  Images1/ (Nummern 100–105 ganz, 106 zum Teil, 991, 993, 999; Klassen ohne Blue_Stain und overgrown), entpackt
  nach ~/fehlstellenscan/daten/kodytek/bilder/Images1/. Entpackt außerdem: boxen/ (alle), masken/ (100000000, 100000061, 100000062).
  Laden mit Wiederholung (im Ordner zip/):

      for i in {1..50}; do curl -L --fail -C - --speed-limit 1000 --speed-time 120 -o Images1.zip "https://zenodo.org/api/records/4694695/files/Images1.zip/content" && break; sleep 30; done
      md5 Images1.zip

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
2. Probe erledigt (12.11.2026). Offen: Entscheidung Jan, ob Images3–10 (rund 125 GB) geladen werden; mit allem
   entpackt rund 330 GB auf dem Mac. Blue_Stain und overgrown liegen nur in anderen ZIPs.
3. datensatz.py bauen: Umwandlung ins YOLO-Format, Prüfungen, Aufteilung, data.yaml (mit Tests).
4. auswertung.py bauen: results.csv und args.yaml eines Laufs lesen, Läufe vergleichen, Meldung an Jan.
5. Austausch Mac und Server festlegen (z. B. rsync oder scp nur für Annotationen, Läufe und Gewichte).
6. Zentrale kennt den Agenten noch nicht (AGENTEN in shared/telegram/logik.py), Bedarf steht in der Haupt-STATUS.md
   Punkt 40. Dienst systemd/fehlstellenscan.service fehlt noch, braucht Jans Okay.

## Gelernte Regeln
- (noch keine)
