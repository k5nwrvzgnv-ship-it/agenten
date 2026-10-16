"""Auftrags-Warteschlange: shared/auftraege/neu/ und erledigt/.

Die Telegram-Zentrale legt hier Jans Aufträge und Korrekturen ab und startet
danach den Dienst des Agenten. Der Agent holt seine Aufträge, bearbeitet sie
und schließt sie ab. Stürzt er vorher ab, bleibt der Auftrag in neu/ und wird
beim nächsten Lauf wieder geholt.

Modus (gilt für alle Agenten, Standard ist "erledigen"):
- erledigen: Der Agent arbeitet allein und liefert danach ein verständliches
  Protokoll (was er getan hat, Quellen, Unsicherheiten, wie Jan es prüfen kann).
- lernen: Der Agent geht den Auftrag Schritt für Schritt gemeinsam mit Jan
  durch (erklären, Fragen stellen, Rückmeldung geben), per Telegram oder im
  Claude-Code-Chat am PC.
"""

from pathlib import Path

from . import _ablage
from ._ablage import AblageFehler as AuftragFehler  # noqa: F401
from .config import SHARED_DIR

BASIS = SHARED_DIR / "auftraege"
ABSCHLUESSE = ("erledigt", "fehlgeschlagen")
MODI = ("erledigen", "lernen")


def neuer_auftrag(
    agent: str,
    text: str,
    quelle: str = "telegram",
    modus: str = "erledigen",
    bezug: str | None = None,
    basis: Path | None = None,
) -> str:
    """Legt einen Auftrag an und gibt seine ID zurück.

    bezug: ID eines Entwurfs, wenn der Auftrag eine Korrektur dazu ist.
    """
    if modus not in MODI:
        raise AuftragFehler(f"Unbekannter Modus: {modus!r}")
    basis = basis or BASIS
    if bezug is not None:
        _ablage.pruefe_id(bezug)
    eintrag_id = _ablage.neue_id(agent)
    eintrag = {
        "id": eintrag_id,
        "agent": agent,
        "text": text,
        "quelle": quelle,
        "modus": modus,
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
