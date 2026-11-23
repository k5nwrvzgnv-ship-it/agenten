# Plan: Werkbank für Daten, Fehler, Labeln und Training

Stand 23.11.2026. Reihenfolge von Jan bestätigt (23.11.2026). Phase 0 gebaut. Phase 1: Python 3.13 und fiftyone
auf dem Mac freigegeben (Jan 23.11.2026), Ladeskript fertig, Installation steht aus. Phase 2 noch nicht freigegeben. Auftrag von Jan (23.11.2026): ein Programm mit Oberfläche statt Terminal, das
Training und Fine-Tuning bedienbar und die Materie verständlicher macht, und in dem man den Stil der Masken
einstellen kann.

Antworten von Jan (23.11.2026): Henri und Felix haben Windows und Mac (X-AnyLabeling passt). Felix misst am 27.11.
mit Messschieber, Äste dürfen dafür markiert werden. „Masken-Design“ heißt der Stil der Masken selbst (wie eng,
welche Form), nicht die Darstellung für Folien.

## Kern der Sache
Das Training selbst ist bei uns gelöst (ein Befehl, wenige Einstellungen zählen: imgsz, Epochen, Modellgröße,
mask_ratio). Engpass sind gute Labels und das Wissen, wo das Modell danebenliegt (siehe
docs/recherche-hardware-training.md und den Balken-Lauf: Fugen als Risse, übersehene Äste). Die Werkbank bildet
deshalb diese Schleife ab, Training ist der letzte Knopf darin:

    Daten ansehen -> Fehler finden -> gezielt labeln -> nachtrainieren -> gegen feste Messlatte prüfen

Maßstab ist nicht mAP allein, sondern was die Norm braucht: Fehler beim kleinsten Astdurchmesser in mm,
Trefferquote nach Astgröße, Fehlalarme je Meter Balken, später Sortierklasse.

## Aufteilung Mac / Server
- Mac (M4 Pro, 24 GB): Werkbank. Training (ultralytics, vorhandene .venv mit Python 3.14), Vorhersagen,
  FiftyOne zum Ansehen und Auswerten (eigene .venv, siehe Pakete). Die Bilder liegen dort.
- Server: Logik ohne Netz und ohne Modell, getestet wie bisher (datensatz.py, masken.py, balken.py, neu
  auswertung.py). Archiv der Ergebnisse in data/laeufe/, Rüdiger liest sie. Kein FiftyOne auf dem Server
  (7,8 GB RAM ohne Swap, FiftyOne bringt eine eigene MongoDB mit).
- Henri und Felix: labeln auf ihren eigenen Rechnern (Phase 2), Dateien kommen über Jan zurück.

## Phase 0: vor dem 27.11. (ohne Installation)
Eilig, weil der Termin bei Felix die einzige Gelegenheit für Messwerte am echten Holz ist.
1. Messprotokoll für Felix' Balken (docs/messprotokoll-27-11.md): je Ast Lage in mm, kleinster und größter
   Durchmesser mit Messschieber, einige Äste von einer zweiten Person verdeckt nachgemessen (wie genau messen
   Menschen?). Ziel: 10 bis 20 Äste auf 2 bis 3 Balken. Diese Balken werden Test, nie Training.
2. auswertung.py (Server, numpy/Pillow/opencv wie masken.py, mit Tests): aus Markierung und Vorhersage
   (YOLO-seg-Textdateien) je Bild
   die Zuordnung Objekt zu Objekt (IoU der Masken), daraus übersehen / Fehlalarm / Klasse vertauscht, Trefferquote
   nach Größenklassen in mm, und der mm-Vergleich gegen eine Messtabelle (mittlere Abweichung, Streuung,
   Bland-Altman-Grenzen), Bootstrap-Intervalle. Läuft auch ohne FiftyOne und bleibt die Referenz.
3. Entwurf Labelrichtlinie (docs/labelrichtlinie.md): Klassen für Altholz (Kodytek-Nummern 0-9 bleiben, neue
   ab 10, damit das Kodytek-Modell weiter lernen kann) und vor allem der Stil der Masken: wie eng, welche Form je
   Klasse, berührende Objekte, Bildrand, Unsicherheit. Henri und Felix lesen gegen.

