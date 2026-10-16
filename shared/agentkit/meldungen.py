"""Meldungs-Warteschlange: shared/meldungen/neu/ und gesendet/.

Für Hinweise an Jan, die keine Freigabe brauchen (Fristen, wichtige Mails,
Statusmeldungen). Der Agent legt die Meldung ab, die Telegram-Zentrale
verschickt sie und verschiebt sie nach gesendet/. Das Verschieben klappt nur
einmal, eine Meldung kommt also nicht doppelt. Schlägt das Senden fehl, bleibt
sie in neu/ und wird bei der nächsten Prüfung erneut versucht.

dateien: Dateien aus dem Agent-Ordner, die die Zentrale nach dem Text schickt.
"""

from pathlib import Path

from . import _ablage
from ._ablage import AblageFehler as MeldungFehler  # noqa: F401
from .config import SHARED_DIR

BASIS = SHARED_DIR / "meldungen"
AGENTEN_DIR = SHARED_DIR.parent


def melden(agent: str, text: str, dateien: list[Path] | None = None, basis: Path | None = None,
           agenten_dir: Path | None = None) -> str:
    """Legt eine Meldung an und gibt ihre ID zurück."""
    if not text.strip():
        raise MeldungFehler("Leere Meldung")
    eintrag_id = _ablage.neue_id(agent)
    anhaenge = _ablage.anhaenge_pruefen((agenten_dir or AGENTEN_DIR) / agent, dateien or [])
    _ablage.schreibe(_ablage.ordner(basis or BASIS, "neu") / f"{eintrag_id}.json", {
        "id": eintrag_id,
        "agent": agent,
        "text": text,
        "dateien": anhaenge,
        "erstellt": _ablage.jetzt(),
        "gesendet": None,
    })
    return eintrag_id


def neue(agent: str | None = None, basis: Path | None = None) -> list[dict]:
    """Noch nicht gesendete Meldungen, älteste zuerst."""
    return _ablage.liste(_ablage.ordner(basis or BASIS, "neu"), agent)


def als_gesendet(eintrag_id: str, basis: Path | None = None) -> dict:
    basis = basis or BASIS
    return _ablage.abschliessen(_ablage.ordner(basis, "neu"), _ablage.ordner(basis, "gesendet"),
                                eintrag_id, {"gesendet": _ablage.jetzt()})
