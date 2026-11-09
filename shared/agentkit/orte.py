"""Orte des Arbeitsplatzes: freier Baum aus Seiten, beliebig tief (docs/arbeitsplatz-plan.md, Abschnitt Orte).

Datei <instanz>/orte.json: {"orte": [Knoten, ...]}, Knoten {"id", "titel", "eltern" (id oder None = oberste Ebene),
"position" (Reihenfolge unter Geschwistern, 0, 1, ...), "archiviert" (Zeitpunkt oder None), "angelegt"}.
ids nach dem Muster von agentkit.auftraege (ort=...), fest: Umbenennen ändert sie nicht.

Archivieren blendet den Knoten samt Unterseiten aus (nur der Knoten trägt die Marke), Wiederherstellen holt ihn
zurück. Gelöscht wird nichts.

Schreiben unter Sperre (<instanz>/.orte.sperre), atomar. Jede Änderung ist eine Aktion in <instanz>/orte-aktionen.json
mit den Knoten vorher und nachher; rueckgaengig(aktion) stellt die Knoten von vorher wieder her, wenn sie noch so sind
wie nachher (sonst Konflikt). Rückgängig ist selbst eine Aktion (also auch rückgängig zu machen).

Aufruf:
  from agentkit import orte
  aus = orte.anlegen("Modul Holzschutz")              # aus.id, aus.aktion, aus.text
  orte.anlegen("Kapitel 3", eltern=aus.id)
  orte.verschieben(id, eltern=None, position=0)        # kein Zyklus
  orte.umbenennen(id, "Neuer Titel"); orte.archivieren(id); orte.wiederherstellen(id)
  orte.rueckgaengig(aus.aktion); orte.letzte(20)
  baum = orte.laden(); orte.kinder(baum, None); orte.pfad(baum, id); orte.sichtbar(baum, id)
"""

import fcntl
import json
import os
import re
import secrets
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import _ablage, config
from .auftraege import REIHE_MUSTER as ID_MUSTER

DATEI = "orte.json"
AKTIONEN = "orte-aktionen.json"
SPERRE = ".orte.sperre"
MAX_TITEL = 200
MAX_ORTE = 5000
AKTIONEN_BEHALTEN = 500
SCHLUESSEL = ("id", "titel", "eltern", "position", "archiviert", "angelegt")


class OrtFehler(Exception):
    """Eingabe falsch oder Datei ungültig. Text ist für Jan lesbar."""


class Konflikt(OrtFehler):
    """Rückgängig geht nicht mehr, weil sich die Knoten seitdem geändert haben."""


@dataclass
class Ausgang:
    aktion: str
    id: str | None
    text: str


def _instanz(instanz: Path | None) -> Path:
    return Path(instanz) if instanz is not None else config.SHARED_DIR


def _lies_datei(instanz: Path) -> dict[str, dict]:
    pfad = instanz / DATEI
    if not pfad.exists():
        return {}
    try:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as f:
        raise OrtFehler(f"{pfad} ist nicht lesbar: {f}") from f
    if not isinstance(roh, dict) or not isinstance(roh.get("orte"), list):
        raise OrtFehler(f"{pfad}: erwartet {{\"orte\": [...]}}")
    knoten = {}
    for k in roh["orte"]:
        if not isinstance(k, dict) or not isinstance(k.get("id"), str) or not ID_MUSTER.fullmatch(k["id"]):
            raise OrtFehler(f"{pfad}: Knoten ohne gültige id: {str(k)[:80]}")
        if k["id"] in knoten:
            raise OrtFehler(f"{pfad}: id {k['id']} doppelt")
        if not isinstance(k.get("titel"), str) or not k["titel"].strip():
            raise OrtFehler(f"{pfad}: {k['id']} ohne Titel")
        if not isinstance(k.get("position", 0), int):
            raise OrtFehler(f"{pfad}: {k['id']} mit ungültiger Position")
        knoten[k["id"]] = {s: k.get(s) for s in SCHLUESSEL} | {"position": k.get("position", 0)}
    for k in knoten.values():
        if k["eltern"] is not None and k["eltern"] not in knoten:
            raise OrtFehler(f"{pfad}: {k['id']} hängt an unbekanntem Ort {k['eltern']!r}")
        if _hat_zyklus(knoten, k["id"]):
            raise OrtFehler(f"{pfad}: {k['id']} liegt in sich selbst")
    return knoten


