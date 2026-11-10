"""Eigene Dateien am Ort (bauplan-gespraech.md, Abschnitt 2): <instanz>/ablage/<ort-id>/<Name>.

Lia legt an Klasse/Kurs, Reihe oder Stunde Dateien ab (Planung, Buchseite, Bewertungskriterien), ohne Auftrag.
Gespräche an diesem Ort und darunter kennen sie (lia/chat liest den Ordner). Schreibt nur die Web-App.
Ort-ids sind die festen ids aus agentkit.struktur (Kleinbuchstaben, Ziffern, Bindestrich). Gleicher Name ersetzt.

Jeder Pfad wird geprüft wie in dateien.py: nur direkt im Ordner des Orts, nichts Verstecktes, erlaubte Endung.
"""

import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path

ENDUNGEN = {".pdf", ".docx", ".pptx", ".xlsx", ".jpg", ".jpeg", ".png"}
FOTOS = {".jpg", ".jpeg", ".png"}
MAX_BYTES = 20 * 1024 * 1024
MAX_JE_ORT = 30
_ORT = re.compile(r"[a-z0-9][a-z0-9-]{0,119}")
_UNERLAUBT = re.compile(r"[\x00-\x1f\x7f/\\:*?\"<>|]")
MEDIENTYP = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
             ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
             ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
ARTNAME = {".pdf": "PDF", ".docx": "Word", ".pptx": "PowerPoint", ".xlsx": "Excel", ".jpg": "Foto", ".jpeg": "Foto",
           ".png": "Foto"}

FEHLER = {"leer": "Die Datei ist leer.", "art": "Das geht als PDF, Word, PowerPoint, Excel, JPG oder PNG.",
          "veraltet": "Die Seite war veraltet. Bitte wähl die Datei noch einmal.",
          "gross": "Die Datei ist größer als 20 MB.", "voll": f"Hier liegen schon {MAX_JE_ORT} Dateien.",
          "heic": "Fotos vom iPhone (HEIC) gehen noch nicht. Am iPhone unter Einstellungen › Kamera › Formate "
                  "„Maximale Kompatibilität“ wählen, dann kommen sie als JPG."}


def ort_gueltig(ort_id: str) -> bool:
    return bool(ort_id) and bool(_ORT.fullmatch(ort_id))


def ordner(instanz: Path, ort_id: str) -> Path | None:
    return instanz / "ablage" / ort_id if ort_gueltig(ort_id) else None


def name_bereinigen(name: str) -> str:
    """Wie logik.dateiname_bereinigen: ohne Ordner, Steuerzeichen und Punkt am Anfang, höchstens 100 Zeichen."""
    name = unicodedata.normalize("NFC", (name or "").replace("\\", "/").rsplit("/", 1)[-1])
    name = " ".join(_UNERLAUBT.sub("_", name).split()).lstrip(".")
    stamm, punkt, endung = name.rpartition(".")
    if not punkt:
        stamm, endung = name, ""
    stamm = stamm[: 100 - len(endung) - 1].rstrip() or "datei"
    return f"{stamm}.{endung.lower()}" if endung else stamm


def pruefen(name: str, groesse: int, vorhanden: int) -> str:
    """Fehler-Schlüssel (FEHLER) oder "". vorhanden: Zahl der Dateien am Ort ohne die gleichnamige."""
    endung = Path(name_bereinigen(name)).suffix.lower()
    if endung in (".heic", ".heif"):
        return "heic"
    if endung not in ENDUNGEN:
        return "art"
    if groesse <= 0:
        return "leer"
    if groesse > MAX_BYTES:
        return "gross"
    if vorhanden >= MAX_JE_ORT:
        return "voll"
    return ""


def liste(instanz: Path, ort_id: str) -> list[dict]:
    """Dateien am Ort, neueste zuerst: {"name", "art", "foto", "groesse", "zeit" (datetime)}."""
    o = ordner(instanz, ort_id)
    if o is None or not o.is_dir():
        return []
    out = []
    for p in o.iterdir():
        if p.name.startswith(".") or p.suffix.lower() not in ENDUNGEN or not p.is_file() or p.is_symlink():
            continue
        st = p.stat()
        out.append({"name": p.name, "art": ARTNAME[p.suffix.lower()], "foto": p.suffix.lower() in FOTOS,
                    "groesse": st.st_size, "zeit": datetime.fromtimestamp(st.st_mtime).astimezone()})
    return sorted(out, key=lambda d: d["zeit"], reverse=True)


def pfad(instanz: Path, ort_id: str, name: str) -> Path | None:
    """Geprüfter Pfad einer abgelegten Datei oder None."""
    o = ordner(instanz, ort_id)
    if o is None or not name or name != name_bereinigen(name) or name.startswith("."):
        return None
    if Path(name).suffix.lower() not in ENDUNGEN:
        return None
    p = o / name
    if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(o.resolve()):
        return None
    return p


def ablegen(instanz: Path, ort_id: str, name: str, quelle) -> str:
    """Schreibt die Datei (Dateiobjekt quelle) an den Ort, gleicher Name ersetzt. Gibt den bereinigten Namen zurück.
    Erst in eine Zwischendatei, dann umbenennen: eine halb geschriebene Datei liest lia/chat nie."""
    o = ordner(instanz, ort_id)
    if o is None:
        raise ValueError("Ort ungültig")
    o.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = name_bereinigen(name)
    zwischen = o / f".{name}.teil"
    with zwischen.open("wb") as ziel:
        shutil.copyfileobj(quelle, ziel)
    zwischen.replace(o / name)
    return name


def entfernen(instanz: Path, ort_id: str, name: str) -> bool:
    p = pfad(instanz, ort_id, name)
    if p is None:
        return False
    p.unlink()
    return True
