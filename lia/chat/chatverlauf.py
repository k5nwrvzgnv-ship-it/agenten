"""Verlauf des Chats: eine Zeile JSON je Frage und Antwort in data/verlauf.jsonl, höchstens 30 Tage.

Nur Python-Bordmittel: Die Web-App liest den Verlauf über schnittstelle.py mit ihrer eigenen Python-Umgebung.
Gespeichert werden nur beantwortete Fragen. Fehlertexte stehen nur in der Antwort-Datei.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

DATEI = "verlauf.jsonl"
TAGE = 30  # Jan 30.10.2026: Verläufe nach 30 Tagen löschen


def jetzt() -> datetime:
    return datetime.now().astimezone()


def lesen(ordner: Path) -> list[dict]:
    """Alle Einträge, älteste zuerst. Kaputte Zeilen werden übersprungen."""
    pfad = Path(ordner) / DATEI
    if not pfad.exists():
        return []
    eintraege = []
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        if isinstance(e, dict):
            eintraege.append(e)
    return eintraege


def anhaengen(ordner: Path, eintrag: dict) -> None:
    Path(ordner).mkdir(parents=True, exist_ok=True)
    with open(Path(ordner) / DATEI, "a", encoding="utf-8") as f:
        f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")


def am_ort(eintraege: list[dict], reihe: str | None, anzahl: int = 6) -> list[dict]:
    """Die letzten Einträge seit dem letzten Ortswechsel (Ort = Reihe, ohne Ort = None), älteste zuerst."""
    treffer = []
    for e in reversed(eintraege):
        if e.get("reihe") != reihe or len(treffer) >= anzahl:
            break
        treffer.append(e)
    return list(reversed(treffer))


def _alt(zeit: str, grenze: datetime) -> bool:
    try:
        return datetime.fromisoformat(zeit) < grenze
    except (TypeError, ValueError):
        return True  # ohne lesbare Zeit lieber löschen als ewig behalten


def aufraeumen(ordner: Path, tage: int = TAGE, heute: datetime | None = None) -> int:
    """Löscht Verlaufseinträge und Antwort-Dateien, die älter als `tage` sind. Gibt die Zahl gelöschter zurück."""
    ordner = Path(ordner)
    grenze = (heute or jetzt()) - timedelta(days=tage)
    eintraege = lesen(ordner)
    bleiben = [e for e in eintraege if not _alt(e.get("zeit"), grenze)]
    weg = len(eintraege) - len(bleiben)
    if weg:
        tmp = ordner / (DATEI + ".tmp")
        tmp.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in bleiben), encoding="utf-8")
        os.replace(tmp, ordner / DATEI)
    for pfad in (ordner / "antworten").glob("*.json"):
        if datetime.fromtimestamp(pfad.stat().st_mtime).astimezone() < grenze:
            pfad.unlink()
            weg += 1
    return weg
