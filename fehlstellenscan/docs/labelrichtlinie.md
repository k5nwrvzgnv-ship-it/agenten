# Labelrichtlinie Altholz (Entwurf)

Stand 23.11.2026, Entwurf von Claude, nicht entschieden. Henri und Felix lesen gegen, dann legen wir sie zu dritt
fest. Gehört zu docs/plan-trainingswerkzeug.md (Phase 0) und docs/plan-erster-test-altholz.md.
Warum so genau: Das Modell lernt den Stil der Masken mit. Zeichnen wir weit, misst es später zu groß. Zeichnet
jede Person anders, lernt es Rauschen. Die Kodytek-Masken sind mit dem Pinsel großzügig gemalt, deshalb messen
Modelle daraus eher zu groß (siehe STATUS.md, Abschnitt masken.py).

## 1. Klassen
Nummern 0 bis 9 wie Kodytek, damit das Kodytek-Modell mit unseren Bildern weiterlernen kann (Fine-Tuning ohne
neue Zuordnung). Neue Klassen ab 10. Vorschlag, gemeinsam festlegen:

| Nr | Name im Datensatz | Bedeutung |
|---|---|---|
| 0 | live_knot | Ast lebend (verwachsen, hell, fest) |
| 1 | dead_knot | Ast tot (dunkel, oft mit Ring, lose oder nicht verwachsen) |
| 2 | knot_missing | Astloch (Ast herausgefallen) |
| 3 | knot_with_crack | Ast mit Riss |
| 4 | crack | Riss (Schwindriss, Trockenriss) |
| 5 | quartzity | wie Kodytek, auf Altholz vermutlich selten |
| 6 | resin | Harzgalle, Harzfluss |
| 7 | marrow | Mark |
| 8 | blue_stain | Bläue |
| 9 | overgrown | Überwallung |
| 10 | bohrloch | gebohrtes Loch, rund, scharfer Rand |
| 11 | metall | sichtbares Metall: Nagel, Schraube, Klammer, Beschlag |
| 12 | nagelloch | Loch von Nagel oder Schraube ohne Metall |
| 13 | farbe | Farbe, Lack, Beschichtung |
| 14 | faeule | Fäulnis, weiches oder stark verfärbtes Holz |
| 15 | insektenfrass | Fraßgänge, Ausfluglöcher |
| 16 | verbindung | alte Verbindung: Zapfenloch, Kerve, Blatt, Versatz |
| 17 | fuge | Klebefuge (nur BSH, KVH), sonst hält das Modell Fugen für Risse |

Live gegen tot ist schon bei Kodytek die häufigste Verwechslung. Wenn wir uns beim Labeln oft nicht einig sind,
fassen wir 0 und 1 zu „Ast“ zusammen (entscheiden nach den 20 doppelt gelabelten Bildern).

## 2. Stil der Masken
Grundsatz: eng am sichtbaren Rand. Die Maske deckt das Merkmal, nicht das Holz drumherum.

- Form: Polygon, kein Pinsel. Punkte so dicht, dass der Umriss nicht mehr als etwa 1 mm vom sichtbaren Rand
  abweicht. Mit SAM (Klick ins Merkmal) vorschlagen lassen, dann den Rand prüfen und korrigieren; SAM-Masken
  laufen gern ins dunkle Holz daneben aus.
- Äste: Grenze ist der Übergang Ast zu Holz. Dunkler Ring oder Rinde: offen, was die Norm zum Ast zählt (Henri
  fragen). Bis dahin ohne Ring zeichnen und in der Beschreibung „Ring“ eintragen.
- Risse: dünnes Polygon entlang des sichtbaren Spalts, Breite wie sichtbar, mindestens 2 Pixel (schmaler fällt bei
  der Umwandlung weg). Ein durchgehender Riss ist ein Objekt, auch wenn er sich verzweigt. Unterbrochen um mehr als
  etwa 10 mm: zwei Objekte.
- Flächen (Farbe, Fäule, Bläue): Umriss der Fläche, Inseln unter etwa 5 mm weglassen. Löcher in der Fläche nicht
  ausschneiden (die Umwandlung füllt sie ohnehin).
- Löcher (Astloch, Bohrloch, Nagelloch): Rand des Lochs, nicht der ausgefranste Bereich drumherum.
- Metall: nur das sichtbare Metall. Das Loch drumherum nicht extra.
- Fugen: dünnes Polygon über die ganze sichtbare Länge der Fuge.

## 3. Grenzfälle
- Berührende Objekte gleicher Klasse (zwei Äste nebeneinander): zwei Objekte, nicht eins. Kodytek hat hier oft
  ein Objekt, das stört beim Zählen und Messen.
- Merkmal am Bildrand abgeschnitten: bis zum Rand zeichnen. Das nächste Bild (Überlappung) zeigt es ganz.
- Ast mit Riss: Klasse 3 für den Ast, der Riss im Ast gehört dazu. Läuft der Riss weit ins Holz, zusätzlich ein
  Riss-Objekt für den Teil außerhalb.
- Unsicher (Klasse oder Rand): trotzdem zeichnen, in der Beschreibung „unsicher“. Die Auswertung zählt diese
  getrennt. Nicht weglassen: Weggelassenes lernt das Modell als Holz.
- Kreidenummern vom Messtermin: nicht labeln. Diese Balken sind ohnehin nur Test.
- Schmutz, Staub, Sägespuren: nicht labeln (kein Fehler im Holz).

## 4. Wie wir prüfen, ob die Richtlinie trägt
- 20 Bilder labeln alle drei unabhängig. auswertung.py vergleicht je Paar (IoU der Masken, Klasse gleich,
  Durchmesser in mm). Wo wir uns nicht einig sind, ist die Richtlinie unklar: Regel hier nachschärfen.
- Die Abweichung zwischen uns ist die Grenze, die das Modell erreichen kann. Mehr verlangen wir nicht.
- Stil an Zahlen festmachen: Kodytek-Masken enger und weiter machen und sehen, wie sich Durchmesser und
  Modellgüte ändern (Werkbank, Phase 1).

## 5. Werkzeug und Ablage (Vorschlag)
X-AnyLabeling auf dem eigenen Rechner (Windows oder Mac), Export als YOLO-Segmentierung, Dateien je Balken an Jan.
Klassenliste als Datei, damit alle dieselben Nummern haben (kommt mit der Installationsanleitung).
