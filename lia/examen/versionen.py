"""Eigenes Git-Repo der Reihe (data/reihe/): jede Runde eine Version.

Plan Examensreihe, Schritt 6 (Jan 25.10.2026, Punkt 6 freigegeben): lokales Repo, nie gepusht, getrennt vom
Code-Repo, damit Lias Inhalte nicht ins Agenten-Repo geraten. data/ ist im Code-Repo ignoriert.
"""

import os
import subprocess
from pathlib import Path

AUTOR = {"GIT_AUTHOR_NAME": "Agent examen", "GIT_AUTHOR_EMAIL": "examen@localhost",
         "GIT_COMMITTER_NAME": "Agent examen", "GIT_COMMITTER_EMAIL": "examen@localhost"}


def _umgebung() -> dict:
    """Ohne geerbte GIT_*-Variablen (z. B. aus einem Commit-Hook des Code-Repos), mit festem Autor."""
    return {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")}, **AUTOR}


class VersionsFehler(Exception):
    """git ist gescheitert. Der Text ist für Jan."""


def _git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=_umgebung())
    if p.returncode != 0:
        raise VersionsFehler(f"git {' '.join(args)} in {repo}: {p.stderr.strip() or p.stdout.strip()}")
    return p.stdout.strip()


def sichern(repo: Path, nachricht: str) -> str:
    """Legt das Repo bei Bedarf an, nimmt alle Änderungen auf und committet. Gibt den Commit zurück.

    Ohne Änderungen: kein neuer Commit, der letzte wird zurückgegeben.
    """
    repo = Path(repo)
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    if _git(repo, "status", "--porcelain"):
        _git(repo, "commit", "-q", "-m", nachricht)
    return _git(repo, "rev-parse", "--short", "HEAD")
