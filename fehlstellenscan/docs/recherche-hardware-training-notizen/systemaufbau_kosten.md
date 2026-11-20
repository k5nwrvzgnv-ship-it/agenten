# Systemaufbau und Kostenszenarien: optischer Oberflächenscanner für Altholz (YOLO)

Stand der Recherche: 20.11.2026. Preise in EUR, Deutschland, soweit belegt. Alles, was mit **[Schätzung]** markiert ist,
hat keine Quelle aus dieser Recherche und beruht auf Erfahrungswerten bzw. eigener Rechnung. Kamera und Licht sind
nicht Teil dieser Notiz (andere Teilrecherche), tauchen in den Tabellen nur als Platzhalter-Zeile auf.

Annahmen für alle Rechnungen: Werkstücke bis ca. 4–6 m, Querschnitte 5x10 bis 20x30 cm. Ein Balken 20x30 cm x 5 m
Nadelholz (ca. 450–500 kg/m3) wiegt rund 135–150 kg; feuchtes oder Eichen-Altholz (ca. 700 kg/m3) bis ca. 210 kg
**[eigene Rechnung: 0,2 x 0,3 x 5 m = 0,3 m3]**. Das bestimmt die Fördertechnik.

## 1. Materialführung (Förderung/Vorschub)

### Takeaway
Für 5–10 k EUR ist entweder (a) eine nicht angetriebene Schwerlast-Rollenbahn mit Durchschieben von Hand plus
Messrad-Encoder oder (b) ein feststehendes Werkstück mit bewegter Kamera auf einer Linearachse realistisch.
Angetriebene Förderer (Gurt oder Rollen mit Getriebemotor und FU) kosten neu schnell 3 k EUR und mehr allein für
2,6–3 m und sind eher Szenario 2 (oben) bzw. 3.

