import unittest

import statistik


def a(kat, von, bis, erg=None, korr=(), auto="hoch", eingaben=("freitext",), belastung=False):
    return {"chat": "c", "von": von, "bis": bis, "kategorie": kat, "titel": f"{kat}{von}", "fach": "ethik",
            "runde_ergebnis": erg, "korrekturen": [{"runde": von, "art": x, "zitat": "z"} for x in korr],
            "ergebnis": "erreicht" if erg else "abgebrochen", "automatisierbar": auto,
            "eingaben": list(eingaben), "belastung": belastung}


AUFGABEN = [a("material", 1, 5, 4, ["niveau", "form"]), a("material", 6, 6, 6), a("material", 7, 9, None, ["niveau"]),
            a("verwaltung", 10, 11, 10, auto="mittel", eingaben=("bild", "freitext"), belastung=True)]


class JeKategorie(unittest.TestCase):
    def test_kennzahlen(self):
        s = statistik.je_kategorie(AUFGABEN)
        self.assertEqual(list(s), ["material", "verwaltung"])
        m = s["material"]
        self.assertEqual((m["aufgaben"], m["runden_summe"], m["runden_median"]), (3, 9, 3))
        self.assertEqual(m["bis_ergebnis_median"], 2.5)  # 4 und 1
        self.assertEqual((m["korrekturen_summe"], m["mit_korrektur"]), (3, 2))
        self.assertEqual(m["korrekturarten"], {"niveau": 2, "form": 1})
        self.assertEqual(m["ergebnis"], {"erreicht": 2, "abgebrochen": 1})
        self.assertEqual(s["verwaltung"]["eingaben"], {"bild": 1, "freitext": 1})
        self.assertEqual(s["verwaltung"]["belastung"], 1)

    def test_runde_ergebnis_ausserhalb(self):
        self.assertIsNone(statistik.bis_ergebnis(a("x", 5, 6, 9)))


class Korrekturen(unittest.TestCase):
    def test_flach(self):
        k = statistik.korrekturen(AUFGABEN)
        self.assertEqual(len(k), 3)
        self.assertEqual(k[0], {"chat": "c", "runde": 1, "art": "niveau", "zitat": "z", "kategorie": "material",
                                "aufgabe": "material1"})
