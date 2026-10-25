import json
import tempfile
import unittest
from pathlib import Path

import traegt

REGISTER = {"liszt": {"stellen": [{"seite": 41, "seiten": [41, 42], "zitat": "Die dritte Gruppe"}]}}


def daten():
    ok = {"status": "bestanden"}
    return {"zahlen": {"aussagen": 4, "belegt": 3, "unbelegt": 1}, "abschnitte": [
        {"titel": "B", "aussagen": [
            {"text": "Zwei Studentinnen in Olching.", "belegt": True,
             "belege": [{"url": "https://x.de", "zitat": "zwei Studentinnen", "pruefung": ok},
                        {"url": "https://y.de", "zitat": "falsch", "pruefung": {"status": "durchgefallen"}}]},
            {"text": "Einschätzung: guter Fall.", "belegt": True, "belege": [{"register": "liszt:42", "pruefung": ok}]},
            {"text": "Unbelegt.", "belegt": False, "belege": []}]},
        {"titel": "L", "aussagen": [
            {"text": "Liszt: dritte Gruppe.", "belegt": True, "belege": [{"register": "liszt:42", "pruefung": ok}]}]}]}


class FaelleTest(unittest.TestCase):
    def test_nur_belegte_tatsachen_mit_bestandenen_belegen(self):
        f = traegt.faelle(daten(), REGISTER)
        self.assertEqual([x["id"] for x in f], ["a0-0", "a1-0"])
        self.assertEqual(f[0]["belege"], [{"quelle": "https://x.de", "zitat": "zwei Studentinnen"}])
        self.assertEqual(f[1]["belege"], [{"quelle": "Quellenregister liszt:42", "zitat": "Die dritte Gruppe"}])

    def test_prompt(self):
        p = traegt.prompt(traegt.faelle(daten(), REGISTER), "data/web/x/traegt.json")
        for teil in ("keine Werkzeuge", "außer Write", '"id": "a0-0"', "data/web/x/traegt.json", "teilweise"):
            self.assertIn(teil, p)


class LesenTest(unittest.TestCase):
    def lesen(self, inhalt, ids=("a0-0", "a1-0")):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.json"
            p.write_text(inhalt if isinstance(inhalt, str) else json.dumps(inhalt), encoding="utf-8")
            return traegt.lesen(p, list(ids))

    def test_gut(self):
        u, f = self.lesen({"urteile": [{"id": "a0-0", "traegt": "teilweise", "fehlt": "Olching"},
                                       {"id": "a1-0", "traegt": "ja"}]})
        self.assertEqual(f, [])
        self.assertEqual(u["a0-0"], {"traegt": "teilweise", "fehlt": "Olching"})
        self.assertEqual(u["a1-0"], {"traegt": "ja", "fehlt": ""})

    def test_fehler(self):
        u, f = self.lesen({"urteile": [{"id": "a0-0", "traegt": "vielleicht"}, {"id": "zz", "traegt": "ja"},
                                       {"id": "a1-0", "traegt": "ja"}, {"id": "a1-0", "traegt": "nein"}]})
        self.assertEqual(u, {})
        text = "; ".join(f)
        for teil in ("vielleicht", "unbekannte id 'zz'", "a1-0 doppelt"):
            self.assertIn(teil, text)
        self.assertEqual(self.lesen("{")[0], {})
        self.assertIn("ids fehlen: a1-0", "; ".join(self.lesen({"urteile": [{"id": "a0-0", "traegt": "ja"}]})[1]))


class AnwendenTest(unittest.TestCase):
    def test_folgen(self):
        d = traegt.anwenden(daten(), ["a0-0", "a1-0"], {"a0-0": {"traegt": "nein", "fehlt": "Olching"}})
        s = d["abschnitte"][0]["aussagen"][0]
        self.assertFalse(s["belegt"])
        self.assertEqual(d["abschnitte"][1]["aussagen"][0]["traegt"]["traegt"], "nicht geprüft")
        self.assertEqual(d["traegt_zahlen"], {"ja": 0, "teilweise": 0, "nein": 1, "nicht_geprueft": 1})
        self.assertEqual((d["zahlen"]["belegt"], d["zahlen"]["unbelegt"]), (2, 2))


if __name__ == "__main__":
    unittest.main()
