"""claude.ai-Export entpacken und seine Struktur beschreiben (Schritt 3), ohne Inhalte auszugeben.

entpacken: ZIP nach data/export/, nur normale Dateien mit sicheren relativen Pfaden, Rechte 700/600.
struktur: Feldpfade aller JSON-Dateien mit Typen und Anzahlen ("[]" steht für Listenelemente).
verzweigungen: Nachrichten mit gleichem Vorgänger (neu erzeugte Antworten, bearbeitete Prompts).
  Annahme: Der Vorgänger steht im Feld parent_message_uuid. Ob es das gibt, zeigt erst der echte Export.
Ohne Netz, getestet in tests/test_export.py.
"""

import json
import stat
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

import ablage

HOECHSTENS_BYTES = 2_000_000_000  # Schutz gegen ZIP-Bomben: entpackt höchstens 2 GB


class ExportFehler(Exception):
    pass


def _sicherer_pfad(name: str) -> PurePosixPath:
    pfad = PurePosixPath(name)
    if pfad.is_absolute() or ".." in pfad.parts or "\\" in name or not pfad.parts:
        raise ExportFehler(f"Unsicherer Pfad im ZIP: {name!r}")
    return pfad


def entpacken(zip_pfad: Path, ziel: Path) -> list[Path]:
    """Entpackt zip_pfad nach ziel. Prüft erst alle Einträge, dann wird geschrieben. Gibt die Dateien zurück."""
    with zipfile.ZipFile(zip_pfad) as z:
        eintraege = [e for e in z.infolist() if not e.is_dir()]
        for e in eintraege:
            _sicherer_pfad(e.filename)
            if stat.S_ISLNK(e.external_attr >> 16):
                raise ExportFehler(f"Symlink im ZIP: {e.filename!r}")
        if sum(e.file_size for e in eintraege) > HOECHSTENS_BYTES:
            raise ExportFehler("ZIP ist entpackt größer als 2 GB")
        ablage.datenordner(ziel)
        dateien = []
        for e in eintraege:
            pfad = ziel.joinpath(*_sicherer_pfad(e.filename).parts)
            for ordner in reversed(pfad.relative_to(ziel).parents[:-1]):
                ablage.datenordner(ziel / ordner)
            ablage.schreiben_bytes(pfad, z.read(e))
            dateien.append(pfad)
    return dateien


def _typ(wert) -> str:
    if wert is None:
        return "null"
    return {dict: "objekt", list: "liste", str: "text", bool: "ja/nein", int: "zahl", float: "zahl"}[type(wert)]


def struktur(daten) -> dict[str, Counter]:
    """Feldpfad -> Zähler der Typen. Inhalte werden nicht übernommen."""
    ergebnis: dict[str, Counter] = defaultdict(Counter)

    def gehen(wert, pfad: str) -> None:
        ergebnis[pfad or "."][_typ(wert)] += 1
        if isinstance(wert, dict):
            for schluessel, kind in wert.items():
                gehen(kind, f"{pfad}.{schluessel}")
        elif isinstance(wert, list):
            for kind in wert:
                gehen(kind, f"{pfad}[]")

    gehen(daten, "")
    return dict(ergebnis)


def verzweigungen(gespraeche: list) -> dict:
    """Zählt Stellen, an denen ein Vorgänger mehrere Nachfolger hat, getrennt nach Absender der Nachfolger."""
    mit_feld = 0
    stellen = Counter()
    for g in gespraeche:
        kinder = defaultdict(list)
        for n in g.get("chat_messages") or []:
            if "parent_message_uuid" in n:
                mit_feld += 1
                kinder[n["parent_message_uuid"]].append(n.get("sender", "?"))
        for absender in kinder.values():
            if len(absender) > 1:
                stellen[absender[0]] += 1
    return {"nachrichten_mit_vorgaenger": mit_feld, "stellen_nach_absender": dict(stellen)}


def bericht(ordner: Path) -> str:
    """Strukturbericht über alle JSON-Dateien in ordner, ohne Inhalte."""
    zeilen = []
    for datei in sorted(ordner.rglob("*")):
        if not datei.is_file():
            continue
        name = datei.relative_to(ordner)
        if datei.suffix != ".json":
            zeilen.append(f"## {name}: keine JSON-Datei, {datei.stat().st_size} Bytes")
            continue
        try:
            daten = json.loads(datei.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            zeilen.append(f"## {name}: nicht lesbar ({e.__class__.__name__})")
            continue
        anzahl = len(daten) if isinstance(daten, list) else 1
        zeilen.append(f"## {name}: {anzahl} Einträge")
        for pfad, typen in sorted(struktur(daten).items()):
            zeilen.append(f"{pfad}  " + ", ".join(f"{t} {n}" for t, n in typen.most_common()))
        if isinstance(daten, list) and any(isinstance(g, dict) and "chat_messages" in g for g in daten):
            v = verzweigungen([g for g in daten if isinstance(g, dict)])
            zeilen.append(f"Verzweigungen: {v}")
        zeilen.append("")
    return "\n".join(zeilen)
