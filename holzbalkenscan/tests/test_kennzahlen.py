"""Kennzahlen aus den Berichten: echter Bericht ISO 800 und eine nach dem Code gebaute Vorprüfung."""

import unittest
from pathlib import Path

import kennzahlen

BEISPIELE = Path(__file__).parent / "beispiele"


class TestZusammenbau(unittest.TestCase):
    def setUp(self):
        self.k = kennzahlen.aus_zusammenbau((BEISPIELE / "zusammenbau_iso800.txt").read_text(encoding="utf-8"))

    def test_massstab_und_naehte(self):
        self.assertEqual(self.k["px_mm_band"], 8.90)
        self.assertEqual((self.k["px_mm_min"], self.k["px_mm_max"]), (8.35, 9.79))
        self.assertEqual(self.k["naehte"], 25)
        self.assertEqual(self.k["nahtversatz_median_mm"], 0.09)
        self.assertEqual(self.k["nahtversatz_max_mm"], 0.33)

    def test_laenge_und_drift(self):
        self.assertEqual(self.k["laenge_roh_mm"], 6212)
        self.assertEqual(self.k["laengsabweichung_mm"], -273)
        self.assertEqual(self.k["laengsabweichung_prozent"], -4.21)
        self.assertEqual(self.k["einpassfaktor"], 1.0439)
        self.assertEqual(self.k["kante_streuung_mm"], 1.52)
        self.assertEqual(self.k["kante_langwellig_mm"], 4.20)
        self.assertEqual(self.k["kante_gefunden_prozent"], 85)

    def test_letzte_fundstelle_gilt(self):
        self.assertEqual(self.k["punktpaar_rest_median_mm"], 0.306)

    def test_naht_zeit_belegung(self):
        self.assertEqual(self.k["nahtkanten"], 59)
        self.assertEqual(self.k["nahtkante_staerke"], 36)
        self.assertEqual(self.k["belegt_prozent"], 100.0)
        self.assertEqual(self.k["rechenzeit_s"], 33)

    def test_pruefbericht_und_verbindung(self):
        self.assertEqual(len(self.k["pruefbericht"]), 14)
        self.assertEqual(self.k["pruefbericht"][-1], "59 sichtbare Nahtkanten")
        self.assertEqual(self.k["ohne_verbindung"], [])

    def test_abgehaengte_aufnahmen(self):
        k = kennzahlen.aus_zusammenbau("  ACHTUNG  ohne Verbindung zur Reihe: IMG_1.jpg, IMG_7.jpg\n")
        self.assertEqual(k["ohne_verbindung"], ["IMG_1.jpg", "IMG_7.jpg"])

    def test_keine_beanstandung(self):
        k = kennzahlen.aus_zusammenbau("Pruefbericht\n------------\n  Keine Beanstandung.\n\nErgebnis: 1 x 1 Px\n")
        self.assertEqual(k["pruefbericht"], [])

    def test_abgebrochener_lauf_gibt_none(self):
        k = kennzahlen.aus_zusammenbau("Kanten\n  Traceback ...\n")
        self.assertIsNone(k["nahtversatz_median_mm"])
        self.assertIsNone(k["pruefbericht"])
        self.assertIsNone(k["rechenzeit_s"])

    def test_negative_und_positive_abweichung(self):
        k = kennzahlen.aus_zusammenbau("Balken im Streifen: 6500 mm, Aufmass 6485 mm -> +15 mm = +0.23 %\n")
        self.assertEqual(k["laengsabweichung_mm"], 15)
        self.assertEqual(k["laengsabweichung_prozent"], 0.23)


class TestVorpruefung(unittest.TestCase):
    def setUp(self):
        self.k = kennzahlen.aus_vorpruefung((BEISPIELE / "vorpruefung_gebaut.txt").read_text(encoding="utf-8"))

    def test_urteil(self):
        self.assertEqual(self.k["masstreue"], "GELB")
        self.assertEqual(self.k["farbtreue"], "ROT")

    def test_zahlen(self):
        self.assertEqual(self.k["aufnahmen"], 26)
        self.assertEqual(self.k["aufloesung_px_mm"], 8.90)
        self.assertEqual(self.k["ueberlappung_median_prozent"], 61.2)
        self.assertEqual(self.k["ueberlappung_min_prozent"], 42.0)
        self.assertEqual(self.k["rechenzeit_s"], 21.4)

    def test_maengel(self):
        self.assertEqual(self.k["maengel"], ["ROT: Weissabgleich nicht fest (Farbe)",
                                             "gelb: Handy nicht parallel zum Bauteil (Mass)"])

    def test_leer(self):
        k = kennzahlen.aus_vorpruefung("")
        self.assertIsNone(k["masstreue"])
        self.assertEqual(k["maengel"], [])


if __name__ == "__main__":
    unittest.main()
