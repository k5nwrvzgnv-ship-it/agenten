import unittest

from agentkit import wortlaut

TEXTFASSUNG = """--- Seite 1
Inhalt
--- Seite 2
Wer Regeln und Gesetze nicht einhält oder verletzt, dem droht eine Strafe. Doch was ist
eine gerechte Strafe? Um diese Fragen beantwor-
ten zu können ...
--- Seite 3
Begriffe: Rache, Faust-
recht, Gewaltmonopol (Straf- und Straf-
rechtstheorien) etc.
"""


class WortlautTest(unittest.TestCase):
    def test_silbentrennung_am_zeilenende(self):
        self.assertTrue(wortlaut.steht_in("Um diese Fragen beantworten zu können", TEXTFASSUNG))
        self.assertTrue(wortlaut.steht_in("Faustrecht, Gewaltmonopol (Straf- und Strafrechtstheorien)", TEXTFASSUNG))
        self.assertEqual(wortlaut.normalisieren("verschie-\n  denen"), "verschiedenen")

    def test_bindestrich_im_satz_bleibt(self):
        self.assertTrue(wortlaut.steht_in("Straf- und", TEXTFASSUNG))
        self.assertFalse(wortlaut.steht_in("Strafund", "Straf- und"))

    def test_ein_anderes_wort_faellt_auf(self):
        self.assertFalse(wortlaut.steht_in("Doch was ist eine gerechte Rache?", TEXTFASSUNG))
        self.assertFalse(wortlaut.steht_in("Um diese Frage beantworten", TEXTFASSUNG))

    def test_typografische_zeichen_gleich(self):
        self.assertTrue(wortlaut.steht_in("„Strafe“ – ja", 'Die "Strafe" - ja'))
        self.assertTrue(wortlaut.steht_in("Aufzählung", "­ Aufzählung"))

    def test_leeres_zitat_nie(self):
        self.assertFalse(wortlaut.steht_in("  \n", TEXTFASSUNG))

    def test_seiten(self):
        seiten = wortlaut.seiten(TEXTFASSUNG)
        self.assertEqual(sorted(seiten), [1, 2, 3])
        self.assertIn("Faust-", seiten[3])


if __name__ == "__main__":
    unittest.main()
