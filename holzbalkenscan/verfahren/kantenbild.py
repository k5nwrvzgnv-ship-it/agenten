"""Zeichnet die gefundenen Kantenpunkte in die Aufnahme - zum Hinsehen.

Wenn Zahlen sich widersprechen, ist das Bild schneller als die naechste
Messung: Man sieht sofort, ob der Detektor die Bauteilkante trifft oder
etwas daneben.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zusammensetzen2 as z

TEILER = 4
STATIONEN = 200


def main():
    ordner = Path(sys.argv[1])
    ziel = Path(sys.argv[-1])
    bilder = sys.argv[2:-1]
    dreh = z.achse_bestimmen(sorted(ordner.glob("*.jpg")))

    # DIESELBE Vorgabe wie im echten Ablauf. Ohne sie sucht die Kantenmessung
    # im ganzen Bild und findet bei diesem Aufbau die Kanthoelzer mit.
    bv = z.band_aus_bewegung(sorted(ordner.glob("*.jpg")), dreh)
    erw = mitte = None
    if bv:
        with z.lade(ordner / bilder[0], TEILER, dreh) as im:
            fak = im.width and (im.width * TEILER) / im.width / TEILER
        lo, hi = bv[0] / TEILER, bv[1] / TEILER
        erw = hi - lo
        mitte = (lo + hi) / 2.0
        print(f"Vorgabe aus der Parallaxe: {lo:.0f}..{hi:.0f} Px "
              f"(Band {erw:.0f} Px)")
    for n, name in enumerate(bilder):
        with z.lade(ordner / name, TEILER, dreh) as im:
            a = np.asarray(im, np.float32)
            roh = im.copy()
        stat = z.stationsprofile(a, STATIONEN)
        Q = a.shape[1]
        if erw is None:
            b = z.bandsuche(stat[0], np.arange(int(0.20 * Q), int(0.85 * Q), 2))
            erw = float(b[2] - b[1]); mitte = (b[1] + b[2]) / 2.0
            print(f"Band {erw:.0f} Px, Mitte {mitte:.0f} Px von {Q} Px")
        # Bandbreite je Bild im Vorgabefenster nachmessen - mit DENSELBEN
        # Grenzen wie im echten Ablauf, sonst zeigt das Bild etwas anderes,
        # als der Zusammenbau spaeter tut.
        d_eng = np.arange(int(erw * 0.90), int(erw * 1.10) + 1)
        b = z.bandsuche(stat[0], d_eng, mitte, 0.30 * erw)
        bw = (b[2] - b[1]) if b else erw
        mi = ((b[1] + b[2]) / 2.0) if b else mitte
        print(f"  {name}: Band {bw:.0f} Px, Mitte {mi:.0f}")
        li, re, _ = z.kanten_je_station(stat, bw, mi, 0.12 * bw)

        # Arbeitskoordinaten: x quer, y laengs. Zum Ansehen zurueckdrehen.
        bild = roh.convert("RGB")
        d = ImageDraw.Draw(bild)
        for pkt, farbe in ((li, (255, 40, 40)), (re, (40, 120, 255))):
            for y, x in pkt:
                d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=farbe)
        if dreh:
            bild = bild.transpose(Image.ROTATE_270)
        br = 1500
        bild = bild.resize((br, round(bild.height * br / bild.width)))
        p = ziel.with_name(f"{ziel.stem}_{Path(name).stem}{ziel.suffix}")
        bild.save(p, quality=86)
        print(f"geschrieben: {p}   ({len(li)}/{STATIONEN} Stationen)")


if __name__ == "__main__":
    main()
