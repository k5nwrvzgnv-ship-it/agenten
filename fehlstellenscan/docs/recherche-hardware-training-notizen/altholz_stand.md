# Stand der Technik: Scannen von Altholz / rückgebautem Bauholz (Fehlstellen, Wiederverwendungs-Sortierung)

Stand der Recherche: 20.11.2026. Etwa 17 Such- und Abrufschritte. Einige Seiten (ScienceDirect, SINTEF) waren gesperrt (HTTP 403), dort stammen die Angaben nur aus Suchtreffern oder Projektseiten. Unsicheres ist jeweils markiert.

## 1. Forschungsprojekte zum Scannen und Sortieren von rückgebautem Holz (Sensoren)

### Takeaway
Die Forschung zu rückgebautem Bauholz misst vor allem Festigkeit und Steifigkeit: visuelle Sortierung, Eigenfrequenz/Ultraschall, CT, LiDAR. Kamerabasierte KI zum Erkennen von Fehlstellen an Altholz ist neu: Die einzige klar passende Arbeit (Cornell 2025) setzt auf Tablet- und Handykameras. Im deutschen Altholz-Recycling (Hackschnitzel, Kategorien A I bis A IV) wird dagegen NIR-Spektroskopie eingesetzt, um Schadstoffe zu erkennen, nicht um Fehlstellen zu finden.

