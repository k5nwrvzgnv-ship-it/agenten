"""Lias Reihen aus Dateien laden (nur lesend). Prüfen und Zuordnen macht logik.py (reihen_aus, reihe_von).

Ziel (Jan 30.10.2026): EINE Datei <instanz>/reihen.toml, die die App zeigt und die Agenten lesen. Format wie
lia/unterricht/reihen.toml ([[reihe]] mit fach, klasse, titel, reihenfrage, lerngruppe, notizen, behandelt,
merksaetze, bisherige_reihen), dazu freiwillig:
  id       feste Kennung (sonst aus Fach, Klasse und Titel ohne Klammern), steht in Aufträgen im Feld "reihe"
  stand    "laufend" (Standard) oder "abgeschlossen"
  agenten  Aufträge dieser Agenten gehören zu dieser Reihe (z. B. ["theater"]), wenn der Agent nur hier steht

Bis die Datei dort liegt (Umzug macht der lia/unterricht-Chat), setzt die App sie aus dem Bestand zusammen:
  <agenten>/unterricht/reihen.toml        Reihen, fach ohne Angabe aus unterricht/profil.toml
  <agenten>/examen/examen.toml            [reihe] titel_in_reihen_toml: Reihe der Examensaufträge
  <agenten>/theater/theater.toml          [stueck] titel: Reihe des Theater-Agenten, Fach Theater, THEATER_KURS
"""

import tomllib
from pathlib import Path

import logik

DATEI = "reihen.toml"
THEATER_FACH = "Theater"   # Jan 30.10.2026: in der App „Theater“, nicht „Darstellendes Spiel“
THEATER_KURS = "Kurs 11"   # Jan 30.10.2026, steht noch in keiner Datei des Theater-Agenten


def _toml(pfad: Path) -> dict:
    """Inhalt einer TOML-Datei, {} wenn sie fehlt. Kaputte Dateien werfen ValueError mit Dateiname."""
    if not pfad.exists():
        return {}
    try:
        return tomllib.loads(pfad.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"{pfad}: {e}") from None


def _ersatz(agenten: Path) -> tuple[list, str]:
    """[[reihe]]-Blöcke aus dem Bestand der Agent-Ordner und das Standardfach."""
    eintraege = [dict(e) for e in _toml(agenten / "unterricht" / DATEI).get("reihe", [])
                 if isinstance(e, dict)]
    fach = _toml(agenten / "unterricht" / "profil.toml").get("fach") or ""
    examen = (_toml(agenten / "examen" / "examen.toml").get("reihe") or {}).get("titel_in_reihen_toml") or ""
    treffer = [e for e in eintraege if examen and str(e.get("titel", "")).startswith(examen)]
    if len(treffer) == 1:
        treffer[0]["agenten"] = [*treffer[0].get("agenten", []), "examen"]
    stueck = (_toml(agenten / "theater" / "theater.toml").get("stueck") or {}).get("titel") or ""
    if stueck:
        eintraege.append({"fach": THEATER_FACH, "klasse": THEATER_KURS, "titel": stueck, "agenten": ["theater"]})
    return eintraege, fach


def laden(instanz: Path) -> tuple[list[dict], list[str]]:
    """Reihen der Instanz und Fehlertexte für Jan. Bei kaputten Dateien keine Reihen, die App läuft weiter."""
    try:
        datei = instanz / DATEI
        if datei.exists():
            eintraege, fach = _toml(datei).get("reihe", []), ""
        else:
            eintraege, fach = _ersatz(instanz.parent)
    except ValueError as e:
        return [], [str(e)]
    if not isinstance(eintraege, list):
        return [], [f"{DATEI}: Reihen als [[reihe]] schreiben"]
    return logik.reihen_aus(eintraege, fach)
