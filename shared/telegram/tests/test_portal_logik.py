import unittest

import portal_logik as p


def alle_daten(knoepfe):
    return [d for zeile in knoepfe for _, d in zeile]


class AnsichtenTest(unittest.TestCase):
    def test_alle_knoepfe_gueltig_und_kurz(self):
        ansichten = [
            p.ansicht_home(1, 2, "Hinweis"), p.ansicht_anleitung("material"), p.ansicht_anleitung("frage"),
            p.ansicht_bestaetigen({"art": "material", "text": "x"}), p.ansicht_einordnen("x"),
            p.ansicht_anfragen([]), p.ansicht_hilfe(), ("", p.MENUE_KNOPF),
        ]
        for _, knoepfe in ansichten:
            for daten in alle_daten(knoepfe):
                self.assertLessEqual(len(daten.encode()), 64)
                self.assertIsNotNone(p.knopf_auswerten(daten), daten)

    def test_home_zeigt_zahlen_und_hinweis(self):
        text, knoepfe = p.ansicht_home(1, 3, "Ist unterwegs.")
        self.assertIn("Unterwegs: 1", text)
        self.assertIn("Fertig: 3", text)
        self.assertIn("Ist unterwegs.", text)
        self.assertIn(p.IM_AUFBAU, text)
        beschriftungen = [t for zeile in knoepfe for t, _ in zeile]
        for name in ("Neues Material", "Meine Woche", "Frage stellen", "Meine Anfragen"):
            self.assertIn(name, beschriftungen)

    def test_anfragen_neueste_zuerst_ohne_technik(self):
        auftraege = [
            {"id": "20261021-100000-unterricht-aaaaaa", "text": "Alt", "status": "erledigt", "quelle": "portal-frage"},
            {"id": "20261021-110000-unterricht-bbbbbb", "text": "Neu", "status": "neu", "quelle": "portal-material"},
        ]
        text, _ = p.ansicht_anfragen(auftraege)
        self.assertLess(text.index("Neu"), text.index("Alt"))
        self.assertIn("Neues Material: Neu – unterwegs", text)
        self.assertIn("Frage stellen: Alt – fertig", text)
        self.assertNotIn("unterricht", text)

    def test_knopf_auswerten(self):
        self.assertEqual(p.knopf_auswerten("p:ja"), "ja")
        self.assertIsNone(p.knopf_auswerten("p:text"))
        self.assertIsNone(p.knopf_auswerten("f:123"))


class AblaufTest(unittest.TestCase):
    def test_material_anleitung_dann_bestaetigen(self):
        z = {}
        p.anleitung_gewaehlt(z, "material")
        self.assertEqual(p.text_eingang(z, "  Arbeitsblatt Kant, Klasse 10 "), "bestaetigen")
        self.assertNotIn("wartet_auf", z)
        self.assertEqual(p.entwurf_nehmen(z), {"art": "material", "text": "Arbeitsblatt Kant, Klasse 10"})
        self.assertIsNone(p.entwurf_nehmen(z))  # Doppelklick

    def test_gruss_zeigt_menue_statt_auftrag(self):
        for gruss in ("hallo", "Hallo!", "moin", "Guten Morgen", "start"):
            z = {}
            self.assertEqual(p.text_eingang(z, gruss), "home", gruss)
            self.assertNotIn("entwurf", z)

    def test_gruss_waehrend_anleitung_ist_inhalt(self):
        z = {}
        p.anleitung_gewaehlt(z, "frage")
        self.assertEqual(p.text_eingang(z, "Hallo"), "bestaetigen")

    def test_freitext_einordnen(self):
        z = {}
        self.assertEqual(p.text_eingang(z, "Was ist Ethik?"), "einordnen")
        self.assertTrue(p.einordnen(z, "frage"))
        self.assertEqual(p.entwurf_nehmen(z)["art"], "frage")
        self.assertFalse(p.einordnen(z, "frage"))  # alter Knopf

    def test_woche_sofort(self):
        z = {"wartet_auf": "frage", "entwurf": {"art": "text", "text": "x"}}
        entwurf = p.sofort_entwurf(z, "woche")
        self.assertEqual(entwurf["art"], "woche")
        self.assertEqual(z, {})

    def test_abbrechen(self):
        z = {"wartet_auf": "frage", "entwurf": {}}
        p.abbrechen(z)
        self.assertEqual(z, {})

    def test_ergebnis_mit_bezug(self):
        text = p.ergebnis_text({"status": "erledigt", "ergebnis": "Kommt bald.", "text": "Arbeitsblatt Kant"})
        self.assertIn("Arbeitsblatt Kant", text)
        self.assertTrue(text.endswith("Kommt bald."))
        self.assertIn(p.FEHLGESCHLAGEN, p.ergebnis_text({"status": "fehlgeschlagen", "text": "x"}))


if __name__ == "__main__":
    unittest.main()
