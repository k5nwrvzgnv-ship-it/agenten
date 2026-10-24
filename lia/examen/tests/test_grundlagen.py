import tempfile
import unittest
from pathlib import Path

import grundlagen
import wortlaut

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
    def test_trennung_und_umbruch_zaehlen_nicht(self):
        self.assertTrue(wortlaut.steht_in("Um diese Fragen beantworten zu können", TEXTFASSUNG))
        self.assertTrue(wortlaut.steht_in("Faustrecht, Gewaltmonopol (Straf- und Strafrechtstheorien)", TEXTFASSUNG))

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


class AuszugTest(unittest.TestCase):
    def stelle(self, text, seite):
        return {"id": "x", "seite": seite, "abschnitt": "a", "text": text}

    def test_belegt(self):
        self.assertEqual(grundlagen.auszug_pruefen([self.stelle("eine gerechte Strafe?", 2)], TEXTFASSUNG), [])

    def test_falsche_seite(self):
        fehler = grundlagen.auszug_pruefen([self.stelle("eine gerechte Strafe?", 3)], TEXTFASSUNG)
        self.assertEqual(fehler, ["x: steht nicht auf Seite 3, sondern auf [2]"])

    def test_nicht_gefunden(self):
        fehler = grundlagen.auszug_pruefen([self.stelle("Strafe muss sein.", 2)], TEXTFASSUNG)
        self.assertEqual(fehler, ["x: nicht wörtlich im RLP gefunden"])


class LadenTest(unittest.TestCase):
    def datei(self, inhalt):
        ordner = tempfile.TemporaryDirectory()
        self.addCleanup(ordner.cleanup)
        pfad = Path(ordner.name) / "d.toml"
        pfad.write_text(inhalt, encoding="utf-8")
        return pfad

    RUBRIK = """
[stufen]
liste = ["schwach", "gut"]
mindestens = "gut"
[[kriterium]]
id = "a"
name = "A"
frage = "?"
gut = "so"
quelle = "Seminar"
"""

    def test_rubrik_gut(self):
        self.assertEqual(len(grundlagen.rubrik_laden(self.datei(self.RUBRIK))["kriterium"]), 1)

    def test_rubrik_fehler(self):
        faelle = {
            "mindestens": self.RUBRIK.replace('mindestens = "gut"', 'mindestens = "top"'),
            "quelle fehlt": self.RUBRIK.replace('quelle = "Seminar"', ""),
            "unbekannte": self.RUBRIK + 'farbe = "rot"\n',
            "doppelte": self.RUBRIK + "[[kriterium]]" + self.RUBRIK.split("[[kriterium]]")[1],
            "kein gültiges TOML": "[stufen",
        }
        for erwartet, inhalt in faelle.items():
            with self.subTest(erwartet), self.assertRaisesRegex(grundlagen.GrundlagenFehler, erwartet):
                grundlagen.rubrik_laden(self.datei(inhalt))

    def test_auszug_seite_muss_zahl_sein(self):
        inhalt = '[[stelle]]\nid = "a"\nseite = "24"\nabschnitt = "x"\ntext = "y"\n'
        with self.assertRaisesRegex(grundlagen.GrundlagenFehler, "Zahl"):
            grundlagen.auszug_laden(self.datei(inhalt))

    def test_offene_angaben(self):
        daten = {"a": "", "b": "x", "c": {"d": "", "e": [], "f": ["y"]}}
        self.assertEqual(grundlagen.offene_angaben(daten), ["a", "c.d", "c.e"])


class EchteDateienTest(unittest.TestCase):
    """Die Dateien im Repo müssen immer laden; der Wortlaut nur, wenn das PDF da ist (data/ ist nicht im Repo)."""

    def test_rubrik_und_auszug_laden(self):
        self.assertGreaterEqual(len(grundlagen.rubrik_laden()["kriterium"]), 12)
        self.assertGreaterEqual(len(grundlagen.auszug_laden()), 10)
        grundlagen.offene_angaben(grundlagen._toml(grundlagen.EXAMEN))

    @unittest.skipUnless(grundlagen.RLP_PDF.exists(), "RLP-PDF nicht vorhanden")
    def test_rlp_wortlaut(self):
        from agentkit import textfassung
        self.assertEqual(grundlagen.auszug_pruefen(grundlagen.auszug_laden(), textfassung.als_text(grundlagen.RLP_PDF)), [])


if __name__ == "__main__":
    unittest.main()
