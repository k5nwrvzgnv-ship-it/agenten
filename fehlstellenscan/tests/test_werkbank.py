"""Tests für werkbank.py: Rechteck und Maske aus YOLO-seg, Objekte aus Dateien."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

import masken as m
import werkbank as w


def quadrat(x, y, seite):
    return np.array([[x, y], [x + seite, y], [x + seite, y + seite], [x, y + seite]], dtype=np.float64)


class TestRechteckUndMaske(unittest.TestCase):
    def test_quadrat(self):
        rechteck, maske = w.rechteck_und_maske(quadrat(100, 50, 40), 400, 200)
        self.assertEqual(maske.shape, (41, 41))
        self.assertTrue(maske.all())
        self.assertAlmostEqual(rechteck[0], 0.25)
        self.assertAlmostEqual(rechteck[1], 0.25)
        self.assertAlmostEqual(rechteck[2], 41 / 400)

    def test_dreieck_halb_gefuellt(self):
        _, maske = w.rechteck_und_maske(np.array([[0, 0], [100, 0], [0, 100]], dtype=float), 200, 200)
        self.assertAlmostEqual(maske.mean(), 0.5, delta=0.03)

    def test_am_bildrand_abgeschnitten(self):
        rechteck, maske = w.rechteck_und_maske(quadrat(390, 190, 10), 400, 200)
        self.assertLessEqual(rechteck[0] + rechteck[2], 1.0)
        self.assertLessEqual(rechteck[1] + rechteck[3], 1.0)
        self.assertEqual(maske.shape, (10, 10))


class TestObjekte(unittest.TestCase):
    def test_label_und_vorhersage(self):
        zeile = m.zu_yolo_seg(1, quadrat(100, 100, 200), 2800, 1024)
        mark = w.objekte(zeile + "\n", 2800, 1024, vorhersage=False)
        vor = w.objekte(zeile + " 0.7\n", 2800, 1024, vorhersage=True)
        self.assertEqual(mark[0]["name"], "Ast tot")
        self.assertEqual(mark[0]["klasse"], "dead_knot")
        self.assertIsNone(mark[0]["konfidenz"])
        self.assertTrue(mark[0]["ast"])
        self.assertEqual(vor[0]["konfidenz"], 0.7)
        # 200 px quer = 12,0 mm, 200 px längs = 30,0 mm
        self.assertAlmostEqual(mark[0]["kurz_mm"], 12.0, delta=0.5)
        self.assertEqual(mark[0]["groesse"], "10-20")

    def test_fehlende_datei_leer(self):
        self.assertEqual(w.datei_objekte(Path("/gibt/es/nicht.txt"), 10, 10, True), [])
        self.assertEqual(w.datei_objekte(None, 10, 10, True), [])

    def test_bilder_finden(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n in ("b.BMP", "a.jpg", "c.txt"):
                Path(tmp, n).write_text("")
            self.assertEqual([p.name for p in w.bilder_finden(Path(tmp))], ["a.jpg", "b.BMP"])


if __name__ == "__main__":
    unittest.main()
