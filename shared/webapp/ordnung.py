"""Lias Struktur laden (nur lesend) über agentkit.struktur, EINE Leseschicht für App und Agenten (Strukturplan
docs/struktur-pflege-plan.md, Bauschritt 2). Quelle ist <instanz>/reihen.toml, im alten Format (nur [[reihe]])
oder im neuen ([[fach]], [[klasse]], [[reihe]], [[reihe.stunde]]). Was die App daraus zeigt, macht
logik.reihen_aus; zugeordnet wird in logik.py (reihe_von).
"""

import tomllib
from pathlib import Path

from agentkit import struktur

import logik


def _toml(pfad: Path) -> dict:
    """Inhalt einer TOML-Datei, {} wenn sie fehlt. Kaputte Dateien werfen ValueError mit Dateiname."""
    if not pfad.exists():
        return {}
    try:
        return tomllib.loads(pfad.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"{pfad}: {e}") from None


def laden(instanz: Path) -> tuple[list[dict], list[dict], list[str]]:
    """Reihen, Klassen/Kurse (logik.reihen_aus) und Fehlertexte für Jan. Ist die Datei kaputt, zeigt die App keine
    Reihen und läuft weiter (agentkit.struktur prüft die ganze Datei, wie lia/unterricht). Fehlt sie: leer."""
    try:
        s = struktur.laden(instanz)
    except (struktur.StrukturFehler, OSError, UnicodeDecodeError) as e:
        return [], [], [str(e)]
    return (*logik.reihen_aus(s), [])


# Für die Seiten „Vorlagen“ und „Ich“ (nur lesend): Gestaltung aus dem Profil des Material-Agenten, Lias Regeln aus
# <instanz>/regeln.md und den „Gelernten Regeln“ der Agenten. Auswerten macht logik.py (gestaltung, regeln_aus).
REGEL_AGENTEN = ("unterricht", "theater", "examen", "recherche")


def profil(instanz: Path) -> tuple[dict, list[str]]:
    """Profil des Material-Agenten (Schrift, Farben); fehlt es: {}. Kaputt: {} und Fehlertext für Jan."""
    try:
        return _toml(instanz.parent / "unterricht" / "profil.toml"), []
    except ValueError as e:
        return {}, [str(e)]


def regeltexte(instanz: Path) -> list[tuple[str, str]]:
    """(Agent oder "", Text) für regeln.md der Instanz und die STATUS.md der Agenten, soweit vorhanden."""
    quellen = [("", instanz / "regeln.md")] + [(a, instanz.parent / a / "STATUS.md") for a in REGEL_AGENTEN]
    texte = []
    for agent, pfad in quellen:
        try:
            texte.append((agent, pfad.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError):
            continue
    return texte
