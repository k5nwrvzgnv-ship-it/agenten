#!/usr/bin/env bash
# Prüft das ganze Repo: alle Tests (und den Linter, sobald er installiert ist).
# Aufruf aus beliebigem Ordner: ~/agenten/pruefen.sh
# Ergebnis: "ALLES GRÜN" und Exit-Code 0, sonst die Fehler und Exit-Code 1.
# Neue Agenten mit Tests hier unten bei TESTS eintragen.

cd "$(dirname "$0")" || exit 1
WURZEL=$(pwd)
FEHLER=0
# Tests schreiben Ereignisse (agentkit.ereignis) und Logs (agentkit.log) nie in die echten Dateien
WEGWERF=$(mktemp -d)
trap 'rm -rf "$WEGWERF"' EXIT
mkdir "$WEGWERF/ereignisse" "$WEGWERF/logs"
export AGENTKIT_EREIGNIS_DIR="$WEGWERF/ereignisse"
export AGENTKIT_LOG_DIR="$WEGWERF/logs"
# Tests starten nie das echte claude: Der Ersatz scheitert sofort und hinterlässt eine Spur,
# die unten als Fehler zählt (bis 16.11.2026 startete ein uni-Test bei jeder Prüfung einen echten Lauf).
export CLAUDE_SPUR="$WEGWERF/claude-gestartet"
printf '#!/bin/sh\necho "$PWD: $*" | cut -c1-300 >> "$CLAUDE_SPUR"\nexit 1\n' > "$WEGWERF/kein-claude"
chmod +x "$WEGWERF/kein-claude"
export AGENTKIT_CLAUDE_BIN="$WEGWERF/kein-claude"

# Ordner | Python | Testordner (relativ zum Ordner)
TESTS=(
  "shared|python3|agentkit/tests"
  "shared|python3|sicherung/tests"
  "shared/telegram|.venv/bin/python|tests"
  "shared/feedback|.venv/bin/python|tests"
  "shared/renderer|.venv/bin/python|tests"
  "shared/leitstand|.venv/bin/python|tests"
  "shared/webapp|.venv/bin/python|tests"
  "shared/arbeitsplatz|.venv/bin/python|tests"
  "uni|.venv/bin/python|tests"
  "uni/portal|../.venv/bin/python|tests"
  "dokumente|.venv/bin/python|tests"
  "posteingang|.venv/bin/python|tests"
  "holzbalkenscan|.venv/bin/python|tests"
  "finance|.venv/bin/python|tests"
  "fehlstellenscan|.venv/bin/python|tests"
  "kleinanzeigen|.venv/bin/python|tests"
  "lia/unterricht|.venv/bin/python|tests"
  "lia/auswertung|.venv/bin/python|tests"
  "lia/examen|.venv/bin/python|tests"
  "lia/recherche|.venv/bin/python|tests"
  "lia/theater|.venv/bin/python|tests"
  "lia/chat|.venv/bin/python|tests"
  "lia/schnell|.venv/bin/python|tests"
  "lia/verwaltung|.venv/bin/python|tests"
  "lia/vabali|.venv/bin/python|tests"
)

for eintrag in "${TESTS[@]}"; do
  IFS="|" read -r ordner python testordner <<< "$eintrag"
  ausgabe=$(cd "$WURZEL/$ordner" && "$python" -m unittest discover -s "$testordner" -t . 2>&1)
  if [ $? -eq 0 ]; then
    echo "ok      Tests $ordner ($(grep -o 'Ran [0-9]* tests\?' <<< "$ausgabe"))"
  else
    echo "FEHLER  Tests $ordner"
    echo "$ausgabe" | tail -30
    FEHLER=1
  fi
done

if [ -s "$CLAUDE_SPUR" ]; then
  echo "FEHLER  Ein Test hat claude gestartet (Ordner: Aufruf):"
  head -5 "$CLAUDE_SPUR"
  FEHLER=1
else
  echo "ok      kein Test hat claude gestartet"
fi

if [ -x "$WURZEL/.venv/bin/ruff" ]; then
  if ausgabe=$("$WURZEL/.venv/bin/ruff" check . 2>&1); then
    echo "ok      Linter ruff"
  else
    echo "FEHLER  Linter ruff"
    echo "$ausgabe" | tail -40
    FEHLER=1
  fi
fi

if [ $FEHLER -eq 0 ]; then
  echo "ALLES GRÜN"
else
  echo "NICHT GRÜN: erst reparieren, dann committen."
fi
exit $FEHLER
