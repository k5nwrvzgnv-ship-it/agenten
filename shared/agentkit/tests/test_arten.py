import tempfile
import tomllib
import unittest
from pathlib import Path

from agentkit import arten

GUT = """
[[art]]
kennung = "praesentation"
name = "Präsentation"
beschreibung = "Folien"
agent = "dokumente"
aktiv = true
ausgabe = ["pptx", "pdf"]
ansicht = ""
[[art.feld]]
name = "Thema"
art = "zeile"
pflicht = true
[[art.feld]]
name = "Umfang"
art = "auswahl"
werte = ["5 Folien", "10 Folien"]
[[art.feld]]
name = "Seiten"
art = "zahl"
[[art.feld]]
name = "Hinweise"
art = "text"
"""


class TestArten(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.agenten = Path(self._tmp.name)
        (self.agenten / "dokumente").mkdir()
        (self.agenten / "dokumente" / "agent.py").write_text("")

    def fehler(self, text):
        return arten.pruefen(tomllib.loads(text), self.agenten)

    def test_echte_datei_ist_gueltig(self):
        alle = arten.laden()  # shared/arbeitsplatz/arten.toml mit den echten Agenten
        self.assertEqual(len({a["kennung"] for a in alle}), len(alle))
        self.assertIn("recherche", [a["kennung"] for a in arten.aktive(alle)])
        pruefung = arten.finden(alle, "pruefung")
        self.assertEqual((pruefung["material_oder"], pruefung["rueckmeldung"]), ("Transkript", False))

    def test_gut(self):
        self.assertEqual(self.fehler(GUT), [])
        datei = self.agenten / "arten.toml"
        datei.write_text(GUT, encoding="utf-8")
        art = arten.finden(arten.laden(datei, self.agenten), "praesentation")
        self.assertEqual((art["material"], art["feld"][1]["pflicht"]), ("optional", False))

    def test_fehler(self):
        faelle = {
            "kennung doppelt": GUT + GUT.split("[[art.feld]]")[0],
            "Agent fehlt": GUT.replace('agent = "dokumente"', 'agent = "uni"'),
            "Pflicht fehlt": GUT.replace('name = "Präsentation"\n', ""),
            "aktiv kein bool": GUT.replace("aktiv = true", 'aktiv = "ja"'),
            "falsche Feldart": GUT.replace('art = "zahl"', 'art = "datum"'),
            "auswahl ohne werte": GUT.replace('werte = ["5 Folien", "10 Folien"]', ""),
            "werte ohne auswahl": GUT.replace('art = "zahl"', 'art = "zahl"\nwerte = ["1"]'),
            "Tippfehler": GUT.replace("pflicht = true", "plicht = true"),
            "Feldname doppelt": GUT.replace('name = "Seiten"', 'name = "Thema"'),
            "Ausgabe": GUT.replace('"pptx", "pdf"', '"exe"'),
            "Kennung": GUT.replace('kennung = "praesentation"', 'kennung = "Präsentation"'),
            "leer": "",
        }
        for name, text in faelle.items():
            with self.subTest(name):
                self.assertTrue(self.fehler(text))
        datei = self.agenten / "arten.toml"
        datei.write_text(faelle["Agent fehlt"], encoding="utf-8")
        with self.assertRaises(arten.ArtFehler):
            arten.laden(datei, self.agenten)

    def test_material_oder_und_rueckmeldung(self):
        text = GUT.replace('ansicht = ""', 'ansicht = ""\nmaterial_oder = "Hinweise"\nrueckmeldung = false')
        self.assertEqual(self.fehler(text), [])
        datei = self.agenten / "arten.toml"
        datei.write_text(text, encoding="utf-8")
        art = arten.laden(datei, self.agenten)[0]
        self.assertFalse(art["rueckmeldung"])
        self.assertEqual(arten.material_fehler(art, {"Hinweise": ""}, 0), ["Hinweise: bitte ausfüllen oder eine Datei anhängen"])
        self.assertEqual(arten.material_fehler(art, {"Hinweise": "x"}, 0), [])
        self.assertEqual(arten.material_fehler(art, {"Hinweise": ""}, 1), [])
        self.assertTrue(self.fehler(GUT.replace('ansicht = ""', 'ansicht = ""\nmaterial_oder = "Gibt es nicht"')))
        self.assertTrue(self.fehler(GUT.replace('ansicht = ""', 'ansicht = ""\nmaterial = "pflicht"\nmaterial_oder = "Thema"')))
        self.assertTrue(self.fehler(GUT.replace('ansicht = ""', 'ansicht = ""\nrueckmeldung = "nein"')))
        standard = arten.laden(self.schreibe(GUT), self.agenten)[0]
        self.assertTrue(standard["rueckmeldung"])
        self.assertEqual(arten.material_fehler({**standard, "material": "pflicht"}, {}, 0),
                         ["Material: bitte mindestens eine Datei anhängen"])

    def schreibe(self, text):
        datei = self.agenten / "arten2.toml"
        datei.write_text(text, encoding="utf-8")
        return datei

    def test_formular(self):
        datei = self.agenten / "arten.toml"
        datei.write_text(GUT, encoding="utf-8")
        art = arten.laden(datei, self.agenten)[0]
        werte = arten.formular_pruefen(art, {"Thema": "  Holz\n schutz ", "Umfang": "5 Folien", "Seiten": "3,5",
                                             "Hinweise": "a\r\nb", "Fremd": "x"})
        self.assertEqual(werte, {"Thema": "Holz schutz", "Umfang": "5 Folien", "Seiten": "3,5", "Hinweise": "a\nb"})
        self.assertEqual(arten.auftragstext(art, werte),
                         "Art: Präsentation\nThema: Holz schutz\nUmfang: 5 Folien\nSeiten: 3,5\nHinweise: a\n  b")
        with self.assertRaises(arten.ArtFehler) as f:
            arten.formular_pruefen(art, {"Umfang": "7 Folien", "Seiten": "drei"})
        self.assertIn("Thema: bitte ausfüllen", str(f.exception))
        self.assertIn("Umfang: bitte aus der Liste wählen", str(f.exception))
        self.assertIn("Seiten: bitte eine Zahl", str(f.exception))


if __name__ == "__main__":
    unittest.main()
