"""Streifenbild als Balken: Stücke, Zuschneiden der Umrisse, Vorlabel in Anteilen."""

import unittest

from aufnahme import kette as k
from aufnahme import streifen as st


class TestStreifen(unittest.TestCase):
    def test_stuecke_gleich_lang(self):
        s = st.stuecke(6485)
        self.assertEqual(len(s), 7)
        self.assertAlmostEqual(s[0][1] - s[0][0], 6485 / 7)
        self.assertEqual((s[0][0], s[-1][1]), (0, 6485))
        self.assertEqual(st.stuecke(1000), [(0.0, 1000.0)])
        self.assertEqual(len(st.stuecke(1000.5)), 2)

    def test_zuschneiden(self):
        quadrat = [[900, 10], [1100, 10], [1100, 20], [900, 20]]
        links = st.zuschneiden(quadrat, 0, 1000)
        self.assertEqual(sorted(map(tuple, links)), [(900, 10), (900, 20), (1000, 10), (1000, 20)])
        self.assertEqual(st.zuschneiden(quadrat, 1200, 2000), [])
        self.assertAlmostEqual(st.flaeche(st.zuschneiden(quadrat, 1000, 2000)), 1000)

    def test_vorlabels(self):
        funde = [{"klasse": "dead_knot", "konfidenz": 0.44123, "l_von": 990, "l_bis": 1010,
                  "umriss": [[990, 100], [1010, 100], [1010, 120], [990, 120]]},
                 {"klasse": "unbekannt", "konfidenz": 0.9, "l_von": 10, "l_bis": 20, "umriss": [[10, 1], [20, 1], [15, 9]]},
                 {"klasse": "crack", "konfidenz": 0.3, "l_von": 999.9, "l_bis": 1100,
                  "umriss": [[999.9, 1], [1100, 1], [1100, 1.1], [999.9, 1.1]]}]
        o = st.vorlabels(funde, 0, 1000, 200, k.KLASSEN, "kodytek-seg1-n1280")
        self.assertEqual(len(o), 1)                           # unbekannte Klasse und Splitter fallen weg
        self.assertEqual((o[0]["k"], o[0]["ok"], o[0]["c"], o[0]["q"]), (1, False, 0.4412, "kodytek-seg1-n1280"))
        self.assertEqual(max(p[0] for p in o[0]["p"]), 1.0)
        self.assertAlmostEqual(min(p[1] for p in o[0]["p"]), 0.5)
        k.objekte_pruefen(o)                                  # so speicherbar
        self.assertEqual(len(st.vorlabels(funde, 1000, 2000, 200, k.KLASSEN, "m")), 2)


if __name__ == "__main__":
    unittest.main()
