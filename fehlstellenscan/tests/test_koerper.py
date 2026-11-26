"""Tests für aufnahme/koerper.py mit künstlichen Fotos: dunkler Grund, Holzfläche mit Maserung."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from aufnahme import koerper as ko

GRUND = (18, 20, 30)
PX = 5.0                      # px je mm der künstlichen Fotos


def maserung(breite: int, hoehe: int, saat: int = 1) -> Image.Image:
    """Holzfarbe mit unregelmäßigen Streifen und Flecken, damit Lage und Inhalt prüfbar sind."""
    g = np.random.default_rng(saat)
    x = np.arange(breite)[None, :]
    y = np.arange(hoehe)[:, None]
    welle = np.sin(y / 9 + 3 * np.sin(x / 140)) * 25 + g.normal(0, 6, (hoehe, breite))
    for _ in range(max(3, breite // 150)):           # Äste: dunkle Flecken
        cx, cy, r = g.integers(0, breite), g.integers(0, hoehe), g.integers(8, 30)
        welle -= 70 * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * r * r))
    rgb = np.stack([190 + welle, 140 + welle * .8, 80 + welle * .5], -1)
    return Image.fromarray(rgb.clip(0, 255).astype(np.uint8))


def foto(holz: Image.Image, links_px: int, breite_px=2000, hoehe_px=1000, winkel=0.0) -> Image.Image:
    """Holz mittig quer, links_px = Lage des Holzanfangs im Foto (darf negativ sein)."""
    bild = Image.new("RGB", (breite_px, hoehe_px), GRUND)
    bild.paste(holz, (links_px, (hoehe_px - holz.height) // 2))
    return bild.rotate(winkel, resample=Image.Resampling.BICUBIC, fillcolor=GRUND) if winkel else bild


class TestKanten(unittest.TestCase):
    def test_otsu_trennt_zwei_gruppen(self):
        werte = np.concatenate([np.full(500, -10), np.full(300, 90)])
        self.assertTrue(-10 < ko.schwelle_otsu(werte) < 90)

    def test_schraeg_liegende_flaeche(self):
        holz = maserung(1200, 500)                     # 240 x 100 mm
        for winkel in (2.0, -1.5, 0.0):
            gerade, k = ko.flaeche_finden(foto(holz, 400, winkel=winkel))
            # PIL dreht gegen den Uhrzeigersinn, die Fläche ist danach im Uhrzeigersinn geneigt
            self.assertAlmostEqual(k["winkel"], -winkel, delta=0.15)
            self.assertAlmostEqual((k["rechts"] - k["links"]) / PX, 240, delta=2.5)
            self.assertAlmostEqual((k["unten"] - k["oben"]) / PX, 100, delta=1.5)
            self.assertFalse(k["rand_links"] or k["rand_rechts"])

    def test_ohne_holz(self):
        with self.assertRaises(ValueError):
            ko.laengster_lauf(np.zeros(10, bool))


class TestSeite(unittest.TestCase):
    def test_ein_foto(self):
        holz = maserung(1500, 600)                      # 300 x 120 mm
        bild, b = ko.seite_bauen([{"bild": foto(holz, 250), "mitte_mm": 150, "px_je_mm": PX}], 300, 120)
        self.assertEqual(bild.size, (1200, 480))       # 4 px je mm
        self.assertAlmostEqual(b["laenge_mm"], 300, delta=2)
        self.assertAlmostEqual(b["flaeche_mm"], 120, delta=1)
        self.assertEqual((b["richtung"], b["luecke_anteil"]), (1, 0.0))

    def zwei_fotos(self, spiegeln: bool):
        """600 mm Balken, zwei Fotos je 400 mm breit, Mitten bei 150 und 450 mm (100 mm Überlappung)."""
        holz = maserung(3000, 500, saat=7)              # 600 x 100 mm
        fotos = []
        for mitte in (150, 450):
            f = foto(holz, round((200 - mitte) * PX))   # Bildmitte (1000 px) zeigt mm "mitte"
            if spiegeln:                                # Vorschub andersherum: mm wachsen nach links
                f = f.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            fotos.append({"bild": f, "mitte_mm": mitte, "px_je_mm": PX})
        return holz, ko.seite_bauen(fotos, 600, 100)

    def test_zwei_fotos_ergeben_den_ganzen_balken(self):
        for spiegeln in (False, True):
            holz, (bild, b) = self.zwei_fotos(spiegeln)
            self.assertEqual(b["richtung"], -1 if spiegeln else 1)
            self.assertAlmostEqual(b["laenge_mm"], 600, delta=2)
            self.assertEqual(b["luecke_anteil"], 0.0)
            soll = holz.resize(bild.size)
            if spiegeln:                                # nie gespiegelt: Bildrichtung wie im Foto
                soll = soll.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            fehler = np.abs(np.asarray(bild, float) - np.asarray(soll, float)).mean()
            self.assertLess(fehler, 8, f"spiegeln={spiegeln}")

    def test_kein_ende_im_ersten_foto(self):
        holz = maserung(3000, 500)
        f = {"bild": foto(holz, -500), "mitte_mm": 150, "px_je_mm": PX}
        with self.assertRaises(ValueError):
            ko.seite_bauen([f], 600, 100)


class TestPlausibel(unittest.TestCase):
    def bericht(self, winkel=0.0, laenge=0.0, flaeche=0.0, luecke=0.0):
        return {"winkel_grad": [winkel], "abweichung_prozent": {"laenge": laenge, "flaeche": flaeche},
                "luecke_anteil": luecke}

    def test_gruende(self):
        self.assertIsNone(ko.unplausibel(self.bericht(winkel=-0.3, laenge=3.3, flaeche=3.7)))    # B002 S3
        self.assertIn("schief", ko.unplausibel(self.bericht(winkel=-76.4)))                    # B001 S3
        self.assertIn("139 %", ko.unplausibel(self.bericht(laenge=-49.9, flaeche=138.8)))      # B001 S2
        self.assertIn("fehlen", ko.unplausibel(self.bericht(luecke=0.5)))
        self.assertIsNone(ko.unplausibel({"winkel_grad": [0], "abweichung_prozent": {"laenge": None, "flaeche": 1},
                                          "luecke_anteil": 0}))

    def test_quer_liegender_balken_wird_verworfen(self):
        """Wie B001 Seite 2: Fläche liegt quer im Bild, gemessen 100 x 300 statt 300 x 100 mm."""
        with tempfile.TemporaryDirectory() as t:
            ordner = Path(t) / "B009"
            (ordner / "zuschnitt").mkdir(parents=True)
            foto(maserung(500, 1500).resize((500, 900)), 750, hoehe_px=1000).save(ordner / "zuschnitt" / "q.jpg")
            (ordner / "balken.json").write_text(json.dumps({"id": "B009", "laenge_mm": 300, "breite_mm": 100,
                "hoehe_mm": 100, "seiten": {"1": {"plan": {"flaeche_mm": 100}, "fotos": {"0": {
                    "datei": "q.heic", "mitte_mm": 150, "px_je_mm": PX}}}}}))
            self.assertIsNotNone(ko.koerper_bauen(ordner)["seiten"]["1"]["grund"])


class TestOrdner(unittest.TestCase):
    def test_px_aus_plan_wie_b002(self):
        zuschnitt = Image.new("RGB", (2910, 2834))
        plan = {"zuschnitt": [0.098, 0.0313, 0.7218, 0.9373], "voll_mm": 607.6343162027969}
        self.assertAlmostEqual(ko.px_aus_plan(zuschnitt, plan), 6.64, delta=0.01)    # sips am Mac: 6,64


    def test_koerper_bauen(self):
        with tempfile.TemporaryDirectory() as t:
            ordner = Path(t) / "B007"
            (ordner / "zuschnitt").mkdir(parents=True)
            seiten = {}
            for nr, flaeche in (("1", 100), ("2", 60)):
                name = f"B007_S{nr}_01_00150mm_x"
                foto(maserung(1500, flaeche * 5, saat=int(nr)), 250).save(ordner / "zuschnitt" / f"{name}.jpg")
                seiten[nr] = {"plan": {"flaeche_mm": flaeche},
                              "fotos": {"0": {"datei": f"{name}.heic", "mitte_mm": 150, "px_je_mm": PX}}}
            seiten["3"] = {"plan": {"flaeche_mm": 100}, "fotos": {}}
            (ordner / "balken.json").write_text(json.dumps(
                {"id": "B007", "laenge_mm": 300, "breite_mm": 60, "hoehe_mm": 100, "seiten": seiten}))
            k = ko.koerper_bauen(ordner)
            self.assertEqual(sorted(k["seiten"]), ["1", "2"])
            self.assertAlmostEqual(k["seiten"]["2"]["abweichung_prozent"]["flaeche"], 0, delta=1.5)
            with Image.open(ordner / "koerper" / "S2.jpg") as s2:
                self.assertEqual(s2.size, (1200, 240))
            self.assertEqual(json.loads((ordner / "koerper" / "koerper.json").read_text())["id"], "B007")

    def test_zuschnitt_fehlt(self):
        with tempfile.TemporaryDirectory() as t:
            ordner = Path(t)
            (ordner / "balken.json").write_text(json.dumps({"id": "B1", "laenge_mm": 1, "breite_mm": 1, "hoehe_mm": 1,
                "seiten": {"1": {"plan": {"flaeche_mm": 1}, "fotos": {"0": {"datei": "x.heic", "mitte_mm": 0,
                                                                              "px_je_mm": 1}}}}}))
            with self.assertRaises(FileNotFoundError):
                ko.koerper_bauen(ordner)


if __name__ == "__main__":
    unittest.main()
