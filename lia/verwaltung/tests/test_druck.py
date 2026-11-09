import tempfile
import unittest
from datetime import date
from pathlib import Path

import druck
import formulare
from angaben import Angaben
from tests.hilfe import PAKET, beispiel, braucht_paket

TAG = date(2026, 11, 10)


class TestPruefsumme(unittest.TestCase):
    def test_geaendertes_paket(self):
        with tempfile.TemporaryDirectory() as d:
            pfad = Path(d) / "paket.pdf"
            pfad.write_bytes(b"%PDF-1.4 anders")
            with self.assertRaises(druck.DruckFehler):
                druck.paket_oeffnen(pfad, formulare.PAKET_SHA256, formulare.SEITEN_PAKET)


@braucht_paket
class TestMitPaket(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paket = druck.paket_oeffnen(PAKET, formulare.PAKET_SHA256, formulare.SEITEN_PAKET)

    def bauen(self, a):
        teile = [druck.formular_bauen(self.paket, f.seiten, f.felder(a, TAG), f.schluessel)
                 for f, gilt, _ in formulare.auswahl(a) if gilt is not False]
        return druck.zusammenfuegen(teile)

    def test_alle_feldnamen_gibt_es(self):
        # alle Formulare, auch die bedingten, mit möglichst vielen Angaben
        a = beispiel(familie={"stand": "verheiratet", "seit": "01.06.2022", "partner_name": "Max",
                              "partner_geburtsdatum": "01.01.1990", "partner_oeffentlicher_dienst": True,
                              "kinder": [{"name": f"Kind {i}", "geburtsdatum": "01.01.2020"} for i in range(4)]},
                     dienst={"laufbahnpruefung_am": "15.01.2027", "personalnummer": "123"})
        for f in formulare.FORMULARE:
            druck.formular_bauen(self.paket, f.seiten, f.felder(a, TAG), f.schluessel)  # wirft bei Tippfehlern

    def test_werte_landen_im_richtigen_formular(self):
        werte = druck.feldwerte(self.bauen(beispiel()))
        self.assertEqual(werte["fin770.Name ggf auch Geburtsname"], "Muster")
        self.assertEqual(werte["zsp0013a.Nachname"], "Muster")
        self.assertEqual(werte["zsp0001a.Zwangsvollstreckungsmaßnahmen"], "/0")
        self.assertEqual(werte["zsp0001b.Zwangsvollstreckungsmaßnahmen"], "/2")
        self.assertEqual(werte["zsp0007.undefined_4"], "Erika Anna Muster")
        self.assertFalse(any(k.startswith("fin586.") for k in werte))  # VL nicht gewünscht

    def test_ohne_angaben_nur_feste_kreuze(self):
        a = Angaben({})
        gefuellt = druck.feldwerte(self.bauen(a))
        leer = druck.feldwerte(druck.zusammenfuegen([
            druck.formular_bauen(self.paket, f.seiten, {}, f.schluessel)
            for f, gilt, _ in formulare.auswahl(a) if gilt is not False]))  # Vorgaben im PDF selbst
        neu = {k for k in gefuellt if gefuellt[k] != leer.get(k)}
        self.assertEqual(neu, {"zsp0005.Antrag VB", "zsp2603.Beschäftigtengruppe", "zsp0013a.Check Box1"})

    def test_unbekanntes_feld(self):
        with self.assertRaises(druck.DruckFehler):
            druck.formular_bauen(self.paket, [37], {"Gibtsnicht": "x"}, "zsp0013a")


if __name__ == "__main__":
    unittest.main()
