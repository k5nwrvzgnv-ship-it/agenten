import unittest

import stueck

ANMERKUNG = ("Anmerkung: Was Sie gerade lesen ist eine Ansichtssendung, ausschließlich Ihnen überlassen,\n"
             "damit Sie prüfen können. Einen vollständigen Rollensatz erhalten Sie beim DEUTSCHEN\n"
             "THEATERVERLAG, Grabengasse 5, 69469 Weinheim\n")
FUSS = "Probeexemplar für Schule, Kurs DS. Alle Rechte sind vorbehalten.\n"

TEXT = (
    "--- Seite 1\nPERSONEN\nDOTTY OTLEY\n" + FUSS +
    "--- Seite 6\n4\nERSTER AKT\nDas Wohnzimmer.\n"
    "Mrs Clackett Ja, ja, bimmel du nur.\n"
    "(Stellt die Sardinen ab.)\n"
    "Hallo... Ja, aber es ist niemand\nhier.\n"
    "Die Stimme von LLOYD DALLAS erwidert\naus dem Dunkel.\n"
    "LLOYD: Du lässt die Sardinen stehen.\n"
    "DOTTY: Ich lass die Sardinen ste-\nhen? (Beginnt,\n" + ANMERKUNG + "abzugehen) Ach so.\n"
    + FUSS +
    "--- Seite 7\n5\nMRS.C.: Squire, Squire.\n77\nZWEITER AKT\nHinter der Bühne.\n"
    "POPPY: (über Lautsprecher) Zum Ersten Akt bitte.\n"
    "TIM: Meinst du?\nAuftritt BELINDA.\n"
    "BELINDA: Schätzchen!\n" + FUSS +
    "--- Seite 8\n6\nDRITTER\nAKT\nSELSDON: Letzter Satz?\nALLE: Vorhang!\n" + FUSS
)


class Zerlegen(unittest.TestCase):
    def setUp(self):
        self.e = stueck.zerlegen(TEXT)

    def test_akte_und_nummern(self):
        self.assertEqual([x.nr for x in self.e], list(range(1, len(self.e) + 1)))
        self.assertEqual(set(stueck.akt_grenzen(self.e)), {1, 2, 3})
        self.assertEqual(self.e[0].text, "ERSTER AKT Das Wohnzimmer.")  # Ortsangabe gehört zur Aktüberschrift

    def test_vor_akt_eins_nichts(self):
        self.assertFalse(any("PERSONEN" in x.text or "OTLEY" in x.text for x in self.e))

    def test_fuss_anmerkung_und_seitenzahl_weg(self):
        alles = " ".join(x.text for x in self.e)
        for rest in ("Probeexemplar", "Ansichtssendung", "Weinheim", " 77"):
            self.assertNotIn(rest, alles)

    def test_anmerkung_mitten_in_zeile(self):
        dotty = next(x for x in self.e if x.sprecher == "DOTTY" and x.typ == "rede")
        self.assertEqual(dotty.text, "Ich lass die Sardinen stehen? (Beginnt, abzugehen) Ach so.")

    def test_sprecher_und_rollen(self):
        reden = [(x.sprecher, x.text) for x in self.e if x.typ == "rede"]
        self.assertIn(("MRS CLACKETT", "Ja, ja, bimmel du nur."), reden)
        self.assertIn(("MRS CLACKETT", "Squire, Squire."), reden)
        self.assertIn(("ALLE", "Vorhang!"), reden)

    def test_regie_mit_und_ohne_klammer(self):
        regie = [x.text for x in self.e if x.typ == "regie"]
        self.assertIn("(Stellt die Sardinen ab.)", regie)
        self.assertIn("Die Stimme von LLOYD DALLAS erwidert aus dem Dunkel.", regie)
        self.assertIn("Auftritt BELINDA.", regie)

    def test_text_nach_regie_mit_letztem_sprecher(self):
        x = next(x for x in self.e if x.text.startswith("Hallo"))
        self.assertEqual((x.typ, x.sprecher, x.text), ("text", "MRS CLACKETT", "Hallo... Ja, aber es ist niemand hier."))

    def test_seiten_gedruckt_und_pdf(self):
        x = next(x for x in self.e if x.sprecher == "SELSDON")
        self.assertEqual((x.seite, x.pdf_seite, x.akt), (6, 8, 3))

    def test_fehlender_akt(self):
        with self.assertRaises(stueck.StueckFehler):
            stueck.zerlegen(TEXT.split("DRITTER")[0])


class Hilfen(unittest.TestCase):
    def test_sprechminuten_ohne_regie(self):
        e = [stueck.Einheit(1, 1, 1, 1, "rede", "TIM", "wort " * 130), stueck.Einheit(2, 1, 1, 1, "regie", "", "x " * 500)]
        self.assertAlmostEqual(stueck.sprechminuten(e), 1.0)

    def test_nummeriert_teile_und_kopf(self):
        e = stueck.zerlegen(TEXT)
        teile = stueck.nummeriert(e, max_zeichen=120)
        self.assertGreater(len(teile), 1)
        alles = "\n".join(teile)
        for x in e:
            self.assertIn(f"[{x.nr}] ", alles)
        self.assertTrue(teile[0].startswith("=== AKT 1 ===\n--- S. 4"))
        self.assertIn("LLOYD: Du lässt", alles)

    def test_dicts_hin_und_zurueck(self):
        e = stueck.zerlegen(TEXT)
        self.assertEqual(stueck.aus_dicts(stueck.als_dicts(e)), e)


if __name__ == "__main__":
    unittest.main()
