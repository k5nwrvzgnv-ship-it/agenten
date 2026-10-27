"""Nächtliche Sicherung des Agenten-Repos auf Jans privates GitHub-Repo (Jan 27.10.2026).

Schiebt main zum Remote „sicherung“ (Deploy-Key ~/.ssh/github_sicherung, Host-Alias github-sicherung) und prüft,
dass GitHub danach denselben Stand hat. Schlägt etwas fehl, bekommt Jan eine Meldung in seiner Zentrale.
Nur committete Stände werden gesichert; data/ und .env sind nicht im Repo und gehen nie nach GitHub.
Aufruf (Timer sicherung.timer, oder von Hand): python3 /home/agent/agenten/shared/sicherung/sicherung.py
"""

import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))  # agentkit liegt in shared/

from agentkit import log, meldungen  # noqa: E402

AGENT = "sicherung"
REPO = HIER.parent.parent
REMOTE = "sicherung"
ZWEIG = "main"
ZEITLIMIT_S = 300
logger = log.hole_logger(HIER, AGENT)


def _git(repo: Path, *args: str, laufen=subprocess.run) -> subprocess.CompletedProcess:
    return laufen(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=ZEITLIMIT_S)


def sichern(repo: Path = REPO, laufen=subprocess.run) -> tuple[bool, str]:
    """Push nach GitHub und Abgleich. Rückgabe (ok, Text für Log bzw. Meldung)."""
    try:
        lokal = _git(repo, "rev-parse", ZWEIG, laufen=laufen)
        if lokal.returncode != 0:
            return False, f"Lokaler Stand von {ZWEIG} nicht lesbar: {lokal.stderr.strip()}"
        stand = lokal.stdout.strip()
        push = _git(repo, "push", "--porcelain", REMOTE, f"{ZWEIG}:{ZWEIG}", laufen=laufen)
        if push.returncode != 0:
            return False, f"git push fehlgeschlagen: {(push.stderr or push.stdout).strip()[-500:]}"
        fern = _git(repo, "ls-remote", REMOTE, f"refs/heads/{ZWEIG}", laufen=laufen)
        if fern.returncode != 0:
            return False, f"Abgleich mit GitHub fehlgeschlagen: {fern.stderr.strip()[-500:]}"
        fern_stand = fern.stdout.split()[0] if fern.stdout.split() else ""
        if fern_stand != stand:
            return False, f"GitHub hat {fern_stand[:7] or 'nichts'}, der Server {stand[:7]}"
    except subprocess.TimeoutExpired:
        return False, f"Zeitüberschreitung nach {ZEITLIMIT_S} s"
    except OSError as e:
        return False, f"git nicht ausführbar: {e}"
    return True, f"GitHub auf Stand {stand[:7]}"


def main(melden=meldungen.melden) -> int:
    ok, text = sichern()
    if ok:
        logger.info("Sicherung ok: %s", text)
        return 0
    logger.error("Sicherung fehlgeschlagen: %s", text)
    melden(AGENT, f"Sicherung nach GitHub fehlgeschlagen: {text}")
    return 0  # Jan ist informiert; ein Fehler hier (Meldung nicht möglich) fällt an ausfall@


if __name__ == "__main__":
    sys.exit(main())
