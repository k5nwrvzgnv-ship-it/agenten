# Beleuchtung und Laser-Maßmessung für einen optischen Altholz-Oberflächenscanner

Stand: 20.11.2026. Budget gesamt 5–10 kEUR. Preise in EUR, wo möglich; USD-Preise unverändert angegeben. "Schätzung" = nicht quellenbelegt, eigene Einordnung. Recherche mit ca. 20 Tool-Aufrufen; viele Herstellerpreise sind nicht öffentlich.

## (A) Beleuchtung: Bauform, Winkel, Blitz, Abschirmung, Produkte, Industriescanner

### Takeaway
Industrielle Holzscanner (WEINIG/LuxScan, MiCROTEC) kombinieren LED-Beleuchtung mit Farbkameras plus Laserlinie (3D) und Punkt-/Streulaser (Tracheideneffekt); Streiflicht bzw. Photometric Stereo ist für Relief und Risse in der Holzliteratur belegt (Hobelwelligkeit), aber nicht speziell für Altholz-Risse. Für das Budget realistisch: 1–2 Linien-/Balkenleuchten (je ca. 450–2.000 USD) oder DIY-LED-Leisten mit Diffusor in einem abgeschirmten Tunnel; Streiflicht als zweiter, flacher Kanal.

### Cited Findings
**Was Industriescanner nutzen**
- WEINIG CombiScan Evo: standardmäßig Laser- und Farbkameras sowie LED-Beleuchtung und Linienlaser — [Höchsmann-Lexikon CombiScan](https://wtp.hoechsmann.com/en/lexikon/33272/combiscan)
- WEINIG CombiScan Sense (Broschüre 2022): Kombination aus Linienlaser und Punktlaser; Linienlaser v. a. für Äste, Risse, Harzgallen; verbessertes Lasersystem erkennt auch 3D-Oberflächenfehler wie Löcher, Baumkante, Kantenfehler; Standard-Laserkamera bis zu 4 Seiten; optional Röntgen, Feuchte, Formmessung — [WEINIG CombiScan Sense Broschüre 2022](https://wtp.hoechsmann.com/es/lexikon/pdf/wei_combiscan_sense_2022_en.pdf); [WEINIG CombiScan Sense](https://m.weinig.com/en/solid-wood/scanner-systems/combiscan-sense.html)
- WEINIG EasyScan C (Einstieg): Basis = Laserkamera, LED-Beleuchtung, automatische Positionierung; Punktlaser und Farbkameras optional — [Höchsmann-Lexikon EasyScan C](https://wtp.hoechsmann.com/en/lexikon/35829/weinig_easyscan_c)
- LuxScan (seit 2007 WEINIG-Gruppe, >400 Scanner verkauft): kombiniert Laserkameras, Farbkameras und Röntgen; Software OptiCore AI mit Deep Learning zur Fehlerklassifikation — [LuxScan Broschüre](https://wtp.hoechsmann.com/ru/lexikon/pdf/lux_brochure_en.pdf); [WEINIG Scanner-Systeme](https://www.weinig.com/en/solid-wood/scanner-systems.html)
- MiCROTEC Goldeneye: Farbkameras, 3D-Kameras für Abmessungen und Laserstreu-Kameras mit Punktlasern für Äste und Faserabweichung; Goldeneye 900: Laserstreuung, 3D-Lasertriangulation, Farbanalyse (+ Röntgen in einzelnen Modellen); Laserstreuung (Tracheideneffekt) bei MiCROTEC seit 1997; bis 1200 m/min (Goldeneye 801/802) — [MiCROTEC Goldeneye 700 Referenz](https://microtec.eu/it/referenze/double-pack-of-scanners); [MiCROTEC Goldeneye](https://stories.microtec.eu/en/products/goldeneye); [Goldeneye 900 Broschüre (Ligna 2019)](https://www.messe.de/apollo/ligna_2019/obs/Binary/A922892/922892_01820474.pdf); [MiCROTEC Zeitleiste (Ligna 2019)](https://www.messe.de/apollo/ligna_2019/obs/Binary/A922893/922893_01820507.pdf)
- Konkrete Lichtquellen (Wellenlänge, Winkel, Blitz/Dauerlicht) der Industriescanner fanden sich in keiner öffentlichen Quelle (siehe Gaps).

**Streiflicht / Photometric Stereo bei Holz**
- Zwei-Bild-Photometric-Stereo zur Messung der Welligkeit gehobelter Holzoberflächen (Lambert-Annahme, Ausnutzung der 1D-Struktur der Messerschläge) — [Jackson, Yang, Parkin 2007 (core.ac.uk)](https://core.ac.uk/download/288388397.pdf)
- Erweiterung auf bewegte Bretter (In-Prozess-Prüfung) mit hoher Korrelation zu statischen Tastschnittmessungen; unbehandeltes Holz nahezu diffus, poliertes Holz spiegelnd + diffus — [Loughborough Repository, dynamisches Photometric Stereo](https://repository.lboro.ac.uk/articles/In-process_surface_profile_assessment_of_rotary_machined_timber_using_a_dynamic_photometric_stereo_technique/9564494/files/17196830.pdf); [Crossref-Eintrag](https://api.crossref.org/works/10.1177%2F0959651811433121)
- Photometric Stereo liefert Normalenkarten, die Defekte bei reduzierten Glanz-/Schatteneffekten sichtbar machen (Beispiel Metallteile 2022) — [Sensors 2022, PMC9655976](https://pmc.ncbi.nlm.nih.gov/articles/PMC9655976); Differenzbilder zeigen Tiefengradienten ohne Schattierungseinfluss — [Simler et al., VISAPP 2017](https://scitepress.org/Papers/2017/61133/pdf/index.html)
- Patent: Erkennung nicht offener Risse in Holzbrettern über Streulicht am Riss im Bild mit unsichtbarem Licht (z. B. NIR) — [US 11615521](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11615521)
- Fraunhofer IPM bietet Oberflächeninspektion inline an (Referenz für Forschungspartner) — [Fraunhofer IPM Surface inspection](https://www.ipm.fraunhofer.de/en/bu/production-control-inline-measurement-techniques/applications/surface-inspection.html)

**Produkte und Preise (Linien-/Balkenleuchten)**
- Smart Vision Lights LC300 Linear Light: ab 513 USD (Hersteller) — [SVL LC300](https://smartvisionlights.com/products/lc300/)
- SVL LX150 Direct Connect Linear Light (150 mm): 441 USD — [Machine Vision Direct LX150](https://machinevisiondirect.com/products/svl-lx150)
- SVL LZE300 Linearleuchte 300 mm mit Silikonlinse: 967 USD — [Machine Vision Direct LZE300](https://machinevisiondirect.com/products/lze300)
- SVL LHI1200-DO-WHI-W30 High-Intensity Balkenleuchte 1200 mm: 1.990 USD (Händler, lieferrückständig) — [KingBarcode](https://www.kingbarcode.com/smart-vision-lights-lhi1200-do-whi-w30-high-intensity-wide-beam-led-bar-light)
- Advanced Illumination LL230 Ultra-High-Intensity-Linienlicht: modular in 150-mm-Schritten bis 2400 mm, Preis nur auf Anfrage — [PSI Rep LL230](https://www.psirep.com/products/advanced-illumination-ll230-series-ultra-high-intensity-line-lights); [Datenblatt LL230](https://psirep.com/system/files/spec-sheet-ll230-series.pdf)
- SVL LZEW300 Washdown-Linearleuchte bei B&H gelistet (Preis im Suchergebnis nicht sichtbar) — [B&H](https://www.bhphotovideo.com/c/product/1976010-REG/smart_vision_lights_lzew300_ss_sc_470_w30_lzew300_washdown_linear_light.html)
- Für CCS, Effilux, Metaphase, Stemmer-Eigenmarken und chinesische Leuchten wurden keine Preise gefunden.

### Inferences
- Bauformwahl (Fachwissen, Schätzung): Für ein bewegtes Brett mit Zeilenkamera ist eine Linienleuchte (fokussiert, hohe Leuchtdichte) Standard; mit Flächenkamera eher zwei breite Balkenleuchten (je ca. ±45°, diffus) für Hellfeld/Farbe. Dome-Leuchten sind für Bretter bis 300 mm Breite und mehrere Meter Länge unpraktisch groß und teuer.
- Streiflicht (flacher Winkel, ca. 5–20° zur Oberfläche, Schätzung) quer zur Faser betont Risse, Bohr-/Insektenlöcher, Nagelköpfe und alte Verbindungen (Relief); längs zur Faser reduziert es Faserstruktur-Rauschen. Praktisch: 2–4 Leuchten aus verschiedenen Richtungen, nacheinander geblitzt (Multiplex) = einfaches Photometric Stereo. Das ist methodisch durch die Holz-PS-Arbeiten gestützt, aber Altholz (rau, verschmutzt, Farbreste) ist dort nicht untersucht.
- Blitz vs. Dauerlicht (Fachwissen): Bei Vorschub und Flächenkamera erlaubt Blitz (Strobe, getriggert über Kamera-Ausgang oder Encoder) kurze Belichtung ohne Bewegungsunschärfe und mehrere Lichtkanäle im Wechsel; die SVL-/AI-Leuchten mit integriertem Treiber ("Direct Connect", Overdrive) sind dafür gebaut. Dauerlicht reicht bei Zeilenkamera und langsamem Vorschub.
- Fremdlicht (Fachwissen): Geschlossener Tunnel mit schwarzem Innenleben ist die billigste und wirksamste Maßnahme; zusätzlich Blitz mit kurzer Belichtung. Für Farbbeurteilung (Farbe/Fäule) weißes LED-Licht mit hohem CRI (≥90) und konstanter Farbtemperatur (ca. 5000–6500 K), Weißabgleich per Graukarte je Lauf; LED-Drift durch Temperatur ist bei DIY-Streifen größer als bei Industrieleuchten mit Konstantstrom-Treiber.
- DIY (Schätzung, nicht quellenbelegt): Hochwertige 24-V-LED-Streifen (CRI ≥90) in Aluprofilen mit opalem Diffusor + MOSFET-Blitzansteuerung kosten ca. 100–300 EUR für einen 1-m-Tunnel; Nachteil: geringere Leuchtdichte, Homogenität und Stabilität als Industrieleuchten.
- Budgetvorschlag (Schätzung): 2 Balkenleuchten 300–600 mm (je ca. 450–1.000 USD) + 2 flache Streiflicht-Leisten (DIY oder Industrie) + Tunnel ≈ 1.500–3.000 EUR.

### Gaps
- Keine öffentlichen Angaben zu Wellenlängen, Winkeln und Blitzbetrieb der Beleuchtung in Goldeneye, CombiScan, LuxScan.
- Keine Preise für CCS, Effilux, Metaphase, Stemmer-Leuchten und chinesische Marken (z. B. Hikrobot, OPT) gefunden.
- Keine Studie zu Streiflicht/Photometric Stereo speziell für Risse, Nagellöcher oder Altholz gefunden.
- Keine Herstellerangaben zu CRI/Temperaturdrift der genannten Leuchten geprüft.

## (B) Laser-Maßmessung: Triangulation, Profilsensoren, DIY, Lasersicherheit, Alternativen, Tracheideneffekt

### Takeaway
Fertige Profilsensoren mit genügend breitem Messfeld für Bretter/Balken (z. B. Gocator 2880, 390–1260 mm) sind teuer und nur auf Anfrage bepreist; kleinere Sensoren kosten neu rund 15–19 kEUR (Stemmer-Listenpreise Gocator 2500), gebraucht 6–10 kUSD. Im 5–10-kEUR-Budget realistisch: ein gebrauchter Profilsensor, ein günstiger chinesischer Sensor (ab ca. 4.200 USD bei AT Sensors als Richtwert) oder DIY-Linienlaser (Klasse 2/2M) + Industriekamera mit eigener Kalibrierung. Klasse 3R erfordert an Hochschulen meist Risikobeurteilung und Prüfung durch den Laserschutzbeauftragten; Klasse 3B zusätzlich kontrollierten Bereich — Klasse 2/2M oder gekapselt (Klasse 1) anstreben.

### Cited Findings
**Fertige Profilsensoren: Specs und Preise**
- LMI Gocator 2880 (für Holz): Messfeld 390–1260 mm, 1280 Punkte/Profil; Formdaten für Volumen, Konizität, Krümmung (sweep), Seitenkrümmung (crook) — [LMI Datenblatt Gocator 2880 Wood](https://lmi3d.com/wp-content/uploads/2024/09/DATASHEET_Gocator_2880_Wood_US.pdf); [LMI Gocator 2800](https://lmi3d.com/series/gocator-2800-series/); Preis 2880-3R bei Stemmer nur auf Anfrage — [Stemmer Gocator 2880-3R](https://www.stemmer-imaging.com/en/lmi-gocator-28803r)
- LMI Gocator 2100 (Einstieg, VGA, 640 Punkte/Profil): 2140 Messfeld 96–194 mm, X-Auflösung 0,19–0,34 mm, Z-Auflösung 0,013–0,037 mm, Z-Linearität 0,01 % des Messbereichs, Messbereich 210 mm — [LMI Datenblatt Gocator 2100](https://stg.lmi3d.com/wp-content/uploads/2024/08/DATASHEET_Gocator_2100_US_WEB.pdf); [Adept Gocator 2100](https://adept.net.au/cameras/LMI/Gocator_2100.shtml); 2150 Messfeld 158–365 mm laut Händler — [GlobalSpec Gocator 2150](https://datasheets.globalspec.com/ds/lmi-technologies/gocator-2150/45110c4e-0838-4fc0-89bd-6c0fdc0143e1)
- Preise Gocator 2500 (Hochgeschwindigkeit, kleines Messfeld): 2510-2 Listenpreis 18.790 EUR, 2525-2-B 15.550 EUR (Stemmer, nur Firmenkunden) — [Stemmer Gocator 2510-2](https://www.stemmer-imaging.com/es/lmi-gocator-25102); [Stemmer Gocator 2525-2-B](https://www.stemmer-imaging.com/en/lmi-gocator-25252b); gebraucht 2512A ca. 6.529 USD (eBay) — [eBay](https://www.ebay.com/itm/135720891553)
- LMI Holz-Sensoren auch Gocator 2300 Wood — [LMI Datenblatt Gocator 2300 Wood](https://lmi3d.com/wp-content/uploads/2024/09/DATASHEET_Gocator_2300_Wood_US.pdf); [LMI Holzindustrie](https://go.lmi3d.com/en/lmi3d-wood-industry)
- Keyence LJ-X8000: eBay-Angebote neu ca. 2.000–8.600 USD (oft 5.000–8.000 USD, Teile vs. Komplettsatz uneinheitlich); gebraucht LJ-X8400 ca. 4.700 USD (Kopf) bis 10.600 USD (komplett); gebrauchter Controller LJ-X8000A ca. 1.650–2.990 USD; nur Angebotspreise, keine Verkaufspreise; Herkunft "brandneu" aus Fernost-Angeboten nicht verifizierbar — [eBay LJ-X8000 Übersicht](https://www.ebay.com/p/14065007411); [eBay.de LJ-X8000](https://www.ebay.de/itm/404930222733); [eBay LJ-X8080](https://www.ebay.com/itm/306127970604)
- Micro-Epsilon scanCONTROL 3000: kein Listenpreis gefunden; gebraucht 2 × scanCONTROL 3012-100 (Bj. 2013) mit Controller für 6.000 EUR VB (Exapro) — [Exapro](https://www.exapro.com/mirco-epsilon-3012-100-p260109174/); Serie mit roten und blauen Lasern — [Micro-Epsilon scanCONTROL](https://www.micro-epsilon.com/2D_3D/3D-sensors/scanCONTROL/)
- Hikrobot DP-Serie (z. B. MV-DP3900-03P/03H, 405-nm-Blaulaser): kein Preis veröffentlicht — [ZTEC Hikrobot MV-DP3900](https://www.ztec.dk/shop/hikrobot-mv-dp3900-03h-mv-dp3900-03h-42217); [Qviro Hikrobot Line Laser 3D Camera](https://qviro.com/product/hikrobot/line-laser-3d-camera); [ITVoice Hikrobot](https://www.itvoice.in/hikrobot-introduces-3d-laser-profile-sensor-in-india-for-various-application-scenarios)
- AT Sensors (Automation Technology): 3D-Laserprofilsensoren "ab 4.200 USD" — [AT Sensors](https://www.at-sensors.com/3d-laserprofilesensors-ga/)
- Wenglor weCat3D/MLWL und SICK Ranger3/Ruler: keine Preise gefunden (nicht gezielt erfolgreich recherchiert).

**DIY Linienlaser + Kamera**
- Genauigkeit hängt v. a. von der Kalibrierung (Kamera + Laserebene) ab; einfache, präzise Laserebenen-Kalibrierung ist bei Low-Cost-Systemen zentral — [DLR Laser Stripe Profiler, Strobl 2004](https://www.dlr.de/de/rm/downloads/roboter_und_systeme/3d-scanner/laser_stripe_profiler/paper_strobl_2004randa_The_DLR_Multisensory_Hand-Guided_Device_The_Laser_Stripe_Profiler.pdf/@@download/file); [MDPI Sensors 21/3/765](https://mdpi.com/1424-8220/21/3/765)
- Fehlausrichtung Laser–Kamera wird in der Literatur oft ignoriert, beeinflusst aber direkt die Maßgenauigkeit — [core.ac.uk 287604624](https://core.ac.uk/download/287604624.pdf)
- Open Source: FabScan (Webcam + günstiger Linienlaser + Drehteller) — [RWTH Engelmann 2011](https://almeida.informatik.rwth-aachen.de/publications/engelmann2011a.pdf); TU-Delft-Masterarbeit zu Low-Cost-Linienlaser-Distanzsensor mit µs-Synchronisation (Reichweite bis 3 m) — [TU Delft Repository](https://repository.tudelft.nl/file/File_817d47bb-ce51-4322-8817-65f7e9e6a808?preview=1)

**Lasersicherheit**
- UK-Hochschulen (BS EN 60825-1): Laserschutzbeauftragter (LSO) schriftlich bestellt ab Klasse 3; für 3R, 3B, 4 MPE-Berechnung in der Risikobeurteilung, Prüfung durch LSO, Schulung der Nutzer; Grenzwert Klasse 3R bei 633 nm: 5 mW — [UCL AOR Safety Standard](https://www.ucl.ac.uk/safety-services/policies/2022/feb/ucl-artificial-optical-radiation-aor-safety-standard); [Bangor Info Sheet Lasers](https://www.bangor.ac.uk/hss/inflink/documents/Info%20Sheet%20Safe%20Use%20of%20Lasers.pdf); [London Met Laser Policy](https://www.londonmet.ac.uk/media/london-metropolitan-university/london-met-documents/professional-service-departments/policies/Laser-Management-and-Use-Policy-v1.0.pdf)
- Klasse 3B/4: Registrierung vor Nutzung, kontrollierter Laserbereich (sofern nicht technisch auf Klasse 1 gekapselt) — [Dundee Laser Policy](https://www.dundee.ac.uk/corporate-information/laser-safety-management-policy); [Surrey Laser Safety Procedure](https://www.surrey.ac.uk/sites/default/files/2023-06/laser-safety-procedure.pdf)
- Gocator-Datenblatt: Linearität/Auflösung/Wiederholbarkeit können je Laserklasse variieren (Modelle in Klasse 2, 3R, 3B erhältlich) — [LMI Datenblatt Gocator 2100](https://stg.lmi3d.com/wp-content/uploads/2024/08/DATASHEET_Gocator_2100_US_WEB.pdf)

**Einfachere Alternativen (Tiefenkameras)**
- Intel RealSense D405: ca. 300 USD, kurzreichweitig (0,07–0,5 m optimal laut Hersteller; Quellenangaben widersprüchlich) — [roboticscenter.ai Vergleich](https://www.roboticscenter.ai/blog/best-depth-cameras-robotics); [OpenELAB Gemini 335Lg vs D405](https://openelab.io/de/blogs/learn/orbbec-gemini-335lg-vs-intel-realsense-d405)
- Orbbec Gemini 335: Herstellerangabe Präzision ≤1,5 % bei 2 m, optimal 0,26–3 m (entspricht ~mm bis cm, für Brettmaße zu ungenau) — [roboticscenter.ai Kamera-Vergleich](https://www.roboticscenter.ai/compare/cameras); [B&H Gemini 335](https://www.bhphotovideo.com/c/product/1865585-REG/orbbec_100100476_gemini_335_depth_camera.html)
- Zivid 2+: Strukturlicht, IP65, kein Preis/keine Genauigkeitszahl in den Treffern — [Zivid Vergleich](https://www.zivid.com/comparison-point-clouds-quality)

**Tracheideneffekt**
- Prinzip: runder Laserpunkt senkrecht auf Holz streut elliptisch in Faserrichtung; v. a. Nadelholz — [J Wood Sci 2020, s10086-020-01922-y](https://link.springer.com/10.1186/s10086-020-01922-y)
- Low-Cost-Aufbau in Studien: 5-mW-Laserdioden 650 nm, CMOS-Digitalkamera, 35-mm-Objektiv; Auswertung u. a. per modifizierter Hough-Ellipsenanalyse — [J Wood Sci 2020](https://jwoodscience.springeropen.com/track/pdf/10.1186/s10086-020-01922-y); [Materials and Structures 2022, s11527-022-01995-9](https://link.springer.com/content/pdf/10.1617/s11527-022-01995-9.pdf)
- Laubholz: 650 nm funktioniert nicht bei allen Arten; Buche/Birke zeigen den Effekt besonders bei 808 nm; Transmission bei Buche/Eiche bei 650 nm sehr gering — [Wood Sci Technol 2017, s00226-017-0952-3](https://link.springer.com/article/10.1007/s00226-017-0952-3); [Wood Sci Technol 2025, s00226-025-01653-7](https://link.springer.com/article/10.1007/s00226-025-01653-7)
- Genauigkeit: max. Fehler 4,6° bei sägerauer Sugi, gehobelt geringer — [J Wood Sci 2003, s10086-003-0569-z](https://jwoodscience.springeropen.com/counter/pdf/10.1007/s10086-003-0569-z.pdf)
- Patent Faserwinkelsensor — [US 7466403](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/7466403)
- Industriell: MiCROTEC nutzt Punktlaser-Streukameras für Äste und Faserabweichung; WEINIG Punktlaser optional — [MiCROTEC Referenz](https://microtec.eu/it/referenze/double-pack-of-scanners); [Höchsmann EasyScan C](https://wtp.hoechsmann.com/en/lexikon/35829/weinig_easyscan_c)

### Inferences
- Triangulation (Fachwissen): Linienlaser projiziert quer zum Brett, Kamera unter Winkel (typ. 20–45°) sieht die Linie; Höhe = Versatz im Bild. Bei 300 mm Messbreite und ~1280–2000 Pixeln quer ergibt sich X-Auflösung ~0,15–0,25 mm; Z-Genauigkeit mit Sub-Pixel-Linienschwerpunkt im Bereich 0,05–0,3 mm (Schätzung) — für Breite/Dicke/Profil von Altholz (Toleranzen im mm-Bereich) mehr als ausreichend. Länge, Krümmung (bow/crook) erfordern Vorschubmessung (Encoder am Förderer) und Zusammensetzen der Profile.
- Für Breite und Dicke beidseitig: entweder zwei Sensoren (oben/unten bzw. oben/seitlich) oder ein Sensor + Referenzauflage; Rauheit/Schmutz von Altholz verschlechtert Genauigkeit, Farbe (dunkle Stellen) reduziert Signal — blauer Laser (405/450 nm) ist auf dunklen/organischen Oberflächen oft robuster (Herstellerargument, hier nicht separat belegt).
- Budgetoptionen (Schätzung): (1) DIY: Linienlaser-Modul Klasse 2 (≤1 mW, ca. 30–150 EUR) + Global-Shutter-Industriekamera mit Bandpassfilter (ca. 400–900 EUR) + Objektiv (ca. 100–300 EUR) + Encoder ≈ 0,7–1,5 kEUR; Kalibrierung mit OpenCV (Kamera) + Laserebene über Ebenen-Target. (2) Gebrauchter Keyence/Micro-Epsilon/Gocator ≈ 2–10 kUSD, Risiko Software/Lizenz/Support. (3) Neuer chinesischer Profilsensor (Hikrobot, AT Sensors als Referenz ab 4.200 USD) — Messfeldbreite prüfen. Neue Gocator 2880 liegen nach Preisniveau der 2500-Serie vermutlich über dem Gesamtbudget (Schätzung).
- Lasersicherheit (Einordnung, Schätzung für DE): Klasse 1/2/2M ohne besondere Auflagen außer Unterweisung; ab 3R nach deutscher Praxis (OStrV/TROS Laserstrahlung) Laserschutzbeauftragter erforderlich — hier nicht quellengeprüft. Empfehlung: Klasse 2 oder Gehäuse/Tunnel, der die Anlage praktisch auf Klasse 1 bringt.
- Tiefenkameras (RealSense, Orbbec) sind für mm-genaue Brettmaße ungeeignet (~1–2 % der Distanz); allenfalls grobe Präsenz/Länge. Lichtvorhänge (Messlichtgitter) sind eine bewährte, günstigere Alternative für Breite/Länge, aber ohne Profil (nicht recherchiert, siehe Gaps).
- Tracheideneffekt Low-Cost (Schätzung): Reihe aus 5–10 Punktlasern 650 nm (Klasse 2, ca. 5–20 EUR/Stück) oder 808-nm-Dioden für Laubholz + Monochromkamera; für Altholz (Nadelholz-Balken überwiegend) gut geeignet zur Asterkennung, aber Farbe/Schmutz/Verwitterung der Oberfläche dürften das Signal stören (nicht untersucht).

### Gaps
- Kein öffentlicher Preis für Gocator 2100/2880, Keyence LJ-X/LJ-S (neu), Micro-Epsilon (neu), Wenglor, SICK Ranger3/Ruler, Hikrobot.
- Gocator-2880-Datenblatt war als PDF nicht maschinell lesbar; Z-Auflösung, Laserklasse, Profilrate nicht übernommen.
- Lichtvorhänge, ToF-/Ultraschallsensoren, Stereo-Kameras: keine Preise/Genauigkeiten recherchiert (Tool-Budget).
- Deutsche Rechtslage (OStrV, TROS Laserstrahlung, Pflicht zum Laserschutzbeauftragten ab 3R) nicht mit Quelle bestätigt; nur UK-Hochschulrichtlinien gefunden.
- Zivid-2+-Preis und Genauigkeit nicht gefunden.
- Keine veröffentlichten Zahlen zur erreichbaren Genauigkeit von DIY-Triangulation bei Brettformat.
- Keine Quelle zum Tracheideneffekt auf verwitterter/lackierter Altholz-Oberfläche.
