"""Ablage der Rohdaten (claude.ai-Export, Zwischenstände, Ergebnisse) in data/.

Die Daten enthalten Lias Chats und damit möglicherweise Namen von Schülerinnen und Schülern.
Darum: Ordner nur für den User agent (chmod 700), Dateien chmod 600. data/ ist per .gitignore
vom Repo ausgeschlossen. Ohne Netz, getestet in tests/test_ablage.py.
"""

import os
import stat
from pathlib import Path

HIER = Path(__file__).resolve().parent
DATEN = HIER / "data"


class AblageFehler(Exception):
    pass


def datenordner(pfad: Path = DATEN) -> Path:
    """Legt den Ordner an (auch Elternordner) und setzt chmod 700. Gibt den Pfad zurück."""
    pfad.mkdir(parents=True, exist_ok=True)
    os.chmod(pfad, 0o700)
    return pfad


def schreiben(pfad: Path, text: str) -> None:
    """Schreibt text atomar mit chmod 600. Der Zielordner muss schon geschützt sein."""
    schreiben_bytes(pfad, text.encode("utf-8"))


def schreiben_bytes(pfad: Path, inhalt: bytes) -> None:
    """Wie schreiben, für Bytes."""
    ordner = pfad.parent
    if not ordner.is_dir():
        raise AblageFehler(f"Ordner fehlt: {ordner}")
    if stat.S_IMODE(ordner.stat().st_mode) & 0o077:
        raise AblageFehler(f"Ordner ist für andere lesbar: {ordner}")
    temp = pfad.with_name(pfad.name + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(inhalt)
    os.chmod(temp, 0o600)  # falls temp schon mit anderen Rechten existierte
    os.replace(temp, pfad)
