"""Freigabe-Warteschlange: shared/freigabe/offen/ und erledigt/.

Agenten legen hier Entwürfe ab (Mails, Nachrichten, Käufe ...). Sie senden
oder bezahlen nie selbst. Die Telegram-Zentrale zeigt offene Entwürfe an
und trägt Jans Entscheidung ein:
- freigegeben
- abgelehnt (optional mit Begründung)
- aendern (mit Kommentar; der Agent erstellt daraus einen neuen Entwurf
  mit `vorgaenger` = alte ID)
"""

from pathlib import Path

from . import _ablage
from ._ablage import AblageFehler as FreigabeFehler  # noqa: F401
from .config import SHARED_DIR

BASIS = SHARED_DIR / "freigabe"
ENTSCHEIDUNGEN = ("freigegeben", "abgelehnt", "aendern")


def neuer_entwurf(
    agent: str,
    titel: str,
    inhalt: str,
    typ: str = "entwurf",
    daten: dict | None = None,
    vorgaenger: str | None = None,
    basis: Path | None = None,
) -> str:
    """Legt einen Entwurf an und gibt seine ID zurück.

    typ: z. B. "mail", "nachricht", "kauf". daten: alles, was der Agent nach
    der Freigabe braucht (Empfänger, Betreff, Link ...).
    """
    basis = basis or BASIS
    if vorgaenger is not None:
        _ablage.pruefe_id(vorgaenger)
    eintrag_id = _ablage.neue_id(agent)
    eintrag = {
        "id": eintrag_id,
        "agent": agent,
        "typ": typ,
        "titel": titel,
        "inhalt": inhalt,
        "daten": daten or {},
        "vorgaenger": vorgaenger,
        "erstellt": _ablage.jetzt(),
        "status": "offen",
        "entschieden": None,
        "kommentar": "",
    }
    _ablage.schreibe(_ablage.ordner(basis, "offen") / f"{eintrag_id}.json", eintrag)
    return eintrag_id


def offene(agent: str | None = None, basis: Path | None = None) -> list[dict]:
    return _ablage.liste(_ablage.ordner(basis or BASIS, "offen"), agent)


def erledigte(agent: str | None = None, basis: Path | None = None) -> list[dict]:
    return _ablage.liste(_ablage.ordner(basis or BASIS, "erledigt"), agent)


def entscheide(
    eintrag_id: str, status: str, kommentar: str = "", basis: Path | None = None
) -> dict:
    """Trägt Jans Entscheidung ein und verschiebt den Entwurf nach erledigt/."""
    if status not in ENTSCHEIDUNGEN:
        raise FreigabeFehler(f"Unbekannte Entscheidung: {status!r}")
    if status == "aendern" and not kommentar.strip():
        raise FreigabeFehler("Bei 'aendern' ist ein Kommentar nötig")
    basis = basis or BASIS
    return _ablage.abschliessen(
        _ablage.ordner(basis, "offen"),
        _ablage.ordner(basis, "erledigt"),
        eintrag_id,
        {"status": status, "entschieden": _ablage.jetzt(), "kommentar": kommentar},
    )
