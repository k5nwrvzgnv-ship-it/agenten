"""Vorlabel mit Claude (claudelabel.py): Antwort prüfen, Umrisse aus Kästchen, Bild mit Lineal. Ohne Claude."""

import unittest

import cv2
import numpy as np
from PIL import Image

import claudelabel as cl
from aufnahme import klassen as kl


def bild(w=400, h=300, hell=200):
    return np.full((h, w, 3), hell, np.uint8)


class TestClaudelabel(unittest.TestCase):
    def setUp(self):
        self.d = kl.standard()
        kl.gruppenklassen(self.d)

    def test_prompt_nur_aktive_klassen(self):
        kl.weg(self.d, 15, 12, 0)                             # Insektenfraß gelöscht
        p = cl.prompt([{"name": "F1", "datei": "/x/F1.jpg", "breite_mm": 280, "hoehe_mm": 300, "holz": "Kiefer"}],
                      self.d)
        self.assertIn("- abplatzung:", p)
        self.assertIn("- riss_klebefuge:", p)
        self.assertNotIn("- insektenfrass:", p)
        self.assertIn("F1: Datei /x/F1.jpg", p)

    def test_antwort_lesen(self):
        text = ('Hier: {"fotos": {"F1": [{"k": "nagelloch", "box": [52, 10, 50, 12], "s": 1.4},'
                '{"k": "gibtsnicht", "box": [1, 1, 2, 2]}, {"k": "crack", "box": [5, 5, 5, 9]},'
                '{"k": "crack", "box": [-3, 0, 4, 120]}], "F9": [], "F2": []}}')
        a = cl.antwort_lesen(text, ["F1", "F2"], self.d)
        self.assertEqual(set(a), {"F1", "F2"})
        self.assertEqual(a["F1"][0], {"k": "nagelloch", "box": [50, 10, 52, 12], "s": 1.0})
        self.assertEqual(a["F1"][1]["box"], [0.0, 0.0, 4.0, 100.0])
        self.assertEqual(len(a["F1"]), 2)
        with self.assertRaises(ValueError):
            cl.antwort_lesen("keine Ahnung", ["F1"], self.d)

    def test_loch_findet_dunklen_fleck(self):
        b = bild()
        cv2.circle(b, (200, 150), 6, (20, 20, 20), -1)
        p, wie = cl.umriss(b, "nagelloch", [46, 45, 54, 55])     # Kästchen etwas zu groß
        self.assertEqual(wie, "loch")
        xs, ys = [q[0] for q in p], [q[1] for q in p]
        self.assertTrue(192 <= min(xs) and max(xs) <= 208 and 142 <= min(ys) and max(ys) <= 158)

    def test_riss_folgt_schraeger_linie(self):
        b = bild()
        cv2.line(b, (150, 20), (190, 280), (10, 10, 10), 2)
        p, wie = cl.umriss(b, "crack", [30, 0, 60, 100])
        self.assertEqual(wie, "riss")
        maske = np.zeros((300, 400), np.uint8)
        cv2.fillPoly(maske, [np.array(p, np.int32)], 1)
        self.assertEqual(maske[150, 170], 1)                    # Mitte der Linie liegt drin
        self.assertLess(maske.sum(), 30 * 300)                  # schmales Band, nicht das Kästchen

    def test_leeres_kaestchen_gibt_ellipse(self):
        p, wie = cl.umriss(bild(), "nagelloch", [10, 10, 20, 20])
        self.assertEqual(wie, "ellipse")
        self.assertEqual(len(p), 24)

    def test_objekte_in_anteilen(self):
        b = bild()
        cv2.circle(b, (100, 100), 8, (20, 20, 20), -1)
        o = cl.objekte(b, [{"k": "nagelloch", "box": [22, 30, 28, 37], "s": 0.8},
                           {"k": "metall_fremd", "box": [1, 1, 2, 2], "s": 0.5}], {"nagelloch": 12}, "claude")
        self.assertEqual(len(o), 1)
        self.assertEqual((o[0]["k"], o[0]["ok"], o[0]["c"], o[0]["q"]), (12, False, 0.8, "claude"))
        self.assertTrue(all(0 <= x <= 1 and 0 <= y <= 1 for x, y in o[0]["p"]))

    def test_lineal_und_kontrolle(self):
        g = cl.mit_lineal(Image.new("RGB", (300, 200), "gray"))
        self.assertEqual(g.size, (300 + 2 * cl.RAND, 200 + 2 * cl.RAND))
        k = cl.kontrolle(Image.new("RGB", (300, 200)), [{"k": 4, "p": [[0.1, 0.1], [0.5, 0.1], [0.3, 0.6]],
                                                         "c": 0.7}], {4: "Riss"})
        self.assertEqual(k.size, (300, 200))


if __name__ == "__main__":
    unittest.main()
