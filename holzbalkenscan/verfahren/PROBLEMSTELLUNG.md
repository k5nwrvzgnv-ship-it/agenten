# Problemstellung: maßhaltige Panoramabilder von Gebrauchtholz-Bauteilen

**Stand 2026-11-05.** Dieses Dokument ist für eine externe Zweiteinschätzung
geschrieben und setzt keine Vorkenntnis des Projekts voraus. Alle genannten
Zahlen sind gemessen, nicht geschätzt; wo etwas geschätzt ist, steht es dabei.

---

## 1 Worum es geht

In einem Forschungsprojekt zur **visuellen Sortierung von Gebrauchtholz** sollen
Bauteile (Brettschichtholz und Vollholz, Träger und Balken) wiederverwendet
werden. Dafür müssen sie in Sortierklassen eingeordnet werden, und das verlangt,
Merkmale zu **messen**: Äste, mechanische Beschädigungen, Risse — Lage, Länge,
Breite.

Das soll nicht am Bauteil geschehen, sondern am Bildschirm. Der Ablauf:

1. Ein Mitarbeiter fotografiert eine Bauteilseite mit dem Smartphone in einer
   Reihe überlappender Aufnahmen, aus der Hand.
2. Ein Programm setzt die Reihe zu **einem** Bild dieser Seite zusammen.
3. Am Laptop werden die Merkmale im Bild vermessen.

Tiefenabhängige Befunde (z. B. Risstiefe) werden weiterhin am Bauteil gemessen.

### Zielgrößen

| Größe | Anforderung |
|---|---|
| **Maßtreue lokal**, am einzelnen Merkmal | **±1 mm** (z. B. Astdurchmesser 30 mm) |
| **Maßtreue global**, Position eines Befunds auf dem Bauteil | **±5 bis ±10 mm** |
| **Farbtreue** | Farben müssen zwischen Bauteilen vergleichbar sein (Vergrauung, Verfärbung sind Sortiermerkmale) |
| Durchsatz | Mitarbeiter sollen die Reihe in wenigen Minuten aufnehmen |

Maßtreue und Farbtreue sind gleichrangig die beiden wichtigsten Parameter.

#### Was daraus folgt — die Anforderung zerfällt in zwei verschiedene Probleme

Das ist für die Bewertung der Probleme in Abschnitt 5 entscheidend, weil die
beiden Zahlen **an verschiedenen Größen hängen**.

**Quer** kommt der Maßstab aus der bekannten Flächenhöhe geteilt durch die im
Bild gemessene Bandbreite. Für ±1 mm an einem 30-mm-Ast muss dieser Maßstab
auf **3,3 %** stimmen:

| Fehlerquelle | Beitrag | an 30 mm | Urteil |
|---|---|---|---|
| **Mehrdeutigkeit der Bandbreite** (P1) | 14 % | 4,20 mm | **fällt durch** |
| **Zulauf des Bauteils** (P3) | 5 % | 1,50 mm | **fällt durch** |
| Unsicherheit der Flächenhöhe | 1,5 % | 0,45 mm | hält |
| Kantenfindung in Pixeln | 0,1 % | 0,03 mm | hält |

**Längs** kommt der Maßstab aus der bekannten Gesamtlänge. Die Enden sind durch
die Einpassung exakt; maßgeblich ist die **Drift dazwischen**, heute rund
0,5 % (gemessen: dieselbe Stelle lag zwischen zwei Codefassungen 35 mm
auseinander, bei außen exakt gleicher Solllänge):

| Bauteillänge | Abweichung in der Mitte bei 0,5 % | nötige Driftgrenze für ±10 mm |
|---|---|---|
| 1610 mm | 4,0 mm — hält | 1,24 % |
| 4000 mm | 10,0 mm — gerade noch | 0,50 % |
| 6485 mm | 16,2 mm — **fällt durch** | 0,31 % |
| 12 000 mm | 30,0 mm — **fällt durch** | **0,17 %** |

**Drei Schlussfolgerungen:**

1. Der **Quermaßstab** ist für die lokale Anforderung bindend und heute um den
   Faktor vier zu ungenau. P1 und P3 sind damit beide erstrangig — P3 ist
   **kein kosmetisches Problem**, wie es auf den ersten Blick wirkt.
2. Die **Längsdrift** ist für die globale Anforderung bindend. Bis etwa 4 m
   Bauteillänge reicht der heutige Stand; bei 6,5 m und erst recht bei 12 m
   nicht mehr. Da Bauteile bis 12 m vorkommen, ist das ein echtes Problem.
3. Die **Unsicherheit der Flächenhöhe**, die das Konzeptpapier (§4.6) als
   dominierenden Fehler bezeichnet, ist es für die lokale Anforderung
   **nicht**: 0,45 von 1 mm zulässig. Sie wird erst dominierend, wenn P1 und
   P3 gelöst sind.

