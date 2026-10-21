"""Liest shared/einstellungen.toml (keine Geheimnisse, liegt im Repo).

Die Datei gilt für alle Instanzen (ein Claude-Konto: Stufen, Plätze, Modelle). Eine Instanz darf
in ihrer eigenen <instanz>/einstellungen.toml nur [werkzeuge] für ihre Agenten ergänzen.
"""

import tomllib
from pathlib import Path

from .config import KONTINGENT_DIR, SHARED_DIR

DATEI = KONTINGENT_DIR / "einstellungen.toml"
INSTANZ_DATEI = SHARED_DIR / "einstellungen.toml"


def lade(datei: Path | None = None, instanz_datei: Path | None = None) -> dict:
    with open(datei or DATEI, "rb") as f:
        cfg = tomllib.load(f)
    instanz_datei = instanz_datei or INSTANZ_DATEI
    if instanz_datei != (datei or DATEI) and instanz_datei.exists():
        with open(instanz_datei, "rb") as f:
            eigen = tomllib.load(f)
        fremd = set(eigen) - {"werkzeuge"}
        if fremd:
            raise ValueError(f"{instanz_datei}: nur [werkzeuge] erlaubt, nicht {sorted(fremd)}")
        cfg["werkzeuge"] = {**cfg["werkzeuge"], **eigen.get("werkzeuge", {})}
    return cfg


def werkzeuge(cfg: dict, agent: str) -> list[str]:
    w = cfg["werkzeuge"]
    liste = w.get(agent, w["standard"])
    if "Bash" in liste:
        raise ValueError("Bash ist für Agenten nicht erlaubt (Claude handelt nie selbst nach außen)")
    return liste
