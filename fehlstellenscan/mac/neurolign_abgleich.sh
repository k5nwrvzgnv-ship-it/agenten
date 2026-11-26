#!/usr/bin/env bash
# Abgleich der Neurolign-Ablage zwischen Jans Mac und dem Server (Jan 26.11.2026, docs/plan-neurolign-server.md).
# Der Server (neurolign.meldro.de) ist die Hauptablage: dort laden Henri und Felix hoch und dort wird gelabelt.
#
#   bash ~/fehlstellenscan/mac/neurolign_abgleich.sh hoch    neue Fotobox-Balken und die Kodytek-Auswahl auf den Server
#   bash ~/fehlstellenscan/mac/neurolign_abgleich.sh runter  alle Balken und Kodytek-Korrekturen vom Server auf den Mac
#
# Kodytek-Auswahl (Randfälle, Jan 26.11.2026 „immer auf der Domain“): hoch schickt die ausgewählten Bilder mit ihren
# Originalumrissen nach kodytek/quelle/ (gleicher Aufbau wie der Datensatz), dazu Korrekturen und Einmessung vom Mac,
# ohne etwas auf dem Server zu überschreiben, und auswahl.json zuletzt. runter holt Korrekturen und Einmessung zurück.
#
# hoch schickt nur Balken, die es auf dem Server noch nicht gibt oder die dort noch keine Labels haben, und nie mit
# --delete. Gibt es dieselbe ID auf dem Server mit anderem Anlegedatum, bricht es für diesen Balken ab.
# runter überschreibt Labels auf dem Mac mit denen vom Server. Ab jetzt nur noch auf neurolign.meldro.de labeln.
set -euo pipefail
SERVER=agents-user
FERN=agenten/fehlstellenscan/data/neurolign/aufnahmen
HIER=~/fehlstellenscan/aufnahmen
FILTER=(--exclude 'zuschnitt/' --include 'B*/' --include 'B*/**' --include 'klassen.json'
        --include 'kodytek/' --include 'kodytek/labels/***' --include 'kodytek/einmessung.json' --exclude '*')

# Was es auf dem Server gibt: je Zeile ID, Anlegedatum und "labels", wenn dort schon gelabelt wird
server_stand() {
  ssh "$SERVER" "cd $FERN 2>/dev/null && for b in B*/balken.json; do [ -e \"\$b\" ] || continue; d=\${b%/balken.json}; \
    a=\$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get(\"angelegt\",\"\"))' \"\$b\"); \
    l=\$(ls \"\$d/labels\" 2>/dev/null | head -1); echo \"\$d \$a \${l:+labels}\"; done" || true
}
angelegt_hier() { python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("angelegt",""))' "$1"; }

case "${1:-}" in
  runter)
    mkdir -p "$HIER"
    stand=$(server_stand)
    weg=()
    for pfad in "$HIER"/B*/balken.json; do
      [ -e "$pfad" ] || continue
      id=$(basename "$(dirname "$pfad")")
      fern=$(echo "$stand" | awk -v i="$id" '$1==i {print $2}')
      if [ -n "$fern" ] && [ "$fern" != "$(angelegt_hier "$pfad")" ]; then
        echo "$id: auf dem Server ist das ein anderer Balken. Nicht geholt, Mac-Balken bleibt."; weg+=(--exclude "/$id/")
      fi
    done
    rsync -av "${weg[@]}" "${FILTER[@]}" "$SERVER:$FERN/" "$HIER/"
    echo "Fertig. Training startet wie gewohnt in Neurolign auf dem Mac."
    ;;
  hoch)
    stand=$(server_stand)
    ssh "$SERVER" "mkdir -p $FERN"
    for pfad in "$HIER"/B*/balken.json; do
      [ -e "$pfad" ] || continue
      id=$(basename "$(dirname "$pfad")")
      angelegt=$(angelegt_hier "$pfad")
      zeile=$(echo "$stand" | awk -v i="$id" '$1==i' || true)
      if [ -n "$zeile" ]; then
        if [ "$(echo "$zeile" | awk '{print $2}')" != "$angelegt" ]; then
          echo "$id: auf dem Server gibt es einen anderen Balken mit dieser ID. Ausgelassen."; continue
        fi
        if [ "$(echo "$zeile" | awk '{print $3}')" = "labels" ]; then
          echo "$id: auf dem Server wird schon gelabelt. Ausgelassen."; continue
        fi
      fi
      rsync -av --exclude 'zuschnitt/' "$HIER/$id/" "$SERVER:$FERN/$id/"
    done
    auswahl="$HIER/kodytek/auswahl.json"
    if [ -e "$auswahl" ]; then
      liste=$(mktemp)
      # erste Zeile: Ordner des Datensatzes, danach je Bild der Pfad des Bildes und seiner Umrisse darin
      python3 - "$auswahl" > "$liste" <<'PY'
import json, sys
from pathlib import Path
auswahl = [Path(e["bild"]) for e in json.load(open(sys.argv[1], encoding="utf-8"))]
print(auswahl[0].parents[2] if auswahl else "")
for b in auswahl:
    print(f"images/{b.parent.name}/{b.name}")
    print(f"labels/{b.parent.name}/{b.stem}.txt")
PY
      quelle=$(head -1 "$liste")
      if [ -n "$quelle" ]; then
        ssh "$SERVER" "mkdir -p $FERN/kodytek/quelle"
        tail -n +2 "$liste" | rsync -a --files-from=- "$quelle/" "$SERVER:$FERN/kodytek/quelle/"
        for x in labels einmessung.json; do
          if [ -e "$HIER/kodytek/$x" ]; then rsync -a --ignore-existing "$HIER/kodytek/$x" "$SERVER:$FERN/kodytek/"; fi
        done
        rsync -a "$auswahl" "$SERVER:$FERN/kodytek/auswahl.json"
        echo "Kodytek-Auswahl: $(( $(wc -l < "$liste") / 2 )) Bilder auf dem Server."
      fi
      rm -f "$liste"
    fi
    echo "Fertig. Die Balken sind auf neurolign.meldro.de."
    ;;
  *)
    echo "Aufruf: bash $0 hoch|runter" >&2; exit 1 ;;
esac
