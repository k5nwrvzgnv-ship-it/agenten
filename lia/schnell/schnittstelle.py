"""Schnittstelle der Web-App zum Agenten schnell (nur Python-Bordmittel, zum Importieren aus shared/webapp).

aendern() und dokument() legen einen Wunsch nach data/wuensche/<id>.json (über data/tmp, atomar). systemd
(lia-schnell.path) startet daraufhin lia-schnell.service, der Agent schreibt data/antworten/<id>.json und löscht den
Wunsch. Die Web-App fragt mit antwort_holen(id) nach, bis die Antwort da ist (Vorschlag: alle 2 s).
Format: STATUS.md, Abschnitt „Schnittstelle“.
"""

import json
import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ORDNER = Path(__file__).resolve().parent / "data"
ZONE = ZoneInfo("Europe/Berlin")
ID_MUSTER = re.compile(r"^[0-9a-f]{12}$")
AUFTRAG_MUSTER = re.compile(r"^\d{8}-\d{6}-[a-z]+-[0-9a-f]{6}$")  # wie agentkit._ablage.ID_MUSTER
ORT_MUSTER = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")  # wie agentkit.auftraege (ort=)
MAX_ZEICHEN = 4000
ENDUNGEN = (".pdf", ".docx", ".pptx", ".xlsx", ".jpg", ".jpeg", ".png")
FOTO_ENDUNGEN = (".jpg", ".jpeg", ".png")
MAX_DATEIEN = 5
MAX_BYTES = 20 * 1024 * 1024
NOTIZ_PRAEFIX = "Schnell geändert: "  # Notiz jeder schnell geänderten eigenen Fassung (zugesichert)
_UNERLAUBT = re.compile(r"[^\w .()-]")


class WunschFehler(ValueError):
    """Ungültiger Wunsch. Der Text ist ein Satz für Lia."""


def jetzt() -> str:
    return datetime.now(ZONE).isoformat(timespec="seconds")


def dateiname(name: str) -> str:
    """Dateiname ohne Pfadteile und Sonderzeichen, nicht versteckt, höchstens 120 Zeichen (Endung bleibt)."""
    stamm, endung = os.path.splitext(_UNERLAUBT.sub("_", Path(str(name)).name).strip().lstrip("."))
    return (stamm[:120 - len(endung)].strip() or "datei") + endung.lower()


def _text_pruefen(text) -> str:
    if not isinstance(text, str) or not text.strip():
        raise WunschFehler("Schreib bitte kurz, was du möchtest.")
    if len(text) > MAX_ZEICHEN:
        raise WunschFehler(f"Der Text ist zu lang (höchstens {MAX_ZEICHEN} Zeichen).")
    return text.strip()


def _zahl(wert, name: str, minimum: int, maximum: int) -> int | None:
    if wert is None:
        return None
    if not isinstance(wert, int) or isinstance(wert, bool) or not minimum <= wert <= maximum:
        raise WunschFehler(f"{name} ungültig")
    return wert


def wunsch_pruefen(w) -> dict:
    """Prüft eine Wunsch-Datei (auch im Agenten). Gibt den bereinigten Wunsch zurück oder wirft WunschFehler."""
    if not isinstance(w, dict) or not isinstance(w.get("id"), str) or not ID_MUSTER.match(w["id"]):
        raise WunschFehler("Wunsch ohne gültige id")
    basis = {"id": w["id"], "zeit": str(w.get("zeit") or ""), "text": _text_pruefen(w.get("text"))}
    if w.get("art") == "aenderung":
        if not isinstance(w.get("bezug"), str) or not AUFTRAG_MUSTER.match(w["bezug"]):
            raise WunschFehler("Bezug ungültig")
        return {**basis, "art": "aenderung", "bezug": w["bezug"], "nr": _zahl(w.get("nr", 0), "nr", 0, 99) or 0,
                "eigene": _zahl(w.get("eigene"), "eigene", 1, 9999), "seite": _zahl(w.get("seite"), "seite", 1, 999)}
    if w.get("art") == "dokument":
        ort = w.get("ort")
        if ort is not None and (not isinstance(ort, str) or not ORT_MUSTER.match(ort)):
            raise WunschFehler("Ort ungültig")
        namen = w.get("dateien") or []
        if not isinstance(namen, list) or not all(isinstance(n, str) for n in namen):
            raise WunschFehler("dateien ist eine Liste von Namen")
        if len(namen) > MAX_DATEIEN:
            raise WunschFehler(f"Höchstens {MAX_DATEIEN} Dateien.")
        for n in namen:
            if n != dateiname(n):
                raise WunschFehler("Dateiname ungültig")
            if not n.lower().endswith(ENDUNGEN):
                raise WunschFehler("Es gehen PDF, Word, PowerPoint, Excel und Fotos (JPG, PNG).")
        if len(set(namen)) != len(namen):
            raise WunschFehler("Zwei Dateien mit demselben Namen")
        return {**basis, "art": "dokument", "ort": ort, "dateien": namen}
    raise WunschFehler("Art des Wunsches unbekannt")


