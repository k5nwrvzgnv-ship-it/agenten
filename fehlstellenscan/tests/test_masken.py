"""Tests für masken.py: Flecken finden, YOLO-seg-Zeilen, Masken aus ZIP und Ordner, Bauen, Gegenprobe, Zeichnen."""

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

import datensatz as d
import masken as m

HIER = Path(__file__).resolve().parent.parent
PROBE_MASKEN = HIER / "data" / "annotationen"
PROBE_BILDER = HIER / "data" / "rohbilder"
SPEZIFIKATION = PROBE_MASKEN / "Semantic Map Specification.txt"

GRUEN, ROT, LILA = (0, 255, 0), (255, 0, 0), (0x64, 0, 0x64)   # live_knot, dead_knot, quartzity


def maske(hoehe=40, breite=60) -> np.ndarray:
    return np.zeros((hoehe, breite, 3), np.uint8)


def flecken(rgb: np.ndarray, min_px=2) -> dict:
    return m.flecken(m.farbschluessel(rgb), min_px)


def bmp(rgb: np.ndarray) -> bytes:
    puffer = io.BytesIO()
    Image.fromarray(rgb).save(puffer, format="BMP")
    return puffer.getvalue()


class TestFlecken(unittest.TestCase):
    def test_farben_in_klassenreihenfolge(self):
        self.assertEqual(m.KLASSE_VON[0x00FF00], d.NUMMER["live_knot"])
        self.assertEqual(m.KLASSE_VON[0xFF0000], d.NUMMER["dead_knot"])
        self.assertEqual(m.KLASSE_VON[0x004000], d.NUMMER["overgrown"])
        self.assertNotIn(m.HINTERGRUND, m.KLASSE_VON)

    def test_jeder_fleck_ein_objekt(self):
        a = maske()
        a[5:15, 5:20] = GRUEN
        a[25:35, 30:50] = GRUEN
        a[20:30, 5:10] = ROT
        f = flecken(a)
        self.assertEqual(sorted(k for k, _ in f["objekte"]), [0, 0, 1])
        self.assertEqual((f["klein"], f["linie"], f["unbekannt"]), ([], [], {}))

    def test_polygon_durch_pixelmitten(self):
        a = maske()
        a[4:9, 3:13] = ROT                    # x 3..12, y 4..8
        (klasse, punkte), = flecken(a)["objekte"]
        self.assertEqual(klasse, 1)
        self.assertEqual(punkte.min(axis=0).tolist(), [3.5, 4.5])
        self.assertEqual(punkte.max(axis=0).tolist(), [12.5, 8.5])

    def test_klein_und_linie_weggelassen(self):
        a = maske()
        a[2, 2] = GRUEN                       # 1 x 1: Klickfehler
        a[10:12, 40:41] = GRUEN               # 1 breit
        for i in range(8):                    # schräge Linie 1 px: 8 x 8, aber ohne Fläche
            a[20 + i, 10 + i] = ROT
        f = flecken(a)
        self.assertEqual(f["objekte"], [])
        self.assertEqual(sorted(f["klein"]), [(0, 1, 1), (0, 1, 2)])
        self.assertEqual(f["linie"], [(1, 8, 8)])

    def test_zwei_pixel_bleiben(self):
        a = maske()
        a[10:12, 10:12] = GRUEN
        self.assertEqual(len(flecken(a)["objekte"]), 1)

    def test_unbekannte_farbe_gemeldet_nicht_geraten(self):
        a = maske()
        a[5:10, 5:10] = (0, 254, 0)           # fast live_knot, z. B. Mischfarbe am Rand
        f = flecken(a)
        self.assertEqual(f["objekte"], [])
        self.assertEqual(f["unbekannt"], {"00FE00": 25})

    def test_loch_wird_gezaehlt(self):
        a = maske()
        a[5:25, 5:25] = LILA
        a[10:15, 10:15] = 0
        f = flecken(a)
        self.assertEqual(len(f["objekte"]), 1)
        self.assertEqual(f["loecher"], {5: 1})

    def test_leere_maske(self):
        f = flecken(maske())
        self.assertEqual((f["objekte"], f["unbekannt"]), ([], {}))


