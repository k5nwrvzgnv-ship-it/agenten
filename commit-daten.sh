#!/usr/bin/env bash
# Committet NUR lia/instanz/reihen.toml (Änderungen aus der Web-App, später auch Skripte für Jan).
# Ausnahme vom Hook (Jan 03.11.2026, Strukturplan F4): Statt pruefen.sh (alle Tests, rund 76 s, bricht bei
# fremdem Rot ab) prüft es nur die Struktur über agentkit.struktur. Alle anderen Commits laufen über commit.sh.
# Dieselbe Sperre wie commit.sh, damit sich die Commits der Chats und der App nicht in die Quere kommen.
# Autor bleibt Jans git-Einstellung, die Nachricht nennt die Herkunft, z. B. „… (Lia, Web-App)“ (F5).
# Nie Lerngruppen-Text in die Nachricht.
# Aufruf aus beliebigem Ordner: ~/agenten/commit-daten.sh "Nachricht"
set -euo pipefail
cd "$(dirname "$0")"
PFAD=lia/instanz/reihen.toml

if [ $# -ne 1 ] || [ -z "$1" ]; then
  echo "Aufruf: ./commit-daten.sh \"Nachricht\" (committet nur $PFAD)" >&2
  exit 1
fi
nachricht=$1

# Sperre gilt bis zum Ende des Skripts (Dateideskriptor 9 bleibt offen)
exec 9>"$(git rev-parse --git-dir)/commit.sperre"
flock -n 9 || { echo "Anderer Commit läuft, warte ..." >&2; flock 9; }

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
