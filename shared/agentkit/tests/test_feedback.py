import json
import tempfile
import unittest
from pathlib import Path

from agentkit import feedback as fb

AGENTEN = ["recherche", "unterricht"]


def antwort(**felder):
    z = {"art": "regel", "ziel": "alle", "auftrag": "", "regel": "Ergebnisse beginnen mit einer Empfehlung.",
         "notiz": "", "heikel": False, "heikel_grund": "", "widerspricht": "", "zusammenfassung": "Lia will es kürzer."}
    z.update(felder)
    return z


class TestZuordnung(unittest.TestCase):
    def test_json_mit_text_drumherum(self):
        text = "Hier:\n```json\n" + json.dumps(antwort()) + "\n```"
        z = fb.zuordnung_lesen(text, AGENTEN)
        self.assertEqual((z["art"], z["ziel"], z["heikel"]), ("regel", "alle", False))

    def test_fehler(self):
        for text in ("kein json", "{kaputt}", json.dumps(antwort(art="loeschen")),
                     json.dumps(antwort(art="nachbesserung", auftrag="")),
                     json.dumps(antwort(regel="zwei\nzeilen")), json.dumps(antwort(ziel="uni")),
                     json.dumps(antwort(art="notiz", notiz="x", ziel="alle")), json.dumps(antwort(regel="x" * 401))):
            with self.subTest(text=text[:40]), self.assertRaises(fb.FeedbackFehler):
                fb.zuordnung_lesen(text, AGENTEN)

    def test_heikel_nur_bei_true(self):
        self.assertFalse(fb.zuordnung_lesen(json.dumps(antwort(heikel="ja")), AGENTEN)["heikel"])
        self.assertTrue(fb.zuordnung_lesen(json.dumps(antwort(heikel=True)), AGENTEN)["heikel"])

    def test_prompt_enthaelt_alles(self):
        p = fb.prompt("Lia", "recherche", {"text": "Reihe Strafe", "ergebnis": "31 Aussagen"}, "zu lang",
                      "- Kurz halten", AGENTEN)
        for teil in ("Reihe Strafe", "31 Aussagen", "zu lang", "- Kurz halten", "recherche, unterricht", '"art"'):
            self.assertIn(teil, p)


class TestEntscheiden(unittest.TestCase):
    def test_regel_und_notiz_sofort(self):
        self.assertEqual(fb.entscheiden(antwort(), fb.Lage()), (True, ""))
        self.assertEqual(fb.entscheiden(antwort(art="notiz", ziel="oberflaeche"), fb.Lage())[0], True)

    def test_nie_automatisch(self):
        gut = fb.Lage(kosten_usd=0.6, dienst_da=True)
        nb = antwort(art="nachbesserung", auftrag="kürzer")
        self.assertTrue(fb.entscheiden(nb, gut)[0])
        faelle = [
            (antwort(heikel=True, heikel_grund="Datenschutz"), gut, "Datenschutz"),
            (antwort(widerspricht="Lieber kurz"), gut, "widerspricht"),
            (nb, fb.Lage(nachbesserungen_bisher=1, kosten_usd=0.6, dienst_da=True), "schon eine"),
            (nb, fb.Lage(kosten_usd=None, dienst_da=True), "unbekannt"),
            (nb, fb.Lage(kosten_usd=2.1, dienst_da=True), "2.10 USD"),
            (nb, fb.Lage(kosten_usd=0.6, dienst_da=False), "keinen Dienst"),
        ]
        for z, lage, grund in faelle:
            with self.subTest(grund=grund):
                ok, text = fb.entscheiden(z, lage)
                self.assertFalse(ok)
                self.assertIn(grund, text)


class TestTexte(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo, self.instanz, self.agenten = self.tmp, self.tmp / "lia" / "instanz", self.tmp / "lia"

    def test_ziel_datei(self):
        z = antwort()
        self.assertEqual(fb.ziel_datei(z, self.instanz, self.agenten, self.repo), (self.instanz / "regeln.md", "## Regeln"))
        self.assertEqual(fb.ziel_datei(antwort(ziel="recherche"), self.instanz, self.agenten, self.repo),
                         (self.agenten / "recherche" / "STATUS.md", "## Gelernte Regeln"))
        self.assertEqual(fb.ziel_datei(antwort(art="notiz", ziel="oberflaeche"), self.instanz, self.agenten, self.repo),
                         (self.repo / "STATUS.md", "## Wünsche aus Feedback"))
        self.assertIsNone(fb.ziel_datei(antwort(art="keine"), self.instanz, self.agenten, self.repo))

    def test_zusammenfassung_mit_stopp(self):
        z = antwort()
        ziel = fb.ziel_datei(z, self.instanz, self.agenten, self.repo)
        text, knoepfe = fb.zusammenfassung("Lia", "recherche", "Bitte immer erst die Empfehlung", z, True, "",
                                           fb.wirkung_text(z, ziel, self.repo))
        self.assertEqual(text, "Lia zu recherche: „Bitte immer erst die Empfehlung“\nLia will es kürzer.\n"
                               "Art: Regel (dauerhaft), für alle Agenten von Lia\n"
                               "Passiert: „Ergebnisse beginnen mit einer Empfehlung.“ in lia/instanz/regeln.md")
        self.assertEqual(knoepfe, [["Stopp"]])

    def test_vorschlag_mit_zwei_knoepfen(self):
        z = antwort(art="nachbesserung", auftrag="kürzer")
        text, knoepfe = fb.zusammenfassung("Lia", "unterricht", "zu lang", z, False, "Kosten unbekannt",
                                           fb.wirkung_text(z, None, self.repo))
        self.assertIn("Nicht automatisch übernommen: Kosten unbekannt", text)
        self.assertIn("Vorschlag: neuer Auftrag an den Agenten: kürzer", text)
        self.assertEqual(knoepfe, [["Übernehmen", "Verwerfen"]])

    def test_bestaetigungen(self):
        self.assertIn("Ab jetzt gilt: Ergebnisse beginnen", fb.bestaetigung(antwort(), True))
        self.assertIn("Nachbesserung läuft", fb.bestaetigung(antwort(art="nachbesserung"), True))
        self.assertIn("für später notiert", fb.bestaetigung(antwort(art="notiz"), True))
        self.assertIn("Jan zur Entscheidung", fb.bestaetigung(antwort(), False))
        fall = {"feedback": "zu lang", "zuordnung": antwort()}
        self.assertIn("zurückgenommen: Regel entfernt", fb.stopp_text(fall, "Regel entfernt"))
        self.assertIn("übernommen. Danke, übernommen.", fb.entscheidung_text(fall, True))
        self.assertIn("nicht zu übernehmen", fb.entscheidung_text(fall, False))

    def test_agenten_und_index(self):
        for name in ("uni", "dokumente", "Kaputt"):
            (self.tmp / name).mkdir()
            (self.tmp / name / "STATUS.md").write_text("x")
        (self.tmp / "shared").mkdir()
        self.assertEqual(fb.agenten(self.tmp), ["dokumente", "uni"])
        index = fb.Index(self.tmp / "data" / "meldungen.json")
        self.assertIsNone(index.finden("m1"))
        index.merken("m1", self.instanz, "f1")
        self.assertEqual(index.finden("m1"), {"instanz": str(self.instanz), "feedback_id": "f1"})


if __name__ == "__main__":
    unittest.main()
