"""Streifenbild eines ganzen Balkens (holzbalkenscan) als Balken in Neurolign übernehmen, mit den Funden eines
Modells als Vorlabel (Jan 26.11.2026: Felix' Balken als Test für die neuen Klassen).

Das Streifenbild wird längs in gleich lange Stücke um 1 m geschnitten (Maßstab bleibt, Länge waagerecht wie bei der
Fotobox). Jedes Stück wird ein hochgeladenes Foto von Seite 1. Die Funde aus balken.py karte (funde.json, Umrisse
in mm: l längs ab Balkenanfang, q quer ab Oberkante) werden auf die Stücke zugeschnitten und als offene Objekte mit
Konfidenz und Modellname gespeichert. Ein Mensch prüft sie in Labeln.

    .venv/bin/python -m aufnahme.streifen --kacheln data/laeufe/balken-felix-iso800/kacheln/kacheln.json \\
        --funde data/laeufe/balken-felix-iso800/karte/funde.json --ordner data/neurolign/aufnahmen \\
        --name "Felix 261019 A" --modell kodytek-seg1-n1280 --von jan

Pillow wird nur zum Schneiden gebraucht (Trainings- oder fehlstellenscan-.venv)."""

import argparse
import io
import json
import math
import sys
from pathlib import Path

STUECK_MM = 1000.0
MIN_FLAECHE_MM2 = 1.0


def stuecke(laenge_mm: float, ziel_mm: float = STUECK_MM) -> list[tuple[float, float]]:
    """Gleich lange Stücke, keins länger als ziel_mm."""
    n = max(1, math.ceil(laenge_mm / ziel_mm - 1e-9))
    return [(laenge_mm * i / n, laenge_mm * (i + 1) / n) for i in range(n)]


def zuschneiden(umriss: list, l0: float, l1: float) -> list[list[float]]:
    """Vieleck (Punkte [l, q]) auf l0 <= l <= l1 beschneiden (Sutherland-Hodgman an zwei Kanten)."""
    def kante(punkte, drin, schnitt):
        aus = []
        for i, a in enumerate(punkte):
            b = punkte[(i + 1) % len(punkte)]
            if drin(a):
                aus.append(a)
                if not drin(b):
                    aus.append(schnitt(a, b))
            elif drin(b):
                aus.append(schnitt(a, b))
        return aus

    def bei(x):
        return lambda a, b: [x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])]

    p = [list(map(float, q)) for q in umriss]
    p = kante(p, lambda a: a[0] >= l0, bei(l0)) if p else p
    p = kante(p, lambda a: a[0] <= l1, bei(l1)) if p else p
    return p


def flaeche(p: list) -> float:
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1], strict=True))) / 2


def vorlabels(funde: list[dict], l0: float, l1: float, hoehe_mm: float, namen: list[str], modell: str) -> list[dict]:
    """Funde eines Stücks als Objekte in Anteilen des Stücks (x längs, y quer). Klassen über den Schlüssel."""
    ergebnis = []
    for f in funde:
        if f["l_bis"] < l0 or f["l_von"] > l1 or f["klasse"] not in namen:
            continue
        p = zuschneiden(f["umriss"], l0, l1)
        if len(p) < 3 or flaeche(p) < MIN_FLAECHE_MM2:
            continue
        ergebnis.append({"k": namen.index(f["klasse"]), "ok": False, "c": round(float(f["konfidenz"]), 4), "q": modell,
                         "p": [[min(1, max(0, (a[0] - l0) / (l1 - l0))), min(1, max(0, a[1] / hoehe_mm))] for a in p]})
    return ergebnis


def uebernehmen(a) -> str:
    from PIL import Image
    if __package__:
        from . import server as s
    else:
        import server as s
    Image.MAX_IMAGE_PIXELS = None
    beschreibung = json.loads(Path(a.kacheln).read_text(encoding="utf-8"))
    funde = json.loads(Path(a.funde).read_text(encoding="utf-8"))
    laenge, hoehe, px = beschreibung["laenge_mm"], beschreibung["hoehe_mm"], beschreibung["px_je_mm"]
    fx, fy = beschreibung["feld_px"]
    werk = s.Werk(Path(a.ordner), Path(sys.executable))
    namen = werk.kette.namen()
    b = werk.balken_speichern({"laenge_mm": laenge, "breite_mm": hoehe, "hoehe_mm": a.hoehe_mm, "holzart": a.holzart,
                               "name": a.name}, a.von)
    kennung = b["id"]
    with Image.open(beschreibung["streifen"]) as roh:
        streifen = roh.convert("RGB")
        for l0, l1 in stuecke(laenge):
            kasten = tuple(round(v) for v in (fx + l0 * px, fy, fx + l1 * px, fy + hoehe * px))
            puffer = io.BytesIO()
            streifen.crop(kasten).save(puffer, "JPEG", quality=92)
            werk.hochladen(kennung, "1", puffer.getvalue(), a.von)
            with werk.schloss:
                bb = werk.lesen(kennung)
                nr = max(bb["seiten"]["1"]["fotos"], key=int)
                foto = bb["seiten"]["1"]["fotos"][nr]
                foto |= {"breite_px": kasten[2] - kasten[0], "hoehe_px": kasten[3] - kasten[1], "px_je_mm": px,
                         "quelle": "streifenbild", "lage_mm": [round(l0, 1), round(l1, 1)]}
                werk.ablegen(bb)
            objekte = vorlabels(funde, l0, l1, hoehe, namen, a.modell)
            werk.kette.speichern({"name": Path(foto["datei"]).stem, "objekte": objekte}, "vorlabel")
            print(f"{kennung} {l0:.0f}-{l1:.0f} mm: {len(objekte)} Vorlabel")
    return kennung


def main(argv=None) -> None:
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--kacheln", required=True, help="kacheln.json von balken.py (Streifen, Feld, Maßstab)")
    a.add_argument("--funde", required=True, help="funde.json von balken.py karte")
    a.add_argument("--ordner", required=True, help="Ablage von Neurolign (aufnahmen)")
    a.add_argument("--name", default="")
    a.add_argument("--modell", required=True, help="Name des Modells, steht an jedem Vorlabel")
    a.add_argument("--von", default="jan")
    a.add_argument("--holzart", default="")
    a.add_argument("--hoehe-mm", type=float, default=230.0, help="zweites Querschnittsmaß, wenn bekannt")
    print(uebernehmen(a.parse_args(argv)))


if __name__ == "__main__":
    main()
