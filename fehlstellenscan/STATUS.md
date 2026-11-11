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
- .venv ohne Pakete (nur Bordmittel und agentkit per .pth). Kein Dienst, kein Timer, keine Daten geladen.

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
- Vorbehalte: Box-Format im Paper widersprüchlich (Reihenfolge der Ecken, „durch 100 geteilt“), vor dem Umwandeln
  an Bildern prüfen. Ob alle sichtbaren Fehler markiert sind, sagt das Paper nicht. Kaggle-Spiegel (nomihsa965)
  nicht nutzen (ohne Login nicht lesbar, Lizenz und Inhalt unbekannt), Original von Zenodo nehmen.

## Offene Punkte
1. Pakete, Entscheidung Jan:
   a) Server: Pillow und numpy, um Bilder und Boxen zu prüfen und umzuwandeln (klein, wie holzbalkenscan).
   b) Server, später für Vorhersagen: ultralytics. Zieht torch nach sich (CPU-Fassung rund 1 GB, braucht beim
      Rechnen spürbar RAM).
   c) Mac: torch und ultralytics für das Training, installiert Jan dort selbst (Anleitung folgt hier).
2. Kleine Probe des Datensatzes (ein ZIP auf dem Mac, wenige Bilder samt Annotationen auf den Server), damit
   datensatz.py das Box-Format an echten Dateien prüft. Download nur nach Jans Okay.
3. datensatz.py bauen: Umwandlung ins YOLO-Format, Prüfungen, Aufteilung, data.yaml (mit Tests).
4. auswertung.py bauen: results.csv und args.yaml eines Laufs lesen, Läufe vergleichen, Meldung an Jan.
5. Austausch Mac und Server festlegen (z. B. rsync oder scp nur für Annotationen, Läufe und Gewichte).
6. Zentrale kennt den Agenten noch nicht (AGENTEN in shared/telegram/logik.py), Bedarf steht in der Haupt-STATUS.md
   Punkt 40. Dienst systemd/fehlstellenscan.service fehlt noch, braucht Jans Okay.

## Gelernte Regeln
- (noch keine)
