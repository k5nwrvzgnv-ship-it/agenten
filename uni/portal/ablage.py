"""Was das Portal lesen darf: feste Positivliste, alles andere gibt es für die App nicht.

Das Portal liest aus dem Agent-Ordner uni/ nur die Dateien in MODUL_DATEIEN, Bilder im Unterordner bilder/ der
Module aus MODULE und in uebungen/<id>/ die Dateien aus UEBUNG_DATEIEN. Damit bleiben .env, data/mails,
data/mailauftraege und alles Übrige außen vor. Bilder werden über die Karte gefunden, nie über einen Pfad aus der
Adresse; eine Übung nur über eine ID im festen Format. tests/test_schutz.py belegt das.

Aus portal/.env liest die App nur die Adresse des ElevenLabs-Agenten. Das Passwort, das dort auch steht, sieht sie nie.

Zu einem Projekt aus PROJEKTE liest das Portal nur: expose.json, die Fassungen (docx, pdf), recherche/geprueft.json, das
Protokoll der Kette und den Auszug schriftverkehr.json. Der Auszug enthält nur Mails der eingetragenen Kontaktpersonen
(uni/schriftverkehr.py, Jans Wunsch 04.11.); data/mails und das Postfach bleiben außen vor.
"""

import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import lernmodell

LERNEN_RELATIV = PurePosixPath("data/lernen")
MODULE = {"holzschutz": "Holzschutz"}  # Ordner unter data/lernen -> Anzeigename; weitere Module kommen hier dazu
RUBRIK = "rubrik.json"
VORGEMERKT = "vorgemerkt.json"
MODUL_DATEIEN = frozenset({"pruefungsplan.json", "karten.json", "zustand.json", "verlauf.jsonl", RUBRIK, VORGEMERKT})
BILD_ORDNER = "bilder"
BILD_ENDUNGEN = {".jpg", ".jpeg", ".png"}

UEBUNGEN_ORDNER = "uebungen"
TRANSKRIPT = "transkript.txt"
STAND = "stand.json"
AUSWERTUNG = "auswertung.json"
KARTENSTAND = "kartenstand.json"
UEBUNG_DATEIEN = frozenset({TRANSKRIPT, STAND, AUSWERTUNG, KARTENSTAND})
UEBUNG_ENDUNGEN = {".txt", ".json"}
UEBUNG_ID = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")

ELEVENLABS_SCHLUESSEL = "ELEVENLABS_AGENT_URL"

# Projekt -> Anzeigename und Kette: Überarbeitungen bleiben in derselben Kette, der Eintrag ändert sich dadurch nicht
PROJEKTE = {"fehlstellen": {"name": "Forschungsprojekt", "kette": "20261102-165741-uni-ac9dcc"}}
FASSUNG_ENDUNGEN = {".docx", ".pdf"}


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


def uebung_ordner(uni: Path, modul: str, uebung_id: str) -> Path | None:
    """data/lernen/<modul>/uebungen/<id>/ nur für bekannte Module und IDs im festen Format; kein Symlink."""
    ordner = modul_ordner(uni, modul)
    if ordner is None or not UEBUNG_ID.match(uebung_id or ""):
        return None
    pfad = ordner / UEBUNGEN_ORDNER / uebung_id
    return pfad if pfad.is_dir() and not pfad.is_symlink() else None


def uebung_datei(uni: Path, modul: str, uebung_id: str, name: str) -> Path | None:
    """Eine Datei der Übung, nur aus der Liste UEBUNG_DATEIEN, aufgelöst unter dem Ordner der Übung."""
    ordner = uebung_ordner(uni, modul, uebung_id)
    if ordner is None or name not in UEBUNG_DATEIEN:
        return None
    return sicher(ordner, name, UEBUNG_ENDUNGEN)


def uebungen_ids(uni: Path, modul: str) -> list[str]:
    """IDs der Übungen eines Moduls, neueste zuerst."""
    ordner = modul_ordner(uni, modul)
    if ordner is None or not (ordner / UEBUNGEN_ORDNER).is_dir():
        return []
    ids = [p.name for p in (ordner / UEBUNGEN_ORDNER).iterdir() if uebung_ordner(uni, modul, p.name)]
    return sorted(ids, reverse=True)


def _projekt_kette(projekt: str) -> str | None:
    eintrag = PROJEKTE.get(projekt)
    return eintrag["kette"] if eintrag else None


def expose_lesen(uni: Path, projekt: str) -> dict | None:
    kette = _projekt_kette(projekt)
    pfad = sicher(uni / "data" / "expose" / kette, "expose.json", {".json"}) if kette else None
    return lernmodell.lies_json(pfad, None) if pfad else None


def geprueft_lesen(uni: Path, projekt: str) -> dict | None:
    kette = _projekt_kette(projekt)
    pfad = sicher(uni / "data" / "expose" / kette / "recherche", "geprueft.json", {".json"}) if kette else None
    return lernmodell.lies_json(pfad, None) if pfad else None


def protokoll_lesen(uni: Path, projekt: str) -> str | None:
    kette = _projekt_kette(projekt)
    pfad = sicher(uni / "protokolle", f"{kette}.md", {".md"}) if kette else None
    return pfad.read_text(encoding="utf-8") if pfad else None


def fassung_pfad(uni: Path, projekt: str, endung: str) -> Path | None:
    """Neueste Datei mit dieser Endung direkt in fassung/ des Projekts. Der Name kommt nie aus der Adresse."""
    kette = _projekt_kette(projekt)
    endung = f".{endung}"
    if kette is None or endung not in FASSUNG_ENDUNGEN:
        return None
    ordner = uni / "data" / "expose" / kette / "fassung"
    if not ordner.is_dir():
        return None
    dateien = [p for p in (sicher(ordner, d.name, {endung}) for d in ordner.iterdir() if not d.is_symlink()) if p]
    return max(dateien, key=lambda p: p.stat().st_mtime, default=None)


def schriftverkehr_lesen(uni: Path, projekt: str) -> dict | None:
    if projekt not in PROJEKTE:
        return None
    pfad = sicher(uni / "data" / "projekte" / projekt, "schriftverkehr.json", {".json"})
    return lernmodell.lies_json(pfad, None) if pfad else None


def elevenlabs_adresse(env_datei: Path) -> str | None:
    """Adresse des ElevenLabs-Agenten aus portal/.env, nur https. Nur diese eine Zeile wird ausgewertet."""
    try:
        zeilen = Path(env_datei).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    for zeile in zeilen:
        name, trenner, wert = zeile.partition("=")
        if trenner and name.strip() == ELEVENLABS_SCHLUESSEL:
            wert = wert.strip().strip("'\"")
            try:
                teile = urlsplit(wert)
            except ValueError:
                return None
            sauber = teile.scheme == "https" and teile.hostname and not re.search(r"[\s\"'<>]", wert)
            return wert if sauber else None
    return None
