#!/usr/bin/env bash
# Committet NUR lia/instanz/reihen.toml (Änderungen aus der Web-App, später auch Skripte für Jan).
# Ausnahme vom Hook (Jan 03.11.2026, Strukturplan F4): Statt pruefen.sh (alle Tests, rund 76 s, bricht bei
# fremdem Rot ab) prüft es nur die Struktur über agentkit.struktur. Alle anderen Commits laufen über commit.sh.
# Dieselbe Sperre wie commit.sh, damit sich die Commits der Chats und der App nicht in die Quere kommen.
# Autor bleibt Jans git-Einstellung, die Nachricht nennt die Herkunft, z. B. „… (Lia, Web-App)“ (F5).
# Nie Lerngruppen-Text in die Nachricht.
# Aufruf aus beliebigem Ordner: ~/agenten/commit-daten.sh "Nachricht"
#   committet die Datei, wie sie gerade ist (von Hand, Jan).
# Aus der Warteschlange der Web-App (agentkit.strukturpflege): ~/agenten/commit-daten.sh "Nachricht" <stand> <blob>
#   committet genau den Inhalt der Datei <stand> als lia/instanz/reihen.toml, nicht die Arbeitsdatei, damit jede
#   Aktion ihren eigenen Commit bekommt, auch wenn die Datei schon weiter ist. Nur, wenn HEAD noch den Stand <blob>
#   (git rev-parse HEAD:lia/instanz/reihen.toml) hat, sonst Ausgang 3 und nichts committet. Arbeitsdatei und
#   gemeinsamer Index bleiben unberührt (nur der Index-Eintrag dieses Pfads folgt dem neuen HEAD).
set -euo pipefail
cd "$(dirname "$0")"
PFAD=lia/instanz/reihen.toml

if { [ $# -ne 1 ] && [ $# -ne 3 ]; } || [ -z "$1" ]; then
  echo "Aufruf: ./commit-daten.sh \"Nachricht\" [<stand> <blob>] (committet nur $PFAD)" >&2
  exit 1
fi
nachricht=$1

# Sperre gilt bis zum Ende des Skripts (Dateideskriptor 9 bleibt offen)
exec 9>"$(git rev-parse --git-dir)/commit.sperre"
flock -n 9 || { echo "Anderer Commit läuft, warte ..." >&2; flock 9; }

if [ $# -eq 3 ]; then
  stand=$2
  erwartet=$3
  if [ "$(git rev-parse -q --verify "HEAD:$PFAD")" != "$erwartet" ]; then
    echo "HEAD hat inzwischen einen anderen Stand von $PFAD, nichts committet." >&2
    exit 3
  fi
  # Struktur des Stands prüfen, in einem Temp-Ordner als eigene Instanz (die Lerngruppe ist nicht im Repo)
  ordner=$(mktemp -d)
  trap 'rm -rf "$ordner"' EXIT
  cp -- "$stand" "$ordner/reihen.toml"
  if ! (cd shared && env -u AGENTKIT_INSTANZ python3 -m agentkit.struktur "$ordner"); then
    echo "Commit abgebrochen: der Stand für $PFAD ist ungültig (siehe oben)." >&2
    exit 1
  fi
  blob=$(git hash-object -w -- "$stand")
  if [ "$blob" = "$erwartet" ]; then
    echo "$PFAD ist unverändert, nichts zu committen."
    exit 0
  fi
  # Baum = HEAD mit diesem einen Blob, gebaut in einem eigenen Index (der gemeinsame Index bleibt, wie er ist)
  modus=$(git ls-tree HEAD -- "$PFAD" | cut -d' ' -f1)
  GIT_INDEX_FILE="$ordner/index" git read-tree HEAD
  GIT_INDEX_FILE="$ordner/index" git update-index --cacheinfo "${modus:-100644},$blob,$PFAD"
  baum=$(GIT_INDEX_FILE="$ordner/index" git write-tree)
  alt=$(git rev-parse HEAD)
  neu=$(git commit-tree "$baum" -p "$alt" -m "$nachricht")
  # Nur, wenn HEAD noch $alt ist (unter der Sperre ohnehin); kein Hook, siehe oben
  git update-ref -m "commit-daten: $nachricht" HEAD "$neu" "$alt"
  git reset -q -- "$PFAD"
  echo "$neu"
  exit 0
fi

# Nur die Struktur prüfen (reihen.toml und lerngruppen.toml der Instanz). Ungültig: kein Commit.
if ! (cd shared && env -u AGENTKIT_INSTANZ python3 -m agentkit.struktur "$(dirname "$(pwd)")/lia/instanz"); then
  echo "Commit abgebrochen: $PFAD ist ungültig (siehe oben)." >&2
  exit 1
fi

if git diff --quiet HEAD -- "$PFAD"; then
  echo "$PFAD ist unverändert, nichts zu committen."
  exit 0
fi

# --no-verify: der Hook (pruefen.sh) läuft hier bewusst nicht, siehe oben. Nur dieser eine Pfad.
git add -- "$PFAD"
git commit --no-verify -m "$nachricht" -- "$PFAD"
