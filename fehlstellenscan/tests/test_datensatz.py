"""Tests für datensatz.py: Lesen, Umrechnen, Filtern, Aufteilen, Bauen. Ohne PyTorch, ohne Netz."""

import json
import random
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from PIL import Image

import datensatz as d

HIER = Path(__file__).resolve().parent.parent
PROBE_BOXEN = HIER / "data" / "annotationen" / "boxen"
PROBE_BILDER = HIER / "data" / "rohbilder"
AUFTEILUNG = HIER / "konfig" / "kodytek_aufteilung.json"


class TestLesen(unittest.TestCase):
    def test_zeile_mit_punkt_und_komma(self):
        a = d.zeile_lesen("Live_Knot\t0.1\t0.2\t0.3\t0.4\r\n")
        b = d.zeile_lesen("Live_Knot\t0,1\t0,2\t0,3\t0,4")
        self.assertEqual(a, b)
        self.assertEqual(a, d.Box(0, 0.1, 0.2, 0.3, 0.4))

    def test_alle_namen_der_quelle(self):
        namen = ["Live_Knot", "Dead_Knot", "Knot_missing", "knot_with_crack", "Crack", "Quartzity", "resin",
                 "Marrow", "Blue_Stain", "overgrown"]
        self.assertEqual([d.klasse_nummer(n) for n in namen], list(range(10)))

    def test_unbekannte_klasse_bricht_ab(self):
        with self.assertRaises(ValueError):
            d.zeile_lesen("Death_know\t0.1\t0.2\t0.3\t0.4")

    def test_ungueltige_ecken(self):
        for zeile in ["Crack\t0.3\t0.2\t0.1\t0.4", "Crack\t0.1\t0.2\t1.1\t0.4", "Crack\t0.1\t0.2\t0.3"]:
            with self.assertRaises(ValueError, msg=zeile):
                d.zeile_lesen(zeile)

    def test_leere_datei_ist_ohne_fehler(self):
        self.assertEqual(d.datei_lesen(""), ([], False))
        self.assertEqual(d.datei_lesen("\r\n"), ([], False))

    def test_datei_meldet_komma(self):
        boxen, komma = d.datei_lesen("Crack\t0,1\t0.2\t0.3\t0.4\r\nresin\t0.5\t0.5\t0.6\t0.6\r\n")
        self.assertEqual(len(boxen), 2)
        self.assertTrue(komma)


class TestUmrechnen(unittest.TestCase):
    def test_yolo_wert(self):
        # Maske 100000000: Box 1231..1412 x 304..1024 Pixel
        box = d.Box(5, 1231 / 2800, 304 / 1024, 1412 / 2800, 1.0)
        k, xm, ym, b, h = d.zu_yolo(box).split()
        self.assertEqual(k, "5")
        self.assertAlmostEqual(float(xm) * 2800, 1321.5, places=2)
        self.assertAlmostEqual(float(ym) * 1024, 664.0, places=2)
        self.assertAlmostEqual(float(b) * 2800, 181.0, places=2)
        self.assertAlmostEqual(float(h) * 1024, 720.0, places=2)

    def test_hin_und_zurueck_in_pixeln(self):
        rng = random.Random(1)
        for _ in range(500):
            breite = rng.choice([2800, 2799, 2709])
            x1, x2 = sorted(rng.sample(range(breite + 1), 2))
            y1, y2 = sorted(rng.sample(range(1025), 2))
            box = d.Box(rng.randrange(10), x1 / breite, y1 / 1024, x2 / breite, y2 / 1024)
            zurueck = d.von_yolo(d.zu_yolo(box))
            self.assertEqual(zurueck.klasse, box.klasse)
            for a, b, n in [(zurueck.x1, x1, breite), (zurueck.x2, x2, breite), (zurueck.y1, y1, 1024),
                            (zurueck.y2, y2, 1024)]:
                self.assertLess(abs(a * n - b), 0.01)

    def test_filter_mindestgroesse_in_echten_pixeln(self):
        schmal = d.Box(0, 0.1, 0.1, 0.1 + 1 / 2800, 0.5)     # 1 px breit
        flach = d.Box(0, 0.1, 0.1, 0.5, 0.1 + 1.5 / 1024)    # 1,5 px hoch
        gut = d.Box(0, 0.1, 0.1, 0.1 + 2 / 2800, 0.1 + 2 / 1024)
        behalten, weg = d.filtern([schmal, flach, gut], 2800, 1024, 2)
        self.assertEqual(behalten, [gut])
        self.assertEqual(weg, [schmal, flach])

    def test_gruppe(self):
        self.assertEqual(d.gruppe("100000061"), "1000")
        self.assertEqual(d.gruppe("100100027"), "1001")
        self.assertEqual(d.gruppe("99100031"), "991")
        with self.assertRaises(ValueError):
            d.gruppe("abc")

    def test_data_yaml(self):
        text = d.data_yaml("/x/kodytek-1")
        self.assertIn("path: /x/kodytek-1\n", text)
        self.assertIn("test: images/test\n", text)
        self.assertIn("  0: live_knot\n", text)
        self.assertIn("  9: overgrown\n", text)
        self.assertNotIn("test:", d.data_yaml("/x", val="images/train", test=None))