Ein Ast **längs** gemessen ist unkritisch: 0,5 % von 30 mm sind 0,15 mm.

---

## 2 Randbedingungen

**Aufnahme**
- iPhone, App ProCamera, alles manuell einstellbar. JPEG, 8064 × 6048 Px
  (48 MP), EXIF-Brennweite 26 mm KB → Brennweite ≈ 5824 Px.
- Aus der Hand, im laufenden Hallenbetrieb. Aufnahmeabstand typisch
  350–650 mm, Schwankung ±9 %.
- **Mehrere wechselnde Mitarbeiter** werden fotografieren. Es kann nicht
  angenommen werden, dass sich alle optimal an Vorgaben halten. Das Verfahren
  muss robust sein, nicht optimal.

**Bauteile**
- Immer rechteckige Querschnitte, BSH oder Vollholz (VH).
- Bis **12 m** lang. Jedes Bauteil unterscheidet sich in Farbe, Maserung,
  Merkmalen, Vergrauung.
- Liegen **immer auf zwei Böcken** — das ist unvermeidbar.
- Vollholzbauteile sind gesägt: Kanten weder exakt gerade noch exakt parallel.

**Umgebung**
- Echte Halle: Pflasterboden, Container, Regale, Hallendecke mit Pfetten und
  Leuchtstoffröhren (lange Linien parallel zum Bauteil).
- Ein schwarzer Hintergrundvorhang ist wegen der 12 m Länge praktisch
  ausgeschlossen.

**Software**
- Harte Vorgabe des Auftraggebers: **kein Import von Fremdcode oder
  Fremdsoftware.** Erlaubt sind ausschließlich **Pillow und numpy**.
  Kein OpenCV, kein scikit-image, kein SIFT/ORB/AKAZE, kein scipy, kein
  Deep Learning, keine fertigen Stitcher (Hugin, PTGui, OpenPano).
  *Diese Vorgabe steht; sie darf aber in der Zweiteinschätzung ausdrücklich
  in Frage gestellt werden — siehe Frage F7.*

---

## 3 Wie das Verfahren heute arbeitet

Zwei Programme, beide reines numpy/Pillow:

- `zusammensetzen2.py` (~2300 Zeilen) — setzt zusammen.
- `pruefen.py` (~1300 Zeilen) — beurteilt eine Fotoreihe **vor** dem
  Zusammensetzen und sagt vorher, ob sie taugt.

### Begriffe

- **Band** — der Querstreifen im Rohbild, den das Verfahren für das Bauteil
  hält, begrenzt von Ober- und Unterkante. **Seine Breite in Pixeln ist der
  Maßstab**, denn sie entspricht der bekannten Flächenhöhe in Millimetern.
  Ein um 10 % zu breites Band macht alle Maße 10 % zu klein.
- **Station** — eine von 36 Stellen längs des Bildes, an denen das Kantenpaar
  quer gesucht wird.
- **Arbeitskoordinaten** — x quer zum Bauteil, y längs.

### Ablauf

1. **Achse** bestimmen: läuft das Bauteil im Rohbild längs der Zeilen oder der
   Spalten? Entschieden über die Beständigkeit der gefundenen Bandbreite.
2. **Band finden.** Zwei unabhängige Wege:
   - *frei*: Suche im ganzen Bild nach dem Streifen, der sich nach **beiden**
     Seiten in dieselbe Richtung abhebt (Kriterium über drei Querprofile:
     Helligkeit, Sättigung, Wärme R−B; bewertet mit dem *kleineren* der beiden
     Unterschiede).
   - *Parallaxe*: Das Bauteil ist das nächste große Objekt vor der Kamera und
     wandert zwischen zwei Aufnahmen weiter durchs Bild als der Hintergrund.
3. **Kanten je Bild**: Kantenpaar je Station, Ausgleichsgerade, zwei
   Durchgänge (grobes Fenster → enges Fenster, das der Geraden folgt).
4. **Zuordnung** benachbarter Aufnahmen auf entzerrten Streifen (3 Px/mm),
   Kachel-Kreuzkorrelation (NCC über FFT), Kachelwahl nach Shi-Tomasi,
   RANSAC-Affine.
5. **Bündelausgleichung** (Levenberg-Marquardt, numerische Jacobi-Matrix,
   Huber-Gewichtung, alles in numpy): je Bild Bilddrehung, Längsverjüngung und
   Lage; **Querverkippung und Brennweite gemeinsam für die Reihe**.
   Residuen: Kantenstationen gegen die Flächenhöhe, Punktpaare, Gesamtlänge.
