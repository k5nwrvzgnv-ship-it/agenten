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


def fichte(breite: int, hoehe: int, saat: int = 1, aeste: int = 3) -> Image.Image:
    """Fichte wie B004/B005: Jahrringe laufen längs (quer gestreift, längs fast gleich), nur wenige Äste."""
    g = np.random.default_rng(saat)
    x = np.arange(breite)[None, :]
    y = np.arange(hoehe)[:, None]
    welle = np.sin(y / 6 + 2 * np.sin(x / 900) + 0.6 * np.sin(y / 2.3)) * 12 + g.normal(0, 3, (hoehe, breite))
    for _ in range(aeste):
        cx, cy, r = g.integers(0, breite), g.integers(0, hoehe), g.integers(6, 20)
        welle -= 60 * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * r * r))
    rgb = np.stack([200 + welle, 160 + welle * .8, 110 + welle * .5], -1)
    return Image.fromarray(rgb.clip(0, 255).astype(np.uint8))


def box_licht(bilder: list[Image.Image], saat: int = 3) -> list[Image.Image]:
    """Licht der Fotobox: Vignette und ein Glanzstreifen an fester Bildstelle, je Foto etwas heller oder dunkler."""
    g = np.random.default_rng(saat)
    x = np.arange(bilder[0].width)[None, :, None]
    licht = 1 - 0.25 * ((x - 900) / 1000) ** 2 + 0.25 * np.exp(-((x - 1300) ** 2) / (2 * 40 ** 2))
    return [Image.fromarray((np.asarray(b, float) * licht * g.uniform(0.9, 1.1)
                             + g.normal(0, 4, (b.height, b.width, 1))).clip(0, 255).astype(np.uint8)) for b in bilder]


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

    def test_graues_holz_auf_blauem_grund(self):
        """Wie B004 Seite 4: vergrautes Holz (129, 148, 161, Rot minus Blau -32) auf blaugrauem Grund, der zum Rand hin
        dunkel wird (70, 91, 121 bis 34, 43, 55: Rot minus Blau -51 bis -21). Rot minus Blau trennt das nicht (Fläche
        kam 165 statt 100 mm heraus), die Helligkeit schon."""
        g = np.random.default_rng(2)
        hell = np.abs(np.linspace(-1, 1, 1000))[:, None, None]               # Grund zu den Rändern hin dunkler
        bild = (1 - hell) * np.array([70, 91, 121]) + hell * np.array([34, 43, 55]) + g.normal(0, 4, (1000, 2000, 3))
        bild[250:750, 400:1600] = np.array([129, 148, 161]) + g.normal(0, 10, (500, 1200, 3))
        _, k = ko.flaeche_finden(Image.fromarray(bild.clip(0, 255).astype(np.uint8)))
        self.assertAlmostEqual((k["unten"] - k["oben"]) / PX, 100, delta=2)
        self.assertAlmostEqual((k["rechts"] - k["links"]) / PX, 240, delta=3)

    def test_drehen_ohne_schwarze_ecken(self):
        """Holz über die ganze Bildbreite, leicht schief, Grund bläulich: Die schwarzen Ecken der Drehung galten als
        Holz (Rot minus Blau 0 liegt über dem Grund), aus -1,2° wurden bei B004 -19°."""
        bild = Image.new("RGB", (2000, 1000), (60, 80, 115))
        hell = np.asarray(maserung(2600, 500), float) * 0.2 + np.array([225, 215, 210]) * 0.8      # helle Fichte
        bild.paste(Image.fromarray(hell.astype(np.uint8)), (-300, 250))
        bild = bild.rotate(1.2, resample=Image.Resampling.BICUBIC, fillcolor=(60, 80, 115))
        _, k = ko.flaeche_finden(bild)
        self.assertAlmostEqual(k["winkel"], -1.2, delta=0.3)
        self.assertTrue(k["rand_links"] and k["rand_rechts"])

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

    def test_serie_findet_die_lage_selbst(self):
        """Serie: Balken ungleichmäßig durchgeschoben, Lage nur aus der Überlappung (Jan 27.11.2026)."""
        holz = maserung(4000, 500, saat=7)                                   # 800 x 100 mm
        links = [200, -320, -900, -1450, -2080, -2600]                       # Schritte 104 bis 126 mm
        for spiegeln in (False, True):
            h = holz.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if spiegeln else holz
            fotos = [{"bild": foto(h, (2000 - 4000 - x) if spiegeln else x), "px_je_mm": PX} for x in links]
            bild, b = ko.seite_bauen(fotos, 800, 100, serie=True)
            self.assertEqual(b["serie"]["unsicher"], 0, b["serie"])
            self.assertAlmostEqual(b["laenge_mm"], 800, delta=3)
            self.assertEqual(b["luecke_anteil"], 0.0)
            soll = holz.resize(bild.size)
            if spiegeln:
                soll = soll.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            self.assertLess(np.abs(np.asarray(bild, float) - np.asarray(soll, float)).mean(), 10, f"spiegeln={spiegeln}")

    def test_serie_fichte_mit_maserung_laengs(self):
        """Wie B004/B005: Maserung längs, drei Äste, Licht steht im Bild, Schritte 80 bis 120 mm. Vorher kam die
        Länge 8 bis 17 % zu kurz heraus, weil Einzelpaare Nebengipfel trafen."""
        holz = fichte(5000, 500, saat=4)                                     # 1000 x 100 mm
        links, x = [], 300
        for schritt in (100, 85, 115, 95, 120, 80, 105, 110, 90, 100):
            links.append(x)
            x -= schritt * round(PX)
        fotos = [{"bild": b, "px_je_mm": PX} for b in box_licht([foto(holz, x) for x in links])]
        bild, b = ko.seite_bauen(fotos, 1000, 100, serie=True)
        self.assertAlmostEqual(b["laenge_mm"], 1000, delta=10, msg=b["serie"])
        self.assertEqual(b["luecke_anteil"], 0.0)
        self.assertLess(np.abs(np.asarray(bild, float) - np.asarray(holz.resize(bild.size), float)).mean(), 25)

    def test_serie_mit_hellen_raendern_und_leerem_ende(self):
        """Wie B007 Seite 4: Das Holz ist am Bildrand heller, an wechselnder Stelle quer (Güte 0,85 bei Weg 0), und
        am Ende der Serie zeigt ein Foto nur noch die Schiene am Rand (zählt nicht)."""
        holz = fichte(4000, 500, saat=6, aeste=5)                            # 800 x 100 mm
        g = np.random.default_rng(8)
        links, x = [], 300
        for schritt in (90, 110, 100, 95, 105, 100):
            links.append(x)
            x -= schritt * round(PX)
        bilder = []
        for b in box_licht([foto(holz, x) for x in links]):
            a = np.asarray(b, float).copy()
            for rand in (slice(0, 60), slice(1940, 2000)):                   # helle Flecken am Rand, quer verschieden
                y = int(g.integers(250, 550))
                a[y:y + 200, rand] = np.minimum(a[y:y + 200, rand] + 70, 255)
            bilder.append(Image.fromarray(a.astype(np.uint8)))
        schiene = Image.new("RGB", (2000, 1000), GRUND)
        schiene.paste((200, 190, 180), (1985, 0, 2000, 1000))
        fotos = [{"bild": b, "px_je_mm": PX} for b in bilder + [schiene]]
        _, b = ko.seite_bauen(fotos, 800, 100, serie=True)
        self.assertEqual(b["leer"], 1)
        self.assertAlmostEqual(b["laenge_mm"], 800, delta=8, msg=b["serie"])
        self.assertTrue(all(v < -50 for v in b["serie"]["versatz_mm"]), b["serie"])

    def test_korrelation_wie_von_hand(self):
        g = np.random.default_rng(5)
        a, b = g.normal(0, 1, (6, 90)), g.normal(0, 1, (6, 70))
        b[:, 10:50] += 3 * a[:, 30:70]                                       # Spalte j von b liegt auf j + 20 von a
        s, guete = ko.korrelation(a, b, 20)
        self.assertEqual(int(s[guete.argmax()]), 20)
        for v in (-30, 0, 20, 55):                                           # gleiche Zahl wie direkt gerechnet
            j0, j1 = max(0, -v), min(70, 90 - v)
            x, y = a[:, j0 + v:j1 + v].ravel(), b[:, j0:j1].ravel()
            self.assertAlmostEqual(float(guete[s == v][0]), float(np.corrcoef(x, y)[0, 1]), places=6)
        self.assertEqual(ko.guete_bei((5, np.array([0.1, 0.2])), np.array([4, 5, 6, 7])).tolist(), [-1, 0.1, 0.2, -1])

    def test_schiefes_endfoto_kippt_nichts(self):
        gerade, k = ko.flaeche_finden(foto(maserung(1200, 500), 400, winkel=35))
        self.assertTrue(k["ausreisser"])
        self.assertEqual(k["winkel"], 0.0)

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
    def test_senkrecht_aufgenommen(self):
        """Balken lief im Bild von oben nach unten (Richtung kurz): Zuschnitt wird vorher gedreht."""
        with tempfile.TemporaryDirectory() as t:
            ordner = Path(t) / "B010"
            (ordner / "zuschnitt").mkdir(parents=True)
            holz = maserung(1500, 500)                                      # 300 x 100 mm
            foto(holz, 250).transpose(Image.Transpose.ROTATE_270).save(ordner / "zuschnitt" / "s.jpg")
            (ordner / "balken.json").write_text(json.dumps({"id": "B010", "laenge_mm": 300, "breite_mm": 100,
                "hoehe_mm": 100, "seiten": {"1": {"plan": {"flaeche_mm": 100, "richtung": "kurz"}, "fotos": {"0": {
                    "datei": "s.heic", "mitte_mm": 150, "px_je_mm": PX}}}}}))
            s = ko.koerper_bauen(ordner)["seiten"]["1"]
            self.assertIsNone(s["grund"], s)
            self.assertAlmostEqual(s["laenge_mm"], 300, delta=2)

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

    def test_schaerfe(self):
        bild = foto(fichte(1500, 500, saat=2), 250)
        _, k = ko.flaeche_finden(bild)
        from PIL import ImageFilter
        self.assertGreater(ko.schaerfe(bild, k), 2 * ko.schaerfe(bild.filter(ImageFilter.BoxBlur(3)), k))

    def test_auswahl_dichte_serie(self):
        """Serie mit 40 mm Schritt (Bildfeld 400 mm) und leerem Foto am Ende: wenige Fotos fürs Labeln."""
        holz = fichte(5000, 500, saat=4, aeste=8)                            # 1000 x 100 mm
        links = [300 - i * 200 for i in range(19)]
        with tempfile.TemporaryDirectory() as t:
            ordner = Path(t) / "B008"
            (ordner / "zuschnitt").mkdir(parents=True)
            fotos = {}
            g = np.random.default_rng(3)
            grund = (np.array(GRUND) + g.normal(0, 4, (1000, 2000, 3))).clip(0, 255).astype(np.uint8)
            bilder = box_licht([foto(holz, x) for x in links]) + [Image.fromarray(grund)]
            for i, b in enumerate(bilder):
                name = f"B008_S1_{i + 1:02d}_x"
                b.save(ordner / "zuschnitt" / f"{name}.jpg", quality=95)
                fotos[str(i)] = {"datei": f"{name}.heic", "mitte_mm": 0, "px_je_mm": PX}
            (ordner / "balken.json").write_text(json.dumps(
                {"id": "B008", "laenge_mm": 1000, "breite_mm": 100, "hoehe_mm": 100,
                 "seiten": {"1": {"plan": {"flaeche_mm": 100, "serie": True}, "fotos": fotos}}}))
            s = ko.koerper_bauen(ordner)["seiten"]["1"]
            wahl = [x["wahl"] for x in s["auswahl"]]
            self.assertEqual(len(wahl), 20)
            self.assertEqual(wahl[-1], "leer")
            self.assertLessEqual(wahl.count("drin"), 6 + 2 * s["serie"]["unsicher"], s["auswahl"])
            self.assertEqual(s["auswahl"][3]["name"], "B008_S1_04_x")
            drin = sorted((x["a_mm"], x["b_mm"]) for x in s["auswahl"] if x["wahl"] == "drin")
            self.assertLess(drin[0][0], 5)
            self.assertGreater(drin[-1][1], 990)

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
