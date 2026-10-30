#!/usr/bin/env bash
# Committet nur die genannten Pfade. Mehrere Chats teilen sich den Index von git,
# deshalb laufen Commits über eine Sperre (flock) nacheinander, nie gleichzeitig.
# Aufruf aus beliebigem Ordner: ~/agenten/commit.sh "Nachricht" pfad [pfad ...]
# Pfade relativ zum Hauptordner. Der Hook githooks/pre-commit (pruefen.sh) läuft einmal.
set -euo pipefail
cd "$(dirname "$0")"

if [ $# -lt 2 ] || [ -z "$1" ]; then
  echo "Aufruf: ./commit.sh \"Nachricht\" pfad [pfad ...]" >&2
  exit 1
fi
nachricht=$1
shift

# Sperre gilt bis zum Ende des Skripts (Dateideskriptor 9 bleibt offen)
exec 9>"$(git rev-parse --git-dir)/commit.sperre"
flock -n 9 || { echo "Anderer Commit läuft, warte ..." >&2; flock 9; }

# Nur diese Pfade vormerken (auch neue und gelöschte Dateien) und nur sie committen
git add -A -- "$@"
git commit -m "$nachricht" -- "$@"