6. **Zweiter Zuordnungsdurchgang** im Modellrahmen.
7. **Photometrie**: je Bild Faktor pro Farbkanal **plus ein gemeinsames
   Lichtfeld über dem Bild** (fängt den mitwandernden Schatten des Fotografen).
8. **Balkenenden** über die Faserrichtung, darauf der Längsmaßstab.
9. **Naht statt Mischung**: je Ausgabespalte genau ein Quellbild, Schnitt dort,
   wo die Bilder übereinstimmen, 24 mm Überblendung.
10. Einmal entzerren, direkt vom Originalpixel ins Endraster.

---

## 4 Was funktioniert

Damit die Zweiteinschätzung nicht am Gelösten arbeitet:

- **Geisterfragmente sind weg.** Ursache war eine Zweibandmischung (Tiefpass
  über bis zu drei Bilder gemittelt, Hochpass hart aus einem). Ersetzt durch
  Nahtwahl statt Mischung. Querversatz an den Nähten heute 0,09–0,21 mm im
  Median.
- **Photometrie**: Ohne das gemeinsame Lichtfeld liefen die Helligkeitsfaktoren
  über die Reihe von 0,82 auf 1,47 davon, bei real ±7 %. Mit Lichtfeld stabil.
- **Faserrichtung als Materialmerkmal** trägt: gewachsenes Holz hat fast nur
  Struktur quer zur Faser. Gemessener Quotient quer/längs: Balken 2,2–3,5;
  quer liegende Kanthölzer 1,26; Pflaster 1,49; Zollstock 0,62. Damit werden
  die Balkenenden zuverlässig gefunden, und es ist das einzige Merkmal, das
  für BSH **und** Vollholz gleich gilt.
- **Grundsatz der Merkmalswahl**: Es darf nichts gemessen werden, was die
  Bauteile *voneinander* unterscheidet. Farbe, Helligkeit und Sättigung
  wechseln von Bauteil zu Bauteil; Geometrie und Faserrichtung nicht.

### Datenlage: fünf Reihen mit bekanntem Ausgang

| | 261019 A | 261019 B | 261019 C | 261022 V1 | 261022 V2 |
|---|---|---|---|---|---|
| Bauteil | BSH 6485 × 230 | BSH, Schmalseite 120 | BSH 6485 × 230 | VH 1610 × 225 | VH 1610 × 225 |
| Aufnahmen | 26 | 22 | 30 | 7 | 9 |
| Bauteilanteil am Bild | 27 % | **11 %** | 27 % | 58 % | 39 % |
| Auflösung | 9,15 Px/mm | 9,67 | 8,59 | 16,71 | 15,68 |
| Kantenkontrast K1/K2 (Graustufen) | 88 / 62 | 47 / 66 | **50 / 38** | 55 / 41 | 38 / 66 |
| Punktpaare je Naht | **51,9** | 7,8 | 6,1 | — | — |
| abgehängte Aufnahmen | **0** | 9 | 13 | 2 | 2 |
| **Ausgang** | gelingt, Nahtversatz 0,09 mm | **fällt auseinander** | **fällt auseinander** | **fällt auseinander** | gelingt, 0,21 mm |

Die drei Fehlschläge haben **drei verschiedene Ursachen**: B zu wenig
Bildfläche, C kein Kantenkontrast, V1 ein Band, das die Auflager einschließt.

---

## 5 Die offenen Probleme

### P1 — Der Maßstab ist mehrdeutig *(das schwerwiegendste Problem)*

**Befund.** Die beiden Wege zum Band liefern unterschiedliche Maßstäbe, und
keiner ist zuverlässig:

| Reihe | frei | Parallaxe | Abweichung |
|---|---|---|---|
| 261019 A | 9,04 Px/mm | 9,15 | 1,1 % |
| 261019 B | 11,47 | 9,67 | 17 % |
| 261019 C | 6,75 | 8,59 | **24 %** |
| 261022 V1 | **1,60** (völlig daneben) | 16,71 | gefiltert |
| 261022 V2 | 15,64 | 13,69 | **13,8 %** |

Eine dritte, unabhängige Probe bei V2 — EXIF-Brennweite 5824 Px geteilt durch
den ausgeglichenen Aufnahmeabstand 389 mm — ergibt **14,97 Px/mm**. Die
Wahrheit liegt also **zwischen** den beiden Kandidaten; *keiner der beiden Wege
trifft sie*.

**Dahinter steckt eine Entartung.** Aus zwei parallelen Kanten im bekannten
Abstand und Aufnahmen von vorn folgt der **Längsmaßstab nicht**: Verkippung um
die Längsachse und Aufnahmeabstand lassen sich gegeneinander tauschen, ohne
dass sich das Bild merklich ändert. Gemessen: eine Ausgleichung mit freier Pose
je Bild endete bei **76 Grad Verkippung und 30 mm Aufnahmeabstand** und passte
zu allen Punktpaaren genauso gut wie die richtige Lösung. Bei Reihe B trat die
Entartung real ein: 73 Grad bei 70 mm Aufnahmeabstand.

