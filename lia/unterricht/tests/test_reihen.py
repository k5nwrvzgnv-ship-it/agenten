import tempfile
import unittest
from pathlib import Path

import reihen

HIER = Path(__file__).resolve().parent.parent

GUT = """
[[reihe]]
klasse = 8
titel = "Helfen"
reihenfrage = "Muss ich Fremden genauso helfen wie meiner Familie?"
lerngruppe = "lernschwach, mehrsprachig"
behandelt = ["Singer", "Aristoteles"]
merksaetze = ["Merksatz eins.", "Merksatz zwei."]
notizen = "Nächste Stunde Fallbeispiel"

[[reihe]]
fach = "Darstellendes Spiel"
klasse = "11"
reihenfrage = "Wie entsteht eine Figur?"
"""


class ReihenTest(unittest.TestCase):
    def datei(self, text: str) -> Path:
        pfad = Path(tempfile.mkdtemp()) / "reihen.toml"
        pfad.write_text(text, encoding="utf-8")
        return pfad

    def test_mitgelieferte_datei_ist_gueltig(self):
        reihen.laden(HIER / "reihen.toml")

    def test_ohne_datei_und_leer(self):
        self.assertEqual(reihen.laden(Path(tempfile.mkdtemp()) / "fehlt.toml"), [])
        self.assertEqual(reihen.laden(self.datei("# nur Kommentare\n")), [])
        self.assertEqual(reihen.prompt_reihen([], "Ethik"), "")

    def test_laden_und_prompt(self):
        r = reihen.laden(self.datei(GUT))
        self.assertEqual(len(r), 2)
        text = reihen.prompt_reihen(r, "Ethik")
        self.assertTrue(text.startswith("## Lias laufende Reihen\n"))
        self.assertIn("### Ethik, Klasse 8: Helfen\n- Reihenfrage: Muss ich Fremden", text)
        self.assertIn("- Lerngruppe: lernschwach, mehrsprachig", text)
        self.assertIn("- Schon behandelt: Singer; Aristoteles", text)
        self.assertIn("- Merksätze der Reihe:\n  - Merksatz eins.\n  - Merksatz zwei.", text)
        self.assertIn("- Notizen: Nächste Stunde Fallbeispiel", text)
        self.assertIn("### Darstellendes Spiel, Klasse 11\n- Reihenfrage: Wie entsteht eine Figur?\n\n", text)
        self.assertNotIn("Lerngruppe", text.split("### Darstellendes Spiel")[1])

    def test_fehler(self):
        faelle = {
            "[[reihe]\nklasse = 8": "kein gültiges TOML",
            "[reihe]\nklasse = 8\nreihenfrage = 'x'": "[[reihe]]",
            "klasse = 8": "unbekannte Einträge",
            "[[reihe]]\nklasse = 8": "reihenfrage fehlt",
            "[[reihe]]\nklasse = 8\nreihenfrage = '  '": "reihenfrage fehlt",
            "[[reihe]]\nreihenfrage = 'x'": "klasse fehlt",
            "[[reihe]]\nklasse = 8\nreihenfrage = 'x'\nthema = 'y'": "unbekannte Felder ['thema']",
            "[[reihe]]\nklasse = 8\nreihenfrage = 'x'\nbehandelt = 'Singer'": "behandelt muss eine Liste",
            "[[reihe]]\nklasse = 8\nreihenfrage = 'x'\nmerksaetze = [1]": "merksaetze muss eine Liste",
        }
        for text, erwartet in faelle.items():
            with self.subTest(text=text), self.assertRaises(reihen.ReihenFehler) as f:
                reihen.laden(self.datei(text))
            self.assertIn(erwartet, str(f.exception))


if __name__ == "__main__":
    unittest.main()
