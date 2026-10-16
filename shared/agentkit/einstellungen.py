"""Liest shared/einstellungen.toml (keine Geheimnisse, liegt im Repo)."""

import tomllib
from pathlib import Path

from .config import SHARED_DIR

DATEI = SHARED_DIR / "einstellungen.toml"


def lade(datei: Path | None = None) -> dict:
    with open(datei or DATEI, "rb") as f:
        return tomllib.load(f)


def werkzeuge(cfg: dict, agent: str) -> list[str]:
    w = cfg["werkzeuge"]
    liste = w.get(agent, w["standard"])
    if "Bash" in liste:
        raise ValueError("Bash ist für Agenten nicht erlaubt (Claude handelt nie selbst nach außen)")
    return liste