def _gruppen(seed: int = 3, anzahl: int = 300) -> dict[str, Counter]:
    """Künstliche Gruppen mit stark ungleichen Klassen wie bei Kodytek."""
    rng = random.Random(seed)
    gruppen = {}
    for i in range(anzahl):
        c = Counter({"_bilder": rng.randint(1, 70)})
        c[0] = rng.randint(0, 100)
        c[1] = rng.randint(0, 50)
        if rng.random() < 0.08:
            c[8] = rng.randint(1, 8)       # selten wie blue_stain
        if i < 5:
            c[9] = 2                       # sehr selten wie overgrown
        gruppen[str(1000 + i)] = c
    return gruppen


class TestAufteilen(unittest.TestCase):
    def test_jede_gruppe_genau_ein_teil_und_fest(self):
        gruppen = _gruppen()
        a = d.aufteilen(gruppen, seed=7)
        self.assertEqual(set(a), set(gruppen))
        self.assertTrue(set(a.values()) <= set(d.TEILE))
        self.assertEqual(a, d.aufteilen(gruppen, seed=7))
        self.assertNotEqual(a, d.aufteilen(gruppen, seed=8))

    def test_anteile_und_seltene_klassen(self):
        gruppen = _gruppen()
        a = d.aufteilen(gruppen, seed=7)
        summe = {t: Counter() for t in d.TEILE}
        for g, t in a.items():
            summe[t].update(gruppen[g])
        bilder = sum(s["_bilder"] for s in summe.values())
        for t, soll in zip(d.TEILE, d.ANTEILE, strict=True):
            self.assertAlmostEqual(summe[t]["_bilder"] / bilder, soll, delta=0.03)
            self.assertGreater(summe[t][8], 0, f"seltene Klasse fehlt in {t}")
        # 5 Gruppen mit der seltensten Klasse: zu wenige für drei Teile, train bekommt den größten Teil
        self.assertGreaterEqual(summe["train"][9], max(summe["val"][9], summe["test"][9]))


def _bild(pfad: Path, breite: int, hoehe: int = 1024) -> None:
    Image.new("RGB", (breite, hoehe), (200, 180, 140)).save(pfad)


