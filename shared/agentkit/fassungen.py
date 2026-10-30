"""Fassungen eines Auftrags: "final" und eigene Fassungen der Person (Board Punkt 10, Jan 30.10.2026).

Ein Auftrag mit Nachbesserungen ist eine Kette über bezug (Nachbesserung -> voriges Ergebnis). Ihr erster
Auftrag heißt Ursprung. Je Ursprung eine JSON-Datei <instanz>/fassungen/<ursprung>.json:
  {"ursprung": "<id>", "agent": "unterricht",
   "final": {"fassung": "<auftrags-id aus der Kette>" oder "eigene-<n>", "zeit": "<iso>"} oder null,
   "eigene": [{"n": 1, "name": "Blatt.docx", "datei": "data/eingang/<ursprung>/eigene-1/Blatt.docx",
               "notiz": "", "zeit": "<iso>"}]}
Die Dateien eigener Fassungen liegen im Ordner des Agenten (datei relativ dazu), dort darf Claude sie lesen.

Wofür:
- final: Agenten nehmen finale Fassungen als Beispiel (finale(agent)).
- eigene Fassung: Grundlage der nächsten Nachbesserung (grundlage(auftrag_id)); der Feedback-Dienst hängt sie an.
Rückmeldung mit Datei (rueckmeldung): Die Datei wird eine eigene Fassung, der Feedback-Dienst liest ihre
Word-Kommentare und hängt sie als Kopie an die Nachbesserung.
Schreiben: die Web-App (final_setzen, eigene_dazu, rueckmeldung). Alle Funktionen nehmen basis= wie agentkit.auftraege
(Warteschlange der Instanz); die Fassungen liegen daneben in basis.parent / "fassungen".
"""

import fcntl
import re
import shutil
from contextlib import contextmanager
from pathlib import Path

from . import _ablage, auftraege
from ._ablage import AblageFehler as FassungFehler  # noqa: F401
from .auftraege import AGENTEN_DIR, BASIS, EINGANG

EIGENE = re.compile(r"eigene-([1-9][0-9]{0,3})")
MAX_NOTIZ = 2000


def _ordner(basis: Path | None) -> Path:
    return (basis or BASIS).parent / "fassungen"


def _alle(agent: str, basis: Path) -> dict[str, dict]:
    """Offene und abgeschlossene Aufträge eines Agenten nach ID."""
    return {a["id"]: a for a in auftraege.erledigte(agent, basis) + auftraege.neue(agent, basis)}


def _auftrag(auftrag_id: str, basis: Path) -> dict:
    _ablage.pruefe_id(auftrag_id)
    agent = auftrag_id.split("-")[2]
    a = _alle(agent, basis).get(auftrag_id)
    if a is None:
        raise FassungFehler(f"Auftrag {auftrag_id} nicht gefunden")
    return a


def _ursprung_in(a: dict, alle: dict[str, dict]) -> str:
    return _weg(a, alle)[-1]


def _weg(a: dict, alle: dict[str, dict]) -> list[str]:
    """IDs von a über bezug zurück bis zum Ursprung (Ursprung zuletzt)."""
    weg = [a["id"]]
    while (b := alle.get(a.get("bezug") or "")) and b["id"] not in weg:
        weg.append(b["id"])
        a = b
    return weg


def ursprung(auftrag_id: str, basis: Path | None = None) -> str:
    """Erster Auftrag der Kette über bezug (nur Aufträge desselben Agenten)."""
    basis = basis or BASIS
    a = _auftrag(auftrag_id, basis)
    return _ursprung_in(a, _alle(a["agent"], basis))


def kette(auftrag_id: str, basis: Path | None = None) -> list[dict]:
    """Alle Aufträge mit demselben Ursprung, nach Stufe der Kette (Ursprung vorn)."""
    basis = basis or BASIS
    a = _auftrag(auftrag_id, basis)
    alle = _alle(a["agent"], basis)
    u = _ursprung_in(a, alle)
    return sorted((b for b in alle.values() if _ursprung_in(b, alle) == u),
                  key=lambda b: (len(_weg(b, alle)), b["id"]))


