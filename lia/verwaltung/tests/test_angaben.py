import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from angaben import Angaben, AngabenFehler, laden
from tests.hilfe import beispiel


class TestAngaben(unittest.TestCase):
    def test_fehlende_werte_werden_gemerkt(self):
        a = Angaben({"person": {"nachname": "Muster", "ort": " "}})
        self.assertEqual(a.text("person.nachname"), "Muster")
        self.assertEqual(a.text("person.ort"), "")
        self.assertIsNone(a.ja("person.deutsch"))
        self.assertEqual(a.text("dienst.personalnummer", merken=False), "")
        self.assertEqual(a.fehlend, ["person.ort", "person.deutsch"])

    def test_formate(self):
        a = Angaben({"person": {"geburtsdatum": "1.2.1995", "deutsch": "ja", "nachname": True}})
        with self.assertRaises(AngabenFehler):
            a.datum("person.geburtsdatum")
        with self.assertRaises(AngabenFehler):
            a.ja("person.deutsch")
        with self.assertRaises(AngabenFehler):
            a.text("person.nachname")

    def test_abgeleitete_werte(self):
        a = beispiel(person={"geburtsname": "Alt"})
        self.assertEqual(a.name_komma(), "Muster, Erika Anna")
        self.assertEqual(a.nachname_mit_geburtsname(), "Muster, geb. Alt")
        self.assertEqual(a.anschrift(), "Beispielstraße 1, 10115 Berlin")
        self.assertEqual(a.zum_absender(), ["Erika Anna Muster", "Beispielstraße 1", "10115 Berlin"])

    def test_alter(self):
        a = Angaben({"person": {"geburtsdatum": "10.11.1979"}})
        self.assertFalse(a.unter_47(date(2026, 11, 10)))  # 47. Geburtstag: vollendet
        self.assertTrue(a.unter_47(date(2026, 11, 9)))
        self.assertFalse(a.vor_1972())
        self.assertTrue(Angaben({"person": {"geburtsdatum": "12.01.1972"}}).vor_1972())
        self.assertIsNone(Angaben({}).unter_47(date(2026, 1, 1)))

    def test_laden_verlangt_600(self):
        with tempfile.TemporaryDirectory() as d:
            pfad = Path(d) / "angaben.toml"
            with self.assertRaises(AngabenFehler):
                laden(pfad)
            pfad.write_text('[person]\nnachname = "Muster"\n', encoding="utf-8")
            os.chmod(pfad, 0o644)
            with self.assertRaises(AngabenFehler):
                laden(pfad)
            os.chmod(pfad, 0o600)
            self.assertEqual(laden(pfad).text("person.nachname"), "Muster")
            pfad.write_text("kaputt = ", encoding="utf-8")
            with self.assertRaises(AngabenFehler):
                laden(pfad)


if __name__ == "__main__":
    unittest.main()
