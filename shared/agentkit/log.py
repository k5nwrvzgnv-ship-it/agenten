"""Logging für Agenten.

Schreibt nach <agent>/logs/<name>.log (max. 1 MB pro Datei, 5 alte Dateien
werden behalten) und zusätzlich nach stderr, damit es im journalctl landet.

Ist AGENTKIT_LOG_DIR gesetzt (pruefen.sh setzt einen Wegwerf-Ordner), landen die Dateien dort
unter <Ordnername des Agenten>/<name>.log: Tests schreiben so nie in echte Logs.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def ordner(agent_dir: Path) -> Path:
    """Wohin die Logdateien eines Agenten gehören (siehe Modulkommentar)."""
    if ersatz := os.environ.get("AGENTKIT_LOG_DIR"):
        return Path(ersatz) / Path(agent_dir).resolve().name
    return Path(agent_dir) / "logs"


def hole_logger(agent_dir: Path, name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:  # schon eingerichtet, nicht doppelt anhängen
        return logger
    log_dir = ordner(agent_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(FORMAT)

    datei = RotatingFileHandler(
        log_dir / f"{name}.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    datei.setFormatter(formatter)
    konsole = logging.StreamHandler(sys.stderr)
    konsole.setFormatter(formatter)

    logger.addHandler(datei)
    logger.addHandler(konsole)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
