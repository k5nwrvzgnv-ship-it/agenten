import unittest

import portal_logik as p


class PortalLogikTest(unittest.TestCase):
    def test_menue_hat_drei_knoepfe_ohne_schraegstrich(self):
        knoepfe = [z[0] for z in p.menue_knoepfe()]
        self.assertEqual([t for t, _ in knoepfe], ["Neues Material", "Meine Woche", "Frage stellen"])
        for _, daten in knoepfe:
            self.assertLessEqual(len(daten.encode()), 64)
            self.assertIsNotNone(p.knopf_auswerten(daten))

    def test_knopf_auswerten(self):
        self.assertEqual(p.knopf_auswerten("p:ja"), "ja")
        self.assertEqual(p.knopf_auswerten("p:menue"), "menue")
        self.assertIsNone(p.knopf_auswerten("p:text"))  # nicht im Menü
        self.assertIsNone(p.knopf_auswerten("f:123"))

    def test_material_fragt_nach_dann_bestaetigen(self):
        z = {}
        text, bestaetigen = p.menue_gewaehlt(z, "material")
        self.assertFalse(bestaetigen)
        self.assertIn("Fach", text)
        rueckfrage = p.text_eingang(z, "  Arbeitsblatt Kant, Klasse 10 ")
        self.assertIn("Neues Material", rueckfrage)
        self.assertNotIn("wartet_auf", z)
        self.assertEqual(p.entwurf_nehmen(z), {"art": "material", "text": "Arbeitsblatt Kant, Klasse 10"})
        self.assertIsNone(p.entwurf_nehmen(z))  # Doppelklick

    def test_woche_sofort_bestaetigen(self):
        z = {"wartet_auf": "frage"}
        _, bestaetigen = p.menue_gewaehlt(z, "woche")
        self.assertTrue(bestaetigen)
        self.assertNotIn("wartet_auf", z)
        self.assertEqual(z["entwurf"]["art"], "woche")

    def test_text_ohne_menue(self):
        z = {}
        self.assertIn("Nachricht", p.text_eingang(z, "Hallo"))
        self.assertEqual(z["entwurf"]["art"], "text")

    def test_neuer_menueknopf_verwirft_alten_entwurf(self):
        z = {}
        p.text_eingang(z, "alt")
        p.menue_gewaehlt(z, "frage")
        self.assertNotIn("entwurf", z)

    def test_ergebnis_text(self):
        self.assertEqual(p.ergebnis_text({"status": "erledigt", "ergebnis": "Kommt bald."}), "Kommt bald.")
        self.assertEqual(p.ergebnis_text({"status": "fehlgeschlagen", "ergebnis": "Traceback"}), p.FEHLGESCHLAGEN)


if __name__ == "__main__":
    unittest.main()
