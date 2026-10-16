"""Auftrags-Warteschlange: shared/auftraege/neu/ und erledigt/.

Die Telegram-Zentrale legt hier Jans Aufträge und Korrekturen ab und startet
danach den Dienst des Agenten. Der Agent holt seine Aufträge, bearbeitet sie
und schließt sie ab. Stürzt er vorher ab, bleibt der Auftrag in neu/ und wird
beim nächsten Lauf wieder geholt.
"""

from pathlib import Path

from . import _ablage
from ._ablage import AblageFehler as AuftragFehler  # noqa: F401
from .config import SHARED_DIR

BASIS = SHARED_DIR / "auftraege"
ABSCHLUESSE = ("erledigt", "fehlgeschlagen")


def neuer_auftrag(
    agent: str,
    text: str,
    quelle: str = "telegram",
    bezug: str | None = None,
    basis: Path | None = None,
) -> str:
    """Legt einen Auftrag an und gibt seine ID zurück.

    bezug: ID eines Entwurfs, wenn der Auftrag eine Korrektur dazu ist.
    """
    basis = basis or BASIS
    if bezug is not None:
        _ablage.pruefe_id(bezug)
    eintrag_id = _ablage.neue_id(agent)
    eintrag = {
        "id": eintrag_id,
        "agent": agent,
        "text": text,
        "quelle": quelle,
        "bezug": bezug,
        "erstellt": _ablage.jetzt(),
        "status": "neu",
        "abgeschlossen": None,
        "ergebnis": "",
    }
    _ablage.schreibe(_ablage.ordner(basis, "neu") / f"{eintrag_id}.json", eintrag)
    return eintrag_id


def neue(agent: str | None = None, basis: Path | None = None) -> list[dict]:
    """Offene Aufträge, älteste zuerst."""
    return _ablage.liste(_ablage.ordner(basis or BASIS, "neu"), agent)


def erledigte(agent: str | None = None, basis: Path | None = None) -> list[dict]:
    return _ablage.liste(_ablage.ordner(basis or BASIS, "erledigt"), agent)


def abschliessen(
    eintrag_id: str,
    ergebnis: str = "",
    status: str = "erledigt",
    basis: Path | None = None,
) -> dict:
    """Verschiebt den Auftrag nach erledigt/ (status erledigt oder fehlgeschlagen)."""
    if status not in ABSCHLUESSE:
        raise AuftragFehler(f"Unbekannter Abschluss: {status!r}")
    basis = basis or BASIS
    return _ablage.abschliessen(
        _ablage.ordner(basis, "neu"),
        _ablage.ordner(basis, "erledigt"),
        eintrag_id,
        {"status": status, "abgeschlossen": _ablage.jetzt(), "ergebnis": ergebnis},
    )
