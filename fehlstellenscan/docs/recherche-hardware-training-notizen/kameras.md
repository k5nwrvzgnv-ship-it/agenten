# Kameras für einen optischen Altholz-Oberflächenscanner (YOLO) – Flächen-, Zeilen- und Smartphone-Kameras

Stand der Recherche: 20.11.2026. Preise sind Netto-Listenpreise aus Shop-Snapshots, sofern nicht anders vermerkt. Rechnungen (mm/px, Zeilenrate, Belichtung, Schärfentiefe) sind eigene Überschlagsrechnungen und stehen deshalb unter "Inferences". Begrenzte Recherchetiefe (ca. 15 Abfragen): Einige Shopseiten (Basler-Einzelseite, LMI) sperrten den automatischen Abruf, dort stammen die Zahlen aus Suchtreffer-Auszügen.

## 1. Benötigte Auflösung (mm/px), Bildfeld, Anzahl Kameras für 1 bzw. 4 Seiten

### Takeaway
Für Insektenlöcher von 1–2 mm und Nagelköpfe reichen etwa 0,1–0,2 mm/px. Für 10–30 cm Breite sind das 1.500–3.000 px quer zur Förderrichtung, also eine 2k-Zeilenkamera (grenzwertig) oder eine 4k-Zeilenkamera bzw. eine 5-MP-Flächenkamera je Seite. Für vier Seiten eines Balkens braucht man vier Kameras, alternativ zwei Kameras und Wenden.