def _schreiben(ziel: Path, daten: dict) -> None:
    """Atomar: erst in data/tmp, dann umbenennen (die Pfad-Unit sieht nie eine halbe Datei)."""
    tmp = ziel.parent.parent / "tmp" / ziel.name
    tmp.parent.mkdir(parents=True, exist_ok=True)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, ziel)


def aendern(bezug: str, text: str, nr: int = 0, eigene: int | None = None, seite: int | None = None,
            ordner: Path = ORDNER) -> str:
    """Kleine Änderung an einem Dokument. Gibt die id des Wunsches zurück. Ungültig: WunschFehler.

    bezug: id eines erledigten Auftrags (unterricht, theater oder schnell), nr: Index der Datei in dessen
    ergebnis_dateien. eigene: statt dessen die eigene Fassung n der Kette von bezug (eine schnell geänderte;
    Lias hochgeladene Fassungen haben keine Beschreibung und gehen gründlich). seite: Seite im Betrachter.
    """
    w = wunsch_pruefen({"id": uuid.uuid4().hex[:12], "zeit": jetzt(), "art": "aenderung", "bezug": bezug,
                        "text": text, "nr": nr, "eigene": eigene, "seite": seite})
    _schreiben(Path(ordner) / "wuensche" / f"{w['id']}.json", w)
    return w["id"]


def dokument(text: str, ort: str | None = None, dateien: list[tuple[str, Path]] | None = None,
             ordner: Path = ORDNER) -> str:
    """Schnelles Dokument. ort: id aus agentkit.struktur (Fach, Klasse, Reihe, Stunde) oder None.
    dateien: [(Name wie hochgeladen, Pfad)], höchstens 5, PDF/Word/PowerPoint/Excel/JPG/PNG bis 20 MB. Sie werden
    nach data/dateien/<id>/ verschoben; bei WunschFehler bleibt alles liegen (die Web-App räumt selbst weg)."""
    dateien = list(dateien or [])
    namen = [dateiname(n) for n, _ in dateien]
    w = wunsch_pruefen({"id": uuid.uuid4().hex[:12], "zeit": jetzt(), "art": "dokument", "text": text, "ort": ort,
                        "dateien": namen})
    for _, quelle in dateien:
        if not Path(quelle).is_file():
            raise WunschFehler("Eine Datei ist nicht angekommen.")
        if Path(quelle).stat().st_size > MAX_BYTES:
            raise WunschFehler("Eine Datei ist zu groß (höchstens 20 MB).")
    for name, (_, quelle) in zip(namen, dateien, strict=True):
        ziel = dateien_ordner(w["id"], ordner)
        ziel.mkdir(parents=True, exist_ok=True)
        shutil.move(str(quelle), ziel / name)
    _schreiben(Path(ordner) / "wuensche" / f"{w['id']}.json", w)
    return w["id"]


def dateien_ordner(wunsch_id: str, ordner: Path = ORDNER) -> Path:
    return Path(ordner) / "dateien" / wunsch_id


def antwort_schreiben(antwort: dict, ordner: Path = ORDNER) -> None:
    _schreiben(Path(ordner) / "antworten" / f"{antwort['id']}.json", antwort)


def antwort_holen(wunsch_id: str, ordner: Path = ORDNER) -> dict | None:
    """Die Antwort oder None, solange sie noch nicht da ist."""
    if not ID_MUSTER.match(wunsch_id or ""):
        return None
    try:
        return json.loads((Path(ordner) / "antworten" / f"{wunsch_id}.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def wartet(wunsch_id: str, ordner: Path = ORDNER) -> bool:
    """True, solange der Wunsch noch in der Warteschlange liegt."""
    return bool(ID_MUSTER.match(wunsch_id or "")) and (Path(ordner) / "wuensche" / f"{wunsch_id}.json").exists()


def schnell_fassung(ursprung: str, n: int, ordner: Path = ORDNER) -> bool:
    """Stammt die eigene Fassung n der Kette ursprung von schnell? (Dann gibt es ihre Beschreibung hier, und sie lässt
    sich wieder schnell ändern.) Festes Kennzeichen neben dem Notiz-Präfix NOTIZ_PRAEFIX."""
    if not AUFTRAG_MUSTER.match(ursprung or "") or not isinstance(n, int) or isinstance(n, bool) or n < 1:
        return False
    return (Path(ordner) / "fassungen" / ursprung / f"eigene-{n}" / "beschreibung.json").is_file()