**Bisher:** Querverkippung ist *ein globaler Parameter* für die ganze Reihe
(nicht je Bild), Brennweite fest, Längsmaßstab aus der bekannten Gesamtlänge.
Damit ist die **Länge Eingangsgröße, nicht Probe**.

**Offen:**
- Eine dritte Bandbestimmung aus Brennweite und Aufnahmeabstand, die den
  Streit entscheiden könnte, statt ihn nur zu melden.
- Ein Prior auf die Querverkippung (nahe 0, σ 15–20°), um die Entartung
  physikalisch zu sperren. 73° bei 70 mm ist unmöglich — der Code warnt, aber
  rechnet es aus.
- Eine wirklich unabhängige Längsprobe (siehe P6).

---

### P2 — Abgrenzung zum Hintergrund: die Kanten

Das gesamte Maßgerüst hängt an zwei Dingen: dass beide Längskanten gefunden
werden und dass sie das **Bauteil** begrenzen und nicht etwas daneben.

**P2a — Zu wenig Kantenkontrast.** Reihe C ist daran gescheitert: vergrauter
Balken vor grauem Pflaster, Unterkante 4,7 Graustufen Kontrast (Reihe A: 26).
Die Kette: schwache Kante → Kantengerade 79 statt 25 Px daneben → jedes Bild
falsch entzerrt → Zuordnung findet nichts → 13 von 30 Aufnahmen abgehängt.

Wichtig: Der **Median über die Reihe verdeckt das**. Reihe C hat im Median 50
und 38 Graustufen — unauffällig. Tatsächlich liegen die Aufnahmen 2291–2301 bei
4 bis 18 Graustufen und die Aufnahmen 2305–2314 bei 57 bis 120.

**P2b — Das Auflager ist auch Holz.** Reihe 261022 V1: Der Balken lag auf
Kanthölzern. Gemessen:

| | Helligkeit | Sättigung | Wärme R−B | Faser quer/längs |
|---|---|---|---|---|
| Balken | 103,8 | 64,0 | +64,0 | **2,16** |
| Spalt darunter | 142,4 | 57,3 | +56,8 | 1,77 |
| Kanthölzer | 144,7 | 51,7 | +51,5 | **1,26** |
| Pflaster | 155,5 | 30,4 | +29,4 | 1,49 |

Vom Balken zu den Kanthölzern ist der Sprung 12 Punkte, von den Kanthölzern zum
Pflaster 21 — die **stärkste waagerechte Grenze liegt unter den Auflagern**.
Der Bandsucher bewertet das falsche Band mit 4,16 und das wahre mit 2,50;
daraus werden 256 statt 223 mm, ein Maßstabsfehler von 15 %.

Gegenmaßnahme am Bauteil: Balken über die Böcke überstehen lassen — in V2
nachgewiesen wirksam. **Aber:** Bei 12 m langen Bauteilen auf zwei Böcken ist
nicht jede Stelle überstehend; die Böcke stehen zwangsläufig unter dem Bauteil.

Nebenbefund zur Farbe: Ein **neon-orange** gestrichenes Auflager macht es
*schlechter*. Das Bandkriterium verlangt, dass sich das Bauteil von beiden
Nachbarschaften in *dieselbe* Richtung unterscheidet. Gegen den hellen
Hintergrund ist der Balken dunkler und gesättigter; ein Auflager, das noch
dunkler und gesättigter ist (orange: Sättigung 95,5 gegen 61,5), kippt das
Vorzeichen, und der Kanal wird mit null gewertet.

**P2c — Hilfsmittel erzeugen falsche Kanten.** Ein Zollstock, der auf der
Bauteiloberkante liegt, erzeugt eine zweite starke Kante. Der Detektor springt
dann zwischen beiden. Gemessen an V1: Kantenpunkte verteilt über Zollstock und
Balkenoberkante statt auf einer Linie.

**Offen:**
- Robustheit, wenn **eine** Kante gut und die andere schwach ist: die starke
  genau vermessen, die Bandbreite aus der Reihe nehmen, die schwache daraus
  konstruieren und kennzeichnen. Noch nicht gebaut.
- Erkennung von Auflagern, die *unter* dem Bauteil liegen und aus Holz sind.
  Heute nur als **Prüfung** des fertigen Bandes gelöst (Faserhomogenität in
  15-mm-Querscheiben), nicht als Korrektur.

---

### P3 — Das Rechteckmodell passt nicht auf Vollholz

Das Verfahren nimmt an: **zwei gerade, parallele Längskanten im bekannten
Abstand**. Ein gesägter Gebrauchtholzbalken erfüllt das nicht.