@contextmanager
def _gesperrt(basis: Path | None):
    ordner = _ordner(basis)
    ordner.mkdir(parents=True, exist_ok=True)
    with open(ordner / ".lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield ordner
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _lies(ordner: Path, u: str) -> dict:
    pfad = ordner / f"{u}.json"
    if pfad.exists():
        return _ablage.lies(pfad)
    return {"ursprung": u, "agent": u.split("-")[2], "final": None, "eigene": []}


def lesen(auftrag_id: str, basis: Path | None = None) -> dict:
    """Stand der Kette, zu der auftrag_id gehört (leer, wenn nichts gespeichert ist)."""
    return _lies(_ordner(basis), ursprung(auftrag_id, basis))


def final_setzen(auftrag_id: str, fassung: str | None, basis: Path | None = None) -> dict:
    """Markiert eine Fassung der Kette als final. fassung: ID eines erledigten Auftrags der Kette oder
    "eigene-<n>"; None nimmt die Markierung zurück. Gibt den neuen Stand zurück."""
    basis = basis or BASIS
    u = ursprung(auftrag_id, basis)
    if fassung is not None and not EIGENE.fullmatch(fassung):
        if fassung not in {a["id"] for a in kette(u, basis) if a.get("status") == "erledigt"}:
            raise FassungFehler(f"{fassung} ist keine erledigte Fassung von {u}")
    with _gesperrt(basis) as ordner:
        stand = _lies(ordner, u)
        if fassung is not None and EIGENE.fullmatch(fassung) \
                and fassung not in {f"eigene-{e['n']}" for e in stand["eigene"]}:
            raise FassungFehler(f"{fassung} gibt es zu {u} nicht")
        stand["final"] = None if fassung is None else {"fassung": fassung, "zeit": _ablage.jetzt()}
        _ablage.schreibe(ordner / f"{u}.json", stand)
    return stand


def eigene_dazu(auftrag_id: str, datei: Path, notiz: str = "", basis: Path | None = None,
                agenten_dir: Path | None = None) -> dict:
    """Verschiebt eine eigene Fassung (z. B. Word mit Kommentaren) zum Agenten der Kette und trägt sie ein.
    Gibt den Eintrag zurück ({"n", "name", "datei", "notiz", "zeit"}), Fassung heißt dann "eigene-<n>"."""
    basis = basis or BASIS
    datei = Path(datei)
    if not datei.is_file():
        raise FassungFehler(f"Datei fehlt: {datei}")
    if datei.stat().st_size > _ablage.MAX_ANHANG_BYTES:
        raise FassungFehler(f"Datei größer als {_ablage.MAX_ANHANG_BYTES // 2**20} MB: {datei.name}")
    if len(notiz) > MAX_NOTIZ:
        raise FassungFehler(f"Notiz länger als {MAX_NOTIZ} Zeichen")
    u = ursprung(auftrag_id, basis)
    agent_dir = (agenten_dir or AGENTEN_DIR) / u.split("-")[2]
    if not agent_dir.is_dir():
        raise FassungFehler(f"Agent-Ordner fehlt: {agent_dir}")
    with _gesperrt(basis) as ordner:
        stand = _lies(ordner, u)
        n = max((e["n"] for e in stand["eigene"]), default=0) + 1
        ziel = agent_dir / EINGANG / u / f"eigene-{n}"
        ziel.mkdir(parents=True)
        name = datei.name.lstrip(".") or "fassung"
        shutil.move(datei, ziel / name)
        eintrag = {"n": n, "name": name, "datei": (ziel / name).relative_to(agent_dir).as_posix(),
                   "notiz": notiz.strip(), "zeit": _ablage.jetzt()}
        stand["eigene"].append(eintrag)
        _ablage.schreibe(ordner / f"{u}.json", stand)
    return eintrag


def grundlage(auftrag_id: str, basis: Path | None = None) -> dict | None:
    """Neueste eigene Fassung, wenn sie nach dem letzten erledigten Ergebnis der Kette kam (sonst None).
    Eintrag wie bei eigene_dazu; die nächste Nachbesserung soll auf ihr aufbauen."""
    basis = basis or BASIS
    stand = lesen(auftrag_id, basis)
    if not stand["eigene"]:
        return None
    neueste = max(stand["eigene"], key=lambda e: e["n"])
    zuletzt = max((a.get("abgeschlossen") or "" for a in kette(auftrag_id, basis) if a.get("status") == "erledigt"),
                  default="")
    return neueste if neueste["zeit"] >= zuletzt else None


def finale(agent: str, basis: Path | None = None) -> list[dict]:
    """Finale Fassungen eines Agenten, neueste zuerst: {"ursprung", "auftrag" (Text des Ursprungs),
    "fassung", "dateien" (relativ zum Agent-Ordner), "zeit"}. Als Beispiele für neue Aufträge."""
    _ablage.pruefe_agent(agent)
    basis = basis or BASIS
    ordner, alle = _ordner(basis), _alle(agent, basis)
    ergebnis = []
    for pfad in sorted(ordner.glob(f"*-{agent}-*.json")):
        stand = _ablage.lies(pfad)
        f = stand.get("final")
        if not f or stand.get("agent") != agent:
            continue
        if m := EIGENE.fullmatch(f["fassung"]):
            dateien = [e["datei"] for e in stand["eigene"] if e["n"] == int(m.group(1))]
        else:
            dateien = (alle.get(f["fassung"]) or {}).get("ergebnis_dateien") or []
        ursprung_auftrag = alle.get(stand["ursprung"]) or {}
        ergebnis.append({"ursprung": stand["ursprung"], "auftrag": ursprung_auftrag.get("text", ""),
                         "fassung": f["fassung"], "dateien": dateien, "zeit": f["zeit"]})
    return sorted(ergebnis, key=lambda e: e["zeit"], reverse=True)


def rueckmeldung(bezug: str, text: str, datei: Path | None = None, notiz: str = "", basis: Path | None = None,
                 agenten_dir: Path | None = None) -> tuple[str, dict | None]:
    """Feedback zum Ergebnis bezug an den Feedback-Dienst, optional mit Datei (z. B. Word mit Kommentaren).
    Die Datei wird erst eigene Fassung der Kette (eigene_dazu), dann entsteht der Auftrag an "feedback".
    Gibt (ID des Feedback-Auftrags, Eintrag der eigenen Fassung oder None) zurück. Den Dienst startet der Aufrufer."""
    basis = basis or BASIS
    if auftraege.erledigter(bezug, basis).get("status") != "erledigt":
        raise FassungFehler(f"{bezug} ist kein fertiges Ergebnis")
    eintrag = eigene_dazu(bezug, datei, notiz, basis, agenten_dir) if datei is not None else None
    fid = auftraege.neuer_auftrag("feedback", text, quelle="feedback", bezug=bezug, basis=basis,
                                  agenten_dir=agenten_dir)
    return fid, eintrag
