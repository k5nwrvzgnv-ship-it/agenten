import unittest

import portal_logik as p


def alle_daten(knoepfe):
    return [d for zeile in knoepfe for _, d in zeile]


class AnsichtenTest(unittest.TestCase):
    def test_alle_knoepfe_gueltig_und_kurz(self):
        ansichten = [
            p.ansicht_home(1, 2, "Hinweis"), p.ansicht_home(1, 2, "Hinweis", True), p.ansicht_anleitung("material"),
            p.ansicht_anfragen([]), p.ansicht_hilfe(), ("", p.MENUE_KNOPF), p.ansicht_dateien(2),
        ]
        for _, knoepfe in ansichten:
            for daten in alle_daten(knoepfe):
                self.assertLessEqual(len(daten.encode()), 64)
                self.assertIsNotNone(p.knopf_auswerten(daten), daten)

    def test_home_zeigt_zahlen_und_hinweis(self):
        text, knoepfe = p.ansicht_home(1, 3, "Ist unterwegs.")
        self.assertIn("In Arbeit: 1", text)
        self.assertIn("Fertig: 3", text)
        self.assertIn("Ist unterwegs.", text)
        beschriftungen = [t for zeile in knoepfe for t, _ in zeile]
        self.assertEqual(beschriftungen, ["Neues Material", "Meine Anfragen", "Hilfe"])  # höchstens drei (B10)
        for weg in ("Meine Woche", "Frage stellen", "Aktualisieren", "gibt es bald"):
            self.assertNotIn(weg, text + " ".join(beschriftungen))

    def test_home_nach_abschicken_mit_zurueckziehen(self):
        _, knoepfe = p.ansicht_home(1, 3, "Ich mache mich an …", zurueckziehbar=True)
        self.assertEqual(knoepfe[0], [("↩ Zurückziehen", "p:zurueck")])
        self.assertNotIn("p:zurueck", alle_daten(p.ansicht_home(1, 3)[1]))

    def test_hilfe_ohne_platzhalter(self):
        for weg in ("Meine Woche", "Frage stellen", "frage ich"):
            self.assertNotIn(weg, p.HILFE)

    def test_anfragen_neueste_zuerst_ohne_technik(self):
        auftraege = [
            {"id": "20261021-100000-unterricht-aaaaaa", "text": "Alt", "status": "erledigt", "quelle": "portal-frage"},
            {"id": "20261021-110000-unterricht-bbbbbb", "text": "Neu", "status": "neu", "quelle": "portal-material"},
        ]
        text, _ = p.ansicht_anfragen(auftraege)
        self.assertLess(text.index("Neu"), text.index("Alt"))
        self.assertIn("Neues Material: „Neu“ – in Arbeit", text)
        self.assertIn("Nachricht: „Alt“ – fertig", text)  # alte Art ohne eigenen Knopf
        self.assertNotIn("unterricht", text)

    def test_knopf_auswerten(self):
        self.assertEqual(p.knopf_auswerten("p:material"), "material")
        for alt in ("ja", "nein", "woche", "frage", "alsmaterial", "alsfrage", "neu"):  # alte Knöpfe: veraltet
            self.assertIsNone(p.knopf_auswerten(f"p:{alt}"), alt)
        self.assertIsNone(p.knopf_auswerten("p:text"))
        self.assertIsNone(p.knopf_auswerten("f:123"))


class AblaufTest(unittest.TestCase):
    def test_material_anleitung_dann_sofort_los(self):
        z = {}
        p.anleitung_gewaehlt(z, "material")
        self.assertEqual(p.text_eingang(z, "  Arbeitsblatt Kant, Klasse 10 "), "abschicken")
        self.assertNotIn("wartet_auf", z)
        self.assertEqual(p.entwurf_nehmen(z), {"art": "material", "text": "Arbeitsblatt Kant, Klasse 10"})
        self.assertIsNone(p.entwurf_nehmen(z))  # nur einmal

    def test_gruss_zeigt_menue_statt_auftrag(self):
        for gruss in ("hallo", "Hallo!", "moin", "Guten Morgen", "start"):
            z = {}
            self.assertEqual(p.text_eingang(z, gruss), "home", gruss)
            self.assertNotIn("entwurf", z)

    def test_gruss_waehrend_anleitung_ist_inhalt(self):
        z = {}
        p.anleitung_gewaehlt(z, "material")
        self.assertEqual(p.text_eingang(z, "Hallo"), "abschicken")

    def test_freitext_ohne_rueckfrage(self):
        """B10: ein Schritt statt drei. Text ohne Menü ist ein Materialwunsch und geht sofort los."""
        z = {}
        self.assertEqual(p.text_eingang(z, "Kannst du mir einen Fall zu Strafe für Klasse 8 machen?"), "abschicken")
        entwurf = p.entwurf_nehmen(z)
        self.assertEqual(entwurf["art"], "material")
        self.assertEqual(p.ARTEN[entwurf["art"]].quelle, "portal-material")
        self.assertEqual(z, {})

    def test_abbrechen(self):
        z = {"wartet_auf": "material", "entwurf": {}, "letzter": "x"}
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
        p.anleitung_gewaehlt(z, "material")
        self.assertNotIn("feedback", z)

    def test_feedback_knoepfe_nur_bei_ergebnissen(self):
        a = {"id": "20261027-120000-unterricht-abcdef", "agent": "unterricht", "status": "erledigt"}
        self.assertEqual(len(p.ergebnis_knoepfe(a)), 2)
        self.assertEqual(p.ergebnis_knoepfe({**a, "status": "fehlgeschlagen"}), p.MENUE_KNOPF)
        self.assertEqual(p.ergebnis_knoepfe({**a, "agent": "feedback"}), p.MENUE_KNOPF)
        nur_antwort = {**a, "daten": {"kern": "Dossier", "knoepfe": "nur_antwort"}}
        self.assertEqual(p.ergebnis_knoepfe(nur_antwort), p.MENUE_KNOPF)
        self.assertTrue(p.mit_feedback(nur_antwort))  # Lias Antwort darauf bleibt Feedback
        self.assertEqual(len(p.ergebnis_knoepfe({**a, "daten": {"knoepfe": "unbekannt"}})), 2)
        self.assertEqual(p.fuer_lia([a, {**a, "agent": "feedback"}, {**a, "status": "zurueckgezogen"}]), [a])

    def test_dateien(self):
        self.assertIn("(mit 2 Dateien)", p.unterwegs("Mach daraus ein Arbeitsblatt", 2))
        text, knoepfe = p.ansicht_dateien(1)
        self.assertIn("1 Datei liegt bereit", text)
        self.assertIn("verwerfen", p.knopf_auswerten(knoepfe[0][0][1]))
        self.assertEqual(p.hinweis_dateien(0), "")
        self.assertIn("2 Dateien liegen bereit und kommen", p.hinweis_dateien(2))
        self.assertIn("Dateien", p.HILFE)


if __name__ == "__main__":
    unittest.main()
