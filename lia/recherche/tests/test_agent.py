import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import agent
from agentkit import abruf, wortlaut
from tests.test_auslesen import GESETZ, KORPORA

QUELLEN = '''[abruf]
allowlist = ["gesetze-im-internet.de", "korpora.org"]

[[quelle]]
id = "tg-7"
art = "gesetz"
werk = "TG § 7"
ausgabe = "gii"
urls = ["https://www.gesetze-im-internet.de/tg/__7.html"]

[[quelle]]
id = "kant"
art = "primaertext"
autor = "Kant"
todesjahr_autor = 1804
werk = "MdS"
ausgabe = "AA 6"
herausgeber = ""
seiten = [331]
urls = ["https://korpora.org/kant/aa06/331.html"]
'''


class Laden:
    """Ersetzt abruf.laden: Seiten aus einem dict, merkt sich, was "neu" geladen wurde."""

    def __init__(self, seiten):
        self.seiten, self.geladen = seiten, []

    def __call__(self, url, allowlist, cache_dir):
        abruf.pruefen(url, allowlist)
        if url not in self.seiten:
            raise abruf.AbrufFehler(f"HTTP-Fehler 404 (Not Found) bei {url}")
        neu = url not in self.geladen
        self.geladen.append(url)
        inhalt, ct = self.seiten[url]
        meta = {"url": url, "abgerufen": "2026-10-25T10:00:00+01:00", "content_type": ct,
                "sha256": hashlib.sha256(inhalt).hexdigest()}
        return abruf.Ergebnis(inhalt, meta, not neu)


SEITEN = {
    "https://www.gesetze-im-internet.de/tg/__7.html": (GESETZ.encode("latin-1"), "text/html"),
    "https://korpora.org/kant/aa06/331.html": (KORPORA.encode("latin-1"), "text/html; charset=Charset=ISO-8859-1"),
}


class LaufTest(unittest.TestCase):
    def setUp(self):
        self.hier = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.hier)
        (self.hier / "quellen.toml").write_text(QUELLEN, encoding="utf-8")
        self.meldungen = []

    def lauf(self, seiten=SEITEN, laden=None):
        self.laden = laden or Laden(seiten)
        return agent.lauf(self.hier, laden=self.laden, melden=self.meldungen.append, jahr=2026)

    def register(self):
        return {e["id"]: e for e in json.loads((self.hier / "data/register.json").read_text())["quellen"]}

    def test_register(self):
        self.assertEqual(self.lauf(), [])
        reg = self.register()
        g, k = reg["tg-7"], reg["kant"]
        self.assertEqual(g["stellen"], [{"seite": 1, "zitat": g["stellen"][0]["zitat"], "geprueft": True}])
        self.assertTrue(g["stellen"][0]["zitat"].startswith("(1) Die Strafe soll wirken."))
        self.assertEqual(g["gemeinfreiheit"]["status"], "frei")
        self.assertEqual(k["gemeinfreiheit"]["status"], "ungeklaert")
        self.assertFalse(k["gemeinfreiheit"]["verwendbar"])
        self.assertEqual((k["stellen"], k["autor"], k["urls"]), ([], "Kant", ["https://korpora.org/kant/aa06/331.html"]))
        text = (self.hier / k["textfassung"]).read_text(encoding="utf-8")
        self.assertEqual(k["sha256"], hashlib.sha256(text.encode()).hexdigest())
        self.assertIn("heißt Verbrechen schlechthin (crimen)", wortlaut.seiten(text)[331])
        self.assertEqual(k["roh"][0]["sha256"], hashlib.sha256(SEITEN[k["urls"][0]][0]).hexdigest())
        self.assertEqual(len(self.meldungen), 1)  # erster Lauf: Gemeinfreiheit beider Quellen
        self.assertIn("kant: Gemeinfreiheit ungeklaert (Herausgeber nicht geklärt", self.meldungen[0])
        self.assertNotIn("herausgeber", k)  # leer = nicht eingetragen

    def test_herausgeber_im_register(self):
        (self.hier / "quellen.toml").write_text(
            QUELLEN.replace('herausgeber = ""', 'herausgeber = "H"\nherausgeber_todesjahr = 1924'), encoding="utf-8")
        self.assertEqual(self.lauf(), [])
        k = self.register()["kant"]
        self.assertEqual((k["herausgeber"], k["gemeinfreiheit"]["status"]), ("H", "frei"))

    def test_zweiter_lauf_still_und_stellen_bleiben(self):
        self.lauf()
        reg = json.loads((self.hier / "data/register.json").read_text())
        for e in reg["quellen"]:
            if e["id"] == "kant":
                e["stellen"] = [{"seite": 331, "zitat": "Vom Straf= und", "geprueft": True}]
        (self.hier / "data/register.json").write_text(json.dumps(reg))
        self.meldungen.clear()
        self.assertEqual(agent.lauf(self.hier, laden=self.laden, melden=self.meldungen.append, jahr=2026), [])
        self.assertEqual(self.meldungen, [])
        self.assertEqual(len(self.register()["kant"]["stellen"]), 1)

    def test_geaenderter_text_verwirft_stellen(self):
        self.lauf()
        reg = json.loads((self.hier / "data/register.json").read_text())
        reg["quellen"][1]["stellen"] = [{"seite": 331, "zitat": "x", "geprueft": True}]
        reg["quellen"][1]["sha256"] = "alt"
        (self.hier / "data/register.json").write_text(json.dumps(reg))
        self.meldungen.clear()
        agent.lauf(self.hier, laden=self.laden, melden=self.meldungen.append, jahr=2026)
        self.assertEqual(self.register()["kant"]["stellen"], [])
        self.assertIn("1 Stellen verworfen", self.meldungen[0])

    def test_fehler_wird_gemeldet_alter_eintrag_bleibt(self):
        self.lauf()
        kaputt = dict(SEITEN)
        del kaputt["https://korpora.org/kant/aa06/331.html"]
        self.meldungen.clear()
        fehler = self.lauf(kaputt)
        self.assertEqual(len(fehler), 1)
        self.assertIn("404", fehler[0])
        self.assertIn("1 Fehler:", self.meldungen[0])
        self.assertIn("kant", self.register())

    def test_falsche_seite(self):
        (self.hier / "quellen.toml").write_text(QUELLEN.replace("[331]", "[332]"), encoding="utf-8")
        fehler = self.lauf()
        self.assertIn("ist Seite 331, erwartet 332", fehler[0])
        self.assertNotIn("kant", self.register())

    def test_quellen_kaputt(self):
        (self.hier / "quellen.toml").write_text("[[quelle", encoding="utf-8")
        self.assertEqual(len(self.lauf()), 1)
        self.assertIn("quellen.toml fehlerhaft", self.meldungen[0])


class MeldenTest(unittest.TestCase):
    def test_jan_melden_in_basis(self):
        with tempfile.TemporaryDirectory() as d:
            agent.jan_melden("Test", basis=Path(d))
            datei = next((Path(d) / "neu").glob("*.json"))
            self.assertIn("Lia, Agent recherche: Test", datei.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
