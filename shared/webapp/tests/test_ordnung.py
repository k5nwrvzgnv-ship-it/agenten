import shutil
import tempfile
import unittest
from pathlib import Path

import ordnung

UNTERRICHT = '''
[[reihe]]
fach = "Ethik"
klasse = "8"
titel = "Straftheorien (in Planung)"
behandelt = ["Kant"]
'''


class TestLaden(unittest.TestCase):
    def setUp(self):
        self.agenten = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.agenten)
        self.instanz = self.agenten / "instanz"
        self.instanz.mkdir()

    def schreiben(self, relativ: str, text: str) -> None:
        pfad = self.agenten / relativ
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(text, encoding="utf-8")

    def test_ohne_dateien_keine_reihen(self):
        self.assertEqual(ordnung.laden(self.instanz), ([], []))

    def test_ersatz_aus_dem_bestand(self):
        self.schreiben("unterricht/reihen.toml", UNTERRICHT)
        self.schreiben("examen/examen.toml", '[reihe]\ntitel_in_reihen_toml = "Straftheorien"\n')
        self.schreiben("theater/theater.toml", '[stueck]\ntitel = "Der nackte Wahnsinn"\n')
        reihen, fehler = ordnung.laden(self.instanz)
        self.assertEqual(fehler, [])
        self.assertEqual([(r["id"], r["fach"], r["gruppe"], r["agenten"]) for r in reihen], [
            ("ethik-8-straftheorien", "Ethik", "Klasse 8", ["examen"]),
            ("darstellendes-spiel-kurs-12-der-nackte-wahnsinn", "Darstellendes Spiel", "Kurs 12", ["theater"])])

    def test_fach_aus_dem_profil(self):
        self.schreiben("unterricht/reihen.toml", '[[reihe]]\nklasse = "7"\ntitel = "Glück"\n')
        self.schreiben("unterricht/profil.toml", 'fach = "Ethik"\n')
        reihen, _ = ordnung.laden(self.instanz)
        self.assertEqual(reihen[0]["id"], "ethik-7-glueck")

    def test_datei_der_instanz_hat_vorrang(self):
        self.schreiben("unterricht/reihen.toml", UNTERRICHT)
        self.schreiben("instanz/reihen.toml", '[[reihe]]\nid = "strafe"\nfach = "Ethik"\nklasse = "8"\n'
                                              'titel = "Strafe"\nstand = "abgeschlossen"\n')
        reihen, fehler = ordnung.laden(self.instanz)
        self.assertEqual(fehler, [])
        self.assertEqual([(r["id"], r["laufend"]) for r in reihen], [("strafe", False)])

    def test_kaputte_datei_meldet_und_zeigt_nichts(self):
        self.schreiben("unterricht/reihen.toml", "[[reihe]\n")
        reihen, fehler = ordnung.laden(self.instanz)
        self.assertEqual(reihen, [])
        self.assertIn("reihen.toml", fehler[0])
        self.schreiben("instanz/reihen.toml", 'reihe = "x"\n')
        self.assertEqual(ordnung.laden(self.instanz)[0], [])


if __name__ == "__main__":
    unittest.main()
