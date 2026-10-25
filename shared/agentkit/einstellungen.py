"""Liest shared/einstellungen.toml (keine Geheimnisse, liegt im Repo).

Die Datei gilt für alle Instanzen (ein Claude-Konto: Stufen, Plätze, Modelle). Eine Instanz darf
in ihrer eigenen <instanz>/einstellungen.toml nur [werkzeuge] und [webfetch] für ihre Agenten ergänzen und
[weitergabe] festlegen. [weitergabe] gilt nur in der Instanz, in deren Datei sie steht.

[webfetch] <agent> = ["domain", ...]: WebFetch nur auf diese Domains (Subdomains eingeschlossen).
claude_lauf erlaubt WebFetch dann nur je Domain, Python nutzt dieselbe Liste als Allowlist (agentkit.abruf).
Agenten ohne Eintrag: WebFetch wie bisher, falls es unter [werkzeuge] steht.
"""

import re
import tomllib
from pathlib import Path

from .config import KONTINGENT_DIR, SHARED_DIR

DATEI = KONTINGENT_DIR / "einstellungen.toml"
INSTANZ_DATEI = SHARED_DIR / "einstellungen.toml"


def lade(datei: Path | None = None, instanz_datei: Path | None = None) -> dict:
    with open(datei or DATEI, "rb") as f:
        cfg = tomllib.load(f)
    instanz_datei = instanz_datei or INSTANZ_DATEI
    if instanz_datei == (datei or DATEI):
        return cfg
    eigen = {}
    if instanz_datei.exists():
        with open(instanz_datei, "rb") as f:
            eigen = tomllib.load(f)
    fremd = set(eigen) - {"werkzeuge", "webfetch", "weitergabe"}
    if fremd:
        raise ValueError(f"{instanz_datei}: nur [werkzeuge], [webfetch] und [weitergabe] erlaubt, nicht {sorted(fremd)}")
    cfg["werkzeuge"] = {**cfg["werkzeuge"], **eigen.get("werkzeuge", {})}
    cfg["webfetch"] = {**cfg.get("webfetch", {}), **eigen.get("webfetch", {})}
    cfg["weitergabe"] = eigen.get("weitergabe", {})  # nie Jans Weitergaben erben
    return cfg


def weitergabe_erlaubt(cfg: dict, von: str, an: str) -> bool:
    """Darf Agent von dem Agenten an Aufträge geben? Nur was in [weitergabe] steht."""
    return an in cfg.get("weitergabe", {}).get(von, [])


def werkzeuge(cfg: dict, agent: str) -> list[str]:
    w = cfg["werkzeuge"]
    liste = w.get(agent, w["standard"])
    if "Bash" in liste:
        raise ValueError("Bash ist für Agenten nicht erlaubt (Claude handelt nie selbst nach außen)")
    return liste


_DOMAIN = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def webfetch_domains(cfg: dict, agent: str) -> list[str] | None:
    """Freigegebene Domains für WebFetch des Agenten (klein geschrieben), None ohne Eintrag.

    Nur reine Domainnamen ("bpb.de"), kein Schema, Pfad, Port oder Platzhalter. Sonst ValueError.
    """
    liste = cfg.get("webfetch", {}).get(agent)
    if liste is None:
        return None
    domains = []
    for d in liste:
        d = str(d).strip().lower()
        if not _DOMAIN.match(d):
            raise ValueError(f"[webfetch] {agent}: {d!r} ist kein reiner Domainname")
        domains.append(d)
    if not domains:
        raise ValueError(f"[webfetch] {agent}: Liste ist leer (WebFetch dann aus [werkzeuge] nehmen)")
    return domains