Fertig: Messprotokoll gedruckt am 27.11. dabei; auswertung.py grün in pruefen.sh und an kodytek-seg1-n1280 (val)
gegen die ultralytics-Zahlen geprüft (Trefferquote je Klasse muss in der Nähe liegen); Richtlinie gelesen.

## Phase 1: Fehler ansehen mit FiftyOne (Mac)
FiftyOne (Voxel51, Apache 2.0) ist eine lokale Oberfläche im Browser für Bilddaten mit Labels und Vorhersagen.
Laut Doku kann es ultralytics-Modelle direkt auf einen Datensatz anwenden (auch Seg), Vorhersagen mit Masken
auswerten (evaluate_detections mit use_masks=True), verdächtige Labels finden (compute_mistakenness), seltene und
doppelte Bilder (compute_uniqueness) und eine Karte aller Bilder nach Ähnlichkeit zeigen, in der man Gruppen
markiert (compute_visualization).
1. Skript werkbank_laden.py (Mac): kodytek-seg-1 val (2.026 Bilder) mit Markierung laden, kodytek-seg1-n1280
   anwenden, auswerten. Dazu die 114 Balken-Kacheln von Felix ohne Markierung.
2. Gespeicherte Ansichten: übersehene Äste nach Größe, Fehlalarme je Klasse, live/dead vertauscht,
   verdächtigste Labels, Kacheln mit Fund auf einer Fuge.
3. Zum Verstehen, mit unseren Bildern: Konfidenzschwelle verschieben und sehen, welche Funde kommen und gehen;
   ein Ast bei imgsz 640 / 1280 / voll; was die Augmentierung (Mosaik, Farbe, Spiegeln) aus einem Brettbild
   macht; Riss mit Maske in 1/4-Auflösung gegen Original. Erst prüfen, was FiftyOne mitbringt, eigene Ansichten
   nur für den Rest.
4. Maskenstil einstellen und seine Folgen sehen: Kodytek-Masken schrittweise enger und weiter machen (Erosion
   und Dilatation in mm), daneben, wie sich der gemessene Astdurchmesser und die Übereinstimmung mit dem Modell
   ändern. Später dasselbe mit unseren eng gezeichneten Masken. So wird der Stil eine begründete Entscheidung.
- Code, der fiftyone oder ultralytics importiert, liegt in einem Unterordner mac/ (der Gerüst-Test verbietet
  diese Pakete in den Modulen des Agenten, Tests auf dem Server laden sie nie).

Fertig: Jan findet in der Oberfläche ohne Terminal die zehn schlimmsten Fehler auf val und die Fugen-Fehlalarme;
Zahlen stimmen mit auswertung.py überein (zweite, unabhängige Rechnung).

## Phase 2: Labeln (nach dem 27.11.)
Vorschlag X-AnyLabeling: Programm für den eigenen Rechner (Windows, Linux, macOS), Masken per Klick mit SAM 2,
Vorlabel mit unserem YOLO-Seg-Modell, Export im YOLO-Format. Kein Server nötig, Henri und Felix brauchen kein
Konto. SAM läuft dort über onnxruntime auf der CPU (auf dem Mac keine GPU).
1. 20 Altholzbilder labeln alle drei unabhängig nach der Richtlinie, auswertung.py rechnet die Übereinstimmung
   (IoU zwischen uns). Das ist die Obergrenze, die kein Modell sinnvoll überbieten kann, und zeigt, wo die
   Richtlinie unklar ist.
2. Danach Bilder verteilen, Reihenfolge aus Phase 1: zuerst Bilder, bei denen das Modell unsicher ist, und
   solche aus Bereichen der Ähnlichkeitskarte, die noch fehlen.
3. Import in unser Format (masken.py oder eigenes Modul, mit Tests), Aufteilung nach Balken wie bei Kodytek,
   Test-Teil sofort einfrieren. Test-Teil labeln Henri oder Felix, nicht Jan.

Fertig: Henri oder Felix labeln 20 Bilder ohne Hilfe; Übereinstimmung gemessen; Altholz-Datensatz gebaut und von
ultralytics gelesen.

