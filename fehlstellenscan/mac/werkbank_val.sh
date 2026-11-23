#!/bin/bash
# val in die Werkbank: Vorhersage mit dem Seg-Modell (Trainings-.venv, conf 0.05), Markierung und Vorhersage zum
# Server (für auswertung.py fehler), in FiftyOne laden und auswerten (.venv-werkbank), Bericht zum Server, dann
# Oberfläche unter http://localhost:5151 (Beenden mit ctrl-c). Vorher einmal mac/werkbank_einrichten.sh.
# Start (Mac-Terminal): bash ~/fehlstellenscan/mac/werkbank_val.sh
set -euo pipefail
cd ~/fehlstellenscan
SERVER=agents-user
ZIEL=agenten/fehlstellenscan/data/laeufe/kodytek-seg1-n1280
MODELL=runs/segment/kodytek-seg1-n1280/weights/best.pt
DATEN=datensaetze/kodytek-seg-1
NAME=kodytek-seg1-val

for p in "$MODELL" "$DATEN/images/val" "$DATEN/labels/val" .venv/bin/yolo .venv-werkbank/bin/python; do
    [ -e "$p" ] || { echo "FEHLER: $p fehlt"; exit 1; }
done

# yolo schreibt Textdateien anhängend: alte Vorhersagen vorher weg, sonst doppelte Zeilen
rm -rf val-vorhersage/seg1 runs/segment/val-vorhersage/seg1
echo "1/4 Vorhersage für val (2.026 Bilder, conf 0.05)"
.venv/bin/yolo segment predict model="$MODELL" source="$DATEN/images/val" imgsz=1280 conf=0.05 \
    retina_masks=True save_txt=True save_conf=True save=False project=val-vorhersage name=seg1 exist_ok=True \
    verbose=False
VORHERSAGE=""
for p in val-vorhersage/seg1/labels runs/segment/val-vorhersage/seg1/labels; do
    [ -d "$p" ] && VORHERSAGE="$p"
done
[ -n "$VORHERSAGE" ] || { echo "FEHLER: labels-Ordner der Vorhersage nicht gefunden"; exit 1; }
echo "   $(ls "$VORHERSAGE" | wc -l | tr -d ' ') Vorhersagedateien in $VORHERSAGE"

echo "2/4 Markierung und Vorhersage zum Server"
ssh "$SERVER" "rm -rf $ZIEL/val-auswertung/markierung $ZIEL/val-auswertung/vorhersage && mkdir -p $ZIEL/val-auswertung"
scp -rq "$DATEN/labels/val" "$SERVER:$ZIEL/val-auswertung/markierung"
scp -rq "$VORHERSAGE" "$SERVER:$ZIEL/val-auswertung/vorhersage"

echo "3/4 In FiftyOne laden und auswerten"
.venv-werkbank/bin/python -u mac/werkbank_laden.py kodytek --datensatz "$DATEN" --teil val \
    --vorhersage "$VORHERSAGE" --name "$NAME" --ersetzen --nur-laden | tee werkbank-val.txt
scp -q werkbank-val.txt "$SERVER:$ZIEL/"

echo "4/4 Oberfläche öffnen"
.venv-werkbank/bin/python mac/werkbank_laden.py zeigen --name "$NAME"
