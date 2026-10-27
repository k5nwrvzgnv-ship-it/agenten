import unittest

import portal_logik as p


def alle_daten(knoepfe):
    return [d for zeile in knoepfe for _, d in zeile]


class AnsichtenTest(unittest.TestCase):
    def test_alle_knoepfe_gueltig_und_kurz(self):
        ansichten = [
            p.ansicht_home(1, 2, "Hinweis"), p.ansicht_anleitung("material"), p.ansicht_anleitung("frage"),
            p.ansicht_bestaetigen({"art": "material", "text": "x"}), p.ansicht_einordnen("x"),
            p.ansicht_anfragen([]), p.ansicht_hilfe(), ("", p.MENUE_KNOPF), p.ansicht_dateien(2),
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

    def test_dateien_text(self):
        self.assertEqual(p.dateien_text(1, True), "Das ist die Datei.")
        self.assertIn("2 Dateien", p.dateien_text(2, True))
        self.assertIn("Jan", p.dateien_text(2, False))

    def test_ergebnis_mit_bezug(self):
        [text] = p.ergebnis_nachricht({"status": "erledigt", "ergebnis": "Kommt bald.", "text": "Arbeitsblatt Kant"})
        self.assertIn("Arbeitsblatt Kant", text)
        self.assertTrue(text.endswith("Kommt bald."))
        self.assertIn(p.FEHLGESCHLAGEN, p.ergebnis_nachricht({"status": "fehlgeschlagen", "text": "x"})[0])
        # der Grund des Agenten kommt bei Lia an (Bedarf aus lia/unterricht)
        self.assertIn("ab 14:00", p.ergebnis_nachricht({"status": "fehlgeschlagen", "text": "x",
                                                        "ergebnis": "Kontingent aufgebraucht, ab 14:00"})[0])

    def test_feedback_zustand(self):
        z = {"wartet_auf": "material"}
        p.feedback_gewaehlt(z, "20261027-120000-unterricht-abcdef", "fokus")
        self.assertEqual(z, {"feedback": {"bezug": "20261027-120000-unterricht-abcdef", "k": "fokus"}})
        self.assertEqual(p.text_eingang(z, "mehr Fälle"), "feedback")
        self.assertIn("feedback", z)  # portal.py nimmt es heraus
        p.anleitung_gewaehlt(z, "frage")
        self.assertNotIn("feedback", z)

    def test_feedback_knoepfe_nur_bei_ergebnissen(self):
        a = {"id": "20261027-120000-unterricht-abcdef", "agent": "unterricht", "status": "erledigt"}
        self.assertEqual(len(p.ergebnis_knoepfe(a)), 2)
        self.assertEqual(p.ergebnis_knoepfe({**a, "status": "fehlgeschlagen"}), p.MENUE_KNOPF)
        self.assertEqual(p.ergebnis_knoepfe({**a, "agent": "feedback"}), p.MENUE_KNOPF)
        self.assertEqual(p.fuer_lia([a, {**a, "agent": "feedback"}, {**a, "status": "zurueckgezogen"}]), [a])

    def test_dateien(self):
        text, _ = p.ansicht_bestaetigen({"art": "material", "text": "Mach daraus ein Arbeitsblatt"}, 2)
        self.assertIn("Mit 2 Dateien.", text)
        self.assertNotIn("Mit", p.ansicht_bestaetigen({"art": "material", "text": "x"})[0])
        text, knoepfe = p.ansicht_dateien(1)
        self.assertIn("1 Datei liegt bereit", text)
        self.assertIn("verwerfen", p.knopf_auswerten(knoepfe[0][0][1]))
        self.assertEqual(p.hinweis_dateien(0), "")
        self.assertIn("2 Dateien liegen bereit und kommen", p.hinweis_dateien(2))
        self.assertIn("Dateien", p.HILFE)


if __name__ == "__main__":
    unittest.main()
