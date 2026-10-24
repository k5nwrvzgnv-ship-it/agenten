import unittest

import gemeinfrei


def text(**felder):
    return {"art": "primaertext", "autor": "A", "todesjahr_autor": 1804, **felder}


class GemeinfreiTest(unittest.TestCase):
    def test_gesetz(self):
        e = gemeinfrei.pruefen({"art": "gesetz"}, 2026)
        self.assertEqual(e["status"], "frei")
        self.assertTrue(e["verwendbar"])
        self.assertIn("§ 5", e["begruendung"])

    def test_autor_lange_tot(self):
        e = gemeinfrei.pruefen(text(), 2026)
        self.assertEqual((e["status"], e["verwendbar"]), ("frei", True))
        self.assertIn("A gest. 1804", e["begruendung"])

    def test_grenze_70_volle_jahre(self):
        self.assertEqual(gemeinfrei.pruefen(text(todesjahr_autor=1955), 2026)["status"], "frei")
        self.assertEqual(gemeinfrei.pruefen(text(todesjahr_autor=1956), 2026)["status"], "nicht_frei")
        self.assertEqual(gemeinfrei.pruefen(text(todesjahr_autor=1956), 2027)["status"], "frei")

    def test_herausgeber_geschuetzt(self):
        e = gemeinfrei.pruefen(text(herausgeber="H", herausgeber_todesjahr=1990), 2026)
        self.assertEqual((e["status"], e["verwendbar"]), ("nicht_frei", False))
        self.assertIn("Herausgeber H gest. 1990, geschützt bis Ende 2060", e["begruendung"])

    def test_uebersetzer_frei(self):
        e = gemeinfrei.pruefen(text(uebersetzer="U", uebersetzer_todesjahr=1900), 2026)
        self.assertEqual(e["status"], "frei")
        self.assertIn("Übersetzer U", e["begruendung"])

    def test_herausgeber_leer_ist_ungeklaert(self):
        e = gemeinfrei.pruefen(text(herausgeber=""), 2026)
        self.assertEqual((e["status"], e["verwendbar"]), ("ungeklaert", False))
        self.assertIn("Herausgeber nicht geklärt", e["begruendung"])

    def test_todesjahr_fehlt(self):
        e = gemeinfrei.pruefen({"art": "primaertext", "autor": "A"}, 2026)
        self.assertEqual(e["status"], "ungeklaert")
        self.assertIn("Todesjahr fehlt", e["begruendung"])

    def test_geschuetzt_geht_vor_ungeklaert(self):
        e = gemeinfrei.pruefen(text(todesjahr_autor=2000, herausgeber=""), 2026)
        self.assertEqual(e["status"], "nicht_frei")

    def test_zeitschriftenaufsatz_ohne_herausgeber(self):
        e = gemeinfrei.pruefen(text(todesjahr_autor=1919, herausgeber_entfaellt="Zeitschriftenaufsatz"), 2026)
        self.assertEqual((e["status"], e["verwendbar"]), ("frei", True))
        self.assertIn("kein Herausgeber (Zeitschriftenaufsatz)", e["begruendung"])

    def test_nur_entfaellt_ohne_autor_ist_ungeklaert(self):
        e = gemeinfrei.pruefen({"art": "primaertext", "herausgeber_entfaellt": "Zeitschriftenaufsatz"}, 2026)
        self.assertEqual(e["status"], "ungeklaert")

    def test_entfaellt_schuetzt_nicht_vor_geschuetztem_autor(self):
        e = gemeinfrei.pruefen(text(todesjahr_autor=1990, herausgeber_entfaellt="Aufsatz"), 2026)
        self.assertEqual(e["status"], "nicht_frei")

    def test_ohne_personen(self):
        self.assertEqual(gemeinfrei.pruefen({"art": "primaertext"}, 2026)["status"], "ungeklaert")


if __name__ == "__main__":
    unittest.main()