### Cited Findings
- Blume-Schwerlast-Rollenbahn mit Stahlrollen: Traglast 300 kg pro Meter; leichte Rollenbahn desselben Herstellers
  200 kg pro Meter. Preise im Suchergebnis nicht sichtbar — [udobaer.de Schwerlast-Rollenbahn](https://oci.udobaer.de/blume-foerderanlagen-schwerlast-rollenbahn-mit-stahlrollen-e11173.html), [udobaer.de leichte Rollenbahn](https://oci.udobaer.de/blume-foerderanlagen-leichte-rollenbahn-e13552.html)
- Neuer Bandförderer 2600 x 400 mm mit Getriebemotor und PVC-Gurt: 3.080 EUR inkl. MwSt. (eBay-Händlerangebot) — [eBay-Angebot laut Suchergebnis](https://www.ebay.de/itm/144997480372)
- Gebrauchte Gurtförderer: Göbling/Gössling 3100 x 400 mm für 1.400 EUR (Motor unklar); Transnorm 1000 mm, 400 mm Gurt,
  SEW-Getriebemotor, 1.724 EUR; Lippert 14,59 m für 3.836 EUR; Schunk 3050 x 400 mm inkl. Motor und FU (Preis nicht
  lesbar) — [maschinensucher Gössling](https://www.maschinensucher.de/g%C3%B6ssling-3100+x+400/i-19449746), [maschinensucher Transnorm](https://www.maschinensucher.de/transnorm-1000-500-400/i-21175577), [maschinensucher Lippert](https://www.maschinensucher.de/lippert-14590-550-400/i-20392380), [maschinensucher Schunk](https://www.maschinensucher.de/schunk+f%C3%B6rdertechnik+gmbh-gurtbandf%C3%B6rderer%2C+gurtband/i-22044858)
- Frequenzumrichter 0,75 kW: Schneider ATV12H075M3 341 EUR (RS); Danfoss FC-302 0,75 kW 286,87 EUR inkl. MwSt. (eBay);
  ABB ACS150 0,75 kW ab 169,46 EUR (eBay); Lenze gebraucht ab ca. 150–380 EUR — [RS Frequenzumrichter](https://de.rs-online.com/web/p/frequenzumrichter/8200823), [eBay Danfoss](https://www.ebay.de/p/15079463654), [RS Danfoss PK75](https://de.rs-online.com/web/p/frequenzumrichter/2193267)
- igus drylin ZLW Zahnriemenachse: ZLW-1660 bis 3.000 mm Hub, Preis "auf Anfrage"; ZLW-20120/20160/20200 bis 3.000 mm
  Hub, US-Basispreise 994,32 USD (ZLW-20120-AL, 200 mm Hub) bis 4.091,42 USD (ZLW-20200-ES, 200 mm Hub); ZLW-0630
  216,26 EUR Basis, max. 1.000 mm Hub — [igus UK ZLW-1660](https://igus.co.uk/info/toothed-belt-axis-zlw-1660), [igus ZLW-1660B](https://www.igus.eu/product/20942), [igus ZLW-0630](https://www.igus.de/wpck/4769/zlw_0630)

### Inferences
- Optionen im Vergleich **[Bewertung, eigene Einschätzung]**:
  - *Durchschieben von Hand auf Rollenbahn + Messrad-Encoder*: billigste Variante, Encoder taktet die Zeilenkamera
    wegsynchron, ungleichmäßige Geschwindigkeit stört dann nicht (nur Belichtung/Max-Zeilenrate begrenzt). Nachteil:
    150–200-kg-Balken von Hand schieben ist mühsam, Schlupf am Messrad bei rauer/verschmutzter Altholzoberfläche,
    Querversatz/Verdrehen. Seitliche Führungsrollen nötig.
  - *Angetriebene Rollenbahn (Kettenantrieb) oder Gurt* mit Getriebemotor + FU: gleichmäßiger Vorschub, gut für
    Zeilenkamera. Gurt nur bei leichten Brettern sinnvoll; schwere Balken auf Gurt mit Nägeln/Metallresten =
    Gurtverschleiß. Angetriebene Rollen robuster.
  - *Feststehendes Werkstück, Kamera-Portal auf Linearachse*: Werkstück liegt auf Böcken, Kamera fährt; kein
    Schlupfproblem (Motorgeber/Riemen gibt Position), leichtes Bauteil bewegt statt schwerem. Nachteil: Achslänge =
    Werkstücklänge (4–6 m Achsen sind teuer und nicht im igus-ZLW-Standard >3 m); Alternative selbstgebaute Achse aus
    Alu-Profil + Zahnriemen + Schrittmotor (CNC-Bauweise) **[Schätzung 400–1.200 EUR für 4–6 m]**.
  - Für ein Forschungsprojekt mit wenigen Proben pro Tag ist Portal oder Hand-Durchschub ausreichend; Durchsatz ist
    nicht das Ziel.
- Preisrahmen **[Schätzung]**: nicht angetriebene Rollenbahn Stahlrollen, 2 x 3 m (Ein- und Auslauf), 300–1.200 EUR
  (China/eBay günstig, Blume/Bito teurer); angetriebene Rollenbahn 2 x 3 m neu 4.000–12.000 EUR; Getriebemotor 0,37–0,75
  kW 200–600 EUR.

### Gaps
- Keine belegten Neupreise pro Meter für Schwerlast-Rollenbahnen (Hersteller nennen Preise erst im Shop/auf Anfrage).
- Keine belegten Preise für igus-Achsen mit 3.000 mm Hub (Konfigurator) und für Alibaba-Förderer (nicht abgefragt).

## 2. Encoder, Lichtschranken, Trigger, Steuerung

### Takeaway
Die Wegsynchronisation über ein Messrad mit Inkrementalgeber ist der etablierte Weg (auch in Patenten industrieller
Scanner). Messrad plus Markengeber kosten zusammen ca. 150–800 EUR; Lichtschranken für Anfang/Ende wenige 10–150 EUR je
Stück. Für einen Prototyp genügt ein Mikrocontroller (Pico/ESP32) oder der Encodereingang der Kamera; eine SPS ist erst
bei Sicherheitsfunktionen/Industrie sinnvoll.

### Cited Findings
- US-Patent für Oberflächenfehlererkennung: Drehgeber auf einer Förderrolle erzeugt Impulse zur Zeitsynchronisation,
  Kameras sehen Ober- und Unterseite — [USPTO 6122065](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6122065)
- Sägewerkstudie mit trilinearer Zeilenkamera (9,6 m/s): Aufnahme lief ohne Trigger im Dauerbetrieb, Folge: viele
  Bilder vom leeren Band bzw. halbe Oberflächen; 20.276 Proben, 10 Fehlerarten — [BioResources, doi 10.15376/biores.18.1.Chen](https://doi.org/10.15376/biores.18.1.Chen)
- Kübler Messrad Serie 8.0000: 59,74 EUR netto (RS AT); anderes Kübler-Messrad 135,84 EUR netto (RS DE);
  Wachendorff-Messrad für 10-mm-Welle 81,16 EUR netto; Wachendorff-Inkrementalgeber 16384/U 638,85 EUR netto;
  Kübler-Inkrementalgeber 1024/U ca. 225 CHF (Angabe unklar) — [RS Kübler Messrad](https://at.rs-online.com/web/p/sensor-zubehor/2872597), [RS Wachendorff Messrad](https://at.rs-online.com/web/p/sensor-zubehor/2858446), [RS Wachendorff Geber](https://de.rs-online.com/web/p/bewegungssensoren/2496493), [RS Kübler Geber](https://dech.rs-online.com/web/p/bewegungssensoren/4314599)
- Fertige Messrad-Drehgeber gibt es als System (Baumer, Kübler Mini-Messradsystem, Umfang 100 mm) — [Baumer Messrad-Drehgeber](https://www.baumer.com/at/de/produktubersicht/distanzmessung/messrad-drehgeber/c/292), [Kübler Datenblatt](https://static.mercateo.com/67/6996b3ad28464d939bc17e037ed63c99/pdf/Mini-Messradsystem_ger_tds.pdf)

### Inferences
- Auslegung **[eigene Rechnung]**: Messrad 200 mm Umfang, Geber 1024 Impulse/U, 4-fach ausgewertet = 4096
  Flanken/U = 0,049 mm pro Flanke. Bei 0,2 mm Pixel in Längsrichtung also Teiler 4. Bei 0,5 m/s und 0,2 mm/Zeile:
  2.500 Zeilen/s — für übliche Zeilenkameras unkritisch. 1024er Geber reicht; 16384er unnötig.
- Viele Industrie-Zeilenkameras und Framegrabber haben direkte Encoder-/Trigger-Eingänge (RS-422/TTL) mit Teiler;
  dann braucht man keinen Mikrocontroller im Zeilentakt, sondern nur Logik für Start/Ende **[Schätzung, Herstellerdaten
  der jeweiligen Kamera prüfen]**.
- Lichtschranken/Reflexlichttaster M18 (Sick, Pepperl+Fuchs, Banner) **[Schätzung 40–150 EUR je Stück; China-Ware
  10–25 EUR]**; zwei Stück (Anfang/Ende bzw. Werkstück vorhanden).
- Steuerung **[Bewertung]**: Raspberry Pi Pico/ESP32 (5–15 EUR) mit Optokopplern/Pegelwandler für 24 V reicht für
  Prototyp (Encoderzählung per PIO, Trigger-Ausgang, Lichtschranken). Industrielle Alternative: kleine SPS
  (Siemens S7-1200, Kleinsteuerung) oder Remote-IO **[Schätzung 300–1.000 EUR]**; nötig spätestens, wenn
  Not-Halt/Sicherheitsfunktionen an Antrieben hängen (dann Sicherheitsrelais 100–250 EUR **[Schätzung]**).
- Schlupf am Messrad auf Altholz (Schmutz, Risse, Unebenheiten): Federandruck, gummiertes Rad, ggf. zweites Messrad
  oder Geber auf angetriebener Rolle **[Bewertung]**.

### Gaps
- Keine Preise für Lichtschranken und SPS in dieser Recherche abgefragt (nur Schätzung).

## 3. 1-seitig vs. 4-seitig (Wenden, Kameras rundum, Spiegel)

### Takeaway
4-seitig mit einer Kamera je Seite vervierfacht Kamera-/Lichtkosten und braucht freien Blick auf die Unterseite
(Lücke zwischen Rollen/Bändern). Für das Budget ist 1-seitig mit Wenden von Hand (4 Durchläufe) oder 2-seitig
(oben + eine Kante, Wenden einmal) realistisch. Industrielle Scanner sind teils auch nur oben/unten (2-seitig).

### Cited Findings
- Gebrauchter Weinig-Scanner mit Kappsäge für 85.000 USD, ausdrücklich nur oben/unten, nicht 4-seitig —
  [woodweb.com](https://woodweb.com/exchanges/machinery/posts/556092.html)
- Patent: Kameras sehen Ober- und Unterseite des Bretts auf dem Förderer — [USPTO 6122065](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6122065)

### Inferences
- Varianten **[Bewertung]**:
  - *1 Kamera, Wenden von Hand*: Kosten minimal, 4 Durchläufe je Balken; Registrierung der 4 Seiten über Kante/Anfang
    (Lichtschranke) machbar. Bei 150–200 kg Balken braucht Wenden zwei Personen oder Hilfsmittel (Wendehaken,
    Kettenzug) — Arbeitssicherheit beachten.
  - *4 Kameras rundum*: Unterseite nur durch Lücke zwischen zwei Förderabschnitten (Spalt mit Messfenster);
    Querschnittsbereich 5–30 cm verlangt Fokus/Schärfentiefe-Reserve oder verstellbare Kamerahalter (verschiedene
    Abstände je Querschnitt).
  - *Spiegel*: eine Flächenkamera sieht Oberseite und zwei Kanten über 45°-Spiegel; spart Kameras, kostet Auflösung
    pro Seite und braucht saubere, große Oberflächenspiegel (bei 30 cm Breite groß); Staub in der Altholz-Umgebung.
    Für Zeilenkamera mit großem Querschnittsbereich eher unpraktisch.
  - Kompromiss für Szenario 2: 2 Kameras (oben + unten im Spalt) und einmal Kippen um 90° für die Kanten.
- Kostenfaktor **[Schätzung]**: 4-seitig ≈ 3–4x Kamera+Optik+Licht + mehr Rahmen + mehr Rechenlast; der Rest
  (Förderung, Encoder, Steuerung) bleibt fast gleich.

### Gaps
- Keine dokumentierten Preise für Spiegelanordnungen oder Wendevorrichtungen gefunden.

## 4. Rahmen, Abschirmung, Sicherheit (CE)

### Takeaway
Alu-Profil 40x40 Nut 8 (item-kompatibel) kostet bei Drittanbietern ca. 21–24 EUR/m; ein Rahmen mit Lichtschutz liegt
**[Schätzung]** bei 500–2.500 EUR je nach Größe und Profilmarke. Rechtlich kann ein reiner Forschungsaufbau unter die
Ausnahme der Maschinenrichtlinie fallen, die aber eng auszulegen ist (nicht für Prüfstände/Messeinrichtungen,
nicht für dauerhaften Betrieb).

### Cited Findings
- Alu-Profil 40x40 I-Typ Nut 8, eloxiert (Kaufland, aluboerse): 500 mm 10,64 EUR, 1500 mm 33,81 EUR, 2000 mm
  47,98 EUR (≈ 21–24 EUR/m) — [Kaufland](https://www.kaufland.de/product/534233054/); eBay "item-kompatibel" 1,88–35,60 EUR je Länge — [eBay blankprofiltechnik](https://www.ebay.de/str/blankprofiltechnik/Profile-Festpreis-/_i.html)
- Maschinenrichtlinie 2006/42/EG Art. 1 Abs. 2 h: ausgenommen sind Maschinen, die speziell für Forschungszwecke
  konstruiert und zur vorübergehenden Verwendung in Laboratorien bestimmt sind; nicht für dauerhaft installierte
  Maschinen oder Prüfzwecke; Eigenbau sonst voll unter MRL inkl. Konformitätserklärung — [KomNet NRW](https://www.komnet.nrw.de/_sitetools/dialog/43545), [KomNet NRW 19569](https://www.komnet.nrw.de/_sitetools/dialog/19569), [WKO FAQ Maschinenrichtlinie](https://www.wko.at/oe/ce-kennzeichnung-normen/faq-maschinenrichtlinie)
- KomNet-Fall: Motorenprüfstände nicht ausgenommen, weil Qualitätssicherung, keine Forschung; Messeinrichtungen
  ebenfalls nicht — [KomNet NRW](https://www.komnet.nrw.de/_sitetools/dialog/42419)
- DGUV Information 202-002: Herstellen und Betreiben von Geräten für Forschungszwecke (CE-Konformität,
  Betriebssicherheit) — [DGUV](https://publikationen.dguv.de/widgets/pdf/download/article/772)
- Neue EU-Maschinenverordnung gilt ab 20.01.2027 — [IHK Lippe](https://www.ihk.de/lippe-detmold/hauptnavigation/beraten-und-informieren/innovation-und-digitalisierung/aktuelles2/neue-eu-maschinenverordnung-5683128)

### Inferences
- item/Bosch Rexroth-Originalprofile liegen nach Erfahrung beim 2–3-fachen von No-Name-Profilen; Verbinder/Nutensteine
  machen oft 30–50 % der Rahmenkosten aus **[Schätzung]**.
- Abschirmung: Lichtschutz gegen Hallenlicht mit Alu-Verbundplatte/schwarzem PVC oder Bürstenleisten am Ein-/Auslauf
  **[Schätzung 200–800 EUR]**. Bei Zeilenkamera + starker Linienbeleuchtung ist Fremdlicht weniger kritisch als bei
  Flächenkamera.
- Sicherheit: Sobald Antriebe (Förderer, Linearachse) bewegt werden: Not-Halt, Schutz gegen Einzug an Rollen,
  Gefährdungsbeurteilung. Bei der Hand-Durchschub-Variante entfallen die meisten Maschinenrisiken (nur
  Quetschgefahr/Lasten) — ein Argument für Szenario 1/2. Ausnahme der MRL im Projekt mit der Arbeitssicherheit der
  Hochschule klären; mit Blick auf Übergang zur Maschinenverordnung 2027 **[Bewertung]**.
- Wenn der Aufbau später als Demonstrator/Prüfstand für Altholz-Sortierung weiterverwendet wird, greift die
  Forschungsausnahme vermutlich nicht mehr **[Inferenz aus KomNet-Auskünften]**.

### Gaps
- Keine Originalpreise item/Bosch Rexroth/Motedis pro Meter abgerufen. Ob die Maschinenverordnung (EU) 2023/1230 die
  Forschungsausnahme gleich fortführt, nicht geprüft.

## 5. Rechner für Inferenz an der Linie

### Takeaway
Ein Jetson Orin Nano Super (249 USD; ca. 340–350 EUR inkl. MwSt. in DE) schafft YOLO-Nano bei 640 px in rund 4–5 ms
pro Kachel (TensorRT FP16), AGX Orin 64GB (ca. 2.470 EUR inkl. MwSt.) rund 2,6 ms. Für einen Forschungsscanner ohne
harten Takt reicht ein Orin Nano/NX; die Bilderfassung (GigE/USB3/CoaXPress, Speicherbandbreite) ist eher der Engpass.
Alternativ PC mit RTX-GPU oder Auswertung offline.

### Cited Findings
- Jetson Orin Nano Super Developer Kit: 249 USD (vorher 499 USD) — [NVIDIA Blog](https://blogs.nvidia.com/blog/jetson-generative-ai-supercomputer); [NVIDIA DE](https://www.nvidia.com/de-de/autonomous-machines/embedded-systems/jetson-orin/nano-super-developer-kit/)
- Euro-Preise Orin Nano Super: RS Irland 280,96 EUR netto / 345,58 EUR brutto; Conrad über eBay 338,99 EUR;
  Waveshare 555,68 EUR — [RS IE](https://ie.rs-online.com/web/p/processor-development-tools/2647384), [eBay](https://www.ebay.de/itm/388604301594), [Waveshare](https://www.waveshare.com/directory/currency/switch/currency/EUR/uenc/aHR0cHM6Ly93d3cud2F2ZXNoYXJlLmNvbS9wcm9kdWN0L2FpL2JvYXJkcy1raXRzL2pldHNvbi1vcmluL2pldHNvbi1vcmluLW5hbm8tc3VwZXItZGV2ZWxvcGVyLWtpdC5odG0,/)
- SparkFun weist auf mögliche Preisanpassungen wegen Bauteilkosten und Zöllen hin — [SparkFun](https://www.sparkfun.com/nvidia-jetson-orin-nano-developer-kit.html)
- Jetson AGX Orin 64GB Developer Kit: RS DE 2.078,20 EUR netto / 2.473,06 EUR brutto; SparkFun 1.999,95 USD —
  [RS DE](https://de.rs-online.com/web/p/entwicklungstools-prozessor/2539662), [SparkFun](https://www.sparkfun.com/nvidia-jetson-agx-orin-64gb-developer-kit.html)
- Ultralytics-Benchmark YOLO26n, Eingang 640, TensorRT: AGX Orin 64GB 2,62 ms (FP16) / 2,30 ms (INT8); Orin NX 16GB
  4,13 / 3,49 ms; Orin Nano Super 4,57 / 3,80 ms; ohne Vor-/Nachverarbeitung; INT8 etwas geringere mAP (AGX: 0,4640
  vs. 0,4789) — [Ultralytics Jetson Guide](https://docs.ultralytics.com/guides/nvidia-jetson/)

### Inferences
- Rechenlast **[eigene Rechnung]**: 5 m Balken, 30 cm Seite, 0,2 mm/px ⇒ 25.000 x 1.500 px ≈ 37,5 MPx pro Seite ⇒
  bei 640er-Kacheln mit ca. 10 % Überlapp ≈ 45 x 3 ≈ 135 Kacheln ⇒ Nano-Modell auf Orin Nano Super ≈ 0,6 s reine
  Inferenz pro Seite (plus Vor-/Nachverarbeitung, Größenordnung Faktor 2). Bei s/m-Modellen entsprechend 2–5x mehr
  **[Schätzung]**. Für Laborbetrieb unkritisch; für 4 Seiten parallel mit 1 m/s eher Orin NX/AGX oder RTX-PC.
- Orin NX 16GB Modul + Trägerboard **[Schätzung 800–1.200 EUR]**; Industrie-PC mit RTX 4060/4070-Klasse und
  GigE-/USB3-Karten **[Schätzung 1.500–3.500 EUR]**; lüfterloser Industrie-PC mit GPU (z. B. Neousys/Advantech)
  **[Schätzung 3.000–8.000 EUR]**. Mac mini (Apple Silicon) läuft YOLO per CoreML/MPS, aber Treiber für
  Industriekameras (GenICam/GigE Vision) und Framegrabber sind unter macOS schlechter unterstützt — für die Linie
  eher Linux **[Bewertung]**.
- Speicher: Rohdaten pro Balkenseite ≈ 37,5 MB (8 bit mono) bzw. ≈ 112 MB (RGB) **[eigene Rechnung]**; für
  Trainingsdaten-Sammlung 2–4 TB NVMe/SSD (150–300 EUR) **[Schätzung]**. Projektvorgabe (CLAUDE.md): Training auf Jans
  Mac, nicht auf dem Contabo-Server.

### Gaps
- Kein belegter Euro-Preis für Orin NX und keine Benchmarks für YOLO11/YOLOv8 auf Jetson (Ultralytics-Seite zeigt
  nur YOLO26). Industrie-PC-Preise nicht abgefragt.

## 6. Metalldetektion für verdeckte Nägel (Zusatz)

### Takeaway
Industrielle Tunnel-Metalldetektoren für Holz (Mesutronic, Sesotec, CEIA u. a.) werden nur auf Anfrage angeboten;
einziger belegter Preis ist ein Gebrauchtgerät Mesutronic für 6.500 EUR netto. Neu ist **[Schätzung]** mit 8.000–25.000
EUR je nach Tunnelgröße (für 20x30 cm Querschnitt plus Abstand) zu rechnen — damit sprengt ein Detektor allein das
5–10-k-Budget.

### Cited Findings
- Mesutronic: Metalldetektoren im Sägewerk schützen Sägeblätter; Tunnelgeräte für Förderband/Schwingrinne;
  Produktreihe METRON 05 CO (Rundholz), METRON 05 D (teilbarer Tunnel), METRON 05 VT; keine Preise —
  [Mesutronic Holz](https://mesutronic.de/en/category/wood), [Mesutronic Sägewerk-Fallbeispiel](https://www.mesutronic.de/en/cutting-without-a-break-increasing-process-reliability-in-sawmills-with-metal-detectors/), [Katalog Holzindustrie](https://pdf.directindustry.com/pdf/mesutronic-gmbh/inspection-systems-timber-industry/39454-1084932.html)
- Gebraucht: Mesutronic MN 5.0 CI 400/200 für 6.500 EUR zzgl. MwSt., verhandelbar (spanischer Händler) —
  [Machineseeker](https://www.machineseeker.com/mesutronic-m/i-22841180)
- Weitere Tunnel-Metalldetektoren, z. B. Cassel METAL SHARK OCTA — [DirectIndustry](https://www.directindustry.com/prod/cassel-messtechnik/product-41245-490807.html)
- Gebrauchte Sesotec- und Loma-Geräte gelistet, ohne Preise — [maschinensucher Metalldetektoren](https://www.maschinensucher.de/mss/metalldetektoren)

### Inferences
- Für das Forschungsprojekt sinnvoller **[Bewertung]**: (a) Handdetektor/Stabdetektor für Stichproben und
  Ground-Truth beim Labeln (Hobby-/Sicherheits-Handgeräte ab ca. 40–1.100 EUR laut Kaufland-Treffern, aber nicht für
  Holz kalibriert — [Kaufland Garrett](https://www.kaufland.de/product/534504642/)); (b) gebrauchter Tunneldetektor
  als spätere Erweiterung; (c) Nägel/Nagellöcher optisch als YOLO-Klasse (sichtbare Köpfe, Rostflecken) — verdeckte
  Nägel bleiben optisch unsichtbar.
- Ein Tunnel-Metalldetektor braucht eine metallfreie Zone in der Fördertechnik (Kunststoffrollen/Gurt im Bereich der
  Spule) — wichtig für die Rahmenplanung **[Schätzung, Herstellerangaben prüfen]**.

### Gaps
- Keine Neupreise für Mesutronic, CEIA, Sesotec, Lorenz, Goring Kerr gefunden (alle "auf Anfrage"). CEIA nicht
  gefunden.

## 7. Referenzkosten industrieller Scanner und Forschungsprototypen

### Takeaway
Hersteller (MiCROTEC, WEINIG, LuxScan/Weinig, Lucidyne, Woodeye/MiCROTEC, Nukor) veröffentlichen keine Preise. Einziger
belegter Wert: gebrauchter Weinig-Scanner + Kappsäge (nur oben/unten) für 85.000 USD. Das Startup-Angebot von ~100 k EUR
liegt damit im Bereich eines (gebrauchten) Industriescanners. Neue 4-seitige Industriescanner liegen **[Schätzung]** im
mittleren sechsstelligen Bereich und darüber.

### Cited Findings
- Gebrauchter Weinig-Scanner mit Kappsäge 85.000 USD, nur oben/unten, Käufer trägt Abbau/Fracht — [woodweb.com](https://woodweb.com/exchanges/machinery/posts/556092.html)
- WEINIG: Preis abhängig vom Bedarf, unverbindliches Angebot nach Gespräch; Einstiegsscanner EasyScan Lite C "mit KI",
  EasyScan+ S "high performance – low investment" — [WEINIG Scanner](https://m.weinig.com/en/solid-wood/scanner-systems.html), [EasyScan Lite C](https://m.weinig.com/en/solid-wood/scanner-systems/easyscan/easyscan-rl.html), [EasyScan+ S](https://m.weinig.com/en/solid-wood/scanner-systems/easyscan-series/easyscan-s.html)
- MiCROTEC Goldeneye/Woodeye: keine Preise; gebrauchter Goldeneye GLD 600 DSC (2014) Preis auf Anfrage;
  Kundenangabe Ausbeutesteigerung von ca. 80 % auf 98 % — [MiCROTEC Goldeneye](https://microtec.eu/en/products/goldeneye), [MiCROTEC Woodeye](https://microtec.eu/en/products/woodeye), [Exapro](https://www.exapro.com/microtec-goldeneye-gld-600-dsc-p260225170)
- MiCROTEC übernahm WoodEye (schwedisch) 2015 — [timber-online](https://www.timber-online.net/wood_products/2025/07/it-s-what-s-inside-that-counts.html)
- Nukor (Südafrika) EasyScan-Reihe mit KI-Fehlererkennung, ohne Preis — [Nukor EasyScan](https://www.nukor.co.za/product/easyscan-series/)
- Wood Business (2016) Marktübersicht Scanner: keine Preise — [woodbusiness.ca](https://www.woodbusiness.ca/scanning-options-3644/)
- Review 2023: Systeme zur Holzfehlererkennung mit geringeren Kosten und breiterer Zielgruppe zu entwickeln, sei
  bedeutsam — [Applied Sciences 2023 via DOAJ](https://doaj.org/article/eeca3702406b42719b825b4902097365)

### Inferences
- Für den Antrag/Vergleich mit dem Startup: Ein 5–10-k-Eigenbau ist kein gleichwertiger Industriescanner (Durchsatz,
  4-seitig, Robustheit, Service), sondern ein Forschungsdemonstrator; das Gegenargument liegt in offener Hard-/Software,
  Anpassbarkeit an Altholz und Datenhoheit **[Bewertung]**.

### Gaps
- Kein dokumentierter Forschungsprototyp mit veröffentlichten Gesamtkosten (Zeilenkamera + Encoder + Kostenaufstellung)
  gefunden. Keine Preise für LuxScan, Lucidyne, Woodeye neu.

## 8. Kostentabellen je Szenario

Hinweis: Fast alle Summen sind **[Schätzung]**, gestützt auf die oben belegten Einzelpreise. Brutto inkl. MwSt.
Kamera/Optik/Licht nur als Platzhalter (andere Teilrecherche).

### Szenario 1: Low-Cost-Prototyp < 5.000 EUR (1-seitig, Wenden von Hand)

| Komponente | Ausführung | Preis EUR | Beleg |
|---|---|---|---|
| Förderung | 2 x 2–3 m nicht angetriebene Rollenbahn (Stahlrollen, gebraucht/China) oder Holzböcke + Rollen, seitliche Führungsrollen | 300–900 | Schätzung |
| Vorschub | von Hand durchschieben | 0 | – |
| Encoder | Messrad (60–140 EUR) + Inkrementalgeber 1024/U (ca. 150–250 EUR) oder China-Geber+Rad (30–60 EUR) | 50–400 | RS Kübler/Wachendorff (s. o.), China Schätzung |
| Lichtschranken | 2 x Reflexlichttaster (China bzw. Marke) | 20–250 | Schätzung |
| Trigger/Steuerung | Raspberry Pi Pico/ESP32 + Optokoppler, 24-V-Netzteil, Klemmen | 50–150 | Schätzung |
| Rahmen/Kameraportal | Alu 40x40 Nut 8 No-Name, ca. 15–25 m + Verbinder | 400–900 | Kaufland ≈ 21–24 EUR/m + Schätzung Verbinder |
| Lichtschutz | Platten/Bürstenleisten | 100–300 | Schätzung |
| Rechner | Jetson Orin Nano Super Dev Kit + 1 TB NVMe | 400–450 | RS IE 345,58 EUR + Schätzung SSD |
| Speicher Daten | 2 TB externe SSD | 120–200 | Schätzung |
| Kamera/Optik/Licht | Platzhalter (z. B. 1 Flächen- oder günstige Zeilenkamera) | 1.000–2.000 | andere Teilrecherche |
| Kleinteile, Kabel, Not-Aus-Taster | | 100–300 | Schätzung |
| **Summe** | | **ca. 2.500–5.000** | Schätzung |

### Szenario 2: Zielaufbau 5.000–10.000 EUR (2-seitig oben/unten oder 1-seitig mit Antrieb)

| Komponente | Ausführung | Preis EUR | Beleg |
|---|---|---|---|
| Förderung | Variante A: Schwerlast-Rollenbahn (300 kg/m, z. B. Blume-Klasse), 2 x 3 m, mit Messspalt für Unterseite; Variante B: Werkstück fest, Kamera-Portal auf selbstgebauter 4–6-m-Achse (Zahnriemen, Schrittmotor/Servo) | 800–2.000 (A) bzw. 600–1.500 (B) | Traglast: udobaer; Preise Schätzung |
| Antrieb (optional) | Getriebemotor 0,37–0,75 kW + FU 0,75 kW (170–340 EUR) an einem angetriebenen Rollensegment / Treibrolle | 400–1.000 | FU: RS/eBay; Motor Schätzung |
| Encoder | Markengeber 1024–2048/U + Messrad mit Federandruck (Kübler/Wachendorff/Baumer) | 250–600 | RS (s. o.) + Schätzung |
| Lichtschranken | 2–3 x Marken-Reflexlichttaster | 120–400 | Schätzung |
| Steuerung | Pico/ESP32 oder kleine Kleinsteuerung; Not-Halt-Kreis mit Sicherheitsrelais, falls Antrieb | 150–700 | Schätzung |
| Rahmen | Alu 40x40/40x80 Nut 8 (No-Name oder Motedis), Kamerahalter höhenverstellbar für 5–30 cm Querschnitt | 800–1.800 | Kaufland-Profilpreis + Schätzung |
| Lichtschutz/Gehäuse | geschlossener Messtunnel, Bürsten am Ein-/Auslauf | 300–800 | Schätzung |
| Rechner | Jetson Orin NX 16GB (Schätzung 800–1.200) oder AGX Orin 64GB (2.473) oder Linux-PC mit RTX-GPU | 800–2.500 | RS DE AGX; Rest Schätzung |
| Speicher | 2–4 TB NVMe | 150–300 | Schätzung |
| Kamera/Optik/Licht | Platzhalter: 2 Kameras (oben + unten im Spalt) | 2.000–4.000 | andere Teilrecherche |
| Kleinteile, Kabel, Schaltschrank klein | | 200–500 | Schätzung |
| **Summe** | | **ca. 6.000–10.000** | Schätzung |

4-seitig im Szenario 2 nur, wenn Kameras sehr günstig sind (z. B. 4 x Flächen-/Zeilenkamera je < 800 EUR inkl. Optik
und Licht); sonst 2-seitig plus einmal Kippen.

### Szenario 3: Industrieniveau (4-seitig, angetrieben, Metalldetektor)

| Komponente | Ausführung | Preis EUR | Beleg |
|---|---|---|---|
| Förderung | angetriebene Schwerlast-Rollenbahn/Kettenförderer Ein- und Auslauf 2 x 4–6 m, Andruckrollen, Messspalt | 8.000–25.000 | Schätzung (Neupreis Gurtförderer 2,6 m ab 3.080 EUR als Untergrenze, eBay) |
| Antriebe | 2–3 Getriebemotoren + FU, ggf. Servo | 1.500–4.000 | FU-Preise RS + Schätzung |
| Encoder | Industrie-Messradsystem, redundant | 500–1.500 | RS + Schätzung |
| Sensorik | Lichtgitter/Lichtschranken, Höhen-/Breitenmessung (Laser-Triangulation optional) | 1.000–5.000 | Schätzung |
| Steuerung/Sicherheit | SPS mit Sicherheitstechnik, Schutzzäune/Lichtgitter, Schaltschrank, CE-Verfahren nach MRL/MVO | 5.000–20.000 | Schätzung |
| Rahmen/Gehäuse | item/Bosch Rexroth oder Stahlbau, gekapselt, Staubschutz | 3.000–10.000 | Schätzung |
| Rechner | Industrie-PC mit GPU + Framegrabber, oder AGX Orin je Seite | 3.000–10.000 | RS AGX 2.473 EUR; Rest Schätzung |
| Kamera/Optik/Licht | 4 Seiten, Zeilenkameras, ggf. 3D | 15.000–40.000 | andere Teilrecherche / Schätzung |
| Metalldetektor | Tunnel-Metalldetektor für Holz (Mesutronic/Sesotec o. ä.) | 8.000–25.000 neu; gebraucht ab 6.500 netto | Machineseeker (gebraucht); Neupreis Schätzung |
| Engineering/Inbetriebnahme | | erheblich, nicht beziffert | Gap |
| **Summe Hardware** | | **ca. 45.000–140.000** | Schätzung |

Einordnung: Das Startup-Angebot von ~100 k EUR liegt in diesem Bereich; ein gebrauchter Industriescanner (nur oben/unten)
wurde für 85.000 USD angeboten ([woodweb.com](https://woodweb.com/exchanges/machinery/posts/556092.html)).

