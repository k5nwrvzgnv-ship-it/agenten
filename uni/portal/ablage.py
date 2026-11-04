"""Was das Portal lesen darf: feste Positivliste, alles andere gibt es für die App nicht.

Das Portal liest aus dem Agent-Ordner uni/ nur die Dateien in MODUL_DATEIEN und Bilder im Unterordner bilder/ der
Module aus MODULE. Damit bleiben .env, data/mails, data/mailauftraege und alles Übrige außen vor. Bilder werden
über die Karte gefunden, nie über einen Pfad aus der Adresse. tests/test_schutz.py belegt das.
"""

from pathlib import Path, PurePosixPath

import lernmodell

LERNEN_RELATIV = PurePosixPath("data/lernen")
MODULE = {"holzschutz": "Holzschutz"}  # Ordner unter data/lernen -> Anzeigename; weitere Module kommen hier dazu
MODUL_DATEIEN = frozenset({"pruefungsplan.json", "karten.json", "zustand.json", "verlauf.jsonl"})
BILD_ORDNER = "bilder"
BILD_ENDUNGEN = {".jpg", ".jpeg", ".png"}


def sicher(wurzel: Path, relativ: str | Path, endungen: set[str]) -> Path | None:
    """Pfad einer Datei unter wurzel oder None (Kopie aus shared/webapp/dateien.py): aufgelöst, auch Symlinks,
    kein "..", nichts Verstecktes, nur erlaubte Endungen, muss eine Datei sein."""
    rel = Path(relativ)
    if rel.is_absolute() or ".." in rel.parts or any(teil.startswith(".") for teil in rel.parts):
        return None
    if rel.suffix.lower() not in endungen:
        return None
    wurzel = wurzel.resolve()
    pfad = (wurzel / rel).resolve()
    if not pfad.is_relative_to(wurzel) or pfad.suffix.lower() not in endungen or not pfad.is_file():
        return None
    return pfad


def modul_ordner(uni: Path, modul: str) -> Path | None:
    """data/lernen/<modul>/ nur für Module aus der Liste."""
    return uni / LERNEN_RELATIV / modul if modul in MODULE else None


def modul_laden(uni: Path, modul: str) -> lernmodell.Modul | None:
    """Lernstand frisch von der Platte: Telegram (lernen.py) schreibt dieselben Dateien."""
    ordner = modul_ordner(uni, modul)
    return lernmodell.Modul(ordner) if ordner else None


def plan_lesen(uni: Path, modul: str) -> dict:
    ordner = modul_ordner(uni, modul)
    return lernmodell.lies_json(ordner / "pruefungsplan.json", {}) if ordner else {}


def bild_pfad(uni: Path, modul: str, bild: str | None) -> Path | None:
    """Datei zu einem Bildeintrag der Karte (relativ zu uni/), nur aus bilder/ des Moduls."""
    if not bild or modul not in MODULE:
        return None
    basis = LERNEN_RELATIV / modul / BILD_ORDNER
    try:
        rel = PurePosixPath(bild).relative_to(basis)
    except ValueError:
        return None
    return sicher(uni / basis, rel, BILD_ENDUNGEN)
