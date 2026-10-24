import tempfile
import unittest
from pathlib import Path

import quellen

HIER = Path(__file__).resolve().parent.parent
KOPF = '[abruf]\nallowlist = ["korpora.org"]\n'
KANT = '''[[quelle]]
id = "k"
art = "primaertext"
autor = "Kant"
todesjahr_autor = 1804
werk = "W"
ausgabe = "A"
seiten = [1]
urls = ["https://korpora.org/1.html"]
'''


class QuellenTest(unittest.TestCase):
    def laden(self, inhalt):
        with tempfile.TemporaryDirectory() as d:
            pfad = Path(d) / "quellen.toml"
            pfad.write_text(inhalt, encoding="utf-8")
            return quellen.laden(pfad)

    def fehler(self, inhalt, teil):
        with self.assertRaises(quellen.QuellenFehler) as f:
            self.laden(inhalt)
        self.assertIn(teil, str(f.exception))

    def test_echte_datei(self):
        allowlist, alle = quellen.laden(HIER / "quellen.toml")
        self.assertIn("archive.org", allowlist)
        self.assertEqual([q["id"] for q in alle], ["stgb-46", "jgg-2", "kant-mds-strafrecht"])

    def test_gut(self):
        allowlist, alle = self.laden(KOPF + KANT)
        self.assertEqual((allowlist, alle[0]["id"]), (["korpora.org"], "k"))

    def test_ohne_allowlist(self):
        self.fehler(KANT, "allowlist")

    def test_domain_nicht_erlaubt(self):
        self.fehler(KOPF + KANT.replace("korpora.org/1", "zeno.org/1"), "Domain nicht erlaubt")

    def test_kein_https(self):
        self.fehler(KOPF + KANT.replace("https:", "http:"), "Nur https")

    def test_doppelt(self):
        self.fehler(KOPF + KANT + KANT, "doppelt")

    def test_art_unbekannt(self):
        self.fehler(KOPF + KANT.replace('"primaertext"', '"roman"'), "art")

    def test_seiten_passen_nicht(self):
        self.fehler(KOPF + KANT.replace("[1]", "[1, 2]"), "2 Seiten, aber 1 URLs")

    def test_ohne_autor(self):
        self.fehler(KOPF + KANT.replace('autor = "Kant"\n', ""), "autor fehlt")

    def test_kaputt(self):
        self.fehler("[[quelle", "nicht lesbar")


if __name__ == "__main__":
    unittest.main()
