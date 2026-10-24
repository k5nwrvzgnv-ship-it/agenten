import json
import tempfile
import unittest
from pathlib import Path

import kernstellen

TEXT = """--- Seite 331
Richterliche Strafe kann niemals bloß
als Mittel ein anderes Gute zu befördern verhängt werden.
--- Seite 332
Das Strafgesetz ist ein kategorischer
Imperativ, und wehe dem!
"""


def stelle(seite, zitat, **mehr):
    return {"seite": seite, "zitat": zitat, "position": "Vergeltung", "zweck": "Einstieg.", **mehr}


class PruefenTest(unittest.TestCase):
    def test_bestanden_ueber_zeilen(self):
        gut, schlecht = kernstellen.pruefen([stelle(332, "Das Strafgesetz ist ein kategorischer Imperativ")], TEXT)
        self.assertEqual(schlecht, [])
        self.assertEqual(gut, [{"seite": 332, "zitat": "Das Strafgesetz ist ein kategorischer Imperativ",
                                "position": "Vergeltung", "zweck": "Einstieg.", "geprueft": True}])

    def test_falsche_seite(self):
        gut, schlecht = kernstellen.pruefen([stelle(331, "Das Strafgesetz ist ein kategorischer Imperativ")], TEXT)
        self.assertEqual(gut, [])
        self.assertIn("nicht wörtlich auf Seite 331", schlecht[0]["grund"])

    def test_ueber_seitengrenze(self):
        _, schlecht = kernstellen.pruefen([stelle(331, "verhängt werden. Das Strafgesetz")], TEXT)
        self.assertEqual(len(schlecht), 1)

    def test_verfaelscht(self):
        _, schlecht = kernstellen.pruefen([stelle(332, "Das Strafgesetz ist ein kategorischer Befehl")], TEXT)
        self.assertEqual(len(schlecht), 1)

    def test_seite_fehlt_und_felder(self):
        _, schlecht = kernstellen.pruefen([stelle(999, "x"), {"seite": 331, "zitat": "Richterliche"},
                                           stelle("331", "Richterliche"), "kaputt"], TEXT)
        self.assertEqual(len(schlecht), 4)
        self.assertIn("Seite 999", schlecht[0]["grund"])
        self.assertIn("Felder fehlen", schlecht[1]["grund"])

    def test_zu_lang(self):
        lang = "Richterliche Strafe " * 50
        _, schlecht = kernstellen.pruefen([stelle(331, lang)], TEXT + "--- Seite 333\n" + lang)
        self.assertIn("zu lang", schlecht[0]["grund"])

    def test_doppelt_auch_gegen_schon(self):
        gut, schlecht = kernstellen.pruefen([stelle(332, "kategorischer Imperativ"),
                                             stelle(332, "ein kategorischer Imperativ, und")], TEXT)
        self.assertEqual((len(gut), len(schlecht)), (1, 1))
        _, schlecht = kernstellen.pruefen([stelle(332, "kategorischer Imperativ")], TEXT, schon=gut)
        self.assertIn("doppelt", schlecht[0]["grund"])

    def test_leere_position(self):
        _, schlecht = kernstellen.pruefen([stelle(331, "Richterliche Strafe", position=" ")], TEXT)
        self.assertIn("position", schlecht[0]["grund"])

    def test_scan_markiert_ocr_stellen(self):
        gut, _ = kernstellen.pruefen([stelle(331, "Richterliche Strafe")], TEXT, scan={"331": "https://archive.org/x/n5"})
        self.assertEqual((gut[0]["am_scan_pruefen"], gut[0]["scan"]), (True, "https://archive.org/x/n5"))


class AntwortTest(unittest.TestCase):
    def lesen(self, inhalt):
        with tempfile.TemporaryDirectory() as d:
            pfad = Path(d) / "a.json"
            if inhalt is not None:
                pfad.write_text(inhalt, encoding="utf-8")
            return kernstellen.antwort_lesen(pfad)

    def test_gut(self):
        self.assertEqual(self.lesen(json.dumps({"stellen": [stelle(331, "x")]}))[0]["seite"], 331)

    def test_fehlt_kaputt_falsch(self):
        for inhalt in (None, "{kaputt", json.dumps([1]), json.dumps({"stellen": "x"})):
            with self.assertRaises(kernstellen.KernstellenFehler):
                self.lesen(inhalt)


class PromptTest(unittest.TestCase):
    def test_reihe(self):
        reihen = [{"klasse": "7", "titel": "Lügen"},
                  {"klasse": "8", "titel": "Straftheorien (in Planung)", "notizen": "erst Kant, dann von Liszt",
                   "lerngruppe": "heterogen"}]
        text = kernstellen.reihe_text(reihen)
        self.assertIn("Klasse 8, Reihe Straftheorien", text)
        self.assertIn("erst Kant, dann von Liszt", text)
        self.assertNotIn("Lügen", text)
        self.assertEqual(kernstellen.reihe_text(reihen[:1]), "")

    def test_prompt_nennt_dateien(self):
        p = kernstellen.prompt({"autor": "Kant", "werk": "MdS", "ausgabe": "AA"}, "data/text/k.txt",
                               "data/kernstellen/k.json", "Reihe X")
        for teil in ("data/text/k.txt", "data/kernstellen/k.json", "Reihe X", "WÖRTLICH", "--- Seite N"):
            self.assertIn(teil, p)
        n = kernstellen.nachbesserung_prompt([{"stelle": stelle(1, "abc"), "grund": "Zitat steht nicht"}],
                                             "data/text/k.txt", "data/kernstellen/k.json")
        self.assertIn("Seite 1: Zitat steht nicht", n)


if __name__ == "__main__":
    unittest.main()
