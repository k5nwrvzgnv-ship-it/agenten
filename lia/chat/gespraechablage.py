"""Gespräche als Objekte: data/gespraeche/<id>.json, Dateien in data/gespraeche/<id>/ (nur Python-Bordmittel).

Die Web-App nutzt das über schnittstelle.py, der Agent (agent.py, gespraechlauf.py) direkt. Schreiben nur unter
einer gemeinsamen Sperre (data/gespraeche/.sperre), weil Web-App (umbenennen, Nachricht) und Agent (Antwort)
dieselbe Datei ändern. Format: STATUS.md, Abschnitt „Gespräche“.
"""

import fcntl
import json
import os
import re
import shutil
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

ID_MUSTER = re.compile(r"^[0-9a-f]{12}$")
STRUKTUR_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")  # wie agentkit.struktur.ID_MUSTER
EBENEN = ("klasse", "reihe", "stunde")
OHNE_ORT = "ohne"  # gespraeche(OHNE_ORT): nur die ohne Ort
MAX_NAME = 80
TAGE = 30  # Jan 09.11.2026: 30 Tage ab der letzten Nachricht


class GespraechFehler(ValueError):
    """Ungültige Eingabe. Der Text ist ein fertiger Satz für Lia."""


def jetzt() -> datetime:
    return datetime.now().astimezone()


def zeit_text() -> str:
    return jetzt().isoformat(timespec="seconds")


def ordner_von(daten: Path) -> Path:
    return Path(daten) / "gespraeche"


def datei(gid: str, daten: Path) -> Path:
    return ordner_von(daten) / f"{gid}.json"


def dateien_ordner(gid: str, daten: Path) -> Path:
    """Ordner mit Lias Dateien des Gesprächs (je Nachricht ein Unterordner, Ablage-Fotos in ablage/)."""
    return ordner_von(daten) / gid


@contextmanager
def sperre(daten: Path):
    pfad = ordner_von(daten) / ".sperre"
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with open(pfad, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def ort_pruefen(ort) -> dict | None:
    """None (ohne Ort) oder {"ebene": klasse|reihe|stunde, "id": <id aus agentkit.struktur>}."""
    if ort is None:
        return None
    if (not isinstance(ort, dict) or set(ort) != {"ebene", "id"} or ort["ebene"] not in EBENEN
            or not isinstance(ort["id"], str) or not STRUKTUR_ID.match(ort["id"]) or len(ort["id"]) > 80):
        raise GespraechFehler("Der Ort ist ungültig.")
    return {"ebene": ort["ebene"], "id": ort["id"]}


def name_pruefen(name) -> str:
    if not isinstance(name, str):
        raise GespraechFehler("Der Name ist ungültig.")
    name = " ".join(name.split())
    if len(name) > MAX_NAME:
        raise GespraechFehler(f"Der Name ist zu lang (höchstens {MAX_NAME} Zeichen).")
    return name


def name_aus_text(text: str) -> str:
    """Name aus der ersten Nachricht: erste Zeile, an einer Wortgrenze auf höchstens 50 Zeichen gekürzt."""
    zeile = next((z.strip() for z in text.splitlines() if z.strip()), "")
    zeile = " ".join(zeile.split()).strip("#*> ")
    if len(zeile) <= 50:
        return zeile or "Gespräch"
    kurz = zeile[:50].rsplit(" ", 1)[0]
    return (kurz if len(kurz) >= 20 else zeile[:50]).rstrip(" ,.;:") + " …"


def lesen(gid: str, daten: Path) -> dict | None:
    if not ID_MUSTER.match(gid or ""):
        return None
    try:
        g = json.loads(datei(gid, daten).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return g if isinstance(g, dict) else None


def schreiben(g: dict, daten: Path) -> None:
    """Atomar (erst .tmp, dann umbenennen). Nur unter sperre() aufrufen."""
    ziel = datei(g["id"], daten)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    tmp = ziel.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, ziel)


def neu(gid: str, name: str, ort: dict | None) -> dict:
    z = zeit_text()
    return {"id": gid, "name": name, "name_vorschlag": not name, "ort": ort, "angelegt": z, "zuletzt": z,
            "sitzung": None, "kontext": {"ort": "", "ablage": []}, "gesehen": 0, "eintraege": []}


def laeuft(g: dict) -> bool:
    """True, solange Lias letzte Nachricht noch keine Antwort hat."""
    return any(e.get("rolle") == "lia" and e.get("stand") == "wartet" for e in g.get("eintraege", []))


def antworten_gesehen(g: dict) -> int:
    """Wie viele Antworten Lia schon gesehen hat (gesehen() setzt es auf alle)."""
    return g.get("gesehen") if isinstance(g.get("gesehen"), int) else 0


def kurz(g: dict) -> dict:
    """Übersicht eines Gesprächs für Listen."""
    eintraege = g.get("eintraege", [])
    claude = [e for e in eintraege if e.get("rolle") == "claude"]
    letzte = eintraege[-1]["text"] if eintraege else ""
    return {"id": g["id"], "name": g.get("name") or "Neues Gespräch", "ort": g.get("ort"),
            "angelegt": g.get("angelegt"), "zuletzt": g.get("zuletzt"), "nachrichten": len(eintraege),
            "laeuft": laeuft(g), "neu": len(claude) > antworten_gesehen(g),
            "vorschau": " ".join(letzte.split())[:160]}


def alle(daten: Path) -> list[dict]:
    o = ordner_von(daten)
    gs = [lesen(p.stem, daten) for p in o.glob("*.json")] if o.is_dir() else []
    return [g for g in gs if g]


def loeschen(gid: str, daten: Path) -> dict | None:
    """Gesprächsdatei und Dateiordner weg. Gibt das gelöschte Gespräch zurück (für die Sitzung) oder None."""
    g = lesen(gid, daten)
    if g is None:
        return None
    shutil.rmtree(dateien_ordner(gid, daten), ignore_errors=True)
    datei(gid, daten).unlink(missing_ok=True)
    return g


def alt(g: dict, tage: int = TAGE, heute: datetime | None = None) -> bool:
    try:
        return datetime.fromisoformat(g.get("zuletzt") or "") < (heute or jetzt()) - timedelta(days=tage)
    except ValueError:
        return True