Gemessen am Testbalken 261022 (Bandbreite je Längsstation, Maßstab je Bild aus
Brennweite/Aufnahmeabstand, also unabhängig vom Band):

| Längsposition | gemessene Höhe |
|---|---|
| −300 … −200 mm | 222 mm |
| 0 … 100 mm | 224 mm |
| 300 … 400 mm | 227 mm |
| 600 … 700 mm | 227 mm |
| 800 … 900 mm | 234 mm |
| 900 … 1000 mm | 237 mm |

Rund **10–15 mm Zulauf über die Länge** (Streuung der Einzelmessung ±10 mm; die
Richtung ist eindeutig, der Betrag grob). Die Nennhöhe 225 mm und die Nennlänge
1610 mm beziehen sich auf den **größtmöglichen** Abstand.

Die Ausgleichung zieht beide Kanten auf 0 und 225 mm. Im fertigen Streifen
bleiben davon 2,0 mm Streuung und 5,2 mm langwellige Abweichung übrig; bei BSH
(Reihe A) sind es 0,7 bzw. 2,3 mm.

**Folgen:**
- Der Zulauf von 10–15 mm auf 225 mm Nennhöhe ist eine Schwankung des
  **Quermaßstabs um rund 5 %** über die Bauteillänge. Nach der
  Fehleraufteilung in Abschnitt 1 sind davon an einem 30-mm-Ast 1,5 mm
  Messfehler — bei ±1 mm zulässig. **Dieses Problem ist damit erstrangig
  und nicht kosmetisch**, auch wenn es sich am fertigen Bild kaum zeigt.
- Inhalt nahe den Kanten wird zusätzlich quer **verschoben**, dort wo das
  Bauteil von der Nennhöhe abweicht — ein Positionsfehler obendrauf.
- Die schrägen **Endflächen** fielen aus der Leinwand, weil sie genau
  `LAENGE × HOEHE` groß war. Entschärft durch einen größeren Zeichen-Saum; der
  Nullpunkt und die Skala beziehen sich weiterhin auf das Sollrechteck.
- Die Textur in den untersten 4 mm fällt in 4 von 81 Abschnitten unter 55 % der
  Textur weiter innen — genau dort, wo das Modell die krumme Kante zurechtzieht.

**Vorschlag, noch nicht gebaut:** die Kanten weiterhin gerade, aber **nicht
parallel** annehmen — ein Trapez statt eines Rechtecks, ein zusätzlicher
Parameter für die Reihe. Zu klären ist, ob sich ein Bauteilzulauf von der
globalen Querverkippung **trennen** lässt. Ob das reicht, ist ebenfalls offen:
echte Krümmung und lokale Ausbrüche bildet auch ein Trapez nicht ab.

---

### P4 — Die Kette reißt

Die Aufnahmen bilden eine Kette: jede wird an ihre Nachbarn angeschlossen. Eine
einzelne unbrauchbare Aufnahme lässt sich überspringen (bei 65 % Überlappung
haben auch die Nachbarn beidseits noch gut 30 % gemeinsam). **Zwei
hintereinander trennen die Kette**, und alles dahinter lässt sich nicht mehr
anschließen.

Entscheidend ist die Ausbeute an Punktpaaren, und die hängt an der **Fläche**,
auf der sich zwei Aufnahmen wiederfinden können — also am Band:

| | Band im Bild | Punktpaare je Naht | abgehängt |
|---|---|---|---|
| Reihe A | 2170 Px | **51,9** | 0 von 26 |
| Reihe B | 1088 Px | 7,8 | 9 von 22 |
| Reihe C | 1976 Px | 6,1 | 13 von 30 |

Halbes Band, ein Siebtel der Punktpaare — **weit schneller als linear**. Reihe
C zeigt zugleich, dass ein breites Band allein nicht genügt: dort ist das Band
breit und die Ausbeute trotzdem klein, weil die Entzerrung an den
kontrastlosen Kanten scheitert.

**Offen:** Die Zuordnung arbeitet auf entzerrten Streifen; eine fehlerhafte
Entzerrung zerstört sie. Eine Zuordnung, die *vor* der Entzerrung trägt, wäre
robuster — mit den erlaubten Mitteln (reine Kreuzkorrelation, keine
rotations-/skaleninvarianten Deskriptoren) ist unklar wie.

---

### P5 — Farbtreue

Farbtreue ist eine der beiden Hauptanforderungen, und **alle fünf Reihen**
scheitern daran in gleicher Weise:

| Reihe | Farbdrift R/G, B/G | Helligkeitsdrift |
|---|---|---|
| A | 21 % / 30 % | 73 % |
| B | 20 % / 26 % | 29 % |
| C | 26 % / 30 % | 37 % |
| 261022 V2 | 19 % | 10 % |

