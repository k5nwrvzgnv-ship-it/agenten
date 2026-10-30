import tempfile
import unittest
from pathlib import Path

import reihen

HIER = Path(__file__).resolve().parent.parent

GUT = """
[[reihe]]
id = "ethik-8-helfen"
fach = "Ethik"
klasse = 8
titel = "Helfen"
reihenfrage = "Muss ich Fremden genauso helfen wie meiner Familie?"
lerngruppe = "lernschwach, mehrsprachig"
behandelt = ["Singer", "Aristoteles"]
merksaetze = ["Merksatz eins.", "Merksatz zwei."]
notizen = "Nächste Stunde Fallbeispiel"

[[reihe]]
fach = "Darstellendes Spiel"
klasse = "Kurs 11"
reihenfrage = "Wie entsteht eine Figur?"
agenten = ["theater"]

[[reihe]]
fach = "Ethik"
klasse = 8
titel = "Strafe (in Planung)"
bisherige_reihen = ["Klasse 7: Lüge", "Klasse 8: Helfen"]

[[reihe]]
fach = "Ethik"
klasse = "7"
titel = "Glück"
reihenfrage = "Wie führe ich ein glückliches Leben?"
schuljahr = "2025/26"
stand = "abgeschlossen"
lerngruppe = "steht nicht im Prompt"
"""


class ReihenTest(unittest.TestCase):
    def datei(self, text: str) -> Path:
        pfad = Path(tempfile.mkdtemp()) / "reihen.toml"
        pfad.write_text(text, encoding="utf-8")
        return pfad

    def test_mitgelieferte_datei_ist_gueltig(self):
        r = reihen.laden(HIER.parent / "instanz" / "reihen.toml")
        text = reihen.prompt_reihen(r, "Ethik")
        self.assertIn("### Ethik, Klasse 8: Straftheorien", text)
        self.assertIn("### Darstellendes Spiel, Kurs 12: Der nackte Wahnsinn", text)

    def test_ohne_datei_und_leer(self):
        self.assertEqual(reihen.laden(Path(tempfile.mkdtemp()) / "fehlt.toml"), [])
        self.assertEqual(reihen.laden(self.datei("# nur Kommentare\n")), [])
        self.assertEqual(reihen.prompt_reihen([], "Ethik"), "")

    def test_laden_und_prompt(self):
        r = reihen.laden(self.datei(GUT))
        self.assertEqual(len(r), 4)
        text = reihen.prompt_reihen(r, "Ethik")
        self.assertTrue(text.startswith("## Lias laufende Reihen\n"))
        self.assertIn("### Ethik, Klasse 8: Helfen\n- Reihenfrage: Muss ich Fremden", text)
        self.assertIn("- Lerngruppe: lernschwach, mehrsprachig", text)
        self.assertIn("- Schon behandelt: Singer; Aristoteles", text)
        self.assertIn("- Merksätze der Reihe:\n  - Merksatz eins.\n  - Merksatz zwei.", text)
        self.assertIn("- Notizen: Nächste Stunde Fallbeispiel", text)
        self.assertIn("### Darstellendes Spiel, Kurs 11\n- Reihenfrage: Wie entsteht eine Figur?\n\n", text)
        self.assertNotIn("Lerngruppe", text.split("### Darstellendes Spiel")[1])
        self.assertIn("### Ethik, Klasse 8: Strafe (in Planung)\n"
                      "- Frühere Reihen der Klasse:\n  - Klasse 7: Lüge\n  - Klasse 8: Helfen\n\n", text)
        self.assertTrue(text.endswith("### Abgeschlossene Reihen (nur zur Orientierung, was die Klassen schon kennen)\n"
                                      "- Ethik, Klasse 7 (2025/26): Glück – Wie führe ich ein glückliches Leben?\n\n"))
        self.assertNotIn("steht nicht im Prompt", text)

    def test_fehler(self):
        faelle = {
            "[[reihe]\nklasse = 8": "kein gültiges TOML",
            "[reihe]\nklasse = 8\nreihenfrage = 'x'": "[[reihe]]",
            "klasse = 8": "unbekannte Einträge",
            "[[reihe]]\nfach = 'Ethik'\nreihenfrage = 'x'": "klasse fehlt",
            "[[reihe]]\nfach = 'Ethik'\nklasse = ' '": "klasse fehlt",
            "[[reihe]]\nklasse = 8": "fach fehlt",
            "[[reihe]]\nfach = 'Ethik'\nklasse = 8\nstand = 'fertig'": "stand 'fertig'",
            "[[reihe]]\nfach = 'Ethik'\nklasse = 8\nid = 'Ethik 8'": "id nur aus",
            "[[reihe]]\nfach = 'E'\nklasse = 8\nid = 'a'\n[[reihe]]\nfach = 'E'\nklasse = 7\nid = 'a'": "doppelt",
            "[[reihe]]\nfach = 'Ethik'\nklasse = 8\nagenten = 'theater'": "agenten muss eine Liste",
            "[[reihe]]\nfach = 'Ethik'\nklasse = 8\nbisherige_reihen = 'Lüge'": "bisherige_reihen muss eine Liste",
            "[[reihe]]\nfach = 'Ethik'\nklasse = 8\nreihenfrage = 'x'\nthema = 'y'": "unbekannte Felder ['thema']",
            "[[reihe]]\nfach = 'Ethik'\nklasse = 8\nreihenfrage = 'x'\nbehandelt = 'Singer'": "behandelt muss eine Liste",
            "[[reihe]]\nfach = 'Ethik'\nklasse = 8\nreihenfrage = 'x'\nmerksaetze = [1]": "merksaetze muss eine Liste",
        }
        for text, erwartet in faelle.items():
            with self.subTest(text=text), self.assertRaises(reihen.ReihenFehler) as f:
                reihen.laden(self.datei(text))
            self.assertIn(erwartet, str(f.exception))


if __name__ == "__main__":
    unittest.main()