### Cited Findings
- Der öffentliche Holzfehler-Datensatz der VŠB-TU Ostrava (Kodytek, Bodzas, Bilik 2021, 10 Fehlerklassen, ca. 20.000 Bilder, oft mit YOLO verwendet) wurde mit einer trilinearen Farbzeilenkamera aufgenommen: 3 × 4096 px, 66 kHz, 50-mm-Objektiv in 40 cm Abstand, 16,66 px/mm quer (also ca. 0,06 mm/px), Bilder aus Blöcken von 1.024 Zeilen. — [PMC9277195](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9277195/)
- Die Bildgröße wird widersprüchlich angegeben: 1024 × 4096 im Datenpaper, 2800 × 1024 im CFIS-YOLO-Paper, das mit 640 × 640 trainiert. — [PMC9277195](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9277195/); [CFIS-YOLO, arXiv 2504.11305](https://arxiv.org/pdf/2504.11305)
- Industriescanner prüfen alle vier Seiten: MiCROTEC Goldeneye "determines the overall quality of the boards on all four sides", WEINIG CombiScan "detects defects on up to 4 sides". — [MiCROTEC Goldeneye](https://www.microtec.com/en/products/goldeneye); [WEINIG Solid Scan 4000](https://www.weinig.com/en/solid-wood/scanner-systems/solid-scan-4000-series/)

### Inferences
- Faustregel Objekterkennung: Ein Fehler sollte im Bild mindestens 3–5 px groß sein (bei YOLO nach dem Herunterskalieren auf die Netzeingabe). 1 mm Loch → ≤ 0,2–0,33 mm/px. Empfehlung: 0,1–0,15 mm/px Aufnahme, damit beim Kacheln oder Herunterskalieren Reserve bleibt. Feine Risse sind oft schmaler als ein Pixel, werden aber über ihre Länge und ihren Kontrast sichtbar. Für Haarrisse sind 0,1 mm/px besser.
- Breite 300 mm: 0,15 mm/px = 2.000 px (2k-Zeile genau passend, ohne Rand), 0,1 mm/px = 3.000 px (4k-Zeile mit Rand), 4k bei 300 mm + Rand (ca. 340 mm) ≈ 0,083 mm/px.
- Flächenkamera 2448 × 2048 (5 MP): quer 2448 px über 340 mm ≈ 0,14 mm/px. 12-MP-Sensoren (ca. 4096 px) liegen bei ≈ 0,08 mm/px.
- Der VŠB-Datensatz mit ca. 0,06 mm/px ist feiner als nötig. Für Altholz (Schmutz, Farbe, Nägel) ist ein Aufnahmemaßstab von ca. 0,1 mm/px sinnvoll und kompatibel mit der Literatur.
- Seitenzahl: Bretter (Breitseiten 10–30 cm, Kanten 2–5 cm) brauchen 2 Kameras für die Breitseiten, und für die Kanten entweder 2 kleine Kameras (z. B. 1k/2k oder Flächenkamera) oder Spiegel. Balken (z. B. 16 × 16 cm) brauchen 4 gleichwertige Kameras. Günstige Forschungsvariante: 1–2 Kameras und Werkstück wenden (zwei bzw. vier Durchläufe), dabei die Seiten per Software zuordnen.
- Für den späteren BSH-Lamellenscanner vor der Kappsäge (Lamellen ca. 100–250 mm breit, oft gehobelt) reicht in der Regel die gleiche Auflösung. Meist zählen zwei Breitseiten, die Kanten sind weniger wichtig. Hier ist die Zeilenkamera der Standard (siehe Abschnitt 8).

### Gaps
- Keine Quelle mit einer begründeten Mindestauflösung speziell für Altholzfehler (Bohrlöcher, Schrauben, Insektenlöcher). Die Werte oben sind abgeleitet.
- Die Pixelauflösung der Farbkameras in MiCROTEC- und WEINIG-Scannern wird öffentlich nicht angegeben.

## 2. Vorschub, Belichtungszeit, Bewegungsunschärfe, Zeilenrate, Encoder, Rolling vs. Global Shutter

### Takeaway
Zeilenkamera: nötige Zeilenrate = Vorschub / Pixelgröße längs, bei 2 m/s und 0,1 mm also 20 kHz, bei 0,2 m/s 2 kHz. Das schafft jede aktuelle Einsteiger-Zeilenkamera (25–29 kHz). Flächenkamera: Bei 2 m/s ist für unter 0,5 px Unschärfe eine Belichtung von ca. 25–40 µs nötig, also Blitz-LED. Bei 0,2 m/s reichen ca. 250–375 µs. Rolling Shutter (Smartphone, Pi HQ) ist am bewegten Band ungeeignet, Global Shutter ist Pflicht.

### Cited Findings
- Rolling Shutter belichtet und liest die Zeilen nacheinander aus. Bewegte Objekte werden verzerrt, je nach Bildrate leicht bis stark. Die Belichtungszeit hat keinen Einfluss auf den Rolling-Shutter-Effekt, nur die Auslesegeschwindigkeit. Global Shutter verhindert ihn ganz, Blitzlicht mildert ihn. — [Basler Knowledge Base: CMOS rolling shutter](https://www.baslerweb.com/en/sales-support/knowledge-base/cmos-rolling-shutter-cameras)
- Eine Patentschrift zur Qualitätsprüfung hält fest, dass Rolling-Shutter-Sensoren oft verzerrte oder unscharfe Bilder liefern und für die Prüfung deshalb Global-Shutter-Sensoren bevorzugt werden. — [USPTO 11941799](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11941799)
- Der Raspberry-Pi-IMX296-Sensor (Global Shutter) erlaubt bei genug Licht Belichtungszeiten ab 30 µs. — [PetaPixel](https://petapixel.com/2023/03/09/raspberry-pis-new-global-shutter-camera-costs-just-50/)
- Zeilenraten der Einsteigermodelle: Basler racer 2 4k GigE r2L4096-29gm (Modellname = 29 kHz), Teledyne DALSA Linea Lite 2k Farbe 25 kHz (mit TurboDrive bis 50 kHz nachhaltig), Hikrobot MV-CL020-41GC 2k Farbe ca. 26 kHz. — [Basler Shop r2L4096-29gm](https://www.baslerweb.com/en/shop/r2l4096-29gm/); [Teledyne Linea Lite](https://www.teledynevisionsolutions.com/products/linea-lite/); [Polytec Hikrobot-Katalog](https://www.polytec.com/fileadmin/website/photonique-vision/pdf/hikrobot/Catalogue_HikRobot_2022.pdf)
- Industriescanner laufen viel schneller: MiCROTEC Goldeneye 301/302 bis 150 m/min (2,5 m/s), 501/502 bis 300 m/min, 801–806 bis 1200 m/min (20 m/s). — [MiCROTEC Goldeneye](https://www.microtec.com/en/products/goldeneye)

### Inferences
- Zeilenrate f = v / Δy (Δy = Pixel längs, gleich quer für quadratische Pixel):
  - 0,2 m/s: 0,1 mm → 2 kHz, 0,15 mm → 1,3 kHz
  - 1 m/s: 0,1 mm → 10 kHz, 0,15 mm → 6,7 kHz
  - 2 m/s: 0,1 mm → 20 kHz, 0,15 mm → 13,3 kHz
  - Goldeneye-302-Niveau (2,5 m/s) bei 0,1 mm → 25 kHz. Selbst industrielle Einstiegsgeschwindigkeit ist mit 25–29-kHz-Kameras erreichbar, die Grenze ist eher Licht (siehe unten) und Bandbreite (Abschnitt 4).
- Die Belichtungszeit je Zeile ist bei der Zeilenkamera höchstens 1/f (bei 20 kHz 50 µs). Das braucht sehr helle, gebündelte Linienbeleuchtung (LED-Linienlicht). Das ist der eigentliche Kostentreiber neben der Kamera.
- Encoder: Bei einer Zeilenkamera wird jede Zeile über einen Drehgeber am Förderband/an der Rolle ausgelöst (Zeilen-Trigger), sonst wird das Bild bei schwankendem Vorschub gestreckt oder gestaucht. Gängige Kameras (racer 2, Linea) haben Trigger-Eingänge, viele Zeilenkameras auch Encoder-Eingänge mit Teiler. Die konkrete Encoder-Unterstützung je Modell ist im Datenblatt zu prüfen (nicht verifiziert). Ein Inkrementalgeber mit z. B. 1.000–5.000 Impulsen/Umdrehung an einer Messrolle ist eine Industrie-Standardkomponente (Preis nicht recherchiert).
- Flächenkamera: Unschärfe = v · t_exp. Bei 0,14 mm/px und höchstens 0,5 px (0,07 mm): 2 m/s → 35 µs, 1 m/s → 70 µs, 0,2 m/s → 350 µs. Unter ca. 100 µs braucht es einen getriggerten Blitz (LED-Strobe, Overdrive). Auslösung per Lichtschranke/Encoder, Bildabstand so, dass sich die Bilder 10–20 % überlappen. Bildrate bei 2448 × 2048 und 0,14 mm/px (ca. 290 mm Bildhöhe längs): 2 m/s → ca. 7–8 fps nötig, die ace 2 mit 23 fps reicht.
- Stitching vieler Flächenbilder (Überlappung, perspektivische Verzerrung, Beleuchtungsverlauf am Bildrand) ist Mehraufwand gegenüber dem fortlaufenden Zeilenbild. Für YOLO ist es aber unkritisch, wenn auf Einzelbildern gearbeitet und doppelte Treffer anschließend zusammengeführt werden.
- Rolling Shutter bei Bewegung: Bei z. B. 30 ms Auslesezeit wandert das Holz bei 2 m/s um 60 mm während des Auslesens, bei 0,2 m/s um 6 mm. Das ergibt eine deutliche Scherung. Nur stillstehend oder mit kurzem Blitz in dunkler Umgebung brauchbar.

### Gaps
- Encoder-Eingänge und die Farb-Zeilenrate des racer 2 2k GigE Farbe (r2L2048-29gc) konnten nicht verifiziert werden (Shopseite nicht abrufbar).
- Preise für Encoder und LED-Linienbeleuchtung wurden nicht recherchiert (vermutlich ein anderer Rechercheteil).

## 3. Farbe: Bayer-Flächenkamera vs. bi-/trilineare Farbzeilenkamera

### Takeaway
Farbe ist für Altholz wichtig (Fäule, Verfärbung, Farbe/Lack, Rost um Nägel). Bilineare Farbzeilen (z. B. 2048 × 2, Linea Lite, racer 2, Hikrobot CL "×2") und trilineare Farbzeilen (VŠB-Datensatz) liefern volle Farbe je Pixel ohne Bayer-Interpolation. Bayer-Flächenkameras sind billiger und einfacher, verlieren aber effektive Farbauflösung. Weißabgleich und Farbtreue hängen bei beiden vor allem von stabiler Beleuchtung und Referenzkarte ab.

### Cited Findings
- Linea Lite 2k Farbe: 2048 × 2 Teledyne-e2v-"Tetra"-Sensor (bilinear), 14 µm Pixel, 25 kHz, GigE Vision. — [Teledyne Linea Lite](https://www.teledynevisionsolutions.com/products/linea-lite/); [Edmund Optics EU](https://www.edmundoptics.eu/p/l2-gc-02k02b-00-a-dalsa-linea-lite-line-scan-gige-camera/55495/)
- Die Linea Color 2k (LA-GC-02K05B) ist ein anderes Modell mit 7,04 µm Pixeln und 26 kHz. — [Edmund Optics IN](https://www.edmundoptics.in/p/la-gc-02k05b-00-r-dalsa-linea-line-scan-gige-camera/55488/)
- Hikrobot führt Farbzeilenkameras als "2048 × 2" / "4096 × 2" (bilinear), z. B. MV-CL020-41GC (2k, 7 µm, ca. 26 kHz) und MV-CL042-91GC (4096 × 2). — [Polytec Hikrobot-Katalog](https://www.polytec.com/fileadmin/website/photonique-vision/pdf/hikrobot/Catalogue_HikRobot_2022.pdf); [IndiaMART-Listing MV-CL042-91GC](https://m.indiamart.com/proddetail/hikrobot-mv-cl042-91gc-2858082121888.html)
- Der VŠB-Holzdatensatz nutzt eine trilineare Kamera (3 × 4096 px). — [PMC9277195](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9277195/)
- Industriescanner nutzen Farbkameras zusätzlich zu Laser/Tracheid und Röntgen: WEINIG "additional high-resolution, color camera" für Farbmerkmale; MiCROTEC Goldeneye kombiniert "scattering laser, 3D laser, color, and X-ray". — [WEINIG](https://www.weinig.com/en/solid-wood/scanner-systems/solid-scan-4000-series/); [MiCROTEC](https://www.microtec.com/en/products/goldeneye)

### Inferences
- Bilineare Farbzeilen sitzen in zwei benachbarten Zeilen (z. B. R/B und G abwechselnd). Bei einer Zeilenkamera ist das zeitliche Zusammensetzen der Farben über den Encoder-Takt wichtig (räumliche Korrektur), sonst entstehen Farbsäume an Kanten. Trilineare Kameras (Zeilen mit Abstand) sind noch empfindlicher gegenüber Vorschubschwankungen und Höhenänderung. Bilinear ist daher für unebene Balken robuster.
- Für YOLO ist Bayer-Farbe in der Regel ausreichend. Die Farbtreue ist eher für spätere Klassierung (z. B. Fäule vs. Verschmutzung) relevant. Weißabgleich einmalig mit Graukarte unter der festen Beleuchtung, danach fixieren. Keine Automatik, damit die Trainingsdaten reproduzierbar sind.
- Mono plus Farbe: Mono-Kameras sind lichtempfindlicher und günstiger, verlieren aber Information über Farbe/Lack/Fäule. Für Altholz wird Farbe empfohlen.

### Gaps
- Keine Quelle zur messbaren Farbtreue (Delta E) von Bayer- vs. bilinearen Zeilenkameras auf Holz gefunden.

## 4. Schnittstellen (GigE, 5GigE, USB3, CoaXPress, Camera Link) und Host-Hardware, Framegrabber

### Takeaway
Für das Forschungsbudget ist GigE (PoE) die beste Wahl: kein Framegrabber, lange Kabel (bis 100 m), mehrere Kameras an einer Mehrport-Netzwerkkarte. 5GigE ist die Option, wenn Farbe, 4k und hohe Zeilenrate zusammenkommen. CoaXPress kostet zusätzlich einen Framegrabber (ca. 1.600 EUR). USB3 ist billig, hat aber kurze Kabel und ist bei 4 Kameras an einem Rechner eher heikel.

### Cited Findings
- Basler racer 2 Preise je Schnittstelle: 4k GigE r2L4096-29gm 779 EUR (Singapur-Shop 724 EUR), 4k 5GigE r2L4096-84g5m 879 EUR, 2k CXP-12 r2L2048-172cm 899 EUR, 4k CXP-12 r2L4096-84cm 979 EUR, 16k CXP-12 2.859 EUR. — [Basler r2L4096-29gm](https://www.baslerweb.com/en/shop/r2l4096-29gm/); [r2L4096-84g5m](https://www.baslerweb.com/en/shop/r2L4096-84g5m); [r2L2048-172cm](https://www.baslerweb.com/en/shop/r2L2048-172cm); [r2L4096-84cm](https://baslerweb.com/en/shop/r2L4096-84cm); [r2L16384-120cm](https://baslerweb.com/en/shop/r2L16384-120cm)
- Basler führt als Zubehör für CXP-Kameras den Framegrabber "imaWorx CXP-12 Quad" für +1.589 EUR. — [Basler r2L8192-240cm](https://www.baslerweb.com/en-sg/shop/r2l8192-240cm/)
- Auch 2k/4k-Farbmodelle mit CXP (r2L4096-42cc, r2L2048-62cc) und 5GigE (r2L4096-42g5c) gibt es. Ihre Preise kamen im Suchergebnis nicht vor. — [Basler r2L4096-42cc](https://www.baslerweb.com/en/shop/r2l4096-42cc); [r2L4096-42g5c](https://www.baslerweb.com/en/shop/r2L4096-42g5c)

### Inferences
- Datenraten: GigE ≈ 115–120 MB/s nutzbar. 2k Mono 8 bit × 20 kHz = 41 MB/s (passt). 2k RGB 24 bit × 20 kHz = 123 MB/s (an der Grenze, TurboDrive/Kompression oder 5GigE nötig). 4k RGB × 20 kHz = 246 MB/s (5GigE ca. 580 MB/s oder CXP). Bei 1 m/s und 0,1 mm (10 kHz) passt 2k RGB bequem in GigE und 4k RGB knapp nicht.
- Flächenkamera 5 MP Bayer 8 bit × 10 fps = 50 MB/s, also GigE problemlos.
- Host: Für 4 GigE-Kameras eine 4-Port-PoE-Netzwerkkarte (Intel-Chipsatz) oder ein PoE-Switch mit 10G-Uplink, dazu ein PC/Industrie-PC mit GPU für YOLO-Inferenz. Preise dafür nicht recherchiert, als Schätzung ca. 200–500 EUR für die NIC/Switch. Camera Link ist veraltet, teuer (Framegrabber + Kabel) und nicht nötig.
- Der vorhandene Contabo-Server ist für den Kamerabetrieb ungeeignet (keine Kamera vor Ort, keine GPU). Erfassung und Inferenz brauchen einen lokalen Rechner an der Anlage.

### Gaps
- Preise für 4-Port-PoE-NICs, Kabel und Industrie-PCs wurden nicht recherchiert.

## 5. Objektive, Arbeitsabstand, Schärfentiefe

### Takeaway
Zeilenkameras mit 2k × 14 µm oder 4k × 7 µm haben 28,7-mm-Sensoren und brauchen F-Mount- oder M42-Objektive mit großem Bildkreis (Kowa LM-LF ca. 930–1.340 EUR, alternativ günstige Kleinbild-F-Mount-Festbrennweiten). Flächenkameras mit 2/3"-Sensor nutzen C-Mount-Objektive (Größenordnung 200–600 EUR, nicht verifiziert). Bei Blende 8 und 0,1–0,15 mm/px ergeben sich rechnerisch ca. 7–10 cm Schärfentiefe. Das reicht für verzogene Balken, telezentrische Optik ist unnötig.

### Cited Findings
- Kowa LM50LF: 50 mm, F-Mount, für 4k-Zeilenkameras, 46 mm Bildkreis, Arbeitsabstand 0,4 m bis unendlich. Kowa-Listenpreise der Reihe ca. 932–1.338 EUR (F-Mount- und TFL-II-Varianten). — [Kowa LM50LF](https://kowa-lenses.com/LM50LF-43.3mm-50mm-F-Mount-Line-Scan-Lens/10781); [Stemmer Kowa LM-LF](https://www.stemmer-imaging.com/en/series-kowa-lmlf)
- Telezentrische Zeilenobjektive mit M42 (Opto Engineering TC4K) gibt es mit Arbeitsabständen von 174–254 mm. Sie decken aber nur kleine Bildfelder ab (z. B. Vergrößerung 0,159×). Preis nur auf Anfrage. — [Opto Engineering TC4K](https://opto-e.com/en/products/tc4k-series); [Stemmer TC 4K 120-J](https://www.stemmer-imaging.com/en/oe-tc-4k-120j)
- Schneider-Kreuznach bietet Zeilenobjektive (Reihen Pyrite, Zirconia, Sapphire) für große Zeilensensoren an, ohne öffentliche Preise. — [Schneider-Kreuznach line scan lenses](https://schneiderkreuznach.com/en/industrial-optics/lenses/line-scan-lenses)
- Die Raspberry Pi Global Shutter Camera nutzt die C/CS-Mount-Aufnahme der Pi-HQ-Kamera. — [Raspberry Pi](https://www.raspberrypi.com/products/raspberry-pi-global-shutter-camera/)

### Inferences
- Schärfentiefe ≈ 2 · k · c · (1+m) / m² (k = Blende, c = zulässiger Zerstreuungskreis ≈ 2 px, m = Abbildungsmaßstab):
  - Zeilenkamera 7 µm Pixel, 0,15 mm/px (m ≈ 0,047), k = 8: ≈ 105 mm. Bei 0,1 mm/px (m = 0,07): ≈ 48 mm.
  - 14 µm Pixel (Linea Lite 2k), 0,15 mm/px (m ≈ 0,093), k = 8: ≈ 57 mm.
  - Flächenkamera 2,74 µm, 0,14 mm/px (m ≈ 0,02), k = 8: rechnerisch > 20 cm, aber bei k = 8 ist das Beugungsscheibchen (ca. 10 µm) deutlich größer als das 2,74-µm-Pixel. Realistisch ist k = 4–5,6 und damit ca. 10 cm.
  - Für unebene Altbalken (Verzug, Bearbeitungsspuren, Zapfenlöcher) sind ±2–5 cm Höhenschwankung zu erwarten. Das passt, braucht aber viel Licht (kleine Blende).
- Arbeitsabstand: 2k × 14 µm (28,7 mm Sensor) auf 340 mm Bildbreite → m ≈ 0,084, mit 50 mm Brennweite ≈ 0,65 m Abstand. 2/3"-Flächenkamera (6,7 mm Sensorbreite) auf 340 mm → m ≈ 0,02, mit 12 mm ≈ 0,6 m, mit 16 mm ≈ 0,8 m. Beides passt in einen kompakten Rahmen. Beim Zeilenscanner muss die Beleuchtung entlang der Linie gleichmäßig sein.
- Kosteneffizient für die Forschung: gebrauchte oder neue Kleinbild-F-Mount-Objektive (Nikon 50 mm f/1.8 o. Ä.) an der Zeilenkamera. Bei 7-µm-Pixeln sind sie optisch meist ausreichend (nicht verifiziert, Größenordnung ca. 100–250 EUR geschätzt).

### Gaps
- Keine verifizierten Straßenpreise für C-Mount-Objektive (z. B. Basler-, Kowa-, Computar-Objektive für 5 MP).
- Ob die Zeilenkameras von Basler/Hikrobot standardmäßig M42 oder F-Mount haben, wurde nicht je Modell verifiziert (racer 2 hat je nach Modell M42/M58/F-Adapter, nicht bestätigt).

## 6. Konkrete Modelle und Preise

### Takeaway
Industriekameras sind inzwischen günstig: Zeilenkamera ab ca. 780 EUR (Basler racer 2 4k GigE Mono), Farbzeile 2k ab ca. 1.155 EUR (Linea Lite), 5-MP-Global-Shutter-Flächenkamera 600–760 EUR (Basler ace 2). Hikrobot ist meist 30–50 % günstiger, aber die Preise sind schwer zu verifizieren. Ein 4-seitiges System nur mit Kameras kostet etwa 2.500–5.000 EUR. Das passt zu 5–10k EUR, wenn Licht, Mechanik und PC knapp gehalten werden.

### Cited Findings
Zeilenkameras:
- Basler racer 2 r2L4096-29gm (4k Mono, GigE): 779 EUR netto (Singapur-Shop 724 EUR). — [Basler Shop](https://www.baslerweb.com/en/shop/r2l4096-29gm/)
- Basler racer 2 r2L4096-84g5m (4k Mono, 5GigE): 879 EUR. — [Basler Shop](https://www.baslerweb.com/en/shop/r2L4096-84g5m)
- Basler racer 2 r2L2048-29gc (2k Farbe, GigE): existiert, Preis nicht ermittelt. — [Basler Shop](https://www.baslerweb.com/en/shop/r2L2048-29gc)
- Teledyne DALSA Linea Lite L2-GC-02K02B-00-A (2k bilinear Farbe, 14 µm, 25 kHz, GigE): 1.155,00 EUR netto bei Edmund Optics EU (Stückpreis). — [Edmund Optics EU](https://www.edmundoptics.eu/p/l2-gc-02k02b-00-a-dalsa-linea-lite-line-scan-gige-camera/55495/)
- Hikrobot MV-CL020-41GC (2k Farbe, 7 µm, ca. 26 kHz, GigE): kein offizieller Preis. Ein Aggregator nennt 970–978 USD für eine 2k/4k-Farbzeile GigE (nur Richtwert); ein indisches Listing nennt 2.00.000 INR (ca. 2.000 EUR, ohne Steuern) für eine 4k-Mono-Hikrobot. — [Polytec-Katalog](https://www.polytec.com/fileadmin/website/photonique-vision/pdf/hikrobot/Catalogue_HikRobot_2022.pdf); [Accio](https://www.accio.com/plp/hikrobot-price); [IndiaMART](https://m.indiamart.com/proddetail/hikrobot-line-scan-camera-2856844992897.html?pos=3)

Flächenkameras (Global Shutter):
- Basler ace 2 a2A2448-23gcPRO (5 MP, Sony IMX547, 2,74 µm, 23 fps, GigE, Global Shutter): 759 EUR netto. a2A2448-23gcBAS: 639 EUR. IMX547-Familie ab 599 EUR. — [Basler Shop RU](https://www.baslerweb.com/ru-ru/shop/a2a2448-23gcpro); [Basler Shop IT](https://www.baslerweb.com/it-it/shop/a2a2448-23gcbas); [Basler IMX547](https://baslerweb.com/en/shop/a2a2448-imx547)
- Hikrobot MV-CS050-10GC (5 MP, Sony IMX264 2/3", Global Shutter, 24 fps, GigE): EUR-Preis nur auf Anfrage (Maxxvision). Der abgekündigte Vorgänger MV-CA050-10GC lag bei 310 EUR zzgl. MwSt. eBay-Angebote für die Mono-PRO-Variante liegen bei ca. 554 EUR (unverifizierte Händler). — [roboticscenter.ai](https://www.roboticscenter.ai/store/product/hikrobot-mv-cs050-10gc/); [Maxxvision MV-CA050-10GC](https://www.maxxvision.com/produkte/kameras/abgekuendigte-kameras/317/mv-ca050-10gc); [eBay](https://www.ebay.de/itm/167903483818)

Günstige Optionen:
- Raspberry Pi Global Shutter Camera (Sony IMX296, 1,6 MP, 1456 × 1088, 3,45 µm, C/CS-Mount, Belichtung ab 30 µs, verfügbar mindestens bis Januar 2032): Einführungspreis 50 USD, Pimoroni 50,95 EUR (zum Abrufzeitpunkt ausverkauft). — [Raspberry Pi](https://www.raspberrypi.com/products/raspberry-pi-global-shutter-camera/); [Pimoroni](https://shop.pimoroni.com/en-eu/products/raspberry-pi-global-shutter-camera); [PetaPixel](https://petapixel.com/2023/03/09/raspberry-pis-new-global-shutter-camera-costs-just-50/)
- Waveshare IMX296 Global Camera (A): 62,99 USD. — [Waveshare](https://www.waveshare.com/imx296-global-camera-a.htm)

### Inferences
- Raspberry Pi GS: 1456 px quer ergeben auf 300 mm nur ca. 0,2 mm/px. Für 1-mm-Löcher grenzwertig, für einen Prüfstand mit kleinem Bildfeld (z. B. 150 mm → 0,1 mm/px) brauchbar. Dazu kommt ein Pi (Preis nicht recherchiert) und ein C-Mount-Objektiv. Gut zum Lernen und für Trigger-/Blitz-Experimente, nicht als Endlösung für 30-cm-Breiten. Die Pi HQ Camera (IMX477, 12 MP) hat Rolling Shutter und ist nur stillstehend sinnvoll.
- Beispiel-Budget (Schätzung, nur Kameras):
  - Variante A, Flächenkamera 4 Seiten: 4 × Basler ace 2 Farbe 5 MP (ca. 640–760 EUR) ≈ 2.600–3.000 EUR.
  - Variante B, Zeilenkamera 2 Breitseiten Farbe + 2 Kanten: 2 × Linea Lite 2k Farbe (1.155 EUR) + 2 kleinere Kameras ≈ 3.500–4.000 EUR.
  - Variante C, Zeilenkamera 4 Seiten 4k Farbe: 4 × ca. 1.000–1.300 EUR (Preis für 4k-Farbe nicht verifiziert) ≈ 4.000–5.200 EUR.
  - Variante D, Einstieg: 1 Zeilenkamera + Wenden ≈ 800–1.200 EUR.
  Hinzu kommen jeweils Objektive, Licht, Encoder/Trigger, NIC/PC und Mechanik.
- Allied Vision (Alvium, chromaPIXA-Farbzeilen), IDS (uEye) und Daheng (MER-Serie) wurden in dieser Runde nicht bepreist. Nach Marktkenntnis liegen IDS und Allied Vision etwa auf Basler-Niveau, Daheng eher auf Hikrobot-Niveau (unverifizierte Einschätzung).

### Gaps
- Keine verifizierten EUR-Preise für: racer 2 Farbe (2k/4k), Hikrobot-Zeilenkameras in Europa, IDS uEye, Allied Vision Alvium/chromaPIXA, Daheng, Arducam-Global-Shutter-Module. Für die Beschaffung Angebote einholen (Stemmer Imaging, Framos, Maxxvision, Polytec für Hikrobot).

## 7. Smartphone-Kameras: Datensammlung vs. Produktion

### Takeaway
Smartphones taugen zum Sammeln erster Trainingsbilder an stillstehenden Werkstücken (hohe Auflösung, kostenlos verfügbar). Für einen Durchlaufscanner taugen sie nicht: Rolling Shutter, automatische Bildverarbeitung (HDR, Schärfung, Weißabgleich), kein Hardware-Trigger, schlechte Reproduzierbarkeit. Außerdem passt die Bilddomäne später nicht zur Industriekamera.

### Cited Findings
- Rolling Shutter verzerrt bewegte Objekte, abhängig von der Auslesegeschwindigkeit. Die Belichtungszeit ändert daran nichts. — [Basler Knowledge Base](https://www.baslerweb.com/en/sales-support/knowledge-base/cmos-rolling-shutter-cameras)
- Für kamerabasierte Qualitätsprüfung führen Rolling-Shutter-Sensoren oft zu verzerrten oder unscharfen Bildern. Global Shutter wird bevorzugt. — [USPTO 11941799](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11941799)
- Ein Fachartikel (Herstellersicht, keine unabhängige Evidenz) argumentiert, Smartphone-Prüfung sei billiger und leichter zu standardisieren, und der Abstand zu Industriesensoren schrumpfe. — [Vision Systems Design](https://www.vision-systems.com/cameras-accessories/article/55368033/is-smartphone-based-visual-inspection-the-future-of-quality-control)

### Inferences
- Für die Datensammlung (Phase 1) mit dem Smartphone: Werkstück liegt still, Stativ, fester Abstand, Maßstab/Graukarte im Bild, RAW/Pro-Modus mit fixer Belichtung und Weißabgleich, kein HDR, diffuses Licht. Damit lassen sich Klassen und Annotationsrichtlinien früh erarbeiten.
- Domänenwechsel: Ein YOLO-Modell, das auf Smartphone-Bildern trainiert wurde, verliert beim Wechsel auf Zeilenkamerabilder (andere Geometrie, Beleuchtung, Farbe, Schärfe) voraussichtlich an Güte. Smartphone-Bilder sind als Vortraining oder Ergänzung sinnvoll. Die Produktionsdaten sollten mit der späteren Kamera und Beleuchtung entstehen.
- Für die Produktion: kein Encoder-Trigger, nicht synchronisierbar über 4 Seiten, Wärme und Langzeitbetrieb unklar, OS-Updates ändern die Bildverarbeitung. Damit ungeeignet.

### Gaps
- Keine Studie gefunden, die Smartphone- und Industriekamera-Trainingsdaten für Holzfehler direkt vergleicht.

## 8. Kameratypen in industriellen Holzscannern (MiCROTEC, WEINIG, LuxScan, Lucidyne, LMI)

### Takeaway
Industrielle Holzscanner sind Multisensorsysteme: Farbkameras (in der Regel Farbzeilenkameras), 3D-Laserprofil, Tracheid-/Streulaser und oft Röntgen. Die konkreten Kameramodelle und Auflösungen veröffentlichen die Hersteller nicht. Ein rein optischer Farbscanner deckt also nur einen Teil dessen ab, was ein Goldeneye oder CombiScan misst (z. B. keine Dichte, keine Faserneigung über Tracheid).

### Cited Findings
- MiCROTEC Goldeneye: Technologien "3D laser, scattering laser, color, X-ray, MiCROTEC Ai", 4 Seiten, bis 1200 m/min; Funktionen u. a. Erkennung schräger Risse, Jahrringkarte, Markröhrenfinder. Kameratyp und Auflösung werden nicht angegeben. — [MiCROTEC Goldeneye](https://www.microtec.com/en/products/goldeneye)
- Eine Designpreis-Seite zum Goldeneye (2015) nennt neue Kameras "mit Full HD Auflösung" und On-Chip-Bildverarbeitung. Technische Details fehlen. — [iF Design Award](https://ifdesign.com/de/winner-ranking/project/goldeneye/151442)
- WEINIG CombiScan / Solid Scan 4000: Standard-Laserkamera für Fehler auf bis zu 4 Seiten, zusätzlich eine "high-resolution, color camera" für Farbmerkmale, optional Röntgen, Feuchte und automatisch verfahrende Kameras. Die Baureihe heißt "LuxscanLine" (LuxScan gehört zu WEINIG). — [WEINIG Solid Scan 4000](https://www.weinig.com/en/solid-wood/scanner-systems/solid-scan-4000-series/); [WEINIG CombiScan Sense](https://m.weinig.com/en/solid-wood/scanner-systems/combiscan-sense.html)
- Lucidyne-Patente beschreiben eine Beleuchtung mit scharfer Lichtkante zur Erfassung von Tracheid-, Farb- und Geometriemerkmalen. — [Lucidyne-Patente (Justia)](https://patents.justia.com/assignee/lucidyne-technologies-inc)
- Ein Patent zur Nassholzerkennung beschreibt einen Scanrahmen, in dem jeder Scanner je ein Paar Tracheid-Sensoren, Farbkameras und Laserprofilsensoren hat (Hersteller nicht genannt). — [USPTO 11416980](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11416980)
- LMI (Marke chroma+scan, früher Nachrüstsätze für Sägewerksscanner) kombiniert Profil, Tracheid und Farbe. Hohe 3D-Dichte plus Tracheid hilft z. B. bei der Faserneigung. — [LMI chroma+scan](https://lmi3d.com/brand/chroma-scan/); [LMI-Artikel (PDF, 2018)](https://lmi3d.com/wp-content/uploads/2018-08/IFI%20Article-%20May%202018.pdf)

### Inferences
- Die Branchenarchitektur (Zeilenkamera + Linienlicht + Encoder, Profil per Lasertriangulation) ist das Vorbild für den BSH-Lamellenscanner vor der Kappsäge. Für den Altholz-Prüfstand bei langsamem Vorschub (0,2–1 m/s) ist eine Flächenkamera mit Blitz eine gleichwertige, einfacher zu bauende Alternative.
- Was optisch nicht geht (aus Sicht der Industriesensorik): Faserneigung (Tracheid), innere Fäule und verdeckte Metallteile (Röntgen bzw. Metalldetektor). Für Altholz sind versteckte Nägel/Schrauben sicherheitsrelevant für die Säge. Ein rein optischer Scanner sieht nur sichtbare Köpfe und Löcher. Ein günstiger Metalldetektor als Ergänzung sollte geprüft werden (nicht recherchiert).
- Das Startup-Angebot über ca. 100k EUR liegt im Bereich, in dem kommerzielle Lösungen mehrere Sensortypen kombinieren. Die eigene 5–10k-EUR-Lösung konkurriert realistisch nur im optischen Teil.

### Gaps
- Keine öffentlichen Angaben zu Kamerahersteller, Zeilenlänge, Zeilenrate oder mm/px bei MiCROTEC, WEINIG/LuxScan oder Lucidyne. LMI-Seiten sperrten den automatischen Abruf.
- Ob Goldeneye- und CombiScan-Farbkameras Zeilen- oder Flächenkameras sind, ist nicht belegt. Die Patente und die Funktionsweise sprechen für Zeilenkameras, öffentlich bestätigt ist das nicht.