def _hat_zyklus(knoten: dict[str, dict], start: str) -> bool:
    gesehen, k = set(), knoten.get(start)
    while k is not None and k["eltern"] is not None:
        if k["id"] in gesehen:
            return True
        gesehen.add(k["id"])
        k = knoten.get(k["eltern"])
    return False


def laden(instanz: Path | None = None) -> list[dict]:
    """Alle Knoten (auch archivierte), nach Eltern und Position sortiert. Fehlt die Datei: []."""
    knoten = _lies_datei(_instanz(instanz))
    return sorted(knoten.values(), key=lambda k: (k["eltern"] or "", k["position"], k["titel"].casefold()))


def kinder(baum: list[dict], eltern: str | None, archivierte: bool = False) -> list[dict]:
    """Direkte Unterseiten von eltern (None = oberste Ebene) nach Position."""
    return sorted((k for k in baum if k["eltern"] == eltern and (archivierte or not k["archiviert"])),
                  key=lambda k: (k["position"], k["titel"].casefold()))


def pfad(baum: list[dict], ort_id: str) -> list[dict]:
    """Knoten von der obersten Ebene bis ort_id (für Brotkrumen). Unbekannt: OrtFehler."""
    nach_id = {k["id"]: k for k in baum}
    if ort_id not in nach_id:
        raise OrtFehler(f"Ort {ort_id!r} gibt es nicht")
    weg, k = [], nach_id[ort_id]
    while k is not None and k not in weg:
        weg.append(k)
        k = nach_id.get(k["eltern"]) if k["eltern"] else None
    return weg[::-1]


def sichtbar(baum: list[dict], ort_id: str) -> bool:
    """Weder der Ort noch einer seiner Eltern ist archiviert."""
    return not any(k["archiviert"] for k in pfad(baum, ort_id))


def archiv(baum: list[dict]) -> list[dict]:
    """Archivierte Knoten (je der oberste archivierte eines Zweigs), zuletzt archivierte zuerst."""
    nach_id = {k["id"]: k for k in baum}
    oben = [k for k in baum if k["archiviert"]
            and not any(e["archiviert"] for e in pfad(baum, k["id"])[:-1])]
    return sorted(oben, key=lambda k: (k["archiviert"], nach_id[k["id"]]["titel"]), reverse=True)


def nachkommen(baum: list[dict], ort_id: str) -> set[str]:
    """ids aller Unterseiten (beliebig tief), ohne ort_id selbst."""
    ergebnis, offen = set(), [ort_id]
    while offen:
        eltern = offen.pop()
        for k in baum:
            if k["eltern"] == eltern and k["id"] not in ergebnis:
                ergebnis.add(k["id"])
                offen.append(k["id"])
    return ergebnis


# --- Schreiben ---------------------------------------------------------------------------------------------------

