# YOLO-Training für einen Altholz-Fehlstellenscanner: Daten-, Annotations- und Rechenaufwand (Stand Nov. 2026)

Anker (eigene Messung, keine externe Quelle): Kodytek/VSB-TUO-Datensatz, 16.000 Trainingsbilder, yolo11n Detektion, imgsz 1280, Mac M4 Pro (MPS, 24 GB): ca. 21 min/Epoche, 9,4 GB GPU-Speicher, 100 Epochen ca. 35 h, Plateau ab ca. Epoche 40, val mAP50 0,75 / mAP50-95 0,46. Overfit-Test 20 Bilder x 150 Epochen: 6,5 min.
Abgeleiteter Durchsatz (Rechnung): 16.000 Bilder / (21 x 60 s) = **ca. 12,7 Bilder/s bei 1280** (entspricht grob ca. 50 Bilder/s bei 640, wenn man 4-fache Pixelzahl ~ 4-facher Rechenaufwand annimmt; Schätzung).

## 1. Wie viele annotierte Bilder/Instanzen pro Klasse werden gebraucht, und wie schnell sättigt mAP?

### Takeaway
Ultralytics empfiehlt ≥1.500 Bilder und ≥10.000 Instanzen pro Klasse, die publizierte Holzfehler-Literatur arbeitet aber fast durchweg mit 1.000–4.000 Bildern insgesamt und erreicht damit mAP50 um 0,70–0,78 auf Kodytek. Eine saubere Lernkurve (mAP über Datensatzgröße) für Holzfehler wurde nicht gefunden; der eigene Kodytek-Lauf mit 16.000 Bildern liegt (mAP50 0,75) auf dem Niveau von Arbeiten mit ca. 3.500 Bildern, was auf Sättigung bzw. Label-/Klassenproblem statt Datenmangel hindeutet.

