"""Meldungs-Warteschlange: shared/meldungen/neu/ und gesendet/.

Für Hinweise an Jan, die keine Freigabe brauchen (Fristen, wichtige Mails,
Statusmeldungen). Der Agent legt die Meldung ab, die Telegram-Zentrale
verschickt sie und verschiebt sie nach gesendet/. Das Verschieben klappt nur
einmal, eine Meldung kommt also nicht doppelt. Schlägt das Senden fehl, bleibt
sie in neu/ und wird bei der nächsten Prüfung erneut versucht.

dateien: Dateien aus dem Agent-Ordner, die die Zentrale nach dem Text schickt.

Rückfragen: Mit knoepfe (Zeilen von Beschriftungen, z. B. [["Hingehen", "Nicht"]]) zeigt
die Zentrale Knöpfe unter der Meldung. Ein Klick (einmal je Meldung) oder Jans
Text-Antwort auf die Meldung wird ein Auftrag an den Agenten: Text = Beschriftung bzw.
Jans Antwort, quelle "knopf" bzw. "antwort", Feld meldung = ID dieser Meldung,
Feld dienst = dienst der Meldung. Die Zentrale startet danach <dienst>.service
(ohne dienst: <agent>.service). Antworten nimmt nur eine Meldung mit knoepfe oder dienst an.
"""

from pathlib import Path

from . import _ablage
from ._ablage import AblageFehler as MeldungFehler  # noqa: F401
from .config import SHARED_DIR

BASIS = SHARED_DIR / "meldungen"
AGENTEN_DIR = SHARED_DIR.parent
MAX_KNOPF_ZEILEN = 10
MAX_KNOPF_SPALTEN = 8  # mehr passt auf dem Handy nicht nebeneinander
MAX_KNOPF_LAENGE = 40


def melden(agent: str, text: str, dateien: list[Path] | None = None, knoepfe: list[list[str]] | None = None,
           dienst: str | None = None, basis: Path | None = None, agenten_dir: Path | None = None) -> str:
    """Legt eine Meldung an und gibt ihre ID zurück (knoepfe, dienst: siehe oben)."""
    if not text.strip():
        raise MeldungFehler("Leere Meldung")
    eintrag_id = _ablage.neue_id(agent)
    _knoepfe_pruefen(knoepfe or [])
    _ablage.pruefe_dienst(agent, dienst)
    anhaenge = _ablage.anhaenge_pruefen((agenten_dir or AGENTEN_DIR) / agent, dateien or [])
    _ablage.schreibe(_ablage.ordner(basis or BASIS, "neu") / f"{eintrag_id}.json", {
        "id": eintrag_id,
        "agent": agent,
        "text": text,
        "dateien": anhaenge,
        "knoepfe": knoepfe or [],
        "dienst": dienst,
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


def gesendete(eintrag_id: str, basis: Path | None = None) -> dict:
    """Eine gesendete Meldung per ID (z. B. die, auf die Jan antwortet oder klickt)."""
    _ablage.pruefe_id(eintrag_id)
    pfad = _ablage.ordner(basis or BASIS, "gesendet") / f"{eintrag_id}.json"
    if not pfad.exists():
        raise MeldungFehler(f"{eintrag_id} ist nicht gesendet")
    return _ablage.lies(pfad)


def nimmt_antwort(meldung: dict) -> bool:
    return bool(meldung.get("knoepfe") or meldung.get("dienst"))


def _knoepfe_pruefen(knoepfe: list[list[str]]) -> None:
    if len(knoepfe) > MAX_KNOPF_ZEILEN:
        raise MeldungFehler(f"Mehr als {MAX_KNOPF_ZEILEN} Knopfzeilen")
    for zeile in knoepfe:
        if not isinstance(zeile, list) or not 1 <= len(zeile) <= MAX_KNOPF_SPALTEN:
            raise MeldungFehler(f"Knopfzeile muss eine Liste mit 1 bis {MAX_KNOPF_SPALTEN} Knöpfen sein: {zeile!r}")
        for knopf in zeile:
            if not isinstance(knopf, str) or not knopf.strip() or len(knopf) > MAX_KNOPF_LAENGE:
                raise MeldungFehler(f"Ungültige Knopfbeschriftung (1 bis {MAX_KNOPF_LAENGE} Zeichen): {knopf!r}")