class TestYoloSeg(unittest.TestCase):
    def test_hin_und_zurueck(self):
        punkte = np.array([[3.5, 4.5], [12.5, 4.5], [12.5, 8.5], [3.5, 8.5]])
        zeile = m.zu_yolo_seg(4, punkte, 2780, 1024)
        self.assertTrue(zeile.startswith("4 0.001259 0.004395 "))
        klasse, zurueck = m.von_yolo_seg(zeile, 2780, 1024)
        self.assertEqual(klasse, 4)
        np.testing.assert_allclose(zurueck, punkte, atol=0.002)

    def test_ungueltige_zeilen(self):
        for zeile in ["0 0.1 0.1 0.2 0.2", "0 0.1 0.1 0.2 0.2 0.3", "0 0.1 0.1 0.2 0.2 0.3 1.2"]:
            with self.assertRaises(ValueError, msg=zeile):
                m.von_yolo_seg(zeile, 100, 100)

    def test_klassen_zaehlen(self):
        self.assertEqual(m.label_klassen("0 0.1 0.2\n1 0.3 0.4\n0 0.5 0.6\n\n"), {0: 2, 1: 1})


class TestBauen(unittest.TestCase):
    """Kleiner Box-Datensatz als Vorlage (train 2, val 1, test 1 Bild) und Masken im ZIP."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.vorlage = self.tmp / "kodytek-1"
        self.masken = {}
        bilder = {"train": ["100000000", "100000001"], "val": ["200000000"], "test": ["300000000"]}
        for teil, nummern in bilder.items():
            (self.vorlage / "images" / teil).mkdir(parents=True)
            (self.vorlage / "labels" / teil).mkdir(parents=True)
            for nummer in nummern:
                breite = 59 if nummer == "100000001" else 60          # ein schmales Bild wie bei Kodytek
                Image.fromarray(np.full((40, breite, 3), 128, np.uint8)).save(
                    self.vorlage / "images" / teil / f"{nummer}.bmp")
                self.masken[nummer] = maske(40, breite)
        self.masken["100000000"][5:15, 5:20] = GRUEN
        self.masken["100000000"][20:30, 30:40] = ROT
        self.masken["200000000"][10:20, 10:20] = LILA
        boxen = {"100000000": "0 0.208333 0.250000 0.250000 0.250000\n1 0.583333 0.625000 0.166667 0.250000\n",
                 "100000001": "", "200000000": "5 0.250000 0.375000 0.166667 0.250000\n", "300000000": ""}
        for teil, nummern in bilder.items():
            for nummer in nummern:
                (self.vorlage / "labels" / teil / f"{nummer}.txt").write_text(boxen[nummer])
        self.zip = self.tmp / "Semantic Maps.zip"
        self.zip_schreiben()
        self.ziel = self.tmp / "kodytek-seg-1"

    def zip_schreiben(self):
        with zipfile.ZipFile(self.zip, "w", zipfile.ZIP_DEFLATED) as z:
            for nummer, rgb in self.masken.items():
                z.writestr(f"Semantic Maps/{nummer}_segm.bmp", bmp(rgb))

    def tearDown(self):
        self._tmp.cleanup()

    def test_masken_aus_zip_und_ordner_gleich(self):
        ordner = self.tmp / "masken"
        with zipfile.ZipFile(self.zip) as z:
            z.extractall(ordner)
        aus_zip, aus_ordner = m.Masken(self.zip), m.Masken(ordner)
        self.assertEqual(aus_zip.nummern(), aus_ordner.nummern())
        self.assertIn("100000001", aus_zip)
        np.testing.assert_array_equal(aus_zip.lesen("100000000"), self.masken["100000000"])
        np.testing.assert_array_equal(aus_ordner.lesen("100000000"), self.masken["100000000"])

    def test_bauen_mit_aufteilung_der_vorlage(self):
        bericht = m.bauen(self.vorlage, self.zip, self.ziel, 2)
        t = bericht["teile"]
        self.assertEqual([t[x]["bilder"] for x in d.TEILE], [2, 1, 1])
        self.assertEqual([t[x]["ohne_fehler"] for x in d.TEILE], [1, 0, 1])
        self.assertEqual(t["train"]["objekte"], {"live_knot": 1, "dead_knot": 1})
        self.assertEqual(t["val"]["objekte"], {"quartzity": 1})
        self.assertTrue((self.ziel / "images" / "val" / "200000000.bmp").samefile(
            self.vorlage / "images" / "val" / "200000000.bmp"))
        self.assertEqual((self.ziel / "labels" / "test" / "300000000.txt").read_text(), "")
        zeilen = (self.ziel / "labels" / "train" / "100000000.txt").read_text().splitlines()
        klasse, punkte = m.von_yolo_seg(zeilen[0], 60, 40)
        self.assertEqual(klasse, 0)
        self.assertEqual(punkte.min(axis=0).round(3).tolist(), [5.5, 5.5])
        yaml = (self.ziel / "data.yaml").read_text()
        self.assertIn("test: images/test", yaml)
        self.assertIn("  9: overgrown", yaml)
        self.assertEqual(json.loads((self.ziel / "bericht.json").read_text())["fehlende_masken"], 0)
        self.assertTrue((self.ziel / "DATENKARTE.md").exists())

    def test_normiert_auf_echte_breite(self):
        self.masken["100000001"][0:40, 49:59] = ROT          # bis zum rechten Rand des 59 px breiten Bilds
        self.zip_schreiben()
        m.bauen(self.vorlage, self.zip, self.ziel, 2)
        zeile = (self.ziel / "labels" / "train" / "100000001.txt").read_text()
        _, punkte = m.von_yolo_seg(zeile, 59, 40)
        self.assertAlmostEqual(punkte[:, 0].max(), 58.5, places=2)

    def test_ziel_wird_nie_ueberschrieben(self):
        self.ziel.mkdir()
        with self.assertRaises(FileExistsError):
            m.bauen(self.vorlage, self.zip, self.ziel, 2)

    def test_fehlende_maske(self):
        del self.masken["300000000"]
        self.zip_schreiben()
        with self.assertRaises(FileNotFoundError):
            m.bauen(self.vorlage, self.zip, self.ziel, 2)
        bericht = m.bauen(self.vorlage, self.zip, self.ziel, 2, nur_vorhandene=True)
        self.assertEqual(bericht["fehlende_masken"], 1)
        self.assertEqual(bericht["teile"]["test"]["bilder"], 0)

    def test_falsche_groesse_und_unbekannte_farbe_gemeldet(self):
        self.masken["300000000"] = maske(40, 61)
        self.masken["200000000"][30:35, 30:35] = (1, 2, 3)
        self.zip_schreiben()
        bericht = m.bauen(self.vorlage, self.zip, self.ziel, 2)
        self.assertEqual(bericht["groesse_abweichend"],
                         [{"nummer": "300000000", "bild": [60, 40], "maske": [61, 40]}])
        self.assertFalse((self.ziel / "labels" / "test" / "300000000.txt").exists())
        self.assertEqual(bericht["unbekannte_farben"], {"010203": {"pixel": 25, "bilder": ["200000000"]}})
        self.assertEqual(bericht["teile"]["val"]["objekte"], {"quartzity": 1})

    def test_probe_nur_train_mit_objekten(self):
        bericht = m.bauen(self.vorlage, self.zip, self.ziel, 2, probe=5)
        self.assertEqual(bericht["teile"]["train"]["bilder"], 1)
        self.assertEqual(bericht["teile"]["val"]["bilder"], 0)
        self.assertIn("val: images/train", (self.ziel / "data.yaml").read_text())

    def test_gegenprobe(self):
        self.masken["100000000"][35:38, 50:55] = GRUEN       # Fleck ohne Box
        self.zip_schreiben()
        m.bauen(self.vorlage, self.zip, self.ziel, 2)
        ergebnis = m.gegenprobe(self.ziel, self.vorlage)
        zeile = next(z for z in ergebnis["tabelle"] if z["teil"] == "train" and z["klasse"] == "live_knot")
        self.assertEqual((zeile["boxen"], zeile["flecken"], zeile["differenz"]), (1, 2, 1))
        self.assertEqual(ergebnis["bilder_mit_abweichung"],
                         [{"teil": "train", "nummer": "100000000", "abweichung": {"live_knot": [1, 2]}}])

    def test_zeichnen_nur_masken(self):
        m.bauen(self.vorlage, self.zip, self.ziel, 2)
        jpg = m.zeichnen(self.ziel, "100000000", self.tmp / "bilder")
        self.assertEqual(jpg.name, "100000000_masken.jpg")
        with Image.open(jpg) as bild:
            hoehe = round(40 * m.BREITE_BILD / 60)
            self.assertEqual(bild.size, (m.BREITE_BILD, 50 + hoehe))
            pixel = np.asarray(bild.convert("RGB")).astype(int)
        mitte = pixel[50 + round(10 * m.BREITE_BILD / 60), round(12.5 * m.BREITE_BILD / 60)]  # im grünen Fleck
        self.assertGreater(mitte[1] - mitte[0], 50)                  # grün eingefärbt
        rand = pixel[-5, -5]                                         # Holz ohne Fehlstelle bleibt grau
        self.assertLess(abs(rand[1] - rand[0]), 15)
        with self.assertRaises(FileNotFoundError):
            m.zeichnen(self.ziel, "999999999", self.tmp / "bilder")

    def test_gruppenbilder_vergleich_umriss_masse(self):
        bilder, markierung, vorhersage = (self.tmp / n for n in ("bilder", "markierung", "vorhersage"))
        for ordner in (bilder, markierung, vorhersage):
            ordner.mkdir()
        (bilder / "100000000.bmp").write_bytes((self.vorlage / "images/train/100000000.bmp").read_bytes())
        (bilder / "100000001.bmp").write_bytes((self.vorlage / "images/train/100000001.bmp").read_bytes())
        punkte = np.array([[5.5, 5.5], [19.5, 5.5], [19.5, 14.5], [12, 15], [5.5, 14.5]])
        label = m.zu_yolo_seg(0, punkte, 60, 40) + "\n"
        (markierung / "100000000.txt").write_text(label)
        (markierung / "100000001.txt").write_text("")
        (vorhersage / "100000000.txt").write_text(label.strip() + " 0.83\n")      # save_conf: Konfidenz am Ende
        ziele = m.gruppenbilder(bilder, markierung, vorhersage, "100000000", self.tmp / "fertig")
        self.assertEqual([z.name for z in ziele],
                         ["100000000_vergleich.jpg", "100000000_umriss.jpg", "100000000_masse.jpg"])
        hoehe = 50 + round(40 * m.BREITE_BILD / 60)
        with Image.open(ziele[0]) as vergleich, Image.open(ziele[1]) as umriss:
            self.assertEqual(vergleich.size, (m.BREITE_BILD, 2 * hoehe + 6))
            self.assertEqual(umriss.size, (m.BREITE_BILD, hoehe))
            pixel = np.asarray(umriss.convert("RGB")).astype(int)
        mitte = pixel[50 + round(10 * m.BREITE_BILD / 60), round(12.5 * m.BREITE_BILD / 60)]
        self.assertLess(abs(mitte[1] - mitte[0]), 15)                 # Umriss: innen nicht eingefärbt
        # ohne Datei der Vorhersage (Modell fand nichts) entstehen die Bilder trotzdem, nur ohne Masken
        self.assertEqual(len(m.gruppenbilder(bilder, markierung, vorhersage, "100000001", self.tmp / "fertig")), 3)

    def test_unbekannte_art(self):
        with self.assertRaises(ValueError):
            m.masken_bild(Image.new("RGB", (10, 10)), [], "x", art="boxen")


class TestVorhersageUndMasse(unittest.TestCase):
    def test_vorhersage_mit_und_ohne_konfidenz(self):
        zeile = m.zu_yolo_seg(1, np.array([[10.0, 10], [20, 10], [20, 20]]), 100, 50)
        mit, ohne = m.objekte_aus_vorhersage(f"{zeile} 0.61\n\n{zeile}\n", 100, 50)
        self.assertEqual((mit[0], mit[2]), (1, 0.61))
        self.assertIsNone(ohne[2])
        np.testing.assert_allclose(mit[1], ohne[1])

    def test_masse_kreis_in_mm_trotz_ungleicher_pixel(self):
        t = np.linspace(0, 2 * np.pi, 60, endpoint=False)
        kreis_mm = np.stack([50 + 5 * np.cos(t), 40 + 5 * np.sin(t)], axis=1)       # Durchmesser 10 mm
        masse = m.masse_mm(kreis_mm * m.PX_JE_MM)
        self.assertAlmostEqual(masse["lang"], 10, delta=0.1)
        self.assertAlmostEqual(masse["kurz"], 10, delta=0.1)

    def test_masse_gedrehte_ellipse_und_rueckweg(self):
        t, w = np.linspace(0, 2 * np.pi, 80, endpoint=False), np.radians(30)
        x, y = 12 * np.cos(t), 4 * np.sin(t)                                         # 24 x 8 mm, 30 Grad gedreht
        mm = np.stack([30 + x * np.cos(w) - y * np.sin(w), 20 + x * np.sin(w) + y * np.cos(w)], axis=1)
        masse = m.masse_mm(mm * m.PX_JE_MM)
        self.assertAlmostEqual(masse["lang"], 24, delta=0.1)
        self.assertAlmostEqual(masse["kurz"], 8, delta=0.1)
        umfang = m.ellipse_px(masse) / m.PX_JE_MM - (30, 20)
        np.testing.assert_allclose(np.linalg.norm(umfang, axis=1).max(), 12, atol=0.1)
        laengen = sorted(np.linalg.norm(np.diff(a / m.PX_JE_MM, axis=0)) for a in m.achsen_px(masse))
        np.testing.assert_allclose(laengen, [8, 24], atol=0.1)

    def test_textplatz_weicht_aus(self):
        punkte = np.array([[100.0, 100], [200, 100], [200, 150], [100, 150]])
        belegt = []
        for _ in range(3):                           # drei Masken auf demselben Ast
            belegt.append(m.textplatz(punkte, 120, 30, (800, 600), belegt))
        self.assertEqual(belegt[0], (100.0, 66.0, 220.0, 96.0))          # über dem Fleck
        self.assertEqual(belegt[1][1], 154.0)                              # darunter
        for i, a in enumerate(belegt):
            for b in belegt[i + 1:]:
                self.assertFalse(a[1] < b[3] and b[1] < a[3], (a, b))      # keine Überdeckung
        # am oberen Rand: gleich darunter, am rechten Rand: nach links ins Bild geschoben
        rand = m.textplatz(np.array([[790.0, 5], [799, 5], [799, 20]]), 120, 30, (800, 600), [])
        self.assertEqual(rand, (680.0, 24.0, 800.0, 54.0))

    def test_masse_braucht_fuenf_punkte(self):
        self.assertIsNone(m.masse_mm(np.array([[0.0, 0], [10, 0], [10, 10], [0, 10]])))

    def test_namen_je_klasse(self):
        self.assertEqual(len(m.NAMEN_DE), len(d.KLASSEN))
        self.assertEqual(len(m.ANZEIGE), len(d.KLASSEN))


@unittest.skipUnless((PROBE_MASKEN / "100000062_segm.bmp").exists() and PROBE_BILDER.is_dir(),
                     "Probemasken nur auf dem Server")
class TestProbemasken(unittest.TestCase):
    """Die 3 echten Masken unter data/annotationen/ (nicht im Repo): Flecken passen zu den Boxen der Quelle."""

    def test_farben_wie_spezifikation(self):
        text = SPEZIFIKATION.read_text(encoding="utf-8")
        farben = [z.split("=")[1].strip() for z in text.splitlines() if z.startswith("color=")]
        self.assertEqual(farben, m.FARBEN)

    def test_flecken_gleich_boxen(self):
        masken = m.Masken(PROBE_MASKEN)
        for nummer in ("100000000", "100000061", "100000062"):
            boxen, _ = d.datei_lesen(next((PROBE_MASKEN / "boxen").rglob(f"{nummer}_anno.txt")).read_text())
            breite, hoehe = d.bildgroesse(PROBE_BILDER / f"{nummer}.bmp")
            boxen, _ = d.filtern(boxen, breite, hoehe, d.MIN_PX)
            f = m.flecken(m.farbschluessel(masken.lesen(nummer)), d.MIN_PX)
            self.assertEqual(f["unbekannt"], {}, nummer)
            self.assertEqual(sorted(k for k, _ in f["objekte"]), sorted(b.klasse for b in boxen), nummer)
            for k, punkte in f["objekte"]:      # jedes Polygon liegt in einer Box derselben Klasse
                x1, y1 = (punkte.min(axis=0) - 0.5) / (breite, hoehe)
                x2, y2 = (punkte.max(axis=0) + 0.5) / (breite, hoehe)
                self.assertTrue(any(b.klasse == k and abs(b.x1 - x1) < 2e-3 and abs(b.y1 - y1) < 2e-3
                                    and abs(b.x2 - x2) < 2e-3 and abs(b.y2 - y2) < 2e-3 for b in boxen), nummer)


if __name__ == "__main__":
    unittest.main()
