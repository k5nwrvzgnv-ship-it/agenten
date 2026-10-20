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

Gespräch: Ein abgeschlossener Auftrag trägt die Claude-Sitzung seines Laufs
(Feld sitzung). Antwortet Jan in Telegram auf die Meldung, legt die Zentrale
einen neuen Auftrag mit bezug=<alter Auftrag> und derselben sitzung an, und der
Agent setzt diese Sitzung fort statt neu anzufangen.

Dateien: Schickt Jan Dateien mit, verschiebt neuer_auftrag(..., dateien=) sie nach
<agent>/data/eingang/<auftrag-id>/ (dort darf Claude lesen, nicht im Repo). Die Pfade
stehen im Feld dateien und zusätzlich am Ende des Auftragstexts, damit jeder Agent
sie ohne eigenen Code im Prompt hat.
Umgekehrt gibt abschliessen(..., dateien=) Ergebnisdateien aus dem Agent-Ordner mit,
die Zentrale schickt sie Jan nach dem Ergebnistext.

Rückfragen per Meldung (siehe meldungen): Klick oder Antwort auf eine Meldung wird ein
Auftrag mit meldung=<Meldungs-ID> und dienst=<Dienst der Meldung>. Jeder Dienst holt
nur seine Aufträge: neue(agent, dienst=None) die ohne Dienst (<agent>.service),
neue(agent, dienst="uni-lernen") nur die für uni-lernen. Ohne Angabe kommen alle.
"""

import shutil
from pathlib import Path

from . import _ablage
from ._ablage import AblageFehler as AuftragFehler  # noqa: F401
from .config import SHARED_DIR

BASIS = SHARED_DIR / "auftraege"
AGENTEN_DIR = SHARED_DIR.parent
EINGANG = Path("data") / "eingang"
ABSCHLUESSE = ("erledigt", "fehlgeschlagen")
MODI = ("erledigen", "lernen")
ALLE = "*"  # neue(..., dienst=ALLE): Aufträge aller Dienste


def neuer_auftrag(
    agent: str,
    text: str,
    quelle: str = "telegram",
    modus: str = "erledigen",
    bezug: str | None = None,
    sitzung: str | None = None,
    dateien: list[Path] | None = None,
    meldung: str | None = None,
    dienst: str | None = None,
    basis: Path | None = None,
    agenten_dir: Path | None = None,
) -> str:
    """Legt einen Auftrag an und gibt seine ID zurück.

    bezug: ID eines Entwurfs (Korrektur) oder Auftrags (Antwort darauf).
    sitzung: Claude-Sitzung, die der Agent fortsetzen soll.
    dateien: werden in den Agent-Ordner verschoben (siehe oben).
    meldung, dienst: Antwort auf eine Meldung (siehe oben).
    """
    if modus not in MODI:
        raise AuftragFehler(f"Unbekannter Modus: {modus!r}")
    basis = basis or BASIS
    if bezug is not None:
        _ablage.pruefe_id(bezug)
    if meldung is not None:
        _ablage.pruefe_id(meldung)
    _ablage.pruefe_dienst(agent, dienst)
    eintrag_id = _ablage.neue_id(agent)
    anhaenge = _dateien_ablegen((agenten_dir or AGENTEN_DIR) / agent, eintrag_id, dateien or [])
    if anhaenge:
        text += "\n\nAngehängte Dateien von Jan (im Agent-Ordner):\n" + "\n".join(f"- {p}" for p in anhaenge)
    eintrag = {
        "id": eintrag_id,
        "agent": agent,
        "text": text,
        "quelle": quelle,
        "modus": modus,
        "bezug": bezug,
        "sitzung": sitzung,
        "meldung": meldung,
        "dienst": dienst,
        "dateien": anhaenge,
        "erstellt": _ablage.jetzt(),
        "status": "neu",
        "abgeschlossen": None,
        "ergebnis": "",
    }
    _ablage.schreibe(_ablage.ordner(basis, "neu") / f"{eintrag_id}.json", eintrag)
    return eintrag_id


def _dateien_ablegen(agent_dir: Path, eintrag_id: str, dateien: list[Path]) -> list[str]:
    """Verschiebt die Dateien nach <agent>/data/eingang/<id>/, gibt Pfade relativ zum Agent-Ordner zurück."""
    if not dateien:
        return []
    if not agent_dir.is_dir():
        raise AuftragFehler(f"Agent-Ordner fehlt: {agent_dir}")
    ziel = agent_dir / EINGANG / eintrag_id
    ziel.mkdir(parents=True)
    pfade = []
    for quelle in map(Path, dateien):
        pfad, n = ziel / quelle.name, 2
        while pfad.exists():  # gleicher Name zweimal: nichts überschreiben
            pfad, n = ziel / f"{quelle.stem}-{n}{quelle.suffix}", n + 1
        shutil.move(quelle, pfad)
        pfade.append(str(pfad.relative_to(agent_dir)))
    return pfade


def neue(agent: str | None = None, basis: Path | None = None, dienst: str | None = ALLE) -> list[dict]:
    """Offene Aufträge, älteste zuerst. dienst: siehe oben."""
    eintraege = _ablage.liste(_ablage.ordner(basis or BASIS, "neu"), agent)
    if dienst == ALLE:
        return eintraege
    return [a for a in eintraege if a.get("dienst") == dienst]


def erledigte(agent: str | None = None, basis: Path | None = None) -> list[dict]:
    return _ablage.liste(_ablage.ordner(basis or BASIS, "erledigt"), agent)


def erledigter(eintrag_id: str, basis: Path | None = None) -> dict:
    """Ein abgeschlossener Auftrag per ID (z. B. der, auf den Jan antwortet)."""
    _ablage.pruefe_id(eintrag_id)
    pfad = _ablage.ordner(basis or BASIS, "erledigt") / f"{eintrag_id}.json"
    if not pfad.exists():
        raise AuftragFehler(f"{eintrag_id} ist nicht abgeschlossen")
    return _ablage.lies(pfad)


def abschliessen(
    eintrag_id: str,
    ergebnis: str = "",
    status: str = "erledigt",
    sitzung: str | None = None,
    dateien: list[Path] | None = None,
    basis: Path | None = None,
    agenten_dir: Path | None = None,
) -> dict:
    """Verschiebt den Auftrag nach erledigt/ (status erledigt oder fehlgeschlagen).

    sitzung: Claude-Sitzung des Laufs, damit Jan per Antwort darin weitermachen kann.
    dateien: Ergebnisdateien im Agent-Ordner (absolut oder relativ dazu), gehen an Jan.
    """
    if status not in ABSCHLUESSE:
        raise AuftragFehler(f"Unbekannter Abschluss: {status!r}")
    _ablage.pruefe_id(eintrag_id)
    agent = eintrag_id.split("-")[2]  # vor dem Verschieben prüfen, sonst bliebe der Auftrag halb abgeschlossen
    ergebnis_dateien = _ablage.anhaenge_pruefen((agenten_dir or AGENTEN_DIR) / agent, dateien or [])
    basis = basis or BASIS
    return _ablage.abschliessen(
        _ablage.ordner(basis, "neu"),
        _ablage.ordner(basis, "erledigt"),
        eintrag_id,
        {"status": status, "abgeschlossen": _ablage.jetzt(), "ergebnis": ergebnis, "sitzung": sitzung,
         "ergebnis_dateien": ergebnis_dateien},
    )
