#!/usr/bin/env bash
# Einmal auf Jans Mac (Jan 26.11.2026): Neurolign als Dienst, damit neurolign.meldro.de ein Training auf dem Mac
# starten kann. Holt das Programm vom Server, legt den Schlüssel für den Tunnel in ~/fehlstellenscan/.env und richtet
# launchd ein (startet bei der Anmeldung, nach einem Absturz neu).
#
#   bash ~/fehlstellenscan/mac/neurolign_einrichten.sh        einrichten oder auf den neuesten Stand bringen
#   bash ~/fehlstellenscan/mac/neurolign_einrichten.sh aus    Dienst stoppen und entfernen
set -euo pipefail
SERVER=agents-user
FERN=agenten/fehlstellenscan
HIER="$HOME/fehlstellenscan"
NAME=de.meldro.neurolign
PLIST="$HOME/Library/LaunchAgents/$NAME.plist"
LOG="$HOME/Library/Logs/neurolign.log"
ZIEL="gui/$(id -u)"

if [ "${1:-}" = "aus" ]; then
  launchctl bootout "$ZIEL/$NAME" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Dienst entfernt. Neurolign startet wieder nur von Hand."
  exit 0
fi

echo "1/6 Verbindung zum Server"
ssh -o BatchMode=yes "$SERVER" true || {
  echo "ssh $SERVER geht nicht ohne Passwortabfrage. Der Dienst braucht das. Abbruch."; exit 1; }

echo "2/6 Programm vom Server holen"
mkdir -p "$HIER/aufnahme" "$HIER/mac"
rsync -a --exclude '__pycache__/' --exclude 'app/' "$SERVER:$FERN/aufnahme/" "$HIER/aufnahme/"
rsync -a "$SERVER:$FERN/mac/neurolign_abgleich.sh" "$SERVER:$FERN/mac/neurolign_dienst.sh" \
  "$SERVER:$FERN/mac/neurolign_einrichten.sh" "$HIER/mac/"

echo "3/6 Schlüssel für den Tunnel"
zeile=$(ssh "$SERVER" "grep '^NEUROLIGN_TUNNEL_SCHLUESSEL=' $FERN/.env")
touch "$HIER/.env"; chmod 600 "$HIER/.env"
grep -v '^NEUROLIGN_TUNNEL_SCHLUESSEL=' "$HIER/.env" > "$HIER/.env.neu" || true
echo "$zeile" >> "$HIER/.env.neu"; mv "$HIER/.env.neu" "$HIER/.env"; chmod 600 "$HIER/.env"

echo "4/6 Python"
PY=$(command -v python3)
"$PY" -c 'import sys; sys.exit(sys.version_info < (3, 10))' || {
  echo "$PY ist älter als 3.10. Abbruch."; exit 1; }
echo "    $PY"

echo "5/6 Port 8765"
launchctl bootout "$ZIEL/$NAME" 2>/dev/null || true
sleep 1
if lsof -nP -iTCP:8765 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Neurolign läuft noch in einem Terminal. Dort mit ctrl-c beenden, dann dieses Skript noch einmal."; exit 1
fi

echo "6/6 Dienst einrichten"
mkdir -p "$(dirname "$PLIST")" "$(dirname "$LOG")"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$NAME</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$HIER/mac/neurolign_dienst.sh</string></array>
  <key>EnvironmentVariables</key><dict>
    <key>NEUROLIGN_PYTHON</key><string>$PY</string>
    <key>PATH</key><string>$(dirname "$PY"):/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
EOF
launchctl bootstrap "$ZIEL" "$PLIST"
echo "    gestartet, warte 15 s auf den Tunnel"
sleep 15

code=$(ssh "$SERVER" "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8797/api/training" || true)
if [ "$code" = "403" ]; then
  echo "Fertig. Der Server erreicht den Mac. Training geht jetzt auch auf neurolign.meldro.de."
  echo "Neurolign auf dem Mac: http://localhost:8765 (läuft jetzt immer, nicht mehr von Hand starten)."
else
  echo "Der Server erreicht den Mac noch nicht (Antwort $code). Letzte Zeilen aus $LOG:"
  tail -n 15 "$LOG" || true
  exit 1
fi
