import tomllib
import unittest
from pathlib import Path

import kritik
from renderer import pruefen as renderer_pruefen

RUBRIK = tomllib.loads((Path(__file__).resolve().parents[1] / "theater.toml").read_text(encoding="utf-8"))


def antwort(stufe="gut", **aenderung):
    k = {"kriterien": [{"id": x["id"], "stufe": stufe, "beleg": "B07 trägt", "verbesserung": "mehr Fallhöhe"}
                       for x in RUBRIK["kriterium"]],
         "staerken": ["Chor"], "wichtigste_aenderungen": ["Countdown je Akt"]}
    k.update(aenderung)
    return k


class Pruefen(unittest.TestCase):
    def test_gut(self):
        self.assertEqual(kritik.pruefen(antwort(), RUBRIK), [])
        self.assertEqual(kritik.unter_schwelle(antwort("sehr gut"), RUBRIK), [])

    def test_rubrik_hat_elf_kriterien_mit_feldern(self):
        self.assertEqual(len(RUBRIK["kriterium"]), 11)
        for k in RUBRIK["kriterium"]:
            self.assertTrue(all(k.get(f) for f in ("id", "name", "frage", "gut", "quelle")), k)

    def test_kriterium_fehlt_oder_doppelt(self):
        k = antwort()
        k["kriterien"][1] = dict(k["kriterien"][0])
        fehler = kritik.pruefen(k, RUBRIK)
        self.assertIn("Kriterium steigerung kommt 2-mal vor, genau einmal nötig", fehler)
        self.assertIn("Kriterium fallhoehe kommt 0-mal vor, genau einmal nötig", fehler)

    def test_falsche_stufe_und_fremde_id(self):
        k = antwort()
        k["kriterien"][0]["stufe"] = "mittel"
        k["kriterien"].append({"id": "x", "stufe": "gut", "beleg": "b"})
        fehler = kritik.pruefen(k, RUBRIK)
        self.assertTrue(any("kriterien[0].stufe" in f for f in fehler))
        self.assertTrue(any("kriterien[11].id" in f for f in fehler))

    def test_verbesserung_pflicht_unter_gut(self):
        k = antwort("ansatzweise")
        del k["kriterien"][2]["verbesserung"]
        self.assertIn("kriterien[2].verbesserung: Text fehlt (Pflicht unter „gut“)", kritik.pruefen(k, RUBRIK))
        k = antwort("gut")
        del k["kriterien"][2]["verbesserung"]
        self.assertEqual(kritik.pruefen(k, RUBRIK), [])

    def test_unter_gut_braucht_wichtigste_aenderungen(self):
        fehler = kritik.pruefen(antwort("nicht erkennbar", wichtigste_aenderungen=[]), RUBRIK)
        self.assertEqual(fehler, ["wichtigste_aenderungen: unter „gut“ mindestens eine Änderung nennen"])

    def test_laengen(self):
        k = antwort()
        k["kriterien"][0]["beleg"] = "x" * 501
        k["staerken"] = ["a"] * 6
        fehler = kritik.pruefen(k, RUBRIK)
        self.assertTrue(any("beleg: höchstens 500" in f for f in fehler))
        self.assertTrue(any(f.startswith("staerken:") for f in fehler))

    def test_aenderungen(self):
        self.assertEqual(kritik.aenderungen_pruefen({"aenderungen": ["B07 gekürzt"]}), [])
        self.assertTrue(kritik.aenderungen_pruefen({}))
        self.assertTrue(kritik.aenderungen_pruefen({"aenderungen": ["x"] * 9}))


class Texte(unittest.TestCase):
    def test_ueberarbeitung_nennt_kriterien_unter_gut(self):
        k = antwort("gut")
        k["kriterien"][1]["stufe"] = "ansatzweise"
        p = kritik.ueberarbeitung_prompt("data/r/ablauf-2.json", "data/r/ablauf.json", k, RUBRIK, ["data/r/teil-1.txt"])
        self.assertIn("unter „gut“ (fallhoehe)", p)
        self.assertIn("- fallhoehe (Thema Scheitern trägt): ansatzweise. B07 trägt", p)
        self.assertIn("Schreibe die ganze Datei data/r/ablauf-2.json", p)
        self.assertIn("- data/r/teil-1.txt", p)

    def test_prompt_enthaelt_rubrik(self):
        p = kritik.prompt("data/r/kritik-1.json", "data/r/spielfassung-1.txt", "data/r/ablauf.json", "v.md", "g.md",
                          ["b1.md"], "data/r/szenenkarte.json", RUBRIK, 1)
        self.assertIn("Schreibe die Datei data/r/kritik-1.json", p)
        for k in RUBRIK["kriterium"]:
            self.assertIn(f"- {k['id']} – {k['name']}", p)

    def test_bloecke_gueltig(self):
        k = antwort("gut")
        k["kriterien"][0]["stufe"] = "ansatzweise"
        b = kritik.bloecke(k, RUBRIK, 2, ["B07 neu"])
        self.assertEqual(renderer_pruefen({"art": "arbeitsblatt", "titel": "T", "bloecke": b}), [])
        text = str(b)
        self.assertIn("2-mal überarbeitet. Noch unter „gut“: Steigerung über drei Durchläufe.", text)
        self.assertIn("Was der Prüfer noch vorschlägt", text)
        self.assertNotIn("Was der Prüfer noch vorschlägt", str(kritik.bloecke(antwort(), RUBRIK, 0, [])))


if __name__ == "__main__":
    unittest.main()
