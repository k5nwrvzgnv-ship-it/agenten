"""Weitergabe an den Agenten dokumente: Auslöser erkennen und Claudes Übergabedatei prüfen.

Claude kann auftraege.weitergeben nicht selbst aufrufen. Bei einem Dokument-Auftrag schreibt Claude
data/weitergabe/<auftrag-id>.json = {"text": ..., "dateien": [...]} und legt die Dateien in
data/weitergabe/<auftrag-id>/ ab. Python prüft das hier und gibt erst danach weiter (agent.py).
Nur Dateien aus diesem Ordner dürfen mit, so gelangen Eingänge wie Jans Transkript nicht an dokumente.
Pflicht sind behauptungen.json (Behauptungsliste, Format wie in dokumente/zusammenfassen.py: Liste aus
{"nr", "aussage", "quellen", "kennzeichnung"}) und eine Renderer-Beschreibung (.json), die renderer.pruefung
besteht. dokumente schreibt daraus mit eigenem Claude-Lauf die Zusammenfassung und prüft sie gegen die Liste.
"""

import json
from pathlib import Path

from renderer import pruefung

AUSLOESER = "dokument:"
ORDNER = Path("data") / "weitergabe"
MAX_TEXT = 2000
MAX_DATEIEN = 5
BEHAUPTUNGEN = "behauptungen.json"
MAX_BEHAUPTUNGEN = 300


class UebergabeFehler(Exception):
    def __init__(self, fehler: list[str]):
        self.fehler = fehler
        super().__init__("Übergabe ungültig:\n" + "\n".join(f"- {f}" for f in fehler))


def ist_dokumentauftrag(text: str) -> bool:
    """Nur Aufträge, die mit "Dokument:" beginnen, werden weitergegeben."""
    return text.lstrip().lower().startswith(AUSLOESER)


def format_abschnitt(format_md: str, titel: str = "## Zusammenfassung") -> str:
    """Der Abschnitt aus shared/renderer/FORMAT.md, den Claude braucht (bis zur nächsten Überschrift ##)."""
    anfang = format_md.find(titel)
    if anfang < 0:
        raise ValueError(f"{titel} fehlt in FORMAT.md")
    ende = format_md.find("\n## ", anfang + len(titel))
    return format_md[anfang:ende if ende >= 0 else None].strip()


def uebergabe_datei(hier: Path, auftrag_id: str) -> Path:
    return hier / ORDNER / f"{auftrag_id}.json"


def dateien_ordner(hier: Path, auftrag_id: str) -> Path:
    return hier / ORDNER / auftrag_id


def merkdatei(hier: Path, auftrag_id: str) -> Path:
    return hier / ORDNER / f"{auftrag_id}.erledigt"


def uebergabe_pruefen(hier: Path, auftrag_id: str) -> tuple[str, list[Path]]:
    """Text und Dateien (absolut) der Übergabe. Wirft UebergabeFehler mit allen Fehlern auf einmal."""
    datei = uebergabe_datei(hier, auftrag_id)
    try:
        daten = json.loads(datei.read_text())
    except FileNotFoundError:
        raise UebergabeFehler([f"{datei.relative_to(hier)} fehlt"]) from None
    except (OSError, ValueError) as f:
        raise UebergabeFehler([f"{datei.relative_to(hier)} nicht lesbar: {f}"]) from None
    if not isinstance(daten, dict):
        raise UebergabeFehler(["Übergabe muss ein Objekt {\"text\", \"dateien\"} sein"])
    fehler = []
    text = daten.get("text")
    if not isinstance(text, str) or not text.strip():
        fehler.append("text fehlt oder ist leer")
    elif len(text) > MAX_TEXT:
        fehler.append(f"text zu lang ({len(text)} Zeichen, höchstens {MAX_TEXT})")
    namen = daten.get("dateien")
    if not isinstance(namen, list) or not namen:
        fehler.append("dateien fehlt oder ist leer")
        namen = []
    elif len(namen) > MAX_DATEIEN:
        fehler.append(f"zu viele Dateien ({len(namen)}, höchstens {MAX_DATEIEN})")
    ordner = dateien_ordner(hier, auftrag_id)
    wurzel = ordner.resolve()
    pfade, beschreibungen, liste = [], 0, False
    for name in namen:
        if not isinstance(name, str) or not name:
            fehler.append(f"Dateiname ungültig: {name!r}")
            continue
        pfad = (hier / name).resolve()
        if not pfad.is_relative_to(wurzel) or pfad == wurzel:
            fehler.append(f"{name}: nur Dateien aus {ordner.relative_to(hier)}/ dürfen mit")
            continue
        if (hier / name).is_symlink() or not pfad.is_file():
            fehler.append(f"{name}: Datei fehlt")
            continue
        if pfad.name == BEHAUPTUNGEN:
            liste = True
            fehler += [f"{name}: {f}" for f in behauptungen_pruefen(pfad.read_text())]
        elif pfad.suffix == ".json":
            beschreibungen += 1
            fehler += [f"{name}: {f}" for f in pruefung.pruefen(pfad.read_text())]
        pfade.append(pfad)
    if namen and not liste:
        fehler.append(f"{BEHAUPTUNGEN} fehlt")
    if namen and not beschreibungen:
        fehler.append("keine Renderer-Beschreibung (.json) dabei")
    if fehler:
        raise UebergabeFehler(fehler)
    return text.strip(), pfade


def behauptungen_pruefen(text: str) -> list[str]:
    """Fehler der Behauptungsliste. quellen und kennzeichnung prüft der Renderer (wie an einem Absatz)."""
    try:
        liste = json.loads(text)
    except ValueError as f:
        return [f"kein gültiges JSON: {f}"]
    if not isinstance(liste, list) or not liste:
        return ["muss eine nicht leere Liste sein"]
    if len(liste) > MAX_BEHAUPTUNGEN:
        return [f"zu viele Behauptungen ({len(liste)}, höchstens {MAX_BEHAUPTUNGEN})"]
    fehler, gesehen = [], set()
    for i, b in enumerate(liste):
        if not isinstance(b, dict):
            fehler.append(f"[{i}] ist kein Objekt")
            continue
        nr = b.get("nr")
        if not isinstance(nr, int) or isinstance(nr, bool) or nr in gesehen:
            fehler.append(f"[{i}].nr muss eine eindeutige ganze Zahl sein, ist {nr!r}")
        else:
            gesehen.add(nr)
        if not isinstance(b.get("aussage"), str) or not b["aussage"].strip():
            fehler.append(f"[{i}].aussage fehlt")
            continue
        unbekannt = set(b) - {"nr", "aussage", "quellen", "kennzeichnung"}
        if unbekannt:
            fehler.append(f"[{i}]: unbekannte Felder {sorted(unbekannt)}")
        absatz = {"typ": "absatz", "text": b["aussage"],
                  **{k: b[k] for k in ("quellen", "kennzeichnung") if k in b}}
        probe = {"art": "zusammenfassung", "titel": "Probe", "kurs": "Probe", "datum": "01.01.2026",
                 "bloecke": [absatz]}
        fehler += [f"[{i}]{f.removeprefix('bloecke[0]')}" for f in pruefung.pruefen(probe)]
    return fehler