class TestBauen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        wurzel = Path(self.tmp.name)
        self.boxen, self.bilder = wurzel / "boxen", wurzel / "bilder" / "Images1"
        self.boxen.mkdir()
        self.bilder.mkdir(parents=True)
        self.ziel = wurzel / "aus" / "kodytek-1"
        inhalt = {
            "100000001": "Live_Knot\t0.1\t0.1\t0.2\t0.3\r\n",
            "100000002": "",                                              # ohne Fehler
            "100100001": "Crack\t0,5\t0,5\t0,6\t0,9\r\nresin\t0.3\t0.3\t0.30035\t0.4\r\n",  # Komma, 1 px
            "100100002": "overgrown\t0.3\t0.3\t0.30035\t0.4\r\n",          # nur Klickfehler
            "100200001": "Blue_Stain\t0.2\t0.2\t0.4\t0.4\r\n",
        }
        for nummer, text in inhalt.items():
            (self.boxen / f"{nummer}_anno.txt").write_text(text, encoding="utf-8", newline="")
            _bild(self.bilder / f"{nummer}.bmp", 2799 if nummer == "100100001" else 2800, 64)
        _bild(self.bilder / "100000001_segm.bmp", 10, 10)                 # Maske, wird ignoriert
        self.aufteilung = wurzel / "aufteilung.json"
        self.aufteilung.write_text(json.dumps({"teile": {"train": ["1000"], "val": ["1001"], "test": ["1002"]}}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_bauen(self):
        bericht = d.bauen(self.boxen, self.bilder.parent, self.ziel, self.aufteilung, 2)
        z = self.ziel
        self.assertEqual(sorted(p.name for p in (z / "images" / "train").iterdir()),
                         ["100000001.bmp", "100000002.bmp"])
        self.assertEqual((z / "labels" / "train" / "100000002.txt").read_text(), "")
        self.assertTrue((z / "labels" / "train" / "100000001.txt").read_text().startswith("0 0.150000 0.200000"))
        self.assertEqual(len((z / "labels" / "val" / "100100001.txt").read_text().splitlines()), 1)
        self.assertFalse((z / "images" / "val" / "100100002.bmp").exists())
        self.assertEqual(bericht["weggelassen_alle_boxen_aussortiert"], ["100100002"])
        self.assertEqual(len(bericht["aussortiert"]), 2)
        self.assertEqual(bericht["dateien_mit_dezimalkomma"], 1)
        self.assertEqual(bericht["teile"]["train"]["ohne_fehler"], 1)
        self.assertEqual(bericht["teile"]["test"]["boxen"], {"blue_stain": 1})
        # Hardlink: dieselbe Datei, kein zusätzlicher Platz
        self.assertTrue((z / "images" / "test" / "100200001.bmp").samefile(self.bilder / "100200001.bmp"))
        yaml = (z / "data.yaml").read_text()
        self.assertIn(f"path: {z.resolve()}", yaml)
        manifest = json.loads((z / "manifest.json").read_text())
        self.assertEqual(len(manifest["md5_bilder"]), 4)
        self.assertTrue((z / "DATENKARTE.md").exists())

    def test_ziel_wird_nie_ueberschrieben(self):
        self.ziel.mkdir(parents=True)
        with self.assertRaises(FileExistsError):
            d.bauen(self.boxen, self.bilder.parent, self.ziel, self.aufteilung, 2)

    def test_fehlendes_bild_und_fehlende_gruppe(self):
        (self.bilder / "100000002.bmp").unlink()
        with self.assertRaises(FileNotFoundError):
            d.bauen(self.boxen, self.bilder.parent, self.ziel, self.aufteilung, 2)
        bericht = d.bauen(self.boxen, self.bilder.parent, self.ziel, self.aufteilung, 2, nur_vorhandene=True)
        self.assertEqual(bericht["fehlende_bilder"], 1)
        self.aufteilung.write_text(json.dumps({"teile": {"train": ["1000"], "val": [], "test": []}}))
        with self.assertRaises(ValueError):
            d.bauen(self.boxen, self.bilder.parent, self.ziel.parent / "b", self.aufteilung, 2,
                    nur_vorhandene=True)

    def test_probe_train_gleich_val(self):
        bericht = d.bauen(self.boxen, self.bilder.parent, self.ziel, self.aufteilung, 2, probe=2, mit_md5=False)
        self.assertEqual(bericht["teile"]["train"]["bilder"], 2)
        self.assertEqual(bericht["teile"]["train"]["ohne_fehler"], 0)
        self.assertIn("val: images/train", (self.ziel / "data.yaml").read_text())


class TestUeberlappung(unittest.TestCase):
    def test_echte_ueberlappung_wird_erkannt(self):
        import numpy as np
        rng = np.random.default_rng(0)
        brett = rng.normal(128, 20, (1600, 1000)).astype(np.float32)
        a, b = brett[:1024], brett[800:1600]        # 224 gemeinsame Zeilen
        fremd = rng.normal(128, 20, (1024, 1000)).astype(np.float32)
        echt = d.ueberlappung(a, b, rand=10)
        self.assertGreater(echt["a_ende_in_b"], 0.99)
        self.assertEqual(echt["zeile_in_b"], 1024 - 32 - 800)
        self.assertLess(d.ueberlappung(a, fremd, rand=10)["a_ende_in_b"], 0.3)


@unittest.skipUnless(PROBE_BILDER.is_dir() and PROBE_BOXEN.is_dir(), "Probedaten nur auf dem Server")
class TestProbedaten(unittest.TestCase):
    """Echte Box-Dateien und die 11 Probebilder unter data/ (nicht im Repo)."""

    def test_alle_box_dateien_lesbar(self):
        boxen, komma = d.alle_boxen_lesen(PROBE_BOXEN)
        self.assertEqual(len(boxen), 20276)
        self.assertEqual(sum(not b for b in boxen.values()), 1992)
        self.assertEqual(sum(map(len, boxen.values())), 43974)
        self.assertEqual(len(komma), 132)

    def test_eingefrorene_aufteilung_passt(self):
        boxen, _ = d.alle_boxen_lesen(PROBE_BOXEN)
        eingefroren = json.loads(AUFTEILUNG.read_text(encoding="utf-8"))
        neu = d.aufteilen(d.gruppen_zaehlen(boxen, eingefroren["min_px"]), seed=eingefroren["seed"])
        self.assertEqual({t: sorted(g for g, tt in neu.items() if tt == t) for t in d.TEILE},
                         eingefroren["teile"])

    def test_bauen_mit_probebildern(self):
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "kodytek-probe"
            bericht = d.bauen(PROBE_BOXEN, PROBE_BILDER, ziel, AUFTEILUNG, d.MIN_PX, nur_vorhandene=True,
                              mit_md5=False)
            self.assertEqual(sum(t["bilder"] for t in bericht["teile"].values()), 11)
            self.assertEqual(bericht["fehlende_bilder"], 20276 - 11)
            text = (ziel / "labels").rglob("100000061.txt")
            zeilen = next(text).read_text().splitlines()
            self.assertEqual(len(zeilen), 2)


if __name__ == "__main__":
    unittest.main()
