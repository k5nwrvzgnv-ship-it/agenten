# Plan: erster Test mit echtem Altholz (iPhone + Mac)

Stand 20.11.2026, Vorschlag von Jan, noch nicht entschieden. Für die Gruppe (Jan, Henri, Felix). Hintergrund und
Quellen: docs/recherche-hardware-training.md.

## Worum es geht
Bevor wir Geld in Kameras und Licht stecken, wollen wir billig klären: Kann YOLO die typischen Altholz-Fehler
überhaupt lernen, und kommen wir bei Ästen und Bohrlöchern grob dahin, wo das Startup (Dataspree) steht?
Dafür: ein paar hundert iPhone-Fotos von Altholzbalken bei Felix auf der Arbeit, selbst labeln, auf Jans Mac
(M4 Pro) trainieren.

## Warum das reicht und warum es sich lohnt
- Laut Recherche ist nicht die Rechenleistung der Engpass, sondern gute Labels. Training mit ein paar hundert
  Bildern dauert auf dem Mac Stunden, nicht Tage.
- Unser Kodytek-Lauf (16.000 Bilder, mAP50 0,75) liegt auf dem Niveau veröffentlichter Arbeiten mit rund
  3.500 Bildern. Mehr vom Gleichen bringt wenig, eigene Altholzbilder bringen viel.
- Einen öffentlichen Altholz-Datensatz gibt es nach unserer Recherche nicht. Ein eigener, sauber gelabelter
  Datensatz ist schon für sich ein Ergebnis und ein Argument für die Bewerbung.
- Die HNEE hat mit WIn-Altholz (FNR) schon einen NIR-Handscanner für Altholzkategorien gebaut. Unser Scanner
  würde die Schäden ergänzen. Guter Anknüpfungspunkt.

## Was der Test zeigt und was nicht
- Zeigt: welche Klassen lernbar sind, welche schwer, wie lange Labeln pro Bild dauert, grober Vergleich mit
  Dataspree bei Ästen und Bohrlöchern.
- Zeigt nicht: Güte mit Industriekamera im Durchlauf (andere Kamera und anderes Licht kosten Güte, wie viel ist
  offen), Messgenauigkeit, Tempo. Verdeckte Nägel und innere Fäule sieht keine Kamera.

## Fotos (Felix' Arbeit, Erlaubnis vorher einholen)
1. Vielfalt vor Menge: lieber 40 verschiedene Balken mit je etwa 8 Bildern als 300 Bilder von fünf Balken.
   Alle Seiten, auch verschmutzte und kaputte Stücke.
2. Immer gleich: Stativ, senkrecht, fester Abstand, je Bild etwa 30-40 cm Balken mit etwas Überlappung.
   Kein Nachtmodus, kein HDR, Belichtung und Weißabgleich fest (z. B. App Halide).
3. Licht: zwei LED-Strahler mit Diffusor, möglichst ohne Sonne. Ein Teil zusätzlich mit flachem Seitenlicht für
   Risse und Relief.
4. Zollstock und Graukarte im Bild.
5. Jeder Balken bekommt eine Nummer (Zettel im ersten Bild).

## Labeln
- Zuerst eine Seite Klassen-Leitfaden: je Klasse ein Beispielbild und die Grenze (ab wann ist es ein Riss?).
  Vorschlag Klassen: Ast, Bohrloch, Nagel/Schraube, Nagelloch, Riss, Farbe/Beschichtung, Fäule/Verfärbung,
  Insektenfraß, alte Verbindung (Zapfenloch, Kerve), Verschmutzung. Gemeinsam festlegen.
- Erst 50 Bilder labeln und die Zeit messen, dann hochrechnen und aufteilen. 20 Bilder doppelt labeln, um zu
  sehen, wie einig wir uns sind.
- Werkzeug: X-AnyLabeling mit SAM-Vorschlägen.

## Training (Jan, Mac)
- Aufteilung nach Balken, nicht nach Bild, sonst sieht das Ergebnis besser aus als es ist.
- Bilder in Kacheln schneiden statt verkleinern (sonst verschwinden Nagellöcher).
- Vergleich: Start vom Kodytek-Modell gegen Standardmodell, yolo11n gegen yolo11s.
- Erfolgskriterium vorher festlegen, z. B. Anteil gefundener Bohrlöcher und Nägel im Prüfteil. Klassen mit
  unter etwa 50 Beispielen werden kaum etwas Brauchbares ergeben (Schätzung).

## Aufwand (Schätzung)
- 1 Tag Fotos
- 2-5 Personentage Labeln, je nachdem wie viele Fehler pro Bild es gibt
- 1-2 Tage Datensatz und Training

## Offen
- Wann und wie fotografieren bei Felix, Erlaubnis.
- Wer labelt was.
- Klassenliste und Erfolgskriterium.
