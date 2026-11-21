#!/bin/bash
# Seg-Nachtlauf auf Jans Mac (Jan 19.11.2026): Probe bauen und trainieren, nur bei Erfolg den vollen Datensatz
# bauen, prüfen und 60 Epochen trainieren. Schritte einzeln: STATUS.md, Abschnitt „Mac: Seg-Datensatz“.
# Start in ~/fehlstellenscan mit aktiver .venv:   caffeinate -i bash seg_nacht.sh 2>&1 | tee seg_nacht.log
set -euo pipefail
cd ~/fehlstellenscan
ZIP="daten/kodytek/zip/Semantic Maps.zip"
SCHWELLE=0.9          # Überanpassungstest bestanden, wenn die beste Mask-mAP50 mindestens so hoch ist

schritt() { echo; echo "== $(date '+%d.%m. %H:%M') $*"; }

schritt "Fünf Masken ansehen"
python masken.py ansehen --masken "$ZIP" --anzahl 5

schritt "Probe-Datensatz (20 Bilder, train = val)"
[ -d datensaetze/kodytek-seg-probe20 ] || python masken.py bauen --vorlage datensaetze/kodytek-1 \
    --masken "$ZIP" --ziel datensaetze/kodytek-seg-probe20 --probe 20

schritt "Überanpassungstest"
yolo segment train data=datensaetze/kodytek-seg-probe20/data.yaml model=yolo11n-seg.pt epochs=150 imgsz=1280 \
    batch=4 mosaic=0 device=mps name=seg-probe20 exist_ok=True
python - "$SCHWELLE" <<'EOF'
import csv, sys
with open("runs/segment/seg-probe20/results.csv") as f:
    zeilen = [{k.strip(): v for k, v in z.items()} for z in csv.DictReader(f)]
werte = [float(z["metrics/mAP50(M)"]) for z in zeilen]
schwelle = float(sys.argv[1])
print(f"Probe Mask-mAP50: bester {max(werte):.3f}, letzter {werte[-1]:.3f}, Schwelle {schwelle}")
if max(werte) < schwelle:
    print("NICHT BESTANDEN: Umwandlung prüfen, volles Training nicht gestartet")
    sys.exit(1)
print("BESTANDEN")
EOF

schritt "Voller Seg-Datensatz"
[ -d datensaetze/kodytek-seg-1 ] || python masken.py bauen --vorlage datensaetze/kodytek-1 \
    --masken "$ZIP" --ziel datensaetze/kodytek-seg-1

schritt "Gegenprobe, Bilder, ultralytics liest den Datensatz"
python masken.py gegenprobe --seg datensaetze/kodytek-seg-1 --boxen datensaetze/kodytek-1 \
    --ausgabe gegenprobe-seg.json
python masken.py zeichnen --seg datensaetze/kodytek-seg-1 --ausgabe seg-bilder \
    100000000 100000061 100000062
python -c "from ultralytics.data.utils import check_det_dataset; print(check_det_dataset('datensaetze/kodytek-seg-1/data.yaml'))"

schritt "Volles Training, 60 Epochen (bricht batch=8 ab, folgt batch=4)"
yolo segment train data=datensaetze/kodytek-seg-1/data.yaml model=yolo11n-seg.pt epochs=60 imgsz=1280 batch=8 \
    device=mps name=kodytek-seg1-n1280 \
  || yolo segment train data=datensaetze/kodytek-seg-1/data.yaml model=yolo11n-seg.pt epochs=60 imgsz=1280 \
    batch=4 device=mps name=kodytek-seg1-n1280-b4

schritt "Fertig"
