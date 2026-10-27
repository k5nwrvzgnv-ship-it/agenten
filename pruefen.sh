#!/usr/bin/env bash
# Prüft das ganze Repo: alle Tests (und den Linter, sobald er installiert ist).
# Aufruf aus beliebigem Ordner: ~/agenten/pruefen.sh
# Ergebnis: "ALLES GRÜN" und Exit-Code 0, sonst die Fehler und Exit-Code 1.
# Neue Agenten mit Tests hier unten bei TESTS eintragen.

cd "$(dirname "$0")" || exit 1
WURZEL=$(pwd)
FEHLER=0

# Ordner | Python | Testordner (relativ zum Ordner)
TESTS=(
  "shared|python3|agentkit/tests"
  "shared|python3|sicherung/tests"
  "shared/telegram|.venv/bin/python|tests"
  "shared/renderer|.venv/bin/python|tests"
  "uni|.venv/bin/python|tests"
  "dokumente|.venv/bin/python|tests"
  "lia/unterricht|.venv/bin/python|tests"
  "lia/auswertung|.venv/bin/python|tests"
  "lia/examen|.venv/bin/python|tests"
  "lia/recherche|.venv/bin/python|tests"
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
