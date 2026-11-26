# Vorlabeln per Modell (26.11.2026)

Auftrag: Vorlabel für ganze Balken oder einzelne Fotos per Modell, gerechnet auf Jans Mac, Ergebnis als offene
Labels auf dem Server. Kein torch auf dem Server, keine neuen Pakete.

## Weg der Daten

```
Browser (Labeln)        Server (neurolign.meldro.de)            Mac (Tunnel-Eingang 8766)
POST /api/vorlabeln --> reicht durch (tunnel.py) ------------> Kette.vorlabeln_starten: Lauf anlegen, sofort Antwort
                                                                Faden: abgleich.sh runter (rsync über ssh, holt
                                                                Fotos und balken.json, wie vor dem Training)
                                                                je Balken: Teil prüfen (teile.json des Macs),
                                                                Zuschnitt (bilder.py schneiden), Kacheln 1280 px
                                                                (bilder.py kacheln), yolo segment predict als
                                                                eigener Prozess, Kacheln zurück aufs Foto
                                                                (vorlabeln.py, Bordmittel) -> Ergebnis im Speicher
GET /api/vorlabeln  --> holt Stand vom Mac <------------------- Stand: Modelle, Läufe, je Balken Status und
                        fertige Balken: einfuegen() in die       Ergebnis (nur bis abgeholt)
                        Labels des Servers (unter Kette.schloss)
                        POST /api/vorlabeln-ab --------------> Ergebnis dieses Balkens vergessen
                        Faden fragt alle 3 s, solange ein Lauf
                        offen ist (auch ohne offene Seite)
```

- Der Mac schreibt nie selbst auf den Server. Der Server holt ab und wendet die Regeln an, wo die gültigen Labels
  liegen. Wer zwischendurch speichert, bekommt den bekannten Konflikt („Inzwischen von vorlabel gespeichert“).
- Mac-Modus (Galerie, Labeln auf localhost): gleicher Lauf ohne Tunnel und ohne Abgleich, das Ergebnis geht sofort
  in die Labels auf dem Mac. `neurolign_abgleich.sh hoch` nimmt sie mit, solange der Server den Balken noch nicht labelt.
- Ein Lauf auf einmal; nicht während eines Trainings und umgekehrt (mps).

## Regeln (vorlabeln.einfuegen, rein, getestet)

- Bestätigte Objekte (`ok: true`) bleiben immer. Offene ohne Quelle (von Hand gezeichnet) bleiben auch.
- Offene Vorlabel (`ok: false`, mit `q`) werden durch die neue Vorhersage ersetzt.
- Neue Vorhersagen, die ein bleibendes Objekt überdecken (Schnitt mindestens halb so groß wie das kleinere), fallen weg.
- Jedes neue Objekt: `k` (Klassen-ID), `p`, `c` (Konfidenz), `q` (Modellname), `ok: false`.
- Balken in Prüfung oder Nur Test (teile.json des Macs) werden übersprungen (Status „gesperrt“), außer bewusst über ···.

## Modell (vorlabeln.modell_wahl)

- Kandidaten: runs/segment/altholz-N mit weights/best.pt und Ergebnis. Prüfzahl = Masken-mAP50-95 auf Altholz
  (zweite Prüfung, wenn gemischt trainiert, sonst die Gesamtzahl eines reinen Altholz-Laufs). Alte Läufe mit
  Prüfung auf Trainingsbildern zählen nicht. Beste Zahl gewinnt, bei Gleichstand der neuere.
- Sonst kodytek-seg1-n1280. Andere Läufe in runs/segment nur über ···.
- Klassen: Namen des Modells aus dem Lauf (aufnahmen/altholz-N.json bzw. data.yaml aus args.yaml) über den Schlüssel
  auf die feste ID in klassen.json. Unbekannte Namen fallen weg.

## Kacheln

Wie beim Training: Zuschnitt in Kacheln 1280 px mit mindestens 256 px Überlappung (bilder.raster). Ein Objekt zählt
nur in der Kachel, in deren Kern (bis zur Mitte der Überlappung) seine Boxmitte liegt, so entsteht es nicht doppelt.