Der Zusammenbau rechnet Kanalfaktoren je Bild und ein gemeinsames Lichtfeld
heraus, und maßlich stört das nicht (Reihe A setzt sich mit 21 % Farbdrift
sauber zusammen). Was bleibt, ist **Unsicherheit in der Farbe selbst**: Der
Streifen zeigt das Mittel der Reihe, nicht die wahre Farbe des Bauteils.

Ein Teil davon ist am Bauteil lösbar (Kelvinwert und Belichtung fest
einstellen). Offen bleibt: **Woran wird die Farbe absolut kalibriert?** Ohne
Referenz im Bild ist „die wahre Farbe" nicht definiert, und Vergrauungsgrade
verschiedener Bauteile sind dann nicht sauber vergleichbar.

---

### P6 — Es fehlt eine unabhängige Längsprobe

Weil der Längsmaßstab nicht aus der Geometrie folgt (P1), wird die bekannte
Bauteillänge als Maßnormal benutzt. Damit ist sie **Eingangsgröße und nicht
Probe** — ein Fehler im Längsmaßstab fällt nicht auf.

Nach der Fehleraufteilung in Abschnitt 1 entscheidet genau das über die
globale Anforderung: Die Einpassung auf die Gesamtlänge macht die **Enden**
exakt, sagt aber nichts über die Drift **dazwischen**. Heute liegt sie bei
rund 0,5 %; für ±10 mm in der Mitte eines 12-m-Bauteils sind 0,17 % nötig.
Eine Referenz **in der Bauteilmitte** würde genau den Term prüfen, der dort
anfällt — eine Referenz am Ende dagegen nicht, weil die Enden ohnehin
eingepasst sind.

Versuch mit einem Zollstock im Bild: Die 10-mm-Teilung lässt sich über
Autokorrelation messen. Bei 261022 V1 ergab das 16,40 gegen 16,68 Px/mm aus dem
Band, also +1,7 %. Drei Fallen, alle gemessen und abgestellt: JPEG-Blockartefakt
bei zu grober Lesung; zu langes Glättungsfenster lässt auch Pflaster mit Güte
0,7 durchgehen; ein einzelner Fund kann ein Pflaster sein.

**Die eigentliche Schwierigkeit ist nicht die Länge, sondern die Tiefe.** Bei
363 mm Aufnahmeabstand:

| Versatz der Referenz aus der Bauteilebene | Maßstabsfehler | auf 1610 mm |
|---|---|---|
| 3 mm | 0,83 % | 13 mm |
| 20 mm | 5,5 % | 89 mm |
| 50 mm | 13,8 % | 222 mm |

Der Maßstab muss also **flach auf der fotografierten Fläche** liegen — wo er
aber Oberfläche verdeckt, die vermessen werden soll.

Fehlerfortpflanzung der Referenzlänge (Marke im Bild auf ±2 Px lokalisierbar,
zwei Marken ±0,18 mm):

| Referenz | rel. Fehler | bei 1610 mm | bei 6485 mm | bei 12 m |
|---|---|---|---|---|
| 50 mm | 0,35 % | ±5,7 mm | ±23 mm | ±42 mm |
| 200 mm | 0,088 % | ±1,4 mm | ±5,7 mm | ±11 mm |
| 500 mm | 0,035 % | ±0,6 mm | ±2,3 mm | ±4,2 mm |
| Bauteillänge selbst | 0,03 % | — | ±2 mm | ±2 mm |

---

### P7 — Die Qualitätssicherung ist auf dünner Datenbasis kalibriert

`pruefen.py` sagt vor dem Zusammensetzen ein Urteil vorher (grün / gelb / rot,
getrennt nach Maßtreue und Farbtreue). Alle fünf bekannten Ausgänge stimmen
inzwischen — aber **zwei Vorhersagen waren vorher falsch**:

- Reihe B: **gelb** vorhergesagt, fiel auseinander. Ursache: der Zusammenhang
  zwischen Bandbreite und Punktpaarausbeute war unterschätzt.
- Reihe 261022 V2: **rot** vorhergesagt, setzte sich zusammen. Ursache: eine
  feste Schwelle von 8 mm für die Abweichung von der Kantengeraden, die für
  gesägtes Vollholz zu scharf ist.

Daraus die Regel: **Eine Aufnahme muss aus ihrer eigenen Reihe herausfallen,
nicht aus einer Tabelle.** Schwellen sind heute teils relativ zum Median der
Reihe. Mit fünf Reihen bleibt jede Schwelle trotzdem eine Schätzung — die rote
Schwelle für den Bauteilanteil (18 %) liegt z. B. ungemessen zwischen 11 %
(fällt auseinander) und 27 % (gelingt).

---

### P8 — Zwei strukturelle Fehler, die zeigen, wie fragil das Ganze ist