### Cited Findings
- **InFutUReWood** (EU, 2019–2022): Design for Deconstruction, ein Arbeitspaket zur Eignung von rückgebautem Holz. Ergebnis aus mehreren Beiträgen: Die normalen visuellen Sortiernormen (VSG) stufen den Großteil des rückgebauten Holzes ab. Brettsperrholz (CLT) aus rückgebautem Holz erreicht in Biegefestigkeit und Steifigkeit die Werte von CLT aus Neuholz. — [Galway WCTE 2023, recovered CLT](https://www.universityofgalway.ie/media/timberengineeringresearchgroup/WCTE-2023---Caitriona---recovered-CLT.pdf); [Galway Repository (WP3-Bericht)](https://researchrepository.universityofgalway.ie/server/api/core/bitstreams/05c17aa1-6fad-48cf-bd12-7857366e7714/content)
- InFutUReWood, ZfP-Versuchsreihe an Eiche: 30 Prüfkörper aus Quercus robur, 135 × 150 mm, 3 m lang; zerstörungsfreie Messungen werden mit den mechanischen Eigenschaften verglichen. Die Zahlen standen nicht im Suchausschnitt. — [proceedings.com 080513-0424](https://www.proceedings.com/content/080/080513-0424open.pdf)
- **Luleå University of Technology / DRASTIC-Projekt (EU):** X-Ray-CT an einzelnen rückgebauten Bauteilen, dazu ein datengetriebenes Modell, das Steifigkeit und Festigkeit vorhersagt. Eigenfrequenz- bzw. Stresswellen-Messung wird als vielversprechend genannt. Laser- und Röntgenscan (nicht CT) gelten als billigere Alternativen. Metallische Verbindungsmittel wurden vor dem CT entfernt. — [LTU DiVA Volltext](https://ltu.diva-portal.org/smash/get/diva2:1925761/FULLTEXT01.pdf); [DRASTIC-PDF](https://drasticproject.eu/sites/default/files/2026-01/Non-Destructive%20Assessment%20of%20Reclaimed%20Timber%20Elements%20Using%20CT%20Scanning%20Methods%20and%20Computational%20Modelling%20Framework%201.pdf); [Zenodo](https://zenodo.org/records/12529234)
- **SINTEF (Norwegen):** Kapitel „Reclaimed timber assessment supported by Lidar scanning“. Der Inhalt war nicht abrufbar (403). — [SINTEF](https://www.sintef.no/en/publications/publication/0198cc85c521-ad007429-3b18-4146-8652-7ebdc4db93e6/)
- **Cornell (Heisel-Gruppe, Circular Construction Lab):** Shi, Bergsagel, Owen, Heisel, „Scalable AI-Driven Automation for Visual Lumber Grading“, Journal of Cleaner Production 533 (2025), 146986. Gegenstand ist ausdrücklich rückgebautes Schnittholz (unregelmäßige Maße, eingebettete Verbindungsmittel, Verwitterung, biologischer Abbau). Die Kette: 2D-Bilder kalibrieren, Fehlstellen auf allen vier Seiten erkennen, Sortierklasse nach normbasiertem Regelwerk vergeben. Gedacht für Alltagsgeräte (Tablet, Handy). Genauigkeit, Modell und Datensatzgröße konnten nicht geprüft werden (Volltext gesperrt). — [Cornell-Projektseite](https://labs.aap.cornell.edu/node/1154); [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0959652625023431)
- **Visuelle Sortierung, angepasst an Abbruchholz (2026):** Die französische Norm stufte rückgebaute Bauteile tendenziell zu hoch ein. Die norwegische Vornorm sortierte mehr aus und unterschätzte die Festigkeit in den meisten Fällen. Die Autoren schlagen einen eigenen Rahmen vor, der Rohdichte und nutzungsbedingte Schäden einbezieht. — [ScienceDirect S0950061826014601](https://www.sciencedirect.com/science/article/abs/pii/S0950061826014601)
- **TU München (Holzbau):** visuelle Sortierung von Fichtenlatten aus rückgebautem Holz, mit Vorschlag für geänderte Regeln in DIN 4074-1. — [TUM-Portal](https://portal.fis.tum.de/en/publications/the-visual-strength-grading-of-norway-spruce-battens-processed-fr/). Dazu 2026 eine Arbeit zur Zugfestigkeits-Vorhersage für Fichtenbretter aus rückgebautem Holz, visuell und maschinell sortiert. — [Springer, Eur. J. Wood Prod. 2026](https://link.springer.com/article/10.1007/s00107-026-02431-3)
- **WIn-Altholz** (FNR/BMLEH, FKZ 2220HV044, abgeschlossen, Meldung 22.06.2026). Koordination HNEE Eberswalde (Fachbereich Holzingenieurwesen, A. Pfriem, inzwischen TU Dresden), Partner Fraunhofer IAP, TH Wildau, IMACS GmbH und Barnimer Dienstleistungsgesellschaft. Ergebnisse:
  - tragbarer NIR-Handscanner (LED-Anzeige, WLAN), unterscheidet A I von A II bis A IV
  - Referenzdatenbank mit 1.700 Proben und 8.000 NIR-Spektren, mit Analytik zu historischen und aktuellen Holzschutzmitteln
  - Wiederverwendungs- und Verwertungsindex nach Maßen, Schäden und Störstoffen
  - Prototyp an verwittertem Holz in der Praxis getestet; eine Genauigkeit wird nicht genannt

  Hinweis: Jan ist an der HNEE, das Projekt kommt also aus dem eigenen Haus. — [FNR-Projektnews](https://www.fnr.de/presse/forschung-live/projektnews/massiv-altholz-lange-werterhaltend-weiternutzen); [Schlussbericht PDF](https://www.fnr.de/fileadmin/projektdatenbank/2220HV044C.pdf)
- **Fraunhofer WKI / Fraunhofer Vision:** NIR-Sortierung von Altholz-Partikeln. Aufbau:
  - Multiplexer-Spektrometer mit InGaAs-Detektor, 1400–1900 nm, 40 Lichtleiter-Sensoren, 4 × 300-W-Halogen
  - Sortieranlage von RTT-Steinert: Partikel 15–300 mm, Band 600 mm, bis 2 m/s, 40 Luftdüsen
  - Ergebnisse: Kunststoffe (PE, PP, PVC, PLA) unterscheidbar; Vollholz und unbeschichtete Spanplatte von melamin- oder PVC-beschichteten Platten trennbar
  - Holzarten und organische Holzschutzmittel „scheint möglich zu sein“, also nicht belegt

  — [Fraunhofer Vision, Altholz-Recycling](https://www.vision.fraunhofer.de/de/technologien-anwendungen/technologien/hyperspektrale-bildverarbeitung/altholz-recycling.html). WKI will außerdem metallische Fremdkörper (Nägel, Schrauben) und Holzschutzmittel aufspüren und entfernen. — [bvse-Meldung](https://www.bvse.de/verwertung/nachrichten-altholz-ersatzbrennstoffe-bioabfall/10651-fraunhofer-wki-erforscht-wiederverwendung-von-holz.html); [Meinlschmidt, Marktübersicht Altholz (Folien)](https://www.3-n.info/media/4_Downloads/pdf_NwsTrmn_3NVrnstltng_HolzBauInnovationstage_Meinlschmidt.pdf); [Meinlschmidt 2013, Neue Wege der Sortierung](https://tkv-wissen.de/wp-content/uploads/2023/06/2013_RuR_151_176_Meinlschmidt.pdf)
- **REUSE-Leitfaden (WCTE):** Für die visuelle Sortierung von wiederverwendetem Holz wird DIN 4074-1:2012-06 oder eine gleichwertige nationale Norm angewandt. Das weitere Verfahren gilt nur für S10 oder besser. — [proceedings.com 080513-0218](https://www.proceedings.com/content/080/080513-0218open.pdf)
- **Klassische Lumber-Scanner (USDA):** Mehrsensor-Systeme (Kamera, Röntgen usw.) helfen, echte Merkmale von Oberflächenflecken zu unterscheiden. Ein Prototyp hielt natürliche Verfärbungen fälschlich für Fehler. — [USDA Treesearch 304](https://research.fs.usda.gov/download/treesearch/304.pdf); [USDA Treesearch 41881](https://research.fs.usda.gov/download/treesearch/41881.pdf)

### Inferences
- Nach Sensor geordnet:
  - RGB bzw. KI-Bild: Cornell 2025
  - CT: Luleå/DRASTIC
  - LiDAR: SINTEF
  - Eigenfrequenz/Ultraschall: InFutUReWood, Luleå
  - NIR: WIn-Altholz, Fraunhofer WKI (Chemie, Kategorie)
  - Metall: Magnete und Detektoren im Recycling
- Ein bildbasiertes YOLO für Fehlstellen an Altholz-Balken ist damit in Europa praktisch eine Lücke. Mit WIn-Altholz (NIR, Index) an der HNEE gibt es direkt anschließbare Vorarbeit.
- Gegen eine reine Kameralösung sprechen die Befunde zur Festigkeit: Visuelle Merkmale sagen die Festigkeit von Altholz schlecht voraus (95 % Ausschuss nach VSG, siehe Abschnitt 4). Kamera-Fehlstellen sollten deshalb mit Rohdichte oder Eigenfrequenz kombiniert werden.

### Gaps
- Zu ETH Zürich, BFH (Biel), TU Wien, Aalto und Thünen-Institut wurden im Rahmen der Suchgrenze keine konkreten Altholz-Scanprojekte gefunden. Das heißt nicht, dass es keine gibt.
- Zu Circular Timber / CircWood fanden sich keine eindeutigen Treffer. Ein CORDIS-Projekt 101180622 tauchte auf, wurde aber nicht geprüft.
- Die Endzahlen von InFutUReWood zur ZfP (Korrelationen) wurden nicht abgerufen.

## 2. Produkte und Startups (Altholz-Scan, Sortierung, ~100.000-EUR-Angebote)

### Takeaway
Ein marktreifes Produkt, das Altholz-Balken optisch auf Fehlstellen scannt und für die Wiederverwendung sortiert, wurde in Deutschland nicht gefunden. Am nächsten kommt Urban Machine (USA): 3D-Bildverarbeitung plus Roboter entfernt Nägel, ein Metalldetektor prüft am Ende. Im Recycling sind NIR-Sortierer (z. B. RTT-Steinert mit Fraunhofer) und Magnet- bzw. NE-Abscheider Stand der Technik. Ein konkretes Angebot um 100.000 EUR wurde nicht gefunden.

### Cited Findings
- **Urban Machine** (Oakland, CA; CEO Eric Law). Ablauf:
  1. Drahtbürste entfernt Verschmutzung (Gipsreste, Rost)
  2. KI-Bildverarbeitung mit 3D-Bildgebung erkennt Art und Lage der Verbindungsmittel
  3. Roboterarme mit passenden „Pickern“ ziehen sie
  4. Metalldetektor prüft am Ende

  Geplant ist ein Röntgenschritt für Faser und Holzart. Angegebene Leistung: 16.000–20.000 board feet (etwa 38–47 m³) bzw. ungefähr eine LKW-Ladung je Tag und Maschine. Ein Pilot bei Zanker war 2023 abgeschlossen, Napa lief noch. Laut einer Präsentation waren Validierung 2024 und Serienfertigung 2025 geplant; ob das eingetreten ist, ist unbelegt. — [C&D Recycler](https://cdrecycler.com/article/ai-technology-aids-urban-machine-in-reclaiming-wood-waste-at-zanker-facility); [ENR-Präsentation](https://www.enr.com/ext/resources/events/futuretech/presentations/ROBOTIC-CONSTRUCTION-DEBRIS-RECYCLING_A-REAL-NAIL-BITER.pdf)
- US-Patente „System and method for autonomously removing fasteners embedded in wood products“ beschreiben einen Röntgen-Zeilenscanner, an dem Werkstücke per Stapler vorbeigefahren werden. Daraus entsteht ein 3D-Modell mit Lage und Art der Verbindungsmittel (Nagel, Schraube, Klammer). Ob die Patente Urban Machine gehören, ist unbestätigt. — [US 12,409,539](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12409539); [US 11,806,853](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11806853); [US 12,583,066](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12583066)
- **Concular und TRIQBRIQ** (Deutschland): Concular vermittelt Material aus Rückbau, TRIQBRIQ fertigt daraus Holzbausteine (BRIQs, gesteckt mit Holzdübeln, ohne Metall). Erstes Altholz kam aus dem Rückbau für einen großen Discounter. Über Scan-Technik wird nichts berichtet. — [Concular](https://concular.de/kreislauffaehige-innovation-im-holzbau-von-concular-und-triqbriq/); [Allgemeine Bauzeitung](https://allgemeinebauzeitung.de/abz/briqs-von-triqbriq-start-up-fertigt-bausteine-aus-altholz-50173)
- **RTT-Steinert:** baut die NIR-Sortieranlage für Altholz-Partikel im Fraunhofer-Projekt (Daten siehe Abschnitt 1). — [Fraunhofer Vision](https://www.vision.fraunhofer.de/de/technologien-anwendungen/technologien/hyperspektrale-bildverarbeitung/altholz-recycling.html)
- **IMACS GmbH:** hat im Projekt WIn-Altholz das Konzept des NIR-Handscanners, die Auswahl der Sensoren und die Integration entwickelt. Ob daraus ein Produkt wird, ist offen. — [FNR](https://www.fnr.de/presse/forschung-live/projektnews/massiv-altholz-lange-werterhaltend-weiternutzen)
- In der Holzwerkstoffindustrie sind Überbandmagnete und NE-Metallabscheider für Altholz üblich. — [Dissertation Uni Hamburg, MDF aus Altholz](https://ediss.sub.uni-hamburg.de/bitstream/ediss/610/1/Dissertation.pdf)
- Für Schnittholz aus Neuholz gibt es Deep-Learning-Sortierscanner, z. B. Lucidyne. Für Altholz ist das nicht belegt. — [NVIDIA-Blog zu Lucidyne](https://blogs.nvidia.com/?p=42591)
- Händler nennen als Prüfschritte für Altholz: visuelle Sortierung, Feuchte, Metalldetektor, Bleifarbentest und bei kritischen Bauteilen Stresswelle oder Ultraschall. Quelle ist ein Handels-Blog. — [J. Gibson McIlvain](https://blog.mcilvain.com/reclaimed-wood-guide.html)

### Inferences
- Für ein Angebot um 100.000 EUR kommen am ehesten diese Anbieter in Frage: Hersteller von Schnittholzscannern (Microtec, Lucidyne, Weinig/LuxScan; deren Altholz-Fähigkeit wurde nicht recherchiert), Sortieranlagen (Steinert, TOMRA) oder Sondermaschinenbau. Belege dafür gibt es in dieser Recherche nicht.
- Urban Machine zeigt das Prinzip „Optik findet und klassifiziert, Metalldetektor prüft“. Das spricht für eine Kombination aus YOLO und induktivem Sensor statt reiner Optik.

### Gaps
- Microtec (Goldeneye, CT.Log), Weinig und TOMRA: Ob sie Altholz-Anwendungen haben, wurde nicht gefunden; die Suche lieferte nichts dazu.
- Preise für Scanner oder Sortieranlagen wurden nicht gefunden.
- Eine Firma, die in Deutschland Altholz-Balken optisch scannt, wurde nicht gefunden.

## 3. Fremdkörper (Nägel, Schrauben) optisch vs. induktiv; Beschichtungen und Kontamination

### Takeaway
Abgebrochene oder versenkte Nägel und Schrauben sind optisch nicht sicher zu finden. Die Praxis kombiniert deshalb: Optik oder 3D für Sichtbares, Metalldetektor oder Röntgen für Verborgenes. Beschichtungen und Holzschutzmittel lassen sich chemisch mit NIR bzw. Hyperspektral erkennen; der Erfolg ist für Beschichtungen belegt, für organische Schutzmittel nur „scheint möglich“.

### Cited Findings
- Urban Machine: 3D-Bildverarbeitung klassifiziert sichtbare Verbindungsmittel, ein Metalldetektor prüft am Ende. — [C&D Recycler](https://cdrecycler.com/article/ai-technology-aids-urban-machine-in-reclaiming-wood-waste-at-zanker-facility)
- Röntgen-Zeilenscan erkennt innenliegende metallische Objekte und erzeugt ein 3D-Modell der Verbindungsmittel (Patent). — [US 12,409,539](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12409539)
- Handgeführte und Laserlinien-Metalldetektoren für Altholz-Bretter und -Balken werden vor dem Sägen oder Hobeln eingesetzt (Herstellerangaben, z. B. Lumber Wizard). — [Amazon, Lumber Wizard 5](https://www.amazon.com/Wizard-Industries-Lumber-5/dp/B07FG21H9M)
- Eine Suche nach YOLO bzw. Deep Learning zur Nagelerkennung an Altholz fand keine einschlägige Arbeit, nur allgemeine Fehlstellen-YOLOs (Äste, Risse). — [BioResources Review 2021–2025](https://bioresources.cnr.ncsu.edu/resources/recent-advances-in-wood-surface-defect-inspection-using-deep-learning-2021-2025/)
- NIR mit InGaAs (1400–1900 nm) trennt melamin- oder PVC-beschichtete Platten von unbeschichtetem Holz; organische Holzschutzmittel „scheint möglich“. — [Fraunhofer Vision](https://www.vision.fraunhofer.de/de/technologien-anwendungen/technologien/hyperspektrale-bildverarbeitung/altholz-recycling.html)
- Der NIR-Handscanner aus WIn-Altholz unterscheidet A I von A II–IV; Referenzdaten siehe Abschnitt 1 (8.000 Spektren). — [FNR](https://www.fnr.de/presse/forschung-live/projektnews/massiv-altholz-lange-werterhaltend-weiternutzen)
- Ältere Arbeit zu prozessanalytischen Methoden, die Kontamination beim Altholz-Recycling erkennen. — [ResearchGate](https://www.researchgate.net/publication/278302825_Untersuchung_Weiterentwicklung_und_Adaption_prozessanalytischer_Methoden_zur_Erkennung_von_Kontaminationen_beim_Recycling_von_Altholz)
- Altholzverordnung, amtlicher Text mit Anhang „Zuordnung gängiger Altholzsortimente im Regelfall“. — [gesetze-im-internet.de/altholzv](https://www.gesetze-im-internet.de/altholzv). Die Einteilung (A I naturbelassen bzw. nur mechanisch bearbeitet; A II verleimt, gestrichen, beschichtet, ohne halogenorganische Verbindungen und ohne Holzschutzmittel; A III mit halogenorganischen Verbindungen in der Beschichtung, ohne Holzschutzmittel; A IV mit Holzschutzmitteln, z. B. Bahnschwellen, Masten) stammt aus Vorwissen; der Wortlaut wurde in dieser Recherche nicht abgerufen. Eine Novelle wird gefordert (BAV-Eintrag im Lobbyregister vom 23.05.2025, Vorhaben „Kaskadennutzung“), ein Beschluss wurde nicht gefunden. — [Lobbyregister RV0016458](https://www.lobbyregister.bundestag.de/inhalte-der-interessenvertretung/regelungsvorhabensuche/RV0016458); [EUWID](https://www.euwid-recycling.de/news/wirtschaft/bundestagswahl-bav-fordert-novelle-der-altholzverordnung-030225/)
- Laut FNR erlaubt die geltende AltholzV weder die stoffliche Verwertung als Vollholz noch die Nutzung von A IV; das wird als Hemmnis genannt. — [FNR](https://www.fnr.de/presse/forschung-live/projektnews/massiv-altholz-lange-werterhaltend-weiternutzen)

### Inferences
- RGB-YOLO kann sichtbare Nagelköpfe, Löcher, Farbreste und Verfärbungen erkennen, aber keine A-Kategorie sicher bestimmen und keine verborgenen Metallteile finden. Für eine belastbare Aussage braucht es induktive Metalldetektion (billig, robust) und für die Kategorie NIR.

### Gaps
- Es wurden keine Messwerte gefunden, die optische und induktive Nagelerkennung an Altholz vergleichen (Trefferquote).
- Die Genauigkeit des WIn-Altholz-Scanners steht vermutlich im Schlussbericht, wurde aber nicht gelesen.

## 4. Sortierregeln für wiederverwendetes Bauholz

### Takeaway
Eine eigene CEN- oder DIN-Norm für rückgebautes Bauholz wurde nicht gefunden. In der Praxis gilt DIN 4074-1 bzw. EN 14081/EN 1912, mit Abwandlungen. Ob das funktioniert, ist umstritten: Je nach Studie liegt die Ausbeute bei 91 % oder 95 % fallen durch. Es gibt Vorschläge für geänderte Regeln (TUM, französisch-norwegischer Vergleich 2026).

### Cited Findings
- Bretter aus rückgebauten Sparren ließen sich nach DIN 4074-1:2012 sortieren, mit 91 % Ausbeute in S13, S10 oder S7. — [TUM-Portal](https://portal.fis.tum.de/en/publications/the-visual-strength-grading-of-norway-spruce-battens-processed-fr/) (laut Suchzusammenfassung, nicht im Volltext geprüft)
- Rückgebaute Fichte: Nach NF B52001-1 und DIN 4074-1 fallen rund 95 % durch; die visuellen Regeln schätzen die mechanischen Eigenschaften schlecht. — [Construction and Building Materials 2023 (ndt.net)](https://www.ndt.net/article/construction_and_building_materials/papers/1-s2.0-S0950061823021566-main.pdf)
- Die beiden Befunde passen zusammen, wenn man unterscheidet: Aus Altholz neu aufgeschnittene Bretter kommen gut durch, ganze Altbauteile schlecht. Das ist eine Deutung, siehe Inferences.
- REUSE-Leitfaden: visuelle Sortierung nach DIN 4074-1:2012-06, danach weiter nur mit S10 oder besser. — [proceedings.com](https://www.proceedings.com/content/080/080513-0218open.pdf)
- CE-Kennzeichnung ist bei wiederverwendetem Bauholz nur nötig, wenn es erneut als tragendes Bauprodukt in Verkehr gebracht wird; Sortierung nach EN 1912 und nationaler Norm (für Laubholz in Deutschland DIN 4074-5). Quelle ist ein Händler. — [Frank Pouwer](https://www.frankpouwer.com/what-are-the-ce-marking-requirements-for-air-dried/)
- Norwegische Vornorm für rückgebautes Holz: sortiert konservativ aus. Die französische Norm stuft zu hoch ein. Vorschlag eines eigenen Rahmens mit Rohdichte und nutzungsbedingten Schäden. — [ScienceDirect 2026](https://www.sciencedirect.com/science/article/abs/pii/S0950061826014601)
- 2026: visuelle und maschinelle Sortierung von Fichtenbrettern aus rückgebautem Holz im Vergleich (Zugfestigkeit). — [Springer 2026](https://link.springer.com/article/10.1007/s00107-026-02431-3); ebenso [Wood Material Science & Engineering 2026](https://www.tandfonline.com/doi/pdf/10.1080/17480272.2026.2615820)

### Inferences
- Für einen Scanner heißt das: Die Fehlstellen-Klassen sollten über die DIN-4074-Merkmale (Äste, Risse, Faserneigung, Mark, Verfärbung) hinaus nutzungsbedingte Schäden erfassen: Nagel- und Bohrlöcher, Kerven und Ausklinkungen, Insektenfraß, Fäule, Farbreste.

### Gaps
- Die Schweizer Leitfäden (Lignum, BFH) und die britischen (TRADA, reclaimed timber) wurden nicht gefunden bzw. nicht geprüft.
- Den genauen Titel und Status der norwegischen Vornorm konnte ich nicht ermitteln (ScienceDirect gesperrt).
- Den Stand einer CEN-TS bei CEN/TC 124 konnte ich nicht ermitteln.

## 5. Öffentliche Datensätze zu Holzfehlern (für YOLO-Vortraining)

### Takeaway
Der beste offene Datensatz ist Kodytek et al. (VSB Ostrava), erschienen in F1000Research, nicht in Scientific Data: 20.275 Bilder, 10 Klassen, Boxen und Segmentierungsmasken, CC BY 4.0. Er zeigt Neuholz aus dem Sägewerk und enthält keinen Datensatz zu Altholz. Einen öffentlichen Altholz-Datensatz habe ich nicht gefunden.

### Cited Findings
- **Kodytek, Bodzas, Bilik (2022)**, „A large-scale image dataset of wood surface defects for automated vision-based quality control processes“, F1000Research 10:581, DOI 10.12688/f1000research.52903.2.
  - 20.275 Bilder: 1.992 ohne Fehler, 18.283 mit Fehlern; über 43.000 gelabelte Fehler
  - 2.800 × 1.024 px, BMP
  - Trilineare Zeilenkamera JAI SW-4000TL, Objektiv 50 mm, LED-Zeilenlicht Chromasens Corona II, Band 9,6 m/s in einem Sägewerk; 16,66 px/mm × 6,67 px/mm
  - Holzart nicht angegeben
  - Klassen (Vorkommen): Lebender Ast 21.224; Toter Ast 11.985; Harz 3.455; Ast mit Riss 2.276; Riss 2.169; Mark 1.181; Quartzity 1.075; Fehlender Ast 503; Bläue 96; Überwallung 10
  - Labels: Box je Bild als Textdatei (Klasse plus links/oben/unten/rechts) und Semantik-Maske als BMP mit Farbcode
  - Lizenz CC BY 4.0; Download über [Zenodo 10.5281/zenodo.4694695](https://zenodo.org/record/4694695), Label-Software unter 10.5281/zenodo.4904736
  - Baseline: modifiziertes ResNet-50, 81 % Genauigkeit, viele Fehlalarme

  — [PMC9277195](https://pmc.ncbi.nlm.nih.gov/articles/PMC9277195/); [F1000Research](https://f1000research.com/articles/10-581/v2)
- **University of Oulu (Silvén et al. 2003):** 839 RGB-Bilder von Fichte, 488 × 512 px, 8 Bit, Rechtecke von etwa 2,5 × 2,5 cm von Hand gelabelt. Den aktuellen Download und die Lizenz konnte ich nicht prüfen. — [Fang et al. 2021, BioResources (beschreibt den Datensatz)](https://bioresources.cnr.ncsu.edu/wp-content/uploads/2021/06/BioRes_16_3_5390_Fang_GCZY_Accurate_Automated_Detec_Surface_Knots_Sawn-Timbers_18688.pdf)
- **UEF Spectral Image Database of Nordic Sawn Timbers** (Univ. Eastern Finland): spektrale Bilder von Schnittholz; Größe und Lizenz nicht geprüft. — [UEF](https://sites.uef.fi/spectral/?p=874)
- **VNWoodKnot** (Mendeley Data, mehrere Versionen): Datensatz zur Erkennung und Klassifikation von Ästen; Größe und Lizenz nicht geprüft. — [Mendeley](https://data.mendeley.com/datasets/vnst548g5n)
- **Kaggle:** Ableitungen des Kodytek-Satzes, z. B. 4.000 Bilder, 8 Klassen, im YOLOv5-Format. Den Link selbst habe ich nicht geprüft. — [awesome-industrial-datasets](https://github.com/jonathanwvd/awesome-industrial-datasets/blob/master/markdown/large_scale_image_dataset_of_wood_surface_defects.md)
- **Roboflow Universe:** Wood Defects (YOLO Wood Detection, CC BY 4.0, u. a. knot_with_crack); Wood Defect Detection (Defect Detection, 3.258 bzw. 4.169 Bilder); Wood-Defect (Golden Y, 3.773 Bilder). Herkunft oft Kodytek-Ausschnitte, Qualität uneinheitlich. — [Roboflow 1](https://universe.roboflow.com/yolo-wood-detection/wood-defects-irc4o-anwwb); [Roboflow 2](https://universe.roboflow.com/defect-detection-w4mv8/wood-defect-detection-9w3x4); [Roboflow 3](https://universe.roboflow.com/yolo11-yqwwf/wood-defect-detection-dataset-w0ws3)
- **OptiWood-YOLO (Preprint 09/2026):** neuer Industriedatensatz mit 6 Klassen (Blasen, Riss, Keilzinkung, Hobelausriss, Kratzer, Faltenbildung) und der Hilfsklasse Objects, ohne Äste. — [Preprints.org](https://www.preprints.org/manuscript/202609.0951)
- Spanplatten-Datensatz (Roboflow) mit 950 Bildern, 4 Klassen (toter Ast, lebender Ast, Riss, Narbe), verwendet in einer YOLOv8n-Arbeit. — [BioResources 2025](https://bioresources.cnr.ncsu.edu/wp-content/uploads/2025/02/BioRes_20_2_2556_Li_ZY_Wood_Panel_Defect-Detection_Improved_YOLOv8n_24141.pdf)

### Inferences
- Kodytek eignet sich gut zum Vortraining für Ast und Riss (Lizenz frei, viele Boxen). Die Bildgeometrie ist anisotrop (6,67 px/mm in Laufrichtung); beim Umrechnen auf YOLO-Kacheln die Auflösung angleichen.
- Altholz-typische Klassen (Nagel und Nagelloch, Schraube, Farbe, Fäule, Insekt, Verwitterung) fehlen in allen gefundenen Datensätzen. Sie müssen selbst gelabelt werden.

### Gaps
- Einen Datensatz zu Altholz bzw. rückgebautem Holz habe ich nicht gefunden. Ob die Cornell-Gruppe Daten veröffentlicht hat, ist unbekannt.
- Lizenzen von Oulu, VNWoodKnot, UEF und dem Kaggle-Spiegel wurden nicht geprüft.

## 6. Berichtete Ergebnisse (Genauigkeit, Geschwindigkeit) bei der Fehlstellen-Erkennung an Altholz

### Takeaway
Belastbare, veröffentlichte Kennzahlen (mAP, Geschwindigkeit) speziell für Altholz habe ich nicht gefunden. Es gibt nur Zahlen zur Festigkeitssortierung und eine Durchsatzangabe von Urban Machine. Für Neuholz sind YOLO-Ergebnisse zahlreich, Übersicht im BioResources-Review.

### Cited Findings
- Urban Machine: 16.000–20.000 board feet pro Tag und Maschine (Herstellerangabe). — [ENR-Präsentation](https://www.enr.com/ext/resources/events/futuretech/presentations/ROBOTIC-CONSTRUCTION-DEBRIS-RECYCLING_A-REAL-NAIL-BITER.pdf)
- Kodytek (Neuholz): ResNet-50-Baseline mit 81 % Genauigkeit. — [PMC9277195](https://pmc.ncbi.nlm.nih.gov/articles/PMC9277195/)
- YOLOv5 erkennt Äste auf Schnittholz „genau“; Zahlen nicht im Ausschnitt. — [BioResources, Fang et al.](https://bioresources.cnr.ncsu.edu/resources/accurate-and-automated-detection-of-surface-knots-on-sawn-timbers-using-yolo-v5-model/)
- Review der Deep-Learning-Fehlstellenerkennung 2021–2025, als Einstieg in YOLO-Kennzahlen für Neuholz. — [BioResources Review](https://bioresources.cnr.ncsu.edu/resources/recent-advances-in-wood-surface-defect-inspection-using-deep-learning-2021-2025/)
- Visuelle Sortierung von Altholz: 91 % Ausbeute (neu aufgeschnittene Bretter) gegenüber 95 % Ausschuss (rückgebaute Fichte, VSG). — [TUM](https://portal.fis.tum.de/en/publications/the-visual-strength-grading-of-norway-spruce-battens-processed-fr/); [ndt.net](https://www.ndt.net/article/construction_and_building_materials/papers/1-s2.0-S0950061823021566-main.pdf)

### Inferences
- Wer belastbare Altholz-Kennzahlen veröffentlicht, füllt eine Lücke. Ein eigener, gut gelabelter Altholz-Datensatz hätte Neuigkeitswert.

### Gaps
- Die Kennzahlen der Cornell-Arbeit (JCP 2025) sind nicht abrufbar (Paywall bzw. 403). Sie sind die wichtigste offene Quelle.
- Die Genauigkeit des WIn-Altholz-NIR-Scanners steht vermutlich im FNR-Schlussbericht, wurde aber nicht gelesen.
