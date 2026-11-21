"""Tests für balken.py: Kachelraster, Lage und Maßstab der Kacheln, Rückweg auf den Balken, Doppelte, Karte."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

import balken as b


def streifen_mit_punkt(l_mm, q_mm, laenge=600.0, hoehe=230.0, s=6.0, feld=(12, 30)):
    """Weißer Streifen mit grauem Balkenfeld und einem roten Quadrat (4 x 4 mm) bei (l_mm, q_mm)."""
    breite, hoch = round(laenge * s) + 2 * feld[0], round(hoehe * s) + 2 * feld[1]
    a = np.full((hoch, breite, 3), 255, np.uint8)
    a[feld[1]:feld[1] + round(hoehe * s), feld[0]:feld[0] + round(laenge * s)] = (120, 90, 60)
    x, y = round(feld[0] + l_mm * s), round(feld[1] + q_mm * s)
    a[y - 12:y + 12, x - 12:x + 12] = (255, 0, 0)
    return Image.fromarray(a)


def rot_mitte(bild) -> np.ndarray:
    a = np.asarray(bild).astype(int)
    ys, xs = np.nonzero((a[..., 0] > 200) & (a[..., 1] < 80) & (a[..., 2] < 80))
    if not len(xs):
        return np.array([[np.nan, np.nan]])
    return np.array([[xs.mean(), ys.mean()]])


class TestRaster(unittest.TestCase):
    def test_anfaenge_buendig_und_ueberlappend(self):
        starts = b.anfaenge(1000, 150, 40)
        self.assertEqual(starts[0], 0)
        self.assertAlmostEqual(starts[-1] + 150, 1000)
        for a, c in zip(starts, starts[1:], strict=False):
            self.assertGreaterEqual(a + 150 - c, 40 - 1e-9)

    def test_kurze_strecke_eine_kachel(self):
        self.assertEqual(b.anfaenge(100, 150, 40), [0.0])
        self.assertEqual(b.kerne([0.0], 150), [(-np.inf, np.inf)])

    def test_kerne_lueckenlos(self):
        starts = b.anfaenge(1000, 150, 40)
        kerne = b.kerne(starts, 150)
        for (_, oben), (unten, _) in zip(kerne, kerne[1:], strict=False):
            self.assertEqual(oben, unten)

    def test_raster_balken_felix(self):
        kacheln = b.raster(6485, 230)
        quer = {k["q0"] for k in kacheln}
        self.assertEqual(len(quer), 2)                    # 230 mm hoch, Kachel 168 mm quer
        self.assertAlmostEqual(max(quer) + b.KACHEL_MM[0], 230, places=2)
        self.assertEqual(len({k["name"] for k in kacheln}), len(kacheln))

    def test_ueberlappung_zu_gross(self):
        with self.assertRaises(ValueError):
            b.anfaenge(1000, 150, 150)


class TestKachelLage(unittest.TestCase):
    def test_punkt_hin_und_zurueck(self):
        """Ein Punkt im Streifen landet in der Kachel und über kachel_zu_balken wieder an derselben Stelle."""
        l_mm, q_mm = 230.0, 170.0
        streifen = streifen_mit_punkt(l_mm, q_mm)
        kacheln = b.raster(600, 230)
        getroffen = 0
        for kachel in kacheln:
            bild = b.kachel_schneiden(streifen, (12, 30), 6.0, kachel)
            self.assertEqual(bild.size, b.KACHEL_PX)
            mitte = rot_mitte(bild)
            if np.isnan(mitte).any():
                continue
            getroffen += 1
            zurueck = b.kachel_zu_balken(mitte, kachel)[0]
            self.assertAlmostEqual(zurueck[0], l_mm, delta=0.5)
            self.assertAlmostEqual(zurueck[1], q_mm, delta=0.5)
        self.assertGreaterEqual(getroffen, 1)

    def test_kachel_transponiert(self):
        """Längs im Streifen (x) wird y in der Kachel: Ein längs langer Strich steht in der Kachel senkrecht."""
        a = np.full((300, 1200, 3), 100, np.uint8)
        a[140:146, 100:1100] = (255, 0, 0)                # waagerechter Strich längs
        kachel = {"l0": 0.0, "q0": 0.0}
        bild = np.asarray(b.kachel_schneiden(Image.fromarray(a), (0, 0), 6.0, kachel)).astype(int)
        ys, xs = np.nonzero((bild[..., 0] > 200) & (bild[..., 1] < 80))
        self.assertGreater(np.ptp(ys), 5 * np.ptp(xs))


class TestFunde(unittest.TestCase):
    def zeile(self, klasse, punkte_px, konfidenz=0.8):
        w, h = b.KACHEL_PX
        werte = " ".join(f"{x / w:.6f} {y / h:.6f}" for x, y in punkte_px)
        return f"{klasse} {werte} {konfidenz}"

    def kreis(self, mx, my, r=80):
        t = np.linspace(0, 2 * np.pi, 24, endpoint=False)
        return np.stack([mx + r * np.cos(t), my + r * np.sin(t)], axis=1)

    def test_doppelte_in_ueberlappung(self):
        kacheln = b.raster(250, 100)                      # zwei Kacheln längs (0 und 96,5 mm), eine quer
        self.assertEqual(len(kacheln), 2)
        # derselbe Ast in beiden Kacheln, im Balken bei l = 120 mm (Überlappung 96,5..153,5)
        l_mm, q_mm = 120.0, 50.0
        texte = {}
        for k in kacheln:
            px = ((q_mm - k["q0"]) * b.m.PX_JE_MM[0], (l_mm - k["l0"]) * b.m.PX_JE_MM[1])
            texte[k["name"]] = self.zeile(0, self.kreis(*px))
        funde, doppelt = b.funde_sammeln(kacheln, texte)
        self.assertEqual(len(funde), 1)
        self.assertEqual(doppelt, 1)
        f = funde[0]
        self.assertAlmostEqual((f["l_von"] + f["l_bis"]) / 2, l_mm, delta=0.5)
        self.assertEqual(f["name"], "Ast lebend")
        # Kreis mit 80 px Radius: quer 80/16,66 mm, längs 80/6,67 mm; Ellipse in mm also länglich längs
        self.assertAlmostEqual(f["ellipse_lang"], 2 * 80 / b.m.PX_JE_MM[1], delta=1.0)
        self.assertAlmostEqual(f["ellipse_kurz"], 2 * 80 / b.m.PX_JE_MM[0], delta=0.5)
        self.assertEqual(f["konfidenz"], 0.8)

    def test_riss_ohne_ellipse(self):
        kacheln = b.raster(100, 100)
        funde, _ = b.funde_sammeln(kacheln, {kacheln[0]["name"]: self.zeile(4, self.kreis(500, 500))})
        self.assertIsNone(funde[0]["ellipse_lang"])


class TestKarte(unittest.TestCase):
    def test_ende_zu_ende(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pfad = tmp / "streifen.jpg"
            streifen_mit_punkt(230.0, 170.0, laenge=1200.0).save(pfad, quality=95)
            beschreibung = b.kacheln_schreiben(pfad, tmp / "kacheln", 1200.0, 230.0, (12, 30), 6.0, 40.0)
            self.assertEqual(len(list((tmp / "kacheln").glob("*.jpg"))), len(beschreibung["kacheln"]))
            kachel = beschreibung["kacheln"][0]
            (tmp / "labels").mkdir()
            punkte = np.array([[1000, 300], [1200, 300], [1200, 500], [1000, 500], [1100, 550]])
            w, h = b.KACHEL_PX
            (tmp / "labels" / f"{kachel['name']}.txt").write_text(
                "1 " + " ".join(f"{x / w} {y / h}" for x, y in punkte) + " 0.6\n", encoding="utf-8")
            ergebnis = b.karte_schreiben(tmp / "kacheln", tmp / "labels", tmp / "karte")
            self.assertEqual(ergebnis["funde"], 1)
            self.assertEqual(ergebnis["je_klasse"], {"Ast tot": 1})
            self.assertEqual(len(ergebnis["bilder"]), 2)  # 1,2 m -> zwei Abschnitte
            funde = json.loads((tmp / "karte" / "funde.json").read_text(encoding="utf-8"))
            self.assertEqual(funde[0]["kachel"], kachel["name"])
            self.assertIn("klasse;name;konfidenz", (tmp / "karte" / "funde.csv").read_text(encoding="utf-8"))
            with Image.open(ergebnis["bilder"][0]) as karte:
                self.assertEqual(karte.width, round(1000 * b.KARTE_PX_JE_MM))

    def test_fremde_vorhersage(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "kacheln").mkdir()
            (tmp / "kacheln" / "kacheln.json").write_text(json.dumps({"kacheln": b.raster(250, 100)}),
                                                          encoding="utf-8")
            (tmp / "labels").mkdir()
            (tmp / "labels" / "fremd.txt").write_text("0 0 0 1 0 1 1 0.5\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                b.karte_schreiben(tmp / "kacheln", tmp / "labels", tmp / "karte")


if __name__ == "__main__":
    unittest.main()