Beide gefunden und behoben, hier als Hinweis auf die Fehlerklasse:

1. **Der Achsentest suchte Bänder nur bis 48 % der Profillänge.** Sobald das
   Bauteil mehr als die Hälfte des Bildes füllte (nach der Empfehlung „näher
   heran" genau eingetreten: 60 %), fand die Suche auf der *richtigen* Achse nur
   noch Bruchstücke und wählte die falsche. Verräterisches Zeichen: die
   gemeldete Faserrichtung war 0,40 — genau der Kehrwert des richtigen Werts.
2. **Der Zeichen-Saum veränderte die Geometrie.** Die Suchstreifen der
   Zuordnung waren `HOEHE + 2 × SAUM` hoch, mit demselben `saum_mm`, das nur
   die Leinwand größer machen sollte. Mit 30 statt 5 mm fiel der Nahtversatz
   von 0,21 auf 0,61 mm und die belegte Länge von 1568 auf 1364 mm — ohne dass
   an der Reihe etwas anders war.

Daraus folgt eine allgemeine Frage: **Wie stellt man bei einem Verfahren mit so
vielen gekoppelten Schwellen sicher, dass eine Änderung an einer Stelle nicht
an anderer Stelle etwas kippt?** Es gibt heute keine Testsuite, nur fünf
Fotoreihen, die nach jeder Änderung von Hand durchgerechnet werden.

---

### P9 — Praktische Kleinigkeiten mit großer Wirkung

- **EXIF teilweise defekt**: In den Dateien der Reihen 261019 zeigen alle
  RATIONAL-Felder (Belichtungszeit, Blende, Brennweite, Verschlusszeit) auf
  dieselbe Stelle und liefern denselben Wert. In den Reihen 261022 ist die EXIF
  intakt. Belichtungskonstanz wird deshalb an der gemessenen Helligkeit
  geprüft, nicht an den Kameradaten.
- **Handyhaltung**: In den ersten drei Reihen lag der Bauteilquerschnitt auf der
  *langen* Bildachse. Um 90° gedreht: Bauteilanteil 27 → 36 %, erfasste Länge je
  Aufnahme 641 → 855 mm. Zweimal gewonnen, ohne einen Schritt zu gehen.
- **Rechenzeit**: `pruefen.py` rund 20 s für 20 Aufnahmen auf einem MacBook;
  `zusammensetzen2.py` einige Minuten. Für 12-m-Bauteile mit entsprechend vielen
  Aufnahmen ist die Skalierung ungeprüft.

---

## 6 Was bereits geprüft und **verworfen** wurde

Damit die Zweiteinschätzung nicht Wege vorschlägt, die schon gemessen
gescheitert sind:

| Ansatz | Warum verworfen |
|---|---|
| Farbe / Sättigung / Wärme als **Merkmal** zum Finden des Bauteils | Reihe C: die Hallendecke gewinnt. Varianten zwischen Bauteilen zu stark. |
| Schärfe / Hochpassenergie als Merkmal | Reihe C: versagt. |
| Faserrichtung quer durchs **ganze Rohbild** zum Finden | Pfetten und Leuchtröhren laufen parallel zum Bauteil. |
| Faserrichtung als **vierter Kanal in der Bandsuche** | Verschiebt 261022 nur von 115 auf 109 % des Solls und verschlechtert Reihe C. |
| Band an die Parallaxe **fesseln** (enges Fenster) | Die Parallaxe ist mal 4 % zu hoch, mal 12 % zu hoch, mal 2 % zu niedrig. |
| Faserhomogenität als **Auswahlkriterium** zwischen zwei Bandkandidaten | Erkennt „Band zu groß" zuverlässig, „Band zu klein" **grundsätzlich nicht** — ein zu schmales Band liegt ganz im Holz und ist perfekt homogen. Als beidseitige Prüfung (innen *und* Nachbarstreifen) trennt sie 8 von 8 Fällen richtig. |
| Längsmaßstab aus zwei parallelen Kanten | Mathematisch nicht bestimmbar (P1). |
| Balkenenden über „Kantenpaar hört auf" oder „innen Holz, außen Hintergrund" | Beides versagt; nur die Faserrichtung trägt. |
| Zweibandmischung an den Nähten | Erzeugte die Geisterfragmente. |
| Schwarzer Hintergrundvorhang | Bei 12 m praktisch ausgeschlossen. |
| Durchgehendes Bandmaß längs am Bauteil | Vom Auftraggeber als unpraktisch verworfen. |

---

## 7 Fragen an die Zweiteinschätzung

Nach Wichtigkeit geordnet.

**F0 — Stimmt die Fehleraufteilung?** *(siehe Abschnitt 1)* Die Anforderung
±1 mm lokal / ±5–10 mm global ist auf zwei getrennte Größen zurückgeführt: den
**Quermaßstab** (muss auf 3,3 % stimmen) und die **Längsdrift** (muss bei 12 m
unter 0,17 % bleiben). Ist diese Aufteilung vollständig? Übersehen ist
möglicherweise, dass ein Ast nahe der Bauteilkante zusätzlich von der
Kantenzurechtziehung (P3) verschoben wird, also einen Positions- *und* einen
Größenfehler bekommt.

**F1 — Maßstab.** Gibt es einen Weg, den Maßstab **ohne** die bekannte
Bauteillänge und ohne eine Referenz in der Bauteilebene zu bestimmen, der mit
Pillow/numpy umsetzbar ist? Sinnvoll erscheint die Kombination aus
EXIF-Brennweite und Aufnahmeabstand — aber der Abstand kommt selbst aus der
Ausgleichung, also aus dem Band. Lässt sich die Zirkularität brechen?

**F2 — Hintergrundabgrenzung.** Welches Merkmal trennt ein Holzbauteil von
einem Holzauflager direkt darunter, wenn das Auflager weder farblich noch in
der Helligkeit sicher abweicht? Die Parallaxe trennt sie nicht gut, weil die
Böcke fast in derselben Tiefe stehen. Faserrichtung trägt als Prüfung, aber
spaltenweise ist sie zu verrauscht, um Kanten zu setzen.

**F3 — Geometriemodell.** Ist das Trapezmodell (gerade, aber nicht parallele
Kanten) der richtige nächste Schritt, oder sollte das Modell die Kanten
freigeben und die bekannte Flächenhöhe nur noch als **mittlere** Nebenbedingung
führen? Letzteres ist ehrlicher, gibt aber die Versteifung auf, die die
Ausgleichung heute stabil hält.

**F4 — Entartung.** Ist ein Prior auf die Querverkippung (nahe 0, σ 15–20°)
der saubere Weg, oder gibt es eine Umparametrisierung, die die Entartung
zwischen Verkippung und Abstand strukturell beseitigt?

**F5 — Zuordnung.** Die Zuordnung arbeitet auf entzerrten Streifen und bricht
zusammen, wenn die Entzerrung falsch ist. Gibt es mit reiner Kreuzkorrelation
(ohne rotations-/skaleninvariante Deskriptoren) einen Weg, zuerst grob
zuzuordnen und daraus die Entzerrung zu bekommen, statt umgekehrt?

**F6 — Farbkalibrierung.** Wie lässt sich Farbtreue zwischen Bauteilen
absolut sichern, ohne eine Farbkarte ins Bild zu legen, die Oberfläche verdeckt?

**F7 — Die Fremdcode-Vorgabe.** Welche dieser Probleme sind **durch die
Beschränkung auf Pillow und numpy** verursacht und mit Standardwerkzeugen
(OpenCV, SIFT/AKAZE, COLMAP, Segmentierungsnetze) gelöst — und welche blieben
auch dort bestehen? Eine ehrliche Einschätzung dazu ist ausdrücklich erwünscht,
auch wenn sie gegen die Vorgabe spricht.

**F8 — Verifikation.** Wie würde man ein solches Verfahren absichern, wenn nur
fünf Fotoreihen mit bekanntem Ausgang vorliegen und jede neue Reihe einen halben
Tag Aufnahme kostet?

---

## 8 Anhang: Glossar

| Begriff | Bedeutung |
|---|---|
| **Band** | Querstreifen im Rohbild, den das Verfahren für das Bauteil hält; seine Breite ist der Maßstab |
| **Station** | eine von 36 Stellen längs des Bildes, an denen quer nach dem Kantenpaar gesucht wird |
| **Saum** | Rand aus echtem Hintergrund um das Bauteil herum in der fertigen Zeichnung |
| **Naht** | Stelle, an der im Ausgabebild von einer Quellaufnahme auf die nächste gewechselt wird |
| **Querversatz an der Naht** | wie weit der Bildinhalt beim Wechsel quer springt — das Hauptgütemaß |
| **Faserrichtung quer/längs** | Verhältnis der mittleren Betragsgradienten quer zu längs; im Holz 2–3,5 |
| **Verjüngung** | perspektivische Verschmälerung des Bandes über die Bildlänge |
| **BSH / VH** | Brettschichtholz (verleimt, gehobelt) / Vollholz (gesägt) |

**Dateien:** `zusammensetzen2.py` (Zusammenbau), `pruefen.py` (Vorab-Prüfung),
`kantenbild.py` (zeichnet die gefundenen Kantenpunkte zur Sichtkontrolle ins
Bild). Alles reines Python mit Pillow und numpy, deutschsprachig kommentiert,
mit den jeweiligen Messwerten als Begründung im Code.
