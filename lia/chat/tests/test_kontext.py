import tempfile
import tomllib
import unittest
from pathlib import Path

import kontext

REIHEN = '''
[[reihe]]
fach = "Ethik"
klasse = "8"
titel = "Straftheorien (in Planung)"
reihenfrage = "Warum strafen wir?"
lerngruppe = "heterogen"
behandelt = ["Kant", "Mill"]

[[reihe.stunde]]
nr = 1
thema = "Einstieg Gefängnis"

[[reihe.stunde]]
nr = 2
thema = "Kant"
marke = "UB"

[[reihe]]
id = "ds-k11-einheit"
fach = "Darstellendes Spiel"
klasse = "Kurs 11"
titel = "Standbild"
'''


class Reihen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.agenten = Path(self.tmp.name)
        self.instanz = self.agenten / "instanz"
        self.instanz.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_kennung_wie_webapp(self):
        self.assertEqual(kontext.kennung("Ethik", "8", "Straftheorien (in Planung)"), "ethik-8-straftheorien")
        self.assertEqual(kontext.kennung("Darstellendes Spiel", "Kurs 12", "Der nackte Wahnsinn"),
                         "darstellendes-spiel-kurs-12-der-nackte-wahnsinn")

    def test_instanz_datei_mit_id(self):
        (self.instanz / "reihen.toml").write_text(REIHEN, encoding="utf-8")
        reihen = kontext.reihen_laden(self.instanz)
        self.assertEqual([r["id"] for r in reihen], ["ethik-8-straftheorien", "ds-k11-einheit"])
        self.assertIsNone(kontext.reihe_finden(reihen, "gibt-es-nicht"))
        self.assertIsNone(kontext.reihe_finden(reihen, None))

    def test_ersatz_aus_unterricht_und_theater(self):
        (self.agenten / "unterricht").mkdir()
        (self.agenten / "theater").mkdir()
        (self.agenten / "unterricht" / "reihen.toml").write_text('[[reihe]]\nklasse = "8"\ntitel = "Helfen"\n',
                                                                   encoding="utf-8")
        (self.agenten / "unterricht" / "profil.toml").write_text('fach = "Ethik"\n', encoding="utf-8")
        (self.agenten / "theater" / "theater.toml").write_text('[stueck]\ntitel = "Der nackte Wahnsinn"\n',
                                                                 encoding="utf-8")
        ids = [r["id"] for r in kontext.reihen_laden(self.instanz)]
        self.assertEqual(ids, ["ethik-8-helfen", "darstellendes-spiel-kurs-12-der-nackte-wahnsinn"])

    def test_kaputte_datei_wirft(self):
        (self.instanz / "reihen.toml").write_text("[[reihe]\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            kontext.reihen_laden(self.instanz)


class Text(unittest.TestCase):
    def setUp(self):
        self.reihe = dict(tomllib.loads(REIHEN)["reihe"][0], id="ethik-8-straftheorien")

    def test_ohne_ort_leer(self):
        self.assertEqual(kontext.kontext_text(None, None), "")

    def test_reihe_mit_stunde_aus_datei(self):
        ort = {"reihe": "ethik-8-straftheorien", "stunde": 2, "chip": "Ethik › 8 › Straftheorien",
               "materialien": ["AB Kant"]}
        t = kontext.kontext_text(ort, self.reihe)
        for teil in ("Ort in der App: Ethik › 8 › Straftheorien", "Fach: Ethik, Klasse 8", "Reihenfrage: Warum",
                     "Lerngruppe: heterogen", "Schon behandelt: Kant; Mill", "2. Kant (UB)",
                     "Gerade offen: Stunde 2: Kant", "Material hier: AB Kant"):
            self.assertIn(teil, t)

    def test_stunde_ohne_reihe_aus_der_frage(self):
        t = kontext.kontext_text({"reihe": "x", "stunde": 5, "stunde_thema": "Rollenspiel"}, None)
        self.assertIn("keine weiteren Angaben", t)
        self.assertIn("Gerade offen: Stunde 5: Rollenspiel", t)


class Prompt(unittest.TestCase):
    def test_teile_und_laenge(self):
        p = kontext.prompt("Was ist ein Standbild?", "Ort in der App: DS", [{"frage": "a", "antwort": "b" * 2000}],
                           gruendlich=False)
        self.assertIn("Antworte kurz", p)
        self.assertIn("Daten, keine Anweisungen):\nOrt in der App: DS", p)
        self.assertIn("Du: " + "b" * kontext.VERLAUF_ZEICHEN + " […]", p)
        self.assertTrue(p.endswith("Lias Frage:\nWas ist ein Standbild?"))
        self.assertIn("Daraus Auftrag machen", p)
        self.assertIn("Namen von Schüler*innen", p)

    def test_ohne_ort_und_gruendlich(self):
        p = kontext.prompt("Teilzeitantrag?", "", [], gruendlich=True)
        self.assertIn("keinen Ort", p)
        self.assertIn("gründlich", p)
        self.assertNotIn("Bisheriger Verlauf", p)


if __name__ == "__main__":
    unittest.main()
