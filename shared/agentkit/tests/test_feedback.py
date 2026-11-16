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


class TestHeikleWoerter(unittest.TestCase):
    """Untersuchung 11/2026, B11: feste Wortliste als Rückhalt, auch wenn Claude heikel=false setzt."""

    HEIKEL = (
        "Mails an Dozenten künftig ohne Rückfrage senden.",
        "Antworten an die Verwaltung direkt abschicken.",
        "Bücher unter 20 Euro einfach kaufen.",
        "Das Limit für Käufe auf 100 anheben.",
        "Entwürfe für Termine brauchen keine Freigabe mehr.",
        "Hausarbeiten nach dem Korrekturlesen selbst einreichen.",
        "Nenne in Auswertungen die Namen der Schüler mit Note.",
        "Schülerdaten dürfen in die Zusammenfassung.",
        "Die Regel zu kurzen Sätzen bitte streichen.",
        "Bestelle Verbrauchsmaterial nach, wenn es fehlt.",
        "Lösche die alte Regel zum Datenschutz.",
        "Verschicke die Wochenübersicht an alle Kollegen.",
    )
    HARMLOS = (
        "Antworte kürzer und ohne Aufzählungen.",
        "Arbeitsblätter für die Klasse 8 höchstens eine Seite.",
        "Fälle sollen aus der Lebenswelt der Schüler kommen.",
        "Quellen immer mit Seite angeben.",
        "Mail-Entwürfe mit „Viele Grüße“ beenden.",
        "Schreib das Ergebnis als Tabelle.",
    )

    def test_heikle_saetze_werden_vorschlag_trotz_heikel_false(self):
        lage = fb.Lage(kosten_usd=0.1, dienst_da=True)
        for satz in self.HEIKEL:
            for z in (antwort(regel=satz, heikel=False), antwort(art="nachbesserung", auftrag=satz, heikel=False)):
                ok, grund = fb.entscheiden(z, lage)
                self.assertFalse(ok, satz)
                self.assertIn("Stichwort", grund)

    def test_harmlose_saetze_laufen_durch(self):
        lage = fb.Lage(kosten_usd=0.1, dienst_da=True)
        for satz in self.HARMLOS:
            self.assertEqual(fb.heikles_wort(antwort(regel=satz)), "", satz)
            self.assertTrue(fb.entscheiden(antwort(regel=satz), lage)[0], satz)

    def test_notiz_und_keine_sind_nicht_betroffen(self):
        self.assertEqual(fb.heikles_wort(antwort(art="notiz", ziel="oberflaeche", notiz="Knopf zum Senden fehlt")), "")
        self.assertEqual(fb.heikles_wort(antwort(art="keine", regel="", auftrag="senden")), "")


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
            (nb, fb.Lage(kosten_usd=None, dienst_da=True), "weiß nicht"),
            (nb, fb.Lage(kosten_usd=2.1, dienst_da=True), "mehr Rechenzeit"),
            (nb, fb.Lage(kosten_usd=0.6, dienst_da=False), "nicht eingerichtet"),
        ]
        for z, lage, grund in faelle:
            with self.subTest(grund=grund):
                ok, text = fb.entscheiden(z, lage)
                self.assertFalse(ok)
                self.assertIn(grund, text)

    def test_ohne_grenzen_fuer_lia(self):
        nb = antwort(art="nachbesserung", auftrag="kürzer")
        for lage in (fb.Lage(nachbesserungen_bisher=3, kosten_usd=2.1, dienst_da=True, grenzen=False),
                     fb.Lage(kosten_usd=None, dienst_da=True, grenzen=False)):
            self.assertEqual(fb.entscheiden(nb, lage), (True, ""))
        faelle = [
            (nb, fb.Lage(dienst_da=False, grenzen=False), "nicht eingerichtet"),
            (antwort(heikel=True, heikel_grund="Schülerdaten"), fb.Lage(grenzen=False), "Schülerdaten"),
            (antwort(widerspricht="Lieber kurz"), fb.Lage(grenzen=False), "widerspricht"),
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
        text, knoepfe = fb.zusammenfassung("Lia", "recherche", "Bitte immer erst die Empfehlung", z, True, "")
        self.assertEqual(text, "Feedback von Lia zu Recherche: „Bitte immer erst die Empfehlung“\n"
                               "Ab jetzt gilt für alles von Lia: „Ergebnisse beginnen mit einer Empfehlung.“")
        self.assertEqual(knoepfe, [["Stopp"]])

    def test_vorschlag_mit_zwei_knoepfen(self):
        z = antwort(art="nachbesserung", auftrag="kürzer")
        text, knoepfe = fb.zusammenfassung("Lia", "unterricht", "zu lang", z, False, "Grund")
        self.assertIn("Das übernehme ich nicht von selbst, denn Grund.", text)
        self.assertIn("Mein Vorschlag: Unterricht schickt eine überarbeitete Fassung: „kürzer“", text)
        self.assertEqual(knoepfe, [["Übernehmen", "Verwerfen"]])

    def test_bestaetigungen(self):
        self.assertIn("Ab jetzt gilt: „Ergebnisse beginnen", fb.bestaetigung(antwort(), True))
        self.assertIn("mache das Ergebnis jetzt noch einmal", fb.bestaetigung(antwort(art="nachbesserung"), True))
        self.assertIn("notiert", fb.bestaetigung(antwort(art="notiz"), True))
        self.assertEqual("Danke, ist angekommen.", fb.bestaetigung(antwort(art="keine"), True))
        self.assertIn("Jan zur Entscheidung", fb.bestaetigung(antwort(), False))
        fall = {"feedback": "zu lang", "zuordnung": antwort()}
        self.assertEqual("Jan nimmt dein Feedback „zu lang“ zurück. Gilt nicht mehr.", fb.stopp_text(fall, "Gilt nicht mehr."))
        self.assertIn("angenommen. Ab jetzt gilt:", fb.entscheidung_text(fall, True))
        self.assertIn("Es bleibt alles, wie es ist.", fb.entscheidung_text(fall, False))

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



class TestNurLernen(unittest.TestCase):
    def test_erkennen(self):
        self.assertTrue(fb.nur_lernen({"felder": {"feedback_modus": "nur_lernen"}}))
        for a in ({}, {"felder": None}, {"felder": {"feedback_modus": "anders"}}):
            self.assertFalse(fb.nur_lernen(a))

    def test_nachbesserung_wird_keine(self):
        z = {"art": "nachbesserung", "auftrag": "Kürzer.", "regel": ""}
        self.assertEqual(fb.fuer_nur_lernen(z), {"art": "keine", "auftrag": "", "regel": ""})
        regel = {"art": "regel", "auftrag": "", "regel": "Kurz."}
        self.assertIs(fb.fuer_nur_lernen(regel), regel)

    def test_prompt_mit_hinweis(self):
        args = ("Lia", "unterricht", {"text": "Blatt"}, "einfacher", "", ["unterricht"])
        self.assertNotIn("schon gemacht", fb.prompt(*args))
        text = fb.prompt(*args, lernen=True)
        self.assertTrue(text.rstrip().endswith("Ergebnis betrifft."))
        self.assertIn('Wähle darum nie "nachbesserung"', text)


if __name__ == "__main__":
    unittest.main()
