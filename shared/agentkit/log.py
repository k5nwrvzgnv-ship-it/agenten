"""Logging für Agenten.

Schreibt nach <agent>/logs/<name>.log (max. 1 MB pro Datei, 5 alte Dateien
werden behalten) und zusätzlich nach stderr, damit es im journalctl landet.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def hole_logger(agent_dir: Path, name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:  # schon eingerichtet, nicht doppelt anhängen
        return logger
    log_dir = Path(agent_dir) / "logs"
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
