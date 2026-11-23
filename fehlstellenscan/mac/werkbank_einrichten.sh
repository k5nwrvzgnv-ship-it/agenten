#!/bin/bash
# Werkbank auf Jans Mac einrichten (Freigabe Jan 23.11.2026): Skripte vom Server holen, ~/fehlstellenscan/.venv-werkbank
# mit Python 3.13 bauen, fiftyone installieren, Nutzungsstatistik abschalten. Erneut starten schadet nicht.
# Start (Mac-Terminal): bash ~/fehlstellenscan/mac/werkbank_einrichten.sh
set -euo pipefail
cd ~/fehlstellenscan
SERVER=agents-user:agenten/fehlstellenscan
PY=/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13

if [ ! -x "$PY" ]; then
    echo "Python 3.13 fehlt. Auf der Seite, die sich jetzt öffnet, die neueste 3.13.x nehmen"
    echo "(macOS 64-bit universal2 installer), installieren und dieses Skript erneut starten."
    open https://www.python.org/downloads/macos/
    exit 1
fi

echo "1/5 Skripte vom Server holen"
mkdir -p mac
scp -q "$SERVER"/{werkbank,auswertung,masken,datensatz}.py ./
scp -q "$SERVER"/mac/{requirements-werkbank.txt,werkbank_laden.py,werkbank_val.sh} mac/

if [ ! -x .venv-werkbank/bin/python ]; then
    echo "2/5 Umgebung .venv-werkbank bauen"
    "$PY" -m venv .venv-werkbank
else
    echo "2/5 Umgebung .venv-werkbank gibt es schon"
fi
echo "3/5 pip aktualisieren"
.venv-werkbank/bin/python -m pip install -q --upgrade pip
echo "4/5 fiftyone installieren (einige Minuten)"
.venv-werkbank/bin/python -m pip install -q -r mac/requirements-werkbank.txt

echo "5/5 Nutzungsstatistik abschalten"
mkdir -p ~/.fiftyone
.venv-werkbank/bin/python - <<'ENDE'
import json, pathlib
p = pathlib.Path.home() / ".fiftyone" / "config.json"
d = json.loads(p.read_text()) if p.exists() and p.read_text().strip() else {}
d["do_not_track"] = True
p.write_text(json.dumps(d, indent=4) + "\n")
ENDE
WERT=$(.venv-werkbank/bin/fiftyone config do_not_track)
echo "do_not_track: $WERT"
if [ "$(echo "$WERT" | tr "[:upper:]" "[:lower:]")" != "true" ]; then
    echo "FEHLER: Statistik ist nicht abgeschaltet. Bitte Claude melden."
    exit 1
fi
echo "Fertig: $(.venv-werkbank/bin/python --version), fiftyone $(.venv-werkbank/bin/python -c 'import fiftyone; print(fiftyone.__version__)')"
echo "Weiter mit: bash mac/werkbank_val.sh"