## Phase 3: Training per Knopf (Mac)
Erst wenn die Schleife einmal von Hand gelaufen ist. Kleine lokale Oberfläche, die `yolo segment train` mit den
wenigen wichtigen Einstellungen startet (Startmodell kodytek-seg1 oder yolo11n-seg, imgsz, Epochen, mask_ratio),
jeden Lauf mit manifest.json des Datensatzes verknüpft, Läufe nebeneinander zeigt und den Test-Teil gesperrt
hält. Umsetzung offen (FiftyOne-Plugin oder eigene kleine Seite); entscheiden nach Phase 1, je nachdem wie gut
FiftyOne sich erweitern lässt.

Fertig: Henri oder Felix starten ein Fine-Tuning ohne Hilfe und finden danach, was sich verbessert hat.

## Messlatte (außer Jan und Claude)
- Messschieber gegen Modell an Felix' Balken (Phase 0, Auswertung nach Phase 2).
- Altholz-Test-Teil, gelabelt von Henri oder Felix; Übereinstimmung zwischen uns als Obergrenze.
- Kodytek-Test-Teil (eingefroren) als feste Latte für alle Kodytek-Läufe, nur einmal je Modell.
- Später: Prof. Böhme oder ein Sortierer sortiert dieselben Balken nach DIN 4074, Vergleich der Klassen.

## Pakete zum Freigeben (Stand Recherche 23.11.2026, Versionen vor Installation auf PyPI prüfen)
- Phase 0: keine (numpy ist auf dem Server da).
- Phase 1, nur Mac: `fiftyone` in eigener .venv (~/fehlstellenscan/.venv-werkbank). FiftyOne verlangt laut Doku
  und PyPI Python 3.10 bis 3.13; unsere Mac-.venv hat 3.14, also zusätzlich Python 3.13 von python.org. Dazu
  ultralytics in dieser .venv (für apply_model), evtl. umap-learn für die Ähnlichkeitskarte.
- Phase 2, Rechner von Jan, Henri, Felix: `x-anylabeling-cvhub[cpu]`, laut Doku Python 3.10 bis 3.12, also eigene
  Umgebung mit 3.12. Für macOS 15 ist ein Qt-Problem gemeldet, vorher an Jans Mac ausprobieren.

## Verworfen (vorerst)
- Ultralytics HUB: Daten gingen in deren Cloud; wir haben sync=False bewusst gesetzt.
- CVAT: braucht Docker, auf dem Server ohne root nicht möglich, auf dem Mac schwer für drei Leute.
- Label Studio mit SAM 2: das SAM-2-Backend braucht laut Doku eine GPU und liefert Pinselmasken, die der
  YOLO-Export nicht kann. Wieder ansehen, wenn mehr Leute gleichzeitig an einem gemeinsamen Datensatz labeln.

## Offen
- Freigabe X-AnyLabeling (Phase 2). Für Ähnlichkeitskarte in Phase 1 vermutlich torch in .venv-werkbank.
- Normfrage für den Maskenstil: Was zählt nach DIN 4074 zum Ast (dunkler Rand, Rindenring)? Henri fragen.

## Quellen
- FiftyOne Installation (Python 3.10-3.13): https://docs.voxel51.com/installation/ und https://pypi.org/project/fiftyone/
- FiftyOne und Ultralytics: https://docs.voxel51.com/integrations/ultralytics.html
- Auswertung mit Masken (use_masks): https://docs.voxel51.com/api/fiftyone.utils.eval.detection.html
- Brain (mistakenness, uniqueness, visualization): https://docs.voxel51.com/brain.html,
  https://docs.voxel51.com/tutorials/detection_mistakes.html
- X-AnyLabeling: https://github.com/CVHub520/X-AnyLabeling, https://pypi.org/project/x-anylabeling-cvhub/,
  Qt-Problem macOS: https://github.com/CVHub520/X-AnyLabeling/issues/924
- Label Studio SAM 2 und YOLO-Export: https://labelstud.io/tutorials/segment_anything_2_image,
  https://community.labelstud.io/t/export-in-yolo-format-after-sam-annotation/426