### Cited Findings
- Ultralytics-Empfehlung: "≥ 1500 images per class recommended", "≥ 10000 instances (labeled objects) per class recommended", 0–10 % Hintergrundbilder gegen Fehlalarme (COCO ca. 1 %); vortrainierte Gewichte "recommended for small to medium-sized datasets"; Start mit 300 Epochen; bei vielen kleinen Objekten höhere Auflösung z. B. 1280; Inferenz am besten mit derselben imgsz wie im Training — [Ultralytics Tips for Best Training Results](https://docs.ultralytics.com/yolov5/tutorials/tips_for_best_training_results/)
- Kodytek/VSB-TUO: 20.275 Bilder 2800x1024, davon 1.992 fehlerfrei, 10 Klassen (Live Knot, Dead Knot, Quartzity, Knot with crack, Knot missing, Crack, Overgrown, Resin, Marrow, Blue stain). CFIS-YOLO nutzt nach Ausschluss der drei seltenen Klassen (Quartzity, Blue stain, Overgrown) nur 3.465 Bilder, Split 8:1:1, 640x640, 300 Epochen, Batch 32, NVIDIA A10 24 GB — [CFIS-YOLO, arXiv 2504.11305](https://arxiv.org/pdf/2504.11305)
- Ergebnisse auf diesen 3.465 Kodytek-Bildern (mAP@0.5): YOLOv5s 69,0; YOLOv7-tiny 71,0; YOLOv8s 74,1; YOLOv9s 71,6; YOLOv10s 73,5; CFIS-YOLO 77,5. Faster R-CNN 59,2 und RT-DETR 64,8 (aus Wang et al. 2025 mit 3.600 zufälligen Kodytek-Bildern) — [CFIS-YOLO, arXiv 2504.11305](https://arxiv.org/pdf/2504.11305)
- Weitere Holzfehler-Arbeiten mit kleinen Datensätzen: Wang et al. 2021, 1.800 Bilder (je 450 fehlerfrei/Wurmloch/Ast/Riss), verbessertes YOLOv3 — [BioResources 16(4)](https://bioresources.cnr.ncsu.edu/wp-content/uploads/2021/08/BioRes_16_4_6766_Wang_YDQ_Dectect_Wood_Surface_Defects_Impr_YOLOV3_Algorithm_19077.pdf); Lopes et al. 2020, 921 Bilder Ast-Erkennung mit YOLOv3, Autoren sehen Datenmenge als Grenze — [BioResources 15(4)](https://bioresources.cnr.ncsu.edu/wp-content/uploads/2020/10/BioRes_15_4_9351_Lopes_BG_Fast_Robust_Artificial_Intellig_Techniq_Wood_Knot_Detec_17998_.pdf); YOLOv8-Asterkennung mit 2 x 573 Bildern (balanciert), berichtetes mAP nur 0,0887 — [Sci. Bull. UPB 2026](https://www.scientificbulletin.upb.ro/static/pdfs/a2026nr2c_20_C-223_MButolo_AHadar_pag.pdf)
- Neuere Ergebnisse auf eigenen Datensätzen: EFCW-YOLO 90,26 % mAP50 auf selbst gebautem PlankDef-9K (ca. 9.000 Bilder); OptiWood-YOLO (Preprint Sept. 2026, Sägewerk-Datensatz, 7 Klassen) YOLOv8n mAP50 0,46 / mAP50-95 0,23; Dou & You 2025 YOLOv8 72,9 → 79,5 % mAP — [MDPI Forests 16/12/1757](https://www.mdpi.com/1999-4907/16/12/1757); [Preprints.org 202609.0951](https://www.preprints.org/manuscript/202609.0951); [BioResources](https://bioresources.cnr.ncsu.edu/?p=49477) (Angaben aus Suchauszügen, Volltexte nicht geprüft)

### Inferences
- Rechnung Ultralytics-Richtwert für Altholz: 11 Klassen, Äste in lebend/tot geteilt = 12 Klassen x 10.000 Instanzen = **ca. 120.000 Instanzen**; das ist ein Ideal für COCO-artige Vielfalt, nicht Mindestbedarf. Seltene Klassen (Insektenlöcher, alte Verbindungen, Fäule) werden diesen Wert in Altholz realistisch nie erreichen (Schätzung).
- Praktischer Richtwert aus Literatur (Schätzung): 200–500 Instanzen pro Klasse für brauchbare erste Ergebnisse (mAP50 ~0,5–0,7 bei gut sichtbaren Klassen wie Nägel, Bohrlöcher, Äste), 1.000–3.000 Instanzen pro Klasse für Kodytek-Niveau. Klassen mit diffusen Grenzen (Schmutz, Farbe, Bläue, Fäule) brauchen mehr und erreichen bei Boxen strukturell niedrigere mAP50-95.
- Eigener Lauf: Plateau ab Epoche ~40 bei 16.000 Bildern und mAP50 0,75 ≈ CFIS/YOLOv8s mit 3.465 Bildern bei 640. Das spricht dafür, dass mehr Bilder desselben Typs auf Kodytek kaum noch helfen; Begrenzung eher durch Label-Rauschen/Klassen-Mehrdeutigkeit (Kodytek-Klassen wie Knot-with-crack vs. Crack) und Modellkapazität (n). Vergleichbarkeit eingeschränkt: CFIS nutzt nur 7 Klassen und 640.
- Für Altholz ist die Domänenlücke (andere Holzarten, Patina, Schmutz, Beleuchtung) der größere Faktor als die absolute Bildzahl: einige hundert eigene Bilder sind wichtiger als 16.000 weitere Kodytek-Bilder.

### Gaps
- Keine kontrollierte Lernkurve (mAP vs. Anzahl Trainingsbilder) für Holzfehler mit YOLO gefunden.
- Keine Few-Shot-Ergebnisse für Holzfehler mit YOLO gefunden.
- Kodytek-Originalpaper (Kodytek, Bodzas, Bilik 2021) mit eigenen Baselines nicht abgerufen.

## 2. Annotationsaufwand pro Bild (Box vs. Polygon/Maske), Werkzeuge, modellgestütztes Labeln, Kosten

### Takeaway
Klassisches Boxzeichnen kostet laut Literatur ca. 35 s pro hochwertiger Box (mit Extreme Clicking ca. 7 s), Polygone ca. 80 s pro Objekt (COCO). Mit SAM-gestützten Werkzeugen (X-AnyLabeling mit SAM 1/2/3, Train-and-Relabel-Schleife) sinkt der Aufwand deutlich; Annotation bleibt aber der größte Zeitposten. Dienstleister: Boxen ca. 0,02–0,10 USD, Polygone ca. 0,03–0,20 USD pro Objekt (Herstellerangaben).

### Cited Findings
- Extreme Clicking: ca. 7 s pro Box, 5x schneller als klassisches Zeichnen; ILSVRC brauchte ca. 35 s (34,5 s) pro hochwertiger Box; Qualität gleichwertig — [Papadopoulos et al., ICCV 2017, arXiv 1708.02750](https://arxiv.org/abs/1708.02750v1)
- COCO-Polygone: ca. 80 s pro Objekt (zitiert in Folgearbeit) — [arXiv 2407.18682](https://arxiv.org/html/2407.18682v1)
- X-AnyLabeling: unterstützt SAM 1/2/3 (lokale ONNX-Unterstützung für SAM-3-Segmentierung per Textprompt seit 26.04.2026), Import/Export u. a. YOLO, COCO, VOC; Ultralytics in der GUI integriert: Batch labeln → YOLO trainieren → Modell zum Vorlabeln des nächsten Batches laden; v4.0.0 am 05.08.2026, YOLO11-Seg/YOLO26-Seg, TensorRT-Inferenz — [X-AnyLabeling GitHub](https://github.com/CVHub520/X-AnyLabeling); [PyPI x-anylabeling-cvhub 4.0.0](https://pypi.org/project/x-anylabeling-cvhub/4.0.0/); [DEV: X-AnyLabeling](https://dev.to/jack_wang_d47b1f7f781c64f/meet-x-anylabeling-the-python-native-ai-powered-annotation-tool-for-modern-cv-507b)
- SAM 3 Text-zu-Maske zum Batch-Labeln für YOLO-Segmentierung (Skript-Tutorial) — [DEV: Auto-label with SAM3](https://dev.to/artzabarov/how-to-auto-label-your-segmentation-dataset-with-sam3-3p8)
- Preise (Herstellerangaben, indikativ): einfache Boxen meist 0,015–0,10 USD, Marktspanne 0,03–1,00 USD; Polygone 0,03–0,20 USD — [Basic.ai](https://www.basic.ai/blog-post/image-annotation-services-cost); Roboflow Managed Labeling ab 0,10 USD/Box, 0,20 USD/Polygon — [Roboflow Labeling](https://roboflow.com/roboflow-labeling); Label Your Data ab 0,02 USD/Objekt — [Label Your Data Pricing](https://labelyourdata.com/pricing/); Stundensätze ca. 4–60 USD, Spezialdomänen deutlich teurer, Kosten pro akzeptiertem Label nach QA zählt — [Label Studio: Pricing models](https://labelstud.io/learningcenter/how-data-labeling-pricing-models-compare)

### Inferences (alles Schätzungen)
- Annahme Altholz: 4 Instanzen pro Bild im Mittel (Nägel, Bohrlöcher, Äste dominieren), effektive Zeit mit gutem Werkzeug und Vorlabeln: Box 8–12 s, SAM-Maske mit Klick + Korrektur 10–20 s, Polygon von Hand 40–80 s; plus ca. 20 % Prüfung.
  - 300 Bilder x 4 x 10 s x 1,2 = **4 h** (Boxen) bzw. 300 x 4 x 15 s x 1,2 = 6 h (SAM-Masken).
  - 2.000 Bilder: Boxen ca. **27 h**, SAM-Masken ca. 40 h, Handpolygone ca. 130–210 h.
  - 20.000 Bilder: Boxen ca. **270 h** (≈ 34 Personentage), SAM-Masken ca. 400 h.
  - Ultralytics-Ideal 120.000 Instanzen: Boxen ca. 400 h; Dienstleister 120.000 x 0,05 USD = 6.000 USD (Boxen) bzw. x 0,20 USD = 24.000 USD (Polygone), ohne Fachprüfung.
- Diffuse Klassen (Schmutz, Farbe/Beschichtung, Bläue, Fäule, Harz) sind als Boxen mehrdeutig; Segmentierung ist dort fachlich passender, SAM liefert aber bei Verfärbungen ohne klare Kante schlechte Masken (Erfahrungswert, nicht belegt). Mischstrategie: Boxen für punktförmige/kompakte Fehler, Masken für Flächenfehler.
- Fachwissen (Holzschutz, Fäule vs. Verfärbung, lebender vs. toter Ast) macht günstige Dienstleister unzuverlässig und ist für Schülerhilfskräfte/Projektpartner der eigentliche Engpass; Datenschutz ist bei Holzbildern unkritisch.
- Active-Learning-Schleife (Vorlabeln mit eigenem Modell, nur unsichere Bilder priorisieren) kann den Aufwand nach den ersten 300–500 Bildern grob halbieren (Schätzung, kein Beleg gefunden).

### Gaps
- Keine Messung der Annotationszeit speziell für Holzfehler gefunden; keine belastbare Zahl für SAM-2/3-gestützte Zeit pro Objekt.
- CVAT, Label Studio, Roboflow nicht im Detail geprüft (Funktionen bekannt, aber nicht für diese Notiz verifiziert).

## 3. Transfer Learning, Augmentation, Tiling/SAHI, imgsz

### Takeaway
Vortrainierte Gewichte sind für kleine/mittlere Datensätze ausdrücklich empfohlen; zweistufig COCO → Kodytek → Altholz ist plausibel, aber nicht durch eine gefundene Studie belegt. Für 2800x1024-Bilder mit kleinen Fehlern (Nagellöcher, Insektenlöcher, Haarrisse) ist 1280 oder Kachelung nötig.

### Cited Findings
- Pretrained für kleine/mittlere Datensätze empfohlen, from scratch nur für große; höhere imgsz (1280) bei vielen kleinen Objekten; gleiche imgsz in Training und Inferenz — [Ultralytics Tips](https://docs.ultralytics.com/yolov5/tutorials/tips_for_best_training_results/)
- Kodytek-Arbeiten trainieren mit 640x640 (Bild 2800x1024 wird stark verkleinert) und kommen trotzdem auf mAP50 ~0,74 (YOLOv8s) — [CFIS-YOLO](https://arxiv.org/pdf/2504.11305); eine Arbeit mit 3.600 Kodytek-Bildern setzt stark auf Augmentation gegen Overfitting (laut Suchauszug) — [CFIS-YOLO, Verweis auf Wang et al. 2025](https://arxiv.org/pdf/2504.11305)

### Inferences (Schätzungen)
- Seitenverhältnis 2800x1024 ≈ 2,7:1: bei imgsz 1280 wird das Bild auf 1280x468 skaliert (letterbox), ein 3-mm-Nagelloch auf einem 2800-px-Bild über z. B. 1 m Länge wird dann ca. 1–2 px groß – zu klein. Alternativen: Kacheln 2–3 Stück à 1024x1024 bei Training und Inferenz (SAHI-artig), oder rect-Training. Für einen Zeilenscanner mit fester Geometrie ist Kachelung natürlicher als SAHI-Nachbearbeitung.
- Kodytek als Zwischenstufe hilft vor allem für Äste, Risse, Harz, Bläue (dieselben Klassen); für Nägel, Schrauben, Bohrlöcher, Farbe, Fäule, alte Verbindungen gibt es dort keine Beispiele – hier zählt nur eigenes Material.
- Augmentation: Helligkeit/Farbton (Patina, Verschmutzung), Flips, Mosaic; Vorsicht mit starker Farbaugmentation bei Bläue/Farbe, weil Farbe das Klassenmerkmal ist.

### Gaps
- Keine Studie gefunden, die COCO-Pretrain vs. Holz-Pretrain (Kodytek) für einen Zieldatensatz vergleicht.
- SAHI/Tiling-Ergebnisse für Holzfehler nicht gefunden.

## 4. Szenario A: 300–2.000 eigene Bilder + Uni-GPU-Cluster (A100/H100, Slurm)

### Takeaway
Rechenzeit ist in Szenario A kein Engpass: Selbst auf dem Mac dauert ein yolo11n-Lauf mit 2.000 Bildern bei 1280 und 300 Epochen ca. 13 h, auf einer A100 geschätzt 1–3 h. Der Cluster lohnt sich für Modellvergleiche (s/m/l) und Hyperparameter-Suchen, nicht für den Basislauf; Engpass sind Annotation und Domänenabdeckung.

### Cited Findings
- Ultralytics-Benchmark (YOLO26, COCO 25 %, 640, AMP, Auto-Batch, Einzel-GPU, stationäre 2. Epoche): H100 SXM ca. 424 Bilder/s, A100 SXM ca. 287 Bilder/s, Spitzenspeicher 23,1 GB; Modellgröße im Auszug nicht genannt — [Ultralytics Benchmarks](https://ultralytics.com/benchmarks) (Zahlen aus Suchauszug, Tabelle beim Abruf nicht als Text lesbar)
- ThunderCompute: 2x A100 80 GB, MinneApple-Datensatz, 100 Epochen ca. 8 min (YOLO11n), 11 min (m), 15 min (l) — kleiner Datensatz, Multi-GPU — laut Suchauszug, Primärquelle nicht abgerufen
- CFIS-YOLO trainierte auf einer einzelnen A10 (24 GB) 300 Epochen bei 640, Batch 32 — [CFIS-YOLO](https://arxiv.org/pdf/2504.11305)

### Inferences (Rechnung, Schätzung)
- A100 bei 1280 ≈ 287 / 4 ≈ **70 Bilder/s**, H100 ≈ 424 / 4 ≈ **105 Bilder/s** (Annahme: Benchmarkwert gilt für ein n-/s-Modell; bei 4-facher Pixelzahl ca. 4-facher Aufwand).
- Eigener 16k-Lauf auf Cluster: A100: 16.000 / 70 ≈ 230 s ≈ **4 min/Epoche**, 100 Epochen ≈ **6–7 h** (Mac: 35 h, Faktor ca. 5); H100: ≈ 2,5 min/Epoche, 100 Epochen ≈ **4–5 h** (Faktor ca. 8). Unsicherheit groß (Faktor 2): Datenlader mit 2800x1024-BMP-Dekodierung kann CPU-gebunden sein → `cache=ram` (16.000 x 2800 x 1024 x 3 B ≈ 138 GB unkomprimiert, bei Verkleinerung auf 1280 ≈ 29 GB) oder `cache=disk`, ausreichend CPU-Kerne pro GPU in Slurm anfordern.
- Szenario A, 2.000 Bilder, 300 Epochen bei 1280: A100 yolo11n ≈ 2.000/70 x 300 ≈ 2,4 h; yolo11s ≈ 5–8 h; yolo11m ≈ 12–25 h (FLOPs-Verhältnis s/n 3,3, m/n 10,5; Durchsatz skaliert unterproportional; Schätzung). Mac zum Vergleich yolo11n ≈ 2.000/12,7 x 300 ≈ 13 h.
- Multi-GPU (DDP, `device=0,1`) lohnt bei ≤2.000 Bildern kaum (Epochen dauern Sekunden, Validierung/Start dominieren).
- Grenzen Cluster (allgemein, nicht recherchiert): Wartezeiten in der Queue, Laufzeitlimits (oft 24–72 h je Job → `resume=True` nutzen), Container/venv-Einrichtung, Datentransfer der Rohbilder (Datenschutz bei Holzbildern unkritisch, aber Nutzungsbedingungen des Clusters beachten).

### Gaps
- Keine direkte, veröffentlichte YOLO11-Epochenzeit pro Modellgröße für A100/H100 gefunden; Ultralytics-Benchmark gibt nur YOLO26-Durchsatz ohne lesbare Modellgrößen-Aufschlüsselung.
- Konkrete Bedingungen des HNEE-/Uni-Clusters nicht recherchiert.

## 5. Szenario B: 5.000–20.000 Bilder + Mac M4 Pro (MPS)

### Takeaway
Machbar für yolo11n (eigene Messung) und grenzwertig für yolo11s bei 1280 (Schätzung 55–70 min/Epoche, 100 Epochen ca. 4–5 Tage); yolo11m bei 1280 auf dem Mac ist mit 9–15 Tagen für 100 Epochen praktisch unattraktiv. MPS läuft ohne AMP, Training auf Apple Silicon wird häufig als langsam beschrieben.

### Cited Findings
- Ultralytics deaktiviert AMP auf MPS (Log "AMP: checks failed, disabling Automatic Mixed Precision") — [PyTorch Forum](https://discuss.pytorch.org/t/mps-is-not-working-even-with-nightly-conda-and-pip3-versions/160168)
- Nutzerberichte: YOLO-Training auf M3 Max unerwartet langsam, geringe GPU-Auslastung, deutlich schneller auf NVIDIA; Thread ohne Lösung — [Apple Discussions](https://discussions.apple.com/thread/256057418); M1 Pro "really slow" — [Apple Developer Forums](https://developer.apple.com/forums/thread/756252); M5-Mac deutlich langsamer als RTX 4050 — [PyTorch Forum](https://discuss.pytorch.org/t/super-slow-training-in-m5-mac-compared-to-4050-nvidia-gpu-why/224311)
- Datenlader-Zeiten auf MPS oft größer als Trainingsschritt — [PyTorch Forum: Dataloader slows down with MPS](https://discuss.pytorch.org/t/dataloader-slows-down-when-training-with-mac-mps/196185); Overhead CPU↔MPS kann MPS langsamer als CPU machen — [Apple Developer Forums](https://developer.apple.com/forums/thread/735997)
- Apple bezeichnet das MPS-Backend als Beta, Fehler an PyTorch-GitHub mit Label "module: mps" — [Apple: Accelerated PyTorch training on Mac](https://developer.apple.com/metal/pytorch)
- MPS unterstützt grundsätzlich bf16/fp16-Mixed-Precision (bf16 ab macOS 14) in Hugging Face — [HF Apple Silicon](https://huggingface.co/docs/transformers/main/perf_train_special.md); Ultralytics nutzt das für MPS dennoch nicht (siehe AMP-Log oben)

### Inferences (Rechnung, Schätzung)
- Mac-Durchsatz yolo11n@1280 ≈ 12,7 Bilder/s; A100-Schätzung ≈ 70 Bilder/s → Mac ≈ 1/5 A100, ≈ 1/8 H100 (für n; für größere Modelle eher größerer Abstand, da kein AMP).
- 5.000 Bilder, n@1280: 5.000/12,7 ≈ 6,6 min/Epoche, 100 Epochen ≈ 11 h; 20.000 Bilder ≈ 26 min/Epoche, 100 Epochen ≈ 44 h. Bei Plateau ab Epoche ~40: 50–60 Epochen mit `patience` reichen → ca. 20–25 h für 20k.
- yolo11s@1280: Faktor 2,5–3,3 auf n → 16k Bilder 52–70 min/Epoche, 100 Epochen 90–115 h (≈ 4–5 Tage). Speicher: n brauchte 9,4 GB bei (vermutlich) Batch 16; s mit Batch 16 dürfte 20+ GB brauchen → Batch 8 und ggf. weniger Datenlader-Worker; 24 GB werden mit dem Betriebssystem geteilt.
- yolo11m@1280: Faktor 6–10 → 2–3,5 h/Epoche, 100 Epochen 9–15 Tage. Nicht sinnvoll auf dem Mac; Cluster nutzen.
- Praktische Tipps: Bilder vorab auf Trainingsgröße verkleinern und als JPG/PNG statt 2800x1024-BMP ablegen (Dekodierlast), `cache=ram` nur wenn es in den Speicher passt, Mac nicht schlafen lassen, `resume=True`.

### Gaps
- Kein offizieller Ultralytics-Benchmark für MPS/M4 gefunden; keine Ultralytics-GitHub-Issues zu MPS-Op-Fallbacks im Detail geprüft.

## 6. Größere Modelle (s/m/l/x): erwartbare mAP-Gewinne vs. Kosten; ist das Plateau ein Kapazitätslimit?

### Takeaway
Auf COCO bringt n → s +7,5 Punkte mAP50-95, s → m +4,5, danach nur noch +1–2 Punkte bei vielfachen FLOPs. Auf Holzfehler-Datensätzen sind die Abstände kleiner; ein Wechsel n → s ist der wahrscheinlich lohnendste Schritt, das Plateau mit n ist teilweise ein Kapazitätslimit, teilweise Label-/Datenlimit.

### Cited Findings
- YOLO11 COCO 640 (mAP50-95 box / Params / FLOPs / T4-TensorRT ms): n 39,5 / 2,6 M / 6,5 B / 1,5; s 47,0 / 9,4 M / 21,6 B / 2,5; m 51,5 / 20,1 M / 68,1 B / 4,7; l 53,4 / 25,3 M / 87,2 B / 6,2; x 54,7 / 56,9 M / 195,3 B / 11,3 — [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/)
- Kodytek (3.465 Bilder, 640): s-Modelle verschiedener YOLO-Generationen streuen zwischen 69,0 und 74,1 mAP50; architekturelle Verbesserungen bringen ca. +3–4 Punkte — [CFIS-YOLO](https://arxiv.org/pdf/2504.11305)

### Inferences (Schätzungen)
- Für Kodytek erwartbar: yolo11s@1280 ca. +2–5 Punkte mAP50 gegenüber n (0,75 → 0,77–0,80), m weitere +1–2. Ein frühes Plateau (Epoche 40 von 100) bei n ist typisch für Kapazitätsgrenze kombiniert mit Label-Mehrdeutigkeit; Test: s mit 50 Epochen auf einer Teilmenge (z. B. 4.000 Bilder) – steigt mAP deutlich, war n zu klein.
- mAP50-95 von 0,46 bei mAP50 0,75 weist auf ungenaue Boxgrenzen hin (bei Rissen, Harz, Bläue fachlich unscharf), nicht nur auf Modellkapazität.

### Gaps
- Keine Studie mit YOLO11 n/s/m/l auf Kodytek bei 1280 gefunden.

## 7. Inferenz auf Edge (Jetson Orin) für Echtzeit-Zeilenscan

### Takeaway
Nano-Modelle laufen auf Jetson Orin mit TensorRT FP16 bei 640 in ca. 2,6–4,6 ms pro Bild (ohne Vor-/Nachverarbeitung); bei 1280 bzw. 2–3 Kacheln pro Bild und s-Modell realistisch 20–60 ms pro Scanbild (Schätzung) – für Zeilenscan bei moderater Vorschubgeschwindigkeit ausreichend.

### Cited Findings
- YOLO26n TensorRT, 640, Inferenz ohne Pre/Post (ms/Bild, mAP50-95): AGX Orin 64 GB FP16 2,62 (0,479), INT8 2,30 (0,464); Orin NX 16 GB FP16 4,13, INT8 3,49; Orin Nano Super FP16 4,57, INT8 3,80 (0,449) — [Ultralytics NVIDIA Jetson Guide](https://docs.ultralytics.com/guides/nvidia-jetson/)
- YOLO11 T4-TensorRT-Latenzen n 1,5 ms bis x 11,3 ms (640) — [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/)
- CFIS-YOLO (s-Klasse, 7,17 M Params) auf SOPHON BM1684X: 135 FPS, 17 W, mAP50 77,0 vs. 77,5 auf A10 (103 FPS, 98 W) — [CFIS-YOLO](https://arxiv.org/pdf/2504.11305)

### Inferences (Schätzungen)
- Skalierung: 1280 ≈ 4x Pixel → n auf Orin NX FP16 ca. 15–20 ms; s ca. 3x n → 45–60 ms; mit Vor-/Nachverarbeitung +5–10 ms. Beispiel: Kamerabild deckt 0,5 m Brettlänge ab, Vorschub 0,5 m/s → 1 Bild/s nötig; selbst m-Modell auf Orin NX ausreichend. Bei 2 m/s und 0,25 m pro Bild → 8 Bilder/s → s-Modell auf Orin NX knapp, AGX Orin komfortabel.
- INT8 kostet auf COCO 1,5–3 Punkte mAP50-95; für kleine Fehler (Nagellöcher) vorher am eigenen Validierungssatz prüfen.

### Gaps
- Keine YOLO11-s/m-Zahlen auf Jetson aus der Ultralytics-Seite extrahierbar; keine Jetson-Messung für Holzfehler gefunden.

## 8. Gesamturteil: Daten oder Rechenleistung als Engpass?

### Takeaway
**Daten (Annotation mit Fachwissen und Abdeckung der Altholz-Domäne) sind in beiden Szenarien der Engpass, nicht Rechenleistung.** Szenario A braucht nur Stunden Rechenzeit (sogar auf dem Mac), aber ca. 4–30 h Annotation; Szenario B braucht auf dem Mac 1–5 Tage pro Lauf (n/s), aber ca. 70–400 h Annotation. Rechenleistung wird erst bei Modellvergleichen mit m/l bei 1280 und vielen Wiederholungen spürbar – dafür ist der Cluster sinnvoll.

### Cited Findings
- Annotationszeiten 7–35 s pro Box, ca. 80 s pro Polygon — [Papadopoulos et al. 2017](https://arxiv.org/abs/1708.02750v1); [arXiv 2407.18682](https://arxiv.org/html/2407.18682v1)
- Literatur erreicht Kodytek-Niveau mit ca. 3.500 Bildern bei 640 auf einer A10 — [CFIS-YOLO](https://arxiv.org/pdf/2504.11305)

### Inferences (Schätzungen, Übersicht)
| | Szenario A (300–2.000 Bilder, Cluster) | Szenario B (5.000–20.000 Bilder, Mac) |
|---|---|---|
| Annotation Boxen (4 Inst./Bild, 10 s, +20 % QA) | 4–27 h | 67–270 h |
| Annotation SAM-Masken (15 s) | 6–40 h | 100–400 h |
| Training n@1280, 100 Ep. | A100: ca. 0,2–1 h (Mac: 0,7–4,4 h) | Mac: 11–44 h |
| Training s@1280, 100 Ep. | A100: ca. 0,5–3 h | Mac: ca. 1,5–6 Tage |
| Training m@1280, 100 Ep. | A100: ca. 1–8 h | Mac: ca. 4–15 Tage (nicht empfohlen) |
| Engpass | Daten/Annotation, Domänenabdeckung | Daten/Annotation; Mac-Rechenzeit nur für s/m relevant |
- Empfohlener Ablauf: 300 eigene Bilder labeln (Boxen; Masken nur für Flächenfehler), Kodytek-n/s als Startgewichte, Training lokal; dann Vorlabeln + Korrektur in 500er-Batches, Lernkurve (mAP vs. Bildzahl) selbst messen und stoppen, wenn der Zuwachs pro 500 Bilder < 1–2 Punkte fällt; Cluster nur für s/m-Vergleich und Endtraining.

### Gaps
- Instanzen pro Bild für Altholz unbekannt (Annahme 4) – bestimmt die Annotationszeit linear; sollte an den ersten 50 eigenen Bildern gemessen werden.
- Cluster-Wartezeiten und -Bedingungen unbekannt.
