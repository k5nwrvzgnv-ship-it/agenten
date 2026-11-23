"""Umwandlung von YOLO-seg-Textdateien in Objekte für die Werkbank (FiftyOne auf dem Mac), reine Logik ohne
fiftyone, auf dem Server getestet. Das Laden selbst macht mac/werkbank_laden.py (importiert fiftyone).

Ein Objekt wird beschrieben wie bei FiftyOne-Detektionen mit Maske: Rechteck relativ zur Bildgröße
[x, y, breite, hoehe] in 0..1 und eine Maske nur für dieses Rechteck (2D, bool, volle Pixelauflösung). Dazu Name
(deutsch, für die Anzeige), Klasse (Datensatzname), Konfidenz und Größe in mm wie in auswertung.py.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import auswertung as a
import datensatz as d
import masken as m


def rechteck_und_maske(punkte: np.ndarray, breite: int, hoehe: int) -> tuple[list[float], np.ndarray]:
    """Umriss in Pixeln -> (Rechteck relativ [x, y, b, h], Maske bool für das Rechteck in Pixeln)."""
    x0 = max(int(np.floor(punkte[:, 0].min())), 0)
    y0 = max(int(np.floor(punkte[:, 1].min())), 0)
    x1 = min(int(np.ceil(punkte[:, 0].max())), breite - 1)
    y1 = min(int(np.ceil(punkte[:, 1].max())), hoehe - 1)
    b, h = max(x1 - x0 + 1, 1), max(y1 - y0 + 1, 1)
    bild = Image.new("1", (b, h), 0)
    ImageDraw.Draw(bild).polygon([(float(x) - x0, float(y) - y0) for x, y in punkte], fill=1, outline=1)
    return [x0 / breite, y0 / hoehe, b / breite, h / hoehe], np.asarray(bild, dtype=bool)


def objekte(text: str, breite: int, hoehe: int, vorhersage: bool) -> list[dict]:
    """Inhalt einer Label- oder Vorhersagedatei als Liste von Objekten (siehe Modulbeschreibung)."""
    lesen = m.objekte_aus_vorhersage if vorhersage else m.objekte_aus_label
    ergebnis = []
    for klasse, punkte, konfidenz in lesen(text, breite, hoehe):
        rechteck, maske = rechteck_und_maske(punkte, breite, hoehe)
        kurz, lang = a.groesse_mm(punkte)
        ergebnis.append({"name": m.NAMEN_DE[klasse], "klasse": d.KLASSEN[klasse], "konfidenz": konfidenz,
                         "rechteck": rechteck, "maske": maske, "kurz_mm": round(kurz, 1), "lang_mm": round(lang, 1),
                         "groesse": a.groessenklasse(kurz), "ast": klasse in m.AESTE})
    return ergebnis


def datei_objekte(pfad: Path | None, breite: int, hoehe: int, vorhersage: bool) -> list[dict]:
    """Wie objekte, aus einer Datei; fehlende Datei = keine Objekte (yolo predict schreibt ohne Fund nichts)."""
    if pfad is None or not pfad.exists():
        return []
    return objekte(pfad.read_text(encoding="utf-8"), breite, hoehe, vorhersage)


def bilder_finden(ordner: Path) -> list[Path]:
    """Alle Bilder eines Ordners, sortiert nach Name."""
    return sorted(p for p in ordner.iterdir() if p.suffix.lower() in a.BILD_ENDUNGEN)
