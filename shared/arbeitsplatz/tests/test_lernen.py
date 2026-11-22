"""lernen.py: Prüfungsmodule finden, Portal-Seiten durchreichen (Logik ohne Netz)."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import lernen

ABLAGE = 'X = 1\nMODULE = {"holzschutz": "Holzschutz", "leer": "Ohne Karten", "../boese": "x"}  # Kommentar\n'


def uni_anlegen(wurzel: Path, ablage: str = ABLAGE, karten=None) -> Path:
    uni = wurzel / "uni"
    (uni / "portal").mkdir(parents=True)
    (uni / "portal" / "ablage.py").write_text(ablage, encoding="utf-8")
    (uni / "data" / "lernen" / "holzschutz").mkdir(parents=True)
    (uni / "data" / "lernen" / "holzschutz" / "karten.json").write_text(
        json.dumps(karten if karten is not None else [{"id": "a"}, {"id": "b"}]), encoding="utf-8")
    return uni


class TestModule(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_module_mit_karten(self):
        uni = uni_anlegen(self.tmp)
        self.assertEqual(lernen.portal_module(uni), {"holzschutz": "Holzschutz", "leer": "Ohne Karten"})
        self.assertEqual(lernen.module(uni), [{"id": "holzschutz", "name": "Holzschutz", "karten": 2,
                                               "link": "/modul/holzschutz", "ueben": "/modul/holzschutz/ueben"}])

    def test_ohne_portal_oder_kaputt(self):
        self.assertEqual(lernen.module(self.tmp / "gibtsnicht"), [])
        uni = uni_anlegen(self.tmp, ablage="MODULE = {")
        self.assertEqual(lernen.module(uni), [])
        (uni / "portal" / "ablage.py").write_text("MODULE = dict(a=1)\n")
        self.assertEqual(lernen.module(uni), [])
        (uni / "portal" / "ablage.py").write_text(ABLAGE)
        (uni / "data" / "lernen" / "holzschutz" / "karten.json").write_text("{kaputt")
        self.assertEqual(lernen.module(uni), [])
        self.assertIsNone(lernen.karten_zahl(uni, "holzschutz"))

    def test_ort_des_moduls(self):
        ids = {"modul-holzschutz", "finanzen", "modul-sanierung-im-holzbau", "praxis"}
        self.assertEqual(lernen.ort_des_moduls("holzschutz", ids), "modul-holzschutz")
        self.assertEqual(lernen.ort_des_moduls("sanierung", ids), "modul-sanierung-im-holzbau")
        self.assertEqual(lernen.ort_des_moduls("praxis", ids), "praxis")
        self.assertIsNone(lernen.ort_des_moduls("statik", ids))
        mods = [{"id": "holzschutz"}, {"id": "statik"}]
        self.assertEqual(lernen.fuer_ort(mods, ids, {"fachplanung", "modul-holzschutz"}), [{"id": "holzschutz"}])
        self.assertEqual(lernen.fuer_ort(mods, ids, {"finanzen"}), [])


class TestDurchreichen(unittest.TestCase):
    def test_pfad_erlaubt(self):
        for gut in ("/modul/holzschutz", "/modul/holzschutz/ueben", "/modul/holzschutz/bild/k1-a/frage",
                    "/modul/holzschutz/uebung/20261109-120000-abcdef/karten"):
            self.assertTrue(lernen.pfad_erlaubt(gut), gut)
        for schlecht in ("/modul/", "/modul/../app.py", "/modul/holzschutz/../../x", "/projekt/fehlstellen",
                         "/modul/Holz schutz", "/modul/a/b/c/d/e/f"):
            self.assertFalse(lernen.pfad_erlaubt(schlecht), schlecht)

    def test_kopfzeilen(self):
        self.assertEqual(lernen.anfrage_kopf({"host": "uni.meldro.de", "origin": "https://uni.meldro.de",
                                              "cookie": "x", "authorization": "Basic y", "content-type": "a/b"}),
                         {"host": "uni.meldro.de", "origin": "https://uni.meldro.de", "content-type": "a/b"})
        aus = lernen.antwort_kopf([("Content-Type", "text/html"), ("Content-Security-Policy", "x"),
                                   ("Location", "/modul/holzschutz/ueben?veraltet=1"), ("Set-Cookie", "a")])
        self.assertEqual(aus, {"content-type": "text/html", "location": "/modul/holzschutz/ueben?veraltet=1"})
        for fremd in ("https://boese.example/", "/projekt/x", "//boese.example/modul/x"):
            self.assertNotIn("location", lernen.antwort_kopf([("Location", fremd)]), fremd)

    def test_html_umschreiben(self):
        html = ('<title>Karten üben · Uni</title>\n<link rel="stylesheet" href="/statisch/stil.css">\n'
                '<div class="rahmen">\n<article class="lernkarte">\n<a class="baum-name" href="/">Uni</a>\n  <ul>\n'
                '    <li><a class="baum-eintrag" href="/projekt/fehlstellen"><span>Forschungsprojekt</span></a></li>\n'
                '    <li><a class="baum-eintrag" href="/modul/holzschutz" aria-current="page"><span>Holzschutz</span></a></li>')
        neu = lernen.html_umschreiben(html)
        self.assertNotIn("stil.css", neu)
        self.assertIn('href="/statisch/ruhig.css"', neu)
        self.assertIn('href="/statisch/lernen.css"', neu)
        self.assertIn("<title>Karten üben · Arbeitsplatz</title>", neu)
        self.assertIn('<a class="baum-name" href="/">Arbeitsplatz</a>', neu)
        self.assertNotIn("/projekt/", neu)
        self.assertIn('href="/modul/holzschutz"', neu)
        self.assertIn('<div class="rahmen ohne-rechts lernen-seite">', neu)
        self.assertIn('<h1 class="unsichtbar">Karten üben</h1>', neu)


if __name__ == "__main__":
    unittest.main()
