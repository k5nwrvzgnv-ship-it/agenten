import unittest
from datetime import date

import formulare
from angaben import Angaben
from tests.hilfe import beispiel

TAG = date(2026, 11, 10)


def nach_schluessel(s):
    return next(f for f in formulare.FORMULARE if f.schluessel == s)


def felder(s, a):
    return nach_schluessel(s).felder(a, TAG)


class TestPersonalfragebogen(unittest.TestCase):
    def test_ledig(self):
        w = felder("fin770", beispiel())
        self.assertEqual(w["Kontrollkästchen4"], "/Ja")
        self.assertNotIn("Datum", w)
        self.assertEqual(w["Text63"], "01.02.1995")
        self.assertEqual(w["Kontrollkästchen21"], "/Ja")  # nicht schwerbehindert
        self.assertEqual(w["Kontrollkästchen26"], "/Ja")  # Häftlingshilfe: nein (nach 1990 geboren)
        self.assertEqual(w["Kontrollkästchen48"], "/Ja")
        self.assertNotIn("Kontrollkästchen35", w)  # 2. Staatsprüfung noch nicht

    def test_verheiratet_mit_kind(self):
        a = beispiel(familie={"stand": "verheiratet", "seit": "01.06.2022", "partner_name": "Max Muster",
                              "partner_geburtsdatum": "01.01.1990", "partner_oeffentlicher_dienst": False,
                              "kinder": [{"name": "Kim Muster", "geburtsdatum": "01.01.2024"}]})
        w = felder("fin770", a)
        self.assertEqual(w["Kontrollkästchen5"], "/Ja")
        self.assertEqual(w["Datum"], "01.06.2022")
        self.assertEqual(w["Kontrollkästchen15"], "/Ja")
        self.assertEqual((w["1_2"], w["Text16"]), ("Kim Muster", "01.01.2024"))
        gilt = {f.schluessel: g for f, g, _ in formulare.auswahl(a)}
        self.assertTrue(gilt["fin708"])
        self.assertTrue(gilt["zsp1360"])

    def test_geschieden(self):
        w = felder("fin770", beispiel(familie={"stand": "geschieden", "seit": "01.01.2020"}))
        self.assertEqual((w["Kontrollkästchen7"], w["geschieden seit"]), ("/Ja", "01.01.2020"))

    def test_falscher_familienstand(self):
        with self.assertRaises(ValueError):
            felder("fin770", beispiel(familie={"stand": "single"}))

    def test_staatspruefung_bestanden(self):
        w = felder("fin770", beispiel(dienst={"laufbahnpruefung_am": "15.01.2027", "laufbahnpruefung_note": "2,0"}))
        self.assertEqual((w["Kontrollkästchen35"], w["Text43"], w["Ergebnis_2"]), ("/Ja", "15.01.2027", "2,0"))


class TestWeitere(unittest.TestCase):
    def test_einstellungserklaerung_zwei_ausfertigungen(self):
        a = beispiel()
        self.assertEqual(felder("zsp0001a", a)["Zwangsvollstreckungsmaßnahmen"], "/0")
        self.assertEqual(felder("zsp0001b", a)["Zwangsvollstreckungsmaßnahmen"], "/2")

    def test_erklaerungen_ohne_angabe_bleiben_leer(self):
        a = beispiel(erklaerungen=None)
        w = felder("zsp0001a", a)
        self.assertNotIn("Verurteilungen keine", w)
        self.assertNotIn("Zwangsvollstreckungsmaßnahmen", w)
        self.assertIn("erklaerungen.keine_verurteilungen", a.fehlend)

    def test_bank(self):
        w = felder("zsp0013a", beispiel())
        self.assertEqual(w["IBAN"], "02120300000000202051")
        self.assertEqual((w["Kirche"], w["Kinder"], w["Check Box1"]), ("--", "Nein", "/Ja"))
        with self.assertRaises(ValueError):
            felder("zsp0013a", beispiel(geld={"iban": "AT61 1904 3002 3457 3201"}))
        with self.assertRaises(ValueError):
            felder("zsp0013a", beispiel(geld={"kirche": "neuapostolisch"}))

    def test_arbeitszeit(self):
        self.assertEqual(felder("zsp3999", beispiel())["oder"], "/On")
        w = felder("zsp3999", beispiel(dienst={"arbeitszeit": "teilzeit", "teilzeit_stunden": "20",
                                               "pflichtstunden": "26"}))
        self.assertEqual((w["undefined_4"], w["Teilzeit mit"], w["von"]), ("X", "20", "26"))
        self.assertNotIn("oder", w)

    def test_firmenticket(self):
        w = felder("zsp2603", beispiel())
        self.assertEqual((w["Firmenticket"], w["Firmenticket_Art"]), ("/JA", "/Deutschlandticket_Job"))
        w = felder("zsp2603", beispiel(geld={"firmenticket": "nein"}))
        self.assertEqual(w["Firmenticket"], "/Nein")
        self.assertNotIn("Firmenticket_Art", w)

    def test_antrag_verbeamtung(self):
        w = felder("zsp0005", beispiel())
        self.assertEqual((w["Antrag VB"], w["ja"], w["ja_2"], w["ja_3"]), ("/On",) * 4)
        self.assertEqual(w["Absender 1"], "Erika Anna Muster")
        w = felder("zsp0005", beispiel(person={"geburtsdatum": "01.01.1970"}))
        self.assertEqual(w["toggle_7"], "/On")

    def test_auswahl(self):
        gilt = {f.schluessel: (g, grund) for f, g, grund in formulare.auswahl(beispiel())}
        self.assertFalse(gilt["fin761"][0])
        self.assertFalse(gilt["fin708"][0])
        self.assertFalse(gilt["fin586"][0])
        self.assertTrue(gilt["zsp0029"][0])
        offen = {f.schluessel: g for f, g, _ in formulare.auswahl(Angaben({}))}
        self.assertIsNone(offen["fin586"])  # unbekannt: wird mitgedruckt
        self.assertIsNone(offen["fin761"])

    def test_seiten_ohne_ueberschneidung(self):
        alle = [s for f in formulare.FORMULARE for s in f.seiten]
        self.assertEqual(len(alle), len(set(alle)))
        self.assertTrue(all(1 <= s <= formulare.SEITEN_PAKET for s in alle))


if __name__ == "__main__":
    unittest.main()
