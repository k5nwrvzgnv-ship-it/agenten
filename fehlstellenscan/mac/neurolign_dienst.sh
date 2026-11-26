#!/usr/bin/env bash
# Neurolign auf Jans Mac als Dienst (launchd de.meldro.neurolign, eingerichtet mit neurolign_einrichten.sh).
# Startet Neurolign (http://localhost:8765, wie von Hand) mit einem zweiten Eingang 127.0.0.1:8766 nur fürs Training
# und hält einen SSH-Tunnel zum Server offen: Port 8797 auf dem Server führt zu diesem Eingang. So startet die Seite
# Training auf neurolign.meldro.de ein Training mit der Rechenleistung des Macs. Vor jedem Start holt Neurolign die
# Labels vom Server (neurolign_abgleich.sh runter). caffeinate -s hält den Mac am Netzteil wach, sonst schläft er wie
# immer und die Seite zeigt den Mac als nicht erreichbar.
set -u
HIER="$HOME/fehlstellenscan"
PY="${NEUROLIGN_PYTHON:-python3}"
SERVER=agents-user

caffeinate -s -w $$ &
"$PY" "$HIER/aufnahme/server.py" --still --tunnel-port 8766 --env "$HIER/.env" \
  --abgleich "$HIER/mac/neurolign_abgleich.sh" &
APP=$!
SSH=""
trap 'kill $APP $SSH 2>/dev/null' EXIT INT TERM

while kill -0 "$APP" 2>/dev/null; do
  if [ -z "$SSH" ] || ! kill -0 "$SSH" 2>/dev/null; then
    [ -n "$SSH" ] && echo "$(date '+%F %T') Tunnel weg, neuer Versuch"
    ssh -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
      -R 127.0.0.1:8797:127.0.0.1:8766 "$SERVER" &
    SSH=$!
  fi
  sleep 30
done
echo "$(date '+%F %T') Neurolign beendet, launchd startet neu"
exit 1
