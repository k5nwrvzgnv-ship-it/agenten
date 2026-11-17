"""Adapter geprueft.json -> Wissensbasis, gegen eine kleine Kopie der echten Exposé-Recherche (Kette
20261102-165741-uni-ac9dcc, 7 Aussagen, alle fünf Status, Normen und ein lokales Werk)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agentkit import recherche as wissen

import rechercheprojekt as rp

KLEIN = Path(__file__).parent / "daten" / "recherche_klein"


def _lies(name: str) -> dict:
    return json.loads((KLEIN / name).read_text(encoding="utf-8"))


class Eintraege(unittest.TestCase):
    def setUp(self):
        self.g, self.gegen = _lies("geprueft.json"), _lies("gegenpruefung.json")
        self.e = rp.eintraege(self.g, self.gegen)

    def test_fragen_mit_fenster_als_gruppe(self):
        f1 = next(f for f in self.e["fragen"] if f["id"] == "F1")
        self.assertEqual(f1["gruppe"], "regelwerk")
        self.assertTrue(f1["anlass"].startswith("Henri"))

    def test_lokale_belege_mit_register(self):
        reg = {q["register"]: q for q in self.e["quellen"] if q.get("register")}
        self.assertEqual(reg["norm:DIN 4074-1:2026-05"]["art"], "norm")
        self.assertEqual(reg["datei:data/literatur/kit/Blass_Sandhaas_Ingenieurholzbau_2016.pdf"]["art"], "werk")
        beleg = next(b for a in self.e["aussagen"] for b in a["belege"] if b.get("register"))
        self.assertIsInstance(beleg["seite"], int)
        self.assertNotIn("url", beleg)

    def test_pruefung_und_urteil(self):
        a = self.e["aussagen"][0]  # literatur-1
        self.assertEqual(a["belege"][0]["pruefung"], {"status": "bestanden", "grund": "Zitat auf der Seite gefunden"})
        self.assertEqual(a["traegt"]["urteil"], "teilweise")
        self.assertIn("Lin et al.", a["traegt"]["fehlt"])

    def test_ohne_gegenpruefung_offen(self):
        e = rp.eintraege(self.g)
        self.assertTrue(all(a["traegt"] is None for a in e["aussagen"]))

    def test_widersprueche_und_rueckfragen(self):
        self.assertIn("literatur-13", self.e["widersprueche"][0])
        self.assertEqual(self.e["widersprueche"][0], self.g["widersprueche"][0]["worum"])
        self.assertTrue(rp._widerspruch({"ids": ["a-1"], "worum": "Zahlen passen nicht"}).endswith("(a-1)"))
        self.assertTrue(self.e["rueckfragen"][0].startswith("F1: "))
        self.assertEqual(len(self.e["luecken"]), 2)

    def test_status_wie_im_motor(self):
        basis = wissen.neu("p", "t", "jan", "uni")
        lauf = wissen.einarbeiten(basis, {"art": "suche"}, self.e)
        self.assertEqual(lauf["doppelt"], 0)
        self.assertEqual([a["status"] for a in basis["aussagen"]], [a["status"] for a in self.g["aussagen"]])
        self.assertEqual([f["id"] for f in basis["fragen"]], [f["id"] for f in self.g["fragen"]])

    def test_zusammenfassung(self):
        z = rp.zusammenfassung(self.g, 35.2257)
        self.assertIn("7 Aussagen (1 gesichert, 2 teilweise, 1 verworfen, 2 unbelegt", z)
        self.assertIn("Scopus 02.11.2026: 2 Suchen", z)
        self.assertTrue(z.endswith("35.23 USD."))


class Einlesen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hier = Path(self.tmp.name)
        self.lauf = self.hier / "data" / "expose" / "kette-1" / "recherche"
        shutil.copytree(KLEIN, self.lauf)

    def tearDown(self):
        self.tmp.cleanup()

    def test_legt_projekt_an(self):
        ziel, lauf = rp.einlesen(self.hier, self.lauf, "kette-1", "20261102-uni-test", "Test", ort="expose/kette-1")
        self.assertEqual(ziel, self.hier / "data" / "projekte" / "20261102-uni-test" / "wissen.json")
        basis = wissen.laden(ziel)
        self.assertEqual((basis["fuer"], basis["agent"], basis["ort"]), ("jan", "uni", "expose/kette-1"))
        self.assertTrue(basis["thema"].startswith("Entwicklung"))
        self.assertEqual(lauf["usd"], 35.2257)
        self.assertEqual(lauf["modell"], "opus")
        self.assertEqual(lauf["auftrag"], "kette-1")
        self.assertEqual((ziel.parent / lauf["ordner"]).resolve(), self.lauf.resolve())
        z = wissen.zahlen(basis)
        self.assertEqual((z["aussagen"], z["gesichert"], z["einschaetzung"]), (7, 1, 1))

    def test_nicht_doppelt_und_laufordner_unveraendert(self):
        vorher = {p.name: p.read_bytes() for p in self.lauf.iterdir()}
        rp.einlesen(self.hier, self.lauf, "kette-1", "p1", "Test")
        with self.assertRaises(wissen.RechercheFehler):
            rp.einlesen(self.hier, self.lauf, "kette-1", "p1", "Test")
        self.assertEqual({p.name: p.read_bytes() for p in self.lauf.iterdir()}, vorher)

    def test_frage_kennungen_mit_luecke(self):
        pfad = self.lauf / "geprueft.json"
        g = json.loads(pfad.read_text(encoding="utf-8"))
        g["fragen"][1]["id"] = "F9"
        for a in g["aussagen"]:
            a["frage"] = "F9" if a["frage"] == "F2" else a["frage"]
        pfad.write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(wissen.RechercheFehler):
            rp.einlesen(self.hier, self.lauf, "kette-1", "p1", "Test")
        self.assertFalse((self.hier / "data" / "projekte" / "p1" / "wissen.json").exists())

    def test_ohne_geprueft(self):
        (self.lauf / "geprueft.json").unlink()
        with self.assertRaises(wissen.RechercheFehler):
            rp.einlesen(self.hier, self.lauf, "kette-1", "p1", "Test")
        self.assertFalse((self.hier / "data" / "projekte").exists())


class AusAuftrag(unittest.TestCase):
    """Bauschritt 6b: Projekt nach einem recherche-Auftrag aus dem Arbeitsplatz, mit ort."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.hier = Path(self.tmp.name)
        self.lauf = self.hier / "data" / "recherchen" / "20261117-093000-uni-abc123" / "recherche"
        shutil.copytree(KLEIN, self.lauf)
        self.a = {"id": "20261117-093000-uni-abc123", "ort": "forschung/fehlstellen", "text": "Art: recherche"}

    def test_projekt_id(self):
        self.assertEqual(rp.projekt_id(self.a["id"], "Holzfeuchte messen (Darr-Methode)"),
                         "20261117-uni-holzfeuchte-messen-darr-methode-abc123")
        self.assertEqual(rp.projekt_id(self.a["id"], "Fäulnis über Größe"), "20261117-uni-faeulnis-ueber-groesse-abc123")
        lang = rp.projekt_id(self.a["id"], "Optische Erkennung von Fehlstellen an Schnittholz mit neuronalen Netzen")
        self.assertEqual(lang, "20261117-uni-optische-erkennung-von-fehlstellen-an-abc123")
        self.assertEqual(rp.projekt_id(self.a["id"], "?!"), "20261117-uni-abc123")
        self.assertEqual(rp.projekt_id("Fremd_ID", "x"), "uni-x-fremd-id")
        for pid in (lang, rp.projekt_id("Fremd_ID", "x")):
            self.assertTrue(wissen.PROJEKT_ID.fullmatch(pid))

    def test_mit_ort_und_titel(self):
        ziel = rp.aus_auftrag(self.hier, self.lauf, self.a, "Fehlstellen")
        self.assertEqual(ziel.parent.name, "20261117-uni-fehlstellen-abc123")
        basis = wissen.laden(ziel)
        self.assertEqual((basis["titel"], basis["ort"]), ("Fehlstellen", "forschung/fehlstellen"))
        self.assertEqual(basis["laeufe"][0]["auftrag"], self.a["id"])
        self.assertEqual((ziel.parent / basis["laeufe"][0]["ordner"]).resolve(), self.lauf.resolve())

    def test_ohne_ort_und_nicht_doppelt(self):
        a = {k: v for k, v in self.a.items() if k != "ort"}
        ziel = rp.aus_auftrag(self.hier, self.lauf, a, "Fehlstellen")
        self.assertNotIn("ort", wissen.laden(ziel))
        self.assertIsNone(rp.aus_auftrag(self.hier, self.lauf, a, "Fehlstellen"))


if __name__ == "__main__":
    unittest.main()
