import unittest

import buch


def text(seiten: dict[int, list[str]]) -> str:
    return "".join(f"--- Seite {p}\n" + "".join(z + "\n" for z in zeilen) for p, zeilen in seiten.items())


TEXT = text({
    1: ["Titel"],
    12: ["Sequenz 8 Slow Motion", "l>ii§i!§li!.I.j", "~", "Übung 4 Aufstehen   in Slow Motion"],
    13: ["Weiter geht es mit Freeze."],
    14: ["Kapitel 9"],
})


class Auszug(unittest.TestCase):
    def test_gedruckte_seiten_und_versatz(self):
        teile = buch.auszug(TEXT, [[10, 11]], 2, "Kündiger")
        self.assertEqual(len(teile), 1)
        self.assertIn("--- Buch S. 10\nSequenz 8 Slow Motion\nÜbung 4 Aufstehen in Slow Motion\n--- Buch S. 11\n"
                      "Weiter geht es mit Freeze.", teile[0])
        self.assertNotIn("Kapitel 9", teile[0])
        self.assertTrue(teile[0].startswith("# Auszug: Kündiger"))

    def test_zeichensalat_faellt_weg(self):
        self.assertNotIn("§", buch.auszug(TEXT, [[10, 10]], 2, "K")[0])
        self.assertFalse(buch.lesbar("l>ii§i!§li!.I.j"))
        self.assertFalse(buch.lesbar("~"))
        self.assertTrue(buch.lesbar("-+ Bildet einen Kreis."))

    def test_teile_an_seitengrenzen(self):
        teile = buch.auszug(TEXT, [[10, 11]], 2, "K", max_zeichen=80)
        self.assertEqual(len(teile), 2)
        self.assertIn("--- Buch S. 10", teile[0])
        self.assertTrue(teile[1].startswith("# Auszug (Fortsetzung): K\n--- Buch S. 11"))

    def test_fehlende_seite(self):
        with self.assertRaisesRegex(buch.BuchFehler, "Seite 20 \\(PDF 22\\) fehlt"):
            buch.auszug(TEXT, [[20, 20]], 2, "K")

    def test_falscher_bereich(self):
        with self.assertRaises(buch.BuchFehler):
            buch.auszug(TEXT, [[11, 10]], 2, "K")


if __name__ == "__main__":
    unittest.main()
