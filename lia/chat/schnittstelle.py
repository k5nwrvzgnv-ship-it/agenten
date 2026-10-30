"""Schnittstelle der Web-App zum Chat-Agenten (nur Python-Bordmittel, zum Importieren aus shared/webapp).

Ablauf: frage_stellen() legt data/fragen/<id>.json an. systemd (lia-chat.path) startet daraufhin lia-chat.service,
der Agent schreibt data/antworten/<id>.json und löscht die Frage. Die Web-App fragt mit antwort_holen(id) nach,
bis die Antwort da ist (Vorschlag: alle 2 s). Format beider Dateien: STATUS.md, Abschnitt „Schnittstelle“.
"""

import json
import os
import re
import uuid
from pathlib import Path

import chatverlauf as _verlauf

ORDNER = Path(__file__).resolve().parent / "data"
MAX_ZEICHEN = 4000
ID_MUSTER = re.compile(r"^[0-9a-f]{12}$")
ORT_FELDER = {"reihe": str, "stunde": int, "chip": str, "stunde_thema": str, "materialien": list}


class FrageFehler(ValueError):
    pass


def ort_pruefen(ort) -> dict | None:
    """Ort aus der Frage: None (ohne Ort) oder dict nur mit bekannten Feldern richtigen Typs."""
    if ort is None:
        return None
    if not isinstance(ort, dict) or not isinstance(ort.get("reihe"), str) or not ort["reihe"]:
        raise FrageFehler("Ort braucht eine Reihe (Kennung) oder ist None")
    for k, v in ort.items():
        if k not in ORT_FELDER or (v is not None and (not isinstance(v, ORT_FELDER[k]) or isinstance(v, bool))):
            raise FrageFehler(f"Ort: Feld {k} unbekannt oder falscher Typ")
    if not all(isinstance(m, str) for m in ort.get("materialien") or []):
        raise FrageFehler("Ort: materialien ist eine Liste von Titeln")
    return {k: v for k, v in ort.items() if v is not None}


def frage_pruefen(frage) -> dict:
    """Prüft eine Frage-Datei (auch im Agenten). Gibt die bereinigte Frage zurück oder wirft FrageFehler."""
    if not isinstance(frage, dict):
        raise FrageFehler("Frage ist kein JSON-Objekt")
    if not isinstance(frage.get("id"), str) or not ID_MUSTER.match(frage["id"]):
        raise FrageFehler("Frage ohne gültige id")
    text = frage.get("text")
    if not isinstance(text, str) or not text.strip():
        raise FrageFehler("Die Frage ist leer.")
    if len(text) > MAX_ZEICHEN:
        raise FrageFehler(f"Die Frage ist zu lang (höchstens {MAX_ZEICHEN} Zeichen).")
    return {"id": frage["id"], "zeit": str(frage.get("zeit") or ""), "text": text.strip(),
            "gruendlich": frage.get("gruendlich") is True, "ort": ort_pruefen(frage.get("ort"))}


def _schreiben(ziel: Path, daten: dict) -> None:
    """Atomar: erst in data/tmp, dann umbenennen (die Pfad-Unit sieht nie eine halbe Datei)."""
    tmp = ziel.parent.parent / "tmp" / ziel.name
    tmp.parent.mkdir(parents=True, exist_ok=True)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, ziel)


def frage_stellen(text: str, ort: dict | None = None, gruendlich: bool = False, ordner: Path = ORDNER) -> str:
    """Legt die Frage in die Warteschlange und gibt ihre id zurück. Ungültig: FrageFehler (Text für Lia)."""
    frage = frage_pruefen({"id": uuid.uuid4().hex[:12], "zeit": _verlauf.jetzt().isoformat(timespec="seconds"),
                           "text": text, "gruendlich": gruendlich, "ort": ort})
    _schreiben(Path(ordner) / "fragen" / f"{frage['id']}.json", frage)
    return frage["id"]


def antwort_schreiben(antwort: dict, ordner: Path = ORDNER) -> None:
    _schreiben(Path(ordner) / "antworten" / f"{antwort['id']}.json", antwort)


def antwort_holen(frage_id: str, ordner: Path = ORDNER) -> dict | None:
    """Die Antwort oder None, solange sie noch nicht da ist."""
    if not ID_MUSTER.match(frage_id or ""):
        return None
    pfad = Path(ordner) / "antworten" / f"{frage_id}.json"
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def wartet(frage_id: str, ordner: Path = ORDNER) -> bool:
    """True, solange die Frage noch in der Warteschlange liegt."""
    return bool(ID_MUSTER.match(frage_id or "")) and (Path(ordner) / "fragen" / f"{frage_id}.json").exists()


def verlauf(ordner: Path = ORDNER) -> list[dict]:
    """Beantwortete Fragen der letzten 30 Tage, älteste zuerst."""
    return _verlauf.lesen(ordner)