@contextmanager
def _gesperrt(instanz: Path):
    instanz.mkdir(parents=True, exist_ok=True)
    with open(instanz / SPERRE, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _schreibe_json(pfad: Path, daten) -> None:
    tmp = pfad.with_name(f".{pfad.name}.tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, pfad)


def _titel(wert) -> str:
    if not isinstance(wert, str):
        raise OrtFehler("Titel fehlt")
    titel = " ".join(wert.split())
    if not titel:
        raise OrtFehler("Titel fehlt")
    if len(titel) > MAX_TITEL:
        raise OrtFehler(f"Titel länger als {MAX_TITEL} Zeichen")
    return titel


def id_aus_titel(titel: str, vergeben: set[str]) -> str:
    """Lesbare, freie id aus dem Titel: Kleinbuchstaben, Umlaute umschrieben, höchstens 40 Zeichen, bei Bedarf -2 ..."""
    t = titel.casefold().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    basis = re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40].strip("-") or f"ort-{secrets.token_hex(3)}"
    kandidat, n = basis, 2
    while kandidat in vergeben:
        kandidat, n = f"{basis}-{n}", n + 1
    return kandidat


def _neu_nummerieren(knoten: dict[str, dict], eltern: str | None, reihenfolge: list[str]) -> None:
    for i, kid in enumerate(reihenfolge):
        knoten[kid]["position"] = i
    rest = sorted((k for k in knoten.values() if k["eltern"] == eltern and k["id"] not in reihenfolge),
                  key=lambda k: (k["position"], k["titel"].casefold()))
    for i, k in enumerate(rest, start=len(reihenfolge)):
        k["position"] = i


def _geschwister(knoten: dict[str, dict], eltern: str | None, ausser: str | None = None) -> list[str]:
    return [k["id"] for k in sorted((k for k in knoten.values() if k["eltern"] == eltern and k["id"] != ausser),
                                    key=lambda k: (k["position"], k["titel"].casefold()))]


def _knoten(knoten: dict[str, dict], ort_id) -> dict:
    if not isinstance(ort_id, str) or ort_id not in knoten:
        raise OrtFehler(f"Ort {ort_id!r} gibt es nicht")
    return knoten[ort_id]


def _ablauf(instanz: Path | None, aendern, rueckgaengig_von: str | None = None) -> Ausgang:
    """aendern(knoten) ändert das dict an Ort und Stelle und gibt (id, text) zurück."""
    instanz = _instanz(instanz)
    with _gesperrt(instanz):
        knoten = _lies_datei(instanz)
        vorher = json.loads(json.dumps(knoten))
        ort_id, text = aendern(knoten)
        if len(knoten) > MAX_ORTE:
            raise OrtFehler(f"Mehr als {MAX_ORTE} Orte")
        geaendert = sorted(k for k in set(vorher) | set(knoten) if vorher.get(k) != knoten.get(k))
        aktion = {"aktion": f"{_ablage.jetzt()[:19].replace(':', '').replace('-', '')}-{secrets.token_hex(3)}",
                  "zeit": _ablage.jetzt(), "text": text, "rueckgaengig_von": rueckgaengig_von,
                  "vorher": {k: vorher.get(k) for k in geaendert}, "nachher": {k: knoten.get(k) for k in geaendert}}
        _schreibe_json(instanz / DATEI, {"orte": sorted(knoten.values(), key=lambda k: (k["eltern"] or "",
                                                                                         k["position"], k["id"]))})
        aktionen = _aktionen(instanz)
        aktionen.append(aktion)
        _schreibe_json(instanz / AKTIONEN, aktionen[-AKTIONEN_BEHALTEN:])
    return Ausgang(aktion["aktion"], ort_id, text)


def _aktionen(instanz: Path) -> list[dict]:
    pfad = instanz / AKTIONEN
    if not pfad.exists():
        return []
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as f:
        raise OrtFehler(f"{pfad} ist nicht lesbar: {f}") from f
    return daten if isinstance(daten, list) else []


def anlegen(titel: str, eltern: str | None = None, ort_id: str | None = None,
            instanz: Path | None = None) -> Ausgang:
    """Neue Seite als letzte unter eltern (None = oberste Ebene). ort_id: feste id, sonst aus dem Titel."""
    titel = _titel(titel)

    def aendern(knoten):
        if eltern is not None:
            _knoten(knoten, eltern)
        if ort_id is not None:
            if not ID_MUSTER.fullmatch(ort_id):
                raise OrtFehler(f"Ungültige id: {ort_id!r}")
            if ort_id in knoten:
                raise OrtFehler(f"id {ort_id} ist schon vergeben")
        neu = ort_id or id_aus_titel(titel, set(knoten))
        knoten[neu] = {"id": neu, "titel": titel, "eltern": eltern, "position": len(_geschwister(knoten, eltern)),
                       "archiviert": None, "angelegt": _ablage.jetzt()}
        wo = f" unter „{knoten[eltern]['titel']}“" if eltern else ""
        return neu, f"Seite „{titel}“{wo} angelegt"
    return _ablauf(instanz, aendern)


def umbenennen(ort_id: str, titel: str, instanz: Path | None = None) -> Ausgang:
    titel = _titel(titel)

    def aendern(knoten):
        k = _knoten(knoten, ort_id)
        alt, k["titel"] = k["titel"], titel
        return ort_id, f"„{alt}“ heißt jetzt „{titel}“"
    return _ablauf(instanz, aendern)


def verschieben(ort_id: str, eltern: str | None, position: int | None = None,
                instanz: Path | None = None) -> Ausgang:
    """Hängt ort_id unter eltern (None = oberste Ebene) an Stelle position (None = ans Ende). Nicht in sich selbst
    oder eine eigene Unterseite."""
    if position is not None and (not isinstance(position, int) or position < 0):
        raise OrtFehler(f"Ungültige Position: {position!r}")

    def aendern(knoten):
        k = _knoten(knoten, ort_id)
        if eltern is not None:
            _knoten(knoten, eltern)
            if eltern == ort_id or eltern in nachkommen(list(knoten.values()), ort_id):
                raise OrtFehler(f"„{k['titel']}“ kann nicht in sich selbst liegen")
        alt_eltern = k["eltern"]
        k["eltern"] = eltern
        reihe = _geschwister(knoten, eltern, ausser=ort_id)
        reihe.insert(len(reihe) if position is None else min(position, len(reihe)), ort_id)
        _neu_nummerieren(knoten, eltern, reihe)
        if alt_eltern != eltern:
            _neu_nummerieren(knoten, alt_eltern, _geschwister(knoten, alt_eltern))
        wohin = f"unter „{knoten[eltern]['titel']}“" if eltern else "auf die oberste Ebene"
        return ort_id, f"„{k['titel']}“ {wohin} verschoben"
    return _ablauf(instanz, aendern)


def archivieren(ort_id: str, instanz: Path | None = None) -> Ausgang:
    def aendern(knoten):
        k = _knoten(knoten, ort_id)
        if k["archiviert"]:
            raise OrtFehler(f"„{k['titel']}“ ist schon archiviert")
        k["archiviert"] = _ablage.jetzt()
        return ort_id, f"„{k['titel']}“ archiviert"
    return _ablauf(instanz, aendern)


def wiederherstellen(ort_id: str, instanz: Path | None = None) -> Ausgang:
    def aendern(knoten):
        k = _knoten(knoten, ort_id)
        if not k["archiviert"]:
            raise OrtFehler(f"„{k['titel']}“ ist nicht archiviert")
        k["archiviert"] = None
        return ort_id, f"„{k['titel']}“ wiederhergestellt"
    return _ablauf(instanz, aendern)


def rueckgaengig(aktion_id: str, instanz: Path | None = None) -> Ausgang:
    """Macht eine Aktion rückgängig, wenn die betroffenen Knoten seitdem nicht geändert wurden."""
    inst = _instanz(instanz)
    with _gesperrt(inst):
        aktion = next((a for a in _aktionen(inst) if a.get("aktion") == aktion_id), None)
    if aktion is None:
        raise OrtFehler("Diese Änderung ist nicht mehr bekannt")

    def aendern(knoten):
        for kid, nachher in aktion["nachher"].items():
            if knoten.get(kid) != nachher:
                raise Konflikt("Seitdem wurde hier weiter geändert, Rückgängig geht nicht mehr")
        for kid, vorher in aktion["vorher"].items():
            if vorher is None:
                knoten.pop(kid, None)
            else:
                knoten[kid] = vorher
        for k in knoten.values():
            if k["eltern"] is not None and k["eltern"] not in knoten:
                raise Konflikt("Rückgängig würde eine Seite ohne Eltern hinterlassen")
        return next(iter(aktion["nachher"]), None), f"Rückgängig: {aktion['text']}"
    return _ablauf(instanz, aendern, rueckgaengig_von=aktion_id)


def letzte(anzahl: int = 20, instanz: Path | None = None) -> list[dict]:
    """Letzte Aktionen, neueste zuerst: {"aktion", "zeit", "text", "rueckgaengig_von"}."""
    return [{s: a.get(s) for s in ("aktion", "zeit", "text", "rueckgaengig_von")}
            for a in reversed(_aktionen(_instanz(instanz))[-anzahl:])]
